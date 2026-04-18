"""
Personalized Trading Assistant Module
Transforms generic stock analysis into user-specific trading decisions
Version 2.0 - Personal AI Trading Mentor
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from supabase import create_client, Client

# Load Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")


@dataclass
class UserProfile:
    """User profile for personalized trading"""
    id: str
    risk_tolerance: str  # low, medium, high
    capital: float
    preferred_strategy: str  # intraday, swing, long_term
    email: str
    created_at: datetime


@dataclass
class PortfolioPosition:
    """User's portfolio position"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    sector: Optional[str] = None


@dataclass
class TradeEntry:
    """Trade journal entry"""
    id: Optional[str]
    user_id: str
    symbol: str
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    trade_type: str  # buy/sell
    strategy: str
    reason: str
    emotion: Optional[str]
    pnl: Optional[float]
    entry_date: datetime
    exit_date: Optional[datetime]
    status: str  # open/closed


class SupabaseManager:
    """Manages Supabase database operations"""

    def __init__(self):
        self.client: Optional[Client] = None
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                print(f"[WARNING] Supabase connection failed: {e}")

    def is_connected(self) -> bool:
        return self.client is not None

    # User Profile Operations
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Fetch user profile from Supabase"""
        if not self.client:
            return None
        try:
            response = self.client.table("profiles").select("*").eq("id", user_id).execute()
            if response.data:
                data = response.data[0]
                return UserProfile(
                    id=data["id"],
                    risk_tolerance=data.get("risk_tolerance", "medium"),
                    capital=data.get("capital", 100000),
                    preferred_strategy=data.get("preferred_strategy", "swing"),
                    email=data.get("email", ""),
                    created_at=datetime.fromisoformat(data["created_at"])
                )
        except Exception as e:
            print(f"[ERROR] Failed to fetch profile: {e}")
        return None

    def create_user_profile(self, user_id: str, email: str, risk_tolerance: str = "medium",
                           capital: float = 100000, preferred_strategy: str = "swing") -> bool:
        """Create new user profile"""
        if not self.client:
            return False
        try:
            self.client.table("profiles").insert({
                "id": user_id,
                "email": email,
                "risk_tolerance": risk_tolerance,
                "capital": capital,
                "preferred_strategy": preferred_strategy
            }).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create profile: {e}")
            return False

    def update_user_profile(self, user_id: str, **kwargs) -> bool:
        """Update user profile"""
        if not self.client:
            return False
        try:
            self.client.table("profiles").update(kwargs).eq("id", user_id).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to update profile: {e}")
            return False

    # Portfolio Operations
    def get_portfolio(self, user_id: str) -> List[PortfolioPosition]:
        """Get user's portfolio"""
        if not self.client:
            return []
        try:
            response = self.client.table("portfolio").select("*").eq("user_id", user_id).execute()
            positions = []
            for data in response.data:
                positions.append(PortfolioPosition(
                    symbol=data["symbol"],
                    quantity=data["quantity"],
                    avg_price=data["avg_price"],
                    current_price=data.get("current_price", data["avg_price"]),
                    pnl=data.get("pnl", 0),
                    pnl_percent=data.get("pnl_percent", 0),
                    sector=data.get("sector")
                ))
            return positions
        except Exception as e:
            print(f"[ERROR] Failed to fetch portfolio: {e}")
            return []

    def add_position(self, user_id: str, symbol: str, quantity: int,
                     avg_price: float, sector: Optional[str] = None) -> bool:
        """Add or update position"""
        if not self.client:
            return False
        try:
            # Check if position exists
            existing = self.client.table("portfolio").select("*") \
                .eq("user_id", user_id).eq("symbol", symbol).execute()

            if existing.data:
                # Update existing position
                old_qty = existing.data[0]["quantity"]
                old_avg = existing.data[0]["avg_price"]
                new_qty = old_qty + quantity
                new_avg = (old_qty * old_avg + quantity * avg_price) / new_qty

                self.client.table("portfolio").update({
                    "quantity": new_qty,
                    "avg_price": new_avg,
                    "sector": sector
                }).eq("id", existing.data[0]["id"]).execute()
            else:
                # Create new position
                self.client.table("portfolio").insert({
                    "user_id": user_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "avg_price": avg_price,
                    "sector": sector
                }).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to add position: {e}")
            return False

    def close_position(self, user_id: str, symbol: str, exit_price: float) -> Optional[float]:
        """Close position and return P&L"""
        if not self.client:
            return None
        try:
            response = self.client.table("portfolio").select("*") \
                .eq("user_id", user_id).eq("symbol", symbol).execute()

            if response.data:
                position = response.data[0]
                pnl = (exit_price - position["avg_price"]) * position["quantity"]

                # Delete position
                self.client.table("portfolio").delete().eq("id", position["id"]).execute()
                return pnl
        except Exception as e:
            print(f"[ERROR] Failed to close position: {e}")
        return None

    # Trade History Operations
    def log_trade(self, trade: TradeEntry) -> bool:
        """Log trade to history"""
        if not self.client:
            return False
        try:
            self.client.table("trade_history").insert({
                "user_id": trade.user_id,
                "symbol": trade.symbol,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "quantity": trade.quantity,
                "trade_type": trade.trade_type,
                "strategy": trade.strategy,
                "reason": trade.reason,
                "emotion": trade.emotion,
                "pnl": trade.pnl,
                "entry_date": trade.entry_date.isoformat(),
                "exit_date": trade.exit_date.isoformat() if trade.exit_date else None,
                "status": trade.status
            }).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to log trade: {e}")
            return False

    def get_trade_history(self, user_id: str, limit: int = 100) -> List[TradeEntry]:
        """Get user's trade history"""
        if not self.client:
            return []
        try:
            response = self.client.table("trade_history").select("*") \
                .eq("user_id", user_id).order("entry_date", desc=True).limit(limit).execute()

            trades = []
            for data in response.data:
                trades.append(TradeEntry(
                    id=data.get("id"),
                    user_id=data["user_id"],
                    symbol=data["symbol"],
                    entry_price=data["entry_price"],
                    exit_price=data.get("exit_price"),
                    quantity=data["quantity"],
                    trade_type=data["trade_type"],
                    strategy=data["strategy"],
                    reason=data["reason"],
                    emotion=data.get("emotion"),
                    pnl=data.get("pnl"),
                    entry_date=datetime.fromisoformat(data["entry_date"]),
                    exit_date=datetime.fromisoformat(data["exit_date"]) if data.get("exit_date") else None,
                    status=data["status"]
                ))
            return trades
        except Exception as e:
            print(f"[ERROR] Failed to fetch trade history: {e}")
            return []

    # Watchlist Operations
    def get_watchlist(self, user_id: str) -> List[str]:
        """Get user's watchlist"""
        if not self.client:
            return []
        try:
            response = self.client.table("watchlist").select("symbol").eq("user_id", user_id).execute()
            return [item["symbol"] for item in response.data]
        except Exception as e:
            print(f"[ERROR] Failed to fetch watchlist: {e}")
            return []

    def add_to_watchlist(self, user_id: str, symbol: str) -> bool:
        """Add symbol to watchlist"""
        if not self.client:
            return False
        try:
            self.client.table("watchlist").insert({
                "user_id": user_id,
                "symbol": symbol
            }).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to add to watchlist: {e}")
            return False

    def remove_from_watchlist(self, user_id: str, symbol: str) -> bool:
        """Remove symbol from watchlist"""
        if not self.client:
            return False
        try:
            self.client.table("watchlist").delete().eq("user_id", user_id).eq("symbol", symbol).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to remove from watchlist: {e}")
            return False

    # Alerts Operations
    def get_alerts(self, user_id: str, active_only: bool = True) -> List[Dict]:
        """Get user alerts"""
        if not self.client:
            return []
        try:
            query = self.client.table("alerts").select("*").eq("user_id", user_id)
            if active_only:
                query = query.eq("is_active", True)
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"[ERROR] Failed to fetch alerts: {e}")
            return []

    def create_alert(self, user_id: str, symbol: str, alert_type: str,
                     condition: str, threshold: float) -> bool:
        """Create new alert"""
        if not self.client:
            return False
        try:
            self.client.table("alerts").insert({
                "user_id": user_id,
                "symbol": symbol,
                "alert_type": alert_type,
                "condition": condition,
                "threshold": threshold,
                "is_active": True
            }).execute()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create alert: {e}")
            return False


class PersonalizedAnalyzer:
    """Analyzes stocks with user-specific context"""

    def __init__(self, user_profile: UserProfile, supabase: SupabaseManager):
        self.profile = user_profile
        self.supabase = supabase

    def calculate_position_size(self, atr: float, current_price: float) -> Dict[str, Any]:
        """
        Calculate personalized position size based on user capital and risk tolerance
        Formula: risk_per_trade = capital * risk_percentage / ATR_stop_loss
        """
        # Risk per trade based on risk tolerance
        risk_pct = {
            "low": 0.005,      # 0.5%
            "medium": 0.01,    # 1%
            "high": 0.02       # 2%
        }.get(self.profile.risk_tolerance, 0.01)

        risk_per_trade = self.profile.capital * risk_pct

        # Stop loss distance (2x ATR for medium risk)
        atr_multiplier = {
            "low": 1.0,
            "medium": 1.5,
            "high": 2.0
        }.get(self.profile.risk_tolerance, 1.5)

        stop_loss_distance = atr * atr_multiplier

        # Position sizing
        if stop_loss_distance > 0:
            shares = int(risk_per_trade / stop_loss_distance)
        else:
            shares = 0

        position_value = shares * current_price
        position_pct_of_capital = (position_value / self.profile.capital) * 100

        return {
            "risk_per_trade": round(risk_per_trade, 2),
            "stop_loss_distance": round(stop_loss_distance, 2),
            "atr_multiplier": atr_multiplier,
            "recommended_shares": shares,
            "position_value": round(position_value, 2),
            "position_pct_of_capital": round(position_pct_of_capital, 2),
            "stop_loss_price": round(current_price - stop_loss_distance, 2),
            "take_profit_price": round(current_price + (stop_loss_distance * 2), 2),  # 1:2 risk-reward
            "risk_reward_ratio": 2.0
        }

    def generate_personalized_signal(self, technical_data: Dict, sentiment_score: float,
                                     ml_probability: float) -> Dict[str, Any]:
        """Generate trading signal personalized to user's risk profile and strategy"""

        # Extract technical signals
        rsi = technical_data.get("rsi", 50)
        trend = technical_data.get("trend", "neutral")
        macd_status = technical_data.get("macd_status", "neutral")

        # Composite signal score (-100 to 100)
        signal_score = 0

        # RSI contribution
        if rsi < 30:
            signal_score += 30
        elif rsi > 70:
            signal_score -= 30

        # Trend contribution
        if trend == "Bullish":
            signal_score += 25
        elif trend == "Bearish":
            signal_score -= 25

        # MACD contribution
        if macd_status == "Bullish":
            signal_score += 20
        elif macd_status == "Bearish":
            signal_score -= 20

        # Sentiment contribution
        signal_score += sentiment_score * 15

        # ML contribution
        signal_score += (ml_probability - 50) * 0.5

        # Clamp score
        signal_score = max(-100, min(100, signal_score))

        # Determine action based on score and user profile
        if signal_score >= 60:
            action = "Strong Buy"
            confidence = signal_score / 100
        elif signal_score >= 20:
            action = "Buy"
            confidence = signal_score / 100
        elif signal_score <= -60:
            action = "Strong Sell"
            confidence = abs(signal_score) / 100
        elif signal_score <= -20:
            action = "Sell"
            confidence = abs(signal_score) / 100
        else:
            action = "Hold"
            confidence = (60 - abs(signal_score)) / 60

        # Adjust for risk tolerance
        if self.profile.risk_tolerance == "low" and action in ["Strong Buy", "Strong Sell"]:
            action = action.replace("Strong ", "")  # Conservative users get moderated signals
            confidence *= 0.8

        # Adjust for preferred strategy timeframe
        strategy_match = self._check_strategy_match(technical_data)

        return {
            "action": action,
            "confidence": round(confidence, 2),
            "signal_score": round(signal_score, 2),
            "reasoning": self._generate_reasoning(action, technical_data, sentiment_score, strategy_match),
            "suitable_for_strategy": strategy_match,
            "risk_adjusted": self.profile.risk_tolerance
        }

    def _check_strategy_match(self, technical_data: Dict) -> str:
        """Check if signal matches user's preferred strategy"""
        strategy = self.profile.preferred_strategy

        # Intraday: Focus on momentum and volume
        if strategy == "intraday":
            if technical_data.get("volume_spike") and abs(technical_data.get("rsi", 50) - 50) > 10:
                return "high_match"
            return "moderate_match"

        # Swing: Focus on trend and momentum
        elif strategy == "swing":
            if technical_data.get("trend") in ["Bullish", "Bearish"]:
                return "high_match"
            return "moderate_match"

        # Long term: Focus on fundamentals and trend strength
        elif strategy == "long_term":
            if technical_data.get("trend_strength", 0) > 50:
                return "high_match"
            return "moderate_match"

        return "unknown"

    def _generate_reasoning(self, action: str, technical_data: Dict,
                           sentiment: float, strategy_match: str) -> str:
        """Generate human-readable reasoning for the signal"""
        reasons = []

        if technical_data.get("rsi", 50) < 30:
            reasons.append("RSI indicates oversold conditions")
        elif technical_data.get("rsi", 50) > 70:
            reasons.append("RSI indicates overbought conditions")

        if technical_data.get("trend"):
            reasons.append(f"Trend is {technical_data['trend'].lower()}")

        if abs(sentiment) > 0.3:
            sentiment_desc = "positive" if sentiment > 0 else "negative"
            reasons.append(f"News sentiment is {sentiment_desc}")

        if strategy_match == "high_match":
            reasons.append(f"Signal aligns well with your {self.profile.preferred_strategy} strategy")

        if not reasons:
            reasons.append("Technical indicators show mixed signals")

        return "; ".join(reasons)


