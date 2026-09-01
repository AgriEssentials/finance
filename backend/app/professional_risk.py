"""
Professional Risk Management Module
Advanced position sizing, portfolio risk analysis, and institutional-grade risk controls
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math


class RiskLevel(Enum):
    VERY_LOW = "Very Low"
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    VERY_HIGH = "Very High"


@dataclass
class PositionSizingResult:
    """Position sizing calculation result"""
    recommended_shares: int
    position_value: float
    position_size_percent: float
    risk_amount: float
    risk_percent: float
    stop_loss_price: float
    take_profit_price: float
    risk_reward_ratio: float
    kelly_fraction: float
    optimal_position_percent: float
    max_position_shares: int
    suggested_capital: float


@dataclass
class PortfolioRiskMetrics:
    """Portfolio-level risk metrics"""
    total_value: float
    total_risk: float
    risk_percent: float
    max_drawdown: float
    sharpe_ratio: float
    beta: float
    correlation_with_market: float
    diversification_score: float
    concentration_risk: float


class ProfessionalRiskManager:
    """Institutional-grade risk management system"""
    
    def __init__(self, 
                 portfolio_value: float = 1000000,
                 max_risk_per_trade: float = 1.0,
                 max_position_size: float = 10.0,
                 correlation_threshold: float = 0.7):
        """
        Initialize risk manager
        
        Args:
            portfolio_value: Total portfolio value in INR
            max_risk_per_trade: Maximum risk per trade (%)
            max_position_size: Maximum position size (% of portfolio)
            correlation_threshold: Maximum correlation with existing positions
        """
        self.portfolio_value = portfolio_value
        self.max_risk_per_trade = max_risk_per_trade
        self.max_position_size = max_position_size
        self.correlation_threshold = correlation_threshold
        
    def calculate_kelly_criterion(self, 
                                  win_rate: float, 
                                  avg_win: float, 
                                  avg_loss: float) -> Dict[str, float]:
        """
        Calculate Kelly Criterion for optimal position sizing
        
        Kelly % = W - [(1 - W) / R]
        Where W = Win rate, R = Win/Loss ratio
        
        Args:
            win_rate: Probability of winning (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount
            
        Returns:
            Kelly criterion calculations
        """
        if avg_loss == 0:
            return {
                'kelly_fraction': 0,
                'half_kelly': 0,
                'quarter_kelly': 0,
                'recommended': 0,
                'interpretation': 'Insufficient data'
            }
        
        # Calculate win/loss ratio
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Kelly formula: K% = W - [(1-W)/R]
        kelly_fraction = win_rate - ((1 - win_rate) / win_loss_ratio) if win_loss_ratio > 0 else 0
        
        # Clamp between 0 and 1
        kelly_fraction = max(0, min(1, kelly_fraction))
        
        # Conservative variants
        half_kelly = kelly_fraction / 2
        quarter_kelly = kelly_fraction / 4
        
        # Recommended: Use half-Kelly for safety
        recommended = half_kelly
        
        interpretation = self._interpret_kelly(kelly_fraction)
        
        return {
            'kelly_fraction': round(kelly_fraction * 100, 2),
            'half_kelly': round(half_kelly * 100, 2),
            'quarter_kelly': round(quarter_kelly * 100, 2),
            'recommended': round(recommended * 100, 2),
            'win_rate': round(win_rate * 100, 2),
            'win_loss_ratio': round(win_loss_ratio, 2),
            'interpretation': interpretation
        }
    
    def _interpret_kelly(self, kelly: float) -> str:
        """Interpret Kelly criterion value"""
        if kelly >= 0.5:
            return "Aggressive bet - High edge detected"
        elif kelly >= 0.25:
            return "Moderate bet - Favorable edge"
        elif kelly >= 0.1:
            return "Conservative bet - Small edge"
        elif kelly > 0:
            return "Minimal bet - Weak edge"
        else:
            return "No bet - Negative edge or insufficient data"
    
    def calculate_position_sizing(self,
                                  entry_price: float,
                                  stop_loss: float,
                                  take_profit: float,
                                  atr: float,
                                  win_rate: float = 0.55,
                                  volatility: float = 0.20,
                                  risk_per_trade: Optional[float] = None) -> PositionSizingResult:
        """
        Calculate optimal position size using multiple methods
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            atr: Average True Range
            win_rate: Expected win rate
            volatility: Stock volatility
            risk_per_trade: Risk per trade (defaults to max_risk_per_trade)
            
        Returns:
            Comprehensive position sizing result
        """
        if risk_per_trade is None:
            risk_per_trade = self.max_risk_per_trade
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share == 0:
            risk_per_share = atr * 1.5  # Fallback to ATR-based stop
        
        # Calculate potential reward
        reward_per_share = abs(take_profit - entry_price)
        risk_reward = reward_per_share / risk_per_share if risk_per_share > 0 else 0
        
        # Method 1: Fixed Risk Position Sizing
        max_risk_amount = self.portfolio_value * (risk_per_trade / 100)
        shares_fixed_risk = int(max_risk_amount / risk_per_share)
        
        # Method 2: Kelly Criterion Position Sizing
        avg_win = reward_per_share * win_rate
        avg_loss = risk_per_share * (1 - win_rate)
        kelly = self.calculate_kelly_criterion(win_rate, avg_win, avg_loss)
        kelly_fraction = kelly['recommended'] / 100
        
        # Apply Kelly sizing (capped at 25% of portfolio)
        kelly_position_value = self.portfolio_value * min(kelly_fraction, 0.25)
        shares_kelly = int(kelly_position_value / entry_price)
        
        # Method 3: Volatility-Adjusted Position Sizing
        # Reduce position size for high volatility stocks
        vol_adjustment = max(0.3, 1 - (volatility - 0.15) * 2)
        vol_adjusted_risk = risk_per_trade * vol_adjustment
        vol_risk_amount = self.portfolio_value * (vol_adjusted_risk / 100)
        shares_vol_adjusted = int(vol_risk_amount / risk_per_share)
        
        # Method 4: Maximum Position Size Constraint
        max_position_value = self.portfolio_value * (self.max_position_size / 100)
        shares_max_position = int(max_position_value / entry_price)
        
        # Select most conservative (minimum of all methods)
        recommended_shares = min(shares_fixed_risk, shares_kelly, shares_vol_adjusted, shares_max_position)
        recommended_shares = max(1, recommended_shares)  # At least 1 share
        
        # Calculate final metrics
        position_value = recommended_shares * entry_price
        position_size_percent = (position_value / self.portfolio_value) * 100
        risk_amount = recommended_shares * risk_per_share
        actual_risk_percent = (risk_amount / self.portfolio_value) * 100
        
        return PositionSizingResult(
            recommended_shares=recommended_shares,
            position_value=round(position_value, 2),
            position_size_percent=round(position_size_percent, 2),
            risk_amount=round(risk_amount, 2),
            risk_percent=round(actual_risk_percent, 2),
            stop_loss_price=round(stop_loss, 2),
            take_profit_price=round(take_profit, 2),
            risk_reward_ratio=round(risk_reward, 2),
            kelly_fraction=round(kelly_fraction * 100, 2),
            optimal_position_percent=round(kelly['recommended'], 2),
            max_position_shares=shares_max_position,
            suggested_capital=round(position_value, 2)
        )
    
    def calculate_portfolio_risk(self, 
                                 positions: List[Dict[str, Any]],
                                 historical_returns: Optional[pd.DataFrame] = None) -> PortfolioRiskMetrics:
        """
        Calculate portfolio-level risk metrics
        
        Args:
            positions: List of position dictionaries with symbol, value, entry, stop_loss
            historical_returns: DataFrame of historical returns for correlation analysis
            
        Returns:
            Portfolio risk metrics
        """
        total_value = sum(pos['value'] for pos in positions) if positions else self.portfolio_value
        
        # Calculate total risk exposure
        total_risk = sum(
            pos['value'] * (abs(pos['entry'] - pos['stop_loss']) / pos['entry'])
            for pos in positions
        )
        risk_percent = (total_risk / total_value) * 100 if total_value > 0 else 0
        
        # Calculate concentration risk (Herfindahl Index)
        weights = [pos['value'] / total_value for pos in positions] if total_value > 0 else []
        concentration = sum(w**2 for w in weights) if weights else 0
        
        # Calculate diversification score
        num_positions = len(positions)
        diversification_score = min(100, num_positions * 10) if num_positions > 0 else 0
        if concentration > 0.25:  # If any single position > 25%
            diversification_score *= 0.7
        
        # Estimate max drawdown (simplified)
        max_drawdown = risk_percent * 1.5  # Conservative estimate
        
        # Calculate Sharpe ratio (if returns provided)
        sharpe = 0
        if historical_returns is not None and len(historical_returns) > 0:
            returns_mean = historical_returns.mean().mean()
            returns_std = historical_returns.std().mean()
            if returns_std > 0:
                sharpe = (returns_mean * 252) / (returns_std * np.sqrt(252))  # Annualized
        
        return PortfolioRiskMetrics(
            total_value=round(total_value, 2),
            total_risk=round(total_risk, 2),
            risk_percent=round(risk_percent, 2),
            max_drawdown=round(max_drawdown, 2),
            sharpe_ratio=round(sharpe, 2),
            beta=0,  # Would need market data
            correlation_with_market=0,
            diversification_score=round(diversification_score, 1),
            concentration_risk=round(concentration * 100, 2)
        )
    
    def assess_trade_quality(self,
                            entry_price: float,
                            stop_loss: float,
                            take_profit: float,
                            technical_score: float,
                            fundamental_score: float,
                            sentiment_score: float) -> Dict[str, Any]:
        """
        Comprehensive trade quality assessment
        
        Returns:
            Trade quality metrics and recommendation
        """
        # Calculate risk-reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Calculate composite score
        composite_score = (technical_score * 0.4 + 
                          fundamental_score * 0.35 + 
                          sentiment_score * 0.25)
        
        # Risk-reward quality score
        rr_quality = 0
        if rr_ratio >= 3:
            rr_quality = 10
        elif rr_ratio >= 2:
            rr_quality = 8
        elif rr_ratio >= 1.5:
            rr_quality = 6
        elif rr_ratio >= 1:
            rr_quality = 4
        else:
            rr_quality = 2
        
        # Final trade score
        final_score = (composite_score * 0.7 + rr_quality * 3)
        
        # Determine quality grade
        if final_score >= 85:
            grade = 'A+ (Excellent Trade)'
            recommendation = 'Strong Buy - All criteria met'
            confidence = 'Very High'
        elif final_score >= 70:
            grade = 'A (Very Good Trade)'
            recommendation = 'Buy - Strong setup'
            confidence = 'High'
        elif final_score >= 55:
            grade = 'B+ (Good Trade)'
            recommendation = 'Moderate Buy - Favorable setup'
            confidence = 'Medium'
        elif final_score >= 40:
            grade = 'B (Average Trade)'
            recommendation = 'Small Position - Mixed signals'
            confidence = 'Medium-Low'
        elif final_score >= 25:
            grade = 'C (Below Average)'
            recommendation = 'Avoid or Very Small Position'
            confidence = 'Low'
        else:
            grade = 'D (Poor Trade)'
            recommendation = 'Do Not Trade - Unfavorable setup'
            confidence = 'Very Low'
        
        return {
            'trade_score': round(final_score, 1),
            'grade': grade,
            'recommendation': recommendation,
            'confidence': confidence,
            'risk_reward_ratio': round(rr_ratio, 2),
            'component_scores': {
                'technical': round(technical_score, 1),
                'fundamental': round(fundamental_score, 1),
                'sentiment': round(sentiment_score, 1),
                'risk_reward_quality': rr_quality
            },
            'risk_amount': round(risk, 2),
            'potential_reward': round(reward, 2),
            'breakeven_win_rate': round(1 / (1 + rr_ratio) * 100, 1) if rr_ratio > 0 else 0
        }
    
    def calculate_scenarios(self,
                           entry_price: float,
                           stop_loss: float,
                           take_profit: float,
                           position_size: int,
                           scenarios: List[float] = None) -> List[Dict[str, Any]]:
        """
        Calculate P&L for different price scenarios
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss
            take_profit: Take profit
            position_size: Number of shares
            scenarios: List of price movement percentages (default: -10% to +10%)
            
        Returns:
            List of scenario results
        """
        if scenarios is None:
            scenarios = [-0.10, -0.08, -0.05, -0.03, 0, 0.03, 0.05, 0.08, 0.10]
        
        results = []
        for change in scenarios:
            scenario_price = entry_price * (1 + change)
            pnl = (scenario_price - entry_price) * position_size
            pnl_percent = change * 100
            
            # Determine outcome
            if scenario_price <= stop_loss:
                outcome = 'Stop Loss Hit'
                status = 'Loss'
            elif scenario_price >= take_profit:
                outcome = 'Take Profit Hit'
                status = 'Win'
            elif change < 0:
                outcome = 'Unrealized Loss'
                status = 'Loss'
            elif change > 0:
                outcome = 'Unrealized Profit'
                status = 'Win'
            else:
                outcome = 'Break Even'
                status = 'Neutral'
            
            results.append({
                'price_change': f"{change*100:+.1f}%",
                'price': round(scenario_price, 2),
                'pnl': round(pnl, 2),
                'pnl_percent': round(pnl_percent, 1),
                'outcome': outcome,
                'status': status
            })
        
        return results
    
    def get_complete_risk_report(self,
                                entry_price: float,
                                stop_loss: float,
                                take_profit: float,
                                atr: float,
                                technical_score: float = 60,
                                fundamental_score: float = 60,
                                sentiment_score: float = 50) -> Dict[str, Any]:
        """
        Generate complete professional risk report
        
        Returns:
            Comprehensive risk analysis report
        """
        position_sizing = self.calculate_position_sizing(
            entry_price, stop_loss, take_profit, atr
        )
        
        trade_quality = self.assess_trade_quality(
            entry_price, stop_loss, take_profit,
            technical_score, fundamental_score, sentiment_score
        )
        
        scenarios = self.calculate_scenarios(
            entry_price, stop_loss, take_profit,
            position_sizing.recommended_shares
        )
        
        # Calculate Kelly criterion
        avg_win = abs(take_profit - entry_price)
        avg_loss = abs(entry_price - stop_loss)
        kelly = self.calculate_kelly_criterion(0.55, avg_win, avg_loss)
        
        return {
            'position_sizing': {
                'shares': position_sizing.recommended_shares,
                'position_value': position_sizing.position_value,
                'position_percent': position_sizing.position_size_percent,
                'risk_amount': position_sizing.risk_amount,
                'risk_percent': position_sizing.risk_percent
            },
            'risk_management': {
                'stop_loss': position_sizing.stop_loss_price,
                'take_profit': position_sizing.take_profit_price,
                'risk_reward': position_sizing.risk_reward_ratio,
                'kelly_criterion': kelly
            },
            'trade_quality': trade_quality,
            'scenario_analysis': scenarios,
            'professional_recommendations': self._generate_recommendations(
                trade_quality, position_sizing
            )
        }
    
    def _generate_recommendations(self, 
                                  trade_quality: Dict,
                                  position_sizing: PositionSizingResult) -> List[str]:
        """Generate professional recommendations"""
        recommendations = []
        
        score = trade_quality['trade_score']
        
        if score >= 70:
            recommendations.append("✓ Excellent trade setup - Consider full position size")
        elif score >= 55:
            recommendations.append("✓ Good trade setup - Consider 75% of recommended position")
        elif score >= 40:
            recommendations.append("⚠ Average setup - Consider 50% of recommended position or wait")
        else:
            recommendations.append("✗ Poor setup - Avoid this trade")
        
        if position_sizing.risk_reward_ratio >= 2:
            recommendations.append(f"✓ Favorable risk-reward ratio ({position_sizing.risk_reward_ratio}:1)")
        elif position_sizing.risk_reward_ratio < 1.5:
            recommendations.append(f"⚠ Poor risk-reward ratio ({position_sizing.risk_reward_ratio}:1) - Consider better entry")
        
        if position_sizing.position_size_percent > self.max_position_size * 0.8:
            recommendations.append(f"⚠ Position size ({position_sizing.position_size_percent}%) approaching maximum limit")
        
        if trade_quality.get('breakeven_win_rate', 0) > 50:
            recommendations.append(f"⚠ High breakeven win rate ({trade_quality['breakeven_win_rate']}%)")
        
        return recommendations
