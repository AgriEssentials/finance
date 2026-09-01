/**
 * Quant Terminal v2 - Dynamic UI Engine (Frontend) - STABILIZED VERSION
 * 
 * FIXED: Theme disco/flickering issues
 * - Added theme change hysteresis (5-minute lock after change)
 * - Only applies theme if truly different
 * - Smooth CSS transitions
 * - Reduced refresh frequency to 60s (was 30s)
 */

class DynamicUIController {
    constructor() {
        this.currentTheme = 'professional_dark';
        this.lastThemeChange = 0;
        this.THEME_LOCKOUT_MS = 300000; // 5 minutes between theme changes (prevents disco)
        this.systemState = null;
        this.refreshInterval = null;
        this.shadowVisualization = null;
        this.alertSound = null;
        this.pendingAlerts = new Set();
        this.isProcessing = false;
        
        // Initialize
        this.init();
    }
    
    init() {
        // Load alert sound (silent fail if not found - no 404 console spam)
        try {
            this.alertSound = new Audio('/static/sounds/alert.mp3');
            this.alertSound.volume = 0.3;
            this.alertSound.onerror = () => { this.alertSound = null; };
            this.alertSound.load();
        } catch (e) {
            this.alertSound = null;
        }
        
        // Start polling
        this.startStatePolling();
        
        // Setup UI elements
        this.setupDynamicElements();
        
        console.log('[DYNAMIC UI] Controller initialized - STABLE MODE');
    }
    
    /**
     * Start polling for system state updates
     */
    startStatePolling() {
        // Initial fetch after 2 seconds (let page load first)
        setTimeout(() => this.fetchSystemState(), 2000);
        
        // Poll every 60 seconds (reduced from 30s to prevent flicker)
        this.refreshInterval = setInterval(() => {
            this.fetchSystemState();
        }, 60000);
    }
    
    /**
     * Fetch system state from backend
     */
    async fetchSystemState() {
        // Prevent concurrent fetches
        if (this.isProcessing) return;
        
        try {
            this.isProcessing = true;
            const token = localStorage.getItem('access_token');
            if (!token || token === 'undefined' || token.length < 20) {
                this.isProcessing = false;
                return;
            }
            
            const response = await fetch('/api/v2/system-state', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Cache-Control': 'no-cache'
                }
            });
            
            if (response.status === 401) {
                // Session expired - stop polling quietly
                this.stopStatePolling();
                return;
            }
            if (!response.ok) return; // transient error - retry next cycle
            
            const state = await response.json();
            
