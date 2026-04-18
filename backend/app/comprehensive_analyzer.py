"""
Comprehensive Stock Analysis Module
Combines technical, fundamental, sentiment, and risk analysis into professional-grade reports
"""

import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
import requests

from app.indicators import TechnicalIndicators, prepare_ml_features
from app.advanced_indicators import AdvancedTechnicalAnalyzer, get_support_resistance_zones
from app.fundamental_analysis import FundamentalAnalyzer
from app.sentiment import sentiment_analyzer
from app.ml_model import predictors
from app.professional_risk import ProfessionalRiskManager
from app.risk_manager import RiskManager
from app.ai_predictor import ai_predictor
from app.broker_analytics import BrokerAnalytics


class ComprehensiveStockAnalyzer:
    """Professional-grade stock analyzer that combines all analysis types"""
    
    def __init__(self, symbol: str, mode: str = 'swing', 
                 portfolio_value: float = 1000000):
        """
        Initialize comprehensive analyzer
        
        Args:
            symbol: Stock symbol
            mode: 'intraday', 'swing', or 'longterm'
            portfolio_value: Portfolio value for position sizing
        """
        self.symbol = symbol
        self.mode = mode
        self.portfolio_value = portfolio_value
        self.ticker = yf.Ticker(symbol)
        self.finnhub_api_key = (
            os.getenv('FINNHUB_API_KEY')
            or os.getenv('FINHUB_API_KEY')
            or os.getenv('FINNHUB_KEY')
            or os.getenv('FINNHUB_TOKEN')
            or os.getenv('FINNHUB_API_TOKEN')
        )
        self.finnhub_base_url = "https://finnhub.io/api/v1"

    def _finnhub_symbol_candidates(self) -> list[str]:
        clean_symbol = self.symbol.split('.')[0]
        return list(dict.fromkeys([self.symbol, clean_symbol, f"NSE:{clean_symbol}", f"BSE:{clean_symbol}"]))

    def _fetch_finnhub_insights(self) -> Dict[str, Any]:
        """Fetch advanced stock intelligence from Finnhub."""
        if not self.finnhub_api_key:
            return {
                "available": False,
                "provider": "finnhub",
                "message": "FINNHUB_API_KEY not configured"
            }

        for ticker in self._finnhub_symbol_candidates():
            params_base = {"symbol": ticker, "token": self.finnhub_api_key}
            try:
                quote_resp = requests.get(
                    f"{self.finnhub_base_url}/quote",
                    params=params_base,
                    timeout=6
                )
                recommendation_resp = requests.get(
                    f"{self.finnhub_base_url}/stock/recommendation",
                    params=params_base,
                    timeout=6
                )
                target_resp = requests.get(
                    f"{self.finnhub_base_url}/stock/price-target",
                    params=params_base,
                    timeout=6
                )
                profile_resp = requests.get(
                    f"{self.finnhub_base_url}/stock/profile2",
                    params=params_base,
                    timeout=6
                )
                earnings_resp = requests.get(
                    f"{self.finnhub_base_url}/stock/earnings",
                    params=params_base,
                    timeout=6
                )
            except requests.exceptions.RequestException as exc:
                print(f"Finnhub request failed for {ticker}: {exc}")
                continue

            # Quote access is mandatory; other endpoints are optional by plan.
            if quote_resp.status_code != 200:
                continue

            quote = quote_resp.json() if quote_resp.content else {}
            if not isinstance(quote, dict):
                continue
            current_price = float(quote.get("c", 0) or 0)
            # No usable quote coverage for this ticker mapping.
            if current_price <= 0:
                continue

            recommendation_rows = recommendation_resp.json() if recommendation_resp.status_code == 200 and recommendation_resp.content else []
            target = target_resp.json() if target_resp.status_code == 200 and target_resp.content else {}
            profile = profile_resp.json() if profile_resp.status_code == 200 and profile_resp.content else {}
            earnings_rows = earnings_resp.json() if earnings_resp.status_code == 200 and earnings_resp.content else []
            if not isinstance(recommendation_rows, list):
                recommendation_rows = []
            if not isinstance(target, dict):
                target = {}
            if not isinstance(profile, dict):
                profile = {}
            if not isinstance(earnings_rows, list):
                earnings_rows = []

            recommendation = recommendation_rows[0] if recommendation_rows else {}
            if not isinstance(recommendation, dict):
                recommendation = {}

            buy = int(recommendation.get("buy", 0) or 0)
            hold = int(recommendation.get("hold", 0) or 0)
            sell = int(recommendation.get("sell", 0) or 0)
            strong_buy = int(recommendation.get("strongBuy", 0) or 0)
            strong_sell = int(recommendation.get("strongSell", 0) or 0)
            total = buy + hold + sell + strong_buy + strong_sell

            weighted = (strong_buy * 2 + buy - sell - strong_sell * 2)
            if total == 0:
                consensus = "No analyst coverage"
            elif weighted >= total * 0.5:
                consensus = "Strong Bullish"
            elif weighted > 0:
                consensus = "Bullish"
            elif weighted <= -total * 0.5:
                consensus = "Strong Bearish"
            elif weighted < 0:
                consensus = "Bearish"
            else:
                consensus = "Neutral"

            target_mean = float(target.get("targetMean", 0) or 0)
            upside_pct = ((target_mean - current_price) / current_price * 100) if current_price > 0 and target_mean > 0 else 0.0

            signal_summary = (
                f"{consensus} analyst stance from {total} ratings. "
                f"Mean target implies {upside_pct:+.2f}% from current price."
            )

            latest_earnings = earnings_rows[0] if earnings_rows else {}
            if not isinstance(latest_earnings, dict):
                latest_earnings = {}

            return {
                "available": True,
                "provider": "finnhub",
                "symbol_used": ticker,
                "endpoint_access": {
                    "quote": quote_resp.status_code,
                    "stock_recommendation": recommendation_resp.status_code,
                    "stock_price_target": target_resp.status_code,
                    "stock_profile2": profile_resp.status_code,
                    "stock_earnings": earnings_resp.status_code
                },
                "analyst_recommendation": {
                    "buy": buy,
                    "hold": hold,
                    "sell": sell,
                    "strong_buy": strong_buy,
                    "strong_sell": strong_sell,
                    "total_ratings": total,
                    "consensus": consensus,
                    "period": recommendation.get("period", "")
                },
                "price_target": {
                    "target_high": target.get("targetHigh"),
                    "target_low": target.get("targetLow"),
                    "target_mean": target.get("targetMean"),
                    "target_median": target.get("targetMedian"),
                    "upside_percent_vs_current": round(upside_pct, 2),
                    "last_updated": target.get("lastUpdated", "")
                },
                "market_snapshot": {
                    "current": quote.get("c"),
                    "change": quote.get("d"),
                    "change_percent": quote.get("dp"),
                    "high": quote.get("h"),
                    "low": quote.get("l"),
                    "open": quote.get("o"),
                    "previous_close": quote.get("pc")
                },
                "company_profile": {
                    "name": profile.get("name"),
                    "exchange": profile.get("exchange"),
                    "finnhub_industry": profile.get("finnhubIndustry"),
                    "market_cap": profile.get("marketCapitalization"),
                    "currency": profile.get("currency"),
                    "country": profile.get("country")
                },
                "earnings_signal": {
                    "period": latest_earnings.get("period"),
                    "actual": latest_earnings.get("actual"),
                    "estimate": latest_earnings.get("estimate"),
                    "surprise_percent": latest_earnings.get("surprisePercent")
                },
                "signal_summary": signal_summary
            }

        return {
            "available": False,
            "provider": "finnhub",
            "message": "No Finnhub quote coverage for this symbol/tier. Common cause: plan limits for NSE/BSE resources."
        }
        
    def fetch_data(self) -> pd.DataFrame:
        """Fetch stock data based on mode"""
        if self.mode == 'intraday':
            df = self.ticker.history(period="5d", interval="5m")
        elif self.mode == 'swing':
            df = self.ticker.history(period="6mo", interval="1d")
        else:  # longterm
            df = self.ticker.history(period="2y", interval="1wk")
        
        if df.empty:
            raise ValueError(f"No data found for symbol {self.symbol}")
        
        return df
    
    def analyze_technical(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Complete technical analysis"""
        # Basic indicators
        ti = TechnicalIndicators(df)
        
        if self.mode == 'intraday':
            basic_indicators = ti.get_all_indicators_intraday()
        elif self.mode == 'swing':
            basic_indicators = ti.get_all_indicators_swing()
        else:
            basic_indicators = ti.get_all_indicators_longterm()
        
        # Advanced indicators
        advanced = AdvancedTechnicalAnalyzer(df)
        advanced_indicators = advanced.get_all_advanced_indicators()
        
        return {
            'basic': basic_indicators,
            'advanced': advanced_indicators,
            'current_price': basic_indicators['current_price'],
            'atr': basic_indicators['atr']
        }
    
    def analyze_fundamental(self) -> Dict[str, Any]:
        """Fundamental analysis"""
        try:
            analyzer = FundamentalAnalyzer(self.symbol)
            return analyzer.get_complete_fundamental_analysis()
        except Exception as e:
            return {
                'error': str(e),
                'symbol': self.symbol,
                'metrics': {},
                'valuation_assessment': {},
                'financial_health': {}
            }
    
    def analyze_sentiment(self) -> Dict[str, Any]:
        """Sentiment analysis"""
        return sentiment_analyzer.get_sentiment_for_stock(self.symbol)
    
    def analyze_ml(self, df: pd.DataFrame, mode: str) -> Dict[str, Any]:
        """ML prediction"""
        try:
            features = prepare_ml_features(df, mode)
            latest_features = features.iloc[-1:]
            predictor = predictors.get(mode, predictors['swing'])
            return predictor.predict(latest_features)
        except Exception as e:
            return {
                'up_probability': 50.0,
                'prediction': 'Neutral',
                'confidence': 'Low',
                'model_trained': False,
                'error': str(e)
            }
    
    def calculate_risk_management(self, 
                                  entry_price: float,
                                  technical_indicators: Dict,
                                  fundamental_analysis: Dict,
                                  sentiment_analysis: Dict) -> Dict[str, Any]:
        """Professional risk management"""
        # Basic risk calculation
        indicators = {
            'atr': technical_indicators['atr'],
            'trend': technical_indicators['basic']['trend'],
            'rsi': technical_indicators['basic']['rsi'],
            'sentiment_score': sentiment_analysis.get('sentiment_score', 0)
        }
        
        if 'volatility' in technical_indicators['basic']:
            indicators['volatility'] = technical_indicators['basic']['volatility']
        
        basic_risk_mgr = RiskManager(indicators)
        basic_risk = basic_risk_mgr.get_full_risk_assessment(entry_price)
        
        # Professional risk calculation
        pro_risk_mgr = ProfessionalRiskManager(
            portfolio_value=self.portfolio_value
        )
        
        # Calculate technical score (0-100)
        tech_score = self._calculate_technical_score(technical_indicators)
        
        # Calculate fundamental score (0-100)
        fund_score = self._calculate_fundamental_score(fundamental_analysis)
        
        # Calculate sentiment score (0-100)
        sent_score = self._calculate_sentiment_score(sentiment_analysis)
        
        # Get professional risk report
        risk_report = pro_risk_mgr.get_complete_risk_report(
            entry_price=entry_price,
            stop_loss=basic_risk['stop_loss']['stop_loss_price'],
            take_profit=basic_risk['take_profit']['take_profit_price'],
            atr=technical_indicators['atr'],
            technical_score=tech_score,
            fundamental_score=fund_score,
            sentiment_score=sent_score
        )
        
        return {
            'basic': basic_risk,
            'professional': risk_report
        }
    
    def _calculate_technical_score(self, technical: Dict) -> float:
        """Calculate technical analysis score (0-100)"""
        score = 50  # Neutral base
        
        basic = technical['basic']
        advanced = technical['advanced']
        
        # Trend score
        trend = basic['trend']
        if 'Strong Bullish' in trend:
            score += 20
        elif 'Bullish' in trend:
            score += 10
        elif 'Strong Bearish' in trend:
            score -= 20
        elif 'Bearish' in trend:
            score -= 10
        
        # RSI score
        rsi = basic['rsi']
        if rsi < 30:
            score += 10  # Oversold
        elif rsi > 70:
            score -= 10  # Overbought
        
        # Trend strength
        trend_strength = advanced.get('trend_strength', {})
        adx = trend_strength.get('adx', 0)
        if adx > 25:
            score += 10
        
        # Market structure
        structure = advanced.get('market_structure', {})
        if 'Uptrend' in structure.get('structure_type', ''):
            score += 10
        elif 'Downtrend' in structure.get('structure_type', ''):
            score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_fundamental_score(self, fundamental: Dict) -> float:
        """Calculate fundamental score (0-100)"""
        if 'error' in fundamental:
            return 50
        
        health = fundamental.get('financial_health', {})
        return health.get('health_percentage', 50)
    
    def _calculate_sentiment_score(self, sentiment: Dict) -> float:
        """Calculate sentiment score (0-100)"""
        score = 50  # Neutral
        sentiment_score = sentiment.get('sentiment_score', 0)
        
        # Convert -1 to 1 range to 0 to 100
        score = 50 + (sentiment_score * 50)
        
        return max(0, min(100, score))
    
    def get_ai_prediction(self,
                         technical: Dict,
                         fundamental: Dict,
                         sentiment: Dict,
                         ml: Dict,
                         risk: Dict,
                         df: pd.DataFrame) -> Dict[str, Any]:
        """Get comprehensive AI prediction"""
        technical_indicators = {
            'trend': technical['basic']['trend'],
            'rsi_value': technical['basic']['rsi'],
            'rsi_interpretation': technical['basic']['rsi_interpretation'],
            'macd_value': technical['basic'].get('macd'),
            'macd_signal': technical['basic'].get('macd_signal'),
            'macd_histogram': technical['basic'].get('macd_histogram'),
            'atr': technical['atr'],
            'current_price': technical['current_price']
        }
        
        # Add advanced indicators
        advanced = technical['advanced']
        if 'trend_strength' in advanced:
            ts = advanced['trend_strength']
            technical_indicators['adx'] = ts.get('adx')
            technical_indicators['trend_strength'] = ts.get('trend_strength')
        
        return ai_predictor.get_ai_prediction(
            symbol=self.symbol,
            current_price=technical['current_price'],
            mode=self.mode,
            technical_indicators=technical_indicators,
            sentiment_data=sentiment,
            ml_prediction=ml,
            risk_data=risk['basic'],
            price_history=df
        )
    
    def generate_professional_recommendation(self,
                                           technical: Dict,
                                           fundamental: Dict,
                                           sentiment: Dict,
                                           risk: Dict,
                                           ai: Dict) -> Dict[str, Any]:
        """Generate comprehensive professional recommendation"""
        
        # Calculate composite score
        tech_score = self._calculate_technical_score(technical)
        fund_score = self._calculate_fundamental_score(fundamental)
        sent_score = self._calculate_sentiment_score(sentiment)
        
        # Weight the scores
        composite = (tech_score * 0.40 + 
                    fund_score * 0.35 + 
                    sent_score * 0.25)
        
        # Risk adjustment
        risk_level = risk['basic']['risk_level']
        if risk_level == 'High':
            composite -= 10
        elif risk_level == 'Low':
            composite += 5
        
        # Determine recommendation
        if composite >= 75:
            recommendation = 'STRONG BUY'
            action = 'Initiate full position immediately'
            confidence = 'Very High'
        elif composite >= 60:
            recommendation = 'BUY'
            action = 'Initiate 75% position'
            confidence = 'High'
        elif composite >= 50:
            recommendation = 'MODERATE BUY'
            action = 'Initiate 50% position or wait for better entry'
            confidence = 'Medium'
        elif composite >= 40:
            recommendation = 'HOLD'
            action = 'Hold existing positions, avoid new entries'
            confidence = 'Medium'
        elif composite >= 25:
            recommendation = 'REDUCE'
            action = 'Reduce position size by 25-50%'
            confidence = 'Medium-Low'
        else:
            recommendation = 'SELL'
            action = 'Exit position completely'
            confidence = 'High'
        
        # Generate detailed reasoning
        reasoning = self._generate_reasoning(
            technical, fundamental, sentiment, risk, ai, composite
        )
        
        return {
            'recommendation': recommendation,
            'action': action,
            'confidence': confidence,
            'composite_score': round(composite, 1),
            'component_scores': {
                'technical': round(tech_score, 1),
                'fundamental': round(fund_score, 1),
                'sentiment': round(sent_score, 1)
            },
            'reasoning': reasoning,
            'time_horizon': self._get_time_horizon(),
            'risk_profile': risk_level,
            'expected_return': self._estimate_return(ai, risk),
            'position_sizing': risk.get('professional', {}).get('position_sizing', {})
        }
    
    def _generate_reasoning(self, technical, fundamental, sentiment, risk, ai, score):
        """Generate detailed reasoning for recommendation"""
        reasons = []
        
        # Technical reasoning
        basic = technical['basic']
        if 'Bullish' in basic['trend']:
            reasons.append(f"Technical: {basic['trend']} trend with RSI at {basic['rsi']}")
        elif 'Bearish' in basic['trend']:
            reasons.append(f"Technical: {basic['trend']} trend with RSI at {basic['rsi']}")
        
        # Fundamental reasoning
        if 'financial_health' in fundamental:
            health = fundamental['financial_health']
            reasons.append(f"Fundamental: Financial health score {health.get('health_percentage', 'N/A')}%")
        
        # Sentiment reasoning
        reasons.append(f"Sentiment: {sentiment.get('sentiment_classification', 'Neutral')} news sentiment")
        
        # Risk reasoning
        risk_level = risk['basic']['risk_level']
        reasons.append(f"Risk: {risk_level} risk level with proper stop-loss at {risk['basic']['stop_loss']['stop_loss_percent']}%")
        
        # AI reasoning
        if 'reasoning' in ai:
            reasons.append(f"AI Analysis: {ai['reasoning'][:100]}...")
        
        return " | ".join(reasons)
    
    def _get_time_horizon(self) -> str:
        """Get time horizon based on mode"""
        horizons = {
            'intraday': 'Same day to 1-3 days',
            'swing': '1-4 weeks',
            'longterm': '3-12 months'
        }
        return horizons.get(self.mode, 'Variable')
    
    def _estimate_return(self, ai: Dict, risk: Dict) -> Dict[str, Any]:
        """Estimate potential return"""
        ai_pred = ai.get('ai_prediction', 'NEUTRAL')
        confidence = ai.get('confidence', 50)
        
        if ai_pred == 'UP':
            upside = min(confidence * 0.5, 25)  # Cap at 25%
            return {
                'expected_upside': f"+{upside:.1f}%",
                'target_hit_probability': f"{confidence}%",
                'risk_reward': risk.get('basic', {}).get('take_profit', {}).get('risk_reward_ratio', 0)
            }
        elif ai_pred == 'DOWN':
            downside = min(confidence * 0.3, 15)  # Cap at 15%
            return {
                'expected_downside': f"-{downside:.1f}%",
                'stop_loss_probability': f"{confidence}%",
                'risk_reward': risk.get('basic', {}).get('take_profit', {}).get('risk_reward_ratio', 0)
            }
        else:
            return {
                'expected_return': '0-5%',
                'consolidation_probability': 'High'
            }

    def _build_external_api_signal(self, sentiment: Dict[str, Any], finnhub_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Blend external API outputs into a single actionable signal."""
        sentiment_score = float(sentiment.get("sentiment_score", 0) or 0)
        breakdown = sentiment.get("breakdown", {}) if isinstance(sentiment.get("breakdown"), dict) else {}
        positive = int(breakdown.get("positive", 0) or 0)
        negative = int(breakdown.get("negative", 0) or 0)
        total_news = int(sentiment.get("articles_count", 0) or 0)
        scope = sentiment.get("analysis_scope", {}) if isinstance(sentiment.get("analysis_scope"), dict) else {}
        analyzed_count = int(scope.get("articles_analyzed_for_sentiment", 0) or 0)

        analyst_consensus = "Not Available"
        analyst_bias = 0.0
        target_upside = 0.0
        endpoint_access: Dict[str, Any] = {}
        if isinstance(finnhub_insights, dict) and finnhub_insights.get("available"):
            rec = finnhub_insights.get("analyst_recommendation", {})
            if isinstance(rec, dict):
                analyst_consensus = str(rec.get("consensus", "Not Available"))
                if "Strong Bullish" in analyst_consensus:
                    analyst_bias = 1.0
                elif "Bullish" in analyst_consensus:
                    analyst_bias = 0.6
                elif "Strong Bearish" in analyst_consensus:
                    analyst_bias = -1.0
                elif "Bearish" in analyst_consensus:
                    analyst_bias = -0.6
            target = finnhub_insights.get("price_target", {})
            if isinstance(target, dict):
                target_upside = float(target.get("upside_percent_vs_current", 0) or 0)
            endpoint_access = finnhub_insights.get("endpoint_access", {}) if isinstance(finnhub_insights.get("endpoint_access"), dict) else {}

        news_bias = max(-1.0, min(1.0, sentiment_score))
        upside_bias = max(-1.0, min(1.0, target_upside / 20.0))
        composite = (news_bias * 0.45) + (analyst_bias * 0.35) + (upside_bias * 0.20)

        if composite >= 0.45:
            stance = "Bullish"
        elif composite <= -0.45:
            stance = "Bearish"
        else:
            stance = "Neutral"

        confidence = min(95, max(35, int(50 + abs(composite) * 45)))

        return {
            "stance": stance,
            "confidence_percent": confidence,
            "composite_score": round(composite, 3),
            "drivers": {
                "news_sentiment_score": round(sentiment_score, 3),
                "news_positive_vs_negative": f"{positive}:{negative}",
                "analyst_consensus": analyst_consensus,
                "target_upside_percent": round(target_upside, 2)
            },
            "coverage": {
                "fetched_articles": total_news,
                "analyzed_articles": analyzed_count,
                "finnhub_endpoint_access": endpoint_access
            }
        }
    
    def get_complete_analysis(self, fast_mode: bool = False) -> Dict[str, Any]:
        """
        Get complete professional analysis with parallel execution
        
        Args:
            fast_mode: If True, skip fundamental analysis and use simplified sentiment
            
        Returns:
            Comprehensive analysis dictionary
        """
        start_time = time.time()
        timings = {}
        
        # Fetch data (sequential, needed by others)
        fetch_start = time.time()
        df = self.fetch_data()
        timings['data_fetch_ms'] = int((time.time() - fetch_start) * 1000)
        
        # Parallel execution of independent tasks using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            tech_start = time.time()
            tech_future = executor.submit(self.analyze_technical, df)
            
            if not fast_mode:
                fund_start = time.time()
                fund_future = executor.submit(self.analyze_fundamental)
            
            sent_start = time.time()
            sent_future = executor.submit(self.analyze_sentiment)
            
            ml_start = time.time()
            ml_future = executor.submit(self.analyze_ml, df, self.mode)
            
            # Collect results
            try:
                technical = tech_future.result(timeout=15)
                timings['technical_ms'] = int((time.time() - tech_start) * 1000)
            except Exception as e:
                print(f"Technical analysis failed: {e}")
                technical = self._get_default_technical(df)
                timings['technical_ms'] = int((time.time() - tech_start) * 1000)
            
            try:
                fundamental = fund_future.result(timeout=20) if not fast_mode else {'fast_mode_skipped': True, 'financial_health': {}}
                timings['fundamental_ms'] = int((time.time() - fund_start) * 1000) if not fast_mode else 0
            except Exception as e:
                print(f"Fundamental analysis failed: {e}")
                fundamental = {'error': str(e), 'metrics': {}, 'valuation_assessment': {}, 'financial_health': {}}
                timings['fundamental_ms'] = int((time.time() - fund_start) * 1000)
            
            try:
                sentiment = sent_future.result(timeout=30)
                timings['sentiment_ms'] = int((time.time() - sent_start) * 1000)
            except Exception as e:
                print(f"Sentiment analysis failed: {e}")
                import traceback
                traceback.print_exc()
                sentiment = {
                    'symbol': self.symbol,
                    'sentiment_score': 0,
                    'sentiment_classification': 'Neutral',
                    'method': 'fallback',
                    'headlines_count': 0,
                    'sources': [],
                    'news_articles': [],
                    'breakdown': {'positive': 0, 'negative': 0, 'neutral': 0}
                }
                timings['sentiment_ms'] = int((time.time() - sent_start) * 1000)
            
            try:
                ml = ml_future.result(timeout=10)
                timings['ml_ms'] = int((time.time() - ml_start) * 1000)
            except Exception as e:
                print(f"ML prediction failed: {e}")
                ml = {'up_probability': 50.0, 'prediction': 'Neutral', 'confidence': 'Low', 'error': str(e)}
                timings['ml_ms'] = int((time.time() - ml_start) * 1000)
        
        # Calculate risk (depends on technical, fundamental, sentiment)
        risk_start = time.time()
        risk = self.calculate_risk_management(
            technical['current_price'],
            technical,
            fundamental,
            sentiment
        )
        timings['risk_ms'] = int((time.time() - risk_start) * 1000)
        
        # Get AI prediction (depends on all previous analyses)
        ai_start = time.time()
        ai = self.get_ai_prediction(
            technical, fundamental, sentiment, ml, risk, df
        )
        timings['ai_ms'] = int((time.time() - ai_start) * 1000)
        
        # Generate recommendation
        rec_start = time.time()
        recommendation = self.generate_professional_recommendation(
            technical, fundamental, sentiment, risk, ai
        )
        timings['recommendation_ms'] = int((time.time() - rec_start) * 1000)
        
        total_time = int((time.time() - start_time) * 1000)
        timings['total_ms'] = total_time
        
        # Initialize broker analytics
        broker = BrokerAnalytics(self.symbol)
        
        # Get broker-level recommendations and analysis
        tech_score = self._calculate_technical_score(technical)
        fund_score = self._calculate_fundamental_score(fundamental)
        sent_score = self._calculate_sentiment_score(sentiment)
        
        broker_rec = broker.get_broker_recommendations(
            technical_score=tech_score,
            sentiment_score=sent_score,
            ml_prediction=ml['up_probability'] if 'up_probability' in ml else 50,
            current_price=technical['current_price'],
            support_level=technical['basic'].get('support') if 'basic' in technical else None,
            resistance_level=technical['basic'].get('resistance') if 'basic' in technical else None
        )
        
        dividend_info = broker.get_dividend_info()
        corporate_actions = broker.get_corporate_actions()
        earnings = broker.get_earnings_schedule()
        analyst_ratings = broker.get_analyst_ratings()
        sector_comp = broker.get_sector_comparison()
        finnhub_insights = self._fetch_finnhub_insights()
        external_api_signal = self._build_external_api_signal(sentiment, finnhub_insights)
        
        # Extract analyzed news from sentiment data
        news_articles = sentiment.get('news_articles', [])

        # Handle case where news_articles might be strings instead of dicts
        if news_articles and isinstance(news_articles[0], str):
            news_articles = [{'title': article, 'source': 'Sample', 'url': ''} for article in news_articles]

        news_summary = broker.get_news_summary(news_articles) if news_articles else {
            'total_articles': 0,
            'key_news': [],
            'news_sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0}
        }

        result = {
            'symbol': self.symbol,
            'mode': self.mode,
            'timestamp': datetime.now().isoformat(),
            'current_price': float(technical['current_price']),
            
            # Core analysis
            'technical_analysis': technical,
            'fundamental_analysis': fundamental,
            'sentiment_analysis': sentiment,
            'ml_prediction': ml,
            'risk_management': risk,
            'ai_prediction': ai,
            'professional_recommendation': recommendation,
            
            # Broker-level features
            'broker_intelligence': {
                'broker_recommendation': broker_rec,
                'analyst_consensus': analyst_ratings,
                'dividend_information': dividend_info,
                'corporate_actions': corporate_actions,
                'earnings_information': earnings,
                'sector_comparison': sector_comp,
                'news_analysis': news_summary
            },
            'finnhub_insights': finnhub_insights,
            'external_api_signal': external_api_signal,
            
            # Analyzed news articles (what sentiment was calculated from)
            'analyzed_news': {
                'total_articles_analyzed': len(news_articles),
                'news_articles': news_articles[:20],  # Top 20 articles
                'sentiment_breakdown': sentiment.get('breakdown', {}),
                'news_sources': sentiment.get('sources', [])
            },
            
            # Performance tracking
            'performance_metrics': {
                'analysis_mode': 'fast' if fast_mode else 'full',
                'timings_ms': timings,
                'quality_score': 95 if total_time < 5000 else (90 if total_time < 10000 else 85)
            },
            
            'disclaimer': 'This analysis is for educational purposes only and does not constitute financial advice. Stock market investments carry significant risks. Please consult a SEBI-registered financial advisor before making any investment decisions.'
        }
        
        # Convert to JSON-serializable format
        return self._convert_to_json_serializable(result)
    
    def _get_default_technical(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Return default technical analysis when primary fails"""
        return {
            'basic': {
                'trend': 'Neutral',
                'rsi': 50,
                'rsi_interpretation': 'Neutral',
                'macd': 0,
                'macd_signal': 0,
                'macd_histogram': 0,
                'current_price': float(df['Close'].iloc[-1]) if not df.empty else 0,
                'volatility': 0
            },
            'advanced': {},
            'current_price': float(df['Close'].iloc[-1]) if not df.empty else 0,
            'atr': 0
        }
    
    def _convert_to_json_serializable(self, obj):
        """Recursively convert numpy types and other non-serializable objects to Python native types"""
        import numpy as np
        from dataclasses import asdict, is_dataclass
        
        if isinstance(obj, dict):
            return {k: self._convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(item) for item in obj]
        elif isinstance(obj, pd.DataFrame):
            # Convert DataFrame to dict of records
            return obj.to_dict('records')
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            val = float(obj)
            return None if np.isnan(val) or np.isinf(val) else val
        elif isinstance(obj, np.ndarray):
            return [self._convert_to_json_serializable(x) for x in obj.tolist()]
        elif isinstance(obj, float):
            return None if np.isnan(obj) or np.isinf(obj) else obj
        elif is_dataclass(obj):
            return self._convert_to_json_serializable(asdict(obj))
        elif obj is None:
            return None
        elif isinstance(obj, (int, str, bool)):
            return obj
        elif hasattr(obj, 'item'):  # numpy scalar
            val = obj.item()
            if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                return None
            return val
        else:
            return obj
