"""EPA — kullanıcının EMA 8/21/55 + hacim + mum + destek/direnç + trend çizgisi + pullback/breakout stratejisi.

Kurallar ANALIZ_EMA_STRATEJI.md Bölüm 4'teki nesnel tanımlarla kodlanmıştır (kripto, 1G bağlam + 4S işlem, yalnız long).

Kurulum A (pullback): 4S EMA8 > EMA21 > EMA55; son 10 mumun tepesi en az 2 mum önce; mum dibi (bu ya da önceki) EMA8'e
  inmiş, kapanış EMA21 üstünde. Sinyal mumu (mum=), konum (konum=) ve hacim (hacim=) şartları ayrı ayrı açılıp kapanır.
  Giriş: sinyal mumunun tepesinde bekleyen alış emri (bir sonraki mum). Stop: iki mumun dibi - 0.2 ATR (>= smin ATR).
Kurulum B (breakout): son n mumun aralığı < k ATR (sıkışma), isteğe bağlı EMA8/21 iç içe; kırılım mumu aralık tepesinin
  üstünde güçlü kapanır; isteğe bağlı hacim >= vk x 20 mum ortalaması. Giriş sonraki açılış, stop aralık ortası.
Çıkış: 4S EMA21 altında 2 kapanış (e21x2) / EMA8 < EMA21 (e8x21) / 4S EMA21-50 trend dönüşü (h4); isteğe bağlı 1R kısmi kâr.

Kullanım: python3 -m backtest.epa izgara A|B
"""
import itertools, pickle, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit
from . import kripto_strateji as ks, gostergeler as g
from .pa_arastirma import yeniden_ornekle
from .kripto_motor import portfoy, metrik

SONUC = Path(__file__).resolve().parent.parent / "sonuclar" / "epa"
KES = pd.Timestamp("2024-01-01")
HIZALAMALAR = (0, 1, 2, 3)          # 4S mum başlangıcı kaydırma (saat)
BO_N, BO_K, BO_IC, BO_V = (12, 24), (3.0, 5.0), (0, 1), (0.0, 1.5, 2.0)   # kurulum B ön hesap ızgarası
PORTFOY = dict(evren_n=15, risk=0.005, max_poz=5, max_yon=5, max_pay=0.25, max_brut=1.0, maliyet=0.0007)


def yukle_hacim(V):
    """1S quote_volume (USDT hacmi) T x N, V ekseninde."""
    VOL = np.full(V["C"].shape, np.nan)
    for j, s in enumerate(V["semboller"]):
        d = pd.read_pickle(ks.KOK / "1h" / f"{s}.pkl")
        VOL[:, j] = d.quote_volume.reindex(V["zaman"]).to_numpy()
    VOL[np.isnan(V["C"])] = np.nan
    return VOL


@njit(cache=True)
def _seviyeler(h, l, c, a, k, tampon):
    """destek: bar dibi, kırılmış bir pivot tepeye (direnç -> destek) ya da onaylı pivot dibe +-tampon*ATR yakın ve kapanış üstünde.
    tc: son iki yükselen pivot dibi birleştiren trend çizgisine dokunup üstünde kapanış (çizgi kapanışla kırılınca geçersiz)."""
    n = len(c)
    destek = np.zeros(n, np.bool_); tc = np.zeros(n, np.bool_)
    kir = np.full(8, np.nan); kn = 0           # kırılmış dirençler (son 8)
    bek = np.full(8, np.nan); bn = 0           # henüz kırılmamış pivot tepeler
    dip = np.full(8, np.nan); dn = 0           # onaylı pivot dipler
    p1i = -1; p1v = 0.0; p2i = -1; p2v = 0.0; gecerli = False
    for t in range(2 * k, n):
        m = t - k                               # t kapanışında onaylanan pivot adayı
        ph = True; pl = True
        for u in range(m - k, m + k + 1):
            if u != m:
                if h[u] >= h[m]:
                    ph = False
                if l[u] <= l[m]:
                    pl = False
        if ph:
            bek[bn % 8] = h[m]; bn += 1
        if pl:
            dip[dn % 8] = l[m]; dn += 1
            if p2i >= 0 and l[m] > p2v and m - p2i >= k:
                p1i = p2i; p1v = p2v; p2i = m; p2v = l[m]; gecerli = True
            else:
                p1i = -1; p2i = m; p2v = l[m]; gecerli = False
        for q in range(8):                      # kapanışla kırılan dirençler destek olur
            if not np.isnan(bek[q]) and c[t] > bek[q]:
                kir[kn % 8] = bek[q]; kn += 1; bek[q] = np.nan
        if np.isnan(a[t]):
            continue
        tz = tampon * a[t]
        for q in range(8):
            for v in (kir[q], dip[q]):
                if not np.isnan(v) and l[t] <= v + tz and l[t] >= v - tz and c[t] > v:
                    destek[t] = True
        if gecerli and p1i >= 0:
            egim = (p2v - p1v) / (p2i - p1i)
            cizgi = p2v + egim * (t - p2i)
            if c[t] < cizgi:
                gecerli = False
            elif l[t] <= cizgi + tz:
                tc[t] = True
    return destek, tc


