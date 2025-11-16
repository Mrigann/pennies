"""
Position tracker for monitoring open positions and calculating P&L.
Handles profit targets, stop losses, and daily P&L aggregation.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from config import settings
from utils.logger import logger
from utils.data_loader import load_daily_pnl, save_daily_pnl, load_trades_history, save_trades_history
from trading.alpaca_client import AlpacaClient
from trading.strategy import TradingStrategy

class PositionTracker:
    """Tracks positions and manages exits."""
    
    def __init__(self, alpaca_client: AlpacaClient, strategy: TradingStrategy):
        """
        Initialize position tracker.
        
        Args:
            alpaca_client: Alpaca client instance
            strategy: Trading strategy instance
        """
        self.client = alpaca_client
        self.strategy = strategy
        self.positions = {}  # symbol -> position dict
        self.daily_trades = []
    
    def track_positions(self) -> List[Dict[str, Any]]:
        """
        Track all open positions and update P&L.
        
        Returns:
            List of position dictionaries with updated P&L
        """
        try:
            # Get positions from Alpaca
            alpaca_positions = self.client.get_positions()
            
            updated_positions = []
            for pos in alpaca_positions:
                symbol = pos['symbol']
                position_info = self._update_position(pos)
                if position_info:
                    updated_positions.append(position_info)
                    self.positions[symbol] = position_info
            
            # Remove closed positions
            active_symbols = {p['symbol'] for p in alpaca_positions}
            closed_symbols = set(self.positions.keys()) - active_symbols
            for symbol in closed_symbols:
                if symbol in self.positions:
                    logger.info(f"Position {symbol} closed")
                    del self.positions[symbol]
            
            return updated_positions
        except Exception as e:
            logger.error(f"Error tracking positions: {e}")
            return []
    
    def _update_position(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update position information and check exit conditions.
        
        Args:
            position: Position dictionary from Alpaca
        
        Returns:
            Updated position dictionary
        """
        symbol = position['symbol']
        current_price = position['current_price']
        
        # Get stored position info or create new
        if symbol not in self.positions:
            # New position - initialize
            self.positions[symbol] = {
                'symbol': symbol,
                'qty': position['qty'],
                'entry_price': position['avg_entry_price'],
                'entry_time': datetime.now(),
                'stop_loss': None,
                'profit_target': None,
                'strategy': 'unknown'
            }
            
            # Calculate stop loss and profit target
            entry_price = position['avg_entry_price']
            self.positions[symbol]['stop_loss'] = self.strategy.calculate_stop_loss(entry_price)
            self.positions[symbol]['profit_target'] = self.strategy.calculate_profit_target(entry_price)
        
        stored_pos = self.positions[symbol]
        
        # Update current values
        stored_pos['current_price'] = current_price
        stored_pos['market_value'] = position['market_value']
        stored_pos['unrealized_pl'] = position['unrealized_pl']
        stored_pos['unrealized_plpc'] = position['unrealized_plpc']
        
        # Check exit conditions
        should_exit, reason, exit_price = self.strategy.check_exit_conditions(
            stored_pos,
            current_price,
            stored_pos.get('entry_time')
        )
        
        if should_exit:
            logger.info(f"Exit signal for {symbol}: {reason} @ ${exit_price:.4f}")
            self._exit_position(symbol, reason, exit_price)
            return None
        
        return stored_pos
    
    def _exit_position(self, symbol: str, reason: str, exit_price: float):
        """
        Exit a position.
        
        Args:
            symbol: Stock symbol
            reason: Exit reason
            exit_price: Exit price
        """
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Place sell order
        qty = abs(position['qty'])
        order = self.client.place_order(
            symbol=symbol,
            qty=qty,
            side='sell',
            order_type='market'
        )
        
        if order:
            # Calculate trade P&L
            entry_price = position['entry_price']
            pnl = (exit_price - entry_price) * qty
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            
            # Record trade
            trade_record = {
                'symbol': symbol,
                'entry_time': position['entry_time'].isoformat(),
                'exit_time': datetime.now().isoformat(),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'qty': qty,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'exit_reason': reason,
                'strategy': position.get('strategy', 'unknown'),
                'order_id': order.get('id')
            }
            
            self.daily_trades.append(trade_record)
            logger.info(
                f"Position exited: {symbol} | "
                f"Entry: ${entry_price:.4f} | "
                f"Exit: ${exit_price:.4f} | "
                f"P&L: ${pnl:.2f} ({pnl_percent:.2f}%) | "
                f"Reason: {reason}"
            )
            
            # Save to history
            self._save_trade_to_history(trade_record)
        else:
            logger.error(f"Failed to exit position {symbol}")
    
    def calculate_unrealized_pnl(self, position: Dict[str, Any]) -> float:
        """
        Calculate unrealized P&L for a position.
        
        Args:
            position: Position dictionary
        
        Returns:
            Unrealized P&L
        """
        return position.get('unrealized_pl', 0.0)
    
    def check_profit_targets(self) -> List[Dict[str, Any]]:
        """
        Check all positions for profit target hits.
        
        Returns:
            List of positions that hit profit targets
        """
        positions_to_exit = []
        
        for symbol, position in self.positions.items():
            current_price = position.get('current_price', 0)
            profit_target = position.get('profit_target', 0)
            
            if profit_target and current_price >= profit_target:
                positions_to_exit.append({
                    'symbol': symbol,
                    'reason': 'profit_target',
                    'exit_price': profit_target
                })
        
        return positions_to_exit
    
    def check_stop_losses(self) -> List[Dict[str, Any]]:
        """
        Check all positions for stop loss hits.
        
        Returns:
            List of positions that hit stop losses
        """
        positions_to_exit = []
        
        for symbol, position in self.positions.items():
            current_price = position.get('current_price', 0)
            stop_loss = position.get('stop_loss', 0)
            
            if stop_loss and current_price <= stop_loss:
                positions_to_exit.append({
                    'symbol': symbol,
                    'reason': 'stop_loss',
                    'exit_price': stop_loss
                })
        
        return positions_to_exit
    
    def update_daily_pnl(self) -> Dict[str, Any]:
        """
        Update and aggregate daily P&L.
        
        Returns:
            Daily P&L summary
        """
        # Calculate from positions
        total_unrealized_pl = sum(
            pos.get('unrealized_pl', 0) for pos in self.positions.values()
        )
        
        # Calculate from closed trades
        realized_profit = sum(t.get('pnl', 0) for t in self.daily_trades if t.get('pnl', 0) > 0)
        realized_loss = sum(t.get('pnl', 0) for t in self.daily_trades if t.get('pnl', 0) < 0)
        
        net_pnl = realized_profit + realized_loss + total_unrealized_pl
        
        # Calculate win rate
        winning_trades = [t for t in self.daily_trades if t.get('pnl', 0) > 0]
        win_rate = len(winning_trades) / len(self.daily_trades) if self.daily_trades else 0.0
        
        daily_summary = {
            'date': datetime.now().date().isoformat(),
            'realized_profit': realized_profit,
            'realized_loss': realized_loss,
            'unrealized_pl': total_unrealized_pl,
            'net': net_pnl,
            'trades': len(self.daily_trades),
            'win_rate': win_rate,
            'winning_trades': len(winning_trades),
            'losing_trades': len(self.daily_trades) - len(winning_trades)
        }
        
        return daily_summary
    
    def save_daily_pnl(self, date: str = None) -> bool:
        """
        Save daily P&L to JSON file.
        
        Args:
            date: Date string (defaults to today)
        
        Returns:
            True if successful
        """
        if date is None:
            date = datetime.now().date().isoformat()
        
        summary = self.update_daily_pnl()
        summary['date'] = date
        
        # Load existing data
        pnl_data = load_daily_pnl()
        pnl_data[date] = summary
        
        # Save
        success = save_daily_pnl(pnl_data)
        if success:
            logger.info(f"Daily P&L saved for {date}: ${summary['net']:.2f}")
        
        return success
    
    def _save_trade_to_history(self, trade: Dict[str, Any]):
        """Save trade to history file."""
        trades = load_trades_history()
        trades.append(trade)
        save_trades_history(trades)
    
    def get_daily_trades(self) -> List[Dict[str, Any]]:
        """Get all trades for today."""
        return self.daily_trades
    
    def get_active_positions(self) -> List[Dict[str, Any]]:
        """Get all active positions."""
        return list(self.positions.values())