class TradeJournalAnalyzer:
    """Analyzes trade history to provide AI insights"""

    def __init__(self, supabase: SupabaseManager):
        self.supabase = supabase

    def analyze_performance(self, user_id: str) -> Dict[str, Any]:
        """Analyze user's trading performance"""
        trades = self.supabase.get_trade_history(user_id)

        if not trades:
            return {"error": "No trade history found"}

        closed_trades = [t for t in trades if t.status == "closed" and t.pnl is not None]

        if not closed_trades:
            return {"error": "No closed trades to analyze"}

        # Basic metrics
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl <= 0]

        win_rate = len(winning_trades) / total_trades * 100

        # P&L metrics
        total_pnl = sum(t.pnl for t in closed_trades)
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0

        # Strategy performance
        strategy_performance = {}
        for trade in closed_trades:
            strategy = trade.strategy
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {"trades": 0, "wins": 0, "pnl": 0}
            strategy_performance[strategy]["trades"] += 1
            strategy_performance[strategy]["pnl"] += trade.pnl
            if trade.pnl > 0:
                strategy_performance[strategy]["wins"] += 1

        # Best and worst performers
        best_trade = max(closed_trades, key=lambda x: x.pnl)
        worst_trade = min(closed_trades, key=lambda x: x.pnl)

        # Emotion analysis
        emotions_with_pnl = [(t.emotion, t.pnl) for t in closed_trades if t.emotion]
        emotion_performance = {}
        for emotion, pnl in emotions_with_pnl:
            if emotion not in emotion_performance:
                emotion_performance[emotion] = {"count": 0, "total_pnl": 0}
            emotion_performance[emotion]["count"] += 1
            emotion_performance[emotion]["total_pnl"] += pnl

        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
            "strategy_performance": {
                k: {
                    "trades": v["trades"],
                    "win_rate": round(v["wins"] / v["trades"] * 100, 2),
                    "total_pnl": round(v["pnl"], 2)
                }
                for k, v in strategy_performance.items()
            },
            "best_trade": {
                "symbol": best_trade.symbol,
                "pnl": round(best_trade.pnl, 2),
                "strategy": best_trade.strategy
            },
            "worst_trade": {
                "symbol": worst_trade.symbol,
                "pnl": round(worst_trade.pnl, 2),
                "strategy": worst_trade.strategy
            },
            "emotion_analysis": {
                k: {
                    "count": v["count"],
                    "avg_pnl": round(v["total_pnl"] / v["count"], 2)
                }
                for k, v in emotion_performance.items()
            },
            "behavioral_insights": self._generate_behavioral_insights(
                win_rate, avg_win, avg_loss, strategy_performance, emotion_performance
            )
        }

    def _generate_behavioral_insights(self, win_rate, avg_win, avg_loss,
                                      strategy_performance, emotion_performance) -> List[str]:
        """Generate AI insights about trading behavior"""
        insights = []

        if win_rate < 40:
            insights.append("Your win rate is below 40%. Consider refining your entry criteria or using tighter stop losses.")
        elif win_rate > 60:
            insights.append("Excellent win rate! You're good at picking winning trades.")

        if avg_loss != 0 and avg_win / abs(avg_loss) < 1.5:
            insights.append("Your average loss is relatively large compared to wins. Consider using tighter stop losses.")

        if emotion_performance:
            best_emotion = max(emotion_performance.items(),
                              key=lambda x: x[1]["total_pnl"] / x[1]["count"])
            insights.append(f"You perform best when feeling {best_emotion[0]}.")

        # Find best strategy
        if strategy_performance:
            best_strategy = max(strategy_performance.items(),
                               key=lambda x: x[1]["pnl"] / x[1]["trades"])
            insights.append(f"Your '{best_strategy[0]}' strategy is performing best. Consider focusing on this approach.")

        return insights


