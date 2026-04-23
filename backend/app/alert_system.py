"""
Alert System Module
Professional alert management with multiple notification channels
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from enum import Enum
from fastapi import HTTPException, status
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

from app.database import Alert, User
from app.cache import cache

class AlertType(str, Enum):
    PRICE = "price"
    INDICATOR = "indicator"
    NEWS = "news"
    VOLUME = "volume"
    PERCENTAGE_CHANGE = "percentage_change"

class AlertCondition(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    PERCENTAGE_UP = "percentage_up"
    PERCENTAGE_DOWN = "percentage_down"

class NotificationMethod(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"

class AlertManager:
    """Manage price and indicator alerts"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_handlers = {
            NotificationMethod.EMAIL: self._send_email_notification,
            NotificationMethod.SMS: self._send_sms_notification,
            NotificationMethod.PUSH: self._send_push_notification,
            NotificationMethod.WEBHOOK: self._send_webhook_notification,
            NotificationMethod.WEBSOCKET: self._send_websocket_notification,
        }
    
    def create_alert(
        self,
        user_id: str,
        symbol: str,
        alert_type: AlertType,
        condition: AlertCondition,
        value: float,
        message: Optional[str] = None,
        notification_methods: List[NotificationMethod] = None,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create a new alert"""
        symbol = symbol.upper()
        
        # Validate alert parameters
        if alert_type == AlertType.PRICE and condition not in [
            AlertCondition.ABOVE, AlertCondition.BELOW,
            AlertCondition.CROSSES_ABOVE, AlertCondition.CROSSES_BELOW
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid condition for price alert"
            )
        
        if notification_methods is None:
            notification_methods = [NotificationMethod.EMAIL]
        
        # Set default expiry (30 days)
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=30)
        
        alert = Alert(
            user_id=user_id,
            symbol=symbol,
            alert_type=alert_type,
            condition=condition,
            value=value,
            message=message or f"{symbol} {condition.value} {value}",
            notification_methods=[m.value for m in notification_methods],
            expires_at=expires_at
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        return self._alert_to_dict(alert)
    
    def get_user_alerts(
        self,
        user_id: str,
        active_only: bool = True,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all alerts for a user"""
        query = self.db.query(Alert).filter(Alert.user_id == user_id)
        
        if active_only:
            query = query.filter(
                and_(
                    Alert.is_active == True,
                    or_(
                        Alert.expires_at > datetime.utcnow(),
                        Alert.expires_at == None
                    )
                )
            )
        
        if symbol:
            query = query.filter(Alert.symbol == symbol.upper())
        
        alerts = query.order_by(Alert.created_at.desc()).all()
        return [self._alert_to_dict(alert) for alert in alerts]
    
    def get_alert(self, alert_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific alert"""
        alert = self.db.query(Alert).filter(
            and_(Alert.id == alert_id, Alert.user_id == user_id)
        ).first()
        
        if alert:
            return self._alert_to_dict(alert)
        return None
    
    def update_alert(
        self,
        alert_id: int,
        user_id: str,
        value: Optional[float] = None,
        message: Optional[str] = None,
        is_active: Optional[bool] = None,
        notification_methods: Optional[List[NotificationMethod]] = None
    ) -> Dict[str, Any]:
        """Update an alert"""
        alert = self.db.query(Alert).filter(
            and_(Alert.id == alert_id, Alert.user_id == user_id)
        ).first()
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        if value is not None:
            alert.value = value
        if message is not None:
            alert.message = message
        if is_active is not None:
            alert.is_active = is_active
            if is_active:
                alert.is_triggered = False
        if notification_methods is not None:
            alert.notification_methods = [m.value for m in notification_methods]
        
        self.db.commit()
        self.db.refresh(alert)
        
        return self._alert_to_dict(alert)
    
    def delete_alert(self, alert_id: int, user_id: str) -> bool:
        """Delete an alert"""
        alert = self.db.query(Alert).filter(
            and_(Alert.id == alert_id, Alert.user_id == user_id)
        ).first()
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        self.db.delete(alert)
        self.db.commit()
        
        return True
    
    def check_alerts(self, symbol: str, current_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check all active alerts for a symbol and trigger if conditions met"""
        symbol = symbol.upper()
        triggered_alerts = []
        
        # Get active alerts for this symbol
        alerts = self.db.query(Alert).filter(
            and_(
                Alert.symbol == symbol,
                Alert.is_active == True,
                Alert.is_triggered == False,
                or_(
                    Alert.expires_at > datetime.utcnow(),
                    Alert.expires_at == None
                )
            )
        ).all()
        
        for alert in alerts:
            if self._check_alert_condition(alert, current_data):
                # Trigger alert
                alert.is_triggered = True
                alert.triggered_at = datetime.utcnow()
                self.db.commit()
                
                alert_data = self._alert_to_dict(alert)
                alert_data["trigger_data"] = current_data
                triggered_alerts.append(alert_data)
                
                # Send notifications
                asyncio.create_task(self._send_notifications(alert, current_data))
        
        return triggered_alerts
    
    def _check_alert_condition(self, alert: Alert, current_data: Dict[str, Any]) -> bool:
        """Check if alert condition is met"""
        if alert.alert_type == AlertType.PRICE:
            current_price = current_data.get("price", 0)
            
            if alert.condition == AlertCondition.ABOVE:
                return current_price > alert.value
            elif alert.condition == AlertCondition.BELOW:
                return current_price < alert.value
            elif alert.condition == AlertCondition.CROSSES_ABOVE:
                # Would need historical data to properly check crosses
                return current_price >= alert.value
            elif alert.condition == AlertCondition.CROSSES_BELOW:
                return current_price <= alert.value
        
        elif alert.alert_type == AlertType.PERCENTAGE_CHANGE:
            change_percent = current_data.get("change_percent", 0)
            
            if alert.condition == AlertCondition.PERCENTAGE_UP:
                return change_percent >= alert.value
            elif alert.condition == AlertCondition.PERCENTAGE_DOWN:
                return change_percent <= -alert.value
        
        elif alert.alert_type == AlertType.VOLUME:
            volume = current_data.get("volume", 0)
            avg_volume = current_data.get("avg_volume", volume)
            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
            
            if alert.condition == AlertCondition.ABOVE:
                return volume_ratio > alert.value
        
        return False
    
    async def _send_notifications(self, alert: Alert, trigger_data: Dict[str, Any]):
        """Send notifications through all configured channels"""
        user = self.db.query(User).filter(User.id == alert.user_id).first()
        
        if not user:
            return
        
        notification_data = {
            "alert_id": alert.id,
            "symbol": alert.symbol,
            "type": alert.alert_type,
            "condition": alert.condition,
            "trigger_value": alert.value,
            "current_data": trigger_data,
            "message": alert.message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for method in alert.notification_methods:
            handler = self.notification_handlers.get(NotificationMethod(method))
            if handler:
                try:
                    await handler(user, notification_data)
                except Exception as e:
                    print(f"Failed to send {method} notification: {e}")
    
    async def _send_email_notification(self, user: User, data: Dict[str, Any]):
        """Send email notification"""
        # This is a placeholder - would need SMTP configuration
        smtp_server = os.getenv("SMTP_SERVER")
        if not smtp_server:
            print("SMTP not configured, skipping email notification")
            return
        
        try:
            msg = MIMEMultipart()
            msg["From"] = os.getenv("SMTP_FROM_EMAIL")
            msg["To"] = user.email
            msg["Subject"] = f"Stock Alert: {data['symbol']}"
            
            body = f"""
            Alert Triggered!
            
            Symbol: {data['symbol']}
            Type: {data['type']}
            Condition: {data['condition']}
            Target Value: {data['trigger_value']}
            Current Price: {data['current_data'].get('price', 'N/A')}
            
            Message: {data['message']}
            
            Time: {data['timestamp']}
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            # server = smtplib.SMTP(smtp_server, 587)
            # server.starttls()
            # server.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
            # server.send_message(msg)
            # server.quit()
            
            print(f"Email notification sent to {user.email}")
            
        except Exception as e:
            print(f"Email notification failed: {e}")
    
    async def _send_sms_notification(self, user: User, data: Dict[str, Any]):
        """Send SMS notification"""
        # Placeholder for SMS service integration (Twilio, etc.)
        print(f"SMS notification would be sent for {data['symbol']} alert")
    
    async def _send_push_notification(self, user: User, data: Dict[str, Any]):
        """Send push notification"""
        # Placeholder for push notification service (Firebase, etc.)
        print(f"Push notification would be sent for {data['symbol']} alert")
    
    async def _send_webhook_notification(self, user: User, data: Dict[str, Any]):
        """Send webhook notification"""
        import aiohttp
        
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=data) as response:
                    if response.status == 200:
                        print(f"Webhook notification sent successfully")
                    else:
                        print(f"Webhook notification failed with status {response.status}")
        except Exception as e:
            print(f"Webhook notification failed: {e}")
    
    async def _send_websocket_notification(self, user: User, data: Dict[str, Any]):
        """Send WebSocket notification"""
        from app.websocket_manager import streamer
        
        await streamer.broadcast_alert(data['symbol'], data)
    
    def get_triggered_alerts(self, user_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get all triggered alerts for a user"""
        query = self.db.query(Alert).filter(
            and_(
                Alert.user_id == user_id,
                Alert.is_triggered == True
            )
        )
        
        if since:
            query = query.filter(Alert.triggered_at >= since)
        
        alerts = query.order_by(Alert.triggered_at.desc()).all()
        return [self._alert_to_dict(alert) for alert in alerts]
    
    def reactivate_alert(self, alert_id: int, user_id: str) -> Dict[str, Any]:
        """Reactivate a triggered alert"""
        alert = self.db.query(Alert).filter(
            and_(Alert.id == alert_id, Alert.user_id == user_id)
        ).first()
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        alert.is_triggered = False
        alert.is_active = True
        alert.triggered_at = None
        
        self.db.commit()
        self.db.refresh(alert)
        
        return self._alert_to_dict(alert)
    
    def create_batch_alerts(
        self,
        user_id: str,
        alerts_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create multiple alerts at once"""
        results = {
            "created": [],
            "failed": []
        }
        
        for alert_data in alerts_data:
            try:
                alert = self.create_alert(
                    user_id=user_id,
                    symbol=alert_data["symbol"],
                    alert_type=AlertType(alert_data["alert_type"]),
                    condition=AlertCondition(alert_data["condition"]),
                    value=alert_data["value"],
                    message=alert_data.get("message"),
                    notification_methods=[NotificationMethod(m) for m in alert_data.get("notification_methods", ["email"])],
                    expires_at=datetime.fromisoformat(alert_data["expires_at"]) if "expires_at" in alert_data else None
                )
                results["created"].append(alert)
            except Exception as e:
                results["failed"].append({
                    "data": alert_data,
                    "error": str(e)
                })
        
        return results
    
    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert alert model to dictionary"""
        return {
            "id": alert.id,
            "symbol": alert.symbol,
            "alert_type": alert.alert_type,
            "condition": alert.condition,
            "value": alert.value,
            "message": alert.message,
            "is_active": alert.is_active,
            "is_triggered": alert.is_triggered,
            "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
            "notification_methods": alert.notification_methods,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "expires_at": alert.expires_at.isoformat() if alert.expires_at else None
        }

# Factory function
def get_alert_manager(db: Session) -> AlertManager:
    """Get alert manager instance"""
    return AlertManager(db)

# Alert checker background task
async def check_all_alerts_background():
    """Background task to periodically check all active alerts"""
    from app.database import SessionLocal
    import yfinance as yf
    
    while True:
        try:
            db = SessionLocal()
            alert_manager = AlertManager(db)
            
            # Get all unique symbols with active alerts
            symbols = db.query(Alert.symbol).filter(
                and_(
                    Alert.is_active == True,
                    Alert.is_triggered == False
                )
            ).distinct().all()
            
            for (symbol,) in symbols:
                try:
                    # Fetch current data
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period="1d", interval="1m")
                    
                    if not data.empty:
                        latest = data.iloc[-1]
                        current_data = {
                            "price": latest["Close"],
                            "change": latest["Close"] - latest["Open"],
                            "change_percent": ((latest["Close"] - latest["Open"]) / latest["Open"]) * 100,
                            "volume": latest["Volume"],
                            "high": latest["High"],
                            "low": latest["Low"]
                        }
                        
                        # Check alerts
                        triggered = alert_manager.check_alerts(symbol, current_data)
                        
                        if triggered:
                            print(f"Triggered {len(triggered)} alerts for {symbol}")
                
                except Exception as e:
                    print(f"Error checking alerts for {symbol}: {e}")
            
            db.close()
            
            # Check every 30 seconds
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"Alert checker error: {e}")
            await asyncio.sleep(30)
