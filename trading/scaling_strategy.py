"""
Scaling exit strategy with Fibonacci-style partial exits and risk-adjusted position sizing.
Implements quick profit taking with staggered exits for maximum profit while managing risk.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from config import settings
from utils.logger import logger

class ScalingStrategy:
    """Manages scaling exits and Fibonacci-style position management."""
    
    def __init__(self):
        """Initialize scaling strategy."""
        # Fibonacci exit ratios (can be customized)
        self.fibonacci_ratios = [0.618, 0.382, 0.236]  # 61.8%, 38.2%, 23.6%
        # Alternative: Quick profit + runner
        self.quick_exit_ratio = 0.618  # Exit 61.8% quickly
        self.runner_ratio = 0.382  # Keep 38.2% for higher targets
        
        # Profit target tiers
        self.profit_targets = {
            'quick': 0.001,      # 0.1% - immediate exit
            'conservative': 0.002,  # 0.2% - quick profit
            'moderate': 0.005,   # 0.5% - standard target
            'aggressive': 0.01,  # 1% - higher risk
            'runner': 0.02       # 2% - let winners run
        }
    
    def calculate_fibonacci_exits(
        self,
        entry_price: float,
        position_size: int,
        profit_targets: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate Fibonacci-style exit levels and position scaling.
        
        Args:
            entry_price: Entry price
            position_size: Total position size
            profit_targets: Custom profit targets (optional)
        
        Returns:
            Dictionary with exit plan
        """
        if position_size < 1:
            return {}
        
        targets = profit_targets or self.profit_targets
        
        # Calculate exit prices
        exit_prices = {
            'quick': entry_price * (1 + targets['quick']),
            'conservative': entry_price * (1 + targets['conservative']),
            'moderate': entry_price * (1 + targets['moderate']),
            'aggressive': entry_price * (1 + targets['aggressive']),
            'runner': entry_price * (1 + targets['runner'])
        }
        
        # Calculate position splits using Fibonacci ratios
        # Example: 13 shares -> 8 shares (61.8%) + 5 shares (38.2%)
        quick_exit_size = int(position_size * self.quick_exit_ratio)
        runner_size = position_size - quick_exit_size
        
        # Further split runner if position is large enough
        runner_exits = {}
        if runner_size >= 3:
            # Split runner into multiple exits
            moderate_exit_size = int(runner_size * 0.5)  # 50% at moderate target
            aggressive_exit_size = runner_size - moderate_exit_size  # Rest at aggressive
            
            runner_exits = {
                'moderate': {
                    'size': moderate_exit_size,
                    'price': exit_prices['moderate'],
                    'target_pct': targets['moderate'] * 100
                },
                'aggressive': {
                    'size': aggressive_exit_size,
                    'price': exit_prices['aggressive'],
                    'target_pct': targets['aggressive'] * 100
                }
            }
        else:
            # Small runner, single exit
            runner_exits = {
                'aggressive': {
                    'size': runner_size,
                    'price': exit_prices['aggressive'],
                    'target_pct': targets['aggressive'] * 100
                }
            }
        
        return {
            'entry_price': entry_price,
            'total_size': position_size,
            'quick_exit': {
                'size': quick_exit_size,
                'price': exit_prices['quick'],
                'target_pct': targets['quick'] * 100,
                'priority': 1  # Execute first
            },
            'runner_exits': runner_exits,
            'all_exit_prices': exit_prices,
            'expected_profit': self._calculate_expected_profit(
                entry_price, quick_exit_size, runner_size,
                exit_prices['quick'], exit_prices['aggressive']
            ),
            'risk_reward_ratio': self._calculate_risk_reward(
                entry_price, exit_prices['quick'], exit_prices['aggressive']
            )
        }
    
    def _calculate_expected_profit(
        self,
        entry: float,
        quick_size: int,
        runner_size: int,
        quick_price: float,
        runner_price: float
    ) -> Dict[str, float]:
        """Calculate expected profit from scaling exits."""
        quick_profit = quick_size * (quick_price - entry)
        runner_profit = runner_size * (runner_price - entry)
        total_profit = quick_profit + runner_profit
        total_cost = (quick_size + runner_size) * entry
        
        return {
            'quick_profit': quick_profit,
            'runner_profit': runner_profit,
            'total_profit': total_profit,
            'total_profit_pct': (total_profit / total_cost) * 100 if total_cost > 0 else 0
        }
    
    def _calculate_risk_reward(
        self,
        entry: float,
        quick_target: float,
        runner_target: float,
        stop_loss: float = None
    ) -> Dict[str, float]:
        """Calculate risk/reward ratios."""
        if stop_loss is None:
            stop_loss = entry * (1 - settings.STOP_LOSS_PERCENT)
        
        quick_reward = quick_target - entry
        runner_reward = runner_target - entry
        risk = entry - stop_loss
        
        return {
            'quick_rr': quick_reward / risk if risk > 0 else 0,
            'runner_rr': runner_reward / risk if risk > 0 else 0,
            'risk_amount': risk,
            'quick_reward': quick_reward,
            'runner_reward': runner_reward
        }
    
    def create_scaling_plan(
        self,
        symbol: str,
        entry_price: float,
        position_size: int,
        stop_loss: float,
        current_price: float = None,
        volatility: float = None
    ) -> Dict[str, Any]:
        """
        Create a complete scaling exit plan based on market conditions.
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price
            position_size: Total position size
            stop_loss: Stop loss price
            current_price: Current market price (for dynamic adjustment)
            volatility: Current volatility (ATR %)
        
        Returns:
            Complete scaling plan
        """
        # Adjust profit targets based on volatility
        adjusted_targets = self._adjust_targets_for_volatility(
            self.profit_targets.copy(),
            volatility
        )
        
        # Calculate Fibonacci exits
        exit_plan = self.calculate_fibonacci_exits(
            entry_price,
            position_size,
            adjusted_targets
        )
        
        # Add timing information
        exit_plan['timing'] = {
            'quick_exit_time': 'immediate',  # Execute as soon as target hit
            'runner_exit_time': 'extended',  # Can hold longer
            'max_hold_time': settings.MAX_POSITION_HOLD_TIME_MINUTES
        }
        
        # Add risk management
        exit_plan['risk_management'] = {
            'stop_loss': stop_loss,
            'stop_loss_pct': ((entry_price - stop_loss) / entry_price) * 100,
            'trailing_stop': stop_loss,  # Will be updated as price moves
            'max_loss': position_size * (entry_price - stop_loss)
        }
        
        # Add execution priority
        exit_plan['execution_priority'] = [
            {
                'order': 1,
                'type': 'quick_exit',
                'size': exit_plan['quick_exit']['size'],
                'target': exit_plan['quick_exit']['price'],
                'description': 'Quick profit taking - execute immediately'
            }
        ]
        
        # Add runner exits
        for exit_name, exit_data in exit_plan['runner_exits'].items():
            exit_plan['execution_priority'].append({
                'order': len(exit_plan['execution_priority']) + 1,
                'type': f'runner_{exit_name}',
                'size': exit_data['size'],
                'target': exit_data['price'],
                'description': f'Runner exit at {exit_data["target_pct"]:.2f}% profit'
            })
        
        exit_plan['symbol'] = symbol
        exit_plan['created_at'] = datetime.now().isoformat()
        
        return exit_plan
    
    def _adjust_targets_for_volatility(
        self,
        targets: Dict[str, float],
        volatility: float = None
    ) -> Dict[str, float]:
        """Adjust profit targets based on volatility."""
        if volatility is None:
            return targets
        
        # Higher volatility = wider targets
        # Lower volatility = tighter targets
        volatility_multiplier = 1.0
        
        if volatility > 3.0:  # High volatility
            volatility_multiplier = 1.5
        elif volatility > 2.0:  # Medium volatility
            volatility_multiplier = 1.2
        elif volatility < 1.0:  # Low volatility
            volatility_multiplier = 0.8
        
        adjusted = {}
        for key, value in targets.items():
            adjusted[key] = value * volatility_multiplier
        
        return adjusted
    
    def check_exit_conditions(
        self,
        scaling_plan: Dict[str, Any],
        current_price: float,
        entry_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Check if any exit conditions are met.
        
        Args:
            scaling_plan: The scaling exit plan
            current_price: Current market price
            entry_time: When position was entered
        
        Returns:
            List of exit orders to execute
        """
        exits_to_execute = []
        
        # Check stop loss first
        stop_loss = scaling_plan['risk_management']['stop_loss']
        if current_price <= stop_loss:
            # Emergency exit - close entire position
            exits_to_execute.append({
                'type': 'stop_loss',
                'size': scaling_plan['total_size'],
                'price': stop_loss,
                'reason': 'Stop loss triggered',
                'priority': 0  # Highest priority
            })
            return exits_to_execute
        
        # Check each exit target
        for exit_order in scaling_plan['execution_priority']:
            target_price = exit_order['target']
            exit_size = exit_order['size']
            
            # Check if target is hit
            if current_price >= target_price:
                # Check if this exit hasn't been executed yet
                # (In real implementation, track executed exits)
                exits_to_execute.append({
                    'type': exit_order['type'],
                    'size': exit_size,
                    'price': target_price,
                    'reason': f'Profit target hit: {exit_order["description"]}',
                    'priority': exit_order['order']
                })
        
        # Sort by priority
        exits_to_execute.sort(key=lambda x: x['priority'])
        
        return exits_to_execute
    
    def optimize_position_size(
        self,
        available_capital: float,
        entry_price: float,
        stop_loss: float,
        risk_per_trade: float = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Optimize position size for scaling strategy.
        
        Args:
            available_capital: Available capital
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_per_trade: Risk amount per trade (optional)
        
        Returns:
            Tuple of (optimal_size, sizing_details)
        """
        if risk_per_trade is None:
            # Default: risk 1% of capital per trade
            risk_per_trade = available_capital * 0.01
        
        # Calculate price risk
        price_risk = entry_price - stop_loss
        if price_risk <= 0:
            return 0, {}
        
        # Calculate base position size
        base_size = int(risk_per_trade / price_risk)
        
        # Ensure minimum size for scaling (need at least 2 shares)
        if base_size < 2:
            return 0, {'reason': 'Position too small for scaling strategy'}
        
        # Calculate scaling breakdown
        quick_size = int(base_size * self.quick_exit_ratio)
        runner_size = base_size - quick_size
        
        # Ensure minimum sizes
        if quick_size < 1:
            quick_size = 1
            runner_size = base_size - 1
        
        if runner_size < 1:
            runner_size = 1
            quick_size = base_size - 1
        
        return base_size, {
            'total_size': base_size,
            'quick_exit_size': quick_size,
            'runner_size': runner_size,
            'risk_amount': base_size * price_risk,
            'capital_required': base_size * entry_price,
            'risk_per_share': price_risk,
            'risk_pct': (price_risk / entry_price) * 100
        }

