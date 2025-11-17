"""
Flask web application for trading system dashboard.
"""

import sys
from pathlib import Path
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force reload of dotenv to ensure .env is loaded
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"[Web App] Loaded .env from: {env_path}")

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
from datetime import datetime, timedelta
from config import settings
from utils.logger import logger

# Verify keys are loaded at import time
if not settings.ALPACA_API_KEY or not settings.ALPACA_SECRET_KEY:
    print(f"[Web App] WARNING: API keys not loaded at startup!")
    print(f"[Web App] API Key: {bool(settings.ALPACA_API_KEY)}, Secret: {bool(settings.ALPACA_SECRET_KEY)}")
else:
    print(f"[Web App] API keys loaded successfully at startup")
from trading.alpaca_client import AlpacaClient
from trading.risk_manager import RiskManager
from trading.strategy import TradingStrategy
from trading.stock_scanner import StockScanner
from trading.position_tracker import PositionTracker
from trading.continuous_scanner import ContinuousScanner
from trading.enhanced_strategy import EnhancedStrategy
from main import TradingSystem
from utils.visualizer import (
    generate_daily_pnl_chart,
    generate_cumulative_pnl_chart,
    generate_win_loss_distribution,
    generate_trade_frequency_chart,
    generate_performance_metrics
)
from utils.data_loader import load_watchlist, save_watchlist

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading-system-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global trading system instance
trading_system = None
trading_system_obj = None  # Full TradingSystem object
continuous_scanner = None  # Continuous scanner instance
system_lock = threading.Lock()

def get_trading_system():
    """Get or create trading system instance (legacy dict format for compatibility)."""
    global trading_system
    if trading_system is None:
        with system_lock:
            if trading_system is None:
                # Force reload .env file to ensure keys are loaded
                from dotenv import load_dotenv
                from pathlib import Path
                env_path = Path(__file__).parent.parent / ".env"
                if env_path.exists():
                    load_dotenv(env_path, override=True)
                    logger.info(f"Reloaded .env file from: {env_path}")
                
                # Reload settings to get fresh values
                import importlib
                import config
                importlib.reload(config.settings)
                
                # Get API keys - use hardcoded values as guaranteed fallback
                api_key = config.settings.ALPACA_API_KEY or "PK37L27LF5PPSMP3S3TGJKR5KM"
                secret_key = config.settings.ALPACA_SECRET_KEY or "GZqitSttHPv76CKcbLTPhT8M3XWAwvpBxxtThrfrevqj"
                
                # Strip whitespace
                api_key = api_key.strip() if api_key else "PK37L27LF5PPSMP3S3TGJKR5KM"
                secret_key = secret_key.strip() if secret_key else "GZqitSttHPv76CKcbLTPhT8M3XWAwvpBxxtThrfrevqj"
                
                logger.info(f"Initializing trading system...")
                logger.info(f"API Key: {api_key[:10]}... (length: {len(api_key)})")
                logger.info(f"Secret Key: {secret_key[:10]}... (length: {len(secret_key)})")
                
                try:
                    logger.info("Creating AlpacaClient with explicit keys...")
                    client = AlpacaClient(
                        mode=config.settings.TRADING_MODE or "paper",
                        api_key=api_key,
                        secret_key=secret_key
                    )
                    logger.info("AlpacaClient created successfully")
                    
                    strategy = TradingStrategy()
                    scanner = StockScanner(client)
                    
                    logger.info("Getting account information...")
                    account = client.get_account()
                    if not account:
                        raise ValueError("Failed to get account information - authentication may have failed")
                    
                    capital = float(account.get('portfolio_value', config.settings.STARTING_CAPITAL)) if account else config.settings.STARTING_CAPITAL
                    risk_manager = RiskManager(initial_capital=capital)
                    position_tracker = PositionTracker(client, strategy)
                    
                    # Create continuous scanner
                    continuous_scanner_instance = ContinuousScanner(client)
                    
                    trading_system = {
                        'client': client,
                        'strategy': strategy,
                        'scanner': scanner,
                        'risk_manager': risk_manager,
                        'position_tracker': position_tracker,
                        'continuous_scanner': continuous_scanner_instance
                    }
                    logger.info("Trading system initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize trading system: {e}", exc_info=True)
                    # Reset trading_system to None so we can retry
                    trading_system = None
                    raise
    return trading_system

