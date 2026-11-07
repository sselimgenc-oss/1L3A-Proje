from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from .data import validate_ohlcv
from .indicators import (
    bollinger_bands,
    ema,
    rate_of_change,
    rsi,
    supertrend_direction,
)

MTFSignalFunction = Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class MTFStrategyInfo:
    strategy_id: str
    name: str
    architecture: str
    base_interval: str
    family: str
    rule_summary: str
    pdf_basis: str


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


def _resample_completed(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate bars with labels at the first instant the completed bar is knowable."""
    data = validate_ohlcv(frame)
    resampled = data.resample(rule, label="right", closed="left", origin="start_day").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    resampled = resampled.dropna(subset=["open", "high", "low", "close"])
    # A bucket whose right boundary is after the last base timestamp is not complete yet.
    return resampled.loc[resampled.index <= data.index[-1]]


def _align_completed(values: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    return values.reindex(index, method="ffill")


def _weekly_direction(frame: pd.DataFrame) -> pd.Series:
    weekly = _resample_completed(frame, "W-MON")
    direction = (weekly["close"] > ema(weekly["close"], 20)) & (
        ema(weekly["close"], 20) > ema(weekly["close"], 40)
    )
    return _align_completed(direction, frame.index).eq(True)


def _daily_and_four_hour_direction(frame: pd.DataFrame) -> pd.Series:
    daily = _resample_completed(frame, "1D")
    four_hour = _resample_completed(frame, "4h")
    daily_up = (daily["close"] > ema(daily["close"], 20)) & (
        ema(daily["close"], 20) > ema(daily["close"], 50)
    )
    four_hour_up = (four_hour["close"] > ema(four_hour["close"], 20)) & (
        ema(four_hour["close"], 20) > ema(four_hour["close"], 50)
    )
    return _align_completed(daily_up, frame.index).eq(True) & _align_completed(
        four_hour_up, frame.index
    ).eq(True)


def weekly_daily_breakout(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"]
    direction = _weekly_direction(frame)
    prior_high = frame["high"].rolling(20, min_periods=20).max().shift(1)
    prior_low = frame["low"].rolling(10, min_periods=10).min().shift(1)
    entry = direction & (close > prior_high)
    exit_ = ~direction | (close < prior_low) | (close < ema(close, 20))
    return _long_state(entry, exit_)


def weekly_daily_pullback(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"]
    fast = ema(close, 20)
    slow = ema(close, 50)
    direction = _weekly_direction(frame)
    recovered = (close > fast) & (close.shift(1) <= fast.shift(1))
    entry = direction & (fast > slow) & recovered & (rsi(close, 14) > 50)
    exit_ = ~direction | (close < slow) | (rsi(close, 14) < 40)
    return _long_state(entry, exit_)


def weekly_daily_reversion(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"]
    middle, _, lower = bollinger_bands(close, 20, 2.0)
    short_rsi = rsi(close, 2)
    direction = _weekly_direction(frame)
    entry = direction & (close < lower) & (short_rsi < 10)
    exit_ = ~direction | (close >= middle) | (short_rsi > 70)
    return _long_state(entry, exit_)


def weekly_daily_momentum(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"]
    direction = _weekly_direction(frame)
    fast = ema(close, 20)
    slow = ema(close, 50)
    entry = direction & (fast > slow) & (rate_of_change(close, 20) > 5)
    exit_ = ~direction | (fast < slow) | (rate_of_change(close, 20) < 0)
    return _long_state(entry, exit_)


def daily_four_hour_pullback(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"]
    fast = ema(close, 20)
    slow = ema(close, 50)
    direction = _daily_and_four_hour_direction(frame)
    recovered = (close > fast) & (close.shift(1) <= fast.shift(1))
    entry = direction & recovered & (fast > slow) & (rsi(close, 14) > 50)
    exit_ = ~direction | (close < slow) | (rsi(close, 14) < 40)
    return _long_state(entry, exit_)


def daily_four_hour_breakout(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"]
    direction = _daily_and_four_hour_direction(frame)
    prior_high = frame["high"].rolling(24, min_periods=24).max().shift(1)
    prior_low = frame["low"].rolling(12, min_periods=12).min().shift(1)
    entry = direction & (close > prior_high)
    exit_ = ~direction | (close < prior_low) | (close < ema(close, 20))
    return _long_state(entry, exit_)


def daily_four_hour_reversion(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"]
    direction = _daily_and_four_hour_direction(frame)
    middle, _, lower = bollinger_bands(close, 20, 2.0)
    short_rsi = rsi(close, 2)
    entry = direction & (close < lower) & (short_rsi < 10)
    exit_ = ~direction | (close >= middle) | (short_rsi > 70)
    return _long_state(entry, exit_)


def daily_four_hour_supertrend(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"]
    direction = _daily_and_four_hour_direction(frame)
    local_trend = supertrend_direction(frame, period=10, multiplier=3.0)
    entry = direction & (local_trend == 1) & (close > ema(close, 50))
    exit_ = ~direction | (local_trend == -1) | (close < ema(close, 50))
    return _long_state(entry, exit_)


MTF_STRATEGIES = (
    MTFStrategyInfo(
        "wd_breakout",
        "Haftalık Rejim + Günlük Kırılım",
        "1W yön → 1D işlem",
        "1d",
        "Trend / Donchian",
        "Haftalık EMA20>EMA40; günlük 20-bar tepe kırılımı, 10-bar dip/EMA20 çıkışı.",
        "PDF kırılım, kanal ve rejim ailelerinin evrensel birleşimi.",
    ),
    MTFStrategyInfo(
        "wd_pullback",
        "Haftalık Rejim + Günlük Geri Çekilme",
        "1W yön → 1D işlem",
        "1d",
        "Trend / pullback",
        "Haftalık yükseliş; günlük EMA20 geri kazanımı ve RSI>50, EMA50/RSI40 çıkışı.",
        "PDF trend filtresi ve momentum devam ailelerinden türetildi.",
    ),
    MTFStrategyInfo(
        "wd_reversion",
        "Haftalık Rejim + Günlük Ortalamaya Dönüş",
        "1W yön → 1D işlem",
        "1d",
        "Rejim / ortalamaya dönüş",
        "Haftalık yükselişte günlük alt Bollinger+RSI2; orta bant/RSI70 çıkışı.",
        "Mean Reversion Setup ve Channel Reversion ailelerinden türetildi.",
    ),
    MTFStrategyInfo(
        "wd_momentum",
        "Haftalık Rejim + Günlük Momentum",
        "1W yön → 1D işlem",
        "1d",
        "Trend / momentum",
        "Haftalık yükseliş; günlük EMA20>50 ve ROC20>%5; ROC<0 veya rejim kaybı çıkışı.",
        "PDF momentum ve trend-rider ailelerinden türetildi.",
    ),
    MTFStrategyInfo(
        "d4h_pullback",
        "Günlük+4S Rejim + 1S Geri Çekilme",
        "1D+4H yön → 1H işlem",
        "1h",
        "Trend / pullback",
        "Günlük ve 4S EMA20>50; 1S EMA20 geri kazanımı, RSI ve EMA50 çıkışı.",
        "PDF çoklu-zaman trend ve momentum ailelerinden türetildi.",
    ),
    MTFStrategyInfo(
        "d4h_breakout",
        "Günlük+4S Rejim + 1S Kırılım",
        "1D+4H yön → 1H işlem",
        "1h",
        "Trend / Donchian",
        "Günlük ve 4S yükseliş; 1S 24-bar tepe kırılımı, 12-bar dip/EMA20 çıkışı.",
        "PDF breakout ve ORB dışı kanal-kırılım ailelerinden türetildi.",
    ),
    MTFStrategyInfo(
        "d4h_reversion",
        "Günlük+4S Rejim + 1S Ortalamaya Dönüş",
        "1D+4H yön → 1H işlem",
        "1h",
        "Rejim / ortalamaya dönüş",
        "Günlük ve 4S yükselişte 1S alt Bollinger+RSI2; orta bant/RSI70 çıkışı.",
        "PDF mean-reversion ve kanal ailelerinden türetildi.",
    ),
    MTFStrategyInfo(
        "d4h_supertrend",
        "Günlük+4S Rejim + 1S SuperTrend",
        "1D+4H yön → 1H işlem",
        "1h",
        "Trend / ATR",
        "Günlük ve 4S yükseliş; 1S SuperTrend+EMA50 giriş ve rejim çıkışı.",
        "PDF SuperTrend ve ATR rejim ailelerinden türetildi.",
    ),
)


MTF_REGISTRY: dict[str, MTFSignalFunction] = {
    "wd_breakout": weekly_daily_breakout,
    "wd_pullback": weekly_daily_pullback,
    "wd_reversion": weekly_daily_reversion,
    "wd_momentum": weekly_daily_momentum,
    "d4h_pullback": daily_four_hour_pullback,
    "d4h_breakout": daily_four_hour_breakout,
    "d4h_reversion": daily_four_hour_reversion,
    "d4h_supertrend": daily_four_hour_supertrend,
}


def generate_mtf_signal(strategy_id: str, frame: pd.DataFrame) -> pd.Series:
    try:
        strategy = MTF_REGISTRY[strategy_id]
    except KeyError as error:
        raise KeyError(f"Bilinmeyen MTF strateji: {strategy_id}") from error
    signal = strategy(validate_ohlcv(frame))
    return signal.reindex(frame.index).fillna(0).clip(0, 1).astype("int64")
