"""Üç strateji: S1 Trend Geri Çekilme, S2 Momentum Kırılması, S3 ORB + Pivot.

Her strateji, `features.build` çıktısı üzerinde vektörel olarak sinyal üretir:
  long / short       : mum kapanışında sinyal (bool)
  long_stop / short_stop : stop fiyatı
Çıkış kuralları `exit` sözlüğünde backtest motoruna verilir.
Parametre değerleri yalnızca kitaplarda geçen ayarlardan seçilir
(bkz. docs/strateji_analizi.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Signals:
    long: pd.Series
    short: pd.Series
    long_stop: pd.Series
    short_stop: pd.Series
    exit: dict = field(default_factory=dict)


def _trend(df: pd.DataFrame, mode: str, adx_min: float = 0):
    """Üst zaman dilimi yön filtresi. Dönüş: (up, down) bool serileri.

    adx_min > 0 ise 1s ADX(14) bu değerin üstünde olmalı (Lien/Denham: ADX>20 trend,
    ADX>25 güçlü trend)."""
    up, dn = _trend_dir(df, mode)
    if adx_min:
        strong = df["h1_adx"] > adx_min
        up, dn = up & strong, dn & strong
    return up, dn


def _trend_dir(df: pd.DataFrame, mode: str):
    h4u_200 = (df["h4_close"] > df["h4_ema200"]) | (df["h4_ema50"] > df["h4_ema200"])
    h4d_200 = (df["h4_close"] < df["h4_ema200"]) | (df["h4_ema50"] < df["h4_ema200"])
    h4u = df["h4_ema20"] > df["h4_ema50"]
    h4d = df["h4_ema20"] < df["h4_ema50"]
    h1u = (df["h1_ema20"] > df["h1_ema50"]) & (df["h1_close"] > df["h1_ema50"])
    h1d = (df["h1_ema20"] < df["h1_ema50"]) & (df["h1_close"] < df["h1_ema50"])
    if mode == "h4_200+h1":      # Wallace 200 EMA + Velez saatlik MA çifti
        return h4u_200 & h1u, h4d_200 & h1d
    if mode == "h4+h1":          # 4s EMA20/50 + 1s EMA20/50
        return h4u & h1u, h4d & h1d
    if mode == "strict":         # ikisi birden (mükemmel düzene yakın)
        return h4u & h4u_200 & h1u, h4d & h4d_200 & h1d
    if mode == "h1":
        return h1u, h1d
    if mode == "po_h4":          # Lien mükemmel düzen (4s) + 1s yön
        return df["h4_po_up"].fillna(False).astype(bool) & h1u, df["h4_po_dn"].fillna(False).astype(bool) & h1d
    if mode == "po_h1":          # Lien mükemmel düzen (1s) + 4s EMA20/50
        return df["h1_po_up"].fillna(False).astype(bool) & h4u, df["h1_po_dn"].fillna(False).astype(bool) & h4d
    if mode == "none":
        t = pd.Series(True, df.index)
        return t, t
    raise ValueError(mode)


def _clamp_stop(df, raw_long, raw_short, min_atr, max_atr, min_risk_cost=0.0):
    """Stopu [min_atr, max_atr]·ATR aralığına sıkıştırır.

    min_risk_cost > 0 ise risk, gidiş-dönüş maliyetinin en az bu katı olmalı;
    aksi halde işlem açılmaz (maliyet R'nin büyük kısmını yer)."""
    a = df["atr"]
    c = df["close"]
    ls = np.minimum(raw_long, c - min_atr * a)
    ss = np.maximum(raw_short, c + min_atr * a)
    ok_l = (c - ls) <= max_atr * a
    ok_s = (ss - c) <= max_atr * a
    if min_risk_cost:
        rt = 2 * df["cost_pct"] * c
        ok_l &= (c - ls) >= min_risk_cost * rt
        ok_s &= (ss - c) >= min_risk_cost * rt
    return ls, ss, ok_l, ok_s


def _session_ok(df, p):
    return (df["in_session"] & ~df["last_bar"] & (df["since_open"] >= p.get("skip_open_min", 0))
            & (df["since_open"] + p.get("no_entry_last_min", 30)
               < df["since_open"].groupby(df["day"]).transform("max")))


def _range_day(df, p):
    """Trend günü değil: fiyat gün açılışından max_day_move·günlük ATR'den az uzaklaşmış
    (Lien: aralık ortamında dönüş işlemleri; Tranquil Trader: geniş CPR = yatay gün)."""
    if p.get("max_day_move") is None:
        return pd.Series(True, df.index)
    return ((df["close"] - df["dopen"]).abs() / df["atr_d"]) < p["max_day_move"]


# ---------------------------------------------------------------- S1
S1_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h4+h1", pb_lookback=3, touch_atr=0.25, trigger="either",
                  ltf_align=True, stop_buf=0.1, min_atr=0.5, max_atr=2.0,
                  partial_R=1.0, partial_frac=0.5, target_R=2.0, ema_exit=True,
                  skip_open_min=0, no_entry_last_min=30)


