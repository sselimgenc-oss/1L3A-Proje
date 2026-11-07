"""Olay güdümlü backtest motoru: tek sembol, aynı anda en fazla 1 pozisyon.

Zamanlama
  - Sinyal mum i KAPANIŞINDA üretilir; giriş/çıkış mum i+1 AÇILIŞINDA yapılır.
  - Stop/hedef mum içi yüksek/düşükle kontrol edilir. Aynı mumda ikisi de değerse STOP sayılır.
  - Fiyat stopun ötesinde açılırsa (gap) dolum açılış fiyatındandır.
  - Kısmi kâr (CikisAyarlari.kismi): seviye mum içinde görülürse o fiyattan (limit, hedefle aynı komisyon
    kuralı) pozisyonun belirtilen oranı kapanır; miktar step'e AŞAĞI yuvarlanır, kalan < min_qty ise tamamı
    kapanır. Aynı mumda stop da değerse önce stop sayılır, kısmi uygulanmaz. İşlem tablosunda pozisyon başına
    TEK satır vardır (net_pnl/komisyon/R tüm parçaları içerir); `miktar` ilk miktardır.
    `kismi_pnl` = kısmi parçaların brüt K/Z'si eksi o parçaların çıkış komisyonu (giriş komisyonu hariç).
    Funding kalan miktar üzerinden ödenir.
  - Giriş ve sinyal/zaman çıkışlarına `kayma_bps`; stop, stop_gap ve kill_switch çıkışlarına
    `stop_kayma_bps` uygulanır. Hedef (limit) dolumuna kayma uygulanmaz.
Funding
  - Pozisyon açıkken her funding zamanı f için `nominal * oran * yön` ödenir (pozitif oran long öder).
  - f, giriş zamanından SONRA ve çıkış zamanına (dahil) kadar olanlar için uygulanır.
  - İşlem tablosundaki `funding` sütunu ÖDENEN tutardır (negatif = tahsil edilen).
Risk
  - SERT_LIMITLER her zaman uygulanır; MotorAyarlari bunları aşarsa tavana kırpılır.
  - limit_modu="olc": günlük kayıp ve kill switch işlemi DURDURMAZ, yalnızca `limit_olaylari`na
    kaydedilir. YALNIZCA araştırma/backtest içindir; canlı ve paper'da kullanılmaz.
    İşlem başı risk ve kaldıraç tavanı her iki modda da uygulanır.
  - limit_modu="uygula": günlük kayıp limiti mum kapanışında aşılırsa açık pozisyon sonraki açılışta
    `stop_kayma_bps` ile kapanır (neden "gunluk_limit"); o UTC günü yeni giriş yok.
Yönlü çıkış: sinyal tablosunda opsiyonel `cikis_long` / `cikis_short` sütunları varsa long pozisyon yalnız
  `cikis_long` (veya genel `cikis`) ile, short yalnız `cikis_short` (veya `cikis`) ile kapanır. Sütunlar yoksa
  `cikis` her iki yönü kapatır (eski davranış).
Zorunlu çıkış: strateji.cikis_var_mi() False ve CikisAyarlari'nda hiç çıkış yoksa ValueError.
Muhasebe Decimal ile yapılır; çıktı tablosu float'tır.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Optional

import numpy as np
import pandas as pd

from motor.risk.limitler import SERT_LIMITLER
from motor.strateji import cikislar as cks
from motor.strateji import gostergeler as gst
from motor.strateji.temel import SINYAL_SUTUNLARI, Strateji


def D(x) -> Decimal:
    if isinstance(x, Decimal):
        return x
    return Decimal(repr(float(x)))


@dataclass
class SembolKurallari:
    tick_size: float = 0.01
    step_size: float = 0.001
    min_qty: float = 0.001
    min_notional: float = 5.0


@dataclass
class MotorAyarlari:
    baslangic_sermaye: float = 10000.0
    risk_yuzde: float = 1.0                  # işlem başı risk (%); sert limitle kırpılır
    kaldirac: float = 3.0                    # üst sınır; sert limitle kırpılır
    komisyon_taker_yuzde: float = 0.05
    komisyon_maker_yuzde: float = 0.02
    hedef_limit_emri: bool = False           # True: hedef dolumlarında maker komisyonu
    kayma_bps: float = 2.0                   # giriş, sinyal ve zaman çıkışları
    stop_kayma_bps: float = 5.0              # stop, stop_gap ve kill_switch çıkışları
    # "uygula": günlük kayıp / kill switch işlemi durdurur (varsayılan).
    # "olc": durdurmaz, sadece limit_olaylari'na kaydeder. YALNIZCA araştırma/backtest;
    # canlı ve paper'da kullanılmaz. İşlem başı risk ve kaldıraç tavanı her iki modda uygulanır.
    limit_modu: str = "uygula"
    kurallar: SembolKurallari = field(default_factory=SembolKurallari)


@dataclass
class SonucBacktest:
    islemler: pd.DataFrame
    ozsermaye: pd.Series
    reddedilenler: list
    uyarilar: list
    baslangic_sermaye: float
    limit_olaylari: list = field(default_factory=list)   # {tur, zaman, ozsermaye, dusus_yuzde}


@dataclass
class _Poz:
    yon: int
    miktar: Decimal
    giris: Decimal
    zaman: pd.Timestamp
    stop: Decimal
    ilk_stop: Decimal
    hedef: Optional[Decimal]
    giris_komisyon: Decimal
    son_f: pd.Timestamp
    ekstrem: float
    zaman_limit: Optional[int]
    funding: Decimal = Decimal(0)
    tutulan: int = 0
    ilk_miktar: Decimal = Decimal(0)
    brut_toplam: Decimal = Decimal(0)         # realize edilmiş brüt (kısmi parçalar dahil)
    cikis_kom_toplam: Decimal = Decimal(0)
    kismi_sayisi: int = 0
    kismi_net: Decimal = Decimal(0)           # kısmi parçaların brüt - çıkış komisyonu
    kismi_bekleyen: tuple = ()                # ((seviye_fiyati, oran), ...) henüz dolmamış


class CikisYokHatasi(ValueError):
    """Hiçbir çıkış mekanizması yok (yalnızca ilk stop)."""


MESAJ_CIKIS_YOK = "ilk stop dışında çıkış yok"


KOLONLAR = ["yon", "giris_zamani", "giris_fiyati", "cikis_zamani", "cikis_fiyati", "miktar",
            "brut_pnl", "komisyon", "funding", "net_pnl", "r", "cikis_nedeni",
            "kismi_sayisi", "kismi_pnl"]


def _tick(fiyat: Decimal, tick: Decimal) -> Decimal:
    return (fiyat / tick).quantize(Decimal(1), rounding=ROUND_HALF_UP) * tick


def _step_asagi(miktar: Decimal, step: Decimal) -> Decimal:
    return (miktar / step).to_integral_value(rounding=ROUND_DOWN) * step


def backtest(mumlar: pd.DataFrame, strateji: Strateji, ayarlar: MotorAyarlari = None,
             funding: Optional[pd.DataFrame] = None,
             islem_baslangic: Optional[pd.Timestamp] = None) -> SonucBacktest:
    """islem_baslangic: bu zamandan önceki mumlarda yeni giriş yapılmaz (ısınma payı için)."""
    ayarlar = ayarlar or MotorAyarlari()
    ca = strateji.cikis_ayarlari
    # Kısmi kâr ve başabaş tek başına çıkış sayılmaz: kalan pozisyon yine yalnız stopla kapanır (lider kararı).
    if not (strateji.cikis_var_mi() or ca.atr_iz_suren_k or ca.zaman_cikisi_mum
            or ca.sabit_r_hedefi or ca.azalan_roi or ca.geri_cekilme_yuzde or ca.kar_rsi_esikleri):
        raise CikisYokHatasi(MESAJ_CIKIS_YOK)
    L = SERT_LIMITLER
    uyarilar = []
    risk_yuzde = min(ayarlar.risk_yuzde, L.islem_basi_max_risk_yuzde)
    kaldirac = min(ayarlar.kaldirac, L.max_kaldirac)
    if risk_yuzde < ayarlar.risk_yuzde:
        uyarilar.append(f"risk_yuzde {ayarlar.risk_yuzde} -> {risk_yuzde} (sert limit)")
    if kaldirac < ayarlar.kaldirac:
        uyarilar.append(f"kaldirac {ayarlar.kaldirac} -> {kaldirac} (sert limit)")
    risk_oran = D(risk_yuzde) / 100
    kural = ayarlar.kurallar
    tick, step = D(kural.tick_size), D(kural.step_size)
    taker, maker = D(ayarlar.komisyon_taker_yuzde) / 100, D(ayarlar.komisyon_maker_yuzde) / 100
    kayma = D(ayarlar.kayma_bps) / 10000
    stop_kayma = D(ayarlar.stop_kayma_bps) / 10000
    if ayarlar.limit_modu not in ("uygula", "olc"):
        raise ValueError("limit_modu 'uygula' veya 'olc' olmalı")
    olc = ayarlar.limit_modu == "olc"
    limit_olaylari = []
    kill_asildi, gunluk_kaydedildi = False, False

    # --- sinyaller ---
    sig = strateji.sinyaller(mumlar)
    if not sig.index.equals(mumlar.index):
        raise ValueError("sinyaller() mumlarla aynı indeksi dönmeli")
    eksik = [c for c in SINYAL_SUTUNLARI if c not in sig.columns]
    if eksik:
        raise ValueError(f"Sinyal sütunları eksik: {eksik}")
    s_yon = sig["yon"].to_numpy(dtype=int)
    s_stop = sig["stop"].to_numpy(dtype=float)
    s_hedef = sig["hedef"].to_numpy(dtype=float)
    s_cikis = sig["cikis"].to_numpy(dtype=bool)
    # Yönlü çıkış: long için cikis | cikis_long, short için cikis | cikis_short (sütun yoksa yalnız cikis).
    s_cikis_l = s_cikis | (sig["cikis_long"].fillna(False).to_numpy(dtype=bool)
                           if "cikis_long" in sig.columns else False)
    s_cikis_s = s_cikis | (sig["cikis_short"].fillna(False).to_numpy(dtype=bool)
                           if "cikis_short" in sig.columns else False)
    s_zc = (sig["zaman_cikisi_mum"].to_numpy(dtype=float) if "zaman_cikisi_mum" in sig.columns
            else np.full(len(sig), np.nan))
    if np.any((s_yon != 0) & np.isnan(s_stop)):
        raise ValueError("Giriş sinyali olan her satırda stop zorunlu")

    cks_ayar = strateji.cikis_ayarlari
    idx = mumlar.index
    zaman = list(idx)
    acilis = mumlar["acilis"].to_numpy(dtype=float)
    yuksek = mumlar["yuksek"].to_numpy(dtype=float)
    dusuk = mumlar["dusuk"].to_numpy(dtype=float)
    kapanis = mumlar["kapanis"].to_numpy(dtype=float)
    n = len(mumlar)
    atr = (gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], cks_ayar.atr_periyot).to_numpy()
           if (cks_ayar.atr_iz_suren_k or cks_ayar.agresif_iz_atr_k) else np.full(n, np.nan))
    rsi_dizi = (gst.rsi(mumlar["kapanis"], cks_ayar.rsi_periyot).to_numpy()
                if cks_ayar.kar_rsi_esikleri else np.full(n, np.nan))
    son_stop_i = None         # son stop/stop_gap çıkışının mum indeksi (stop_sonrasi_bekleme_mum)
    aralik = pd.Series(idx).diff().median() if n > 1 else pd.Timedelta(0)

    if funding is not None and len(funding):
        f_zaman = funding.index
        f_oran = funding["oran"].to_numpy(dtype=float)
    else:
        f_zaman, f_oran = None, None

    # --- durum ---
    nakit = D(ayarlar.baslangic_sermaye)
    poz: Optional[_Poz] = None
    islemler, reddedilenler = [], []
    ozs = []
    onceki_ozs = nakit
    zirve = nakit
    kill = False
    gun, gun_basi, gunluk_blok = None, nakit, False
    bekleyen_giris = None     # (yon, stop, hedef, zc)
    bekleyen_cikis = None     # neden

    def funding_ode(p: _Poz, bitis, dahil: bool) -> Decimal:
        if f_zaman is None:
            return Decimal(0)
        a = f_zaman.searchsorted(p.son_f, side="right")
        b = f_zaman.searchsorted(bitis, side="right" if dahil else "left")
        toplam = Decimal(0)
        for k in range(a, b):
            j = max(idx.searchsorted(f_zaman[k], side="right") - 1, 0)
            toplam += p.miktar * D(acilis[j]) * D(f_oran[k]) * p.yon
        p.funding += toplam
        if dahil:
            p.son_f = bitis
        return toplam

    def kapat(p: _Poz, fiyat: Decimal, t, neden: str, komisyon_orani: Decimal) -> Decimal:
        """Kalan miktarı kapatır, işlem satırını yazar; nakde eklenecek tutarı döner."""
        brut_son = (fiyat - p.giris) * p.miktar * p.yon
        kom_son = fiyat * p.miktar * komisyon_orani
        brut = p.brut_toplam + brut_son
        cikis_kom = p.cikis_kom_toplam + kom_son
        net = brut - p.giris_komisyon - cikis_kom - p.funding
        risk_tutar = p.ilk_miktar * abs(p.giris - p.ilk_stop)
        islemler.append({
            "yon": p.yon, "giris_zamani": p.zaman, "giris_fiyati": float(p.giris),
            "cikis_zamani": t, "cikis_fiyati": float(fiyat), "miktar": float(p.ilk_miktar),
            "brut_pnl": float(brut), "komisyon": float(p.giris_komisyon + cikis_kom),
            "funding": float(p.funding), "net_pnl": float(net),
            "r": float(net / risk_tutar) if risk_tutar else np.nan, "cikis_nedeni": neden,
            "kismi_sayisi": p.kismi_sayisi, "kismi_pnl": float(p.kismi_net),
        })
        return brut_son - kom_son

    def kismi_kapat(p: _Poz, fiyat: Decimal, qty: Decimal, komisyon_orani: Decimal) -> Decimal:
        brut = (fiyat - p.giris) * qty * p.yon
        kom = fiyat * qty * komisyon_orani
        p.brut_toplam += brut
        p.cikis_kom_toplam += kom
        p.kismi_net += brut - kom
        p.kismi_sayisi += 1
        p.miktar -= qty
        return brut - kom

    def piyasa_fiyati(p: _Poz, ham: float, k: Decimal = kayma) -> Decimal:
        """Çıkış tarafına kayma uygula (long satar -> düşük, short alır -> yüksek)."""
        return _tick(D(ham) * (1 - p.yon * k), tick)

    for i in range(n):
        t = zaman[i]
        o, h, l, c = acilis[i], yuksek[i], dusuk[i], kapanis[i]

        if t.date() != gun:
            gun, gun_basi, gunluk_blok = t.date(), onceki_ozs, False
            gunluk_kaydedildi = False

        # 1) açılışta: funding + bekleyen çıkış
        if poz is not None:
            nakit -= funding_ode(poz, t, dahil=True)
            if bekleyen_cikis:
                nakit += kapat(poz, piyasa_fiyati(poz, o, stop_kayma if bekleyen_cikis in ("kill_switch", "gunluk_limit") else kayma),
                                  t, bekleyen_cikis, taker)
                poz = None
        bekleyen_cikis = None

        # 2) açılışta: bekleyen giriş
        if poz is None and bekleyen_giris is not None:
            yon, stop_ham, hedef_ham, zc = bekleyen_giris
            red = None
            if kill:
                red = "kill_switch"
            elif gunluk_blok:
                red = "gunluk_kayip_limiti"
            elif islem_baslangic is not None and t < islem_baslangic:
                red = "isinma"
            elif (cks_ayar.stop_sonrasi_bekleme_mum and son_stop_i is not None
                  and i - son_stop_i <= cks_ayar.stop_sonrasi_bekleme_mum):
                red = "bekleme"
            if red is None:
                fiyat = _tick(D(o) * (1 + yon * kayma), tick)
                stop = _tick(D(stop_ham), tick)
                risk_birim = abs(fiyat - stop)
                if risk_birim == 0 or (yon == 1 and stop >= fiyat) or (yon == -1 and stop <= fiyat):
                    red = "gecersiz_stop"
            if red is None:
                if not np.isnan(hedef_ham):
                    hedef = _tick(D(hedef_ham), tick)
                elif cks_ayar.sabit_r_hedefi:
                    hedef = _tick(D(cks.r_hedef_fiyati(yon, float(fiyat), float(risk_birim),
                                                        cks_ayar.sabit_r_hedefi)), tick)
                else:
                    hedef = None
                if hedef is not None and (hedef - fiyat) * yon <= 0:
                    red = "gecersiz_hedef"
            if red is None:
                miktar = nakit * risk_oran / risk_birim
                miktar = min(miktar, nakit * D(kaldirac) / fiyat)
                miktar = _step_asagi(miktar, step)
                if miktar < D(kural.min_qty) or miktar <= 0:
                    red = "min_qty"
                elif miktar * fiyat < D(kural.min_notional):
                    red = "min_notional"
            if red is not None:
                reddedilenler.append({"zaman": t, "yon": yon, "neden": red})
            else:
                kom = miktar * fiyat * taker
                nakit -= kom
                zc_n = int(zc) if not np.isnan(zc) else cks_ayar.zaman_cikisi_mum
                kis = tuple((_tick(D(cks.r_hedef_fiyati(yon, float(fiyat), float(risk_birim), r_k)), tick), D(oran))
                            for r_k, oran in sorted(cks_ayar.kismi))
                poz = _Poz(yon, miktar, fiyat, t, stop, stop, hedef, kom, t, float(fiyat), zc_n,
                           ilk_miktar=miktar, kismi_bekleyen=kis)
        bekleyen_giris = None

        # 3) mum içi stop / hedef
        if poz is not None:
            p = poz
            if p.yon == 1:
                stop_gap, stop_vur = o <= p.stop, l <= p.stop
                hedef_gap = p.hedef is not None and o >= p.hedef
                hedef_vur = p.hedef is not None and h >= p.hedef
            else:
                stop_gap, stop_vur = o >= p.stop, h >= p.stop
                hedef_gap = p.hedef is not None and o <= p.hedef
                hedef_vur = p.hedef is not None and l <= p.hedef
            cikis = None
            if stop_gap:
                cikis = (piyasa_fiyati(p, o, stop_kayma), "stop_gap", t, taker)
            elif hedef_gap:
                cikis = (_tick(D(o), tick), "hedef", t, maker if ayarlar.hedef_limit_emri else taker)
            elif stop_vur:
                cikis = (piyasa_fiyati(p, float(p.stop), stop_kayma), "stop", t + aralik, taker)
            elif hedef_vur:
                cikis = (p.hedef, "hedef", t + aralik, maker if ayarlar.hedef_limit_emri else taker)
            if p.kismi_bekleyen and (cikis is None or (cikis[1] == "hedef" and not hedef_gap)):
                kom_k = maker if ayarlar.hedef_limit_emri else taker
                kalan_seviye = []
                for seviye, oran in p.kismi_bekleyen:
                    if p.hedef is not None and (seviye - p.hedef) * p.yon >= 0:
                        continue    # hedefin ötesi: hedef zaten önce dolar
                    gorulen = (o >= seviye) if p.yon == 1 else (o <= seviye)
                    vurdu = (h >= seviye) if p.yon == 1 else (l <= seviye)
                    if not (gorulen or vurdu):
                        kalan_seviye.append((seviye, oran))
                        continue
                    fiyat_k = _tick(D(o), tick) if gorulen else seviye
                    t_k = t if gorulen else t + aralik
                    qty = min(_step_asagi(p.ilk_miktar * oran, step), p.miktar)
                    if qty <= 0:
                        continue    # yuvarlama sıfır: seviye atlanır
                    if t_k != t:
                        nakit -= funding_ode(p, t_k, dahil=False)
                        if f_zaman is not None:     # t_k'dan önceki funding'ler ödendi; t_k'dakiler sonra
                            b_ = f_zaman.searchsorted(t_k, side="left")
                            if b_ > 0 and f_zaman[b_ - 1] > p.son_f:
                                p.son_f = f_zaman[b_ - 1]
                    if p.miktar - qty < D(kural.min_qty):
                        cikis = (fiyat_k, "kismi_tam", t_k, kom_k)
                        break
                    nakit += kismi_kapat(p, fiyat_k, qty, kom_k)
                p.kismi_bekleyen = tuple(kalan_seviye)
            if cikis is not None:
                fiyat_c, neden, t_c, kom_o = cikis
                if t_c != t:
                    nakit -= funding_ode(p, t_c, dahil=False)
                nakit += kapat(p, fiyat_c, t_c, neden, kom_o)
                poz = None
                if neden in ("stop", "stop_gap"):
                    son_stop_i = i

        # 4) veri sonu
        if poz is not None and i == n - 1:
            nakit -= funding_ode(poz, t + aralik, dahil=False)
            nakit += kapat(poz, _tick(D(c), tick), t + aralik, "veri_sonu", taker)
            poz = None

        # 5) mum kapanışı: özsermaye, limitler
        ozs_i = nakit + (D(c) - poz.giris) * poz.miktar * poz.yon if poz is not None else nakit
        ozs.append(ozs_i)
        onceki_ozs = ozs_i
        zirve = max(zirve, ozs_i)
        dusus = (zirve - ozs_i) / zirve * 100
        if olc:
            if dusus >= D(L.kill_switch_dusus_yuzde):
                if not kill_asildi:
                    kill_asildi = True
                    limit_olaylari.append({"tur": "kill_switch", "zaman": t,
                                           "ozsermaye": float(ozs_i), "dusus_yuzde": float(dusus)})
            else:
                kill_asildi = False
        elif not kill and dusus >= D(L.kill_switch_dusus_yuzde):
            kill = True
        gunluk_pct = (ozs_i - gun_basi) / gun_basi * 100
        if gunluk_pct <= -D(L.gunluk_max_kayip_yuzde):
            if olc:
                if not gunluk_kaydedildi:
                    gunluk_kaydedildi = True
                    limit_olaylari.append({"tur": "gunluk_kayip", "zaman": t,
                                           "ozsermaye": float(ozs_i), "dusus_yuzde": float(-gunluk_pct)})
            else:
                gunluk_blok = True

        # 6) mum kapanışı: sonraki açılış için kararlar
        if poz is not None:
            p = poz
            p.tutulan += 1
            p.ekstrem = max(p.ekstrem, h) if p.yon == 1 else min(p.ekstrem, l)
            risk_birim_f = float(abs(p.giris - p.ilk_stop))
            yeni = float(p.stop)
            if cks_ayar.basabas_r_esigi:
                yeni = cks.basabasa_cek(p.yon, yeni, float(p.giris), p.ekstrem,
                                        risk_birim_f, cks_ayar.basabas_r_esigi)
            if cks_ayar.atr_iz_suren_k:
                yeni = cks.iz_suren_stop(p.yon, yeni, p.ekstrem, atr[i], cks_ayar.atr_iz_suren_k)
            if cks_ayar.stop_basamaklari and risk_birim_f > 0:
                yeni = cks.stop_basamagi(p.yon, yeni, float(p.giris), p.ekstrem, risk_birim_f,
                                         cks_ayar.stop_basamaklari)
            if cks_ayar.elder_guvenli_bolge_k:
                ref = dusuk if p.yon == 1 else yuksek
                eld = cks.elder_guvenli_bolge(ref, i, cks_ayar.elder_n1, cks_ayar.elder_n2,
                                              cks_ayar.elder_guvenli_bolge_k, p.yon)
                if not np.isnan(eld):
                    yeni = max(yeni, eld) if p.yon == 1 else min(yeni, eld)
            if cks_ayar.agresif_iz_esigi and p.hedef is not None:
                yol = p.yon * float(p.hedef - p.giris)
                if yol > 0 and p.yon * (p.ekstrem - float(p.giris)) / yol >= cks_ayar.agresif_iz_esigi:
                    yeni = cks.iz_suren_stop(p.yon, yeni, p.ekstrem, atr[i], cks_ayar.agresif_iz_atr_k)
            yeni_d = _tick(D(yeni), tick)
            if (yeni_d - p.stop) * p.yon > 0:
                p.stop = yeni_d
            if kill:
                bekleyen_cikis = "kill_switch"
            elif gunluk_blok and not olc:
                bekleyen_cikis = "gunluk_limit"
            elif (s_cikis_l[i] if p.yon == 1 else s_cikis_s[i]):
                bekleyen_cikis = "sinyal"
            elif cks.zaman_doldu(p.tutulan, p.zaman_limit):
                bekleyen_cikis = "zaman"
            else:
                # kâr/zirve yalnız kapanmış mumlardan (kapanış ve p.ekstrem); çıkış sonraki açılışta
                kar_c = cks.kar_yuzde(p.yon, float(p.giris), c)
                if cks_ayar.azalan_roi and cks.azalan_roi_doldu(p.tutulan, kar_c, cks_ayar.azalan_roi):
                    bekleyen_cikis = "roi"
                elif cks.geri_cekilme_doldu(cks.kar_yuzde(p.yon, float(p.giris), p.ekstrem), kar_c,
                                            cks_ayar.geri_cekilme_yuzde, cks_ayar.geri_cekilme_min_kar_yuzde):
                    bekleyen_cikis = "geri_cekilme"
                elif cks.kar_rsi_doldu(p.yon, kar_c, rsi_dizi[i], cks_ayar.kar_rsi_esikleri):
                    bekleyen_cikis = "kar_rsi"
        if s_yon[i] != 0:
            bekleyen_giris = (int(s_yon[i]), s_stop[i], s_hedef[i], s_zc[i])

    ozsermaye = pd.Series([float(x) for x in ozs], index=idx, name="ozsermaye")
    df = pd.DataFrame(islemler, columns=KOLONLAR)
    return SonucBacktest(df, ozsermaye, reddedilenler, uyarilar, float(ayarlar.baslangic_sermaye), limit_olaylari)
