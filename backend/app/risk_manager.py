"""
Risk Management Module
Handles risk calculations, stop-loss determination, and risk level classification
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional


class RiskManager:
    """Class to manage risk calculations and assessments"""
    
    def __init__(self, indicators: Dict[str, Any]):
        """
        Initialize risk manager with calculated indicators
        
        Args:
            indicators: Dictionary containing technical indicators
        """
        self.indicators = indicators
        
    def calculate_stop_loss(self, current_price: float, atr: float, 
                          multiplier: float = 1.5) -> Dict[str, Any]:
        """
        Calculate ATR-based stop loss
        
        Args:
            current_price: Current stock price
            atr: Average True Range value
            multiplier: ATR multiplier (default 1.5)
            
        Returns:
            Dictionary with stop loss information
        """
        stop_loss_price = current_price - (atr * multiplier)
        stop_loss_percent = ((current_price - stop_loss_price) / current_price) * 100
        
        return {
            "stop_loss_price": round(stop_loss_price, 2),
            "stop_loss_percent": round(stop_loss_percent, 2),
            "atr_used": round(atr, 2),
            "multiplier": multiplier
        }
    
    def calculate_take_profit(self, current_price: float, stop_loss_percent: float,
                            risk_reward_ratio: float = 2.0) -> Dict[str, Any]:
        """
        Calculate take profit level based on risk-reward ratio
        
        Args:
            current_price: Current stock price
            stop_loss_percent: Stop loss percentage
            risk_reward_ratio: Risk to reward ratio (default 2:1)
            
        Returns:
            Dictionary with take profit information
        """
        take_profit_percent = stop_loss_percent * risk_reward_ratio
        take_profit_price = current_price * (1 + take_profit_percent / 100)
        
        return {
            "take_profit_price": round(take_profit_price, 2),
            "take_profit_percent": round(take_profit_percent, 2),
            "risk_reward_ratio": risk_reward_ratio
        }
    
    def assess_risk_level(self, trend: str, rsi: float, 
                         sentiment_score: float, volatility: Optional[float] = None) -> str:
        """
        Assess overall risk level based on multiple factors
        
        Args:
            trend: Current trend (Bullish/Bearish/Neutral)
            rsi: RSI value
            sentiment_score: Sentiment score (-1 to 1)
            volatility: Volatility measure (optional)
            
        Returns:
            Risk level string (Low/Medium/High)
        """
        risk_score = 0
        
        # Trend risk
        if trend == "Bearish":
            risk_score += 2
        elif trend == "Neutral":
            risk_score += 1
        
        # RSI risk (extreme values increase risk)
        if rsi > 70 or rsi < 30:
            risk_score += 2
        elif rsi > 65 or rsi < 35:
            risk_score += 1
        
        # Sentiment risk
        if abs(sentiment_score) < 0.2:
            risk_score += 1  # Uncertain sentiment
        elif sentiment_score < -0.5:
            risk_score += 2  # Strong negative sentiment
        
        # Volatility risk
        if volatility is not None:
            if volatility > 30:  # High volatility
                risk_score += 2
            elif volatility > 20:  # Medium volatility
                risk_score += 1
        
        # Classify risk level
        if risk_score >= 4:
            return "High"
        elif risk_score >= 2:
            return "Medium"
        else:
            return "Low"
    
    def calculate_position_size(self, portfolio_value: float, 
                              risk_percent: float, 
                              stop_loss_percent: float) -> Dict[str, Any]:
        """
        Calculate recommended position size based on risk management
        
        Args:
            portfolio_value: Total portfolio value
            risk_percent: Percentage of portfolio to risk (e.g., 1 for 1%)
            stop_loss_percent: Stop loss percentage
            
        Returns:
            Dictionary with position sizing information
        """
        risk_amount = portfolio_value * (risk_percent / 100)
        position_size = risk_amount / (stop_loss_percent / 100)
        position_percent = (position_size / portfolio_value) * 100
        
        return {
            "max_position_value": round(position_size, 2),
            "position_percent": round(position_percent, 2),
            "risk_amount": round(risk_amount, 2),
            "risk_percent": risk_percent
        }
    
    def get_full_risk_assessment(self, current_price: float, portfolio_value: float = 100000) -> Dict[str, Any]:
        """
        Get complete risk assessment
        
        Args:
            current_price: Current stock price
            portfolio_value: Portfolio value for position sizing (default 100000)
            
        Returns:
            Dictionary with complete risk information
        """
        # Extract values from indicators
        atr = self.indicators.get('atr', 0)
        trend = self.indicators.get('trend', 'Neutral')
        rsi = self.indicators.get('rsi', 50)
        volatility = self.indicators.get('volatility', None)
        
        # Default sentiment score (will be updated from sentiment module)
        sentiment_score = self.indicators.get('sentiment_score', 0)
        
        # Calculate stop loss
        stop_loss = self.calculate_stop_loss(current_price, atr)
        
        # Calculate take profit (2:1 risk-reward)
        take_profit = self.calculate_take_profit(
            current_price, 
            stop_loss['stop_loss_percent']
        )
        
        # Assess risk level
        risk_level = self.assess_risk_level(trend, rsi, sentiment_score, volatility)
        
        # Calculate position size (risk 1% of portfolio)
        position_size = self.calculate_position_size(
            portfolio_value,
            risk_percent=1.0,
            stop_loss_percent=stop_loss['stop_loss_percent']
        )
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_level": risk_level,
            "position_sizing": position_size,
            "risk_factors": {
                "trend": trend,
                "rsi_level": rsi,
                "sentiment": sentiment_score,
                "volatility": volatility
            }
        }