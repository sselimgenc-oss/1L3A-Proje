"""B3 formasyon aileleri için ortak yardımcılar ve çekirdekler (hepsi nedensel).

Tasarım: her çekirdek yalnız LONG biçiminde yazılır ve (yon in {0,1}, stop, hedef) dizileri döner.
Short taraf, fiyatların işaret çevrilmiş aynası (`ayna`) üzerinde AYNI çekirdek çalıştırılarak elde edilir
(`iki_yon`). Böylece long/short simetrik olur. Aynada fiyatlar negatiftir; bu yüzden çekirdeklerde yüzde değil
ATR ve oran (aralığa göre) kullanılır.

Çekirdekler: bas_omuz (ters baş-omuz), bayrak, elmas, gann, abcd, elliott, pin, mum (çoklu mum desenleri), renko.
Pivotlar `pivotlar.pivot_tablosu` ile (onay mumundan önce kullanılamaz); üst TF `htf.ust_zaman` ile.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.htf import ust_zaman
from motor.strateji.pivotlar import pivot_tablosu, sinyal_cercevesi
from motor.strateji.temel import Strateji

# ------------------------------------------------------------------ ortak yardımcılar


def ayna(m: pd.DataFrame) -> pd.DataFrame:
    """Fiyat aynası: tüm fiyatlar negatiflenir, yüksek/düşük yer değiştirir (hacim aynı)."""
    a = m.copy()
    a["acilis"] = -m["acilis"]
    a["yuksek"] = -m["dusuk"]
    a["dusuk"] = -m["yuksek"]
    a["kapanis"] = -m["kapanis"]
    return a


def iki_yon(m, cekirdek, long_acik=True, short_acik=True):
    """Long çekirdeği düz veriyle (long), aynada (short) çalıştırır. -> yon, stop, hedef (numpy)."""
    n = len(m)
    yon = np.zeros(n, dtype="int64")
    stop = np.full(n, np.nan)
    hedef = np.full(n, np.nan)
    if long_acik:
        y, s, h = cekirdek(m)
        k = y == 1
        yon[k], stop[k], hedef[k] = 1, s[k], h[k]
    if short_acik:
        y, s, h = cekirdek(ayna(m))
        k = (y == 1) & (yon == 0)
        yon[k], stop[k], hedef[k] = -1, -s[k], -h[k]
    return yon, stop, hedef


def temizle(m, yon, stop, hedef):
    """Yanlış tarafta stop/hedef veya NaN stop olan sinyalleri düşürür."""
    kap = m["kapanis"].to_numpy(float)
    yon, stop, hedef = yon.copy(), stop.copy(), hedef.copy()
    with np.errstate(invalid="ignore"):
        kotu = (yon != 0) & (np.isnan(stop) | ((yon == 1) & ~(stop < kap)) | ((yon == -1) & ~(stop > kap)))
        kotu |= (yon == 1) & ~np.isnan(hedef) & ~(hedef > kap)
        kotu |= (yon == -1) & ~np.isnan(hedef) & ~(hedef < kap)
    yon[kotu] = 0
    stop[yon == 0] = np.nan
    hedef[yon == 0] = np.nan
    return yon, stop, hedef


def soguma_uygula(ok: np.ndarray, bekle: int) -> np.ndarray:
    """Aday indekslerinde, bir sinyalden sonra `bekle` mum içindeki adayları eler."""
    cikti = np.zeros(len(ok), dtype=bool)
    son = -10 ** 9
    for t in np.flatnonzero(ok):
        if t - son > bekle:
            cikti[t] = True
            son = t
    return cikti


def ust_tf_trend(m: pd.DataFrame, ust_tf: str, ema_n: int) -> np.ndarray:
    """Üst TF filtresi (long yönlü): üst TF kapanışı > üst TF EMA(ema_n). Lookahead'siz (htf.ust_zaman).
    ust_tf boşsa hep True. Aynada aynı fonksiyon short koşulunu verir."""
    if not ust_tf:
        return np.ones(len(m), dtype=bool)

    def f(u):
        e = g.ema(u["kapanis"], int(ema_n))
        return pd.DataFrame({"y": (u["kapanis"] > e).astype(float).where(e.notna())})
    r = ust_zaman(m, ust_tf, f)["y"].to_numpy()
    return np.nan_to_num(r, nan=0.0) == 1.0


def stoch_rsi(kapanis: pd.Series, rsi_periyot=14, stoch_periyot=14, k_periyot=3) -> pd.Series:
    """Stokastik RSI %K (0-100): (RSI - min)/(max - min) üzerinden k_periyot SMA."""
    r = g.rsi(kapanis, rsi_periyot)
    lo = r.rolling(stoch_periyot, min_periods=stoch_periyot).min()
    hi = r.rolling(stoch_periyot, min_periods=stoch_periyot).max()
    ham = 100.0 * (r - lo) / (hi - lo).replace(0.0, np.nan)
    return g.sma(ham, k_periyot)


class PivotAkisi:
    """pivot_tablosu çıktısından, t. mumda ONAYLANAN pivotları (tip, idx, fiyat) sırayla biriktirir.
    tip: +1 tepe, -1 dip."""

    def __init__(self, pv: pd.DataFrame):
        self.yd = pv["yeni_dip"].to_numpy()
        self.yt = pv["yeni_tepe"].to_numpy()
        self.sdi, self.sdf = pv["son_dip_idx"].to_numpy(), pv["son_dip_fiyat"].to_numpy()
        self.sti, self.stf = pv["son_tepe_idx"].to_numpy(), pv["son_tepe_fiyat"].to_numpy()
        self.liste = []

    def isle(self, t: int):
        yeni = []
        if self.yd[t]:
            yeni.append((-1, int(self.sdi[t]), float(self.sdf[t])))
        if self.yt[t]:
            yeni.append((1, int(self.sti[t]), float(self.stf[t])))
        yeni.sort(key=lambda x: x[1])
        self.liste.extend(yeni)
        return yeni


def _diziler(m):
    return (m[c].to_numpy(float) for c in ("acilis", "yuksek", "dusuk", "kapanis"))


def _atr(m, p):
    return g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_periyot"])).to_numpy()


# ------------------------------------------------------------------ taban strateji


class FormasyonTaban(Strateji):
    """Ortak iskelet: sinyaller() = çekirdek(ler) -> temizle -> çerçeve. Alt sınıflar `cekirdek` yazar."""

    def cekirdek(self, m):  # (yon, stop, hedef), long biçimi
        raise NotImplementedError

    def _hesapla(self, m, long_acik, short_acik):
        return iki_yon(m, self.cekirdek, long_acik, short_acik)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        yon, stop, hedef = self._hesapla(mumlar, bool(p.get("long", True)), bool(p.get("short", True)))
        yon, stop, hedef = temizle(mumlar, yon, stop, hedef)
        return sinyal_cercevesi(mumlar.index, yon, stop, hedef)


def rr_ok(kap, stop, hedef, min_rr):
    """Ödül/risk >= min_rr (long biçimi)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        return (hedef - kap) >= min_rr * (kap - stop)