def s1_pullback(df: pd.DataFrame, **kw) -> Signals:
    p = {**S1_DEFAULT, **kw}
    up, dn = _trend(df, p["trend"], p["adx_min"])
    a, c, lb = df["atr"], df["close"], p["pb_lookback"]
    # Geri çekilme: son lb mumda dip EMA20'ye touch_atr·ATR kadar yaklaştı, EMA50 altı kapanış yok
    pb_l = ((df["low"] - df["ema20"]) / a).rolling(lb).min() <= p["touch_atr"]
    pb_s = ((df["ema20"] - df["high"]) / a).rolling(lb).min() <= p["touch_atr"]
    hold_l = (df["close"] - df["ema50"]).rolling(lb).min() > 0
    hold_s = (df["ema50"] - df["close"]).rolling(lb).min() > 0
    # Tetik (Backus): Stokastik %K>%D kesişimi (<50 bölgesinden) veya RSI9 > MA4 kesişimi
    st_up = ((df["stk"] > df["std"]) & (df["stk"].shift() <= df["std"].shift())
             & (df["std"].shift() < 50)).rolling(3).max().astype(bool)
    st_dn = ((df["stk"] < df["std"]) & (df["stk"].shift() >= df["std"].shift())
             & (df["std"].shift() > 50)).rolling(3).max().astype(bool)
    rs_up = (df["rsi9"] > df["rsi9_ma4"]) & (df["rsi9"].shift() <= df["rsi9_ma4"].shift())
    rs_dn = (df["rsi9"] < df["rsi9_ma4"]) & (df["rsi9"].shift() >= df["rsi9_ma4"].shift())
    trig = p["trigger"]
    tl = {"stoch": st_up, "rsi": rs_up, "either": st_up | rs_up, "both": st_up & rs_up,
          "none": pd.Series(True, df.index)}[trig]
    ts = {"stoch": st_dn, "rsi": rs_dn, "either": st_dn | rs_dn, "both": st_dn & rs_dn,
          "none": pd.Series(True, df.index)}[trig]
    rev_l = (c > df["ema20"]) & (c > df["high"].shift())
    rev_s = (c < df["ema20"]) & (c < df["low"].shift())
    al_l = df["ema20"] > df["ema50"] if p["ltf_align"] else True
    al_s = df["ema20"] < df["ema50"] if p["ltf_align"] else True
    raw_l = df["low"].rolling(lb + 2).min() - p["stop_buf"] * a
    raw_s = df["high"].rolling(lb + 2).max() + p["stop_buf"] * a
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & pb_l & hold_l & tl & rev_l & al_l & ok_l & ses
    short = dn & pb_s & hold_s & ts & rev_s & al_s & ok_s & ses
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"],
              target_R=p["target_R"], close_exit="ema20" if p["ema_exit"] else None)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S2
S2_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h4+h1", h1_macd=True, setup_lb=10, buf_atr=0.1, macd_bars=5,
                  confirm="macd", min_atr=0.5, max_atr=2.0, partial_R=1.0,
                  partial_frac=0.5, target_R=None, trail_atr=0.25,
                  skip_open_min=0, no_entry_last_min=30)


def s2_momentum(df: pd.DataFrame, **kw) -> Signals:
    p = {**S2_DEFAULT, **kw}
    up, dn = _trend(df, p["trend"], p["adx_min"])
    if p["h1_macd"]:
        up = up & (df["h1_macd_hist"] > 0) & (df["h1_close"] > df["h1_sma100"])
        dn = dn & (df["h1_macd_hist"] < 0) & (df["h1_close"] < df["h1_sma100"])
    a, c = df["atr"], df["close"]
    top = np.maximum(df["ema20"], df["sma100"]) + p["buf_atr"] * a
    bot = np.minimum(df["ema20"], df["sma100"]) - p["buf_atr"] * a
    was_below = (c < np.minimum(df["ema20"], df["sma100"])).rolling(p["setup_lb"]).max().astype(bool)
    was_above = (c > np.maximum(df["ema20"], df["sma100"])).rolling(p["setup_lb"]).max().astype(bool)
    brk_l = (c > top) & (c.shift() <= top.shift()) & was_below.shift(fill_value=False)
    brk_s = (c < bot) & (c.shift() >= bot.shift()) & was_above.shift(fill_value=False)
    nb = p["macd_bars"]
    macd_l = (df["macd"] > 0) & (df["macd"].rolling(nb + 1).min() < 0)   # ≤nb mum önce pozitife döndü
    macd_s = (df["macd"] < 0) & (df["macd"].rolling(nb + 1).max() > 0)
    mom_l = df["mom"] > df["mom_ma"]
    mom_s = df["mom"] < df["mom_ma"]
    cf = p["confirm"]
    cl = {"macd": macd_l, "mom": mom_l, "either": macd_l | mom_l, "both": macd_l & mom_l}[cf]
    cs = {"macd": macd_s, "mom": mom_s, "either": macd_s | mom_s, "both": macd_s & mom_s}[cf]
    ls, ss, ok_l, ok_s = _clamp_stop(df, df["low"], df["high"], p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & brk_l & cl & ok_l & ses
    short = dn & brk_s & cs & ok_s & ses
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              trail="ema20", trail_atr=p["trail_atr"])
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S3
S3_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h1", pivot_filter=True, cpr_narrow=False, width_max=0.8,
                  vwap=True, volume=True, stop_mode="mid", min_atr=0.3, max_atr=2.5,
                  partial_R=1.0, partial_frac=0.5, target_R=2.0, window_min=240,
                  no_entry_last_min=30)


