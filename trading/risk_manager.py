"""
Risk management module for enforcing trading limits and position sizing.
Implements daily loss limits, position sizing, and trading permission logic.
"""

from typing import Optional, Tuple
from config import settings
from utils.logger import logger
from utils.data_loader import get_previous_day_pnl

class RiskManager:
    """Manages risk controls and position sizing."""
    
    def __init__(self, initial_capital: float = None):
        """
        Initialize risk manager.
        
        Args:
            initial_capital: Starting capital (defaults to settings.STARTING_CAPITAL)
        """
        self.initial_capital = initial_capital or settings.STARTING_CAPITAL
        self.daily_pnl = 0.0
        self.daily_betting_amount = 0.0
        self.used_betting_amount = 0.0
        self.trades_today = 0
        self.previous_day_profit = 0.0
        self.max_daily_loss = 0.0
        
        # Load previous day's profit and set loss limit
        self._initialize_daily_limits()
    
    def _initialize_daily_limits(self):
        """Initialize daily limits based on previous day's profit."""
        self.previous_day_profit = get_previous_day_pnl()
        
        # Max loss cannot exceed previous day's profit
        if self.previous_day_profit > 0:
            self.max_daily_loss = min(
                self.previous_day_profit,
                settings.MAX_DAILY_LOSS_ABSOLUTE,
                self.initial_capital * settings.MAX_DAILY_LOSS_PERCENT
            )
        else:
            # If no previous profit, use absolute limit
            self.max_daily_loss = min(
                settings.MAX_DAILY_LOSS_ABSOLUTE,
                self.initial_capital * settings.MAX_DAILY_LOSS_PERCENT
            )
        
        # Calculate daily betting amount
        self.daily_betting_amount = self.initial_capital * settings.DAILY_BETTING_PERCENTAGE
        self.used_betting_amount = 0.0
        self.trades_today = 0
        
        logger.info(
            f"Risk Manager initialized: "
            f"Capital=${self.initial_capital:.2f}, "
            f"Daily Betting=${self.daily_betting_amount:.2f}, "
            f"Max Loss=${self.max_daily_loss:.2f}, "
            f"Previous Day Profit=${self.previous_day_profit:.2f}"
        )
    
    def update_daily_pnl(self, pnl: float):
        """
        Update daily P&L.
        
        Args:
            pnl: Profit/loss amount to add
        """
        self.daily_pnl += pnl
        logger.debug(f"Daily P&L updated: ${self.daily_pnl:.2f}")
    
    def check_daily_loss_limit(self) -> Tuple[bool, str]:
        """
        Check if daily loss limit has been reached.
        
        Returns:
            Tuple of (can_trade, reason)
        """
        if self.daily_pnl <= -self.max_daily_loss:
            reason = (
                f"Daily loss limit reached: ${self.daily_pnl:.2f} "
                f"exceeds max loss of ${self.max_daily_loss:.2f}"
            )
            logger.warning(reason)
            return False, reason
        
        return True, "OK"
    
    def check_max_daily_loss(self) -> Tuple[bool, str]:
        """
        Check absolute daily loss limit.
        
        Returns:
            Tuple of (can_trade, reason)
        """
        absolute_limit = settings.MAX_DAILY_LOSS_ABSOLUTE
        if self.daily_pnl <= -absolute_limit:
            reason = f"Absolute daily loss limit reached: ${self.daily_pnl:.2f}"
            logger.warning(reason)
            return False, reason
        
        return True, "OK"
    
    def get_daily_betting_amount(self) -> float:
        """
        Get the daily betting amount.
        
        Returns:
            Daily betting amount in dollars
        """
        return self.daily_betting_amount
    
    def get_remaining_betting_amount(self) -> float:
        """
        Get remaining betting amount for the day.
        
        Returns:
            Remaining betting amount
        """
        return max(0.0, self.daily_betting_amount - self.used_betting_amount)
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on all risk criteria.
        
        Returns:
            Tuple of (can_trade, reason)
        """
        # Check daily loss limits
        can_trade, reason = self.check_daily_loss_limit()
        if not can_trade:
            return False, reason
        
        can_trade, reason = self.check_max_daily_loss()
        if not can_trade:
            return False, reason
        
        # Check position limit
        if self.trades_today >= settings.MAX_POSITIONS_PER_DAY:
            reason = f"Maximum positions per day reached: {self.trades_today}"
            logger.warning(reason)
            return False, reason
        
        # Check remaining betting amount
        if self.get_remaining_betting_amount() <= 0:
            reason = "Daily betting amount exhausted"
            logger.warning(reason)
            return False, reason
        
        return True, "OK"
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        risk_per_trade: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Calculate position size based on risk per trade and stop loss.
        
        Args:
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price
            risk_per_trade: Risk amount per trade (defaults to daily betting / max positions)
        
        Returns:
            Tuple of (position_size, actual_risk_amount)
        """
        if risk_per_trade is None:
            # Calculate risk per trade: daily betting / max positions
            risk_per_trade = self.daily_betting_amount / settings.MAX_POSITIONS_PER_DAY
        
        # Ensure we don't exceed remaining betting amount
        risk_per_trade = min(risk_per_trade, self.get_remaining_betting_amount())
        
        # Calculate price risk per share
        price_risk = abs(entry_price - stop_loss_price)
        
        if price_risk <= 0:
            logger.error(f"Invalid stop loss: entry={entry_price}, stop={stop_loss_price}")
            return 0.0, 0.0
        
        # Calculate position size
        position_size = risk_per_trade / price_risk
        
        # Round down to whole shares
        position_size = int(position_size)
        
        # Calculate actual risk
        actual_risk = position_size * price_risk
        
        logger.debug(
            f"Position sizing: entry=${entry_price:.4f}, "
            f"stop=${stop_loss_price:.4f}, "
            f"risk=${risk_per_trade:.2f}, "
            f"size={position_size} shares, "
            f"actual_risk=${actual_risk:.2f}"
        )
        
        return float(position_size), actual_risk
    
    def record_trade(self, risk_amount: float):
        """
        Record a trade to track daily usage.
        
        Args:
            risk_amount: Amount risked in this trade
        """
        self.used_betting_amount += risk_amount
        self.trades_today += 1
        logger.debug(
            f"Trade recorded: risk=${risk_amount:.2f}, "
            f"used=${self.used_betting_amount:.2f}/{self.daily_betting_amount:.2f}, "
            f"trades={self.trades_today}"
        )
    
    def get_risk_summary(self) -> dict:
        """
        Get current risk management summary.
        
        Returns:
            Dictionary with risk metrics
        """
        return {
            "daily_pnl": self.daily_pnl,
            "daily_betting_amount": self.daily_betting_amount,
            "used_betting_amount": self.used_betting_amount,
            "remaining_betting_amount": self.get_remaining_betting_amount(),
            "max_daily_loss": self.max_daily_loss,
            "previous_day_profit": self.previous_day_profit,
            "trades_today": self.trades_today,
            "max_positions": settings.MAX_POSITIONS_PER_DAY,
            "can_trade": self.can_trade()[0]
        }
    
    def reset_daily(self):
        """Reset daily counters (call at start of new trading day)."""
        self._initialize_daily_limits()
        self.daily_pnl = 0.0
        logger.info("Risk manager reset for new trading day")

