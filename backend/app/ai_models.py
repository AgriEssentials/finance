"""
Advanced AI Models Module
Contains LSTM, Transformer, RL, and Explainability models
OPTIMIZED FOR LOW-MEMORY ENVIRONMENTS
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List, Any
import warnings
warnings.filterwarnings('ignore')

# Lazy-load TensorFlow only when needed (DO NOT import at module level)
TF_AVAILABLE = False
SKLEARN_AVAILABLE = False
SHAP_AVAILABLE = False

def get_tensorflow():
    """Lazy-load TensorFlow on demand"""
    global TF_AVAILABLE
    if not TF_AVAILABLE:
        try:
            import tensorflow as tf
            TF_AVAILABLE = True
            return tf
        except ImportError:
            return None
    try:
        import tensorflow as tf
        return tf
    except:
        return None

try:
    import sklearn
    from sklearn.preprocessing import MinMaxScaler, StandardScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


class LSTMPricePredictor:
    """LSTM Model for Time-Series Price Forecasting"""
    
    def __init__(self, lookback: int = 60, forecast_steps: int = 5):
        """
        Initialize LSTM predictor
        
        Args:
            lookback: Number of previous days to use
            forecast_steps: Number of days to forecast
        """
        self.lookback = lookback
        self.forecast_steps = forecast_steps
        self.scaler = MinMaxScaler(feature_range=(0, 1)) if SKLEARN_AVAILABLE else None
        self.model = None
        self.is_trained = False
        
    def prepare_data(self, prices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for LSTM training"""
        if not SKLEARN_AVAILABLE:
            print("[ERROR] sklearn required for data preparation")
            return None, None
        
        # Normalize prices
        normalized = self.scaler.fit_transform(prices.reshape(-1, 1))
        
        # Create sequences
        X, y = [], []
        for i in range(len(normalized) - self.lookback - self.forecast_steps):
            X.append(normalized[i:i + self.lookback])
            y.append(normalized[i + self.lookback:i + self.lookback + self.forecast_steps])
        
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape: Tuple):
        """Build LSTM model"""
        # Lazy-load TensorFlow on demand
        tf = get_tensorflow()
        if not tf:
            print("[ERROR] TensorFlow required for LSTM")
            return None
        
        from tensorflow.keras import layers, Sequential
        from tensorflow.keras.optimizers import Adam
        
        model = Sequential([
            layers.LSTM(128, activation='relu', input_shape=input_shape, return_sequences=True),
            layers.Dropout(0.2),
            layers.LSTM(64, activation='relu', return_sequences=False),
            layers.Dropout(0.2),
            layers.Dense(32, activation='relu'),
            layers.Dense(self.forecast_steps)
        ])
        
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
        return model
    
    def train(self, prices: np.ndarray, epochs: int = 20, batch_size: int = 32) -> Dict:
        """Train LSTM model"""
        if not TF_AVAILABLE:
            return {"status": "error", "message": "TensorFlow not available"}
        
        print("[LSTM] Preparing data...")
        X, y = self.prepare_data(prices)
        
        if X is None:
            return {"status": "error"}
        
        # Split train/test
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        print(f"[LSTM] Training on {len(X_train)} samples...")
        self.model = self.build_model((X_train.shape[1], X_train.shape[2]))
        
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            verbose=0
        )
        
        # Evaluate
        y_pred = self.model.predict(X_test, verbose=0)
        if SKLEARN_AVAILABLE:
            y_true_flat = y_test.reshape(y_test.shape[0], -1)
            y_pred_flat = y_pred.reshape(y_pred.shape[0], -1)
            mse = mean_squared_error(y_true_flat, y_pred_flat)
        else:
            mse = 0
        
        self.is_trained = True
        
        return {
            "status": "success",
            "epochs": epochs,
            "mse": float(mse),
            "final_loss": float(history.history['loss'][-1]),
            "train_samples": len(X_train),
            "test_samples": len(X_test)
        }
    
    def predict(self, recent_prices: np.ndarray) -> Dict[str, Any]:
        """Make price prediction"""
        if not self.is_trained or self.model is None:
            return {"error": "Model not trained"}
        
        if not SKLEARN_AVAILABLE:
            return {"error": "sklearn not available"}
        
        # Normalize recent prices
        normalized = self.scaler.transform(recent_prices.reshape(-1, 1))
        X = normalized[-self.lookback:].reshape(1, self.lookback, 1)
        
        # Predict
        pred_normalized = self.model.predict(X, verbose=0)[0]
        
        # Denormalize
        predicted_prices = self.scaler.inverse_transform(pred_normalized.reshape(-1, 1)).flatten()
        
        return {
            "method": "LSTM",
            "predictions": predicted_prices.tolist(),
            "confidence": 0.75
        }