def s3_orb(df: pd.DataFrame, **kw) -> Signals:
    p = {**S3_DEFAULT, **kw}
    up, dn = _trend(df, p["trend"], p["adx_min"])
    c = df["close"]
    if p["pivot_filter"]:
        up = up & (c > df["P"])
        dn = dn & (c < df["P"])
    if p["cpr_narrow"]:
        up = up & df["cpr_narrow"].fillna(False).astype(bool)
        dn = dn & df["cpr_narrow"].fillna(False).astype(bool)
    width = df["orb_hi"] - df["orb_lo"]
    narrow = width <= p["width_max"] * df["atr_d"]
    base = df["orb_done"] & df["orb_ok"] & narrow & (df["since_open"] < df["orb_min"] + p["window_min"])
    brk_l = (c > df["orb_hi"]) & (c.shift() <= df["orb_hi"])
    brk_s = (c < df["orb_lo"]) & (c.shift() >= df["orb_lo"])
    if p["vwap"]:
        brk_l &= c > df["vwap"]
        brk_s &= c < df["vwap"]
    if p["volume"]:
        vol_ok = (df["volume"] > df["vol_ma"]) | (df["vol_ma"] <= 0)
        brk_l &= vol_ok
        brk_s &= vol_ok
    mid = (df["orb_hi"] + df["orb_lo"]) / 2
    raw_l = mid if p["stop_mode"] == "mid" else df["orb_lo"]
    raw_s = mid if p["stop_mode"] == "mid" else df["orb_hi"]
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & base & brk_l & ok_l & ses
    short = dn & base & brk_s & ok_s & ses
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"],
              target_R=p["target_R"], max_per_day=1)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S4
S4_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h4+h1", regime="trend", adx_max=25,
                  setup="bb", setup_lb=3, stop_buf=0.1, min_atr=1.0, max_atr=3.0,
                  tp="bb_mid", partial_R=None, partial_frac=0.5, target_R=None,
                  max_bars=None, skip_open_min=0, no_entry_last_min=30)


def s4_band_reversion(df: pd.DataFrame, **kw) -> Signals:
    """Bollinger(20,2) + Stokastik aşırı alım/satımdan dönüş.

    Kaynak: Odin Velez (Böl. 6: yükseliş trendinde alt bant/aşırı satım alım fırsatı,
    orta banda dönüşte kâr), Kathy Lien (ADX<20-25 aralık piyasasında Bollinger ile
    aralık ticareti; ADX>25 trendde geri çekilme), Manny Backus (Stokastik 20 altından
    dönüş tetiği), Baron McBane / Mark Denham (alt bant destek, üst bant direnç).
    regime="trend": yalnızca üst TF yönünde, aşırı satım dipte alım.
    regime="range": 1s ADX<adx_max iken her iki yönde bant dışından içeri dönüş.
    """
    p = {**S4_DEFAULT, **kw}
    a, c, lb = df["atr"], df["close"], p["setup_lb"]
    if p["regime"] == "trend":
        up, dn = _trend(df, p["trend"], p["adx_min"])
    else:
        rng = df["h1_adx"] < p["adx_max"]
        up, dn = rng, rng
    ob_l = {"bb": df["low"] < df["bb_lo"], "stoch": df["stk"] < 20,
            "both": (df["low"] < df["bb_lo"]) & (df["stk"] < 20)}[p["setup"]]
    ob_s = {"bb": df["high"] > df["bb_up"], "stoch": df["stk"] > 80,
            "both": (df["high"] > df["bb_up"]) & (df["stk"] > 80)}[p["setup"]]
    was_l = ob_l.rolling(lb).max().astype(bool)
    was_s = ob_s.rolling(lb).max().astype(bool)
    # Dönüş teyidi: kapanış alt bandın içinde ve önceki mumun tepesi üstünde (short tersi)
    rev_l = (c > df["bb_lo"]) & (c > df["high"].shift()) & (c < df["bb_mid"])
    rev_s = (c < df["bb_up"]) & (c < df["low"].shift()) & (c > df["bb_mid"])
    raw_l = df["low"].rolling(lb + 1).min() - p["stop_buf"] * a
    raw_s = df["high"].rolling(lb + 1).max() + p["stop_buf"] * a
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"],
                                     p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & was_l & rev_l & ok_l & ses
    short = dn & was_s & rev_s & ok_s & ses
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"],
              target_R=p["target_R"], tp=p["tp"], max_bars=p["max_bars"])
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S5
S5_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h4+h1", day_filter="none", stop_mode="atr",
                  stop_atr=1.0, min_atr=0.5, max_atr=3.0, partial_R=1.0, partial_frac=0.5,
                  target_R=2.0, window_min=600, skip_open_min=0, no_entry_last_min=60)


