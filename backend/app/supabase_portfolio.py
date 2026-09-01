"""
Supabase Portfolio Manager
Real-time portfolio tracking with live stock prices per user
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import yfinance as yf
import pandas as pd
import numpy as np
from app.supabase_auth import supabase_admin, supabase_client


@dataclass
class Position:
    """Individual stock position"""
    symbol: str
    shares: int
    avg_cost: float
    current_price: float = 0.0
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    sector: Optional[str] = None
    last_updated: str = ""
    
    @property
    def market_value(self) -> float:
        return self.shares * self.current_price if self.current_price else 0
    
    @property
    def cost_basis(self) -> float:
        return self.shares * self.avg_cost


@dataclass
class Transaction:
    """Trade transaction record"""
    symbol: str
    action: str  # 'buy' or 'sell'
    shares: int
    price: float
    date: str
    fees: float = 0.0
    total_amount: float = 0.0
    
    @property
    def total_value(self) -> float:
        return self.shares * self.price


class SupabasePortfolioManager:
    """Portfolio management using Supabase for per-user storage"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.positions: Dict[str, Position] = {}
        self.transactions: List[Transaction] = []
        self.cash: float = 0.0  # Start with 0 - user must set up portfolio
        self.initial_capital: float = 0.0
        self.is_setup: bool = False  # Track if user has set up portfolio
        self._load_from_supabase()
    
    def _load_from_supabase(self):
        """Load portfolio data from Supabase with fallback to local storage"""
        # Portfolio tables don't exist in Supabase - use local storage only
        print("[PORTFOLIO] Portfolio tables not available in Supabase, using local storage")
        self._use_local_only = True
        self._load_from_local()
    
    def _load_from_local(self):
        """Load portfolio from local file storage as fallback"""
        try:
            import json
            import os
            
            # Create data directory if needed
            data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'portfolios')
            os.makedirs(data_dir, exist_ok=True)
            
            portfolio_file = os.path.join(data_dir, f'{self.user_id}.json')
            print(f"[PORTFOLIO] Loading from file: {portfolio_file}")
            
            if os.path.exists(portfolio_file):
                with open(portfolio_file, 'r') as f:
                    data = json.load(f)
                    # Only set values if user has actually set up their portfolio
                    file_cash = data.get('cash', 0)
                    file_positions = data.get('positions', [])
                    file_is_setup = data.get('is_setup', False)
                    
                    # Consider set up if: explicit is_setup flag, or has cash, or has positions
                    if file_is_setup or file_cash > 0 or file_positions:
                        self.cash = file_cash
                        self.initial_capital = data.get('initial_capital', 0)
                        self.is_setup = True  # Mark as set up
                        
                        # Load positions
                        for pos_data in file_positions:
                            pos = Position(**pos_data)
                            self.positions[pos.symbol] = pos
                        
                        # Load transactions
                        for trans_data in data.get('transactions', []):
                            trans = Transaction(**trans_data)
                            self.transactions.append(trans)
                        
                        print(f"[PORTFOLIO] Loaded portfolio for user: {self.user_id}, cash: {self.cash}, positions: {len(self.positions)}")
                    else:
                        print(f"[PORTFOLIO] File exists but empty - user hasn't set up portfolio yet")
            else:
                print(f"[PORTFOLIO] No portfolio file for user: {self.user_id} - needs setup")
                
        except Exception as e:
            print(f"[PORTFOLIO] Error loading from local: {e}")
    
    def _save_to_supabase(self):
        """Save portfolio data to Supabase with local fallback"""
        # Always save to local as backup - Supabase portfolio tables don't exist
        self._save_to_local()
        
        # Skip Supabase - tables don't exist
        return
    
    def _save_to_local(self):
        """Save portfolio to local file storage"""
        try:
            import json
            import os
            
            data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'portfolios')
            os.makedirs(data_dir, exist_ok=True)
            
            portfolio_file = os.path.join(data_dir, f'{self.user_id}.json')
            print(f"[PORTFOLIO] Saving to file: {portfolio_file}")
            
            # Mark as set up if there's any data to save
            if self.cash > 0 or self.positions:
                self.is_setup = True
                
            data = {
                'cash': self.cash,
                'initial_capital': self.initial_capital,
                'is_setup': self.is_setup,
                'positions': [
                    {
                        'symbol': pos.symbol,
                        'shares': pos.shares,
                        'avg_cost': pos.avg_cost,
                        'current_price': pos.current_price,
                        'current_value': pos.current_value,
                        'unrealized_pnl': pos.unrealized_pnl,
                        'unrealized_pnl_percent': pos.unrealized_pnl_percent,
                        'sector': pos.sector,
                        'last_updated': pos.last_updated
                    }
                    for pos in self.positions.values()
                ],
                'transactions': [
                    {
                        'symbol': trans.symbol,
                        'action': trans.action,
                        'shares': trans.shares,
                        'price': trans.price,
                        'date': trans.date,
                        'fees': trans.fees,
                        'total_amount': trans.total_amount
                    }
                    for trans in self.transactions
                ],
                'last_saved': datetime.now().isoformat()
            }
            
            with open(portfolio_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"[PORTFOLIO] Error saving to local: {e}")
    
    def buy(self, symbol: str, shares: int, price: Optional[float] = None, sector: Optional[str] = None) -> Dict[str, Any]:
        """Buy shares of a stock"""
        symbol = symbol.upper().strip()
        
        if price is None:
            # Fetch current price
            try:
                ticker = yf.Ticker(symbol)
                price = ticker.history(period="1d").iloc[-1]['Close']
            except Exception as e:
                return {'success': False, 'error': f'Could not fetch price for {symbol}: {e}'}
        
        price = float(price)
        total_cost = shares * price
        
        if total_cost > self.cash:
            return {
                'success': False,
                'error': f'Insufficient cash. Required: ₹{total_cost:,.2f}, Available: ₹{self.cash:,.2f}'
            }
        
        try:
            # Update local position first
            if symbol in self.positions:
                # Update existing position
                existing = self.positions[symbol]
                old_shares = existing.shares
                old_avg = existing.avg_cost
                new_shares = old_shares + shares
                new_avg = (old_shares * old_avg + shares * price) / new_shares
                
                existing.shares = new_shares
                existing.avg_cost = new_avg
                existing.current_price = price
                existing.sector = sector or existing.sector
            else:
                # Create new position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    shares=shares,
                    avg_cost=price,
                    current_price=price,
                    sector=sector
                )
            
            # Update cash
            self.cash -= total_cost
            
            # Record transaction locally
            trans = Transaction(
                symbol=symbol,
                action='buy',
                shares=shares,
                price=price,
                date=datetime.utcnow().isoformat(),
                fees=0.0,
                total_amount=total_cost
            )
            self.transactions.append(trans)
            
            # Save to local storage (Supabase portfolio tables don't exist)
            self._save_to_local()
            
            return {
                'success': True,
                'symbol': symbol,
                'shares': shares,
                'price': price,
                'total_cost': total_cost,
                'remaining_cash': self.cash
            }
            
        except Exception as e:
            print(f"[PORTFOLIO] Error in buy: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def sell(self, symbol: str, shares: int, price: Optional[float] = None) -> Dict[str, Any]:
        """Sell shares of a stock"""
        symbol = symbol.upper().strip()
        
        if symbol not in self.positions:
            return {'success': False, 'error': f'No position found for {symbol}'}
        
        position = self.positions[symbol]
        
        if shares > position.shares:
            return {
                'success': False,
                'error': f'Insufficient shares. You own {position.shares}, tried to sell {shares}'
            }
        
        if price is None:
            try:
                ticker = yf.Ticker(symbol)
                price = ticker.history(period="1d").iloc[-1]['Close']
            except Exception as e:
                return {'success': False, 'error': f'Could not fetch price: {e}'}
        
        price = float(price)
        total_value = shares * price
        realized_pnl = (price - position.avg_cost) * shares
        
        try:
            remaining_shares = position.shares - shares
            
            if remaining_shares == 0:
                # Close position completely
                del self.positions[symbol]
            else:
                # Update position
                position.shares = remaining_shares
                position.current_price = price
            
            # Update cash
            self.cash += total_value
            
            # Record transaction locally
            trans = Transaction(
                symbol=symbol,
                action='sell',
                shares=shares,
                price=price,
                date=datetime.utcnow().isoformat(),
                fees=0.0,
                total_amount=total_value
            )
            self.transactions.append(trans)
            
            # Save to local storage (Supabase portfolio tables don't exist)
            self._save_to_local()
            
            return {
                'success': True,
                'symbol': symbol,
                'shares': shares,
                'price': price,
                'total_value': total_value,
                'realized_pnl': realized_pnl,
                'remaining_cash': self.cash
            }
            
        except Exception as e:
            print(f"[PORTFOLIO] Error in sell: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def update_prices(self):
        """Update current prices for all positions using real-time data"""
        updated_positions = []
        
        for symbol, position in self.positions.items():
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d")
                if not data.empty:
                    current_price = float(data.iloc[-1]['Close'])
                    position.current_price = current_price
                    position.current_value = position.shares * current_price
                    position.unrealized_pnl = position.current_value - (position.shares * position.avg_cost)
                    if position.avg_cost > 0:
                        position.unrealized_pnl_percent = (position.unrealized_pnl / (position.shares * position.avg_cost)) * 100
                    position.last_updated = datetime.now().isoformat()
                    
                    updated_positions.append({
                        'symbol': symbol,
                        'current_price': current_price,
                        'unrealized_pnl': position.unrealized_pnl
                    })
            except Exception as e:
                print(f"[PORTFOLIO] Error updating price for {symbol}: {e}")
        
        # Update portfolio total value
        if updated_positions:
            self._save_to_supabase()
        
        return updated_positions
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary with real-time data"""
        # Update all prices first
        self.update_prices()
        
        total_value = self.cash + sum(pos.market_value for pos in self.positions.values())
        invested_value = sum(pos.cost_basis for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        # Calculate day change
        day_change = 0
        day_change_percent = 0
        for pos in self.positions.values():
            try:
                ticker = yf.Ticker(pos.symbol)
                hist = ticker.history(period="2d")
                if len(hist) >= 2:
                    prev_close = float(hist.iloc[-2]['Close'])
                    day_change += (pos.current_price - prev_close) * pos.shares
            except:
                pass
        
        if invested_value > 0:
            day_change_percent = (day_change / invested_value) * 100
        
        # Calculate sector allocation
        sector_allocation = {}
        for pos in self.positions.values():
            sector = pos.sector or "Unknown"
            if sector not in sector_allocation:
                sector_allocation[sector] = 0
            sector_allocation[sector] += pos.market_value
        
        # Convert to percentages
        total_invested = sum(sector_allocation.values())
        if total_invested > 0:
            sector_allocation = {k: round(v/total_invested*100, 2) for k, v in sector_allocation.items()}
        
        return {
            'is_setup': self.is_setup,
            'total_value': round(total_value, 2),
            'cash': round(self.cash, 2),
            'invested': round(invested_value, 2),
            'unrealized_pnl': round(total_unrealized_pnl, 2),
            'unrealized_pnl_percent': round((total_unrealized_pnl / invested_value * 100) if invested_value > 0 else 0, 2),
            'day_change': round(day_change, 2),
            'day_change_percent': round(day_change_percent, 2),
            'total_return': round(((total_value - self.initial_capital) / self.initial_capital * 100), 2) if self.initial_capital > 0 else 0,
            'positions_count': len(self.positions),
            'sector_allocation': sector_allocation,
            'positions': [
                {
                    'symbol': pos.symbol,
                    'shares': pos.shares,
                    'avg_cost': round(pos.avg_cost, 2),
                    'current_price': round(pos.current_price, 2),
                    'market_value': round(pos.market_value, 2),
                    'cost_basis': round(pos.cost_basis, 2),
                    'unrealized_pnl': round(pos.unrealized_pnl, 2),
                    'unrealized_pnl_percent': round(pos.unrealized_pnl_percent, 2),
                    'sector': pos.sector,
                    'weight': round(pos.market_value / invested_value * 100, 2) if invested_value > 0 else 0,
                    'last_updated': pos.last_updated
                }
                for pos in sorted(self.positions.values(), key=lambda x: x.market_value, reverse=True)
            ],
            'transactions': [
                {
                    'symbol': trans.symbol,
                    'action': trans.action,
                    'shares': trans.shares,
                    'price': trans.price,
                    'date': trans.date,
                    'total_value': trans.total_value
                }
                for trans in self.transactions[:10]  # Last 10 transactions
            ]
        }
    
    def get_ai_recommendations(self) -> List[Dict[str, Any]]:
        """Get AI-powered recommendations for portfolio"""
        recommendations = []
        
        for symbol, position in self.positions.items():
            try:
                # Fetch recent data
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                
                if len(hist) < 2:
                    continue
                
                current_price = float(hist.iloc[-1]['Close'])
                prev_price = float(hist.iloc[-2]['Close'])
                price_change = ((current_price - prev_price) / prev_price) * 100
                
                # Simple recommendation logic based on unrealized P&L and momentum
                unrealized_pct = position.unrealized_pnl_percent
                
                action = None
                reason = None
                
                if unrealized_pct > 20 and price_change < -2:
                    action = "CONSIDER_TAKING_PROFITS"
                    reason = f"Up {unrealized_pct:.1f}% but showing weakness (-{abs(price_change):.1f}% today)"
                elif unrealized_pct < -10 and price_change > 2:
                    action = "CONSIDER_BUYING_MORE"
                    reason = f"Down {abs(unrealized_pct):.1f}% but showing strength (+{price_change:.1f}% today)"
                elif unrealized_pct < -15:
                    action = "STOP_LOSS_ALERT"
                    reason = f"Position down {abs(unrealized_pct):.1f}%, consider cutting losses"
                elif price_change > 5:
                    action = "MOMENTUM_ALERT"
                    reason = f"Strong momentum today (+{price_change:.1f}%)"
                
                if action:
                    recommendations.append({
                        'symbol': symbol,
                        'action': action,
                        'reason': reason,
                        'current_price': current_price,
                        'unrealized_pnl_percent': unrealized_pct,
                        'day_change_percent': price_change
                    })
                    
            except Exception as e:
                print(f"[PORTFOLIO] Error getting recommendation for {symbol}: {e}")
        
        return recommendations


# Factory function to get portfolio manager for a user
def get_user_portfolio_manager(user_id: str) -> SupabasePortfolioManager:
    """Get portfolio manager for a specific user"""
    return SupabasePortfolioManager(user_id)
