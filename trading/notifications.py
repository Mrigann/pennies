"""
Notification system for trading events.
Supports in-app notifications and can be extended for email/SMS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque
import json
import os
from utils.logger import logger

class NotificationManager:
    """Manages trading notifications and alerts."""
    
    def __init__(self, max_notifications: int = 100):
        """
        Initialize notification manager.
        
        Args:
            max_notifications: Maximum number of notifications to keep in memory
        """
        self.max_notifications = max_notifications
        self.notifications = deque(maxlen=max_notifications)
        self.subscribers = []  # For future WebSocket integration
    
    def notify(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        data: Optional[Dict] = None
    ):
        """
        Create a notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type (info, success, warning, error)
            data: Additional data
        """
        notification = {
            "id": len(self.notifications) + 1,
            "title": title,
            "message": message,
            "type": notification_type,
            "timestamp": datetime.now().isoformat(),
            "read": False,
            "data": data or {}
        }
        
        self.notifications.appendleft(notification)
        logger.info(f"Notification: {title} - {message}")
        
        # Emit to subscribers (for WebSocket)
        self._emit_to_subscribers(notification)
        
        return notification
    
    def notify_trade_executed(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_id: str
    ):
        """Notify when a trade is executed."""
        return self.notify(
            title="Trade Executed",
            message=f"{side.upper()} {quantity} shares of {symbol} @ ${price:.4f}",
            notification_type="success",
            data={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "order_id": order_id
            }
        )
    
    def notify_exit_executed(
        self,
        symbol: str,
        exit_type: str,
        size: int,
        price: float,
        profit: float
    ):
        """Notify when a scaling exit is executed."""
        return self.notify(
            title="Exit Executed",
            message=f"{symbol}: {exit_type} - {size} shares @ ${price:.4f} (Profit: ${profit:.2f})",
            notification_type="success",
            data={
                "symbol": symbol,
                "exit_type": exit_type,
                "size": size,
                "price": price,
                "profit": profit
            }
        )
    
    def notify_stop_loss_hit(
        self,
        symbol: str,
        price: float,
        loss: float
    ):
        """Notify when stop loss is hit."""
        return self.notify(
            title="Stop Loss Hit",
            message=f"{symbol}: Stop loss triggered @ ${price:.4f} (Loss: ${loss:.2f})",
            notification_type="warning",
            data={
                "symbol": symbol,
                "price": price,
                "loss": loss
            }
        )
    
    def notify_signal_generated(
        self,
        symbol: str,
        signal: str,
        confidence: float
    ):
        """Notify when a trading signal is generated."""
        return self.notify(
            title="Trading Signal",
            message=f"{symbol}: {signal} signal (Confidence: {confidence:.1%})",
            notification_type="info",
            data={
                "symbol": symbol,
                "signal": signal,
                "confidence": confidence
            }
        )
    
    def notify_daily_limit_reached(
        self,
        limit_type: str,
        current: float,
        limit: float
    ):
        """Notify when daily limit is reached."""
        return self.notify(
            title="Daily Limit Reached",
            message=f"{limit_type}: ${current:.2f} / ${limit:.2f}",
            notification_type="warning",
            data={
                "limit_type": limit_type,
                "current": current,
                "limit": limit
            }
        )
    
    def get_notifications(
        self,
        limit: int = 20,
        unread_only: bool = False
    ) -> List[Dict]:
        """
        Get notifications.
        
        Args:
            limit: Maximum number of notifications to return
            unread_only: Only return unread notifications
        
        Returns:
            List of notifications
        """
        notifications = list(self.notifications)
        
        if unread_only:
            notifications = [n for n in notifications if not n.get('read', False)]
        
        return notifications[:limit]
    
    def mark_read(self, notification_id: int):
        """Mark a notification as read."""
        for notification in self.notifications:
            if notification.get('id') == notification_id:
                notification['read'] = True
                return True
        return False
    
    def mark_all_read(self):
        """Mark all notifications as read."""
        for notification in self.notifications:
            notification['read'] = True
    
    def clear(self):
        """Clear all notifications."""
        self.notifications.clear()
    
    def _emit_to_subscribers(self, notification: Dict):
        """Emit notification to subscribers (for WebSocket integration)."""
        # This would integrate with WebSocket in the future
        pass
    
    def subscribe(self, callback):
        """Subscribe to notifications (for WebSocket integration)."""
        self.subscribers.append(callback)

