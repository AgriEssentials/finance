"""
News Sentiment Analysis Module
Handles fetching and analyzing news sentiment using NewsData API with pretrained transformer models
"""

import os
import requests
from typing import List, Dict, Any, Optional
import re
from datetime import datetime, timedelta

# Load environment variables from .env file at module import time
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, will use system env vars only
    pass


class SentimentAnalyzer:
    """Class to analyze news sentiment using NewsData API + pretrained transformer models"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize sentiment analyzer
        
        Args:
            api_key: Reserved for compatibility (unused)
        """
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        # Support both env var names used across project setup.
        self.newsdata_api_key = os.getenv('NEWSDATA_API_KEY') or os.getenv('NEWS_API_KEY')
        self.gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        configured_candidates = os.getenv('GEMINI_MODEL_CANDIDATES', '').strip()
        default_candidates = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.0-flash']
        if configured_candidates:
            parsed = [m.strip() for m in configured_candidates.split(',') if m.strip()]
            self.gemini_model_candidates = parsed if parsed else default_candidates
        else:
            self.gemini_model_candidates = default_candidates
        self.newsdata_url = "https://newsdata.io/api/1/news"
        self.gnews_api_key = os.getenv('GNEWS_API_KEY')
        self.gnews_url = "https://gnews.io/api/v4/search"
        self.finnhub_api_key = (
            os.getenv('FINNHUB_API_KEY')
            or os.getenv('FINHUB_API_KEY')
            or os.getenv('FINNHUB_KEY')
            or os.getenv('FINNHUB_TOKEN')
            or os.getenv('FINNHUB_API_TOKEN')
        )
        self.finnhub_url = "https://finnhub.io/api/v1/company-news"
        self.max_articles_to_analyze = 500
        self.min_articles_to_analyze = 50
        self.top_impact_to_show = 15
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
        """Lazy load transformer model on first use"""
        if self.use_transformer is not None:
            return  # Already tried to load
        
        try:
            from transformers import pipeline
            # Use DistilBERT for faster sentiment analysis
            print("[LOADING] Loading DistilBERT model (first time only, ~3-5 seconds)...")
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

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment with transformer primary, Gemini secondary, then keyword fallback."""
        # Ensure transformer is loaded (lazy load on first use)
        if self.use_transformer is None:
            self._ensure_transformer_loaded()
        
        # Try transformer first (most accurate)
        if self.use_transformer:  # Now it's either True or False, not None
            try:
                transformer_result = self._analyze_sentiment_transformer(text)
                if transformer_result:
                    return transformer_result
            except Exception as e:
                pass

        # Try Gemini
        try:
            gemini_result = self._analyze_sentiment_gemini(text)
            if gemini_result:
                return gemini_result
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
                    # Scale score to 0.1-0.5
                    normalized_score = 0.5 - (score * 0.4)
                else:
                    label = 'neutral'
                    normalized_score = 0.5
                
                return {
                    "label": label,
                    "score": normalized_score,
                    "text": text,
                    "method": "transformer:distilbert"
                }
        except Exception as e:
            print(f"Transformer sentiment error: {e}")
            return None

    def _normalize_url(self, raw_url: str) -> str:
        """Normalize and validate article URL; return empty string when invalid."""
        if not raw_url:
            return ""
        url = raw_url.strip()
        if not url:
            return ""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url if url.startswith(("http://", "https://")) else ""

    def _get_company_context(self, symbol: str) -> Dict[str, str]:
        """Resolve clean symbol and readable company name."""
        clean_symbol = symbol.split('.')[0]
        company_name_map = {
            'HDFCBANK': 'HDFC Bank',
            'RELIANCE': 'Reliance Industries',
            'TCS': 'Tata Consultancy Services',
            'INFY': 'Infosys',
            'ICICIBANK': 'ICICI Bank',
            'SBIN': 'State Bank of India',
            'KOTAKBANK': 'Kotak Mahindra Bank',
            'AXISBANK': 'Axis Bank',
            'BHARTIARTL': 'Bharti Airtel',
            'LT': 'Larsen & Toubro',
            'ASIANPAINT': 'Asian Paints',
            'MARUTI': 'Maruti Suzuki',
            'TITAN': 'Titan Company',
            'WIPRO': 'Wipro',
            'SUNPHARMA': 'Sun Pharma',
            'BAJFINANCE': 'Bajaj Finance',
            'NESTLEIND': 'Nestle India',
            'HINDUNILVR': 'Hindustan Unilever',
            'ITC': 'ITC Limited',
            'ULTRACEMCO': 'UltraTech Cement'
        }
        return {
            "clean_symbol": clean_symbol,
            "company_name": company_name_map.get(clean_symbol, clean_symbol)
        }

    def _company_keywords(self, company_name: str, clean_symbol: str) -> List[str]:
        keywords = [company_name.lower(), clean_symbol.lower()]
        lower_name = company_name.lower()
        if lower_name == 'hdfc bank':
            keywords.extend(['hdfc', 'hdfcbank'])
        elif lower_name == 'reliance industries':
            keywords.extend(['reliance', 'ril'])
        elif lower_name == 'state bank of india':
            keywords.extend(['sbi', 'state bank'])
        return list(dict.fromkeys([kw for kw in keywords if kw]))

    def _is_relevant_article(self, title: str, description: str, company_name: str, clean_symbol: str) -> bool:
        article_text = f"{(title or '').lower()} {(description or '').lower()}"
        return any(keyword in article_text for keyword in self._company_keywords(company_name, clean_symbol))

    def _fetch_news_headlines_finnhub(self, symbol: str, company_name: str, clean_symbol: str) -> List[Dict[str, Any]]:
        """Fetch company headlines from Finnhub."""
        if not self.finnhub_api_key:
            return []

        to_date = datetime.utcnow().date()
        from_date = to_date - timedelta(days=14)
        symbol_candidates = [symbol, clean_symbol, f"NSE:{clean_symbol}", f"BSE:{clean_symbol}"]
        symbol_candidates = list(dict.fromkeys([s for s in symbol_candidates if s]))

        formatted_articles: List[Dict[str, Any]] = []
        seen_urls = set()

        print(f"[FETCHING] Requesting real news for {company_name} from Finnhub API...")
        for ticker in symbol_candidates:
            params = {
                "symbol": ticker,
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
                "token": self.finnhub_api_key
            }
            try:
                response = requests.get(self.finnhub_url, params=params, timeout=6)
            except requests.exceptions.ReadTimeout:
                print(f"[TIMEOUT] Finnhub timeout for ticker {ticker}")
                continue
            except requests.exceptions.RequestException as exc:
                print(f"[ERROR] Finnhub request failed for ticker {ticker}: {exc}")
                continue

            if response.status_code != 200:
                print(f"[ERROR] Finnhub API error for ticker {ticker}: {response.status_code} - {response.text[:160]}")
                continue

            try:
                payload = response.json()
            except ValueError:
                print(f"[ERROR] Finnhub returned invalid JSON for ticker {ticker}")
                continue

            if not isinstance(payload, list):
                continue

            for article in payload:
                if not isinstance(article, dict):
                    continue
                title = article.get("headline", "") or article.get("title", "")
                description = article.get("summary", "") or article.get("description", "")
                url = self._normalize_url(article.get("url", ""))
                if not url or url in seen_urls:
                    continue
                if not self._is_relevant_article(title, description, company_name, clean_symbol):
                    continue

                timestamp = article.get("datetime")
                published_at = ""
                if isinstance(timestamp, (int, float)):
                    published_at = datetime.utcfromtimestamp(int(timestamp)).isoformat()

                seen_urls.add(url)
                formatted_articles.append({
                    "title": title or "No title",
                    "source": article.get("source", "Finnhub"),
                    "url": url,
                    "description": description or "",
                    "published_at": published_at,
                    "image": article.get("image", "")
                })

            if len(formatted_articles) >= self.max_articles_to_analyze:
                break

        print(f"[OK] Final real article count for {company_name} from Finnhub: {len(formatted_articles)}")
        return formatted_articles

    def _fetch_news_headlines_newsdata(self, company_name: str, clean_symbol: str) -> List[Dict[str, Any]]:
        """Fetch company headlines from NewsData API with pagination."""
        if not self.newsdata_api_key:
            return []

        base_params = {
            'apikey': self.newsdata_api_key,
            'q': company_name,
            'country': 'in',
            'language': 'en'
        }

        print(f"[FETCHING] Requesting real news for {company_name} from NewsData API...")
        formatted_articles: List[Dict[str, Any]] = []
        seen_urls = set()
        next_page = None
        max_pages = 10

        for page_idx in range(max_pages):
            params = dict(base_params)
            if next_page:
                params['page'] = next_page

            try:
                response = requests.get(self.newsdata_url, params=params, timeout=8)
            except requests.exceptions.ReadTimeout:
                print(f"[TIMEOUT] NewsData API timed out on page {page_idx + 1}")
                break
            except requests.exceptions.RequestException as exc:
                print(f"[ERROR] NewsData request failed on page {page_idx + 1}: {exc}")
                break

            print(f"[API RESPONSE] NewsData page {page_idx + 1} status: {response.status_code}")
            if response.status_code != 200:
                error_msg = response.text if response.text else f"HTTP {response.status_code}"
                print(f"[ERROR] NewsData API error: {response.status_code} - {error_msg[:200]}")
                break

            data = response.json()
            articles = data.get('results', [])
            if not articles:
                print(f"[INFO] No more NewsData articles returned on page {page_idx + 1}")
                break

            for article in articles:
                if not isinstance(article, dict):
                    continue
                url = self._normalize_url(article.get('link', ''))
                if not url or url in seen_urls:
                    continue

                title = article.get('title', '') or ''
                description = article.get('description', '') or ''
                if not self._is_relevant_article(title, description, company_name, clean_symbol):
                    continue

                seen_urls.add(url)
                formatted_articles.append({
                    'title': title or 'No title',
                    'source': article.get('source_id', 'NewsData'),
                    'url': url,
                    'description': description,
                    'published_at': article.get('pubDate', ''),
                    'image': article.get('image_url', '')
                })

            print(f"[SUCCESS] Collected {len(formatted_articles)} unique NewsData articles so far")
            if len(formatted_articles) >= 30:
                break

            next_page = data.get('nextPage')
            if not next_page:
                break

        print(f"[OK] Final real article count for {company_name} from NewsData: {len(formatted_articles)}")
        return formatted_articles

    def _fetch_news_headlines_gnews(self, company_name: str, clean_symbol: str) -> List[Dict[str, Any]]:
        """Fetch company headlines from GNews API with pagination up to ~300 articles."""
        if not self.gnews_api_key:
            return []

        formatted_articles: List[Dict[str, Any]] = []
        seen_urls = set()
        max_pages = 5  # 5 * 100 = 500
        query = f'"{company_name}" OR {clean_symbol} stock OR share'

        print(f"[FETCHING] Requesting real news for {company_name} from GNews API...")
        for page in range(1, max_pages + 1):
            params = {
                "q": query,
                "lang": "en",
                "country": "in",
                "max": 100,
                "page": page,
                "apikey": self.gnews_api_key
            }

            try:
                response = requests.get(self.gnews_url, params=params, timeout=8)
            except requests.exceptions.ReadTimeout:
                print(f"[TIMEOUT] GNews API timed out on page {page}")
                break
            except requests.exceptions.RequestException as exc:
                print(f"[ERROR] GNews request failed on page {page}: {exc}")
                break

            print(f"[API RESPONSE] GNews page {page} status: {response.status_code}")
            if response.status_code != 200:
                print(f"[ERROR] GNews API error: {response.status_code} - {response.text[:200]}")
                break

            try:
                payload = response.json()
            except ValueError:
                print(f"[ERROR] GNews returned invalid JSON on page {page}")
                break

            articles = payload.get("articles", [])
            if not articles:
                break

            for article in articles:
                if not isinstance(article, dict):
                    continue
                title = article.get("title", "") or ""
                description = article.get("description", "") or ""
                if not self._is_relevant_article(title, description, company_name, clean_symbol):
                    continue

                url = self._normalize_url(article.get("url", ""))
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                source_obj = article.get("source", {})
                source_name = source_obj.get("name", "GNews") if isinstance(source_obj, dict) else "GNews"
                formatted_articles.append({
                    "title": title or "No title",
                    "source": source_name,
                    "url": url,
                    "description": description,
                    "published_at": article.get("publishedAt", ""),
                    "image": article.get("image", ""),
                    "content": article.get("content", "")
                })

            print(f"[SUCCESS] Collected {len(formatted_articles)} unique GNews articles so far")
            if len(formatted_articles) >= self.max_articles_to_analyze:
                break

        print(f"[OK] Final real article count for {company_name} from GNews: {len(formatted_articles)}")
        return formatted_articles[:self.max_articles_to_analyze]

    def _score_article_impact(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Score how severely an article can affect near-term stock price."""
        title = str(article.get("title", "") or "")
        description = str(article.get("description", "") or "")
        content = str(article.get("content", "") or "")
        text = f"{title} {description} {content}".lower()

        severe_negative = {
            "fraud": 22, "bankruptcy": 24, "default": 20, "probe": 16, "lawsuit": 14,
            "downgrade": 14, "misses": 12, "miss": 12, "plunge": 16, "crash": 18,
            "sanction": 14, "war": 12, "conflict": 10, "ban": 12
        }
        severe_positive = {
            "upgrade": 12, "buyback": 14, "acquisition": 12, "merger": 12,
            "beats": 12, "beat": 12, "surge": 14, "rally": 10, "contract win": 12,
            "guidance raise": 14
        }
        macro_event = {
            "rbi": 10, "fed": 10, "interest rate": 10, "inflation": 8, "opec": 10,
            "oil": 8, "election": 8, "policy": 8, "regulation": 9, "budget": 8
        }

        score = 0.0
        tags: List[str] = []

        for keyword, weight in severe_negative.items():
            if keyword in text:
                score += weight
                tags.append(f"risk:{keyword}")
        for keyword, weight in severe_positive.items():
            if keyword in text:
                score += weight
                tags.append(f"catalyst:{keyword}")
        for keyword, weight in macro_event.items():
            if keyword in text:
                score += weight
                tags.append(f"macro:{keyword}")

        # Recency boost
        published_at = str(article.get("published_at", "") or "")
        if published_at:
            try:
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                age_hours = (datetime.now(dt.tzinfo) - dt).total_seconds() / 3600
                if age_hours <= 24:
                    score += 10
                elif age_hours <= 72:
                    score += 6
                elif age_hours <= 168:
                    score += 3
            except Exception:
                pass

        # More concrete article body implies higher confidence of impact
        if len(description) > 120:
            score += 2
        if len(content) > 120:
            score += 2

        if score >= 35:
            severity = "High"
        elif score >= 20:
            severity = "Medium"
        else:
            severity = "Low"

        return {
            "impact_score": round(score, 2),
            "impact_severity": severity,
            "impact_tags": tags[:5]
        }
        
    def fetch_news_headlines(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch latest news headlines for a stock symbol using Finnhub (preferred)
        with NewsData fallback.

        Args:
            symbol: Stock symbol (e.g., 'HDFCBANK.NS')
        
        Returns:
            List of news articles with title, source, url, published date
        """
        context = self._get_company_context(symbol)
        clean_symbol = context["clean_symbol"]
        company_name = context["company_name"]

        # Use all available providers together: GNews + Finnhub + NewsData.
        if not self.gnews_api_key and not self.finnhub_api_key and not self.newsdata_api_key:
            print("[WARNING] No GNews/Finnhub/NewsData key found in environment")
            return []

        gnews_articles = self._fetch_news_headlines_gnews(company_name, clean_symbol)

        finnhub_articles = self._fetch_news_headlines_finnhub(symbol, company_name, clean_symbol)
        newsdata_articles = self._fetch_news_headlines_newsdata(company_name, clean_symbol)

        merged: List[Dict[str, Any]] = []
        seen_urls = set()
        for article in gnews_articles + finnhub_articles + newsdata_articles:
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
            f"[MERGED] Combined articles => GNews: {len(gnews_articles)}, "
            f"Finnhub: {len(finnhub_articles)}, NewsData: {len(newsdata_articles)}, Final: {len(merged)}"
        )
        self.last_news_provider_stats = {
            "configured_keys": {
                "gnews": bool(self.gnews_api_key),
                "finnhub": bool(self.finnhub_api_key),
                "newsdata": bool(self.newsdata_api_key)
            },
            "provider_article_counts": {
                "gnews": len(gnews_articles),
                "finnhub": len(finnhub_articles),
                "newsdata": len(newsdata_articles)
            },
            "merged_unique_articles": len(merged)
        }
        return merged

    def fetch_article_body(self, url: str, timeout: int = 5) -> str:
        """Fetch the full article body content for sentiment analysis with fast timeout"""
        try:
            if not url:
                return ""
            
            # First try fast BeautifulSoup approach (more reliable than newspaper3k)
            try:
                response = requests.get(url, timeout=timeout, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text[:2000] if text else ""  # Limit to first 2000 chars
            except requests.Timeout:
                return ""  # Return empty on timeout, don't try newspaper3k
            except Exception as bs_error:
                # Fallback to newspaper if BeautifulSoup fails
                try:
                    from newspaper import Article
                    article = Article(url)
                    article.download()
                    article.parse()
                    return article.text[:2000] if article.text else ""
                except Exception:
                    return ""
        except Exception as e:
            return ""

    def _analyze_sentiment_gemini(self, text: str) -> Optional[Dict[str, Any]]:
        """Fallback sentiment classification using Gemini JSON output."""
        if not self.gemini_api_key:
            return None

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Classify sentiment of this stock-market headline for Indian markets. "
                                "Return ONLY JSON with keys: label (positive|negative|neutral), score (0-1).\n\n"
                                f"Headline: {text}"
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 120,
                "responseMimeType": "application/json"
            }
        }

        try:
            models_to_try = []
            for candidate in self.gemini_model_candidates:
                if candidate not in models_to_try:
                    models_to_try.append(candidate)
            if self.gemini_model and self.gemini_model not in models_to_try:
                models_to_try.append(self.gemini_model)

            import json
            for model_name in models_to_try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model_name}:generateContent?key={self.gemini_api_key}"
                )
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 400:
                    # Retry without responseMimeType (some models/plans don't support it)
                    payload_no_json = dict(payload)
                    payload_no_json["generationConfig"] = {"temperature": 0, "maxOutputTokens": 120}
                    response = requests.post(url, json=payload_no_json, timeout=10)
                if response.status_code != 200:
                    print(f"Gemini sentiment error ({model_name}): {response.status_code} - {response.text[:200]}")
                    continue

                result = response.json()
                parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                if not parts:
                    continue

                raw_text = parts[0].get("text", "{}")
                # Try direct JSON parse first
                try:
                    parsed = json.loads(raw_text)
                except json.JSONDecodeError:
                    # Try extracting JSON from markdown fences
                    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
                    try:
                        parsed = json.loads(cleaned)
                    except json.JSONDecodeError:
                        continue
                label = (parsed.get("label") or "neutral").lower()
                if label not in {"positive", "negative", "neutral"}:
                    label = "neutral"
                score = float(parsed.get("score", 0.5))
                score = max(0.1, min(0.9, score))

                return {
                    "label": label,
                    "score": score,
                    "text": text,
                    "method": f"gemini:{model_name}"
                }
        except Exception:
            return None
    
    def _detect_language(self, text: str) -> str:
        """Detect if text is Hindi or English"""
        # Simple detection based on Unicode range
        hindi_pattern = re.compile(r'[\u0900-\u097F]')
        if hindi_pattern.search(text):
            return "hi-IN"  # Hindi
        return "en-IN"  # English (India)
    
    def _fallback_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Fallback sentiment analysis using keyword matching
        Used when transformer/Sarvam API is unavailable
        """
        text_lower = text.lower()
        
        # Positive keywords
        positive_words = [
            'strong', 'growth', 'profit', 'up', 'rise', 'gain', 'bullish', 
            'upgrade', 'buy', 'positive', 'excellent', 'surge', 'rally',
            'मजबूत', 'लाभ', 'वृद्धि', 'अच्छा', 'उछाल'
        ]
        
        # Negative keywords
        negative_words = [
            'weak', 'loss', 'down', 'fall', 'drop', 'bearish', 'downgrade',
            'sell', 'negative', 'poor', 'crash', 'decline', 'plunge',
            'कमजोर', 'हानि', 'गिरावट', 'खराब', 'मंदी'
        ]
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            label = "positive"
            score = 0.5 + (pos_count - neg_count) * 0.1
        elif neg_count > pos_count:
            label = "negative"
            score = 0.5 - (neg_count - pos_count) * 0.1
        else:
            label = "neutral"
            score = 0.5
        
        # Normalize score to 0-1 range
        score = max(0.1, min(0.9, score))
        
        return {
            "label": label,
            "score": score,
            "text": text,
            "method": "fallback"
        }
    
    def aggregate_sentiment(self, texts: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment for multiple headlines and aggregate results
        
        Args:
            texts: List of article texts/headlines
        
        Returns:
            Dictionary with aggregated sentiment results
        """
        if not texts:
            return {
                "average_score": 0.5,
                "classification": "Neutral",
                "headlines_analyzed": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0
            }
        
        # Analyze each article text payload
        results = []
        for text in texts:
            try:
                sentiment = self.analyze_sentiment(text)
                results.append(sentiment)
            except Exception as e:
                results.append(self._fallback_sentiment(text))
        
        if not results:
            # All headlines failed, use fallback
            return {
                "average_score": 0.5,
                "classification": "Neutral",
                "headlines_analyzed": len(texts),
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": len(texts)
            }

        # Count sentiments
        positive_count = sum(1 for r in results if r.get('label') == 'positive')
        negative_count = sum(1 for r in results if r.get('label') == 'negative')
        neutral_count = len(results) - positive_count - negative_count
        
        # Calculate average score (0-1 scale)
        avg_score = sum(r.get('score', 0.5) for r in results) / len(results) if results else 0.5

        # Convert to -1 to 1 scale for ML model
        normalized_score = (avg_score - 0.5) * 2
        
        # Final classification
        if positive_count > negative_count and positive_count > neutral_count:
            classification = "Positive"
        elif negative_count > positive_count and negative_count > neutral_count:
            classification = "Negative"
        else:
            classification = "Neutral"
        
        return {
            "average_score": round(normalized_score, 3),
            "raw_score": round(avg_score, 3),
            "classification": classification,
            "headlines_analyzed": len(texts),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "details": results
        }
    
    def get_sentiment_for_stock(self, symbol: str) -> Dict[str, Any]:
        """
        Main method to get sentiment analysis for a stock using real market news APIs.
        Uses Finnhub first, then NewsData fallback. No sample headlines.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Complete sentiment analysis results with ONLY real news details
        """
        # Fetch REAL news articles from Finnhub (preferred) with NewsData fallback
        print(f"\n[ANALYZING] Starting sentiment analysis for {symbol}")
        news_articles = self.fetch_news_headlines(symbol)
        
        # NO FALLBACK - Only real articles from NewsData API
        if not news_articles:
            print(f"[NO REAL NEWS] No real articles found for {symbol} from GNews/Finnhub/NewsData APIs")
            # Return empty result with no articles - NO SAMPLE HEADLINES
            return {
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

        # Impact-rank all fetched articles, then analyze up to 300 and show top 10 severe-impact.
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
        analysis_pool = enriched_articles[:analyze_count]
        top_impact_articles = analysis_pool[:self.top_impact_to_show]

        source_values = {str(a.get("source", "")).lower() for a in enriched_articles if isinstance(a, dict)}
        if any("gnews" in src for src in source_values):
            fetch_method = "gnews_api"
        elif any("finnhub" in src for src in source_values):
            fetch_method = "finnhub_api"
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
        
        # Analyze sentiment of headlines with robust error handling
        try:
            sentiment = self.aggregate_sentiment(texts_for_analysis)
            print(f"[SENTIMENT] {sentiment.get('classification', 'Unknown')}: {sentiment.get('average_score', 0)}")
        except Exception as e:
            # Fallback sentiment if analysis fails
            print(f"[ERROR] Sentiment analysis failed: {str(e)[:50]}")
            sentiment = {
                "average_score": 0,
                "classification": "Neutral",
                "headlines_analyzed": len(texts_for_analysis),
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": len(texts_for_analysis)
            }

        # Return real articles with impact ranking (top 10 shown)
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
            "api_capabilities": self.last_news_provider_stats
        }
        
        print(f"[DONE] Returning {len(result['news_articles'])} articles ({fetch_method})\n")
        return result


# Initialize global sentiment analyzer instance
sentiment_analyzer = SentimentAnalyzer()

