"""Strateji sinyal üreticileri. Her fonksiyon (f, p) -> simulate() argümanları döner.

Ortak çerçeve: 1D/4H yön filtresi + 1H giriş tetikleyicisi.
"""
import numpy as np
import pandas as pd
from numba import njit


def htf_direction(f, mode):
    """+1 / -1 / 0 yön. Üst zaman dilimi trend filtresi (Pruitt / Ratford: 'bir gösterge trendi doğrular')."""
    d1_up = f["d1_close"] > f["d1_ema50"]
    d1_dn = f["d1_close"] < f["d1_ema50"]
    if mode == "d1_200":
        d1_up = f["d1_close"] > f["d1_ema200"]; d1_dn = f["d1_close"] < f["d1_ema200"]
    if mode == "d1_50_200":
        d1_up = (f["d1_close"] > f["d1_ema50"]) & (f["d1_ema50"] > f["d1_ema200"])
        d1_dn = (f["d1_close"] < f["d1_ema50"]) & (f["d1_ema50"] < f["d1_ema200"])
    h4_up = (f["h4_ema20"] > f["h4_ema50"]) & (f["h4_close"] > f["h4_ema50"])
    h4_dn = (f["h4_ema20"] < f["h4_ema50"]) & (f["h4_close"] < f["h4_ema50"])
    up = d1_up & h4_up
    dn = d1_dn & h4_dn
    return np.where(up, 1, np.where(dn, -1, 0))


def _risk_kw(p):
    """Davey risk koruma / Pruitt LTLF parametreleri (simulate'e aynen geçer)."""
    return dict(loss_delay=p.get("loss_delay", 0), skip_after_win=p.get("skip_after_win", False))


def breakout_state(f, win, n=20, vol_min=0.0):
    """Son `win` saat içindeki en son 4H Donchian(n) kırılımının yönü (+1/-1, yoksa 0)."""
    up = f["h4_close"] > f[f"h4_dcp_hi{n}"]
    dn = f["h4_close"] < f[f"h4_dcp_lo{n}"]
    if vol_min:
        v = f["h4_vol_ratio"] > vol_min
        up &= v; dn &= v
    up_ev = up & ~up.shift(1, fill_value=False)
    dn_ev = dn & ~dn.shift(1, fill_value=False)
    ev = pd.Series(np.where(up_ev, 1.0, np.where(dn_ev, -1.0, np.nan)), index=f.index)
    last = ev.ffill()
    t = pd.Series(np.where(ev.notna(), np.arange(len(f)), np.nan), index=f.index).ffill()
    age = np.arange(len(f)) - t
    return np.where((age <= win) & last.notna(), last.fillna(0), 0).astype(int)


# ================================================================
# NOT: s1, s2, s3 araştırma aşamasında test edilip ELENDİ (bkz. STRATEJILER.md §1).
# Sonuçların yeniden üretilebilmesi için tutuluyor; nihai sistemde kullanılmıyor.
# ================================================================

