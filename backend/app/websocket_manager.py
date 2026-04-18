"""
WebSocket Manager for Real-time Stock Data Streaming
Industry-grade real-time market data streaming
"""

import asyncio
import json
from typing import Dict, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
import yfinance as yf
from datetime import datetime
import threading
import time
import random
import numpy as np

from app.cache import cache
from app.realtime import rt_data

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        # Active connections grouped by symbol
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # User subscriptions: user_id -> set of symbols
        self.user_subscriptions: Dict[int, Set[str]] = {}
        # Connection metadata: websocket -> {user_id, subscribed_symbols}
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        
    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "subscribed_symbols": set(),
            "connected_at": datetime.utcnow().isoformat()
        }
        
        # Update user subscriptions tracking
        if user_id:
            if user_id not in self.user_subscriptions:
                self.user_subscriptions[user_id] = set()
    
    def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            user_id = metadata.get("user_id")
            subscribed_symbols = metadata.get("subscribed_symbols", set())
            
            # Remove from symbol subscriptions
            for symbol in subscribed_symbols:
                if symbol in self.active_connections:
                    if websocket in self.active_connections[symbol]:
                        self.active_connections[symbol].remove(websocket)
                    # Clean up empty symbol lists
                    if not self.active_connections[symbol]:
                        del self.active_connections[symbol]
            
            # Update user subscriptions
            if user_id and user_id in self.user_subscriptions:
                self.user_subscriptions[user_id].difference_update(subscribed_symbols)
            
            # Clean up metadata
            del self.connection_metadata[websocket]
    
    async def subscribe(self, websocket: WebSocket, symbols: List[str]):
        """Subscribe WebSocket to symbols"""
        if websocket not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[websocket]
        user_id = metadata.get("user_id")
        
        for symbol in symbols:
            symbol = symbol.upper()
            
            # Add to active connections for symbol
            if symbol not in self.active_connections:
                self.active_connections[symbol] = []
            if websocket not in self.active_connections[symbol]:
                self.active_connections[symbol].append(websocket)
            
            # Update metadata
            metadata["subscribed_symbols"].add(symbol)
            
            # Update user subscriptions
            if user_id:
                self.user_subscriptions[user_id].add(symbol)
        
        # Send confirmation
        await websocket.send_json({
            "type": "subscription_confirmed",
            "symbols": symbols,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def unsubscribe(self, websocket: WebSocket, symbols: List[str]):
        """Unsubscribe WebSocket from symbols"""
        if websocket not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[websocket]
        user_id = metadata.get("user_id")
        
        for symbol in symbols:
            symbol = symbol.upper()
            
            # Remove from active connections
            if symbol in self.active_connections:
                if websocket in self.active_connections[symbol]:
                    self.active_connections[symbol].remove(websocket)
                if not self.active_connections[symbol]:
                    del self.active_connections[symbol]
            
            # Update metadata
            metadata["subscribed_symbols"].discard(symbol)
            
            # Update user subscriptions
            if user_id and user_id in self.user_subscriptions:
                self.user_subscriptions[user_id].discard(symbol)
        
        # Send confirmation
        await websocket.send_json({
            "type": "unsubscription_confirmed",
            "symbols": symbols,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def broadcast_to_symbol(self, symbol: str, message: Dict):
        """Broadcast message to all connections subscribed to a symbol"""
        if symbol not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[symbol]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)
    
    def get_subscribed_symbols(self) -> Set[str]:
        """Get all symbols with active subscriptions"""
        return set(self.active_connections.keys())
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.connection_metadata)
    
    def get_symbol_subscriber_count(self, symbol: str) -> int:
        """Get number of subscribers for a symbol"""
        return len(self.active_connections.get(symbol, []))

# Global connection manager
manager = ConnectionManager()

class RealTimeDataStreamer:
    """Stream real-time stock data to WebSocket clients"""
    
    def __init__(self, update_interval: float = 5.0):
        self.update_interval = update_interval
        self.is_running = False
        self.stream_task = None
        self.price_cache: Dict[str, Dict] = {}
        
    async def start(self):
        """Start the data streaming loop"""
        if self.is_running:
            return
        
        self.is_running = True
        self.stream_task = asyncio.create_task(self._streaming_loop())
        print("Real-time data streamer started")
    
    async def stop(self):
        """Stop the data streaming loop"""
        self.is_running = False
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
        print("Real-time data streamer stopped")
    
    async def _streaming_loop(self):
        """Main streaming loop"""
        while self.is_running:
            try:
                await self._fetch_and_broadcast()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                print(f"Streaming error: {e}")
                await asyncio.sleep(1)
    
    async def _fetch_and_broadcast(self):
        """Fetch latest prices and broadcast to subscribers"""
        subscribed_symbols = manager.get_subscribed_symbols()
        
        if not subscribed_symbols:
            return
        
        # Fetch data for all subscribed symbols
        for symbol in subscribed_symbols:
            try:
                # Check cache first
                cached_data = cache.get_stock_price(symbol)
                
                if cached_data:
                    price_data = cached_data
                else:
                    # Fetch from yfinance
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period="1d", interval="1m")
                    
                    if data.empty:
                        continue
                    
                    latest = data.iloc[-1]
                    price_data = {
                        "symbol": symbol,
                        "price": round(latest["Close"], 2),
                        "change": round(latest["Close"] - latest["Open"], 2),
                        "change_percent": round(((latest["Close"] - latest["Open"]) / latest["Open"]) * 100, 2),
                        "volume": int(latest["Volume"]),
                        "high": round(latest["High"], 2),
                        "low": round(latest["Low"], 2),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Cache the price
                    cache.set_stock_price(symbol, price_data)
                
                # Calculate additional metrics
                if symbol in self.price_cache:
                    prev_price = self.price_cache[symbol].get("price", price_data["price"])
                    price_data["tick"] = "up" if price_data["price"] > prev_price else "down" if price_data["price"] < prev_price else "flat"
                
                self.price_cache[symbol] = price_data
                
                # Broadcast to subscribers
                await manager.broadcast_to_symbol(symbol, {
                    "type": "price_update",
                    "data": price_data
                })
                
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
    
    async def broadcast_market_event(self, event_type: str, data: Dict):
        """Broadcast market-wide events"""
        message = {
            "type": "market_event",
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all connections
        for websocket in list(manager.connection_metadata.keys()):
            try:
                await manager.send_personal_message(websocket, message)
            except Exception:
                pass
    
    async def broadcast_alert(self, symbol: str, alert_data: Dict):
        """Broadcast price alert to symbol subscribers"""
        message = {
            "type": "alert",
            "symbol": symbol,
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await manager.broadcast_to_symbol(symbol, message)

# Global streamer instance
streamer = RealTimeDataStreamer(update_interval=5.0)

# WebSocket message handlers
async def handle_websocket_message(websocket: WebSocket, message: Dict):
    """Handle incoming WebSocket messages"""
    msg_type = message.get("type")
    
    if msg_type == "subscribe":
        symbols = message.get("symbols", [])
        if symbols:
            await manager.subscribe(websocket, symbols)
    
    elif msg_type == "unsubscribe":
        symbols = message.get("symbols", [])
        if symbols:
            await manager.unsubscribe(websocket, symbols)
    
    elif msg_type == "get_price":
        symbol = message.get("symbol", "").upper()
        if symbol:
            ticker = yf.Ticker(symbol)
            try:
                data = ticker.history(period="1d", interval="1m")
                if not data.empty:
                    latest = data.iloc[-1]
                    await manager.send_personal_message(websocket, {
                        "type": "price_response",
                        "symbol": symbol,
                        "data": {
                            "price": round(latest["Close"], 2),
                            "change": round(latest["Close"] - data.iloc[0]["Open"], 2),
                            "change_percent": round(((latest["Close"] - data.iloc[0]["Open"]) / data.iloc[0]["Open"]) * 100, 2),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    })
            except Exception as e:
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": f"Failed to fetch price for {symbol}: {str(e)}"
                })
    
    elif msg_type == "ping":
        await manager.send_personal_message(websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif msg_type == "get_subscriptions":
        metadata = manager.connection_metadata.get(websocket, {})
        await manager.send_personal_message(websocket, {
            "type": "subscriptions",
            "symbols": list(metadata.get("subscribed_symbols", [])),
            "timestamp": datetime.utcnow().isoformat()
        })

# WebSocket endpoint handler
async def websocket_endpoint_handler(websocket: WebSocket, user_id: Optional[int] = None):
    """Main WebSocket connection handler"""
    await manager.connect(websocket, user_id)
    
    try:
        # Start streamer if not running
        if not streamer.is_running:
            await streamer.start()
        
        # Send welcome message
        await manager.send_personal_message(websocket, {
            "type": "connected",
            "message": "Connected to real-time stock data stream",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except json.JSONDecodeError:
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except WebSocketDisconnect:
                break
            except Exception as e:
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": str(e)
                })
    
    except WebSocketDisconnect:
        pass
    finally:
        # Unsubscribe from real-time data
        for symbol in list(rt_data.subscribers.keys()):
            rt_data.unsubscribe(symbol, websocket)
        
        manager.disconnect(websocket)
        
        # Stop streamer if no more connections
        if manager.get_connection_count() == 0:
            streamer.stop()


# Real-time high-frequency streaming endpoint
async def realtime_stream_endpoint(websocket: WebSocket):
    """
    Industry-grade real-time market data streaming
    100ms updates (10Hz) for live trading
    """
    await websocket.accept()
    
    client_id = id(websocket)
    print(f"[REALTIME] Client {client_id} connected")
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "Real-time market data stream active",
            "timestamp": datetime.utcnow().isoformat(),
            "updates_per_second": 10,
            "latency_target_ms": 50
        })
        
        subscribed_symbols = set()
        last_data_sent = {}
        
        # Create two tasks: one for receiving messages, one for sending data
        async def receive_messages():
            """Handle incoming messages from client"""
            nonlocal subscribed_symbols
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    msg_type = message.get('type')
                    
                    if msg_type == 'subscribe':
                        symbols = message.get('symbols', [])
                        for symbol in symbols:
                            symbol = symbol.upper()
                            rt_data.subscribe(symbol, websocket)
                            subscribed_symbols.add(symbol)
                            
                            # Send initial snapshot
                            snapshot = rt_data.get_latest_data(symbol)
                            if snapshot:
                                await websocket.send_json({
                                    "type": "snapshot",
                                    "symbol": symbol,
                                    "data": snapshot
                                })
                        
                        await websocket.send_json({
                            "type": "subscribed",
                            "symbols": list(subscribed_symbols),
                            "count": len(subscribed_symbols)
                        })
                    
                    elif msg_type == 'unsubscribe':
                        symbols = message.get('symbols', [])
                        for symbol in symbols:
                            rt_data.unsubscribe(symbol, websocket)
                            subscribed_symbols.discard(symbol)
                        
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "symbols": list(subscribed_symbols)
                        })
                    
                    elif msg_type == 'orderbook':
                        symbol = message.get('symbol', '').upper()
                        depth = message.get('depth', 10)
                        orderbook = rt_data.get_order_book(symbol, depth)
                        await websocket.send_json({
                            "type": "orderbook",
                            "symbol": symbol,
                            "data": orderbook
                        })
                    
                    elif msg_type == 'ping':
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"[REALTIME] Receive error for client {client_id}: {e}")
                    break
        
        async def send_realtime_data():
            """Send real-time data updates to client"""
            nonlocal last_data_sent
            while True:
                try:
                    # Send data for all subscribed symbols
                    for symbol in list(subscribed_symbols):
                        data = rt_data.get_latest_data(symbol)
                        if data:
                            # Only send if data changed
                            last_sent = last_data_sent.get(symbol, {})
                            if data.get('price') != last_sent.get('price') or \
                               data.get('volume') != last_sent.get('volume'):
                                
                                await websocket.send_json({
                                    "type": "tick",
                                    "symbol": symbol,
                                    "data": data
                                })
                                last_data_sent[symbol] = data.copy()
                    
                    # Send heartbeat every second
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # 100ms = 10Hz updates
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"[REALTIME] Send error for client {client_id}: {e}")
                    break
        
        # Run both tasks concurrently
        await asyncio.gather(
            receive_messages(),
            send_realtime_data(),
            return_exceptions=True
        )
                
    except WebSocketDisconnect:
        print(f"[REALTIME] Client {client_id} disconnected")
    except Exception as e:
        print(f"[REALTIME] Error for client {client_id}: {e}")
    finally:
        # Clean up subscriptions
        for symbol in list(subscribed_symbols):
            rt_data.unsubscribe(symbol, websocket)
        print(f"[REALTIME] Client {client_id} cleanup complete")
