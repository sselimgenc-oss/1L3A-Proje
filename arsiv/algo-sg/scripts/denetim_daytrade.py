"""day-trade-sg çapraz denetim — salt okunur; kendi kodu (daytrade/*, kagit/motor.portfoy) ile.
Kullanım: python denetim_dt.py <cache_kok> <etiket> <cikti.json>"""
import sys, os, json
CK, ET, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.environ["DAYTRADE_CACHE"] = CK
sys.path.insert(0, "/home/user/day-trade-sg")
import numpy as np, pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from daytrade import data as D
from daytrade.universe import crypto
from daytrade.features import build
from daytrade.backtest import simulate
from daytrade.strategies import STRATEGIES, Signals
from daytrade.secili import SECILI, PORTFOY
from kagit.motor import portfoy_ayri

SCR = Path(__file__).parent
SYMS = sorted({p.name.split("_")[0][:-4] for p in Path(CK, "binance").glob("*_15m.pkl")})
POST23 = {"ZEC", "HYPE", "GRAM", "TAO", "QNT", "ENA", "SUI", "NEAR", "AAVE", "PUMP"}  # Eki-2023'te ilk 25'te olmayanlar

def bun(inst):
    e, h1, h4 = D.load(inst, "15m"), D.load(inst, "1h"), D.load(inst, "4h")
    if e is None or h1 is None or len(e) < 300 or len(h1) < 250:
        return None
    if h4 is None or len(h4) < 210:
        h4 = D.resample(h1, "4h")
    return build(inst, e, h1, h4, "15m")

def btc_gunluk():
    s = []
    for k in ("dt_2021", "dt_uzun"):
        x = pd.read_pickle(SCR / k / "cache/binance/BTCUSDT_1h.pkl")["close"]
        s.append(x)
    c = pd.concat(s); c = c[~c.index.duplicated(keep="last")].sort_index().resample("1D").last().dropna()
    return c

def isle(sym):
    inst = crypto(sym)
    btc = bun(crypto("BTC"))
    df = btc if sym == "BTC" else bun(inst)
    if df is None:
        return []
    df = df.copy()
    df["mkt_move"] = ((btc["close"] - btc["dopen"]) / btc["atr_d"]).reindex(df.index)
    df["mkt_h4_up"] = (btc["h4_ema20"] > btc["h4_ema50"]).reindex(df.index)
    df["mkt_h4_dn"] = (btc["h4_ema20"] < btc["h4_ema50"]).reindex(df.index)
    guc = (df["close"] - df["dopen"]) / df["atr_d"]
    out = []
    for st, p in SECILI.items():
        fn = STRATEGIES[st][0]
        for filt in ("btc4h", "yok"):
            pp = dict(p, btc_filter=(filt == "btc4h"))
            sig = fn(df, **pp)
            vars_ = [("v", sig)]
            if filt == "btc4h":   # +1 mum gecikme (canlı paritesi)
                sh = lambda s, f: s.shift(1).fillna(f)
                vars_.append(("gec1", Signals(sh(sig.long, False).astype(bool), sh(sig.short, False).astype(bool),
                                              sig.long_stop.shift(1), sig.short_stop.shift(1), sig.exit)))
            for vk, sg in vars_:
                for c in ((0.0008, 0.0012, 0.0016) if vk == "v" and filt == "btc4h" else (0.0008,)):
                    tr = simulate(df, sg, c, inst.symbol, st)
                    if len(tr) == 0:
                        continue
                    sb = tr["entry_time"] - pd.Timedelta(minutes=15)
                    tr = tr.assign(skor=tr["dir"].to_numpy() * guc.reindex(sb).to_numpy(), asset_class="crypto",
                                   filt=filt, var=vk, cost=c, sym=sym)
                    out.append(tr)
    h4up = df["mkt_h4_up"] if sym == "BTC" else None
    return out, (h4up.resample("1D").mean() if h4up is not None else None)

def istat(al, eq0, a=None, b=None, btcr=None):
    x = al
    if a is not None: x = x[x.entry_time >= a]
    if b is not None: x = x[x.entry_time < b]
    if len(x) == 0:
        return dict(n=0)
    g = x.groupby(x.exit_time.dt.floor("D"))["kar_usd"].sum()
    idx = pd.date_range(x.entry_time.min().floor("D"), x.exit_time.max().floor("D"), freq="D")
    g = g.reindex(idx, fill_value=0.0)
    eq = eq0 + g.cumsum(); r = g / eq.shift(1).fillna(eq0)
    w = r.resample("W").apply(lambda z: (1 + z).prod() - 1)
    q = r.quantile(0.05)
    R = x.R.to_numpy(); gl = -R[R <= 0].sum()
    d = dict(n=int(len(x)), wr=round(float((R > 0).mean() * 100), 1), pf=round(float(R[R > 0].sum() / gl), 2) if gl > 0 else None,
             getiri=round(float(eq.iloc[-1] / eq0 - 1) * 100, 1), dd=round(float((eq / eq.cummax() - 1).min()) * 100, 1),
             sharpe=round(float(r.mean() / r.std() * np.sqrt(365)), 2) if r.std() > 0 else None,
             en_kotu_gun=round(float(r.min()) * 100, 2), en_kotu_hafta=round(float(w.min()) * 100, 2),
             cvar95_gun=round(float(r[r <= q].mean()) * 100, 2), skew=round(float(r.skew()), 2), kurt=round(float(r.kurt()), 2), gun=int(len(r)))
    if btcr is not None:
        j = pd.concat([r, btcr], axis=1, join="inner").dropna()
        d["btc_kor"] = round(float(j.iloc[:, 0].corr(j.iloc[:, 1])), 2)
        wj = j.resample("W").sum(); d["btc_kor_hafta"] = round(float(wj.iloc[:, 0].corr(wj.iloc[:, 1])), 2)
    return d