def s5_pdhl_break(df: pd.DataFrame, **kw) -> Signals:
    """Önceki gün tepe/dip kırılması.

    Kaynak: Kathy Lien (iç gün kırılması: önceki günün tepesinin üzerinde al, 2R'de kâr al),
    Jacob Bernstein (önceki gün aralığı/boşluk yöntemleri), Tranquil Trader (iç değer CPR =
    trend/kırılma günü). day_filter: none | inside (dün iç gün) | nr7 (dün 7 günün en dar aralığı).
    """
    p = {**S5_DEFAULT, **kw}
    up, dn = _trend(df, p["trend"], p["adx_min"])
    c, a = df["close"], df["atr"]
    if p["day_filter"] == "inside":
        f = df["inside_prev"].fillna(False).astype(bool)
    elif p["day_filter"] == "nr7":
        f = df["nr7_prev"].fillna(False).astype(bool)
    elif p["day_filter"] == "either":
        f = (df["inside_prev"] | df["nr7_prev"]).fillna(False).astype(bool)
    else:
        f = pd.Series(True, df.index)
    first = df["since_open"] < p["window_min"]
    brk_l = (c > df["PDH"]) & (c.shift() <= df["PDH"]) & (df["dopen"] < df["PDH"])
    brk_s = (c < df["PDL"]) & (c.shift() >= df["PDL"]) & (df["dopen"] > df["PDL"])
    if p["stop_mode"] == "level":   # stop: kırılan seviyenin altında (bugünkü dip ile sınırlı)
        raw_l = np.maximum(df["dlow"], df["PDH"] - p["stop_atr"] * a)
        raw_s = np.minimum(df["dhigh"], df["PDL"] + p["stop_atr"] * a)
    else:
        raw_l, raw_s = c - p["stop_atr"] * a, c + p["stop_atr"] * a
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & f & first & brk_l & ok_l & ses
    short = dn & f & first & brk_s & ok_s & ses
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              max_per_day=1)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S6
S6_DEFAULT = dict(adx_min=0, min_risk_cost=0, max_day_move=None, regime="any", adx_max=35, trend="h4+h1", gap=False,
                  sweep_atr=0.1, reclaim_bars=3, level="pd", stop_buf=0.1, min_atr=0.5,
                  max_atr=3.0, tp="P", partial_R=1.0, partial_frac=0.5, target_R=2.0,
                  skip_open_min=30, no_entry_last_min=60)


def s6_fader(df: pd.DataFrame, **kw) -> Signals:
    """Sahte kırılma / Fader: önceki günün dibinin altına sarkıp (stop avı) geri içeri
    kapanan fiyatta al; tepe için tersi.

    Kaynak: Kathy Lien "Fader" ve "Yanlış kırılmaları filtreleme" (ADX<35 aralık ortamında
    önceki gün dibinin altına sarkma sonrası ters yönde işlem; sahte kırılmalar gerçeklerden
    daha sık), Carole Christensen "VWAP sahte kırılması", Al Brooks/Galen Woods başarısız
    kırılma mantığı (metinler/). regime: any | range (1s ADX<adx_max) | trend (üst TF yönünde).
    level: pd (önceki gün tepe/dip) | orb (açılış aralığı).
    gap=True: Jacob Bernstein "boşluk (Oops) ticareti" — gün dünün dibinin altında AÇILMIŞ
    olmalı, fiyat dünün dibinin üzerine çıkınca al (tepe için tersi); takip: stop + gün sonu.
    """
    p = {**S6_DEFAULT, **kw}
    c, a = df["close"], df["atr"]
    if p["level"] == "orb":
        lo_lvl, hi_lvl = df["orb_lo"].where(df["orb_done"]), df["orb_hi"].where(df["orb_done"])
    else:
        lo_lvl, hi_lvl = df["PDL"], df["PDH"]
    nb = p["reclaim_bars"]
    swept_l = ((lo_lvl - df["low"]) >= p["sweep_atr"] * a).rolling(nb).max().astype(bool)
    swept_s = ((df["high"] - hi_lvl) >= p["sweep_atr"] * a).rolling(nb).max().astype(bool)
    rec_l = (c > lo_lvl) & (c.shift() <= lo_lvl.shift()) | ((c > lo_lvl) & (df["low"] < lo_lvl))
    rec_s = (c < hi_lvl) & (c.shift() >= hi_lvl.shift()) | ((c < hi_lvl) & (df["high"] > hi_lvl))
    if p["regime"] == "range":
        okr = df["h1_adx"] < p["adx_max"]
        up = dn = okr
    elif p["regime"] == "trend":
        up, dn = _trend(df, p["trend"], p["adx_min"])
    else:
        up = dn = pd.Series(True, df.index)
    raw_l = df["low"].rolling(nb + 1).min() - p["stop_buf"] * a
    raw_s = df["high"].rolling(nb + 1).max() + p["stop_buf"] * a
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    if p["gap"]:
        swept_l = swept_l | (df["dopen"] < lo_lvl)
        swept_s = swept_s | (df["dopen"] > hi_lvl)
        up = up & (df["dopen"] < lo_lvl)
        dn = dn & (df["dopen"] > hi_lvl)
    rd = _range_day(df, p)
    long = up & swept_l & rec_l & ok_l & ses & rd
    short = dn & swept_s & rec_s & ok_s & ses & rd
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              tp=p["tp"] if p["tp"] else None, max_per_day=2)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S7
S7_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h4+h1", dip_bars=4, dip_atr=0.2,
                  stop_buf=0.1, min_atr=0.5, max_atr=3.0, partial_R=1.0, partial_frac=0.5,
                  target_R=2.0, close_exit=False, skip_open_min=30, no_entry_last_min=60)