# ------------------------------------------------------------------ 1) ters baş-omuz (long biçimi)


def bas_omuz_cekirdek(m, p):
    """Ters baş-omuz. Ardışık 3 onaylı dip: omuz(D1) - baş(D2, en düşük) - omuz(D3). Boyun çizgisi: iki dip arası
    en yüksek ikişer tepeden (T1: D1-D2 arası, T2: D2-D3 arası) geçen doğru (eğimli olabilir).
    Tetik: kapanış boyun çizgisinin üstüne geçer (formasyon yalnız D3 pivotu onaylandıktan sonra kurulur)."""
    n = len(m)
    ac, yu, du, kap = _diziler(m)
    atr = _atr(m, p)
    pv = pivot_tablosu(m, p["pivot_yontemi"], int(p["pivot_k"]), int(p["atr_periyot"]), p["zigzag_esik_k"])
    ak = PivotAkisi(pv)
    dipler = []
    yon = np.zeros(n, dtype="int64")
    stop = np.full(n, np.nan)
    hedef = np.full(n, np.nan)
    kur = None
    for t in range(n):
        for tip, idx, f in ak.isle(t):
            if tip == -1:
                dipler.append((idx, f))
                if len(dipler) >= 3 and not np.isnan(atr[t]):
                    (i1, d1), (i2, d2), (i3, d3) = dipler[-3:]
                    a = atr[t]
                    if (d2 < min(d1, d3) - p["min_bas_atr"] * a
                            and 1.0 / p["zaman_oran"] <= (i2 - i1) / max(i3 - i2, 1) <= p["zaman_oran"]):
                        ia = i1 + int(np.argmax(yu[i1:i2 + 1]))
                        ib = i2 + int(np.argmax(yu[i2:i3 + 1]))
                        if ib > ia:
                            pa, pb = yu[ia], yu[ib]
                            egim = (pb - pa) / (ib - ia)
                            H = pa + egim * (i2 - ia) - d2
                            if (H >= p["min_yuk_atr"] * a and abs(d1 - d3) <= p["sim_tol"] * H
                                    and abs(pb - pa) <= p["egim_tol"] * H
                                    and (not p["sag_omuz_filtre"] or (d3 - d2) >= (d1 - d2))):
                                kur = (pa, egim, ia, H, d2, d3, t + int(p["gecerlilik"]))
        if kur is None or np.isnan(atr[t]):
            continue
        pa, egim, ia, H, bas, omuz, bitis = kur
        boyun = pa + egim * (t - ia)
        if kap[t] < bas or t > bitis:
            kur = None
        elif kap[t] > boyun:
            kur = None
            if kap[t] - boyun <= p["maks_asim_atr"] * atr[t]:
                s = (omuz if p["stop_modu"] == "omuz" else bas) - p["tampon_atr"] * atr[t]
                h = boyun + p["hedef_olcu"] * H
                if h > kap[t] and s < kap[t] and (h - kap[t]) >= p["min_rr"] * (kap[t] - s):
                    yon[t], stop[t], hedef[t] = 1, s, h
    return yon, stop, hedef