class TransformerPricePredictor:
    """Transformer Model for Price Prediction"""
    
    def __init__(self, lookback: int = 60, forecast_steps: int = 5, num_heads: int = 4):
        """Initialize Transformer predictor"""
        self.lookback = lookback
        self.forecast_steps = forecast_steps
        self.num_heads = num_heads
        self.scaler = MinMaxScaler(feature_range=(0, 1)) if SKLEARN_AVAILABLE else None
        self.model = None
        self.is_trained = False
    
    def build_model(self, input_shape: Tuple):
        """Build Transformer model"""
        # Lazy-load TensorFlow on demand
        tf = get_tensorflow()
        if not tf:
            return None
        
        from tensorflow import keras
        from tensorflow.keras import layers
        from tensorflow.keras.optimizers import Adam
        
        inputs = keras.Input(shape=input_shape)
        
        # Multi-head attention
        x = layers.MultiHeadAttention(
            num_heads=self.num_heads,
            key_dim=32
        )(inputs, inputs)
        
        x = layers.GlobalAveragePooling1D()(x)
        x = layers.Dense(64, activation='relu')(x)
        x = layers.Dropout(0.2)(x)
        x = layers.Dense(32, activation='relu')(x)
        outputs = layers.Dense(self.forecast_steps)(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        
        return model
    
    def train(self, prices: np.ndarray, epochs: int = 15) -> Dict:
        """Train transformer model"""
        if not TF_AVAILABLE:
            return {"status": "error", "message": "TensorFlow not available"}
        
        print("[TRANSFORMER] Preparing data...")
        
        if not SKLEARN_AVAILABLE:
            return {"status": "error"}
        
        normalized = self.scaler.fit_transform(prices.reshape(-1, 1))
        
        X, y = [], []
        for i in range(len(normalized) - self.lookback - self.forecast_steps):
            X.append(normalized[i:i + self.lookback])
            y.append(normalized[i + self.lookback:i + self.lookback + self.forecast_steps])
        
        X, y = np.array(X), np.array(y)
        
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        print(f"[TRANSFORMER] Training...")
        self.model = self.build_model((X_train.shape[1], X_train.shape[2]))
        
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=32,
            validation_data=(X_test, y_test),
            verbose=0
        )
        
        self.is_trained = True
        
        return {
            "status": "success",
            "epochs": epochs,
            "final_loss": float(history.history['loss'][-1]),
            "train_samples": len(X_train)
        }
    
    def predict(self, recent_prices: np.ndarray) -> Dict[str, Any]:
        """Make prediction"""
        if not self.is_trained or self.model is None:
            return {"error": "Model not trained"}
        
        if not SKLEARN_AVAILABLE:
            return {"error": "sklearn not available"}
        
        normalized = self.scaler.transform(recent_prices.reshape(-1, 1))
        X = normalized[-self.lookback:].reshape(1, self.lookback, 1)
        
        pred_normalized = self.model.predict(X, verbose=0)[0]
        predicted_prices = self.scaler.inverse_transform(pred_normalized.reshape(-1, 1)).flatten()
        
        return {
            "method": "Transformer",
            "predictions": predicted_prices.tolist(),
            "confidence": 0.72
        }