def s7_vwap_reclaim(df: pd.DataFrame, **kw) -> Signals:
    """VWAP geri alma: üst TF yükselişte, fiyat VWAP'ın altına sarkıp tekrar üstünde kapanınca al.

    Kaynak: Carole Christensen (Yöntem 5: VWAP; "hisse VWAP'ın altına düşüp hemen geri
    sıçrarsa alıcılar kontrolü ele geçirdi"; ORB stopu VWAP altı kapanış), Don Charles (VWAP),
    Kathy Lien / Odin Velez (çoklu zaman dilimi: büyük trend yönünde geri çekilmede al).
    """
    p = {**S7_DEFAULT, **kw}
    up, dn = _trend(df, p["trend"], p["adx_min"])
    c, a, v = df["close"], df["atr"], df["vwap"]
    nb = p["dip_bars"]
    dip_l = ((v - df["low"]) >= p["dip_atr"] * a).rolling(nb).max().astype(bool)
    dip_s = ((df["high"] - v) >= p["dip_atr"] * a).rolling(nb).max().astype(bool)
    rec_l = (c > v) & (c.shift() <= v.shift())
    rec_s = (c < v) & (c.shift() >= v.shift())
    raw_l = df["low"].rolling(nb + 1).min() - p["stop_buf"] * a
    raw_s = df["high"].rolling(nb + 1).max() + p["stop_buf"] * a
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & dip_l & rec_l & ok_l & ses
    short = dn & dip_s & rec_s & ok_s & ses
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              close_exit="vwap" if p["close_exit"] else None, max_per_day=2)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S8
S8_DEFAULT = dict(adx_min=0, min_risk_cost=0, max_day_move=None, regime="range", adx_max=25, trend="h4+h1",
                  stop_buf=0.25, min_atr=0.5, max_atr=3.0, tp="P", partial_R=None,
                  partial_frac=0.5, target_R=2.0, skip_open_min=30, no_entry_last_min=60)


def s8_camarilla(df: pd.DataFrame, **kw) -> Signals:
    """Camarilla L3/H3 dönüşü: fiyat L3'ün altına iner ve tekrar üstünde kapanırsa al
    (H3 için sat); hedef pivot (P), stop L4/H4 yönünde.

    Kaynak: Tranquil Trader (Camarilla: en önemli seviyeler 3. ve 4. seviyeler; L3/H3'te
    dönüş, H4/L4 kırılımı trend), Manny Backus (pivot çizgileri destek/direnç).
    """
    p = {**S8_DEFAULT, **kw}
    c, a = df["close"], df["atr"]
    if p["regime"] == "range":
        up = dn = df["h1_adx"] < p["adx_max"]
    elif p["regime"] == "trend":
        up, dn = _trend(df, p["trend"], p["adx_min"])
    else:
        up = dn = pd.Series(True, df.index)
    rec_l = (c > df["L3"]) & (df["low"].rolling(3).min() < df["L3"]) & (c < df["P"])
    rec_s = (c < df["H3"]) & (df["high"].rolling(3).max() > df["H3"]) & (c > df["P"])
    raw_l = df["low"].rolling(4).min() - p["stop_buf"] * a
    raw_s = df["high"].rolling(4).max() + p["stop_buf"] * a
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    rd = _range_day(df, p)
    long = up & rec_l & ok_l & ses & rd
    short = dn & rec_s & ok_s & ses & rd
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              tp=p["tp"] if p["tp"] else None, max_per_day=2)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S9
S9_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="none", anchor_utc=13.5, range_h=2.0,
                  window_h=4.0, buf_atr=0.0, width_max=1.0, stop_mode="mid", min_atr=0.5,
                  max_atr=4.0, partial_R=1.0, partial_frac=0.5, target_R=2.0, volume=False,
                  no_entry_last_min=60)


def s9_session_break(df: pd.DataFrame, **kw) -> Signals:
    """Seans aralığı kırılması (kripto 7/24 için seans açılışları referans alınır).

    Kaynak: Kathy Lien "Gerçek anlaşmayı beklemek" (Frankfurt/Londra açılışı öncesi aralık,
    kırılımda giriş, 1R'de yarısını kapat), Odin Velez "New York kırılması" (07:00-09:00 EST
    aralığının tepesine/dibine bekleyen emir, karşı uca stop), Christensen ORB (aralık
    günlük ATR'ye göre dar olmalı). anchor_utc: seans açılışı (Londra 7-8, New York 13.5).
    Aralık = [anchor - range_h, anchor); giriş penceresi = [anchor, anchor + window_h).
    """
    p = {**S9_DEFAULT, **kw}
    c, a = df["close"], df["atr"]
    utc = df.index.hour + df.index.minute / 60
    a0 = p["anchor_utc"]
    in_rng = (utc >= a0 - p["range_h"]) & (utc < a0)
    win = (utc >= a0) & (utc < a0 + p["window_h"])
    key = pd.Series(df.index.floor("D"), index=df.index)
    hi = df["high"].where(in_rng).groupby(key).transform("max")
    lo = df["low"].where(in_rng).groupby(key).transform("min")
    width_ok = (hi - lo) <= p["width_max"] * df["atr_d"]
    top, bot = hi + p["buf_atr"] * a, lo - p["buf_atr"] * a
    brk_l = (c > top) & (c.shift() <= top) & win & width_ok
    brk_s = (c < bot) & (c.shift() >= bot) & win & width_ok
    if p["volume"]:
        brk_l &= df["volume"] > df["vol_ma"]
        brk_s &= df["volume"] > df["vol_ma"]
    if p["trend"] == "none":
        up = dn = pd.Series(True, df.index)
    else:
        up, dn = _trend(df, p["trend"], p["adx_min"])
    mid = (hi + lo) / 2
    raw_l = mid if p["stop_mode"] == "mid" else lo
    raw_s = mid if p["stop_mode"] == "mid" else hi
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & brk_l & ok_l & ses
    short = dn & brk_s & ok_s & ses
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              max_per_day=1)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S10
S10_DEFAULT = dict(adx_min=0, min_risk_cost=0, mkt_min=None, yon="both", trend="none", at_utc=12.0, at_end=None, move_atr=0.5,
                   cpr_narrow=False, stop_mode="open", stop_atr_d=0.5, min_atr=0.5, max_atr=8.0,
                   partial_R=None, partial_frac=0.5, target_R=None, no_entry_last_min=60)


