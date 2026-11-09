"""Çoklu coin portföy backtest motoru (1 saatlik ortak zaman ekseni, T x N diziler).

Varsayımlar (muhafazakâr):
  * Sinyal t mumunun kapanışında; giriş t+1 açılışında. Çıkış sinyali de bir sonraki açılışta uygulanır.
  * Stop/hedef mum içi high/low ile; aynı mumda ikisi de değerse önce STOP.
  * Açılış boşluğu stopu aşarsa açılıştan çıkılır.
  * Masraf: her taraf için oran (komisyon + kayma). Fonlama: pozisyon açıkken her fonlama saatinde
    long: -notional*oran, short: +notional*oran.
  * Pozisyon boyutu: risk_oran * özsermaye / stop_mesafesi_%; tek pozisyon notional'ı <= ozsermaye*max_pay.
    Toplam brüt notional <= ozsermaye*max_brut (kaldıraçsız: 1.0).
  * Evrende olmayan coinde yeni pozisyon açılmaz; açık pozisyon evrenden çıksa da kurallarına göre yönetilir.
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _portfoy(O, H, L, C, SIG, STOP, ATR, CIKIS, FUND, UYE, ONCELIK, GSEV, IZSEV, SON, BEZ,
             risk_oran, max_poz, max_yon, max_pay, max_brut, maliyet,
             tp1_r, tp1_pay, iz_atr, be_sonra_tp1, hedef_r, max_bar, ici_sira, tasfiye_d=0.0, kaldirac=1.0):
    # tasfiye_d > 0: izole teminatlı kaldıraç. Girişte stop, giriş fiyatından tasfiye_d (oran) kadar uzaktaysa
    # tasfiye fiyatı = giriş x (1 - yön x tasfiye_d); fiyat bu seviyeye stoptan önce değerse pozisyonun teminatının
    # tamamı (notional / kaldirac) kaybedilir (sebep 8). Stop başabaşa ya da tasfiyenin içine çekilince kontrol kalkar.
    T, N = C.shape
    liq = np.full(C.shape[1], np.nan)
    ozs = 1.0
    egri = np.empty(T)
    # açık pozisyon durumu (coin başına)
    acik = np.zeros(N, np.bool_)
    yon = np.zeros(N); miktar = np.zeros(N); giris = np.zeros(N); stop = np.zeros(N)
    risk_f = np.zeros(N); tp1 = np.zeros(N); tp1_yapildi = np.zeros(N, np.bool_)
    en_iyi = np.zeros(N); gi = np.zeros(N, np.int64); bekleyen_cikis = np.zeros(N, np.bool_)
    hedef = np.zeros(N); r_toplam = np.zeros(N); fon_top = np.zeros(N); q0 = np.zeros(N); ozs0 = np.zeros(N)
    # işlem kaydı
    kayit = np.zeros((200000, 13))
    k = 0
    bekleyen = np.zeros(N)       # t kapanışında üretilen giriş sinyali (t+1 açılışında)
    bek_stop = np.zeros(N)
    bek_sev = np.full(N, np.nan)   # bekleyen emir seviyesi (NaN: piyasa emriyle açılışta giriş)
    emir_giris = np.zeros(N, np.bool_)
    for t in range(T):
        if k >= kayit.shape[0] - 4 * C.shape[1]:
            raise ValueError("islem kaydi tamponu doldu")
        # 1) bekleyen girişler: t açılışında
        if t > 0:
            nacik = 0; nl = 0; ns = 0; brut = 0.0
            for j in range(N):
                if acik[j]:
                    nacik += 1
                    if yon[j] > 0:
                        nl += 1
                    else:
                        ns += 1
                    brut += miktar[j] * C[t - 1, j]
            # öncelik sırasına göre
            sira = np.argsort(ONCELIK[t - 1])
            for jj in range(N):
                j = sira[jj]
                if bekleyen[j] == 0 or acik[j] or np.isnan(O[t, j]):
                    continue
                if nacik >= max_poz:
                    break
                if bekleyen[j] > 0 and nl >= max_yon:
                    continue
                if bekleyen[j] < 0 and ns >= max_yon:
                    continue
                px = O[t, j]
                sd = bek_stop[j]
                if sd <= 0 or np.isnan(sd):
                    continue
                lvl = bek_sev[j]
                emirli = not np.isnan(lvl)
                if emirli:   # bekleyen (stop) emir: yalnız bu mum seviyeye değerse dolar
                    if bekleyen[j] > 0:
                        if H[t, j] < lvl:
                            continue
                        px = max(O[t, j], lvl)
                        sd = px - (lvl - bek_stop[j])
                    else:
                        if L[t, j] > lvl:
                            continue
                        px = min(O[t, j], lvl)
                        sd = (lvl + bek_stop[j]) - px
                    if sd <= 0:
                        continue
                notional = risk_oran * ozs / (sd / px)
                notional = min(notional, max_pay * ozs, max_brut * ozs - brut)
                if notional <= 0.0005 * ozs:
                    continue
                acik[j] = True; yon[j] = bekleyen[j]; giris[j] = px; miktar[j] = notional / px
                stop[j] = px - yon[j] * sd; risk_f[j] = sd; tp1_yapildi[j] = False
                tp1[j] = px + yon[j] * tp1_r * sd if tp1_r > 0 else np.nan
                hedef[j] = px + yon[j] * hedef_r * sd if hedef_r > 0 else np.nan
                liq[j] = px * (1.0 - yon[j] * tasfiye_d) if (tasfiye_d > 0 and sd / px > tasfiye_d) else np.nan
                en_iyi[j] = px; gi[j] = t; emir_giris[j] = emirli; bekleyen_cikis[j] = False; r_toplam[j] = 0.0; fon_top[j] = 0.0; q0[j] = miktar[j]; ozs0[j] = ozs
                ozs -= notional * maliyet
                r_toplam[j] -= notional * maliyet
                nacik += 1; brut += notional
                if yon[j] > 0:
                    nl += 1
                else:
                    ns += 1
        bekleyen[:] = 0
        bek_sev[:] = np.nan
        # 2) açık pozisyon yönetimi
        for j in range(N):
            if not acik[j]:
                continue
            y = yon[j]
            o = O[t, j]; h = H[t, j]; l = L[t, j]; c = C[t, j]
            if np.isnan(c) and t <= SON[j]:   # geçici veri boşluğu: pozisyon korunur, veri gelince yönetilir
                continue
            if np.isnan(c):   # veri bitti (delist) -> son geçerli kapanıştan kapat
                cik = C[SON[j], j]
                pnl = y * (cik - giris[j]) * miktar[j] - miktar[j] * cik * maliyet
                ozs += pnl
                r_toplam[j] += pnl
                kayit[k, 0] = gi[j]; kayit[k, 1] = t; kayit[k, 2] = j; kayit[k, 3] = y; kayit[k, 4] = giris[j]
                kayit[k, 5] = cik; kayit[k, 6] = r_toplam[j] / (q0[j] * risk_f[j]); kayit[k, 7] = 6; kayit[k, 8] = risk_f[j]; kayit[k, 9] = fon_top[j]; kayit[k, 10] = q0[j] * giris[j]; kayit[k, 11] = r_toplam[j] / ozs0[j]; kayit[k, 12] = r_toplam[j]
                k += 1; acik[j] = False
                continue
            cikis_px = np.nan; sebep = 0
            ilk_mum = emir_giris[j] and gi[j] == t   # emirle girilen mum: açılış kontrolü yok, kötümser stop
            lq = liq[j]
            if not np.isnan(lq):     # izole teminat tasfiyesi (stoptan önce; bekleyen çıkışta yalnız açılış fiyatı)
                ust = o if bekleyen_cikis[j] else (l if y > 0 else h)
                if (y > 0 and ust <= lq) or (y < 0 and ust >= lq):
                    pnl = -miktar[j] * giris[j] / kaldirac
                    ozs += pnl
                    r_toplam[j] += pnl
                    kayit[k, 0] = gi[j]; kayit[k, 1] = t; kayit[k, 2] = j; kayit[k, 3] = y; kayit[k, 4] = giris[j]
                    kayit[k, 5] = lq; kayit[k, 6] = r_toplam[j] / (q0[j] * risk_f[j]); kayit[k, 7] = 8; kayit[k, 8] = risk_f[j]; kayit[k, 9] = fon_top[j]; kayit[k, 10] = q0[j] * giris[j]; kayit[k, 11] = r_toplam[j] / ozs0[j]; kayit[k, 12] = r_toplam[j]
                    k += 1; acik[j] = False
                    continue
            if ilk_mum:
                if (y > 0 and l <= stop[j]) or (y < 0 and h >= stop[j]):
                    cikis_px = stop[j]; sebep = 1
            elif bekleyen_cikis[j]:
                cikis_px = o; sebep = 3
            else:
                if (y > 0 and o <= stop[j]) or (y < 0 and o >= stop[j]):
                    cikis_px = o; sebep = 1
                elif (y > 0 and l <= stop[j]) or (y < 0 and h >= stop[j]):
                    cikis_px = stop[j]; sebep = 1
            # kısmi kâr al (stop vurulmadıysa)
            if sebep == 0 and tp1_r > 0 and not tp1_yapildi[j] and not ilk_mum:
                if (y > 0 and h >= tp1[j]) or (y < 0 and l <= tp1[j]):
                    px = max(o, tp1[j]) if y > 0 else min(o, tp1[j])
                    q = miktar[j] * tp1_pay
                    pnl = y * (px - giris[j]) * q - q * px * maliyet
                    ozs += pnl
                    r_toplam[j] += pnl
                    miktar[j] -= q
                    tp1_yapildi[j] = True
                    if be_sonra_tp1:
                        if y * (giris[j] - stop[j]) > 0:
                            stop[j] = giris[j]
                    if not np.isnan(liq[j]) and y * (stop[j] - liq[j]) > 0:
                        liq[j] = np.nan
                    # aynı mum içinde yeni (başabaş) stop: 0 = kontrol yok (eski), 1 = OHLC yolu varsayımı
                    # (long: düşüş mumunda önce tepe sonra dip; her durumda kapanış stopun altındaysa vurulmuş),
                    # 2 = kötümser (mumun dibi stopa değdiyse vurulmuş)
                    if ici_sira > 0:
                        if ici_sira == 3:   # 1 dakikalık veriyle çözülmüş: BEZ[t, coin] > 0 ise başabaş bu mumda vuruldu
                            vur = BEZ[t, j] > 0
                        elif ici_sira == 2:
                            vur = (y > 0 and l <= stop[j]) or (y < 0 and h >= stop[j])
                        else:
                            vur = (y > 0 and ((c < o and l <= stop[j]) or c <= stop[j])) or \
                                  (y < 0 and ((c > o and h >= stop[j]) or c >= stop[j]))
                        if vur:
                            cikis_px = stop[j]; sebep = 1
            if sebep == 0 and hedef_r > 0 and not ilk_mum:
                if (y > 0 and h >= hedef[j]) or (y < 0 and l <= hedef[j]):
                    cikis_px = max(o, hedef[j]) if y > 0 else min(o, hedef[j]); sebep = 2
            if sebep != 0:
                q = miktar[j]
                pnl = y * (cikis_px - giris[j]) * q - q * cikis_px * maliyet
                ozs += pnl
                r_toplam[j] += pnl
                kayit[k, 0] = gi[j]; kayit[k, 1] = t; kayit[k, 2] = j; kayit[k, 3] = y; kayit[k, 4] = giris[j]
                kayit[k, 5] = cikis_px; kayit[k, 6] = r_toplam[j] / (q0[j] * risk_f[j]); kayit[k, 7] = sebep; kayit[k, 8] = risk_f[j]; kayit[k, 9] = fon_top[j]; kayit[k, 10] = q0[j] * giris[j]; kayit[k, 11] = r_toplam[j] / ozs0[j]; kayit[k, 12] = r_toplam[j]
                k += 1; acik[j] = False
                continue
            # fonlama (bu saatte fonlama varsa)
            f = FUND[t, j]
            if f != 0 and not np.isnan(f):
                odeme = -y * miktar[j] * c * f
                ozs += odeme
                fon_top[j] += odeme
                r_toplam[j] += odeme
            # kapanışta yönetim: izleyen stop, çıkış sinyali, süre
            if y > 0:
                en_iyi[j] = max(en_iyi[j], c)
            else:
                en_iyi[j] = min(en_iyi[j], c)
            iv = IZSEV[t, j]           # iz süren stop seviyesi (ör. son salınım dibi); yalnız stopu iyileştirir
            if not np.isnan(iv) and y * (iv - stop[j]) > 0:
                stop[j] = iv
            if iz_atr > 0 and not np.isnan(ATR[t, j]):
                yeni = en_iyi[j] - y * iz_atr * ATR[t, j]
                if y * (yeni - stop[j]) > 0:
                    stop[j] = yeni
            if not np.isnan(liq[j]) and y * (stop[j] - liq[j]) > 0:   # stop tasfiyenin içine çekildi
                liq[j] = np.nan
            if CIKIS[t, j] == -y or CIKIS[t, j] == 2:
                bekleyen_cikis[j] = True
            if max_bar > 0 and t - gi[j] >= max_bar:
                bekleyen_cikis[j] = True
        # 3) yeni sinyaller (t kapanışı)
        for j in range(N):
            if not acik[j] and UYE[t, j] and SIG[t, j] != 0 and not np.isnan(STOP[t, j]):
                bekleyen[j] = SIG[t, j]; bek_stop[j] = STOP[t, j]; bek_sev[j] = GSEV[t, j]
        # 4) piyasa değeri ile özsermaye eğrisi
        acik_pnl = 0.0
        for j in range(N):
            if acik[j] and not np.isnan(C[t, j]):
                acik_pnl += yon[j] * (C[t, j] - giris[j]) * miktar[j]
        egri[t] = ozs + acik_pnl
    # dönem sonunda açık kalan pozisyonlar: son geçerli fiyattan, çıkış masrafı düşülmeden (özsermaye eğrisiyle aynı)
    for j in range(N):
        if acik[j]:
            tt = min(T - 1, SON[j]); cik = C[tt, j]
            acik_pnl = yon[j] * (cik - giris[j]) * miktar[j]
            kayit[k, 0] = gi[j]; kayit[k, 1] = tt; kayit[k, 2] = j; kayit[k, 3] = yon[j]; kayit[k, 4] = giris[j]
            kayit[k, 5] = cik; kayit[k, 6] = (r_toplam[j] + acik_pnl) / (q0[j] * risk_f[j]); kayit[k, 7] = 7
            kayit[k, 8] = risk_f[j]; kayit[k, 9] = fon_top[j]; kayit[k, 10] = q0[j] * giris[j]
            kayit[k, 11] = (r_toplam[j] + acik_pnl) / ozs0[j]; kayit[k, 12] = r_toplam[j] + acik_pnl
            k += 1
    return egri, kayit[:k]


@njit(cache=True)
def _portfoy_s(O, H, L, C, SIG, STOP, ATR, CIKIS, FUND, UYE, ONCELIK, GSEV, IZSEV, SON, BEZ, S, ekle_r,
             risk_oran, max_poz, max_yon, max_pay, max_brut, maliyet,
             tp1_r, tp1_pay, iz_atr, be_sonra_tp1, hedef_r, max_bar, ici_sira):
    T, N = C.shape
    P = N * S
    ozs = 1.0
    egri = np.empty(T)
    # açık pozisyon durumu (slot başına; slot p'nin coini p // S)
    acik = np.zeros(P, np.bool_)
    yon = np.zeros(P); miktar = np.zeros(P); giris = np.zeros(P); stop = np.zeros(P)
    risk_f = np.zeros(P); tp1 = np.zeros(P); tp1_yapildi = np.zeros(P, np.bool_)
    en_iyi = np.zeros(P); gi = np.zeros(P, np.int64); bekleyen_cikis = np.zeros(P, np.bool_)
    hedef = np.zeros(P); r_toplam = np.zeros(P); fon_top = np.zeros(P); q0 = np.zeros(P); ozs0 = np.zeros(P)
    emir_giris = np.zeros(P, np.bool_)
    # işlem kaydı
    kayit = np.zeros((200000, 13))
    k = 0
    bekleyen = np.zeros(N)       # t kapanışında üretilen giriş sinyali (t+1 açılışında)
    bek_stop = np.zeros(N)
    bek_sev = np.full(N, np.nan)   # bekleyen emir seviyesi (NaN: piyasa emriyle açılışta giriş)
    for t in range(T):
        if k >= kayit.shape[0] - 4 * C.shape[1]:
            raise ValueError("islem kaydi tamponu doldu")
        # 1) bekleyen girişler: t açılışında
        if t > 0:
            nacik = 0; nl = 0; ns = 0; brut = 0.0
            for pp in range(P):
                if acik[pp]:
                    nacik += 1
                    if yon[pp] > 0:
                        nl += 1
                    else:
                        ns += 1
                    brut += miktar[pp] * C[t - 1, pp // S]
            # öncelik sırasına göre
            sira = np.argsort(ONCELIK[t - 1])
            for jj in range(N):
                j = sira[jj]
                if bekleyen[j] == 0 or np.isnan(O[t, j]):
                    continue
                # boş slot: ilk slot boşsa normal giriş; değilse ekleme -> son açık slot >= ekle_r R kârda olmalı
                slot = -1
                for s_ in range(S):
                    pp = j * S + s_
                    if not acik[pp]:
                        if s_ == 0:
                            slot = pp
                        else:
                            onceki = pp - 1
                            if acik[onceki] and yon[onceki] == bekleyen[j] and \
                                    yon[onceki] * (C[t - 1, j] - giris[onceki]) >= ekle_r * risk_f[onceki]:
                                slot = pp
                        break
                if slot < 0:
                    continue
                if nacik >= max_poz:
                    break
                if bekleyen[j] > 0 and nl >= max_yon:
                    continue
                if bekleyen[j] < 0 and ns >= max_yon:
                    continue
                px = O[t, j]
                sd = bek_stop[j]
                if sd <= 0 or np.isnan(sd):
                    continue
                lvl = bek_sev[j]
                emirli = not np.isnan(lvl)
                if emirli:   # bekleyen (stop) emir: yalnız bu mum seviyeye değerse dolar
                    if bekleyen[j] > 0:
                        if H[t, j] < lvl:
                            continue
                        px = max(O[t, j], lvl)
                        sd = px - (lvl - bek_stop[j])
                    else:
                        if L[t, j] > lvl:
                            continue
                        px = min(O[t, j], lvl)
                        sd = (lvl + bek_stop[j]) - px
                    if sd <= 0:
                        continue
                notional = risk_oran * ozs / (sd / px)
                notional = min(notional, max_pay * ozs, max_brut * ozs - brut)
                if notional <= 0.0005 * ozs:
                    continue
                q_ = slot
                acik[q_] = True; yon[q_] = bekleyen[j]; giris[q_] = px; miktar[q_] = notional / px
                stop[q_] = px - yon[q_] * sd; risk_f[q_] = sd; tp1_yapildi[q_] = False
                tp1[q_] = px + yon[q_] * tp1_r * sd if tp1_r > 0 else np.nan
                hedef[q_] = px + yon[q_] * hedef_r * sd if hedef_r > 0 else np.nan
                en_iyi[q_] = px; gi[q_] = t; emir_giris[q_] = emirli; bekleyen_cikis[q_] = False; r_toplam[q_] = 0.0; fon_top[q_] = 0.0; q0[q_] = miktar[q_]; ozs0[q_] = ozs
                ozs -= notional * maliyet
                r_toplam[q_] -= notional * maliyet
                nacik += 1; brut += notional
                if yon[q_] > 0:
                    nl += 1
                else:
                    ns += 1
        bekleyen[:] = 0
        bek_sev[:] = np.nan
        # 2) açık pozisyon yönetimi
        for pp in range(P):
            if not acik[pp]:
                continue
            jc = pp // S
            j = pp
            y = yon[j]
            o = O[t, jc]; h = H[t, jc]; l = L[t, jc]; c = C[t, jc]
            if np.isnan(c) and t <= SON[jc]:   # geçici veri boşluğu: pozisyon korunur
                continue
            if np.isnan(c):   # veri bitti (delist) -> son geçerli kapanıştan kapat
                cik = C[SON[jc], jc]
                pnl = y * (cik - giris[j]) * miktar[j] - miktar[j] * cik * maliyet
                ozs += pnl
                r_toplam[j] += pnl
                kayit[k, 0] = gi[j]; kayit[k, 1] = t; kayit[k, 2] = jc; kayit[k, 3] = y; kayit[k, 4] = giris[j]
                kayit[k, 5] = cik; kayit[k, 6] = r_toplam[j] / (q0[j] * risk_f[j]); kayit[k, 7] = 6; kayit[k, 8] = risk_f[j]; kayit[k, 9] = fon_top[j]; kayit[k, 10] = q0[j] * giris[j]; kayit[k, 11] = r_toplam[j] / ozs0[j]; kayit[k, 12] = r_toplam[j]
                k += 1; acik[j] = False
                continue
            cikis_px = np.nan; sebep = 0
            ilk_mum = emir_giris[j] and gi[j] == t   # emirle girilen mum: açılış kontrolü yok, kötümser stop
            if ilk_mum:
                if (y > 0 and l <= stop[j]) or (y < 0 and h >= stop[j]):
                    cikis_px = stop[j]; sebep = 1
            elif bekleyen_cikis[j]:
                cikis_px = o; sebep = 3
            else:
                if (y > 0 and o <= stop[j]) or (y < 0 and o >= stop[j]):
                    cikis_px = o; sebep = 1
                elif (y > 0 and l <= stop[j]) or (y < 0 and h >= stop[j]):
                    cikis_px = stop[j]; sebep = 1
            # kısmi kâr al (stop vurulmadıysa)
            if sebep == 0 and tp1_r > 0 and not tp1_yapildi[j] and not ilk_mum:
                if (y > 0 and h >= tp1[j]) or (y < 0 and l <= tp1[j]):
                    px = max(o, tp1[j]) if y > 0 else min(o, tp1[j])
                    q = miktar[j] * tp1_pay
                    pnl = y * (px - giris[j]) * q - q * px * maliyet
                    ozs += pnl
                    r_toplam[j] += pnl
                    miktar[j] -= q
                    tp1_yapildi[j] = True
                    if be_sonra_tp1:
                        if y * (giris[j] - stop[j]) > 0:
                            stop[j] = giris[j]
                    # aynı mum içinde yeni (başabaş) stop: 0 = kontrol yok (eski), 1 = OHLC yolu varsayımı
                    # (long: düşüş mumunda önce tepe sonra dip; her durumda kapanış stopun altındaysa vurulmuş),
                    # 2 = kötümser (mumun dibi stopa değdiyse vurulmuş)
                    if ici_sira > 0:
                        if ici_sira == 3:   # 1 dakikalık veriyle çözülmüş: BEZ[t, coin] > 0 ise başabaş bu mumda vuruldu
                            vur = BEZ[t, jc] > 0
                        elif ici_sira == 2:
                            vur = (y > 0 and l <= stop[j]) or (y < 0 and h >= stop[j])
                        else:
                            vur = (y > 0 and ((c < o and l <= stop[j]) or c <= stop[j])) or \
                                  (y < 0 and ((c > o and h >= stop[j]) or c >= stop[j]))
                        if vur:
                            cikis_px = stop[j]; sebep = 1
            if sebep == 0 and hedef_r > 0 and not ilk_mum:
                if (y > 0 and h >= hedef[j]) or (y < 0 and l <= hedef[j]):
                    cikis_px = max(o, hedef[j]) if y > 0 else min(o, hedef[j]); sebep = 2
            if sebep != 0:
                q = miktar[j]
                pnl = y * (cikis_px - giris[j]) * q - q * cikis_px * maliyet
                ozs += pnl
                r_toplam[j] += pnl
                kayit[k, 0] = gi[j]; kayit[k, 1] = t; kayit[k, 2] = jc; kayit[k, 3] = y; kayit[k, 4] = giris[j]
                kayit[k, 5] = cikis_px; kayit[k, 6] = r_toplam[j] / (q0[j] * risk_f[j]); kayit[k, 7] = sebep; kayit[k, 8] = risk_f[j]; kayit[k, 9] = fon_top[j]; kayit[k, 10] = q0[j] * giris[j]; kayit[k, 11] = r_toplam[j] / ozs0[j]; kayit[k, 12] = r_toplam[j]
                k += 1; acik[j] = False
                continue
            # fonlama (bu saatte fonlama varsa)
            f = FUND[t, jc]
            if f != 0 and not np.isnan(f):
                odeme = -y * miktar[j] * c * f
                ozs += odeme
                fon_top[j] += odeme
                r_toplam[j] += odeme
            # kapanışta yönetim: izleyen stop, çıkış sinyali, süre
            if y > 0:
                en_iyi[j] = max(en_iyi[j], c)
            else:
                en_iyi[j] = min(en_iyi[j], c)
            iv = IZSEV[t, jc]           # iz süren stop seviyesi (ör. son salınım dibi); yalnız stopu iyileştirir
            if not np.isnan(iv) and y * (iv - stop[j]) > 0:
                stop[j] = iv
            if iz_atr > 0 and not np.isnan(ATR[t, jc]):
                yeni = en_iyi[j] - y * iz_atr * ATR[t, jc]
                if y * (yeni - stop[j]) > 0:
                    stop[j] = yeni
            if CIKIS[t, jc] == -y or CIKIS[t, jc] == 2:
                bekleyen_cikis[j] = True
            if max_bar > 0 and t - gi[j] >= max_bar:
                bekleyen_cikis[j] = True
        # 3) yeni sinyaller (t kapanışı)
        for j in range(N):
            if UYE[t, j] and SIG[t, j] != 0 and not np.isnan(STOP[t, j]):
                bekleyen[j] = SIG[t, j]; bek_stop[j] = STOP[t, j]; bek_sev[j] = GSEV[t, j]
        # 4) piyasa değeri ile özsermaye eğrisi
        acik_pnl = 0.0
        for pp in range(P):
            if acik[pp] and not np.isnan(C[t, pp // S]):
                acik_pnl += yon[pp] * (C[t, pp // S] - giris[pp]) * miktar[pp]
        egri[t] = ozs + acik_pnl
    return egri, kayit[:k]



SEBEP = {1: "stop", 2: "hedef", 3: "sinyal/süre", 6: "veri sonu", 7: "açık (dönem sonu)", 8: "tasfiye"}


def son_gecerli(C):
    """Her coinin son geçerli (NaN olmayan) fiyat indeksi; bundan sonra NaN = borsadan çıkış, öncesindeki NaN = geçici boşluk."""
    ok = ~np.isnan(C)
    return np.where(ok.any(0), C.shape[0] - 1 - np.argmax(ok[::-1], axis=0), -1).astype(np.int64)


def portfoy(V, SIG, STOP, ATR, CIKIS, ONCELIK, p, GSEV=None, IZSEV=None):
    """p['ici_sira']: aynı mumda 1R kısmi kârdan sonra başabaş stopunun ele alınışı (0 eski/iyimser, 1 OHLC yolu
    [varsayılan], 2 kötümser)."""
    """p['slot'] > 1 ise kârdaki pozisyona ekleme (piramit) yapan slotlu motor kullanılır (p['ekle_r']: ekleme için
    önceki pozisyonun asgari kârı, R)."""
    """GSEV: bekleyen emir seviyesi (T x N). Verilirse STOP, seviyeden stop fiyatına MESAFE olarak yorumlanır."""
    """V: dict(O,H,L,C,FUND,UYE, zaman, semboller). p: parametre sözlüğü."""
    import pandas as pd
    S = int(p.get("slot", 1))
    ortak = (V["O"], V["H"], V["L"], V["C"], SIG.astype(np.float64), STOP.astype(np.float64),
             ATR.astype(np.float64), CIKIS.astype(np.float64), V["FUND"], V["UYE"], ONCELIK.astype(np.float64),
             np.full(SIG.shape, np.nan) if GSEV is None else GSEV.astype(np.float64),
             np.full(SIG.shape, np.nan) if IZSEV is None else IZSEV.astype(np.float64), son_gecerli(V["C"]),
             np.zeros(SIG.shape) if p.get("BEZ") is None else np.asarray(p["BEZ"], np.float64))
    fn = _portfoy if S == 1 else _portfoy_s
    ek = () if S == 1 else (S, float(p.get("ekle_r", 1.0)))
    son = (float(p.get("tasfiye_d", 0.0)), float(p.get("kaldirac", 1.0))) if S == 1 else ()
    egri, kay = fn(*ortak, *ek,
                         p.get("risk", 0.01), p.get("max_poz", 10), p.get("max_yon", 10), p.get("max_pay", 0.25),
                         p.get("max_brut", 1.0), p.get("maliyet", 0.0007),
                         p.get("tp1_r", 0.0), p.get("tp1_pay", 0.5), p.get("iz_atr", 0.0),
                         p.get("be_tp1", True), p.get("hedef_r", 0.0), p.get("max_bar", 0), int(p.get("ici_sira", 1)), *son)
    z = V["zaman"]
    t = pd.DataFrame(kay, columns=["gi", "ci", "j", "yon", "giris", "cikis", "R", "sebep", "risk", "fonlama", "notional", "pnl_ozs", "pnl"])
    for c in ("gi", "ci", "j", "sebep"):
        t[c] = t[c].astype(int)
    t["sembol"] = np.asarray(V["semboller"])[t.j]
    t["giris_zaman"] = z[t.gi]; t["cikis_zaman"] = z[t.ci]
    t["sebep"] = t.sebep.map(SEBEP)
    return pd.Series(egri, index=z), t


def metrik(egri, t):
    import pandas as pd
    e = egri.dropna()
    gun = e.resample("1D").last().dropna()
    r = gun.pct_change().dropna()
    yil = (e.index[-1] - e.index[0]).days / 365.25
    cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yil) - 1 if yil > 0 and e.iloc[-1] > 0 else np.nan
    dd = (1 - e / e.cummax()).max()
    sharpe = r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else np.nan
    kaz = t.R[t.R > 0].sum(); kay = -t.R[t.R <= 0].sum()
    return dict(islem=len(t), kazanma=100 * (t.R > 0).mean() if len(t) else np.nan,
                pf=kaz / kay if kay > 0 else np.nan, ortR=t.R.mean() if len(t) else np.nan,
                toplam_getiri=100 * (e.iloc[-1] / e.iloc[0] - 1), cagr=100 * cagr, maxdd=100 * dd,
                sharpe=sharpe, calmar=(100 * cagr) / (100 * dd) if dd > 0 else np.nan,
                yillik_islem=len(t) / yil if yil > 0 else np.nan)
