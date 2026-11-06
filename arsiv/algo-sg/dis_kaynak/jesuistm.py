"""je-suis-tm/quant-trading stratejileri — orijinal kurallar, kripto verisine uyarlanmış.

Uyarlama notları (rapor tablosunda da yazıyor):
- Orijinaller tek hisse/FX üzerinde, çoğu sadece long ve günlük mum. Burada 25 coinde eşit dilimle.
- Mutlak fiyat eşikleri (FX'te 0.0001, hissede 0.2$) fiyatın oranına çevrildi.
- Shooting Star orijinalinde ertesi mumu kullanan (ileriye bakan) iki koşul var; burada onay mumu
  kapandıktan sonra işleme giriliyor (dürüst sürüm).
- London Breakout ve Dual Thrust dakika verisi ister; 1 saatlik mumla yaklaşık uygulandı.
"""
import numpy as np, pandas as pd, talib
from . import ortak as O


def macd_osc(b, ma1=12, ma2=26):
    c = b["close"]
    pos = (c.rolling(ma1, min_periods=1).mean() >= c.rolling(ma2, min_periods=1).mean()).astype(float)
    pos.iloc[:ma2] = 0.0
    return pos


def heikin_ashi(b, stls=3):
    o, h, l, c = (b[k].values for k in ("open", "high", "low", "close"))
    n = len(c)
    hc = (o + h + l + c) / 4
    ho = np.zeros(n); ho[0] = o[0]
    for i in range(1, n):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    hh = np.maximum.reduce([ho, hc, h]); hl = np.minimum.reduce([ho, hc, l])
    units = np.zeros(n); u = 0
    for i in range(1, n):
        if ho[i] > hc[i] and np.isclose(ho[i], hh[i]) and abs(ho[i] - hc[i]) > abs(ho[i - 1] - hc[i - 1]) and ho[i - 1] > hc[i - 1]:
            if u < stls:
                u += 1
        elif ho[i] < hc[i] and np.isclose(ho[i], hl[i]) and ho[i - 1] < hc[i - 1]:
            u = 0
        units[i] = u
    return pd.Series(units / stls, index=b.index)


def awesome(b):
    m = (b["high"] + b["low"]) / 2
    return (m.rolling(5).mean() > m.rolling(34).mean()).astype(float)


def psar(b):
    s = talib.SAR(b["high"].values, b["low"].values, acceleration=0.02, maximum=0.2)
    return pd.Series(np.where(s < b["close"].values, 1.0, 0.0), index=b.index)


def rsi_basit(b):
    r = talib.RSI(b["close"].values, 14)
    return pd.Series(np.select([r < 30, r > 70], [1.0, -1.0], 0.0), index=b.index)


def rsi_obo(b, period=25, delta=0.02, head=1.1, shoulder=1.1, exit_rsi=4, exit_days=5):
    """Fiyatta omuz-baş-omuz -> short; RSI 4 puan yükselince veya 5 mum sonra kapat. delta fiyatın oranı."""
    c = b["close"].values; r = talib.RSI(c, 14); n = len(c)
    pos = np.zeros(n); inpos = False; entry_rsi = 0.0; cnt = 0
    for i in range(period + 14, n):
        if inpos:
            cnt += 1
            if r[i] - entry_rsi > exit_rsi or cnt > exit_days:
                inpos = False; cnt = 0
            pos[i] = -1.0 if inpos else 0.0
            continue
        w = c[i - period:i]
        if c[i] == w.max():
            continue
        d = delta * c[i]
        j = i - period + int(np.argmax(w))
        if abs(c[j] - c[i]) <= head * d:
            continue
        bottom = c[i]
        ks = [k for k in range(j, i) if abs(c[k] - bottom) < d]
        if not ks:
            continue
        k = ks[0]
        ls = [x for x in range(j, i - period + 1, -1) if abs(c[x] - bottom) < d]
        if not ls:
            continue
        l = ls[0]
        ms = [x for x in range(i - period, l) if abs(c[x] - bottom) < d]
        if not ms:
            continue
        m = ms[0]
        if l <= m:
            continue
        nn = m + int(np.argmax(c[m:l]))
        if not (c[nn] - bottom > shoulder * d and c[j] - c[nn] > shoulder * d):
            continue
        top = c[nn]
        if any(abs(c[o] - top) < d for o in range(k, i)):
            inpos = True; entry_rsi = r[i]; cnt = 0; pos[i] = -1.0
    return pd.Series(pos, index=b.index)