# ---------------------------------------------------------------- S1
def s1_trend_pullback(f, p):
    """Trend yönünde aşırı satım/alım dönüşü (Davey MR #1/#3, Ratford RSI+BB #7, Connors RSI2).

    Long: üst ZD yükseliş + 1H RSI(n) eşik altından geri yukarı keser + son k mumda alt BB'ye temas.
    Çıkış: hedef R veya fiyat orta banda/RSI çıkış seviyesine döner; stop ATR katı.
    """
    dirn = htf_direction(f, p.get("dir_mode", "d1_50"))
    r = f[f"rsi{p['rsi_n']}"]
    lo_th, hi_th = p["rsi_lo"], 100 - p["rsi_lo"]
    bb = p.get("bb", "bb20_2.0")
    k = p.get("touch_k", 3)
    touch_lo = (f["low"] <= f[f"{bb}_lo"]).rolling(k).max().astype(bool)
    touch_hi = (f["high"] >= f[f"{bb}_up"]).rolling(k).max().astype(bool)
    cross_up = (r.shift(1) < lo_th) & (r >= lo_th)
    cross_dn = (r.shift(1) > hi_th) & (r <= hi_th)
    if p.get("trigger", "cross") == "level":
        cross_up = r < lo_th; cross_dn = r > hi_th
    long = (dirn == 1) & cross_up & (touch_lo if p.get("need_touch", True) else True)
    short = (dirn == -1) & cross_dn & (touch_hi if p.get("need_touch", True) else True)
    if p.get("adx_max"):
        long &= f["adx14"] < p["adx_max"]; short &= f["adx14"] < p["adx_max"]
    side = np.where(long, 1, np.where(short, -1, 0))
    if p.get("long_only"):
        side = np.where(side > 0, 1, 0)
    sl = p["sl_atr"] * f["atr14"]
    if p.get("sl_swing"):
        swing_lo = f["low"].rolling(p["sl_swing"]).min()
        swing_hi = f["high"].rolling(p["sl_swing"]).max()
        sl_l = (f["close"] - swing_lo) + 0.2 * f["atr14"]
        sl_s = (swing_hi - f["close"]) + 0.2 * f["atr14"]
        sl = np.where(side > 0, sl_l, sl_s)
        sl = np.clip(sl, 0.5 * f["atr14"], 4 * f["atr14"])
    exl = exs = None
    if p.get("exit_mid"):
        exl = (f["close"] >= f[f"{bb}_mid"]) if p["exit_mid"] == "mid" else (f["close"] >= f[f"{bb}_up"])
        exs = (f["close"] <= f[f"{bb}_mid"]) if p["exit_mid"] == "mid" else (f["close"] <= f[f"{bb}_lo"])
    if p.get("exit_rsi"):
        exl = r > p["exit_rsi"]; exs = r < 100 - p["exit_rsi"]
    return dict(side=side, sl_dist=sl, tp1_R=p.get("tp1_R", 1.0), tp1_frac=p.get("tp1_frac", 0.0),
                tp2_R=p.get("tp_R", np.inf), be_R=p.get("be_R", 0.0), exit_long=exl, exit_short=exs,
                max_bars=p.get("max_bars", 48), trail_atr=f["atr14"], trail_k=p.get("trail_k", 0.0),
                trail_start_R=p.get("trail_start_R", 1.0))


# ---------------------------------------------------------------- S2
def s2_breakout(f, p):
    """Üst ZD trendi yönünde 1H Donchian kırılımı (Pruitt Turtle/Donchian, Davey breakout, D'errico).

    Kazanma oranını yükseltmek için: 1R'de kısmi kâr + başabaş stop (Davey: başabaş stoplar
    stop&reverse kadar iyi), kalan pozisyon ATR iz süren stop ile.
    """
    dirn = htf_direction(f, p.get("dir_mode", "d1_50"))
    n = p["dc_n"]
    hi = f[f"dc_hi{n}"].shift(1); lo = f[f"dc_lo{n}"].shift(1)
    long = (dirn == 1) & (f["close"] > hi) & (f["close"].shift(1) <= hi.shift(1))
    short = (dirn == -1) & (f["close"] < lo) & (f["close"].shift(1) >= lo.shift(1))
    if p.get("adx_min"):
        long &= f["h4_adx14"] > p["adx_min"]; short &= f["h4_adx14"] > p["adx_min"]
    if p.get("vol_mult"):
        vok = f["quote_volume"] > p["vol_mult"] * f["vol_sma20"]
        long &= vok; short &= vok
    if p.get("max_ext"):  # aşırı uzamış kırılımları alma
        ext = (f["close"] - f["ema20"]).abs() / f["atr14"]
        long &= ext < p["max_ext"]; short &= ext < p["max_ext"]
    side = np.where(long, 1, np.where(short, -1, 0))
    if p.get("long_only"):
        side = np.where(side > 0, 1, 0)
    sl = p["sl_atr"] * f["atr14"]
    exl = exs = None
    if p.get("exit_dc"):
        m = p["exit_dc"]
        exl = f["close"] < f[f"dc_lo{m}"].shift(1); exs = f["close"] > f[f"dc_hi{m}"].shift(1)
    return dict(side=side, sl_dist=sl, tp1_R=p.get("tp1_R", 1.0), tp1_frac=p.get("tp1_frac", 0.0),
                tp2_R=p.get("tp_R", np.inf), be_R=p.get("be_R", 0.0), exit_long=exl, exit_short=exs,
                max_bars=p.get("max_bars", 10**6), trail_atr=f["atr14"], trail_k=p.get("trail_k", 0.0),
                trail_start_R=p.get("trail_start_R", 1.0))


# ---------------------------------------------------------------- S3
@njit(cache=True)
def _swing_leg(high, low, n):
    """Son n mumdaki en yüksek/en düşük ve hangisinin daha yeni olduğu."""
    m = len(high)
    H = np.full(m, np.nan); L = np.full(m, np.nan); up = np.zeros(m)
    for i in range(n - 1, m):
        hi = -1e300; lo = 1e300; ih = 0; il = 0
        for j in range(i - n + 1, i + 1):
            if high[j] >= hi:
                hi = high[j]; ih = j
            if low[j] <= lo:
                lo = low[j]; il = j
        H[i] = hi; L[i] = lo
        up[i] = 1.0 if ih > il else -1.0
    return H, L, up