# ------------------------------------------------------------------ 2) bayrak / flama (long biçimi)


def bayrak_cekirdek(m, p):
    """Yükseliş direği + dar/sığ geri çekilme (bayrak) + üst sınır kırılımı. Her bayrak uzunluğu F için
    (bayrak_min..bayrak_maks): bayrak = son F mum (t-F..t-1), direk = ondan önceki `direk_n` mum.
    Direk: aralık >= direk_min_atr*ATR ve direk sonu kapanışı tepeye yakın (<= direk_yakin*aralık).
    Bayrak: üst sınırı direk tepesini geçmez, dibi direk tepesinin maks_derinlik*aralık'tan fazla altında değil,
    bayrağın son kapanışı ilk kapanışından belirgin yukarıda değil. Tetik: kapanış > bayrak tepesi + tampon*ATR.
    Aynı F ilk sağlayan (en kısa bayrak) kullanılır; sinyaller `soguma` mum aralıkla."""
    n = len(m)
    ac, yu, du, kap = _diziler(m)
    Y, D, K = m["yuksek"], m["dusuk"], m["kapanis"]
    atr_s = g.atr(Y, D, K, int(p["atr_periyot"]))
    P = int(p["direk_n"])
    dolu = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    hedef = np.full(n, np.nan)
    atr = atr_s.to_numpy()
    for F in range(int(p["bayrak_min"]), int(p["bayrak_maks"]) + 1):
        fh = Y.rolling(F, min_periods=F).max().shift(1).to_numpy()
        fl = D.rolling(F, min_periods=F).min().shift(1).to_numpy()
        pt = Y.rolling(P, min_periods=P).max().shift(F + 1).to_numpy()
        pd_ = D.rolling(P, min_periods=P).min().shift(F + 1).to_numpy()
        pson = K.shift(F + 1).to_numpy()
        a_pol = atr_s.shift(F + 1).to_numpy()
        ilk_k = K.shift(F).to_numpy()
        son_k = K.shift(1).to_numpy()
        ar = pt - pd_
        with np.errstate(invalid="ignore"):
            ok = ((kap > fh + p["tampon_atr"] * atr)
                  & (ar >= p["direk_min_atr"] * a_pol)
                  & ((pt - pson) <= p["direk_yakin"] * ar)
                  & (fh <= pt + 0.1 * ar)
                  & ((pt - fl) <= p["maks_derinlik"] * ar)
                  & (son_k <= ilk_k + 0.1 * ar))
            if p["hacim_k"] > 0 and "hacim" in m.columns:
                vh = m["hacim"].rolling(F, min_periods=F).mean().shift(1).to_numpy()
                ok &= m["hacim"].to_numpy(float) > p["hacim_k"] * vh
        yeni = ok & ~dolu
        stop = np.where(yeni, fl - p["stop_tampon_atr"] * atr, stop)
        hedef = np.where(yeni, kap + p["hedef_olcu"] * ar, hedef)
        dolu |= yeni
    dolu &= ust_tf_trend(m, p["ust_tf"], p["ust_ema"])
    dolu = soguma_uygula(dolu, int(p["soguma"]))
    dolu &= rr_ok(kap, stop, hedef, p["min_rr"])
    return dolu.astype("int64"), np.where(dolu, stop, np.nan), np.where(dolu, hedef, np.nan)


# ------------------------------------------------------------------ 3) elmas (long biçimi = yukarı kırılım)


