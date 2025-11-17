# Penny Trading System - Complete Documentation

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage Guide](#usage-guide)
6. [API Reference](#api-reference)
7. [Strategy Guide](#strategy-guide)
8. [Risk Management](#risk-management)
9. [Performance Analytics](#performance-analytics)
10. [Backtesting](#backtesting)
11. [Troubleshooting](#troubleshooting)

## Overview

The Penny Trading System is a comprehensive algorithmic trading platform designed for penny stock trading with advanced risk management, multi-timeframe analysis, and automated scaling exit strategies.

### Key Capabilities

- **Real-time Market Scanning**: Continuously monitors watchlist symbols for trading opportunities
- **Multi-timeframe Analysis**: Analyzes price action across 15m, 30m, 1h, and 2h timeframes
- **Intelligent Entry/Exit**: Uses bid/ask analysis, order flow, and technical indicators
- **Scaling Exit Strategy**: Fibonacci-style partial exits (61.8% quick, 38.2% runner)
- **Risk Management**: Stop loss, trailing stops, daily loss limits
- **Performance Tracking**: Comprehensive analytics and backtesting

## Features

### Core Trading Features

1. **Continuous Scanner**
   - Monitors symbols every 30 seconds
   - Generates real-time BUY/SELL signals
   - Multi-timeframe confirmation
   - Profit probability calculations

2. **Smart Entry System**
   - Bid/Ask analysis for optimal entry timing
   - Order flow direction detection
   - Spread and liquidity scoring
   - Entry price recommendations (BID/ASK/MID)

3. **Scaling Exit Strategy**
   - Automatic partial exits at profit targets
   - Fibonacci ratios (61.8% / 38.2%)
   - Multiple profit tiers (0.1%, 0.2%, 0.5%, 1%, 2%)
   - Trailing stop loss updates

4. **Risk Management**
   - 1% default stop loss (configurable)
   - Trailing stop loss (1% trailing)
   - Daily loss limits
   - Position sizing based on risk

### Advanced Features

1. **Performance Analytics**
   - Win rate tracking
   - Profit factor calculation
   - Scaling strategy success metrics
   - Daily performance statistics
   - Symbol-specific analytics

2. **Backtesting**
   - Historical strategy testing
   - Equity curve visualization
   - Performance statistics
   - Comparison with/without scaling

3. **Strategy Customization**
   - Adjustable Fibonacci ratios
   - Custom profit targets
   - Real-time configuration updates

4. **Real-time Dashboard**
   - Live account metrics
   - Active positions monitoring
   - Trading signals display
   - Risk management status

## Installation

### Prerequisites

- Python 3.8 or higher
- Alpaca API account (paper or live)
- pip package manager

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd pennies
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment

Create a `.env` file in the root directory:

```env
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
TRADING_MODE=paper  # or 'live' for real trading
```

### Step 4: Start the Application

```bash
python web/app.py
```

The application will be available at `http://localhost:5000`

## Configuration

### Settings File

Edit `config/settings.py` to customize:

- **STOP_LOSS_PERCENT**: Default stop loss (0.0075 = 0.75%)
- **PROFIT_TARGET_PERCENT**: Default profit target (0.015 = 1.5%)
- **MAX_DAILY_LOSS_PERCENT**: Daily loss limit (0.02 = 2%)
- **DAILY_BETTING_PERCENTAGE**: Capital allocation (0.15 = 15%)
- **MAX_POSITIONS_PER_DAY**: Maximum positions (10)

### Strategy Configuration

Access `/strategy-config` to customize:

- **Quick Exit Ratio**: Percentage for quick profit (default: 61.8%)
- **Runner Ratio**: Percentage for higher targets (default: 38.2%)
- **Profit Targets**: Custom profit percentages for each tier

## Usage Guide

### Starting the Scanner

1. Navigate to Dashboard (`/`)
2. Click "Start Scanner" button
3. Scanner will begin monitoring watchlist symbols
4. Signals will appear in real-time

### Placing a Trade

1. Go to Trade page (`/trade`)
2. Enter symbol and quantity
3. Optionally click "Optimize" for position sizing
4. Check "Use Scaling Exit Strategy" (recommended)
5. Review scaling plan preview
6. Click "Execute Trade"

### Monitoring Positions

1. Go to Positions page (`/positions`)
2. View active positions with scaling plans
3. Click "View Plan" to see exit strategy details
4. Click "Check Exits" to manually trigger exit checks

### Running a Backtest

1. Go to Backtest page (`/backtest`)
2. Enter symbol, date range, and initial capital
3. Choose whether to use scaling strategy
4. Click "Run Backtest"
5. Review results and equity curve

### Viewing Analytics

1. Go to Analytics page (`/analytics`)
2. View performance summary
3. Check scaling strategy metrics
4. Review daily statistics

## API Reference

### Account Endpoints

- `GET /api/account` - Get account information
- `GET /api/positions` - Get active positions
- `GET /api/risk` - Get risk management status

### Trading Endpoints

- `POST /api/trade` - Execute a trade
  ```json
  {
    "symbol": "AAPL",
    "qty": 10,
    "side": "buy",
    "order_type": "market",
    "use_scaling": true
  }
  ```

### Scanner Endpoints

- `GET /api/scanner/status` - Get scanner status
- `POST /api/scanner/start` - Start scanner
- `POST /api/scanner/stop` - Stop scanner
- `GET /api/scanner/signals` - Get current signals

### Scaling Endpoints

- `POST /api/scaling/calculate` - Calculate scaling plan
- `POST /api/scaling/optimize-size` - Optimize position size
- `GET /api/positions/scaling/<symbol>` - Get scaling status
- `GET /api/positions/scaling/all` - Get all scaling positions
- `POST /api/positions/scaling/check-exits` - Manually check exits

### Analytics Endpoints

- `GET /api/analytics/summary` - Get performance summary
- `GET /api/analytics/symbol/<symbol>` - Get symbol performance

### Backtesting Endpoints

- `POST /api/backtest/run` - Run backtest
  ```json
  {
    "symbol": "AAPL",
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-01-31T23:59:59",
    "initial_capital": 10000,
    "use_scaling": true
  }
  ```

### Strategy Configuration

- `GET /api/strategy/config` - Get current configuration
- `POST /api/strategy/config` - Update configuration

## Strategy Guide

### Signal Generation

The system uses multiple technical indicators:

- **RSI (Relative Strength Index)**: Momentum indicator
- **MSI (Money Flow Index)**: Volume-weighted momentum
- **MACD**: Trend-following indicator
- **Moving Averages**: SMA 20, SMA 50, EMA 12, EMA 26
- **ATR (Average True Range)**: Volatility measure
- **Bollinger Bands**: Volatility bands

### Entry Criteria

A BUY signal is generated when:

1. Multi-timeframe analysis shows bullish alignment
2. RSI is not overbought (< 70)
3. MSI indicates buying pressure
4. Price is above key moving averages
5. Volume is above average
6. Bid/Ask analysis shows bullish order flow

### Exit Strategy

**Quick Exit (61.8%)**:
- Exits at 0.1% profit target
- Locks in quick gains
- Reduces risk exposure

**Runner (38.2%)**:
- Targets 0.5% to 2% profit
- Lets winners run
- Higher risk/reward

**Stop Loss**:
- 1% default stop loss
- Trailing stop updates automatically
- Protects against large losses

## Risk Management

### Position Sizing

Position size is calculated based on:

1. Available capital
2. Risk per trade (default: 1% of capital)
3. Stop loss distance
4. Maximum position size limits

### Daily Limits

- **Daily Betting**: 15% of capital (configurable)
- **Max Daily Loss**: 2% of capital
- **Max Positions**: 10 per day

### Safety Features

- Stop loss on all trades
- Trailing stop loss
- Daily loss limits
- Position size limits
- Risk per trade limits

## Performance Analytics

### Metrics Tracked

- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Total profit / Total loss
- **Average Win**: Average profit per winning trade
- **Average Loss**: Average loss per losing trade
- **Largest Win/Loss**: Best and worst trades
- **Scaling Success Rate**: Success rate of scaling exits

### Viewing Analytics

1. Go to `/analytics` page
2. View summary statistics
3. Check scaling performance
4. Review daily statistics
5. Analyze symbol-specific performance

## Backtesting

### Running Backtests

1. Select symbol and date range
2. Set initial capital
3. Choose scaling strategy option
4. Run backtest
5. Review results:
   - Total return
   - Win rate
   - Profit factor
   - Equity curve

### Interpreting Results

- **Total Return**: Overall profit/loss
- **Win Rate**: Percentage of winning trades
- **Profit Factor**: Should be > 1.0 for profitable strategy
- **Equity Curve**: Shows capital growth over time

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify API keys in `.env` file
   - Check Alpaca account status
   - Ensure keys are for correct mode (paper/live)

2. **No Signals Generated**
   - Check if scanner is running
   - Verify watchlist has symbols
   - Check market hours (signals work best during market hours)

3. **Orders Not Executing**
   - Verify account has buying power
   - Check if daily limits are reached
   - Ensure symbol is tradeable on Alpaca

4. **Scaling Exits Not Working**
   - Verify scaling is enabled on trade
   - Check if position has scaling plan
   - Ensure exit manager is running

### Getting Help

- Check logs in console output
- Review error messages in dashboard
- Verify configuration settings
- Test with paper trading first

## Best Practices

1. **Start with Paper Trading**: Always test strategies in paper mode first
2. **Use Scaling Strategy**: Enable scaling exits for better risk management
3. **Monitor Positions**: Regularly check active positions and scaling plans
4. **Review Analytics**: Analyze performance regularly to improve strategies
5. **Backtest First**: Test strategies on historical data before live trading
6. **Risk Management**: Never risk more than you can afford to lose
7. **Market Hours**: System works best during regular market hours

## License

[Your License Here]

## Support

For issues, questions, or contributions, please contact [Your Contact Info]

