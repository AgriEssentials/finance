"""
Advanced AI Routes for LSTM, Transformer, RL, Explainability
Integrates with existing FastAPI app
"""

from fastapi import APIRouter, Query, HTTPException, Depends, WebSocket
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import numpy as np

from app.ai_models import lstm_model, transformer_model, explainer, TF_AVAILABLE, SKLEARN_AVAILABLE
from app.rl_portfolio import portfolio_rl_agent, sharpe_calc
from app.alerts import alert_manager, ws_manager
from app.backtester import backtest_engine, strategy_builder
from app.sentiment import sentiment_analyzer
from app.database import get_db, User
from app.auth import get_current_user_optional
import yfinance as yf
import math
from datetime import datetime
from dataclasses import asdict


router = APIRouter(prefix="/api/ai", tags=["advanced-ai"])


def _safe_num(value: float, default: float = 0.0) -> float:
    """Return JSON-safe finite float."""
    try:
        val = float(value)
        return val if math.isfinite(val) else default
    except Exception:
        return default


def _fetch_close_prices(symbol: str, period: str = "2y") -> np.ndarray:
    """Fetch close prices with validation."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)
    if hist.empty or 'Close' not in hist:
        raise HTTPException(status_code=404, detail=f"No market data found for {symbol}")
    prices = hist['Close'].dropna().values.astype(float)
    if len(prices) == 0:
        raise HTTPException(status_code=404, detail=f"No usable close prices found for {symbol}")
    return prices


# ==================== LSTM FORECASTING (LIGHTWEIGHT - NO TRAINING) ====================

@router.post("/lstm/train")
@router.get("/lstm/train")
async def train_lstm_model(
    symbol: str = Query(..., description="Stock symbol"),
    epochs: int = Query(20, description="Training epochs"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """LSTM training endpoint - DISABLED for memory optimization"""
    return {
        "symbol": symbol,
        "model": "LSTM",
        "status": "disabled",
        "message": "LSTM training is disabled. Use /api/ai/lstm/predict for instant predictions.",
        "note": "LSTM training requires significant memory. Predictions use statistical analysis instead."
    }


@router.get("/lstm/predict")
async def lstm_predict(
    symbol: str = Query(..., description="Stock symbol"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get lightweight price predictions using statistical methods"""
    try:
        # Fetch recent prices (lightweight - 1 year only)
        prices = _fetch_close_prices(symbol, period="1y")
        if len(prices) < 20:
            raise HTTPException(status_code=400, detail="Insufficient data for prediction")
        
        # Use simple statistical forecasting instead of LSTM
        recent = prices[-20:]
        trend = (prices[-1] - prices[-5]) / prices[-5] * 100  # 5-day trend
        volatility = _safe_num(np.std(np.diff(prices[-20:])) / np.mean(prices[-20:]) * 100)
        
        # Simple forecast: extrapolate trend
        forecast_days = 5
        forecasts = []
        last_price = prices[-1]
        daily_change = (trend / 100) * last_price / 5
        
        for i in range(1, forecast_days + 1):
            forecasts.append(_safe_num(last_price + (daily_change * i)))
        
        return {
            "symbol": symbol,
            "method": "Statistical Forecast (Lightweight)",
            "predictions": forecasts,
            "confidence": max(0.5, min(1.0, 0.75 - (volatility / 200))),  # Lower confidence for high volatility
            "forecast_days": forecast_days,
            "trend_percentage": _safe_num(trend),
            "volatility_percentage": _safe_num(volatility),
            "current_price": _safe_num(prices[-1])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TRANSFORMER FORECASTING (LIGHTWEIGHT - NO TRAINING) ====================

@router.post("/transformer/train")
@router.get("/transformer/train")
async def train_transformer_model(
    symbol: str = Query(...),
    epochs: int = Query(15),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Transformer training endpoint - DISABLED for memory optimization"""
    return {
        "symbol": symbol,
        "model": "Transformer",
        "status": "disabled",
        "message": "Transformer training is disabled. Use /api/ai/transformer/predict for instant predictions.",
        "note": "Transformer training requires significant memory. Predictions use statistical analysis instead."
    }


@router.get("/transformer/predict")
async def transformer_predict(
    symbol: str = Query(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get lightweight transformer-style predictions using trend analysis"""
    try:
        # Fetch recent prices (lightweight)
        prices = _fetch_close_prices(symbol, period="1y")
        if len(prices) < 20:
            raise HTTPException(status_code=400, detail="Insufficient data for prediction")
        
        # Multi-timeframe trend analysis (simulating transformer's attention)
        st_trend = (prices[-1] - prices[-5]) / prices[-5]   # 5-day trend
        mt_trend = (prices[-1] - prices[-20]) / prices[-20]  # 20-day trend
        lt_trend = (prices[-1] - prices[-60:][0]) / prices[-60:][0] if len(prices) >= 60 else st_trend  # 60-day trend
        
        # Weighted average trend (attention-like mechanism)
        combined_trend = (st_trend * 0.5 + mt_trend * 0.3 + lt_trend * 0.2)
        volatility = _safe_num(np.std(np.diff(prices[-20:])) / np.mean(prices[-20:]))
        
        # Forecast
        forecast_days = 5
        forecasts = []
        last_price = prices[-1]
        daily_trend = combined_trend / 5
        
        for i in range(1, forecast_days + 1):
            forecasts.append(_safe_num(last_price * (1 + daily_trend * i)))
        
        return {
            "symbol": symbol,
            "method": "Transformer-style Trend Analysis",
            "predictions": forecasts,
            "confidence": max(0.5, min(1.0, 0.75 - volatility)),
            "forecast_days": forecast_days,
            "short_term_trend": _safe_num(st_trend * 100),
            "medium_term_trend": _safe_num(mt_trend * 100),
            "long_term_trend": _safe_num(lt_trend * 100),
            "current_price": _safe_num(prices[-1])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PORTFOLIO OPTIMIZATION (RL) ====================

@router.post("/portfolio/optimize")
@router.get("/portfolio/optimize")
async def optimize_portfolio(
    symbols: List[str] = Query(..., description="List of stock symbols"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get RL-optimized portfolio allocation"""
    try:
        prices_history = {}
        sentiments = {}
        volatilities = {}
        
        for symbol in symbols[:5]:  # Max 5 stocks
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")
            closes = hist['Close'].dropna().values
            if len(closes) < 30:
                continue
            prices_history[symbol] = closes.tolist()
            
            # Mock sentiment and volatility (in production, fetch from analysis)
            sentiments[symbol] = float(np.random.uniform(-0.5, 0.5))
            diffs = np.diff(closes)
            denom = float(np.mean(closes)) if len(closes) else 1.0
            volatilities[symbol] = _safe_num(np.std(diffs) / denom if denom else 0.0)

        if not prices_history:
            raise HTTPException(status_code=400, detail="No sufficient market data for optimization")
        
        # Optimize
        result = portfolio_rl_agent.optimize_portfolio(prices_history, sentiments, volatilities)
        
        # Calculate portfolio metrics
        selected_symbols = list(prices_history.keys())
        avg_returns = [_safe_num(np.mean(np.diff(prices_history[s]))) for s in selected_symbols]
        avg_sentiment = _safe_num(np.mean(list(sentiments.values())))
        
        sharpe = sharpe_calc.calculate_sharpe(avg_returns)
        
        return {
            "symbols": [str(s) for s in selected_symbols],
            "allocation_percentage": int(_safe_num(result.get("allocation", 0))),
            "recommendation": str(result.get("recommended_action", "HOLD")),
            "state": str(result.get("state", "UNKNOWN")),
            "portfolio_sharpe_ratio": float(round(_safe_num(sharpe), 3)),
            "average_sentiment": float(round(_safe_num(avg_sentiment), 3))
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EXPLAINABLE AI ====================

@router.post("/explainability/analyze")
@router.get("/explainability/analyze")
async def explain_prediction(
    symbol: str = Query(...),
    prediction: str = Query(..., description="BUY/SELL/HOLD"),
    confidence: float = Query(...),
    indicators: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get explainable reasons for prediction"""
    try:
        parsed_indicators: Dict[str, Any] = {}
        if indicators:
            try:
                import json
                parsed_indicators = json.loads(indicators)
            except Exception:
                parsed_indicators = {}
        prediction_normalized = str(prediction or "").strip().upper()
        prediction_map = {
            "UP": "BUY",
            "DOWN": "SELL",
            "NEUTRAL": "HOLD"
        }
        decision = prediction_map.get(prediction_normalized, prediction_normalized or "HOLD")
        confidence_pct = float(confidence)
        if confidence_pct <= 1:
            confidence_pct *= 100
        confidence_pct = max(0.0, min(confidence_pct, 100.0))
        confidence_ratio = round(confidence_pct / 100.0, 4)

        reasons = explainer.generate_reasons(decision, confidence_pct, parsed_indicators)
        graph_explanation = explainer.generate_graph_explanation(decision, confidence_pct, parsed_indicators)
        geopolitical_analysis = explainer.generate_geopolitical_analysis(parsed_indicators)
        geopolitical_report = explainer.generate_geopolitical_report(decision, parsed_indicators)
        geopolitical_text = (
            " Geopolitical context considered: " + "; ".join(geopolitical_analysis[:3]) + "."
            if geopolitical_analysis else
            " Geopolitical risk was checked; no dominant headline shock was detected in current inputs."
        )
        technical_block = (
            f"Technical factors: Trend={parsed_indicators.get('trend', 'N/A')}, "
            f"RSI={parsed_indicators.get('rsi', parsed_indicators.get('rsi_value', 'N/A'))}, "
            f"MACD histogram={parsed_indicators.get('macd_histogram', 'N/A')}."
        )
        sentiment_block = (
            f"Sentiment factors: score={parsed_indicators.get('sentiment_score', 'N/A')}, "
            f"classification={parsed_indicators.get('sentiment_classification', 'N/A')}, "
            f"ML up probability={parsed_indicators.get('ml_up_probability', parsed_indicators.get('up_probability', 'N/A'))}%."
        )
        detailed_explanation = (
            f"{decision} with {confidence_pct:.0f}% confidence because "
            f"{'; '.join(reasons[:4]) if reasons else 'multiple signals align moderately'}."
            f" {technical_block} {sentiment_block} {graph_explanation}{geopolitical_text}"
        )
        
        return {
            "symbol": symbol,
            "decision": decision,
            "confidence": confidence_ratio,
            "confidence_percent": confidence_pct,
            "top_reasons": reasons[:3],
            "explanation": detailed_explanation,
            "detailed_explanation": detailed_explanation,
            "graph_explanation": graph_explanation,
            "geopolitical_analysis": geopolitical_analysis,
            "geopolitical_report": geopolitical_report
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ALERTS ====================

@router.post("/alerts/create")
@router.get("/alerts/create")
async def create_alert(
    symbol: str = Query(...),
    alert_type: str = Query(..., description="price_above, price_below, sentiment_positive, etc"),
    threshold: float = Query(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Create price or sentiment alert"""
    try:
        user_id = str(current_user.id) if current_user else "guest"
        
        result = alert_manager.create_alert(
            user_id,
            symbol,
            alert_type,
            threshold,
            f"Alert when {symbol} {alert_type} {threshold}"
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get user alerts"""
    user_id = str(current_user.id) if current_user else "guest"
    alerts = alert_manager.get_user_alerts(user_id)
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/alerts/evaluate")
async def evaluate_alerts(
    symbol: Optional[str] = Query(None, description="Optional symbol to evaluate"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Evaluate active alerts with latest market/sentiment data and return triggered alerts."""
    try:
        symbols_to_check = [symbol] if symbol else alert_manager.get_active_symbols()
        triggered_alerts = []
        checked_symbols = []

        for sym in symbols_to_check:
            if not sym:
                continue

            active_for_symbol = alert_manager.get_alerts_for_symbol(sym)
            if not active_for_symbol:
                continue

            checked_symbols.append(sym)

            latest_price = None
            try:
                prices = _fetch_close_prices(sym, period="5d")
                latest_price = float(prices[-1])
            except HTTPException:
                latest_price = None
            except Exception:
                latest_price = None

            if latest_price is not None:
                triggered_alerts.extend(alert_manager.check_price_alert(sym, latest_price))

            has_sentiment_alert = any(a.alert_type.startswith("sentiment_") for a in active_for_symbol)
            if has_sentiment_alert:
                try:
                    sentiment = sentiment_analyzer.get_sentiment_for_stock(sym)
                    sentiment_score = float(sentiment.get("sentiment_score", 0))
                    triggered_alerts.extend(alert_manager.check_sentiment_alert(sym, sentiment_score))
                except Exception:
                    pass

        if triggered_alerts:
            alert_manager.mark_alerts_triggered(triggered_alerts)

        return {
            "checked_symbols": checked_symbols,
            "triggered_alerts": [asdict(alert) for alert in triggered_alerts],
            "triggered_count": len(triggered_alerts),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Delete alert"""
    success = alert_manager.delete_alert(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert deleted", "alert_id": alert_id}


# ==================== BACKTESTING ====================

@router.post("/backtest/rsi-strategy")
@router.get("/backtest/rsi-strategy")
async def backtest_rsi(
    symbol: str = Query(...),
    oversold: int = Query(30),
    overbought: int = Query(70),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Backtest RSI strategy"""
    try:
        # Fetch data
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2y")
        closes = hist['Close'].dropna()
        prices = closes.values
        if len(prices) < 60:
            raise HTTPException(status_code=400, detail="Insufficient historical data for RSI backtest")

        # Calculate RSI robustly from close series.
        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_series = (100 - (100 / (1 + rs))).fillna(50)
        rsi_values = rsi_series.values
        
        # Generate signals
        signals = strategy_builder.rsi_strategy(rsi_values, oversold, overbought)
        
        # Backtest
        result = backtest_engine.run_strategy(prices, signals, "RSI Strategy")
        
        return {
            "symbol": symbol,
            "strategy": "RSI",
            "total_return": round(_safe_num(result.total_return) * 100, 2),
            "annual_return": round(_safe_num(result.annual_return) * 100, 2),
            "sharpe_ratio": round(_safe_num(result.sharpe_ratio), 3),
            "max_drawdown": round(_safe_num(result.max_drawdown) * 100, 2),
            "win_rate": round(_safe_num(result.win_rate) * 100, 2),
            "num_trades": result.num_trades,
            "profit_per_trade": round(_safe_num(result.profit_per_trade) * 100, 2)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest/macd-strategy")
@router.get("/backtest/macd-strategy")
async def backtest_macd(
    symbol: str = Query(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Backtest MACD strategy"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2y")
        prices = hist['Close'].dropna().values
        if len(prices) < 60:
            raise HTTPException(status_code=400, detail="Insufficient historical data for MACD backtest")
        
        signals = strategy_builder.macd_strategy(prices)
        result = backtest_engine.run_strategy(prices, signals, "MACD Strategy")
        
        return {
            "symbol": symbol,
            "strategy": "MACD",
            "total_return": round(_safe_num(result.total_return) * 100, 2),
            "annual_return": round(_safe_num(result.annual_return) * 100, 2),
            "sharpe_ratio": round(_safe_num(result.sharpe_ratio), 3),
            "max_drawdown": round(_safe_num(result.max_drawdown) * 100, 2),
            "win_rate": round(_safe_num(result.win_rate) * 100, 2),
            "num_trades": result.num_trades,
            "profit_per_trade": round(_safe_num(result.profit_per_trade) * 100, 2)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WEBSOCKET (REAL-TIME ALERTS) ====================

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time alerts"""
    await ws_manager.connect(user_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or process message
            await ws_manager.send_to_user(user_id, {"type": "echo", "data": data})
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    finally:
        await ws_manager.disconnect(user_id, websocket)


# Export router
def get_ai_router():
    """Get AI routes to include in main app"""
    return router




