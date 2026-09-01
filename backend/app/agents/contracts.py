"""
Structured output contracts for the PS-01 multi-agent system.

Every specialized agent returns an `AgentOutput` whose schema is fixed by
Pydantic. The synthesis layer consumes these contracts and produces a single
`SynthesisOutput` with the full reasoning trace, citations and performance
metadata. This gives every agent a *defined role and structured output
contract* as required by PS-01.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A single piece of retrieved source material attributed to an agent output."""

    source_id: str = Field(description="Unique id of the source document")
    title: str = Field(description="Title/headline of the source")
    source: str = Field(description="Publisher/provider (e.g. NSE, GNews, NewsData.io)")
    url: Optional[str] = Field(None, description="Direct URL to the source")
    published_at: Optional[str] = Field(None, description="ISO timestamp of the source")
    doc_type: str = Field(default="news", description="news | filing | announcement | transcript")
    relevance_score: float = Field(default=0.0, description="Retrieval relevance 0-1")
    snippet: str = Field(default="", description="Retrieved passage shown to the user")
    symbol: Optional[str] = Field(None, description="Related stock symbol")


class AgentOutput(BaseModel):
    """Structured output contract returned by every specialized agent."""

    agent_id: str = Field(description="Machine id of the agent (e.g. momentum)")
    agent_name: str = Field(description="Human-readable agent name")
    role: str = Field(description="Defined role of the agent")
    status: str = Field(default="ok", description="ok | degraded | failed")
    latency_ms: float = Field(default=0.0, description="Agent execution time")
    confidence: float = Field(default=0.0, description="Agent confidence 0-100")
    score: float = Field(default=50.0, description="Directional score 0-100 (50 = neutral)")
    recommendation: str = Field(default="NEUTRAL", description="BUY | HOLD | SELL (agent view)")
    summary: str = Field(default="", description="Plain-language summary of the agent finding")
    key_factors: List[str] = Field(default_factory=list, description="Driving factors")
    citations: List[Citation] = Field(default_factory=list, description="Attributed sources")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Raw structured evidence")
    error: Optional[str] = Field(None, description="Error message when degraded/failed")

    def to_trace(self) -> Dict[str, Any]:
        """Flatten for the reasoning-trace viewer."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "role": self.role,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 1),
            "confidence": round(self.confidence, 1),
            "score": round(self.score, 1),
            "recommendation": self.recommendation,
            "summary": self.summary,
            "key_factors": self.key_factors,
            "citations": [c.dict() for c in self.citations],
            "evidence": self.evidence,
            "error": self.error,
        }


class ReasoningStep(BaseModel):
    """A single step in the final reasoning chain."""

    step: int = Field(description="Order of the step")
    title: str = Field(description="Short title of the step")
    detail: str = Field(description="Human-readable explanation")


class PerformanceSnapshot(BaseModel):
    """Session-level performance metrics captured per analysis."""

    session_id: str
    user_id: str
    symbol: str
    signal_type: str
    composite_score: float
    confidence: float
    total_latency_ms: float
    agent_latencies_ms: Dict[str, float]
    risk_concentration_score: float = Field(default=0.0, description="Herfindahl concentration 0-1")
    degraded_agents: List[str] = Field(default_factory=list)
    recorded_at: str
    forward_return_pct: Optional[float] = Field(None, description="Filled when evaluated later")
    signal_accurate: Optional[bool] = Field(None, description="Filled when evaluated later")


class SynthesisOutput(BaseModel):
    """Final output of the synthesis layer consumed by the UI."""

    symbol: str
    mode: str
    timestamp: str
    recommendation: str
    action: str
    confidence: float
    composite_score: float
    component_scores: Dict[str, float]
    reasoning_chain: List[ReasoningStep] = Field(default_factory=list)
    agent_traces: List[AgentOutput] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    degraded_data: List[str] = Field(default_factory=list, description="Degraded-data scenarios handled")
    user_profile_used: Dict[str, Any] = Field(default_factory=dict)
    position_sizing: Dict[str, Any] = Field(default_factory=dict)
    performance: Optional[PerformanceSnapshot] = Field(None)
    disclaimer: str = Field(
        default="This analysis is for educational purposes only and does not constitute financial advice. "
        "Please consult a SEBI-registered financial advisor before making any investment decisions."
    )