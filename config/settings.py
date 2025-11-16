"""
Configuration settings for the penny trading system.
All trading parameters, API credentials, and risk settings are defined here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Load environment variables from .env file
env_path = BASE_DIR / ".env"
if env_path.exists():
    result = load_dotenv(env_path, override=True)
    print(f"Loaded .env from: {env_path} (success: {result})")
else:
    # Try loading from current directory as fallback
    result = load_dotenv(override=True)
    print(f"Loaded .env from current directory (success: {result})")

# Alpaca API Credentials
# Set these as environment variables or update directly
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "").strip()
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "").strip()

# If keys are still empty after loading .env, set them directly as fallback
# This ensures they're always available
if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    # Direct fallback values (from your README)
    ALPACA_API_KEY = "PK37L27LF5PPSMP3S3TGJKR5KM"
    ALPACA_SECRET_KEY = "GZqitSttHPv76CKcbLTPhT8M3XWAwvpBxxtThrfrevqj"
    print("Using fallback API keys from settings.py")

# Debug output
if ALPACA_API_KEY:
    print(f"API Key loaded: {ALPACA_API_KEY[:10]}... (length: {len(ALPACA_API_KEY)})")
else:
    print("WARNING: ALPACA_API_KEY is not set!")
    
if ALPACA_SECRET_KEY:
    print(f"Secret Key loaded: {ALPACA_SECRET_KEY[:10]}... (length: {len(ALPACA_SECRET_KEY)})")
else:
    print("WARNING: ALPACA_SECRET_KEY is not set!")

ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")  # Paper trading default
ALPACA_DATA_URL = os.getenv("ALPACA_DATA_URL", "https://data.alpaca.markets")

# Trading Mode: 'paper' or 'live'
TRADING_MODE = os.getenv("TRADING_MODE", "paper")

# Capital Settings
STARTING_CAPITAL = float(os.getenv("STARTING_CAPITAL", "5000.0"))
DAILY_BETTING_PERCENTAGE = float(os.getenv("DAILY_BETTING_PERCENTAGE", "0.15"))  # 15% default

# Risk Parameters
MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "0.02"))  # 2% of capital
MAX_DAILY_LOSS_ABSOLUTE = float(os.getenv("MAX_DAILY_LOSS_ABSOLUTE", "100.0"))  # $100 hard stop
PROFIT_TARGET_PERCENT = float(os.getenv("PROFIT_TARGET_PERCENT", "0.015"))  # 1.5% per trade
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "0.0075"))  # 0.75% per trade
MAX_POSITIONS_PER_DAY = int(os.getenv("MAX_POSITIONS_PER_DAY", "8"))

# Strategy Parameters
MIN_STOCK_PRICE = float(os.getenv("MIN_STOCK_PRICE", "0.10"))
MAX_STOCK_PRICE = float(os.getenv("MAX_STOCK_PRICE", "5.00"))
MIN_VOLUME_MULTIPLIER = float(os.getenv("MIN_VOLUME_MULTIPLIER", "2.0"))  # 2x average volume
LOOKBACK_PERIOD = int(os.getenv("LOOKBACK_PERIOD", "20"))  # Bars for indicators

# Scanner Parameters
SCANNER_MIN_VOLUME_MULTIPLIER = float(os.getenv("SCANNER_MIN_VOLUME_MULTIPLIER", "2.0"))
SCANNER_MIN_VOLATILITY_PERCENT = float(os.getenv("SCANNER_MIN_VOLATILITY_PERCENT", "1.5"))  # ATR % of price
SCANNER_TOP_RESULTS = int(os.getenv("SCANNER_TOP_RESULTS", "20"))

# Technical Indicators
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70"))
MACD_FAST = int(os.getenv("MACD_FAST", "12"))
MACD_SLOW = int(os.getenv("MACD_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))
ATR_PERIOD = int(os.getenv("ATR_PERIOD", "14"))

# Time-based Exit
MAX_POSITION_HOLD_TIME_MINUTES = int(os.getenv("MAX_POSITION_HOLD_TIME_MINUTES", "30"))
EXIT_BEFORE_MARKET_CLOSE_MINUTES = int(os.getenv("EXIT_BEFORE_MARKET_CLOSE_MINUTES", "15"))

# Data Paths
DATA_DIR = BASE_DIR / "data"
DAILY_PNL_FILE = DATA_DIR / "daily_pnl.json"
TRADES_HISTORY_FILE = DATA_DIR / "trades_history.json"
SCANNER_RESULTS_FILE = DATA_DIR / "scanner_results.json"
WATCHLIST_FILE = BASE_DIR / "config" / "watchlist.json"

# Logging
LOG_DIR = BASE_DIR / "logs"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOG_DIR / "trading.log"

# Web Application
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
WEB_DEBUG = os.getenv("WEB_DEBUG", "False").lower() == "true"

# Ensure data and log directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

