"""
Technical Indicators Module
Handles calculation of all technical indicators for stock analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

# Prefer pandas_ta when available; fall back to pure-pandas implementations
# (needed on Python 3.14+ where numba/pandas_ta cannot be installed).
try:
    import pandas_ta as ta
except ImportError:
    from app import ta_fallback as ta


class TechnicalIndicators:
    """Class to calculate technical indicators for stock data"""
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with stock data DataFrame
        
        Args:
            df: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.df = df.copy()
        
    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        return ta.rsi(self.df['Close'], length=period)
    
    def calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Calculate MACD indicator"""
        macd = ta.macd(self.df['Close'], fast=fast, slow=slow, signal=signal)
        return macd
    
    def calculate_ema(self, period: int) -> pd.Series:
        """Calculate EMA for given period"""
        return ta.ema(self.df['Close'], length=period)
    
    def calculate_atr(self, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        return ta.atr(self.df['High'], self.df['Low'], self.df['Close'], length=period)
    
    def calculate_bollinger_bands(self, period: int = 20, std: int = 2) -> pd.DataFrame:
        """Calculate Bollinger Bands"""
        bb = ta.bbands(self.df['Close'], length=period, std=std)
        # Normalize column names across pandas_ta versions
        rename = {}
        for col in bb.columns:
            low = col.lower()
            if low.startswith('bbl'):
                rename[col] = f'BBL_{period}_{float(std)}'
            elif low.startswith('bbm'):
                rename[col] = f'BBM_{period}_{float(std)}'
            elif low.startswith('bbu'):
                rename[col] = f'BBU_{period}_{float(std)}'
        bb = bb.rename(columns=rename)
        return bb
    
    def detect_volume_spike(self, period: int = 20, threshold: float = 1.5) -> pd.Series:
        """Detect volume spikes"""
        avg_volume = self.df['Volume'].rolling(window=period).mean()
        volume_ratio = self.df['Volume'] / avg_volume
        return volume_ratio > threshold
    
    def get_all_indicators_intraday(self) -> Dict[str, Any]:
        """
        Get all indicators for intraday mode (5m data)
        Returns dict with current values and interpretations
        """
        # Calculate indicators
        self.df['EMA_9'] = self.calculate_ema(9)
        self.df['EMA_21'] = self.calculate_ema(21)
        self.df['RSI'] = self.calculate_rsi(14)
        
        macd_df = self.calculate_macd()
        self.df['MACD'] = macd_df['MACD_12_26_9']
        self.df['MACD_Signal'] = macd_df['MACDs_12_26_9']
        self.df['MACD_Histogram'] = macd_df['MACDh_12_26_9']
        
        self.df['ATR'] = self.calculate_atr(14)
        self.df['Volume_Spike'] = self.detect_volume_spike(20, 1.5)
        
        # Get latest values
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2] if len(self.df) > 1 else latest
        
        # Determine trend
        if latest['EMA_9'] > latest['EMA_21']:
            trend = "Bullish"
        elif latest['EMA_9'] < latest['EMA_21']:
            trend = "Bearish"
        else:
            trend = "Neutral"
        
        # RSI interpretation
        rsi_value = latest['RSI']
        if rsi_value > 70:
            rsi_interp = "Overbought"
        elif rsi_value < 30:
            rsi_interp = "Oversold"
        else:
            rsi_interp = "Neutral"
        
        # MACD status
        if latest['MACD'] > latest['MACD_Signal']:
            macd_status = "Bullish"
        else:
            macd_status = "Bearish"
        
        # Volume analysis
        avg_volume = self.df['Volume'].tail(20).mean()
        volume_ratio = latest['Volume'] / avg_volume if avg_volume > 0 else 1
        
        return {
            "trend": trend,
            "rsi": round(rsi_value, 2),
            "rsi_interpretation": rsi_interp,
            "macd": round(latest['MACD'], 4),
            "macd_signal": round(latest['MACD_Signal'], 4),
            "macd_status": macd_status,
            "macd_histogram": round(latest['MACD_Histogram'], 4),
            "ema_9": round(latest['EMA_9'], 2),
            "ema_21": round(latest['EMA_21'], 2),
            "atr": round(latest['ATR'], 2),
            "current_price": round(latest['Close'], 2),
            "volume_ratio": round(volume_ratio, 2),
            "volume_spike": bool(latest['Volume_Spike']),
            "dataframe": self.df
        }
    
    def get_all_indicators_swing(self) -> Dict[str, Any]:
        """
        Get all indicators for swing mode (daily data)
        """
        # Calculate indicators
        self.df['EMA_20'] = self.calculate_ema(20)
        self.df['EMA_50'] = self.calculate_ema(50)
        self.df['RSI'] = self.calculate_rsi(14)
        
        macd_df = self.calculate_macd()
        self.df['MACD'] = macd_df['MACD_12_26_9']
        self.df['MACD_Signal'] = macd_df['MACDs_12_26_9']
        self.df['MACD_Histogram'] = macd_df['MACDh_12_26_9']
        
        bb_df = self.calculate_bollinger_bands()
        self.df['BB_Upper'] = bb_df['BBU_20_2.0']
        self.df['BB_Lower'] = bb_df['BBL_20_2.0']
        self.df['BB_Middle'] = bb_df['BBM_20_2.0']
        
        self.df['ATR'] = self.calculate_atr(14)
        
        # Get support and resistance levels
        support, resistance = self._calculate_support_resistance()
        
        # Get latest values
        latest = self.df.iloc[-1]
        
        # Determine trend
        if latest['EMA_20'] > latest['EMA_50']:
            trend = "Bullish"
        elif latest['EMA_20'] < latest['EMA_50']:
            trend = "Bearish"
        else:
            trend = "Neutral"
        
        # RSI interpretation
        rsi_value = latest['RSI']
        if rsi_value > 70:
            rsi_interp = "Overbought"
        elif rsi_value < 30:
            rsi_interp = "Oversold"
        else:
            rsi_interp = "Neutral"
        
        # MACD status
        if latest['MACD'] > latest['MACD_Signal']:
            macd_status = "Bullish"
        else:
            macd_status = "Bearish"
        
        # Volume analysis
        avg_volume = self.df['Volume'].tail(20).mean()
        volume_ratio = latest['Volume'] / avg_volume if avg_volume > 0 else 1
        
        # Bollinger Bands position
        bb_position = "Middle"
        if latest['Close'] > latest['BB_Upper']:
            bb_position = "Above Upper"
        elif latest['Close'] < latest['BB_Lower']:
            bb_position = "Below Lower"
        elif latest['Close'] > latest['BB_Middle']:
            bb_position = "Upper Half"
        else:
            bb_position = "Lower Half"
        
        return {
            "trend": trend,
            "rsi": round(rsi_value, 2),
            "rsi_interpretation": rsi_interp,
            "macd": round(latest['MACD'], 4),
            "macd_signal": round(latest['MACD_Signal'], 4),
            "macd_status": macd_status,
            "macd_histogram": round(latest['MACD_Histogram'], 4),
            "ema_20": round(latest['EMA_20'], 2),
            "ema_50": round(latest['EMA_50'], 2),
            "bb_upper": round(latest['BB_Upper'], 2),
            "bb_lower": round(latest['BB_Lower'], 2),
            "bb_middle": round(latest['BB_Middle'], 2),
            "bb_position": bb_position,
            "support": support,
            "resistance": resistance,
            "atr": round(latest['ATR'], 2),
            "current_price": round(latest['Close'], 2),
            "volume_ratio": round(volume_ratio, 2),
            "dataframe": self.df
        }
    
    def get_all_indicators_longterm(self) -> Dict[str, Any]:
        """
        Get all indicators for long-term mode (weekly data)
        """
        # Calculate indicators
        self.df['EMA_20'] = self.calculate_ema(20)
        self.df['EMA_50'] = self.calculate_ema(50)
        self.df['EMA_200'] = self.calculate_ema(200)
        self.df['RSI'] = self.calculate_rsi(14)
        
        macd_df = self.calculate_macd()
        self.df['MACD'] = macd_df['MACD_12_26_9']
        self.df['MACD_Signal'] = macd_df['MACDs_12_26_9']
        self.df['MACD_Histogram'] = macd_df['MACDh_12_26_9']
        
        self.df['ATR'] = self.calculate_atr(14)
        
        # Calculate volatility (standard deviation of returns)
        self.df['Returns'] = self.df['Close'].pct_change()
        volatility = self.df['Returns'].tail(20).std() * np.sqrt(52)  # Annualized
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()
        
        # Get latest values
        latest = self.df.iloc[-1]
        
        # Determine trend (handle case where EMA_200 is None - not enough data)
        ema_200_value = latest['EMA_200']
        if pd.isna(ema_200_value):
            # Fall back to EMA_50 for trend determination
            if latest['Close'] > latest['EMA_50']:
                trend = "Bullish"
            elif latest['Close'] < latest['EMA_50']:
                trend = "Bearish"
            else:
                trend = "Neutral"
        elif latest['Close'] > ema_200_value:
            if latest['EMA_50'] > ema_200_value:
                trend = "Strong Bullish"
            else:
                trend = "Bullish"
        elif latest['Close'] < ema_200_value:
            if latest['EMA_50'] < ema_200_value:
                trend = "Strong Bearish"
            else:
                trend = "Bearish"
        else:
            trend = "Neutral"
        
        # RSI interpretation
        rsi_value = latest['RSI']
        if rsi_value > 70:
            rsi_interp = "Overbought"
        elif rsi_value < 30:
            rsi_interp = "Oversold"
        else:
            rsi_interp = "Neutral"
        
        # MACD status
        if latest['MACD'] > latest['MACD_Signal']:
            macd_status = "Bullish"
        else:
            macd_status = "Bearish"
        
        # Volume analysis
        avg_volume = self.df['Volume'].tail(20).mean()
        volume_ratio = latest['Volume'] / avg_volume if avg_volume > 0 else 1
        
        return {
            "trend": trend,
            "rsi": round(rsi_value, 2),
            "rsi_interpretation": rsi_interp,
            "macd": round(latest['MACD'], 4),
            "macd_signal": round(latest['MACD_Signal'], 4),
            "macd_status": macd_status,
            "macd_histogram": round(latest['MACD_Histogram'], 4),
            "ema_20": round(latest['EMA_20'], 2),
            "ema_50": round(latest['EMA_50'], 2),
            "ema_200": round(latest['EMA_200'], 2) if pd.notna(latest['EMA_200']) else None,
            "atr": round(latest['ATR'], 2),
            "volatility": round(volatility * 100, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "current_price": round(latest['Close'], 2),
            "volume_ratio": round(volume_ratio, 2),
            "dataframe": self.df
        }
    
    def _calculate_support_resistance(self, window: int = 20) -> tuple:
        """Calculate support and resistance levels"""
        recent_data = self.df.tail(window)
        
        # Simple approach: use recent lows for support, recent highs for resistance
        support = recent_data['Low'].min()
        resistance = recent_data['High'].max()
        
        return round(support, 2), round(resistance, 2)
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from peak"""
        cummax = self.df['Close'].cummax()
        drawdown = (self.df['Close'] - cummax) / cummax
        return drawdown.min()


def prepare_ml_features(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    """
    Prepare features for ML model
    
    Args:
        df: DataFrame with indicators
        mode: 'intraday', 'swing', or 'longterm'
    
    Returns:
        DataFrame with features
    """
    features = pd.DataFrame(index=df.index)
    
    # Common features
    features['rsi'] = df['RSI']
    features['macd_histogram'] = df['MACD_Histogram']
    features['volume_ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    features['atr'] = df['ATR']
    
    # Mode-specific features
    if mode == 'intraday':
        features['ema_diff'] = (df['EMA_9'] - df['EMA_21']) / df['Close']
    else:
        features['ema_diff'] = (df['EMA_20'] - df['EMA_50']) / df['Close']
        if 'EMA_200' in df.columns and df['EMA_200'].notna().any():
            features['above_200ema'] = (df['Close'] > df['EMA_200']).fillna(0).astype(int)
    
    # Clean data
    features = features.fillna(0)
    features = features.replace([np.inf, -np.inf], 0)
    
    return features