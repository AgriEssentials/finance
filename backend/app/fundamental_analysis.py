"""
Fundamental Analysis Module
Provides professional fundamental analysis metrics and ratios
Includes intelligent caching for improved performance
"""

import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

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


@dataclass
class FundamentalMetrics:
    """Core fundamental metrics for stock analysis"""
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    peg_ratio: Optional[float]
    pb_ratio: Optional[float]
    ps_ratio: Optional[float]
    ev_ebitda: Optional[float]
    
    # Profitability
    roe: Optional[float]  # Return on Equity
    roa: Optional[float]  # Return on Assets
    roic: Optional[float]  # Return on Invested Capital
    gross_margin: Optional[float]
    operating_margin: Optional[float]
    profit_margin: Optional[float]
    
    # Financial Health
    debt_to_equity: Optional[float]
    debt_to_assets: Optional[float]
    current_ratio: Optional[float]
    quick_ratio: Optional[float]
    interest_coverage: Optional[float]
    
    # Growth
    revenue_growth: Optional[float]
    earnings_growth: Optional[float]
    book_value_growth: Optional[float]
    
    # Valuation
    dividend_yield: Optional[float]
    payout_ratio: Optional[float]
    
    # Efficiency
    asset_turnover: Optional[float]
    inventory_turnover: Optional[float]
    receivables_turnover: Optional[float]


