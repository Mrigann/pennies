# Fibonacci-Style Scaling Exit Strategy

## Overview

The trading system now includes an advanced scaling exit strategy that maximizes profits while managing risk through partial exits at different profit targets.

## Key Features

### 1. **Fibonacci-Style Position Splitting**
- **Quick Exit (61.8%)**: Exits majority of position at quick profit target (0.1%)
- **Runner Position (38.2%)**: Keeps remaining shares for higher profit targets (0.5%, 1%, 2%)

### 2. **Example: 13 Shares**
- **Quick Exit**: 8 shares (61.8%) at 0.1% profit
- **Runner**: 5 shares (38.2%) split between:
  - 2-3 shares at 0.5% profit (moderate target)
  - 2-3 shares at 1%+ profit (aggressive target)

### 3. **Profit Target Tiers**
- **Quick**: 0.1% - Immediate profit taking
- **Conservative**: 0.2% - Quick profit
- **Moderate**: 0.5% - Standard target
- **Aggressive**: 1% - Higher risk/reward
- **Runner**: 2% - Let winners run

### 4. **Risk Management**
- **Stop Loss**: 1% default (configurable)
- **Trailing Stop**: Automatically adjusts as price moves up
- **Position Sizing**: Optimized based on risk per trade
- **Volatility Adjustment**: Targets adjust based on market volatility

## How It Works

### Entry
1. Place buy order (e.g., 13 shares @ $1.00)
2. System automatically creates scaling exit plan:
   - Quick exit: 8 shares @ $1.001 (0.1% profit)
   - Runner: 5 shares for higher targets

### Exit Execution
1. **Quick Exit**: When price hits $1.001, automatically sells 8 shares
2. **Runner Exits**: 
   - 2-3 shares exit at $1.005 (0.5% profit)
   - Remaining 2-3 shares exit at $1.01 (1% profit) or higher

### Automatic Monitoring
- System continuously monitors positions
- Checks exit conditions every scan cycle
- Executes exits automatically when targets are hit
- Updates trailing stops as price moves favorably

## Benefits

1. **Profit Maximization**: Lock in quick profits while letting winners run
2. **Risk Reduction**: Exit majority position quickly, reducing exposure
3. **Flexibility**: Different exit targets for different risk tolerances
4. **Automation**: No manual intervention needed
5. **Adaptive**: Adjusts targets based on volatility

## API Endpoints

### Calculate Scaling Plan
```
POST /api/scaling/calculate
{
  "symbol": "AAPL",
  "entry_price": 1.00,
  "position_size": 13,
  "stop_loss": 0.99,
  "volatility": 2.5  // Optional
}
```

### Optimize Position Size
```
POST /api/scaling/optimize-size
{
  "entry_price": 1.00,
  "stop_loss": 0.99,
  "available_capital": 1000,
  "risk_per_trade": 10  // Optional
}
```

### Get Position Status
```
GET /api/positions/scaling/{symbol}
```

### Check and Execute Exits
```
POST /api/positions/scaling/check-exits
```

## Usage in Trade Page

1. Enter symbol and quantity
2. Check "Use Scaling Exit Strategy" (enabled by default)
3. Preview scaling plan appears automatically
4. Execute trade - scaling plan is created automatically
5. System monitors and executes exits automatically

## Configuration

Default ratios can be adjusted in `trading/scaling_strategy.py`:
- `quick_exit_ratio`: 0.618 (61.8%)
- `runner_ratio`: 0.382 (38.2%)
- Profit targets can be customized per trade

## Best Practices

1. **Minimum Position Size**: Use at least 2 shares for scaling
2. **Risk Management**: Always set appropriate stop loss
3. **Volatility Consideration**: Higher volatility = wider targets
4. **Quick Profits**: Take quick profits on volatile stocks
5. **Let Winners Run**: Keep runners for strong momentum