def bilesenler(V4):
    """4S T x N bileşen dizileri (her kurulum şartı ayrı; ızgara bunları birleştirir)."""
    T, N = V4["C"].shape
    ad = ("d_ust", "d_yatay_ok", "h4_ust", "h4_yatay_ok", "pb", "pb_lvl", "pb_stop", "m_user", "m_hammer", "m_engulf",
          "m_brooks", "k_ema21", "k_destek", "k_tc", "h_azalan", "bo_lvl", "e21x2", "e8x21", "atr")
    B = {k: np.zeros((T, N), bool) for k in ad}
    for k in ("pb_lvl", "pb_stop", "bo_lvl", "atr", "e21x2", "e8x21"):
        B[k] = np.full((T, N), np.nan)
    B["bo"] = {}
    for j in range(N):
        cc = V4["C"][:, j]
        ok = ~np.isnan(cc)
        if ok.sum() < 6 * 120:
            continue
        i0, i1 = np.argmax(ok), len(cc) - np.argmax(ok[::-1]); sl = slice(i0, i1)
        df = pd.DataFrame({k: V4[K][sl, j] for k, K in (("open", "O"), ("high", "H"), ("low", "L"), ("close", "C"))},
                          index=V4["zaman"][sl]).ffill()
        o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
        vol = np.nan_to_num(V4["VOL"][sl, j])
        a = g.atr(h, l, c, 14)
        e8, e21, e55 = g.ema(c, 8), g.ema(c, 21), g.ema(c, 55)
        # 1G bağlam: EMA 8>21>55, kapanış>EMA21, EMA55 eğimi (5 gün) > 0; yatay filtre: EMA21 10 günde >= 0.5 ATR değişmiş
        d = ks._htf(df, "1D"); dc = d.close.to_numpy(); da = g.atr(d.high.values, d.low.values, dc, 14)
        d8, d21, d55 = g.ema(dc, 8), g.ema(dc, 21), g.ema(dc, 55)
        dust = (d8 > d21) & (d21 > d55) & (dc > d21) & (d55 > np.roll(d55, 5))
        dyat = np.abs(d21 - np.roll(d21, 10)) >= 0.5 * da
        dust[:60] = False
        hz = g.htf_hizala(df.index, d, {"u": dust.astype(float), "y": dyat.astype(float)})
        B["d_ust"][sl, j] = hz["u"] == 1; B["d_yatay_ok"][sl, j] = hz["y"] == 1
        hust = (e8 > e21) & (e21 > e55)
        B["h4_ust"][sl, j] = hust
        B["h4_yatay_ok"][sl, j] = np.abs(e21 - np.roll(e21, 10)) >= 0.5 * a
        # Kurulum A: pullback
        hh10 = pd.Series(h).rolling(10).max().to_numpy()
        arg = pd.Series(h).rolling(10).apply(np.argmax, raw=True).to_numpy()      # 0..9, 9 = bu mum
        l2 = np.minimum(l, np.roll(l, 1))
        pb = hust & (arg <= 7) & (np.roll(h, 1) < hh10) & (l2 <= e8) & (c > e21)
        pb[:60] = False
        B["pb"][sl, j] = pb
        B["pb_lvl"][sl, j] = h * 1.0001
        B["pb_stop"][sl, j] = l2 - 0.2 * a
        rng = np.maximum(h - l, 1e-12)
        govde_alt = np.minimum(o, c); o1, c1 = np.roll(o, 1), np.roll(c, 1)
        hammer = ((govde_alt - l) >= 0.5 * rng) & (c >= l + 2 / 3 * rng)
        engulf = (c > o) & (c1 < o1) & (c >= o1) & (o <= c1)
        brooks = (c > o) & (c >= l + 2 / 3 * rng) & ((c - o) >= rng / 3) & (c > c1)
        B["m_hammer"][sl, j] = hammer; B["m_engulf"][sl, j] = engulf; B["m_user"][sl, j] = hammer | engulf
        B["m_brooks"][sl, j] = brooks
        B["k_ema21"][sl, j] = l2 <= e21 + 0.3 * a
        de, tc = _seviyeler(h, l, c, np.nan_to_num(a, nan=np.nan), 3, 0.5)
        B["k_destek"][sl, j] = de | np.roll(de, 1); B["k_tc"][sl, j] = tc | np.roll(tc, 1)
        v3 = pd.Series(vol).rolling(3).mean().shift(1).to_numpy(); v20 = pd.Series(vol).rolling(20).mean().shift(4).to_numpy()
        B["h_azalan"][sl, j] = v3 < v20
        # çıkışlar: -1 long çıkışı, +1 short çıkışı
        alt2 = (c < e21) & (c1 < np.roll(e21, 1)); ust2 = (c > e21) & (c1 > np.roll(e21, 1))
        B["e21x2"][sl, j] = np.where(alt2, -1.0, np.where(ust2, 1.0, 0.0))
        B["e8x21"][sl, j] = np.where(e8 < e21, -1.0, 1.0)
        B["atr"][sl, j] = a
        # Kurulum B: breakout (n, k, iç içe, hacim çarpanı) -> önceden hesaplanır
        v20b = pd.Series(vol).rolling(20).mean().shift(1).to_numpy()
        guclu = (c > o) & ((c - o) >= 0.5 * rng) & (c >= l + 2 / 3 * rng)
        ic = np.roll(np.abs(e8 - e21) < 0.5 * a, 1)
        for n in BO_N:
            ust = pd.Series(h).rolling(n).max().shift(1).to_numpy(); alt = pd.Series(l).rolling(n).min().shift(1).to_numpy()
            for kk in BO_K:
                sik = (ust - alt) < kk * np.roll(a, 1)
                kir = sik & guclu & (c > ust) & (c > e55)
                kir[:60] = False
                for icx in BO_IC:
                    for vk in BO_V:
                        m = kir & (ic if icx else True) & ((vol >= vk * v20b) if vk > 0 else True)
                        key = (n, kk, icx, vk)
                        if key not in B["bo"]:
                            B["bo"][key] = np.zeros((T, N), bool)
                        B["bo"][key][sl, j] = m
                B[("bo_stop", n, kk)] = B.get(("bo_stop", n, kk), np.full((T, N), np.nan))
                B[("bo_stop", n, kk)][sl, j] = np.clip(c - (ust + alt) / 2, 1.0 * a, 4.0 * a)
    return B


