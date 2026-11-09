"""BTC Flip Bot V1 (XGqSzuxJ): 1s grafik; günlük (EMA50) ve 4s RSI süzgeçli, MACD + engulfing + hacim patlaması + yüksek ATR girişi; stop = mum deseni (azami %2.5), ters sinyalde çıkış; SL sonrası aynı yönde 24s bekleme, 1s sonra ters yönde 'flip' girişi (swing stop, %1.5 tavan, 24s zaman stopu). Kısmi kâr (6R'de %15) ve DD durdurma modellenmedi."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "BTC Flip Bot V1"; PINE_ID = "XGqSzuxJ"
PARAM = dict(rsi_l=45, rsi_s=55, atr_ma=50, vol_len=20, vol_k=1.5, sl_max=2.5, sl_buf=0.1, ayni_bekle=24, genel_bekle=2, flip_bekle=1, flip_cap=1.5, flip_lb=10, flip_zaman=24)
TF = "1h"; EVREN = ["kripto"]
NEDEN = "Betik 1s için (başlık: BTC, 1H); kripto saatlik."
@njit(cache=True)
def _sim(ls, ss, stL, stS, hi, lo, cl, sl_max, ayni, genel, fbek, fcap, flb, fzam, buf):
    n = len(cl); sig = np.zeros(n); slv = np.full(n, np.nan); xl = np.zeros(n, np.bool_); xs = np.zeros(n, np.bool_)
    pos = 0; stp = np.nan; flipp = False; febar = -1; lastL = -10**9; lastS = -10**9; lastX = -10**9
    pend = 0; pbar = -1; pref = np.nan
    for i in range(1, n):
        was = pos
        # mevcut pozisyonun stop'u (bu barın içinde)
        if pos > 0 and lo[i] <= stp:
            pos = 0; hit = 1
        elif pos < 0 and hi[i] >= stp:
            pos = 0; hit = -1
        else: hit = 0
        if was != 0 and pos == 0:
            lastX = i
            if hit > 0:
                lastL = i
                if not flipp: pend = -1; pbar = i; pref = stp
            elif hit < 0:
                lastS = i
                if not flipp: pend = 1; pbar = i; pref = stp
            flipp = False
        if pos != 0 and flipp and febar >= 0 and i - febar >= fzam:
            if pos > 0: xl[i] = True
            else: xs[i] = True
            pos = 0; flipp = False; lastX = i
        # ters sinyalle çıkış (kapanış)
        if pos > 0 and ss[i]: xl[i] = True; pos = 0; lastX = i; flipp = False
        elif pos < 0 and ls[i]: xs[i] = True; pos = 0; lastX = i; flipp = False
        exb = (i - lastX) < genel
        if pos == 0 and pend != 0 and (i - pbar) >= fbek and not exb:
            if pend == -1:
                sw = np.max(hi[max(0, i-int(flb)):i+1]) * (1 + buf/100.0); cap = pref * (1 + fcap/100.0); fs = min(sw, cap)
                if fs - cl[i] > 0: sig[i] = -1.0; slv[i] = fs; pos = -1; stp = fs; flipp = True; febar = i
            else:
                sw = np.min(lo[max(0, i-int(flb)):i+1]) * (1 - buf/100.0); cap = pref * (1 - fcap/100.0); fs = max(sw, cap)
                if cl[i] - fs > 0: sig[i] = 1.0; slv[i] = fs; pos = 1; stp = fs; flipp = True; febar = i
            pend = 0
        elif pos == 0 and pend == 0:
            if ls[i] and (i - lastL) >= ayni and not exb and (cl[i] - stL[i]) > 0:
                sig[i] = 1.0; slv[i] = stL[i]; pos = 1; stp = stL[i]; flipp = False
            elif ss[i] and (i - lastS) >= ayni and not exb and (stS[i] - cl[i]) > 0:
                sig[i] = -1.0; slv[i] = stS[i]; pos = -1; stp = stS[i]; flipp = False
    return sig, slv, xl, xs
def sinyal(df, rsi_l, rsi_s, atr_ma, vol_len, vol_k, sl_max, sl_buf, ayni_bekle, genel_bekle, flip_bekle, flip_cap, flip_lb, flip_zaman):
    o, h, l, c, v = df.o.values, df.h.values, df.l.values, df.c.values, df.v.values
    dc = gost.htf(df, "1D", lambda d: gost.sh(d.c.values, 1)); de = gost.htf(df, "1D", lambda d: gost.sh(gost.ema(d.c.values, 50), 1))
    r4 = gost.htf(df, "4h", lambda d: gost.sh(gost.rsi(d.c.values, 14), 1))
    r1 = gost.rsi(c, 14); m = gost.ema(c, 12) - gost.ema(c, 26); sg = gost.ema(m, 9); a = gost.atr(h, l, c, 14)
    hv = a > gost.sma(a, int(atr_ma)); vk = v > vol_k*gost.sma(v, int(vol_len))
    body = np.abs(c-o); pb = gost.sh(body); po, pc = gost.sh(o), gost.sh(c)
    with np.errstate(invalid="ignore"):
        be = (pc < po) & (c > o) & (c >= po) & (o <= pc) & (body > pb)
        se_ = (pc > po) & (c < o) & (o >= pc) & (c <= po) & (body > pb)
        lsig = (r1 > rsi_l) & (m > sg) & be & hv & vk & (dc > de) & (r4 > 50)
        ssig = (r1 < rsi_s) & (m < sg) & se_ & hv & vk & (dc < de) & (r4 < 50)
    stL = np.maximum(np.minimum(l, gost.sh(l))*(1 - sl_buf/100), c*(1 - sl_max/100)); stS = np.minimum(np.maximum(h, gost.sh(h))*(1 + sl_buf/100), c*(1 + sl_max/100))
    sig, slv, xl, xs = _sim(np.nan_to_num(lsig.astype(float)) > 0, np.nan_to_num(ssig.astype(float)) > 0, np.nan_to_num(stL, nan=0.0), np.nan_to_num(stS, nan=1e18), h, l, c,
        sl_max, int(ayni_bekle), int(genel_bekle), int(flip_bekle), flip_cap, int(flip_lb), int(flip_zaman), sl_buf)
    return dict(sig=sig, sl=slv, xl=xl, xs=xs, poc=True)
