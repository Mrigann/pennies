"""
Exit manager for handling partial exits and scaling strategies.
Tracks positions and executes exits based on scaling plans.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from config import settings
from utils.logger import logger
from trading.scaling_strategy import ScalingStrategy

class ExitManager:
    """Manages position exits with scaling strategies."""
    
    def __init__(self, alpaca_client):
        """
        Initialize exit manager.
        
        Args:
            alpaca_client: Alpaca client instance
        """
        self.client = alpaca_client
        self.scaling_strategy = ScalingStrategy()
        self.active_positions = {}  # symbol -> position data
        self.executed_exits = {}  # symbol -> list of executed exits
    
    def register_position(
        self,
        symbol: str,
        entry_price: float,
        position_size: int,
        stop_loss: float,
        volatility: float = None
    ) -> Dict[str, Any]:
        """
        Register a new position with scaling exit plan.
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price
            position_size: Position size
            stop_loss: Stop loss price
            volatility: Current volatility (optional)
        
        Returns:
            Scaling plan
        """
        scaling_plan = self.scaling_strategy.create_scaling_plan(
            symbol=symbol,
            entry_price=entry_price,
            position_size=position_size,
            stop_loss=stop_loss,
            volatility=volatility
        )
        
        self.active_positions[symbol.upper()] = {
            'symbol': symbol.upper(),
            'entry_price': entry_price,
            'total_size': position_size,
            'remaining_size': position_size,
            'stop_loss': stop_loss,
            'scaling_plan': scaling_plan,
            'entry_time': datetime.now(),
            'exits_executed': []
        }
        
        self.executed_exits[symbol.upper()] = []
        
        logger.info(f"Registered position: {symbol} - {position_size} shares @ ${entry_price:.4f}")
        logger.info(f"Scaling plan: Quick exit {scaling_plan['quick_exit']['size']} shares @ ${scaling_plan['quick_exit']['price']:.4f}")
        
        return scaling_plan
    
    def check_and_execute_exits(self, symbol: str, current_price: float) -> List[Dict[str, Any]]:
        """
        Check exit conditions and execute if needed.
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
        
        Returns:
            List of executed exits
        """
        symbol_upper = symbol.upper()
        
        if symbol_upper not in self.active_positions:
            return []
        
        position = self.active_positions[symbol_upper]
        scaling_plan = position['scaling_plan']
        entry_time = position['entry_time']
        
        # Check exit conditions
        exits_to_execute = self.scaling_strategy.check_exit_conditions(
            scaling_plan,
            current_price,
            entry_time
        )
        
        executed = []
        
        for exit_order in exits_to_execute:
            # Check if we still have shares to exit
            if position['remaining_size'] <= 0:
                continue
            
            # Determine actual exit size (don't exceed remaining)
            exit_size = min(exit_order['size'], position['remaining_size'])
            
            if exit_size <= 0:
                continue
            
            # Execute exit
            try:
                # Place sell order
                order = self.client.place_order(
                    symbol=symbol_upper,
                    qty=exit_size,
                    side='sell',
                    order_type='market'
                )
                
                if order:
                    # Record exit
                    exit_record = {
                        'order_id': order.get('id'),
                        'type': exit_order['type'],
                        'size': exit_size,
                        'price': exit_order['price'],
                        'executed_at': datetime.now().isoformat(),
                        'reason': exit_order['reason']
                    }
                    
                    executed.append(exit_record)
                    self.executed_exits[symbol_upper].append(exit_record)
                    position['exits_executed'].append(exit_record)
                    position['remaining_size'] -= exit_size
                    
                    logger.info(
                        f"Executed exit: {symbol_upper} - {exit_size} shares @ ${exit_order['price']:.4f} "
                        f"({exit_order['reason']})"
                    )
                    
                    # If position fully closed, remove from active
                    if position['remaining_size'] <= 0:
                        logger.info(f"Position fully closed: {symbol_upper}")
                        del self.active_positions[symbol_upper]
                
            except Exception as e:
                logger.error(f"Error executing exit for {symbol_upper}: {e}")
        
        return executed
    
    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[float]:
        """
        Update trailing stop loss for position.
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
        
        Returns:
            New trailing stop price or None
        """
        symbol_upper = symbol.upper()
        
        if symbol_upper not in self.active_positions:
            return None
        
        position = self.active_positions[symbol_upper]
        entry_price = position['entry_price']
        current_stop = position['stop_loss']
        
        # Calculate new trailing stop (1% trailing)
        # Use simple calculation to avoid circular dependency
        trailing_percent = 0.01
        
        # If price has moved up, calculate new trailing stop
        if current_price > entry_price:
            new_trailing_stop = current_price * (1 - trailing_percent)
            # Trailing stop should never go below initial stop
            new_trailing_stop = max(new_trailing_stop, current_stop)
        else:
            # Price hasn't moved up, keep current stop
            new_trailing_stop = current_stop
        
        # Only update if trailing stop is higher than current
        if new_trailing_stop > current_stop:
            position['stop_loss'] = new_trailing_stop
            position['scaling_plan']['risk_management']['trailing_stop'] = new_trailing_stop
            logger.debug(f"Updated trailing stop for {symbol_upper}: ${new_trailing_stop:.4f}")
            return new_trailing_stop
        
        return None
    
    def get_position_status(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a position.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Position status dictionary
        """
        symbol_upper = symbol.upper()
        
        if symbol_upper not in self.active_positions:
            return None
        
        position = self.active_positions[symbol_upper]
        scaling_plan = position['scaling_plan']
        
        return {
            'symbol': symbol_upper,
            'entry_price': position['entry_price'],
            'total_size': position['total_size'],
            'remaining_size': position['remaining_size'],
            'exited_size': position['total_size'] - position['remaining_size'],
            'exits_executed': len(position['exits_executed']),
            'stop_loss': position['stop_loss'],
            'scaling_plan': scaling_plan,
            'entry_time': position['entry_time'].isoformat()
        }
    
    def get_all_active_positions(self) -> List[Dict[str, Any]]:
        """Get all active positions with scaling plans."""
        return list(self.active_positions.values())
    
    def close_position_fully(self, symbol: str, reason: str = "Manual close") -> bool:
        """
        Close entire position immediately.
        
        Args:
            symbol: Stock symbol
            reason: Reason for closing
        
        Returns:
            True if successful
        """
        symbol_upper = symbol.upper()
        
        if symbol_upper not in self.active_positions:
            return False
        
        position = self.active_positions[symbol_upper]
        remaining_size = position['remaining_size']
        
        if remaining_size <= 0:
            return False
        
        try:
            order = self.client.place_order(
                symbol=symbol_upper,
                qty=remaining_size,
                side='sell',
                order_type='market'
            )
            
            if order:
                # Record exit
                exit_record = {
                    'order_id': order.get('id'),
                    'type': 'full_close',
                    'size': remaining_size,
                    'price': position['entry_price'],  # Market price will be filled
                    'executed_at': datetime.now().isoformat(),
                    'reason': reason
                }
                
                self.executed_exits[symbol_upper].append(exit_record)
                position['exits_executed'].append(exit_record)
                position['remaining_size'] = 0
                
                del self.active_positions[symbol_upper]
                
                logger.info(f"Fully closed position: {symbol_upper} - {remaining_size} shares ({reason})")
                return True
        
        except Exception as e:
            logger.error(f"Error closing position {symbol_upper}: {e}")
            return False
        
        return False