def s10_trend_day(df: pd.DataFrame, **kw) -> Signals:
    """Gün içi momentum / trend günü: belirlenen saatte gün açılışından bu yana hareket
    günlük ATR'nin move_atr katını aşmışsa o yönde gir, gün sonuna kadar tut.

    Kaynak: Kathy Lien (momentum stratejisi: ivme sizin tarafınızdayken girin; hareketlerin
    %70'i zamanın %20'sinde), Tranquil Trader (dar CPR / iç değer = trend günü, kırılma),
    Jacob Bernstein (trend yönünde gün sonuna kadar tutma, gün sonu çıkışı),
    Joe Duarte / Justin Kuepper (momentum ve trendle işlem).
    """
    p = {**S10_DEFAULT, **kw}
    c = df["close"]
    utc = df.index.hour + df.index.minute / 60
    # karar mumu (at_end verilirse [at_utc, at_end) penceresinde şartın ilk sağlandığı mum;
    # günde tek işlem kuralı nedeniyle ilk sinyal kullanılır)
    at = (utc >= p["at_utc"]) & (utc < (p["at_end"] if p["at_end"] else p["at_utc"] + 0.25))
    mv = (c - df["dopen"]) / df["atr_d"]
    if p["trend"] == "none":
        up = dn = pd.Series(True, df.index)
    else:
        up, dn = _trend(df, p["trend"], p["adx_min"])
    if p["cpr_narrow"]:
        nar = df["cpr_narrow"].fillna(False).astype(bool)
        up, dn = up & nar, dn & nar
    if p["mkt_min"] is not None and "mkt_move" in df:
        # Manny Backus: hisseyi ancak S&P 500 gün içinde pozitifken al. Kripto karşılığı:
        # BTC'nin gün açılışından hareketi (günlük ATR cinsinden) aynı yönde olmalı.
        up = up & (df["mkt_move"] > p["mkt_min"])
        dn = dn & (df["mkt_move"] < -p["mkt_min"])
    if p["stop_mode"] == "open":
        raw_l, raw_s = df["dopen"], df["dopen"]
    else:
        raw_l = c - p["stop_atr_d"] * df["atr_d"]
        raw_s = c + p["stop_atr_d"] * df["atr_d"]
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & at & (mv > p["move_atr"]) & ok_l & ses
    short = dn & at & (mv < -p["move_atr"]) & ok_s & ses
    long, short = _yon(long, short, p, df)
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              max_per_day=1)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S12
S12_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h4+h1", close_pos=0.8, above_pdh=False,
                   at_utc=0.25, at_end=3.0, stop_atr_d=1.0, min_atr=0.5, max_atr=12.0,
                   partial_R=None, partial_frac=0.5, target_R=None, yon="long",
                   no_entry_last_min=60)


def s12_strong_close(df: pd.DataFrame, **kw) -> Signals:
    """Güçlü kapanış devamı: dün gün aralığının üst bölgesinde (close_pos) kapandıysa ve üst
    zaman dilimi yükselişteyse bugünün başında al, gün sonunda kapat.

    Kaynak: Jacob Bernstein (önceki günün kapanışı/aralığına göre kurulum, gün sonu çıkışı;
    "ilk kârlı açılış"), Kathy Lien (momentum: ivme sizin tarafınızdayken girin; trend yönünde
    işlem), Tranquil Trader (yükselen CPR = yükseliş eğilimi).
    """
    p = {**S12_DEFAULT, **kw}
    up, dn = _trend(df, p["trend"], p["adx_min"])
    rng = (df["PDH"] - df["PDL"]).replace(0, np.nan)
    pos = (df["PDC"] - df["PDL"]) / rng
    utc = df.index.hour + df.index.minute / 60
    at = (utc >= p["at_utc"]) & (utc < p["at_end"])
    cond_l = pos > p["close_pos"]
    cond_s = pos < 1 - p["close_pos"]
    if p["above_pdh"]:
        cond_l &= df["close"] > df["PDH"]
        cond_s &= df["close"] < df["PDL"]
    c = df["close"]
    raw_l, raw_s = c - p["stop_atr_d"] * df["atr_d"], c + p["stop_atr_d"] * df["atr_d"]
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & at & cond_l & ok_l & ses
    short = dn & at & cond_s & ok_s & ses
    if p["yon"] == "long":
        short = short & False
    elif p["yon"] == "short":
        long = long & False
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              max_per_day=1)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S13
S13_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h4+h1", n_high=80, n_pull=8, k_bars=12,
                   stop_buf=0.1, stop_atr_d=None, min_atr=0.5, max_atr=12.0, partial_R=None,
                   partial_frac=0.5, target_R=None, yon="long", no_entry_last_min=60,
                   max_per_day=1)


