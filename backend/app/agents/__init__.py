"""
PS-01 Multi-Agent Autonomous Financial Intelligence System

Implements the multi-agent orchestration framework, RAG pipeline, structured
output contracts, performance logging and the reasoning-trace synthesis layer
on top of the existing Quant Terminal architecture.
"""

from app.agents.contracts import (
    Citation,
    AgentOutput,
    SynthesisOutput,
    PerformanceSnapshot,
)
from app.agents.orchestrator import MultiAgentOrchestrator, get_orchestrator

__all__ = [
    "Citation",
    "AgentOutput",
    "SynthesisOutput",
    "PerformanceSnapshot",
    "MultiAgentOrchestrator",
    "get_orchestrator",
]