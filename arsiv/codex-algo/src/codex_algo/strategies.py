from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from .indicators import (
    atr,
    bollinger_bands,
    cci,
    ema,
    hull_moving_average,
    money_flow_index,
    rate_of_change,
    rsi,
    sma,
    supertrend_direction,
)

SignalFunction = Callable[[pd.DataFrame], pd.Series]


def _long_state(entry: pd.Series, exit_: pd.Series) -> pd.Series:
    state = 0
    values: list[int] = []
    for should_enter, should_exit in zip(entry.fillna(False), exit_.fillna(False), strict=True):
        if state == 0 and bool(should_enter):
            state = 1
        elif state == 1 and bool(should_exit):
            state = 0
        values.append(state)
    return pd.Series(values, index=entry.index, dtype="int64")


def compression_breakout(frame: pd.DataFrame) -> pd.Series:
    """PDF'deki Compression Breakout adayının açık, günlük Codex uyarlaması."""
    close = frame["close"]
    middle, upper, lower = bollinger_bands(close, 20, 2.0)
    bandwidth = (upper - lower) / middle.replace(0, pd.NA)
    compression_threshold = bandwidth.rolling(120, min_periods=60).quantile(0.20)
    recently_compressed = (
        (bandwidth <= compression_threshold).rolling(10).max().fillna(0).astype(bool)
    )
    prior_high = frame["high"].rolling(20, min_periods=20).max().shift(1)
    prior_low = frame["low"].rolling(10, min_periods=10).min().shift(1)
    volume_average = frame["volume"].rolling(20, min_periods=20).mean()
    trend = (ema(close, 50) > ema(close, 200)) & (close > ema(close, 50))
    volume_ok = frame["volume"] >= volume_average
    entry = recently_compressed & trend & volume_ok & (close > prior_high)
    exit_ = (close < ema(close, 20)) | (close < prior_low) | ~trend
    return _long_state(entry, exit_)


def channel_reversion(frame: pd.DataFrame) -> pd.Series:
    """PDF'deki Channel Reversion adayının uzun-yönlü Codex uyarlaması."""
    close = frame["close"]
    middle, _, lower = bollinger_bands(close, 20, 2.0)
    short_rsi = rsi(close, 2)
    long_trend = close > ema(close, 200)
    entry = long_trend & (close < lower) & (short_rsi < 10)
    exit_ = (close >= middle) | (short_rsi > 70) | ~long_trend
    return _long_state(entry, exit_)


def supertrend_regime(frame: pd.DataFrame) -> pd.Series:
    """PDF'deki SuperTrend Regime adayının kaldıraçsız Codex uyarlaması."""
    close = frame["close"]
    regime = supertrend_direction(frame, period=10, multiplier=3.0)
    trend_filter = ema(close, 50) > ema(close, 200)
    entry = (regime == 1) & trend_filter
    exit_ = (regime == -1) | ~trend_filter
    return _long_state(entry, exit_)


def fractal_breakout(frame: pd.DataFrame) -> pd.Series:
    """PDF'deki Fractal Breakout adayının günlük kanal-kırılım Codex uyarlaması."""
    close = frame["close"]
    breakout = frame["high"].rolling(20, min_periods=20).max().shift(1)
    trailing_low = frame["low"].rolling(10, min_periods=10).min().shift(1)
    trend_filter = (close > ema(close, 100)) & (ema(close, 50) > ema(close, 200))
    volatility_ok = atr(frame, 14) / close < 0.12
    entry = (close > breakout) & trend_filter & volatility_ok
    exit_ = (close < trailing_low) | (close < ema(close, 50))
    return _long_state(entry, exit_)


def macd_sma200(frame: pd.DataFrame) -> pd.Series:
    """Popüler PDF listesindeki MACD + SMA200 adayının açık Codex uyarlaması."""
    close = frame["close"]
    macd = ema(close, 12) - ema(close, 26)
    macd_signal = ema(macd, 9)
    bullish_cross = (macd > macd_signal) & (macd.shift(1) <= macd_signal.shift(1))
    bearish_cross = (macd < macd_signal) & (macd.shift(1) >= macd_signal.shift(1))
    trend = close > sma(close, 200)
    return _long_state(bullish_cross & trend, bearish_cross | ~trend)


def ao_ac_zones(frame: pd.DataFrame) -> pd.Series:
    """PDF'deki AO/AC Trading Zones adayının standart gösterge formüllü uyarlaması."""
    median_price = (frame["high"] + frame["low"]) / 2
    awesome = sma(median_price, 5) - sma(median_price, 34)
    acceleration = awesome - sma(awesome, 5)
    positive_zone = (awesome > 0) & (acceleration > 0) & (awesome.diff() > 0)
    negative_zone = (awesome < 0) | (acceleration < 0)
    return _long_state(positive_zone, negative_zone)


def kst_momentum(frame: pd.DataFrame) -> pd.Series:
    """PDF KST adayının standart Pring KST formüllü, uzun/nakit Codex uyarlaması."""
    close = frame["close"]
    kst = (
        sma(rate_of_change(close, 10), 10)
        + 2 * sma(rate_of_change(close, 15), 10)
        + 3 * sma(rate_of_change(close, 20), 10)
        + 4 * sma(rate_of_change(close, 30), 15)
    )
    signal = sma(kst, 9)
    bullish_cross = (kst > signal) & (kst.shift(1) <= signal.shift(1))
    bearish_cross = (kst < signal) & (kst.shift(1) >= signal.shift(1))
    trend = close > ema(close, 200)
    return _long_state(bullish_cross & (kst > 0) & trend, bearish_cross | ~trend)


def triple_cci_mfi(frame: pd.DataFrame) -> pd.Series:
    """PDF Triple CCI + MFI adayının sabit parametreli Codex uyarlaması."""
    short = cci(frame, 20)
    medium = cci(frame, 40)
    long = cci(frame, 80)
    flow = money_flow_index(frame, 14)
    entry = (short > 0) & (medium > 0) & (long > 0) & (flow > 55)
    exit_ = ((short < 0) & (medium < 0)) | (flow < 45)
    return _long_state(entry, exit_)


def double_cci_hma(frame: pd.DataFrame) -> pd.Series:
    """PDF Double CCI + HMA adayının sabit parametreli Codex uyarlaması."""
    close = frame["close"]
    short = cci(frame, 20)
    long = cci(frame, 50)
    hull = hull_moving_average(close, 55)
    entry = (short > 0) & (long > 0) & (close > hull) & (hull.diff() > 0)
    exit_ = ((short < 0) & (long < 0)) | (close < hull)
    return _long_state(entry, exit_)


REGISTRY: dict[str, SignalFunction] = {
    "compression_breakout": compression_breakout,
    "channel_reversion": channel_reversion,
    "supertrend_regime": supertrend_regime,
    "fractal_breakout": fractal_breakout,
    "macd_sma200": macd_sma200,
    "ao_ac_zones": ao_ac_zones,
    "kst_momentum": kst_momentum,
    "triple_cci_mfi": triple_cci_mfi,
    "double_cci_hma": double_cci_hma,
}


def generate_signal(strategy_id: str, frame: pd.DataFrame) -> pd.Series:
    try:
        strategy = REGISTRY[strategy_id]
    except KeyError as error:
        raise KeyError(f"Bilinmeyen strateji: {strategy_id}") from error
    signal = strategy(frame)
    return signal.reindex(frame.index).fillna(0).clip(0, 1).astype("int64")