def s3_measured_move(f, p):
    """Ölçülü hareket / Fibonacci geri çekilme (Halsey; Price Action Algo prim/indirim; Altın Oran).

    Son N saatlik bacak (dip->tepe) yükselişse ve üst ZD trendi yukarıysa, fiyat bacağın %50-61.8
    'indirim' bölgesine geri çekilip 1H'de dönüş verdiğinde long. Stop: %78.6 (61.8 başarısızlık
    seviyesinin ötesi), hedef: tepe (0) veya -%23.6 uzantı. Short simetrik.
    """
    if p.get("brk_win"):
        dirn = breakout_state(f, p["brk_win"], p.get("brk_n", 20), p.get("vol_min", 0))
    else:
        dirn = htf_direction(f, p.get("dir_mode", "d1_50"))
    n = p["leg_n"]
    H, L, up = _swing_leg(f["high"].values, f["low"].values, n)
    H = pd.Series(H, index=f.index).shift(1); L = pd.Series(L, index=f.index).shift(1)
    up = pd.Series(up, index=f.index).shift(1)
    rng = H - L
    c = f["close"]
    min_rng = p.get("min_rng_atr", 4) * f["atr14"]
    z_lo, z_hi = p.get("zone", (0.5, 0.618))
    # yükseliş bacağı: geri çekilme oranı = (H - fiyat)/rng
    retr_l = (H - f["low"]) / rng
    retr_s = (f["high"] - L) / rng
    conf_l = (c > f["open"]) & (f[f"rsi{p.get('rsi_n', 3)}"] > f[f"rsi{p.get('rsi_n', 3)}"].shift(1))
    conf_s = (c < f["open"]) & (f[f"rsi{p.get('rsi_n', 3)}"] < f[f"rsi{p.get('rsi_n', 3)}"].shift(1))
    long = (dirn == 1) & (up == 1) & (rng > min_rng) & (retr_l >= z_lo) & (retr_l <= p.get("max_retr", 0.786)) & conf_l \
        & ((H - c) / rng <= z_hi) & ((H - c) / rng >= p.get("close_min", 0.3))
    short = (dirn == -1) & (up == -1) & (rng > min_rng) & (retr_s >= z_lo) & (retr_s <= p.get("max_retr", 0.786)) & conf_s \
        & ((c - L) / rng <= z_hi) & ((c - L) / rng >= p.get("close_min", 0.3))
    side = np.where(long, 1, np.where(short, -1, 0))
    if p.get("long_only"):
        side = np.where(side > 0, 1, 0)
    stop_lvl = p.get("stop_lvl", 0.786)
    sl_l = c - (H - stop_lvl * rng) + p.get("sl_buf_atr", 0.2) * f["atr14"]
    sl_s = (L + stop_lvl * rng) - c + p.get("sl_buf_atr", 0.2) * f["atr14"]
    sl = np.where(side > 0, sl_l, np.where(side < 0, sl_s, 0.0))
    sl = np.where(sl < 0.5 * f["atr14"], 0.5 * f["atr14"], sl)
    tgt = p.get("target", 0.0)  # 0 = tepe, -0.236 = uzantı
    tp_l = (H - tgt * rng - c) / sl
    tp_s = (c - (L + tgt * rng)) / sl
    tp = np.where(side > 0, tp_l, np.where(side < 0, tp_s, np.inf))
    tp = np.where(tp > 0.3, tp, 0.3)
    if p.get("tp_cap"):
        tp = np.minimum(tp, p["tp_cap"])
    return dict(side=side, sl_dist=sl, tp1_R=p.get("tp1_R", 1.0), tp1_frac=p.get("tp1_frac", 0.0),
                tp2_R=tp, be_R=p.get("be_R", 0.0), max_bars=p.get("max_bars", 72),
                trail_atr=f["atr14"], trail_k=p.get("trail_k", 0.0), trail_start_R=p.get("trail_start_R", 1.0))


STRATS = {"s1": s1_trend_pullback, "s2": s2_breakout, "s3": s3_measured_move}


