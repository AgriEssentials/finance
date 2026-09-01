"""
Paper Trading System
Simulated trading environment for strategy testing without real money
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from enum import Enum
from fastapi import HTTPException, status
import yfinance as yf

from app.database import PaperTrade, User, Portfolio as PortfolioModel, PortfolioPosition, PortfolioTransaction

class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class TradeType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class PaperTradingManager:
    """Manage paper trading system"""
    
    def __init__(self, db: Session,         user_id: str):
        self.db = db
        self.user_id = user_id
        self.initial_balance = 1000000.0  # 10 Lakhs INR default
    
    def get_or_create_portfolio(self) -> PortfolioModel:
        """Get or create paper trading portfolio for user"""
        portfolio = self.db.query(PortfolioModel).filter(
            PortfolioModel.user_id == self.user_id
        ).first()
        
        if not portfolio:
            portfolio = PortfolioModel(
                user_id=self.user_id,
                cash_balance=self.initial_balance,
                total_value=self.initial_balance,
                total_invested=0.0,
                total_pnl=0.0
            )
            self.db.add(portfolio)
            self.db.commit()
            self.db.refresh(portfolio)
        
        return portfolio
    
    def place_trade(
        self,
        symbol: str,
        trade_type: TradeType,
        shares: int,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None,
        strategy: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Place a new paper trade"""
        symbol = symbol.upper()
        portfolio = self.get_or_create_portfolio()
        
        # Get current price if not provided
        if entry_price is None:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if data.empty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not fetch price for {symbol}"
                )
            entry_price = round(data['Close'].iloc[-1], 2)
        
        total_cost = entry_price * shares
        
        if trade_type == TradeType.BUY:
            # Check if enough cash
            if portfolio.cash_balance < total_cost:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient funds. Required: ₹{total_cost:,.2f}, Available: ₹{portfolio.cash_balance:,.2f}"
                )
            
            # Deduct cash
            portfolio.cash_balance -= total_cost
            portfolio.total_invested += total_cost
            
            # Create or update position
            position = self.db.query(PortfolioPosition).filter(
                and_(
                    PortfolioPosition.portfolio_id == portfolio.id,
                    PortfolioPosition.symbol == symbol
                )
            ).first()
            
            if position:
                # Update existing position
                total_shares = position.shares + shares
                total_value = (position.shares * position.avg_buy_price) + total_cost
                position.avg_buy_price = total_value / total_shares
                position.shares = total_shares
            else:
                # Create new position
                position = PortfolioPosition(
                    portfolio_id=portfolio.id,
                    symbol=symbol,
                    shares=shares,
                    avg_buy_price=entry_price,
                    current_price=entry_price,
                    current_value=total_cost
                )
                self.db.add(position)
            
            # Record transaction
            transaction = PortfolioTransaction(
                portfolio_id=portfolio.id,
                symbol=symbol,
                transaction_type="BUY",
                shares=shares,
                price=entry_price,
                total_amount=total_cost,
                fees=0.0
            )
            self.db.add(transaction)
        
        else:  # SELL
            # Check if position exists
            position = self.db.query(PortfolioPosition).filter(
                and_(
                    PortfolioPosition.portfolio_id == portfolio.id,
                    PortfolioPosition.symbol == symbol
                )
            ).first()
            
            if not position or position.shares < shares:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient shares to sell. Available: {position.shares if position else 0}"
                )
            
            # Calculate P&L
            sell_value = entry_price * shares
            buy_value = position.avg_buy_price * shares
            pnl = sell_value - buy_value
            
            # Update position
            position.shares -= shares
            portfolio.cash_balance += sell_value
            
            if position.shares == 0:
                self.db.delete(position)
            
            # Record transaction
            transaction = PortfolioTransaction(
                portfolio_id=portfolio.id,
                symbol=symbol,
                transaction_type="SELL",
                shares=shares,
                price=entry_price,
                total_amount=sell_value,
                fees=0.0
            )
            self.db.add(transaction)
        
        # Create paper trade record
        trade = PaperTrade(
            user_id=self.user_id,
            symbol=symbol,
            trade_type=trade_type.value,
            entry_price=entry_price,
            shares=shares,
            stop_loss=stop_loss,
            target_price=target_price,
            strategy=strategy,
            status=TradeStatus.OPEN.value if trade_type == TradeType.BUY else TradeStatus.CLOSED.value,
            notes=notes
        )
        
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        
        # Update portfolio value
        self._update_portfolio_value(portfolio)
        
        return self._trade_to_dict(trade)
    
    def close_trade(
        self,
        trade_id: int,
        exit_price: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Close an open paper trade"""
        trade = self.db.query(PaperTrade).filter(
            and_(
                PaperTrade.id == trade_id,
                PaperTrade.user_id == self.user_id,
                PaperTrade.status == TradeStatus.OPEN.value
            )
        ).first()
        
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found or already closed"
            )
        
        # Get exit price
        if exit_price is None:
            ticker = yf.Ticker(trade.symbol)
            data = ticker.history(period="1d")
            if data.empty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not fetch current price for {trade.symbol}"
                )
            exit_price = round(data['Close'].iloc[-1], 2)
        
        # Calculate P&L
        if trade.trade_type == TradeType.BUY.value:
            pnl = (exit_price - trade.entry_price) * trade.shares
        else:
            pnl = (trade.entry_price - exit_price) * trade.shares
        
        pnl_percent = (pnl / (trade.entry_price * trade.shares)) * 100
        
        # Update trade
        trade.exit_price = exit_price
        trade.pnl = round(pnl, 2)
        trade.pnl_percent = round(pnl_percent, 2)
        trade.status = TradeStatus.CLOSED.value
        trade.closed_at = datetime.utcnow()
        if notes:
            trade.notes = notes
        
        # Update portfolio if BUY trade (SELL trades are closed immediately)
        if trade.trade_type == TradeType.BUY.value:
            portfolio = self.get_or_create_portfolio()
            
            position = self.db.query(PortfolioPosition).filter(
                and_(
                    PortfolioPosition.portfolio_id == portfolio.id,
                    PortfolioPosition.symbol == trade.symbol
                )
            ).first()
            
            if position and position.shares >= trade.shares:
                sell_value = exit_price * trade.shares
                portfolio.cash_balance += sell_value
                position.shares -= trade.shares
                
                if position.shares == 0:
                    self.db.delete(position)
                
                # Record transaction
                transaction = PortfolioTransaction(
                    portfolio_id=portfolio.id,
                    symbol=trade.symbol,
                    transaction_type="SELL",
                    shares=trade.shares,
                    price=exit_price,
                    total_amount=sell_value,
                    fees=0.0
                )
                self.db.add(transaction)
                
                self._update_portfolio_value(portfolio)
        
        self.db.commit()
        self.db.refresh(trade)
        
        return self._trade_to_dict(trade)
    
    def get_trades(
        self,
        status: Optional[TradeStatus] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all paper trades for user"""
        query = self.db.query(PaperTrade).filter(PaperTrade.user_id == self.user_id)
        
        if status:
            query = query.filter(PaperTrade.status == status.value)
        if symbol:
            query = query.filter(PaperTrade.symbol == symbol.upper())
        
        trades = query.order_by(PaperTrade.opened_at.desc()).all()
        return [self._trade_to_dict(trade) for trade in trades]
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions with live P&L"""
        portfolio = self.get_or_create_portfolio()
        positions = self.db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == portfolio.id
        ).all()
        
        positions_with_pnl = []
        for position in positions:
            try:
                # Get live price
                ticker = yf.Ticker(position.symbol)
                data = ticker.history(period="1d")
                if not data.empty:
                    current_price = round(data['Close'].iloc[-1], 2)
                    current_value = current_price * position.shares
                    invested_value = position.avg_buy_price * position.shares
                    unrealized_pnl = current_value - invested_value
                    unrealized_pnl_percent = (unrealized_pnl / invested_value) * 100
                    
                    positions_with_pnl.append({
                        "symbol": position.symbol,
                        "shares": position.shares,
                        "avg_buy_price": position.avg_buy_price,
                        "current_price": current_price,
                        "current_value": round(current_value, 2),
                        "invested_value": round(invested_value, 2),
                        "unrealized_pnl": round(unrealized_pnl, 2),
                        "unrealized_pnl_percent": round(unrealized_pnl_percent, 2),
                        "last_updated": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                positions_with_pnl.append({
                    "symbol": position.symbol,
                    "shares": position.shares,
                    "avg_buy_price": position.avg_buy_price,
                    "error": str(e)
                })
        
        return positions_with_pnl
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        portfolio = self.get_or_create_portfolio()
        
        # Update prices
        positions = self.db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == portfolio.id
        ).all()
        
        total_position_value = 0.0
        for position in positions:
            try:
                ticker = yf.Ticker(position.symbol)
                data = ticker.history(period="1d")
                if not data.empty:
                    position.current_price = round(data['Close'].iloc[-1], 2)
                    position.current_value = position.current_price * position.shares
                    position.last_updated = datetime.utcnow()
                    total_position_value += position.current_value
            except:
                if position.current_value:
                    total_position_value += position.current_value
        
        portfolio.total_value = portfolio.cash_balance + total_position_value
        portfolio.total_pnl = portfolio.total_value - self.initial_balance
        
        self.db.commit()
        
        # Get trades statistics
        all_trades = self.db.query(PaperTrade).filter(
            PaperTrade.user_id == self.user_id
        ).all()
        
        closed_trades = [t for t in all_trades if t.status == TradeStatus.CLOSED.value]
        winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl and t.pnl <= 0]
        
        return {
            "portfolio_value": round(portfolio.total_value, 2),
            "cash_balance": round(portfolio.cash_balance, 2),
            "position_value": round(total_position_value, 2),
            "total_pnl": round(portfolio.total_pnl, 2),
            "total_pnl_percent": round((portfolio.total_pnl / self.initial_balance) * 100, 2),
            "initial_balance": self.initial_balance,
            "open_positions": len(positions),
            "total_trades": len(all_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round((len(winning_trades) / len(closed_trades) * 100), 2) if closed_trades else 0,
            "avg_win": round(sum(t.pnl for t in winning_trades) / len(winning_trades), 2) if winning_trades else 0,
            "avg_loss": round(sum(t.pnl for t in losing_trades) / len(losing_trades), 2) if losing_trades else 0,
            "largest_win": round(max((t.pnl for t in winning_trades), default=0), 2),
            "largest_loss": round(min((t.pnl for t in losing_trades), default=0), 2),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get detailed trade history"""
        trades = self.db.query(PaperTrade).filter(
            PaperTrade.user_id == self.user_id
        ).order_by(PaperTrade.opened_at.desc()).limit(limit).all()
        
        return [self._trade_to_dict(trade) for trade in trades]
    
    def reset_portfolio(self, confirm: bool = False) -> Dict[str, Any]:
        """Reset paper trading portfolio"""
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must confirm portfolio reset"
            )
        
        portfolio = self.db.query(PortfolioModel).filter(
            PortfolioModel.user_id == self.user_id
        ).first()
        
        if portfolio:
            # Delete all positions and transactions
            self.db.query(PortfolioPosition).filter(
                PortfolioPosition.portfolio_id == portfolio.id
            ).delete()
            
            self.db.query(PortfolioTransaction).filter(
                PortfolioTransaction.portfolio_id == portfolio.id
            ).delete()
            
            # Reset portfolio
            portfolio.cash_balance = self.initial_balance
            portfolio.total_value = self.initial_balance
            portfolio.total_invested = 0.0
            portfolio.total_pnl = 0.0
        
        # Close all open trades
        self.db.query(PaperTrade).filter(
            and_(
                PaperTrade.user_id == self.user_id,
                PaperTrade.status == TradeStatus.OPEN.value
            )
        ).update({"status": TradeStatus.CANCELLED.value})
        
        self.db.commit()
        
        return {
            "message": "Portfolio reset successfully",
            "new_balance": self.initial_balance,
            "reset_at": datetime.utcnow().isoformat()
        }
    
    def _update_portfolio_value(self, portfolio: PortfolioModel):
        """Update total portfolio value"""
        positions = self.db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == portfolio.id
        ).all()
        
        position_value = sum(p.current_value or 0 for p in positions)
        portfolio.total_value = portfolio.cash_balance + position_value
        portfolio.total_pnl = portfolio.total_value - self.initial_balance
        
        self.db.commit()
    
    def _trade_to_dict(self, trade: PaperTrade) -> Dict[str, Any]:
        """Convert PaperTrade to dictionary"""
        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "trade_type": trade.trade_type,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "shares": trade.shares,
            "stop_loss": trade.stop_loss,
            "target_price": trade.target_price,
            "strategy": trade.strategy,
            "status": trade.status,
            "pnl": trade.pnl,
            "pnl_percent": trade.pnl_percent,
            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
            "notes": trade.notes
        }

# Factory function
def get_paper_trading_manager(db: Session,         user_id: str) -> PaperTradingManager:
    """Get paper trading manager instance"""
    return PaperTradingManager(db, user_id)