def s13_false_break_filter(df: pd.DataFrame, **kw) -> Signals:
    """Kathy Lien "Yanlış kırılmaları filtreleme" (Böl. 9) — gün içine uyarlanmış:
    1) fiyat n_high mumluk (ör. 80×15dk = 20 saat) yeni tepe yapar, 2) ardından geri çekilip
    n_pull mumluk dibi görür (zayıf oyuncular silkelenir), 3) dipten sonraki k_bars mum içinde
    yeniden n_high tepesinin üzerine çıkarsa al. Stop: geri çekilme dibinin biraz altı.
    Lien: "çok yüksek başarı oranına sahip olma eğilimindedir"; 2R veya iz süren stop.
    """
    p = {**S13_DEFAULT, **kw}
    up, dn = _trend(df, p["trend"], p["adx_min"])
    c, h, l, a = df["close"], df["high"], df["low"], df["atr"]
    N, M, K = p["n_high"], p["n_pull"], p["k_bars"]
    hh = h.rolling(N).max().shift()          # önceki N mumun tepesi
    ll = l.rolling(N).min().shift()
    new_hi = h > hh                          # yeni N-tepe
    new_lo = l < ll
    pull_lo = l <= l.rolling(M).min().shift()   # M-mumluk dip (geri çekilme)
    pull_hi = h >= h.rolling(M).max().shift()
    # adım 1 → 2: son K mum içinde geri çekilme dibi, ondan önceki K mum içinde yeni tepe
    had_hi = new_hi.rolling(K).max().shift(1).fillna(0).astype(bool)
    had_lo = new_lo.rolling(K).max().shift(1).fillna(0).astype(bool)
    pulled_l = (pull_lo & had_hi).rolling(K).max().fillna(0).astype(bool)
    pulled_s = (pull_hi & had_lo).rolling(K).max().fillna(0).astype(bool)
    ref_hi = h.rolling(N + 2 * K).max().shift()      # kırılması gereken son tepe
    ref_lo = l.rolling(N + 2 * K).min().shift()
    brk_l = pulled_l & (c > ref_hi) & (c.shift() <= ref_hi.shift())
    brk_s = pulled_s & (c < ref_lo) & (c.shift() >= ref_lo.shift())
    if p["stop_atr_d"]:
        raw_l, raw_s = c - p["stop_atr_d"] * df["atr_d"], c + p["stop_atr_d"] * df["atr_d"]
    else:
        raw_l = l.rolling(2 * K).min() - p["stop_buf"] * a
        raw_s = h.rolling(2 * K).max() + p["stop_buf"] * a
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & brk_l & ok_l & ses
    short = dn & brk_s & ok_s & ses
    long, short = _yon(long, short, p, df)
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              max_per_day=p["max_per_day"])
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S14
S14_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h4", confirm=True, fresh_h=2, stop="mac",
                   stop_atr_d=1.0, min_atr=0.5, max_atr=12.0, partial_R=None, partial_frac=0.5,
                   target_R=None, yon="long", no_entry_last_min=60, max_per_day=1)


def s14_mac(df: pd.DataFrame, **kw) -> Signals:
    """Jacob Bernstein hareketli ortalama kanalı (MAC) + momentum teyidi (Böl. 6), 1 saatlik
    mumlarda: SMA10(yüksek) üzerinde iki ardışık TAM mum = alış modeli; MOM(28) kendi 28'lik
    SMA'sının üzerindeyse teyit. Giriş 15dk'da (model oluştuktan sonraki ilk mum, fresh_h saat
    içinde), stop SMA8(düşük) altı ya da günlük ATR; çıkış gün sonu (Bernstein: "seansın sonuna
    kadar takip eden stopla").
    """
    p = {**S14_DEFAULT, **kw}
    if p["trend"] == "h4":
        up, dn = df["h4_ema20"] > df["h4_ema50"], df["h4_ema20"] < df["h4_ema50"]
    else:
        up, dn = _trend(df, p["trend"], p["adx_min"])
    mu = df["h1_mac_up2"].fillna(False).astype(bool)
    md = df["h1_mac_dn2"].fillna(False).astype(bool)
    if p["confirm"]:
        mu &= df["h1_mom"] > df["h1_mom_ma"]
        md &= df["h1_mom"] < df["h1_mom_ma"]
    # model yeni oluştu: son fresh_h saat içinde yanlış → doğru geçişi (15dk mum sayısıyla)
    w = int(p["fresh_h"] * 4)
    fresh_u = mu & ~mu.shift(w).fillna(False).astype(bool)
    fresh_d = md & ~md.shift(w).fillna(False).astype(bool)
    c = df["close"]
    if p["stop"] == "mac":
        raw_l, raw_s = df["h1_mac_lo"], df["h1_mac_hi"]
    else:
        raw_l, raw_s = c - p["stop_atr_d"] * df["atr_d"], c + p["stop_atr_d"] * df["atr_d"]
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & fresh_u & ok_l & ses
    short = dn & fresh_d & ok_s & ses
    long, short = _yon(long, short, p, df)
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              max_per_day=p["max_per_day"])
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


