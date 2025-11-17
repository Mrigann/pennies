"""
Backtesting module for testing trading strategies on historical data.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from utils.logger import logger
from trading.enhanced_strategy import EnhancedStrategy
from trading.risk_manager import RiskManager
from trading.scaling_strategy import ScalingStrategy

class Backtester:
    """Backtests trading strategies on historical data."""
    
    def __init__(self, alpaca_client):
        """
        Initialize backtester.
        
        Args:
            alpaca_client: Alpaca client for fetching historical data
        """
        self.client = alpaca_client
        self.strategy = EnhancedStrategy()
        self.risk_manager = RiskManager()
        self.scaling_strategy = ScalingStrategy()
    
    def run_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        use_scaling: bool = True
    ) -> Dict[str, Any]:
        """
        Run backtest on historical data.
        
        Args:
            symbol: Stock symbol to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_capital: Starting capital
            use_scaling: Whether to use scaling exit strategy
        
        Returns:
            Backtest results dictionary
        """
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        
        # Fetch historical bars
        bars = self._fetch_historical_bars(symbol, start_date, end_date)
        if not bars or len(bars) < 50:
            return {
                "error": f"Insufficient data for {symbol}",
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        
        # Initialize backtest state
        capital = initial_capital
        positions = {}  # symbol -> position data
        trades = []
        equity_curve = []
        
        # Process bars chronologically
        for i in range(50, len(bars)):  # Start after enough bars for indicators
            current_bar = bars[i]
            current_time = datetime.fromisoformat(current_bar['timestamp'])
            current_price = current_bar['close']
            
            # Get historical bars up to current point
            historical_bars = bars[:i+1]
            
            # Generate signal
            try:
                signal_data = self._generate_signal(historical_bars, current_price)
            except Exception as e:
                logger.debug(f"Error generating signal at {current_time}: {e}")
                continue
            
            # Check for exit conditions on existing positions
            if symbol in positions:
                position = positions[symbol]
                exit_result = self._check_exit(
                    position, current_price, current_time, use_scaling
                )
                
                if exit_result:
                    # Close position
                    pnl = (current_price - position['entry_price']) * position['quantity']
                    pnl_percent = ((current_price - position['entry_price']) / position['entry_price']) * 100
                    
                    trades.append({
                        "symbol": symbol,
                        "entry_time": position['entry_time'],
                        "exit_time": current_time,
                        "entry_price": position['entry_price'],
                        "exit_price": current_price,
                        "quantity": position['quantity'],
                        "pnl": pnl,
                        "pnl_percent": pnl_percent,
                        "exit_reason": exit_result['reason']
                    })
                    
                    capital += pnl
                    del positions[symbol]
            
            # Check for entry signal
            if symbol not in positions and signal_data['signal'] in ['BUY', 'SELL']:
                if signal_data['confidence'] >= 0.6:  # Minimum confidence threshold
                    # Calculate position size
                    entry_price = signal_data['entry_price']
                    stop_loss = signal_data['stop_loss']
                    
                    position_size, risk_amount = self.risk_manager.calculate_position_size(
                        entry_price=entry_price,
                        stop_loss_price=stop_loss
                    )
                    
                    if position_size > 0 and capital >= entry_price * position_size:
                        # Enter position
                        positions[symbol] = {
                            "entry_time": current_time,
                            "entry_price": entry_price,
                            "quantity": int(position_size),
                            "stop_loss": stop_loss,
                            "scaling_plan": None
                        }
                        
                        if use_scaling:
                            # Create scaling plan
                            volatility = signal_data.get('indicators', {}).get('atr_percent', 0)
                            positions[symbol]['scaling_plan'] = self.scaling_strategy.create_scaling_plan(
                                symbol=symbol,
                                entry_price=entry_price,
                                position_size=int(position_size),
                                stop_loss=stop_loss,
                                volatility=volatility
                            )
                        
                        capital -= entry_price * position_size
            
            # Record equity
            position_value = 0
            if symbol in positions:
                position_value = (current_price - positions[symbol]['entry_price']) * positions[symbol]['quantity']
            
            equity_curve.append({
                "timestamp": current_time.isoformat(),
                "equity": capital + position_value,
                "capital": capital,
                "unrealized_pnl": position_value
            })
        
        # Close any remaining positions at end
        if symbol in positions:
            final_price = bars[-1]['close']
            position = positions[symbol]
            pnl = (final_price - position['entry_price']) * position['quantity']
            pnl_percent = ((final_price - position['entry_price']) / position['entry_price']) * 100
            
            trades.append({
                "symbol": symbol,
                "entry_time": position['entry_time'],
                "exit_time": datetime.fromisoformat(bars[-1]['timestamp']),
                "entry_price": position['entry_price'],
                "exit_price": final_price,
                "quantity": position['quantity'],
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "exit_reason": "backtest_end"
            })
            capital += pnl
        
        # Calculate statistics
        stats = self._calculate_stats(trades, initial_capital, capital)
        
        return {
            "symbol": symbol,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "initial_capital": initial_capital,
            "final_capital": capital,
            "total_return": capital - initial_capital,
            "total_return_pct": ((capital - initial_capital) / initial_capital) * 100,
            "trades": trades,
            "equity_curve": equity_curve,
            "statistics": stats
        }
    
    def _fetch_historical_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Fetch historical bars for backtesting."""
        try:
            # Fetch 1-minute bars and aggregate if needed
            bars = self.client.get_bars(
                symbol=symbol,
                timeframe="1Min",
                start=start_date.isoformat(),
                end=end_date.isoformat()
            )
            return bars or []
        except Exception as e:
            logger.error(f"Error fetching historical bars: {e}")
            return []
    
    def _generate_signal(self, bars: List[Dict], current_price: float) -> Dict[str, Any]:
        """Generate trading signal from historical bars."""
        # Use 15m bars for signal generation
        bars_15m = self._aggregate_bars(bars, "15Min")
        
        if len(bars_15m) < 20:
            return {
                'signal': 'NEUTRAL',
                'confidence': 0.0,
                'entry_price': current_price,
                'stop_loss': current_price * 0.99,
                'indicators': {}
            }
        
        signal = self.strategy.generate_entry_signal(
            bars_15m=bars_15m,
            bars_30m=[],
            bars_1h=[],
            bars_2h=[],
            bars_1m_for_stats=bars,
            quote_data=None
        )
        
        return signal
    
    def _aggregate_bars(self, bars: List[Dict], timeframe: str) -> List[Dict]:
        """Aggregate 1-minute bars to larger timeframe."""
        if not bars:
            return []
        
        # Simple aggregation (can be improved)
        if timeframe == "15Min":
            # Group every 15 bars
            aggregated = []
            for i in range(0, len(bars), 15):
                group = bars[i:i+15]
                if group:
                    aggregated.append({
                        'timestamp': group[0]['timestamp'],
                        'open': group[0]['open'],
                        'high': max(b['high'] for b in group),
                        'low': min(b['low'] for b in group),
                        'close': group[-1]['close'],
                        'volume': sum(b['volume'] for b in group)
                    })
            return aggregated
        
        return bars
    
    def _check_exit(
        self,
        position: Dict,
        current_price: float,
        current_time: datetime,
        use_scaling: bool
    ) -> Optional[Dict]:
        """Check if position should be exited."""
        # Check stop loss
        if current_price <= position['stop_loss']:
            return {'reason': 'stop_loss', 'price': current_price}
        
        # Check scaling exits if enabled
        if use_scaling and position.get('scaling_plan'):
            plan = position['scaling_plan']
            # Simplified: check if quick exit target is hit
            if 'quick_exit' in plan and current_price >= plan['quick_exit']['price']:
                return {'reason': 'quick_exit', 'price': plan['quick_exit']['price']}
        
        return None
    
    def _calculate_stats(
        self,
        trades: List[Dict],
        initial_capital: float,
        final_capital: float
    ) -> Dict[str, Any]:
        """Calculate backtest statistics."""
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0
            }
        
        winning = [t for t in trades if t['pnl'] > 0]
        losing = [t for t in trades if t['pnl'] < 0]
        
        total_profit = sum(t['pnl'] for t in winning)
        total_loss = abs(sum(t['pnl'] for t in losing))
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": (len(winning) / len(trades) * 100) if trades else 0.0,
            "profit_factor": (total_profit / total_loss) if total_loss > 0 else 0.0,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "avg_win": (total_profit / len(winning)) if winning else 0.0,
            "avg_loss": (total_loss / len(losing)) if losing else 0.0,
            "largest_win": max((t['pnl'] for t in winning), default=0.0),
            "largest_loss": min((t['pnl'] for t in losing), default=0.0),
            "sharpe_ratio": 0.0,  # Would need returns series to calculate
            "max_drawdown": 0.0  # Would need equity curve analysis
        }

