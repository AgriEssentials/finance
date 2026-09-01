"""
AI Prediction Module
Handles AI-powered stock prediction using Groq API
Integrates all analysis data to provide professional trading recommendations
Includes price prediction chart data
"""

import os
import requests
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import math
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AIStockPredictor:
    """Class to get AI-powered predictions from Groq API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI predictor
        
        Args:
            api_key: Groq API key (optional, can be set via environment variable)
        """
        self.groq_api_key = api_key or os.getenv('GROQ_API_KEY')
        self.model = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
        configured_candidates = os.getenv('GROQ_MODEL_CANDIDATES', '').strip()
        default_candidates = ['openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'qwen/qwen3.8-27b', 'groq/compound-mini']
        if configured_candidates:
            parsed = [m.strip() for m in configured_candidates.split(',') if m.strip()]
            self.model_candidates = parsed if parsed else default_candidates
        else:
            self.model_candidates = default_candidates
        print(
            "DEBUG: AI Predictor initialized. "
            f"Groq key present: {bool(self.groq_api_key)}"
        )
    
    def get_ai_prediction(
        self,
        symbol: str,
        current_price: float,
        mode: str,
        technical_indicators: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        ml_prediction: Dict[str, Any],
        risk_data: Dict[str, Any],
        price_history: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Get AI prediction from Groq API
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            mode: Analysis mode (intraday/swing/longterm)
            technical_indicators: Technical analysis data
            sentiment_data: News sentiment analysis
            ml_prediction: ML model prediction
            risk_data: Risk management data
            
        Returns:
            AI prediction with recommendation
        """
        try:
            # Build comprehensive prompt
            prompt = self._build_prediction_prompt(
                symbol, current_price, mode, technical_indicators,
                sentiment_data, ml_prediction, risk_data
            )
            
            # Build price history prompt if available
            price_prompt = ""
            if price_history is not None and not price_history.empty:
                recent_prices = price_history.tail(20)
                price_list = []
                for idx, row in recent_prices.iterrows():
                    price_list.append(f"₹{row['Close']:.2f}")
                price_prompt = f"\nRecent Price History (last 20 periods): {', '.join(price_list)}\n"
            
            prediction_data = None
            ai_model = "Fallback Algorithm"
            source = "fallback"

            # Primary: Groq for richer explanatory output.
            ai_response, used_groq_model = self._call_groq(prompt + price_prompt)
            if ai_response:
                prediction_data = self._extract_json(ai_response)
                ai_model = f"Groq ({used_groq_model})"
                source = "api"

            if not prediction_data:
                return self._create_fallback_prediction(
                    technical_indicators, sentiment_data, ml_prediction, price_history, mode
                )

            chart_data = self._generate_chart_data(
                price_history, prediction_data.get("predicted_prices", []), mode
            )
            normalized_predicted_prices = self._normalize_predicted_prices(
                prediction_data.get("predicted_prices", [])
            )
            transparency = self._build_transparency(
                symbol=symbol,
                technical_indicators=technical_indicators,
                sentiment_data=sentiment_data,
                ml_prediction=ml_prediction,
                risk_data=risk_data,
                model_prediction=prediction_data
            )

            return {
                "ai_prediction": prediction_data.get("prediction", "NEUTRAL"),
                "confidence": prediction_data.get("confidence", 50),
                "reasoning": prediction_data.get("reasoning", ""),
                "key_factors": prediction_data.get("key_factors", []),
                "risk_level": prediction_data.get("risk_level", "MEDIUM"),
                "recommendation": prediction_data.get("recommendation", "HOLD"),
                "price_target": self._clean_float(prediction_data.get("price_target")),
                "stop_loss": self._clean_float(prediction_data.get("stop_loss")),
                "predicted_prices": normalized_predicted_prices,
                "chart_data": chart_data,
                "disclaimer": prediction_data.get("disclaimer", "This is not financial advice."),
                "ai_model": ai_model,
                "source": source,
                "transparency": transparency
            }
                
        except Exception as e:
            print(f"AI Prediction error: {e}")
            return self._create_fallback_prediction(
                technical_indicators, sentiment_data, ml_prediction, price_history, mode
            )

    def _call_groq(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        """Call Groq with model fallback and return (output, model_used)."""
        if not self.groq_api_key:
            return None, None

        # Try user-selected model first, then latest known safe fallbacks.
        models_to_try = []
        for candidate in self.model_candidates:
            if candidate not in models_to_try:
                models_to_try.append(candidate)
        if self.model and self.model not in models_to_try:
            models_to_try.append(self.model)

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }

        for model_name in models_to_try:
            try:
                payload = {
                    "model": model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a professional stock market analyst. "
                                "Return ONLY valid JSON with keys: prediction, confidence, reasoning, key_factors, "
                                "risk_level, recommendation, price_target, stop_loss, predicted_prices, "
                                "geopolitical_scenarios, disclaimer."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1200
                }

                # Strict timeout: 8s for first model, 5s for fallbacks
                timeout = 8 if model_name == models_to_try[0] else 5
                response = None
                for attempt in range(3):
                    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
                    if response.status_code != 429:
                        break
                    print(f"Groq ({model_name}): Rate limited (429), retrying in 2s ({attempt + 1}/3)...")
                    time.sleep(2)

                if response is None or response.status_code != 200:
                    print(f"Groq API error ({model_name}): {response.status_code if response else 'no response'} - {(response.text[:200] if response is not None else '')}")
                    continue

                result = response.json()
                choices = result.get("choices", [])
                if not choices:
                    continue

                text = choices[0].get("message", {}).get("content")
                if text:
                    print(f"Groq ({model_name}): Success")
                    return text, model_name
            except requests.Timeout:
                print(f"Groq ({model_name}): Timeout")
                continue
            except Exception as e:
                print(f"Groq ({model_name}): Error - {str(e)[:50]}")
                continue

        return None, None

    def _extract_json(self, model_output: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from model output, supporting fenced responses."""
        text = (model_output or "").strip()
        if not text:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Handle markdown fenced JSON responses.
        if "```" in text:
            text = text.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None

        return None
    
    def _build_prediction_prompt(
        self,
        symbol: str,
        current_price: float,
        mode: str,
        technical_indicators: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        ml_prediction: Dict[str, Any],
        risk_data: Dict[str, Any]
    ) -> str:
        """Build comprehensive prompt for AI"""
        
        prompt = f"""Analyze the following stock data for {symbol} at current price ₹{current_price}:

ANALYSIS MODE: {mode.upper()}

TECHNICAL INDICATORS:
"""
        
        # Add technical indicators
        prompt += f"- Trend: {technical_indicators.get('trend', 'Unknown')}\n"
        prompt += f"- RSI: {technical_indicators.get('rsi_value', 'N/A')} ({technical_indicators.get('rsi_interpretation', 'Unknown')})\n"
        prompt += f"- MACD: {technical_indicators.get('macd_value', 'N/A')}\n"
        prompt += f"- MACD Signal: {technical_indicators.get('macd_signal', 'N/A')}\n"
        prompt += f"- MACD Histogram: {technical_indicators.get('macd_histogram', 'N/A')}\n"
        prompt += f"- ATR: {technical_indicators.get('atr', 'N/A')}\n"
        
        # Add EMA data if available
        if 'ema_9' in technical_indicators and 'ema_21' in technical_indicators:
            prompt += f"- EMA 9: {technical_indicators['ema_9']}\n"
            prompt += f"- EMA 21: {technical_indicators['ema_21']}\n"
        elif 'ema_20' in technical_indicators and 'ema_50' in technical_indicators:
            prompt += f"- EMA 20: {technical_indicators['ema_20']}\n"
            prompt += f"- EMA 50: {technical_indicators['ema_50']}\n"
            if 'ema_200' in technical_indicators:
                prompt += f"- EMA 200: {technical_indicators['ema_200']}\n"
        
        if 'bb_position' in technical_indicators:
            prompt += f"- Bollinger Band Position: {technical_indicators['bb_position']}\n"
        
        if 'support' in technical_indicators and 'resistance' in technical_indicators:
            prompt += f"- Support Level: ₹{technical_indicators['support']}\n"
            prompt += f"- Resistance Level: ₹{technical_indicators['resistance']}\n"
        
        if 'volatility' in technical_indicators:
            prompt += f"- Volatility: {technical_indicators['volatility']}%\n"
        
        # Add sentiment data
        prompt += f"""
SENTIMENT ANALYSIS:
- Overall Sentiment: {sentiment_data.get('sentiment_classification', 'Unknown')}
- Sentiment Score: {sentiment_data.get('sentiment_score', 0)}
- Headlines Analyzed: {sentiment_data.get('headlines_count', 0)}
- Positive Headlines: {sentiment_data.get('breakdown', {}).get('positive', 0)}
- Negative Headlines: {sentiment_data.get('breakdown', {}).get('negative', 0)}
- Neutral Headlines: {sentiment_data.get('breakdown', {}).get('neutral', 0)}
"""
        
        # Add ML prediction
        prompt += f"""
MACHINE LEARNING PREDICTION:
- ML Up Probability: {ml_prediction.get('up_probability', 'N/A')}%
- ML Prediction: {ml_prediction.get('prediction', 'Unknown')}
- ML Confidence: {ml_prediction.get('confidence', 'Low')}
- Model Trained: {ml_prediction.get('model_trained', False)}
"""
        
        # Add risk data
        if risk_data:
            prompt += f"""
RISK MANAGEMENT:
- Risk Level: {risk_data.get('risk_level', 'Unknown')}
- Stop Loss: {risk_data.get('stop_loss', {}).get('stop_loss_price', 'N/A')}
- Stop Loss %: {risk_data.get('stop_loss', {}).get('stop_loss_percent', 'N/A')}%
- Take Profit: {risk_data.get('take_profit', {}).get('take_profit_price', 'N/A')}
- Risk-Reward Ratio: 1:{risk_data.get('take_profit', {}).get('risk_reward_ratio', 'N/A')}
"""
        
        prompt += """
Please provide:
1. Overall prediction (UP, DOWN, or NEUTRAL)
2. Confidence level (0-100)
3. Detailed reasoning based on all factors
4. Key factors that influenced your decision
5. Risk level (LOW, MEDIUM, HIGH)
6. Specific recommendation
7. Price target
8. Stop loss recommendation
9. Geopolitical scenarios impacting this stock right now (list 2-5 concise points)
10. Important disclaimer
 
Respond in JSON format."""
        
        return prompt

    def _clean_float(self, value: Any) -> Optional[float]:
        """Convert a value to a finite float, otherwise return None."""
        try:
            cleaned = float(value)
            if math.isnan(cleaned) or math.isinf(cleaned):
                return None
            return cleaned
        except (TypeError, ValueError):
            return None

    def _safe_round(self, value: Any, digits: int = 2) -> Optional[float]:
        cleaned = self._clean_float(value)
        return round(cleaned, digits) if cleaned is not None else None

    def _normalize_predicted_prices(self, predicted_prices: Any) -> List[float]:
        """Normalize predicted prices to finite rounded floats."""
        if not isinstance(predicted_prices, list):
            return []

        normalized: List[float] = []
        for price in predicted_prices:
            rounded = self._safe_round(price, 2)
            if rounded is not None:
                normalized.append(rounded)
        return normalized

    def _extract_geopolitical_scenarios(
        self,
        sentiment_data: Dict[str, Any],
        model_prediction: Dict[str, Any]
    ) -> List[str]:
        """Extract explicit and inferred geopolitical factors impacting the prediction."""
        scenarios = model_prediction.get("geopolitical_scenarios", [])
        if isinstance(scenarios, str) and scenarios.strip():
            scenarios = [scenarios.strip()]
        if isinstance(scenarios, list):
            cleaned = [str(s).strip() for s in scenarios if str(s).strip()]
            if cleaned:
                return cleaned[:5]

        inferred: List[str] = []
        geopolitics_keywords = {
            "war": "Global conflict risk affecting risk appetite and commodity prices",
            "sanction": "Sanctions risk impacting supply chains and exports",
            "oil": "Crude oil volatility affecting inflation and margins",
            "opec": "OPEC supply policy affecting energy-sensitive sectors",
            "china": "China demand and policy shifts affecting global growth expectations",
            "fed": "US Federal Reserve policy affecting global liquidity and valuation multiples",
            "rbi": "RBI policy stance affecting domestic rates and banking liquidity",
            "election": "Election and policy uncertainty affecting short-term market positioning"
        }
        for article in sentiment_data.get("news_articles", [])[:10]:
            title = str(article.get("title", "")).lower() if isinstance(article, dict) else ""
            for keyword, meaning in geopolitics_keywords.items():
                if keyword in title and meaning not in inferred:
                    inferred.append(meaning)
        return inferred[:5]

    def _build_transparency(
        self,
        symbol: str,
        technical_indicators: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        ml_prediction: Dict[str, Any],
        risk_data: Dict[str, Any],
        model_prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build transparent explanation payload for UI and API consumers."""
        article_drivers: List[Dict[str, str]] = []
        for article in sentiment_data.get("news_articles", [])[:3]:
            if not isinstance(article, dict):
                continue
            title = str(article.get("title", "")).strip()
            if not title:
                continue
            article_drivers.append({
                "title": title,
                "source": str(article.get("source", "Unknown")).strip() or "Unknown",
                "published_at": str(article.get("published_at", "")).strip(),
                "url": str(article.get("url", "")).strip()
            })

        trend_signal = str(technical_indicators.get("trend", "Unknown"))
        market_trend_signals = [
            {
                "factor": "Trend",
                "value": trend_signal,
                "impact": "Bullish trend supports upside probability" if "Bullish" in trend_signal else (
                    "Bearish trend increases downside risk" if "Bearish" in trend_signal else "Mixed trend signal"
                )
            },
            {
                "factor": "RSI",
                "value": str(technical_indicators.get("rsi_value", "N/A")),
                "impact": str(technical_indicators.get("rsi_interpretation", "Momentum is neutral"))
            },
            {
                "factor": "MACD Histogram",
                "value": str(technical_indicators.get("macd_histogram", "N/A")),
                "impact": "Positive momentum confirmation" if self._clean_float(technical_indicators.get("macd_histogram")) and self._clean_float(technical_indicators.get("macd_histogram")) > 0 else "Momentum caution"
            },
            {
                "factor": "ML Up Probability",
                "value": f"{ml_prediction.get('up_probability', 'N/A')}%",
                "impact": f"Model leans {ml_prediction.get('prediction', 'Neutral')}"
            }
        ]

        summary = str(model_prediction.get("reasoning", "")).strip()
        if not summary:
            summary = "Prediction blends technical trend, momentum, sentiment, and ML probability."

        return {
            "symbol": symbol,
            "summary": summary,
            "article_drivers": article_drivers,
            "geopolitical_scenarios": self._extract_geopolitical_scenarios(sentiment_data, model_prediction),
            "market_trend_signals": market_trend_signals,
            "risk_context": {
                "risk_level": str(risk_data.get("risk_level", "MEDIUM")),
                "stop_loss_percent": risk_data.get("stop_loss", {}).get("stop_loss_percent")
            },
            "guide_terms": [
                {"term": "RSI", "meaning": "Momentum indicator; above 70 can be overbought, below 30 can be oversold."},
                {"term": "MACD", "meaning": "Trend-momentum signal; rising histogram can indicate strengthening momentum."},
                {"term": "Support/Resistance", "meaning": "Key demand/supply zones where price often reacts."},
                {"term": "Confidence", "meaning": "Model certainty score, not a guarantee of outcome."},
                {"term": "Risk Level", "meaning": "Estimated downside uncertainty based on volatility and signal quality."}
            ]
        }
    
    def _generate_chart_data(
        self,
        price_history: Optional[pd.DataFrame],
        predicted_prices: List[float],
        mode: str
    ) -> Dict[str, Any]:
        """Generate chart data with historical and predicted prices"""
        
        chart_data = {
            "labels": [],
            "historical": [],
            "predicted": [],
            "current_price": None
        }
        
        if price_history is not None and not price_history.empty:
            # Get last 30 historical data points
            recent_data = price_history.tail(30)
            
            for idx, row in recent_data.iterrows():
                # Format date based on mode
                if mode == 'intraday':
                    label = idx.strftime('%H:%M')
                else:
                    label = idx.strftime('%d-%b')

                close_value = self._safe_round(row['Close'], 2)
                if close_value is None:
                    continue

                chart_data["labels"].append(label)
                chart_data["historical"].append(close_value)

            if chart_data["historical"]:
                chart_data["current_price"] = chart_data["historical"][-1]
            
            # Add predicted prices
            if predicted_prices:
                # Generate labels for predicted periods
                last_date = recent_data.index[-1]
                
                for i, price in enumerate(predicted_prices):
                    if mode == 'intraday':
                        # Next 5 time periods (5m intervals)
                        next_date = last_date + timedelta(minutes=5 * (i + 1))
                        label = next_date.strftime('%H:%M')
                    elif mode == 'swing':
                        # Next 5 days
                        next_date = last_date + timedelta(days=i + 1)
                        label = next_date.strftime('%d-%b')
                    else:  # longterm
                        # Next 5 weeks
                        next_date = last_date + timedelta(weeks=i + 1)
                        label = next_date.strftime('%d-%b')

                    rounded_price = self._safe_round(price, 2)
                    if rounded_price is None:
                        continue

                    chart_data["labels"].append(f"Pred {label}")
                    chart_data["predicted"].append(rounded_price)
        
        return chart_data
    
    def _create_fallback_prediction(
        self,
        technical_indicators: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        ml_prediction: Dict[str, Any],
        price_history: Optional[pd.DataFrame] = None,
        mode: str = "swing"
    ) -> Dict[str, Any]:
        """Create fallback prediction based on available data with balanced scoring"""
        
        # Determine prediction based on trend and ML
        trend = technical_indicators.get('trend', 'Neutral')
        ml_pred = ml_prediction.get('prediction', 'Neutral')
        sentiment = sentiment_data.get('sentiment_classification', 'Neutral')
        current_price = technical_indicators.get('current_price', 0)
        
        # Weighted scoring system - requires stronger consensus
        bullish_score = 0
        bearish_score = 0
        reasons = []
        
        # Trend analysis (highest weight)
        if 'Strong Bullish' in trend:
            bullish_score += 3
            reasons.append("Strong bullish trend")
        elif 'Bullish' in trend:
            bullish_score += 2
            reasons.append("Bullish trend detected")
        elif 'Strong Bearish' in trend:
            bearish_score += 3
            reasons.append("Strong bearish trend")
        elif 'Bearish' in trend:
            bearish_score += 2
            reasons.append("Bearish trend detected")
        
        # RSI analysis - counter-trend signals
        rsi = technical_indicators.get('rsi_value', 50)
        if rsi > 70:
            bearish_score += 1
            reasons.append("RSI overbought - potential reversal down")
        elif rsi < 30:
            bullish_score += 1
            reasons.append("RSI oversold - potential bounce up")
        elif rsi > 60:
            bullish_score += 0.5
            reasons.append("RSI showing strength")
        elif rsi < 40:
            bearish_score += 0.5
            reasons.append("RSI showing weakness")
        
        # ML prediction
        if ml_pred == 'Up':
            bullish_score += 1.5
            reasons.append("ML model predicts upward movement")
        elif ml_pred == 'Down':
            bearish_score += 1.5
            reasons.append("ML model predicts downward movement")
        
        # Sentiment (lower weight to avoid bias)
        if sentiment == 'Positive':
            bullish_score += 0.5
            reasons.append("Positive news sentiment")
        elif sentiment == 'Negative':
            bearish_score += 0.5
            reasons.append("Negative news sentiment")
        
        # MACD momentum
        macd_hist = technical_indicators.get('macd_histogram', 0)
        if macd_hist > 0:
            bullish_score += 0.5
        elif macd_hist < 0:
            bearish_score += 0.5
        
        # Determine final prediction - require at least 2 point advantage
        net_score = bullish_score - bearish_score
        total_signals = bullish_score + bearish_score
        
        if total_signals == 0:
            prediction = "NEUTRAL"
            confidence = 50
        elif net_score >= 2:
            prediction = "UP"
            confidence = min(45 + net_score * 8, 85)
        elif net_score <= -2:
            prediction = "DOWN"
            confidence = min(45 + abs(net_score) * 8, 85)
        else:
            prediction = "NEUTRAL"
            confidence = 50 + int(abs(net_score) * 10)
        
        # Determine risk level based on signal strength and agreement
        signal_strength = max(bullish_score, bearish_score)
        if signal_strength >= 4 or abs(net_score) >= 3:
            risk_level = "HIGH"  # Strong conviction = higher risk if wrong
        elif signal_strength >= 2 or abs(net_score) >= 1.5:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Create recommendation
        if prediction == "UP":
            recommendation = "Consider buying with proper stop loss"
        elif prediction == "DOWN":
            recommendation = "Consider selling or avoid new positions"
        else:
            recommendation = "Hold current positions, wait for clearer signals"
        
        # Generate predicted prices based on trend
        predicted_prices = []
        if current_price > 0:
            if prediction == "UP":
                # Predict gradual increase
                for i in range(1, 6):
                    change = (confidence / 100) * 0.02 * i  # Up to 2% per period
                    predicted_prices.append(current_price * (1 + change))
            elif prediction == "DOWN":
                # Predict gradual decrease
                for i in range(1, 6):
                    change = (confidence / 100) * 0.02 * i  # Up to 2% per period
                    predicted_prices.append(current_price * (1 - change))
            else:
                # Predict slight variation
                for i in range(1, 6):
                    predicted_prices.append(current_price * (1 + (i - 3) * 0.005))
        
        # Generate chart data
        chart_data = self._generate_chart_data(price_history, predicted_prices, mode)
        
        return {
            "ai_prediction": prediction,
            "confidence": confidence,
            "reasoning": f"Based on analysis of {len(reasons)} key factors: " + ", ".join(reasons),
            "key_factors": reasons,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "price_target": self._safe_round(predicted_prices[-1], 2) if predicted_prices else None,
            "stop_loss": None,
            "predicted_prices": self._normalize_predicted_prices(predicted_prices),
            "chart_data": chart_data,
            "disclaimer": "This prediction is based on automated analysis and should not be considered as financial advice. Stock market investments carry significant risks. Please consult a SEBI-registered financial advisor before making any investment decisions.",
            "ai_model": "Fallback Algorithm",
            "source": "fallback",
            "transparency": self._build_transparency(
                symbol=sentiment_data.get("symbol", "UNKNOWN"),
                technical_indicators=technical_indicators,
                sentiment_data=sentiment_data,
                ml_prediction=ml_prediction,
                risk_data={},
                model_prediction={
                    "reasoning": f"Based on analysis of {len(reasons)} key factors: " + ", ".join(reasons),
                    "geopolitical_scenarios": []
                }
            )
        }


# Initialize global AI predictor instance
ai_predictor = AIStockPredictor()
