"""
Backtesting Engine
Professional-grade strategy backtesting with performance metrics
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """Trade record for backtesting"""
    entry_date: str
    exit_date: Optional[str]
    entry_price: float
    exit_price: Optional[float]
    shares: int
    action: str  # 'long' or 'short'
    pnl: float = 0.0
    pnl_percent: float = 0.0


class BacktestEngine:
    """Professional backtesting engine"""
    
    def __init__(self, symbol: str, initial_capital: float = 100000, start_date: str = None, end_date: str = None):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.start_date = start_date or (datetime.now() - pd.Timedelta(days=365)).strftime('%Y-%m-%d')
        self.end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        self.data = None
        self.trades: List[Trade] = []
        self.portfolio_values: List[float] = []
        self.current_position = None
        self.cash = initial_capital
        
    def load_data(self) -> bool:
        """Load historical price data"""
        try:
            ticker = yf.Ticker(self.symbol)
            self.data = ticker.history(start=self.start_date, end=self.end_date)
            return not self.data.empty
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
            
    def run_strategy(self, strategy_func: Callable, **kwargs) -> Dict[str, Any]:
        """
        Run a trading strategy through backtest
        
        Args:
            strategy_func: Function that takes (df, index, **kwargs) and returns 'buy', 'sell', or 'hold'
            **kwargs: Additional parameters for the strategy
        """
        if self.data is None or self.data.empty:
            return {'error': 'No data loaded'}
            
        self.trades = []
        self.portfolio_values = []
        self.current_position = None
        self.cash = self.initial_capital
        
        for i in range(50, len(self.data)):  # Start after enough data for indicators
            current_date = self.data.index[i].strftime('%Y-%m-%d')
            current_price = self.data.iloc[i]['Close']
            
            # Get strategy signal
            signal = strategy_func(self.data.iloc[:i+1], i, **kwargs)
            
            # Execute signal
            if signal == 'buy' and self.current_position is None:
                # Calculate position size (max 10% of capital per trade)
                position_size = min(self.cash * 0.1, self.cash)
                shares = int(position_size / current_price)
                
                if shares > 0:
                    self.current_position = Trade(
                        entry_date=current_date,
                        exit_date=None,
                        entry_price=current_price,
                        exit_price=None,
                        shares=shares,
                        action='long'
                    )
                    self.cash -= shares * current_price
                    
            elif signal == 'sell' and self.current_position is not None:
                # Close position
                self.current_position.exit_date = current_date
                self.current_position.exit_price = current_price
                
                # Calculate P&L
                entry_value = self.current_position.shares * self.current_position.entry_price
                exit_value = self.current_position.shares * current_price
                self.current_position.pnl = exit_value - entry_value
                self.current_position.pnl_percent = (self.current_position.pnl / entry_value) * 100
                
                self.cash += exit_value
                self.trades.append(self.current_position)
                self.current_position = None
                
            # Calculate portfolio value
            position_value = 0
            if self.current_position:
                position_value = self.current_position.shares * current_price
            total_value = self.cash + position_value
            self.portfolio_values.append(total_value)
            
        # Close any open position at the end
        if self.current_position:
            final_price = self.data.iloc[-1]['Close']
            self.current_position.exit_date = self.data.index[-1].strftime('%Y-%m-%d')
            self.current_position.exit_price = final_price
            entry_value = self.current_position.shares * self.current_position.entry_price
            exit_value = self.current_position.shares * final_price
            self.current_position.pnl = exit_value - entry_value
            self.current_position.pnl_percent = (self.current_position.pnl / entry_value) * 100
            self.trades.append(self.current_position)
            
        return self.calculate_metrics()
        
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive backtest metrics"""
        if not self.trades:
            return {'error': 'No trades executed'}
            
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        # Returns
        final_value = self.portfolio_values[-1] if self.portfolio_values else self.initial_capital
        total_return = ((final_value - self.initial_capital) / self.initial_capital) * 100
        
        # Trade metrics
        avg_profit = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        win_rate = (len(winning_trades) / total_trades) * 100
        
        # Risk metrics
        returns = pd.Series(self.portfolio_values).pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100  # Annualized
        
        # Sharpe ratio (assuming 5% risk-free rate)
        risk_free_rate = 0.05
        excess_returns = returns.mean() * 252 - risk_free_rate
        sharpe_ratio = (excess_returns / (returns.std() * np.sqrt(252))) if returns.std() > 0 else 0
        
        # Max drawdown
        peak = pd.Series(self.portfolio_values).cummax()
        drawdown = (peak - pd.Series(self.portfolio_values)) / peak
        max_drawdown = drawdown.max() * 100
        
        # Profit factor
        gross_profit = sum([t.pnl for t in winning_trades])
        gross_loss = abs(sum([t.pnl for t in losing_trades]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'total_return': round(total_return, 2),
            'annualized_return': round(total_return / (len(self.data) / 252), 2) if len(self.data) > 0 else 0,
            'volatility': round(volatility, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'initial_capital': round(self.initial_capital, 2),
            'final_value': round(final_value, 2),
            'trades': [
                {
                    'entry_date': t.entry_date,
                    'exit_date': t.exit_date,
                    'entry_price': round(t.entry_price, 2),
                    'exit_price': round(t.exit_price, 2),
                    'shares': t.shares,
                    'pnl': round(t.pnl, 2),
                    'pnl_percent': round(t.pnl_percent, 2)
                }
                for t in self.trades
            ],
            'portfolio_values': self.portfolio_values
        }


def simple_momentum_strategy(df: pd.DataFrame, index: int, short_window: int = 20, long_window: int = 50) -> str:
    """Simple moving average crossover strategy"""
    if len(df) < long_window:
        return 'hold'
        
    short_ma = df['Close'].rolling(window=short_window).mean().iloc[-1]
    long_ma = df['Close'].rolling(window=long_window).mean().iloc[-1]
    
    if short_ma > long_ma:
        return 'buy'
    elif short_ma < long_ma:
        return 'sell'
    return 'hold'


def rsi_strategy(df: pd.DataFrame, index: int, oversold: int = 30, overbought: int = 70) -> str:
    """RSI-based mean reversion strategy"""
    import pandas_ta as ta
    
    if len(df) < 14:
        return 'hold'
        
    rsi = ta.rsi(df['Close'], length=14).iloc[-1]
    
    if pd.isna(rsi):
        return 'hold'
        
    if rsi < oversold:
        return 'buy'
    elif rsi > overbought:
        return 'sell'
    return 'hold'


def macd_strategy(df: pd.DataFrame, index: int) -> str:
    """MACD crossover strategy"""
    import pandas_ta as ta
    
    if len(df) < 35:
        return 'hold'
        
    macd = ta.macd(df['Close'])
    if macd is None:
        return 'hold'
        
    macd_line = macd['MACD_12_26_9'].iloc[-1]
    signal_line = macd['MACDs_12_26_9'].iloc[-1]
    
    if pd.isna(macd_line) or pd.isna(signal_line):
        return 'hold'
        
    if macd_line > signal_line:
        return 'buy'
    elif macd_line < signal_line:
        return 'sell'
    return 'hold'
