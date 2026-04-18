# AI Stock Analysis Assistant 📈

A professional-grade AI-powered stock analysis platform for Indian markets with real-time sentiment analysis, technical indicators, and machine learning predictions.

## ⚠️ Disclaimer

This tool is for **educational purposes only** and does not constitute financial advice. Stock market investments are subject to market risks. Please consult a SEBI-registered financial advisor before making investment decisions.

## Features 🚀

### Core Analysis
- **Technical Analysis**: RSI, MACD, Bollinger Bands, Fibonacci retracements, Pivots
- **Fundamental Analysis**: P/E ratio, dividend yield, financial health scoring
- **Sentiment Analysis**: Real-time news sentiment using DistilBERT and Gemini AI
- **AI Predictions**: LSTM and Transformer-based price forecasting
- **Risk Management**: Position sizing, VaR calculation, drawdown analysis

### Advanced Features
- **Institutional Dashboard**: Volatility regime, Monte Carlo simulations, portfolio optimization
- **Real-time Alerts**: Price thresholds and sentiment-based notifications
- **Backtesting Engine**: RSI, MACD, and custom strategy testing
- **Options Analysis**: Greeks calculation and option recommendations
- **Multi-timeframe Analysis**: Intraday, swing trading, and long-term perspectives
- **Explainable AI**: SHAP-based feature importance and reasoning

### Data Integration
- **APIs**: Finnhub, NewsData, Gemini AI, Sarvam AI
- **Real-time Data**: Market indices, live ticker data, WebSocket updates
- **News Sources**: Multiple news feeds with sentiment analysis

## Tech Stack 🛠️

### Backend
- **Framework**: FastAPI (Python 3.8+)
- **Database**: Supabase (PostgreSQL)
- **Real-time**: WebSockets
- **ML Models**: TensorFlow, PyTorch, Scikit-learn
- **NLP**: HuggingFace Transformers (DistilBERT)
- **APIs**: Finnhub, NewsData, Gemini, Sarvam

### Frontend
- **HTML/CSS/JavaScript**: Vanilla JS with Chart.js
- **Architecture**: Modular, responsive design
- **Features**: Professional dashboard UI, real-time updates

## Quick Start 🚀

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ai-stock-analysis.git
cd ai-stock-analysis
```

2. **Create virtual environment**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
FINNHUB_API_KEY=your_finnhub_key
NEWSDATA_API_KEY=your_newsdata_key
GEMINI_API_KEY=your_gemini_key
SARVAM_API_KEY=your_sarvam_key
DATABASE_URL=postgresql://user:password@host/db
SECRET_KEY=your_secret_key_here
```

5. **Run the application**
```bash
python run.py
```

Access at: `http://localhost:8000`

## Usage 🎯

### Basic Analysis
1. Navigate to Analysis Terminal
2. Enter stock symbol (e.g., `HDFCBANK.NS` for NSE, `RELIANCE.BO` for BSE)
3. Select analysis mode:
   - **Intraday**: 5-minute candles, quick decisions
   - **Swing**: Daily candles, 2-4 week horizons
   - **Long-term**: Weekly candles, 6+ month outlook
4. Click "Execute Quantitative Analysis"
5. Review recommendations and metrics

### Understanding Results

**Recommendation**: BUY / SELL / HOLD
- **Composite Score** (0-100): Overall strength of recommendation
- **Technical Score**: Technical indicators analysis
- **Fundamental Score**: Company health and metrics
- **Sentiment Score**: News sentiment analysis