            // Apply state (with checks to prevent flicker)
            this.applySystemStateStable(state);
            
        } catch (error) {
            // Network errors - stay quiet, next cycle retries
        } finally {
            this.isProcessing = false;
        }
    }
    
    /**
     * Stop polling (session expired / page hidden)
     */
    stopStatePolling() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    /**
     * Apply system state to UI (STABLE VERSION - prevents disco)
     */
    applySystemStateStable(state) {
        this.systemState = state;
        
        // Apply theme (WITH HYSTERESIS - prevents rapid switching)
        if (state.ui_configuration?.theme) {
            const newTheme = state.ui_configuration.theme;
            const now = Date.now();
            const timeSinceLastChange = now - this.lastThemeChange;
            
            // Only change theme if:
            // 1. It's different from current theme
            // 2. Enough time has passed since last change (5 min lockout)
            if (newTheme !== this.currentTheme && timeSinceLastChange > this.THEME_LOCKOUT_MS) {
                console.log(`[DYNAMIC UI] Theme change: ${this.currentTheme} → ${newTheme}`);
                this.applyTheme(newTheme);
                this.lastThemeChange = now;
            } else if (newTheme !== this.currentTheme) {
                console.log(`[DYNAMIC UI] Theme change blocked (lockout): ${newTheme} (wait ${Math.ceil((this.THEME_LOCKOUT_MS - timeSinceLastChange)/1000)}s)`);
            }
        }
        
        // Apply alert banner (only if content changed)
        if (state.ui_configuration?.alert_banner) {
            const bannerId = JSON.stringify(state.ui_configuration.alert_banner);
            if (this.lastBannerId !== bannerId) {
                this.showAlertBanner(state.ui_configuration.alert_banner);
                this.lastBannerId = bannerId;
            }
        } else {
            if (this.lastBannerId !== null) {
                this.hideAlertBanner();
                this.lastBannerId = null;
            }
        }
        
        // Update market narrative (only if changed)
        if (state.ui_configuration?.market_narrative) {
            const narrativeStr = JSON.stringify(state.ui_configuration.market_narrative);
            if (this.lastNarrative !== narrativeStr) {
                this.updateMarketNarrative(state.ui_configuration.market_narrative);
                this.lastNarrative = narrativeStr;
            }
        }
        
        // Handle new alerts (one-time display)
        if (state.active_alerts) {
            state.active_alerts.forEach(alert => {
                if (!this.pendingAlerts.has(alert.id)) {
                    this.showAlertToast(alert);
                    this.pendingAlerts.add(alert.id);
                    
                    // Limit set size
                    if (this.pendingAlerts.size > 100) {
                        const first = this.pendingAlerts.values().next().value;
                        this.pendingAlerts.delete(first);
                    }
                }
            });
        }
    }
    
    /**
     * Apply theme to document (SMOOTH TRANSITION)
     */
    applyTheme(themeName) {
        if (!themeName || themeName === this.currentTheme) return;
        
        const oldTheme = this.currentTheme;
        this.currentTheme = themeName;
        
        // Remove old theme
        document.body.classList.remove(`theme-${oldTheme}`);
        
        // Add new theme
        document.body.classList.add(`theme-${themeName}`);
        
        // Inject CSS variables
        this.injectThemeCSS(themeName);
        
        // Show notification (only for significant changes)
        if (themeName === 'war_room' || themeName === 'high_alert') {
            this.showThemeNotification(themeName);
            this.playAlertSound();
        }
        
        console.log(`[DYNAMIC UI] Theme applied: ${themeName}`);
    }
    
    /**
     * Inject theme CSS (simplified - avoids re-injection if same)
     */
    injectThemeCSS(themeName) {
        const css = this.getThemeCSS(themeName);
        
        let styleEl = document.getElementById('dynamic-theme-css');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'dynamic-theme-css';
            document.head.appendChild(styleEl);
        }
        
        // Only update if CSS changed
        if (styleEl.textContent !== css) {
            styleEl.textContent = css;
        }
    }
    
    /**
     * Get CSS for theme
     */
    getThemeCSS(themeName) {
        const themes = {
            professional_dark: `
                :root {
                    --bg-primary: #0a0e1a;
                    --accent-primary: #00d4ff;
                    --accent-secondary: #7b2cbf;
                    --alert-color: #00d4ff;
                }
            `,
            war_room: `
                :root {
                    --bg-primary: #1a0505;
                    --accent-primary: #ff2d2d;
                    --accent-secondary: #ff6b35;
                    --alert-color: #ff2d2d;
                }
                body {
                    background: radial-gradient(ellipse at center, #1a0505 0%, #0a0202 100%);
                }
                .alert-banner { animation: pulse-red 2s infinite; }
            `,
            high_alert: `
                :root {
                    --bg-primary: #1a1205;
                    --accent-primary: #ff9500;
                    --accent-secondary: #ffb84d;
                    --alert-color: #ff9500;
                }
                body {
                    background: radial-gradient(ellipse at center, #1a1205 0%, #0a0802 100%);
                }
                .alert-banner { animation: pulse-orange 3s infinite; }
            `,
            caution: `
                :root {
                    --bg-primary: #151520;
                    --accent-primary: #ffd700;
                    --accent-secondary: #b8860b;
                    --alert-color: #ffd700;
                }
            `,
            zen_mode: `
                :root {
                    --bg-primary: #0a1a15;
                    --accent-primary: #00ff9d;
                    --accent-secondary: #00b36b;
                    --alert-color: #00ff9d;
                }
            `
        };
        
        return themes[themeName] || themes.professional_dark;
    }
    
    /**
     * Show theme change notification
     */
    showThemeNotification(themeName) {
        // Remove existing notification
        const existing = document.querySelector('.theme-notification');
        if (existing) existing.remove();
        
        const displayNames = {
            war_room: { name: 'WAR ROOM', icon: '🔴', desc: 'Critical volatility detected' },
            high_alert: { name: 'HIGH ALERT', icon: '🟠', desc: 'Elevated volatility' },
            caution: { name: 'CAUTION', icon: '🟡', desc: 'Bearish conditions' },
            zen_mode: { name: 'ZEN MODE', icon: '🟢', desc: 'Calm markets' }
        };
        
        const info = displayNames[themeName];
        if (!info) return;
        
        const notification = document.createElement('div');
        notification.className = `theme-notification theme-${themeName}`;
        notification.innerHTML = `
            <span class="theme-icon">${info.icon}</span>
            <div class="theme-info">
                <strong>${info.name}</strong>
                <span>${info.desc}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        requestAnimationFrame(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        });
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100px)';
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }
    
    /**
     * Show alert banner
     */
    showAlertBanner(banner) {
        let bannerEl = document.getElementById('dynamic-alert-banner');
        
        if (!bannerEl) {
            bannerEl = document.createElement('div');
            bannerEl.id = 'dynamic-alert-banner';
            bannerEl.className = 'alert-banner';
            
            const header = document.querySelector('.header');
            if (header) {
                header.parentNode.insertBefore(bannerEl, header.nextSibling);
            } else {
                document.body.prepend(bannerEl);
            }
        }
        
        bannerEl.className = `alert-banner alert-${banner.type}`;
        bannerEl.style.display = 'block';
        bannerEl.innerHTML = `
            <div class="alert-content">
                <span class="alert-title">${banner.title}</span>
                <span class="alert-message">${banner.message}</span>
                ${banner.action_text ? `
                    <a href="${banner.action_link || '#'}" class="alert-action">${banner.action_text}</a>
                ` : ''}
            </div>
            <button class="alert-close" onclick="DynamicUI.hideAlertBanner()">×</button>
        `;
    }
    
    hideAlertBanner() {
        const banner = document.getElementById('dynamic-alert-banner');
        if (banner) {
            banner.style.display = 'none';
        }
    }
    
    /**
     * Update market narrative
     */
    updateMarketNarrative(narrative) {
        const ticker = document.getElementById('market-narrative-ticker');
        if (!ticker || !narrative) return;
        
        // Filter to critical/high priority
        const important = narrative.filter(n => n.priority === 'critical' || n.priority === 'high');
        const normal = narrative.filter(n => n.priority === 'normal');
        
        // Build HTML
        let html = important.map(item => `
            <div class="narrative-item narrative-${item.priority}">
                <span class="narrative-icon">${this.getNarrativeIcon(item.type)}</span>
                <span class="narrative-text">${item.content}</span>
            </div>
        `).join('');
        
        html += normal.slice(0, 2).map(item => `
            <div class="narrative-item">
                <span class="narrative-text">${item.content}</span>
            </div>
        `).join('');
        
        // Only update if changed
        if (ticker.innerHTML !== html) {
            ticker.innerHTML = html;
        }
    }
    
    getNarrativeIcon(type) {
        const icons = {
            shadow_alert: '🔮',
            shadow_insight: '📊',
            metric: '📈',
            alert: '⚠️',
            header: '🎯'
        };
        return icons[type] || '•';
    }
    
    /**
     * Show alert toast
     */
    showAlertToast(alert) {
        // Check if toast already shown
        if (document.getElementById(`toast-${alert.id}`)) return;
        
        const container = document.getElementById('toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.id = `toast-${alert.id}`;
        toast.className = `alert-toast alert-toast-${alert.severity}`;
        
        toast.innerHTML = `
            <div class="alert-toast-header">
                <span class="alert-toast-icon">${this.getSeverityIcon(alert.severity)}</span>
                <span class="alert-toast-title">${alert.type.replace('_', ' ').toUpperCase()}</span>
                <button class="alert-toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="alert-toast-body">
                ${alert.symbol ? `<strong>${alert.symbol}</strong>: ` : ''}
                ${alert.message}
            </div>
        `;
        
        container.appendChild(toast);
        
        // Play sound for critical
        if (alert.severity === 'critical' || alert.severity === 'danger') {
            this.playAlertSound();
        }
        
        // Auto-remove
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 500);
        }, 10000);
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }
    
    getSeverityIcon(severity) {
        const icons = {
            critical: '🔴',
            danger: '🟠',
            warning: '🟡',
            info: '🔵'
        };
        return icons[severity] || 'ℹ️';
    }
    
    /**
     * Play alert sound
     */
    playAlertSound() {
        if (this.alertSound) {
            try {
                this.alertSound.currentTime = 0;
                this.alertSound.play().catch(() => {
                    // Ignore audio errors (autoplay policy / missing file)
                });
            } catch (e) {
                this.alertSound = null;
            }
        }
    }
    
    /**
     * Setup event handlers
     */
    setupDynamicElements() {
        // Acknowledge alert handler
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-acknowledge]')) {
                const alertId = e.target.getAttribute('data-acknowledge');
                this.acknowledgeAlert(alertId);
            }
        });
    }
    
    /**
     * Acknowledge alert
     */
    async acknowledgeAlert(alertId) {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`/api/v2/acknowledge-alert/${alertId}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                const toast = document.getElementById(`toast-${alertId}`);
                if (toast) toast.remove();
            }
        } catch (e) {
            console.error('[DYNAMIC UI] Acknowledge failed:', e);
        }
    }
}

