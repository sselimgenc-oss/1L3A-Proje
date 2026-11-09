"""Altyapı depolarındaki (backtrader, backtesting.py, finmarketpy, QuantDinger, ai_quant_trade, OctoBot)
ve binance-trading-bot'taki hazır stratejiler — orijinal kurallar ve varsayılan parametreler.

Her kural üç tipten biridir:
- "pos": coin başına pozisyon serisi (-1..1), kapanışta karar.
- "isl": stop/hedef/iz süren stop gerektiren kural; algo.backtest simülatörü ile (sonraki açılıştan giriş,
         aynı mumda önce stop). Günlük getiri MTM olarak işlem yolundan üretilir.
- "agr": kesitsel portföy ağırlıkları (zaman x coin).
"""
import numpy as np, pandas as pd, talib
from algo import backtest as B
from . import ortak as O

BIG = 0.99  # "stop yok" için uzak stop (fiyatın %99'u)


# ------------------------------------------------------------ yardımcılar
def sma(x, n): return x.rolling(n).mean()
def ema(x, n): return x.ewm(span=n, adjust=False).mean()
def cross_up(a, b): return (a > b) & (a.shift(1) <= b.shift(1))
def cross_dn(a, b): return (a < b) & (a.shift(1) >= b.shift(1))
def atr(b, n): return pd.Series(talib.ATR(b["high"].values, b["low"].values, b["close"].values, n), index=b.index)
def rsi(c, n): return pd.Series(talib.RSI(c.values, n), index=c.index)


def durum(giris, cikis):
    """Giriş sinyalinde 1, çıkış sinyalinde 0 olan ve arada korunan long pozisyonu."""
    s = pd.Series(np.nan, index=giris.index)
    s[cikis.fillna(False)] = 0.0
    s[giris.fillna(False)] = 1.0
    return s.ffill().fillna(0.0)


def durum_ls(uzun, kisa):
    s = pd.Series(np.nan, index=uzun.index)
    s[kisa.fillna(False)] = -1.0
    s[uzun.fillna(False)] = 1.0
    return s.ffill().fillna(0.0)


def islem_yolu(t, b, cost=O.COST):
    """Simülatör işlemlerinden coin başına bar getirisi ve işlem getirileri — sabit nominal (pozisyon tabanlı
    değerlendirmeyle aynı muhasebe): her bar getirisi = yön x (kapanış_k / kapanış_k-1 - 1), giriş bar'ı giriş
    fiyatından, çıkış bar'ı çıkış fiyatına; giriş ve çıkışta maliyet; funding yaklaşık olarak simülatörün değeri."""
    c = b["close"].values
    pnl = np.zeros(len(b)); rets = []
    for r in t.itertuples():
        ei, xi, sd, e, xp = int(r.entry_i), int(r.exit_i), r.side, r.entry, r.exit_px
        tot = 0.0; prev = e
        for k in range(ei, xi + 1):
            px = xp if k == xi else c[k]
            inc = sd * (px / prev - 1); pnl[k] += inc; tot += inc; prev = px
        fund = -((r.R - r.R_gross) * r.sl_pct + 2 * cost)  # simülatörün net-brüt farkından maliyet çıkarılınca kalan funding
        pnl[ei] -= cost; pnl[xi] -= cost + fund
        rets.append((b.index[xi], tot - 2 * cost - fund))
    tr = pd.Series([x[1] for x in rets], index=pd.DatetimeIndex([x[0] for x in rets])) if rets else pd.Series(dtype=float)
    return pd.Series(pnl, index=b.index), tr


def isl_degerlendir(fn, bars, fund):
    cols, trs = {}, []
    for s, b in bars.items():
        kw = fn(b)
        t = B.simulate(b, funding=fund[s].values, **kw)
        p, tr = islem_yolu(t, b)
        cols[s] = p
        if len(tr):
            trs.append(tr)
    P = pd.DataFrame(cols)
    avail = pd.DataFrame({s: bars[s]["close"].notna() for s in bars}).reindex(P.index).fillna(False)
    port = (P.fillna(0).sum(axis=1) / avail.sum(axis=1).replace(0, np.nan)).fillna(0.0)
    tr = pd.concat(trs).sort_index() if trs else pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    if tr.index.tz is None:
        tr.index = tr.index.tz_localize("UTC")
    return port.resample("1D").sum(), tr


