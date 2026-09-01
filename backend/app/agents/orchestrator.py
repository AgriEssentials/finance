"""
Multi-agent orchestrator and synthesis layer for PS-01.

Dispatches specialized agents in parallel, collects their structured outputs
(including per-agent latency), and synthesizes a single explainable
recommendation with a full reasoning chain, source citations, user-profile
personalization and session performance logging.
"""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from app.agents.agents import AGENT_CLASSES
from app.agents.contracts import AgentOutput, PerformanceSnapshot, ReasoningStep, SynthesisOutput
from app.agents import performance as perf

AGENT_WEIGHTS = {
    "momentum": 0.20,
    "volume": 0.15,
    "sentiment": 0.20,
    "fundamental": 0.20,
    "ml": 0.15,
    "rag": 0.10,
}


class MultiAgentOrchestrator:
    """Runs the parallel agent team and synthesizes their outputs."""

    def __init__(self):
        self._agents = [cls() for cls in AGENT_CLASSES]

    @property
    def agent_roles(self) -> List[Dict[str, str]]:
        return [{"id": a.agent_id, "name": a.agent_name, "role": a.role} for a in self._agents]

    # ---- data preparation -------------------------------------------
    def _fetch_technical(self, symbol: str, mode: str) -> Dict[str, Any]:
        """Fetch price history + technical indicators (sequential prerequisite)."""
        import yfinance as yf

        from app.indicators import TechnicalIndicators

        ticker = yf.Ticker(symbol)
        if mode == "intraday":
            df = ticker.history(period="5d", interval="5m")
        elif mode == "longterm":
            df = ticker.history(period="2y", interval="1wk")
        else:
            df = ticker.history(period="6mo", interval="1d")
        if df.empty:
            raise ValueError(f"No market data found for symbol {symbol}")

        ti = TechnicalIndicators(df)
        if mode == "intraday":
            basic = ti.get_all_indicators_intraday()
        elif mode == "longterm":
            basic = ti.get_all_indicators_longterm()
        else:
            basic = ti.get_all_indicators_swing()

        price_change_pct = 0.0
        closes = df["Close"].dropna()
        if len(closes) >= 2:
            prev = float(closes.iloc[-2])
            curr = float(closes.iloc[-1])
            if prev:
                price_change_pct = (curr - prev) / prev * 100

        return {
            "df": ti.df,  # indicator-enhanced copy (RSI/MACD/ATR/EMA columns for the ML agent)
            "technical": {"basic": basic, "current_price": basic.get("current_price", 0)},
            "price_change_pct": price_change_pct,
        }

    def _load_user_profile(self, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not user_profile:
            return {"risk_tolerance": "medium", "preferred_strategy": "swing", "capital": 100000}
        return {
            "risk_tolerance": user_profile.get("risk_tolerance", "medium"),
            "preferred_strategy": user_profile.get("preferred_strategy", "swing"),
            "capital": float(user_profile.get("capital", 100000) or 100000),
        }

    def _risk_concentration(self, portfolio_context: Optional[Dict[str, Any]]) -> float:
        if not portfolio_context:
            return 0.0
        return perf.compute_risk_concentration(portfolio_context.get("holdings"))

    # ---- parallel dispatch ------------------------------------------
    _AGENT_TIMEOUTS = {
        "momentum": 30,
        "volume": 30,
        "sentiment": 70,
        "fundamental": 90,
        "ml": 45,
        "risk": 30,
        "rag": 60,
    }

    def _run_agents(self, ctx: Dict[str, Any]) -> List[AgentOutput]:
        outputs: List[AgentOutput] = []
        with ThreadPoolExecutor(max_workers=len(self._agents)) as executor:
            futures = {executor.submit(a.run, ctx): a for a in self._agents}
            for future in futures:
                agent = futures[future]
                timeout = self._AGENT_TIMEOUTS.get(agent.agent_id, 45)
                try:
                    outputs.append(future.result(timeout=timeout))
                except Exception as exc:  # noqa: BLE001
                    outputs.append(AgentOutput(
                        agent_id=agent.agent_id,
                        agent_name=agent.agent_name,
                        role=agent.role,
                        status="failed",
                        latency_ms=timeout * 1000,
                        confidence=0.0,
                        score=50.0,
                        recommendation="HOLD",
                        summary=f"Agent exceeded {timeout}s budget; pipeline proceeded without it.",
                        error=f"timeout({timeout}s): {exc}",
                    ))
        # Stable ordering for the trace viewer
        order = {a.agent_id: i for i, a in enumerate(self._agents)}
        outputs.sort(key=lambda o: order.get(o.agent_id, 99))
        return outputs

    # ---- synthesis ---------------------------------------------------
    def _synthesize(self, outputs: List[AgentOutput], ctx: Dict[str, Any],
                    profile: Dict[str, Any]) -> SynthesisOutput:
        by_id = {o.agent_id: o for o in outputs}
        available = [o for o in outputs if o.status == "ok"]
        degraded = [o.agent_id for o in outputs if o.status != "ok"]

        # Weighted composite over available agents (renormalized if some fail)
        weights = dict(AGENT_WEIGHTS)
        available_weight = sum(weights.get(o.agent_id, 0) for o in available)
        if available_weight <= 0:
            composite = 50.0
            composite_by_agent = {o.agent_id: o.score for o in outputs}
        else:
            composite = sum(
                weights.get(o.agent_id, 0) * o.score for o in available
            ) / available_weight
            composite_by_agent = {o.agent_id: o.score for o in available}

        # Risk adjustment
        risk = by_id.get("risk")
        if risk and risk.status == "ok":
            risk_level = (risk.evidence or {}).get("risk_level", "Medium")
            if risk_level == "High":
                composite -= 6
            elif risk_level == "Low":
                composite += 3

        # --- User profiling personalization (different outputs per profile) ---
        profile_used = dict(profile)
        personalization_notes: List[str] = []
        if profile["risk_tolerance"] == "low":
            composite = min(composite, 65)
            personalization_notes.append(
                f"Low risk tolerance ({profile['risk_tolerance']}) capped upside score at 65"
            )
        elif profile["risk_tolerance"] == "high":
            composite = min(composite, 92)
            personalization_notes.append(
                f"High risk tolerance ({profile['risk_tolerance']}) permits aggressive positioning"
            )
        else:
            personalization_notes.append(
                f"Medium risk tolerance: balanced stance maintained"
            )

        composite = max(0, min(100, composite))
        recommendation, action, conf = self._recommendation_from_score(composite)

        # Confidence from agent confidences + profile moderation
        agent_confs = [o.confidence for o in available if o.confidence]
        confidence = round(sum(agent_confs) / len(agent_confs), 1) if agent_confs else 50.0
        if profile["risk_tolerance"] == "low":
            confidence = round(confidence * 0.85, 1)

        # Position sizing from profile capital + risk
        position_sizing = self._position_sizing(ctx, profile, by_id)

        component_scores = {**composite_by_agent}
        component_scores["risk_adjusted_composite"] = round(composite, 1)

        reasoning_chain = self._build_reasoning_chain(outputs, by_id, composite,
                                                      recommendation, personalization_notes)
        citations = self._collect_citations(outputs)
        degraded = degraded + ([f"{o.agent_id}: {o.error}" for o in outputs if o.error])

        return SynthesisOutput(
            symbol=ctx["symbol"],
            mode=ctx["mode"],
            timestamp=datetime.now().isoformat(),
            recommendation=recommendation,
            action=action,
            confidence=confidence,
            composite_score=round(composite, 1),
            component_scores={k: round(v, 1) for k, v in component_scores.items()},
            reasoning_chain=reasoning_chain,
            agent_traces=outputs,
            citations=citations,
            degraded_data=degraded,
            user_profile_used=profile_used,
            position_sizing=position_sizing,
        )

    def _recommendation_from_score(self, score: float):
        if score >= 75:
            return "STRONG BUY", "Initiate full position in line with your risk profile", 90.0
        if score >= 62:
            return "BUY", "Initiate a partial position and add on confirmation", 80.0
        if score >= 50:
            return "MODERATE BUY", "Consider a small starter position", 65.0
        if score >= 40:
            return "HOLD", "Hold existing positions, avoid new entries", 60.0
        if score >= 25:
            return "REDUCE", "Reduce position size by 25-50%", 55.0
        return "SELL", "Exit position completely", 60.0

    def _position_sizing(self, ctx: Dict[str, Any], profile: Dict[str, Any],
                         by_id: Dict[str, AgentOutput]) -> Dict[str, Any]:
        try:
            technical = ctx["technical"]["basic"]
            atr = float(technical.get("atr", 0) or 0)
            price = float(ctx["technical"].get("current_price", 0) or 0)
            capital = profile["capital"]
            risk_pct_map = {"low": 0.5, "medium": 1.0, "high": 2.0}
            atr_mult_map = {"low": 1.0, "medium": 1.5, "high": 2.0}
            risk_pct = risk_pct_map.get(profile["risk_tolerance"], 1.0)
            atr_mult = atr_mult_map.get(profile["risk_tolerance"], 1.5)
            stop_pct = (atr * atr_mult / price * 100) if price and atr else 2.0
            risk_amount = capital * (risk_pct / 100)
            stop_amount = (stop_pct / 100) * price if price else 0
            shares = int(risk_amount / stop_amount) if stop_amount > 0 else 0
            return {
                "capital": round(capital, 2),
                "risk_per_trade_pct": risk_pct,
                "atr_multiplier": atr_mult,
                "stop_loss_pct": round(stop_pct, 2),
                "recommended_shares": max(shares, 0),
                "position_value": round(min(shares * price, capital), 2),
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc), "capital": profile.get("capital", 100000)}

    def _build_reasoning_chain(self, outputs: List[AgentOutput],
                               by_id: Dict[str, AgentOutput],
                               composite: float, recommendation: str,
                               personalization_notes: List[str]) -> List[ReasoningStep]:
        steps: List[ReasoningStep] = []
        steps.append(ReasoningStep(step=1, title="Ingest market data",
                                   detail="Fetched live price history and computed technical indicators "
                                          "for the symbol across the selected timeframe."))
        for idx, out in enumerate(outputs, start=2):
            status_note = " (degraded - fallback used)" if out.status != "ok" else ""
            steps.append(ReasoningStep(
                step=idx,
                title=f"{out.agent_name}",
                detail=f"{out.summary}{status_note} | Confidence {out.confidence:.0f}/100 | "
                       f"Score {out.score:.0f}/100 | Latency {out.latency_ms:.0f}ms",
            ))
        next_step = len(outputs) + 2
        for note in personalization_notes:
            steps.append(ReasoningStep(step=next_step, title="User profile personalization", detail=note))
            next_step += 1
        steps.append(ReasoningStep(
            step=next_step, title="Synthesis",
            detail=(f"Weighted composite {composite:.1f}/100 across momentum, volume, sentiment, "
                    f"fundamental, ML and RAG-grounding signals -> {recommendation}."),
        ))
        return steps

    def _collect_citations(self, outputs: List[AgentOutput]):
        seen = set()
        citations = []
        for out in outputs:
            for c in out.citations:
                if c.source_id in seen:
                    continue
                seen.add(c.source_id)
                citations.append(c)
        return citations

    # ---- main entry --------------------------------------------------
    def run_analysis(self, symbol: str, mode: str = "swing",
                     user_profile: Optional[Dict[str, Any]] = None,
                     portfolio_context: Optional[Dict[str, Any]] = None,
                     query: Optional[str] = None,
                     user_id: str = "demo") -> SynthesisOutput:
        start = time.time()
        ctx: Dict[str, Any] = {"symbol": symbol, "mode": mode, "query": query}

        profile = self._load_user_profile(user_profile)
        concentration = self._risk_concentration(portfolio_context)
        ctx["risk_concentration"] = concentration

        # 1. Raw data ingestion (sequential prerequisite)
        try:
            prepared = self._fetch_technical(symbol, mode)
        except Exception as exc:  # noqa: BLE001
            # Degraded-data scenario: no market feed. Build a fully-degraded result.
            outputs = [AgentOutput(
                agent_id="datafeed", agent_name="Market Data Agent", role="Raw data ingestion",
                status="degraded", confidence=0.0, score=50.0, recommendation="HOLD",
                summary=f"Market data feed unavailable: {exc}",
                error=str(exc),
            )]
            return self._finalize(symbol, mode, outputs, ctx, profile, concentration, start, user_id)

        ctx.update(prepared)
        ctx["current_price"] = prepared["technical"].get("current_price", 0)

        # 2. Parallel multi-agent reasoning
        outputs = self._run_agents(ctx)

        # 3. Synthesis
        synthesis = self._synthesize(outputs, ctx, profile)

        # 4. Persist + audit
        total_ms = (time.time() - start) * 1000
        latencies = {o.agent_id: o.latency_ms for o in outputs}
        session_id = perf.log_performance(
            user_id=user_id, symbol=symbol, signal_type=synthesis.recommendation,
            composite_score=synthesis.composite_score, confidence=synthesis.confidence,
            total_latency_ms=total_ms, agent_latencies_ms=latencies,
            risk_concentration_score=concentration,
            degraded_agents=[o.agent_id for o in outputs if o.status != "ok"],
        )
        synthesis.performance = PerformanceSnapshot(
            session_id=session_id, user_id=user_id, symbol=symbol,
            signal_type=synthesis.recommendation,
            composite_score=synthesis.composite_score, confidence=synthesis.confidence,
            total_latency_ms=round(total_ms, 1), agent_latencies_ms={k: round(v, 1) for k, v in latencies.items()},
            risk_concentration_score=concentration,
            degraded_agents=[o.agent_id for o in outputs if o.status != "ok"],
            recorded_at=datetime.now().isoformat(),
        )

        # Wire Veritas audit trail so the audit page has live data
        self._log_veritas(user_id, symbol, synthesis, ctx)
        return synthesis

    def _finalize(self, symbol: str, mode: str, outputs: List[AgentOutput],
                  ctx: Dict[str, Any], profile: Dict[str, Any],
                  concentration: float, start: float, user_id: str) -> SynthesisOutput:
        synthesis = self._synthesize(outputs, ctx, profile)
        total_ms = (time.time() - start) * 1000
        session_id = perf.log_performance(
            user_id=user_id, symbol=symbol, signal_type=synthesis.recommendation,
            composite_score=synthesis.composite_score, confidence=synthesis.confidence,
            total_latency_ms=total_ms,
            agent_latencies_ms={o.agent_id: o.latency_ms for o in outputs},
            risk_concentration_score=concentration,
            degraded_agents=[o.agent_id for o in outputs if o.status != "ok"],
        )
        synthesis.performance = PerformanceSnapshot(
            session_id=session_id, user_id=user_id, symbol=symbol,
            signal_type=synthesis.recommendation,
            composite_score=synthesis.composite_score, confidence=synthesis.confidence,
            total_latency_ms=round(total_ms, 1),
            agent_latencies_ms={o.agent_id: round(o.latency_ms, 1) for o in outputs},
            risk_concentration_score=concentration,
            degraded_agents=[o.agent_id for o in outputs if o.status != "ok"],
            recorded_at=datetime.now().isoformat(),
        )
        return synthesis

    def _log_veritas(self, user_id: str, symbol: str, synthesis: SynthesisOutput,
                     ctx: Dict[str, Any]):
        try:
            from app.veritas_audit import log_signal_for_user

            technical = ctx.get("technical", {}).get("basic", {})
            sentiment = None
            for out in synthesis.agent_traces:
                if out.agent_id == "sentiment" and out.status == "ok":
                    sentiment = {"sentiment_score": out.evidence.get("sentiment_score", 0),
                                 "news_articles": [c.dict() for c in out.citations]}
            signal_type = {"STRONG BUY": "buy", "MODERATE BUY": "buy"}.get(
                synthesis.recommendation, synthesis.recommendation.split(" ")[0]
            )
            log_signal_for_user(
                user_id=user_id,
                symbol=symbol,
                signal_type=signal_type,
                signal_source="ml_model",
                confidence=synthesis.confidence,
                technical_data=technical,
                sentiment_data=sentiment,
                market_context={"mode": ctx.get("mode"), "query": ctx.get("query")},
                portfolio_context={"risk_concentration": ctx.get("risk_concentration", 0.0)},
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[ORCHESTRATOR] Veritas logging skipped: {exc}")


_orchestrator: Optional[MultiAgentOrchestrator] = None


def get_orchestrator() -> MultiAgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator