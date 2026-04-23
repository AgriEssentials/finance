"""
Quant Terminal v2 - Dynamic Logic Controller (The Agent Brain)
An async orchestrator that monitors user portfolios and market conditions to dynamically adapt the system.

This module implements:
1. Market Regime Detection (Bull/Bear/Sideways)
2. Portfolio Risk Monitoring
3. Dynamic Model Switching
4. Context-Aware UI Configuration
5. Alert Generation
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import yfinance as yf
import numpy as np

# Import sentiment analyzer for news processing
from app.sentiment import sentiment_analyzer


class MarketRegime(Enum):
    """Market regime classification"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    CRISIS = "crisis"


class RiskLevel(Enum):
    """Portfolio risk levels"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    DANGER = "danger"


@dataclass
class PortfolioAlert:
    """Alert structure for portfolio events"""
    id: str
    type: str  # price_drop, volatility_spike, sector_risk, etc.
    severity: str  # info, warning, danger, critical
    symbol: Optional[str]
    message: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False


@dataclass
class MarketContext:
    """Real-time market context"""
    vix: float  # India VIX
    nifty_change_pct: float
    market_regime: MarketRegime
    volatility_level: str  # low, normal, high, extreme
    breadth: Dict[str, Any]  # Advance-decline ratio, etc.
    timestamp: datetime


@dataclass
class UIConfiguration:
    """Dynamic UI configuration based on market state"""
    theme: str  # professional_dark, war_room, zen_mode
    visible_indicators: List[str]
    signal_strength: str  # strong, moderate, weak
    alert_banner: Optional[Dict[str, str]]
    recommendation_mode: str  # aggressive, balanced, defensive
    auto_refresh_interval: int  # seconds
    show_portfolio_risk_meter: bool


class AgentBrain:
    """
    The central orchestrator for Quant Terminal v2.
    
    Monitors:
    - User portfolio for risk events
    - Market volatility (VIX)
    - NSE corporate announcements
    - News sentiment shifts
    
    Adapts:
    - ML model aggressiveness
    - UI theme and indicators
    - Risk guardrails
    - Alert priorities
    """
    
    # High-beta stocks that trigger extra scrutiny
    HIGH_BETA_STOCKS = {
        'ADANIENT.NS', 'ADANIPORTS.NS', 'ADANIGREEN.NS', 'ADANITRANS.NS',
        'SBIN.NS', 'PNB.NS', 'BANKBARODA.NS', 'CANBK.NS', 'UNIONBANK.NS',
        'IOC.NS', 'BPCL.NS', 'HPCL.NS', 'ONGC.NS', 'GAIL.NS',
        'TATAMOTORS.NS', 'M&M.NS', 'EICHERMOT.NS', 'BAJAJAUTO.NS',
        'JSWSTEEL.NS', 'TATASTEEL.NS', 'HINDALCO.NS', 'VEDL.NS'
    }
    
    # Defensive stocks for portfolio balancing
    DEFENSIVE_STOCKS = {
        'ITC.NS', 'TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'WIPRO.NS',
        'HINDUNILVR.NS', 'NESTLEIND.NS', 'BRITANNIA.NS', 'DABUR.NS',
        'SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS'
    }
    
    # Sector betas for calculation
    SECTOR_BETAS = {
        'NIFTY BANK': 1.25,
        'NIFTY IT': 0.85,
        'NIFTY FMCG': 0.70,
        'NIFTY PHARMA': 0.75,
        'NIFTY AUTO': 1.15,
        'NIFTY METAL': 1.35,
        'NIFTY OIL & GAS': 1.10,
        'NIFTY PSU BANK': 1.40,
    }
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.current_regime = MarketRegime.SIDEWAYS
        self.market_context: Optional[MarketContext] = None
        self.alerts: List[PortfolioAlert] = []
        self.ui_config: UIConfiguration = self._get_default_ui_config()
        self.last_update = datetime.now()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
    def _get_default_ui_config(self) -> UIConfiguration:
        """Get default UI configuration"""
        return UIConfiguration(
            theme="professional_dark",
            visible_indicators=[
                "rsi", "macd", "atr", "ema", "volume", "bollinger"
            ],
            signal_strength="moderate",
            alert_banner=None,
            recommendation_mode="balanced",
            auto_refresh_interval=30,
            show_portfolio_risk_meter=True
        )
    
    async def start_monitoring(self):
        """Start the async monitoring loop"""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        print(f"[AGENT BRAIN] Started monitoring for user {self.user_id}")
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        print(f"[AGENT BRAIN] Stopped monitoring for user {self.user_id}")
    
    async def _monitor_loop(self):
        """Main monitoring loop - runs every 30 seconds"""
        while self._running:
            try:
                # Update market context
                await self._update_market_context()
                
                # If user is logged in, check portfolio
                if self.user_id:
                    await self._check_portfolio_alerts()
                    await self._update_risk_guardrails()
                
                # Update UI configuration based on state
                self._adapt_ui_configuration()
                
                self.last_update = datetime.now()
                
            except Exception as e:
                print(f"[AGENT BRAIN] Error in monitor loop: {e}")
            
            await asyncio.sleep(30)  # 30-second monitoring interval
    
    async def _update_market_context(self):
        """Fetch and update market context"""
        try:
            # Get India VIX
            vix_ticker = yf.Ticker("^INDIAVIX")
            vix_hist = vix_ticker.history(period="2d")
            vix = float(vix_hist['Close'].iloc[-1]) if not vix_hist.empty else 15.0
            
            # Get NIFTY change
            nifty_ticker = yf.Ticker("^NSEI")
            nifty_hist = nifty_ticker.history(period="2d")
            if len(nifty_hist) >= 2:
                nifty_change = ((nifty_hist['Close'].iloc[-1] / nifty_hist['Close'].iloc[-2]) - 1) * 100
            else:
                nifty_change = 0.0
            
            # Determine market regime
            regime = self._detect_market_regime(vix, nifty_change)
            
            # Determine volatility level
            if vix > 30:
                vol_level = "extreme"
            elif vix > 22:
                vol_level = "high"
            elif vix > 15:
                vol_level = "normal"
            else:
                vol_level = "low"
            
            # Calculate market breadth (simplified)
            breadth = {
                "advance_decline_ratio": 1.0,  # Placeholder
                "new_highs_lows_ratio": 1.0,   # Placeholder
                "volume_trend": "neutral"
            }
            
            self.market_context = MarketContext(
                vix=vix,
                nifty_change_pct=nifty_change,
                market_regime=regime,
                volatility_level=vol_level,
                breadth=breadth,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"[AGENT BRAIN] Error updating market context: {e}")
    
    def _detect_market_regime(self, vix: float, nifty_change: float) -> MarketRegime:
        """
        Detect current market regime with HYSTERESIS to prevent flip-flopping.
        
        Regime changes are sticky - requires sustained conditions to switch.
        This prevents the "disco" effect of constant theme switching.
        """
        now = datetime.now()
        
        # Initialize regime history if not present
        if not hasattr(self, '_regime_history'):
            self._regime_history = []
            self._last_regime_change = now
            self._stable_regime = MarketRegime.SIDEWAYS
        
        # Calculate raw regime based on current conditions
        if vix > 25 or nifty_change < -3:
            raw_regime = MarketRegime.CRISIS
        elif vix > 20:
            raw_regime = MarketRegime.HIGH_VOLATILITY
        elif nifty_change > 1.5:
            raw_regime = MarketRegime.BULL
        elif nifty_change < -1.5:
            raw_regime = MarketRegime.BEAR
        else:
            raw_regime = MarketRegime.SIDEWAYS
        
        # Add to history (keep last 10 readings)
        self._regime_history.append({
            'regime': raw_regime,
            'timestamp': now,
            'vix': vix,
            'nifty_change': nifty_change
        })
        self._regime_history = self._regime_history[-10:]
        
        # HYSTERESIS: Only change regime if sustained for multiple readings
        # or if in crisis (immediate)
        if raw_regime == MarketRegime.CRISIS:
            # Crisis is immediate - no delay
            if self._stable_regime != MarketRegime.CRISIS:
                print(f"[AGENT BRAIN] Regime change (IMMEDIATE): {self._stable_regime.value} → CRISIS (VIX: {vix:.1f})")
                self._stable_regime = MarketRegime.CRISIS
                self._last_regime_change = now
            return self._stable_regime
        
        # For other regimes, require 3 out of last 5 readings to match
        recent_regimes = [h['regime'] for h in self._regime_history[-5:]]
        regime_counts = {}
        for r in recent_regimes:
            regime_counts[r] = regime_counts.get(r, 0) + 1
        
        # Find majority regime (needs 3+ occurrences)
        majority_regime = None
        max_count = 0
        for regime, count in regime_counts.items():
            if count > max_count and count >= 3:
                majority_regime = regime
                max_count = count
        
        # Also require minimum time between changes (3 minutes)
        time_since_change = (now - self._last_regime_change).total_seconds()
        MIN_CHANGE_INTERVAL = 180  # 3 minutes
        
        if majority_regime and majority_regime != self._stable_regime:
            if time_since_change >= MIN_CHANGE_INTERVAL:
                print(f"[AGENT BRAIN] Regime change (CONFIRMED): {self._stable_regime.value} → {majority_regime.value} (after {time_since_change:.0f}s)")
                self._stable_regime = majority_regime
                self._last_regime_change = now
            else:
                print(f"[AGENT BRAIN] Regime change pending: {majority_regime.value} (wait {MIN_CHANGE_INTERVAL - time_since_change:.0f}s)")
        
        return self._stable_regime
    
    async def _check_portfolio_alerts(self):
        """Check portfolio for alert conditions"""
        from app.supabase_portfolio import get_user_portfolio_manager
        
        try:
            portfolio_manager = get_user_portfolio_manager(self.user_id)
            summary = portfolio_manager.get_portfolio_summary()
            
            positions = summary.get('positions', [])
            
            for position in positions:
                symbol = position.get('symbol', '')
                current_price = position.get('current_price', 0)
                avg_cost = position.get('avg_cost', 0)
                
                if not symbol or current_price == 0:
                    continue
                
                # Check for significant price drop (>3% in position)
                pnl_pct = position.get('unrealized_pnl_percent', 0)
                
                if pnl_pct < -3:
                    # Check if we already have an alert for this
                    existing = [a for a in self.alerts 
                               if a.symbol == symbol and a.type == 'price_drop' 
                               and not a.acknowledged
                               and (datetime.now() - a.timestamp).seconds < 3600]
                    
                    if not existing:
                        alert = PortfolioAlert(
                            id=f"drop_{symbol}_{int(datetime.now().timestamp())}",
                            type="price_drop",
                            severity="danger" if pnl_pct < -5 else "warning",
                            symbol=symbol,
                            message=f"{symbol.replace('.NS', '')} down {abs(pnl_pct):.1f}% from your buy price",
                            timestamp=datetime.now(),
                            data={
                                "pnl_pct": pnl_pct,
                                "current_price": current_price,
                                "avg_cost": avg_cost,
                                "position_size": position.get('market_value', 0)
                            }
                        )
                        self.alerts.append(alert)
                        print(f"[AGENT BRAIN] ALERT: {alert.message}")
                
                # Check for volatility spike (simplified - would need intraday data)
                # This would be enhanced with WebSocket data
                
        except Exception as e:
            print(f"[AGENT BRAIN] Error checking portfolio alerts: {e}")
    
    async def _update_risk_guardrails(self):
        """Update risk guardrails based on portfolio composition"""
        from app.supabase_portfolio import get_user_portfolio_manager
        
        try:
            portfolio_manager = get_user_portfolio_manager(self.user_id)
            summary = portfolio_manager.get_portfolio_summary()
            
            positions = summary.get('positions', [])
            
            # Calculate portfolio beta
            portfolio_beta = self._calculate_portfolio_beta(positions)
            
            # Check for concentration risk
            total_value = summary.get('total_value', 0)
            max_position_weight = 0
            
            for pos in positions:
                weight = pos.get('market_value', 0) / total_value if total_value > 0 else 0
                if weight > max_position_weight:
                    max_position_weight = weight
            
            # Generate risk alerts
            if portfolio_beta > 1.3:
                existing = [a for a in self.alerts 
                           if a.type == 'high_beta_warning' and not a.acknowledged]
                if not existing:
                    alert = PortfolioAlert(
                        id=f"beta_{int(datetime.now().timestamp())}",
                        type="high_beta_warning",
                        severity="warning",
                        symbol=None,
                        message=f"Your portfolio beta ({portfolio_beta:.2f}) is high. Consider adding defensive stocks.",
                        timestamp=datetime.now(),
                        data={
                            "portfolio_beta": portfolio_beta,
                            "suggested_defensives": list(self.DEFENSIVE_STOCKS)[:5]
                        }
                    )
                    self.alerts.append(alert)
            
            if max_position_weight > 0.25:
                existing = [a for a in self.alerts 
                           if a.type == 'concentration_risk' and not a.acknowledged]
                if not existing:
                    alert = PortfolioAlert(
                        id=f"concentration_{int(datetime.now().timestamp())}",
                        type="concentration_risk",
                        severity="warning",
                        symbol=None,
                        message=f"One stock represents {max_position_weight*100:.0f}% of your portfolio. Consider diversifying.",
                        timestamp=datetime.now(),
                        data={
                            "max_weight": max_position_weight,
                            "position_count": len(positions)
                        }
                    )
                    self.alerts.append(alert)
            
        except Exception as e:
            print(f"[AGENT BRAIN] Error updating risk guardrails: {e}")
    
    def _calculate_portfolio_beta(self, positions: List[Dict]) -> float:
        """Calculate portfolio beta based on positions"""
        if not positions:
            return 1.0
        
        total_value = sum(pos.get('market_value', 0) for pos in positions)
        if total_value == 0:
            return 1.0
        
        weighted_beta = 0
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            value = pos.get('market_value', 0)
            weight = value / total_value
            
            # Assign beta based on stock category
            if symbol in self.HIGH_BETA_STOCKS:
                beta = 1.4
            elif symbol in self.DEFENSIVE_STOCKS:
                beta = 0.7
            else:
                beta = 1.0  # Market average
            
            weighted_beta += weight * beta
        
        return round(weighted_beta, 2)
    
    def _adapt_ui_configuration(self):
        """
        Adapt UI configuration based on market regime and portfolio state.
        
        WITH HYSTERESIS: UI config changes are sticky to prevent dashboard disco.
        Theme changes only occur with regime changes (which are already debounced).
        """
        if not self.market_context:
            return
        
        regime = self.market_context.market_regime
        vix = self.market_context.vix
        
        # Initialize previous config tracking
        if not hasattr(self, '_prev_ui_config'):
            self._prev_ui_config = None
            self._config_stable_since = datetime.now()
        
        # Determine theme based on conditions
        critical_alerts = [a for a in self.alerts 
                          if a.severity in ['danger', 'critical'] and not a.acknowledged]
        
        if critical_alerts or regime == MarketRegime.CRISIS:
            theme = "war_room"
            recommendation_mode = "defensive"
            signal_strength = "weak"
            visible_indicators = ["rsi", "atr", "volume", "support_resistance"]
            alert_banner = {
                "type": "critical",
                "title": "WAR ROOM MODE",
                "message": "High volatility detected. Risk management prioritized."
            }
        elif regime == MarketRegime.HIGH_VOLATILITY or vix > 20:
            theme = "high_alert"
            recommendation_mode = "defensive"
            signal_strength = "moderate"
            visible_indicators = ["rsi", "macd", "atr", "volume", "bollinger"]
            alert_banner = {
                "type": "warning",
                "title": "High Volatility Alert",
                "message": f"VIX at {vix:.1f}. Increased caution advised."
            }
        elif regime == MarketRegime.BULL:
            theme = "professional_dark"
            recommendation_mode = "aggressive" if vix < 18 else "balanced"
            signal_strength = "strong"
            visible_indicators = ["rsi", "macd", "atr", "ema", "volume", "bollinger", "stochastic"]
            alert_banner = {
                "type": "info",
                "title": "Bull Market",
                "message": "Trend is favorable. Manage risk appropriately."
            }
        elif regime == MarketRegime.BEAR:
            theme = "caution"
            recommendation_mode = "defensive"
            signal_strength = "weak"
            visible_indicators = ["rsi", "atr", "volume", "support_resistance"]
            alert_banner = {
                "type": "warning",
                "title": "Bearish Conditions",
                "message": "Downtrend detected. Consider cash preservation."
            }
        else:  # Sideways
            theme = "professional_dark"
            recommendation_mode = "balanced"
            signal_strength = "moderate"
            visible_indicators = ["rsi", "macd", "atr", "ema", "volume", "bollinger"]
            alert_banner = None
        
        # Adjust refresh interval based on volatility
        if vix > 25:
            refresh_interval = 10  # 10 seconds in high volatility
        elif vix > 20:
            refresh_interval = 20  # 20 seconds
        else:
            refresh_interval = 60  # STABILIZED: 60 seconds in calm markets (was 30)
        
        # Create new config
        new_config = UIConfiguration(
            theme=theme,
            visible_indicators=visible_indicators,
            signal_strength=signal_strength,
            alert_banner=alert_banner,
            recommendation_mode=recommendation_mode,
            auto_refresh_interval=refresh_interval,
            show_portfolio_risk_meter=True
        )
        
        # HYSTERESIS: Only update if significantly different or critical
        if self._prev_ui_config:
            # Check if theme changed
            theme_changed = self._prev_ui_config.theme != theme
            
            # Check if going TO/FROM critical state
            entering_critical = theme == "war_room" and self._prev_ui_config.theme != "war_room"
            leaving_critical = theme != "war_room" and self._prev_ui_config.theme == "war_room"
            
            # Allow change if entering/leaving critical, otherwise be sticky
            if not entering_critical and not leaving_critical:
                # Keep previous theme to prevent flicker
                if self._prev_ui_config.theme in ["war_room", "high_alert"]:
                    # Stay in alert mode longer (hysteresis)
                    new_config.theme = self._prev_ui_config.theme
                    new_config.alert_banner = self._prev_ui_config.alert_banner
        
        # Update previous config tracking
        if self._prev_ui_config is None or new_config.theme != self._prev_ui_config.theme:
            print(f"[AGENT BRAIN] UI config update: theme={new_config.theme}, regime={regime.value}")
        
        self._prev_ui_config = new_config
        self.ui_config = new_config
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get complete system state for frontend"""
        return {
            "market_context": {
                "vix": self.market_context.vix if self.market_context else 15.0,
                "nifty_change_pct": self.market_context.nifty_change_pct if self.market_context else 0.0,
                "regime": self.market_context.market_regime.value if self.market_context else "sideways",
                "volatility_level": self.market_context.volatility_level if self.market_context else "normal",
                "timestamp": self.market_context.timestamp.isoformat() if self.market_context else datetime.now().isoformat()
            },
            "ui_configuration": {
                "theme": self.ui_config.theme,
                "visible_indicators": self.ui_config.visible_indicators,
                "signal_strength": self.ui_config.signal_strength,
                "alert_banner": self.ui_config.alert_banner,
                "recommendation_mode": self.ui_config.recommendation_mode,
                "auto_refresh_interval": self.ui_config.auto_refresh_interval,
                "show_portfolio_risk_meter": self.ui_config.show_portfolio_risk_meter
            },
            "alerts": [
                {
                    "id": a.id,
                    "type": a.type,
                    "severity": a.severity,
                    "symbol": a.symbol,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat(),
                    "data": a.data,
                    "acknowledged": a.acknowledged
                }
                for a in self.alerts if not a.acknowledged
            ][-10:],  # Last 10 unacknowledged alerts
            "last_update": self.last_update.isoformat()
        }
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert by ID"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                print(f"[AGENT BRAIN] Alert {alert_id} acknowledged")
                return True
        return False
    
    def get_recommendation_constraints(self) -> Dict[str, Any]:
        """Get current recommendation constraints for the ML model"""
        constraints = {
            "allow_aggressive_signals": True,
            "allow_high_beta_purchases": True,
            "max_position_size_pct": 25,
            "min_confidence_threshold": 60,
            "risk_off_mode": False
        }
        
        if not self.market_context:
            return constraints
        
        regime = self.market_context.market_regime
        
        # Adjust constraints based on market regime
        if regime == MarketRegime.CRISIS:
            constraints["allow_aggressive_signals"] = False
            constraints["allow_high_beta_purchases"] = False
            constraints["max_position_size_pct"] = 10
            constraints["min_confidence_threshold"] = 75
            constraints["risk_off_mode"] = True
        elif regime == MarketRegime.HIGH_VOLATILITY:
            constraints["allow_aggressive_signals"] = False
            constraints["allow_high_beta_purchases"] = False
            constraints["max_position_size_pct"] = 15
            constraints["min_confidence_threshold"] = 70
        elif regime == MarketRegime.BEAR:
            constraints["allow_aggressive_signals"] = False
            constraints["max_position_size_pct"] = 20
            constraints["min_confidence_threshold"] = 65
        
        # Check portfolio beta constraint
        if self.user_id:
            from app.supabase_portfolio import get_user_portfolio_manager
            try:
                portfolio_manager = get_user_portfolio_manager(self.user_id)
                summary = portfolio_manager.get_portfolio_summary()
                positions = summary.get('positions', [])
                portfolio_beta = self._calculate_portfolio_beta(positions)
                
                if portfolio_beta > 1.3:
                    constraints["allow_high_beta_purchases"] = False
                    constraints["high_beta_restriction_reason"] = f"Portfolio beta ({portfolio_beta:.2f}) too high. Add defensive stocks first."
            except:
                pass
        
        return constraints


# Global agent brain instances (one per user)
_agent_brains: Dict[str, AgentBrain] = {}


def get_agent_brain(user_id: Optional[str] = None) -> AgentBrain:
    """Get or create an agent brain instance for a user"""
    if user_id not in _agent_brains:
        _agent_brains[user_id] = AgentBrain(user_id)
    return _agent_brains[user_id]


async def start_all_monitors():
    """Start monitoring for all active agent brains"""
    for user_id, brain in _agent_brains.items():
        await brain.start_monitoring()


async def stop_all_monitors():
    """Stop all monitoring"""
    for user_id, brain in _agent_brains.items():
        await brain.stop_monitoring()
