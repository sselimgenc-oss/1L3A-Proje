"""Haftalık yön + günlük işlem stratejileri (1W/1D).

Yön filtreleri (haftalık, yalnızca kapanmış haftalar):
  elder   : Elder Impulse — haftalık EMA13 eğimi VE MACD histogram eğimi aynı yönde (Halsey s.92-93'te
            aktarılan Elder hizalama ilkesi; "haftalık trendlere en çok saygı gösterin").
  wdc     : haftalık Donchian(N) kırılım durumu (Pruitt/Turtle mantığı haftalıkta).
  ema     : haftalık kapanış > haftalık EMA(N).
Giriş tetikleri (günlük):
  pullback: Elder Üçlü Ekran ikinci ekranı — haftalık yön yukarıyken günlük osilatör aşırı satımda (RSI2 / BB altı),
            Davey MR #1/#3 ve Connors RSI(2) ile aynı aile.
  breakout: Turtle — günlük N-gün kanal kırılımı (Pruitt Box 3.1).
  half    : Halsey — günlük son bacağın %50'sine geri çekilme (ölçülü hareket girişi).
  impulse : haftalık yönün yeni oluştuğu ilk gün.
"""
import numpy as np
import pandas as pd
from .strategies import _swing_leg


def weekly_dir(f, p):
    mode = p.get("wdir", "elder")
    if mode == "elder":
        up = (f["w_ema13_up"] == 1) & (f["w_macd_hist_up"] == 1)
        dn = (f["w_ema13_up"] == 0) & (f["w_macd_hist_up"] == 0)
    elif mode == "elder_soft":  # yalnız EMA13 eğimi
        up = f["w_ema13_up"] == 1; dn = f["w_ema13_up"] == 0
    elif mode == "wdc":
        n = p.get("wdc_n", 10)
        brk_up = f["w_close"] > f[f"w_dcp_hi{n}"]; brk_dn = f["w_close"] < f[f"w_dcp_lo{n}"]
        st = pd.Series(np.where(brk_up, 1.0, np.where(brk_dn, -1.0, np.nan)), index=f.index).ffill().fillna(0)
        up = st == 1; dn = st == -1
    elif mode == "ema":
        n = p.get("wema_n", 10)
        up = f["w_close"] > f[f"w_ema{n}"]; dn = f["w_close"] < f[f"w_ema{n}"]
    else:
        raise ValueError(mode)
    if p.get("btc_w"):  # BTC haftalık rejim (long için)
        k = p["btc_w"]
        up = up & (f["btc_w_close"] > f[f"btc_w_ema{k}"])
    if p.get("btc_w_short"):
        k = p["btc_w_short"]
        dn = dn & (f["btc_w_close"] < f[f"btc_w_ema{k}"])
    return up.values, dn.values