# ---------------------------------------------------------------- S15
S15_DEFAULT = dict(adx_min=0, min_risk_cost=0, trend="h4+h1", from_utc=8.0, to_utc=20.0,
                   move_atr=0.7, level="vwap", touch_atr=0.2, stop="swing", stop_buf=0.2,
                   stop_atr_d=0.75, min_atr=0.5, max_atr=12.0, partial_R=None, partial_frac=0.5,
                   target_R=None, yon="long", no_entry_last_min=60)


def s15_trendday_pullback(df: pd.DataFrame, **kw) -> Signals:
    """Trend gününde geri çekilmeden alış: gün açılışından ≥ move_atr·günlük ATR yükselmiş
    (momentum günü) ve üst TF yükselişteyken fiyat VWAP'a / EMA20'ye çekilip yeniden üstünde
    kapanınca al; gün sonunda çık.
    Kaynak: Kathy Lien (momentum + geri çekilmede trend yönünde al; 20 EMA tetik),
    Carole Christensen (VWAP: güçlü hisse VWAP'a döner, VWAP'ı geri alınca alıcılar kontrolde),
    Manny Backus (20 EMA'ya geri çekilme ve oradan dönüş).
    """
    p = {**S15_DEFAULT, **kw}
    up, dn = _trend(df, p["trend"], p["adx_min"])
    c, a = df["close"], df["atr"]
    utc = df.index.hour + df.index.minute / 60
    win = (utc >= p["from_utc"]) & (utc < p["to_utc"])
    strong_l = (df["dhigh"] - df["dopen"]) / df["atr_d"] > p["move_atr"]
    strong_s = (df["dopen"] - df["dlow"]) / df["atr_d"] > p["move_atr"]
    lvl = df["vwap"] if p["level"] == "vwap" else df["ema20"]
    touch_l = (df["low"] - lvl) / a <= p["touch_atr"]
    touch_s = (lvl - df["high"]) / a <= p["touch_atr"]
    rec_l = touch_l.rolling(3).max().fillna(0).astype(bool) & (c > lvl) & (c > df["high"].shift())
    rec_s = touch_s.rolling(3).max().fillna(0).astype(bool) & (c < lvl) & (c < df["low"].shift())
    above = (c > df["dopen"])
    below = (c < df["dopen"])
    if p["stop"] == "swing":
        raw_l = df["low"].rolling(4).min() - p["stop_buf"] * a
        raw_s = df["high"].rolling(4).max() + p["stop_buf"] * a
    else:
        raw_l, raw_s = c - p["stop_atr_d"] * df["atr_d"], c + p["stop_atr_d"] * df["atr_d"]
    ls, ss, ok_l, ok_s = _clamp_stop(df, raw_l, raw_s, p["min_atr"], p["max_atr"], p["min_risk_cost"])
    ses = _session_ok(df, p)
    long = up & win & strong_l & above & rec_l & ok_l & ses
    short = dn & win & strong_s & below & rec_s & ok_s & ses
    long, short = _yon(long, short, p, df)
    ex = dict(partial_R=p["partial_R"], partial_frac=p["partial_frac"], target_R=p["target_R"],
              max_per_day=1)
    return Signals(long.fillna(False), short.fillna(False), ls, ss, ex)


def _yon(long, short, p, df=None):
    # Manny Backus: hisseyi ancak S&P 500 olumluyken al → kripto: BTC 4s trendi aynı yönde
    if p.get("btc_filter") and df is not None and "mkt_h4_up" in df:
        long = long & df["mkt_h4_up"].fillna(False).astype(bool)
        short = short & df["mkt_h4_dn"].fillna(False).astype(bool)
    # Rejim filtresi: rejim=100/200 → BTC günlük kapanışı SMA altındayken yeni alış yok
    if p.get("rejim") and df is not None and f"mkt_d_ok{p['rejim']}" in df:
        long = long & (df[f"mkt_d_ok{p['rejim']}"] != False)  # noqa: E712 (NaN: SMA henüz yok → izin)
    if p.get("yon") == "long":
        return long, short & False
    if p.get("yon") == "short":
        return long & False, short
    return long, short


STRATEGIES = {"S1_pullback": (s1_pullback, S1_DEFAULT),
              "S2_momentum": (s2_momentum, S2_DEFAULT),
              "S3_orb": (s3_orb, S3_DEFAULT),
              "S4_band": (s4_band_reversion, S4_DEFAULT),
              "S5_pdhl": (s5_pdhl_break, S5_DEFAULT),
              "S6_fader": (s6_fader, S6_DEFAULT),
              "S7_vwap": (s7_vwap_reclaim, S7_DEFAULT),
              "S8_camarilla": (s8_camarilla, S8_DEFAULT),
              "S9_session": (s9_session_break, S9_DEFAULT),
              "S10_trendday": (s10_trend_day, S10_DEFAULT),
              # Aynı trend günü mantığı, ABD seansında (NY açılışı + 30 dk) karar
              "S11_trendday_us": (s10_trend_day, {**S10_DEFAULT, "at_utc": 14.0}),
              "S12_strongclose": (s12_strong_close, S12_DEFAULT),
              "S13_falsebreak": (s13_false_break_filter, S13_DEFAULT),
              "S14_mac": (s14_mac, S14_DEFAULT),
              "S15_tdpullback": (s15_trendday_pullback, S15_DEFAULT)}
