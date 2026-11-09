"""A v2 (rejime bağlı short) karşılaştırması ve kaldıraç testi.

Kullanım:  ALGO_DATA=<veri> python -m scripts.a_v2_kaldirac <evren_etiketi> <cikti_json>
Ana evren için ALGO_DATA verilmez; stres evreni için ALGO_DATA=data_extra.

GÖREV 1: A mevcut / A yalnız long / A v2 (short yalnız BTC günlük kapanış < EMA200) ve A+B.
GÖREV 2: kaldıraç L = 1, 1.5, 2, 3, 5
  (a) aynı risk, kaldıraç yalnız teminatı azaltır; izole teminatta tasfiye mesafesi = 1/L - %0.5.
      Stop mesafesi bundan büyükse ve işlem içi en kötü fiyat (1H low/high) bu seviyeye ulaştıysa
      işlem tasfiye olur: getiri = -1/L nominal (kârlı kapanacak olsa bile).
  (b) büyütme: işlem riski x L, toplam maruziyet sınırı x L (tasfiye kuralı aynı L ile uygulanır).
"""
import json, os, sys
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
from algo import data as D, features as F
from algo.run import run, IS_END
from algo.portfolio import simulate_portfolio, mtm_drawdown
from algo.final import A1, A2, B as BP, SLEEVES

LEVS = (1.0, 1.5, 2.0, 3.0, 5.0)
Y22 = ("2022-01-01", "2023-01-01")


def mtm_stats(eq, a=None, b=None):
    d = eq.resample("1D").last().ffill()
    if a: d = d[d.index >= pd.Timestamp(a, tz="UTC")]
    if b: d = d[d.index < pd.Timestamp(b, tz="UTC")]
    r = d.pct_change().dropna()
    yrs = max((d.index[-1] - d.index[0]).days / 365.25, 1e-9)
    tot = d.iloc[-1] / d.iloc[0] - 1
    dd = (d / d.cummax() - 1).min()
    return dict(yillik=round(float((1 + tot) ** (1 / yrs) - 1) * 100, 1) if tot > -1 else -100.0,
                dd=round(float(dd) * 100, 1), sharpe=round(float(r.mean() / r.std() * np.sqrt(365)), 2) if r.std() > 0 else None)


def trade_stats(t, a=None, b=None):
    x = t
    if a: x = x[x.entry_time >= pd.Timestamp(a, tz="UTC")]
    if b: x = x[x.entry_time < pd.Timestamp(b, tz="UTC")]
    if len(x) == 0:
        return dict(n=0)
    w, l = x.R[x.R > 0].sum(), -x.R[x.R < 0].sum()
    return dict(n=int(len(x)), wr=round(float((x.R > 0).mean() * 100), 1), pf=round(float(w / l), 2) if l > 0 else None,
                ortR=round(float(x.R.mean()), 3), short=int((x.side < 0).sum()))


def ozet(t, eq):
    return {"TUM": {**trade_stats(t), **mtm_stats(eq)},
            "IS": {**trade_stats(t, b=IS_END), **mtm_stats(eq, b=IS_END)},
            "OOS": {**trade_stats(t, a=IS_END), **mtm_stats(eq, a=IS_END)},
            "2022": {**trade_stats(t, *Y22), **mtm_stats(eq, *Y22)}}


def birlesik(eqs):
    """Raporlardaki yöntem: kolların günlük yüzde getirilerinin ortalaması, bileşik."""
    X = pd.DataFrame(eqs).ffill().fillna(1.0)
    return (1 + X.pct_change().fillna(0).mean(axis=1)).cumprod()


def birlesik_basit(eqs):
    """Sermaye 50/50 bölünür, bileşiksiz: öz sermaye = 1 + ortalama(kol kâr/zararı). Kaldıraçta yanıltmaz."""
    X = pd.DataFrame(eqs).ffill().fillna(1.0)
    return 1 + (X - 1).mean(axis=1)


def mae(t, feats):
    """İşlem içi en kötü fiyatın girişe göre oranı (pozitif sayı = aleyhte hareket)."""
    out = np.zeros(len(t))
    for k, r in enumerate(t.itertuples()):
        f = feats[r.sym]; e, x = int(r.entry_i), int(r.exit_i)
        if r.side > 0:
            out[k] = 1 - f["low"].values[e:x + 1].min() / r.entry
        else:
            out[k] = f["high"].values[e:x + 1].max() / r.entry - 1
    return out


def tasfiye_uygula(t, L, mm=0.005):
    """Tasfiye: stop mesafesi > tasfiye mesafesi ve MAE >= tasfiye mesafesi -> R = -(1/L)/sl_pct (nominalin 1/L'si)."""
    t = t.assign(R_orig=t.R)
    if L <= 1.0:
        return t.assign(tasfiye=False)
    d = 1.0 / L - mm
    liq = (t.sl_pct > d) & (t.mae >= d)
    R = np.where(liq, -(1.0 / L) / t.sl_pct - (t.R_gross - t.R).clip(lower=0), t.R)  # maliyetler korunur
    Rg = np.where(liq, -(1.0 / L) / t.sl_pct, t.R_gross)
    return t.assign(R=R, R_gross=Rg, tasfiye=liq)