def _baglam(B, b):
    if b == "d":
        return B["d_ust"] & B["d_yatay_ok"]
    if b == "d_yok":          # yatay filtre kapalı
        return B["d_ust"]
    if b == "h4":
        return B["h4_yatay_ok"]
    return np.ones_like(B["d_ust"])


def sinyal_A(B, p):
    m = B["pb"] & _baglam(B, p["baglam"])
    if p["mum"] != "yok":
        m &= B["m_" + p["mum"]]
    if p["konum"] == "herhangi":
        m &= B["k_ema21"] | B["k_destek"] | B["k_tc"]
    elif p["konum"] != "yok":
        m &= B["k_" + p["konum"]]
    if p["hacim"]:
        m &= B["h_azalan"]
    lvl = B["pb_lvl"]
    stop = np.maximum(lvl - B["pb_stop"], p.get("smin", 1.0) * B["atr"])
    return m, np.where(m, lvl, np.nan), np.where(m, stop, np.nan)


def sinyal_B(B, p):
    m = B["bo"][(p["n"], p["k"], p["ic"], p["vk"])] & _baglam(B, p["baglam"])
    return m, None, np.where(m, B[("bo_stop", p["n"], p["k"])], np.nan)


def calistir(V4, F4, B, p, kurulum):
    m, lvl, stop = (sinyal_A if kurulum == "A" else sinyal_B)(B, p)
    SIG = m.astype(float); SIG[V4["ONC"] >= PORTFOY["evren_n"]] = 0
    if p["cikis"] == "h4":
        CIK = np.where(F4["h4_yon"] < 0, -1.0, np.where(F4["h4_yon"] > 0, 1.0, 0.0))
    else:
        CIK = np.nan_to_num(B[p["cikis"]])
    q = dict(PORTFOY, risk=p.get("risk", PORTFOY["risk"]), maliyet=p.get("maliyet", PORTFOY["maliyet"]),
             tp1_r=p["tp1_r"], tp1_pay=p.get("tp1_pay", 0.15), be_tp1=True, hedef_r=p.get("hedef_r", 0.0), max_bar=0,
             iz_atr=0.0)
    return portfoy(V4, SIG, stop, np.nan_to_num(B["atr"]), CIK, V4["ONC"], q, GSEV=lvl)