def kw(b, giris, sl_pct=None, sl_abs=None, tp_pct=None, trail=None, trail_k=1.0, trail_start_pct=None,
       cikis=None, max_bars=10**9, short=None, cikis_short=None):
    """Simülatör argümanları. Yüzdeler giriş fiyatına göre; sl yoksa uzak stop."""
    c = b["close"]
    side = giris.fillna(False).astype(int)
    if short is not None:
        side = side - short.fillna(False).astype(int)
    sl = sl_abs if sl_abs is not None else c * (sl_pct if sl_pct is not None else BIG)
    slp = (sl / c).values
    d = dict(side=side.values, sl_dist=np.asarray(sl, dtype=float), max_bars=max_bars)
    if tp_pct is not None:
        d["tp2_R"] = tp_pct / slp
    if trail is not None:
        d["trail_atr"] = np.asarray(trail, dtype=float); d["trail_k"] = trail_k
        if trail_start_pct is not None:
            d["trail_start_R"] = float(np.nanmedian(trail_start_pct / slp))
    if cikis is not None:
        d["exit_long"] = cikis.fillna(False).values
    if cikis_short is not None:
        d["exit_short"] = cikis_short.fillna(False).values
    return d


# ------------------------------------------------------------ "pos" kuralları
def ma_cross(f, s, kind="sma", ls=False):
    def fn(b):
        m = sma if kind == "sma" else ema
        a, z = m(b["close"], f), m(b["close"], s)
        return durum_ls(a > z, a < z) if ls else (a > z).astype(float)
    return fn


def close_vs_ma(n, ls=False, kind="sma"):
    def fn(b):
        m = (sma if kind == "sma" else ema)(b["close"], n)
        return durum_ls(b["close"] > m, b["close"] < m) if ls else (b["close"] > m).astype(float)
    return fn


def fin_sma200_volt(b):
    """finmarketpy FX trend: SMA200 üstü +1 altı -1; sinyal başına %10 vol hedefi (20g vol, en çok 5x), ay sonu ağırlık."""
    c = b["close"]
    sig = np.where(c > sma(c, 200), 1.0, -1.0)
    vol = c.pct_change().rolling(20).std() * np.sqrt(365)
    lev = (0.10 / vol).clip(upper=5.0)
    lev = lev.where(c.index.is_month_end).ffill()
    p = pd.Series(sig, index=c.index) * lev
    p[sma(c, 200).isna()] = 0.0
    return p.fillna(0.0)


def ti_roc(n=20):
    return lambda b: np.sign(b["close"].pct_change(n)).fillna(0.0)


def ti_gmma(b):
    c = b["close"]
    k = sum(ema(c, n) for n in (3, 5, 7, 10, 12, 15)) / 6
    u = sum(ema(c, n) for n in (30, 35, 40, 45, 50, 60)) / 6
    return pd.Series(np.where(k > u, 1.0, -1.0), index=c.index)


def ti_bb(n=20, m=2.0):
    def fn(b):
        c = b["close"]; mu, sd = sma(c, n), c.rolling(n).std()
        return durum_ls(c > mu + m * sd, c < mu - m * sd)
    return fn


def bt_ksignal(b):
    """backtrader kselrsi: RSI14 35 yukarı kesişim long (RSI>50 çık); 65 aşağı kesişim short (RSI<50 çık)."""
    r = rsi(b["close"], 14).values
    pos = np.zeros(len(r)); p = 0
    for i in range(1, len(r)):
        if p == 1 and r[i] > 50: p = 0
        elif p == -1 and r[i] < 50: p = 0
        if p == 0:
            if r[i - 1] <= 35 < r[i]: p = 1
            elif r[i - 1] >= 65 > r[i]: p = -1
        pos[i] = p
    return pd.Series(pos, index=b.index)


def btpy_sma4cross(b, n1=50, n2=100, ne=20, nx=10):
    c = b["close"]; s1, s2, se, sx = sma(c, n1), sma(c, n2), sma(c, ne), sma(c, nx)
    up, ce, cxd, cxu = (s1 > s2).values, cross_up(c, se).values, cross_dn(c, sx).values, cross_up(c, sx).values
    ced = cross_dn(c, se).values
    pos = np.zeros(len(c)); p = 0
    for i in range(len(c)):
        if p == 1 and cxd[i]: p = 0
        if p == -1 and cxu[i]: p = 0
        if p == 0:
            if up[i] and ce[i]: p = 1
            elif (not up[i]) and ced[i]: p = -1
        pos[i] = p
    return pd.Series(pos, index=c.index)


