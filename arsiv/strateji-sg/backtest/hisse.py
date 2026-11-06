"""KGT v3 ve KMN'nin hisse / emtia piyasalarına uyarlanmış testi (Magnificent 7, BIST seçili hisseler, altın, Brent).

Veri: veri_dis/ (Yahoo Finance; araclar/veri_hisse.py ile GitHub sunucusunda indirilir). Saatlik veri son ~2 yıl,
günlük veri 2019-06'dan. Altın ve Brent için ayrıca ilk aşamanın 2020-2023 saatlik verisi (data/XAUUSD_H1, UKOIL_H1).

KGT uyarlaması: seans mumları (gece boşluğu doldurulmaz), pivot/CPR bir önceki işlem gününden, dar CPR + R1 kırılımı +
günlük EMA10/20 + kapanış > EMA20, stop 3 x ATR(1S) (0.75-3 ATR kırpma), 1R'de %15 kısmi + başabaş, 4S EMA21/50 trend
dönüşünde çıkış. Grup başına portföy: işlem başına %0.4 risk, en fazla 5 pozisyon, tek pozisyon <= %25.
KMN uyarlaması: grup içinde (Mag7: 2 long / 2 short, BIST: 3 / 3) 14 günlük riske göre düzeltilmiş momentum, 14 günde
bir dengeleme, ters oynaklık ağırlığı, ağırlık kayması dahil.
Masraf (taraf başına): ABD %0.03, BIST %0.10, emtia vadeli %0.03. BIST sonuçları TL ve USD (USDTRY ile) verilir.

Kullanım: python3 -m backtest.hisse
"""
from pathlib import Path
import numpy as np
import pandas as pd
from . import kripto_final as KF, strateji as st, kripto_strateji as ks, gostergeler as g, momentum as M
from .kripto_motor import portfoy, metrik

KOK = Path(__file__).resolve().parent.parent
VD = KOK / "veri_dis"
GRUPLAR = {
    "Mag7": dict(semboller=["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"], maliyet=0.0003, K=2,
                 tz="America/New_York", gun_bas=0.0, kiyas="NDX"),
    "BIST": dict(semboller=["AKBNK.IS", "BIMAS.IS", "EREGL.IS", "FROTO.IS", "KCHOL.IS", "SISE.IS", "TUPRS.IS",
                            "THYAO.IS", "TRALT.IS", "ASELS.IS", "EKGYO.IS"], maliyet=0.0010, K=3,
                 tz="Europe/Istanbul", gun_bas=0.0, kiyas="XU100.IS"),
    "Emtia": dict(semboller=["GC=F", "BZ=F"], maliyet=0.0003, K=None, tz="America/New_York", gun_bas=18.0, kiyas=None),
}


def _oku(sembol, aralik):
    f = VD / aralik / f"{sembol.replace('=', '_').replace('^', '')}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f, index_col=0, parse_dates=True)
    d.columns = [c.lower() for c in d.columns]
    d = d[["open", "high", "low", "close"]].astype(float).dropna()
    d = d[(d.high >= d.low) & (d.close > 0)]
    return d[~d.index.duplicated()].sort_index()


def kgt_sinyal(df, tz, gun_bas):
    """Seans mumlarında KGT giriş sinyali, stop mesafesi ve 4S trend (çıkış) dizileri."""
    p = dict(KF.GIRIS, tz=tz, gun_bas=gun_bas, bas=0, bit=24)
    st._IND.clear()
    s, stp, _, _, _ = st.gunluk_kirilim(df.assign(volume=1.0), p)
    h4 = ks._htf(df, "4h"); hc = h4.close.to_numpy()
    ef, es = g.ema(hc, KF.TREND["h4_f"]), g.ema(hc, KF.TREND["h4_s"])
    hy = np.where((ef > es) & (hc > ef), 1.0, np.where((ef < es) & (hc < ef), -1.0, 0.0))
    return np.where(s > 0, 1.0, 0.0), np.where(s > 0, stp, np.nan), g.htf_hizala(df.index, h4, {"hy": hy})["hy"]


def kgt_grup(veriler, tz, gun_bas, maliyet):
    """veriler: sembol -> 1S DataFrame. Ortak zaman ekseninde portföy."""
    z = sorted(set().union(*[set(d.index) for d in veriler.values()]))
    z = pd.DatetimeIndex(z); T, N = len(z), len(veriler); sem = list(veriler)
    A = {k: np.full((T, N), np.nan) for k in ("O", "H", "L", "C", "SIG", "STOP", "CIK")}
    for j, s in enumerate(sem):
        d = veriler[s]
        if len(d) < 24 * 40:
            continue
        sig, stp, hy = kgt_sinyal(d, tz, gun_bas)
        i = z.get_indexer(d.index)
        for k, v in (("O", d.open), ("H", d.high), ("L", d.low), ("C", d.close)):
            A[k][i, j] = v.to_numpy()
        A["SIG"][i, j] = sig; A["STOP"][i, j] = stp; A["CIK"][i, j] = hy
    V = dict(O=A["O"], H=A["H"], L=A["L"], C=A["C"], FUND=np.zeros((T, N)), UYE=np.ones((T, N), bool), zaman=z,
             semboller=sem)
    q = dict(KF.KGT, maliyet=maliyet, evren_n=99, ici_sira=1)
    S = np.nan_to_num(A["SIG"]); CIK = np.where(np.nan_to_num(A["CIK"]) < 0, -1.0, 0.0)
    e, t = portfoy(V, S, A["STOP"], np.zeros((T, N)), CIK, np.zeros((T, N)), q)
    return e, t


