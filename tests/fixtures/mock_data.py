"""
Mock data fixtures for testing.
"""

from datetime import datetime, timedelta

def get_mock_bars(count=30, base_price=1.00):
    """Generate mock price bars."""
    bars = []
    base_time = datetime.now() - timedelta(minutes=count)
    
    for i in range(count):
        bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": base_price + (i * 0.01),
            "high": base_price + (i * 0.01) + 0.02,
            "low": base_price + (i * 0.01) - 0.01,
            "close": base_price + (i * 0.01) + 0.01,
            "volume": 100000 + (i * 1000)
        })
    
    return bars

def get_mock_account():
    """Generate mock account data."""
    return {
        "account_number": "TEST123",
        "cash": 5000.0,
        "portfolio_value": 5000.0,
        "buying_power": 10000.0,
        "equity": 5000.0,
        "pattern_day_trader": False,
        "trading_blocked": False,
        "account_blocked": False
    }

def get_mock_position(symbol="TEST"):
    """Generate mock position data."""
    return {
        "symbol": symbol,
        "qty": 100.0,
        "avg_entry_price": 1.00,
        "current_price": 1.01,
        "market_value": 101.0,
        "cost_basis": 100.0,
        "unrealized_pl": 1.00,
        "unrealized_plpc": 1.0,
        "side": "long"
    }

def get_mock_order():
    """Generate mock order data."""
    return {
        "id": "test_order_123",
        "symbol": "TEST",
        "qty": 100.0,
        "side": "buy",
        "order_type": "market",
        "status": "filled",
        "filled_qty": 100.0,
        "filled_avg_price": 1.00,
        "submitted_at": datetime.now().isoformat()
    }