def qd_three_lines(trend=False):
    def fn(b):
        c, o = b["close"], b["open"]
        m5, m10, m20 = sma(c, 5).shift(1), sma(c, 10).shift(1), sma(c, 20).shift(1)
        g = ((c - o) / o >= 0.02) & (o <= np.minimum(np.minimum(m5, m10), m20)) & (c >= np.maximum(np.maximum(m5, m10), m20))
        x = c < sma(c, 20)
        if trend:
            m60 = sma(c, 60); tf = (c > m60) & (m60 > m60.shift(5))
            g = g & tf; x = x | ~tf
        return durum(g, x)
    return fn


def qd_resonance(b):
    c = b["close"].values
    _, _, hist = talib.MACD(c, 12, 26, 9)
    r = talib.RSI(c, 14); adx = talib.ADX(b["high"].values, b["low"].values, c, 14)
    return pd.Series(((hist > 0) & (r > 50) & (r < 75) & (adx > 20)).astype(float), index=b.index)


def supertrend_dir(b, n=10, m=3.0):
    h, l, c = b["high"].values, b["low"].values, b["close"].values
    a = talib.ATR(h, l, c, n); hl2 = (h + l) / 2
    ub, lb = hl2 + m * a, hl2 - m * a
    fu, fl = ub.copy(), lb.copy(); d = np.ones(len(c))
    for i in range(1, len(c)):
        if np.isnan(fu[i - 1]) or np.isnan(fl[i - 1]):
            continue
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        d[i] = 1 if c[i] > fu[i - 1] else (-1 if c[i] < fl[i - 1] else d[i - 1])
    d[np.isnan(a)] = 0
    return pd.Series(d, index=b.index)


def qd_supertrend(b):
    return (supertrend_dir(b) > 0).astype(float)


def aqt_ma_stack(b):
    c = b["close"]; m5, m10, m30 = sma(c, 5), sma(c, 10), sma(c, 30)
    return durum((m5 > m10) & (m10 > m30) & (c > 1.02 * m5), (m5 < m10) & (m10 < m30) & (c < 0.98 * m5))


def aqt_template(b):
    c = b["close"]; m5 = sma(c, 5)
    return durum(c > 1.01 * m5, c < m5)


def okt_bb(b):
    c = b["close"]; mu, sd = sma(c, 20), c.rolling(20).std(); half = 2 * sd
    note = np.where(c > mu + half, 1.0, np.where(c < mu - half, -1.0, np.sign(c - mu) * ((c - mu) / half) ** 2))
    note = pd.Series(note, index=c.index)
    return durum(note < -0.25, note > 0.25)


def okt_ema_mom(b):
    c = b["close"]; e = ema(c, 21)
    return durum(c <= 0.98 * e, c >= 1.02 * e)


def okt_ema_div(b):
    c = b["close"]; diff = c / ema(c, 50) * 100 - 100
    return durum(diff <= 2, diff > 2)


def okt_stochrsi(b):
    fk, fd = talib.STOCHRSI(b["close"].values, 14, 14, 3, 3)
    s = pd.Series(fk, index=b.index)
    return durum(s <= 1, s >= 98)


def okt_rsi_ma(extreme=True):
    def fn(b):
        r = rsi(b["close"], 14)
        m = r.ewm(alpha=1 / 9, adjust=False).mean()  # SMMA 9
        lo, hi = (39.57, 67.45) if extreme else (48.62, 53.63)
        return durum(cross_up(m, pd.Series(lo, index=m.index)), cross_dn(m, pd.Series(hi, index=m.index)))
    return fn


def qd_btc_hedge(b):
    """Sürekli 1 long + SMA50 altında 1 short (hedge) = net: SMA50 üstünde long, altında düz."""
    return (b["close"] >= sma(b["close"], 50)).astype(float)


# ------------------------------------------------------------ "isl" kuralları
def bt_bracket(b):
    c = b["close"]
    return kw(b, cross_up(sma(c, 5), sma(c, 15)), sl_pct=0.02, tp_pct=0.02)


def bt_stop2(b):
    c = b["close"]
    return kw(b, cross_up(ema(c, 10), ema(c, 20)), sl_pct=0.02)


