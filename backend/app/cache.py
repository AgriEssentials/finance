"""
Redis Caching and Rate Limiting Module
"""

import redis
import json
import pickle
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import os
from fastapi import HTTPException, Request, Depends


# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class RedisCache:
    """Redis caching manager for stock data and analysis results"""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_client = None
        self.redis_binary = None
        self._connected = False
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            self.redis_binary = redis.from_url(redis_url, decode_responses=False, socket_connect_timeout=2)
            # Test connection
            self.redis_client.ping()
            self._connected = True
        except Exception as e:
            print(f"[WARNING] Redis not available (caching disabled): {e}")
            self.redis_client = None
            self.redis_binary = None
            self._connected = False
        
        # Cache TTLs in seconds
        self.ttls = {
            'stock_price': 60,           # 1 minute for live prices
            'stock_data': 300,           # 5 minutes for historical data
            'technical_indicators': 300, # 5 minutes for indicators
            'sentiment': 600,            # 10 minutes for sentiment
            'fundamental': 3600,         # 1 hour for fundamentals
            'analysis': 180,             # 3 minutes for analysis
            'news': 300,                 # 5 minutes for news
            'market_scanner': 60,        # 1 minute for scanner data
            'user_session': 1800,        # 30 minutes for sessions
            'api_response': 60,          # 1 minute for API responses
        }
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key"""
        key = f"{prefix}:{identifier}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._connected and self.redis_client is not None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.is_connected():
            return None
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            # Silently fail - cache is optional
            return None
    
    def get_binary(self, key: str) -> Optional[Any]:
        """Get binary data from cache (for complex objects)"""
        if not self.is_connected():
            return None
        try:
            value = self.redis_binary.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            # Silently fail - cache is optional
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.is_connected():
            return False
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                self.redis_client.setex(key, ttl, serialized)
            else:
                self.redis_client.set(key, serialized)
            return True
        except Exception as e:
            # Silently fail - cache is optional
            return False
    
    def set_binary(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set binary data in cache"""
        if not self.is_connected():
            return False
        try:
            serialized = pickle.dumps(value)
            if ttl:
                self.redis_binary.setex(key, ttl, serialized)
            else:
                self.redis_binary.set(key, serialized)
            return True
        except Exception as e:
            # Silently fail - cache is optional
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.is_connected():
            return False
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.is_connected():
            return 0
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.is_connected():
            return False
        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False
    
    def get_stock_price(self, symbol: str) -> Optional[Dict]:
        """Get cached stock price"""
        key = self._generate_key("price", symbol)
        return self.get(key)
    
    def set_stock_price(self, symbol: str, data: Dict) -> bool:
        """Cache stock price"""
        key = self._generate_key("price", symbol)
        return self.set(key, data, self.ttls['stock_price'])
    
    def get_stock_data(self, symbol: str, period: str, interval: str) -> Optional[Any]:
        """Get cached stock historical data"""
        identifier = f"{symbol}:{period}:{interval}"
        key = self._generate_key("data", identifier)
        return self.get_binary(key)
    
    def set_stock_data(self, symbol: str, period: str, interval: str, data: Any) -> bool:
        """Cache stock historical data"""
        identifier = f"{symbol}:{period}:{interval}"
        key = self._generate_key("data", identifier)
        return self.set_binary(key, data, self.ttls['stock_data'])
    
    def get_technical_indicators(self, symbol: str, mode: str) -> Optional[Dict]:
        """Get cached technical indicators"""
        identifier = f"{symbol}:{mode}"
        key = self._generate_key("indicators", identifier)
        return self.get(key)
    
    def set_technical_indicators(self, symbol: str, mode: str, data: Dict) -> bool:
        """Cache technical indicators"""
        identifier = f"{symbol}:{mode}"
        key = self._generate_key("indicators", identifier)
        return self.set(key, data, self.ttls['technical_indicators'])
    
    def get_sentiment(self, symbol: str) -> Optional[Dict]:
        """Get cached sentiment data"""
        key = self._generate_key("sentiment", symbol)
        return self.get(key)
    
    def set_sentiment(self, symbol: str, data: Dict) -> bool:
        """Cache sentiment data"""
        key = self._generate_key("sentiment", symbol)
        return self.set(key, data, self.ttls['sentiment'])
    
    def get_fundamental(self, symbol: str) -> Optional[Dict]:
        """Get cached fundamental data"""
        key = self._generate_key("fundamental", symbol)
        return self.get(key)
    
    def set_fundamental(self, symbol: str, data: Dict) -> bool:
        """Cache fundamental data"""
        key = self._generate_key("fundamental", symbol)
        return self.set(key, data, self.ttls['fundamental'])
    
    def get_analysis(self, symbol: str, mode: str) -> Optional[Dict]:
        """Get cached analysis result"""
        identifier = f"{symbol}:{mode}"
        key = self._generate_key("analysis", identifier)
        return self.get(key)
    
    def set_analysis(self, symbol: str, mode: str, data: Dict) -> bool:
        """Cache analysis result"""
        identifier = f"{symbol}:{mode}"
        key = self._generate_key("analysis", identifier)
        return self.set(key, data, self.ttls['analysis'])
    
    def invalidate_symbol(self, symbol: str) -> int:
        """Invalidate all cached data for a symbol"""
        patterns = [
            f"*price*{symbol}*",
            f"*data*{symbol}*",
            f"*indicators*{symbol}*",
            f"*sentiment*{symbol}*",
            f"*fundamental*{symbol}*",
            f"*analysis*{symbol}*"
        ]
        
        deleted = 0
        for pattern in patterns:
            deleted += self.delete_pattern(pattern)
        
        return deleted
    
    def cache_api_response(self, endpoint: str, params: Dict, response: Dict, ttl: int = 60) -> bool:
        """Cache API response"""
        identifier = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        key = self._generate_key("api", identifier)
        return self.set(key, response, ttl)
    
    def get_cached_api_response(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Get cached API response"""
        identifier = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        key = self._generate_key("api", identifier)
        return self.get(key)
    
    def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        if not self.is_connected():
            return 0
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            return 0
    
    def get_counter(self, key: str) -> int:
        """Get counter value"""
        if not self.is_connected():
            return 0
        try:
            value = self.redis_client.get(key)
            return int(value) if value else 0
        except Exception as e:
            return 0
    
    def set_counter_expiry(self, key: str, seconds: int):
        """Set expiry for counter"""
        if not self.is_connected():
            return
        try:
            self.redis_client.expire(key, seconds)
        except Exception as e:
            pass
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.is_connected():
            return {"status": "disconnected"}
        try:
            info = self.redis_client.info()
            return {
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": self.redis_client.dbsize(),
                "hit_rate": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)),
                "uptime": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

# Global cache instance
cache = RedisCache()

# Rate Limiting Configuration
RATE_LIMITS = {
    "default": "100/minute",
    "analyze": "30/minute",
    "professional_analyze": "10/minute",
    "scanner": "60/minute",
    "backtest": "5/minute",
    "train": "3/minute",
    "auth": "10/minute",
}

class RateLimitExceeded(HTTPException):
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=429, detail=detail)

def get_rate_limit_key(request: Request, user_id: Optional[int] = None) -> str:
    """Generate rate limit key based on user or IP"""
    if user_id:
        return f"rate_limit:user:{user_id}"
    
    # Use X-Forwarded-For if behind proxy, otherwise use client host
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    return f"rate_limit:ip:{client_ip}"

def check_rate_limit(
    key: str,
    limit: int,
    window: int,
) -> tuple[bool, int, int]:
    """
    Check if request is within rate limit
    Returns: (allowed, remaining, reset_time)
    """
    # If Redis is not connected, allow all requests
    if not cache.is_connected():
        return True, limit, window
    
    try:
        current = cache.get_counter(key)

        if current == 0:
            # First request, set expiry
            cache.set_counter_expiry(key, window)

        if current >= limit:
            # Rate limit exceeded
            ttl = cache.redis_client.ttl(key) if cache.is_connected() else window
            return False, 0, ttl

        # Increment counter
        new_count = cache.increment_counter(key)
        remaining = max(0, limit - new_count)
        ttl = cache.redis_client.ttl(key) if cache.is_connected() else window

        return True, remaining, ttl
    except Exception as e:
        # If Redis is unavailable, allow the request
        # This prevents total outage when cache is down
        return True, limit, window

def rate_limit(
    requests: int = 100,
    window: int = 60,
    key_func = get_rate_limit_key
):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                # Get user_id if available
                user_id = None
                if "current_user" in kwargs:
                    user_id = kwargs["current_user"].id
                
                key = key_func(request, user_id)
                allowed, remaining, reset_time = check_rate_limit(key, requests, window)
                
                if not allowed:
                    raise RateLimitExceeded(
                        f"Rate limit exceeded. Try again in {reset_time} seconds"
                    )
                
                # Add rate limit headers to response
                response = await func(*args, **kwargs)
                if hasattr(response, "headers"):
                    response.headers["X-RateLimit-Limit"] = str(requests)
                    response.headers["X-RateLimit-Remaining"] = str(remaining)
                    response.headers["X-RateLimit-Reset"] = str(reset_time)
                
                return response
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Cached decorator for function results
def cached(ttl: Optional[int] = None, key_prefix: str = "func"):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl or cache.ttls['api_response'])
            
            return result
        return wrapper
    return decorator

# Rate Limiting Dependencies for FastAPI
from fastapi import Request, Depends

async def get_rate_limit_key(request: Request, user_id: Optional[int] = None) -> str:
    """Generate rate limit key based on user or IP"""
    if user_id:
        return f"rate_limit:user:{user_id}"
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    return f"rate_limit:ip:{client_ip}"

# Rate limiter instances
limiter_default = type('obj', (object,), {'requests': 100, 'window': 60})()
limiter_analyze = type('obj', (object,), {'requests': 30, 'window': 60})()
limiter_professional = type('obj', (object,), {'requests': 10, 'window': 60})()
limiter_scanner = type('obj', (object,), {'requests': 60, 'window': 60})()
limiter_backtest = type('obj', (object,), {'requests': 5, 'window': 60})()
limiter_train = type('obj', (object,), {'requests': 3, 'window': 60})()
limiter_auth = type('obj', (object,), {'requests': 10, 'window': 60})()

async def rate_limit_default(request: Request):
    """Rate limit for default endpoints: 100/minute"""
    try:
        key = await get_rate_limit_key(request)
        allowed, remaining, reset_time = check_rate_limit(key, 100, 60)
        if not allowed:
            raise RateLimitExceeded(f"Rate limit exceeded. Try again in {reset_time} seconds")
        request.state.rate_limit_remaining = remaining
    except RateLimitExceeded:
        raise
    except Exception:
        # If rate limiting fails, allow the request
        pass

async def rate_limit_analyze(request: Request):
    """Rate limit for analyze endpoints: 30/minute"""
    try:
        key = await get_rate_limit_key(request)
        allowed, remaining, reset_time = check_rate_limit(key, 30, 60)
        if not allowed:
            raise RateLimitExceeded(f"Rate limit exceeded. Try again in {reset_time} seconds")
        request.state.rate_limit_remaining = remaining
    except RateLimitExceeded:
        raise
    except Exception:
        pass

async def rate_limit_professional(request: Request):
    """Rate limit for professional endpoints: 10/minute"""
    try:
        key = await get_rate_limit_key(request)
        allowed, remaining, reset_time = check_rate_limit(key, 10, 60)
        if not allowed:
            raise RateLimitExceeded(f"Rate limit exceeded. Try again in {reset_time} seconds")
        request.state.rate_limit_remaining = remaining
    except RateLimitExceeded:
        raise
    except Exception:
        pass

async def rate_limit_scanner(request: Request):
    """Rate limit for scanner endpoints: 60/minute"""
    try:
        key = await get_rate_limit_key(request)
        allowed, remaining, reset_time = check_rate_limit(key, 60, 60)
        if not allowed:
            raise RateLimitExceeded(f"Rate limit exceeded. Try again in {reset_time} seconds")
        request.state.rate_limit_remaining = remaining
    except RateLimitExceeded:
        raise
    except Exception:
        pass

async def rate_limit_backtest(request: Request):
    """Rate limit for backtest endpoints: 5/minute"""
    try:
        key = await get_rate_limit_key(request)
        allowed, remaining, reset_time = check_rate_limit(key, 5, 60)
        if not allowed:
            raise RateLimitExceeded(f"Rate limit exceeded. Try again in {reset_time} seconds")
        request.state.rate_limit_remaining = remaining
    except RateLimitExceeded:
        raise
    except Exception:
        pass

async def rate_limit_train(request: Request):
    """Rate limit for train endpoints: 3/minute"""
    try:
        key = await get_rate_limit_key(request)
        allowed, remaining, reset_time = check_rate_limit(key, 3, 60)
        if not allowed:
            raise RateLimitExceeded(f"Rate limit exceeded. Try again in {reset_time} seconds")
        request.state.rate_limit_remaining = remaining
    except RateLimitExceeded:
        raise
    except Exception:
        pass

async def rate_limit_auth(request: Request):
    """Rate limit for auth endpoints: 10/minute"""
    try:
        key = await get_rate_limit_key(request)
        allowed, remaining, reset_time = check_rate_limit(key, 10, 60)
        if not allowed:
            raise RateLimitExceeded(f"Rate limit exceeded. Try again in {reset_time} seconds")
        request.state.rate_limit_remaining = remaining
    except RateLimitExceeded:
        raise
    except Exception:
        pass

# Export rate limit functions (to be used with Depends() in routes)
RateLimitDefault = rate_limit_default
RateLimitAnalyze = rate_limit_analyze
RateLimitProfessional = rate_limit_professional
RateLimitScanner = rate_limit_scanner
RateLimitBacktest = rate_limit_backtest
RateLimitTrain = rate_limit_train
RateLimitAuth = rate_limit_auth