## Project Structure 📁

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI application
│   │   ├── auth.py                      # Authentication & JWT
│   │   ├── database.py                  # Database configuration
│   │   ├── cache.py                     # Caching & rate limiting
│   │   ├── indicators.py                # Technical indicators
│   │   ├── sentiment_analysis.py        # News sentiment analysis
│   │   ├── quantitative_analysis.py     # Quant metrics
│   │   ├── ml_predictor.py              # AI predictions (LSTM, Transformer)
│   │   ├── portfolio_optimizer.py       # Portfolio optimization
│   │   ├── options_analyzer.py          # Options analysis
│   │   ├── pro_dashboard.py             # Professional dashboard
│   │   └── websocket_manager.py         # Real-time WebSockets
│   └── requirements.txt
│
├── frontend/
│   ├── index.html                       # Landing page
│   ├── analysis.html                    # Analysis terminal
│   ├── auth.html                        # Login page
│   ├── data-sources.html                # API documentation
│   ├── static/
│   │   ├── css/
│   │   │   ├── style.css                # Main styles
│   │   │   └── pro-theme.css            # Professional theme
│   │   └── js/
│   │       ├── app.js                   # Landing page logic
│   │       ├── analysis.js              # Analysis logic
│   │       ├── auth.js                  # Authentication logic
│   │       └── dashboard.js             # Dashboard logic
│   └── package.json
│
├── tests/                               # Test suite
├── docker-compose.yml                   # Docker configuration
├── Dockerfile                           # Container image
├── run.py                               # Application entry point
├── requirements.txt                     # Python dependencies
└── README.md                            # This file
```

## API Endpoints 📡

### Analysis
- `GET /api/professional/analyze` - Comprehensive stock analysis
- `GET /api/professional/dashboard` - Institutional dashboard data

### Predictions
- `GET /api/ai/lstm/train` - Train LSTM model
- `GET /api/ai/transformer/train` - Train Transformer model
- `GET /api/ai/portfolio/optimize` - Optimize portfolio
- `GET /api/ai/explainability` - Get AI reasoning

### News & Sentiment
- `GET /api/sentiment/{symbol}` - Get sentiment analysis
- `GET /api/news/{symbol}` - Get recent news

### Backtesting
- `GET /api/backtest/rsi` - Backtest RSI strategy
- `GET /api/backtest/macd` - Backtest MACD strategy

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/refresh` - Refresh token

## Configuration 🔧

### Environment Variables
```env
# API Keys (required)
FINNHUB_API_KEY=your_key
NEWSDATA_API_KEY=your_key
GEMINI_API_KEY=your_key
SARVAM_API_KEY=your_key

# Database
DATABASE_URL=postgresql://user:password@host/db

# Application
SECRET_KEY=your_secret_key
PORT=8000
HOST=0.0.0.0
APP_RELOAD=false

# Optional
REDIS_URL=redis://localhost:6379
```

## Performance ⚡

- Fast mode analysis: < 5 seconds
- Standard analysis: 10-30 seconds (with news fetching)
- Results cached for 1 hour
- Optimized for ~200MB RAM usage
- Single worker for stability

## Troubleshooting 🐛

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### Module Import Errors
```bash
pip install -r requirements.txt --force-reinstall
```

### Memory Issues
- Use fast_mode for quicker analysis
- Reduce concurrent requests
- Ensure single worker is used

## Testing 🧪

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_comprehensive.py -v
```

## Deployment 🚀

### Docker
```bash
docker-compose up -d
```

### Production
1. Use production WSGI server (Gunicorn)
2. Set up HTTPS with Let's Encrypt
3. Configure database backups
4. Enable monitoring and logging

## Contributing 🤝

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Stock Symbols 📊

### NSE (National Stock Exchange)
- Add `.NS` suffix: `RELIANCE.NS`, `HDFCBANK.NS`, `INFY.NS`

### BSE (Bombay Stock Exchange)
- Add `.BO` suffix: `RELIANCE.BO`, `HDFCBANK.BO`

## Roadmap 🗺️

- [ ] Mobile app (React Native)
- [ ] Advanced charting integration
- [ ] Social trading features
- [ ] Discord bot
- [ ] Multi-language support
- [ ] Paper trading
- [ ] Custom indicators

## License 📄

MIT License - See LICENSE file for details

## Support 💬

- 📧 Email: support@example.com
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions

---

**Status**: Production Ready ✅
**Version**: 2.0
**Last Updated**: April 2026
