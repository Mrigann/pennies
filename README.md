# Penny Stock Auto-Trading System

Automated trading system for penny stocks using Alpaca API. Focuses on marginal gains through momentum scalping and volume breakout strategies with strict risk management.

## Features

- **Automated Trading**: Momentum scalping and volume breakout strategies
- **Trade Approval System**: All trades require manual approval before execution with detailed analysis
- **Daily Analysis**: View daily high/low, trading bands, upside potential, and exit routes for each trade
- **Risk Management**: Daily loss limits, position sizing, and trading controls
- **Stock Scanner**: Finds high-volume, high-volatility stocks for scalping
- **Web Dashboard**: Real-time monitoring and manual trading controls
- **Paper/Live Trading**: Switch between paper and live trading modes
- **Analytics**: Daily P&L charts and performance metrics
- **Testing Suite**: Comprehensive test coverage

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd pennies
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
export ALPACA_API_KEY="PK37L27LF5PPSMP3S3TGJKR5KM"
export ALPACA_SECRET_KEY="GZqitSttHPv76CKcbLTPhT8M3XWAwvpBxxtThrfrevqj"
export TRADING_MODE="paper"  # or "live"
```

Or create a `.env` file:

```
ALPACA_API_KEY=PK37L27LF5PPSMP3S3TGJKR5KM
ALPACA_SECRET_KEY=GZqitSttHPv76CKcbLTPhT8M3XWAwvpBxxtThrfrevqj
TRADING_MODE=paper
```

## Configuration

Edit `config/settings.py` to adjust:

- Starting capital
- Daily betting percentage (10-20%)
- Profit targets and stop losses
- Risk parameters
- Strategy parameters

## Usage

### Running the Trading System

Start the backend trading system:

```bash
python main.py
```

Start the web dashboard:

```bash
python web/app.py
```

Then open your browser to `http://localhost:5000`

### Trade Approval System

The system now requires manual approval before executing trades. Navigate to the **Approvals** page to:

- Review pending trades with detailed analysis
- View daily high/low prices
- See which trading band the stock is in (Upper/Middle/Lower)
- Check upside potential to profit target and daily high
- Review exit routes (profit target, daily high, stop loss)
- Approve or reject trades before execution

Start the trading system from the Approvals page, and it will queue trades for your review instead of executing them automatically.

### Adding Stocks to Watchlist

Edit `config/watchlist.json`:

```json
{
  "symbols": ["AAPL", "TSLA", "NVDA"],
  "last_updated": "2024-01-15"
}
```

## Testing

Run all tests:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=trading --cov=utils --cov-report=html
```

## Project Structure

```
pennies/
├── config/          # Configuration files
├── trading/         # Core trading modules
├── web/             # Web application
├── data/            # Data storage (P&L, trades)
├── utils/           # Utilities
├── tests/           # Test suite
└── main.py         # Main execution script
```

## Risk Management

- Daily loss cannot exceed previous day's profit
- Maximum daily loss limit (configurable)
- Position sizing based on stop-loss distance
- Maximum positions per day limit
- Automatic trading halt when limits reached

## Disclaimer

This software is for educational purposes only. Trading involves risk of loss. Always test thoroughly in paper trading mode before using real money.
