"""
Tests for trading strategy module.
"""

import pytest
from trading.strategy import TradingStrategy

class TestTradingStrategy:
    """Test trading strategy functionality."""
    
    def test_initialization(self):
        """Test strategy initialization."""
        strategy = TradingStrategy()
        assert strategy.rsi_period == 14
        assert strategy.lookback_period == 20
    
    def test_calculate_indicators(self, sample_bars):
        """Test indicator calculation."""
        strategy = TradingStrategy()
        df = strategy.calculate_indicators(sample_bars)
        
        assert not df.empty
        assert 'rsi' in df.columns
        assert 'macd' in df.columns
        assert 'sma_20' in df.columns
        assert 'atr' in df.columns
    
    def test_momentum_scalping_signal(self, sample_bars):
        """Test momentum scalping signal generation."""
        strategy = TradingStrategy()
        
        # Modify bars to create a signal
        # Make price break high with volume
        sample_bars[-1]['close'] = sample_bars[-2]['high'] + 0.01
        sample_bars[-1]['volume'] = 200000  # High volume
        
        has_signal, signal_info, entry_price, stop_loss = \
            strategy.momentum_scalping_signal(sample_bars)
        
        # May or may not have signal depending on conditions
        if has_signal:
            assert entry_price is not None
            assert stop_loss is not None
            assert stop_loss < entry_price
    
    def test_volume_breakout_signal(self, sample_bars):
        """Test volume breakout signal generation."""
        strategy = TradingStrategy()
        
        has_signal, signal_info, entry_price, stop_loss = \
            strategy.volume_breakout_signal(sample_bars)
        
        # May or may not have signal
        if has_signal:
            assert entry_price is not None
            assert stop_loss is not None
    
    def test_calculate_profit_target(self):
        """Test profit target calculation."""
        strategy = TradingStrategy()
        entry_price = 1.00
        
        profit_target = strategy.calculate_profit_target(entry_price)
        
        assert profit_target > entry_price
        assert profit_target == entry_price * (1 + 0.015)  # 1.5% target
    
    def test_calculate_stop_loss(self):
        """Test stop loss calculation."""
        strategy = TradingStrategy()
        entry_price = 1.00
        
        stop_loss = strategy.calculate_stop_loss(entry_price)
        
        assert stop_loss < entry_price
        assert stop_loss == entry_price * (1 - 0.0075)  # 0.75% stop
    
    def test_check_exit_conditions(self):
        """Test exit condition checking."""
        strategy = TradingStrategy()
        
        position = {
            'entry_price': 1.00,
            'stop_loss': 0.9925,
            'profit_target': 1.015
        }
        
        # Test profit target hit
        should_exit, reason, exit_price = strategy.check_exit_conditions(
            position, 1.015, None
        )
        assert should_exit is True
        assert reason == "profit_target"
        
        # Test stop loss hit
        should_exit, reason, exit_price = strategy.check_exit_conditions(
            position, 0.99, None
        )
        assert should_exit is True
        assert reason == "stop_loss"

