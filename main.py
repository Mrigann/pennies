"""
Main execution script for the penny trading system.
Orchestrates all components and runs the trading loop.
"""

import time
import threading
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import settings
from utils.logger import logger
from trading.alpaca_client import AlpacaClient
from trading.risk_manager import RiskManager
from trading.strategy import TradingStrategy
from trading.stock_scanner import StockScanner
from trading.position_tracker import PositionTracker

class TradingSystem:
    """Main trading system orchestrator."""
    
    def __init__(self):
        """Initialize trading system."""
        logger.info("Initializing trading system...")
        
        # Initialize components
        self.client = AlpacaClient(mode=settings.TRADING_MODE)
        self.strategy = TradingStrategy()
        self.scanner = StockScanner(self.client)
        self.position_tracker = PositionTracker(self.client, self.strategy)
        
        # Get account info for risk manager
        account = self.client.get_account()
        if account:
            capital = float(account.get('portfolio_value', settings.STARTING_CAPITAL))
            self.risk_manager = RiskManager(initial_capital=capital)
        else:
            logger.warning("Could not get account info, using default capital")
            self.risk_manager = RiskManager()
        
        self.running = False
        self.trading_thread = None
        self.pending_trades: List[Dict[str, Any]] = []
        self.pending_trades_lock = threading.Lock()
        
        logger.info(f"Trading system initialized in {settings.TRADING_MODE} mode")
    
    def start(self):
        """Start the trading system."""
        if self.running:
            logger.warning("Trading system already running")
            return
        
        self.running = True
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()
        logger.info("Trading system started")
    
    def stop(self):
        """Stop the trading system."""
        self.running = False
        if self.trading_thread:
            self.trading_thread.join(timeout=5)
        logger.info("Trading system stopped")
    
    def _trading_loop(self):
        """Main trading loop."""
        logger.info("Starting trading loop...")
        
        while self.running:
            try:
                # Check if market is open
                if not self.client.is_market_open():
                    logger.debug("Market is closed, waiting...")
                    time.sleep(60)
                    continue
                
                # Track existing positions
                positions = self.position_tracker.track_positions()
                
                # Update risk manager with current P&L
                daily_summary = self.position_tracker.update_daily_pnl()
                self.risk_manager.update_daily_pnl(daily_summary['net'])
                
                # Check if we can trade
                can_trade, reason = self.risk_manager.can_trade()
                if not can_trade:
                    logger.warning(f"Cannot trade: {reason}")
                    time.sleep(30)
                    continue
                
                # Scan for opportunities
                opportunities = self.scanner.get_top_scalping_opportunities(limit=10)
                
                if not opportunities:
                    logger.debug("No trading opportunities found")
                    time.sleep(30)
                    continue
                
                # Process opportunities
                for opp in opportunities[:3]:  # Limit to top 3
                    if not self.running:
                        break
                    
                    symbol = opp['symbol']
                    
                    # Skip if we already have a position
                    if symbol in [p['symbol'] for p in positions]:
                        continue
                    
                    # Get recent bars for signal generation
                    bars = self.client.get_bars(
                        symbol,
                        timeframe="1Min",
                        limit=settings.LOOKBACK_PERIOD + 10
                    )
                    
                    if not bars or len(bars) < settings.LOOKBACK_PERIOD:
                        continue
                    
                    # Try momentum scalping strategy first
                    has_signal, signal_info, entry_price, stop_loss = \
                        self.strategy.momentum_scalping_signal(bars)
                    
                    # If no momentum signal, try volume breakout
                    if not has_signal:
                        has_signal, signal_info, entry_price, stop_loss = \
                            self.strategy.volume_breakout_signal(bars)
                    
                    if not has_signal:
                        continue
                    
                    # Calculate position size
                    position_size, risk_amount = self.risk_manager.calculate_position_size(
                        entry_price=entry_price,
                        stop_loss_price=stop_loss
                    )
                    
                    if position_size < 1:
                        logger.debug(f"Position size too small for {symbol}")
                        continue
                    
                    # Check if we have enough buying power
                    account = self.client.get_account()
                    if account and float(account.get('buying_power', 0)) < (entry_price * position_size * 1.1):
                        logger.debug(f"Insufficient buying power for {symbol}")
                        continue
                    
                    # Get daily high/low and trading band analysis
                    daily_analysis = self._get_daily_analysis(symbol, bars)
                    
                    # Calculate profit target
                    profit_target = self.strategy.calculate_profit_target(entry_price)
                    
                    # Create pending trade for approval
                    pending_trade = {
                        'id': f"pending_{symbol}_{int(time.time())}",
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'entry_price': entry_price,
                        'position_size': position_size,
                        'stop_loss': stop_loss,
                        'profit_target': profit_target,
                        'risk_amount': risk_amount,
                        'strategy': signal_info.get('strategy', 'unknown'),
                        'signal_info': signal_info,
                        'daily_high': daily_analysis.get('daily_high'),
                        'daily_low': daily_analysis.get('daily_low'),
                        'current_price': entry_price,
                        'trading_band': daily_analysis.get('trading_band'),
                        'band_position': daily_analysis.get('band_position'),
                        'upside_potential': daily_analysis.get('upside_potential'),
                        'exit_routes': daily_analysis.get('exit_routes'),
                        'status': 'pending'
                    }
                    
                    # Add to pending trades queue
                    with self.pending_trades_lock:
                        # Remove any existing pending trade for this symbol
                        self.pending_trades = [t for t in self.pending_trades if t['symbol'] != symbol]
                        self.pending_trades.append(pending_trade)
                    
                    logger.info(
                        f"Trade queued for approval: {symbol} | "
                        f"Size: {position_size} | "
                        f"Entry: ${entry_price:.4f} | "
                        f"Stop: ${stop_loss:.4f} | "
                        f"Risk: ${risk_amount:.2f} | "
                        f"Daily High: ${daily_analysis.get('daily_high', 0):.4f} | "
                        f"Daily Low: ${daily_analysis.get('daily_low', 0):.4f}"
                    )
                    
                    # Small delay between scans
                    time.sleep(2)
                
                # Wait before next scan
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                time.sleep(60)
    
    def end_of_day_processing(self):
        """Process end of day tasks."""
        logger.info("Running end of day processing...")
        
        # Close all positions before market close (if configured)
        if settings.EXIT_BEFORE_MARKET_CLOSE_MINUTES > 0:
            # This would check time and close positions
            pass
        
        # Save daily P&L
        self.position_tracker.save_daily_pnl()
        
        # Reset risk manager for next day
        self.risk_manager.reset_daily()
        
        logger.info("End of day processing complete")
    
    def _get_daily_analysis(self, symbol: str, bars: List[Dict]) -> Dict[str, Any]:
        """
        Get daily analysis including high/low, trading bands, upside potential, and exit routes.
        
        Args:
            symbol: Stock symbol
            bars: List of price bars
            
        Returns:
            Dictionary with analysis data
        """
        try:
            if not bars or len(bars) < 2:
                return {}
            
            # Get today's bars (assuming bars are recent)
            df = pd.DataFrame(bars)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            
            # Get daily high and low
            daily_high = float(df['high'].max())
            daily_low = float(df['low'].min())
            current_price = float(df['close'].iloc[-1])
            
            # Calculate trading bands (using 20-period high/low as bands)
            if len(df) >= 20:
                band_high = float(df['high'].rolling(window=20).max().iloc[-1])
                band_low = float(df['low'].rolling(window=20).min().iloc[-1])
            else:
                band_high = daily_high
                band_low = daily_low
            
            # Determine which band we're trading in
            band_range = band_high - band_low
            if band_range > 0:
                band_position = ((current_price - band_low) / band_range) * 100
                if band_position >= 75:
                    trading_band = "Upper Band"
                elif band_position <= 25:
                    trading_band = "Lower Band"
                else:
                    trading_band = "Middle Band"
            else:
                trading_band = "No Band"
                band_position = 50.0
            
            # Calculate upside potential (distance to daily high and profit target)
            profit_target = self.strategy.calculate_profit_target(current_price)
            upside_to_high = ((daily_high - current_price) / current_price) * 100 if daily_high > current_price else 0
            upside_to_target = ((profit_target - current_price) / current_price) * 100
            
            # Calculate exit routes
            exit_routes = {
                'profit_target': {
                    'price': profit_target,
                    'distance_pct': upside_to_target,
                    'distance_dollars': profit_target - current_price
                },
                'daily_high': {
                    'price': daily_high,
                    'distance_pct': upside_to_high,
                    'distance_dollars': daily_high - current_price
                },
                'stop_loss': {
                    'price': self.strategy.calculate_stop_loss(current_price, bars),
                    'distance_pct': ((self.strategy.calculate_stop_loss(current_price, bars) - current_price) / current_price) * 100,
                    'distance_dollars': self.strategy.calculate_stop_loss(current_price, bars) - current_price
                }
            }
            
            return {
                'daily_high': daily_high,
                'daily_low': daily_low,
                'current_price': current_price,
                'trading_band': trading_band,
                'band_position': round(band_position, 2),
                'band_high': band_high,
                'band_low': band_low,
                'upside_potential': {
                    'to_profit_target_pct': round(upside_to_target, 2),
                    'to_daily_high_pct': round(upside_to_high, 2),
                    'max_upside_pct': round(max(upside_to_target, upside_to_high), 2)
                },
                'exit_routes': exit_routes
            }
        except Exception as e:
            logger.error(f"Error getting daily analysis for {symbol}: {e}")
            return {}
    
    def get_pending_trades(self) -> List[Dict[str, Any]]:
        """Get list of pending trades awaiting approval."""
        with self.pending_trades_lock:
            return self.pending_trades.copy()
    
    def approve_trade(self, trade_id: str) -> Dict[str, Any]:
        """
        Approve and execute a pending trade.
        
        Args:
            trade_id: ID of the pending trade
            
        Returns:
            Result dictionary with order info or error
        """
        with self.pending_trades_lock:
            # Find the pending trade
            trade = None
            for t in self.pending_trades:
                if t['id'] == trade_id and t['status'] == 'pending':
                    trade = t
                    break
            
            if not trade:
                return {'error': 'Trade not found or already processed'}
            
            # Remove from pending list
            self.pending_trades = [t for t in self.pending_trades if t['id'] != trade_id]
        
        try:
            # Place the order
            logger.info(
                f"Approving trade: {trade['symbol']} | "
                f"Size: {trade['position_size']} | "
                f"Entry: ${trade['entry_price']:.4f}"
            )
            
            order = self.client.place_order(
                symbol=trade['symbol'],
                qty=trade['position_size'],
                side='buy',
                order_type='market'
            )
            
            if order:
                # Record trade in risk manager
                self.risk_manager.record_trade(trade['risk_amount'])
                
                # Update position tracker
                position = self.client.get_position(trade['symbol'])
                if position:
                    self.position_tracker.positions[trade['symbol']] = {
                        'symbol': trade['symbol'],
                        'qty': position['qty'],
                        'entry_price': trade['entry_price'],
                        'entry_time': datetime.now(),
                        'stop_loss': trade['stop_loss'],
                        'profit_target': trade['profit_target'],
                        'strategy': trade['strategy']
                    }
                
                logger.info(f"Order placed successfully: {order.get('id')}")
                return {'success': True, 'order': order}
            else:
                logger.error(f"Failed to place order for {trade['symbol']}")
                return {'error': 'Failed to place order'}
        except Exception as e:
            logger.error(f"Error approving trade: {e}")
            return {'error': str(e)}
    
    def reject_trade(self, trade_id: str) -> Dict[str, Any]:
        """
        Reject a pending trade.
        
        Args:
            trade_id: ID of the pending trade
            
        Returns:
            Result dictionary
        """
        with self.pending_trades_lock:
            # Remove from pending list
            initial_count = len(self.pending_trades)
            self.pending_trades = [t for t in self.pending_trades if t['id'] != trade_id]
            
            if len(self.pending_trades) < initial_count:
                logger.info(f"Trade {trade_id} rejected")
                return {'success': True, 'message': 'Trade rejected'}
            else:
                return {'error': 'Trade not found'}

def main():
    """Main entry point."""
    try:
        system = TradingSystem()
        
        # Start trading system
        system.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(60)
                
                # Check if it's end of day
                # In production, check market close time
                current_time = datetime.now().time()
                if current_time.hour == 15 and current_time.minute >= 45:  # 3:45 PM
                    system.end_of_day_processing()
                    time.sleep(3600)  # Wait an hour before next check
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            system.stop()
            logger.info("Trading system shutdown complete")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()