def bt_macd_tharp(b):
    c = b["close"]; m, s, _ = talib.MACD(c.values, 12, 26, 9)
    m, s = pd.Series(m, index=c.index), pd.Series(s, index=c.index)
    s30 = sma(c, 30)
    a = atr(b, 14)
    return kw(b, cross_up(m, s) & (s30 < s30.shift(10)), sl_abs=3 * a, trail=a, trail_k=3.0)


def bt_btfd(b):
    return kw(b, b["low"] / b["high"] - 1 <= -0.01, max_bars=2)


def bt_pinkfish(b):
    return kw(b, b["high"] >= b["high"].rolling(20).max(), max_bars=2)


def bt_weekday(b):
    wd = pd.Series(b.index.dayofweek, index=b.index)
    return kw(b, wd.isin([1, 3, 4]), sl_pct=0.03, tp_pct=0.03, max_bars=7)


def btpy_trail(b):
    c = b["close"]
    return kw(b, cross_up(sma(c, 10), sma(c, 25)), sl_abs=2 * atr(b, 100), trail=atr(b, 100), trail_k=2.0)


def btpy_mtf_rsi(b):
    c = b["close"]
    dr = rsi(c, 30); w = O.D.resample(b, "W-FRI") if False else b.resample("W-FRI").agg({"close": "last"})
    wr = rsi(w["close"], 30).reindex(c.index, method="ffill").shift(7)  # haftalık değer hafta kapanınca
    m10, m20, m50, m100 = sma(c, 10), sma(c, 20), sma(c, 50), sma(c, 100)
    g = (dr > 70) & (wr > 70) & (wr > dr) & (m10 > m20) & (m20 > m50) & (m50 > m100) & (c > m10)
    return kw(b, g, sl_pct=0.08, cikis=c < 0.98 * m10)


def qd_turtle(b):
    c = b["close"]
    return kw(b, c > b["high"].rolling(20).max().shift(1), sl_abs=2 * atr(b, 14), cikis=c < b["low"].rolling(10).min().shift(1))


def qd_macd_kdj(b):
    c = b["close"].values
    _, _, hist = talib.MACD(c, 12, 26, 9)
    k, d = talib.STOCH(b["high"].values, b["low"].values, c, 9, 3, 0, 3, 0)
    H, K, Dd = (pd.Series(x, index=b.index) for x in (hist, k, d))
    g = (H > 0) & (cross_up(H, pd.Series(0.0, index=b.index)) | cross_up(K, Dd)) & (K < 85)
    x = (H <= 0) | cross_dn(K, Dd)
    return kw(b, g, sl_pct=0.02, cikis=x, trail=b["close"] * 0.01, trail_k=1.0, trail_start_pct=0.05)


def okt_rsi_script(b):
    return kw(b, rsi(b["close"], 10) < 28, sl_pct=0.15, tp_pct=0.25)


def aqt_trend_judge(b):
    c = b["close"].values; n = len(c); st = np.zeros(n, dtype=bool)
    for i in range(200, n):
        if abs(c[i] / c[i - 5:i + 1].mean() - 1) > 0.05:
            st[i] = c[i - 19:i + 1].mean() > c[i - 39:i - 19].mean()
        else:
            st[i] = c[i - 99:i + 1].mean() > c[i - 199:i - 99].mean()
    st = pd.Series(st, index=b.index); m100 = sma(b["close"], 100)
    return kw(b, st & (b["close"] > m100), sl_pct=0.05, cikis=~st)


def aqt_minervini(b):
    c = b["close"]; m50, m150, m200 = sma(c, 50), sma(c, 150), sma(c, 200)
    lo, hi = c.rolling(365).min(), c.rolling(365).max()
    rps = c.pct_change(120).rank(pct=True)  # tek coin için anlamsız: kesitsel RPS aşağıda agr sürümünde
    g = (c > m150) & (c > m200) & (m150 > m200) & (m200 > m200.shift(30)) & (m50 > m150) & (m50 > m200) & (c > m50) & (c >= 1.3 * lo) & (c >= 0.75 * hi)
    return kw(b, g, sl_pct=0.10)


def btb_momentum(b):
    c = b["close"]; f, s = ema(c, 9), ema(c, 21)
    g = (f.shift(1) <= s.shift(1)) & (f > s * 1.005) & (c > sma(c, 200)) & (c <= 1.4 * sma(c, 50))
    return kw(b, g, sl_pct=0.05, trail=c * 0.05, trail_k=1.0, cikis=cross_dn(f, s))