// CSS Styles (injected once)
const dynamicStyles = `
    /* Smooth Theme Transitions */
    body {
        transition: background 0.8s ease, color 0.5s ease;
    }
    
    .dashboard-panel {
        transition: background 0.5s ease, border-color 0.5s ease, box-shadow 0.5s ease;
    }
    
    /* Alert Banner */
    .alert-banner {
        padding: 15px 20px;
        margin-bottom: 20px;
        border-radius: 8px;
        display: none;
        position: relative;
        animation: slideDown 0.3s ease;
    }
    
    .alert-banner.alert-critical {
        background: rgba(255, 45, 45, 0.2);
        border: 1px solid rgba(255, 45, 45, 0.6);
        color: #ff6b6b;
    }
    
    .alert-banner.alert-red_alert {
        background: rgba(255, 45, 45, 0.15);
        border: 1px solid rgba(255, 45, 45, 0.5);
        color: #ff9999;
    }
    
    .alert-banner.alert-warning {
        background: rgba(255, 149, 0, 0.15);
        border: 1px solid rgba(255, 149, 0, 0.4);
        color: #ffb84d;
    }
    
    .alert-content {
        display: flex;
        align-items: center;
        gap: 15px;
        flex-wrap: wrap;
    }
    
    .alert-title {
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .alert-message {
        flex: 1;
    }
    
    .alert-action {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid currentColor;
        color: inherit;
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        font-weight: 600;
        text-decoration: none;
        display: inline-block;
    }
    
    .alert-close {
        background: none;
        border: none;
        color: currentColor;
        font-size: 24px;
        cursor: pointer;
        opacity: 0.6;
        position: absolute;
        top: 10px;
        right: 15px;
    }
    
    .alert-close:hover { opacity: 1; }
    
    /* Theme Notification */
    .theme-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        padding: 15px 20px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
        opacity: 0;
        transform: translateX(100px);
        transition: all 0.5s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }
    
    .theme-notification.theme-war_room {
        background: rgba(45, 10, 10, 0.98);
        border: 2px solid rgba(255, 45, 45, 0.6);
        color: #ff6b6b;
    }
    
    .theme-notification.theme-high_alert {
        background: rgba(45, 31, 10, 0.98);
        border: 2px solid rgba(255, 149, 0, 0.6);
        color: #ffb84d;
    }
    
    .theme-icon { font-size: 24px; }
    
    .theme-info {
        display: flex;
        flex-direction: column;
    }
    
    .theme-info strong {
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .theme-info span {
        font-size: 12px;
        opacity: 0.8;
    }
    
    /* Narrative Ticker */
    #market-narrative-ticker {
        background: rgba(0, 0, 0, 0.3);
        border-radius: 8px;
        padding: 12px 15px;
        margin-bottom: 20px;
        max-height: 150px;
        overflow-y: auto;
        border: 1px solid rgba(0, 212, 255, 0.1);
    }
    
    .narrative-item {
        padding: 8px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
    }
    
    .narrative-item:last-child { border-bottom: none; }
    
    .narrative-item.narrative-critical {
        background: rgba(255, 45, 45, 0.1);
        margin: 0 -15px;
        padding: 8px 15px;
        border-left: 3px solid #ff2d2d;
    }
    
    .narrative-item.narrative-high {
        background: rgba(255, 149, 0, 0.1);
        margin: 0 -15px;
        padding: 8px 15px;
        border-left: 3px solid #ff9500;
    }
    
    .narrative-icon { font-size: 16px; }
    
    /* Toast Container */
    .toast-container {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 10001;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    
    .alert-toast {
        width: 350px;
        background: rgba(17, 24, 39, 0.98);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 15px;
        animation: slideUp 0.3s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }
    
    .alert-toast.alert-toast-critical {
        border-color: rgba(255, 45, 45, 0.6);
        background: rgba(45, 10, 10, 0.98);
    }
    
    .alert-toast.alert-toast-danger {
        border-color: rgba(255, 45, 45, 0.4);
    }
    
    .alert-toast.alert-toast-warning {
        border-color: rgba(255, 149, 0, 0.4);
        background: rgba(45, 31, 10, 0.95);
    }
    
    .alert-toast-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
    }
    
    .alert-toast-icon { font-size: 20px; }
    
    .alert-toast-title {
        font-weight: 700;
        flex: 1;
        font-size: 12px;
        text-transform: uppercase;
    }
    
    .alert-toast-close {
        background: none;
        border: none;
        color: rgba(255, 255, 255, 0.6);
        font-size: 20px;
        cursor: pointer;
    }
    
    .alert-toast-body {
        font-size: 13px;
        line-height: 1.5;
    }
    
    /* Animations */
    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 20px rgba(255, 45, 45, 0.4); }
        50% { box-shadow: 0 0 40px rgba(255, 45, 45, 0.8); }
    }
    
    @keyframes pulse-orange {
        0%, 100% { box-shadow: 0 0 15px rgba(255, 149, 0, 0.3); }
        50% { box-shadow: 0 0 30px rgba(255, 149, 0, 0.6); }
    }
    
    @media (max-width: 768px) {
        .alert-toast { width: calc(100vw - 40px); }
        .alert-content { flex-direction: column; align-items: flex-start; }
    }
`;

// Inject styles once
if (!document.getElementById('dynamic-ui-styles')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'dynamic-ui-styles';
    styleEl.textContent = dynamicStyles;
    document.head.appendChild(styleEl);
}

// Initialize global instance
window.DynamicUI = new DynamicUIController();

console.log('[DYNAMIC UI] Stabilized version loaded - Theme changes locked for 5 minutes');
