"""
Professional dashboard analytics for advanced visualization.
Provides quantitative chart payloads for institutional-style workflows.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import yfinance as yf


class ProfessionalDashboardBuilder:
    """Build advanced chart-ready analytics from price history."""

    def __init__(self, symbol: str, mode: str = "swing"):
        self.symbol = symbol
        self.mode = mode

    def _history_config(self) -> Dict[str, str]:
        if self.mode == "intraday":
            return {"period": "60d", "interval": "30m"}
        if self.mode == "longterm":
            return {"period": "5y", "interval": "1wk"}
        return {"period": "2y", "interval": "1d"}

    def _annualization_factor(self) -> int:
        if self.mode == "intraday":
            return 252 * 13
        if self.mode == "longterm":
            return 52
        return 252

    def _forecast_horizon(self) -> int:
        if self.mode == "intraday":
            return 26
        if self.mode == "longterm":
            return 20
        return 30

    def _next_label(self, base: pd.Timestamp, step: int) -> str:
        if self.mode == "intraday":
            return (base + timedelta(minutes=30 * step)).strftime("%d-%b %H:%M")
        if self.mode == "longterm":
            return (base + timedelta(weeks=step)).strftime("%d-%b-%y")
        return (base + timedelta(days=step)).strftime("%d-%b-%y")

    def build(self) -> Dict[str, Any]:
        cfg = self._history_config()
        df = yf.Ticker(self.symbol).history(period=cfg["period"], interval=cfg["interval"])
        if df.empty:
            raise ValueError(f"No dashboard data found for {self.symbol}")

        close = df["Close"].dropna()
        volume = df["Volume"].fillna(0)
        log_returns = np.log(close / close.shift(1)).dropna()
        annual_factor = self._annualization_factor()

        volatility = log_returns.rolling(20).std() * np.sqrt(annual_factor)
        vol_series = volatility.dropna()
        vol_now = float(vol_series.iloc[-1]) if not vol_series.empty else 0.0
        p25 = float(vol_series.quantile(0.25)) if not vol_series.empty else 0.0
        p75 = float(vol_series.quantile(0.75)) if not vol_series.empty else 0.0

        if vol_now >= p75:
            regime = "HIGH_VOL"
        elif vol_now <= p25:
            regime = "LOW_VOL"
        else:
            regime = "NORMAL_VOL"

        drawdown = close / close.cummax() - 1

        mom_windows = [5, 20, 60, 120]
        momentum = []
        for w in mom_windows:
            if len(close) > w:
                ret = (close.iloc[-1] / close.iloc[-w - 1] - 1) * 100
                momentum.append({"horizon": f"{w}p", "return_pct": round(float(ret), 2)})

        var95 = 0.0
        cvar95 = 0.0
        if len(log_returns) > 30:
            var95 = float(np.quantile(log_returns, 0.05))
            tail = log_returns[log_returns <= var95]
            cvar95 = float(tail.mean()) if not tail.empty else var95

        fan = self._build_monte_carlo_fan(close, log_returns)

        rel = self._build_relative_strength(close)

        return {
            "symbol": self.symbol,
            "mode": self.mode,
            "timestamp": datetime.now().isoformat(),
            "kpis": {
                "annualized_volatility_pct": round(vol_now * 100, 2),
                "volatility_regime": regime,
                "max_drawdown_pct": round(float(drawdown.min() * 100), 2),
                "var_95_pct": round(var95 * 100, 2),
                "cvar_95_pct": round(cvar95 * 100, 2),
            },
            "charts": {
                "price_volume": {
                    "labels": [idx.strftime("%d-%b") for idx in close.tail(120).index],
                    "close": [round(float(x), 2) for x in close.tail(120).values],
                    "volume": [int(x) for x in volume.tail(120).values],
                },
                "volatility_regime": {
                    "labels": [idx.strftime("%d-%b") for idx in vol_series.tail(120).index],
                    "volatility": [round(float(x) * 100, 2) for x in vol_series.tail(120).values],
                    "p25": round(p25 * 100, 2),
                    "p75": round(p75 * 100, 2),
                },
                "drawdown": {
                    "labels": [idx.strftime("%d-%b") for idx in drawdown.tail(180).index],
                    "drawdown_pct": [round(float(x) * 100, 2) for x in drawdown.tail(180).values],
                },
                "momentum_heatmap": momentum,
                "monte_carlo_fan": fan,
                "relative_strength": rel,
            },
        }

    def _build_relative_strength(self, close: pd.Series) -> Dict[str, List[float]]:
        bench = yf.Ticker("^NSEI").history(period="2y", interval="1d")
        if bench.empty:
            return {"labels": [], "strategy": [], "benchmark": []}

        combined = pd.DataFrame({"asset": close, "bench": bench["Close"]}).dropna()
        if combined.empty:
            return {"labels": [], "strategy": [], "benchmark": []}

        strategy = (combined["asset"] / combined["asset"].iloc[0]) * 100
        benchmark = (combined["bench"] / combined["bench"].iloc[0]) * 100

        return {
            "labels": [idx.strftime("%d-%b") for idx in combined.tail(180).index],
            "strategy": [round(float(v), 2) for v in strategy.tail(180).values],
            "benchmark": [round(float(v), 2) for v in benchmark.tail(180).values],
        }

    def _build_monte_carlo_fan(self, close: pd.Series, log_returns: pd.Series) -> Dict[str, Any]:
        horizon = self._forecast_horizon()
        if len(log_returns) < 30:
            return {
                "labels": [],
                "q10": [],
                "q25": [],
                "q50": [],
                "q75": [],
                "q90": [],
            }

        mu = float(log_returns.mean())
        sigma = float(log_returns.std())
        current = float(close.iloc[-1])
        n_sims = 400

        shocks = np.random.normal(mu, sigma, size=(n_sims, horizon))
        paths = current * np.exp(np.cumsum(shocks, axis=1))

        q10 = np.quantile(paths, 0.10, axis=0)
        q25 = np.quantile(paths, 0.25, axis=0)
        q50 = np.quantile(paths, 0.50, axis=0)
        q75 = np.quantile(paths, 0.75, axis=0)
        q90 = np.quantile(paths, 0.90, axis=0)

        last_idx = close.index[-1]
        labels = [self._next_label(last_idx, i + 1) for i in range(horizon)]

        return {
            "labels": labels,
            "q10": [round(float(x), 2) for x in q10],
            "q25": [round(float(x), 2) for x in q25],
            "q50": [round(float(x), 2) for x in q50],
            "q75": [round(float(x), 2) for x in q75],
            "q90": [round(float(x), 2) for x in q90],
            "current_price": round(current, 2),
        }

