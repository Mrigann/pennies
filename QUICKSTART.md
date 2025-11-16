# Quick Start Guide - Trading UI

## Starting the Web Interface

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
   - Create a `.env` file or set environment variables:
   ```
   ALPACA_API_KEY=your_api_key
   ALPACA_SECRET_KEY=your_secret_key
   TRADING_MODE=paper
   ```

3. **Start the web server:**
```bash
python web/app.py
```

4. **Open your browser:**
   - Navigate to: `http://localhost:5000`
   - Click on **"Trade"** in the navigation menu

## Using the Trading Interface

### 1. Search for Stocks
- Enter a stock symbol (e.g., AAPL, TSLA) in the search box
- Click "Search" or press Enter
- View current price, volume, and price change
- Click "Add to Watchlist" to save the symbol

### 2. Execute Trades
- **Select a stock:** Search for it or click from watchlist
- **Fill in trade details:**
  - Symbol (auto-filled when selected)
  - Side: Buy or Sell
  - Quantity: Number of shares
  - Order Type: Market or Limit
  - Limit Price: (if using limit order)
- **Review estimated cost** in the trade summary
- **Click "Execute Trade"** to place the order

### 3. Manage Watchlist
- **Add symbols:** Click "Add Symbol" button or use "Add to Watchlist" from search results
- **Quick trade:** Click "Trade" next to any watchlist item
- **Remove:** Click the trash icon to remove from watchlist

### 4. View Recent Trades
- Recent trades appear at the bottom of the Trade page
- Shows time, symbol, side, quantity, price, and status

## Features

- **Real-time Quotes:** Get current stock prices and changes
- **Trade Execution:** Buy/sell stocks with market or limit orders
- **Watchlist Management:** Track your favorite stocks
- **Risk Management:** See buying power and estimated costs
- **Recent Orders:** View your trading history

## Important Notes

- Always start with **Paper Trading** mode to test
- Check your buying power before placing orders
- Market orders execute immediately at current price
- Limit orders only execute at your specified price or better
- The UI updates automatically every few seconds

## Troubleshooting

- **"Symbol not found":** Make sure the symbol is correct and tradeable on Alpaca
- **"Insufficient buying power":** You don't have enough cash for the trade
- **"Order failed":** Check market hours and your account status

