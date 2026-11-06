import importlib, sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, '/home/user')
k = importlib.import_module('swing-sg.karsilastirma.koni')
S = {ad: f() for ad, f in [('swing', k.swing_r), ('trend', k.trend_r), ('algo', k.algo_r), ('daytrade', k.daytrade_r), ('strateji', k.strateji_r)]}
D = pd.DataFrame(S).dropna()
D = D[D.index >= '2023-10-20']
W = (1 + D).resample('W').prod() - 1   # haftalık: kapanış günü topaklanmasını yumuşatır
print("Ortak dönem", D.index[0].date(), "→", D.index[-1].date(), len(W), "hafta")
def ist(r):
    y = (1 + r).prod() ** (52 / len(r)) - 1; v = r.std() * np.sqrt(52)
    e = (1 + r).cumprod(); dd = (e / e.cummax() - 1).min()
    return y, v, y / v if v else np.nan, dd, r.quantile(0.05), r[r <= r.quantile(0.05)].mean()
print("\nHesap      yıllık   vol   Sharpe  maksDD  hafta VaR95 CVaR95")
for c in W: y, v, s, dd, var, cvar = ist(W[c]); print(f"{c:9s} {y:7.1%} {v:6.1%} {s:6.2f} {dd:7.1%} {var:8.1%} {cvar:7.1%}")
print("\nHaftalık korelasyon\n", W.corr().round(2))
def portfoy(w, R): return (R * w).sum(axis=1)
def agirlik(R, yontem):
    n = R.shape[1]; C = R.cov().values; v = np.sqrt(np.diag(C))
    if yontem == 'esit': w = np.ones(n) / n
    elif yontem == 'ters_vol': w = (1 / v) / (1 / v).sum()
    elif yontem == 'min_var':
        Ci = np.linalg.pinv(C); w = Ci @ np.ones(n); w = np.clip(w, 0, None); w /= w.sum()
    elif yontem == 'risk_parite':
        w = np.ones(n) / n
        for _ in range(500):
            rc = w * (C @ w); w = w * (rc.mean() / rc) ** 0.5; w /= w.sum()
    return pd.Series(w, index=R.columns)
yar = len(W) // 2; A, B = W.iloc[:yar], W.iloc[yar:]
print(f"\nAğırlık ilk yarıda ({A.index[0].date()}→{A.index[-1].date()}) belirlendi, ikinci yarıda test ({B.index[0].date()}→{B.index[-1].date()}):")
print("Yöntem        ağırlıklar (swing trend algo daytrade strateji)   | tüm dönem: yıllık vol Sharpe DD | 2. yarı: yıllık Sharpe DD")
for y in ['esit', 'ters_vol', 'risk_parite', 'min_var']:
    w = agirlik(A, y); t = ist(portfoy(w, W)); b = ist(portfoy(w, B))
    print(f"{y:12s} {' '.join(f'{x:5.0%}' for x in w)}   | {t[0]:6.1%} {t[1]:5.1%} {t[2]:5.2f} {t[3]:6.1%} | {b[0]:6.1%} {b[2]:5.2f} {b[3]:6.1%}")
print("\nBirini çıkarınca (eşit ağırlık, tüm dönem):")
for c in W:
    R = W.drop(columns=c); t = ist(R.mean(axis=1)); print(f"  {c:9s} hariç: yıllık {t[0]:6.1%} Sharpe {t[2]:5.2f} DD {t[3]:6.1%}")
for kume in [['strateji', 'trend'], ['strateji', 'trend', 'daytrade'], ['strateji', 'trend', 'swing'], ['strateji', 'swing'], ['strateji', 'trend', 'algo']]:
    t = ist(W[kume].mean(axis=1)); print(f"  yalnız {'+'.join(kume):28s}: yıllık {t[0]:6.1%} Sharpe {t[2]:5.2f} DD {t[3]:6.1%}")
