"""
Alpaca API client wrapper with support for paper and live trading modes.
Handles all interactions with Alpaca API including orders, positions, and market data.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestTradeRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from config import settings
from utils.logger import logger

class AlpacaClient:
    """Wrapper for Alpaca API with paper/live mode switching."""
    
    def __init__(self, mode: str = None, api_key: str = None, secret_key: str = None):
        """
        Initialize Alpaca client.
        
        Args:
            mode: 'paper' or 'live' (defaults to settings.TRADING_MODE)
            api_key: API key (defaults to settings.ALPACA_API_KEY)
            secret_key: Secret key (defaults to settings.ALPACA_SECRET_KEY)
        """
        self.mode = mode or settings.TRADING_MODE
        
        # Get keys - use provided keys or fall back to settings
        if api_key and secret_key:
            self.api_key = api_key
            self.secret_key = secret_key
            logger.info("Using provided API keys")
        else:
            # Get from settings
            self.api_key = settings.ALPACA_API_KEY
            self.secret_key = settings.ALPACA_SECRET_KEY
            
            # If still empty, use hardcoded fallback
            if not self.api_key or not self.secret_key:
                self.api_key = "PK37L27LF5PPSMP3S3TGJKR5KM"
                self.secret_key = "GZqitSttHPv76CKcbLTPhT8M3XWAwvpBxxtThrfrevqj"
                logger.info("Using hardcoded fallback API keys")
        
        # Validate API keys
        if not self.api_key or not self.secret_key:
            error_msg = (
                "Alpaca API credentials not found! "
                "Please set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables, "
                "or create a .env file with these values."
            )
            logger.error(error_msg)
            logger.error(f"API Key present: {bool(self.api_key)}, Secret Key present: {bool(self.secret_key)}")
            raise ValueError(error_msg)
        
        # Log authentication details (without exposing full keys)
        logger.info(f"Initializing Alpaca client - API Key: {self.api_key[:10]}..., Mode: {self.mode}")
        
        # Note: TradingClient handles paper/live mode via 'paper' parameter
        
        # Initialize clients
        try:
            # Ensure keys are strings and not empty
            if not isinstance(self.api_key, str) or not isinstance(self.secret_key, str):
                raise ValueError("API keys must be strings")
            
            # Debug: Log key lengths (not the actual keys)
            logger.debug(f"API Key length: {len(self.api_key)}, Secret Key length: {len(self.secret_key)}")
            
            # Make absolutely sure keys are not empty
            if not self.api_key.strip() or not self.secret_key.strip():
                raise ValueError(f"API keys are empty. API Key length: {len(self.api_key)}, Secret length: {len(self.secret_key)}")
            
            # Initialize TradingClient - test authentication immediately
            logger.info(f"Creating TradingClient with paper={self.mode == 'paper'}")
            logger.info(f"API Key (first 10 chars): {self.api_key[:10] if self.api_key else 'EMPTY'}, Length: {len(self.api_key) if self.api_key else 0}")
            logger.info(f"Secret Key (first 10 chars): {self.secret_key[:10] if self.secret_key else 'EMPTY'}, Length: {len(self.secret_key) if self.secret_key else 0}")
            
            # Create client with explicit parameters
            try:
                self.trade_client = TradingClient(
                    api_key=str(self.api_key).strip(),
                    secret_key=str(self.secret_key).strip(),
                    paper=self.mode == "paper"
                )
                logger.info("TradingClient object created")
            except Exception as init_error:
                logger.error(f"Failed to create TradingClient: {init_error}")
                logger.error(f"API Key type: {type(self.api_key)}, Value (first 15): {str(self.api_key)[:15] if self.api_key else 'None'}")
                logger.error(f"Secret Key type: {type(self.secret_key)}, Value (first 15): {str(self.secret_key)[:15] if self.secret_key else 'None'}")
                raise
            
            # Test authentication by getting account
            try:
                logger.info("Testing authentication by calling get_account()...")
                test_account = self.trade_client.get_account()
                logger.info(f"Authentication test successful. Account: {test_account.account_number}")
            except Exception as auth_error:
                logger.error(f"Authentication test failed: {auth_error}")
                logger.error(f"Error type: {type(auth_error)}")
                raise ValueError(f"Failed to authenticate with Alpaca: {auth_error}")
            
            self.data_client = StockHistoricalDataClient(
                api_key=self.api_key.strip(),
                secret_key=self.secret_key.strip()
            )
            logger.info(f"Alpaca client initialized successfully in {self.mode} mode")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca client: {e}")
            raise
    
    def switch_mode(self, mode: str) -> bool:
        """
        Switch between paper and live trading modes.
        
        Args:
            mode: 'paper' or 'live'
        
        Returns:
            True if successful, False otherwise
        """
        if mode not in ["paper", "live"]:
            logger.error(f"Invalid mode: {mode}. Must be 'paper' or 'live'")
            return False
        
        old_mode = self.mode
        self.mode = mode
        
        try:
            self.trade_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=mode == "paper"
            )
            logger.warning(f"Switched from {old_mode} to {mode} mode")
            return True
        except Exception as e:
            logger.error(f"Failed to switch mode: {e}")
            self.mode = old_mode
            return False
    
    def get_account(self) -> Optional[Dict[str, Any]]:
        """
        Get account information.
        
        Returns:
            Account dictionary with balance, buying power, etc.
        """
        try:
            account = self.trade_client.get_account()
            return {
                "account_number": account.account_number,
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "buying_power": float(account.buying_power),
                "equity": float(account.equity),
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "account_blocked": account.account_blocked
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None
    
    def is_market_open(self) -> bool:
        """
        Check if market is currently open.
        
        Returns:
            True if market is open, False otherwise
        """
        try:
            clock = self.trade_client.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all current positions.
        
        Returns:
            List of position dictionaries
        """
        try:
            positions = self.trade_client.get_all_positions()
            return [
                {
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "cost_basis": float(pos.cost_basis),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "side": pos.side
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for a specific symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Position dictionary or None if not found
        """
        try:
            position = self.trade_client.get_open_position(symbol)
            return {
                "symbol": position.symbol,
                "qty": float(position.qty),
                "avg_entry_price": float(position.avg_entry_price),
                "current_price": float(position.current_price),
                "market_value": float(position.market_value),
                "cost_basis": float(position.cost_basis),
                "unrealized_pl": float(position.unrealized_pl),
                "unrealized_plpc": float(position.unrealized_plpc),
                "side": position.side
            }
        except Exception as e:
            # Position not found is not an error
            return None
    
    def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day"
    ) -> Optional[Dict[str, Any]]:
        """
        Place an order.
        
        Args:
            symbol: Stock symbol
            qty: Quantity to trade
            side: 'buy' or 'sell'
            order_type: 'market' or 'limit'
            limit_price: Limit price (required for limit orders)
            stop_price: Stop price (for stop orders)
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
        
        Returns:
            Order dictionary or None if failed
        """
        try:
            side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif_enum = TimeInForce.DAY if time_in_force.lower() == "day" else TimeInForce.GTC
            
            if order_type.lower() == "limit" and limit_price:
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=side_enum,
                    limit_price=limit_price,
                    time_in_force=tif_enum
                )
            else:
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=side_enum,
                    time_in_force=tif_enum
                )
            
            order = self.trade_client.submit_order(order_request)
            
            logger.info(f"Order placed: {side} {qty} {symbol} @ {order_type}")
            
            return {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side,
                "order_type": order.order_type,
                "status": order.status,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0.0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None
            }
        except Exception as e:
            logger.error(f"Error placing order for {symbol}: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.trade_client.cancel_order_by_id(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_orders(
        self,
        status: str = "open",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get orders.
        
        Args:
            status: 'open', 'closed', 'all'
            limit: Maximum number of orders to return
        
        Returns:
            List of order dictionaries
        """
        try:
            request_params = GetOrdersRequest(status=status, limit=limit)
            orders = self.trade_client.get_orders(request_params)
            
            return [
                {
                    "id": order.id,
                    "symbol": order.symbol,
                    "qty": float(order.qty),
                    "side": order.side,
                    "order_type": order.order_type,
                    "status": order.status,
                    "filled_qty": float(order.filled_qty) if order.filled_qty else 0.0,
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                    "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Min",
        limit: int = 100,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical bars for a symbol.
        
        Args:
            symbol: Stock symbol
            timeframe: '1Min', '5Min', '15Min', '1Hour', '1Day'
            limit: Number of bars to retrieve
            start: Start datetime
            end: End datetime
        
        Returns:
            List of bar dictionaries
        """
        try:
            # Map timeframe string to TimeFrame enum
            # Alpaca limits: period number must be <= 59 for minute-based timeframes
            # Some SDK versions may have issues with TimeFrame(15, TimeFrame.Minute)
            # So we'll use a safer approach
            if timeframe == "1Min":
                tf = TimeFrame.Minute
            elif timeframe == "5Min":
                tf = TimeFrame(5, TimeFrame.Minute)  # 5 < 59, should be OK
            elif timeframe == "15Min":
                # Alpaca sometimes rejects TimeFrame(15, Minute) even though 15 < 59
                # Use 1Min bars and aggregate to avoid the error
                bars_1m = self.get_bars(symbol, timeframe="1Min", limit=limit * 15, start=start, end=end)
                if bars_1m and len(bars_1m) >= 15:
                    return self._aggregate_1min_bars(bars_1m, 15)
                else:
                    return []
            elif timeframe == "1Hour":
                tf = TimeFrame.Hour
            elif timeframe == "1Day":
                tf = TimeFrame.Day
            else:
                tf = TimeFrame.Minute  # Default to 1Min
            
            # If no start/end provided, use recent date range (last 5 days for intraday, last 30 days for daily)
            if not start or not end:
                end = datetime.now()
                if timeframe == "1Day":
                    start = end - timedelta(days=30)
                else:
                    start = end - timedelta(days=5)
            
            request_params = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=tf,
                start=start,
                end=end,
                limit=limit
            )
            
            try:
                bars_response = self.data_client.get_stock_bars(request_params)
            except Exception as api_error:
                error_msg = str(api_error)
                logger.error(f"Alpaca API error getting bars for {symbol}: {error_msg}")
                
                # Check for common errors
                if "subscription" in error_msg.lower() or "data plan" in error_msg.lower():
                    logger.warning(f"Data subscription may be required for {symbol}. Trying alternative method...")
                    # Try using daily bars as fallback
                    if timeframe != "1Day":
                        try:
                            daily_bars = self.get_bars(symbol, timeframe="1Day", limit=limit, start=start, end=end)
                            if daily_bars:
                                logger.info(f"Got {len(daily_bars)} daily bars as fallback for {symbol}")
                                return daily_bars
                        except:
                            pass
                
                # Re-raise if it's not a subscription issue
                raise
            
            result = []
            
            # BarSet is a dictionary-like object - access it properly
            try:
                # Try to get bars for the symbol
                symbol_bars = bars_response.get(symbol) if hasattr(bars_response, 'get') else None
                
                # If get() doesn't work, try direct access
                if symbol_bars is None:
                    try:
                        symbol_bars = bars_response[symbol]
                    except (KeyError, TypeError):
                        # Try iterating if it's iterable
                        if hasattr(bars_response, '__iter__'):
                            # BarSet might be iterable directly
                            symbol_bars = list(bars_response) if bars_response else None
                        else:
                            symbol_bars = None
                
                # Process bars
                if symbol_bars:
                    # Handle both list and single bar
                    if not isinstance(symbol_bars, list):
                        symbol_bars = [symbol_bars]
                    
                    for bar in symbol_bars:
                        result.append({
                            "timestamp": bar.timestamp.isoformat() if hasattr(bar.timestamp, 'isoformat') else str(bar.timestamp),
                            "open": float(bar.open),
                            "high": float(bar.high),
                            "low": float(bar.low),
                            "close": float(bar.close),
                            "volume": int(bar.volume)
                        })
                else:
                    # No bars for this symbol - try fallback
                    logger.warning(f"No bars returned for {symbol} with {timeframe} timeframe")
                    # Try alternative: check if symbol is valid by trying daily bars
                    if timeframe != "1Day":
                        try:
                            logger.info(f"Trying daily bars as fallback for {symbol}")
                            daily_bars = self.get_bars(symbol, timeframe="1Day", limit=5, start=start, end=end)
                            if daily_bars and len(daily_bars) > 0:
                                logger.info(f"Got {len(daily_bars)} daily bars for {symbol} - symbol is valid but no {timeframe} data")
                                return daily_bars
                        except Exception as fallback_error:
                            logger.debug(f"Fallback to daily bars also failed: {fallback_error}")
            except Exception as process_error:
                logger.error(f"Error processing bars response for {symbol}: {process_error}")
                logger.debug(f"BarSet type: {type(bars_response)}, Attributes: {dir(bars_response) if hasattr(bars_response, '__dict__') else 'N/A'}")
            
            return result
        except Exception as e:
            error_msg = str(e)
            # Check if it's a timeframe period error
            if "timeframe period number is larger than the allowed maximum" in error_msg:
                logger.warning(f"Timeframe period error for {symbol} with {timeframe}. Falling back to 1Min.")
                # Retry with 1Min and aggregate if needed
                if timeframe != "1Min":
                    try:
                        bars_1m = self.get_bars(symbol, timeframe="1Min", limit=limit * 15)  # Get more 1Min bars
                        if bars_1m:
                            # Aggregate to requested timeframe
                            if timeframe == "15Min":
                                # Aggregate 15 x 1Min = 15Min
                                return self._aggregate_1min_bars(bars_1m, 15)
                            elif timeframe == "5Min":
                                return self._aggregate_1min_bars(bars_1m, 5)
                    except:
                        pass
            logger.error(f"Error getting bars for {symbol}: {e}")
            return []
    
    def _aggregate_1min_bars(self, bars_1m: List[Dict[str, Any]], minutes: int) -> List[Dict[str, Any]]:
        """
        Aggregate 1-minute bars into larger timeframe.
        
        Args:
            bars_1m: List of 1-minute bars
            minutes: Target timeframe in minutes
        
        Returns:
            List of aggregated bars
        """
        if not bars_1m or len(bars_1m) < minutes:
            return []
        
        aggregated = []
        for i in range(0, len(bars_1m), minutes):
            group = bars_1m[i:i+minutes]
            if group:
                aggregated.append({
                    'timestamp': group[0]['timestamp'],
                    'open': group[0]['open'],
                    'high': max(b['high'] for b in group),
                    'low': min(b['low'] for b in group),
                    'close': group[-1]['close'],
                    'volume': sum(b['volume'] for b in group)
                })
        
        return aggregated
    
    def get_latest_bar(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest bar for a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Latest bar dictionary or None
        """
        bars = self.get_bars(symbol, timeframe="1Min", limit=1)
        return bars[0] if bars else None
    
    def get_latest_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest trade for a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Latest trade dictionary or None
        """
        try:
            request = StockLatestTradeRequest(symbol_or_symbols=[symbol])
            trades = self.data_client.get_stock_latest_trade(request)
            
            if symbol in trades and trades[symbol]:
                trade = trades[symbol]
                return {
                    "price": float(trade.price),
                    "size": int(trade.size),
                    "timestamp": trade.timestamp.isoformat() if trade.timestamp else None
                }
            return None
        except Exception as e:
            logger.error(f"Error getting latest trade for {symbol}: {e}")
            return None
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest quote for a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Latest quote dictionary or None
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
            quotes = self.data_client.get_stock_latest_quote(request)
            
            if symbol in quotes and quotes[symbol]:
                quote = quotes[symbol]
                return {
                    "bid_price": float(quote.bid_price) if quote.bid_price else None,
                    "ask_price": float(quote.ask_price) if quote.ask_price else None,
                    "bid_size": int(quote.bid_size) if quote.bid_size else None,
                    "ask_size": int(quote.ask_size) if quote.ask_size else None,
                    "timestamp": quote.timestamp.isoformat() if quote.timestamp else None
                }
            return None
        except Exception as e:
            logger.error(f"Error getting latest quote for {symbol}: {e}")
            return None
    
    def get_stock_quote_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get stock quote information using multiple methods as fallback.
        Tries: latest bar -> latest trade -> latest quote
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary with price information or None
        """
        # Try to get latest bar first (most complete data)
        latest_bar = self.get_latest_bar(symbol)
        if latest_bar:
            return {
                "price": latest_bar.get('close'),
                "high": latest_bar.get('high'),
                "low": latest_bar.get('low'),
                "open": latest_bar.get('open'),
                "volume": latest_bar.get('volume'),
                "timestamp": latest_bar.get('timestamp'),
                "source": "bar"
            }
        
        # Fallback to latest trade
        latest_trade = self.get_latest_trade(symbol)
        if latest_trade:
            price = latest_trade.get('price')
            return {
                "price": price,
                "high": price,
                "low": price,
                "open": price,
                "volume": latest_trade.get('size', 0),
                "timestamp": latest_trade.get('timestamp'),
                "source": "trade"
            }
        
        # Fallback to latest quote
        latest_quote = self.get_latest_quote(symbol)
        if latest_quote:
            bid = latest_quote.get('bid_price')
            ask = latest_quote.get('ask_price')
            mid_price = (bid + ask) / 2 if bid and ask else (bid or ask)
            if mid_price:
                return {
                    "price": mid_price,
                    "high": mid_price,
                    "low": mid_price,
                    "open": mid_price,
                    "volume": 0,
                    "timestamp": latest_quote.get('timestamp'),
                    "source": "quote"
                }
        
        return None