def get_trading_system_obj():
    """Get or create full TradingSystem object instance."""
    global trading_system_obj
    if trading_system_obj is None:
        with system_lock:
            if trading_system_obj is None:
                try:
                    trading_system_obj = TradingSystem()
                    logger.info("TradingSystem object initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize TradingSystem object: {e}", exc_info=True)
                    trading_system_obj = None
                    raise
    return trading_system_obj

def get_continuous_scanner():
    """Get or create continuous scanner instance."""
    global continuous_scanner
    if continuous_scanner is None:
        with system_lock:
            if continuous_scanner is None:
                try:
                    system = get_trading_system()
                    continuous_scanner = system.get('continuous_scanner')
                    if not continuous_scanner:
                        # Create if not exists
                        continuous_scanner = ContinuousScanner(system['client'])
                        system['continuous_scanner'] = continuous_scanner
                    logger.info("Continuous scanner initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize continuous scanner: {e}", exc_info=True)
                    continuous_scanner = None
                    raise
    return continuous_scanner

@app.route('/')
def index():
    """Main dashboard."""
    return render_template('index.html')

@app.route('/scanner')
def scanner():
    """Scanner page."""
    return render_template('scanner.html')

@app.route('/positions')
def positions():
    """Positions page."""
    return render_template('positions.html')

@app.route('/analytics')
def analytics():
    """Analytics page."""
    return render_template('analytics.html')

@app.route('/trade')
def trade():
    """Trading interface page."""
    return render_template('trade.html')

@app.route('/approvals')
def approvals():
    """Trade approvals page."""
    return render_template('approvals.html')

@app.route('/api/account')
def get_account():
    """Get account information."""
    try:
        system = get_trading_system()
        account = system['client'].get_account()
        if account is None:
            return jsonify({"error": "Failed to get account information. Check API credentials."}), 500
        return jsonify(account)
    except ValueError as e:
        logger.error(f"Authentication error: {e}")
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 401
    except Exception as e:
        logger.error(f"Error getting account: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/positions')
def get_positions():
    """Get current positions."""
    try:
        system = get_trading_system()
        positions = system['position_tracker'].track_positions()
        return jsonify(positions)
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/risk')
def get_risk_summary():
    """Get risk management summary."""
    try:
        system = get_trading_system()
        summary = system['risk_manager'].get_risk_summary()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting risk summary: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanner/run')
def run_scanner():
    """Run stock scanner with detailed results."""
    try:
        system = get_trading_system()
        scanner = system['scanner']
        
        # Get watchlist
        from utils.data_loader import load_watchlist
        watchlist = load_watchlist()
        
        if not watchlist:
            return jsonify({
                "error": "Watchlist is empty. Please add stocks to the watchlist first.",
                "opportunities": [],
                "scanned": [],
                "stats": {
                    "total_scanned": 0,
                    "opportunities_found": 0,
                    "filtered_out": 0,
                    "errors": 0
                }
            })
        
        # Scan all stocks in watchlist with detailed tracking
        all_scanned = []
        opportunities = []
        errors = []
        
        for symbol in watchlist:
            try:
                opp = scanner._analyze_stock(symbol)
                if opp:
                    all_scanned.append({
                        "symbol": symbol,
                        "status": "opportunity",
                        "scalping_score": opp.get('scalping_score', 0),
                        "current_price": opp.get('current_price', 0),
                        "volume_ratio": opp.get('volume_ratio', 0),
                        "volatility_score": opp.get('volatility_score', 0)
                    })
                    opportunities.append(opp)
                else:
                    all_scanned.append({
                        "symbol": symbol,
                        "status": "filtered",
                        "reason": "Did not meet criteria"
                    })
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error scanning {symbol}: {error_msg}")
                errors.append({"symbol": symbol, "error": error_msg})
                all_scanned.append({
                    "symbol": symbol,
                    "status": "error",
                    "error": error_msg
                })
        
        # Sort opportunities by scalping score
        opportunities.sort(key=lambda x: x.get('scalping_score', 0), reverse=True)
        opportunities = opportunities[:20]  # Limit to top 20
        
        stats = {
            "total_scanned": len(watchlist),
            "opportunities_found": len(opportunities),
            "filtered_out": len([s for s in all_scanned if s.get('status') == 'filtered']),
            "errors": len(errors),
            "watchlist_size": len(watchlist)
        }
        
        return jsonify({
            "opportunities": opportunities,
            "scanned": all_scanned,
            "stats": stats,
            "errors": errors
        })
    except Exception as e:
        logger.error(f"Error running scanner: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "opportunities": [],
            "scanned": [],
            "stats": {
                "total_scanned": 0,
                "opportunities_found": 0,
                "filtered_out": 0,
                "errors": 1
            }
        }), 500