def main(etiket, out):
    syms = D.symbols()
    feats = {s: F.build(s) for s in syms}
    closes = {s: f["close"] for s, f in feats.items()}
    mods = {"A1": ("s5", A1), "A2": ("s5", A2),
            "A1_long": ("s5", {**A1, "long_only": True}), "A2_long": ("s5", {**A2, "long_only": True}),
            "A1_v2": ("s5", {**A1, "short_btc": 200}), "A2_v2": ("s5", {**A2, "short_btc": 200}),
            "B": ("s4", BP)}
    with ProcessPoolExecutor(4) as pool:
        tr = {m: run(fn, p, pool=pool).assign(module=m) for m, (fn, p) in mods.items()}
    rA, mA = SLEEVES["A"]["risk"], SLEEVES["A"]["max_open"]
    rB, mB = SLEEVES["B"]["risk"], SLEEVES["B"]["max_open"]
    varyant = {"A_mevcut": pd.concat([tr["A1"], tr["A2"]], ignore_index=True),
               "A_yalniz_long": pd.concat([tr["A1_long"], tr["A2_long"]], ignore_index=True),
               "A_v2_rejim_short": pd.concat([tr["A1_v2"], tr["A2_v2"]], ignore_index=True)}
    res = {"gorev1": {}, "gorev2": {}}
    _, takB = simulate_portfolio(tr["B"], risk=rB, max_open=mB)
    _, eqB = mtm_drawdown(takB, rB, closes)
    res["gorev1"]["B"] = ozet(takB, eqB)
    eqs = {}
    for k, t in varyant.items():
        _, tak = simulate_portfolio(t, risk=rA, max_open=mA)
        _, eq = mtm_drawdown(tak, rA, closes)
        eqs[k] = eq
        res["gorev1"][k] = ozet(tak, eq)
        for ad, fn in (("", birlesik), ("_basit", birlesik_basit)):
            cb = fn({"A": eq, "B": eqB})
            res["gorev1"][f"{k}+B{ad}"] = {p: mtm_stats(cb, *ab) for p, ab in (("TUM", (None, None)), ("IS", (None, IS_END)), ("OOS", (IS_END, None)), ("2022", Y22))}
    # ---------------- GÖREV 2 (mevcut A ve B ile)
    allA = varyant["A_mevcut"].copy(); allA["mae"] = mae(allA, feats)
    allB = tr["B"].copy(); allB["mae"] = mae(allB, feats)
    _, tA1 = simulate_portfolio(allA, risk=rA, max_open=mA)
    _, tB1 = simulate_portfolio(allB, risk=rB, max_open=mB)
    dag = {}
    for k, t in (("A", tA1), ("B", tB1)):
        q = t.sl_pct.quantile([0.5, 0.75, 0.95])
        dag[k] = {"stop_medyan_%": round(q[0.5] * 100, 2), "stop_p75_%": round(q[0.75] * 100, 2), "stop_p95_%": round(q[0.95] * 100, 2),
                  "guvenli_en_yuksek_L": round(1 / (q[0.95] + 0.005), 2)}
    res["gorev2"]["stop_dagilimi"] = dag
    for senaryo in ("a_ayni_risk", "b_buyutme"):
        res["gorev2"][senaryo] = {}
        for L in LEVS:
            row = {}
            eqL = {}
            for k, t0, r0, m0 in (("A", allA, rA, mA), ("B", allB, rB, mB)):
                t = tasfiye_uygula(t0, L)
                risk = r0 * (L if senaryo == "b_buyutme" else 1.0)
                cap = 5.0 * (L if senaryo == "b_buyutme" else 1.0)
                _, tak = simulate_portfolio(t, risk=risk, max_open=m0, max_lev_total=cap)
                _, eq = mtm_drawdown(tak, risk, closes)
                eqL[k] = eq
                s = mtm_stats(eq)
                row[k] = {**s, "islem": int(len(tak)), "tasfiye": int(tak["tasfiye"].sum()),
                          "tasfiye_%": round(float(tak["tasfiye"].mean() * 100), 1),
                          "tasfiye_olmasa_karli": int((tak["tasfiye"] & (tak["R_orig"] > 0)).sum())}
            row["A+B"] = mtm_stats(birlesik(eqL))
            row["A+B_basit"] = mtm_stats(birlesik_basit(eqL))
            res["gorev2"][senaryo][str(L)] = row
    json.dump(res, open(out, "w"), indent=1, default=float)
    print(json.dumps(res, indent=1, default=float)[:3000])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