class AICoach:
    """AI Trading Coach for personalized advice"""

    def __init__(self, supabase: SupabaseManager):
        self.supabase = supabase
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

    def generate_coaching_advice(self, user_id: str) -> Dict[str, Any]:
        """Generate personalized coaching advice using AI"""
        # Get user context
        profile = self.supabase.get_user_profile(user_id)
        if not profile:
            return {"error": "User profile not found"}

        portfolio = self.supabase.get_portfolio(user_id)
        trade_analysis = TradeJournalAnalyzer(self.supabase).analyze_performance(user_id)

        # Build context for AI
        context = {
            "risk_tolerance": profile.risk_tolerance,
            "capital": profile.capital,
            "preferred_strategy": profile.preferred_strategy,
            "portfolio_size": len(portfolio),
            "portfolio_value": sum(p.current_price * p.quantity for p in portfolio),
            "trade_performance": trade_analysis if "error" not in trade_analysis else None
        }

        # Generate advice using Gemini or fallback
        advice = self._generate_ai_advice(context)

        return {
            "user_context": context,
            "advice": advice,
            "action_items": self._generate_action_items(context, trade_analysis),
            "risk_warnings": self._generate_risk_warnings(context, portfolio),
            "timestamp": datetime.now().isoformat()
        }

    def _generate_ai_advice(self, context: Dict) -> str:
        """Generate AI coaching advice"""
        # Try Gemini first
        if self.gemini_api_key:
            try:
                import requests

                prompt = f"""You are an expert trading coach. Analyze this trader's context and provide personalized advice:

Risk Tolerance: {context['risk_tolerance']}
Capital: ₹{context['capital']:,}
Preferred Strategy: {context['preferred_strategy']}
Portfolio Size: {context['portfolio_size']} positions
Portfolio Value: ₹{context['portfolio_value']:,}

Provide 3 specific, actionable recommendations for improvement. Be encouraging but honest about areas for improvement."""

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500}
                }

                response = requests.post(url, json=payload, timeout=15)
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return text
            except Exception as e:
                print(f"[WARNING] Gemini coach failed: {e}")

        # Fallback advice
        return self._generate_fallback_advice(context)

    def _generate_fallback_advice(self, context: Dict) -> str:
        """Generate fallback coaching advice"""
        advice_lines = []

        if context['risk_tolerance'] == 'high':
            advice_lines.append("Your high risk tolerance allows for larger positions, but ensure you're using stop losses to protect your capital.")
        elif context['risk_tolerance'] == 'low':
            advice_lines.append("Your conservative approach is good for capital preservation. Consider gradually increasing position sizes as you gain confidence.")

        if context['portfolio_size'] == 0:
            advice_lines.append("Your portfolio is empty. Start with small positions to test your strategy before committing larger amounts.")
        elif context['portfolio_size'] > 10:
            advice_lines.append("You have many positions. Consider focusing on your best ideas to improve monitoring and performance.")

        strategy_tips = {
            "intraday": "For intraday trading, focus on high-volume stocks and always use stop losses. Don't hold overnight.",
            "swing": "For swing trading, patience is key. Wait for clear setups and let your winners run.",
            "long_term": "For long-term investing, focus on fundamentals and don't worry about short-term volatility."
        }

        if context['preferred_strategy'] in strategy_tips:
            advice_lines.append(strategy_tips[context['preferred_strategy']])

        return "\n\n".join(advice_lines)

    def _generate_action_items(self, context: Dict, trade_analysis: Dict) -> List[str]:
        """Generate specific action items"""
        actions = []

        if context['portfolio_size'] == 0:
            actions.append("Add 2-3 stocks to your watchlist to start tracking")
            actions.append("Paper trade for 1 week to test your strategy")
        else:
            actions.append("Review your portfolio allocation")
            actions.append("Set stop losses for all open positions")

        if "error" not in trade_analysis:
            if trade_analysis.get("win_rate", 0) < 50:
                actions.append("Review your last 5 losing trades for patterns")

        return actions

    def _generate_risk_warnings(self, context: Dict, portfolio: List[PortfolioPosition]) -> List[str]:
        """Generate risk warnings"""
        warnings = []

        # Check concentration risk
        if portfolio:
            total_value = sum(p.current_price * p.quantity for p in portfolio)
            for position in portfolio:
                position_value = position.current_price * position.quantity
                if position_value > total_value * 0.4:
                    warnings.append(f"High concentration in {position.symbol} ({position_value/total_value*100:.1f}% of portfolio)")

        # Check capital usage
        if context['portfolio_value'] > context['capital'] * 0.9:
            warnings.append("You are using most of your available capital. Keep some cash for opportunities.")

        return warnings


# Global instances
supabase_manager = SupabaseManager()
