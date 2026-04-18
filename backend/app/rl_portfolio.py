"""
Reinforcement Learning based Portfolio Optimization
Implements Q-Learning for optimal portfolio allocation
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List
from collections import defaultdict


class PortfolioRLAgent:
    """Reinforcement Learning agent for portfolio optimization"""
    
    def __init__(self, num_stocks: int = 5, learning_rate: float = 0.1, 
                 discount_factor: float = 0.95, epsilon: float = 0.1):
        """
        Initialize RL Agent
        
        Args:
            num_stocks: Number of stocks in portfolio
            learning_rate: Learning rate for Q-learning
            discount_factor: Gamma for value iteration
            epsilon: Epsilon for epsilon-greedy policy
        """
        self.num_stocks = num_stocks
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        
        # Actions: allocation percentages (0-100%)
        self.actions = np.array([0, 25, 50, 75, 100])  # Simple discrete actions
        
        # State space: price changes, sentiment, volatility
        self.q_table = defaultdict(lambda: defaultdict(float))
        
        self.episode_rewards = []
    
    def discretize_state(self, prices: List[float], sentiment: float, 
                        volatility: float) -> str:
        """Discretize continuous state into categorical"""
        # Price change
        price_change = (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else 0
        
        if price_change > 0.05:
            price_state = "UP"
        elif price_change < -0.05:
            price_state = "DOWN"
        else:
            price_state = "FLAT"
        
        # Sentiment state
        if sentiment > 0.3:
            sentiment_state = "POSITIVE"
        elif sentiment < -0.3:
            sentiment_state = "NEGATIVE"
        else:
            sentiment_state = "NEUTRAL"
        
        # Volatility state
        if volatility > 0.04:
            vol_state = "HIGH"
        else:
            vol_state = "LOW"
        
        return f"{price_state}_{sentiment_state}_{vol_state}"
    
    def get_action(self, state: str, train: bool = True) -> int:
        """Epsilon-greedy action selection"""
        if train and np.random.random() < self.epsilon:
            return np.random.choice(range(len(self.actions)))
        
        q_values = [self.q_table[state][a] for a in range(len(self.actions))]
        return np.argmax(q_values)
    
    def calculate_reward(self, portfolio_return: float, sharpe_ratio: float) -> float:
        """Calculate reward based on returns and risk"""
        # Reward = return * risk_adjustment
        reward = portfolio_return * 100  # Convert to percentage points
        reward += sharpe_ratio * 10  # Bonus for risk-adjusted returns
        return reward
    
    def update_q_value(self, state: str, action: int, reward: float, next_state: str):
        """Update Q-value using Q-learning update rule"""
        next_q_values = [self.q_table[next_state][a] for a in range(len(self.actions))]
        max_next_q = max(next_q_values) if next_q_values else 0
        
        current_q = self.q_table[state][action]
        new_q = current_q + self.lr * (reward + self.gamma * max_next_q - current_q)
        
        self.q_table[state][action] = new_q
    
    def optimize_portfolio(self, prices_history: Dict[str, List[float]], 
                          sentiments: Dict[str, float],
                          volatilities: Dict[str, float]) -> Dict:
        """
        Find optimal portfolio allocation
        
        Args:
            prices_history: Dict of symbol -> price history
            sentiments: Dict of symbol -> sentiment score
            volatilities: Dict of symbol -> volatility
        
        Returns:
            Optimal allocation
        """
        # State representation
        avg_price = np.mean([p[-1] for p in prices_history.values()])
        avg_sentiment = np.mean(list(sentiments.values()))
        avg_vol = np.mean(list(volatilities.values()))
        
        state = self.discretize_state([avg_price], avg_sentiment, avg_vol)
        
        # Get best action
        action_idx = self.get_action(state, train=False)
        allocation = self.actions[action_idx]
        
        return {
            "state": state,
            "action": self.actions[action_idx],
            "allocation": allocation,
            "recommended_action": self._action_to_recommendation(allocation)
        }
    
    def _action_to_recommendation(self, allocation: float) -> str:
        """Convert allocation to action recommendation"""
        if allocation >= 75:
            return "STRONG_BUY"
        elif allocation >= 50:
            return "BUY"
        elif allocation >= 25:
            return "HOLD"
        else:
            return "REDUCE"


class SharpeCalculator:
    """Calculate Sharpe Ratio and other portfolio metrics"""
    
    @staticmethod
    def calculate_sharpe(returns: List[float], risk_free_rate: float = 0.05) -> float:
        """
        Calculate Sharpe Ratio
        
        Args:
            returns: List of returns
            risk_free_rate: Risk-free rate (annual)
        
        Returns:
            Sharpe ratio
        """
        if len(returns) < 2:
            return 0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily
        
        if np.std(excess_returns) == 0:
            return 0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        return float(sharpe)
    
    @staticmethod
    def calculate_beta(stock_returns: List[float], market_returns: List[float]) -> float:
        """Calculate Beta (vs market)"""
        if len(stock_returns) < 2 or len(market_returns) < 2:
            return 1.0
        
        stock_ret = np.array(stock_returns)
        market_ret = np.array(market_returns)
        
        covariance = np.cov(stock_ret, market_ret)[0][1]
        market_variance = np.var(market_ret)
        
        if market_variance == 0:
            return 1.0
        
        beta = covariance / market_variance
        return float(beta)
    
    @staticmethod
    def calculate_alpha(stock_return: float, beta: float, market_return: float, 
                       risk_free_rate: float = 0.05) -> float:
        """Calculate Jensen's Alpha"""
        expected_return = risk_free_rate + beta * (market_return - risk_free_rate)
        alpha = stock_return - expected_return
        return float(alpha)


# Global RL agent
portfolio_rl_agent = PortfolioRLAgent(num_stocks=5)
sharpe_calc = SharpeCalculator()

