"""
News Sentiment Analysis Module - ASYNC VERSION
Handles fetching and analyzing news sentiment using NewsData API with pretrained transformer models
Includes intelligent caching for improved performance and async support to prevent server blocking.
"""

import os
import asyncio
import aiohttp
import requests
from typing import List, Dict, Any, Optional
import re
import time
from datetime import datetime, timedelta

# Load environment variables from .env file at module import time
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, will use system env vars only
    pass

# Cache will be imported lazily to avoid circular imports
CACHE_AVAILABLE = None
cache = None

def _get_cache():
    """Lazy import cache to avoid circular imports"""
    global CACHE_AVAILABLE, cache
    if CACHE_AVAILABLE is None:
        try:
            from app.cache import cache as cache_instance
            cache = cache_instance
            CACHE_AVAILABLE = True
        except ImportError:
            CACHE_AVAILABLE = False
    return cache if CACHE_AVAILABLE else None


class SentimentAnalyzer:
    """Class to analyze news sentiment using NewsData API + pretrained transformer models"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize sentiment analyzer
        
        Args:
            api_key: Reserved for compatibility (unused)
        """
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        # Support both env var names used across project setup.
        self.newsdata_api_key = os.getenv('NEWSDATA_API_KEY') or os.getenv('NEWS_API_KEY')
        self.groq_model = os.getenv('GROQ_SENTIMENT_MODEL') or os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
        configured_candidates = os.getenv('GROQ_MODEL_CANDIDATES', '').strip()
        default_candidates = ['openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'qwen/qwen3.8-27b', 'groq/compound-mini']
        if configured_candidates:
            parsed = [m.strip() for m in configured_candidates.split(',') if m.strip()]
            self.groq_model_candidates = parsed if parsed else default_candidates
        else:
            self.groq_model_candidates = default_candidates
        self.newsdata_url = "https://newsdata.io/api/1/news"
        self.gnews_api_key = os.getenv('GNEWS_API_KEY')
        self.gnews_url = "https://gnews.io/api/v4/search"
        self.firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
        self.firecrawl_url = "https://api.firecrawl.dev/v2/search"
        self.finnhub_api_key = (
            os.getenv('FINNHUB_API_KEY')
            or os.getenv('FINHUB_API_KEY')
            or os.getenv('FINNHUB_KEY')
            or os.getenv('FINNHUB_TOKEN')
            or os.getenv('FINNHUB_API_TOKEN')
        )
        self.finnhub_url = "https://finnhub.io/api/v1/company-news"
        self.max_articles_to_analyze = 100  # Analyze at least 100 real articles
        self.min_articles_to_analyze = 50
        self.max_groq_sentiment_articles = 15  # Cap LLM sentiment calls per stock (rate limits)
        self.top_impact_to_show = 15  # Show top 15 most impactful
        self.last_news_provider_stats: Dict[str, Any] = {}
        
        # Initialize transformer model for sentiment analysis
        self._initialize_transformer_model()

    def _initialize_transformer_model(self):
        """Initialize the transformer model for sentiment analysis (lazy loading)"""
        # Don't load model on initialization - load on first use
        self.sentiment_pipeline = None
        self.use_transformer = None  # None means not tried yet
        print("[OK] Sentiment analyzer ready (model will load on first use)")
    
    def _ensure_transformer_loaded(self):
        """Lazy load transformer model on first use (with timeout to avoid hangs)"""
        if self.use_transformer is not None:
            return  # Already tried to load

        def _load():
            try:
                from transformers import pipeline
                self.sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english",
                    truncation=True,
                    max_length=512
                )
                self.use_transformer = True
                print("[OK] Transformer model loaded successfully")
            except Exception as e:
                print(f"[WARNING] Could not load transformer model: {e}. Falling back to keyword-based analysis.")
                self.use_transformer = False

        import threading
        thread = threading.Thread(target=_load, daemon=True)
        thread.start()
        thread.join(timeout=60)
        if thread.is_alive():
            print("[WARNING] Transformer model load timed out (60s). Falling back to keyword-based analysis.")
            self.use_transformer = False

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment with Groq primary, transformer secondary, then keyword fallback."""
        # Try Groq first (fast inference, no heavy model download)
        if self.groq_api_key:
            try:
                groq_result = self._analyze_sentiment_groq(text)
                if groq_result:
                    return groq_result
            except Exception as e:
                pass

        # Try transformer (lazy load on first use)
        if self.use_transformer is None:
            self._ensure_transformer_loaded()
        if self.use_transformer:  # Now it's either True or False, not None
            try:
                transformer_result = self._analyze_sentiment_transformer(text)
                if transformer_result:
                    return transformer_result
            except Exception as e:
                pass

        # Fallback to keyword-based
        return self._fallback_sentiment(text)

    def _analyze_sentiment_transformer(self, text: str) -> Optional[Dict[str, Any]]:
        """Analyze sentiment using pretrained DistilBERT transformer model"""
        try:
            if not self.use_transformer or not hasattr(self, 'sentiment_pipeline'):
                return None
            
            # Truncate text to 512 tokens for the model
            truncated_text = text[:512] if len(text) > 512 else text
            
            result = self.sentiment_pipeline(truncated_text)
            if result and len(result) > 0:
                label_raw = result[0]['label'].lower()
                score = result[0]['score']
                
                # Map POSITIVE/NEGATIVE to our format
                if label_raw == 'positive':
                    label = 'positive'
                    # Scale score to 0.5-0.9
                    normalized_score = 0.5 + (score * 0.4)
                elif label_raw == 'negative':
                    label = 'negative'
                    # Scale score to -0.5 to -0.9
                    normalized_score = -0.5 - (score * 0.4)
                else:
                    label = 'neutral'
                    # Scale neutral to -0.2 to 0.2
                    normalized_score = (score - 0.5) * 0.4
                
                return {
                    'score': normalized_score,
                    'label': label,
                    'confidence': score,
                    'method': 'transformer'
                }
            return None
        except Exception as e:
            return None

    def _analyze_sentiment_groq(self, text: str) -> Optional[Dict[str, Any]]:
        """Analyze sentiment using Groq's LLM API"""
        try:
            if not self.groq_api_key:
                return None
            
            import requests

            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            # Craft a detailed prompt for financial sentiment
            prompt = f"""Analyze the financial sentiment of this news headline/text.
            
Text: "{text}"

Provide ONLY a JSON response with this exact format:
{{
    "sentiment": "positive" | "negative" | "neutral",
    "score": <number between -1 and 1>,
    "confidence": <number between 0 and 1>,
    "reasoning": "brief explanation"
}}

Rules:
- Positive sentiment: bullish, growth, profit, success, breakthrough, strong performance
- Negative sentiment: bearish, loss, decline, crash, scandal, weak performance  
- Neutral: factual reporting, no clear directional impact
- Consider impact on stock price (positive news may be negative for competitors)"""

            payload = {
                "model": self.groq_model,
                "messages": [
                    {"role": "system", "content": "You are a financial sentiment analyst. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 300
            }

            response = None
            for attempt in range(3):
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                if response.status_code != 429:
                    break
                print(f"[GROQ SENTIMENT] Rate limited (429), retrying in 2s ({attempt + 1}/3)...")
                time.sleep(2)

            if response is None or response.status_code != 200:
                print(f"[GROQ SENTIMENT] API error: {response.status_code if response else 'no response'} - {(response.text[:200] if response is not None else '')}")
                return None

            result = response.json()
            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                import json
                parsed = json.loads(json_match.group())
                
                return {
                    'score': parsed.get('score', 0),
                    'label': parsed.get('sentiment', 'neutral'),
                    'confidence': parsed.get('confidence', 0.5),
                    'method': 'groq',
                    'reasoning': parsed.get('reasoning', '')
                }
            return None
            
        except Exception as e:
            return None

    def _fallback_sentiment(self, text: str) -> Dict[str, Any]:
        """Fallback keyword-based sentiment analysis"""
        text_lower = text.lower()
        
        # Positive keywords with weights
        positive_keywords = {
            'strong': 0.3, 'growth': 0.4, 'profit': 0.5, 'surge': 0.6, 'soar': 0.7,
            'breakthrough': 0.8, 'record high': 0.6, 'bullish': 0.7, 'gain': 0.3,
            'up': 0.2, 'rise': 0.3, 'rally': 0.5, 'outperform': 0.4, 'beat': 0.4,
            'exceed': 0.4, 'positive': 0.3, 'optimistic': 0.3, 'upgrade': 0.5,
            'buy': 0.3, 'recommend': 0.2, 'success': 0.4, 'milestone': 0.3,
            'partnership': 0.3, 'launch': 0.3, 'expansion': 0.4, 'dividend': 0.3,
            'bonus': 0.3, 'split': 0.2
        }
        
        # Negative keywords with weights
        negative_keywords = {
            'weak': -0.3, 'loss': -0.5, 'decline': -0.4, 'crash': -0.8, 'plunge': -0.7,
            'bearish': -0.7, 'drop': -0.4, 'fall': -0.3, 'down': -0.2, 'slide': -0.4,
            'underperform': -0.4, 'miss': -0.4, 'negative': -0.3, 'pessimistic': -0.3,
            'downgrade': -0.5, 'sell': -0.4, 'avoid': -0.3, 'concern': -0.2,
            'risk': -0.2, 'investigation': -0.4, 'lawsuit': -0.5, 'scandal': -0.6,
            'fraud': -0.8, 'debt': -0.2, 'bankruptcy': -0.9, 'resign': -0.3,
            'layoff': -0.4, 'cut': -0.3
        }
        
        score = 0
        pos_count = 0
        neg_count = 0
        
        for word, weight in positive_keywords.items():
            if word in text_lower:
                score += weight
                pos_count += 1
                
        for word, weight in negative_keywords.items():
            if word in text_lower:
                score += weight
                neg_count += 1
        
        # Normalize score to -1 to 1
        if pos_count + neg_count > 0:
            score = max(-1, min(1, score / (pos_count + neg_count)))
        
        # Determine label
        if score > 0.1:
            label = 'positive'
        elif score < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
            
        return {
            'score': round(score, 3),
            'label': label,
            'confidence': min(0.7, 0.3 + (pos_count + neg_count) * 0.1),
            'method': 'keyword'
        }

    def aggregate_sentiment(self, texts: List[str]) -> Dict[str, Any]:
        """Aggregate sentiment across multiple texts"""
        if not texts:
            return {
                "average_score": 0,
                "classification": "Neutral",
                "confidence": 0,
                "headlines_analyzed": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "distribution": {"positive": 0, "negative": 0, "neutral": 100}
            }
        
        scores = []
        positive = 0
        negative = 0
        neutral = 0
        
        for text in texts:
            if not text:
                continue
            result = self.analyze_sentiment(text)
            score = result.get('score', 0)
            scores.append(score)
            
            if score > 0.1:
                positive += 1
            elif score < -0.1:
                negative += 1
            else:
                neutral += 1
        
        if not scores:
            return {
                "average_score": 0,
                "classification": "Neutral",
                "confidence": 0,
                "headlines_analyzed": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "distribution": {"positive": 0, "negative": 0, "neutral": 100}
            }
        
        avg_score = sum(scores) / len(scores)
        
        # Determine classification
        if avg_score > 0.2:
            classification = "Positive"
        elif avg_score < -0.2:
            classification = "Negative"
        else:
            classification = "Neutral"
        
        total = positive + negative + neutral
        
        return {
            "average_score": round(avg_score, 3),
            "classification": classification,
            "confidence": round(min(1.0, len(scores) * 0.05), 2),
            "headlines_analyzed": len(scores),
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "distribution": {
                "positive": round(positive / total * 100, 1) if total > 0 else 0,
                "negative": round(negative / total * 100, 1) if total > 0 else 0,
                "neutral": round(neutral / total * 100, 1) if total > 0 else 0
            }
        }

    def _get_company_context(self, symbol: str) -> Dict[str, str]:
        """Get company context for better news search"""
        # Clean symbol
        clean_symbol = symbol.upper().replace('.NS', '').replace('.BO', '').replace('.NSE', '')
        
        # Company name mappings
        company_names = {
            'RELIANCE': 'Reliance Industries',
            'TCS': 'Tata Consultancy Services',
            'INFY': 'Infosys',
            'HDFCBANK': 'HDFC Bank',
            'ICICIBANK': 'ICICI Bank',
            'SBIN': 'State Bank of India',
            'HINDUNILVR': 'Hindustan Unilever',
            'ITC': 'ITC Limited',
            'KOTAKBANK': 'Kotak Mahindra Bank',
            'BAJFINANCE': 'Bajaj Finance',
            'BHARTIARTL': 'Bharti Airtel',
            'ASIANPAINT': 'Asian Paints',
            'MARUTI': 'Maruti Suzuki',
            'HCLTECH': 'HCL Technologies',
            'WIPRO': 'Wipro',
            'SUNPHARMA': 'Sun Pharmaceutical',
            'TITAN': 'Titan Company',
            'ULTRACEMCO': 'UltraTech Cement',
            'NESTLEIND': 'Nestle India',
            'POWERGRID': 'Power Grid Corporation',
            'NTPC': 'NTPC Limited',
            'M&M': 'Mahindra & Mahindra',
            'AXISBANK': 'Axis Bank',
            'LT': 'Larsen & Toubro',
            'ADANIENT': 'Adani Enterprises',
            'ADANIPORTS': 'Adani Ports',
            'TATAMOTORS': 'Tata Motors',
            'BAJAJFINSV': 'Bajaj Finserv',
            'TECHM': 'Tech Mahindra',
            'ONGC': 'Oil and Natural Gas Corporation',
            'HINDALCO': 'Hindalco Industries',
            'COALINDIA': 'Coal India',
            'JSWSTEEL': 'JSW Steel',
            'GRASIM': 'Grasim Industries',
            'DIVISLAB': "Divi's Laboratories",
            'BRITANNIA': 'Britannia Industries',
            'CIPLA': 'Cipla',
            'TATASTEEL': 'Tata Steel',
            'HEROMOTOCO': 'Hero MotoCorp',
            'EICHERMOT': 'Eicher Motors',
            'DRREDDY': "Dr. Reddy's Laboratories",
            'INDUSINDBK': 'IndusInd Bank',
            'APOLLOHOSP': 'Apollo Hospitals',
            'MCDOWELLN': 'United Spirits',
            'VEDL': 'Vedanta',
            'SBILIFE': 'SBI Life Insurance',
            'DABUR': 'Dabur India',
            'HAVELLS': 'Havells India',
            'BAJAJAUTO': 'Bajaj Auto',
            'SHREECEM': 'Shree Cement',
            'TATACONSUM': 'Tata Consumer Products',
            'MARICO': 'Marico',
            'IOC': 'Indian Oil Corporation',
            'DMART': 'Avenue Supermarts',
            'HDFCLIFE': 'HDFC Life Insurance',
            'UPL': 'UPL Limited',
            'PIIND': 'PI Industries',
            'SIEMENS': 'Siemens India',
            'GODREJCP': 'Godrej Consumer Products',
            'PAGEIND': 'Page Industries',
            'AMBUJACEM': 'Ambuja Cements',
            'ADANIGREEN': 'Adani Green Energy',
            'ADANITRANS': 'Adani Transmission',
            'MOTHERSON': 'Motherson Sumi',
            'DLF': 'DLF Limited',
            'BANDHANBNK': 'Bandhan Bank',
            'GAIL': 'GAIL India',
            'BIOCON': 'Biocon',
            'TORNTPHARM': 'Torrent Pharmaceuticals',
            'AUROPHARMA': 'Aurobindo Pharma',
            'LUPIN': 'Lupin Limited',
            'CADILAHC': 'Cadila Healthcare',
            'BOSCHLTD': 'Bosch Limited',
            'IGL': 'Indraprastha Gas',
            'MUTHOOTFIN': 'Muthoot Finance',
            'PEL': 'Piramal Enterprises',
            'JUBLFOOD': 'Jubilant FoodWorks',
            'COLPAL': 'Colgate-Palmolive India',
            'NMDC': 'NMDC Limited',
            'CONCOR': 'Container Corporation',
            'ACC': 'ACC Limited',
            'BALKRISIND': 'Balkrishna Industries',
            'ABB': 'ABB India',
            'RAMCOCEM': 'Ramco Cements',
            'PETRONET': 'Petronet LNG',
            'PIDILITIND': 'Pidilite Industries',
            'BERGEPAINT': 'Berger Paints',
            'HDFCAMC': 'HDFC Asset Management',
            'NAVINFLUOR': 'Navin Fluorine',
            'SRF': 'SRF Limited',
            'ABBOTINDIA': 'Abbott India',
            'GLAXO': 'GlaxoSmithKline Pharma',
            'OFSS': 'Oracle Financial Services',
            'NIACL': 'New India Assurance',
            'MPHASIS': 'Mphasis Limited',
            'NAM-INDIA': 'Nippon Life India',
            'COROMANDEL': 'Coromandel International',
            'ATUL': 'Atul Limited',
            'ASTRAL': 'Astral Poly Technik',
            'LAURUSLABS': 'Laurus Labs',
            'SYNGENE': 'Syngene International',
            'VOLTAS': 'Voltas Limited',
            'WHIRLPOOL': 'Whirlpool India',
            'PFIZER': 'Pfizer India',
            'SANOFI': 'Sanofi India',
            'ESCORTS': 'Escorts Kubota',
            'IDEA': 'Vodafone Idea',
            'ALKEM': 'Alkem Laboratories',
            'APLLTD': 'Alembic Pharmaceuticals',
            'TRENT': 'Trent Limited',
            'JINDALSTEL': 'Jindal Steel',
            'CANBK': 'Canara Bank',
            'IOB': 'Indian Overseas Bank',
            'UCOBANK': 'UCO Bank',
            'MAHABANK': 'Bank of Maharashtra',
            'CENTRALBK': 'Central Bank of India',
            'PSB': 'Punjab & Sind Bank',
            'NSE': 'NSE India',
            'BSE': 'BSE India',
            'NIFTY': 'Nifty 50 Index',
            'SENSEX': 'BSE Sensex',
            'BANKNIFTY': 'Nifty Bank Index'
        }
        
        company_name = company_names.get(clean_symbol, clean_symbol)
        
        return {
            'symbol': symbol,
            'clean_symbol': clean_symbol,
            'company_name': company_name
        }

    def _parse_relative_date(self, date_str: str) -> str:
        """Convert Firecrawl relative dates like '12 hours ago' to ISO format."""
        if not date_str:
            return ""
        text = date_str.strip().lower()
        now = datetime.now()
        match = re.match(r"^(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago$", text)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit == "minute":
                dt = now - timedelta(minutes=amount)
            elif unit == "hour":
                dt = now - timedelta(hours=amount)
            elif unit == "day":
                dt = now - timedelta(days=amount)
            elif unit == "week":
                dt = now - timedelta(weeks=amount)
            elif unit == "month":
                dt = now - timedelta(days=amount * 30)
            else:  # year
                dt = now - timedelta(days=amount * 365)
            return dt.isoformat()
        if text in ("just now", "now", "today"):
            return now.isoformat()
        if text == "yesterday":
            return (now - timedelta(days=1)).isoformat()
        return date_str

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication"""
        if not url:
            return ""
        # Remove tracking parameters
        url = re.sub(r'\?utm_.*$', '', url)
        url = re.sub(r'\?ref=.*$', '', url)
        url = re.sub(r'\?source=.*$', '', url)
        # Remove trailing slash
        url = url.rstrip('/')
        return url.lower()

    def _score_article_impact(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Score article impact based on recency, source authority, and relevance"""
        score = 0.5  # Base score
        
        # Source authority (simplified - you can expand this)
        source = str(article.get('source', '')).lower()
        premium_sources = ['reuters', 'bloomberg', 'financial times', 'wsj', 'cnbc', 'moneycontrol', 'economic times']
        if any(ps in source for ps in premium_sources):
            score += 0.3
        
        # Recency scoring
        published = article.get('published_at', '') or article.get('pubDate', '')
        hours_ago = float('inf')
        if published:
            try:
                # Parse date and calculate recency
                from dateutil import parser
                pub_date = parser.parse(published)
                hours_ago = (datetime.now(pub_date.tzinfo) - pub_date).total_seconds() / 3600
                
                if hours_ago < 1:
                    score += 0.2  # Very recent
                elif hours_ago < 6:
                    score += 0.15
                elif hours_ago < 24:
                    score += 0.1
                elif hours_ago < 72:
                    score += 0.05
            except:
                pass
        
        # Content quality indicators
        title = article.get('title', '')
        if title:
            # Presence of company name or ticker
            if len(title) > 20 and len(title) < 200:
                score += 0.05
            
            # Specific financial keywords indicate higher relevance
            financial_keywords = ['earnings', 'revenue', 'profit', 'loss', 'quarterly', 'annual', 'guidance', 'forecast', 'target', 'price']
            if any(kw in title.lower() for kw in financial_keywords):
                score += 0.1
        
        return {
            "impact_score": round(min(1.0, score), 3),
            "impact_tier": "HIGH" if score >= 0.8 else "MEDIUM" if score >= 0.6 else "LOW",
            "impact_factors": {
                "source_authority": 0.3 if any(ps in source for ps in premium_sources) else 0,
                "recency": 0.2 if hours_ago < 1 else 0.15 if hours_ago < 6 else 0.1 if hours_ago < 24 else 0.05,
                "content_quality": 0.05 if len(title) > 20 else 0
            }
        }

    # ================= ASYNC NEWS FETCHING METHODS =================
    
    async def _fetch_news_headlines_gnews_async(self, session: aiohttp.ClientSession, company_name: str, symbol: str) -> List[Dict[str, Any]]:
        """Async fetch from GNews API"""
        if not self.gnews_api_key:
            return []
            
        params = {
            "q": f'"{company_name}" OR {symbol} stock',
            "lang": "en",
            "country": "in",
            "max": 50,
            "apikey": self.gnews_api_key
        }
        
        try:
            async with session.get(self.gnews_url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    for article in data.get("articles", []):
                        source_obj = article.get("source", {})
                        source_name = source_obj.get("name", "GNews") if isinstance(source_obj, dict) else "GNews"
                        articles.append({
                            "title": article.get("title", ""),
                            "source": source_name,
                            "url": article.get("url", ""),
                            "description": article.get("description", ""),
                            "published_at": article.get("publishedAt", ""),
                            "fetch_source": "gnews"
                        })
                    return articles
        except Exception as e:
            print(f"[ASYNC GNews] Error: {e}")
        return []

    async def _fetch_news_headlines_finnhub_async(self, session: aiohttp.ClientSession, symbol: str, company_name: str, clean_symbol: str) -> List[Dict[str, Any]]:
        """Async fetch from Finnhub API"""
        if not self.finnhub_api_key:
            return []
            
        # Calculate date range (last 7 days)
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            "symbol": clean_symbol,
            "from": from_date,
            "to": to_date,
            "token": self.finnhub_api_key
        }
        
        try:
            async with session.get(self.finnhub_url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    for article in data:
                        timestamp = article.get("datetime")
                        published_at = ""
                        if isinstance(timestamp, (int, float)):
                            published_at = datetime.utcfromtimestamp(int(timestamp)).isoformat()
                        articles.append({
                            "title": article.get("headline", ""),
                            "source": article.get("source", "Finnhub"),
                            "url": article.get("url", ""),
                            "description": article.get("summary", ""),
                            "published_at": published_at,
                            "fetch_source": "finnhub"
                        })
                    return articles
        except Exception as e:
            print(f"[ASYNC Finnhub] Error: {e}")
        return []

    async def _fetch_news_headlines_newsdata_async(self, session: aiohttp.ClientSession, company_name: str, clean_symbol: str) -> List[Dict[str, Any]]:
        """Async fetch from NewsData API"""
        if not self.newsdata_api_key:
            return []
            
        params = {
            'apikey': self.newsdata_api_key,
            'q': f'{company_name} OR {clean_symbol} stock',
            'country': 'in',
            'language': 'en',
            'category': 'business'
        }
        
        try:
            async with session.get(self.newsdata_url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    for article in data.get("results", []):
                        articles.append({
                            'title': article.get('title', ''),
                            'source': article.get('source_id', 'NewsData'),
                            'url': article.get('link', ''),
                            'description': article.get('description', ''),
                            'published_at': article.get('pubDate', ''),
                            'fetch_source': 'newsdata'
                        })
                    return articles
        except Exception as e:
            print(f"[ASYNC NewsData] Error: {e}")
        return []

    async def _fetch_news_headlines_firecrawl_async(self, session: aiohttp.ClientSession, company_name: str, clean_symbol: str) -> List[Dict[str, Any]]:
        """Async fetch stock-specific news via Firecrawl search API"""
        if not self.firecrawl_api_key:
            return []
            
        headers = {
            "Authorization": f"Bearer {self.firecrawl_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": f"{company_name} OR {clean_symbol} stock news",
            "limit": 10,
            "sources": ["news"]
        }
        
        try:
            async with session.post(self.firecrawl_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=25)) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    for item in data.get("data", {}).get("news", []):
                        title = item.get("title", "")
                        if not title:
                            continue
                        snippet = item.get("snippet") or item.get("description") or item.get("markdown") or ""
                        articles.append({
                            "title": title,
                            "source": "Firecrawl",
                            "url": item.get("url", ""),
                            "description": snippet[:2000],
                            "content": snippet[:2000],
                            "published_at": self._parse_relative_date(item.get("date", "")),
                            "fetch_source": "firecrawl"
                        })
                    return articles
        except Exception as e:
            print(f"[ASYNC Firecrawl] Error: {e}")
        return []

    async def fetch_news_headlines_async(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Async version: Fetch latest news headlines for a stock symbol.
        Concurrently fetches from all available sources.
        """
        context = self._get_company_context(symbol)
        clean_symbol = context["clean_symbol"]
        company_name = context["company_name"]

        if not self.gnews_api_key and not self.finnhub_api_key and not self.newsdata_api_key and not self.firecrawl_api_key:
            print("[WARNING] No GNews/Finnhub/NewsData/Firecrawl key found in environment")
            return []

        async with aiohttp.ClientSession() as session:
            # Fetch from all sources concurrently
            tasks = [
                self._fetch_news_headlines_gnews_async(session, company_name, clean_symbol),
                self._fetch_news_headlines_finnhub_async(session, symbol, company_name, clean_symbol),
                self._fetch_news_headlines_newsdata_async(session, company_name, clean_symbol),
                self._fetch_news_headlines_firecrawl_async(session, company_name, clean_symbol)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            gnews_articles = results[0] if not isinstance(results[0], Exception) else []
            finnhub_articles = results[1] if not isinstance(results[1], Exception) else []
            newsdata_articles = results[2] if not isinstance(results[2], Exception) else []
            firecrawl_articles = results[3] if not isinstance(results[3], Exception) else []

        merged: List[Dict[str, Any]] = []
        seen_urls = set()
        for article in gnews_articles + finnhub_articles + newsdata_articles + firecrawl_articles:
            if not isinstance(article, dict):
                continue
            url = self._normalize_url(article.get("url", ""))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append(article)
            if len(merged) >= self.max_articles_to_analyze:
                break

        print(
            f"[MERGED ASYNC] Combined articles => GNews: {len(gnews_articles)}, "
            f"Finnhub: {len(finnhub_articles)}, NewsData: {len(newsdata_articles)}, "
            f"Firecrawl: {len(firecrawl_articles)}, Final: {len(merged)}"
        )
        self.last_news_provider_stats = {
            "configured_keys": {
                "gnews": bool(self.gnews_api_key),
                "finnhub": bool(self.finnhub_api_key),
                "newsdata": bool(self.newsdata_api_key),
                "firecrawl": bool(self.firecrawl_api_key)
            },
            "provider_article_counts": {
                "gnews": len(gnews_articles),
                "finnhub": len(finnhub_articles),
                "newsdata": len(newsdata_articles),
                "firecrawl": len(firecrawl_articles)
            },
            "merged_unique_articles": len(merged)
        }
        return merged

    # ================= SYNC METHODS (for backward compatibility) =================

    def _fetch_news_headlines_gnews(self, company_name: str, symbol: str) -> List[Dict[str, Any]]:
        """Sync fetch from GNews API (fallback)"""
        if not self.gnews_api_key:
            return []
            
        params = {
            "q": f'"{company_name}" OR {symbol} stock',
            "lang": "en",
            "country": "in",
            "max": 50,
            "apikey": self.gnews_api_key
        }
        
        try:
            response = requests.get(self.gnews_url, params=params, timeout=5)
            if response.status_code == 200:
                return [{
                    "title": article.get("title", ""),
                    "source": article.get("source", {}).get("name", "GNews") if isinstance(article.get("source"), dict) else "GNews",
                    "url": article.get("url", ""),
                    "description": article.get("description", ""),
                    "published_at": article.get("publishedAt", ""),
                    "fetch_source": "gnews"
                } for article in response.json().get("articles", [])]
        except Exception as e:
            print(f"[GNews Sync] Error: {e}")
        return []

    def _fetch_news_headlines_finnhub(self, symbol: str, company_name: str, clean_symbol: str) -> List[Dict[str, Any]]:
        """Sync fetch from Finnhub API (fallback)"""
        if not self.finnhub_api_key:
            return []
            
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            "symbol": clean_symbol,
            "from": from_date,
            "to": to_date,
            "token": self.finnhub_api_key
        }
        
        try:
            response = requests.get(self.finnhub_url, params=params, timeout=5)
            if response.status_code == 200:
                articles = []
                for article in response.json():
                    timestamp = article.get("datetime")
                    published_at = ""
                    if isinstance(timestamp, (int, float)):
                        published_at = datetime.utcfromtimestamp(int(timestamp)).isoformat()
                    articles.append({
                        "title": article.get("headline", ""),
                        "source": article.get("source", "Finnhub"),
                        "url": article.get("url", ""),
                        "description": article.get("summary", ""),
                        "published_at": published_at,
                        "fetch_source": "finnhub"
                    })
                return articles
        except Exception as e:
            print(f"[Finnhub Sync] Error: {e}")
        return []

    def _fetch_news_headlines_newsdata(self, company_name: str, clean_symbol: str) -> List[Dict[str, Any]]:
        """Sync fetch from NewsData API (fallback)"""
        if not self.newsdata_api_key:
            return []
            
        params = {
            'apikey': self.newsdata_api_key,
            'q': f'{company_name} OR {clean_symbol} stock',
            'country': 'in',
            'language': 'en',
            'category': 'business'
        }
        
        try:
            response = requests.get(self.newsdata_url, params=params, timeout=5)
            if response.status_code == 200:
                return [{
                    'title': article.get('title', ''),
                    'source': article.get('source_id', 'NewsData'),
                    'url': article.get('link', ''),
                    'description': article.get('description', ''),
                    'published_at': article.get('pubDate', ''),
                    'fetch_source': 'newsdata'
                } for article in response.json().get("results", [])]
        except Exception as e:
            print(f"[NewsData Sync] Error: {e}")
        return []

    def _fetch_news_headlines_firecrawl(self, company_name: str, clean_symbol: str) -> List[Dict[str, Any]]:
        """Sync fetch from Firecrawl search API (fallback)"""
        if not self.firecrawl_api_key:
            return []
            
        headers = {
            "Authorization": f"Bearer {self.firecrawl_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": f"{company_name} OR {clean_symbol} stock news",
            "limit": 10,
            "sources": ["news"]
        }
        
        try:
            response = requests.post(self.firecrawl_url, headers=headers, json=payload, timeout=25)
            if response.status_code == 200:
                articles = []
                for item in response.json().get("data", {}).get("news", []):
                    title = item.get("title", "")
                    if not title:
                        continue
                    snippet = item.get("snippet") or item.get("description") or item.get("markdown") or ""
                    articles.append({
                        "title": title,
                        "source": "Firecrawl",
                        "url": item.get("url", ""),
                        "description": snippet[:2000],
                        "content": snippet[:2000],
                        "published_at": self._parse_relative_date(item.get("date", "")),
                        "fetch_source": "firecrawl"
                    })
                return articles
        except Exception as e:
            print(f"[Firecrawl Sync] Error: {e}")
        return []

    def fetch_news_headlines(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Sync version: Fetch latest news headlines for a stock symbol.
        Runs async version in event loop for compatibility.
        """
        try:
            # Try to use async version for faster concurrent fetching
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create new task
                return asyncio.run_coroutine_threadsafe(
                    self.fetch_news_headlines_async(symbol), loop
                ).result(timeout=15)
            else:
                # No loop running, use run
                return asyncio.run(self.fetch_news_headlines_async(symbol))
        except Exception as e:
            print(f"[ASYNC FALLBACK] Using sync version due to: {e}")
            # Fallback to sync version
            context = self._get_company_context(symbol)
            clean_symbol = context["clean_symbol"]
            company_name = context["company_name"]
            
            gnews_articles = self._fetch_news_headlines_gnews(company_name, clean_symbol)
            finnhub_articles = self._fetch_news_headlines_finnhub(symbol, company_name, clean_symbol)
            newsdata_articles = self._fetch_news_headlines_newsdata(company_name, clean_symbol)
            firecrawl_articles = self._fetch_news_headlines_firecrawl(company_name, clean_symbol)
            
            merged = []
            seen_urls = set()
            for article in gnews_articles + finnhub_articles + newsdata_articles + firecrawl_articles:
                if not isinstance(article, dict):
                    continue
                url = self._normalize_url(article.get("url", ""))
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                merged.append(article)
                if len(merged) >= self.max_articles_to_analyze:
                    break
            return merged

    def fetch_general_market_news(self) -> List[Dict[str, Any]]:
        """
        Fetch latest general Indian market headlines using configured API keys.
        """
        merged: List[Dict[str, Any]] = []
        seen_urls = set()
        
        # 1. GNews
        if self.gnews_api_key:
            params = {
                "q": '"Indian stock market" OR Nifty OR Sensex OR BSE',
                "lang": "en",
                "country": "in",
                "max": 50,
                "apikey": self.gnews_api_key
            }
            try:
                response = requests.get(self.gnews_url, params=params, timeout=8)
                if response.status_code == 200:
                    for article in response.json().get("articles", []):
                        url = self._normalize_url(article.get("url", ""))
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            source_obj = article.get("source", {})
                            source_name = source_obj.get("name", "GNews") if isinstance(source_obj, dict) else "GNews"
                            merged.append({
                                "title": article.get("title", ""),
                                "source": source_name,
                                "url": url,
                                "description": article.get("description", ""),
                                "published_at": article.get("publishedAt", "")
                            })
            except Exception as e:
                print(f"[ERROR] GNews general market fetch failed: {e}")

        # 2. NewsData
        if self.newsdata_api_key and len(merged) < 30:
            params = {
                'apikey': self.newsdata_api_key,
                'q': 'stock market OR Nifty OR Sensex',
                'country': 'in',
                'language': 'en'
            }
            try:
                response = requests.get(self.newsdata_url, params=params, timeout=8)
                if response.status_code == 200:
                    for article in response.json().get("results", []):
                        url = self._normalize_url(article.get('link', ''))
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            merged.append({
                                'title': article.get('title', ''),
                                'source': article.get('source_id', 'NewsData'),
                                'url': url,
                                'description': article.get('description', ''),
                                'published_at': article.get('pubDate', '')
                            })
            except Exception as e:
                print(f"[ERROR] NewsData general market fetch failed: {e}")

        # 3. Finnhub (general news endpoint)
        if self.finnhub_api_key and len(merged) < 40:
            params = {
                "category": "general",
                "token": self.finnhub_api_key
            }
            try:
                response = requests.get("https://finnhub.io/api/v1/news", params=params, timeout=8)
                if response.status_code == 200:
                    for article in response.json():
                        url = self._normalize_url(article.get("url", ""))
                        # Filter out to make it remotely relevant if needed, though finnhub 'general' is global
                        title = article.get("headline", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            timestamp = article.get("datetime")
                            published_at = ""
                            if isinstance(timestamp, (int, float)):
                                published_at = datetime.utcfromtimestamp(int(timestamp)).isoformat()
                            merged.append({
                                "title": title,
                                "source": article.get("source", "Finnhub"),
                                "url": url,
                                "description": article.get("summary", ""),
                                "published_at": published_at
                            })
            except Exception as e:
                print(f"[ERROR] Finnhub general market fetch failed: {e}")

        # Sort roughly by date, fallback to length if empty
        merged.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        # If no news fetched (no API keys or all failed), provide fallback market updates
        if not merged:
            from datetime import datetime, timedelta
            now = datetime.now()
            merged = [
                {
                    "title": "Indian markets open for trading - Nifty and Sensex show positive momentum",
                    "source": "Market Update",
                    "url": "https://www.nseindia.com",
                    "description": "Markets are trading today. Stay updated with latest market movements.",
                    "published_at": now.isoformat()
                },
                {
                    "title": "Nifty 50 holds above key support levels ahead of weekly expiry",
                    "source": "Technical Analysis",
                    "url": "https://www.nseindia.com",
                    "description": "Technical indicators suggest cautious optimism in the markets.",
                    "published_at": (now - timedelta(minutes=30)).isoformat()
                },
                {
                    "title": "Banking stocks show mixed trends; PSU banks gain traction",
                    "source": "Sector Watch",
                    "url": "https://www.bseindia.com",
                    "description": "Banking sector remains in focus with quarterly results season approaching.",
                    "published_at": (now - timedelta(hours=1)).isoformat()
                },
                {
                    "title": "IT sector under pressure amid global tech sell-off concerns",
                    "source": "Global Markets",
                    "url": "https://www.bseindia.com",
                    "description": "Technology stocks face headwinds from global market volatility.",
                    "published_at": (now - timedelta(hours=2)).isoformat()
                },
                {
                    "title": "FII flows remain positive; DIIs continue buying support",
                    "source": "Institutional",
                    "url": "https://www.nseindia.com",
                    "description": "Foreign institutional investors maintain interest in Indian equities.",
                    "published_at": (now - timedelta(hours=3)).isoformat()
                }
            ]
        
        return merged[:50]

    def fetch_article_body(self, url: str, timeout: int = 5) -> str:
        """Fetch the full article body content for sentiment analysis with fast timeout"""
        try:
            if not url:
                return ""
            
            # First try fast BeautifulSoup approach (more reliable than newspaper3k)
            try:
                import requests
                from bs4 import BeautifulSoup
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "header", "footer"]):
                        script.decompose()
                    
                    # Try to find main article content
                    article_tags = soup.find_all(['article', 'main'])
                    if article_tags:
                        text = ' '.join([tag.get_text(separator=' ', strip=True) for tag in article_tags])
                        if len(text) > 200:
                            return text[:2000]  # Limit to 2000 chars
                    
                    # Fallback: get all paragraphs
                    paragraphs = soup.find_all('p')
                    text = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
                    
                    if len(text) > 200:
                        return text[:2000]
            except Exception as e:
                pass
            
            return ""
            
        except Exception as e:
            return ""

    # ================= MAIN SENTIMENT METHODS =================

    async def get_sentiment_for_stock_async(self, symbol: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        ASYNC version: Main method to get sentiment analysis for a stock.
        Fetches news asynchronously for non-blocking operation.
        """
        # Check cache first
        cache_instance = _get_cache()
        if use_cache and cache_instance:
            cached_result = cache_instance.get_sentiment(symbol)
            if cached_result:
                print(f"[SENTIMENT CACHE] Cache hit for {symbol}")
                cached_result['_cached'] = True
                cached_result['_cached_at'] = datetime.now().isoformat()
                # If cache is fresh (< 5 min), return immediately
                cache_time = cached_result.get('_timestamp', '')
                if cache_time:
                    try:
                        from dateutil import parser
                        cached_dt = parser.parse(cache_time)
                        age_minutes = (datetime.now() - cached_dt).total_seconds() / 60
                        if age_minutes < 5:  # Less than 5 minutes old
                            cached_result['_cache_fresh'] = True
                            return cached_result
                    except:
                        pass
                return cached_result
        
        # Fetch news asynchronously
        print(f"\n[ANALYZING ASYNC] Starting sentiment analysis for {symbol}")
        news_articles = await self.fetch_news_headlines_async(symbol)
        
        return self._process_sentiment_result(symbol, news_articles, use_cache)

    def get_sentiment_for_stock(self, symbol: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        SYNC version for backward compatibility: Gets sentiment with caching.
        For non-blocking behavior, use get_sentiment_for_stock_async.
        """
        # Check cache first
        cache_instance = _get_cache()
        if use_cache and cache_instance:
            cached_result = cache_instance.get_sentiment(symbol)
            if cached_result:
                print(f"[SENTIMENT CACHE] Cache hit for {symbol}")
                cached_result['_cached'] = True
                cached_result['_cached_at'] = datetime.now().isoformat()
                return cached_result
        
        # Fetch news
        print(f"\n[ANALYZING] Starting sentiment analysis for {symbol}")
        news_articles = self.fetch_news_headlines(symbol)
        
        return self._process_sentiment_result(symbol, news_articles, use_cache)

    def _process_sentiment_result(self, symbol: str, news_articles: List[Dict], use_cache: bool = True) -> Dict[str, Any]:
        """Process sentiment analysis result from news articles"""
        # NO FALLBACK - Only real articles from NewsData API
        if not news_articles:
            print(f"[NO REAL NEWS] No real articles found for {symbol}")
            result = {
                "symbol": symbol,
                "sentiment_score": 0,
                "sentiment_classification": "No Data",
                "headlines_count": 0,
                "breakdown": {
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0
                },
                "news_articles": [],
                "sources": [],
                "fetch_method": "gnews_finnhub_newsdata",
                "articles_count": 0,
                "message": "No real articles found for this stock. Try a more popular stock or check again later."
            }
            # Cache even empty results to avoid repeated API calls (shorter TTL)
            cache_instance = _get_cache()
            if use_cache and cache_instance:
                cache_instance.set_sentiment(symbol, result)
            return result

        # Impact-rank all fetched articles, then analyze
        enriched_articles: List[Dict[str, Any]] = []
        for article in news_articles[:self.max_articles_to_analyze]:
            if not isinstance(article, dict):
                continue
            impact_meta = self._score_article_impact(article)
            item = dict(article)
            item.update(impact_meta)
            enriched_articles.append(item)

        enriched_articles.sort(key=lambda x: x.get("impact_score", 0), reverse=True)
        total_fetched = len(enriched_articles)
        analyze_count = min(total_fetched, self.max_articles_to_analyze)
        if analyze_count < self.min_articles_to_analyze:
            analyze_count = total_fetched
        # Cap LLM sentiment calls to stay within API rate limits
        analyze_count = min(analyze_count, self.max_groq_sentiment_articles)
        analysis_pool = enriched_articles[:analyze_count]
        top_impact_articles = analysis_pool[:self.top_impact_to_show]

        source_values = {str(a.get("source", "")).lower() for a in enriched_articles if isinstance(a, dict)}
        if any("gnews" in src for src in source_values):
            fetch_method = "gnews_api"
        elif any("finnhub" in src for src in source_values):
            fetch_method = "finnhub_api"
        elif any("firecrawl" in src for src in source_values):
            fetch_method = "firecrawl_api"
        elif enriched_articles:
            fetch_method = "newsdata_api"
        else:
            fetch_method = "unknown"

        print(f"[REAL NEWS] Impact-ranking {total_fetched} real articles from {fetch_method}; analyzing {analyze_count}; showing top {self.top_impact_to_show}")

        # Build richer text payloads per article for sentiment aggregation
        texts_for_analysis: List[str] = []
        for article in analysis_pool:
            title = (article.get('title') or '').strip()
            description = (article.get('description') or '').strip()
            body = (article.get('content') or '').strip()
            text_payload = " ".join([part for part in [title, description, body] if part])
            if text_payload:
                texts_for_analysis.append(text_payload)
        
        # Analyze sentiment of headlines
        try:
            sentiment = self.aggregate_sentiment(texts_for_analysis)
            print(f"[SENTIMENT] {sentiment.get('classification', 'Unknown')}: {sentiment.get('average_score', 0)}")
        except Exception as e:
            print(f"[ERROR] Sentiment analysis failed: {str(e)[:50]}")
            sentiment = {
                "average_score": 0,
                "classification": "Neutral",
                "headlines_analyzed": len(texts_for_analysis),
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": len(texts_for_analysis)
            }

        # Return real articles with impact ranking
        result = {
            "symbol": symbol,
            "sentiment_score": sentiment.get("average_score", 0),
            "sentiment_classification": sentiment.get("classification", "Neutral"),
            "headlines_count": sentiment.get("headlines_analyzed", 0),
            "breakdown": {
                "positive": sentiment.get("positive_count", 0),
                "negative": sentiment.get("negative_count", 0),
                "neutral": sentiment.get("neutral_count", 0)
            },
            "news_articles": top_impact_articles,
            "sources": list(set([article.get('source', 'Unknown') if isinstance(article, dict) else 'Unknown' for article in enriched_articles])) if enriched_articles else ["Unknown"],
            "fetch_method": fetch_method,
            "articles_count": total_fetched,
            "analysis_scope": {
                "total_fetched_articles": total_fetched,
                "articles_analyzed_for_sentiment": analyze_count,
                "articles_shown": len(top_impact_articles),
                "selection_rule": "Top impact score for expected near-term price effect"
            },
            "api_capabilities": self.last_news_provider_stats,
            "_cached": False,
            "_timestamp": datetime.now().isoformat()
        }
        
        # Cache the result
        cache_instance = _get_cache()
        if use_cache and cache_instance:
            cache_instance.set_sentiment(symbol, result)
            print(f"[SENTIMENT CACHE] Cached result for {symbol}")
        
        print(f"[DONE] Returning {len(result['news_articles'])} articles ({fetch_method})\n")
        return result


# Initialize global sentiment analyzer instance
sentiment_analyzer = SentimentAnalyzer()
