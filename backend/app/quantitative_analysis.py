"""
Quantitative Finance Analysis Module
Professional-grade calculations for technical indicators, risk metrics, and portfolio analysis
Version 2.0 - Industry Standard Formulas
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


@dataclass
class RiskMetrics:
    """Professional risk metrics container"""
    volatility: float  # Annualized volatility
    var_95: float  # Value at Risk (95% confidence)
    var_99: float  # Value at Risk (99% confidence)
    cvar_95: float  # Conditional VaR (Expected Shortfall)
    cvar_99: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    calmar_ratio: float
    beta: float
    alpha: float
    treynor_ratio: float
    information_ratio: float
    skewness: float
    kurtosis: float


@dataclass
class TechnicalMetrics:
    """Advanced technical analysis metrics"""
    trend_strength: float  # ADX-based
    volatility_regime: str
    momentum_score: float
    mean_reversion_probability: float
    breakout_probability: float
    support_levels: List[float]
    resistance_levels: List[float]
    fibonacci_levels: Dict[str, float]
    pivot_points: Dict[str, float]


class QuantitativeAnalyzer:
    """
    Professional Quantitative Finance Analyzer
    Implements industry-standard calculations for technical and risk analysis
    """

    def __init__(self, df: pd.DataFrame, risk_free_rate: float = 0.06):
        """
        Initialize with price data

        Args:
            df: DataFrame with OHLCV data
            risk_free_rate: Annual risk-free rate (default 6% for India)
        """
        self.df = df.copy()
        self.risk_free_rate = risk_free_rate
        self.returns = self._calculate_returns()

    def _calculate_returns(self) -> pd.Series:
        """Calculate log returns for better statistical properties"""
        return np.log(self.df['Close'] / self.df['Close'].shift(1)).dropna()

    def calculate_risk_metrics(self, benchmark_returns: Optional[pd.Series] = None) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics using proper quant finance formulas
        """
        returns = self.returns

        if len(returns) < 30:
            return self._empty_risk_metrics()

        # Annualization factor (252 trading days for India)
        ann_factor = 252

        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(ann_factor)

        # Value at Risk (Parametric method)
        var_95 = -stats.norm.ppf(0.95, returns.mean(), returns.std()) * np.sqrt(ann_factor)
        var_99 = -stats.norm.ppf(0.99, returns.mean(), returns.std()) * np.sqrt(ann_factor)

        # Historical VaR
        var_95_hist = -np.percentile(returns, 5)
        var_99_hist = -np.percentile(returns, 1)

        # Conditional VaR (Expected Shortfall)
        cvar_95 = -returns[returns <= -var_95_hist].mean() if len(returns[returns <= -var_95_hist]) > 0 else var_95_hist
        cvar_99 = -returns[returns <= -var_99_hist].mean() if len(returns[returns <= -var_99_hist]) > 0 else var_99_hist

        # Sharpe Ratio (using log returns)
        excess_returns = returns.mean() * ann_factor - self.risk_free_rate
        sharpe = excess_returns / volatility if volatility > 0 else 0

        # Sortino Ratio (downside deviation only)
        downside_returns = returns[returns < 0]
        downside_dev = downside_returns.std() * np.sqrt(ann_factor) if len(downside_returns) > 0 else 0
        sortino = excess_returns / downside_dev if downside_dev > 0 else 0

        # Maximum Drawdown
        cummax = self.df['Close'].cummax()
        drawdown = (self.df['Close'] - cummax) / cummax
        max_drawdown = drawdown.min()

        # Max Drawdown Duration
        is_drawdown = drawdown < 0
        if is_drawdown.any():
            duration = 0
            max_duration = 0
            for val in is_drawdown:
                if val:
                    duration += 1
                    max_duration = max(max_duration, duration)
                else:
                    duration = 0
            max_dd_duration = max_duration
        else:
            max_dd_duration = 0

        # Calmar Ratio
        total_return = (self.df['Close'].iloc[-1] / self.df['Close'].iloc[0]) - 1
        years = len(self.df) / ann_factor
        annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # Beta and Alpha (if benchmark provided)
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            covariance = np.cov(returns, benchmark_returns)[0][1]
            benchmark_var = benchmark_returns.var()
            beta = covariance / benchmark_var if benchmark_var > 0 else 1.0
            alpha = (returns.mean() * ann_factor - self.risk_free_rate) - beta * (benchmark_returns.mean() * ann_factor - self.risk_free_rate)
            treynor = (returns.mean() * ann_factor - self.risk_free_rate) / beta if beta != 0 else 0
            tracking_error = (returns - benchmark_returns).std() * np.sqrt(ann_factor)
            info_ratio = alpha / tracking_error if tracking_error > 0 else 0
        else:
            beta = 1.0
            alpha = 0.0
            treynor = sharpe
            info_ratio = 0.0

        # Higher moments
        skewness = returns.skew()
        kurtosis = returns.kurtosis()

        return RiskMetrics(
            volatility=round(volatility, 4),
            var_95=round(var_95, 4),
            var_99=round(var_99, 4),
            cvar_95=round(cvar_95, 4),
            cvar_99=round(cvar_99, 4),
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            max_drawdown=round(max_drawdown, 4),
            max_drawdown_duration=max_dd_duration,
            calmar_ratio=round(calmar, 4),
            beta=round(beta, 4),
            alpha=round(alpha, 4),
            treynor_ratio=round(treynor, 4),
            information_ratio=round(info_ratio, 4),
            skewness=round(skewness, 4),
            kurtosis=round(kurtosis, 4)
        )

    def _empty_risk_metrics(self) -> RiskMetrics:
        """Return empty risk metrics for insufficient data"""
        return RiskMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 0)

    def calculate_technical_metrics(self) -> TechnicalMetrics:
        """
        Calculate advanced technical analysis metrics
        """
        df = self.df

        # Trend Strength using ADX
        adx = self._calculate_adx(14)
        trend_strength = adx.iloc[-1] if not adx.empty else 50

        # Volatility Regime
        current_vol = self.returns.tail(20).std()
        historical_vol = self.returns.std()
        if current_vol > historical_vol * 1.2:
            vol_regime = "High"
        elif current_vol < historical_vol * 0.8:
            vol_regime = "Low"
        else:
            vol_regime = "Normal"

        # Momentum Score (composite)
        rsi = self._calculate_rsi(14).iloc[-1]
        macd_score = self._calculate_macd_score()
        momentum = (rsi - 50) / 50 * 0.5 + macd_score * 0.5
        momentum = max(-1, min(1, momentum))  # Normalize to [-1, 1]

        # Mean Reversion Probability (based on Bollinger Bands position)
        bb_position = self._calculate_bb_position()
        mean_rev_prob = abs(bb_position) if abs(bb_position) > 0.8 else 0

        # Breakout Probability (based on volume and volatility expansion)
        vol_expansion = self._detect_volatility_expansion()
        volume_spike = self._detect_volume_spike()
        breakout_prob = 0.7 if vol_expansion and volume_spike else 0.3 if vol_expansion or volume_spike else 0.1

        # Support and Resistance (using pivot points and volume profile)
        supports, resistances = self._calculate_support_resistance()

        # Fibonacci Levels
        fib_levels = self._calculate_fibonacci_levels()

        # Pivot Points
        pivot_points = self._calculate_pivot_points()

        return TechnicalMetrics(
            trend_strength=round(trend_strength, 2),
            volatility_regime=vol_regime,
            momentum_score=round(momentum, 4),
            mean_reversion_probability=round(mean_rev_prob, 4),
            breakout_probability=round(breakout_prob, 4),
            support_levels=supports,
            resistance_levels=resistances,
            fibonacci_levels=fib_levels,
            pivot_points=pivot_points
        )

    def _calculate_adx(self, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX)"""
        df = self.df

        # True Range
        tr1 = df['High'] - df['Low']
        tr2 = abs(df['High'] - df['Close'].shift(1))
        tr3 = abs(df['Low'] - df['Close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        plus_dm = df['High'].diff()
        minus_dm = -df['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[plus_dm <= minus_dm] = 0
        minus_dm[minus_dm <= plus_dm] = 0

        # Smoothed averages
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * plus_dm.rolling(window=period).mean() / atr
        minus_di = 100 * minus_dm.rolling(window=period).mean() / atr

        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx

    def _calculate_rsi(self, period: int = 14) -> pd.Series:
        """Calculate RSI using Wilder's smoothing"""
        delta = self.df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd_score(self) -> float:
        """Calculate MACD-based momentum score"""
        ema_12 = self.df['Close'].ewm(span=12).mean()
        ema_26 = self.df['Close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal

        # Normalize histogram to [-1, 1]
        hist_std = histogram.std()
        if hist_std > 0:
            score = histogram.iloc[-1] / (hist_std * 2)
            return max(-1, min(1, score))
        return 0

    def _calculate_bb_position(self) -> float:
        """Calculate position within Bollinger Bands (-1 to 1)"""
        close = self.df['Close']
        sma = close.rolling(20).mean()
        std = close.rolling(20).std()
        upper = sma + 2 * std
        lower = sma - 2 * std

        position = (close.iloc[-1] - sma.iloc[-1]) / (upper.iloc[-1] - sma.iloc[-1])
        return max(-1, min(1, position * 2))  # Scale to [-1, 1]

    def _detect_volatility_expansion(self) -> bool:
        """Detect if volatility is expanding (potential breakout)"""
        recent_vol = self.returns.tail(5).std()
        historical_vol = self.returns.tail(20).std()
        return recent_vol > historical_vol * 1.3

    def _detect_volume_spike(self) -> bool:
        """Detect unusual volume activity"""
        recent_vol = self.df['Volume'].tail(5).mean()
        historical_vol = self.df['Volume'].tail(20).mean()
        return recent_vol > historical_vol * 1.5

    def _calculate_support_resistance(self) -> Tuple[List[float], List[float]]:
        """Calculate support and resistance levels using local minima/maxima"""
        close = self.df['Close']
        high = self.df['High']
        low = self.df['Low']

        # Find local minima (support)
        local_min = close[(close.shift(2) > close.shift(1)) &
                          (close.shift(1) > close) &
                          (close < close.shift(-1)) &
                          (close.shift(-1) < close.shift(-2))]

        # Find local maxima (resistance)
        local_max = close[(close.shift(2) < close.shift(1)) &
                          (close.shift(1) < close) &
                          (close > close.shift(-1)) &
                          (close.shift(-1) > close.shift(-2))]

        # Get 3 most recent levels
        supports = sorted(local_min.tail(3).tolist()) if not local_min.empty else [low.tail(5).min()]
        resistances = sorted(local_max.tail(3).tolist()) if not local_max.empty else [high.tail(5).max()]

        return [round(s, 2) for s in supports], [round(r, 2) for r in resistances]

    def _calculate_fibonacci_levels(self) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        recent_high = self.df['High'].tail(60).max()
        recent_low = self.df['Low'].tail(60).min()
        diff = recent_high - recent_low

        return {
            '0%': round(recent_high, 2),
            '23.6%': round(recent_high - 0.236 * diff, 2),
            '38.2%': round(recent_high - 0.382 * diff, 2),
            '50%': round(recent_high - 0.5 * diff, 2),
            '61.8%': round(recent_high - 0.618 * diff, 2),
            '78.6%': round(recent_high - 0.786 * diff, 2),
            '100%': round(recent_low, 2)
        }

    def _calculate_pivot_points(self) -> Dict[str, float]:
        """Calculate standard pivot points"""
        last = self.df.iloc[-1]
        pivot = (last['High'] + last['Low'] + last['Close']) / 3

        r1 = 2 * pivot - last['Low']
        s1 = 2 * pivot - last['High']
        r2 = pivot + (last['High'] - last['Low'])
        s2 = pivot - (last['High'] - last['Low'])
        r3 = last['High'] + 2 * (pivot - last['Low'])
        s3 = last['Low'] - 2 * (last['High'] - pivot)

        return {
            'pivot': round(pivot, 2),
            'r1': round(r1, 2),
            's1': round(s1, 2),
            'r2': round(r2, 2),
            's2': round(s2, 2),
            'r3': round(r3, 2),
            's3': round(s3, 2)
        }

    def monte_carlo_simulation(self, days: int = 30, simulations: int = 1000) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for price forecasting
        """
        returns = self.returns
        mu = returns.mean()
        sigma = returns.std()
        last_price = self.df['Close'].iloc[-1]

        # Generate random walks
        dt = 1
        random_walks = np.exp(
            (mu - 0.5 * sigma**2) * dt +
            sigma * np.sqrt(dt) * np.random.randn(days, simulations)
        )

        # Calculate price paths
        price_paths = last_price * np.cumprod(random_walks, axis=0)

        # Calculate statistics
        final_prices = price_paths[-1]
        conf_5 = np.percentile(final_prices, 5)
        conf_25 = np.percentile(final_prices, 25)
        conf_50 = np.percentile(final_prices, 50)
        conf_75 = np.percentile(final_prices, 75)
        conf_95 = np.percentile(final_prices, 95)

        # Probability of price increase
        prob_up = np.mean(final_prices > last_price)

        return {
            'current_price': round(last_price, 2),
            'forecast_horizon': days,
            'simulations': simulations,
            'expected_price': round(np.mean(final_prices), 2),
            'price_intervals': {
                'p5': round(conf_5, 2),
                'p25': round(conf_25, 2),
                'p50': round(conf_50, 2),
                'p75': round(conf_75, 2),
                'p95': round(conf_95, 2)
            },
            'probability_up': round(prob_up, 4),
            'probability_down': round(1 - prob_up, 4),
            'expected_return': round((np.mean(final_prices) / last_price - 1) * 100, 2),
            'risk_reward_ratio': round((conf_95 - last_price) / (last_price - conf_5), 2) if conf_5 < last_price else 0
        }

    def generate_signals(self) -> Dict[str, Any]:
        """
        Generate trading signals based on multiple indicators
        """
        df = self.df

        # Individual signals
        signals = {}

        # RSI Signal
        rsi = self._calculate_rsi(14).iloc[-1]
        if rsi > 70:
            signals['rsi'] = 'sell'
        elif rsi < 30:
            signals['rsi'] = 'buy'
        else:
            signals['rsi'] = 'neutral'

        # MACD Signal
        ema_12 = df['Close'].ewm(span=12).mean()
        ema_26 = df['Close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()

        if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
            signals['macd'] = 'buy'
        elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
            signals['macd'] = 'sell'
        else:
            signals['macd'] = 'neutral'

        # Bollinger Bands Signal
        sma = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        upper = sma + 2 * std
        lower = sma - 2 * std

        close = df['Close'].iloc[-1]
        if close > upper.iloc[-1]:
            signals['bollinger'] = 'sell'
        elif close < lower.iloc[-1]:
            signals['bollinger'] = 'buy'
        else:
            signals['bollinger'] = 'neutral'

        # Moving Average Signal
        ema_20 = df['Close'].ewm(span=20).mean().iloc[-1]
        ema_50 = df['Close'].ewm(span=50).mean().iloc[-1]

        if close > ema_20 > ema_50:
            signals['trend'] = 'buy'
        elif close < ema_20 < ema_50:
            signals['trend'] = 'sell'
        else:
            signals['trend'] = 'neutral'

        # Composite Score
        score = 0
        if signals['rsi'] == 'buy': score += 1
        if signals['rsi'] == 'sell': score -= 1
        if signals['macd'] == 'buy': score += 1
        if signals['macd'] == 'sell': score -= 1
        if signals['bollinger'] == 'buy': score += 1
        if signals['bollinger'] == 'sell': score -= 1
        if signals['trend'] == 'buy': score += 1
        if signals['trend'] == 'sell': score -= 1

        if score >= 2:
            composite = 'strong_buy'
        elif score == 1:
            composite = 'buy'
        elif score == 0:
            composite = 'neutral'
        elif score == -1:
            composite = 'sell'
        else:
            composite = 'strong_sell'

        return {
            'individual_signals': signals,
            'composite_signal': composite,
            'signal_score': score,
            'confidence': abs(score) / 4,  # Max 4 signals
            'rsi_value': round(rsi, 2),
            'recommendation': self._signal_to_action(composite)
        }

    def _signal_to_action(self, signal: str) -> str:
        """Convert signal to action text"""
        mapping = {
            'strong_buy': 'Strong Buy - Accumulate positions',
            'buy': 'Buy - Enter position',
            'neutral': 'Hold - Wait for clearer signal',
            'sell': 'Sell - Reduce position',
            'strong_sell': 'Strong Sell - Exit position'
        }
        return mapping.get(signal, 'Neutral')

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive quantitative analysis summary"""
        risk = self.calculate_risk_metrics()
        tech = self.calculate_technical_metrics()
        signals = self.generate_signals()
        monte_carlo = self.monte_carlo_simulation()

        return {
            'risk_metrics': {
                'volatility': f"{risk.volatility*100:.2f}%",
                'sharpe_ratio': risk.sharpe_ratio,
                'sortino_ratio': risk.sortino_ratio,
                'max_drawdown': f"{risk.max_drawdown*100:.2f}%",
                'var_95': f"{risk.var_95*100:.2f}%",
                'beta': risk.beta,
                'alpha': risk.alpha,
                'calmar_ratio': risk.calmar_ratio
            },
            'technical_metrics': {
                'trend_strength': tech.trend_strength,
                'volatility_regime': tech.volatility_regime,
                'momentum_score': tech.momentum_score,
                'breakout_probability': tech.breakout_probability,
                'support_levels': tech.support_levels,
                'resistance_levels': tech.resistance_levels,
                'fibonacci_levels': tech.fibonacci_levels,
                'pivot_points': tech.pivot_points
            },
            'signals': signals,
            'monte_carlo_forecast': monte_carlo,
            'timestamp': datetime.now().isoformat()
        }


class PortfolioOptimizer:
    """
    Markowitz Portfolio Optimization
    Implements Modern Portfolio Theory calculations
    """

    @staticmethod
    def calculate_efficient_frontier(returns_df: pd.DataFrame, target_returns: Optional[np.ndarray] = None):
        """
        Calculate efficient frontier using Markowitz optimization
        """
        n_assets = len(returns_df.columns)
        mean_returns = returns_df.mean()
        cov_matrix = returns_df.cov()

        # Constraints
        def portfolio_return(weights):
            return np.dot(weights, mean_returns)

        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        # Optimization targets
        if target_returns is None:
            target_returns = np.linspace(mean_returns.min(), mean_returns.max(), 50)

        efficient_portfolios = []

        for target in target_returns:
            # Constraints: weights sum to 1, target return achieved
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: portfolio_return(x) - target}
            ]

            # Bounds: 0 <= weight <= 1 (no short selling)
            bounds = tuple((0, 1) for _ in range(n_assets))

            # Initial guess: equal weights
            x0 = np.array([1/n_assets] * n_assets)

            # Optimize
            try:
                result = minimize(
                    portfolio_volatility,
                    x0,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraints
                )

                if result.success:
                    efficient_portfolios.append({
                        'target_return': target,
                        'volatility': portfolio_volatility(result.x),
                        'sharpe': (target * 252 - 0.06) / (portfolio_volatility(result.x) * np.sqrt(252)),
                        'weights': dict(zip(returns_df.columns, result.x.round(4)))
                    })
            except:
                continue

        return efficient_portfolios

    @staticmethod
    def optimize_sharpe(returns_df: pd.DataFrame, risk_free_rate: float = 0.06):
        """
        Find portfolio with maximum Sharpe ratio
        """
        n_assets = len(returns_df.columns)
        mean_returns = returns_df.mean()
        cov_matrix = returns_df.cov()

        def negative_sharpe(weights):
            p_return = np.dot(weights, mean_returns) * 252
            p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)
            return -(p_return - risk_free_rate) / p_vol if p_vol > 0 else 0

        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        bounds = tuple((0, 1) for _ in range(n_assets))
        x0 = np.array([1/n_assets] * n_assets)

        result = minimize(
            negative_sharpe,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if result.success:
            opt_return = np.dot(result.x, mean_returns) * 252
            opt_vol = np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x))) * np.sqrt(252)

            return {
                'sharpe_ratio': -result.fun,
                'expected_return': round(opt_return, 4),
                'volatility': round(opt_vol, 4),
                'optimal_weights': dict(zip(returns_df.columns, result.x.round(4)))
            }

        return None
