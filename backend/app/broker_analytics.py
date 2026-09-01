"""
Broker-Level Analytics Module
Provides institutional-grade portfolio analytics and broker replacement features
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class BrokerAnalytics:
    """Comprehensive broker-level analytics replacing traditional broker roles"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
    
    def get_portfolio_metrics(self, 
                            shares: int,
                            entry_price: float,
                            current_price: float) -> Dict[str, Any]:
        """Calculate portfolio metrics for position tracking"""
        
        investment = shares * entry_price
        current_value = shares * current_price
        profit_loss = current_value - investment
        profit_loss_pct = (profit_loss / investment * 100) if investment != 0 else 0
        
        return {
            'shares': shares,
            'entry_price': round(entry_price, 2),
            'current_price': round(current_price, 2),
            'investment_amount': round(investment, 2),
            'current_value': round(current_value, 2),
            'profit_loss': round(profit_loss, 2),
            'profit_loss_pct': round(profit_loss_pct, 2),
            'unrealized_gain_loss': 'PROFIT' if profit_loss > 0 else ('LOSS' if profit_loss < 0 else 'NEUTRAL')
        }
    
    def get_broker_recommendations(self,
                                  technical_score: float,
                                  sentiment_score: float,
                                  ml_prediction: float,
                                  current_price: float,
                                  support_level: Optional[float] = None,
                                  resistance_level: Optional[float] = None) -> Dict[str, Any]:
        """Provide broker-style buy/sell/hold recommendations"""
        
        # Weighted composite score
        composite = (technical_score * 0.35 + 
                    sentiment_score * 0.25 + 
                    ml_prediction * 0.40)
        
        # Entry points
        entry_point = current_price
        if support_level:
            entry_point = round(support_level * 1.02, 2)  # 2% above support
        
        # Target levels
        if resistance_level and support_level:
            range_size = resistance_level - support_level
            target1 = round(current_price + (range_size * 0.25), 2)
            target2 = round(current_price + (range_size * 0.50), 2)
            target3 = round(current_price + (range_size * 0.75), 2)
        else:
            target1 = round(current_price * 1.05, 2)
            target2 = round(current_price * 1.10, 2)
            target3 = round(current_price * 1.15, 2)
        
        # Stop loss
        if support_level:
            stop_loss = round(support_level * 0.98, 2)
        else:
            stop_loss = round(current_price * 0.95, 2)
        
        # Action signal
        if composite >= 75:
            action = 'STRONG BUY'
            conviction = 'Very High'
            risk_level = 'Low'
        elif composite >= 60:
            action = 'BUY'
            conviction = 'High'
            risk_level = 'Medium'
        elif composite >= 50:
            action = 'ACCUMULATE'
            conviction = 'Medium'
            risk_level = 'Medium'
        elif composite >= 40:
            action = 'HOLD'
            conviction = 'Medium'
            risk_level = 'Medium-High'
        elif composite >= 25:
            action = 'REDUCE'
            conviction = 'Medium-Low'
            risk_level = 'High'
        else:
            action = 'SELL'
            conviction = 'High'
            risk_level = 'Very High'
        
        return {
            'recommendation': action,
            'conviction': conviction,
            'risk_level': risk_level,
            'composite_score': round(composite, 1),
            'entry_point': entry_point,
            'stop_loss': stop_loss,
            'targets': {
                'target_1': target1,
                'target_2': target2,
                'target_3': target3
            },
            'risk_reward_ratio': round((target2 - entry_point) / (entry_point - stop_loss), 2) if entry_point != stop_loss else 0
        }
    
    def get_dividend_info(self) -> Dict[str, Any]:
        """Get dividend and corporate action information"""
        try:
            dividends = self.ticker.dividends
            if dividends.empty:
                return {
                    'dividend_yield': 0,
                    'annual_dividend': 0,
                    'last_dividend_date': None,
                    'ex_dividend_dates': []
                }
            
            annual_dividend = dividends.tail(4).sum()  # Last 4 quarters
            current_price = (self.ticker.info or {}).get('currentPrice', 1)
            dividend_yield = (annual_dividend / current_price * 100) if current_price else 0
            
            return {
                'dividend_yield': round(dividend_yield, 2),
                'annual_dividend': round(annual_dividend, 2),
                'last_dividend_date': str(dividends.index[-1]) if len(dividends) > 0 else None,
                'ex_dividend_dates': [str(d) for d in dividends.tail(12).index]
            }
        except Exception as e:
            print(f"Error fetching dividend info: {e}")
            return {
                'dividend_yield': 0,
                'annual_dividend': 0,
                'last_dividend_date': None,
                'ex_dividend_dates': []
            }
    
    def get_corporate_actions(self) -> Dict[str, Any]:
        """Get stock splits and other corporate actions"""
        try:
            splits = self.ticker.splits
            if splits.empty:
                return {
                    'stock_splits': [],
                    'recent_splits': None
                }
            
            return {
                'stock_splits': [{'date': str(d), 'ratio': float(v)} for d, v in splits.items()],
                'recent_splits': f"{float(splits.iloc[-1])}:1 on {str(splits.index[-1])}" if len(splits) > 0 else None
            }
        except Exception as e:
            print(f"Error fetching corporate actions: {e}")
            return {
                'stock_splits': [],
                'recent_splits': None
            }
    
    def get_earnings_schedule(self) -> Dict[str, Any]:
        """Get next earnings date and historical earnings"""
        try:
            info = self.ticker.info or {}
            next_earnings = info.get('earningsDate', [None])
            
            return {
                'next_earnings_date': str(next_earnings[0]) if next_earnings and next_earnings[0] else None,
                'eps': round(info.get('eps', 0), 2),
                'pe_ratio': round(info.get('trailingPE', 0), 2),
                'forward_pe': round(info.get('forwardPE', 0), 2),
                'peg_ratio': round(info.get('pegRatio', 0), 2)
            }
        except Exception as e:
            print(f"Error fetching earnings schedule: {e}")
            return {
                'next_earnings_date': None,
                'eps': 0,
                'pe_ratio': 0,
                'forward_pe': 0,
                'peg_ratio': 0
            }
    
    def get_analyst_ratings(self) -> Dict[str, Any]:
        """Simulated analyst consensus (real data from broker APIs)"""
        try:
            info = self.ticker.info or {}
            recommendations = info.get('recommendationKey', 'hold')
            target_price = info.get('targetMeanPrice', None)
            
            rating_map = {
                'strong_buy': 'Strong Buy',
                'buy': 'Buy',
                'hold': 'Hold',
                'sell': 'Sell',
                'strong_sell': 'Strong Sell'
            }
            
            current_price = info.get('currentPrice', None)
            return {
                'consensus_rating': rating_map.get(recommendations, 'Hold'),
                'target_price': round(target_price, 2) if target_price else None,
                'upside_potential': round((target_price / current_price - 1) * 100, 2) if target_price and current_price else None,
                'number_of_analysts': info.get('numberOfAnalystRatings', 0)
            }
        except Exception as e:
            print(f"Error fetching analyst ratings: {e}")
            return {
                'consensus_rating': 'Hold',
                'target_price': None,
                'upside_potential': None,
                'number_of_analysts': 0
            }
    
    def get_sector_comparison(self) -> Dict[str, Any]:
        """Compare stock performance to sector and market"""
        try:
            info = self.ticker.info or {}
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            week_change = info.get('52WeekChange', 0) or 0
            
            return {
                'sector': sector,
                'industry': industry,
                'sector_52w_change': round(float(week_change) * 100, 2),
                'market_cap': info.get('marketCap', 0),
                'relative_strength_vs_market': 'Outperforming' if week_change > 0.15 else 'Underperforming'
            }
        except Exception as e:
            print(f"Error fetching sector comparison: {e}")
            return {
                'sector': 'Unknown',
                'industry': 'Unknown',
                'sector_52w_change': 0,
                'market_cap': 0,
                'relative_strength_vs_market': 'Unknown'
            }
    
    def get_news_summary(self, news_articles: List[Dict]) -> Dict[str, Any]:
        """Summarize key news impact"""
        if not news_articles:
            return {
                'total_articles': 0,
                'key_news': [],
                'news_sentiment_distribution': {
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0
                },
                'most_recent_news': None
            }
        
        # Handle case where articles might be strings instead of dicts
        processed_articles = []
        for a in news_articles:
            if isinstance(a, str):
                processed_articles.append({'title': a, 'source': 'Sample', 'sentiment': 'neutral'})
            elif isinstance(a, dict):
                processed_articles.append(a)

        # Group by sentiment (simplified)
        positive = sum(1 for a in processed_articles if 'positive' in str(a.get('sentiment', '')).lower())
        negative = sum(1 for a in processed_articles if 'negative' in str(a.get('sentiment', '')).lower())
        neutral = len(processed_articles) - positive - negative

        # Key news
        key_news = [
            {
                'title': a.get('title', 'Unknown'),
                'source': a.get('source', 'Unknown'),
                'published': a.get('published_at', 'N/A')
            }
            for a in processed_articles[:5]
        ]
        
        return {
            'total_articles': len(processed_articles),
            'key_news': key_news,
            'news_sentiment_distribution': {
                'positive': positive,
                'negative': negative,
                'neutral': neutral
            },
            'most_recent_news': key_news[0] if key_news else None
        }


# Global instance
broker_analytics = BrokerAnalytics