class ExplainableAIAnalyzer:
    """Generate explanations for predictions using SHAP"""

    @staticmethod
    def _as_float(value: Any) -> Any:
        """Best-effort conversion to float."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        if "(" in text:
            text = text.split("(", 1)[0].strip()
        text = text.replace("%", "").strip()
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def generate_reasons(prediction: str, confidence: float, indicators: Dict) -> List[str]:
        """Generate top reasons for prediction"""
        reasons: List[str] = []
        prediction_text = str(prediction or "").upper()
        confidence_pct = ExplainableAIAnalyzer._as_float(confidence) or 0.0
        if confidence_pct <= 1:
            confidence_pct *= 100

        trend = str(indicators.get("trend", "")).lower()
        if "strong bullish" in trend or "uptrend" in trend or "bullish" in trend:
            reasons.append("Trend structure is bullish, supporting upside continuation.")
        elif "strong bearish" in trend or "downtrend" in trend or "bearish" in trend:
            reasons.append("Trend structure is bearish, increasing downside pressure.")

        rsi = ExplainableAIAnalyzer._as_float(indicators.get("rsi"))
        if rsi is None:
            rsi = ExplainableAIAnalyzer._as_float(indicators.get("rsi_value"))
        if rsi is not None:
            if rsi < 30:
                reasons.append("RSI is in oversold territory, which can support a rebound setup.")
            elif rsi > 70:
                reasons.append("RSI is in overbought territory, which raises pullback risk.")
            elif rsi >= 55:
                reasons.append("RSI is above neutral, indicating constructive momentum.")
            elif rsi <= 45:
                reasons.append("RSI is below neutral, indicating weaker momentum.")

        macd_hist = ExplainableAIAnalyzer._as_float(indicators.get("macd_histogram"))
        if macd_hist is not None:
            if macd_hist > 0:
                reasons.append("MACD histogram is positive, confirming bullish momentum.")
            elif macd_hist < 0:
                reasons.append("MACD histogram is negative, confirming bearish momentum.")

        sentiment_score = ExplainableAIAnalyzer._as_float(indicators.get("sentiment_score"))
        sentiment_class = str(indicators.get("sentiment_classification", "")).lower()
        if sentiment_score is not None:
            if sentiment_score > 0.25:
                reasons.append("News flow is net positive, improving near-term sentiment support.")
            elif sentiment_score < -0.25:
                reasons.append("News flow is net negative, adding downside sentiment pressure.")
        elif sentiment_class:
            if "positive" in sentiment_class:
                reasons.append("Sentiment classification is positive based on recent headlines.")
            elif "negative" in sentiment_class:
                reasons.append("Sentiment classification is negative based on recent headlines.")

        ml_up_probability = ExplainableAIAnalyzer._as_float(
            indicators.get("ml_up_probability", indicators.get("up_probability"))
        )
        if ml_up_probability is not None:
            if ml_up_probability >= 55:
                reasons.append(f"ML probability favors upside ({ml_up_probability:.1f}% up likelihood).")
            elif ml_up_probability <= 45:
                reasons.append(f"ML probability favors downside ({100 - ml_up_probability:.1f}% down likelihood).")

        projected_prices = indicators.get("predicted_prices") if isinstance(indicators.get("predicted_prices"), list) else []
        current_price = ExplainableAIAnalyzer._as_float(indicators.get("current_price"))
        if projected_prices and current_price:
            first = ExplainableAIAnalyzer._as_float(projected_prices[0])
            last = ExplainableAIAnalyzer._as_float(projected_prices[-1])
            if first is not None and last is not None and current_price > 0:
                net_change = ((last - current_price) / current_price) * 100
                if net_change > 0:
                    reasons.append(f"Forecast path trends upward by ~{net_change:.2f}% from current levels.")
                elif net_change < 0:
                    reasons.append(f"Forecast path trends downward by ~{abs(net_change):.2f}% from current levels.")
                else:
                    reasons.append("Forecast path is mostly flat, indicating a range-bound expectation.")

        geopolitical = ExplainableAIAnalyzer.generate_geopolitical_analysis(indicators)
        if geopolitical:
            reasons.append("Geopolitical and macro headline risk is included in the decision.")

        if confidence_pct >= 75:
            reasons.append("Signal alignment is relatively strong across multiple inputs.")
        elif confidence_pct <= 55:
            reasons.append("Signal alignment is mixed, so conviction is moderate.")

        if not reasons:
            if prediction_text in {"BUY", "UP"}:
                reasons = ["Overall signals mildly favor upside, but with uncertainty."]
            elif prediction_text in {"SELL", "DOWN"}:
                reasons = ["Overall signals mildly favor downside, but with uncertainty."]
            else:
                reasons = ["Inputs are mixed, so the model remains neutral."]

        return reasons[:6]

    @staticmethod
    def generate_geopolitical_analysis(indicators: Dict) -> List[str]:
        """Extract geopolitical context from structured indicators."""
        scenarios = indicators.get("geopolitical_scenarios", [])
        if isinstance(scenarios, str) and scenarios.strip():
            scenarios = [scenarios.strip()]
        if isinstance(scenarios, list):
            cleaned = [str(item).strip() for item in scenarios if str(item).strip()]
            return cleaned[:5]
        return []

    @staticmethod
    def generate_graph_explanation(prediction: str, confidence: float, indicators: Dict) -> str:
        """Explain why the forecast line shape looks the way it does."""
        confidence_pct = ExplainableAIAnalyzer._as_float(confidence) or 0.0
        if confidence_pct <= 1:
            confidence_pct *= 100

        current_price = ExplainableAIAnalyzer._as_float(indicators.get("current_price"))
        predicted_prices = indicators.get("predicted_prices") if isinstance(indicators.get("predicted_prices"), list) else []
        prediction_text = str(prediction or "").upper()

        if not predicted_prices or not current_price:
            direction = "upward" if prediction_text in {"BUY", "UP"} else ("downward" if prediction_text in {"SELL", "DOWN"} else "sideways")
            return (
                f"The projected line is {direction} because the model aggregates trend, momentum, sentiment, and risk signals "
                f"into a short-horizon path with confidence around {confidence_pct:.0f}%."
            )

        cleaned = [ExplainableAIAnalyzer._as_float(p) for p in predicted_prices]
        cleaned = [p for p in cleaned if p is not None]
        if not cleaned:
            return "The future line reflects blended model signals and confidence-weighted projection."

        final_price = cleaned[-1]
        net_change_pct = ((final_price - current_price) / current_price) * 100 if current_price else 0.0
        slope = "upward" if net_change_pct > 0 else ("downward" if net_change_pct < 0 else "sideways")

        return (
            f"The upcoming forecast appears {slope} because the model's current signal balance points to an expected "
            f"{net_change_pct:+.2f}% move over the projection window. Intermediate points are smoothed between periods "
            f"to represent a gradual path rather than a single-step jump, with confidence at {confidence_pct:.0f}%."
        )

    @staticmethod
    def generate_geopolitical_report(prediction: str, indicators: Dict) -> Dict[str, Any]:
        """Build professional geopolitical analysis for the selected stock."""
        scenarios = ExplainableAIAnalyzer.generate_geopolitical_analysis(indicators)
        sentiment_score = ExplainableAIAnalyzer._as_float(indicators.get("sentiment_score")) or 0.0
        trend = str(indicators.get("trend", "Neutral"))
        finnhub = indicators.get("finnhub_insights", {}) if isinstance(indicators.get("finnhub_insights"), dict) else {}
        analyst = finnhub.get("analyst_recommendation", {}) if isinstance(finnhub.get("analyst_recommendation"), dict) else {}
        price_target = finnhub.get("price_target", {}) if isinstance(finnhub.get("price_target"), dict) else {}
        consensus = str(analyst.get("consensus", "Not available"))
        upside = ExplainableAIAnalyzer._as_float(price_target.get("upside_percent_vs_current"))

        macro_drivers: List[str] = []
        for item in scenarios:
            lower = item.lower()
            if "oil" in lower or "opec" in lower:
                macro_drivers.append("Energy price volatility can affect inflation, rates, and margins.")
            if "fed" in lower or "rbi" in lower or "rate" in lower:
                macro_drivers.append("Interest-rate policy can re-rate valuations and funding costs.")
            if "war" in lower or "conflict" in lower or "sanction" in lower:
                macro_drivers.append("Geopolitical conflict/sanctions can disrupt flows, trade, and risk appetite.")
            if "china" in lower:
                macro_drivers.append("China demand and policy changes can alter global growth expectations.")
            if "election" in lower or "policy" in lower:
                macro_drivers.append("Policy and election uncertainty can raise near-term volatility.")

        if not macro_drivers:
            macro_drivers = [
                "No single macro shock dominates right now; risk is distributed across rates, growth, and liquidity."
            ]

        channels = [
            "Valuation channel: global rate expectations affect equity multiples.",
            "Earnings channel: commodity/currency changes impact input costs and margins.",
            "Flow channel: risk-on/risk-off positioning shifts institutional capital allocation."
        ]

        if "Bullish" in trend and sentiment_score > 0:
            base_prob = "Moderate-to-High"
            base_impact = "Supports continuation if macro volatility remains contained."
        elif "Bearish" in trend and sentiment_score < 0:
            base_prob = "Moderate-to-High"
            base_impact = "Raises downside continuation risk under adverse headlines."
        else:
            base_prob = "Moderate"
            base_impact = "Suggests two-way movement with headline sensitivity."

        scenario_matrix = [
            {
                "scenario": "Base case",
                "probability": base_prob,
                "implication": base_impact,
                "positioning": f"Align with {prediction.upper()} bias but use disciplined risk limits."
            },
            {
                "scenario": "Risk-off shock",
                "probability": "Low-to-Moderate",
                "implication": "Adverse geopolitical surprise can compress multiples and increase drawdown risk.",
                "positioning": "Keep tighter stop discipline and avoid leverage expansion."
            },
            {
                "scenario": "Risk-on relief",
                "probability": "Low-to-Moderate",
                "implication": "Policy clarity / softer global stress can support upside follow-through.",
                "positioning": "Allow trend participation while scaling entries."
            }
        ]

        stock_specific = [
            f"Trend context: {trend}.",
            f"Current sentiment score: {sentiment_score:+.2f} (range -1 to +1).",
            f"Analyst consensus (Finnhub): {consensus}."
        ]
        if upside is not None:
            stock_specific.append(f"Finnhub mean target implies {upside:+.2f}% vs current price.")

        return {
            "macro_drivers": list(dict.fromkeys(macro_drivers))[:5],
            "transmission_channels": channels,
            "scenario_matrix": scenario_matrix,
            "stock_specific_view": stock_specific
        }


# Initialize global models
lstm_model = LSTMPricePredictor(lookback=60, forecast_steps=5)
transformer_model = TransformerPricePredictor(lookback=60, forecast_steps=5)
explainer = ExplainableAIAnalyzer()