class FundamentalAnalyzer:
    """Professional fundamental analysis for Indian stocks"""
    
    def __init__(self, symbol: str):
        """
        Initialize with stock symbol
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
        """
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        self.info = self.ticker.info
        
    def get_fundamental_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive fundamental metrics
        
        Returns:
            Dictionary with all fundamental metrics
        """
        try:
            metrics = FundamentalMetrics(
                pe_ratio=self.info.get('trailingPE'),
                forward_pe=self.info.get('forwardPE'),
                peg_ratio=self.info.get('pegRatio'),
                pb_ratio=self.info.get('priceToBook'),
                ps_ratio=self.info.get('priceToSalesTrailing12Months'),
                ev_ebitda=self.info.get('enterpriseToEbitda'),
                
                roe=self.info.get('returnOnEquity'),
                roa=self.info.get('returnOnAssets'),
                roic=self.info.get('returnOnCapitalEmployed'),
                gross_margin=self.info.get('grossMargins'),
                operating_margin=self.info.get('operatingMargins'),
                profit_margin=self.info.get('profitMargins'),
                
                debt_to_equity=self.info.get('debtToEquity'),
                debt_to_assets=None,  # Calculate manually if needed
                current_ratio=self.info.get('currentRatio'),
                quick_ratio=self.info.get('quickRatio'),
                interest_coverage=self.info.get('interestCoverage'),
                
                revenue_growth=self.info.get('revenueGrowth'),
                earnings_growth=self.info.get('earningsGrowth'),
                book_value_growth=None,  # Requires historical data
                
                dividend_yield=self.info.get('dividendYield'),
                payout_ratio=self.info.get('payoutRatio'),
                
                asset_turnover=self.info.get('totalAssets') / self.info.get('totalRevenue') if self.info.get('totalAssets') and self.info.get('totalRevenue') else None,
                inventory_turnover=None,
                receivables_turnover=None
            )
            
            # Convert to dictionary and format
            result = {}
            for field, value in metrics.__dict__.items():
                if value is not None:
                    # Convert to percentage if ratio
                    if field in ['roe', 'roa', 'roic', 'gross_margin', 'operating_margin', 
                                'profit_margin', 'revenue_growth', 'earnings_growth',
                                'dividend_yield', 'payout_ratio']:
                        result[field] = round(value * 100, 2)  # Convert to percentage
                    else:
                        result[field] = round(value, 2)
                else:
                    result[field] = None
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_valuation_assessment(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide valuation assessment based on metrics
        
        Args:
            metrics: Fundamental metrics dictionary
            
        Returns:
            Valuation assessment
        """
        assessments = []
        valuation_score = 0
        
        # P/E Ratio assessment
        pe = metrics.get('pe_ratio')
        if pe:
            if pe < 15:
                assessments.append({
                    'metric': 'P/E Ratio',
                    'value': pe,
                    'assessment': 'Undervalued',
                    'reason': 'Below market average (15x)',
                    'score': 2
                })
                valuation_score += 2
            elif pe > 30:
                assessments.append({
                    'metric': 'P/E Ratio',
                    'value': pe,
                    'assessment': 'Overvalued',
                    'reason': 'Above market average (30x)',
                    'score': -2
                })
                valuation_score -= 2
            else:
                assessments.append({
                    'metric': 'P/E Ratio',
                    'value': pe,
                    'assessment': 'Fair Value',
                    'reason': 'Within normal range',
                    'score': 0
                })
        
        # P/B Ratio assessment
        pb = metrics.get('pb_ratio')
        if pb:
            if pb < 1:
                assessments.append({
                    'metric': 'P/B Ratio',
                    'value': pb,
                    'assessment': 'Undervalued',
                    'reason': 'Trading below book value',
                    'score': 2
                })
                valuation_score += 2
            elif pb < 3:
                assessments.append({
                    'metric': 'P/B Ratio',
                    'value': pb,
                    'assessment': 'Fair Value',
                    'reason': 'Within reasonable range',
                    'score': 0
                })
            else:
                assessments.append({
                    'metric': 'P/B Ratio',
                    'value': pb,
                    'assessment': 'Overvalued',
                    'reason': 'High premium to book value',
                    'score': -1
                })
                valuation_score -= 1
        
        # ROE assessment
        roe = metrics.get('roe')
        if roe:
            if roe > 20:
                assessments.append({
                    'metric': 'ROE',
                    'value': f"{roe}%",
                    'assessment': 'Excellent',
                    'reason': 'Above 20% indicates strong profitability',
                    'score': 3
                })
                valuation_score += 3
            elif roe > 15:
                assessments.append({
                    'metric': 'ROE',
                    'value': f"{roe}%",
                    'assessment': 'Good',
                    'reason': 'Above 15% is healthy',
                    'score': 2
                })
                valuation_score += 2
            elif roe > 10:
                assessments.append({
                    'metric': 'ROE',
                    'value': f"{roe}%",
                    'assessment': 'Average',
                    'reason': 'Acceptable but not exceptional',
                    'score': 0
                })
            else:
                assessments.append({
                    'metric': 'ROE',
                    'value': f"{roe}%",
                    'assessment': 'Poor',
                    'reason': 'Below 10% indicates weak returns',
                    'score': -1
                })
                valuation_score -= 1
        
        # Debt assessment
        debt_to_equity = metrics.get('debt_to_equity')
        if debt_to_equity is not None:
            if debt_to_equity < 50:
                assessments.append({
                    'metric': 'Debt-to-Equity',
                    'value': debt_to_equity,
                    'assessment': 'Low Risk',
                    'reason': 'Conservative debt levels',
                    'score': 2
                })
                valuation_score += 2
            elif debt_to_equity > 100:
                assessments.append({
                    'metric': 'Debt-to-Equity',
                    'value': debt_to_equity,
                    'assessment': 'High Risk',
                    'reason': 'High leverage increases risk',
                    'score': -2
                })
                valuation_score -= 2
            else:
                assessments.append({
                    'metric': 'Debt-to-Equity',
                    'value': debt_to_equity,
                    'assessment': 'Moderate',
                    'reason': 'Manageable debt levels',
                    'score': 0
                })
        
        # Overall valuation verdict
        if valuation_score >= 4:
            overall = 'Undervalued - Strong Buy Opportunity'
        elif valuation_score >= 2:
            overall = 'Slightly Undervalued - Good Buy'
        elif valuation_score >= -1:
            overall = 'Fairly Valued - Hold'
        elif valuation_score >= -3:
            overall = 'Slightly Overvalued - Consider Selling'
        else:
            overall = 'Overvalued - Consider Selling'
        
        return {
            'metrics_assessed': assessments,
            'valuation_score': valuation_score,
            'overall_assessment': overall,
            'investment_grade': self._get_investment_grade(valuation_score)
        }
    
    def _get_investment_grade(self, score: int) -> str:
        """Convert score to investment grade"""
        if score >= 6:
            return 'A+ (Excellent)'
        elif score >= 4:
            return 'A (Very Good)'
        elif score >= 2:
            return 'B+ (Good)'
        elif score >= 0:
            return 'B (Average)'
        elif score >= -2:
            return 'C (Below Average)'
        else:
            return 'D (Poor)'
    
    def get_financial_health_score(self) -> Dict[str, Any]:
        """
        Calculate overall financial health score
        
        Returns:
            Financial health assessment
        """
        metrics = self.get_fundamental_metrics()
        
        score = 0
        max_score = 0
        details = []
        
        # Profitability (max 30 points)
        max_score += 30
        profitability_score = 0
        if metrics.get('roe') and metrics['roe'] > 15:
            profitability_score += 10
        if metrics.get('roa') and metrics['roa'] > 5:
            profitability_score += 10
        if metrics.get('profit_margin') and metrics['profit_margin'] > 10:
            profitability_score += 10
        score += profitability_score
        details.append(f'Profitability: {profitability_score}/30 points')
        
        # Financial Stability (max 30 points)
        max_score += 30
        stability_score = 0
        debt_to_equity = metrics.get('debt_to_equity')
        if debt_to_equity is not None:
            if debt_to_equity < 50:
                stability_score += 15
            elif debt_to_equity < 100:
                stability_score += 10
            else:
                stability_score += 5
        
        current_ratio = metrics.get('current_ratio')
        if current_ratio:
            if current_ratio > 1.5:
                stability_score += 15
            elif current_ratio > 1:
                stability_score += 10
            else:
                stability_score += 5
        score += stability_score
        details.append(f'Financial Stability: {stability_score}/30 points')
        
        # Growth (max 20 points)
        max_score += 20
        growth_score = 0
        if metrics.get('revenue_growth') and metrics['revenue_growth'] > 10:
            growth_score += 10
        if metrics.get('earnings_growth') and metrics['earnings_growth'] > 10:
            growth_score += 10
        score += growth_score
        details.append(f'Growth: {growth_score}/20 points')
        
        # Valuation (max 20 points)
        max_score += 20
        valuation_score = 0
        pe = metrics.get('pe_ratio')
        if pe and pe < 20:
            valuation_score += 10
        pb = metrics.get('pb_ratio')
        if pb and pb < 3:
            valuation_score += 10
        score += valuation_score
        details.append(f'Valuation: {valuation_score}/20 points')
        
        # Calculate percentage
        health_percentage = (score / max_score) * 100 if max_score > 0 else 0
        
        # Determine health status
        if health_percentage >= 80:
            status = 'Excellent'
            recommendation = 'Strong financial position - Low risk investment'
        elif health_percentage >= 60:
            status = 'Good'
            recommendation = 'Healthy financials - Moderate risk'
        elif health_percentage >= 40:
            status = 'Average'
            recommendation = 'Mixed financials - Monitor closely'
        elif health_percentage >= 20:
            status = 'Weak'
            recommendation = 'Financial concerns - Higher risk'
        else:
            status = 'Poor'
            recommendation = 'Significant financial issues - High risk'
        
        return {
            'health_score': round(score, 1),
            'max_score': max_score,
            'health_percentage': round(health_percentage, 1),
            'status': status,
            'recommendation': recommendation,
            'details': details,
            'raw_metrics': metrics
        }
    
    def get_business_summary(self) -> Dict[str, str]:
        """Get business summary and key information"""
        return {
            'company_name': self.info.get('longName', 'N/A'),
            'sector': self.info.get('sector', 'N/A'),
            'industry': self.info.get('industry', 'N/A'),
            'description': self.info.get('longBusinessSummary', 'No description available')[:500] + '...',
            'employees': self.info.get('fullTimeEmployees', 'N/A'),
            'country': self.info.get('country', 'N/A'),
            'website': self.info.get('website', 'N/A'),
            'market_cap': self._format_market_cap(self.info.get('marketCap')),
            'enterprise_value': self._format_market_cap(self.info.get('enterpriseValue'))
        }
    
    def _format_market_cap(self, value: Optional[int]) -> str:
        """Format market cap in readable format"""
        if not value:
            return 'N/A'
        
        if value >= 1e12:
            return f"₹{value/1e12:.2f}T"
        elif value >= 1e9:
            return f"₹{value/1e9:.2f}B"
        elif value >= 1e6:
            return f"₹{value/1e6:.2f}M"
        else:
            return f"₹{value:,.0f}"
    
    def get_peer_comparison(self) -> Dict[str, Any]:
        """
        Compare with sector peers (simplified version)
        
        Returns:
            Comparison metrics
        """
        sector = self.info.get('sector')
        industry = self.info.get('industry')
        
        metrics = self.get_fundamental_metrics()
        
        return {
            'company': self.info.get('longName'),
            'sector': sector,
            'industry': industry,
            'peer_metrics': {
                'pe_ratio': metrics.get('pe_ratio'),
                'pb_ratio': metrics.get('pb_ratio'),
                'roe': metrics.get('roe'),
                'debt_to_equity': metrics.get('debt_to_equity')
            },
            'note': 'Peer comparison requires sector data from external API'
        }
    
    def get_complete_fundamental_analysis(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get complete fundamental analysis
        Includes intelligent caching for improved performance.
        
        Args:
            use_cache: Whether to use cache (default True)
        
        Returns:
            Comprehensive fundamental analysis
        """
        # Check cache first
        cache_instance = _get_cache()
        if use_cache and cache_instance:
            cached_result = cache_instance.get_fundamental(self.symbol)
            if cached_result:
                print(f"[FUNDAMENTAL CACHE] Cache hit for {self.symbol}")
                cached_result['_cached'] = True
                cached_result['_cached_at'] = datetime.now().isoformat()
                return cached_result
        
        metrics = self.get_fundamental_metrics()
        valuation = self.get_valuation_assessment(metrics)
        health = self.get_financial_health_score()
        summary = self.get_business_summary()
        
        result = {
            'symbol': self.symbol,
            'company_info': summary,
            'metrics': metrics,
            'valuation_assessment': valuation,
            'financial_health': health,
            'analysis_timestamp': datetime.now().isoformat(),
            '_cached': False
        }
        
        # Cache the result
        cache_instance = _get_cache()
        if use_cache and cache_instance:
            cache_instance.set_fundamental(self.symbol, result)
            print(f"[FUNDAMENTAL CACHE] Cached result for {self.symbol}")
        
        return result
