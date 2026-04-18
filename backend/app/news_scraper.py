"""
Real-time News Scraper for Indian Stock Market
Fetches news from multiple financial sources
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import time
import random
from urllib.parse import quote
import concurrent.futures
import os


class NewsScraper:
    """Scrape financial news from multiple Indian sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.news_api_key = os.getenv('NEWS_API_KEY')
        
    def fetch_all_news(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch news from multiple sources concurrently
        Optimized: Skip scraping if API returns >= 12 articles
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')
            company_name: Full company name for better search
            
        Returns:
            List of news articles with title, source, and sentiment
        """
        all_news = []

        # Prefer API provider when configured because it is more stable than scraping.
        api_news = self._fetch_news_provider(symbol, company_name)
        all_news.extend(api_news)
        
        # Only run concurrent scraping if API didn't return enough articles
        if len(all_news) < 12:
            print(f"API returned {len(all_news)} articles, running concurrent scraping...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(self._scrape_moneycontrol, symbol, company_name): 'MoneyControl',
                    executor.submit(self._scrape_economictimes, symbol, company_name): 'Economic Times',
                    executor.submit(self._scrape_businessstandard, symbol, company_name): 'Business Standard',
                    executor.submit(self._scrape_ndtvprofit, symbol, company_name): 'NDTV Profit',
                    executor.submit(self._scrape_livemint, symbol, company_name): 'Livemint',
                }
                
                for future in concurrent.futures.as_completed(futures):
                    source = futures[future]
                    try:
                        news = future.result(timeout=8)
                        for item in news:
                            item['source'] = source
                        all_news.extend(news)
                        if len(all_news) >= 20:  # Early exit once we have enough
                            break
                    except Exception as e:
                        print(f"Error scraping {source}: {e}")
        
        # Remove duplicates based on title similarity
        all_news = self._remove_duplicates(all_news)
        
        return all_news

    def _fetch_news_provider(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch news from configured provider using NEWS_API_KEY."""
        if not self.news_api_key:
            return []

        # NewsData.io keys typically start with `pub_`.
        if self.news_api_key.startswith("pub_"):
            return self._fetch_newsdata(symbol, company_name)
        return self._fetch_newsapi_org(symbol, company_name)

    def _fetch_newsapi_org(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch news via NewsAPI.org endpoint."""

        query = company_name or symbol
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 30,
            "apiKey": self.news_api_key
        }

        try:
            response = self.session.get(url, params=params, timeout=8)
            if response.status_code != 200:
                print(f"NewsAPI.org error: {response.status_code} - {response.text[:200]}")
                return []

            payload = response.json()
            articles = payload.get("articles", [])
            results: List[Dict[str, Any]] = []
            for item in articles:
                title = (item.get("title") or "").strip()
                if len(title) < 20:
                    continue
                results.append({
                    "title": title,
                    "source": (item.get("source") or {}).get("name", "NewsAPI.org"),
                    "url": item.get("url", ""),
                    "published_at": item.get("publishedAt")
                })
            return results
        except Exception as e:
            print(f"NewsAPI.org fetch error: {e}")
            return []

    def _fetch_newsdata(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch news via NewsData.io endpoint."""
        query = company_name or symbol
        url = "https://newsdata.io/api/1/news"
        params = {
            "apikey": self.news_api_key,
            "q": query,
            "country": "in",
            "language": "en"
        }

        try:
            response = self.session.get(url, params=params, timeout=8)
            if response.status_code != 200:
                print(f"NewsData.io error: {response.status_code} - {response.text[:200]}")
                return []

            payload = response.json()
            articles = payload.get("results", [])
            results: List[Dict[str, Any]] = []
            for item in articles:
                title = (item.get("title") or "").strip()
                if len(title) < 20:
                    continue
                results.append({
                    "title": title,
                    "source": item.get("source_name", "NewsData.io"),
                    "url": item.get("link", ""),
                    "published_at": item.get("pubDate")
                })
            return results
        except Exception as e:
            print(f"NewsData.io fetch error: {e}")
            return []
    
    def _scrape_moneycontrol(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scrape news from MoneyControl"""
        news = []
        try:
            search_term = company_name or symbol
            url = f"https://www.moneycontrol.com/news/tags/{quote(search_term)}.html"
            
            response = self.session.get(url, timeout=5)
            if response.status_code != 200:
                # Try alternative URL
                url = f"https://www.moneycontrol.com/news/business/stocks/"
                response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('li', class_='clearfix') or soup.find_all('div', class_='news_listing')
                
                for article in articles[:15]:  # Get top 15 articles
                    title_elem = article.find('h2') or article.find('a')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title and len(title) > 20:  # Filter out short/empty titles
                            news.append({
                                'title': title,
                                'source': 'MoneyControl',
                                'url': title_elem.get('href', '')
                            })
        except Exception as e:
            print(f"MoneyControl scraping error: {e}")
        
        return news
    
    def _scrape_economictimes(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scrape news from Economic Times"""
        news = []
        try:
            search_term = company_name or symbol
            url = f"https://economictimes.indiatimes.com/topic/{quote(search_term)}"
            
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='content') or soup.find_all('div', class_='news_desc')
                
                for article in articles[:15]:
                    title_elem = article.find('a') or article.find('h3')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title and len(title) > 20:
                            news.append({
                                'title': title,
                                'source': 'Economic Times',
                                'url': title_elem.get('href', '')
                            })
        except Exception as e:
            print(f"Economic Times scraping error: {e}")
        
        return news
    
    def _scrape_businessstandard(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scrape news from Business Standard"""
        news = []
        try:
            search_term = company_name or symbol
            url = f"https://www.business-standard.com/search?q={quote(search_term)}"
            
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='article-list') or soup.find_all('div', class_='news-item')
                
                for article in articles[:10]:
                    title_elem = article.find('a') or article.find('h2')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title and len(title) > 20:
                            news.append({
                                'title': title,
                                'source': 'Business Standard',
                                'url': title_elem.get('href', '')
                            })
        except Exception as e:
            print(f"Business Standard scraping error: {e}")
        
        return news
    
    def _scrape_ndtvprofit(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scrape news from NDTV Profit"""
        news = []
        try:
            search_term = company_name or symbol
            url = f"https://www.ndtv.com/business/stocks/{quote(search_term.lower())}-news"
            
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='news_item') or soup.find_all('div', class_='story')
                
                for article in articles[:10]:
                    title_elem = article.find('a') or article.find('h2') or article.find('h3')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title and len(title) > 20:
                            news.append({
                                'title': title,
                                'source': 'NDTV Profit',
                                'url': title_elem.get('href', '')
                            })
        except Exception as e:
            print(f"NDTV Profit scraping error: {e}")
        
        return news
    
    def _scrape_livemint(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scrape news from Livemint"""
        news = []
        try:
            search_term = company_name or symbol
            url = f"https://www.livemint.com/search?q={quote(search_term)}"
            
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find news articles
                articles = soup.find_all('div', class_='listing') or soup.find_all('div', class_='article')
                
                for article in articles[:10]:
                    title_elem = article.find('a') or article.find('h2')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title and len(title) > 20:
                            news.append({
                                'title': title,
                                'source': 'Livemint',
                                'url': title_elem.get('href', '')
                            })
        except Exception as e:
            print(f"Livemint scraping error: {e}")
        
        return news
    
    def _remove_duplicates(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate news based on title similarity"""
        unique_news = []
        seen_titles = set()
        
        for news in news_list:
            title = news['title'].lower()
            # Simple deduplication - check if similar title exists
            is_duplicate = False
            for seen in seen_titles:
                # If titles are very similar (80% match), consider duplicate
                if self._similarity(title, seen) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_titles.add(title)
                unique_news.append(news)
        
        return unique_news
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate simple similarity between two strings"""
        # Simple word-based similarity
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


# Company name mappings for better search
COMPANY_NAMES = {
    'RELIANCE': 'Reliance Industries',
    'TCS': 'Tata Consultancy Services',
    'HDFCBANK': 'HDFC Bank',
    'INFY': 'Infosys',
    'ICICIBANK': 'ICICI Bank',
    'HINDUNILVR': 'Hindustan Unilever',
    'SBIN': 'State Bank of India',
    'BHARTIARTL': 'Bharti Airtel',
    'ITC': 'ITC Limited',
    'KOTAKBANK': 'Kotak Mahindra Bank',
    'LT': 'Larsen & Toubro',
    'AXISBANK': 'Axis Bank',
    'ASIANPAINT': 'Asian Paints',
    'MARUTI': 'Maruti Suzuki',
    'TITAN': 'Titan Company',
    'SUNPHARMA': 'Sun Pharmaceutical',
    'BAJFINANCE': 'Bajaj Finance',
    'WIPRO': 'Wipro',
    'ULTRACEMCO': 'UltraTech Cement',
    'NESTLEIND': 'Nestle India',
}
