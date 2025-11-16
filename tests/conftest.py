"""
Pytest configuration and fixtures for testing.
"""

import pytest
from unittest.mock import Mock, MagicMock
from trading.alpaca_client import AlpacaClient
from trading.risk_manager import RiskManager
from trading.strategy import TradingStrategy
from trading.stock_scanner import StockScanner
from trading.position_tracker import PositionTracker

@pytest.fixture
def mock_alpaca_client():
    """Mock Alpaca client for testing."""
    client = Mock(spec=AlpacaClient)
    client.mode = "paper"
    client.get_account.return_value = {
        "account_number": "TEST123",
        "cash": 5000.0,
        "portfolio_value": 5000.0,
        "buying_power": 10000.0,
        "equity": 5000.0,
        "pattern_day_trader": False,
        "trading_blocked": False,
        "account_blocked": False
    }
    client.is_market_open.return_value = True
    client.get_positions.return_value = []
    client.get_position.return_value = None
    client.place_order.return_value = {
        "id": "test_order_123",
        "symbol": "TEST",
        "qty": 100.0,
        "side": "buy",
        "status": "filled"
    }
    client.get_bars.return_value = []
    return client

@pytest.fixture
def sample_bars():
    """Sample price bars for testing."""
    import pandas as pd
    from datetime import datetime, timedelta
    
    bars = []
    base_price = 1.00
    base_time = datetime.now() - timedelta(minutes=30)
    
    for i in range(30):
        bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": base_price + (i * 0.01),
            "high": base_price + (i * 0.01) + 0.02,
            "low": base_price + (i * 0.01) - 0.01,
            "close": base_price + (i * 0.01) + 0.01,
            "volume": 100000 + (i * 1000)
        })
    
    return bars

@pytest.fixture
def risk_manager():
    """Risk manager instance for testing."""
    return RiskManager(initial_capital=5000.0)

@pytest.fixture
def strategy():
    """Trading strategy instance for testing."""
    return TradingStrategy()

@pytest.fixture
def mock_scanner(mock_alpaca_client):
    """Mock scanner for testing."""
    return StockScanner(mock_alpaca_client)

@pytest.fixture
def position_tracker(mock_alpaca_client, strategy):
    """Position tracker instance for testing."""
    return PositionTracker(mock_alpaca_client, strategy)

