"""
Enhanced trading strategy with multi-timeframe analysis, MSI, and probability calculations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from config import settings
from utils.logger import logger

class EnhancedStrategy:
    """Enhanced strategy with multi-timeframe analysis and probability calculations."""
    
    def __init__(self):
        """Initialize enhanced strategy."""
        self.rsi_period = settings.RSI_PERIOD
        self.macd_fast = settings.MACD_FAST
        self.macd_slow = settings.MACD_SLOW
        self.macd_signal = settings.MACD_SIGNAL
        self.atr_period = settings.ATR_PERIOD
        self.lookback_period = settings.LOOKBACK_PERIOD
        self.msi_period = 14  # Money Flow Index period
    
    def calculate_msi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Money Flow Index (MSI).
        
        Args:
            df: DataFrame with high, low, close, volume
            period: Period for MSI calculation
        
        Returns:
            MSI series (0-100)
        """
        if len(df) < period:
            return pd.Series([np.nan] * len(df), index=df.index)
        
        # Typical price
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        # Money flow
        money_flow = typical_price * df['volume']
        
        # Positive and negative money flow
        price_change = typical_price.diff()
        positive_flow = money_flow.where(price_change > 0, 0)
        negative_flow = money_flow.where(price_change < 0, 0)
        
        # Rolling sums
        positive_flow_sum = positive_flow.rolling(window=period).sum()
        negative_flow_sum = negative_flow.rolling(window=period).sum()
        
        # Money flow ratio
        money_flow_ratio = positive_flow_sum / negative_flow_sum
        
        # MSI (0-100 scale)
        msi = 100 - (100 / (1 + money_flow_ratio))
        
        return msi
    
    def calculate_indicators(self, bars: List[Dict], timeframe: str = "1Min") -> pd.DataFrame:
        """
        Calculate technical indicators from price bars.
        
        Args:
            bars: List of bar dictionaries
            timeframe: Timeframe label for reference
        
        Returns:
            DataFrame with indicators
        """
        if not bars or len(bars) < self.lookback_period:
            return pd.DataFrame()
        
        df = pd.DataFrame(bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        # Calculate RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        
        # Calculate MSI (Money Flow Index)
        df['msi'] = self.calculate_msi(df, self.msi_period)
        
        # Calculate MACD
        macd_data = self._calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_hist'] = macd_data['hist']
        
        # Calculate Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean() if len(df) >= 50 else None
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # Calculate ATR
        df['atr'] = self._calculate_atr(df, self.atr_period)
        df['atr_percent'] = (df['atr'] / df['close']) * 100
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price momentum
        df['price_change'] = df['close'].pct_change()
        df['momentum_3'] = df['close'].pct_change(3)
        df['momentum_5'] = df['close'].pct_change(5)
        
        # Highs and lows
        df['high_20'] = df['high'].rolling(window=20).max()
        df['low_20'] = df['low'].rolling(window=20).min()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
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
    
    def analyze_multi_timeframe(
        self,
        bars_15m: List[Dict],
        bars_30m: List[Dict],
        bars_1h: List[Dict],
        bars_2h: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze symbol across multiple timeframes.
        
        Args:
            bars_15m: 15-minute bars
            bars_30m: 30-minute bars
            bars_1h: 1-hour bars
            bars_2h: 2-hour bars
        
        Returns:
            Dictionary with multi-timeframe analysis
        """
        analysis = {
            'timeframes': {},
            'overall_signal': 'NEUTRAL',
            'signal_strength': 0.0,
            'entry_confidence': 0.0
        }
        
        timeframe_data = {
            '15m': bars_15m,
            '30m': bars_30m,
            '1h': bars_1h,
            '2h': bars_2h
        }
        
        signals = []
        strengths = []
        
        for tf_name, bars in timeframe_data.items():
            if not bars or len(bars) < 10:
                continue
            
            df = self.calculate_indicators(bars, tf_name)
            if df.empty:
                continue
            
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # Calculate signal for this timeframe
            signal_data = self._calculate_timeframe_signal(df, latest, prev, tf_name)
            analysis['timeframes'][tf_name] = signal_data
            signals.append(signal_data['signal'])
            strengths.append(signal_data['strength'])
        
        # Aggregate signals
        if signals:
            buy_count = signals.count('BUY')
            sell_count = signals.count('SELL')
            avg_strength = np.mean(strengths) if strengths else 0.0
            
            if buy_count > sell_count:
                analysis['overall_signal'] = 'BUY'
                analysis['signal_strength'] = avg_strength
                analysis['entry_confidence'] = (buy_count / len(signals)) * avg_strength
            elif sell_count > buy_count:
                analysis['overall_signal'] = 'SELL'
                analysis['signal_strength'] = avg_strength
                analysis['entry_confidence'] = (sell_count / len(signals)) * avg_strength
        
        return analysis
    
    def _calculate_timeframe_signal(
        self,
        df: pd.DataFrame,
        latest: pd.Series,
        prev: pd.Series,
        timeframe: str
    ) -> Dict[str, Any]:
        """Calculate signal for a specific timeframe."""
        signal_score = 0.0
        conditions = {}
        
        # RSI conditions
        rsi = latest.get('rsi', 50)
        if rsi < 30:
            signal_score += 0.2
            conditions['rsi_oversold'] = True
        elif rsi > 70:
            signal_score -= 0.2
            conditions['rsi_overbought'] = True
        elif 40 < rsi < 60:
            signal_score += 0.1
            conditions['rsi_neutral'] = True
        
        # MSI conditions
        msi = latest.get('msi', 50)
        if msi < 20:
            signal_score += 0.15
            conditions['msi_oversold'] = True
        elif msi > 80:
            signal_score -= 0.15
            conditions['msi_overbought'] = True
        
        # MACD conditions
        macd = latest.get('macd', 0)
        macd_signal = latest.get('macd_signal', 0)
        macd_hist = latest.get('macd_hist', 0)
        
        if macd > macd_signal and macd_hist > 0:
            signal_score += 0.2
            conditions['macd_bullish'] = True
        elif macd < macd_signal and macd_hist < 0:
            signal_score -= 0.2
            conditions['macd_bearish'] = True
        
        # Moving average conditions
        sma_20 = latest.get('sma_20', 0)
        close = latest.get('close', 0)
        
        if close > sma_20:
            signal_score += 0.15
            conditions['price_above_sma20'] = True
        else:
            signal_score -= 0.15
            conditions['price_below_sma20'] = True
        
        # Volume conditions
        volume_ratio = latest.get('volume_ratio', 1.0)
        if volume_ratio > 2.0:
            signal_score += 0.15
            conditions['high_volume'] = True
        
        # Momentum
        momentum = latest.get('momentum_3', 0)
        if momentum > 0:
            signal_score += 0.1
            conditions['positive_momentum'] = True
        
        # Determine signal
        if signal_score > 0.3:
            signal = 'BUY'
        elif signal_score < -0.3:
            signal = 'SELL'
        else:
            signal = 'NEUTRAL'
        
        return {
            'signal': signal,
            'strength': abs(signal_score),
            'score': signal_score,
            'conditions': conditions,
            'rsi': rsi,
            'msi': msi,
            'macd': macd,
            'macd_signal': macd_signal,
            'sma_20': sma_20,
            'current_price': close,
            'volume_ratio': volume_ratio
        }
    
    def calculate_profit_probabilities(
        self,
        current_price: float,
        bars: List[Dict],
        profit_targets: List[float] = [0.001, 0.002, 0.005, 0.01, 0.02]
    ) -> Dict[str, float]:
        """
        Calculate probability of reaching different profit targets.
        
        Args:
            current_price: Current stock price
            bars: Historical price bars
            profit_targets: List of profit percentages (0.001 = 0.1%, 0.002 = 0.2%, etc.)
        
        Returns:
            Dictionary mapping profit targets to probabilities
        """
        if not bars or len(bars) < 20:
            return {f"{p*100:.1f}%": 0.0 for p in profit_targets}
        
        df = pd.DataFrame(bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        # Calculate historical price movements
        df['price_change_pct'] = df['close'].pct_change()
        
        # Calculate volatility (standard deviation of returns)
        volatility = df['price_change_pct'].std()
        
        # Calculate average momentum
        momentum = df['close'].pct_change(5).mean()
        
        # Get recent indicators
        df_indicators = self.calculate_indicators(bars)
        if not df_indicators.empty:
            latest = df_indicators.iloc[-1]
            rsi = latest.get('rsi', 50)
            msi = latest.get('msi', 50)
            macd_hist = latest.get('macd_hist', 0)
        else:
            rsi = 50
            msi = 50
            macd_hist = 0
        
        # Calculate probabilities based on historical patterns and indicators
        probabilities = {}
        
        for target_pct in profit_targets:
            target_price = current_price * (1 + target_pct)
            
            # Base probability from historical volatility
            # Higher volatility = higher chance of reaching target (but also higher risk)
            vol_factor = min(volatility * 100, 5.0) / 5.0  # Normalize to 0-1
            
            # Momentum factor
            momentum_factor = max(0, min(1, (momentum * 100 + 2) / 4))  # Normalize to 0-1
            
            # Indicator factors
            rsi_factor = 0.5
            if 30 < rsi < 70:
                rsi_factor = 0.7
            elif rsi < 30:
                rsi_factor = 0.8  # Oversold, potential bounce
            
            msi_factor = 0.5
            if 20 < msi < 80:
                msi_factor = 0.7
            
            macd_factor = 0.5
            if macd_hist > 0:
                macd_factor = 0.7
            
            # Combine factors
            base_prob = vol_factor * 0.3 + momentum_factor * 0.3 + rsi_factor * 0.2 + msi_factor * 0.1 + macd_factor * 0.1
            
            # Adjust for target size (smaller targets = higher probability)
            target_factor = 1.0 - (target_pct * 10)  # Smaller targets get higher probability
            target_factor = max(0.1, min(1.0, target_factor))
            
            # Final probability
            prob = base_prob * target_factor * 100
            prob = max(0, min(100, prob))  # Clamp to 0-100
            
            probabilities[f"{target_pct*100:.1f}%"] = round(prob, 1)
        
        return probabilities
    
    def calculate_daily_price_stats(self, bars: List[Dict]) -> Dict[str, float]:
        """
        Calculate daily high, low, and average price from today's bars.
        
        Args:
            bars: List of price bars (preferably 1-minute bars for accuracy)
        
        Returns:
            Dictionary with daily_high, daily_low, daily_average, daily_open
        """
        if not bars or len(bars) == 0:
            return {
                'daily_high': 0.0,
                'daily_low': 0.0,
                'daily_average': 0.0,
                'daily_open': 0.0,
                'daily_range': 0.0,
                'current_vs_high_pct': 0.0,
                'current_vs_low_pct': 0.0,
                'current_vs_avg_pct': 0.0
            }
        
        df = pd.DataFrame(bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        # Get today's date
        today = datetime.now().date()
        
        # Filter bars for today only
        today_bars = df[df.index.date == today] if len(df) > 0 else df
        
        # If no bars for today, use all available bars (might be intraday data)
        if len(today_bars) == 0:
            today_bars = df
        
        if len(today_bars) == 0:
            return {
                'daily_high': 0.0,
                'daily_low': 0.0,
                'daily_average': 0.0,
                'daily_open': 0.0,
                'daily_range': 0.0,
                'current_vs_high_pct': 0.0,
                'current_vs_low_pct': 0.0,
                'current_vs_avg_pct': 0.0
            }
        
        # Calculate daily stats
        daily_high = float(today_bars['high'].max())
        daily_low = float(today_bars['low'].min())
        daily_open = float(today_bars['open'].iloc[0])
        daily_close = float(today_bars['close'].iloc[-1])
        
        # Calculate average price (volume-weighted average or simple average of close prices)
        # Using simple average of close prices for intraday
        daily_average = float(today_bars['close'].mean())
        
        # Calculate range
        daily_range = daily_high - daily_low
        
        # Calculate current position relative to daily range
        if daily_range > 0:
            current_vs_high_pct = ((daily_high - daily_close) / daily_range) * 100
            current_vs_low_pct = ((daily_close - daily_low) / daily_range) * 100
        else:
            current_vs_high_pct = 0.0
            current_vs_low_pct = 0.0
        
        # Current vs average
        if daily_average > 0:
            current_vs_avg_pct = ((daily_close - daily_average) / daily_average) * 100
        else:
            current_vs_avg_pct = 0.0
        
        return {
            'daily_high': daily_high,
            'daily_low': daily_low,
            'daily_average': daily_average,
            'daily_open': daily_open,
            'daily_close': daily_close,
            'daily_range': daily_range,
            'current_vs_high_pct': current_vs_high_pct,
            'current_vs_low_pct': current_vs_low_pct,
            'current_vs_avg_pct': current_vs_avg_pct
        }
    
    def analyze_bid_ask(self, quote_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Analyze bid/ask data for smart entry/exit decisions.
        
        Args:
            quote_data: Dictionary with bid_price, ask_price, bid_size, ask_size
            current_price: Current market price
        
        Returns:
            Dictionary with bid/ask analysis
        """
        if not quote_data:
            return {
                'bid_price': 0.0,
                'ask_price': 0.0,
                'bid_size': 0,
                'ask_size': 0,
                'spread': 0.0,
                'spread_pct': 0.0,
                'mid_price': current_price,
                'volume_imbalance': 0.0,
                'imbalance_ratio': 0.0,
                'order_flow': 'NEUTRAL',
                'liquidity_score': 0.0
            }
        
        bid_price = quote_data.get('bid_price', 0.0)
        ask_price = quote_data.get('ask_price', 0.0)
        bid_size = quote_data.get('bid_size', 0)
        ask_size = quote_data.get('ask_size', 0)
        
        if not bid_price or not ask_price:
            return {
                'bid_price': bid_price or current_price,
                'ask_price': ask_price or current_price,
                'bid_size': bid_size,
                'ask_size': ask_size,
                'spread': 0.0,
                'spread_pct': 0.0,
                'mid_price': current_price,
                'volume_imbalance': 0.0,
                'imbalance_ratio': 0.0,
                'order_flow': 'NEUTRAL',
                'liquidity_score': 0.0
            }
        
        # Calculate spread
        spread = ask_price - bid_price
        mid_price = (bid_price + ask_price) / 2
        spread_pct = (spread / mid_price) * 100 if mid_price > 0 else 0.0
        
        # Calculate volume imbalance
        total_size = bid_size + ask_size
        if total_size > 0:
            volume_imbalance = ask_size - bid_size
            imbalance_ratio = volume_imbalance / total_size
        else:
            volume_imbalance = 0.0
            imbalance_ratio = 0.0
        
        # Determine order flow direction
        if imbalance_ratio > 0.2:
            order_flow = 'BULLISH'  # More ask volume (buyers willing to pay ask)
        elif imbalance_ratio < -0.2:
            order_flow = 'BEARISH'  # More bid volume (sellers willing to take bid)
        else:
            order_flow = 'NEUTRAL'
        
        # Calculate liquidity score (higher is better)
        # Consider both spread tightness and volume
        spread_score = max(0, 1 - (spread_pct / 1.0))  # Tight spread = higher score
        volume_score = min(1.0, total_size / 10000)  # More volume = higher score
        liquidity_score = (spread_score * 0.6 + volume_score * 0.4) * 100
        
        return {
            'bid_price': bid_price,
            'ask_price': ask_price,
            'bid_size': bid_size,
            'ask_size': ask_size,
            'spread': spread,
            'spread_pct': spread_pct,
            'mid_price': mid_price,
            'volume_imbalance': volume_imbalance,
            'imbalance_ratio': imbalance_ratio,
            'order_flow': order_flow,
            'liquidity_score': liquidity_score,
            'price_vs_bid': ((current_price - bid_price) / bid_price * 100) if bid_price > 0 else 0.0,
            'price_vs_ask': ((ask_price - current_price) / current_price * 100) if current_price > 0 else 0.0
        }
    
    def generate_entry_signal(
        self,
        bars_15m: List[Dict],
        bars_30m: List[Dict],
        bars_1h: List[Dict],
        bars_2h: List[Dict],
        quote_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive entry signal with probabilities.
        
        Args:
            bars_15m: 15-minute bars
            bars_30m: 30-minute bars
            bars_1h: 1-hour bars
            bars_2h: 2-hour bars
        
        Returns:
            Complete signal dictionary
        """
        # Multi-timeframe analysis
        mtf_analysis = self.analyze_multi_timeframe(bars_15m, bars_30m, bars_1h, bars_2h)
        
        # Use 15m bars for current price and probabilities
        if not bars_15m or len(bars_15m) < 2:
            return {
                'signal': 'NEUTRAL',
                'confidence': 0.0,
                'entry_price': None,
                'stop_loss': None,
                'probabilities': {},
                'timeframe_analysis': {},
                'daily_stats': {}
            }
        
        df_15m = self.calculate_indicators(bars_15m, "15m")
        if df_15m.empty:
            return {
                'signal': 'NEUTRAL',
                'confidence': 0.0,
                'entry_price': None,
                'stop_loss': None,
                'probabilities': {},
                'timeframe_analysis': {},
                'daily_stats': {}
            }
        
        latest = df_15m.iloc[-1]
        current_price = latest['close']
        
        # Analyze bid/ask data for smart entry/exit
        bid_ask_analysis = self.analyze_bid_ask(quote_data, current_price)
        
        # Adjust signal based on bid/ask analysis
        original_signal = mtf_analysis['overall_signal']
        original_confidence = mtf_analysis['entry_confidence']
        
        # Use bid/ask data to refine entry/exit decisions
        order_flow = bid_ask_analysis.get('order_flow', 'NEUTRAL')
        imbalance_ratio = bid_ask_analysis.get('imbalance_ratio', 0.0)
        spread_pct = bid_ask_analysis.get('spread_pct', 0.0)
        liquidity_score = bid_ask_analysis.get('liquidity_score', 0.0)
        
        # Adjust confidence based on bid/ask alignment
        confidence_adjustment = 0.0
        
        # If order flow aligns with signal, increase confidence
        if original_signal == 'BUY' and order_flow == 'BULLISH':
            confidence_adjustment = 0.15
        elif original_signal == 'BUY' and order_flow == 'BEARISH':
            confidence_adjustment = -0.15
        elif original_signal == 'SELL' and order_flow == 'BEARISH':
            confidence_adjustment = 0.15
        elif original_signal == 'SELL' and order_flow == 'BULLISH':
            confidence_adjustment = -0.15
        
        # Adjust for spread (tight spread = better entry)
        if spread_pct < 0.5:  # Tight spread
            confidence_adjustment += 0.1
        elif spread_pct > 2.0:  # Wide spread
            confidence_adjustment -= 0.1
        
        # Adjust for liquidity
        if liquidity_score > 70:
            confidence_adjustment += 0.1
        elif liquidity_score < 30:
            confidence_adjustment -= 0.1
        
        # Final confidence (clamped to 0-1)
        confidence = max(0.0, min(1.0, original_confidence + confidence_adjustment))
        
        # Refine signal based on bid/ask
        signal = original_signal
        if original_signal == 'BUY' and order_flow == 'BEARISH' and confidence < 0.3:
            signal = 'NEUTRAL'  # Weak buy signal with bearish order flow
        elif original_signal == 'SELL' and order_flow == 'BULLISH' and confidence < 0.3:
            signal = 'NEUTRAL'  # Weak sell signal with bullish order flow
        
        # Calculate profit probabilities
        probabilities = self.calculate_profit_probabilities(current_price, bars_15m)
        
        # Calculate stop loss (1% default or ATR-based)
        atr = latest.get('atr', 0)
        stop_loss_pct = settings.STOP_LOSS_PERCENT
        atr_stop = current_price - (atr * 1.5) if atr > 0 else None
        pct_stop = current_price * (1 - stop_loss_pct)
        stop_loss = max(atr_stop, pct_stop) if atr_stop else pct_stop
        
        # Get daily price statistics (use 1-minute bars if available, otherwise use 15m)
        # Try to get 1-minute bars for more accurate daily stats
        daily_stats = {}
        try:
            # We'll calculate from the bars we have
            # For best accuracy, we should get 1Min bars, but for now use what we have
            daily_stats = self.calculate_daily_price_stats(bars_15m)
        except Exception as e:
            logger.debug(f"Error calculating daily stats: {e}")
            daily_stats = {
                'daily_high': current_price,
                'daily_low': current_price,
                'daily_average': current_price,
                'daily_open': current_price
            }
        
        # Determine optimal entry price based on bid/ask
        optimal_entry = current_price
        entry_recommendation = 'MARKET'
        
        if bid_ask_analysis.get('bid_price') and bid_ask_analysis.get('ask_price'):
            # For BUY: consider using bid if there's strong support
            if signal == 'BUY':
                if imbalance_ratio < -0.3:  # Strong bid volume
                    optimal_entry = bid_ask_analysis['bid_price']
                    entry_recommendation = 'BID'
                elif spread_pct < 0.3:  # Tight spread, use market
                    optimal_entry = bid_ask_analysis['mid_price']
                    entry_recommendation = 'MID'
                else:
                    optimal_entry = bid_ask_analysis['ask_price']
                    entry_recommendation = 'ASK'
            # For SELL: consider using ask if there's strong resistance
            elif signal == 'SELL':
                if imbalance_ratio > 0.3:  # Strong ask volume
                    optimal_entry = bid_ask_analysis['ask_price']
                    entry_recommendation = 'ASK'
                elif spread_pct < 0.3:  # Tight spread, use market
                    optimal_entry = bid_ask_analysis['mid_price']
                    entry_recommendation = 'MID'
                else:
                    optimal_entry = bid_ask_analysis['bid_price']
                    entry_recommendation = 'BID'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'entry_price': current_price,
            'optimal_entry': optimal_entry,
            'entry_recommendation': entry_recommendation,
            'stop_loss': stop_loss,
            'stop_loss_pct': ((current_price - stop_loss) / current_price) * 100,
            'probabilities': probabilities,
            'timeframe_analysis': mtf_analysis['timeframes'],
            'daily_stats': daily_stats,
            'bid_ask': bid_ask_analysis,
            'indicators': {
                'rsi': latest.get('rsi', 0),
                'msi': latest.get('msi', 0),
                'macd': latest.get('macd', 0),
                'macd_signal': latest.get('macd_signal', 0),
                'sma_20': latest.get('sma_20', 0),
                'volume_ratio': latest.get('volume_ratio', 1.0),
                'atr': atr,
                'atr_percent': latest.get('atr_percent', 0)
            },
            'timestamp': datetime.now().isoformat()
        }

