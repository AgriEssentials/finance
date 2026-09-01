# PS-01 Multi-Agent Autonomous Financial Intelligence System

> Brief written summary of the agent architecture implemented on top of the
> existing Quant Terminal codebase to satisfy PS-01.

---

## 1. What this system does

Quant Terminal now runs a **multi-agent research desk**. When a retail investor
asks for a stock analysis, a team of specialized agents is dispatched **in
parallel**. Each agent studies one dimension of the market independently, and a
**synthesis layer** combines their structured outputs into a single explainable
recommendation — grounded in retrieved filings/announcements, personalized to
the user's risk profile, and logged against performance metrics for every
session.

```
 raw market feed + document corpus
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│              MULTI-AGENT ORCHESTRATOR                    │
│                                                          │
│  ┌─────────────── parallel dispatch (ThreadPool) ──────┐ │
│  │  MomentumAgent      │  VolumeAnomalyAgent           │ │
│  │  SentimentAgent     │  FundamentalAgent             │ │
│  │  MLAgent            │  RiskAgent                    │ │
│  │  NewsGroundingAgent (RAG, with citations)           │ │
│  └─────────────────────────────────────────────────────┘ │
│  each returns a Pydantic AgentOutput (fixed contract)    │
│                          │                                │
│                          ▼                                │
│  SYNTHESIS LAYER                                          │
│   - weighted composite + risk adjustment                  │
│   - user-profile personalization                          │
│   - reasoning chain + citations + degraded-data flags     │
│   - performance log + Veritas audit persistence           │
└─────────────────────────────────────────────────────────┘
        │
        ▼
 user-facing recommendation + full reasoning trace + sources
```

## 2. The agents (roles and output contracts)

| Agent | Dimension studied | Role |
|-------|-------------------|------|
| `MomentumAgent` | Price momentum | RSI, MACD, trend structure |
| `VolumeAnomalyAgent` | Volume anomaly | Volume ratio, spikes, price-volume confirmation |
| `SentimentAgent` | News sentiment | Multi-provider news, per-article attribution |
| `FundamentalAgent` | Fundamentals | Financial health, valuation, earnings quality |
| `MLAgent` | ML probability | Trained classifiers → up-probability |
| `RiskAgent` | Risk | ATR stop-loss, volatility regime, concentration |
| `NewsGroundingAgent` | RAG grounding | Semantic retrieval + citations |

Every agent returns the **same structured contract** (`AgentOutput`, defined in
`backend/app/agents/contracts.py`): `agent_id, role, status, latency_ms,
confidence, score, recommendation, summary, key_factors, citations, evidence,
error`. This fixed schema is what the synthesis layer consumes.

## 3. RAG / semantic retrieval

- **Document corpus** (`rag_documents` table): synthetic SEBI-style filings,
  NSE corporate announcements, and news articles, persisted and searchable.
- **Semantic search**: DistilBERT mean-pooled embeddings (TF-IDF fallback),
  cosine similarity over stored vectors (`backend/app/agents/rag.py`).
- **Grounding**: the `NewsGroundingAgent` retrieves the most relevant documents
  for a symbol/question and attaches them as citations — with source id, title,
  publisher, URL, snippet and relevance score — so every claim has visible
  attribution.
- Endpoints: `GET /api/v2/agents/rag/search`, `GET /api/v2/agents/rag/corpus`,
  `POST /api/v2/agents/rag/ingest`.

## 4. User profiling

`personalized_trading.py` already stored `risk_tolerance`, `preferred_strategy`
and `capital`. The synthesis layer now consumes those values and **demonstrably
changes the output** on identical market data:

- low risk tolerance → upside score capped, confidence scaled down;
- high risk tolerance → aggressive stance allowed;
- capital + risk tolerance drive ATR-based position sizing (shares/stop-loss);
- the profile used is echoed back in the response (`user_profile_used`) so the
  differentiation is auditable.

## 5. Performance logging

Every session writes a `performance_logs` row capturing at least three metrics:

1. **signal accuracy vs forward return** — `evaluate_forward_returns()` marks
   `signal_accurate` by comparing the recorded signal to the realised move;
2. **agent response latency** — per-agent `latency_ms` and total;
3. **portfolio risk-concentration score** — Herfindahl index of holdings.

`GET /api/v2/agents/performance` returns the log and an aggregate summary.
`POST /api/v2/agents/performance/evaluate` fills forward returns.

## 6. End-to-end demo

`GET /api/v2/agents/analyze?symbol=RELIANCE.NS&mode=swing` runs the full chain —
data ingestion → parallel agent reasoning → synthesis → recommendation — and
returns the complete reasoning trace, component scores, citations, degraded-data
warnings, user profile used, position sizing and the performance snapshot. The
`/agent-insights.html` page renders all of it live, and the existing Veritas
audit-trail page (`/audit-trail.html`) now receives real signals because the
orchestrator wires `log_signal_for_user()` on every run.

## 7. Degraded-data handling

The pipeline never fails or produces an uncited output:

- any agent that throws or exceeds its time budget returns `status: "degraded"`
  / `"failed"` instead of crashing;
- the weighted composite is **renormalized** over the available agents;
- RAG degradation is surfaced as an explicit warning while the decision
  proceeds on the remaining dimensions;
- existing fallbacks (no Groq, no news key, no model) are preserved.

## 8. Files added

```
backend/app/agents/__init__.py
backend/app/agents/contracts.py        # AgentOutput / Citation / SynthesisOutput contracts
backend/app/agents/agents.py           # 7 specialized agents
backend/app/agents/orchestrator.py     # parallel dispatch + synthesis + Veritas wiring
backend/app/agents/rag.py              # corpus, embeddings, semantic search, citations
backend/app/agents/performance.py      # session performance log + forward-return evaluation
frontend/agent-insights.html           # reasoning-trace / citations / demo UI
```

Plus `RagDocument` and `PerformanceLog` tables in `backend/app/database.py` and
the `/api/v2/agents/*` endpoints in `backend/app/main.py`.