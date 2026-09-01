"""
Backtesting Engine for Trading Strategy Validation
Test strategies on historical data
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Callable, Tuple
from dataclasses import dataclass
from enum import Enum


class ActionEnum(Enum):
    """Trading actions"""
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class BacktestResult:
    """Backtest results"""
    strategy_name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    profit_per_trade: float


class BacktestEngine:
    """Backtest trading strategies on historical data"""
    
    def __init__(self, initial_capital: float = 100000, commission: float = 0.001):
        """
        Initialize backtest engine
        
        Args:
            initial_capital: Starting capital in INR
            commission: Commission per trade (0.1%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_strategy(self, prices: np.ndarray, signals: np.ndarray,
                    strategy_name: str = "Custom") -> BacktestResult:
        """
        Run backtest on historical prices with buy/sell signals
        
        Args:
            prices: Array of historical prices
            signals: Array of signals (1=BUY, -1=SELL, 0=HOLD)
            strategy_name: Name of strategy
        
        Returns:
            BacktestResult object
        """
        portfolio_values = [self.initial_capital]
        shares = 0
        position_price = 0
        trades = []
        
        for i in range(1, len(prices)):
            signal = signals[i]
            price = prices[i]
            
            if signal == 1 and shares == 0:  # BUY signal
                buy_amount = portfolio_values[-1] * 0.95  # Use 95% of capital
                shares = buy_amount / price
                position_price = price
                trades.append({
                    "type": "BUY",
                    "price": price,
                    "shares": shares,
                    "date": i
                })
            
            elif signal == -1 and shares > 0:  # SELL signal
                sell_value = shares * price * (1 - self.commission)
                portfolio_values.append(portfolio_values[-1] + (sell_value - (shares * position_price)))
                shares = 0
                trades.append({
                    "type": "SELL",
                    "price": price,
                    "shares": shares,
                    "date": i
                })
            else:
                # Hold
                if shares > 0:
                    portfolio_values.append(shares * price)
                else:
                    portfolio_values.append(portfolio_values[-1])
        
        # Close remaining position
        if shares > 0:
            final_value = shares * prices[-1] * (1 - self.commission)
            portfolio_values.append(final_value)
        
        # Calculate metrics
        portfolio_array = np.array(portfolio_values)
        returns = np.diff(portfolio_array) / portfolio_array[:-1]
        
        total_return = (portfolio_array[-1] - self.initial_capital) / self.initial_capital
        annual_return = (1 + total_return) ** (252 / len(prices)) - 1
        
        # Sharpe ratio
        excess_returns = returns - (0.05 / 252)
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if np.std(excess_returns) > 0 else 0
        
        # Max drawdown
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # Win rate
        wins = sum(1 for t in trades if t["type"] == "SELL" and t["price"] > position_price)
        win_rate = wins / (len(trades) // 2) if len(trades) > 0 else 0
        
        profit_per_trade = total_return / (len(trades) // 2) if len(trades) > 0 else 0
        
        return BacktestResult(
            strategy_name=strategy_name,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            num_trades=len(trades),
            profit_per_trade=profit_per_trade
        )
    
    def compare_strategies(self, prices: np.ndarray, 
                          strategy_signals: Dict[str, np.ndarray]) -> List[BacktestResult]:
        """Compare multiple strategies"""
        results = []
        
        for name, signals in strategy_signals.items():
            result = self.run_strategy(prices, signals, strategy_name=name)
            results.append(result)
        
        # Sort by Sharpe ratio
        results.sort(key=lambda x: x.sharpe_ratio, reverse=True)
        
        return results


class StrategyBuilder:
    """Build custom trading strategies"""
    
    @staticmethod
    def rsi_strategy(rsi_values: np.ndarray, oversold: float = 30, 
                     overbought: float = 70) -> np.ndarray:
        """
        RSI-based strategy
        Buy when RSI < oversold, Sell when RSI > overbought
        """
        signals = np.zeros(len(rsi_values))
        
        for i in range(len(rsi_values)):
            if rsi_values[i] < oversold:
                signals[i] = 1  # BUY
            elif rsi_values[i] > overbought:
                signals[i] = -1  # SELL
        
        return signals
    
    @staticmethod
    def moving_average_crossover(prices: np.ndarray, short_window: int = 20,
                                long_window: int = 50) -> np.ndarray:
        """
        Moving Average Crossover strategy
        Buy when SMA20 > SMA50, Sell when SMA20 < SMA50
        """
        sma_short = pd.Series(prices).rolling(window=short_window).mean().values
        sma_long = pd.Series(prices).rolling(window=long_window).mean().values
        
        signals = np.zeros(len(prices))
        
        for i in range(long_window, len(prices)):
            if sma_short[i] > sma_long[i] and sma_short[i-1] <= sma_long[i-1]:
                signals[i] = 1  # BUY crossover
            elif sma_short[i] < sma_long[i] and sma_short[i-1] >= sma_long[i-1]:
                signals[i] = -1  # SELL crossover
        
        return signals
    
    @staticmethod
    def macd_strategy(prices: np.ndarray, fast: int = 12, slow: int = 26,
                     signal: int = 9) -> np.ndarray:
        """
        MACD strategy
        Buy on bullish MACD crossover
        """
        ema_fast = pd.Series(prices).ewm(span=fast).mean().values
        ema_slow = pd.Series(prices).ewm(span=slow).mean().values
        macd = ema_fast - ema_slow
        macd_signal = pd.Series(macd).ewm(span=signal).mean().values
        
        signals = np.zeros(len(prices))
        
        for i in range(1, len(prices)):
            if macd[i] > macd_signal[i] and macd[i-1] <= macd_signal[i-1]:
                signals[i] = 1  # BUY
            elif macd[i] < macd_signal[i] and macd[i-1] >= macd_signal[i-1]:
                signals[i] = -1  # SELL
        
        return signals
    
    @staticmethod
    def sentiment_strategy(sentiment_scores: np.ndarray, threshold: float = 0.3) -> np.ndarray:
        """
        Sentiment-based strategy
        Buy on positive sentiment, Sell on negative
        """
        signals = np.zeros(len(sentiment_scores))
        
        for i in range(len(sentiment_scores)):
            if sentiment_scores[i] > threshold:
                signals[i] = 1  # BUY
            elif sentiment_scores[i] < -threshold:
                signals[i] = -1  # SELL
        
        return signals


# Global instances
backtest_engine = BacktestEngine(initial_capital=100000)
strategy_builder = StrategyBuilder()