# ------------------------------------------------------------ bot döngüleri (1h; mum içinde önce düşüş, sonra yükseliş)
# Muhasebe: nakit + elde tutulan adet x kapanış = öz sermaye (dilim başına 1); bar getirisi = öz sermaye farkı.
def _seri(b, eq, trs):
    pnl = pd.Series(eq, index=b.index).diff().fillna(0.0)
    tr = pd.Series([x[1] for x in trs], index=pd.DatetimeIndex([x[0] for x in trs])) if trs else pd.Series(dtype=float)
    return pnl, tr


def bot_trailing_trade(b, sl=0.97, arm=1.05, trail=0.98, grid2=0.97, cooldown=1):
    """binance-trading-bot Trailing Trade örnek ayarı: ilk alım 15$, ort. maliyetin %3 altında 30$ daha (en çok 45$),
    stop ort. maliyet x0.97, +%5'te iz süren satış devreye girer, tepeden %2 geri çekilmede satar; kayıptan sonra 1 saat bekler.
    Nominal: 45$ = dilim sermayesi 1."""
    o, h, l, c = (b[k].values for k in ("open", "high", "low", "close"))
    n = len(c); eq = np.zeros(n); trs = []; cash = 0.0; q = 0.0; cq = 0.0; armed = False; peak = 0.0; wait = 0; n2 = False
    for i in range(1, n):
        if q == 0 and wait > 0:
            wait -= 1
        elif q == 0:
            sz = 15 / 45; q = sz / o[i]; cash -= sz * (1 + O.COST); cq = sz * (1 + O.COST); armed = False; peak = 0.0; n2 = False
        if q > 0:
            avg = cq / q
            if not n2 and l[i] <= avg * grid2:
                px = min(o[i], avg * grid2); sz = 30 / 45
                q += sz / px; cash -= sz * (1 + O.COST); cq += sz * (1 + O.COST); n2 = True; avg = cq / q
                filled = True
            else:
                filled = False
            ex = None
            if filled:
                pass  # muhafazakâr: dolum mumunda çıkış yok (mum içi sıra bilinmiyor)
            elif l[i] <= avg * sl: ex = min(o[i], avg * sl)
            elif armed and l[i] <= peak * trail: ex = min(o[i], peak * trail)
            if ex is not None:
                v = q * ex * (1 - O.COST); cash += v; trs.append((b.index[i], v - cq))
                if v < cq: wait = cooldown
                q = 0.0; cq = 0.0
            else:
                if h[i] >= avg * arm: armed = True
                if armed: peak = max(peak, h[i])
        eq[i] = cash + q * c[i]
    return _seri(b, eq, trs)


def bot_martingale(b, base=0.8, safety=1.0, dev=0.012, step=1.4, vol=1.6, layers=5, tp=0.005, stop=0.12):
    """QuantDinger martingale (long): ilk emir 0.8, ilk güvenlik emri -%1.2'de 1.0; aralık x1.4, hacim x1.6, en çok 5 kat;
    ort. maliyetin %0.5 üstünde kâr al, %12 altında stop; sonra yeniden başlar (orijinal stop sonrası durur)."""
    sizes = [base] + [safety * vol ** k for k in range(layers)]
    devs = [0.0] + [dev * sum(step ** j for j in range(k + 1)) for k in range(layers)]
    tot = sum(sizes)
    o, h, l, c = (b[k].values for k in ("open", "high", "low", "close"))
    n = len(c); eq = np.zeros(n); trs = []; cash = 0.0; q = 0.0; cq = 0.0; lvl = 0; p0 = 0.0
    for i in range(1, n):
        if q == 0:
            p0 = o[i]; sz = sizes[0] / tot; q = sz / p0; cash -= sz * (1 + O.COST); cq = sz * (1 + O.COST); lvl = 1
        filled = False
        while lvl < len(sizes) and l[i] <= p0 * (1 - devs[lvl]):
            px = min(o[i], p0 * (1 - devs[lvl])); sz = sizes[lvl] / tot
            q += sz / px; cash -= sz * (1 + O.COST); cq += sz * (1 + O.COST); lvl += 1; filled = True
        avg = cq / q; ex = None
        if l[i] <= avg * (1 - stop): ex = min(o[i], avg * (1 - stop))
        elif not filled and h[i] >= avg * (1 + tp): ex = max(o[i], avg * (1 + tp))  # dolum mumunda kâr alma yok
        if ex is not None:
            v = q * ex * (1 - O.COST); cash += v; trs.append((b.index[i], v - cq)); q = 0.0; cq = 0.0
        eq[i] = cash + q * c[i]
    return _seri(b, eq, trs)