if __name__ == "__main__":
    with ProcessPoolExecutor(4) as ex:
        res = list(ex.map(isle, SYMS))
    tr = pd.concat([t for r in res if r for t in r[0]], ignore_index=True)
    h4up = next(r[1] for r, s in zip(res, SYMS) if s == "BTC")
    bd = btc_gunluk(); btcr = bd.pct_change()
    sma = {n: bd.rolling(n).mean() for n in (100, 200)}
    def izin(n):   # dünkü kapanış SMA(n) üstünde (ya da SMA yok) -> izin
        ok = (bd >= sma[n]) | sma[n].isna()
        return ok.shift(1).fillna(True)
    tr["gun"] = tr.entry_time.dt.floor("D")
    for n in (100, 200):
        tr[f"sma{n}"] = izin(n).reindex(tr["gun"]).fillna(True).to_numpy()
    if ET == "uzun":
        t0, t1 = tr.entry_time.min(), tr.entry_time.max()
        cut = t0 + (t1 - t0) * 0.7
        per = {"TUM": (None, None), "IS": (None, cut), "OOS": (cut, None)}
        tr = tr[tr.entry_time >= pd.Timestamp("2023-10-10", tz="UTC")]
    else:
        tr = tr[(tr.entry_time >= pd.Timestamp("2021-01-01", tz="UTC")) & (tr.entry_time < pd.Timestamp("2023-10-01", tz="UTC"))]
        per = {"TUM": (None, None), "2022": (pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2023-01-01", tz="UTC"))}
    surv = set(SYMS) - POST23 if ET == "uzun" else set(SYMS) - {"ALGO","ATOM","AXS","EOS","FIL","FTT","ICP","LUNA","MATIC","SRM","THETA","VET","PUMP"}
    base = (tr.filt == "btc4h") & (tr["var"] == "v") & (tr.cost == 0.0008)
    V = {"V0_taban": base,
         "duyar_maliyet_012": (tr.filt == "btc4h") & (tr["var"] == "v") & (tr.cost == 0.0012),
         "duyar_maliyet_016": (tr.filt == "btc4h") & (tr["var"] == "v") & (tr.cost == 0.0016),
         "parite_gecikme_1mum": (tr.filt == "btc4h") & (tr["var"] == "gec1"),
         "O1_sma200": base & tr.sma200, "O1k_sma100": base & tr.sma100,
         "O2_btc4h_kaldir": (tr.filt == "yok") & (tr["var"] == "v"),
         "O2b_btc4h_yerine_sma200": (tr.filt == "yok") & (tr["var"] == "v") & tr.sma200,
         "O3_pit_evren": base & tr.sym.isin(surv)}
    out = {"semboller": SYMS, "hayatta_kalan_alt_kume": sorted(surv), "sonuc": {}}
    for k, m in V.items():
        al = portfoy_ayri(tr[m].drop(columns=["gun"]), dict(PORTFOY))
        out["sonuc"][k] = {p: istat(al, PORTFOY["sermaye"], a, b, btcr) for p, (a, b) in per.items()}
        if k == "V0_taban":
            al2 = portfoy_ayri(tr[m].drop(columns=["gun"]), dict(PORTFOY, gunluk_zarar_limiti=-1.0))
            out["gunluk_limit_etkisi"] = {"limitli_islem": int(len(al)), "limitsiz_islem": int(len(al2)),
                                         "limitsiz": istat(al2, PORTFOY["sermaye"], None, None, btcr)}
            out["sembol_katki_usd"] = al.groupby("sym")["kar_usd"].sum().round(0).sort_values().to_dict()
            out["strateji"] = {s: istat(al[al.strategy == s], PORTFOY["sermaye"] / 3) for s in SECILI}
            out["yillik"] = {str(y): istat(al[al.entry_time.dt.year == y], PORTFOY["sermaye"]) for y in sorted(al.entry_time.dt.year.unique())}
    if h4up is not None:
        h = h4up.dropna()
        out["btc4h_izin_orani"] = {str(y): round(float(h[h.index.year == y].mean()), 2) for y in sorted(set(h.index.year))}
        out["btc4h_son_30g"] = round(float(h.iloc[-30:].mean()), 2); out["btc_son"] = str(h.index[-1])
    out["btc_sma200_son"] = {"kapanis": float(bd.iloc[-1]), "sma200": float(sma[200].iloc[-1]), "tarih": str(bd.index[-1])}
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "sonuc"}, default=str)[:2500])
    for k, v in out["sonuc"].items():
        print(k, {p: {z: v[p].get(z) for z in ("n", "wr", "pf", "getiri", "dd", "sharpe", "en_kotu_gun", "cvar95_gun")} for p in v})
