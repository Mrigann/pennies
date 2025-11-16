"""
Trading strategies for penny stocks.
Implements momentum scalping and volume breakout strategies with technical indicators.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from config import settings
from utils.logger import logger

class TradingStrategy:
    """Base class for trading strategies."""
    
    def __init__(self):
        """Initialize strategy with indicator parameters."""
        self.rsi_period = settings.RSI_PERIOD
        self.macd_fast = settings.MACD_FAST
        self.macd_slow = settings.MACD_SLOW
        self.macd_signal = settings.MACD_SIGNAL
        self.atr_period = settings.ATR_PERIOD
        self.lookback_period = settings.LOOKBACK_PERIOD
    
    def calculate_indicators(self, bars: List[Dict]) -> pd.DataFrame:
        """
        Calculate technical indicators from price bars.
        
        Args:
            bars: List of bar dictionaries with open, high, low, close, volume
        
        Returns:
            DataFrame with price data and indicators
        """
        if not bars or len(bars) < self.lookback_period:
            return pd.DataFrame()
        
        df = pd.DataFrame(bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        # Calculate RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        
        # Calculate MACD
        macd_data = self._calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_hist'] = macd_data['hist']
        
        # Calculate Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean() if len(df) >= 50 else None
        
        # Calculate ATR (Average True Range)
        df['atr'] = self._calculate_atr(df, self.atr_period)
        df['atr_percent'] = (df['atr'] / df['close']) * 100
        
        # Calculate Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Calculate price momentum
        df['price_change'] = df['close'].pct_change()
        df['momentum_3'] = df['close'].pct_change(3)
        
        # Calculate highs and lows
        df['high_20'] = df['high'].rolling(window=20).max()
        df['low_20'] = df['low'].rolling(window=20).min()
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(
        self,
        prices: pd.Series
    ) -> Dict[str, pd.Series]:
        """Calculate MACD indicator."""
        ema_fast = prices.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = prices.ewm(span=self.macd_slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.macd_signal, adjust=False).mean()
        hist = macd - signal
        
        return {
            'macd': macd,
            'signal': signal,
            'hist': hist
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def momentum_scalping_signal(
        self,
        bars: List[Dict]
    ) -> Tuple[bool, Dict[str, Any], Optional[float], Optional[float]]:
        """
        Generate entry signal using momentum scalping strategy.
        
        Args:
            bars: List of price bars
        
        Returns:
            Tuple of (has_signal, signal_info, entry_price, stop_loss_price)
        """
        df = self.calculate_indicators(bars)
        
        if df.empty or len(df) < self.lookback_period:
            return False, {}, None, None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # Entry conditions
        conditions = {
            "price_breaks_high": latest['close'] > prev['high_20'],
            "high_volume": latest['volume_ratio'] >= settings.MIN_VOLUME_MULTIPLIER,
            "rsi_ok": settings.RSI_OVERSOLD < latest['rsi'] < settings.RSI_OVERBOUGHT,
            "positive_momentum": latest['momentum_3'] > 0,
            "price_above_sma": latest['close'] > latest['sma_20']
        }
        
        has_signal = all([
            conditions["price_breaks_high"],
            conditions["high_volume"],
            conditions["rsi_ok"],
            conditions["positive_momentum"]
        ])
        
        if has_signal:
            entry_price = latest['close']
            # Stop loss: entry price - (ATR * 1.5) or 0.75% below entry
            stop_loss_pct = settings.STOP_LOSS_PERCENT
            atr_stop = entry_price - (latest['atr'] * 1.5)
            pct_stop = entry_price * (1 - stop_loss_pct)
            stop_loss_price = max(atr_stop, pct_stop)
            
            signal_info = {
                "strategy": "momentum_scalping",
                "entry_price": entry_price,
                "stop_loss": stop_loss_price,
                "rsi": latest['rsi'],
                "volume_ratio": latest['volume_ratio'],
                "momentum": latest['momentum_3'],
                "conditions": conditions
            }
            
            logger.debug(f"Momentum scalping signal: {signal_info}")
            return True, signal_info, entry_price, stop_loss_price
        
        return False, {}, None, None
    
    def volume_breakout_signal(
        self,
        bars: List[Dict]
    ) -> Tuple[bool, Dict[str, Any], Optional[float], Optional[float]]:
        """
        Generate entry signal using volume breakout strategy.
        
        Args:
            bars: List of price bars
        
        Returns:
            Tuple of (has_signal, signal_info, entry_price, stop_loss_price)
        """
        df = self.calculate_indicators(bars)
        
        if df.empty or len(df) < self.lookback_period:
            return False, {}, None, None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # Entry conditions
        conditions = {
            "volume_spike": latest['volume_ratio'] >= 2.5,
            "macd_bullish": latest['macd'] > latest['macd_signal'],
            "macd_cross": prev['macd'] <= prev['macd_signal'] and latest['macd'] > latest['macd_signal'],
            "price_above_sma": latest['close'] > latest['sma_20'],
            "rsi_ok": latest['rsi'] < settings.RSI_OVERBOUGHT
        }
        
        has_signal = all([
            conditions["volume_spike"],
            conditions["macd_bullish"],
            conditions["price_above_sma"]
        ]) and conditions["macd_cross"]
        
        if has_signal:
            entry_price = latest['close']
            # Stop loss: entry price - (ATR * 2) or 0.75% below entry
            stop_loss_pct = settings.STOP_LOSS_PERCENT
            atr_stop = entry_price - (latest['atr'] * 2.0)
            pct_stop = entry_price * (1 - stop_loss_pct)
            stop_loss_price = max(atr_stop, pct_stop)
            
            signal_info = {
                "strategy": "volume_breakout",
                "entry_price": entry_price,
                "stop_loss": stop_loss_price,
                "rsi": latest['rsi'],
                "volume_ratio": latest['volume_ratio'],
                "macd": latest['macd'],
                "macd_signal": latest['macd_signal'],
                "conditions": conditions
            }
            
            logger.debug(f"Volume breakout signal: {signal_info}")
            return True, signal_info, entry_price, stop_loss_price
        
        return False, {}, None, None
    
    def check_exit_conditions(
        self,
        position: Dict[str, Any],
        current_price: float,
        entry_time: Optional[datetime]
    ) -> Tuple[bool, str, Optional[float]]:
        """
        Check if position should be exited.
        
        Args:
            position: Position dictionary with entry_price, stop_loss, profit_target
            current_price: Current market price
            entry_time: When position was entered
        
        Returns:
            Tuple of (should_exit, reason, exit_price)
        """
        entry_price = position.get('entry_price', 0)
        stop_loss = position.get('stop_loss', 0)
        profit_target = position.get('profit_target', 0)
        
        if not entry_price:
            return False, "", None
        
        # Check stop loss
        if stop_loss and current_price <= stop_loss:
            return True, "stop_loss", stop_loss
        
        # Check profit target
        if profit_target and current_price >= profit_target:
            return True, "profit_target", profit_target
        
        # Check time-based exit
        if entry_time:
            hold_time = datetime.now() - entry_time
            max_hold = timedelta(minutes=settings.MAX_POSITION_HOLD_TIME_MINUTES)
            if hold_time >= max_hold:
                return True, "time_limit", current_price
        
        return False, "", None
    
    def calculate_profit_target(self, entry_price: float) -> float:
        """
        Calculate profit target price.
        
        Args:
            entry_price: Entry price
        
        Returns:
            Profit target price
        """
        return entry_price * (1 + settings.PROFIT_TARGET_PERCENT)
    
    def calculate_stop_loss(self, entry_price: float, bars: List[Dict] = None) -> float:
        """
        Calculate stop loss price.
        
        Args:
            entry_price: Entry price
            bars: Optional price bars for ATR-based stop
        
        Returns:
            Stop loss price
        """
        # Default percentage-based stop
        stop_loss = entry_price * (1 - settings.STOP_LOSS_PERCENT)
        
        # If bars provided, use ATR-based stop if more conservative
        if bars:
            df = self.calculate_indicators(bars)
            if not df.empty:
                latest = df.iloc[-1]
                atr_stop = entry_price - (latest['atr'] * 1.5)
                stop_loss = max(stop_loss, atr_stop)
        
        return stop_loss

