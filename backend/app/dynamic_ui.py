"""
Quant Terminal v2 - Dynamic UI Engine
Personalized Alpha Frontend with real-time adaptive UI

Features:
1. Context-Aware Theming (Professional Dark, War Room, High Alert modes)
2. Personalized Market Narrative based on user profile
3. Real-time shadow market correlation display
4. Dynamic indicator visibility
5. Alert management
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# Import shadow market types
from app.shadow_market import GlobalDriver

class DynamicUIEngine:
    """
    Generates personalized UI configurations based on:
    - Market regime (Bull/Bear/Volatile)
    - User profile (Value Investor, Scalper, etc.)
    - Portfolio risk state
    - Shadow market correlations
    """
    
    THEMES = {
        'professional_dark': {
            'name': 'Professional',
            'description': 'Standard trading terminal aesthetic',
            'css_variables': {
                '--bg-primary': '#0a0e1a',
                '--bg-secondary': '#111827',
                '--bg-card': 'rgba(17, 24, 39, 0.7)',
                '--accent-primary': '#00d4ff',
                '--accent-secondary': '#7b2cbf',
                '--text-primary': '#ffffff',
                '--text-secondary': 'rgba(255, 255, 255, 0.7)',
                '--border-color': 'rgba(0, 212, 255, 0.2)',
                '--glow-color': 'rgba(0, 212, 255, 0.4)',
                '--alert-banner-bg': 'rgba(0, 212, 255, 0.1)',
                '--alert-banner-border': 'rgba(0, 212, 255, 0.4)',
            },
            'animation': 'none'
        },
        'war_room': {
            'name': 'War Room',
            'description': 'Critical alerts - high volatility mode',
            'css_variables': {
                '--bg-primary': '#1a0505',
                '--bg-secondary': '#2d0a0a',
                '--bg-card': 'rgba(45, 10, 10, 0.85)',
                '--accent-primary': '#ff2d2d',
                '--accent-secondary': '#ff6b35',
                '--text-primary': '#ffffff',
                '--text-secondary': 'rgba(255, 200, 200, 0.8)',
                '--border-color': 'rgba(255, 45, 45, 0.5)',
                '--glow-color': 'rgba(255, 45, 45, 0.6)',
                '--alert-banner-bg': 'rgba(255, 45, 45, 0.2)',
                '--alert-banner-border': 'rgba(255, 45, 45, 0.8)',
            },
            'animation': 'pulse-red'
        },
        'high_alert': {
            'name': 'High Alert',
            'description': 'Warning mode - elevated volatility',
            'css_variables': {
                '--bg-primary': '#1a1205',
                '--bg-secondary': '#2d1f0a',
                '--bg-card': 'rgba(45, 31, 10, 0.8)',
                '--accent-primary': '#ff9500',
                '--accent-secondary': '#ffb84d',
                '--text-primary': '#ffffff',
                '--text-secondary': 'rgba(255, 220, 180, 0.8)',
                '--border-color': 'rgba(255, 149, 0, 0.4)',
                '--glow-color': 'rgba(255, 149, 0, 0.5)',
                '--alert-banner-bg': 'rgba(255, 149, 0, 0.15)',
                '--alert-banner-border': 'rgba(255, 149, 0, 0.6)',
            },
            'animation': 'pulse-orange'
        },
        'zen_mode': {
            'name': 'Zen',
            'description': 'Calm mode - low volatility',
            'css_variables': {
                '--bg-primary': '#0a1a15',
                '--bg-secondary': '#0f2d1f',
                '--bg-card': 'rgba(15, 45, 31, 0.7)',
                '--accent-primary': '#00ff9d',
                '--accent-secondary': '#00b36b',
                '--text-primary': '#ffffff',
                '--text-secondary': 'rgba(200, 255, 230, 0.8)',
                '--border-color': 'rgba(0, 255, 157, 0.3)',
                '--glow-color': 'rgba(0, 255, 157, 0.3)',
                '--alert-banner-bg': 'rgba(0, 255, 157, 0.1)',
                '--alert-banner-border': 'rgba(0, 255, 157, 0.4)',
            },
            'animation': 'breathe'
        },
        'caution': {
            'name': 'Caution',
            'description': 'Bearish conditions detected',
            'css_variables': {
                '--bg-primary': '#151520',
                '--bg-secondary': '#1f1f2e',
                '--bg-card': 'rgba(31, 31, 46, 0.8)',
                '--accent-primary': '#ffd700',
                '--accent-secondary': '#b8860b',
                '--text-primary': '#ffffff',
                '--text-secondary': 'rgba(255, 255, 200, 0.8)',
                '--border-color': 'rgba(255, 215, 0, 0.3)',
                '--glow-color': 'rgba(255, 215, 0, 0.4)',
                '--alert-banner-bg': 'rgba(255, 215, 0, 0.1)',
                '--alert-banner-border': 'rgba(255, 215, 0, 0.5)',
            },
            'animation': 'slow-pulse'
        }
    }
    
    # Market narrative templates by user type
    NARRATIVE_TEMPLATES = {
        'value_investor': {
            'metrics': ['pe_ratio', 'dividend_yield', 'book_value', 'roe'],
            'alerts': ['dividend_announcement', 'earnings_beat', 'valuation_opportunity'],
            'narrative_style': 'fundamental',
            'time_horizon': 'long_term',
            'preferred_indicators': ['rsi', 'macd', 'volume']
        },
        'intraday_scalper': {
            'metrics': ['vwap', 'volume_spike', 'order_flow', 'price_momentum'],
            'alerts': ['vwap_crossover', 'volume_breakout', 'support_resistance_test'],
            'narrative_style': 'technical',
            'time_horizon': 'intraday',
            'preferred_indicators': ['vwap', 'rsi', 'volume', 'order_book']
        },
        'swing_trader': {
            'metrics': ['trend_strength', 'support_resistance', 'volume_profile', 'sector_momentum'],
            'alerts': ['trend_break', 'volume_confirmation', 'sector_rotation'],
            'narrative_style': 'techno_fundamental',
            'time_horizon': 'swing',
            'preferred_indicators': ['rsi', 'macd', 'atr', 'bollinger', 'ema']
        },
        'momentum_trader': {
            'metrics': ['price_momentum', 'relative_strength', 'volume_acceleration', 'breakout_level'],
            'alerts': ['new_high', 'volume_surge', 'momentum_divergence'],
            'narrative_style': 'momentum',
            'time_horizon': 'short_term',
            'preferred_indicators': ['rsi', 'macd', 'volume', 'stochastic']
        },
        'dividend_investor': {
            'metrics': ['dividend_yield', 'payout_ratio', 'dividend_growth', 'ex_div_date'],
            'alerts': ['dividend_declaration', 'ex_div_reminder', 'yield_opportunity'],
            'narrative_style': 'income',
            'time_horizon': 'long_term',
            'preferred_indicators': ['rsi', 'volume']
        }
    }
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.current_theme = 'professional_dark'
        self.visible_indicators = []
        self.alert_banner = None
        self.market_narrative = []
        
    def generate_ui_config(
        self, 
        market_regime: str,
        user_profile: Dict[str, Any],
        portfolio_alerts: List[Dict],
        shadow_analysis: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate complete UI configuration based on all inputs.
        """
        # Determine theme
        theme = self._select_theme(market_regime, portfolio_alerts)
        
        # Get user type configuration
        user_type = user_profile.get('trading_style', 'swing_trader')
        user_config = self.NARRATIVE_TEMPLATES.get(user_type, self.NARRATIVE_TEMPLATES['swing_trader'])
        
        # Determine visible indicators based on regime + user preference
        indicators = self._select_indicators(market_regime, user_config)
        
        # Generate alert banner if needed
        banner = self._generate_alert_banner(market_regime, portfolio_alerts, shadow_analysis)
        
        # Generate market narrative
        narrative = self._generate_market_narrative(user_config, shadow_analysis)
        
        # Calculate refresh interval
        refresh_interval = self._calculate_refresh_interval(market_regime)
        
        # Generate CSS to inject
        css = self._generate_theme_css(theme)
        
        return {
            'theme': {
                'name': theme,
                'display_name': self.THEMES[theme]['name'],
                'description': self.THEMES[theme]['description'],
                'css': css,
                'animation': self.THEMES[theme]['animation']
            },
            'indicators': {
                'visible': indicators,
                'hidden': list(set(['rsi', 'macd', 'atr', 'ema', 'volume', 'bollinger', 
                                   'stochastic', 'vwap', 'order_book', 'support_resistance']) - set(indicators))
            },
            'alert_banner': banner,
            'market_narrative': narrative,
            'refresh_interval': refresh_interval,
            'recommendation_mode': self._get_recommendation_mode(market_regime),
            'signal_strength': self._get_signal_strength(market_regime),
            'show_risk_meter': True,
            'show_shadow_market': shadow_analysis is not None,
            'show_portfolio_correlation': True if shadow_analysis else False
        }
    
    def _select_theme(self, regime: str, alerts: List[Dict]) -> str:
        """Select theme based on market regime and alerts"""
        # Check for critical alerts
        critical_alerts = [a for a in alerts if a.get('severity') in ['critical', 'red_alert']]
        
        if critical_alerts or regime == 'crisis':
            return 'war_room'
        elif regime == 'high_volatility':
            return 'high_alert'
        elif regime == 'bull':
            return 'professional_dark'
        elif regime == 'bear':
            return 'caution'
        elif regime == 'sideways':
            return 'zen_mode'
        else:
            return 'professional_dark'
    
    def _select_indicators(self, regime: str, user_config: Dict) -> List[str]:
        """Select which indicators to show based on regime and user preference"""
        base_indicators = user_config.get('preferred_indicators', ['rsi', 'macd', 'atr'])
        
        # Modify based on regime
        if regime == 'high_volatility' or regime == 'crisis':
            # Add volatility indicators
            if 'atr' not in base_indicators:
                base_indicators.append('atr')
            if 'bollinger' not in base_indicators:
                base_indicators.append('bollinger')
        
        if regime == 'sideways':
            # Add range-bound indicators
            if 'bollinger' not in base_indicators:
                base_indicators.append('bollinger')
            if 'rsi' not in base_indicators:
                base_indicators.append('rsi')
        
        # Limit to 6 indicators max
        return base_indicators[:6]
    
    def _generate_alert_banner(
        self, 
        regime: str, 
        alerts: List[Dict],
        shadow_analysis: Optional[Dict]
    ) -> Optional[Dict]:
        """Generate alert banner content"""
        # Priority: Critical portfolio alerts > Shadow market alerts > Regime alerts
        
        # Check portfolio alerts
        critical_portfolio = [a for a in alerts if a.get('severity') == 'critical']
        if critical_portfolio:
            alert = critical_portfolio[0]
            return {
                'type': 'critical',
                'title': '🚨 CRITICAL ALERT',
                'message': alert.get('message', 'Portfolio at risk. Immediate action required.'),
                'action_text': 'View Details',
                'action_link': '#alerts'
            }
        
        # Check shadow market alerts
        if shadow_analysis:
            shadow_alerts = shadow_analysis.get('active_shadow_alerts', [])
            red_alerts = [a for a in shadow_alerts if a.get('severity') == 'red_alert']
            if red_alerts:
                alert = red_alerts[0]
                return {
                    'type': 'red_alert',
                    'title': '⚠️ SHADOW MARKET ALERT',
                    'message': f"{alert.get('driver', 'Global driver')} spike detected. {alert.get('expected_impact', '')}",
                    'action_text': 'View Correlation',
                    'action_link': '#shadow-market'
                }
        
        # Regime-based banners
        if regime == 'high_volatility':
            return {
                'type': 'warning',
                'title': 'High Volatility Mode',
                'message': 'VIX elevated. Risk management prioritized. Position sizing reduced.',
                'action_text': 'Check Risk',
                'action_link': '#risk'
            }
        elif regime == 'bear':
            return {
                'type': 'caution',
                'title': 'Bearish Conditions',
                'message': 'Downtrend detected. Consider cash preservation.',
                'action_text': 'Review Strategy',
                'action_link': '#strategy'
            }
        elif regime == 'bull':
            return {
                'type': 'info',
                'title': 'Bull Market Active',
                'message': 'Trend favorable. Manage risk appropriately.',
                'action_text': 'View Opportunities',
                'action_link': '#opportunities'
            }
        
        return None
    
    def _generate_market_narrative(
        self, 
        user_config: Dict,
        shadow_analysis: Optional[Dict]
    ) -> List[Dict]:
        """Generate personalized market narrative lines"""
        narrative = []
        style = user_config.get('narrative_style', 'technical')
        
        # Time-based greeting
        hour = datetime.now().hour
        if 9 <= hour < 12:
            greeting = "Pre-market analysis:"
        elif 12 <= hour < 15:
            greeting = "Mid-session update:"
        else:
            greeting = "Market close summary:"
        
        narrative.append({
            'type': 'header',
            'content': greeting,
            'priority': 'normal'
        })
        
        # Add shadow market insights if available
        if shadow_analysis:
            exposures = shadow_analysis.get('portfolio_exposures', [])
            if exposures:
                top_exposure = max(exposures, key=lambda x: abs(x.get('correlation', 0)))
                driver = top_exposure.get('driver', '').upper()
                symbol = top_exposure.get('symbol', '').replace('.NS', '')
                corr = top_exposure.get('correlation', 0)
                
                narrative.append({
                    'type': 'shadow_insight',
                    'content': f"📊 Hidden Exposure: Your {symbol} position is {abs(corr):.0%} correlated with {driver}",
                    'priority': 'high' if abs(corr) > 0.7 else 'normal',
                    'data': top_exposure
                })
            
            # Shadow alerts
            alerts = shadow_analysis.get('active_shadow_alerts', [])
            for alert in alerts[:2]:  # Top 2 alerts
                narrative.append({
                    'type': 'shadow_alert',
                    'content': f"🔮 {alert.get('trigger', 'Macro alert')}. ETA: {alert.get('eta_to_impact', 'unknown')}",
                    'priority': 'critical' if alert.get('severity') == 'critical' else 'high',
                    'data': alert
                })
        
        # Add personalized metrics based on user type
        metrics = user_config.get('metrics', [])
        for metric in metrics[:3]:
            if metric == 'pe_ratio':
                narrative.append({
                    'type': 'metric',
                    'content': "Value Opportunity: NIFTY PE at 22.4 (historical avg: 20)",
                    'priority': 'normal'
                })
            elif metric == 'dividend_yield':
                narrative.append({
                    'type': 'metric',
                    'content': "Income Alert: 12 NIFTY stocks with >3% yield",
                    'priority': 'normal'
                })
            elif metric == 'vwap':
                narrative.append({
                    'type': 'metric',
                    'content': "VWAP Signal: NIFTY trading above VWAP (bullish bias)",
                    'priority': 'normal'
                })
            elif metric == 'volume_spike':
                narrative.append({
                    'type': 'metric',
                    'content': "Volume Alert: Banking sector volume 1.4x average",
                    'priority': 'high'
                })
        
        return narrative
    
    def _calculate_refresh_interval(self, regime: str) -> int:
        """Calculate data refresh interval based on market volatility"""
        intervals = {
            'crisis': 10,  # 10 seconds in crisis
            'high_volatility': 20,  # 20 seconds in high vol
            'bull': 30,  # Normal 30 seconds
            'bear': 20,  # 20 seconds in bear
            'sideways': 45  # 45 seconds in calm markets
        }
        return intervals.get(regime, 30)
    
    def _get_recommendation_mode(self, regime: str) -> str:
        """Get recommendation mode based on regime"""
        modes = {
            'crisis': 'defensive',
            'high_volatility': 'defensive',
            'bull': 'balanced',
            'bear': 'defensive',
            'sideways': 'balanced'
        }
        return modes.get(regime, 'balanced')
    
    def _get_signal_strength(self, regime: str) -> str:
        """Get signal strength based on regime"""
        strengths = {
            'crisis': 'weak',
            'high_volatility': 'weak',
            'bull': 'strong',
            'bear': 'weak',
            'sideways': 'moderate'
        }
        return strengths.get(regime, 'moderate')
    
    def _generate_theme_css(self, theme_name: str) -> str:
        """Generate CSS string for the theme"""
        theme = self.THEMES.get(theme_name, self.THEMES['professional_dark'])
        
        css_lines = [':root {']
        for var, value in theme['css_variables'].items():
            css_lines.append(f'  {var}: {value};')
        css_lines.append('}')
        
        # Add animation keyframes if needed
        if theme['animation'] == 'pulse-red':
            css_lines.append('''
@keyframes pulse-red {
  0%, 100% { box-shadow: 0 0 20px rgba(255, 45, 45, 0.4); }
  50% { box-shadow: 0 0 40px rgba(255, 45, 45, 0.8); }
}
.alert-banner { animation: pulse-red 2s infinite; }
''')
        elif theme['animation'] == 'pulse-orange':
            css_lines.append('''
@keyframes pulse-orange {
  0%, 100% { box-shadow: 0 0 15px rgba(255, 149, 0, 0.3); }
  50% { box-shadow: 0 0 30px rgba(255, 149, 0, 0.6); }
}
.alert-banner { animation: pulse-orange 3s infinite; }
''')
        elif theme['animation'] == 'breathe':
            css_lines.append('''
@keyframes breathe {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}
.market-status { animation: breathe 4s infinite; }
''')
        
        return '\n'.join(css_lines)
    
    def generate_shadow_market_visualization(self, shadow_analysis: Dict) -> Dict:
        """Generate data for shadow market correlation visualization"""
        if not shadow_analysis:
            return {'enabled': False}
        
        exposures = shadow_analysis.get('portfolio_exposures', [])
        macro_states = shadow_analysis.get('macro_states', {})
        
        # Create correlation web data
        nodes = []
        links = []
        
        # Add portfolio center node
        nodes.append({
            'id': 'portfolio',
            'name': 'Your Portfolio',
            'type': 'center',
            'size': 40
        })
        
        # Add driver nodes
        for driver in GlobalDriver:
            driver_key = driver.value
            if driver_key in macro_states:
                state = macro_states[driver_key]
                trend = state.get('trend', 'stable')
                
                nodes.append({
                    'id': driver_key,
                    'name': driver.value.upper(),
                    'type': 'driver',
                    'size': 25,
                    'value': state.get('current_value', 0),
                    'change': state.get('change_1h_pct', 0),
                    'trend': trend
                })
                
                # Add link to portfolio
                total_correlation = sum(
                    abs(e.get('correlation', 0)) 
                    for e in exposures 
                    if e.get('driver') == driver_key
                )
                
                if total_correlation > 0:
                    links.append({
                        'source': driver_key,
                        'target': 'portfolio',
                        'strength': min(total_correlation / 2, 1),
                        'type': 'macro_to_portfolio'
                    })
        
        # Add stock nodes
        seen_stocks = set()
        for exposure in exposures[:10]:  # Top 10 correlations
            symbol = exposure.get('symbol')
            driver = exposure.get('driver')
            correlation = exposure.get('correlation', 0)
            
            if symbol not in seen_stocks:
                seen_stocks.add(symbol)
                nodes.append({
                    'id': symbol,
                    'name': symbol.replace('.NS', ''),
                    'type': 'stock',
                    'size': 20
                })
            
            # Link driver to stock
            links.append({
                'source': driver,
                'target': symbol,
                'strength': abs(correlation),
                'correlation': correlation,
                'type': 'driver_to_stock'
            })
        
        return {
            'enabled': True,
            'nodes': nodes,
            'links': links,
            'shadow_beta': shadow_analysis.get('shadow_beta', 1.0),
            'diversification_score': shadow_analysis.get('diversification_score', 0),
            'invisible_strings': shadow_analysis.get('invisible_strings', [])
        }


# Global engine instance
_ui_engine: Optional[DynamicUIEngine] = None


def get_ui_engine(user_id: Optional[str] = None) -> DynamicUIEngine:
    """Get or create UI engine instance"""
    global _ui_engine
    if _ui_engine is None:
        _ui_engine = DynamicUIEngine(user_id)
    return _ui_engine
