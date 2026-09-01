<div align="center">

# 🧠 AI Quant Terminal

### Your Personal AI Stock-Research Assistant for Indian Markets (NSE / BSE)

**Turn raw market data into clear, personalized, explainable investment intelligence — in seconds.**

&nbsp;

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()
[![Multi-Agent](https://img.shields.io/badge/PS--01-Multi--Agent%20AI-purple)](AGENT_ARCHITECTURE.md)

*Educational tool — not financial advice. Always consult a SEBI-registered advisor.*

</div>

---

## 🎯 What Is This?

**AI Quant Terminal** is a single web app that does professional-grade stock research automatically. Instead of juggling dozens of websites, you open one page, type a stock symbol, and the app:

1. Pulls the latest prices and historical data.
2. Runs technical analysis (RSI, MACD, momentum, volume, support/resistance…).
3. Checks the fundamentals (valuation, financial health).
4. Reads the news **and** measures the mood (positive / negative sentiment).
5. Asks machine-learning models to predict the direction.
6. Weighs the risk and tells you a **stop-loss**.
7. Combines everything and uses an **AI "brain"** (a large language model) to give one clear answer: **BUY / HOLD / SELL**, with a confidence level and the *reasoning behind it*.

Then — when you log in — it personalizes that answer to **your** risk tolerance and portfolio, grounds it in **cited sources** (filings, announcements, news), shows the **full reasoning chain**, and logs every session's **performance** for you.

> **Why it's different:** most stock tools show you *charts*. This one does the *analysis and explains its thinking*, so you understand *why* — not just *what*.

---

## ✨ Key Features

### 🤖 AI-Powered Analysis
- **Multi-Agent AI system** (`/api/v2/agents/analyze`) — a team of 7 specialized agents work **in parallel** and a synthesis layer combines them.
- **Machine-learning predictions** for price direction (up/down probability).
- **AI recommendation** powered by a large language model (Groq) with fallbacks so it never crashes.
- **Explainable** — every recommendation shows the reasoning steps, key factors, and cited sources.

### 📊 Technical & Fundamental Analysis
- **RSI, MACD, ATR, EMA, Bollinger Bands, Stochastic** — a full indicator suite.
- **Multi-timeframe**: Intraday (5-min) · Swing (daily) · Long-term (weekly).
- **Volume anomaly detection** and price-volume confirmation.
- **Financial health**, valuation, profit margins, sector comparison.

### 📰 News & Sentiment
- Aggregates news from **multiple sources** (GNews, NewsData.io, Finnhub, Firecrawl).
- **Sentiment score** (-1 to +1) with per-article reasoning.
- **Source attribution** — each news item links back to where it came from.

### 💼 Portfolio & Watchlist Management
- Track unlimited holdings with **live P&L**, sector allocation, and positions.
- **AI recommendations** personalized to your risk profile and capital.
- Watchlists, alerts, and a **trade journal** with behavioral insights.

### 🔐 Authentication & Security
- **Supabase Auth** (email/password) with JWT tokens and 30-min session refresh.
- User data isolated with **Row-Level Security** where configured.
- Local **SQLite** fallback so the app still runs without Supabase.

### 📈 Performance & Audit
- **Session performance log** — signal accuracy vs. 30-day forward return, agent response latency, portfolio risk-concentration score.
- **Veritas audit trail** — every AI signal is logged with evidence and a verification hash.

---

## 🧩 The Multi-Agent System (PS-01)

The standout feature is an **orchestrated team of specialized AI agents** that research a stock together, then a "synthesis layer" writes one final recommendation.

```
  Market data + document corpus (filings, announcements, news)
                        │
                        ▼
        ┌── MULTI-AGENT ORCHESTRATOR ──────────────┐
        │  Run all agents IN PARALLEL:             │
        │   • Price Momentum Agent                 │
        │   • Volume Anomaly Agent                 │
        │   • News Sentiment Agent                 │
        │   • Fundamental Agent                    │
        │   • Machine-Learning Agent               │
        │   • Risk-Manager Agent                   │
        │   • News Grounding Agent (RAG)           │
        └──────────────────────────────────────────┘
                        │
                        ▼
        SYNTHESIS LAYER (weighted composite)
        • adjusts for YOUR risk profile
        • builds the reasoning chain + citations
        • logs performance + writes the audit trail
                        │
                        ▼
   One clear answer: BUY / HOLD / SELL + confidence + sources
```

### The 7 Agents

| Agent | What it studies | Output |
|-------|-----------------|--------|
| **Momentum** | RSI, MACD, trend | Buy/Hold/Sell + score |
| **Volume Anomaly** | Volume spikes & price-volume confirmation | Buy/Hold/Sell + score |
| **Sentiment** | News mood + article attribution | Buy/Hold/Sell + score |
| **Fundamental** | Financial health & valuation | Buy/Hold/Sell + score |
| **ML Predictor** | Classifier probability of an up-move | Buy/Hold/Sell + score |
| **Risk Manager** | Stop-loss, volatility, concentration | Risk level + position size |
| **News Grounding (RAG)** | Retrieves relevant filings/announcements | Grounded view + citations |

Try it: open `/agent-insights.html`, type a symbol, and hit **Run Multi-Agent Analysis**.

> 📄 Read the full design in [`AGENT_ARCHITECTURE.md`](AGENT_ARCHITECTURE.md).

---

## 🛠 Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | **FastAPI (Python)** | Fast, async, auto-generated docs |
| Market data | **yfinance** | Live/historical prices for NSE/BSE |
| ML / AI | **scikit-learn**, **HuggingFace Transformers**, **Groq LLM** | Predictions & sentiment + narrative |
| Database | **Supabase (PostgreSQL)** with **SQLite fallback** | User data & persistence |
| Cache | **Redis** (optional, in-memory fallback) | Speed |
| Frontend | **HTML5 / CSS3 / Vanilla JS** + **Chart.js** | No build step, served by the backend |

A key design principle: **every external service has a fallback.** If Groq, a news API, or the transformer model is unavailable, the app still works — it just uses a simpler method. It's built so that **nothing crashes the app.**

---

## 📸 Screenshots

> *Add your screenshots to a `screenshots/` folder and reference them here.*

| Home Dashboard | Stock Analysis | Multi-Agent Insights |
|----------------|----------------|----------------------|
| ![Home](screenshots/homepage.png) | ![Analysis](screenshots/analysis.png) | ![Agents](screenshots/agents.png) |

| Portfolio | Audit Trail | Auth |
|-----------|-------------|------|
| ![Portfolio](screenshots/portfolio.png) | ![Audit](screenshots/audit.png) | ![Auth](screenshots/auth.png) |

---

## 🚀 Quick Start

You only need **Python 3.8+** and a few minutes. (The frontend is served by the backend, so there's **one server to run**.)

### 1. Get the code
```bash
git clone https://github.com/AgriEssentials/finance.git
cd finance
```

### 2. Create a virtual environment (optional but recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your keys
Copy the included `.env` (it's already git-ignored) and fill in the values you want:

```env
# REQUIRED for login to work:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Optional but recommended (more features):
GROQ_API_KEY=your-groq-key
NEWSDATA_API_KEY=your-newsdata-key
GNEWS_API_KEY=your-gnews-key
FINNHUB_API_KEY=your-finnhub-key
FIRECRAWL_API_KEY=your-firecrawl-key
```

> 🔐 **Never commit your `.env` file.** It's already in `.gitignore`.

### 5. Run it (that's it!)
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 6. Open the app
- **🖥 Web app:** <http://localhost:8001>
- **📘 API docs (Swagger):** <http://localhost:8001/api/docs>
- **📗 ReDoc:** <http://localhost:8001/api/redoc>
- **🤖 Multi-agent demo:** <http://localhost:8001/agent-insights.html>

---

## 📄 Pages

| URL | What it is |
|-----|-----------|
| `/` | **Home dashboard** — live market pulse, sector heatmap, news |
| `/analysis.html` | **Analysis terminal** — analyze any stock |
| `/agent-insights.html` | **Multi-agent AI research desk** (PS-01) |
| `/dashboard.html` | **Your dashboard** — portfolio, P&L, watchlist |
| `/portfolio.html` | **Portfolio manager** — buy/sell, positions |
| `/setup.html` | **Onboarding** — set risk tolerance, capital, strategy |
| `/auth.html` | **Login / Register** |
| `/audit-trail.html` | **Veritas** — audit trail of AI signals |
| `/data-sources.html` | **Data sources & telemetry** |
| `/test.html` | **API smoke test** (dev) |

---

## 📚 API Reference

The full interactive reference is at `/api/docs`. Here are the highlights:

**Core analysis**
```
GET /api/analyze?symbol=RELIANCE.NS&mode=swing
GET /api/professional/analyze?symbol=RELIANCE.NS&mode=swing
```

**Multi-Agent system (PS-01)**
```
GET  /api/v2/agents/analyze?symbol=INFY.NS&mode=swing
GET  /api/v2/agents/roles                 # list agents + output contracts
GET  /api/v2/agents/rag/search?query=...  # semantic search over the corpus
GET  /api/v2/agents/rag/corpus            # corpus stats + documents
POST /api/v2/agents/rag/ingest            # re-seed the corpus
GET  /api/v2/agents/performance           # session performance log
POST /api/v2/agents/performance/evaluate  # score vs 30-day forward return
```

**Market data**
```
GET /api/landing-data          # public market dashboard data
GET /api/sparklines            # miniature charts
GET /api/market-news           # news feed
GET /api/scanner/top-gainers   # top gainers / losers / most active
```

**Portfolio & user**
```
GET  /api/portfolio/summary
POST /api/portfolio/buy
POST /api/portfolio/sell
POST /api/portfolio/setup
GET  /api/user/profile/{id}
POST /api/user/trades/log      # trade journal
GET  /api/user/coach/{id}      # AI coaching
```

---

## 🗂 Project Structure

```
finance/
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI entry point (all routes + static serving)
│       ├── agents/                  # PS-01 multi-agent system
│       │   ├── orchestrator.py      # parallel dispatch + synthesis
│       │   ├── agents.py            # the 7 specialized agents
│       │   ├── rag.py               # document corpus + semantic search
│       │   ├── performance.py       # session performance log
│       │   └── contracts.py         # structured output contracts
│       ├── indicators.py            # technical indicators
│       ├── sentiment.py             # news sentiment (multi-source)
│       ├── ml_model.py              # ML price-direction model
│       ├── ai_predictor.py          # LLM "brain" with fallbacks
│       ├── fundamental_analysis.py  # fundamentals
│       ├── risk_manager.py          # risk & position sizing
│       ├── personalized_trading.py  # per-user personalization
│       ├── veritas_audit.py         # evidence/audit trail
│       └── database.py              # SQLAlchemy models (SQLite/PG)
├── frontend/
│   ├── index.html                   # home dashboard
│   ├── agent-insights.html          # multi-agent demo UI
│   ├── analysis.html                # stock analysis terminal
│   └── static/                      # css / js / sounds
├── data/                            # local portfolios (per user)
├── .env                             # your secrets (git-ignored)
├── requirements.txt
└── README.md
```

---

## ⚙️ Configuration (`.env`)

| Variable | Required | Purpose |
|----------|:--------:|---------|
| `SUPABASE_URL` | ✅ | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Public anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | ⬜ | Server-side key (admin ops) |
| `GROQ_API_KEY` | ⬜ | AI narrative / sentiment |
| `NEWSDATA_API_KEY` | ⬜ | News source |
| `GNEWS_API_KEY` | ⬜ | News source |
| `FINNHUB_API_KEY` | ⬜ | Analysts & fundamentals |
| `FIRECRAWL_API_KEY` | ⬜ | Stock-specific news search |
| `REDIS_URL` | ⬜ | Cache (falls back to in-memory) |
| `PORT` | ⬜ | Server port (default `8001`) |

**What happens if keys are missing?** The app still runs. Fewer news sources, no AI narrative, and a simpler sentiment method — but nothing crashes. That's intentional.

---

## 🧭 Troubleshooting / FAQ

**The page loads but shows "Login for Full Access"**
That's the guest view — you're not logged in. Register at `/auth.html`. Some features (portfolio, shadow market, personalized dashboard) require an account.

**I see `401 Unauthorized` in the console**
Your login token expired or is stale. Either log in again, or clear it and reload. The app now gracefully falls back to public data instead of breaking.

**The app works without Supabase?**
Yes. Authentication features are limited, but market data and analysis work on the **local SQLite** fallback.

**It's slow on the first search**
The first analysis warms up AI models and fetches news. Subsequent searches are much faster (cached for 10 minutes). The backend pre-warms models at startup.

**Port already in use / connection refused**
`8001` is the default. Change `PORT` in `.env` or run with `--port 8002`. Check nothing else is using it.

**Missing `alert.mp3` or other static 404s**
Run-time asset paths. The app now ignores missing sounds silently — these are cosmetic only.

**I want to reset my data**
The local database is `stock_analyzer.db` (git-ignored). Delete it and re-run to start fresh. User portfolios live under `data/portfolios/`.

---

## 🔒 Security

- All sensitive auth endpoints use **JWT** via Supabase.
- `.env` (secrets) is **git-ignored** and never committed.
- `<audio>/<script>` and user content are escaped on the frontend.
- CORS is configured; rate limiting protects sensitive endpoints.
- **Please:** never share or commit your `.env`, API keys, or a real Supabase service key.

---

## 🧪 Running Tests

```bash
cd backend
pytest
```

> The repo also ships helper scripts (`check_server.py`, `diagnostic.py`, `fix_supabase.py`) to diagnose Supabase/connection issues.

---

## 🤝 Contributing

Contributions are welcome!

1. **Fork** the repo, create a feature branch.
2. Follow existing code style (PEP 8 for Python, ESLint-style for JS).
3. Add tests where possible.
4. **Run** `pytest` and the typecheck (`cd frontend && npm run typecheck`).
5. Open a **Pull Request**.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

---

## 📄 License

Released under the **MIT License** — see [`LICENSE`](LICENSE).

---

## 🙏 Acknowledgments

- **Yahoo Finance** (market data) · **Supabase** (auth/db) · **FastAPI** · **Groq** (LLM) · **Hugging Face** (transformers) · **Chart.js**
- Built as a **PS-01 Multi-Agent Autonomous Financial Intelligence System** for the retail-investor thesis: *from raw data to explainable, personalized, cited decision intelligence.*
- The `data/portfolios/*.json` files are per-user demo data.

---

## 🔗 Related Docs

- [`AGENT_ARCHITECTURE.md`](AGENT_ARCHITECTURE.md) — the multi-agent design (PS-01)
- [`QUICK_START_FOR_ENGINEERS.md`](QUICK_START_FOR_ENGINEERS.md) — short engineering intro
- [`AI_ML_MODELS_DOCUMENTATION.md`](AI_ML_MODELS_DOCUMENTATION.md) — the ML models
- [`CHANGELOG.md`](CHANGELOG.md) — version history

---

<div align="center">

Made with ❤️ for retail investors.

**⚠ Disclaimer:** This software is for educational purposes only and does not constitute investment advice. Stock markets carry significant risk. Always consult a SEBI-registered financial advisor before investing.

</div>
