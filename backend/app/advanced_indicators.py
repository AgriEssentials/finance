"""
Advanced Technical Analysis Module
Professional-grade indicators for institutional-quality analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class TrendStrength(Enum):
    VERY_STRONG = "Very Strong"
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"
    VERY_WEAK = "Very Weak"


@dataclass
class SupportResistanceLevel:
    price: float
    strength: int  # 1-5 based on number of touches
    type: str  # "support" or "resistance"
    date_formed: str


class AdvancedTechnicalAnalyzer:
    """Professional-grade technical analysis with advanced features"""
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV DataFrame
        
        Args:
            df: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.df = df.copy()
        
    def calculate_fibonacci_retracements(self, high_col: str = 'High', 
                                         low_col: str = 'Low') -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels from recent swing high/low
        
        Returns:
            Dictionary with Fibonacci levels (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)
        """
        # Find recent swing high and low
        recent_period = min(60, len(self.df))
        recent_data = self.df.tail(recent_period)
        
        swing_high = recent_data[high_col].max()
        swing_low = recent_data[low_col].min()
        
        price_range = swing_high - swing_low
        
        fib_levels = {
            '0.0': swing_high,
            '0.236': swing_high - (price_range * 0.236),
            '0.382': swing_high - (price_range * 0.382),
            '0.5': swing_high - (price_range * 0.5),
            '0.618': swing_high - (price_range * 0.618),
            '0.786': swing_high - (price_range * 0.786),
            '1.0': swing_low,
            'swing_high': swing_high,
            'swing_low': swing_low,
            'current_position': (self.df['Close'].iloc[-1] - swing_low) / price_range if price_range > 0 else 0
        }
        
        return {k: round(v, 2) for k, v in fib_levels.items()}
    
    def calculate_volume_profile(self, num_bins: int = 20) -> Dict[str, Any]:
        """
        Calculate Volume Profile - shows volume distribution by price level
        
        Returns:
            Dictionary with POC (Point of Control), Value Area, Volume Nodes
        """
        price_min = self.df['Low'].min()
        price_max = self.df['High'].max()
        
        # Create price bins
        bins = np.linspace(price_min, price_max, num_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        
        # Calculate volume for each bin
        volume_profile = np.zeros(num_bins)
        
        for i in range(len(self.df)):
            row = self.df.iloc[i]
            # Distribute volume across bins that overlap with candle
            candle_low = row['Low']
            candle_high = row['High']
            candle_volume = row['Volume']
            
            for j in range(num_bins):
                bin_low = bins[j]
                bin_high = bins[j + 1]
                
                # Calculate overlap
                overlap_low = max(candle_low, bin_low)
                overlap_high = min(candle_high, bin_high)
                
                if overlap_high > overlap_low:
                    overlap_ratio = (overlap_high - overlap_low) / (candle_high - candle_low)
                    volume_profile[j] += candle_volume * overlap_ratio
        
        # Point of Control (highest volume price)
        poc_idx = np.argmax(volume_profile)
        poc_price = bin_centers[poc_idx]
        
        # Value Area (70% of volume)
        total_volume = volume_profile.sum()
        sorted_indices = np.argsort(volume_profile)[::-1]
        cumulative_volume = 0
        value_area_bins = []
        
        for idx in sorted_indices:
            cumulative_volume += volume_profile[idx]
            value_area_bins.append(idx)
            if cumulative_volume >= total_volume * 0.7:
                break
        
        value_area_high = bin_centers[max(value_area_bins)]
        value_area_low = bin_centers[min(value_area_bins)]
        
        # Find High Volume Nodes (HVN) and Low Volume Nodes (LVN)
        avg_volume = volume_profile.mean()
        hvn_indices = np.where(volume_profile > avg_volume * 1.5)[0]
        lvn_indices = np.where(volume_profile < avg_volume * 0.5)[0]
        
        return {
            'poc': round(poc_price, 2),
            'value_area_high': round(value_area_high, 2),
            'value_area_low': round(value_area_low, 2),
            'value_area_range': round(value_area_high - value_area_low, 2),
            'high_volume_nodes': [round(bin_centers[i], 2) for i in hvn_indices],
            'low_volume_nodes': [round(bin_centers[i], 2) for i in lvn_indices],
            'price_range': round(price_max - price_min, 2),
            'volume_profile': volume_profile.tolist(),
            'bin_centers': bin_centers.tolist()
        }
    
    def detect_market_structure(self) -> Dict[str, Any]:
        """
        Detect market structure - higher highs/higher lows or lower highs/lower lows
        
        Returns:
            Dictionary with swing points and trend structure
        """
        closes = self.df['Close'].values
        highs = self.df['High'].values
        lows = self.df['Low'].values
        
        # Find swing highs and lows using a window of 3
        window = 3
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(self.df) - window):
            # Check if this is a swing high
            if all(highs[i] > highs[i-j] for j in range(1, window+1)) and \
               all(highs[i] > highs[i+j] for j in range(1, window+1)):
                swing_highs.append({
                    'index': i,
                    'price': float(highs[i]),
                    'date': str(self.df.index[i])
                })
            
            # Check if this is a swing low
            if all(lows[i] < lows[i-j] for j in range(1, window+1)) and \
               all(lows[i] < lows[i+j] for j in range(1, window+1)):
                swing_lows.append({
                    'index': i,
                    'price': float(lows[i]),
                    'date': str(self.df.index[i])
                })
        
        # Analyze structure
        structure = {
            'swing_highs': swing_highs[-5:] if len(swing_highs) >= 5 else swing_highs,
            'swing_lows': swing_lows[-5:] if len(swing_lows) >= 5 else swing_lows,
            'higher_highs': False,
            'higher_lows': False,
            'lower_highs': False,
            'lower_lows': False,
            'structure_type': 'Undefined'
        }
        
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            # Check for higher highs
            if swing_highs[-1]['price'] > swing_highs[-2]['price']:
                structure['higher_highs'] = True
            else:
                structure['lower_highs'] = True
            
            # Check for higher lows
            if swing_lows[-1]['price'] > swing_lows[-2]['price']:
                structure['higher_lows'] = True
            else:
                structure['lower_lows'] = True
            
            # Determine structure type
            if structure['higher_highs'] and structure['higher_lows']:
                structure['structure_type'] = 'Uptrend (Bullish)'
            elif structure['lower_highs'] and structure['lower_lows']:
                structure['structure_type'] = 'Downtrend (Bearish)'
            elif structure['higher_highs'] and structure['lower_lows']:
                structure['structure_type'] = 'Distribution Phase'
            elif structure['lower_highs'] and structure['higher_lows']:
                structure['structure_type'] = 'Accumulation Phase'
            else:
                structure['structure_type'] = 'Consolidation'
        
        return structure
    
    def calculate_trend_strength(self) -> Dict[str, Any]:
        """
        Calculate trend strength using ADX and directional movement
        
        Returns:
            Dictionary with trend strength metrics
        """
        import pandas_ta as ta
        
        # Calculate ADX
        adx = ta.adx(self.df['High'], self.df['Low'], self.df['Close'], length=14)
        
        if adx is None or len(adx) == 0:
            return {
                'adx': 0,
                'trend_strength': 'Undefined',
                'di_plus': 0,
                'di_minus': 0,
                'trend_direction': 'Neutral'
            }
        
        current_adx = adx['ADX_14'].iloc[-1]
        di_plus = adx['DMP_14'].iloc[-1]
        di_minus = adx['DMN_14'].iloc[-1]
        
        # Determine trend strength
        if pd.isna(current_adx):
            trend_strength = 'Undefined'
        elif current_adx > 40:
            trend_strength = TrendStrength.VERY_STRONG.value
        elif current_adx > 25:
            trend_strength = TrendStrength.STRONG.value
        elif current_adx > 20:
            trend_strength = TrendStrength.MODERATE.value
        elif current_adx > 15:
            trend_strength = TrendStrength.WEAK.value
        else:
            trend_strength = TrendStrength.VERY_WEAK.value
        
        # Determine trend direction
        if di_plus > di_minus:
            trend_direction = 'Bullish'
        elif di_minus > di_plus:
            trend_direction = 'Bearish'
        else:
            trend_direction = 'Neutral'
        
        return {
            'adx': round(float(current_adx), 2) if not pd.isna(current_adx) else 0,
            'trend_strength': trend_strength,
            'di_plus': round(float(di_plus), 2) if not pd.isna(di_plus) else 0,
            'di_minus': round(float(di_minus), 2) if not pd.isna(di_minus) else 0,
            'trend_direction': trend_direction
        }
    
    def detect_divergence(self) -> Dict[str, Any]:
        """
        Detect bullish and bearish divergences between price and RSI/MACD
        
        Returns:
            Dictionary with detected divergences
        """
        import pandas_ta as ta
        
        # Calculate RSI and MACD
        rsi = ta.rsi(self.df['Close'], length=14)
        macd = ta.macd(self.df['Close'])
        
        divergences = {
            'bullish_rsi': False,
            'bearish_rsi': False,
            'bullish_macd': False,
            'bearish_macd': False,
            'description': ''
        }
        
        if rsi is None or len(rsi) < 20:
            return divergences
        
        # Get recent price and RSI values
        recent_window = 20
        prices = self.df['Close'].tail(recent_window).values
        rsi_values = rsi.tail(recent_window).values
        
        # Check for bullish RSI divergence (price makes lower low, RSI makes higher low)
        price_low_idx = np.argmin(prices)
        rsi_low_idx = np.argmin(rsi_values)
        
        if price_low_idx < rsi_low_idx and prices[-1] > prices[price_low_idx]:
            if rsi_values[rsi_low_idx] > rsi_values[price_low_idx]:
                divergences['bullish_rsi'] = True
                divergences['description'] += 'Bullish RSI divergence detected. '
        
        # Check for bearish RSI divergence (price makes higher high, RSI makes lower high)
        price_high_idx = np.argmax(prices)
        rsi_high_idx = np.argmax(rsi_values)
        
        if price_high_idx < rsi_high_idx and prices[-1] < prices[price_high_idx]:
            if rsi_values[rsi_high_idx] < rsi_values[price_high_idx]:
                divergences['bearish_rsi'] = True
                divergences['description'] += 'Bearish RSI divergence detected. '
        
        return divergences
    
    def calculate_pivot_points(self) -> Dict[str, float]:
        """
        Calculate Pivot Points (Classic, Fibonacci, and Camarilla)
        
        Returns:
            Dictionary with all pivot point levels
        """
        # Get previous day's/week's data
        prev_high = self.df['High'].iloc[-2]
        prev_low = self.df['Low'].iloc[-2]
        prev_close = self.df['Close'].iloc[-2]
        
        # Classic Pivot Points
        pivot = (prev_high + prev_low + prev_close) / 3
        
        classic = {
            'pivot': round(pivot, 2),
            'r1': round(2 * pivot - prev_low, 2),
            'r2': round(pivot + (prev_high - prev_low), 2),
            'r3': round(prev_high + 2 * (pivot - prev_low), 2),
            's1': round(2 * pivot - prev_high, 2),
            's2': round(pivot - (prev_high - prev_low), 2),
            's3': round(prev_low - 2 * (prev_high - pivot), 2)
        }
        
        # Fibonacci Pivot Points
        range_val = prev_high - prev_low
        fib_pivot = {
            'pivot': round(pivot, 2),
            'r1': round(pivot + 0.382 * range_val, 2),
            'r2': round(pivot + 0.618 * range_val, 2),
            'r3': round(pivot + 1.0 * range_val, 2),
            's1': round(pivot - 0.382 * range_val, 2),
            's2': round(pivot - 0.618 * range_val, 2),
            's3': round(pivot - 1.0 * range_val, 2)
        }
        
        return {
            'classic': classic,
            'fibonacci': fib_pivot,
            'previous_high': round(prev_high, 2),
            'previous_low': round(prev_low, 2),
            'previous_close': round(prev_close, 2)
        }
    
    def get_all_advanced_indicators(self) -> Dict[str, Any]:
        """
        Get all advanced technical indicators in one call
        
        Returns:
            Dictionary with all advanced analysis
        """
        return {
            'fibonacci_retracements': self.calculate_fibonacci_retracements(),
            'volume_profile': self.calculate_volume_profile(),
            'market_structure': self.detect_market_structure(),
            'trend_strength': self.calculate_trend_strength(),
            'divergence': self.detect_divergence(),
            'pivot_points': self.calculate_pivot_points()
        }


