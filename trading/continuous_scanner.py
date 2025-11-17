"""
Continuous scanner service that monitors symbols and generates real-time signals.
"""

import time
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from config import settings
from utils.logger import logger
from utils.data_loader import load_watchlist
from trading.alpaca_client import AlpacaClient
from trading.enhanced_strategy import EnhancedStrategy
from trading.exit_manager import ExitManager

class ContinuousScanner:
    """Continuous scanner that monitors symbols and generates signals."""
    
    def __init__(self, alpaca_client: AlpacaClient, exit_manager: ExitManager = None):
        """
        Initialize continuous scanner.
        
        Args:
            alpaca_client: Alpaca client instance
            exit_manager: Exit manager instance (optional)
        """
        self.client = alpaca_client
        self.strategy = EnhancedStrategy()
        self.exit_manager = exit_manager
        self.running = False
        self.scan_thread = None
        self.scan_interval = 30  # Scan every 30 seconds
        self.symbol_signals = {}  # Store latest signals per symbol
        self.callbacks = []  # Callbacks for signal updates
    
    def start(self):
        """Start continuous scanning."""
        if self.running:
            logger.warning("Scanner already running")
            return
        
        self.running = True
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        logger.info("Continuous scanner started")
    
    def stop(self):
        """Stop continuous scanning."""
        self.running = False
        if self.scan_thread:
            self.scan_thread.join(timeout=5)
        logger.info("Continuous scanner stopped")
    
    def register_callback(self, callback):
        """
        Register callback for signal updates.
        
        Args:
            callback: Function that receives (symbol, signal_data)
        """
        self.callbacks.append(callback)
    
    def get_latest_signals(self) -> Dict[str, Dict[str, Any]]:
        """
        Get latest signals for all scanned symbols.
        
        Returns:
            Dictionary mapping symbols to their latest signals
        """
        return self.symbol_signals.copy()
    
    def get_symbol_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest signal for a specific symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Signal data or None
        """
        return self.symbol_signals.get(symbol.upper())
    
    def _scan_loop(self):
        """Main scanning loop."""
        while self.running:
            try:
                watchlist = load_watchlist()
                if not watchlist:
                    logger.debug("Watchlist is empty, skipping scan")
                    time.sleep(self.scan_interval)
                    continue
                
                # Check and execute exits for positions with scaling plans
                if self.exit_manager:
                    try:
                        positions = self.exit_manager.get_all_active_positions()
                        for position in positions:
                            symbol = position['symbol']
                            # Get current price
                            quote = self.client.get_stock_quote_info(symbol)
                            if quote and quote.get('price'):
                                current_price = quote.get('price')
                                # Check and execute exits
                                exits = self.exit_manager.check_and_execute_exits(symbol, current_price)
                                if exits:
                                    logger.info(f"Executed {len(exits)} exits for {symbol}")
                                # Update trailing stop
                                self.exit_manager.update_trailing_stop(symbol, current_price)
                    except Exception as e:
                        logger.error(f"Error checking exits: {e}")
                
                # Scan each symbol
                for symbol in watchlist:
                    if not self.running:
                        break
                    
                    try:
                        signal = self._scan_symbol(symbol)
                        if signal:
                            self.symbol_signals[symbol.upper()] = signal
                            # Notify callbacks
                            for callback in self.callbacks:
                                try:
                                    callback(symbol.upper(), signal)
                                except Exception as e:
                                    logger.error(f"Error in callback for {symbol}: {e}")
                    except Exception as e:
                        logger.error(f"Error scanning {symbol}: {e}")
                        continue
                
                # Wait before next scan
                time.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in scan loop: {e}", exc_info=True)
                time.sleep(self.scan_interval)
    
    def _scan_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Scan a single symbol and generate signal.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Signal data or None
        """
        try:
            # Get bars for different timeframes
            # Alpaca supports: 1Min, 5Min, 15Min, 1Hour, 1Day
            # For 30Min and 2Hour, we'll aggregate from smaller timeframes
            
            # Try to get 15Min bars directly
            bars_15m = self.client.get_bars(symbol, timeframe="15Min", limit=100)
            
            # Get 1Hour bars directly
            bars_1h = self.client.get_bars(symbol, timeframe="1Hour", limit=100)
            
            # For 30Min and 2Hour, aggregate from 15Min or 1Min bars
            bars_30m = None
            bars_2h = None
            
            # Get 1Min bars for aggregation if needed
            bars_1m = self.client.get_bars(symbol, timeframe="1Min", limit=500)
            
            # Aggregate 30Min from 15Min bars (2 x 15Min = 30Min)
            if bars_15m and len(bars_15m) >= 20:
                bars_30m = self._aggregate_bars(bars_15m, 2)
            elif bars_1m and len(bars_1m) >= 30:
                bars_30m = self._aggregate_bars(bars_1m, 30)
            
            # Aggregate 2Hour from 1Hour bars (2 x 1Hour = 2Hour)
            if bars_1h and len(bars_1h) >= 20:
                bars_2h = self._aggregate_bars(bars_1h, 2)
            elif bars_1m and len(bars_1m) >= 120:
                bars_2h = self._aggregate_bars(bars_1m, 120)
            
            # Fallback: if 15Min not available, aggregate from 1Min
            if not bars_15m or len(bars_15m) < 10:
                if bars_1m and len(bars_1m) >= 15:
                    bars_15m = self._aggregate_bars(bars_1m, 15)
                else:
                    return None
            
            # Fallback: if 1Hour not available, aggregate from 1Min
            if not bars_1h or len(bars_1h) < 10:
                if bars_1m and len(bars_1m) >= 60:
                    bars_1h = self._aggregate_bars(bars_1m, 60)
            
            # Get 1-minute bars for accurate daily stats
            bars_1m_for_stats = self.client.get_bars(symbol, timeframe="1Min", limit=500)
            
            # Get latest bid/ask quote for smart entry/exit decisions
            quote_data = self.client.get_latest_quote(symbol)
            
            # Generate signal with bid/ask analysis
            signal = self.strategy.generate_entry_signal(
                bars_15m or [],
                bars_30m or [],
                bars_1h or [],
                bars_2h or [],
                quote_data=quote_data
            )
            
            # Recalculate daily stats with 1-minute bars for better accuracy
            if bars_1m_for_stats and len(bars_1m_for_stats) > 0:
                try:
                    daily_stats = self.strategy.calculate_daily_price_stats(bars_1m_for_stats)
                    signal['daily_stats'] = daily_stats
                except Exception as e:
                    logger.debug(f"Error recalculating daily stats with 1Min bars: {e}")
            
            # Add symbol and timestamp
            signal['symbol'] = symbol.upper()
            signal['scan_time'] = datetime.now().isoformat()
            
            return signal
            
        except Exception as e:
            logger.error(f"Error scanning symbol {symbol}: {e}")
            return None
    
    def _aggregate_bars(self, bars: List[Dict], minutes: int) -> List[Dict]:
        """
        Aggregate 1-minute bars into larger timeframes.
        
        Args:
            bars: List of 1-minute bars
            minutes: Target timeframe in minutes
        
        Returns:
            Aggregated bars
        """
        if not bars or len(bars) < minutes:
            return []
        
        aggregated = []
        for i in range(0, len(bars), minutes):
            chunk = bars[i:i+minutes]
            if len(chunk) < minutes:
                break
            
            agg_bar = {
                'timestamp': chunk[0]['timestamp'],
                'open': chunk[0]['open'],
                'high': max(b['high'] for b in chunk),
                'low': min(b['low'] for b in chunk),
                'close': chunk[-1]['close'],
                'volume': sum(b['volume'] for b in chunk)
            }
            aggregated.append(agg_bar)
        
        return aggregated
    
    def scan_symbol_now(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Scan a symbol immediately (synchronous).
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Signal data or None
        """
        return self._scan_symbol(symbol.upper())