def bot_dca(b, every=24, max_orders=5, tp=0.006, cb=0.002, stop=0.12):
    """QuantDinger DCA: 24 saatte bir alım (en çok 5, her biri bütçenin 1/5'i); ort. maliyetin +%0.6'sında iz süren
    kâr al (%0.2 geri çekilme), ort. maliyetin %12 altında stop; sonra yeniden başlar."""
    o, h, l, c = (b[k].values for k in ("open", "high", "low", "close"))
    n = len(c); eq = np.zeros(n); trs = []; cash = 0.0; q = 0.0; cq = 0.0; k = 0; t0 = 0; peak = 0.0
    for i in range(1, n):
        if q == 0 or (k < max_orders and i - t0 >= every):
            sz = 1 / max_orders; q += sz / o[i]; cash -= sz * (1 + O.COST); cq += sz * (1 + O.COST); k += 1; t0 = i
        avg = cq / q; ex = None
        if l[i] <= avg * (1 - stop): ex = min(o[i], avg * (1 - stop))
        elif peak and l[i] <= peak * (1 - cb): ex = min(o[i], peak * (1 - cb))  # tepe önceki mumlardan
        if ex is not None:
            v = q * ex * (1 - O.COST); cash += v; trs.append((b.index[i], v - cq)); q = 0.0; cq = 0.0; k = 0; peak = 0.0
        elif h[i] >= avg * (1 + tp):
            peak = max(peak, h[i])
        eq[i] = cash + q * c[i]
    return _seri(b, eq, trs)


def bot_smart_dca(b):
    """OctoBot Smart DCA (4h): kapanış <= EMA9 iken -%0.2, -%0.7, -%1.2'de limit alım (her biri 1/3);
    ort. maliyetin +%0.35'inde kâr al; stop yok."""
    o, h, l, c = (b[k].values for k in ("open", "high", "low", "close"))
    e = ema(b["close"], 9).values
    n = len(c); eq = np.zeros(n); trs = []; cash = 0.0; q = 0.0; cq = 0.0; lv = []
    for i in range(1, n):
        if q == 0 and not lv and c[i - 1] <= e[i - 1]:
            ref = c[i - 1]; lv = [ref * (1 - 0.002), ref * (1 - 0.007), ref * (1 - 0.012)]
        rem = []; filled = False
        for px in lv:
            if l[i] <= px:
                fp = min(o[i], px); q += (1 / 3) / fp; cash -= (1 / 3) * (1 + O.COST); cq += (1 / 3) * (1 + O.COST); filled = True
            else:
                rem.append(px)
        lv = rem
        if q > 0 and not filled and h[i] >= cq / q * 1.0035:  # dolum mumunda kâr alma yok
            ex = max(o[i], cq / q * 1.0035); v = q * ex * (1 - O.COST); cash += v
            trs.append((b.index[i], v - cq)); q = 0.0; cq = 0.0; lv = []
        eq[i] = cash + q * c[i]
    return _seri(b, eq, trs)


def bot_grid(b, inc=0.005, levels=20):
    """OctoBot Grid varsayılanı: başlangıç fiyatının altında %0.5 aralıklı 20 alım basamağı; dolan her alım bir üst
    basamakta satılır. Elde coin yokken fiyat merkezden %10 uzaklaşırsa ızgara yeni fiyata taşınır."""
    o, h, l, c = (b[k].values for k in ("open", "high", "low", "close"))
    n = len(c); eq = np.zeros(n); trs = []; cash = 0.0; unit = 1 / levels; center = o[1]; held = {}
    for i in range(1, n):
        new = set()
        for k in range(1, levels + 1):
            px = center * (1 - inc) ** k
            if k not in held and l[i] <= px <= o[i]:
                held[k] = (px, unit / px); cash -= unit * (1 + O.COST); new.add(k)
        for k in list(held):
            if k in new:
                continue  # muhafazakâr: dolum mumunda satış yok
            px, qk = held[k]; sp = px * (1 + inc)
            if h[i] >= sp:
                v = qk * sp * (1 - O.COST); cash += v; trs.append((b.index[i], v - unit * (1 + O.COST))); del held[k]
        if not held and abs(c[i] / center - 1) > 0.10:
            center = c[i]
        eq[i] = cash + sum(qk for _, qk in held.values()) * c[i]
    return _seri(b, eq, trs)