def get_support_resistance_zones(df: pd.DataFrame, num_levels: int = 3) -> Dict[str, List[SupportResistanceLevel]]:
    """
    Identify key support and resistance zones using multiple methods
    
    Args:
        df: OHLCV DataFrame
        num_levels: Number of support/resistance levels to return
        
    Returns:
        Dictionary with support and resistance levels
    """
    # Method 1: Swing highs/lows
    highs = df['High'].values
    lows = df['Low'].values
    
    window = 5
    swing_highs = []
    swing_lows = []
    
    for i in range(window, len(df) - window):
        # Swing high
        if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, window+1)):
            swing_highs.append((i, highs[i]))
        
        # Swing low
        if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, window+1)):
            swing_lows.append((i, lows[i]))
    
    # Method 2: Volume Profile POC and Value Area
    analyzer = AdvancedTechnicalAnalyzer(df)
    vol_profile = analyzer.calculate_volume_profile()
    
    # Combine and cluster levels
    resistance_prices = [p for _, p in swing_highs[-10:]]
    support_prices = [p for _, p in swing_lows[-10:]]
    
    # Add volume profile levels
    if vol_profile['poc']:
        support_prices.append(vol_profile['poc'])
    
    # Sort and return top levels
    resistance_prices = sorted(set([round(p, 2) for p in resistance_prices]), reverse=True)
    support_prices = sorted(set([round(p, 2) for p in support_prices]))
    
    # Get current price
    current_price = df['Close'].iloc[-1]
    
    # Filter to get relevant levels (above/below current price)
    resistances = [p for p in resistance_prices if p > current_price][:num_levels]
    supports = [p for p in support_prices if p < current_price][:num_levels]
    
    # Format as SupportResistanceLevel objects
    support_levels = [
        SupportResistanceLevel(
            price=p,
            strength=3,
            type='support',
            date_formed=str(df.index[-1])
        ) for p in supports
    ]
    
    resistance_levels = [
        SupportResistanceLevel(
            price=p,
            strength=3,
            type='resistance',
            date_formed=str(df.index[-1])
        ) for p in resistances
    ]
    
    return {
        'support_levels': support_levels,
        'resistance_levels': resistance_levels,
        'poc': vol_profile.get('poc'),
        'value_area_high': vol_profile.get('value_area_high'),
        'value_area_low': vol_profile.get('value_area_low')
    }