def elmas_cekirdek(m, p):
    """Elmas yaklaşığı: pencere W dört çeyreğe (Q=W//4) bölünür (t'den önceki W mum). Çeyrek aralığı = max(yüksek)
    - min(düşük). Sol yarı GENİŞLEYEN (q2 >= genis_oran*q1), sağ yarı DARALAN (q3 >= genis_oran*q4 ve q4 <=
    daralma_oran*max(q2,q3)). Formasyon yüksekliği H = tüm pencere aralığı >= min_yuk_atr*ATR.
    Tetik: kapanış son çeyreğin (q4) tepesinin üstüne çıkar (yukarı kırılım; aşağı kırılım aynada)."""
    n = len(m)
    ac, yu, du, kap = _diziler(m)
    Y, D, K = m["yuksek"], m["dusuk"], m["kapanis"]
    atr = _atr(m, p)
    W = int(p["pencere"])
    Q = max(W // 4, 2)
    hi = Y.rolling(Q, min_periods=Q).max()
    lo = D.rolling(Q, min_periods=Q).min()
    rng = hi - lo
    q4 = rng.shift(1).to_numpy()
    q3 = rng.shift(Q + 1).to_numpy()
    q2 = rng.shift(2 * Q + 1).to_numpy()
    q1 = rng.shift(3 * Q + 1).to_numpy()
    hi4 = hi.shift(1).to_numpy()
    lo4 = lo.shift(1).to_numpy()
    top = Y.rolling(4 * Q, min_periods=4 * Q).max().shift(1).to_numpy()
    alt = D.rolling(4 * Q, min_periods=4 * Q).min().shift(1).to_numpy()
    H = top - alt
    with np.errstate(invalid="ignore"):
        ok = ((q2 >= p["genis_oran"] * q1) & (q3 >= p["genis_oran"] * q4)
              & (q4 <= p["daralma_oran"] * np.maximum(q2, q3))
              & (H >= p["min_yuk_atr"] * atr)
              & (kap > hi4 + p["tampon_atr"] * atr))
    ok = soguma_uygula(ok, Q)
    taban = lo4 if p["stop_modu"] == "son" else alt
    stop = taban - p["tampon_atr"] * atr
    hedef = kap + p["hedef_olcu"] * H
    ok &= rr_ok(kap, stop, hedef, p["min_rr"])
    return ok.astype("int64"), np.where(ok, stop, np.nan), np.where(ok, hedef, np.nan)


# ------------------------------------------------------------------ 4) Gann fan (long biçimi = destek)

GANN_ORANLARI = [0.25, 1 / 3, 0.5, 1.0, 2.0, 3.0, 4.0, 8.0]


def gann_cekirdek(m, p):
    """Gann fan: fan başlangıcı son ONAYLI dip pivot (zigzag). 1x1 çizgisi bar başına u = olcek_atr*ATR(onay anı)
    fiyat birimi yükselir; diğer çizgiler u*oran (1x2=0.5, 2x1=2 ...). Yükseliş bacağı olmalı (dipten sonra onaylı
    tepe). Giriş: kapanış `cizgi_orani` çizgisinin üstünde, o mumun düşüğü çizgiye <= tol_atr*ATR yaklaşmış, boğa mumu
    ve önceki kapanış çizginin üstünde (çizgiden dönüş). Stop: çizgi/mum düşüğü - stop_tampon*ATR. Hedef: bir
    üstteki Gann çizgisinin `hedef_ufuk` mum sonraki değeri (üst çizgi yoksa 2R), en çok maks_hedef_r*R."""
    n = len(m)
    ac, yu, du, kap = _diziler(m)
    atr = _atr(m, p)
    pv = pivot_tablosu(m, "zigzag", 3, int(p["atr_periyot"]), p["zigzag_esik_k"])
    sdi, sdf = pv["son_dip_idx"].to_numpy(), pv["son_dip_fiyat"].to_numpy()
    sdo = pv["son_dip_onay_idx"].to_numpy()
    sti = pv["son_tepe_idx"].to_numpy()
    t_ = np.arange(n, dtype=float)
    onay_i = np.nan_to_num(sdo, nan=0).astype(int)
    u = p["olcek_atr"] * atr[onay_i]
    u = np.where(np.isnan(sdo), np.nan, u)
    r = p["cizgi_orani"]
    yas = t_ - sdi
    cizgi = sdf + u * r * yas
    cizgi_onc = np.r_[np.nan, cizgi[:-1]]
    kap_onc = np.r_[np.nan, kap[:-1]]
    with np.errstate(invalid="ignore"):
        ok = ((sti > sdi) & (yas >= p["min_yas"]) & (yas <= p["maks_yas"])
              & (kap > cizgi) & (du <= cizgi + p["tol_atr"] * atr) & (kap > ac) & (kap_onc > cizgi_onc)
              & ~np.isnan(atr))
    ok = soguma_uygula(ok, int(p["soguma"]))
    stop = np.minimum(cizgi, du) - p["stop_tampon_atr"] * atr
    ustler = [x for x in GANN_ORANLARI if x > r + 1e-9]
    azami = kap + p["maks_hedef_r"] * (kap - stop)
    if ustler:
        hedef = np.minimum(sdf + u * ustler[0] * (t_ + p["hedef_ufuk"] - sdi), azami)
    else:
        hedef = np.minimum(kap + 2.0 * (kap - stop), azami)
    ok &= rr_ok(kap, stop, hedef, p["min_rr"])
    return ok.astype("int64"), np.where(ok, stop, np.nan), np.where(ok, hedef, np.nan)


# ------------------------------------------------------------------ 5) harmonik ABCD (long biçimi = boğa)


def abcd_cekirdek(m, p):
    """Boğa ABCD: ardışık onaylı pivotlar A(tepe) B(dip) C(tepe, C<A). AB bacağı >= min_ab_atr*ATR, BC geri
    çekilmesi (C-B)/(A-B) in [bc_min, bc_maks]. D = C - ab_oran*(A-B) (CD = ab_oran x AB), D < B olmalı.
    C onaylandıktan sonra: low <= D + tol*ATR ve kapanış D'nin üstünde boğa mumu -> giriş. Geçersiz: kapanış > A,
    kapanış < D - asim_atr*ATR, ya da C'den beri maks_bekle mum geçti. Stop: min(düşük, D) - tampon*ATR.
    Hedef (kartta yok; Carney/Pesavento varsayımı): D + hedef_oran*(A - D)."""
    n = len(m)
    ac, yu, du, kap = _diziler(m)
    atr = _atr(m, p)
    pv = pivot_tablosu(m, p["pivot_yontemi"], int(p["pivot_k"]), int(p["atr_periyot"]), p["zigzag_esik_k"])
    ak = PivotAkisi(pv)
    yon = np.zeros(n, dtype="int64")
    stop = np.full(n, np.nan)
    hedef = np.full(n, np.nan)
    kur = None
    for t in range(n):
        for tip, idx, f in ak.isle(t):
            L = ak.liste
            if tip == 1 and len(L) >= 3 and not np.isnan(atr[t]):
                (t1, ia, A), (t2, ib, B), (t3, ic, C) = L[-3:]
                if t1 == 1 and t2 == -1 and C < A and A - B >= p["min_ab_atr"] * atr[t]:
                    r = (C - B) / (A - B)
                    D = C - p["ab_oran"] * (A - B)
                    if p["bc_min"] <= r <= p["bc_maks"] and D < B:
                        kur = (A, D, ic, ic + int(p["maks_bekle"]))
        if kur is None or np.isnan(atr[t]):
            continue
        A, D, ic, bitis = kur
        if kap[t] > A or t > bitis or kap[t] < D - p["asim_atr"] * atr[t]:
            kur = None
        elif du[t] <= D + p["tol_atr"] * atr[t] and kap[t] > ac[t] and kap[t] > D:
            kur = None
            s = min(du[t], D) - p["tampon_atr"] * atr[t]
            h = D + p["hedef_oran"] * (A - D)
            if s < kap[t] < h and (h - kap[t]) >= p["min_rr"] * (kap[t] - s):
                yon[t], stop[t], hedef[t] = 1, s, h
    return yon, stop, hedef


# ------------------------------------------------------------------ 6) Elliott 2. / 4. dalga (long biçimi)


def elliott_cekirdek(m, p):
    """Zigzag pivotlarıyla yaklaşık Elliott itki: P0(dip) P1(tepe) P2(dip) [P3(tepe) P4(dip)].
    Dalga 2 girişi (dalga in {0,2}): P2 > P0 ve geri çekilme (P1-P2)/(P1-P0) in [r2_min, r2_maks] -> P2 onaylandığı
    mumda giriş. Dalga 4 girişi (dalga in {0,4}): ek olarak P3 > P1, dalga3 (P3-P2) >= w3_oran*dalga1 (P1-P0),
    P4 > P1 (dalga 4 dibi dalga 1 tepesini aşmaz), geri çekilme (P3-P4)/(P3-P2) in [r4_min, r4_maks].
    Stop: swing dibi (P2 veya P4) - tampon*ATR. Hedef: giriş + hedef_r*risk (kart: ideal 1:2).
    Not: 5. dalga tükenme çıkışı (Boxer) giriş kuralı olmadığından kodlanmadı."""
    n = len(m)
    ac, yu, du, kap = _diziler(m)
    atr = _atr(m, p)
    pv = pivot_tablosu(m, "zigzag", 3, int(p["atr_periyot"]), p["zigzag_esik_k"])
    ak = PivotAkisi(pv)
    yon = np.zeros(n, dtype="int64")
    stop = np.full(n, np.nan)
    hedef = np.full(n, np.nan)
    d = int(p["dalga"])
    for t in range(n):
        yeni = ak.isle(t)
        if not yeni or np.isnan(atr[t]):
            continue
        L = ak.liste
        if L[-1][0] != -1:
            continue
        sec = None
        if d in (0, 4) and len(L) >= 5 and [x[0] for x in L[-5:]] == [-1, 1, -1, 1, -1]:
            (_, _, P0), (_, _, P1), (_, _, P2), (_, _, P3), (_, _, P4) = L[-5:]
            w1, w3 = P1 - P0, P3 - P2
            if (P2 > P0 and P3 > P1 and w1 > 0 and w3 >= p["w3_oran"] * w1 and P4 > P1
                    and p["r4_min"] <= (P3 - P4) / w3 <= p["r4_maks"]):
                sec = P4
        if sec is None and d in (0, 2) and len(L) >= 3 and [x[0] for x in L[-3:]] == [-1, 1, -1]:
            (_, _, P0), (_, _, P1), (_, _, P2) = L[-3:]
            w1 = P1 - P0
            if w1 >= p["min_dalga_atr"] * atr[t] and P2 > P0 and p["r2_min"] <= (P1 - P2) / w1 <= p["r2_maks"]:
                sec = P2
        if sec is None:
            continue
        s = sec - p["tampon_atr"] * atr[t]
        if s < kap[t]:
            yon[t], stop[t] = 1, s
            hedef[t] = kap[t] + p["hedef_r"] * (kap[t] - s)
    return yon, stop, hedef


# ------------------------------------------------------------------ 7) pin bar (long biçimi = boğa pin)


def pin_cekirdek(m, p):
    """Boğa pin bar: alt fitil >= fitil_oran*max(gövde, 0.1*aralık), alt fitil >= 0.5*aralık, kapanış mumun üst
    %(1-kapanis_alt) diliminde, aralık [min_aralik_atr, maks_aralik_atr]*ATR. Seviye (seviye_modu): "aralik" = pin düşüğü
    önceki `aralik_n` mumun en düşüğüne <= tol_atr*ATR yakın/altında; "gun" = önceki UTC günün düşüğüne yakın.
    Opsiyonel trend_ema (kapanış > EMA) ve üst TF filtresi. Giriş: teyit_n=0 pin kapanışında; teyit_n=k>0: pin'den
    sonra k mum içinde kapanışın pin tepesini aşması (pin düşüğü kırılmadan). Stop: pin düşüğü - tampon*ATR (risk
    maks_risk_atr*ATR'yi aşarsa işlem yok). Hedef: hedef_r>0 ise R katı; 0 ise aralığın karşı ucu (aralik_n tepesi)."""
    n = len(m)
    ac, yu, du, kap = _diziler(m)
    Y, D, K = m["yuksek"], m["dusuk"], m["kapanis"]
    atr_s = g.atr(Y, D, K, int(p["atr_periyot"]))
    atr = atr_s.to_numpy()
    rng = yu - du
    govde = np.abs(kap - ac)
    alt = np.minimum(ac, kap) - du
    with np.errstate(invalid="ignore", divide="ignore"):
        pin = ((alt >= p["fitil_oran"] * np.maximum(govde, 0.1 * rng)) & (alt >= 0.5 * rng)
               & ((kap - du) >= (1.0 - p["kapanis_alt"]) * rng)
               & (rng >= p["min_aralik_atr"] * atr) & (rng <= p["maks_aralik_atr"] * atr))
        N = int(p["aralik_n"])
        if p["seviye_modu"] == "gun":
            from motor.strateji.daytrade._ortak import onceki_seans_hlc, seans_kimligi
            sev = onceki_seans_hlc(m, seans_kimligi(m.index))["l"].to_numpy()
        else:
            sev = D.rolling(N, min_periods=N).min().shift(1).to_numpy()
        pin &= du <= sev + p["tol_atr"] * atr
        if p["trend_ema"]:
            pin &= kap > g.ema(K, int(p["trend_ema"])).to_numpy()
    pin &= ust_tf_trend(m, p["ust_tf"], p["ust_ema"])
    tampon = p["tampon_atr"] * atr
    karsi = Y.rolling(N, min_periods=N).max().shift(1).to_numpy()

    yon = np.zeros(n, dtype="int64")
    stop = np.full(n, np.nan)
    k = int(p["teyit_n"])
    if k == 0:
        yon[pin] = 1
        stop = np.where(pin, du - tampon, np.nan)
    else:
        for j in range(1, k + 1):
            pj = np.r_[np.zeros(j, dtype=bool), pin[:-j]]
            dj = np.r_[np.full(j, np.nan), du[:-j]]
            yj = np.r_[np.full(j, np.nan), yu[:-j]]
            tj = np.r_[np.full(j, np.nan), tampon[:-j]]
            # pin'den bu yana düşük pin düşüğünün altına inmedi
            alt_min = D.rolling(j, min_periods=j).min().to_numpy()
            with np.errstate(invalid="ignore"):
                c = pj & (kap > yj) & (alt_min >= dj) & (yon == 0)
            yon[c] = 1
            stop = np.where(c, dj - tj, stop)
    with np.errstate(invalid="ignore"):
        risk = kap - stop
        yon[(yon == 1) & ~((risk > 0) & (risk <= p["maks_risk_atr"] * atr))] = 0
    if p["hedef_r"] > 0:
        hedef = kap + p["hedef_r"] * (kap - stop)
    else:
        hedef = karsi
    ok = (yon == 1) & rr_ok(kap, stop, hedef, p["min_rr"])
    if k > 0:
        ok = soguma_uygula(ok, k)      # aynı pin için ardışık teyit mumlarında tekrar giriş yok
    return ok.astype("int64"), np.where(ok, stop, np.nan), np.where(ok, hedef, np.nan)


# ------------------------------------------------------------------ 8) Japon mum çoklu desenleri (long biçimi)


def _mum_ortak(m, p):
    ac, yu, du, kap = _diziler(m)
    atr = _atr(m, p)
    rng = yu - du
    govde = np.abs(kap - ac)
    return ac, yu, du, kap, atr, rng, govde


def _kay(x, j):
    """x[t-j] (nedensel kaydırma)."""
    return np.r_[np.full(j, np.nan), x[:-j]] if j > 0 else x


def _dusus_oncesi(kap, atr, s, p):
    """Desen başlangıcından (s mum öncesi, s>=1) önceki `trend_n` mumda net düşüş >= trend_min_atr*ATR."""
    n_ = int(p["trend_n"])
    with np.errstate(invalid="ignore"):
        return (_kay(kap, s + n_) - _kay(kap, s)) >= p["trend_min_atr"] * atr


def mum_uc_cizgi(m, p):
    """Boğa üç çizgi vuruşu: 3 kırmızı mum (her biri öncekinden düşük dip ve düşük kapanış, kapanış kendi dibine
    yakın), 4. boğa mumu 3.'nün kapanışında/altında açılır ve 1. kırmızının yükseğinin üstünde kapatır."""
    ac, yu, du, kap, atr, rng, govde = _mum_ortak(m, p)
    ok = np.ones(len(m), dtype=bool)
    with np.errstate(invalid="ignore"):
        for j in (1, 2, 3):
            ok &= _kay(kap, j) < _kay(ac, j)
            ok &= (_kay(kap, j) - _kay(du, j)) <= p["yakin"] * _kay(rng, j)
            if j < 3:
                ok &= _kay(du, j) < _kay(du, j + 1)
                ok &= _kay(kap, j) < _kay(kap, j + 1)
        ok &= (kap > ac) & (ac <= _kay(kap, 1) + 1e-12) & (kap > _kay(yu, 3))
    ok &= _dusus_oncesi(kap, atr, 4, p)
    return ok, np.minimum(du, np.fmin(_kay(du, 1), np.fmin(_kay(du, 2), _kay(du, 3))))


def mum_terk_bebek(m, p):
    """Boğa terk edilmiş bebek: kırmızı mum, aşağı boşluklu doji, yukarı boşluklu boğa mumu. "Boşluk" 24/7 veride
    nadir olduğundan gevşek tanım: iki mumun aralıkları en fazla bosluk_tol_atr*ATR örtüşür."""
    ac, yu, du, kap, atr, rng, govde = _mum_ortak(m, p)
    tol = p["bosluk_tol_atr"] * atr
    with np.errstate(invalid="ignore"):
        doji = _kay(govde, 1) <= p["doji_oran"] * _kay(rng, 1)
        ok = ((_kay(kap, 2) < _kay(ac, 2)) & doji & (_kay(yu, 1) <= _kay(du, 2) + tol)
              & (kap > ac) & (du >= _kay(yu, 1) - tol))
    ok &= _dusus_oncesi(kap, atr, 3, p)
    return ok, np.fmin(du, np.fmin(_kay(du, 1), _kay(du, 2)))


def mum_harami_capraz(m, p):
    """Boğa harami çaprazı: güçlü kırmızı mum (gövde >= guclu_atr*ATR), gövdesi içinde doji, doji'de hacim düşüşü
    (hacim_filtre=1 ise), ardından doji'yi yutan boğa mumu (kapanış > kırmızı mumun açılışı)."""
    ac, yu, du, kap, atr, rng, govde = _mum_ortak(m, p)
    with np.errstate(invalid="ignore"):
        ok = ((_kay(kap, 2) < _kay(ac, 2)) & (_kay(govde, 2) >= p["guclu_atr"] * _kay(atr, 2))
              & (_kay(govde, 1) <= p["doji_oran"] * _kay(rng, 1))
              & (np.maximum(_kay(ac, 1), _kay(kap, 1)) <= _kay(ac, 2))
              & (np.minimum(_kay(ac, 1), _kay(kap, 1)) >= _kay(kap, 2))
              & (kap > ac) & (kap > _kay(ac, 2)))
        if p["hacim_filtre"] and "hacim" in m.columns:
            h = m["hacim"].to_numpy(float)
            ok &= _kay(h, 1) < _kay(h, 2)
    ok &= _dusus_oncesi(kap, atr, 3, p)
    return ok, np.fmin(du, np.fmin(_kay(du, 1), _kay(du, 2)))


def mum_uc_beyaz_asker(m, p):
    """Üç beyaz askerin düşüş sonrası hali; AYNADA "üç kara karga" (kart: yükseliş tepesinde 3 kırmızı mum, her biri
    daha düşük dip, kapanış kendi dibine yakın). Yalnız short için çağrılır."""
    ac, yu, du, kap, atr, rng, govde = _mum_ortak(m, p)
    ok = np.ones(len(m), dtype=bool)
    with np.errstate(invalid="ignore"):
        for j in (0, 1, 2):
            ok &= _kay(kap, j) > _kay(ac, j)
            ok &= (_kay(yu, j) - _kay(kap, j)) <= p["yakin"] * _kay(rng, j)
            if j < 2:
                ok &= _kay(kap, j) > _kay(kap, j + 1)
                ok &= _kay(yu, j) > _kay(yu, j + 1)
    ok &= _dusus_oncesi(kap, atr, 3, p)
    return ok, np.fmin(du, np.fmin(_kay(du, 1), _kay(du, 2)))


def mum_iki_bosluk(m, p):
    """Düşüş sonrası iki yukarı boşluklu boğa mumu; AYNADA "iki boşluk" (kart: zirveden sonra aralarında aşağı boşluk
    olan iki kırmızı mum). Boşluk gevşek tanım (bosluk_tol_atr). Yalnız short için çağrılır."""
    ac, yu, du, kap, atr, rng, govde = _mum_ortak(m, p)
    tol = p["bosluk_tol_atr"] * atr
    with np.errstate(invalid="ignore"):
        ok = ((kap > ac) & (_kay(kap, 1) > _kay(ac, 1))
              & (du >= _kay(yu, 1) - tol) & (_kay(du, 1) >= _kay(yu, 2) - tol))
    ok &= _dusus_oncesi(kap, atr, 3, p)
    return ok, np.fmin(du, np.fmin(_kay(du, 1), _kay(du, 2)))


MUM_DESENLERI = {  # ad -> (fonksiyon, long_acik, short_acik)
    "uc_cizgi": (mum_uc_cizgi, True, True),
    "terk_bebek": (mum_terk_bebek, True, True),
    "harami_capraz": (mum_harami_capraz, True, True),
    "uc_kara_karga": (mum_uc_beyaz_asker, False, True),
    "iki_bosluk": (mum_iki_bosluk, False, True),
}


def mum_cekirdek_tek(fonk):
    def cek(m, p):
        n = len(m)
        ac, yu, du, kap = _diziler(m)
        atr = _atr(m, p)
        ok, alt = fonk(m, p)
        ok = ok & ~np.isnan(atr) & ~np.isnan(alt)
        stop = np.minimum(alt - p["tampon_atr"] * atr, kap - p["min_risk_atr"] * atr)
        hedef = kap + p["hedef_r"] * (kap - stop)
        return ok.astype("int64"), np.where(ok, stop, np.nan), np.where(ok, hedef, np.nan)
    return cek


# ------------------------------------------------------------------ 9) Renko destek/direnç (long biçimi)


def renko_serisi(kap: np.ndarray, atr: np.ndarray, k: float):
    """Nedensel Renko: tuğla boyu = k*ATR(t) (tuğla oluştuğu andaki ATR). Standart kural: devam için 1 tuğla,
    tersine dönüş için 2 tuğla (son tuğlanın zıt ucundan 1 tuğla öte). Döner: yon (son tuğla yönü, 0 yok),
    yeni (bu mumda oluşan tuğla yönü, yoksa 0), dondu (bool: bu mumda renk değişti)."""
    n = len(kap)
    yon = np.zeros(n, dtype="int64")
    yeni = np.zeros(n, dtype="int64")
    dondu = np.zeros(n, dtype=bool)
    top = bot = np.nan
    d = 0
    for t in range(n):
        if np.isnan(atr[t]):
            continue
        s = k * atr[t]
        if np.isnan(top):
            top = bot = kap[t]
        elif s > 0:
            hareket = 0
            c = kap[t]
            for _ in range(50):
                if d >= 0 and c >= top + s:
                    bot, top, h = top, top + s, 1
                elif d <= 0 and c <= bot - s:
                    top, bot, h = bot, bot - s, -1
                elif d == 1 and c <= bot - s:
                    top, bot, h = bot, bot - s, -1
                elif d == -1 and c >= top + s:
                    bot, top, h = top, top + s, 1
                else:
                    break
                if d != 0 and h != d:
                    dondu[t] = True
                d = h
                hareket = h
            yeni[t] = hareket
        yon[t] = d
    return yon, yeni, dondu


def renko_cekirdek(m, p):
    """Renko + RSI + StochRSI aşırı satım + destek. Long: bu mumda Renko KIRMIZIDAN YEŞİLE dönüş tuğlası oluştu;
    son `onay_n` mumda RSI <= rsi_alt ve StochRSI %K <= stoch_alt görüldü; destek: son onay_n mumun düşüğü, ondan önceki
    sr_n mumun düşüğüne <= tol_atr*ATR yakın/altında. Stop: son stop_n mumun dibi - tampon*ATR; hedef: hedef_r*risk
    (kart: min 1:3). Risk > maks_risk_atr*ATR ise işlem yok."""
    n = len(m)
    ac, yu, du, kap = _diziler(m)
    K, D = m["kapanis"], m["dusuk"]
    atr = _atr(m, p)
    ry, yeni, dondu = renko_serisi(kap, atr, p["renko_k"])
    onay = int(p["onay_n"])
    rsi_min = g.rsi(K, int(p["rsi_periyot"])).rolling(onay, min_periods=1).min().to_numpy()
    st_min = stoch_rsi(K, int(p["rsi_periyot"]), int(p["rsi_periyot"]), 3).rolling(onay, min_periods=1).min().to_numpy()
    yakin_dip = D.rolling(onay, min_periods=onay).min().to_numpy()
    onc_dip = D.rolling(int(p["sr_n"]), min_periods=int(p["sr_n"])).min().shift(onay).to_numpy()
    sw = D.rolling(int(p["stop_n"]), min_periods=int(p["stop_n"])).min().to_numpy()
    with np.errstate(invalid="ignore"):
        ok = ((yeni == 1) & dondu & (rsi_min <= p["rsi_alt"]) & (st_min <= p["stoch_alt"])
              & (yakin_dip <= onc_dip + p["tol_atr"] * atr))
        stop = sw - p["tampon_atr"] * atr
        risk = kap - stop
        ok &= (risk > 0) & (risk <= p["maks_risk_atr"] * atr)
    ok &= ust_tf_trend(m, p["ust_tf"], p["ust_ema"])
    hedef = kap + p["hedef_r"] * (kap - stop)
    return ok.astype("int64"), np.where(ok, stop, np.nan), np.where(ok, hedef, np.nan)
