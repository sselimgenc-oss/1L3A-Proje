from __future__ import annotations

import numpy as np
import pandas as pd


def sma(values: pd.Series, period: int) -> pd.Series:
    return values.rolling(period, min_periods=period).mean()


def ema(values: pd.Series, period: int) -> pd.Series:
    return values.ewm(span=period, adjust=False, min_periods=period).mean()


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous_close = frame["close"].shift(1)
    ranges = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    return true_range(frame).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def rsi(values: pd.Series, period: int = 14) -> pd.Series:
    delta = values.diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    relative_strength = gains / losses.replace(0, np.nan)
    result = 100 - (100 / (1 + relative_strength))
    return result.where(losses.ne(0), 100.0).fillna(50.0)


def rate_of_change(values: pd.Series, period: int) -> pd.Series:
    return (values / values.shift(period) - 1) * 100


def cci(frame: pd.DataFrame, period: int = 20) -> pd.Series:
    typical = (frame["high"] + frame["low"] + frame["close"]) / 3
    average = sma(typical, period)
    mean_deviation = typical.rolling(period, min_periods=period).apply(
        lambda values: np.mean(np.abs(values - values.mean())), raw=True
    )
    return (typical - average) / (0.015 * mean_deviation.replace(0, np.nan))


def money_flow_index(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    typical = (frame["high"] + frame["low"] + frame["close"]) / 3
    raw_flow = typical * frame["volume"]
    direction = typical.diff()
    positive = raw_flow.where(direction > 0, 0.0).rolling(period, min_periods=period).sum()
    negative = raw_flow.where(direction < 0, 0.0).rolling(period, min_periods=period).sum()
    ratio = positive / negative.replace(0, np.nan)
    result = 100 - (100 / (1 + ratio))
    return result.where(negative.ne(0), 100.0).fillna(50.0)


def weighted_moving_average(values: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1, dtype=float)
    denominator = weights.sum()
    return values.rolling(period, min_periods=period).apply(
        lambda window: float(np.dot(window, weights) / denominator), raw=True
    )


def hull_moving_average(values: pd.Series, period: int) -> pd.Series:
    half = max(1, period // 2)
    root = max(1, int(np.sqrt(period)))
    raw = 2 * weighted_moving_average(values, half) - weighted_moving_average(values, period)
    return weighted_moving_average(raw, root)


def bollinger_bands(
    values: pd.Series, period: int = 20, deviations: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = sma(values, period)
    deviation = values.rolling(period, min_periods=period).std(ddof=0)
    return middle, middle + deviations * deviation, middle - deviations * deviation


def supertrend_direction(
    frame: pd.DataFrame, period: int = 10, multiplier: float = 3.0
) -> pd.Series:
    volatility = atr(frame, period)
    midpoint = (frame["high"] + frame["low"]) / 2
    basic_upper = midpoint + multiplier * volatility
    basic_lower = midpoint - multiplier * volatility
    upper = basic_upper.copy()
    lower = basic_lower.copy()
    direction = pd.Series(0, index=frame.index, dtype="int64")

    first_valid = volatility.first_valid_index()
    if first_valid is None:
        return direction
    start = frame.index.get_loc(first_valid)
    direction.iloc[start] = 1

    for index in range(start + 1, len(frame)):
        previous = index - 1
        if (
            basic_upper.iloc[index] < upper.iloc[previous]
            or frame["close"].iloc[previous] > upper.iloc[previous]
        ):
            upper.iloc[index] = basic_upper.iloc[index]
        else:
            upper.iloc[index] = upper.iloc[previous]

        if (
            basic_lower.iloc[index] > lower.iloc[previous]
            or frame["close"].iloc[previous] < lower.iloc[previous]
        ):
            lower.iloc[index] = basic_lower.iloc[index]
        else:
            lower.iloc[index] = lower.iloc[previous]

        previous_direction = direction.iloc[previous]
        if previous_direction >= 0:
            direction.iloc[index] = -1 if frame["close"].iloc[index] < lower.iloc[index] else 1
        else:
            direction.iloc[index] = 1 if frame["close"].iloc[index] > upper.iloc[index] else -1

    return direction
