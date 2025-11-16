"""
Tests for stock scanner module.
"""

import pytest
from trading.stock_scanner import StockScanner

class TestStockScanner:
    """Test stock scanner functionality."""
    
    def test_initialization(self, mock_alpaca_client):
        """Test scanner initialization."""
        scanner = StockScanner(mock_alpaca_client)
        assert scanner.client is not None
    
    def test_calculate_volume_ratio(self, mock_scanner, sample_bars):
        """Test volume ratio calculation."""
        import pandas as pd
        df = pd.DataFrame(sample_bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        ratio = mock_scanner._calculate_volume_ratio(df)
        assert ratio >= 0
    
    def test_calculate_volatility(self, mock_scanner, sample_bars):
        """Test volatility calculation."""
        import pandas as pd
        df = pd.DataFrame(sample_bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        volatility = mock_scanner._calculate_volatility(df)
        assert volatility >= 0
    
    def test_rank_by_scalping_score(self, mock_scanner):
        """Test ranking by scalping score."""
        opportunities = [
            {'symbol': 'A', 'scalping_score': 50},
            {'symbol': 'B', 'scalping_score': 80},
            {'symbol': 'C', 'scalping_score': 30}
        ]
        
        ranked = mock_scanner.rank_by_scalping_score(opportunities)
        assert ranked[0]['symbol'] == 'B'
        assert ranked[-1]['symbol'] == 'C'
    
    def test_filter_high_volume(self, mock_scanner):
        """Test volume filtering."""
        opportunities = [
            {'symbol': 'A', 'volume_ratio': 1.5},
            {'symbol': 'B', 'volume_ratio': 2.5},
            {'symbol': 'C', 'volume_ratio': 3.0}
        ]
        
        filtered = mock_scanner.filter_high_volume(opportunities, min_multiplier=2.0)
        assert len(filtered) == 2
        assert all(opp['volume_ratio'] >= 2.0 for opp in filtered)

