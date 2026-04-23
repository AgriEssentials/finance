"""
Enhanced Multi-Layer Caching and Rate Limiting Module
Provides Redis + In-Memory caching for maximum performance
"""

import redis
import json
import pickle
import hashlib
import os
import time
import threading
from typing import Optional, Any, Dict, List, Callable
from datetime import datetime, timedelta
from functools import wraps
from fastapi import HTTPException, Request

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class InMemoryCache:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._cache.items() if v['expiry'] < now]
            for k in expired:
                del self._cache[k]
    
    def _evict_if_needed(self):
        """Evict oldest entries if cache is full"""
        with self._lock:
            if len(self._cache) >= self._max_size:
                # Remove oldest 10% of entries
                sorted_items = sorted(self._cache.items(), key=lambda x: x[1]['accessed'])
                to_remove = int(self._max_size * 0.1)
                for k, _ in sorted_items[:to_remove]:
                    del self._cache[k]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry['expiry'] > time.time():
                    entry['accessed'] = time.time()
                    self._hits += 1
                    return entry['value']
                else:
                    del self._cache[key]
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in cache with TTL (seconds)"""
        self._cleanup_expired()
        self._evict_if_needed()
        
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expiry': time.time() + ttl,
                'accessed': time.time()
            }
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
        return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 3)
            }


class MultiLayerCache:
    """Multi-layer caching manager combining Redis and In-Memory caching"""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.memory_cache = InMemoryCache(max_size=2000)
        self.redis_client = None
        self.redis_binary = None
        self._connected = False
        
        # Try to connect to Redis
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            self.redis_binary = redis.from_url(redis_url, decode_responses=False, socket_connect_timeout=2)
            self.redis_client.ping()
            self._connected = True
            print("[CACHE] Redis connected successfully")
        except Exception as e:
            print(f"[CACHE] Redis not available, using in-memory cache only: {e}")
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
            'news': 300,               # 5 minutes for news
            'market_scanner': 60,        # 1 minute for scanner data
            'user_session': 1800,        # 30 minutes for sessions
            'api_response': 60,        # 1 minute for API responses
            'market_indices': 120,      # 2 minutes for market indices
            'sparklines': 300,          # 5 minutes for sparkline data
            'landing_data': 60,          # 1 minute for landing page data
        }
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key"""
        key = f"{prefix}:{identifier}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._connected and self.redis_client is not None
    
    def get(self, key: str, use_memory: bool = True) -> Optional[Any]:
        """
        Get value from cache (memory first, then Redis)
        
        Args:
            key: Cache key
            use_memory: Whether to check memory cache first
        
        Returns:
            Cached value or None
        """
        # Check memory cache first (faster)
        if use_memory:
            value = self.memory_cache.get(key)
            if value is not None:
                return value
        
        # Check Redis
        if not self.is_connected():
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                result = json.loads(value)
                # Populate memory cache for faster future access
                if use_memory:
                    ttl = self.redis_client.ttl(key)
                    if ttl > 0:
                        self.memory_cache.set(key, result, min(ttl, 300))
                return result
            return None
        except Exception:
            return None
    
    def get_binary(self, key: str, use_memory: bool = True) -> Optional[Any]:
        """Get binary data from cache"""
        # Check memory cache first
        if use_memory:
            value = self.memory_cache.get(key)
            if value is not None:
                return value
        
        if not self.is_connected():
            return None
        
        try:
            value = self.redis_binary.get(key)
            if value:
                result = pickle.loads(value)
                # Populate memory cache
                if use_memory:
                    ttl = self.redis_binary.ttl(key)
                    if ttl > 0:
                        self.memory_cache.set(key, result, min(ttl, 300))
                return result
            return None
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            use_memory: bool = True, memory_ttl: Optional[int] = None) -> bool:
        """
        Set value in both memory and Redis cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Redis TTL in seconds
            use_memory: Whether to also cache in memory
            memory_ttl: Memory cache TTL (defaults to min(ttl, 300))
        """
        success = True
        
        # Clean value before caching (handle NaN, Infinity)
        cleaned_value = self._clean_for_json(value)
        
        # Set in memory cache
        if use_memory:
            mem_ttl = memory_ttl or min(ttl or 60, 300)
            self.memory_cache.set(key, cleaned_value, mem_ttl)
        
        # Set in Redis
        if self.is_connected():
            try:
                serialized = json.dumps(cleaned_value, default=self._json_serializer)
                if ttl:
                    self.redis_client.setex(key, ttl, serialized)
                else:
                    self.redis_client.set(key, serialized)
            except Exception as e:
                print(f"[CACHE] Error serializing data for key {key}: {e}")
                success = False
        
        return success
    
    def _clean_for_json(self, obj: Any) -> Any:
        """Clean object for JSON serialization (remove NaN, Infinity)"""
        import math
        
        if isinstance(obj, dict):
            return {k: self._clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_for_json(item) for item in obj]
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif isinstance(obj, (int, str, bool, type(None))):
            return obj
        else:
            # Convert other types to string
            return str(obj)
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for special types"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, (int, float)):
            import math
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        return str(obj)
    
    def set_binary(self, key: str, value: Any, ttl: Optional[int] = None,
                   use_memory: bool = True, memory_ttl: Optional[int] = None) -> bool:
        """Set binary data in cache"""
        success = True
        
        # Set in memory cache
        if use_memory:
            mem_ttl = memory_ttl or min(ttl or 60, 300)
            self.memory_cache.set(key, value, mem_ttl)
        
        # Set in Redis
        if self.is_connected():
            try:
                serialized = pickle.dumps(value)
                if ttl:
                    self.redis_binary.setex(key, ttl, serialized)
                else:
                    self.redis_binary.set(key, serialized)
            except Exception:
                success = False
        
        return success
    
    def delete(self, key: str) -> bool:
        """Delete key from all cache layers"""
        self.memory_cache.delete(key)
        
        if self.is_connected():
            try:
                self.redis_client.delete(key)
                return True
            except Exception:
                return False
        return True
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern from Redis"""
        deleted = 0
        
        # Clear memory cache entirely for simplicity
        if '*' in pattern or '?' in pattern:
            self.memory_cache.clear()
        
        if self.is_connected():
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
            except Exception as e:
                print(f"Cache delete pattern error: {e}")
        
        return deleted
    
    def exists(self, key: str) -> bool:
        """Check if key exists in any cache layer"""
        if self.memory_cache.get(key) is not None:
            return True
        
        if self.is_connected():
            try:
                return self.redis_client.exists(key) > 0
            except Exception:
                return False
        return False
    
    # Specialized cache methods for stock data
    
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
    
    def get_market_indices(self) -> Optional[Dict]:
        """Get cached market indices data"""
        key = self._generate_key("market", "indices")
        return self.get(key)
    
    def set_market_indices(self, data: Dict) -> bool:
        """Cache market indices data"""
        key = self._generate_key("market", "indices")
        return self.set(key, data, self.ttls['market_indices'])
    
    def get_sparklines(self) -> Optional[Dict]:
        """Get cached sparkline data"""
        key = self._generate_key("market", "sparklines")
        return self.get(key)
    
    def set_sparklines(self, data: Dict) -> bool:
        """Cache sparkline data"""
        key = self._generate_key("market", "sparklines")
        return self.set(key, data, self.ttls['sparklines'])
    
    def get_landing_data(self) -> Optional[Dict]:
        """Get cached landing page data"""
        key = self._generate_key("market", "landing")
        return self.get(key)
    
    def set_landing_data(self, data: Dict) -> bool:
        """Cache landing page data"""
        key = self._generate_key("market", "landing")
        return self.set(key, data, self.ttls['landing_data'])
    
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
        except Exception:
            return 0
    
    def get_counter(self, key: str) -> int:
        """Get counter value"""
        if not self.is_connected():
            return 0
        try:
            value = self.redis_client.get(key)
            return int(value) if value else 0
        except Exception:
            return 0
    
    def set_counter_expiry(self, key: str, seconds: int):
        """Set expiry for counter"""
        if not self.is_connected():
            return
        try:
            self.redis_client.expire(key, seconds)
        except Exception:
            pass
    
    def get_cache_stats(self) -> Dict:
        """Get comprehensive cache statistics"""
        stats = {
            'memory_cache': self.memory_cache.get_stats(),
            'redis': {'status': 'disconnected'},
            'ttls': self.ttls
        }
        
        if self.is_connected():
            try:
                info = self.redis_client.info()
                stats['redis'] = {
                    'status': 'connected',
                    'used_memory': info.get("used_memory_human", "N/A"),
                    'connected_clients': info.get("connected_clients", 0),
                    'total_keys': self.redis_client.dbsize(),
                    'hit_rate': info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)),
                    'uptime': info.get("uptime_in_seconds", 0)
                }
            except Exception as e:
                stats['redis'] = {'status': 'error', 'error': str(e)}
        
        return stats


# Global cache instance
cache = MultiLayerCache()


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


def get_rate_limit_key(request: Request, user_id: Optional[str] = None) -> str:
    """Generate rate limit key based on user or IP"""
    if user_id:
        return f"rate_limit:user:{user_id}"
    
    # Use X-Forwarded-For if behind proxy, otherwise use client host
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    return f"rate_limit:ip:{client_ip}"


def check_rate_limit(key: str, limit: int, window: int) -> tuple[bool, int, int]:
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
    except Exception:
        # If Redis is unavailable, allow the request
        return True, limit, window


def rate_limit(requests: int = 100, window: int = 60, key_func = get_rate_limit_key):
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
def cached(ttl: Optional[int] = None, key_prefix: str = "func", 
           use_memory: bool = True, skip_args: Optional[List[int]] = None):
    """
    Decorator to cache function results
    
    Args:
        ttl: Cache TTL in seconds
        key_prefix: Prefix for cache key
        use_memory: Whether to use memory cache
        skip_args: Argument indices to skip when generating cache key (e.g., for request objects)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_args = args
            if skip_args:
                cache_args = tuple(arg for i, arg in enumerate(args) if i not in skip_args)
            
            # Convert kwargs to sorted items, excluding common non-cacheable parameters
            skip_kwargs = {'request', 'current_user', 'db', 'background_tasks'}
            cache_kwargs = {k: v for k, v in sorted(kwargs.items()) if k not in skip_kwargs}
            
            cache_key = f"{key_prefix}:{func.__name__}:{str(cache_args)}:{str(cache_kwargs.items())}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache.get(cache_key, use_memory=use_memory)
            if cached_result is not None:
                # Add cache hit header if response object
                result = cached_result
                if isinstance(result, dict):
                    result['_cache_hit'] = True
                return result
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl or cache.ttls['api_response'], use_memory=use_memory)
            
            # Add cache miss indicator
            if isinstance(result, dict):
                result['_cache_hit'] = False
            
            return result
        return wrapper
    return decorator


