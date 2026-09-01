# Quant Terminal — AI & Machine Learning Architecture

> A deep-dive into the ML models, AI components, and objectives of the Quant Terminal platform.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture (AI/ML View)](#2-system-architecture-aiml-view)
3. [Machine Learning Models](#3-machine-learning-models)
   - 3.1 [Logistic Regression (Direction Signal)](#31-logistic-regression-direction-signal)
   - 3.2 [LSTM (Price Forecasting)](#32-lstm-price-forecasting)
   - 3.3 [Transformer (Price Forecasting)](#33-transformer-price-forecasting)
   - 3.4 [Q-Learning RL Agent (Portfolio Allocation)](#34-q-learning-rl-agent-portfolio-allocation)
   - 3.5 [DistilBERT (News Sentiment)](#35-distilbert-news-sentiment)
4. [LLM / Agentic AI Layer](#4-llm--agentic-ai-layer)
   - 4.1 [Groq LLM Predictor](#41-groq-llm-predictor)
   - 4.2 [Agent Brain (Regime Adaptation)](#42-agent-brain-regime-adaptation)
   - 4.3 [Explainable AI (SHAP-style reasoning)](#43-explainable-ai-shap-style-reasoning)
5. [Data Pipeline](#5-data-pipeline)
6. [Objectives & Goals](#6-objectives--goals)
7. [Key File References](#7-key-file-references)
8. [Limitations & Fallbacks](#8-limitations--fallbacks)

---

## 1. Project Overview

**Quant Terminal** is a professional-grade, AI-powered stock analysis platform built for **Indian equity markets (NSE/BSE)**. It combines:

- Real-time market data (Yahoo Finance, WebSocket streaming)
- Advanced technical indicators (RSI, MACD, ATR, EMA, Bollinger Bands, Stochastic, OBV)
- Machine learning price-direction prediction
- News sentiment analysis (multi-provider aggregation)
- LLM-powered investment reasoning and recommendations
- Institutional-grade risk management (VaR, CVaR, Monte Carlo, Sharpe/Sortino)
- Dynamic market-regime adaptation

**Target users:** Retail traders (intraday/swing), long-term investors, and market analysts.

**Trading modes:** Intraday (5m charts), Swing (daily), Long-term (weekly).

---

## 2. System Architecture (AI/ML View)

```
                         ┌─────────────────────────────┐
                         │       CLIENT (Frontend)     │
                         │  HTML / JS / Chart.js       │
                         └──────────────┬──────────────┘
                                        │ REST + WebSocket
                         ┌──────────────▼──────────────┐
                         │      FastAPI Backend        │
                         │  (JWT Auth, Rate Limit)     │
                         └──────────────┬──────────────┘
                                        │
          ┌─────────────────┬───────────┴───────────┬─────────────────┐
          ▼                 ▼                       ▼                 ▼
   ┌────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌────────────┐
   │ Technical  │   │  ML Engine   │   │   LLM Layer      │   │ Sentiment  │
   │ Indicators │   │ (sklearn)    │   │   (Groq API)     │   │  Engine    │
   │            │   │ LSTM/Transf  │   │  Final signal +  │   │ (DistilBERT│
   │ RSI, MACD, │   │ RL (Q-Learn) │   │  price forecast  │   │ + LLM)     │
   │ ATR, EMA   │   │              │   │  + reasoning     │   │            │
   └────────────┘   └──────────────┘   └──────────────────┘   └────────────┘
                                        │
                               ┌────────▼────────┐
                               │   Agent Brain   │
                               │ Regime detection│
                               │ UI/risk adapt   │
                               └─────────────────┘
                                        │
                  ┌─────────────────────┼─────────────────────┐
                  ▼                     ▼                     ▼
        ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
        │  Supabase    │      │  Local .pkl  │      │  External    │
        │ (PostgreSQL) │      │  models/     │      │  APIs        │
        │ profiles,    │      │  ML artifacts│      │  yfinance,   │
        │ portfolios   │      │              │      │  GNews, etc. │
        └──────────────┘      └──────────────┘      └──────────────┘
```

---

## 3. Machine Learning Models

### 3.1 Logistic Regression (Direction Signal)

**File:** `backend/app/ml_model.py`

The primary classification model used for live buy/sell signals.

| Aspect | Detail |
|--------|--------|
| Algorithm | Logistic Regression (binary classifier) |
| Library | scikit-learn |
| Task | Predict probability of price moving **UP** over next 3 (intraday) / 5 (swing) periods |
| Features | RSI, MACD histogram, volume ratio, ATR, EMA difference |
| Target | `1` if future return > 0, else `0` |
| Training | `class_weight='balanced'`, max_iter 1000, MinMax/Standard scaling |
| Persistence | `joblib` → `backend/models/{mode}_model.pkl` + `{mode}_scaler.pkl` |
| Modes | `intraday`, `swing`, `longterm` (separate models) |
| Output | `up_probability` %, `prediction` (Up/Down/Neutral), confidence tier |

**Decision thresholds:**
- `up_probability > 60` → "Up" (High if > 70)
- `up_probability < 40` → "Down" (High if < 30)
- otherwise → "Neutral"

### 3.2 LSTM (Price Forecasting)

**File:** `backend/app/ai_models.py` → `LSTMPricePredictor`

Deep-learning sequence model for multi-step price forecasting.

| Aspect | Detail |
|--------|--------|
| Architecture | LSTM(128) → Dropout(0.2) → LSTM(64) → Dense(32) → Dense(forecast_steps) |
| Lookback | 60 periods |
| Forecast | 5 future prices |
| Optimizer | Adam (lr 0.001), loss = MSE, metric = MAE |
| Preprocessing | MinMaxScaler (0–1), 80/20 train/test split |
| Memory | TensorFlow lazy-loaded only when needed (avoids cold-start cost) |
| Confidence | Fixed at 0.75 |

### 3.3 Transformer (Price Forecasting)

**File:** `backend/app/ai_models.py` → `TransformerPricePredictor`

Attention-based alternative to the LSTM for price prediction.

| Aspect | Detail |
|--------|--------|
| Architecture | MultiHeadAttention(num_heads=4, key_dim=32) → GlobalAvgPool1D → Dense(64) → Dense(32) → Dense(forecast_steps) |
| Lookback / Forecast | 60 / 5 |
| Optimizer | Adam (lr 0.001), loss = MSE |
| Confidence | Fixed at 0.72 |

### 3.4 Q-Learning RL Agent (Portfolio Allocation)

**File:** `backend/app/rl_portfolio.py` → `PortfolioRLAgent`

Reinforcement-learning agent that recommends portfolio allocation levels.

| Aspect | Detail |
|--------|--------|
| Algorithm | Tabular Q-Learning |
| State | Discretized: `{PriceTrend}_{Sentiment}_{Volatility}` (e.g. `UP_POSITIVE_HIGH`) |
| Actions | Allocation %: `[0, 25, 50, 75, 100]` |
| Reward | `return*100 + sharpe*10` (risk-adjusted returns bonus) |
| Policy | Epsilon-greedy (ε = 0.1) |
| Hyperparameters | lr = 0.1, γ (discount) = 0.95 |
| Output | STRONG_BUY / BUY / HOLD / REDUCE |

**Supporting math (`SharpeCalculator`):** Sharpe Ratio, Beta, and Jensen's Alpha calculations used for portfolio evaluation.

### 3.5 DistilBERT (News Sentiment)

**File:** `backend/app/sentiment.py` → `SentimentAnalyzer`

Transformer-based NLP model for financial news sentiment.

| Aspect | Detail |
|--------|--------|
| Model | `distilbert-base-uncased-finetuned-sst-2-english` |
| Pipeline | Hugging Face `sentiment-analysis` |
| Score mapping | Positive → +0.5..0.9, Negative → -0.5..-0.9, Neutral → -0.2..0.2 |
| Loading | Lazy, thread-safe, 60s timeout guard |
| Priority chain | 1) Groq LLM → 2) DistilBERT → 3) keyword fallback |
| Aggregation | Average score → Positive/Neutral/Negative + distribution breakdown |

---

## 4. LLM / Agentic AI Layer

### 4.1 Groq LLM Predictor

**File:** `backend/app/ai_predictor.py` → `AIStockPredictor`

The "brain" that fuses all analysis into a final trading recommendation.

**How it works:**
1. Builds a structured prompt with: technical indicators, sentiment data, ML prediction, risk management data, and recent price history.
2. Calls Groq's chat-completions API (`openai/gpt-oss-120b` default, with model fallback candidates and 429 retry logic).
3. The model returns **strict JSON** with keys:
   - `prediction` (UP / DOWN / NEUTRAL)
   - `confidence` (0–100)
   - `reasoning`
   - `key_factors`
   - `risk_level` (LOW / MEDIUM / HIGH)
   - `recommendation`
   - `price_target`, `stop_loss`
   - `predicted_prices` (for the forecast chart)
   - `geopolitical_scenarios`
   - `disclaimer`
4. Output is validated/normalized and combined with transparency data (which articles/indicators drove the call).

**Fallback engine:** If the API is unreachable, a weighted rule-based algorithm (trend > RSI > ML > sentiment > MACD) generates the signal so the platform never fails.

### 4.2 Agent Brain (Regime Adaptation)

**File:** `backend/app/agent_brain.py` → `AgentBrain`

An async orchestration layer that makes the whole platform **context-aware**.

**Responsibilities:**
1. **Market regime detection** — classifies market as BULL / BEAR / SIDEWAYS / HIGH_VOLATILITY / CRISIS using India VIX + Nifty daily change, with **hysteresis** (3-of-5 readings must agree, 3-min cooldown) to prevent theme "flip-flopping".
2. **Portfolio risk monitoring** — detects >3% position drawdowns, generates price-drop alerts.
3. **Risk guardrails** — computes portfolio beta (high-beta vs defensive stock mapping) and concentration risk; blocks aggressive signals when beta > 1.3 or during crises.
4. **Dynamic UI config** — switches theme (war-room / caution / professional-dark), visible indicators, recommendation aggressiveness, and refresh interval (10s in crisis → 60s calm).
5. **Recommendation constraints** — e.g. in CRISIS mode: `allow_aggressive_signals=false`, max position size 10%, min confidence 75.

### 4.3 Explainable AI (SHAP-style reasoning)

**File:** `backend/app/ai_models.py` → `ExplainableAIAnalyzer`

Since true SHAP is heavy, the platform implements a **rule-based explanation engine** that generates human-readable reasons for each signal:

- Trend structure support (bullish/bearish)
- RSI regime (oversold / overbought / momentum)
- MACD histogram confirmation
- Sentiment score direction
- ML up-probability alignment
- Projected price path slope (net % change from current)
- Geopolitical / macro headline context
- Signal alignment strength vs confidence

It also produces a full **geopolitical report** (macro drivers, transmission channels, scenario matrix, stock-specific view) and a graph explanation describing why the forecast line is upward/downward/flat.

---

## 5. Data Pipeline

```
yfinance (prices)
   │
   ▼
Technical Indicators ──► Features ──► ML (LogReg) ──► up_probability
   │
GNews / NewsData / Finnhub / Firecrawl
   │  (async, concurrent, dedup, impact-scored)
   ▼
DistilBERT / Groq ──► Sentiment score
   │
   ▼
┌─────────────────────────────────────────────┐
│  Groq LLM: fuse all inputs → final signal   │
└─────────────────────────────────────────────┘
   │
   ▼
Risk engine (ATR stops, VaR) → price target / stop-loss / confidence
```

Caching (Redis + in-memory) sits over sentiment and market data to cut API costs; 10-min sentiment cache, 5-min default TTL.

---

## 6. Objectives & Goals

### Primary goal
Deliver an **all-in-one intelligent terminal** that lets Indian retail investors make better, more informed, lower-risk trading decisions — without needing institutional tools or a quant background.

### What the AI is trying to achieve
1. **Predict short-term direction** — "Will this stock go up in the next 3–5 periods?" via logistic regression, backed by deep-learning price paths.
2. **Explain every signal** — every recommendation comes with reasons, key factors, confidence, and geopolitical context (no black box).
3. **Adapt to market conditions** — the system becomes defensive in volatile/crisis regimes and more aggressive in clear bull trends, guarding the user's capital.
4. **Personalize to the user** — recommendations respect the user's risk tolerance, portfolio beta, and holdings.
5. **Manage risk like an institution** — ATR-based stops, VaR/CVaR, portfolio beta/concentration checks, and risk-reward framing.

### Practical outcomes delivered to the user
- BUY / SELL / HOLD recommendation with confidence %
- 5-period forecast chart (historical + predicted line)
- Price target and stop-loss suggestions
- Why-it-happened reasoning + transparency panel
- Portfolio health alerts (drawdowns, beta, concentration)
- Regime-aware UI (war-room mode during stress)

---

## 7. Key File References

| Component | File |
|-----------|------|
| Logistic Regression signal model | `backend/app/ml_model.py` |
| LSTM / Transformer / Explainable AI | `backend/app/ai_models.py` |
| Groq LLM predictor | `backend/app/ai_predictor.py` |
| Agent Brain (regime adaptation) | `backend/app/agent_brain.py` |
| Sentiment (DistilBERT + LLM + fallback) | `backend/app/sentiment.py` |
| RL portfolio optimization | `backend/app/rl_portfolio.py` |
| Quantitative risk metrics (VaR, Sharpe...) | `backend/app/quantitative_analysis.py` |
| Backtesting engine | `backend/app/backtest_engine.py`, `backend/app/backtester.py` |
| Options analysis (Greeks) | `backend/app/options_analyzer.py` |
| API routes for AI features | `backend/app/ai_routes.py` |
| Trained model artifacts | `backend/models/*.pkl` |

---

## 8. Limitations & Fallbacks

| Scenario | Behavior |
|----------|----------|
| No TensorFlow installed | LSTM / Transformer gracefully disabled |
| Groq API down / rate-limited | Weighted rule-based fallback predictor |
| DistilBERT fails to load | Keyword-based sentiment fallback |
| No news API keys | Hard-coded market update fallbacks |
| Insufficient training data (< 50 samples) | Neutral prediction (up_prob 50%) |
| No `model.pkl` present | Neutral prediction until model is trained |

Every AI component has a non-AI fallback, so the platform remains functional even when external services or heavy models are unavailable.