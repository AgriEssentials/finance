"""
Specialized agents for the PS-01 multi-agent system.

Each agent has a defined role and returns a fixed `AgentOutput` structured
contract. Agents run independently so the orchestrator can dispatch them in
parallel. Every agent fails gracefully: an exception produces a `degraded`
output instead of crashing the pipeline (PS-01 degraded-data requirement).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.agents.contracts import AgentOutput, Citation
from app.agents import rag


class _BaseAgent:
    """Base class providing timing + safe output construction."""

    agent_id = "base"
    agent_name = "Base Agent"
    role = "Base role"

    def _make(self, score: float, recommendation: str, confidence: float,
              summary: str, key_factors: List[str], evidence: Dict[str, Any],
              citations: Optional[List[Citation]] = None,
              status: str = "ok", error: Optional[str] = None, start: float = 0.0) -> AgentOutput:
        return AgentOutput(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            role=self.role,
            status=status,
            latency_ms=(time.time() - start) * 1000,
            confidence=confidence,
            score=score,
            recommendation=recommendation,
            summary=summary,
            key_factors=key_factors,
            evidence=evidence,
            citations=citations or [],
            error=error,
        )

    def _signal(self, score: float) -> str:
        """Map a 0-100 score to a directional recommendation."""
        if score >= 60:
            return "BUY"
        if score <= 40:
            return "SELL"
        return "HOLD"


class MomentumAgent(_BaseAgent):
    """Dimension 1: price momentum."""

    agent_id = "momentum"
    agent_name = "Price Momentum Agent"
    role = "Evaluates price momentum across RSI, MACD and trend structure."

    def run(self, ctx: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        try:
            tech = ctx["technical"]
            basic = tech.get("basic", {})
            score = 50.0
            factors: List[str] = []

            trend = basic.get("trend", "Neutral")
            rsi = float(basic.get("rsi", 50) or 50)
            macd = float(basic.get("macd", 0) or 0)
            macd_signal = float(basic.get("macd_signal", 0) or 0)

            if "Strong Bullish" in trend:
                score += 20
            elif "Bullish" in trend:
                score += 10
            elif "Strong Bearish" in trend:
                score -= 20
            elif "Bearish" in trend:
                score -= 10

            if rsi >= 70:
                score -= 8
                factors.append(f"RSI {rsi:.1f} overbought - momentum may be stretched")
            elif rsi <= 30:
                score += 6
                factors.append(f"RSI {rsi:.1f} oversold - potential mean-reversion bounce")
            else:
                factors.append(f"RSI {rsi:.1f} in neutral zone")

            if macd > macd_signal:
                score += 10
                factors.append(f"MACD {macd:.2f} above signal {macd_signal:.2f} - bullish momentum")
            else:
                score -= 8
                factors.append(f"MACD {macd:.2f} below signal {macd_signal:.2f} - bearish momentum")

            factors.insert(0, f"Trend: {trend}")
            score = max(0, min(100, score))
            rec = self._signal(score)
            conf = min(95, 50 + abs(score - 50) * 0.9)
            return self._make(
                score=score,
                recommendation=rec,
                confidence=conf,
                summary=f"Price momentum is {rec.lower()} with a composite momentum score of {score:.0f}/100.",
                key_factors=factors,
                evidence={"trend": trend, "rsi": rsi, "macd": macd, "macd_signal": macd_signal},
                start=start,
            )
        except Exception as exc:  # noqa: BLE001
            return self._make(50, "HOLD", 0, f"Momentum data unavailable: {exc}", [],
                              {}, status="degraded", error=str(exc), start=start)


class VolumeAnomalyAgent(_BaseAgent):
    """Dimension 2: volume anomaly."""

    agent_id = "volume"
    agent_name = "Volume Anomaly Agent"
    role = "Detects abnormal volume, volume spikes and volume-price confirmation."

    def run(self, ctx: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        try:
            tech = ctx["technical"]
            basic = tech.get("basic", {})
            score = 50.0
            factors: List[str] = []

            volume_ratio = float(basic.get("volume_ratio", 1.0) or 1.0)
            volume_spike = bool(basic.get("volume_spike", volume_ratio >= 1.5))
            price_change_pct = float(ctx.get("price_change_pct", 0.0) or 0.0)

            if volume_spike:
                score += 15
                factors.append(f"Volume spike detected ({volume_ratio:.1f}x 20-day average)")
            elif volume_ratio > 1.2:
                score += 6
                factors.append(f"Above-average volume ({volume_ratio:.1f}x) - institutional interest")
            elif volume_ratio < 0.7:
                score -= 5
                factors.append(f"Low volume ({volume_ratio:.1f}x) - thin participation")

            # Price-volume confirmation
            if price_change_pct > 1.0 and volume_ratio >= 1.2:
                score += 10
                factors.append(f"Price +{price_change_pct:.1f}% on strong volume - bullish confirmation")
            elif price_change_pct < -1.0 and volume_ratio >= 1.2:
                score -= 10
                factors.append(f"Price {price_change_pct:.1f}% on strong volume - bearish distribution")

            score = max(0, min(100, score))
            rec = self._signal(score)
            conf = min(90, 40 + abs(score - 50) * 0.8)
            return self._make(
                score=score,
                recommendation=rec,
                confidence=conf,
                summary=f"Volume anomaly assessment: {rec.lower()} with volume ratio {volume_ratio:.1f}x.",
                key_factors=factors,
                evidence={"volume_ratio": volume_ratio, "volume_spike": volume_spike,
                          "price_change_pct": price_change_pct},
                start=start,
            )
        except Exception as exc:  # noqa: BLE001
            return self._make(50, "HOLD", 0, f"Volume data unavailable: {exc}", [],
                              {}, status="degraded", error=str(exc), start=start)


class SentimentAgent(_BaseAgent):
    """Dimension 3: news sentiment."""

    agent_id = "sentiment"
    agent_name = "News Sentiment Agent"
    role = "Aggregates multi-source news sentiment with cited article attribution."

    def run(self, ctx: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        try:
            from app.sentiment import sentiment_analyzer

            symbol = ctx["symbol"]
            data = sentiment_analyzer.get_sentiment_for_stock(symbol, use_cache=True)
            sent_score = float(data.get("sentiment_score", 0) or 0)
            classification = data.get("sentiment_classification", "Neutral")

            score = 50 + (sent_score * 50)
            score = max(0, min(100, score))
            rec = self._signal(score)

            factors = [
                f"Sentiment score {sent_score:+.2f} ({classification})",
                f"Based on {data.get('articles_count', 0)} articles",
            ]
            breakdown = data.get("breakdown", {})
            if isinstance(breakdown, dict):
                factors.append(
                    f"Breakdown: {breakdown.get('positive', 0)} positive / "
                    f"{breakdown.get('negative', 0)} negative / {breakdown.get('neutral', 0)} neutral"
                )

            citations: List[Citation] = []
            for art in (data.get("news_articles", []) or [])[:4]:
                if isinstance(art, dict) and art.get("title"):
                    citations.append(Citation(
                        source_id=f"news:{symbol}:{abs(hash(art.get('title', '')))}",
                        title=art.get("title", ""),
                        source=art.get("source", "News"),
                        url=art.get("url"),
                        published_at=art.get("published_at"),
                        doc_type="news",
                        relevance_score=float(art.get("impact_score", 0.5) or 0.5),
                        snippet=art.get("title", "")[:300],
                        symbol=symbol,
                    ))

            conf = min(95, 45 + abs(sent_score) * 50)
            return self._make(
                score=score,
                recommendation=rec,
                confidence=conf,
                summary=f"News sentiment is {classification.lower()} (score {sent_score:+.2f}).",
                key_factors=factors,
                evidence={"sentiment_score": sent_score, "classification": classification,
                          "articles_count": data.get("articles_count", 0)},
                citations=citations,
                start=start,
            )
        except Exception as exc:  # noqa: BLE001
            return self._make(50, "HOLD", 0, f"Sentiment feed unavailable: {exc}", [],
                              {}, status="degraded", error=str(exc), start=start)


class FundamentalAgent(_BaseAgent):
    """Dimension 4: fundamentals."""

    agent_id = "fundamental"
    agent_name = "Fundamental Agent"
    role = "Assesses financial health, valuation and earnings quality."

    def run(self, ctx: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        try:
            from app.fundamental_analysis import FundamentalAnalyzer

            symbol = ctx["symbol"]
            analyzer = FundamentalAnalyzer(symbol)
            data = analyzer.get_complete_fundamental_analysis()

            if "error" in data:
                raise RuntimeError(data["error"])

            health = data.get("financial_health", {}) or {}
            health_pct = float(health.get("health_percentage", 50) or 50)
            score = max(0, min(100, health_pct))
            rec = self._signal(score)

            factors = [f"Financial health score {health_pct:.0f}/100"]
            metrics = data.get("metrics", {}) or {}
            for k in ("pe_ratio", "roe", "debt_to_equity", "profit_margin", "revenue_growth"):
                if metrics.get(k) is not None:
                    factors.append(f"{k}: {metrics[k]}")
            if len(factors) == 1:
                factors.append("Fundamental metrics unavailable - using health score only")

            conf = min(90, 40 + abs(score - 50) * 0.8)
            return self._make(
                score=score,
                recommendation=rec,
                confidence=conf,
                summary=f"Fundamental assessment: financial health {health_pct:.0f}/100.",
                key_factors=factors,
                evidence={"health_percentage": health_pct,
                          "valuation": data.get("valuation_assessment", {}),
                          "metrics": metrics},
                start=start,
            )
        except Exception as exc:  # noqa: BLE001
            return self._make(50, "HOLD", 0, f"Fundamental data unavailable: {exc}", [],
                              {}, status="degraded", error=str(exc), start=start)


class MLAgent(_BaseAgent):
    """Dimension 5: machine-learning probability."""

    agent_id = "ml"
    agent_name = "Machine Learning Agent"
    role = "Applies trained classifiers to estimate the probability of upward movement."

    def run(self, ctx: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        try:
            from app.indicators import prepare_ml_features
            from app.ml_model import predictors

            df = ctx["df"]
            mode = ctx["mode"]
            features = prepare_ml_features(df, mode)
            predictor = predictors.get(mode, predictors["swing"])
            result = predictor.predict(features.iloc[-1:])

            up_prob = float(result.get("up_probability", 50) or 50)
            score = max(0, min(100, up_prob))
            rec = self._signal(score)
            conf_str = result.get("confidence", "Low")
            conf_map = {"Very High": 90, "High": 75, "Medium": 60, "Low": 45}
            conf = conf_map.get(str(conf_str), 55)
            if not result.get("model_trained", False):
                conf = min(conf, 40)

            return self._make(
                score=score,
                recommendation=rec,
                confidence=conf,
                summary=f"ML model estimates {up_prob:.1f}% probability of upward movement.",
                key_factors=[f"Up probability {up_prob:.1f}%",
                             f"Confidence: {conf_str}",
                             "Trained on historical price features (RSI, MACD, volume, ATR, EMA)"],
                evidence={"up_probability": up_prob, "prediction": result.get("prediction"),
                          "confidence": conf_str, "model_trained": result.get("model_trained", False)},
                start=start,
            )
        except Exception as exc:  # noqa: BLE001
            return self._make(50, "HOLD", 0, f"ML model unavailable: {exc}", [],
                              {}, status="degraded", error=str(exc), start=start)


class RiskAgent(_BaseAgent):
    """Dimension 6: risk."""

    agent_id = "risk"
    agent_name = "Risk Manager Agent"
    role = "Computes ATR-based stop-loss, volatility regime and portfolio concentration risk."

    def run(self, ctx: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        try:
            from app.risk_manager import RiskManager

            tech = ctx["technical"]
            basic = tech.get("basic", {})
            indicators = {
                "atr": float(basic.get("atr", 0) or 0),
                "trend": basic.get("trend", "Neutral"),
                "rsi": float(basic.get("rsi", 50) or 50),
                "sentiment_score": 0,
            }
            risk_mgr = RiskManager(indicators)
            entry = float(ctx.get("current_price", 0) or 0)
            risk = risk_mgr.get_full_risk_assessment(entry)

            risk_level = risk.get("risk_level", "Medium")
            level_map = {"Low": 78, "Medium": 55, "High": 30}
            score = float(level_map.get(risk_level, 50))
            rec = self._signal(score)

            stop_loss = risk.get("stop_loss", {})
            position = risk.get("position_sizing", {})

            factors = [
                f"Risk level: {risk_level}",
                f"ATR-based stop-loss: {stop_loss.get('stop_loss_percent', 'N/A')}%",
                f"Suggested position: {position.get('position_pct', 'N/A')}% of portfolio",
            ]
            concentration = float(ctx.get("risk_concentration", 0.0) or 0.0)
            if concentration > 0:
                if concentration > 0.4:
                    factors.append(f"Portfolio concentration {concentration:.2f} - high single-stock risk")
                    score -= 8
                elif concentration > 0.25:
                    factors.append(f"Portfolio concentration {concentration:.2f} - moderate")
                    score -= 3
                else:
                    factors.append(f"Portfolio concentration {concentration:.2f} - well diversified")

            score = max(0, min(100, score))
            conf = 70.0
            return self._make(
                score=score,
                recommendation=rec,
                confidence=conf,
                summary=f"Risk assessment: {risk_level} risk with stop-loss at {stop_loss.get('stop_loss_percent', 'N/A')}%.",
                key_factors=factors,
                evidence={"risk_level": risk_level, "stop_loss": stop_loss,
                          "position_sizing": position, "risk_concentration": concentration},
                start=start,
            )
        except Exception as exc:  # noqa: BLE001
            return self._make(50, "HOLD", 0, f"Risk calculation unavailable: {exc}", [],
                              {}, status="degraded", error=str(exc), start=start)


class NewsGroundingAgent(_BaseAgent):
    """RAG agent: grounds output in retrieved source material with citations."""

    agent_id = "rag"
    agent_name = "News Grounding Agent (RAG)"
    role = "Retrieves relevant filings, announcements and news from the document corpus to ground the decision."

    def run(self, ctx: Dict[str, Any]) -> AgentOutput:
        start = time.time()
        try:
            symbol = ctx["symbol"]
            query = ctx.get("query") or f"{symbol} financial performance, results, announcements"
            citations = rag.ground_analysis(query, symbol=symbol, top_k=4)

            if not citations:
                raise RuntimeError("No documents retrieved from corpus")

            score = 50.0
            factors = [f"Retrieved {len(citations)} relevant documents from the corpus"]
            for c in citations[:3]:
                factors.append(f"[{c.source}] {c.title}")

            # Aggregate retrieval sentiment heuristically from snippets
            bull_terms = ("profit", "growth", "dividend", "buyback", "expansion", "strong", "record")
            bear_terms = ("loss", "decline", "down", "weak", "soft", "provision", "guidance cut")
            bull_hits = sum(1 for c in citations for t in bull_terms if t in c.snippet.lower())
            bear_hits = sum(1 for c in citations for t in bear_terms if t in c.snippet.lower())
            if bull_hits > bear_hits:
                score += 8
                factors.append("Retrieved disclosures skew positive")
            elif bear_hits > bull_hits:
                score -= 8
                factors.append("Retrieved disclosures skew negative")

            score = max(0, min(100, score))
            rec = self._signal(score)
            conf = min(80, 45 + len(citations) * 5)
            return self._make(
                score=score,
                recommendation=rec,
                confidence=conf,
                summary=f"Grounded in {len(citations)} retrieved sources: {rec.lower()} lean.",
                key_factors=factors,
                evidence={"retrieved_count": len(citations), "query": query},
                citations=citations,
                start=start,
            )
        except Exception as exc:  # noqa: BLE001
            return self._make(50, "HOLD", 0,
                              f"Retrieval unavailable - decision proceeds without grounding: {exc}",
                              ["Corpus retrieval degraded"], {}, status="degraded", error=str(exc),
                              start=start)


AGENT_CLASSES = [
    MomentumAgent,
    VolumeAnomalyAgent,
    SentimentAgent,
    FundamentalAgent,
    MLAgent,
    RiskAgent,
    NewsGroundingAgent,
]