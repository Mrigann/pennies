"""
Utilities for loading and managing historical data and JSON files.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from config import settings
from utils.logger import logger

def load_json(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON data from file.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        Dictionary with loaded data, empty dict if file doesn't exist
    """
    try:
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return {}

def save_json(data: Dict[str, Any], file_path: Path) -> bool:
    """
    Save data to JSON file.
    
    Args:
        data: Data dictionary to save
        file_path: Path to save file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")
        return False

def load_daily_pnl() -> Dict[str, Any]:
    """Load daily P&L records."""
    return load_json(settings.DAILY_PNL_FILE)

def save_daily_pnl(data: Dict[str, Any]) -> bool:
    """Save daily P&L records."""
    return save_json(data, settings.DAILY_PNL_FILE)

def load_trades_history() -> List[Dict[str, Any]]:
    """Load trades history."""
    data = load_json(settings.TRADES_HISTORY_FILE)
    return data.get("trades", [])

def save_trades_history(trades: List[Dict[str, Any]]) -> bool:
    """Save trades history."""
    data = {"trades": trades, "last_updated": datetime.now().isoformat()}
    return save_json(data, settings.TRADES_HISTORY_FILE)

def load_watchlist() -> List[str]:
    """Load watchlist symbols."""
    data = load_json(settings.WATCHLIST_FILE)
    return data.get("symbols", [])

def save_watchlist(symbols: List[str]) -> bool:
    """Save watchlist symbols."""
    data = {
        "symbols": symbols,
        "last_updated": datetime.now().isoformat(),
        "notes": "Add stock symbols to track for daily trading"
    }
    return save_json(data, settings.WATCHLIST_FILE)

def get_previous_day_pnl() -> float:
    """
    Get the previous trading day's profit.
    
    Returns:
        Previous day's net profit, 0.0 if not found
    """
    pnl_data = load_daily_pnl()
    if not pnl_data:
        return 0.0
    
    # Get yesterday's date
    yesterday = date.today()
    # In production, should use previous trading day, not calendar day
    yesterday_str = yesterday.isoformat()
    
    if yesterday_str in pnl_data:
        return float(pnl_data[yesterday_str].get("net", 0.0))
    
    # If yesterday not found, get most recent entry
    if pnl_data:
        sorted_dates = sorted(pnl_data.keys(), reverse=True)
        if sorted_dates:
            return float(pnl_data[sorted_dates[0]].get("net", 0.0))
    
    return 0.0

