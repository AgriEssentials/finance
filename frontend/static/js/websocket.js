/**
 * WebSocket Client - AI Stock Analysis Pro
 * Handles real-time WebSocket connections
 */

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 5000;
        this.isConnected = false;
        this.subscribers = new Map();
    }

    connect() {
        // Check if WebSocket is available
        if (!window.WebSocket) {
            console.warn('WebSocket not supported in this browser');
            return;
        }

        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.onStatusChange('connected');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.onStatusChange('disconnected');
                
                // Attempt to reconnect
                setTimeout(() => this.connect(), this.reconnectInterval);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.onStatusChange('error');
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }

    handleMessage(data) {
        // Route messages to subscribers
        const type = data.type;
        if (this.subscribers.has(type)) {
            this.subscribers.get(type).forEach(callback => callback(data));
        }
    }

    subscribe(type, callback) {
        if (!this.subscribers.has(type)) {
            this.subscribers.set(type, []);
        }
        this.subscribers.get(type).push(callback);
    }

    unsubscribe(type, callback) {
        if (this.subscribers.has(type)) {
            const callbacks = this.subscribers.get(type);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    send(message) {
        if (this.isConnected && this.ws) {
            this.ws.send(JSON.stringify(message));
        }
    }

    onStatusChange(status) {
        // Dispatch custom event for UI updates
        const event = new CustomEvent('websocket-status', { detail: { status } });
        document.dispatchEvent(event);
    }
}

// Create global WebSocket manager instance
const wsManager = new WebSocketManager();

// Initialize WebSocket when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Connect to WebSocket
    wsManager.connect();
    
    // Subscribe to market data updates
    wsManager.subscribe('market_data', (data) => {
        console.log('Market data update:', data);
        // Update UI with market data
        updateMarketDisplay(data);
    });
    
    // Subscribe to alerts
    wsManager.subscribe('alert', (data) => {
        console.log('Alert received:', data);
        showNotification(data.message, data.type);
    });
});

// Helper functions
function updateMarketDisplay(data) {
    // Update market data displays if available
    if (data.symbol && data.price) {
        const element = document.getElementById(`price-${data.symbol}`);
        if (element) {
            element.textContent = '₹' + data.price.toFixed(2);
            element.classList.add('price-updated');
            setTimeout(() => element.classList.remove('price-updated'), 500);
        }
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'error' ? '#ff1744' : type === 'success' ? '#00c853' : '#2962ff'};
        color: white;
        border-radius: 8px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Make WebSocket manager globally available
window.wsManager = wsManager;
window.WebSocketManager = WebSocketManager;
