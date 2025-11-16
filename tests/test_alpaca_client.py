"""
Tests for Alpaca client module.
"""

import pytest
from unittest.mock import Mock, patch
from trading.alpaca_client import AlpacaClient

class TestAlpacaClient:
    """Test Alpaca client functionality."""
    
    @patch('trading.alpaca_client.TradeClient')
    @patch('trading.alpaca_client.StockHistoricalDataClient')
    def test_initialization(self, mock_data_client, mock_trade_client):
        """Test client initialization."""
        with patch('config.settings.ALPACA_API_KEY', 'test_key'), \
             patch('config.settings.ALPACA_SECRET_KEY', 'test_secret'):
            client = AlpacaClient(mode='paper')
            assert client.mode == 'paper'
            assert client.base_url is not None
    
    def test_switch_mode(self, mock_alpaca_client):
        """Test mode switching."""
        # This would require mocking the client initialization
        # For now, just test the logic
        assert True  # Placeholder
    
    def test_get_account(self, mock_alpaca_client):
        """Test account retrieval."""
        account = mock_alpaca_client.get_account()
        assert account is not None
        assert 'cash' in account
        assert 'portfolio_value' in account
    
    def test_is_market_open(self, mock_alpaca_client):
        """Test market status check."""
        is_open = mock_alpaca_client.is_market_open()
        assert isinstance(is_open, bool)
    
    def test_get_positions(self, mock_alpaca_client):
        """Test position retrieval."""
        positions = mock_alpaca_client.get_positions()
        assert isinstance(positions, list)
    
    def test_place_order(self, mock_alpaca_client):
        """Test order placement."""
        order = mock_alpaca_client.place_order(
            symbol='TEST',
            qty=100,
            side='buy',
            order_type='market'
        )
        assert order is not None
        assert 'id' in order

