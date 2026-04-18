"""
Real-Time Alerts and WebSocket Management
Handles live notifications and alerts for price/sentiment changes
"""

import asyncio
from typing import Dict, List, Set
from datetime import datetime
from dataclasses import dataclass, asdict
import json


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    symbol: str
    alert_type: str  # "price", "sentiment", "signal"
    message: str
    value: float
    threshold: float
    timestamp: str
    severity: str  # "info", "warning", "critical"


class AlertManager:
    """Manages user alerts and notifications"""
    
    def __init__(self):
        """Initialize alert manager"""
        self.active_alerts: Dict[str, List[Alert]] = {}  # symbol -> alerts
        self.alert_history: Dict[str, List[Alert]] = {}
        self.alert_id_counter = 0
        self.user_subscriptions: Dict[str, Set[str]] = {}  # user_id -> symbols
    
    def create_alert(self, user_id: str, symbol: str, alert_type: str,
                    threshold: float, condition: str) -> Dict:
        """
        Create price/sentiment alert
        
        Args:
            user_id: User ID
            symbol: Stock symbol
            alert_type: "price_above", "price_below", "sentiment_positive", etc
            threshold: Threshold value
            condition: Alert condition description
        
        Returns:
            Alert details
        """
        if symbol not in self.active_alerts:
            self.active_alerts[symbol] = []
        
        self.alert_id_counter += 1
        alert_id = f"alert_{self.alert_id_counter}"
        
        alert = Alert(
            id=alert_id,
            symbol=symbol,
            alert_type=alert_type,
            message=condition,
            value=0,
            threshold=threshold,
            timestamp=datetime.now().isoformat(),
            severity="info"
        )
        
        self.active_alerts[symbol].append(alert)
        
        # Track subscription
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        self.user_subscriptions[user_id].add(symbol)
        
        return {
            "alert_id": alert_id,
            "status": "created",
            "message": f"Alert created for {symbol}"
        }
    
    def check_price_alert(self, symbol: str, current_price: float) -> List[Alert]:
        """Check if price crossed any thresholds"""
        triggered = []
        
        if symbol not in self.active_alerts:
            return triggered
        
        for alert in self.active_alerts[symbol]:
            if alert.alert_type == "price_above" and current_price > alert.threshold:
                alert.value = current_price
                alert.severity = "critical"
                triggered.append(alert)
            elif alert.alert_type == "price_below" and current_price < alert.threshold:
                alert.value = current_price
                alert.severity = "critical"
                triggered.append(alert)
        
        return triggered
    
    def check_sentiment_alert(self, symbol: str, sentiment_score: float) -> List[Alert]:
        """Check if sentiment changed"""
        triggered = []
        
        if symbol not in self.active_alerts:
            return triggered
        
        for alert in self.active_alerts[symbol]:
            if alert.alert_type == "sentiment_positive" and sentiment_score > 0.3:
                alert.value = sentiment_score
                triggered.append(alert)
            elif alert.alert_type == "sentiment_negative" and sentiment_score < -0.3:
                alert.value = sentiment_score
                triggered.append(alert)
        
        return triggered
    
    def get_user_alerts(self, user_id: str) -> List[Dict]:
        """Get all alerts for user"""
        alerts = []
        
        if user_id not in self.user_subscriptions:
            return alerts
        
        for symbol in self.user_subscriptions[user_id]:
            if symbol in self.active_alerts:
                for alert in self.active_alerts[symbol]:
                    alerts.append(asdict(alert))
        
        return alerts

    def get_active_symbols(self) -> List[str]:
        """Return symbols that currently have active alerts."""
        return [symbol for symbol, items in self.active_alerts.items() if items]

    def get_alerts_for_symbol(self, symbol: str) -> List[Alert]:
        """Return active alerts for a symbol."""
        return list(self.active_alerts.get(symbol, []))

    def mark_alerts_triggered(self, triggered_alerts: List[Alert]) -> None:
        """Move triggered alerts to history and remove from active list."""
        if not triggered_alerts:
            return

        triggered_ids = {alert.id for alert in triggered_alerts}
        grouped_by_symbol: Dict[str, List[Alert]] = {}
        for alert in triggered_alerts:
            grouped_by_symbol.setdefault(alert.symbol, []).append(alert)

        for symbol, alerts in grouped_by_symbol.items():
            self.alert_history.setdefault(symbol, []).extend(alerts)

            remaining = [
                alert for alert in self.active_alerts.get(symbol, [])
                if alert.id not in triggered_ids
            ]
            if remaining:
                self.active_alerts[symbol] = remaining
            elif symbol in self.active_alerts:
                del self.active_alerts[symbol]
    
    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert"""
        for symbol in self.active_alerts:
            for i, alert in enumerate(self.active_alerts[symbol]):
                if alert.id == alert_id:
                    self.active_alerts[symbol].pop(i)
                    return True
        return False


class WebSocketConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        """Initialize connection manager"""
        self.active_connections: Dict[str, List] = {}  # user_id -> connections
        self.message_queue: asyncio.Queue = asyncio.Queue()
    
    async def connect(self, user_id: str, websocket):
        """Add new WebSocket connection"""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        print(f"[WEBSOCKET] User {user_id} connected")
    
    async def disconnect(self, user_id: str, websocket):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"[WEBSOCKET] User {user_id} disconnected")
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected users"""
        message_json = json.dumps(message)
        
        for user_id, connections in list(self.active_connections.items()):
            for connection in list(connections):
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    print(f"[ERROR] Failed to send message: {e}")
    
    async def send_to_user(self, user_id: str, message: Dict):
        """Send message to specific user"""
        if user_id not in self.active_connections:
            return
        
        message_json = json.dumps(message)
        
        for connection in list(self.active_connections[user_id]):
            try:
                await connection.send_text(message_json)
            except Exception as e:
                print(f"[ERROR] Failed to send message to {user_id}: {e}")
    
    async def send_alert(self, alert: Alert):
        """Send alert to relevant users"""
        message = {
            "type": "alert",
            "data": asdict(alert)
        }
        await self.broadcast(message)
    
    async def send_price_update(self, symbol: str, price: float, change: float):
        """Send price update"""
        message = {
            "type": "price_update",
            "symbol": symbol,
            "price": price,
            "change": change,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
    
    async def send_sentiment_update(self, symbol: str, sentiment: float):
        """Send sentiment update"""
        message = {
            "type": "sentiment_update",
            "symbol": symbol,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)


# Global instances
alert_manager = AlertManager()
ws_manager = WebSocketConnectionManager()

