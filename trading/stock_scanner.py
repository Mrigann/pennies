"""
Stock scanner for finding high-volume, high-volatility penny stocks ideal for scalping.
Scans watchlist and market for best scalping opportunities.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any
from datetime import datetime
from config import settings
from utils.logger import logger
from utils.data_loader import load_watchlist
from trading.alpaca_client import AlpacaClient

class StockScanner:
    """Scanner for finding scalping opportunities."""
    
    def __init__(self, alpaca_client: AlpacaClient):
        """
        Initialize stock scanner.
        
        Args:
            alpaca_client: Alpaca client instance
        """
        self.client = alpaca_client
        self.watchlist = load_watchlist()
    
    def scan_watchlist(self) -> List[Dict[str, Any]]:
        """
        Scan watchlist stocks for scalping opportunities.
        
        Returns:
            List of stock opportunities with scores
        """
        if not self.watchlist:
            logger.warning("Watchlist is empty")
            return []
        
        opportunities = []
        for symbol in self.watchlist:
            try:
                opp = self._analyze_stock(symbol)
                if opp:
                    opportunities.append(opp)
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
                continue
        
        # Rank by scalping score
        opportunities.sort(key=lambda x: x.get('scalping_score', 0), reverse=True)
        return opportunities
    
    def scan_market(
        self,
        min_price: float = None,
        max_price: float = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Scan market for penny stocks in price range.
        Note: This is a simplified version. In production, you'd need to
        get a list of all tradeable symbols from Alpaca or another source.
        
        Args:
            min_price: Minimum stock price
            max_price: Maximum stock price
            limit: Maximum number of stocks to scan
        
        Returns:
            List of stock opportunities
        """
        min_price = min_price or settings.MIN_STOCK_PRICE
        max_price = max_price or settings.MAX_STOCK_PRICE
        
        # In production, you would:
        # 1. Get list of all tradeable symbols from Alpaca
        # 2. Filter by price range
        # 3. Analyze each symbol
        
        # For now, return empty list as we need a symbol list source
        logger.warning("Market scanning requires symbol list - use watchlist for now")
        return []
    
    def _analyze_stock(self, symbol: str, include_rejected: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyze a single stock for scalping potential.
        
        Args:
            symbol: Stock symbol
            include_rejected: If True, return analysis even if it doesn't meet criteria
        
        Returns:
            Dictionary with analysis results or None
        """
        try:
            # Get recent bars
            bars = self.client.get_bars(
                symbol,
                timeframe="1Min",
                limit=settings.LOOKBACK_PERIOD + 10
            )
            
            rejection_reasons = []
            
            if not bars or len(bars) < settings.LOOKBACK_PERIOD:
                if include_rejected:
                    return {
                        "symbol": symbol,
                        "status": "rejected",
                        "rejection_reasons": ["Insufficient data: Need at least {} bars, got {}".format(settings.LOOKBACK_PERIOD, len(bars) if bars else 0)],
                        "bars_count": len(bars) if bars else 0,
                        "required_bars": settings.LOOKBACK_PERIOD
                    }
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(bars)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            
            # Get latest price
            latest = df.iloc[-1]
            current_price = latest['close']
            
            # Check price range
            price_in_range = settings.MIN_STOCK_PRICE <= current_price <= settings.MAX_STOCK_PRICE
            if not price_in_range:
                rejection_reasons.append(
                    "Price out of range: ${:.4f} (Required: ${:.2f} - ${:.2f})".format(
                        current_price, settings.MIN_STOCK_PRICE, settings.MAX_STOCK_PRICE
                    )
                )
            
            # Calculate metrics
            volume_ratio = self._calculate_volume_ratio(df)
            volatility_score = self._calculate_volatility(df)
            momentum_score = self._calculate_momentum(df)
            
            # Calculate scalping score
            scalping_score = (
                volume_ratio * 0.4 +
                volatility_score * 0.4 +
                momentum_score * 0.2
            )
            
            # Check volume threshold
            volume_passed = volume_ratio >= settings.SCANNER_MIN_VOLUME_MULTIPLIER
            if not volume_passed:
                rejection_reasons.append(
                    "Volume too low: {:.2f}x (Required: {:.2f}x minimum)".format(
                        volume_ratio, settings.SCANNER_MIN_VOLUME_MULTIPLIER
                    )
                )
            
            # Check volatility threshold
            volatility_passed = volatility_score >= settings.SCANNER_MIN_VOLATILITY_PERCENT
            if not volatility_passed:
                rejection_reasons.append(
                    "Volatility too low: {:.2f}% (Required: {:.2f}% minimum)".format(
                        volatility_score, settings.SCANNER_MIN_VOLATILITY_PERCENT
                    )
                )
            
            # Calculate additional metrics for diagnostics
            avg_volume = df['volume'].rolling(window=20).mean().iloc[-1] if len(df) >= 20 else df['volume'].mean()
            current_volume = latest['volume']
            price_change_20 = ((current_price - df.iloc[-20]['close']) / df.iloc[-20]['close']) * 100 if len(df) >= 20 else 0
            
            # Calculate all technical indicators using EnhancedStrategy
            from trading.enhanced_strategy import EnhancedStrategy
            strategy = EnhancedStrategy()
            df_indicators = strategy.calculate_indicators(bars, "1Min")
            
            # Extract latest indicator values
            indicators = {}
            if not df_indicators.empty and len(df_indicators) > 0:
                latest_indicators = df_indicators.iloc[-1]
                indicators = {
                    "rsi": float(latest_indicators.get('rsi', 0)) if pd.notna(latest_indicators.get('rsi')) else None,
                    "msi": float(latest_indicators.get('msi', 0)) if pd.notna(latest_indicators.get('msi')) else None,
                    "macd": float(latest_indicators.get('macd', 0)) if pd.notna(latest_indicators.get('macd')) else None,
                    "macd_signal": float(latest_indicators.get('macd_signal', 0)) if pd.notna(latest_indicators.get('macd_signal')) else None,
                    "macd_hist": float(latest_indicators.get('macd_hist', 0)) if pd.notna(latest_indicators.get('macd_hist')) else None,
                    "sma_20": float(latest_indicators.get('sma_20', 0)) if pd.notna(latest_indicators.get('sma_20')) else None,
                    "sma_50": float(latest_indicators.get('sma_50', 0)) if pd.notna(latest_indicators.get('sma_50')) else None,
                    "ema_12": float(latest_indicators.get('ema_12', 0)) if pd.notna(latest_indicators.get('ema_12')) else None,
                    "ema_26": float(latest_indicators.get('ema_26', 0)) if pd.notna(latest_indicators.get('ema_26')) else None,
                    "atr": float(latest_indicators.get('atr', 0)) if pd.notna(latest_indicators.get('atr')) else None,
                    "atr_percent": float(latest_indicators.get('atr_percent', 0)) if pd.notna(latest_indicators.get('atr_percent')) else None,
                    "bb_upper": float(latest_indicators.get('bb_upper', 0)) if pd.notna(latest_indicators.get('bb_upper')) else None,
                    "bb_middle": float(latest_indicators.get('bb_middle', 0)) if pd.notna(latest_indicators.get('bb_middle')) else None,
                    "bb_lower": float(latest_indicators.get('bb_lower', 0)) if pd.notna(latest_indicators.get('bb_lower')) else None,
                    "high_20": float(latest_indicators.get('high_20', 0)) if pd.notna(latest_indicators.get('high_20')) else None,
                    "low_20": float(latest_indicators.get('low_20', 0)) if pd.notna(latest_indicators.get('low_20')) else None,
                    "momentum_3": float(latest_indicators.get('momentum_3', 0)) if pd.notna(latest_indicators.get('momentum_3')) else None,
                    "momentum_5": float(latest_indicators.get('momentum_5', 0)) if pd.notna(latest_indicators.get('momentum_5')) else None,
                    "volume_ratio_ind": float(latest_indicators.get('volume_ratio', 1.0)) if pd.notna(latest_indicators.get('volume_ratio')) else 1.0
                }
            
            # Get historical indicator data for charts (last 50 bars)
            indicator_history = []
            if not df_indicators.empty and len(df_indicators) > 0:
                for idx, row in df_indicators.tail(50).iterrows():
                    indicator_history.append({
                        "timestamp": idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                        "rsi": float(row.get('rsi', 0)) if pd.notna(row.get('rsi')) else None,
                        "msi": float(row.get('msi', 0)) if pd.notna(row.get('msi')) else None,
                        "macd": float(row.get('macd', 0)) if pd.notna(row.get('macd')) else None,
                        "macd_signal": float(row.get('macd_signal', 0)) if pd.notna(row.get('macd_signal')) else None,
                        "macd_hist": float(row.get('macd_hist', 0)) if pd.notna(row.get('macd_hist')) else None,
                        "sma_20": float(row.get('sma_20', 0)) if pd.notna(row.get('sma_20')) else None,
                        "ema_12": float(row.get('ema_12', 0)) if pd.notna(row.get('ema_12')) else None,
                        "ema_26": float(row.get('ema_26', 0)) if pd.notna(row.get('ema_26')) else None,
                        "close": float(row.get('close', 0)),
                        "volume": float(row.get('volume', 0))
                    })
            
            result = {
                "symbol": symbol,
                "status": "opportunity" if not rejection_reasons else "rejected",
                "current_price": float(current_price),
                "volume_ratio": float(volume_ratio),
                "volatility_score": float(volatility_score),
                "momentum_score": float(momentum_score),
                "scalping_score": float(scalping_score),
                "volume": int(latest['volume']),
                "avg_volume": float(avg_volume),
                "price_change_pct": float(price_change_20),
                "indicators": indicators,
                "indicator_history": indicator_history,
                "rejection_reasons": rejection_reasons,
                "criteria": {
                    "price_in_range": bool(price_in_range),
                    "volume_passed": bool(volume_passed),
                    "volatility_passed": bool(volatility_passed),
                    "min_price": float(settings.MIN_STOCK_PRICE),
                    "max_price": float(settings.MAX_STOCK_PRICE),
                    "min_volume_multiplier": float(settings.SCANNER_MIN_VOLUME_MULTIPLIER),
                    "min_volatility_percent": float(settings.SCANNER_MIN_VOLATILITY_PERCENT)
                },
                "bars_data": {
                    "count": int(len(bars)),
                    "required": int(settings.LOOKBACK_PERIOD),
                    "sufficient": bool(len(bars) >= settings.LOOKBACK_PERIOD)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Return None if rejected and include_rejected is False
            if rejection_reasons and not include_rejected:
                return None
            
            return result
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            if include_rejected:
                return {
                    "symbol": symbol,
                    "status": "error",
                    "rejection_reasons": [f"Error during analysis: {str(e)}"],
                    "error": str(e)
                }
            return None
    
    def _calculate_volume_ratio(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate current volume vs average volume.
        
        Args:
            df: Price DataFrame
            period: Period for average calculation
        
        Returns:
            Volume ratio (current / average)
        """
        if len(df) < period:
            return 0.0
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(window=period).mean().iloc[-1]
        
        if avg_volume == 0:
            return 0.0
        
        return current_volume / avg_volume
    
    def _calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate volatility score (ATR as percentage of price).
        
        Args:
            df: Price DataFrame
            period: Period for ATR calculation
        
        Returns:
            Volatility score (ATR % of price)
        """
        if len(df) < period:
            return 0.0
        
        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=period).mean().iloc[-1]
        
        current_price = df['close'].iloc[-1]
        
        if current_price == 0:
            return 0.0
        
        return (atr / current_price) * 100
    
    def _calculate_momentum(self, df: pd.DataFrame, period: int = 3) -> float:
        """
        Calculate price momentum score.
        
        Args:
            df: Price DataFrame
            period: Period for momentum calculation
        
        Returns:
            Momentum score (0-100 scale)
        """
        if len(df) < period + 1:
            return 0.0
        
        # Calculate percentage change
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-period-1]) / df['close'].iloc[-period-1]
        
        # Normalize to 0-100 scale (assuming -5% to +5% range)
        momentum_score = min(100, max(0, (price_change + 0.05) * 1000))
        
        return momentum_score
    
    def rank_by_scalping_score(
        self,
        opportunities: List[Dict[str, Any]],
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Rank opportunities by scalping score.
        
        Args:
            opportunities: List of opportunity dictionaries
            limit: Maximum number to return
        
        Returns:
            Sorted list of opportunities
        """
        limit = limit or settings.SCANNER_TOP_RESULTS
        sorted_opps = sorted(
            opportunities,
            key=lambda x: x.get('scalping_score', 0),
            reverse=True
        )
        return sorted_opps[:limit]
    
    def filter_high_volume(
        self,
        opportunities: List[Dict[str, Any]],
        min_multiplier: float = None
    ) -> List[Dict[str, Any]]:
        """
        Filter opportunities by volume.
        
        Args:
            opportunities: List of opportunities
            min_multiplier: Minimum volume multiplier
        
        Returns:
            Filtered list
        """
        min_multiplier = min_multiplier or settings.SCANNER_MIN_VOLUME_MULTIPLIER
        return [
            opp for opp in opportunities
            if opp.get('volume_ratio', 0) >= min_multiplier
        ]
    
    def filter_high_volatility(
        self,
        opportunities: List[Dict[str, Any]],
        min_atr_percent: float = None
    ) -> List[Dict[str, Any]]:
        """
        Filter opportunities by volatility.
        
        Args:
            opportunities: List of opportunities
            min_atr_percent: Minimum ATR percentage
        
        Returns:
            Filtered list
        """
        min_atr_percent = min_atr_percent or settings.SCANNER_MIN_VOLATILITY_PERCENT
        return [
            opp for opp in opportunities
            if opp.get('volatility_score', 0) >= min_atr_percent
        ]
    
    def get_top_scalping_opportunities(
        self,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get top scalping opportunities from watchlist.
        
        Args:
            limit: Maximum number to return
        
        Returns:
            List of top opportunities
        """
        opportunities = self.scan_watchlist()
        return self.rank_by_scalping_score(opportunities, limit)