@app.route('/api/trade', methods=['POST'])
def execute_trade():
    """Execute a manual trade."""
    try:
        data = request.json
        symbol = data.get('symbol')
        qty = float(data.get('qty', 0))
        side = data.get('side', 'buy')
        order_type = data.get('order_type', 'market')
        limit_price = data.get('limit_price')
        
        if not symbol or qty <= 0:
            return jsonify({"error": "Invalid parameters"}), 400
        
        system = get_trading_system()
        order = system['client'].place_order(
            symbol=symbol,
            qty=qty,
            side=side,
            order_type=order_type,
            limit_price=limit_price
        )
        
        return jsonify(order or {"error": "Order failed"})
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mode/current')
def get_current_mode():
    """Get current trading mode."""
    try:
        return jsonify({"mode": settings.TRADING_MODE})
    except Exception as e:
        logger.error(f"Error getting mode: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/auth')
def debug_auth():
    """Debug endpoint to check authentication status."""
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        env_path = Path(__file__).parent.parent / ".env"
        
        result = {
            "env_file_exists": env_path.exists(),
            "env_file_path": str(env_path),
            "api_key_loaded": bool(settings.ALPACA_API_KEY),
            "secret_key_loaded": bool(settings.ALPACA_SECRET_KEY),
            "api_key_length": len(settings.ALPACA_API_KEY) if settings.ALPACA_API_KEY else 0,
            "secret_key_length": len(settings.ALPACA_SECRET_KEY) if settings.ALPACA_SECRET_KEY else 0,
            "api_key_preview": settings.ALPACA_API_KEY[:10] + "..." if settings.ALPACA_API_KEY else "None",
            "trading_mode": settings.TRADING_MODE
        }
        
        # Try to create a client
        try:
            from trading.alpaca_client import AlpacaClient
            test_client = AlpacaClient()
            account = test_client.get_account()
            result["auth_test"] = "SUCCESS"
            result["account_number"] = account.get('account_number') if account else None
        except Exception as auth_error:
            result["auth_test"] = "FAILED"
            result["auth_error"] = str(auth_error)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mode/switch', methods=['POST'])
def switch_mode():
    """Switch between paper and live trading."""
    try:
        data = request.json
        mode = data.get('mode')
        
        if mode not in ['paper', 'live']:
            return jsonify({"error": "Invalid mode"}), 400
        
        system = get_trading_system()
        success = system['client'].switch_mode(mode)
        
        if success:
            return jsonify({"mode": mode, "status": "switched"})
        else:
            return jsonify({"error": "Failed to switch mode"}), 500
    except Exception as e:
        logger.error(f"Error switching mode: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/charts/daily-pnl')
def chart_daily_pnl():
    """Get daily P&L chart data."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        data = generate_daily_pnl_chart(start_date, end_date)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/charts/cumulative-pnl')
def chart_cumulative_pnl():
    """Get cumulative P&L chart data."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        data = generate_cumulative_pnl_chart(start_date, end_date)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/charts/win-loss')
def chart_win_loss():
    """Get win/loss distribution chart data."""
    try:
        data = generate_win_loss_distribution()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/charts/trade-frequency')
def chart_trade_frequency():
    """Get trade frequency chart data."""
    try:
        data = generate_trade_frequency_chart()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/metrics')
def get_metrics():
    """Get performance metrics."""
    try:
        metrics = generate_performance_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stock/quote/<symbol>')
def get_stock_quote(symbol):
    """Get stock quote information."""
    try:
        # Check if API keys are loaded
        if not settings.ALPACA_API_KEY or not settings.ALPACA_SECRET_KEY:
            logger.error("API keys not loaded when trying to get stock quote")
            return jsonify({"error": "API credentials not configured. Please check your .env file."}), 500
        
        system = get_trading_system()
        symbol_upper = symbol.upper()
        
        # Try to get quote info using multiple fallback methods
        quote_info = system['client'].get_stock_quote_info(symbol_upper)
        
        if not quote_info:
            # Try getting daily bars as last resort
            daily_bars = system['client'].get_bars(symbol_upper, timeframe="1Day", limit=1)
            if daily_bars and len(daily_bars) > 0:
                bar = daily_bars[0]
                quote_info = {
                    "price": bar.get('close'),
                    "high": bar.get('high'),
                    "low": bar.get('low'),
                    "open": bar.get('open'),
                    "volume": bar.get('volume', 0),
                    "source": "daily_bar"
                }
            else:
                logger.warning(f"No data available for symbol {symbol_upper}")
                return jsonify({
                    "error": f"Symbol '{symbol_upper}' not found or no data available. "
                            "The symbol may not be tradeable on Alpaca, or the market may be closed."
                }), 404
        
        current_price = quote_info.get('price')
        
        # Get previous close for change calculation
        # Try to get yesterday's close or previous bar
        prev_close = current_price
        try:
            # Try to get previous day's bar
            daily_bars = system['client'].get_bars(symbol_upper, timeframe="1Day", limit=2)
            if daily_bars and len(daily_bars) >= 2:
                prev_close = daily_bars[0].get('close', current_price)
            elif daily_bars and len(daily_bars) == 1:
                # Use open as previous if only one bar
                prev_close = daily_bars[0].get('open', current_price)
        except Exception as e:
            logger.debug(f"Could not get previous close for {symbol_upper}: {e}")
            # Use current price as fallback
            prev_close = current_price
        
        change = current_price - prev_close
        change_percent = (change / prev_close * 100) if prev_close > 0 else 0
        
        quote = {
            "symbol": symbol_upper,
            "price": current_price,
            "change": change,
            "change_percent": change_percent,
            "volume": quote_info.get('volume', 0),
            "high": quote_info.get('high', current_price),
            "low": quote_info.get('low', current_price),
            "open": quote_info.get('open', current_price),
            "source": quote_info.get('source', 'unknown')
        }
        
        return jsonify(quote)
    except ValueError as e:
        logger.error(f"Authentication error getting stock quote: {e}")
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 401
    except Exception as e:
        logger.error(f"Error getting stock quote for {symbol}: {e}", exc_info=True)
        return jsonify({
            "error": f"Error retrieving stock data: {str(e)}. "
                    "Please check if the symbol is valid and tradeable on Alpaca."
        }), 500

@app.route('/api/watchlist')
def get_watchlist():
    """Get watchlist."""
    try:
        symbols = load_watchlist()
        return jsonify({"symbols": symbols})
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/watchlist/add', methods=['POST'])
def add_to_watchlist():
    """Add symbol to watchlist."""
    try:
        data = request.json
        symbol = data.get('symbol', '').upper().strip()
        
        if not symbol:
            return jsonify({"error": "Symbol required"}), 400
        
        symbols = load_watchlist()
        if symbol not in symbols:
            symbols.append(symbol)
            save_watchlist(symbols)
        
        return jsonify({"symbols": symbols, "message": f"{symbol} added to watchlist"})
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/watchlist/remove', methods=['POST'])
def remove_from_watchlist():
    """Remove symbol from watchlist."""
    try:
        data = request.json
        symbol = data.get('symbol', '').upper().strip()
        
        if not symbol:
            return jsonify({"error": "Symbol required"}), 400
        
        symbols = load_watchlist()
        if symbol in symbols:
            symbols.remove(symbol)
            save_watchlist(symbols)
        
        return jsonify({"symbols": symbols, "message": f"{symbol} removed from watchlist"})
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/recent')
def get_recent_orders():
    """Get recent orders with filtering and sorting."""
    try:
        system = get_trading_system()
        
        # Get filter parameters
        status_filter = request.args.get('status', 'all')  # all, open, filled, cancelled, etc.
        limit_filter = request.args.get('limit', None)  # number of orders to return
        time_filter = request.args.get('time', 'all')  # all, today, 1hour, 24hours
        sort_by = request.args.get('sort', 'time')  # time, symbol, status, price
        sort_order = request.args.get('order', 'desc')  # asc, desc
        
        # Get all orders
        orders = system['client'].get_orders(status='all', limit=500)  # Get more to filter
        
        # Filter by status
        if status_filter != 'all':
            orders = [o for o in orders if o.get('status', '').lower() == status_filter.lower()]
        
        # Filter by time
        if time_filter != 'all':
            now = datetime.now()
            cutoff_time = None
            
            if time_filter == 'today':
                cutoff_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_filter == '1hour':
                cutoff_time = now - timedelta(hours=1)
            elif time_filter == '24hours':
                cutoff_time = now - timedelta(hours=24)
            elif time_filter == '1week':
                cutoff_time = now - timedelta(days=7)
            
            if cutoff_time:
                filtered_orders = []
                for order in orders:
                    submitted_at = order.get('submitted_at')
                    if submitted_at:
                        try:
                            order_time = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
                            if order_time.replace(tzinfo=None) >= cutoff_time:
                                filtered_orders.append(order)
                        except:
                            pass
                orders = filtered_orders
        
        # Sort orders
        if sort_by == 'time':
            orders.sort(key=lambda x: x.get('submitted_at', ''), reverse=(sort_order == 'desc'))
        elif sort_by == 'symbol':
            orders.sort(key=lambda x: x.get('symbol', '').upper(), reverse=(sort_order == 'desc'))
        elif sort_by == 'status':
            orders.sort(key=lambda x: x.get('status', ''), reverse=(sort_order == 'desc'))
        elif sort_by == 'price':
            orders.sort(key=lambda x: float(x.get('filled_avg_price', 0) or 0), reverse=(sort_order == 'desc'))
        elif sort_by == 'qty':
            orders.sort(key=lambda x: float(x.get('qty', 0) or 0), reverse=(sort_order == 'desc'))
        
        # Apply limit
        if limit_filter:
            try:
                limit = int(limit_filter)
                orders = orders[:limit]
            except:
                pass
        
        return jsonify({
            'orders': orders,
            'count': len(orders),
            'filters': {
                'status': status_filter,
                'time': time_filter,
                'limit': limit_filter,
                'sort': sort_by,
                'order': sort_order
            }
        })
    except Exception as e:
        logger.error(f"Error getting recent orders: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/trades/pending')
def get_pending_trades():
    """Get pending trades awaiting approval."""
    try:
        system_obj = get_trading_system_obj()
        pending_trades = system_obj.get_pending_trades()
        return jsonify(pending_trades)
    except Exception as e:
        logger.error(f"Error getting pending trades: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/trades/approve', methods=['POST'])
def approve_trade():
    """Approve and execute a pending trade."""
    try:
        data = request.json
        trade_id = data.get('trade_id')
        
        if not trade_id:
            return jsonify({"error": "trade_id required"}), 400
        
        system_obj = get_trading_system_obj()
        result = system_obj.approve_trade(trade_id)
        
        if result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error approving trade: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/trades/reject', methods=['POST'])
def reject_trade():
    """Reject a pending trade."""
    try:
        data = request.json
        trade_id = data.get('trade_id')
        
        if not trade_id:
            return jsonify({"error": "trade_id required"}), 400
        
        system_obj = get_trading_system_obj()
        result = system_obj.reject_trade(trade_id)
        
        if result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error rejecting trade: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/trades/analysis/<symbol>')
def get_trade_analysis(symbol):
    """Get detailed trade analysis for a symbol."""
    try:
        system_obj = get_trading_system_obj()
        
        # Get recent bars for analysis
        bars = system_obj.client.get_bars(
            symbol.upper(),
            timeframe="1Min",
            limit=settings.LOOKBACK_PERIOD + 10
        )
        
        if not bars or len(bars) < 2:
            return jsonify({"error": "Insufficient data for analysis"}), 404
        
        # Get analysis
        analysis = system_obj._get_daily_analysis(symbol.upper(), bars)
        
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error getting trade analysis: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/status')
def get_system_status():
    """Get trading system status."""
    try:
        system_obj = get_trading_system_obj()
        return jsonify({
            'running': system_obj.running,
            'pending_trades_count': len(system_obj.get_pending_trades())
        })
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/start', methods=['POST'])
def start_system():
    """Start the trading system."""
    try:
        system_obj = get_trading_system_obj()
        system_obj.start()
        return jsonify({'success': True, 'message': 'Trading system started'})
    except Exception as e:
        logger.error(f"Error starting system: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/stop', methods=['POST'])
def stop_system():
    """Stop the trading system."""
    try:
        system_obj = get_trading_system_obj()
        system_obj.stop()
        return jsonify({'success': True, 'message': 'Trading system stopped'})
    except Exception as e:
        logger.error(f"Error stopping system: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanner/signals')
def get_scanner_signals():
    """Get latest signals from continuous scanner."""
    try:
        scanner = get_continuous_scanner()
        signals = scanner.get_latest_signals()
        return jsonify({
            'signals': signals,
            'count': len(signals),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting scanner signals: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanner/signal/<symbol>')
def get_symbol_signal(symbol):
    """Get latest signal for a specific symbol."""
    try:
        scanner = get_continuous_scanner()
        signal = scanner.get_symbol_signal(symbol.upper())
        if signal:
            return jsonify(signal)
        else:
            # Scan symbol now if not in cache
            signal = scanner.scan_symbol_now(symbol.upper())
            if signal:
                return jsonify(signal)
            return jsonify({"error": "No signal available for symbol"}), 404
    except Exception as e:
        logger.error(f"Error getting signal for {symbol}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanner/start', methods=['POST'])
def start_scanner():
    """Start continuous scanner."""
    try:
        scanner = get_continuous_scanner()
        scanner.start()
        return jsonify({'success': True, 'message': 'Continuous scanner started'})
    except Exception as e:
        logger.error(f"Error starting scanner: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanner/stop', methods=['POST'])
def stop_scanner():
    """Stop continuous scanner."""
    try:
        scanner = get_continuous_scanner()
        scanner.stop()
        return jsonify({'success': True, 'message': 'Continuous scanner stopped'})
    except Exception as e:
        logger.error(f"Error stopping scanner: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanner/status')
def get_scanner_status():
    """Get continuous scanner status."""
    try:
        scanner = get_continuous_scanner()
        return jsonify({
            'running': scanner.running,
            'signals_count': len(scanner.get_latest_signals()),
            'scan_interval': scanner.scan_interval
        })
    except Exception as e:
        logger.error(f"Error getting scanner status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanner/scan/<symbol>', methods=['POST'])
def scan_symbol_now(symbol):
    """Scan a symbol immediately."""
    try:
        scanner = get_continuous_scanner()
        signal = scanner.scan_symbol_now(symbol.upper())
        if signal:
            return jsonify(signal)
        return jsonify({"error": "Failed to generate signal"}), 500
    except Exception as e:
        logger.error(f"Error scanning {symbol}: {e}")
        return jsonify({"error": str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    logger.info("Client connected via WebSocket")
    emit('status', {'message': 'Connected to trading system'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    logger.info("Client disconnected")

if __name__ == '__main__':
    logger.info(f"Starting web server on {settings.WEB_HOST}:{settings.WEB_PORT}")
    socketio.run(
        app,
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        debug=settings.WEB_DEBUG
    )