def bot_dca_simple(b):
    """OctoBot Simple DCA: haftada bir eşit tutar alım, hiç satış yok. Toplam yatırım = dilim sermayesi 1."""
    c = b["close"].values; wk = (np.arange(len(c)) % (24 * 7)) == 0; nb = max(wk.sum(), 1); unit = 1 / nb
    q = np.cumsum(np.where(wk, unit / c, 0.0)); cash = -np.cumsum(np.where(wk, unit * (1 + O.COST), 0.0))
    return _seri(b, cash + q * c, [])


def bot_degerlendir(fn, bars):
    cols, trs = {}, []
    for s, b in bars.items():
        p, tr = fn(b); cols[s] = p
        if len(tr): trs.append(tr)
    P = pd.DataFrame(cols)
    avail = pd.DataFrame({s: bars[s]["close"].notna() for s in bars}).reindex(P.index).fillna(False)
    port = (P.fillna(0).sum(axis=1) / avail.sum(axis=1).replace(0, np.nan)).fillna(0.0)
    tr = pd.concat(trs).sort_index() if trs else pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    if tr.index.tz is None:
        tr.index = tr.index.tz_localize("UTC")
    return port.resample("1D").sum(), tr


# ------------------------------------------------------------ "agr" kuralları (kesitsel)
def _rebal(idx, freq):
    if freq == "W-MON":
        return idx.dayofweek == 0
    if freq == "M":
        return idx.is_month_start
    return np.ones(len(idx), dtype=bool)


def topn_agr(score, n, freq, pos_only=False, filt=None):
    W = pd.DataFrame(0.0, index=score.index, columns=score.columns)
    rb = _rebal(score.index, freq)
    for i in np.where(rb)[0]:
        s = score.iloc[i].dropna()
        if filt is not None:
            s = s[filt.iloc[i].reindex(s.index).fillna(False)]
        if pos_only:
            s = s[s > 0]
        if len(s) == 0:
            W.iloc[i] = 0.0; continue
        top = s.sort_values(ascending=False).index[:n]
        W.iloc[i] = 0.0; W.loc[W.index[i], top] = min(1.0 / len(top), 1.0 / n if n else 1)
    W[~rb] = np.nan
    return W.ffill().fillna(0.0)


def qd_mom_top(C):
    return topn_agr(C.pct_change(60), 4, "W-MON", pos_only=True)


def qd_lowvol(C):
    return topn_agr(-C.pct_change().rolling(60).std(), 4, "W-MON")


def qd_mom20(C):
    return topn_agr(C.pct_change(20), 5, "W-MON")


def aqt_eq(C):
    W = C.notna().astype(float); W = W.div(W.sum(axis=1), axis=0); W[~C.index.is_month_start] = np.nan; return W.ffill().fillna(0.0)


def aqt_invvol(C):
    v = 1 / C.pct_change().rolling(60).std()
    W = v.div(v.sum(axis=1), axis=0); W[~C.index.is_month_start] = np.nan
    return W.ffill().fillna(0.0)


def aqt_mom_rotation(C):
    """ai_quant_trade momentum rotation: skor 0.5R20+0.3R60+0.2R120-0.5std20; kapanış >= SMA20 ve SMA60;
    BTC >= SMA60 değilse nakit; aylık, eşit ağırlık top 5 (25 coin için top_n 10 yerine); %15 iz süren stop."""
    R = C.pct_change()
    sc = 0.5 * C.pct_change(20) + 0.3 * C.pct_change(60) + 0.2 * C.pct_change(120) - 0.5 * R.rolling(20).std()
    ok = (C >= C.rolling(20).mean()) & (C >= C.rolling(60).mean())
    mk = C["BTCUSDT"] >= C["BTCUSDT"].rolling(60).mean() if "BTCUSDT" in C else pd.Series(True, index=C.index)
    W = topn_agr(sc, 5, "M", filt=ok)
    W[~mk.reindex(W.index).fillna(False).values] = 0.0
    # iz süren stop: tutuş içinde tepeden %15 düşen coin dönem sonuna kadar sıfırlanır
    hw = None
    out = W.copy()
    for s in W.columns:
        w = W[s].values; px = C[s].values; peak = np.nan; stop = False
        for i in range(len(w)):
            if w[i] == 0:
                peak = np.nan; stop = False; continue
            if i > 0 and w[i - 1] == 0:
                peak = px[i]; stop = False
            if not stop:
                peak = np.nanmax([peak, px[i]])
                if px[i] <= peak * 0.85: stop = True
            if stop: out.iloc[i, out.columns.get_loc(s)] = 0.0
    return out


