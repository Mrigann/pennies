"""
Tests for position tracker module.
"""

import pytest
from datetime import datetime
from trading.position_tracker import PositionTracker

class TestPositionTracker:
    """Test position tracker functionality."""
    
    def test_initialization(self, position_tracker):
        """Test position tracker initialization."""
        assert position_tracker.client is not None
        assert position_tracker.strategy is not None
    
    def test_track_positions(self, position_tracker, mock_alpaca_client):
        """Test position tracking."""
        mock_alpaca_client.get_positions.return_value = [
            {
                'symbol': 'TEST',
                'qty': 100.0,
                'avg_entry_price': 1.00,
                'current_price': 1.01,
                'unrealized_pl': 1.00,
                'unrealized_plpc': 1.0
            }
        ]
        
        positions = position_tracker.track_positions()
        assert isinstance(positions, list)
    
    def test_calculate_unrealized_pnl(self, position_tracker):
        """Test unrealized P&L calculation."""
        position = {
            'unrealized_pl': 10.50
        }
        
        pnl = position_tracker.calculate_unrealized_pnl(position)
        assert pnl == 10.50
    
    def test_update_daily_pnl(self, position_tracker):
        """Test daily P&L update."""
        summary = position_tracker.update_daily_pnl()
        assert 'net' in summary
        assert 'trades' in summary
        assert 'win_rate' in summary