# Rate Limiting Dependencies for FastAPI
async def get_rate_limit_key_dependency(request: Request, user_id: Optional[str] = None) -> str:
    """Generate rate limit key based on user or IP"""
    if user_id:
        return f"rate_limit:user:{user_id}"
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    return f"rate_limit:ip:{client_ip}"


# Rate limiter dependency functions
async def rate_limit_default(request: Request):
    """Rate limit for default endpoints: 100/minute"""
    try:
        key = await get_rate_limit_key_dependency(request)
        allowed, remaining, reset_time = check_rate_limit(key, 100, 60)
        if not allowed:
            raise RateLimitExceeded(f"Rate limit exceeded. Try again in {reset_time} seconds")
        request.state.rate_limit_remaining = remaining
    except RateLimitExceeded:
        raise
    except Exception:
        pass


async def rate_limit_analyze(request: Request):
    """Rate limit for analyze endpoints: 30/minute"""
    try:
        key = await get_rate_limit_key_dependency(request)
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
        key = await get_rate_limit_key_dependency(request)
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
        key = await get_rate_limit_key_dependency(request)
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
        key = await get_rate_limit_key_dependency(request)
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
        key = await get_rate_limit_key_dependency(request)
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
        key = await get_rate_limit_key_dependency(request)
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
