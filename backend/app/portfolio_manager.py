"""
Portfolio Management System
Professional-grade portfolio tracking, P&L calculation, and performance metrics
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import yfinance as yf
import pandas as pd
import numpy as np


@dataclass
class Position:
    """Individual stock position"""
    symbol: str
    shares: int
    avg_cost: float
    current_price: float = 0.0
    last_updated: str = ""
    
    @property
    def market_value(self) -> float:
        return self.shares * self.current_price
    
    @property
    def cost_basis(self) -> float:
        return self.shares * self.avg_cost
    
    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_pnl_percent(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100


@dataclass
class Transaction:
    """Trade transaction record"""
    symbol: str
    action: str  # 'buy' or 'sell'
    shares: int
    price: float
    date: str
    fees: float = 0.0
    
    @property
    def total_value(self) -> float:
        return self.shares * self.price


class PortfolioManager:
    """Professional portfolio management system"""
    
    def __init__(self, portfolio_file: str = "portfolio.json"):
        self.portfolio_file = portfolio_file
        self.positions: Dict[str, Position] = {}
        self.transactions: List[Transaction] = []
        self.cash: float = 1000000.0  # Starting cash
        self.initial_capital: float = 1000000.0
        self.load_portfolio()
        
    def load_portfolio(self):
        """Load portfolio from file"""
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file, 'r') as f:
                    data = json.load(f)
                    self.cash = data.get('cash', 1000000.0)
                    self.initial_capital = data.get('initial_capital', 1000000.0)
                    
                    # Load positions
                    for pos_data in data.get('positions', []):
                        pos = Position(**pos_data)
                        self.positions[pos.symbol] = pos
                        
                    # Load transactions
                    for trans_data in data.get('transactions', []):
                        trans = Transaction(**trans_data)
                        self.transactions.append(trans)
            except Exception as e:
                print(f"Error loading portfolio: {e}")
                
    def save_portfolio(self):
        """Save portfolio to file"""
        try:
            data = {
                'cash': self.cash,
                'initial_capital': self.initial_capital,
                'positions': [asdict(pos) for pos in self.positions.values()],
                'transactions': [asdict(trans) for trans in self.transactions],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.portfolio_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving portfolio: {e}")
            
    def buy(self, symbol: str, shares: int, price: Optional[float] = None) -> Dict[str, Any]:
        """Buy shares of a stock"""
        if price is None:
            # Fetch current price
            ticker = yf.Ticker(symbol)
            price = ticker.history(period="1d").iloc[-1]['Close']
            
        total_cost = shares * price
        
        if total_cost > self.cash:
            return {
                'success': False,
                'error': f'Insufficient cash. Required: ₹{total_cost:,.2f}, Available: ₹{self.cash:,.2f}'
            }
            
        # Update cash
        self.cash -= total_cost
        
        # Update or create position
        if symbol in self.positions:
            # Average cost calculation
            existing = self.positions[symbol]
            total_shares = existing.shares + shares
            total_cost_basis = (existing.shares * existing.avg_cost) + total_cost
            existing.avg_cost = total_cost_basis / total_shares
            existing.shares = total_shares
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                shares=shares,
                avg_cost=price,
                current_price=price,
                last_updated=datetime.now().isoformat()
            )
            
        # Record transaction
        self.transactions.append(Transaction(
            symbol=symbol,
            action='buy',
            shares=shares,
            price=price,
            date=datetime.now().isoformat()
        ))
        
        self.save_portfolio()
        
        return {
            'success': True,
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'total_cost': total_cost,
            'remaining_cash': self.cash
        }
        
    def sell(self, symbol: str, shares: int, price: Optional[float] = None) -> Dict[str, Any]:
        """Sell shares of a stock"""
        if symbol not in self.positions:
            return {
                'success': False,
                'error': f'No position found for {symbol}'
            }
            
        position = self.positions[symbol]
        
        if shares > position.shares:
            return {
                'success': False,
                'error': f'Insufficient shares. You own {position.shares}, tried to sell {shares}'
            }
            
        if price is None:
            # Fetch current price
            ticker = yf.Ticker(symbol)
            price = ticker.history(period="1d").iloc[-1]['Close']
            
        total_value = shares * price
        
        # Update cash
        self.cash += total_value
        
        # Update position
        position.shares -= shares
        if position.shares == 0:
            del self.positions[symbol]
            
        # Record transaction
        self.transactions.append(Transaction(
            symbol=symbol,
            action='sell',
            shares=shares,
            price=price,
            date=datetime.now().isoformat()
        ))
        
        self.save_portfolio()
        
        return {
            'success': True,
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'total_value': total_value,
            'realized_pnl': (price - position.avg_cost) * shares if symbol in self.positions else 0,
            'remaining_cash': self.cash
        }
        
    def update_prices(self):
        """Update current prices for all positions"""
        for symbol, position in self.positions.items():
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d")
                if not data.empty:
                    position.current_price = data.iloc[-1]['Close']
                    position.last_updated = datetime.now().isoformat()
            except Exception as e:
                print(f"Error updating price for {symbol}: {e}")
                
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        self.update_prices()
        
        total_value = self.cash + sum(pos.market_value for pos in self.positions.values())
        total_cost = sum(pos.cost_basis for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        # Calculate day change
        day_change = 0
        for pos in self.positions.values():
            try:
                ticker = yf.Ticker(pos.symbol)
                hist = ticker.history(period="2d")
                if len(hist) >= 2:
                    prev_close = hist.iloc[-2]['Close']
                    day_change += (pos.current_price - prev_close) * pos.shares
            except:
                pass
                
        return {
            'total_value': round(total_value, 2),
            'cash': round(self.cash, 2),
            'invested': round(total_cost, 2),
            'unrealized_pnl': round(total_unrealized_pnl, 2),
            'unrealized_pnl_percent': round((total_unrealized_pnl / total_cost * 100) if total_cost > 0 else 0, 2),
            'day_change': round(day_change, 2),
            'total_return': round(((total_value - self.initial_capital) / self.initial_capital * 100), 2),
            'positions_count': len(self.positions),
            'positions': [
                {
                    'symbol': pos.symbol,
                    'shares': pos.shares,
                    'avg_cost': round(pos.avg_cost, 2),
                    'current_price': round(pos.current_price, 2),
                    'market_value': round(pos.market_value, 2),
                    'unrealized_pnl': round(pos.unrealized_pnl, 2),
                    'unrealized_pnl_percent': round(pos.unrealized_pnl_percent, 2),
                    'weight': round(pos.market_value / (total_value - self.cash) * 100, 2) if (total_value - self.cash) > 0 else 0
                }
                for pos in self.positions.values()
            ]
        }
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio performance metrics"""
        if len(self.transactions) < 2:
            return {'error': 'Insufficient transaction history'}
            
        # Calculate returns
        returns = []
        for i in range(1, len(self.transactions)):
            prev_value = self.transactions[i-1].total_value
            curr_value = self.transactions[i].total_value
            if prev_value > 0:
                ret = (curr_value - prev_value) / prev_value
                returns.append(ret)
                
        if not returns:
            return {'error': 'Could not calculate returns'}
            
        returns = np.array(returns)
        
        return {
            'total_trades': len(self.transactions),
            'win_rate': round((returns > 0).sum() / len(returns) * 100, 2),
            'avg_return': round(returns.mean() * 100, 2),
            'volatility': round(returns.std() * 100, 2),
            'sharpe_ratio': round((returns.mean() / returns.std()) * np.sqrt(252), 2) if returns.std() > 0 else 0,
            'max_drawdown': round(self._calculate_max_drawdown(), 2)
        }
        
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        values = []
        current_value = self.initial_capital
        
        for trans in sorted(self.transactions, key=lambda x: x.date):
            if trans.action == 'buy':
                current_value -= trans.total_value
            else:
                current_value += trans.total_value
            values.append(current_value)
            
        if not values:
            return 0.0
            
        values = np.array(values)
        peak = np.maximum.accumulate(values)
        drawdown = (peak - values) / peak
        return drawdown.max() * 100


# Global portfolio manager instance
portfolio_manager = PortfolioManager()
