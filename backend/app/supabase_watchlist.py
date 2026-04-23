"""
Supabase Watchlist Manager
Efficient watchlist operations using Supabase
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.supabase_auth import supabase_admin

class SupabaseWatchlistManager:
    """Manage user watchlists using Supabase"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def get_watchlists(self) -> List[Dict[str, Any]]:
        """Get all watchlists for user"""
        try:
            if not supabase_admin:
                return []
            
            # Get unique symbols from watchlist table
            response = supabase_admin.table("watchlist") \
                .select("*") \
                .eq("user_id", self.user_id) \
                .execute()
            
            if not response.data:
                return [{"id": 1, "name": "Default", "symbols": []}]
            
            symbols = []
            for item in response.data:
                symbol_data = {
                    "symbol": item["symbol"],
                    "target_price": item.get("target_price"),
                    "stop_loss": item.get("stop_loss"),
                    "notes": item.get("notes"),
                    "alert_enabled": item.get("alert_enabled", False)
                }
                symbols.append(symbol_data)
            
            return [{
                "id": 1,
                "name": "Default",
                "symbols": symbols,
                "count": len(symbols)
            }]
            
        except Exception as e:
            print(f"[WATCHLIST] Error getting watchlists: {e}")
            return [{"id": 1, "name": "Default", "symbols": []}]
    
    def add_symbol(self, symbol: str, target_price: Optional[float] = None, 
                   stop_loss: Optional[float] = None, notes: str = "") -> bool:
        """Add symbol to watchlist"""
        try:
            if not supabase_admin:
                return False
            
            symbol = symbol.upper().strip()
            
            # Check if already exists
            existing = supabase_admin.table("watchlist") \
                .select("id") \
                .eq("user_id", self.user_id) \
                .eq("symbol", symbol) \
                .execute()
            
            if existing.data:
                # Update existing
                supabase_admin.table("watchlist") \
                    .update({
                        "target_price": target_price,
                        "stop_loss": stop_loss,
                        "notes": notes,
                        "alert_enabled": True
                    }) \
                    .eq("id", existing.data[0]["id"]) \
                    .execute()
            else:
                # Insert new
                supabase_admin.table("watchlist") \
                    .insert({
                        "user_id": self.user_id,
                        "symbol": symbol,
                        "target_price": target_price,
                        "stop_loss": stop_loss,
                        "notes": notes,
                        "alert_enabled": True,
                        "created_at": datetime.utcnow().isoformat()
                    }) \
                    .execute()
            
            return True
            
        except Exception as e:
            print(f"[WATCHLIST] Error adding symbol: {e}")
            return False
    
    def remove_symbol(self, symbol: str) -> bool:
        """Remove symbol from watchlist"""
        try:
            if not supabase_admin:
                return False
            
            symbol = symbol.upper().strip()
            
            supabase_admin.table("watchlist") \
                .delete() \
                .eq("user_id", self.user_id) \
                .eq("symbol", symbol) \
                .execute()
            
            return True
            
        except Exception as e:
            print(f"[WATCHLIST] Error removing symbol: {e}")
            return False


def get_supabase_watchlist_manager(user_id: str) -> SupabaseWatchlistManager:
    """Get watchlist manager for user"""
    return SupabaseWatchlistManager(user_id)
