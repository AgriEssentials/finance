"""
Supabase Alert Manager
Efficient alert operations using Supabase
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from app.supabase_auth import supabase_admin

class AlertType(str, Enum):
    PRICE = "price"
    INDICATOR = "indicator"
    NEWS = "news"
    VOLUME = "volume"

class AlertCondition(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"

class SupabaseAlertManager:
    """Manage user alerts using Supabase"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def get_alerts(self, active_only: bool = True, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get alerts for user"""
        try:
            if not supabase_admin:
                return []
            
            query = supabase_admin.table("alerts") \
                .select("*") \
                .eq("user_id", self.user_id)
            
            if active_only:
                query = query.eq("is_active", True)
            
            if symbol:
                query = query.eq("symbol", symbol.upper())
            
            response = query.order("created_at", desc=True).execute()
            
            if not response.data:
                return []
            
            alerts = []
            for item in response.data:
                alert = {
                    "id": str(item["id"]),
                    "symbol": item["symbol"],
                    "alert_type": item["alert_type"],
                    "condition": item["condition"],
                    "threshold": float(item["threshold"]),
                    "message": item.get("message", ""),
                    "is_active": item.get("is_active", True),
                    "is_triggered": item.get("is_triggered", False),
                    "triggered_at": item.get("triggered_at"),
                    "created_at": item.get("created_at"),
                    "expires_at": item.get("expires_at")
                }
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            print(f"[ALERTS] Error getting alerts: {e}")
            return []
    
    def create_alert(self, symbol: str, alert_type: str, condition: str, 
                     threshold: float, message: str = "") -> Optional[Dict[str, Any]]:
        """Create new alert"""
        try:
            if not supabase_admin:
                return None
            
            symbol = symbol.upper().strip()
            
            response = supabase_admin.table("alerts") \
                .insert({{
                    "user_id": self.user_id,
                    "symbol": symbol,
                    "alert_type": alert_type,
                    "condition": condition,
                    "threshold": threshold,
                    "message": message,
                    "is_active": True,
                    "is_triggered": False,
                    "notification_methods": ["email"],
                    "created_at": datetime.utcnow().isoformat(),
                    "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat()
                }}) \
                .execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            print(f"[ALERTS] Error creating alert: {e}")
            return None
    
    def update_alert(self, alert_id: str, **kwargs) -> bool:
        """Update alert"""
        try:
            if not supabase_admin:
                return False
            
            update_data = {}
            if "is_active" in kwargs:
                update_data["is_active"] = kwargs["is_active"]
            if "is_triggered" in kwargs:
                update_data["is_triggered"] = kwargs["is_triggered"]
                if kwargs["is_triggered"]:
                    update_data["triggered_at"] = datetime.utcnow().isoformat()
            if "threshold" in kwargs:
                update_data["threshold"] = kwargs["threshold"]
            if "message" in kwargs:
                update_data["message"] = kwargs["message"]
            
            if update_data:
                supabase_admin.table("alerts") \
                    .update(update_data) \
                    .eq("id", alert_id) \
                    .eq("user_id", self.user_id) \
                    .execute()
            
            return True
            
        except Exception as e:
            print(f"[ALERTS] Error updating alert: {e}")
            return False
    
    def delete_alert(self, alert_id: str) -> bool:
        """Delete alert"""
        try:
            if not supabase_admin:
                return False
            
            supabase_admin.table("alerts") \
                .delete() \
                .eq("id", alert_id) \
                .eq("user_id", self.user_id) \
                .execute()
            
            return True
            
        except Exception as e:
            print(f"[ALERTS] Error deleting alert: {e}")
            return False
    
    def check_alerts(self, symbol: str, current_price: float) -> List[Dict[str, Any]]:
        """Check if any alerts should be triggered"""
        try:
            if not supabase_admin:
                return []
            
            # Get active alerts for symbol
            response = supabase_admin.table("alerts") \
                .select("*") \
                .eq("user_id", self.user_id) \
                .eq("symbol", symbol.upper()) \
                .eq("is_active", True) \
                .eq("is_triggered", False) \
                .execute()
            
            if not response.data:
                return []
            
            triggered = []
            for alert in response.data:
                condition = alert["condition"]
                threshold = float(alert["threshold"])
                
                should_trigger = False
                if condition == "above" and current_price > threshold:
                    should_trigger = True
                elif condition == "below" and current_price < threshold:
                    should_trigger = True
                
                if should_trigger:
                    # Update alert as triggered
                    self.update_alert(str(alert["id"]), is_triggered=True)
                    triggered.append(alert)
            
            return triggered
            
        except Exception as e:
            print(f"[ALERTS] Error checking alerts: {e}")
            return []


def get_supabase_alert_manager(user_id: str) -> SupabaseAlertManager:
    """Get alert manager for user"""
    return SupabaseAlertManager(user_id)
