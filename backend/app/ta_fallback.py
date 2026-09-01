"""
Pure-pandas fallback implementations of common technical indicators.

Used when `pandas_ta` is not available (e.g. Python 3.14+ where numba has
no wheels). The function signatures and output column names mirror the
`pandas_ta` calls used across the codebase.
"""

import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int = 9) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=length, adjust=False).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)"""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    return result.fillna(50.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD line, signal line and histogram"""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({
        "MACD_12_26_9": macd_line,
        "MACDs_12_26_9": signal_line,
        "MACDh_12_26_9": histogram,
    })


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average True Range (Wilder's smoothing)"""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def bbands(close: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands (lower, middle, upper)"""
    middle = close.rolling(length).mean()
    deviation = close.rolling(length).std(ddof=0)
    upper = middle + (deviation * std)
    lower = middle - (deviation * std)
    return pd.DataFrame({
        "BBL_20_2.0": lower,
        "BBM_20_2.0": middle,
        "BBU_20_2.0": upper,
    })


def adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """Average Directional Index with +/-DI"""
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr_series = tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()

    plus_di = 100 * (pd.Series(plus_dm, index=high.index).ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / atr_series.replace(0, np.nan))
    minus_di = 100 * (pd.Series(minus_dm, index=high.index).ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / atr_series.replace(0, np.nan))

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx_series = dx.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()

    return pd.DataFrame({
        "DMP_14": plus_di,
        "DMN_14": minus_di,
        "ADX_14": adx_series,
    })