# ---------------------------------------------------------------- S4
def s4_stretch_reversion(f, p):
    """Ortalamadan aşırı uzaklaşma dönüşü — Davey'in en iyi MR yöntemi (#4 MA Stretch) ile
    Connors RSI(2) ve Bollinger stretch'in VE (AND) kombinasyonu.

    Yön (1D/4H): fiyat günlük EMA20'nin `d1_k` günlük-ATR altında (veya 4H EMA20'nin `h4_k`
    4H-ATR altında) => yalnızca long beklentisi (kapitülasyon bölgesi).
    Tetik (1H): RSI(n) aşırı satımdan yukarı döner (+ isteğe bağlı alt BB teması).
    Çıkış: fiyat 4H EMA20'ye (ortalama) döner veya hedef/stop/zaman.
    """
    c = f["close"]
    d1_st = (c - f["d1_ema20"]) / f["d1_atr14"]
    h4_st = (c - f["h4_ema20"]) / f["h4_atr14"]
    bias = pd.Series(False, index=f.index)
    if p.get("d1_k") is not None:
        bias |= d1_st < -p["d1_k"]
    if p.get("h4_k") is not None:
        bias |= h4_st < -p["h4_k"]
    if p.get("ret24") is not None:  # (eski) log getiri eşiği — geriye dönük uyumluluk
        bias |= np.log(c / c.shift(24)) < -p["ret24"]
    if p.get("drop24") is not None:  # Davey #5 Percent Decrease: 24 saatte basit % düşüş
        bias |= c / c.shift(24) - 1 < -p["drop24"]
    if p.get("ma_stretch") is not None:  # Davey #4 MA Stretch: fiyat ortalamanın % X altında
        ma = f[p.get("stretch_ma", "d1_ema20")]
        bias |= (ma - c) / ma > p["ma_stretch"]
    bias = bias.rolling(p.get("bias_win", 6)).max().astype(bool)  # bölge son N saatte aktifti
    if p.get("and_rsi") is not None:  # Davey: MR yöntemleri VE ile istiflenince güçlenir (#2 Connors RSI)
        bias &= f["rsi2"] < p["and_rsi"]
    if p.get("and_bb"):  # Davey #3 Bollinger stretch (1H)
        bias &= c < f["bb20_2.0_lo"]
    r = f[f"rsi{p.get('rsi_n', 2)}"]
    th = p.get("rsi_lo", 10)
    tmode = p.get("trigger", "cross")
    if tmode == "none":  # ek 1H tetiği yok: koşulun oluştuğu mumun kapanışında sinyal
        trig = pd.Series(True, index=f.index)
    elif tmode == "cross":
        trig = (r.shift(1) < th) & (r >= th)
    else:
        trig = r < th
    if p.get("need_green"):
        trig &= c > f["open"]
    long = bias & trig
    if p.get("btc_regime"):
        k = p["btc_regime"]
        long &= f["btc_d1_close"] > f[f"btc_d1_ema{k}"]
    if p.get("btc_not_crash"):  # BTC de aynı anda çöküyorsa (sistemik) girme — coin ile aynı (1H) saat
        col = "btc_close" if p.get("btc_1h", True) else "btc_h4_close"
        long &= f[col] / f[col].shift(24) - 1 > -p["btc_not_crash"]
    if p.get("d1_regime"):  # isteğe bağlı: uzun vadeli boğa rejimi
        long &= f["d1_close"] > f["d1_ema200"] if p["d1_regime"] == "200" else f["d1_ema50"] > f["d1_ema200"]
    side = np.where(long, 1, 0)
    sl = p.get("sl_atr", 3.0) * f["atr14"]
    if p.get("sl_h4atr"):
        sl = p["sl_h4atr"] * f["h4_atr14"]
    ex = p.get("exit", "h4_ema20")
    exl = None
    if ex == "h4_ema20":
        exl = c >= f["h4_ema20"]
    elif ex == "ema50":
        exl = c >= f["ema50"]
    elif ex == "bbmid":
        exl = c >= f["bb20_2.0_mid"]
    elif ex == "rsi":
        exl = f["rsi14"] > p.get("exit_rsi", 60)
    elif ex == "d1_ema20":  # Davey #4 çıkışı: fiyat ortalamanın üstüne döner
        exl = c >= f["d1_ema20"]
    return dict(side=side, sl_dist=sl, tp1_R=p.get("tp1_R", 1.0), tp1_frac=p.get("tp1_frac", 0.0),
                tp2_R=p.get("tp_R", np.inf), be_R=p.get("be_R", 0.0), exit_long=exl,
                max_bars=p.get("max_bars", 96), trail_atr=f["atr14"], trail_k=p.get("trail_k", 0.0),
                trail_start_R=p.get("trail_start_R", 1.0), **_risk_kw(p))


