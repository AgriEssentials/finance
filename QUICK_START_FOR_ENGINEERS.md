# Quick Start Guide for New Engineers

> A very simple explanation of how this project is built and how it works.
> Read this first. It takes about 2 minutes.

---

## 1. The Big Picture

This is **one app**, not many apps. It has two parts:

- **Backend** — a Python server (FastAPI). It does all the thinking and all the math.
- **Frontend** — simple web pages (HTML/CSS/JavaScript). They just show the results.

The frontend is served by the backend itself. So you run **one server**, and it does everything.

```
User opens browser
        │
        ▼
  ┌─────────────────┐
  │  FastAPI Server │   ← the whole app lives here
  │  (Python)       │
  └─────────────────┘
        │
        ▼
  Shows results in the browser
```

---

## 2. Where Everything Lives

Everything important is inside one folder:

```
backend/app/   ← all the code
```

`main.py` is the front door. It has all the web routes (the URLs the app answers to). It is a big file, but you don't need to read it all — just know it is the entry point.

There is no complicated structure. No microservices. No separate services. One folder, one server.

---

## 3. How One Request Travels Through the App

When a user asks to analyze a stock, the app follows the same steps every time. This is the most important thing to understand:

```
1. Get the price history (from Yahoo Finance)
        │
        ▼
2. Calculate technical indicators (RSI, MACD, ATR, etc.)
        │
        ▼
3. Ask the machine-learning model: "will the price go up or down?"
        │
        ▼
4. Read the news and measure the mood (positive / negative)
        │
        ▼
5. Calculate risk (where to put the stop-loss)
        │
        ▼
6. Combine ALL of the above and ask an AI (Groq LLM)
   to give one final answer: BUY / SELL / HOLD, plus confidence
```

If you understand these 6 steps, you understand how the whole app works.

---

## 4. The AI Parts, Explained Simply

The project uses several "brains." Each one has one job. They are separate files so they stay simple.

| File | What it does | Plain explanation |
|------|--------------|-------------------|
| `ml_model.py` | Logistic Regression | "Should I bet on the price going up?" → yes/no with a probability |
| `ai_models.py` | LSTM + Transformer | Deep-learning models that draw the future price line on the chart |
| `rl_portfolio.py` | Q-Learning (RL) | "How much of my money should go into this stock?" → 0% / 25% / 50% / 75% / 100% |
| `sentiment.py` | DistilBERT + LLM | Reads news headlines and says "this news is positive/negative" |
| `ai_predictor.py` | Groq LLM | The main brain. Reads all the other results and writes the final recommendation in plain language |
| `agent_brain.py` | Rule-based "agent" | Watches the whole market. If things get crazy, it tells the app to be more careful |

**How they connect:**

```
Technical indicators ──► ML model ──► "55% chance of going up"
News ──► Sentiment ──► "news is positive"
Risk data ──► "keep a stop-loss at this price"
                  │
                  ▼
     Groq LLM combines everything
                  │
                  ▼
     Final answer: BUY (72% confident), target price ₹X
```

---

## 5. The Most Important Rule: Nothing Breaks the App

Every AI piece has a **backup plan**. If something fails, the app still works:

- Groq (AI) is down → a simple rule-based calculator gives the answer instead
- No TensorFlow installed → LSTM/Transformer are skipped
- DistilBERT fails to load → keyword matching gives a rough sentiment
- No news API keys → the app shows basic market updates

So you will see lots of `try/except` and "fallback" code. That is **on purpose**. This app is built so it never crashes just because an outside service is unavailable.

---

## 6. Setup Is Done Through a `.env` File

The app reads its settings (API keys, database URL) from a file called `.env`.

If the keys are missing, the app still starts — it just runs with less data and more fallbacks.

---

## 7. Where to Start Reading

Open these files in this order. That's it:

1. `backend/app/main.py` — go to the `/api/analyze` function. It shows the whole flow.
2. `backend/app/ml_model.py` — the simplest ML model.
3. `backend/app/ai_predictor.py` — how the AI brain works.
4. `backend/app/agent_brain.py` — how the app adapts to market conditions.

---

## 8. TL;DR (One Paragraph)

This is a single FastAPI app for analyzing Indian stocks. A request goes through a fixed chain: price data → technical indicators → machine-learning prediction → news sentiment → risk → an AI brain that writes the final BUY/SELL/HOLD answer. Each AI component lives in its own file and has a non-AI fallback so the app never breaks. Read `main.py` → `/api/analyze` first, and you'll understand the entire architecture.