def shooting_star(b, lower_bound=0.2, body_size=0.5, stop_threshold=0.05, holding_period=7):
    o, h, l, c = (b[k] for k in ("open", "high", "low", "close"))
    body = (o - c).abs()
    c1 = o >= c
    c2 = (c - l) < lower_bound * body
    c3 = body < (o - c).expanding().mean().abs() * body_size  # orijinal: abs(tüm örneğin (o-c) ortalaması) (ileriye bakar) -> genişleyen ortalama
    c4 = (h - o) >= 2 * (o - c)
    c5 = c >= c.shift(1)
    c6 = c.shift(1) >= c.shift(2)
    pat = c1 & c2 & c3 & c4 & c5 & c6
    conf = pat.shift(1, fill_value=False) & (h <= h.shift(1)) & (c <= c.shift(1))  # onay mumu kapandı
    cv = c.values; pos = np.zeros(len(cv)); i = 0; cf = conf.values
    while i < len(cv):
        if cf[i]:
            e = cv[i]; pos[i] = -1.0; k = 0
            while i + 1 < len(cv):
                i += 1; k += 1
                if abs(cv[i] / e - 1) > stop_threshold or k >= holding_period:
                    break
                pos[i] = -1.0
        i += 1
    return pd.Series(pos, index=b.index)


def bollinger_w(b, period=75, alpha=0.0001 / 1.3, beta=0.0001 / 1.3):
    """W dibi (Bollinger) -> long; bant daralınca (std < beta) çık. alpha/beta GBPUSD fiyatına göre orana çevrildi."""
    p = b["close"].values; n = len(p)
    sd = pd.Series(p).rolling(20).std().values; mid = pd.Series(p).rolling(20).mean().values
    up = mid + 2 * sd; lo = mid - 2 * sd
    pos = np.zeros(n); inpos = False
    for i in range(period, n):
        a = alpha * p[i]; moveon = False
        if not inpos and p[i] > up[i]:
            for j in range(i, i - period, -1):
                if abs(mid[j] - p[j]) < a and abs(mid[j] - up[i]) < a:
                    moveon = True; break
            if moveon:
                moveon = False
                for k in range(j, i - period, -1):
                    if abs(lo[k] - p[k]) < a:
                        thr = p[k]; moveon = True; break
            if moveon:
                moveon = False
                for l in range(k, i - period, -1):
                    if mid[l] < p[l]:
                        moveon = True; break
            if moveon:
                moveon = False
                for m in range(i, j, -1):
                    if p[m] - lo[m] < a and p[m] > lo[m] and p[m] < thr:
                        inpos = True; moveon = True; break
        if inpos and sd[i] < beta * p[i] and not moveon:
            inpos = False
        pos[i] = 1.0 if inpos else 0.0
    return pd.Series(pos, index=b.index)


def london_breakout(b1h, risky_stop=0.01 / 1.3, tokyo_hour=7, open_hour=8, close_hour=12):
    """b1h: 1h mum. Tokyo son saati (07 UTC) aralığı; 08 UTC mumu kapanışı aralığı aşarsa (en fazla risky_stop) giriş;
    ±risky_stop/2 veya 12 UTC'de çıkış."""
    idx = b1h.index; h, l, c = b1h["high"].values, b1h["low"].values, b1h["close"].values
    hr = idx.hour; n = len(c); pos = np.zeros(n); side = 0; ex = 0.0; up = lo = np.nan
    for i in range(n):
        if side != 0:
            hit = (l[i] < ex * (1 - risky_stop / 2) or h[i] > ex * (1 + risky_stop / 2))
            if hit or hr[i] == close_hour:
                side = 0
        if hr[i] == tokyo_hour:
            up, lo = h[i], l[i]
        elif hr[i] == open_hour and side == 0 and not np.isnan(up):
            if 0 < c[i] / up - 1 <= risky_stop:
                side = 1; ex = c[i]
            elif 0 < 1 - c[i] / lo <= risky_stop:
                side = -1; ex = c[i]
        pos[i] = side
    return pd.Series(pos, index=idx)


def dual_thrust(b1h, rg=5, k=0.5):
    """Önceki rg günün aralığı; gün açılışı ± k*aralık kırılımında giriş (ters sinyalde dön), gün sonunda kapat."""
    d = O.D.resample(b1h, "1D")
    r1 = d["high"].rolling(rg).max() - d["close"].rolling(rg).min()
    r2 = d["close"].rolling(rg).max() - d["low"].rolling(rg).min()
    rng = np.maximum(r1, r2).shift(1)
    day = b1h.index.floor("1D")
    op = d["open"].reindex(day).values; rr = rng.reindex(day).values
    up = op + k * rr; lo = op - (1 - k) * rr
    c = b1h["close"].values; hr = b1h.index.hour
    pos = np.zeros(len(c)); side = 0
    for i in range(len(c)):
        if hr[i] == 0:
            side = 0
        if not np.isnan(up[i]):
            if c[i] > up[i]:
                side = 1
            elif c[i] < lo[i]:
                side = -1
        if hr[i] == 23:
            side = 0
        pos[i] = side
    return pd.Series(pos, index=b1h.index)