# ---------------------------------------------------------------- S5
def s5_momentum(f, p):
    """Güçlü momentum devamı (Pruitt Donchian/Turtle, Davey volatilite kırılımı, Kılınçarslan:
    'piyasalar momentum olduğu müddetçe dinamiktir').

    Yön (1D/4H): 4H kapanış 4H Donchian(20) zirvesini kırdı / günlük fiyat EMA20'nin `d1_k` ATR üstünde
    ve günlük trend yukarı. Tetik (1H): kısa geri çekilme sonrası RSI yeniden yukarı (pullback giriş)
    veya 1H Donchian kırılımı. Çıkış: ATR iz süren stop + kısmi kâr.
    """
    c = f["close"]
    d1_st = (c - f["d1_ema20"]) / f["d1_atr14"]
    h4_st = (c - f["h4_ema20"]) / f["h4_atr14"]
    bias_l = pd.Series(True, index=f.index)
    bias_s = pd.Series(True, index=f.index)
    if p.get("d1_k") is not None:
        bias_l &= d1_st > p["d1_k"]; bias_s &= d1_st < -p["d1_k"]
    if p.get("h4_k") is not None:
        bias_l &= h4_st > p["h4_k"]; bias_s &= h4_st < -p["h4_k"]
    if p.get("ret24_min"):  # 24 saatlik momentum patlaması
        r24 = np.log(c / c.shift(24))
        bias_l &= r24 > p["ret24_min"]; bias_s &= r24 < -p["ret24_min"]
    if p.get("h4_dc"):
        n4 = p.get("h4_dc_n", 20)
        bias_l &= f["h4_close"] > f[f"h4_dcp_hi{n4}"]; bias_s &= f["h4_close"] < f[f"h4_dcp_lo{n4}"]
    if p.get("d1_dc"):
        nd = p.get("d1_dc_n", 20)
        bias_l &= f["d1_close"] > f[f"d1_dcp_hi{nd}"]; bias_s &= f["d1_close"] < f[f"d1_dcp_lo{nd}"]
    if p.get("d1_vol_min"):
        bias_l &= f["d1_vol_ratio"] > p["d1_vol_min"]; bias_s &= f["d1_vol_ratio"] > p["d1_vol_min"]
    if p.get("d1_trend", True):
        bias_l &= f["d1_ema20_slope"] > 0; bias_s &= f["d1_ema20_slope"] < 0
    if p.get("vol_min"):
        bias_l &= f["h4_vol_ratio"] > p["vol_min"]; bias_s &= f["h4_vol_ratio"] > p["vol_min"]
    if p.get("squeeze"):
        sq = f["h4_bbw_rank_prev"] < p["squeeze"]
        bias_l &= sq; bias_s &= sq
    if p.get("max_ext"):
        ext_l = (f["h4_close"] - f[f"h4_dcp_hi{p.get('h4_dc_n', 20)}"]) / f["h4_atr14"]
        ext_s = (f[f"h4_dcp_lo{p.get('h4_dc_n', 20)}"] - f["h4_close"]) / f["h4_atr14"]
        bias_l &= ext_l < p["max_ext"]; bias_s &= ext_s < p["max_ext"]
    if p.get("d1_filter"):
        k = p["d1_filter"]
        bias_l &= f["d1_close"] > f[f"d1_ema{k}"]; bias_s &= f["d1_close"] < f[f"d1_ema{k}"]
    if p.get("btc_filter"):
        k = p["btc_filter"]
        bias_l &= f["btc_d1_close"] > f[f"btc_d1_ema{k}"]; bias_s &= f["btc_d1_close"] < f[f"btc_d1_ema{k}"]
    if p.get("short_btc"):  # short yalnızca BTC günlük ayı rejiminde
        k = p["short_btc"]
        bias_s &= f["btc_d1_close"] < f[f"btc_d1_ema{k}"]
    if p.get("long_btc"):
        k = p["long_btc"]
        bias_l &= f["btc_d1_close"] > f[f"btc_d1_ema{k}"]
    if p.get("adx_min"):
        bias_l &= f["h4_adx14"] > p["adx_min"]; bias_s &= f["h4_adx14"] > p["adx_min"]
    if p.get("entry_ema_side") and p.get("exit_h4ema"):
        # Çelişki giderme: çıkış koşulu girişte zaten doğruysa işlem açma
        e = f[f"h4_ema{p['exit_h4ema']}"]
        bias_l &= f["h4_close"] > e; bias_s &= f["h4_close"] < e
    if p.get("vol_kill"):
        # Davey Risk Koruma #4: kırılım mumu aşırı volatilse (TR > k x ATR) girme
        tr4 = (f["h4_high"] - f["h4_low"]) / f["h4_atr14"]
        bias_l &= tr4 < p["vol_kill"]; bias_s &= tr4 < p["vol_kill"]
    w = p.get("bias_win", 1)
    bias_l0, bias_s0 = bias_l, bias_s
    if w > 1:
        bias_l = bias_l.rolling(w).max().astype(bool); bias_s = bias_s.rolling(w).max().astype(bool)
    trig = p.get("trigger", "dc")
    if trig == "dc":
        n = p.get("dc_n", 24)
        tl = (c > f[f"dc_hi{n}"].shift(1)); ts = (c < f[f"dc_lo{n}"].shift(1))
    elif trig == "pullback":
        r = f[f"rsi{p.get('rsi_n', 3)}"]; th = p.get("rsi_lo", 30)
        tl = (r.shift(1) < th) & (r >= th); ts = (r.shift(1) > 100 - th) & (r <= 100 - th)
    elif trig == "retest":  # 4H kırılım seviyesine 1H geri test + üzerinde kapanış
        n4 = p.get("h4_dc_n", 20)
        ev_l = bias_l0 & ~bias_l0.shift(1, fill_value=False)
        ev_s = bias_s0 & ~bias_s0.shift(1, fill_value=False)
        lvl_l = f[f"h4_dcp_hi{n4}"].where(ev_l).ffill()
        lvl_s = f[f"h4_dcp_lo{n4}"].where(ev_s).ffill()
        tol = p.get("retest_tol", 0.25) * f["h4_atr14"]
        tl = (f["low"] <= lvl_l + tol) & (c > lvl_l) & ~ev_l
        ts = (f["high"] >= lvl_s - tol) & (c < lvl_s) & ~ev_s
        bias_l = bias_l0.rolling(p.get("retest_win", 24)).max().astype(bool)
        bias_s = bias_s0.rolling(p.get("retest_win", 24)).max().astype(bool)
    else:  # 'now' — bias'ın ilk oluştuğu mum
        tl = bias_l & ~bias_l.shift(1, fill_value=False); ts = bias_s & ~bias_s.shift(1, fill_value=False)
    long = bias_l & tl
    short = bias_s & ts
    side = np.where(long, 1, np.where(short, -1, 0))
    if p.get("long_only", True):
        side = np.where(side > 0, 1, 0)
    sl = p.get("sl_atr", 3.0) * f["atr14"]
    if p.get("sl_h4atr"):
        sl = p["sl_h4atr"] * f["h4_atr14"]
    exl = pd.Series(False, index=f.index); exs = pd.Series(False, index=f.index)
    if p.get("exit_h4ema"):
        exl |= f["h4_close"] < f[f"h4_ema{p['exit_h4ema']}"]; exs |= f["h4_close"] > f[f"h4_ema{p['exit_h4ema']}"]
    if p.get("exit_h4dc"):  # Turtle çıkışı (Pruitt Box 3.1): ters yöndeki N/2 kanal kırılımı (4H)
        m = p["exit_h4dc"]
        exl |= f["h4_close"] < f[f"h4_dcp_lo{m}"]; exs |= f["h4_close"] > f[f"h4_dcp_hi{m}"]
    if p.get("exit_d1dc"):  # Turtle çıkışı günlük kanal ile
        m = p["exit_d1dc"]
        exl |= f["d1_close"] < f[f"d1_dcp_lo{m}"]; exs |= f["d1_close"] > f[f"d1_dcp_hi{m}"]
    return dict(side=side, sl_dist=sl, tp1_R=p.get("tp1_R", 1.0), tp1_frac=p.get("tp1_frac", 0.0),
                tp2_R=p.get("tp_R", np.inf), be_R=p.get("be_R", 0.0), exit_long=exl.values, exit_short=exs.values,
                max_bars=p.get("max_bars", 240), trail_atr=f["h4_atr14"] if p.get("trail_h4") else f["atr14"],
                trail_k=p.get("trail_k", 0.0), trail_start_R=p.get("trail_start_R", 1.0), **_risk_kw(p))


STRATS.update({"s4": s4_stretch_reversion, "s5": s5_momentum})
