"""
Real-time Market Data WebSocket Manager
Provides live price streaming and market updates
"""

import asyncio
import websockets
import json
import yfinance as yf
from typing import Dict, Set, Callable, Any
from datetime import datetime
import threading
import time


class MarketDataStreamer:
    """Real-time market data streaming service"""
    
    def __init__(self):
        self.connections: Set[websockets.WebSocketServerProtocol] = set()
        self.subscriptions: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.price_cache: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.update_interval = 5  # seconds
        
    async def register(self, websocket: websockets.WebSocketServerProtocol):
        """Register new WebSocket connection"""
        self.connections.add(websocket)
        print(f"Client connected. Total connections: {len(self.connections)}")
        
    async def unregister(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister WebSocket connection"""
        self.connections.discard(websocket)
        # Remove from all subscriptions
        for symbol in self.subscriptions:
            self.subscriptions[symbol].discard(websocket)
        print(f"Client disconnected. Total connections: {len(self.connections)}")
        
    async def subscribe(self, websocket: websockets.WebSocketServerProtocol, symbols: list):
        """Subscribe to symbols for real-time updates"""
        for symbol in symbols:
            if symbol not in self.subscriptions:
                self.subscriptions[symbol] = set()
            self.subscriptions[symbol].add(websocket)
            
        # Send confirmation
        await websocket.send(json.dumps({
            "type": "subscription_confirmed",
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        }))
        
    async def broadcast_price_update(self, symbol: str, data: Dict[str, Any]):
        """Broadcast price update to all subscribed clients"""
        if symbol not in self.subscriptions:
            return
            
        message = json.dumps({
            "type": "price_update",
            "symbol": symbol,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
        # Send to all subscribers
        disconnected = set()
        for websocket in self.subscriptions[symbol]:
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
                
        # Clean up disconnected clients
        for websocket in disconnected:
            await self.unregister(websocket)
            
    def fetch_live_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch live market data for symbol"""
        try:
            ticker = yf.Ticker(symbol)
            # Get real-time data
            data = ticker.history(period="1d", interval="1m").tail(1)
            
            if data.empty:
                return None
                
            current = data.iloc[-1]
            
            return {
                "price": round(current['Close'], 2),
                "change": round(current['Close'] - current['Open'], 2),
                "change_percent": round(((current['Close'] - current['Open']) / current['Open']) * 100, 2),
                "volume": int(current['Volume']),
                "high": round(current['High'], 2),
                "low": round(current['Low'], 2),
                "open": round(current['Open'], 2),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
            
    async def data_collection_loop(self):
        """Continuously collect and broadcast data"""
        while self.running:
            for symbol in list(self.subscriptions.keys()):
                if not self.subscriptions[symbol]:
                    continue
                    
                data = self.fetch_live_data(symbol)
                if data:
                    self.price_cache[symbol] = data
                    await self.broadcast_price_update(symbol, data)
                    
            await asyncio.sleep(self.update_interval)
            
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    action = data.get('action')
                    
                    if action == 'subscribe':
                        symbols = data.get('symbols', [])
                        await self.subscribe(websocket, symbols)
                    elif action == 'unsubscribe':
                        symbols = data.get('symbols', [])
                        for symbol in symbols:
                            if symbol in self.subscriptions:
                                self.subscriptions[symbol].discard(websocket)
                    elif action == 'get_data':
                        symbol = data.get('symbol')
                        if symbol in self.price_cache:
                            await websocket.send(json.dumps({
                                "type": "cached_data",
                                "symbol": symbol,
                                "data": self.price_cache[symbol]
                            }))
                            
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
            
    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Start WebSocket server"""
        self.running = True
        
        # Start data collection in background
        asyncio.create_task(self.data_collection_loop())
        
        # Start WebSocket server
        async with websockets.serve(self.handle_client, host, port):
            print(f"WebSocket server started on ws://{host}:{port}")
            await asyncio.Future()  # Run forever
            
# Global streamer instance
market_streamer = MarketDataStreamer()