def ozet(e, t=None, usd=None):
    e = e.dropna()
    if usd is not None:      # TL eğrisini USD'ye çevir
        kur = usd.reindex(e.index, method="ffill")
        e = e / kur * kur.iloc[0]
    m = metrik(e, t if t is not None else pd.DataFrame({"R": []}))
    y = e.resample("YE").last(); yil = 100 * (y / y.shift(1).fillna(e.iloc[0]) - 1)
    out = dict(cagr=m["cagr"], dd=m["maxdd"], sh=m["sharpe"], yillar={k.year: round(v, 1) for k, v in yil.items()})
    if t is not None and len(t):
        tk = t[t.sebep != "açık (dönem sonu)"]
        out.update(islem=len(t), kazanma=100 * (tk.R > 0).mean(),
                   pf=tk.R[tk.R > 0].sum() / max(1e-9, -tk.R[tk.R <= 0].sum()))
    return out


def kmn_grup(semboller, K, maliyet, **kw):
    kap = {s: _oku(s, "1d") for s in semboller}
    C = pd.DataFrame({s: d.close for s, d in kap.items() if d is not None}).sort_index()
    C = C[C.index >= "2019-06-01"]
    H = pd.DataFrame({s: d.high for s, d in kap.items() if d is not None}).reindex(C.index)
    L_ = pd.DataFrame({s: d.low for s, d in kap.items() if d is not None}).reindex(C.index)
    D = dict(C=C, H=H, L=L_, F=pd.DataFrame(0.0, index=C.index, columns=C.columns),
             ONC=pd.DataFrame(0.0, index=C.index, columns=C.columns))
    P = dict(mod="notr", N=99, L=14, S=0, K=K, H=14, agirlik="ters_oyn", skor="risk", gecmis_gun=90, kayma=True,
             maliyet=maliyet)
    P.update(kw)
    r = M.calistir(D, P)
    r = r[r.index >= "2020-01-01"]
    esit = C.pct_change().mean(axis=1).fillna(0); esit = esit[esit.index >= "2020-01-01"]
    return r, esit


def calistir():
    sonuc = {}
    usdtry = _oku("USDTRY=X", "1d")
    usdtry = None if usdtry is None else usdtry.close
    for ad, G in GRUPLAR.items():
        veri = {s: _oku(s, "1h") for s in G["semboller"]}
        veri = {s: d for s, d in veri.items() if d is not None and len(d)}
        e, t = kgt_grup(veri, G["tz"], G["gun_bas"], G["maliyet"])
        sonuc[(ad, "KGT", "TL" if ad == "BIST" else "USD")] = ozet(e, t)
        if ad == "BIST" and usdtry is not None:
            sonuc[(ad, "KGT", "USD")] = ozet(e, t, usdtry)
        bh = pd.concat([d.close.resample("1D").last() for d in veri.values()], axis=1).ffill()
        bh = (bh / bh.bfill().iloc[0]).mean(axis=1)
        sonuc[(ad, "Al-tut (saatlik dönem)", "TL" if ad == "BIST" else "USD")] = ozet(bh)
        print(ad, "KGT:", {k: v for k, v in sonuc[(ad, 'KGT', 'TL' if ad == 'BIST' else 'USD')].items()}, flush=True)
        if G["K"]:
            for etiket, kw in (("KMN", {}), ("KMN L=30", dict(L=30)), ("KMN H=7", dict(H=7)),
                               ("Momentum long-only", dict(mod="long"))):
                r, esit = kmn_grup(G["semboller"], G["K"], G["maliyet"], **kw)
                e = (1 + r).cumprod()
                sonuc[(ad, etiket, "TL" if ad == "BIST" else "USD")] = ozet(e)
                if ad == "BIST" and usdtry is not None:
                    sonuc[(ad, etiket, "USD")] = ozet(e, None, usdtry)
            sonuc[(ad, "Al-tut eşit ağırlık (günlük)", "TL" if ad == "BIST" else "USD")] = ozet((1 + esit).cumprod())
            if ad == "BIST" and usdtry is not None:
                sonuc[(ad, "Al-tut eşit ağırlık (günlük)", "USD")] = ozet((1 + esit).cumprod(), None, usdtry)
    # altın ve Brent: ilk aşamanın 2020-2023 saatlik verisi (ayrı dönem)
    eski = {}
    for s, f in (("XAUUSD", "XAUUSD_H1"), ("UKOIL", "UKOIL_H1")):
        d = pd.read_pickle(KOK / "data" / f"{f}.pkl")[["open", "high", "low", "close"]].astype(float)
        eski[s] = d[d.high >= d.low]
    e, t = kgt_grup(eski, "America/New_York", 18.0, 0.0003)
    sonuc[("Emtia 2020-2023", "KGT", "USD")] = ozet(e, t)
    for s in eski:
        e1, t1 = kgt_grup({s: eski[s]}, "America/New_York", 18.0, 0.0003)
        sonuc[(f"{s} 2020-2023", "KGT", "USD")] = ozet(e1, t1)
    for s in ("GC=F", "BZ=F"):
        d = _oku(s, "1h")
        if d is not None:
            e1, t1 = kgt_grup({s: d}, "America/New_York", 18.0, 0.0003)
            sonuc[(f"{s} son 2 yıl", "KGT", "USD")] = ozet(e1, t1)
    return sonuc


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    s = calistir()
    satir = []
    for (grup, strat, para), o in s.items():
        satir.append(dict(grup=grup, strateji=strat, para=para, **{k: v for k, v in o.items() if k != "yillar"},
                          yillar=o["yillar"]))
    d = pd.DataFrame(satir)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    print(d.round(2).to_string(index=False))
    (KOK / "sonuclar" / "hisse").mkdir(parents=True, exist_ok=True)
    d.to_csv(KOK / "sonuclar" / "hisse" / "ozet.csv", index=False)