PAIR_COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT", "LINKUSDT", "BCHUSDT", "ETCUSDT"]


def pair_trading_weights(bars, coins, bandwidth=250):
    """Engle-Granger (pencere 250 gün); eşbütünleşik ise kalıntı z'si üst sınırı aşınca asset1 long / asset2 short, alt sınırda tersi."""
    import statsmodels.api as sm
    from statsmodels.tsa.stattools import adfuller
    C = O.panel({s: bars[s] for s in coins}).dropna(how="all")
    pairs = [(a, b_) for i, a in enumerate(coins) for b_ in coins[i + 1:]]
    W = pd.DataFrame(0.0, index=C.index, columns=coins)
    for a, b_ in pairs:
        x, y = C[a], C[b_]
        ok = x.notna() & y.notna()
        xi, yi = x[ok], y[ok]
        prev = False; z = up = lo = None; params = None; sig = pd.Series(0.0, index=xi.index)
        for t in range(bandwidth, len(xi), 1):
            X = xi.iloc[t - bandwidth:t]; Y = yi.iloc[t - bandwidth:t]
            m = sm.OLS(Y.values, sm.add_constant(X.values)).fit()
            e = m.resid
            try:
                coint = adfuller(e, maxlag=1, autolag=None)[1] <= 0.05
            except ValueError:  # sabit kalıntı (işlem görmeyen coin)
                coint = False
            if coint:
                dX = np.column_stack([np.ones(bandwidth - 1), np.diff(X.values), e[:-1]])
                coint = np.linalg.lstsq(dX, np.diff(Y.values), rcond=None)[0][-1] <= 0
            if not prev and coint:
                params = m.params; mu, sd = e.mean(), e.std()
                z0 = ((yi.iloc[t] - (params[0] + params[1] * xi.iloc[t])) - mu) / sd
                up, lo = z0 + sd, z0 - sd
            if coint and params is not None:
                zt = ((yi.iloc[t] - (params[0] + params[1] * xi.iloc[t])) - mu) / sd
                if zt > up:
                    sig.iloc[t] = 1.0
                elif zt < lo:
                    sig.iloc[t] = -1.0
            prev = coint
        W.loc[sig.index, a] += sig / len(pairs) / 2
        W.loc[sig.index, b_] -= sig / len(pairs) / 2
    return W


STRATEJILER = {
    "JT_MACD_osilator": ("1D", macd_osc), "JT_Heikin_Ashi": ("1D", heikin_ashi), "JT_Awesome_osilator": ("1D", awesome),
    "JT_Parabolic_SAR": ("1D", psar), "JT_RSI_30_70": ("1D", rsi_basit), "JT_RSI_omuz_bas_omuz": ("1D", rsi_obo),
    "JT_Shooting_Star": ("1D", shooting_star), "JT_Bollinger_W": ("1h", bollinger_w),
    "JT_London_Breakout": ("1h", london_breakout), "JT_Dual_Thrust": ("1h", dual_thrust),
}


def calistir():
    rows, seriler = [], {}
    for ad, (tf, fn) in STRATEJILER.items():
        res = {}
        for ev in (("ana", "stres", "gel") if tf == "1D" else ("ana", "stres")):
            bars, fund = O.barlar(ev, tf)
            pos = {s: fn(b) for s, b in bars.items()}
            g, tr = O.pozisyon_degerlendir(pos, bars, fund)
            res[ev] = O.donemler(g, tr)
            if ev == "ana":
                seriler[ad] = g
        rows.append(O.tablo_satiri(ad, res["ana"], res["stres"]))
        if "gel" in res:
            for per, k in (("IS", "is"), ("OOS", "oos")):
                d = res["gel"][per] or {}
                rows[-1][f"pf_gel_{k}"] = d.get("pf", np.nan); rows[-1][f"sh_gel_{k}"] = d.get("sharpe", np.nan)
        print(ad, {k: round(v, 2) if isinstance(v, float) else v for k, v in rows[-1].items()}, flush=True)
    # çift işlemi (ana evren 10 eski coin; stres evreninde 10 coin)
    res = {}
    for ev, coins in (("ana", PAIR_COINS), ("stres", None)):
        bars, fund = O.barlar(ev, "1D")
        cs = coins or sorted(bars, key=lambda s: bars[s].index[0])[:10]
        W = pair_trading_weights(bars, cs)
        g, tr = O.agirlik_degerlendir(W, {s: bars[s] for s in cs}, {s: fund[s] for s in cs})
        res[ev] = O.donemler(g, tr)
        if ev == "ana":
            seriler["JT_Pair_trading"] = g
    rows.append(O.tablo_satiri("JT_Pair_trading", res["ana"], res["stres"]))
    rows[-1]["kapsam"] = "Pair trading (10 coin, 45 çift)"
    print("JT_Pair_trading", rows[-1], flush=True)
    return pd.DataFrame(rows), seriler
