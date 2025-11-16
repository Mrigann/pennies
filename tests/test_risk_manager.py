"""
Tests for risk manager module.
"""

import pytest
from trading.risk_manager import RiskManager
from config import settings

class TestRiskManager:
    """Test risk manager functionality."""
    
    def test_initialization(self):
        """Test risk manager initialization."""
        rm = RiskManager(initial_capital=5000.0)
        assert rm.initial_capital == 5000.0
        assert rm.daily_betting_amount > 0
        assert rm.max_daily_loss >= 0
    
    def test_daily_betting_amount(self):
        """Test daily betting amount calculation."""
        rm = RiskManager(initial_capital=5000.0)
        expected = 5000.0 * settings.DAILY_BETTING_PERCENTAGE
        assert abs(rm.daily_betting_amount - expected) < 0.01
    
    def test_position_sizing(self):
        """Test position size calculation."""
        rm = RiskManager(initial_capital=5000.0)
        entry_price = 1.00
        stop_loss = 0.9925  # 0.75% stop
        
        position_size, risk_amount = rm.calculate_position_size(
            entry_price=entry_price,
            stop_loss_price=stop_loss
        )
        
        assert position_size > 0
        assert risk_amount > 0
        assert risk_amount <= rm.get_remaining_betting_amount()
    
    def test_daily_loss_limit(self):
        """Test daily loss limit enforcement."""
        rm = RiskManager(initial_capital=5000.0)
        
        # Update P&L to negative
        rm.update_daily_pnl(-100.0)
        
        can_trade, reason = rm.check_daily_loss_limit()
        
        # Should still be able to trade if loss < max
        if rm.daily_pnl > -rm.max_daily_loss:
            assert can_trade is True
        else:
            assert can_trade is False
    
    def test_can_trade(self):
        """Test trading permission logic."""
        rm = RiskManager(initial_capital=5000.0)
        
        can_trade, reason = rm.can_trade()
        assert can_trade is True
        assert reason == "OK"
    
    def test_record_trade(self):
        """Test trade recording."""
        rm = RiskManager(initial_capital=5000.0)
        initial_used = rm.used_betting_amount
        initial_trades = rm.trades_today
        
        rm.record_trade(100.0)
        
        assert rm.used_betting_amount == initial_used + 100.0
        assert rm.trades_today == initial_trades + 1
    
    def test_max_positions_limit(self):
        """Test maximum positions per day limit."""
        rm = RiskManager(initial_capital=5000.0)
        
        # Record trades up to limit
        for i in range(settings.MAX_POSITIONS_PER_DAY):
            rm.record_trade(100.0)
        
        can_trade, reason = rm.can_trade()
        assert can_trade is False
        assert "positions" in reason.lower()

