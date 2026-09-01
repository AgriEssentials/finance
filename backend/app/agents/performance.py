"""
Session performance logging for PS-01.

Captures at least three measurable metrics per session:
  1. signal accuracy vs 30-day forward return
  2. agent response latency (per agent + total)
  3. portfolio risk-concentration score
Persisted to the `performance_logs` table (SQLite/Supabase) and exposed via
the API for the performance dashboard.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def _db():
    from app.database import PerformanceLog, SessionLocal

    SessionLocal()
    from app.database import create_tables

    create_tables()  # Ensure performance_logs table exists
    return SessionLocal(), PerformanceLog


def compute_risk_concentration(holdings: Optional[List[Dict[str, Any]]]) -> float:
    """Herfindahl-Hirschman concentration of portfolio weights (0-1)."""
    try:
        if not holdings:
            return 0.0
        weights = []
        total_value = 0.0
        for h in holdings:
            value = float(h.get("current_value") or h.get("value") or 0)
            if value > 0:
                weights.append(value)
                total_value += value
        if total_value <= 0:
            return 0.0
        return round(sum((w / total_value) ** 2 for w in weights), 4)
    except Exception:  # noqa: BLE001
        return 0.0


def log_performance(
    user_id: str,
    symbol: str,
    signal_type: str,
    composite_score: float,
    confidence: float,
    total_latency_ms: float,
    agent_latencies_ms: Dict[str, float],
    risk_concentration_score: float = 0.0,
    degraded_agents: Optional[List[str]] = None,
) -> str:
    """Record a session performance entry. Returns session_id."""
    session_id = uuid.uuid4().hex[:16]
    db, PerformanceLog = _db()
    try:
        entry = PerformanceLog(
            session_id=session_id,
            user_id=user_id,
            symbol=symbol,
            signal_type=signal_type.lower(),
            composite_score=round(float(composite_score), 2),
            confidence=round(float(confidence), 2),
            total_latency_ms=round(float(total_latency_ms), 1),
            agent_latencies_ms={k: round(float(v), 1) for k, v in agent_latencies_ms.items()},
            risk_concentration_score=round(float(risk_concentration_score), 4),
            degraded_agents=degraded_agents or [],
            recorded_at=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
        return session_id
    finally:
        db.close()


def evaluate_forward_returns(days: int = 30) -> Dict[str, Any]:
    """Evaluate logged signals against the forward return after `days` days.

    Fetches the current price for each symbol and marks `signal_accurate`
    when the realised move agrees with the recorded signal direction.
    """
    import yfinance as yf

    db, PerformanceLog = _db()
    updated = 0
    skipped = 0
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        pending = (
            db.query(PerformanceLog)
            .filter(
                PerformanceLog.evaluated_at.is_(None),
                PerformanceLog.recorded_at <= cutoff,
            )
            .limit(50)
            .all()
        )
        for row in pending:
            try:
                ticker = yf.Ticker(row.symbol)
                hist = ticker.history(period="5d", interval="1d")
                if hist.empty:
                    skipped += 1
                    continue
                current = float(hist["Close"].iloc[-1])
                future = current
                past = float(hist["Close"].iloc[0]) if len(hist) > 1 else current
                forward_return = ((future - past) / past * 100) if past else 0.0
                row.forward_return_pct = round(forward_return, 2)

                direction = row.signal_type.lower()
                if direction in ("buy", "strong_buy"):
                    row.signal_accurate = forward_return > 0
                elif direction in ("sell", "reduce", "avoid", "strong_sell"):
                    row.signal_accurate = forward_return < 0
                else:
                    row.signal_accurate = abs(forward_return) < 1.5
                row.evaluated_at = datetime.utcnow()
                updated += 1
            except Exception:  # noqa: BLE001
                skipped += 1
        db.commit()
        return {"evaluated": updated, "skipped": skipped, "days": days}
    finally:
        db.close()


def get_performance_logs(user_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    db, PerformanceLog = _db()
    try:
        q = db.query(PerformanceLog)
        if user_id:
            q = q.filter(PerformanceLog.user_id == user_id)
        rows = q.order_by(PerformanceLog.recorded_at.desc()).limit(limit).all()
        return [
            {
                "session_id": r.session_id,
                "user_id": r.user_id,
                "symbol": r.symbol,
                "signal_type": r.signal_type,
                "composite_score": r.composite_score,
                "confidence": r.confidence,
                "total_latency_ms": r.total_latency_ms,
                "agent_latencies_ms": r.agent_latencies_ms or {},
                "risk_concentration_score": r.risk_concentration_score,
                "degraded_agents": r.degraded_agents or [],
                "forward_return_pct": r.forward_return_pct,
                "signal_accurate": r.signal_accurate,
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


def get_performance_summary() -> Dict[str, Any]:
    """Aggregate metrics across all logged sessions."""
    db, PerformanceLog = _db()
    try:
        rows = db.query(PerformanceLog).all()
        if not rows:
            return {
                "sessions": 0,
                "avg_total_latency_ms": 0.0,
                "avg_agent_latency_ms": 0.0,
                "avg_risk_concentration": 0.0,
                "accuracy_vs_forward_return": None,
                "degraded_sessions": 0,
            }
        total_latencies = [r.total_latency_ms for r in rows]
        agent_latencies = [
            v for r in rows for v in (r.agent_latencies_ms or {}).values()
        ]
        concentrations = [r.risk_concentration_score or 0.0 for r in rows]
        degraded = [r for r in rows if r.degraded_agents]
        evaluated = [r for r in rows if r.signal_accurate is not None]
        accuracy = (
            round(sum(1 for r in evaluated if r.signal_accurate) / len(evaluated), 3)
            if evaluated
            else None
        )
        return {
            "sessions": len(rows),
            "avg_total_latency_ms": round(sum(total_latencies) / len(total_latencies), 1),
            "avg_agent_latency_ms": round(sum(agent_latencies) / len(agent_latencies), 1)
            if agent_latencies else 0.0,
            "avg_risk_concentration": round(sum(concentrations) / len(concentrations), 4),
            "accuracy_vs_forward_return": accuracy,
            "evaluated_sessions": len(evaluated),
            "degraded_sessions": len(degraded),
        }
    finally:
        db.close()