def btb_rebal_fixed(C, tw={"BTCUSDT": 0.5, "ETHUSDT": 0.3, "SOLUSDT": 0.2}, drift=0.05):
    """binance-trading-bot Rebalance (sabit, 4h): BTC 0.5 ETH 0.3 SOL 0.2; pay hedeften 5 puan saparsa düzelt."""
    cols = [k for k in tw if k in C]
    X = C[cols]; W = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    w = None
    for i in range(len(X)):
        row = X.iloc[i]
        if row.isna().any():
            continue
        if w is None:
            w = pd.Series(tw)[cols]
        else:
            r = row / X.iloc[i - 1]; v = w * r; v = v / v.sum()
            w = pd.Series(tw)[cols] if (v - pd.Series(tw)[cols]).abs().max() > drift else v
        W.iloc[i, [W.columns.get_loc(k) for k in cols]] = w.values
    return W


def btb_rebal_mom(C):
    """binance-trading-bot Rebalance momentum modu: son 30 mumun getirisine göre top 3 eşit ağırlık (her mum)."""
    return topn_agr(C.pct_change(30), 3, "all")


def okt_index(C, coins=("BTCUSDT", "ETHUSDT", "SOLUSDT"), drift=0.05):
    return btb_rebal_fixed(C, {k: 1 / 3 for k in coins}, drift)


# ------------------------------------------------------------ backtesting.py makine öğrenmesi örneği (P8, ileri yürüyen kNN)
def btpy_knn(b, n_train=400, retrain=20, k=7, horizon=48, thr=0.004):
    """Özellikler: (kapanış - SMA10/20/50/100)/kapanış, SMA farkları, 2 mum momentum, BB(20,2) üst/alt/genişlik,
    haftanın günü, saat. Etiket: 48 mum sonrası getiri > %0.4 -> +1, < -%0.4 -> -1, değilse 0. kNN(7), son 400 mumla
    her 20 mumda yeniden eğitim (dürüst sürüm: son 48 mumun etiketi henüz bilinmediği için eğitime alınmaz).
    Tahmin +1 -> long, -1 -> short; ±%0.4 hedef/stop; 48 mumda kapat (orijinal: 2 günden eski işlemde stop sıkılaştırılır)."""
    from sklearn.neighbors import KNeighborsClassifier
    c = b["close"]; hlc3 = (b["high"] + b["low"] + c) / 3
    s10, s20, s50, s100 = (sma(c, n) for n in (10, 20, 50, 100))
    mu, sd = sma(hlc3, 20), hlc3.rolling(20).std()
    X = pd.DataFrame({"x1": (c - s10) / c, "x2": (c - s20) / c, "x3": (c - s50) / c, "x4": (c - s100) / c,
                      "d1": (s10 - s20) / c, "d2": (s20 - s50) / c, "d3": (s50 - s100) / c, "m": c.pct_change(2),
                      "bu": (mu + 2 * sd - c) / c, "bl": (c - (mu - 2 * sd)) / c, "bw": 4 * sd / c,
                      "dow": b.index.dayofweek, "hr": b.index.hour}, index=b.index)
    fr = c.shift(-horizon) / c - 1
    y = np.where(fr > thr, 1, np.where(fr < -thr, -1, 0))
    Xv = X.values; ok = ~np.isnan(Xv).any(axis=1)
    pred = np.zeros(len(c))
    start = 100 + n_train + horizon
    for j in range(start, len(c), retrain):
        lo, hi = j - horizon - n_train, j - horizon
        m = ok[lo:hi]
        if m.sum() < 100: continue
        clf = KNeighborsClassifier(k).fit(Xv[lo:hi][m], y[lo:hi][m])
        seg = slice(j, min(j + retrain, len(c)))
        mm = ok[seg]
        p = np.zeros(mm.shape[0])
        if mm.any():
            p[mm] = clf.predict(Xv[seg][mm])
        pred[seg] = p
    pr = pd.Series(pred, index=b.index)
    return kw(b, pr > 0, short=pr < 0, sl_pct=thr, tp_pct=thr, max_bars=horizon)
