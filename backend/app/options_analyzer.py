"""
Options Analysis Module
Professional options Greeks calculation and options chain analysis
"""

import numpy as np
from scipy.stats import norm
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import yfinance as yf

@dataclass
class OptionGreeks:
    """Options Greeks"""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    implied_volatility: float
    
@dataclass
class OptionContract:
    """Single option contract details"""
    strike: float
    expiry: datetime
    option_type: str  # 'call' or 'put'
    last_price: float
    bid: float
    ask: float
    volume: int
    open_interest: int
    greeks: Optional[OptionGreeks] = None
    intrinsic_value: float = 0.0
    time_value: float = 0.0
    moneyness: str = "ATM"  # ITM, ATM, OTM

class OptionsAnalyzer:
    """Professional options analysis with Greeks calculation"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.ticker = yf.Ticker(symbol)
        self.risk_free_rate = 0.06  # 6% annual - adjust based on current rates
        
    def get_options_chain(self, expiry_date: Optional[str] = None) -> Dict:
        """Get full options chain for a symbol"""
        try:
            # Get available expiry dates
            if expiry_date:
                chain = self.ticker.option_chain(expiry_date)
            else:
                # Get nearest expiry
                expirations = self.ticker.options
                if not expirations:
                    return {"error": "No options data available"}
                chain = self.ticker.option_chain(expirations[0])
                expiry_date = expirations[0]
            
            # Get current stock price
            current_price = self._get_current_price()
            
            # Calculate time to expiry in years
            expiry_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
            days_to_expiry = (expiry_dt - datetime.now()).days
            time_to_expiry = max(days_to_expiry / 365.0, 0.001)  # Minimum 0.001 years
            
            # Process calls
            calls = self._process_options(
                chain.calls, 
                'call', 
                current_price, 
                time_to_expiry,
                expiry_date
            )
            
            # Process puts
            puts = self._process_options(
                chain.puts, 
                'put', 
                current_price, 
                time_to_expiry,
                expiry_date
            )
            
            # Calculate metrics
            call_volume = sum(c.volume for c in calls)
            put_volume = sum(p.volume for p in puts)
            put_call_ratio = put_volume / call_volume if call_volume > 0 else 0
            
            # Max pain calculation
            max_pain = self._calculate_max_pain(calls, puts, current_price)
            
            return {
                "symbol": self.symbol,
                "current_price": current_price,
                "expiry_date": expiry_date,
                "days_to_expiry": days_to_expiry,
                "calls": [self._contract_to_dict(c) for c in calls],
                "puts": [self._contract_to_dict(p) for p in puts],
                "summary": {
                    "call_volume": call_volume,
                    "put_volume": put_volume,
                    "put_call_ratio": round(put_call_ratio, 2),
                    "total_open_interest_calls": sum(c.open_interest for c in calls),
                    "total_open_interest_puts": sum(p.open_interest for p in puts),
                    "max_pain": max_pain,
                    "implied_volatility_avg": self._calculate_avg_iv(calls, puts)
                },
                "support_resistance": self._find_support_resistance(calls, puts, current_price)
            }
            
        except Exception as e:
            return {"error": f"Failed to fetch options chain: {str(e)}"}
    
    def _process_options(
        self, 
        options_df, 
        option_type: str, 
        current_price: float,
        time_to_expiry: float,
        expiry_date: str
    ) -> List[OptionContract]:
        """Process options DataFrame into OptionContract objects"""
        contracts = []
        
        for _, row in options_df.iterrows():
            strike = row['strike']
            last_price = row.get('lastPrice', 0)
            
            # Calculate moneyness
            if option_type == 'call':
                intrinsic = max(0, current_price - strike)
                moneyness = "ITM" if current_price > strike else "ATM" if abs(current_price - strike) < 0.01 * current_price else "OTM"
            else:
                intrinsic = max(0, strike - current_price)
                moneyness = "ITM" if strike > current_price else "ATM" if abs(current_price - strike) < 0.01 * current_price else "OTM"
            
            time_value = last_price - intrinsic
            
            # Calculate Greeks
            implied_vol = row.get('impliedVolatility', 0.3)
            if implied_vol <= 0:
                implied_vol = self._estimate_iv(row, current_price, strike, time_to_expiry, option_type)
            
            greeks = self._calculate_greeks(
                current_price, 
                strike, 
                time_to_expiry, 
                self.risk_free_rate, 
                implied_vol,
                option_type
            )
            
            contract = OptionContract(
                strike=strike,
                expiry=datetime.strptime(expiry_date, "%Y-%m-%d"),
                option_type=option_type,
                last_price=last_price,
                bid=row.get('bid', 0),
                ask=row.get('ask', 0),
                volume=row.get('volume', 0),
                open_interest=row.get('openInterest', 0),
                greeks=greeks,
                intrinsic_value=round(intrinsic, 2),
                time_value=round(max(0, time_value), 2),
                moneyness=moneyness
            )
            
            contracts.append(contract)
        
        return contracts
    
    def _calculate_greeks(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str
    ) -> OptionGreeks:
        """Calculate option Greeks using Black-Scholes model"""
        
        d1 = (np.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)
        
        if option_type == 'call':
            delta = norm.cdf(d1)
            theta = (-spot * norm.pdf(d1) * volatility / (2 * np.sqrt(time_to_expiry)) 
                    - risk_free_rate * strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)) / 365
        else:
            delta = norm.cdf(d1) - 1
            theta = (-spot * norm.pdf(d1) * volatility / (2 * np.sqrt(time_to_expiry)) 
                    + risk_free_rate * strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2)) / 365
        
        gamma = norm.pdf(d1) / (spot * volatility * np.sqrt(time_to_expiry))
        vega = spot * norm.pdf(d1) * np.sqrt(time_to_expiry) / 100  # Per 1% change in IV
        rho = (strike * time_to_expiry * np.exp(-risk_free_rate * time_to_expiry) 
               * (norm.cdf(d2) if option_type == 'call' else -norm.cdf(-d2))) / 100  # Per 1% change in rate
        
        return OptionGreeks(
            delta=round(delta, 4),
            gamma=round(gamma, 4),
            theta=round(theta, 4),
            vega=round(vega, 4),
            rho=round(rho, 4),
            implied_volatility=round(volatility, 4)
        )
    
    def _estimate_iv(
        self,
        row: Dict,
        spot: float,
        strike: float,
        time_to_expiry: float,
        option_type: str
    ) -> float:
        """Estimate implied volatility using bisection method"""
        market_price = (row.get('bid', 0) + row.get('ask', 0)) / 2
        if market_price <= 0:
            return 0.3  # Default 30%
        
        # Simple bisection to find IV
        low, high = 0.001, 5.0
        tolerance = 0.001
        max_iterations = 100
        
        for _ in range(max_iterations):
            mid = (low + high) / 2
            theoretical_price = self._black_scholes(spot, strike, time_to_expiry, self.risk_free_rate, mid, option_type)
            
            if abs(theoretical_price - market_price) < tolerance:
                return mid
            elif theoretical_price < market_price:
                low = mid
            else:
                high = mid
        
        return mid
    
    def _black_scholes(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str
    ) -> float:
        """Calculate option price using Black-Scholes model"""
        d1 = (np.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)
        
        if option_type == 'call':
            price = spot * norm.cdf(d1) - strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)
        else:
            price = strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)
        
        return price
    
    def _calculate_max_pain(
        self,
        calls: List[OptionContract],
        puts: List[OptionContract],
        current_price: float
    ) -> Dict:
        """Calculate max pain price (price where option holders lose the most)"""
        strikes = sorted(set([c.strike for c in calls] + [p.strike for p in puts]))
        
        pain_values = []
        for strike in strikes:
            total_pain = 0
            
            # Calculate pain from calls
            for call in calls:
                if strike > call.strike:
                    total_pain += (strike - call.strike) * call.open_interest
            
            # Calculate pain from puts
            for put in puts:
                if strike < put.strike:
                    total_pain += (put.strike - strike) * put.open_interest
            
            pain_values.append((strike, total_pain))
        
        # Find strike with minimum pain
        max_pain_strike = min(pain_values, key=lambda x: x[1])
        
        return {
            "strike": max_pain_strike[0],
            "pain_value": max_pain_strike[1],
            "distance_from_spot": round(max_pain_strike[0] - current_price, 2),
            "all_pain_values": [{"strike": s, "pain": p} for s, p in pain_values[:10]]
        }
    
    def _find_support_resistance(
        self,
        calls: List[OptionContract],
        puts: List[OptionContract],
        current_price: float
    ) -> Dict:
        """Find support and resistance levels based on open interest"""
        # Sort by open interest
        call_strikes = sorted(calls, key=lambda x: x.open_interest, reverse=True)[:3]
        put_strikes = sorted(puts, key=lambda x: x.open_interest, reverse=True)[:3]
        
        resistance_levels = [
            {"strike": c.strike, "open_interest": c.open_interest, "type": "call_wall"}
            for c in call_strikes if c.strike >= current_price
        ]
        
        support_levels = [
            {"strike": p.strike, "open_interest": p.open_interest, "type": "put_wall"}
            for p in put_strikes if p.strike <= current_price
        ]
        
        return {
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "strongest_support": support_levels[0] if support_levels else None,
            "strongest_resistance": resistance_levels[0] if resistance_levels else None
        }
    
    def _calculate_avg_iv(self, calls: List[OptionContract], puts: List[OptionContract]) -> float:
        """Calculate average implied volatility"""
        all_ivs = [c.greeks.implied_volatility for c in calls if c.greeks] + [p.greeks.implied_volatility for p in puts if p.greeks]
        return round(np.mean(all_ivs), 4) if all_ivs else 0.3
    
    def _get_current_price(self) -> float:
        """Get current stock price"""
        try:
            data = self.ticker.history(period="1d")
            return round(data['Close'].iloc[-1], 2)
        except:
            return 0.0
    
    def _contract_to_dict(self, contract: OptionContract) -> Dict:
        """Convert OptionContract to dictionary"""
        return {
            "strike": contract.strike,
            "last_price": contract.last_price,
            "bid": contract.bid,
            "ask": contract.ask,
            "volume": contract.volume,
            "open_interest": contract.open_interest,
            "intrinsic_value": contract.intrinsic_value,
            "time_value": contract.time_value,
            "moneyness": contract.moneyness,
            "greeks": {
                "delta": contract.greeks.delta,
                "gamma": contract.greeks.gamma,
                "theta": contract.greeks.theta,
                "vega": contract.greeks.vega,
                "rho": contract.greeks.rho,
                "implied_volatility": contract.greeks.implied_volatility
            } if contract.greeks else None
        }
    
    def get_expiry_dates(self) -> List[str]:
        """Get available options expiry dates"""
        try:
            return list(self.ticker.options)
        except:
            return []
    
    def get_recommendations(self, expiry_date: Optional[str] = None) -> Dict:
        """Get options trading recommendations based on analysis"""
        chain = self.get_options_chain(expiry_date)
        
        if "error" in chain:
            return chain
        
        current_price = chain["current_price"]
        recommendations = []
        
        # Analyze put-call ratio
        pcr = chain["summary"]["put_call_ratio"]
        if pcr > 1.5:
            recommendations.append({
                "type": "SENTIMENT",
                "signal": "BEARISH",
                "reason": f"High Put-Call Ratio ({pcr}) indicates bearish sentiment",
                "strategy": "Consider protective puts or bear spreads"
            })
        elif pcr < 0.7:
            recommendations.append({
                "type": "SENTIMENT",
                "signal": "BULLISH",
                "reason": f"Low Put-Call Ratio ({pcr}) indicates bullish sentiment",
                "strategy": "Consider covered calls or bull spreads"
            })
        
        # Check max pain
        max_pain = chain["summary"]["max_pain"]
        if max_pain:
            distance = max_pain["distance_from_spot"]
            if abs(distance) > current_price * 0.05:  # More than 5% away
                direction = "up" if distance > 0 else "down"
                recommendations.append({
                    "type": "MAX_PAIN",
                    "signal": direction.upper(),
                    "reason": f"Price is {abs(distance):.2f} away from max pain at {max_pain['strike']}",
                    "strategy": f"Price may gravitate towards {max_pain['strike']}"
                })
        
        # Find unusual volume
        calls = chain["calls"]
        puts = chain["puts"]
        
        high_volume_calls = [c for c in calls if c.volume > c.open_interest * 0.5]
        high_volume_puts = [p for p in puts if p.volume > p.open_interest * 0.5]
        
        if high_volume_calls:
            recommendations.append({
                "type": "UNUSUAL_ACTIVITY",
                "signal": "CALL_VOLUME",
                "reason": f"Unusual call volume detected in {len(high_volume_calls)} strikes",
                "strikes": [c.strike for c in high_volume_calls[:3]]
            })
        
        if high_volume_puts:
            recommendations.append({
                "type": "UNUSUAL_ACTIVITY",
                "signal": "PUT_VOLUME",
                "reason": f"Unusual put volume detected in {len(high_volume_puts)} strikes",
                "strikes": [p.strike for p in high_volume_puts[:3]]
            })
        
        return {
            "symbol": self.symbol,
            "current_price": current_price,
            "recommendations": recommendations,
            "summary_metrics": chain["summary"],
            "support_resistance": chain["support_resistance"]
        }