def ozet(rs, ts):
    """Hizalama getirilerinin ortalaması (sermaye eşit bölünür)."""
    r = pd.concat(rs, axis=1).fillna(0).mean(axis=1); e = (1 + r).cumprod(); T = pd.concat(ts) if ts else pd.DataFrame()
    bos = pd.DataFrame({"R": []})
    m = metrik(e, bos); ei = e[e.index < KES]; eo = e[e.index >= KES]
    mi = metrik(ei / ei.iloc[0], bos); mo = metrik(eo / eo.iloc[0], bos)
    y = e.resample("YE").last(); yil = 100 * (y / y.shift(1).fillna(1) - 1); yil = yil[yil.index.year >= 2020]
    R = T.R if len(T) else pd.Series(dtype=float)
    wr = 100 * (R > 0).mean() if len(R) else np.nan
    pf = R[R > 0].sum() / -R[R <= 0].sum() if (R <= 0).any() else np.nan
    ro = T[T.giris_zaman >= KES].R if len(T) else R
    return dict(wr=wr, pf=pf, n_yil=len(R) / len(rs) / 6.75, cagr=m["cagr"], dd=m["maxdd"], sh=m["sharpe"],
                cal=m["calmar"], is_sh=mi["sharpe"], oos_sh=mo["sharpe"], oos_cagr=mo["cagr"], oos_dd=mo["maxdd"],
                oos_pf=ro[ro > 0].sum() / -ro[ro <= 0].sum() if (ro <= 0).any() else np.nan,
                yillar=dict(zip(yil.index.year, np.round(yil.values, 1))), r=r)


_D = None


def _is(args):
    kurulum, p = args
    rs, ts = [], []
    for kay in HIZALAMALAR:
        V4, F4, B = _D[kay]
        e, t = calistir(V4, F4, B, p, kurulum)
        rs.append(e.resample("1D").last().pct_change().fillna(0)); ts.append(t)
    o = ozet(rs, ts); o.pop("r")
    return kurulum, p, o


def hazirla():
    V = ks.yukle(); V["VOL"] = yukle_hacim(V)
    D = {}
    for kay in HIZALAMALAR:
        V4 = yeniden_ornekle(V, "4h", kay)
        F4 = ks.ozellikler(V4, dict(d_f=20, d_s=50, h4_f=21, h4_s=50, kir_n=12, sw_n=12))
        D[kay] = (V4, F4, bilesenler(V4))
        print("hizalama", kay, "hazır", flush=True)
    return D


IZGARA_A = [dict(baglam=b, mum=m, konum=k, hacim=h, cikis=c, tp1_r=tp)
            for b in ("d", "d_yok", "h4") for m in ("yok", "user", "brooks") for k in ("yok", "ema21", "destek", "tc", "herhangi")
            for h in (0, 1) for c in ("e21x2", "e8x21", "h4") for tp in (0.0, 1.0)]
IZGARA_B = [dict(baglam=b, n=n, k=k, ic=i, vk=v, cikis=c, tp1_r=tp)
            for b in ("d", "d_yok", "h4") for n in (12, 24) for k in (3.0, 5.0) for i in (0, 1) for v in (0.0, 1.5, 2.0)
            for c in ("e21x2", "e8x21", "h4") for tp in (0.0, 1.0)]


def izgara(kurulum):
    global _D
    from multiprocessing import get_context
    SONUC.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    _D = hazirla()
    isler = [(kurulum, p) for p in (IZGARA_A if kurulum == "A" else IZGARA_B)]
    print(len(isler), "kombinasyon", f"{time.time()-t0:.0f}s", flush=True)
    res = []
    with get_context("fork").Pool(3) as pool:
        for i, r in enumerate(pool.imap_unordered(_is, isler, chunksize=2)):
            res.append(r)
            if (i + 1) % 50 == 0:
                print(i + 1, f"{time.time()-t0:.0f}s", flush=True)
                pickle.dump(res, open(SONUC / f"izgara_{kurulum}.pkl", "wb"))
    pickle.dump(res, open(SONUC / f"izgara_{kurulum}.pkl", "wb"))
    print("bitti", f"{time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    izgara(sys.argv[2] if len(sys.argv) > 2 else "A")
