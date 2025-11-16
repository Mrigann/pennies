"""
Visualization utilities for generating P&L graphs and analytics charts.
"""

import json
from typing import Dict, List
from datetime import datetime, timedelta
from pathlib import Path
from config import settings
from utils.logger import logger
from utils.data_loader import load_daily_pnl, load_trades_history

def generate_daily_pnl_chart(start_date: str = None, end_date: str = None) -> Dict:
    """
    Generate daily P&L line chart data.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        Dictionary with chart data for Chart.js
    """
    pnl_data = load_daily_pnl()
    
    if not pnl_data:
        return {
            "labels": [],
            "datasets": [{
                "label": "Daily P&L",
                "data": [],
                "borderColor": "rgb(75, 192, 192)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)"
            }]
        }
    
    # Filter by date range if provided
    dates = sorted([d for d in pnl_data.keys()])
    if start_date:
        dates = [d for d in dates if d >= start_date]
    if end_date:
        dates = [d for d in dates if d <= end_date]
    
    # Extract data
    net_values = [pnl_data[d].get('net', 0) for d in dates]
    
    return {
        "labels": dates,
        "datasets": [{
            "label": "Daily Net P&L ($)",
            "data": net_values,
            "borderColor": "rgb(75, 192, 192)",
            "backgroundColor": "rgba(75, 192, 192, 0.2)",
            "tension": 0.1
        }]
    }

def generate_cumulative_pnl_chart(start_date: str = None, end_date: str = None) -> Dict:
    """
    Generate cumulative P&L chart data.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        Dictionary with chart data
    """
    pnl_data = load_daily_pnl()
    
    if not pnl_data:
        return {
            "labels": [],
            "datasets": [{
                "label": "Cumulative P&L",
                "data": [],
                "borderColor": "rgb(54, 162, 235)",
                "backgroundColor": "rgba(54, 162, 235, 0.2)"
            }]
        }
    
    dates = sorted([d for d in pnl_data.keys()])
    if start_date:
        dates = [d for d in dates if d >= start_date]
    if end_date:
        dates = [d for d in dates if d <= end_date]
    
    cumulative = 0
    cumulative_values = []
    for date in dates:
        cumulative += pnl_data[date].get('net', 0)
        cumulative_values.append(cumulative)
    
    return {
        "labels": dates,
        "datasets": [{
            "label": "Cumulative P&L ($)",
            "data": cumulative_values,
            "borderColor": "rgb(54, 162, 235)",
            "backgroundColor": "rgba(54, 162, 235, 0.2)",
            "fill": True
        }]
    }

def generate_win_loss_distribution() -> Dict:
    """
    Generate win/loss distribution chart.
    
    Returns:
        Dictionary with chart data
    """
    pnl_data = load_daily_pnl()
    
    if not pnl_data:
        return {
            "labels": ["Wins", "Losses"],
            "datasets": [{
                "label": "Days",
                "data": [0, 0],
                "backgroundColor": ["rgba(75, 192, 192, 0.6)", "rgba(255, 99, 132, 0.6)"]
            }]
        }
    
    winning_days = sum(1 for d in pnl_data.values() if d.get('net', 0) > 0)
    losing_days = sum(1 for d in pnl_data.values() if d.get('net', 0) < 0)
    
    return {
        "labels": ["Winning Days", "Losing Days"],
        "datasets": [{
            "label": "Number of Days",
            "data": [winning_days, losing_days],
            "backgroundColor": [
                "rgba(75, 192, 192, 0.6)",
                "rgba(255, 99, 132, 0.6)"
            ]
        }]
    }

def generate_trade_frequency_chart() -> Dict:
    """
    Generate trades per day chart.
    
    Returns:
        Dictionary with chart data
    """
    pnl_data = load_daily_pnl()
    
    if not pnl_data:
        return {
            "labels": [],
            "datasets": [{
                "label": "Trades per Day",
                "data": [],
                "backgroundColor": "rgba(153, 102, 255, 0.6)"
            }]
        }
    
    dates = sorted(pnl_data.keys())
    trade_counts = [pnl_data[d].get('trades', 0) for d in dates]
    
    return {
        "labels": dates,
        "datasets": [{
            "label": "Number of Trades",
            "data": trade_counts,
            "backgroundColor": "rgba(153, 102, 255, 0.6)"
        }]
    }

def generate_performance_metrics() -> Dict:
    """
    Generate performance metrics summary.
    
    Returns:
        Dictionary with performance metrics
    """
    pnl_data = load_daily_pnl()
    trades = load_trades_history()
    
    if not pnl_data:
        return {
            "total_days": 0,
            "winning_days": 0,
            "losing_days": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "net_pnl": 0.0,
            "win_rate": 0.0,
            "avg_daily_pnl": 0.0,
            "best_day": 0.0,
            "worst_day": 0.0
        }
    
    total_profit = sum(d.get('realized_profit', 0) for d in pnl_data.values())
    total_loss = sum(d.get('realized_loss', 0) for d in pnl_data.values())
    net_pnl = sum(d.get('net', 0) for d in pnl_data.values())
    
    winning_days = sum(1 for d in pnl_data.values() if d.get('net', 0) > 0)
    losing_days = sum(1 for d in pnl_data.values() if d.get('net', 0) < 0)
    total_days = len(pnl_data)
    
    win_rate = winning_days / total_days if total_days > 0 else 0.0
    avg_daily_pnl = net_pnl / total_days if total_days > 0 else 0.0
    
    daily_nets = [d.get('net', 0) for d in pnl_data.values()]
    best_day = max(daily_nets) if daily_nets else 0.0
    worst_day = min(daily_nets) if daily_nets else 0.0
    
    # Calculate win rate from trades
    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    trade_win_rate = len(winning_trades) / len(trades) if trades else 0.0
    
    return {
        "total_days": total_days,
        "winning_days": winning_days,
        "losing_days": losing_days,
        "total_profit": total_profit,
        "total_loss": total_loss,
        "net_pnl": net_pnl,
        "win_rate": win_rate,
        "trade_win_rate": trade_win_rate,
        "avg_daily_pnl": avg_daily_pnl,
        "best_day": best_day,
        "worst_day": worst_day,
        "total_trades": len(trades)
    }