def strat(f, p):
    up, dn = weekly_dir(f, p)
    up = pd.Series(up, index=f.index); dn = pd.Series(dn, index=f.index)
    c = f["close"]
    trig = p.get("trigger", "pullback")
    if trig == "pullback":
        osc = f[f"rsi{p.get('rsi_n', 2)}"]
        th = p.get("rsi_lo", 15)
        tl = osc < th; ts = osc > 100 - th
        if p.get("bb"):
            tl &= c < f["bb_lo"] if p["bb"] == "below" else c < f["bb_mid"]
            ts &= c > f["bb_up"] if p["bb"] == "below" else c > f["bb_mid"]
        if p.get("turn"):  # Elder: ertesi gün önceki günün tepesini aşınca gir -> onay olarak kapanış > önceki tepe
            tl = tl.shift(1, fill_value=False) & (c > f["high"].shift(1))
            ts = ts.shift(1, fill_value=False) & (c < f["low"].shift(1))
    elif trig == "breakout":
        n = p.get("dc_n", 20)
        tl = c > f[f"dcp_hi{n}"]; ts = c < f[f"dcp_lo{n}"]
        if p.get("fresh", True):
            tl &= ~(c.shift(1) > f[f"dcp_hi{n}"].shift(1)); ts &= ~(c.shift(1) < f[f"dcp_lo{n}"].shift(1))
    elif trig == "half":
        n = p.get("leg_n", 20)
        hi = f["high"].rolling(n).max(); lo = f["low"].rolling(n).min()
        mid = (hi + lo) / 2
        tl = (f["low"] <= mid) & (c > mid) & (hi.shift(1) > hi.shift(n // 2))   # tepe yeni, fiyat %50'den döndü
        ts = (f["high"] >= mid) & (c < mid) & (lo.shift(1) < lo.shift(n // 2))
    elif trig == "mm":
        # Halsey ölçülü hareket: son N günlük bacak (dip->tepe yükseliş), fiyat %50'ye (HWB) geri çekilir,
        # %61.8 başarısızlık seviyesi kırılmamışken kapanır -> ertesi açılışta gir.
        n = p.get("leg_n", 20)
        H, L, legup = _swing_leg(f["high"].values, f["low"].values, n)
        H = pd.Series(H, index=f.index).shift(1); L = pd.Series(L, index=f.index).shift(1)
        legup = pd.Series(legup, index=f.index).shift(1)
        rng = H - L
        okr = rng > p.get("min_rng_atr", 3.0) * f["atr20"]
        lvl50_l = H - 0.5 * rng; lvl618_l = H - 0.618 * rng
        lvl50_s = L + 0.5 * rng; lvl618_s = L + 0.618 * rng
        tl = okr & (legup == 1) & (f["low"] <= lvl50_l) & (c > lvl618_l)
        ts = okr & (legup == -1) & (f["high"] >= lvl50_s) & (c < lvl618_s)
        if p.get("mm_green"):  # dönüş onayı: yeşil/kırmızı mum
            tl &= c > f["open"]; ts &= c < f["open"]
        f = f.assign(_H=H, _L=L, _rng=rng)
    elif trig == "capit":
        # Davey #5 / Connors: k günde sert düşüş sonrası dönüş (yalnız long); haftalık bağlam isteğe bağlı
        k = p.get("cap_k", 3)
        r = c / c.shift(k) - 1
        tl = r < -p.get("cap_drop", 0.20)
        ts = pd.Series(False, index=f.index)
        if p.get("cap_rsi"):
            tl &= f["rsi2"] < p["cap_rsi"]
        ctx = p.get("cap_ctx", "none")
        if ctx == "none":
            up = pd.Series(True, index=f.index)
        elif ctx == "not_down":
            up = ~dn
    elif trig == "impulse":
        tl = up & ~up.shift(1, fill_value=False); ts = dn & ~dn.shift(1, fill_value=False)
    else:
        raise ValueError(trig)
    long = up & tl; short = dn & ts
    if p.get("vol_min"):
        long &= f["vol_ratio"] > p["vol_min"]; short &= f["vol_ratio"] > p["vol_min"]
    side = np.where(long, 1, np.where(short, -1, 0))
    if p.get("long_only", False):
        side = np.where(side > 0, 1, 0)
    atr = f[p.get("atr", "atr20")]
    sl = p.get("sl_atr", 2.0) * atr
    tp1 = p.get("tp1_R", 1.0)
    tp2 = p.get("tp_R", np.inf)
    if trig == "mm" and p.get("mm_levels", True):
        # Stop: seçilen geri çekilme seviyesinin ötesi (Halsey: %61.8 başarısızlık), hedefler: tepe (0) ve -%23.6 uzantı
        sl_lvl = p.get("stop_lvl", 0.786)
        buf = p.get("sl_buf_atr", 0.25) * atr
        sl_l = c - (f["_H"] - sl_lvl * f["_rng"]) + buf
        sl_s = (f["_L"] + sl_lvl * f["_rng"]) - c + buf
        sl = pd.Series(np.where(side > 0, sl_l, np.where(side < 0, sl_s, np.nan)), index=f.index)
        sl = sl.where(sl > 0.5 * atr, 0.5 * atr)
        t1_l = (f["_H"] - c) / sl; t1_s = (c - f["_L"]) / sl
        tp1 = pd.Series(np.where(side > 0, t1_l, t1_s), index=f.index).clip(lower=0.3).fillna(1.0).values
        if p.get("final_target", "ext") == "ext":
            t2_l = (f["_H"] + 0.236 * f["_rng"] - c) / sl; t2_s = (c - (f["_L"] - 0.236 * f["_rng"])) / sl
            tp2 = pd.Series(np.where(side > 0, t2_l, t2_s), index=f.index).clip(lower=0.5).fillna(np.inf).values
    exl = pd.Series(False, index=f.index); exs = pd.Series(False, index=f.index)
    ex = p.get("exit", "wdir")
    if ex in ("wdir", "both"):  # haftalık yön bozulunca çık
        exl |= ~up; exs |= ~dn
    if ex in ("dc", "both"):  # Turtle çıkışı: ters N-gün kanal
        m = p.get("exit_dc", 10)
        exl |= c < f[f"dcp_lo{m}"]; exs |= c > f[f"dcp_hi{m}"]
    if ex == "rsi":  # Connors çıkışı
        exl |= f["rsi2"] > p.get("exit_rsi", 70); exs |= f["rsi2"] < 100 - p.get("exit_rsi", 70)
    if ex == "sma5":
        exl |= c > f["sma5"]; exs |= c < f["sma5"]
    return dict(side=side, sl_dist=np.asarray(sl, dtype=float), tp1_R=tp1, tp1_frac=p.get("tp1_frac", 0.0),
                tp2_R=tp2, be_R=p.get("be_R", 0.0), exit_long=exl.values, exit_short=exs.values,
                max_bars=p.get("max_bars", 60), trail_atr=atr.values, trail_k=p.get("trail_k", 0.0),
                trail_start_R=p.get("trail_start_R", 0.0), loss_delay=p.get("loss_delay", 0))
