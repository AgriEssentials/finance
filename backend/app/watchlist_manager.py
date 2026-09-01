"""
Watchlist Manager Module
Professional watchlist management with CRUD operations
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from fastapi import HTTPException, status

from app.database import Watchlist, WatchlistItem, User
from app.cache import cache

class WatchlistManager:
    """Manage user watchlists"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_watchlist(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        is_default: bool = False
    ) -> Dict[str, Any]:
        """Create a new watchlist"""
        # Check if user already has a watchlist with this name
        existing = self.db.query(Watchlist).filter(
            and_(Watchlist.user_id == user_id, Watchlist.name == name)
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Watchlist '{name}' already exists"
            )
        
        # If this is set as default, unset other defaults
        if is_default:
            self.db.query(Watchlist).filter(
                Watchlist.user_id == user_id
            ).update({"is_default": False})
        
        watchlist = Watchlist(
            user_id=user_id,
            name=name,
            description=description,
            is_default=is_default
        )
        
        self.db.add(watchlist)
        self.db.commit()
        self.db.refresh(watchlist)
        
        return self._watchlist_to_dict(watchlist)
    
    def get_user_watchlists(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all watchlists for a user"""
        watchlists = self.db.query(Watchlist).filter(
            Watchlist.user_id == user_id
        ).all()
        
        return [self._watchlist_to_dict(w) for w in watchlists]
    
    def get_watchlist(self, watchlist_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific watchlist with all items"""
        watchlist = self.db.query(Watchlist).filter(
            and_(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        ).first()
        
        if not watchlist:
            return None
        
        return self._watchlist_to_dict(watchlist, include_items=True)
    
    def get_default_watchlist(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's default watchlist"""
        watchlist = self.db.query(Watchlist).filter(
            and_(Watchlist.user_id == user_id, Watchlist.is_default == True)
        ).first()
        
        if not watchlist:
            # Return first watchlist if no default
            watchlist = self.db.query(Watchlist).filter(
                Watchlist.user_id == user_id
            ).first()
        
        if watchlist:
            return self._watchlist_to_dict(watchlist, include_items=True)
        
        return None
    
    def update_watchlist(
        self,
        watchlist_id: int,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_default: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update watchlist details"""
        watchlist = self.db.query(Watchlist).filter(
            and_(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        ).first()
        
        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )
        
        if name is not None:
            # Check for name conflict
            existing = self.db.query(Watchlist).filter(
                and_(
                    Watchlist.user_id == user_id,
                    Watchlist.name == name,
                    Watchlist.id != watchlist_id
                )
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Watchlist '{name}' already exists"
                )
            
            watchlist.name = name
        
        if description is not None:
            watchlist.description = description
        
        if is_default is not None:
            if is_default:
                # Unset other defaults
                self.db.query(Watchlist).filter(
                    Watchlist.user_id == user_id
                ).update({"is_default": False})
            watchlist.is_default = is_default
        
        watchlist.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(watchlist)
        
        return self._watchlist_to_dict(watchlist)
    
    def delete_watchlist(self, watchlist_id: int, user_id: str) -> bool:
        """Delete a watchlist"""
        watchlist = self.db.query(Watchlist).filter(
            and_(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        ).first()
        
        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )
        
        self.db.delete(watchlist)
        self.db.commit()
        
        return True
    
    def add_symbol(
        self,
        watchlist_id: int,
        user_id: str,
        symbol: str,
        exchange: str = "NSE",
        notes: Optional[str] = None,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        alert_enabled: bool = False
    ) -> Dict[str, Any]:
        """Add a symbol to watchlist"""
        watchlist = self.db.query(Watchlist).filter(
            and_(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        ).first()
        
        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )
        
        symbol = symbol.upper()
        
        # Check if symbol already exists in watchlist
        existing = self.db.query(WatchlistItem).filter(
            and_(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.symbol == symbol
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{symbol} is already in this watchlist"
            )
        
        item = WatchlistItem(
            watchlist_id=watchlist_id,
            symbol=symbol,
            exchange=exchange,
            notes=notes,
            target_price=target_price,
            stop_loss=stop_loss,
            alert_enabled=alert_enabled
        )
        
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        
        # Invalidate cache
        cache.invalidate_symbol(symbol)
        
        return self._item_to_dict(item)
    
    def update_symbol(
        self,
        watchlist_id: int,
        item_id: int,
        user_id: str,
        notes: Optional[str] = None,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        alert_enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update watchlist item details"""
        # Verify watchlist ownership
        watchlist = self.db.query(Watchlist).filter(
            and_(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        ).first()
        
        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )
        
        item = self.db.query(WatchlistItem).filter(
            and_(
                WatchlistItem.id == item_id,
                WatchlistItem.watchlist_id == watchlist_id
            )
        ).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist item not found"
            )
        
        if notes is not None:
            item.notes = notes
        if target_price is not None:
            item.target_price = target_price
        if stop_loss is not None:
            item.stop_loss = stop_loss
        if alert_enabled is not None:
            item.alert_enabled = alert_enabled
        
        self.db.commit()
        self.db.refresh(item)
        
        return self._item_to_dict(item)
    
    def remove_symbol(self, watchlist_id: int, item_id: int, user_id: str) -> bool:
        """Remove a symbol from watchlist"""
        # Verify watchlist ownership
        watchlist = self.db.query(Watchlist).filter(
            and_(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        ).first()
        
        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )
        
        item = self.db.query(WatchlistItem).filter(
            and_(
                WatchlistItem.id == item_id,
                WatchlistItem.watchlist_id == watchlist_id
            )
        ).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist item not found"
            )
        
        self.db.delete(item)
        self.db.commit()
        
        return True
    
    def get_watchlist_with_live_data(self, watchlist_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """Get watchlist with live price data for all symbols"""
        watchlist = self.get_watchlist(watchlist_id, user_id)
        
        if not watchlist:
            return None
        
        # Fetch live data for all symbols
        import yfinance as yf
        
        items_with_data = []
        for item in watchlist.get("items", []):
            symbol = item["symbol"]
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d", interval="1m")
                
                if not data.empty:
                    latest = data.iloc[-1]
                    prev_close = data.iloc[0]["Close"] if len(data) > 1 else latest["Open"]
                    
                    live_data = {
                        **item,
                        "live_data": {
                            "price": round(latest["Close"], 2),
                            "change": round(latest["Close"] - prev_close, 2),
                            "change_percent": round(((latest["Close"] - prev_close) / prev_close) * 100, 2),
                            "volume": int(latest["Volume"]),
                            "high": round(latest["High"], 2),
                            "low": round(latest["Low"], 2),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                    
                    # Check alerts
                    if item.get("alert_enabled"):
                        live_data["alerts"] = self._check_price_alerts(
                            item, latest["Close"]
                        )
                    
                    items_with_data.append(live_data)
                else:
                    items_with_data.append(item)
                    
            except Exception as e:
                items_with_data.append({**item, "error": str(e)})
        
        watchlist["items"] = items_with_data
        return watchlist
    
    def _check_price_alerts(self, item: Dict, current_price: float) -> List[str]:
        """Check if any price alerts are triggered"""
        alerts = []
        
        target = item.get("target_price")
        stop_loss = item.get("stop_loss")
        
        if target and current_price >= target:
            alerts.append(f"Target price reached: {current_price} >= {target}")
        
        if stop_loss and current_price <= stop_loss:
            alerts.append(f"Stop loss triggered: {current_price} <= {stop_loss}")
        
        return alerts
    
    def reorder_symbols(self, watchlist_id: int, user_id: str, item_order: List[int]) -> bool:
        """Reorder symbols in watchlist (for future use with ordering field)"""
        # This is a placeholder for future ordering functionality
        # Would require adding an 'order' field to WatchlistItem model
        return True
    
    def _watchlist_to_dict(self, watchlist: Watchlist, include_items: bool = False) -> Dict[str, Any]:
        """Convert watchlist model to dictionary"""
        data = {
            "id": watchlist.id,
            "name": watchlist.name,
            "description": watchlist.description,
            "is_default": watchlist.is_default,
            "item_count": len(watchlist.items),
            "created_at": watchlist.created_at.isoformat() if watchlist.created_at else None,
            "updated_at": watchlist.updated_at.isoformat() if watchlist.updated_at else None
        }
        
        if include_items:
            data["items"] = [self._item_to_dict(item) for item in watchlist.items]
        
        return data
    
    def _item_to_dict(self, item: WatchlistItem) -> Dict[str, Any]:
        """Convert watchlist item model to dictionary"""
        return {
            "id": item.id,
            "symbol": item.symbol,
            "exchange": item.exchange,
            "notes": item.notes,
            "target_price": item.target_price,
            "stop_loss": item.stop_loss,
            "alert_enabled": item.alert_enabled,
            "created_at": item.created_at.isoformat() if item.created_at else None
        }
    
    def import_symbols(self, watchlist_id: int, user_id: str, symbols: List[str]) -> Dict[str, Any]:
        """Import multiple symbols to watchlist"""
        results = {
            "added": [],
            "skipped": [],
            "failed": []
        }
        
        for symbol in symbols:
            try:
                self.add_symbol(watchlist_id, user_id, symbol.strip().upper())
                results["added"].append(symbol)
            except HTTPException as e:
                if "already in this watchlist" in str(e.detail):
                    results["skipped"].append(symbol)
                else:
                    results["failed"].append({"symbol": symbol, "error": str(e.detail)})
            except Exception as e:
                results["failed"].append({"symbol": symbol, "error": str(e)})
        
        return results
    
    def export_watchlist(self, watchlist_id: int, user_id: str) -> Dict[str, Any]:
        """Export watchlist data"""
        watchlist = self.get_watchlist(watchlist_id, user_id)
        
        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )
        
        return {
            "name": watchlist["name"],
            "description": watchlist["description"],
            "exported_at": datetime.utcnow().isoformat(),
            "symbols": [item["symbol"] for item in watchlist.get("items", [])]
        }

# Factory function
def get_watchlist_manager(db: Session) -> WatchlistManager:
    """Get watchlist manager instance"""
    return WatchlistManager(db)
