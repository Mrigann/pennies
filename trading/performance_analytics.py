"""
Performance analytics module for tracking trading strategy performance.
Tracks scaling strategy success, win rates, profit factors, and more.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os
from utils.logger import logger

class PerformanceAnalytics:
    """Tracks and analyzes trading performance metrics."""
    
    def __init__(self, data_file: str = "data/performance.json"):
        """
        Initialize performance analytics.
        
        Args:
            data_file: Path to JSON file for storing performance data
        """
        self.data_file = data_file
        self.ensure_data_directory()
        self.load_data()
    
    def ensure_data_directory(self):
        """Ensure data directory exists."""
        data_dir = os.path.dirname(self.data_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
    
    def load_data(self):
        """Load performance data from file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading performance data: {e}")
                self.data = self._default_data()
        else:
            self.data = self._default_data()
            self.save_data()
    
    def _default_data(self) -> Dict:
        """Return default data structure."""
        return {
            "trades": [],
            "scaling_exits": [],
            "daily_stats": {},
            "summary": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0
            }
        }
    
    def save_data(self):
        """Save performance data to file."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving performance data: {e}")
    
    def record_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: int,
        entry_time: datetime,
        exit_time: datetime,
        pnl: float,
        pnl_percent: float,
        exit_reason: str = "manual"
    ):
        """
        Record a completed trade.
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price
            exit_price: Exit price
            quantity: Number of shares
            entry_time: Entry timestamp
            exit_time: Exit timestamp
            pnl: Profit/Loss amount
            pnl_percent: Profit/Loss percentage
            exit_reason: Reason for exit (manual, stop_loss, profit_target, etc.)
        """
        trade = {
            "symbol": symbol.upper(),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "entry_time": entry_time.isoformat(),
            "exit_time": exit_time.isoformat(),
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "exit_reason": exit_reason,
            "duration_minutes": (exit_time - entry_time).total_seconds() / 60
        }
        
        self.data["trades"].append(trade)
        self._update_summary()
        self.save_data()
        logger.info(f"Recorded trade: {symbol} - P&L: ${pnl:.2f} ({pnl_percent:.2f}%)")
    
    def record_scaling_exit(
        self,
        symbol: str,
        exit_type: str,
        size: int,
        price: float,
        target_pct: float,
        actual_pct: float,
        profit: float
    ):
        """
        Record a scaling exit execution.
        
        Args:
            symbol: Stock symbol
            exit_type: Type of exit (quick_exit, runner_1, runner_2)
            size: Number of shares exited
            price: Exit price
            target_pct: Target profit percentage
            actual_pct: Actual profit percentage achieved
            profit: Profit amount
        """
        exit_record = {
            "symbol": symbol.upper(),
            "exit_type": exit_type,
            "size": size,
            "price": price,
            "target_pct": target_pct,
            "actual_pct": actual_pct,
            "profit": profit,
            "timestamp": datetime.now().isoformat(),
            "success": actual_pct >= target_pct * 0.8  # 80% of target = success
        }
        
        self.data["scaling_exits"].append(exit_record)
        self.save_data()
        logger.debug(f"Recorded scaling exit: {symbol} - {exit_type} - ${profit:.2f}")
    
    def _update_summary(self):
        """Update summary statistics."""
        trades = self.data["trades"]
        if not trades:
            return
        
        winning = [t for t in trades if t["pnl"] > 0]
        losing = [t for t in trades if t["pnl"] < 0]
        
        total_profit = sum(t["pnl"] for t in winning)
        total_loss = abs(sum(t["pnl"] for t in losing))
        
        self.data["summary"] = {
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "total_profit": total_profit,
            "total_loss": total_loss,
            "win_rate": (len(winning) / len(trades) * 100) if trades else 0.0,
            "profit_factor": (total_profit / total_loss) if total_loss > 0 else 0.0,
            "avg_win": (total_profit / len(winning)) if winning else 0.0,
            "avg_loss": (total_loss / len(losing)) if losing else 0.0,
            "largest_win": max((t["pnl"] for t in winning), default=0.0),
            "largest_loss": min((t["pnl"] for t in losing), default=0.0)
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        self._update_summary()
        return self.data["summary"]
    
    def get_scaling_performance(self) -> Dict[str, Any]:
        """Get scaling strategy performance metrics."""
        exits = self.data["scaling_exits"]
        if not exits:
            return {
                "total_exits": 0,
                "success_rate": 0.0,
                "avg_profit": 0.0,
                "by_type": {}
            }
        
        successful = [e for e in exits if e.get("success", False)]
        by_type = defaultdict(list)
        
        for exit in exits:
            by_type[exit["exit_type"]].append(exit)
        
        type_stats = {}
        for exit_type, type_exits in by_type.items():
            type_successful = [e for e in type_exits if e.get("success", False)]
            type_stats[exit_type] = {
                "count": len(type_exits),
                "success_count": len(type_successful),
                "success_rate": (len(type_successful) / len(type_exits) * 100) if type_exits else 0.0,
                "avg_profit": sum(e["profit"] for e in type_exits) / len(type_exits) if type_exits else 0.0,
                "total_profit": sum(e["profit"] for e in type_exits)
            }
        
        return {
            "total_exits": len(exits),
            "success_rate": (len(successful) / len(exits) * 100) if exits else 0.0,
            "avg_profit": sum(e["profit"] for e in exits) / len(exits) if exits else 0.0,
            "total_profit": sum(e["profit"] for e in exits),
            "by_type": type_stats
        }
    
    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily statistics for the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        daily = defaultdict(lambda: {
            "date": None,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "profit": 0.0,
            "loss": 0.0
        })
        
        for trade in self.data["trades"]:
            exit_time = datetime.fromisoformat(trade["exit_time"])
            if exit_time < cutoff:
                continue
            
            date_key = exit_time.date().isoformat()
            daily[date_key]["date"] = date_key
            daily[date_key]["trades"] += 1
            
            if trade["pnl"] > 0:
                daily[date_key]["wins"] += 1
                daily[date_key]["profit"] += trade["pnl"]
            else:
                daily[date_key]["losses"] += 1
                daily[date_key]["loss"] += abs(trade["pnl"])
        
        return sorted(daily.values(), key=lambda x: x["date"], reverse=True)
    
    def get_symbol_performance(self, symbol: str) -> Dict[str, Any]:
        """Get performance statistics for a specific symbol."""
        symbol_upper = symbol.upper()
        symbol_trades = [t for t in self.data["trades"] if t["symbol"] == symbol_upper]
        
        if not symbol_trades:
            return {
                "symbol": symbol_upper,
                "total_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0
            }
        
        winning = [t for t in symbol_trades if t["pnl"] > 0]
        
        return {
            "symbol": symbol_upper,
            "total_trades": len(symbol_trades),
            "winning_trades": len(winning),
            "win_rate": (len(winning) / len(symbol_trades) * 100) if symbol_trades else 0.0,
            "total_profit": sum(t["pnl"] for t in symbol_trades),
            "avg_profit": sum(t["pnl"] for t in symbol_trades) / len(symbol_trades),
            "best_trade": max(symbol_trades, key=lambda t: t["pnl"]),
            "worst_trade": min(symbol_trades, key=lambda t: t["pnl"])
        }

