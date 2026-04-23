# Quant Terminal - AI Stock Analysis Assistant

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Professional-grade AI-powered stock analysis platform for Indian markets (NSE/BSE) with real-time market data, personalized portfolio tracking, and intelligent trading signals.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Screenshots](#screenshots)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

Quant Terminal is a comprehensive web-based stock analysis platform designed for Indian equity markets. It combines real-time market data, advanced technical indicators, machine learning predictions, and news sentiment analysis to provide actionable trading insights.

### Target Users
- **Retail Traders** - Swing trading and intraday analysis
- **Long-term Investors** - Fundamental analysis and portfolio tracking
- **Market Analysts** - Real-time market monitoring and research

### Market Coverage
- **NSE (National Stock Exchange)** - All listed equities and indices
- **BSE (Bombay Stock Exchange)** - Primary indices and securities
- **Major Indices** - NIFTY 50, SENSEX, BANKNIFTY, INDIA VIX

---

## ⭐ Key Features

### 🔮 AI-Powered Analysis
- **Machine Learning Predictions** - SVM-based classification for buy/sell signals
- **Sentiment Analysis** - Real-time news sentiment using transformer models (DistilBERT)
- **Risk Assessment** - Dynamic position sizing based on volatility (ATR)
- **Personalized Recommendations** - Tailored to user's risk tolerance and portfolio

### 📊 Technical Analysis
- **Multi-Timeframe Support** - Intraday (5m), Swing (1d), Long-term (1wk)
- **Comprehensive Indicators**:
  - RSI (Relative Strength Index) with overbought/oversold signals
  - MACD with histogram and divergence detection
  - ATR (Average True Range) for volatility measurement
  - EMA (9, 21, 50 periods) for trend analysis
  - Volume analysis and OBV
  - Stochastic Oscillator
  - Bollinger Bands

### 📈 Real-Time Market Data
- **Live Price Feeds** - Real-time stock prices via Yahoo Finance
- **Market Indices** - NIFTY, SENSEX, BANKNIFTY with live updates
- **Sector Heatmaps** - Visual representation of sector performance
- **Sparkline Charts** - Mini price charts for quick trend visualization

### 💼 Portfolio Management
- **Multi-Stock Portfolios** - Track unlimited positions
- **Real-time P&L** - Unrealized gains/losses with current market prices
- **Sector Allocation** - Visual breakdown by industry sector
- **Transaction History** - Complete buy/sell history with timestamps
- **Cash Management** - Track available cash and total portfolio value
- **Per-User Isolation** - Each user's data is completely separate and secure

### 🔐 Authentication & Security
- **JWT-based Authentication** - Secure token-based login system
- **Supabase Integration** - PostgreSQL backend with Row Level Security
- **Session Management** - 30-minute session expiry with auto-refresh
- **Rate Limiting** - API endpoint protection against abuse

### 📰 News & Sentiment
- **Multi-Source News Aggregation** - GNews, Finnhub, NewsData.io APIs
- **Real-time Sentiment Scoring** - -1 to +1 sentiment scale
- **Impact Analysis** - Article ranking by recency, source authority, and relevance
- **Caching System** - 10-minute sentiment cache to reduce API costs

### 🎨 User Interface
- **Modern Dark Theme** - Professional trading terminal aesthetic
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Interactive Charts** - Chart.js integration with custom styling
- **Real-time Updates** - Auto-refreshing dashboard every 30 seconds
- **Toast Notifications** - Success/error feedback for all actions

---

## 🛠 Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI (Python) | High-performance async API server |
| Data Provider | yfinance | Real-time and historical stock data |
| ML/AI | scikit-learn, transformers | Predictions and sentiment analysis |
| Database | Supabase (PostgreSQL) | User data, profiles, and persistence |
| Cache | Redis + In-Memory | Multi-layer caching for performance |
| Auth | JWT + Supabase Auth | Secure user authentication |
| Async | asyncio, aiohttp | Non-blocking I/O operations |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Structure | HTML5 | Semantic markup |
| Styling | CSS3 + Custom Properties | Theming and responsive layout |
| Scripting | Vanilla JavaScript (ES6+) | No framework dependency |
| Charts | Chart.js | Interactive data visualization |
| Icons | Font Awesome | UI iconography |
| Fonts | Google Fonts (Outfit, JetBrains Mono) | Typography |

### External APIs
| Service | Purpose | Rate Limits |
|---------|---------|-------------|
| Yahoo Finance | Stock prices and historical data | 2000 requests/hour |
| GNews API | News headlines and articles | 100 requests/day (free) |
| Finnhub API | Company news and fundamentals | 60 requests/minute |
| NewsData.io | Alternative news source | 200 requests/day (free) |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Browser    │  │   Mobile     │  │   Tablet     │          │
│  │  (index.html)│  │ (Responsive) │  │  (Responsive) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Server                         │  │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────────────┐  │  │
│  │  │   CORS     │ │ Rate Limit │ │    JWT Auth          │  │  │
│  │  │  Middleware│ │ Middleware │ │   Middleware         │  │  │
│  │  └────────────┘ └────────────┘ └──────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────┐
│   SERVICE LAYER │  │   CACHE      │  │   EXTERNAL   │
│ ┌─────────────┐ │  │   LAYER      │  │   APIs       │
│ │ Portfolio   │ │  │ ┌──────────┐ │  │ ┌──────────┐ │
│ │   Manager   │ │  │ │  Redis   │ │  │ │ Yahoo    │ │
│ └─────────────┘ │  │ │  Cache   │ │  │ │ Finance  │ │
│ ┌─────────────┐ │  │ └──────────┘ │  │ └──────────┘ │
│ │  Sentiment  │ │  │ ┌──────────┐ │  │ ┌──────────┐ │
│ │  Analyzer   │ │  │ │ In-Memory│ │  │ │  GNews   │ │
│ └─────────────┘ │  │ │  Cache   │ │  │ └──────────┘ │
│ ┌─────────────┐ │  │ └──────────┘ │  │ ┌──────────┐ │
│ │  Technical  │ │  └──────────────┘  │ │ Finnhub  │ │
│ │ Indicators  │ │                    │ └──────────┘ │
│ └─────────────┘ │                    │ ┌──────────┐ │
│ ┌─────────────┐ │                    │ │NewsData  │ │
│ │   ML Models │ │                    │ └──────────┘ │
│ │  (SVM, etc) │ │                    └──────────────┘
│ └─────────────┘ │
└─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA PERSISTENCE LAYER                     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                  Supabase (PostgreSQL)                  │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐       │    │
│  │  │  profiles  │  │ portfolios │  │ watchlists │       │    │
│  │  └────────────┘  └────────────┘  └────────────┘       │    │
│  └──────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                  Local File Storage                      │    │
│  │              (data/portfolios/{user_id}.json)           │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💻 Installation

### Prerequisites
- Python 3.8 or higher
- Node.js 14+ (optional, for frontend development)
- Redis (optional, for caching)
- Git

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/quant-terminal.git
cd quant-terminal
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables
Create a `.env` file in the project root:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# External APIs
NEWSDATA_API_KEY=your-newsdata-key
GNEWS_API_KEY=your-gnews-key
FINNHUB_API_KEY=your-finnhub-key
GEMINI_API_KEY=your-gemini-key

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# App Configuration
DEBUG=false
PORT=8001
```

### Step 5: Initialize Database
1. Create a Supabase project at https://supabase.com
2. Run the SQL migrations in `backend/sql/`
3. Set up authentication providers (Email, Google, etc.)

### Step 6: Run the Application
```bash
# Start the backend server
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# In another terminal, you can serve the frontend (optional)
# The backend already serves static files, but for development:
cd frontend
python -m http.server 8080
```

### Step 7: Access the Application
- **Web App**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs (Swagger UI)
- **API Redoc**: http://localhost:8001/redoc

---

## ⚙ Configuration

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Yes |
| `NEWSDATA_API_KEY` | NewsData.io API key | No* |
| `GNEWS_API_KEY` | GNews API key | No* |
| `FINNHUB_API_KEY` | Finnhub API key | No* |

*At least one news API key is recommended for sentiment analysis

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `PORT` | `8001` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini AI model name |
| `CACHE_TTL` | `300` | Default cache TTL in seconds |

---

## 🚀 Usage

### First-Time Setup
1. Register a new account at `/auth.html`
2. Complete the portfolio setup wizard at `/setup.html`
3. Set your risk tolerance and preferred trading strategy
4. Add initial cash balance and holdings

### Daily Workflow
1. **Check Market Overview** - Visit homepage for real-time indices and heatmap
2. **Analyze Stocks** - Use `/analysis.html` for detailed technical analysis
3. **Manage Portfolio** - Track P&L at `/portfolio.html`
4. **Get AI Insights** - View personalized recommendations

### Trading Modes
- **Intraday** - 5-minute charts, fast signals, tight stops
- **Swing** - Daily charts, medium-term holds, ATR-based stops
- **Long-term** - Weekly charts, fundamental focus, wide stops

---

## 📚 API Documentation

### Authentication Endpoints
```
POST /auth/v1/token?grant_type=password    # Login
POST /auth/v1/signup                       # Register
POST /auth/v1/logout                       # Logout
POST /auth/v1/refresh                      # Refresh token
```

### Analysis Endpoints
```
GET /api/analyze?symbol=RELIANCE.NS&mode=swing    # Analyze stock
GET /api/sentiment/{symbol}                        # Get sentiment
GET /api/fundamental/{symbol}                      # Fundamental analysis
```

### Portfolio Endpoints
```
GET  /api/portfolio/setup           # Get setup status
POST /api/portfolio/setup           # Save portfolio setup
POST /api/portfolio/buy             # Buy shares
POST /api/portfolio/sell            # Sell shares
GET  /api/portfolio/summary         # Get portfolio summary
GET  /api/portfolio/recommendations # AI recommendations
```

### Market Data Endpoints
```
GET /api/landing-data               # Public market data
GET /api/landing-data/personalized  # Personalized data (auth required)
GET /api/sparklines                 # Sparkline charts
GET /api/market/indices             # Market indices
GET /api/market/top-gainers         # Top gainers/losers
```

### User Endpoints
```
GET  /api/user/preferences          # Get preferences
POST /api/user/preferences          # Save preferences
GET  /api/user/profile              # Get profile
PUT  /api/user/profile              # Update profile
```

For complete API documentation, visit `/docs` when the server is running.

---

## 📁 Project Structure

```
quant-terminal/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── sentiment.py            # News sentiment analysis
│   │   ├── indicators.py           # Technical indicators
│   │   ├── ml_model.py             # Machine learning models
│   │   ├── portfolio.py            # Portfolio management
│   │   ├── supabase_portfolio.py   # User portfolio management
│   │   ├── supabase_auth.py        # Authentication
│   │   ├── cache.py                # Redis + in-memory caching
│   │   ├── fundamental_analysis.py # Fundamental data
│   │   ├── realtime.py             # WebSocket real-time data
│   │   └── personalized_trading.py # Personalized recommendations
│   ├── sql/
│   │   └── 001_initial_schema.sql  # Database migrations
│   └── requirements.txt
│
├── frontend/
│   ├── index.html                  # Homepage / Dashboard
│   ├── analysis.html               # Stock analysis terminal
│   ├── portfolio.html              # Portfolio management
│   ├── dashboard.html              # User dashboard
│   ├── setup.html                  # Portfolio setup wizard
│   ├── auth.html                   # Login/register
│   ├── data-sources.html           # API documentation
│   └── static/
│       ├── css/
│       │   ├── style.css           # Main stylesheet
│       │   └── pro-theme.css       # Dark theme variables
│       └── js/
│           ├── app.js              # Main application logic
│           ├── analysis.js         # Analysis page logic
│           └── auth.js             # Authentication logic
│
├── data/
│   └── portfolios/                 # Local portfolio storage
│       └── {user_id}.json
│
├── .env.example                    # Environment template
├── .gitignore
├── LICENSE
└── README.md                       # This file
```

---

## 🗄 Database Schema

### Profiles Table
```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    email TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    risk_tolerance TEXT DEFAULT 'medium',
    preferred_strategy TEXT DEFAULT 'swing',
    capital DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Watchlists Table
```sql
CREATE TABLE watchlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id),
    symbol TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Alerts Table
```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id),
    symbol TEXT NOT NULL,
    alert_type TEXT NOT NULL,  -- price, rsi, sentiment
    condition TEXT NOT NULL, -- above, below
    threshold DECIMAL(10,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 📸 Screenshots

### Homepage Dashboard
![Homepage](screenshots/homepage.png)
*Real-time market indices, sector heatmap, and sparkline charts*

### Stock Analysis Terminal
![Analysis](screenshots/analysis.png)
*Technical indicators, sentiment analysis, and AI predictions*

### Portfolio Management
![Portfolio](screenshots/portfolio.png)
*Track positions, P&L, and sector allocation*

### Portfolio Setup
![Setup](screenshots/setup.png)
*Onboarding wizard for new users*

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the Repository**
2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make Your Changes**
4. **Run Tests**
   ```bash
   pytest backend/tests/
   ```
5. **Commit Changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
6. **Push to Branch**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request**

### Contribution Guidelines
- Follow PEP 8 style guide for Python code
- Use ESLint for JavaScript
- Add tests for new features
- Update documentation
- Ensure backwards compatibility

---

## 🔒 Security

- All API endpoints use JWT authentication
- Row Level Security (RLS) enabled in Supabase
- Rate limiting on sensitive endpoints
- Input validation and sanitization
- CORS protection configured
- No sensitive data in localStorage (except auth token)

### Reporting Security Issues
Please report security vulnerabilities to security@quantterminal.com

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Yahoo Finance** for market data
- **Supabase** for backend infrastructure
- **FastAPI** team for the amazing framework
- **Hugging Face** for transformer models
- **Chart.js** for visualization

---

## 📞 Support

- **Email**: support@quantterminal.com
- **Discord**: [Join our community](https://discord.gg/quantterminal)
- **Issues**: [GitHub Issues](https://github.com/yourusername/quant-terminal/issues)

---

## 🗺 Roadmap

### Q1 2025
- [ ] Mobile app (React Native)
- [ ] Options chain analysis
- [ ] Backtesting engine
- [ ] Paper trading

### Q2 2025
- [ ] Multi-asset support (Crypto, Forex)
- [ ] Social trading features
- [ ] Advanced charting (TradingView integration)
- [ ] Alert system overhaul

### Q3 2025
- [ ] AI-powered trade journal analysis
- [ ] Strategy builder
- [ ] Community features
- [ ] Premium subscription tier

---

<p align="center">
  Made with ❤️ by the Quant Terminal Team
</p>

<p align="center">
  <a href="https://twitter.com/quantterminal">Twitter</a> •
  <a href="https://linkedin.com/company/quantterminal">LinkedIn</a> •
  <a href="https://youtube.com/quantterminal">YouTube</a>
</p>
