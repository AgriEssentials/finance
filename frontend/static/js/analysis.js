"use strict";
// @ts-nocheck
/**
 * Professional AI Stock Analysis - Frontend Application
 * Version 2.0 with Professional Features
 * Protected - Authentication Required
 */

// ==========================================
// AUTHENTICATION PROTECTION
// ==========================================
(function checkAuthentication() {
    const AUTH_KEY = 'quant_terminal_user';
    let session = sessionStorage.getItem(AUTH_KEY) || localStorage.getItem(AUTH_KEY);
    
    if (!session) {
        // No session found, redirect to login
        window.location.href = '/auth.html';
        return;
    }
    
    try {
        const parsed = JSON.parse(session);
        if (parsed.expires && Date.now() > parsed.expires) {
            // Session expired
            localStorage.removeItem(AUTH_KEY);
            sessionStorage.removeItem(AUTH_KEY);
            window.location.href = '/auth.html';
            return;
        }
        
        // User is authenticated - update UI
        const user = parsed.user;
        if (user && user.name) {
            document.addEventListener('DOMContentLoaded', () => {
                const userNameEl = document.getElementById('user-name');
                if (userNameEl) {
                    userNameEl.textContent = user.name;
                }
            });
        }
    } catch (e) {
        // Invalid session data
        localStorage.removeItem(AUTH_KEY);
        sessionStorage.removeItem(AUTH_KEY);
        window.location.href = '/auth.html';
    }
})();

// ==========================================
// APP CONFIGURATION
// ==========================================
const API_BASE_URL = window.location.origin;
// State
let currentMode = 'swing';
let popularSymbols = { nse: [], bse: [] };
let predictionChart = null;
let latestAnalysisData = null;
let liveNewsInterval = null;
let liveAlertsInterval = null;
let dashboardCharts = {
    volatility: null,
    fan: null,
    drawdown: null,
    relative: null
};
let landingMainChart = null;
let landingSparklineCharts = [];
let landingRefreshInterval = null;

// DOM Elements - Always get fresh references (never cache to avoid stale elements after auth redirect)
function getAnalysisElements() {
    return {
        symbolInput: document.getElementById('symbol'),
        portfolioInput: document.getElementById('portfolio-value'),
        analyzeBtn: document.getElementById('analyze-btn'),
        popularSymbolsBtn: document.getElementById('popular-symbols-btn'),
        modeBtns: document.querySelectorAll('.mode-btn'),
        resultsSection: document.getElementById('results-section'),
        emptyState: document.getElementById('empty-state'),
        symbolsModal: document.getElementById('symbols-modal'),
        symbolsList: document.getElementById('symbols-list'),
        modalClose: document.querySelector('.modal-close'),
        tabBtns: document.querySelectorAll('.modal-tabs .tab-btn'),
        logoutBtn: document.getElementById('logout-btn')
    };
}

// Get fresh elements every time - don't cache
    const analysisElements = getAnalysisElements();
/**
 * Logout user and redirect to landing page
 */
function handleLogout() {
    // Use AuthSystem if available for proper logout
    if (typeof AuthSystem !== 'undefined' && AuthSystem.logout) {
        AuthSystem.logout();
    } else {
        // Fallback if AuthSystem not loaded
        const AUTH_KEY = 'quant_terminal_user';
        localStorage.removeItem(AUTH_KEY);
        sessionStorage.removeItem(AUTH_KEY);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/auth.html';
    }
}

/**
 * Initialize page - load data
 */
function initializePage() {
    console.log('[ANALYSIS] Initializing page...');
    populateLiveTickerBar();
}

/**
 * Setup event listeners for the page
 */
function setupPageEventListeners() {
    console.log('[ANALYSIS] Setting up event listeners...');

    // Analyze button
    const analyzeBtn = document.getElementById('analyze-btn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', handleAnalyzeClick);
        console.log('[ANALYSIS] Analyze button connected');
    } else {
        console.warn('[ANALYSIS] Analyze button not found');
    }

    // Symbol input - Enter key
    const symbolInput = document.getElementById('symbol');
    if (symbolInput) {
        symbolInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleAnalyzeClick();
            }
        });
        console.log('[ANALYSIS] Symbol input connected');
    }

    // Mode buttons
    const modeBtns = document.querySelectorAll('.mode-btn');
    if (modeBtns.length > 0) {
        modeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                modeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });
        console.log('[ANALYSIS] Mode buttons connected');
    }

    // Popular symbols button
    const popularBtn = document.getElementById('popular-symbols-btn');
    if (popularBtn) {
        popularBtn.addEventListener('click', () => {
            console.log('[ANALYSIS] Popular symbols clicked');
        });
        console.log('[ANALYSIS] Popular symbols button connected');
    }
}

/**
 * Handle analyze button click
 */
async function handleAnalyzeClick() {
    console.log('[ANALYSIS] Analyze clicked');
    const symbolInput = document.getElementById('symbol');
    const symbol = symbolInput ? symbolInput.value.trim().toUpperCase() : '';

    if (!symbol) {
        alert('Please enter a stock symbol');
        return;
    }

    const analyzeBtn = document.getElementById('analyze-btn');
    if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = '⏳ Analyzing...';
    }

    try {
        console.log(`[ANALYSIS] Fetching data for ${symbol}...`);
        const response = await fetch(`/api/professional/analyze?symbol=${encodeURIComponent(symbol)}&mode=swing&portfolio_value=1000000&fast=true`);

        if (!response.ok) {
            throw new Error(`API returned ${response.status}`);
        }

        const data = await response.json();
        console.log('[ANALYSIS] Analysis complete:', data);
        displayAnalysisResults(data, symbol);

    } catch (error) {
        console.error('[ANALYSIS] Error:', error);
        alert(`Analysis failed: ${error.message}`);
    } finally {
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<span class="btn-icon">🔍</span><span class="btn-text">[ EXECUTE QUANTITATIVE ANALYSIS ]</span>';
        }
    }
}

/**
 * Display analysis results
 */
function displayAnalysisResults(data, symbol) {
    const resultsSection = document.getElementById('analysis-content');
    const emptyState = document.getElementById('empty-state');

    if (emptyState) {
        emptyState.style.display = 'none';
    }

    if (resultsSection) {
        resultsSection.style.display = 'block';

        // Update basic info
        const resultSymbol = document.getElementById('result-symbol');
        if (resultSymbol) {
            resultSymbol.textContent = data.symbol || symbol;
        }

        // Show results
        console.log('[ANALYSIS] Results displayed');
    }
}

async function populateLiveTickerBar() {
    const bar = document.getElementById('live-ticker-bar');
    if (!bar) return;
    try {
        const res = await fetch(`${API_BASE_URL}/api/landing-data`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.indices && data.indices.length > 0) {
            bar.innerHTML = data.indices.map(idx => {
                const cls = idx.change >= 0 ? 'positive' : 'negative';
                const sign = idx.change >= 0 ? '+' : '';
                return `<div class="ticker-item ${cls}"><span>${idx.name}</span><strong>${sign}${idx.change_pct.toFixed(2)}%</strong></div>`;
            }).join('');
        }
    } catch(e) {
        console.warn('Ticker bar fetch failed:', e);
    }
}
function renderTicker(targetId, indices) {
    const bar = document.getElementById(targetId);
    if (!bar)
        return;
    if (!indices || indices.length === 0)
        return;
    bar.innerHTML = indices.slice(0, 5).map(idx => {
        const change = Number(idx.change_pct || 0);
        const cls = change >= 0 ? 'positive' : 'negative';
        const sign = change >= 0 ? '+' : '';
        return `<div class="ticker-item ${cls}"><span>${escapeHtml(idx.name || '-')}</span><strong>${sign}${change.toFixed(2)}%</strong></div>`;
    }).join('');
}
function renderLandingSystemPanels(data) {
    const systemStatus = document.getElementById('hero-system-status');
    const apiStatus = document.getElementById('hero-api-status');
    const mlStatus = document.getElementById('hero-ml-status');
    if (systemStatus) {
        const status = (((data || {}).system || {}).status || 'UNKNOWN').toUpperCase();
        systemStatus.textContent = status;
    }
    if (apiStatus) {
        const keys = ((data || {}).api_keys || {});
        const available = Object.values(keys).filter(Boolean).length;
        const total = Object.keys(keys).length;
        apiStatus.textContent = `${available}/${total || 0} active`;
    }
    if (mlStatus) {
        const ml = ((data || {}).ml_models || {});
        const ready = Object.values(ml).filter(v => v === 'READY' || v === 'TRAINED').length;
        const total = Object.keys(ml).length;
        mlStatus.textContent = `${ready}/${total || 0} ready`;
    }
}
function buildFallbackHeatmap() {
    const symbols = [
        'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN',
        'ITC', 'LT', 'AXISBANK', 'KOTAKBANK', 'SUNPHARMA', 'MARUTI',
        'TITAN', 'BAJFINANCE', 'HCLTECH', 'WIPRO', 'ONGC', 'M&M'
    ];
    return symbols.map((symbol, index) => {
        const wave = Math.sin((Date.now() / 60000) + index) * 1.9;
        const drift = (Math.cos((Date.now() / 120000) + index) * 0.8);
        return {
            symbol,
            change_pct: Number((wave + drift).toFixed(2)),
            price: Number((900 + (index * 37) + Math.abs(wave) * 25).toFixed(2))
        };
    });
}
function buildFallbackSparklines() {
    const base = [
        { symbol: 'RELIANCE', start: 2880 },
        { symbol: 'TCS', start: 4120 },
        { symbol: 'HDFCBANK', start: 1630 },
        { symbol: 'INFY', start: 1520 },
        { symbol: 'ICICIBANK', start: 1145 },
        { symbol: 'SBIN', start: 845 }
    ];
    return base.map((item, idx) => {
        const prices = [];
        for (let i = 0; i < 28; i++) {
            const trend = Math.sin((i / 4) + idx) * (6 + idx);
            const micro = Math.cos((i / 2.7) + idx) * 2.5;
            prices.push(Number((item.start + trend + micro).toFixed(2)));
        }
        const changePct = ((prices[prices.length - 1] - prices[0]) / prices[0]) * 100;
        return {
            symbol: item.symbol,
            prices,
            current: prices[prices.length - 1],
            change_pct: Number(changePct.toFixed(2))
        };
    });
}
function ensureLandingDataShape(data) {
    const safeData = data || {};
    const heatmap = Array.isArray(safeData.heatmap) && safeData.heatmap.length > 0
        ? safeData.heatmap
        : buildFallbackHeatmap();
    const indices = Array.isArray(safeData.indices) ? safeData.indices : [];
    return { ...safeData, indices, heatmap };
}
function renderLandingHeatmap(stocks) {
    const container = document.getElementById('sector-heatmap');
    if (!container)
        return;
    const safeStocks = (stocks && stocks.length > 0) ? stocks : buildFallbackHeatmap();
    container.innerHTML = safeStocks.slice(0, 30).map(stock => {
        const pct = Number(stock.change_pct || 0);
        const cls = pct > 1.0 ? 'heat-up-strong' : pct >= 0 ? 'heat-up' : pct < -1.0 ? 'heat-down-strong' : 'heat-down';
        const sign = pct >= 0 ? '+' : '';
        return `
            <div class="heat-cell ${cls}" title="${escapeHtml(stock.symbol)} ${pct.toFixed(2)}%">
                <span class="heat-symbol">${escapeHtml(stock.symbol)}</span>
                <span class="heat-move">${sign}${pct.toFixed(2)}%</span>
            </div>
        `;
    }).join('');
}
function renderOrderBookFromTop(stock) {
    const container = document.getElementById('order-book');
    if (!container)
        return;
    const fallbackStock = buildFallbackHeatmap()[0];
    const selectedStock = stock || fallbackStock;
    const base = Number((selectedStock || {}).price || 2500);
    const symbol = (selectedStock && selectedStock.symbol) ? selectedStock.symbol : 'NIFTY-LIQ';
    let html = `<div class="ob-header">${escapeHtml(symbol)} | Mid: ${base.toFixed(2)}</div>`;
    html += '<div class="ob-row ob-row-head"><span class="ob-cell">BID</span><span class="ob-cell ob-vol">SIZE</span><span class="ob-cell">ASK</span></div>';
    for (let i = 0; i < 8; i++) {
        const spread = 0.08 + i * 0.11;
        const bid = (base - spread).toFixed(2);
        const ask = (base + spread).toFixed(2);
        const size = Math.round(400 + (i * 120) + Math.random() * 900);
        html += `<div class="ob-row"><span class="ob-cell ob-bid">${bid}</span><span class="ob-cell ob-vol">${size}</span><span class="ob-cell ob-ask">${ask}</span></div>`;
    }
    container.innerHTML = html;
}
function pushLandingLog(message, type = 'info') {
    const stream = document.getElementById('log-stream');
    if (!stream)
        return;
    const stamp = new Date().toLocaleTimeString('en-IN', { hour12: false });
    const line = document.createElement('p');
    line.className = type;
    line.textContent = `[${stamp}] ${message}`;
    stream.insertBefore(line, stream.firstChild);
    while (stream.children.length > 12) {
        stream.removeChild(stream.lastChild);
    }
}
function destroyLandingSparklines() {
    landingSparklineCharts.forEach(chart => {
        if (chart)
            chart.destroy();
    });
    landingSparklineCharts = [];
}
function renderLandingMainChart(sparks) {
    const canvas = document.getElementById('main-chart');
    if (!canvas || !window.Chart)
        return;
    if (landingMainChart) {
        landingMainChart.destroy();
        landingMainChart = null;
    }
    const safeSparks = (sparks && sparks.length > 0) ? sparks : buildFallbackSparklines();
    const series = (safeSparks && safeSparks[0] && Array.isArray(safeSparks[0].prices)) ? safeSparks[0].prices : [];
    const labels = series.map((_, i) => i + 1);
    landingMainChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: [{
                    label: safeSparks && safeSparks[0] ? safeSparks[0].symbol : 'Index',
                    data: series,
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.14)',
                    fill: true,
                    tension: 0.22,
                    pointRadius: 0
                }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.15)' } }
            }
        }
    });
}
function renderLandingSparklines(sparks) {
    const grid = document.getElementById('sparkline-grid');
    if (!grid)
        return;
    const safeSparks = (sparks && sparks.length > 0) ? sparks : buildFallbackSparklines();
    grid.innerHTML = safeSparks.slice(0, 6).map((s, idx) => {
        const pct = Number(s.change_pct || 0);
        const cls = pct >= 0 ? 'pos' : 'neg';
        const sign = pct >= 0 ? '+' : '';
        return `
            <div class="sparkline-card">
                <div class="sparkline-meta">
                    <span>${escapeHtml(s.symbol)}</span>
                    <strong class="${cls}">${sign}${pct.toFixed(2)}%</strong>
                </div>
                <div class="sparkline-canvas-wrap">
                    <canvas id="sparkline-${idx}"></canvas>
                </div>
            </div>
        `;
    }).join('');
    if (!window.Chart)
        return;
    destroyLandingSparklines();
    safeSparks.slice(0, 6).forEach((s, idx) => {
        const canvas = document.getElementById(`sparkline-${idx}`);
        if (!canvas)
            return;
        const pct = Number(s.change_pct || 0);
        const color = pct >= 0 ? '#22c55e' : '#ef4444';
        const chart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: (s.prices || []).map((_, i) => i),
                datasets: [{
                        data: s.prices || [],
                        borderColor: color,
                        pointRadius: 0,
                        borderWidth: 1.7,
                        tension: 0.2
                    }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: { x: { display: false }, y: { display: false } }
            }
        });
        landingSparklineCharts.push(chart);
    });
}
async function loadLandingDashboard() {
    if (!document.getElementById('home-view'))
        return;
    try {
        const landingRes = await fetch(`${API_BASE_URL}/api/landing-data`);
        if (landingRes.ok) {
            const data = ensureLandingDataShape(await landingRes.json());
            renderTicker('market-ticker', data.indices || []);
            renderTicker('live-ticker-bar', data.indices || []);
            renderLandingSystemPanels(data);
            renderLandingHeatmap(data.heatmap || []);
            renderOrderBookFromTop((data.heatmap || [])[0]);
            pushLandingLog('Landing market data synced', 'success');
        }
        else {
            const fallback = ensureLandingDataShape(null);
            renderLandingHeatmap(fallback.heatmap);
            renderOrderBookFromTop(fallback.heatmap[0]);
            pushLandingLog('Landing market data request failed', 'warn');
        }
        const sparkRes = await fetch(`${API_BASE_URL}/api/sparklines`);
        if (sparkRes.ok) {
            const sparkData = await sparkRes.json();
            const sparks = (sparkData && sparkData.sparklines && sparkData.sparklines.length > 0)
                ? sparkData.sparklines
                : buildFallbackSparklines();
            renderLandingSparklines(sparks);
            renderLandingMainChart(sparks);
            pushLandingLog('Sparkline stream updated', 'info');
        }
        else {
            const fallbackSparks = buildFallbackSparklines();
            renderLandingSparklines(fallbackSparks);
            renderLandingMainChart(fallbackSparks);
            pushLandingLog('Sparkline feed unavailable', 'warn');
        }
    }
    catch (error) {
        console.warn('Landing dashboard load failed:', error);
        const fallback = ensureLandingDataShape(null);
        const fallbackSparks = buildFallbackSparklines();
        renderLandingHeatmap(fallback.heatmap);
        renderOrderBookFromTop(fallback.heatmap[0]);
        renderLandingSparklines(fallbackSparks);
        renderLandingMainChart(fallbackSparks);
        pushLandingLog('Landing feed error: using cached UI', 'warn');
    }
}
// Initialize
async function init() {
    console.log('[ANALYSIS] init() starting...');
    initializePage();
    // Setup ALL event listeners including the analyze button
    setupEventListeners();
    setupPageEventListeners(); // Additional listeners for page-specific events
    setupAIFeatures(); // Setup AI feature buttons (LSTM, Transformer, etc.)
    await loadPopularSymbols();
    setupAdvancedTabs();
    loadAlerts();
    console.log('[ANALYSIS] init() complete - all buttons should be functional');
}
// Toast notification
function showToast(message, type = 'error') {
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast)
        existingToast.remove();
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}</span>
        <span class="toast-message">${message}</span>
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}
function normalizeSymbol(rawSymbol) {
    const symbol = (rawSymbol || '').trim().toUpperCase();
    if (!symbol)
        return '';
    if (symbol.includes('.'))
        return symbol;
    return `${symbol}.NS`;
}
// Event Listeners - always get fresh elements to avoid stale references after auth redirect
function setupEventListeners() {
    const els = getAnalysisElements();
    console.log('[ANALYSIS] Setting up event listeners...');

    // Logout button
    if (els.logoutBtn) {
        els.logoutBtn.addEventListener('click', handleLogout);
        console.log('[ANALYSIS] Logout button connected');
    }

    // Mode selection
    if (els.modeBtns && els.modeBtns.length) {
        els.modeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                els.modeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMode = btn.dataset.mode === 'long_term' ? 'longterm' : btn.dataset.mode;
            });
        });
        console.log('[ANALYSIS] Mode buttons connected');
    }

    // Analyze button - CRITICAL: this must be connected for analysis to work
    if (els.analyzeBtn) {
        els.analyzeBtn.addEventListener('click', handleAnalyze);
        console.log('[ANALYSIS] Analyze button connected - CLICK WILL WORK');
    } else {
        console.error('[ANALYSIS] CRITICAL: Analyze button not found!');
    }

    // Popular symbols
    if (els.popularSymbolsBtn && els.symbolsModal) {
        els.popularSymbolsBtn.addEventListener('click', () => {
            els.symbolsModal.style.display = 'flex';
            renderSymbols('nse');
        });
        console.log('[ANALYSIS] Popular symbols button connected');
    }
    if (els.modalClose && els.symbolsModal) {
        els.modalClose.addEventListener('click', () => {
            els.symbolsModal.style.display = 'none';
        });
    }
    if (els.symbolsModal) {
        els.symbolsModal.addEventListener('click', (e) => {
            if (e.target === els.symbolsModal) {
                els.symbolsModal.style.display = 'none';
            }
        });
    }

    // Tab buttons for modal
    if (els.tabBtns && els.tabBtns.length) {
        els.tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                els.tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderSymbols(btn.dataset.tab);
            });
        });
    }

    // Enter key on input
    if (els.symbolInput) {
        els.symbolInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleAnalyze();
            }
        });
        console.log('[ANALYSIS] Symbol input connected (Enter key)');
    }
}
// Setup advanced tabs
function setupAdvancedTabs() {
    const advancedTabs = document.querySelectorAll('.advanced-tabs .tab-btn');
    advancedTabs.forEach(btn => {
        btn.addEventListener('click', () => {
            advancedTabs.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // Content switching will be handled in displayResults
        });
    });
}
// Load popular symbols
async function loadPopularSymbols() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/symbols`);
        if (response.ok) {
            popularSymbols = await response.json();
        }
    }
    catch (error) {
        console.error('Failed to load symbols:', error);
    }
}
// Render symbols list
function renderSymbols(exchange) {
    const els = getAnalysisElements();
    const symbols = popularSymbols[exchange] || [];
    if (!els.symbolsList) return;
    els.symbolsList.innerHTML = symbols.map(symbol => `
        <div class="symbol-item" data-symbol="${symbol}">
            <span class="symbol-code">${symbol}</span>
            <span>Select →</span>
        </div>
    `).join('');
    els.symbolsList.querySelectorAll('.symbol-item').forEach(item => {
        item.addEventListener('click', () => {
            if (els.symbolInput) els.symbolInput.value = item.dataset.symbol;
            if (els.symbolsModal) els.symbolsModal.style.display = 'none';
        });
    });
}
// Handle analyze
async function handleAnalyze() {
    // Always get fresh elements
    const els = getAnalysisElements();
    const symbol = els.symbolInput ? els.symbolInput.value.trim().toUpperCase() : '';
    const portfolioValue = parseFloat(els.portfolioInput ? els.portfolioInput.value : 1000000) || 1000000;
    if (!symbol) {
        showToast('Please enter a stock symbol', 'error');
        return;
    }
    if (!symbol.includes('.')) {
        showToast('Please include exchange suffix (.NS for NSE, .BO for BSE)', 'error');
        return;
    }
    setLoading(true);
    try {
        const normalizedMode = currentMode === 'long_term' ? 'longterm' : currentMode;
        const response = await fetch(`${API_BASE_URL}/api/professional/analyze?symbol=${encodeURIComponent(symbol)}&mode=${normalizedMode}&portfolio_value=${portfolioValue}&fast=true`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }
        const data = await response.json();
        displayResults(data);
        await fetchAndRenderProfessionalDashboard(symbol, normalizedMode);
        showToast('Professional analysis completed!', 'success');
    }
    catch (error) {
        console.error('Analysis error:', error);
        showToast(`Analysis failed: ${error.message}`, 'error');
    }
    finally {
        setLoading(false);
    }
}
async function fetchAndRenderProfessionalDashboard(symbol, mode) {
    ensureDashboardSection();
    try {
        console.log('[DASHBOARD] Fetching professional dashboard data...');
        const response = await fetch(`${API_BASE_URL}/api/professional/dashboard?symbol=${encodeURIComponent(symbol)}&mode=${mode}`);
        if (!response.ok) {
            throw new Error('Advanced dashboard data unavailable');
        }
        const data = await response.json();
        console.log('[DASHBOARD] Received data:', data);
        renderDashboardKpis(data.kpis || {});
        renderDashboardCharts(data.charts || {});
        console.log('[DASHBOARD] Dashboard rendered successfully');
    }
    catch (error) {
        console.error('Dashboard error:', error);
        showToast('Dashboard data unavailable: ' + error.message, 'info');
    }
}
function ensureDashboardSection() {
    if (document.getElementById('pro-dashboard-card'))
        return;
    const results = document.getElementById('results-section');
    const card = document.createElement('div');
    card.id = 'pro-dashboard-card';
    card.className = 'analysis-card chart-card';
    card.innerHTML = `
        <h3>Institutional Quant Dashboard</h3>
        <div id="pro-kpis" class="pro-kpis-grid"></div>
        <div class="pro-chart-grid">
            <div class="chart-container"><canvas id="volatility-regime-chart"></canvas></div>
            <div class="chart-container"><canvas id="drawdown-chart"></canvas></div>
            <div class="chart-container"><canvas id="relative-strength-chart"></canvas></div>
            <div class="chart-container"><canvas id="monte-carlo-fan-chart"></canvas></div>
        </div>
    `;
    results.appendChild(card);
}
function renderDashboardKpis(kpis) {
    var _a, _b, _c, _d;
    const container = document.getElementById('pro-kpis');
    if (!container)
        return;
    const regime = kpis.volatility_regime || '-';
    const regimeColor = regime === 'HIGH_VOL' ? '#ef4444' : regime === 'LOW_VOL' ? '#10b981' : '#f59e0b';
    container.innerHTML = `
        <div class="metric-card"><div class="metric-label">Ann. Volatility</div><div class="metric-value">${(_a = kpis.annualized_volatility_pct) !== null && _a !== void 0 ? _a : '-'}%</div></div>
        <div class="metric-card"><div class="metric-label">Volatility Regime</div><div class="metric-value" style="color:${regimeColor}">${regime}</div></div>
        <div class="metric-card"><div class="metric-label">Max Drawdown</div><div class="metric-value">${(_b = kpis.max_drawdown_pct) !== null && _b !== void 0 ? _b : '-'}%</div></div>
        <div class="metric-card"><div class="metric-label">VaR 95%</div><div class="metric-value">${(_c = kpis.var_95_pct) !== null && _c !== void 0 ? _c : '-'}%</div></div>
        <div class="metric-card"><div class="metric-label">CVaR 95%</div><div class="metric-value">${(_d = kpis.cvar_95_pct) !== null && _d !== void 0 ? _d : '-'}%</div></div>
    `;
}
function destroyDashboardCharts() {
    Object.keys(dashboardCharts).forEach((k) => {
        if (dashboardCharts[k]) {
            dashboardCharts[k].destroy();
            dashboardCharts[k] = null;
        }
    });
}
function renderDashboardCharts(charts) {
    destroyDashboardCharts();
    const volCanvas = document.getElementById('volatility-regime-chart');
    const ddCanvas = document.getElementById('drawdown-chart');
    const rsCanvas = document.getElementById('relative-strength-chart');
    const fanCanvas = document.getElementById('monte-carlo-fan-chart');
    console.log('[CHARTS] Canvas elements found:', {
        vol: !!volCanvas,
        dd: !!ddCanvas,
        rs: !!rsCanvas,
        fan: !!fanCanvas
    });
    if (!volCanvas || !ddCanvas || !rsCanvas || !fanCanvas) {
        console.warn('[CHARTS] Missing canvas elements!');
        return;
    }
    const vol = charts.volatility_regime || {};
    dashboardCharts.volatility = new Chart(volCanvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: vol.labels || [],
            datasets: [
                { label: 'Volatility %', data: vol.volatility || [], borderColor: '#00d4ff', pointRadius: 0, tension: 0.2 },
                { label: 'P25', data: (vol.labels || []).map(() => vol.p25), borderColor: '#10b981', borderDash: [4, 4], pointRadius: 0 },
                { label: 'P75', data: (vol.labels || []).map(() => vol.p75), borderColor: '#ef4444', borderDash: [4, 4], pointRadius: 0 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
    const dd = charts.drawdown || {};
    dashboardCharts.drawdown = new Chart(ddCanvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: dd.labels || [],
            datasets: [{ label: 'Drawdown %', data: dd.drawdown_pct || [], borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,0.2)', fill: true, pointRadius: 0 }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
    const rs = charts.relative_strength || {};
    dashboardCharts.relative = new Chart(rsCanvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: rs.labels || [],
            datasets: [
                { label: 'Stock (Base 100)', data: rs.strategy || [], borderColor: '#00d4ff', pointRadius: 0, tension: 0.2 },
                { label: 'NIFTY 50 (Base 100)', data: rs.benchmark || [], borderColor: '#9ca3af', pointRadius: 0, tension: 0.2 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
    const fan = charts.monte_carlo_fan || {};
    dashboardCharts.fan = new Chart(fanCanvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: fan.labels || [],
            datasets: [
                { label: 'Q10', data: fan.q10 || [], borderColor: '#ef4444', pointRadius: 0, borderDash: [4, 4] },
                { label: 'Q25', data: fan.q25 || [], borderColor: '#f59e0b', pointRadius: 0 },
                { label: 'Q50 Median', data: fan.q50 || [], borderColor: '#00d4ff', pointRadius: 0, borderWidth: 2 },
                { label: 'Q75', data: fan.q75 || [], borderColor: '#10b981', pointRadius: 0 },
                { label: 'Q90', data: fan.q90 || [], borderColor: '#22c55e', pointRadius: 0, borderDash: [4, 4] }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}
// Dynamic terminal simulation state
let bootSequenceInterval;
const bootMessages = [
    "[SYS] Allocating memory tensors...",
    "[NET] Connecting to NSE/BSE websocket feed...",
    "[DATA] Scraping order book depth L2...",
    "[ML] Booting LSTM_v4.2 engine...",
    "[NLP] Sarvam API authenticating...",
    "[MATH] Calculating Kelly Criterion...",
    "[RISK] Adjusting Volatility Stop Loss...",
    "[API] Groq Neural Engine locked and loaded.",
    "[SYS] Integrating composite score... STANDBY"
];

function setLoading(loading) {
    // Always get fresh elements
    const els = getAnalysisElements();
    if (!els.analyzeBtn) return;

    const btnText = els.analyzeBtn.querySelector('.btn-text');
    const btnLoader = els.analyzeBtn.querySelector('.btn-loader');
    
    if (loading) {
        els.analyzeBtn.disabled = true;
        els.analyzeBtn.style.background = 'rgba(239,83,80,0.2)';
        els.analyzeBtn.style.borderColor = 'var(--danger)';
        els.analyzeBtn.style.boxShadow = '0 0 20px rgba(239,83,80,0.4)';
        
        if (btnLoader)
            btnLoader.style.display = 'inline';

        let msgIndex = 0;
        if (btnText)
            btnText.textContent = bootMessages[0];

        bootSequenceInterval = setInterval(() => {
            msgIndex = (msgIndex + 1) % bootMessages.length;
            if (btnText)
                btnText.textContent = bootMessages[msgIndex];

            // Random glitch effect on button
            if (Math.random() > 0.7) {
                els.analyzeBtn.style.transform = 'translate(' + (Math.random()*4-2) + 'px, ' + (Math.random()*4-2) + 'px)';
                setTimeout(() => els.analyzeBtn.style.transform = 'none', 50);
            }
        }, 300);
        
        // Flash shell background
        const shell = document.getElementById('analysis-shell');
        if (shell) {
            shell.style.animation = 'blinker 0.1s linear 3';
        }

    } else {
        clearInterval(bootSequenceInterval);
        els.analyzeBtn.disabled = false;
        els.analyzeBtn.style.background = 'rgba(41,98,255,0.2)';
        els.analyzeBtn.style.borderColor = 'var(--info)';
        els.analyzeBtn.style.boxShadow = '0 0 15px rgba(41,98,255,0.4)';
        if (btnText)
            btnText.textContent = '[ EXECUTE QUANTITATIVE ANALYSIS ]';
        if (btnLoader)
            btnLoader.style.display = 'none';

        // Dramatic reveal of results
        if (els.resultsSection) {
            els.resultsSection.style.opacity = '0';
            els.resultsSection.style.transform = 'translateY(50px)';
            setTimeout(() => {
                els.resultsSection.style.transition = 'all 0.5s cubic-bezier(0.1, 1, 0.1, 1)';
                els.resultsSection.style.opacity = '1';
                els.resultsSection.style.transform = 'translateY(0)';
            }, 100);
        }
    }
}
// Display results
function displayResults(data) {
    var _a;
    console.log('[DISPLAY RESULTS] Received full data:', data);
    latestAnalysisData = data;
    // Always get fresh elements
    const els = getAnalysisElements();
    // Show results, hide empty state
    if (els.emptyState) els.emptyState.style.display = 'none';
    if (els.resultsSection) {
        els.resultsSection.style.display = 'block';
        els.resultsSection.classList.add('active');
    }
    // Update price card
    const resultSymbol = document.getElementById('result-symbol');
    const resultMode = document.getElementById('result-mode');
    const resultPrice = document.getElementById('result-price');
    const priceTimestamp = document.getElementById('price-timestamp');
    if (resultSymbol) resultSymbol.textContent = data.symbol || '-';
    if (resultMode) resultMode.textContent = data.mode || '-';
    if (resultPrice) resultPrice.textContent = (data.current_price || 0).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    if (priceTimestamp) priceTimestamp.textContent = `Last updated: ${new Date(data.timestamp).toLocaleString('en-IN')}`;
    // Update professional recommendation
    updateProfessionalRecommendation(data.professional_recommendation);
    // Update key metrics
    const metricTrend = document.getElementById('metric-trend');
    const metricRsi = document.getElementById('metric-rsi');
    const metricAi = document.getElementById('metric-ai');
    const metricRisk = document.getElementById('metric-risk');
    if (metricTrend) metricTrend.textContent = data.technical_analysis?.basic?.trend || '-';
    if (metricRsi) metricRsi.textContent = `${data.technical_analysis?.basic?.rsi || '-'} (${data.technical_analysis?.basic?.rsi_interpretation || '-'})`;
    if (metricAi) metricAi.textContent = data.ai_prediction?.ai_prediction || 'NEUTRAL';
    if (metricRisk) metricRisk.textContent = data.risk_management?.basic?.risk_level || '-';
    // Update position sizing
    updatePositionSizing((_a = data.risk_management?.professional) === null || _a === void 0 ? void 0 : _a.position_sizing);
    // Update fundamental analysis
    updateFundamentalAnalysis(data.fundamental_analysis);
    // Update advanced indicators
    updateAdvancedIndicators(data.technical_analysis?.advanced);
    // Update technical details
    updateTechnicalDetails(data.technical_analysis?.basic);
    // Update risk details
    updateRiskDetails(data.risk_management);
    // Update Finnhub advanced insights
    updateFinnhubInsights(data.finnhub_insights, data.external_api_signal);
    // Update sentiment
    updateSentimentDetails(data.sentiment_analysis);
    // Update institutional dashboard - ensure it's visible
    console.log('[DISPLAY RESULTS] Checking broker_intelligence:', data.broker_intelligence);
    const instDashboard = document.getElementById('institutional-dashboard');
    if (instDashboard) {
        instDashboard.style.display = 'block'; // Ensure visible
    }
    if (data.broker_intelligence) {
        console.log('[DISPLAY RESULTS] Calling updateInstitutionalDashboard...');
        updateInstitutionalDashboard(data.broker_intelligence);
    } else {
        console.warn('[DISPLAY RESULTS] No broker_intelligence data found!');
        if (instDashboard) {
            instDashboard.innerHTML = '<h3>Institutional Dashboard</h3><p>No institutional data available for this symbol.</p>';
        }
    }
    // Update chart
    updatePredictionChart(data.ai_prediction);
    updateAIPredictionTransparency(data.ai_prediction, data.sentiment_analysis, data.technical_analysis);
    // Scroll to results
    if (els.resultsSection) {
        els.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    // Start live refresh loops for news and alerts
    startLiveNewsUpdates(data.symbol);
    startLiveAlertsMonitoring(data.symbol);
}
// Update professional recommendation
function updateProfessionalRecommendation(rec) {
    if (!rec)
        return;
    const banner = document.getElementById('professional-banner');
    const title = document.getElementById('recommendation-title');
    // Set recommendation classes
    banner.className = 'professional-banner';
    const recClass = rec.recommendation.toLowerCase().replace(/\s+/g, '-');
    banner.classList.add(recClass);
    title.className = 'recommendation-title';
    title.classList.add(recClass);
    title.textContent = rec.recommendation;
    document.getElementById('recommendation-action').textContent = rec.action;
    document.getElementById('composite-score').textContent = rec.composite_score;
    // Update component scores
    if (rec.component_scores) {
        document.getElementById('technical-score').textContent = rec.component_scores.technical;
        document.getElementById('fundamental-score').textContent = rec.component_scores.fundamental;
        document.getElementById('sentiment-score').textContent = rec.component_scores.sentiment;
    }
    // Update reasoning
    const reasoningCard = document.getElementById('reasoning-card');
    const reasoningContent = document.getElementById('reasoning-content');
    if (rec.reasoning) {
        reasoningCard.style.display = 'block';
        // Parse reasoning into bullet points
        const reasons = rec.reasoning.split(' | ').filter(r => r.trim());
        reasoningContent.innerHTML = `
            <div class="reasoning-text">
                <p style="margin-bottom: 16px; color: var(--text-secondary); line-height: 1.7;">
                    <strong>Analysis Summary:</strong> The AI has analyzed this stock based on multiple factors including technical indicators, 
                    fundamental metrics, and market sentiment. Here's what influenced this recommendation:
                </p>
                <ul class="reasoning-list" style="list-style: none; padding: 0;">
                    ${reasons.map(reason => `
                        <li style="padding: 12px 0; border-bottom: 1px solid var(--border-color); display: flex; align-items: flex-start; gap: 12px;">
                            <span style="color: var(--primary); font-size: 1.2rem;">✓</span>
                            <span style="color: var(--text-primary); line-height: 1.6;">${reason}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
            <div style="margin-top: 20px; padding: 16px; background: var(--bg-secondary); border-radius: var(--radius); border-left: 3px solid var(--primary);">
                <strong style="color: var(--primary);">📊 Confidence Level:</strong> 
                <span style="color: var(--text-secondary);">${rec.confidence || 'Medium'}</span>
                <br><br>
                <strong style="color: var(--primary);">⏱️ Time Horizon:</strong> 
                <span style="color: var(--text-secondary);">${rec.time_horizon || 'Variable'}</span>
            </div>
        `;
    }
    else {
        reasoningCard.style.display = 'none';
    }
}
function updatePositionSizing(sizing) {
    if (!sizing)
        return;
    document.getElementById('recommended-shares').textContent = sizing.shares || '-';
    document.getElementById('position-value').textContent =
        sizing.position_value ? `₹${sizing.position_value.toLocaleString('en-IN')}` : '-';
    document.getElementById('position-percent').textContent =
        sizing.position_percent ? `${sizing.position_percent}%` : '-';
    document.getElementById('risk-amount').textContent =
        sizing.risk_amount ? `₹${sizing.risk_amount.toLocaleString('en-IN')}` : '-';
    document.getElementById('risk-percent').textContent =
        sizing.risk_percent ? `${sizing.risk_percent}%` : '-';
    document.getElementById('risk-reward').textContent =
        sizing.risk_reward ? `${sizing.risk_reward}:1` : '-';
}
// Update fundamental analysis
function updateFundamentalAnalysis(fundamental) {
    if (!fundamental || fundamental.error) {
        document.getElementById('financial-health-score').textContent = '-';
        document.getElementById('health-status').textContent = 'N/A';
        document.getElementById('fundamental-metrics').innerHTML = '<p>Fundamental data not available</p>';
        return;
    }
    const health = fundamental.financial_health || {};
    document.getElementById('financial-health-score').textContent = health.health_percentage || 0;
    document.getElementById('health-status').textContent = health.status || '-';
    const metrics = fundamental.metrics || {};
    const metricsHtml = Object.entries(metrics)
        .filter(([_, value]) => value !== null && value !== undefined)
        .map(([key, value]) => `
            <div class="fundamental-item">
                <span class="fundamental-label">${formatMetricName(key)}</span>
                <span class="fundamental-value">${formatMetricValue(key, value)}</span>
            </div>
        `).join('');
    document.getElementById('fundamental-metrics').innerHTML = metricsHtml || '<p>No metrics available</p>';
}
// Update advanced indicators
function updateAdvancedIndicators(advanced) {
    if (!advanced)
        return;
    // Get active tab
    const activeTab = document.querySelector('.advanced-tabs .tab-btn.active');
    const tabName = activeTab ? activeTab.dataset.tab : 'fibonacci';
    const container = document.getElementById('advanced-indicators-content');
    let html = '';
    switch (tabName) {
        case 'fibonacci':
            const fib = advanced.fibonacci_retracements || {};
            html = `
                <div class="fibonacci-levels">
                    ${Object.entries(fib).map(([level, price]) => `
                        <div class="fib-level">
                            <span class="fib-label">${level}</span>
                            <span class="fib-price">₹${price}</span>
                        </div>
                    `).join('')}
                </div>
            `;
            break;
        case 'volume':
            const vol = advanced.volume_profile || {};
            html = `
                <div class="volume-profile">
                    <div class="vol-item"><span>Point of Control:</span> <strong>₹${vol.poc || '-'}</strong></div>
                    <div class="vol-item"><span>Value Area High:</span> <strong>₹${vol.value_area_high || '-'}</strong></div>
                    <div class="vol-item"><span>Value Area Low:</span> <strong>₹${vol.value_area_low || '-'}</strong></div>
                </div>
            `;
            break;
        case 'pivots':
            const pivots = advanced.pivot_points || {};
            html = `
                <div class="pivot-points">
                    <div class="pivot-section">
                        <h4>Classic</h4>
                        ${pivots.classic ? Object.entries(pivots.classic).map(([key, val]) => `
                            <div class="pivot-item"><span>${key.toUpperCase()}:</span> <strong>₹${val}</strong></div>
                        `).join('') : '-'}
                    </div>
                </div>
            `;
            break;
    }
    container.innerHTML = html;
}
// Update technical details
function updateTechnicalDetails(basic) {
    const container = document.getElementById('technical-details');
    const items = [
        { label: 'Current Price', value: `₹${basic.current_price}` },
        { label: 'Trend', value: basic.trend },
        { label: 'RSI', value: `${basic.rsi} (${basic.rsi_interpretation})` },
        { label: 'MACD', value: basic.macd },
        { label: 'MACD Signal', value: basic.macd_signal },
        { label: 'MACD Histogram', value: basic.macd_histogram },
        { label: 'ATR', value: basic.atr },
        { label: 'Volume Ratio', value: basic.volume_ratio }
    ];
    // Add mode-specific indicators
    if (basic.ema_9 !== undefined) {
        items.push({ label: 'EMA 9', value: basic.ema_9 });
        items.push({ label: 'EMA 21', value: basic.ema_21 });
    }
    if (basic.ema_20 !== undefined) {
        items.push({ label: 'EMA 20', value: basic.ema_20 });
        items.push({ label: 'EMA 50', value: basic.ema_50 });
    }
    if (basic.support !== undefined) {
        items.push({ label: 'Support', value: `₹${basic.support}` });
        items.push({ label: 'Resistance', value: `₹${basic.resistance}` });
    }
    container.innerHTML = items.map(item => `
        <div class="detail-item">
            <span class="detail-label">${item.label}</span>
            <span class="detail-value">${item.value}</span>
        </div>
    `).join('');
}
// Update risk details
function updateRiskDetails(risk) {
    var _a, _b, _c, _d;
    const basic = risk.basic || {};
    const container = document.getElementById('risk-details');
    const items = [
        { label: 'Risk Level', value: basic.risk_level },
        { label: 'Stop Loss', value: `₹${((_a = basic.stop_loss) === null || _a === void 0 ? void 0 : _a.stop_loss_price) || '-'}` },
        { label: 'Stop Loss %', value: `${((_b = basic.stop_loss) === null || _b === void 0 ? void 0 : _b.stop_loss_percent) || '-'}%` },
        { label: 'Take Profit', value: `₹${((_c = basic.take_profit) === null || _c === void 0 ? void 0 : _c.take_profit_price) || '-'}` },
        { label: 'Risk-Reward Ratio', value: `1:${((_d = basic.take_profit) === null || _d === void 0 ? void 0 : _d.risk_reward_ratio) || '-'}` }
    ];
    container.innerHTML = items.map(item => `
        <div class="detail-item">
            <span class="detail-label">${item.label}</span>
            <span class="detail-value">${item.value}</span>
        </div>
    `).join('');
}
function updateFinnhubInsights(insights, externalSignal) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k;
    const card = document.getElementById('finnhub-card');
    const container = document.getElementById('finnhub-insights');
    if (!card || !container)
        return;
    if ((!insights || insights.available !== true) && !externalSignal) {
        card.style.display = 'none';
        container.innerHTML = '';
        return;
    }
    const rec = (insights && insights.analyst_recommendation) || {};
    const target = (insights && insights.price_target) || {};
    const quote = (insights && insights.market_snapshot) || {};
    const profile = (insights && insights.company_profile) || {};
    const coverage = (externalSignal && externalSignal.coverage) || {};
    const drivers = (externalSignal && externalSignal.drivers) || {};
    const asRupee = (val) => {
        const num = Number(val);
        return Number.isFinite(num) ? `₹${num.toFixed(2)}` : '-';
    };
    const asPercent = (val) => {
        const num = Number(val);
        return Number.isFinite(num) ? `${num.toFixed(2)}%` : '-';
    };
    const items = [
        { label: 'External API Composite Stance', value: (externalSignal === null || externalSignal === void 0 ? void 0 : externalSignal.stance) ? `${externalSignal.stance} (${externalSignal.confidence_percent || '-'}%)` : '-' },
        { label: 'External Composite Score', value: (_a = externalSignal === null || externalSignal === void 0 ? void 0 : externalSignal.composite_score) !== null && _a !== void 0 ? _a : '-' },
        { label: 'Articles Analyzed (multi-API)', value: (_b = coverage.analyzed_articles) !== null && _b !== void 0 ? _b : '-' },
        { label: 'Consensus', value: rec.consensus || '-' },
        { label: 'Total Analyst Ratings', value: (_c = rec.total_ratings) !== null && _c !== void 0 ? _c : '-' },
        { label: 'Strong Buy / Buy / Hold / Sell / Strong Sell', value: `${(_d = rec.strong_buy) !== null && _d !== void 0 ? _d : 0} / ${(_e = rec.buy) !== null && _e !== void 0 ? _e : 0} / ${(_f = rec.hold) !== null && _f !== void 0 ? _f : 0} / ${(_g = rec.sell) !== null && _g !== void 0 ? _g : 0} / ${(_h = rec.strong_sell) !== null && _h !== void 0 ? _h : 0}` },
        { label: 'Current Price (Finnhub)', value: asRupee(quote.current) },
        { label: 'Mean Target', value: asRupee(target.target_mean) },
        { label: 'Target High / Low', value: `${asRupee(target.target_high)} / ${asRupee(target.target_low)}` },
        { label: 'Upside vs Current', value: asPercent(target.upside_percent_vs_current) },
        { label: 'Daily Change', value: `${asRupee(quote.change)} (${asPercent(quote.change_percent)})` },
        { label: 'Company / Industry', value: profile.name ? `${profile.name} (${profile.finnhub_industry || '-'})` : '-' },
        { label: 'News Sentiment Driver', value: (_j = drivers.news_sentiment_score) !== null && _j !== void 0 ? _j : '-' },
        { label: 'News Pos:Neg', value: (_k = drivers.news_positive_vs_negative) !== null && _k !== void 0 ? _k : '-' },
        { label: 'Signal Summary', value: (insights && insights.signal_summary) || '-' }
    ];
    card.style.display = 'block';
    container.innerHTML = items.map(item => `
        <div class="detail-item">
            <span class="detail-label">${escapeHtml(item.label)}</span>
            <span class="detail-value">${escapeHtml(item.value)}</span>
        </div>
    `).join('');
}
// Update sentiment details
function updateSentimentDetails(sentiment) {
    console.log('[SENTIMENT] Received sentiment data:', sentiment);
    const container = document.getElementById('sentiment-details');
    const breakdown = sentiment.breakdown || {};
    const articles = sentiment.news_articles || [];
    const sources = sentiment.sources || [];
    const scope = sentiment.analysis_scope || {};
    const capabilities = sentiment.api_capabilities || {};
    const providerCounts = capabilities.provider_article_counts || {};
    const configuredKeys = capabilities.configured_keys || {};
    const fetchMethod = sentiment.fetch_method || 'unknown';
    console.log('[SENTIMENT] Articles count:', articles.length);
    console.log('[SENTIMENT] Breakdown:', breakdown);
    console.log('[SENTIMENT] Sources:', sources);
    // Update sentiment stats
    container.innerHTML = `
        <div class="sentiment-stat">
            <div class="stat-value">${breakdown.positive || 0}</div>
            <div class="stat-label">Positive</div>
        </div>
        <div class="sentiment-stat">
            <div class="stat-value">${breakdown.neutral || 0}</div>
            <div class="stat-label">Neutral</div>
        </div>
        <div class="sentiment-stat">
            <div class="stat-value">${breakdown.negative || 0}</div>
            <div class="stat-label">Negative</div>
        </div>
        <div class="sentiment-stat">
            <div class="stat-value">${sentiment.headlines_count || 0}</div>
            <div class="stat-label">Articles</div>
        </div>
    `;
    // Update sources
    const sourcesContainer = document.getElementById('news-sources');
    if (sources.length > 0) {
        const sourceSummary = `GNews: ${providerCounts.gnews || 0} | Finnhub: ${providerCounts.finnhub || 0} | NewsData: ${providerCounts.newsdata || 0}`;
        const keySummary = `Keys -> GNews: ${configuredKeys.gnews ? 'Yes' : 'No'}, Finnhub: ${configuredKeys.finnhub ? 'Yes' : 'No'}, NewsData: ${configuredKeys.newsdata ? 'Yes' : 'No'}`;
        sourcesContainer.innerHTML = `
            <div style="margin-bottom: 16px; padding: 12px; background: var(--bg-secondary); border-radius: var(--radius);">
                <strong style="color: var(--primary);">📡 News Sources:</strong> ${sources.join(', ')}
            </div>
            <div style="margin-bottom: 16px; padding: 12px; background: rgba(0, 212, 255, 0.06); border: 1px solid rgba(0,212,255,0.25); border-radius: var(--radius);">
                <div style="color: var(--text-primary); margin-bottom: 6px;"><strong>Provider Utilization</strong> (${escapeHtml(fetchMethod)})</div>
                <div style="color: var(--text-secondary); font-size: 0.86rem; line-height: 1.5;">
                    ${escapeHtml(sourceSummary)}<br>
                    ${escapeHtml(keySummary)}<br>
                    Fetched: <strong>${scope.total_fetched_articles || articles.length}</strong> | 
                    Analyzed: <strong>${scope.articles_analyzed_for_sentiment || articles.length}</strong> | 
                    Showing: <strong>${scope.articles_shown || articles.length}</strong> top-impact items
                </div>
            </div>
        `;
    }
    else {
        sourcesContainer.innerHTML = '';
    }
    // Update news articles list
    const articlesContainer = document.getElementById('news-articles');
    if (articles.length > 0) {
        // Store articles globally for access from click handlers
        window.newsArticles = articles;
        articlesContainer.innerHTML = `
            <div style="margin-top: 20px;">
                <h4 style="margin-bottom: 12px; color: var(--text-primary);">📰 Top Impact News (Severely affecting near-term price)</h4>
                <div style="max-height: 400px; overflow-y: auto;">
                    ${articles.map((article, index) => {
            var _a;
            const displaySource = article.source || 'News Source';
            const displayTitle = article.title || 'Stock News Update';
            const severity = article.impact_severity || 'Low';
            const impactScore = (_a = article.impact_score) !== null && _a !== void 0 ? _a : '-';
            const severityColor = severity === 'High' ? '#ef4444' : (severity === 'Medium' ? '#f59e0b' : '#10b981');
            return `
                            <div class="news-article-item" data-article-index="${index}" style="padding: 12px; border-bottom: 1px solid var(--border-color); cursor: pointer; transition: all 0.3s ease;">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;">
                                    <div style="flex: 1;">
                                        <div style="font-size: 0.9rem; color: var(--primary); margin-bottom: 4px; font-weight: 500;">${displayTitle}</div>
                                        <div style="font-size: 0.75rem; color: var(--text-muted);">
                                            📍 ${displaySource}
                                            ${article.published_at ? ` • ${new Date(article.published_at).toLocaleDateString()}` : ''}
                                        </div>
                                        <div style="margin-top: 6px; font-size: 0.75rem;">
                                            <span style="padding: 2px 8px; border-radius: 999px; background: rgba(0,0,0,0.25); border: 1px solid ${severityColor}; color: ${severityColor};">${severity} Impact</span>
                                            <span style="margin-left: 8px; color: var(--text-secondary);">Score: ${impactScore}</span>
                                        </div>
                                    </div>
                                    <div style="font-size: 1.2rem; color: var(--primary); opacity: 0.7;">📖</div>
                                </div>
                            </div>
                        `;
        }).join('')}
                </div>
            </div>
        `;
        // Add click event listeners to all article items
        articlesContainer.querySelectorAll('.news-article-item').forEach(item => {
            item.addEventListener('mouseenter', function () {
                this.style.backgroundColor = 'var(--bg-tertiary)';
                this.style.borderLeft = '4px solid var(--primary)';
                this.style.paddingLeft = '8px';
            });
            item.addEventListener('mouseleave', function () {
                this.style.backgroundColor = 'transparent';
                this.style.borderLeft = 'none';
                this.style.paddingLeft = '12px';
            });
            item.addEventListener('click', function () {
                const articleIndex = parseInt(this.dataset.articleIndex);
                showArticleDetail(articleIndex);
            });
        });
    }
    else {
        articlesContainer.innerHTML = '';
    }
}
// Update institutional dashboard with broker intelligence
function updateInstitutionalDashboard(brokerIntel) {
    var _a, _b, _c, _d, _e, _f, _g;
    console.log('[INSTITUTIONAL DASHBOARD] Received data:', brokerIntel);
    // Always get fresh element references
    const dashboardContainer = document.getElementById('institutional-dashboard');
    if (!dashboardContainer) {
        console.error('[INSTITUTIONAL DASHBOARD] Container not found');
        return;
    }
    // Ensure dashboard is visible
    dashboardContainer.style.display = 'block';
    
    const kpiContainer = document.getElementById('kpi-metrics');
    const dashChartsContainer = document.getElementById('dashboard-charts');
    
    // If containers don't exist, create them
    if (!kpiContainer || !dashChartsContainer) {
        dashboardContainer.innerHTML = `
            <h3>Institutional Dashboard</h3>
            <div id="kpi-metrics" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;"></div>
            <div id="dashboard-charts"></div>
        `;
    }
    
    const freshKpiContainer = document.getElementById('kpi-metrics');
    const freshDashChartsContainer = document.getElementById('dashboard-charts');
    
    if (!freshKpiContainer) {
        console.error('[INSTITUTIONAL DASHBOARD] KPI container not found even after recreation');
        return;
    }
    
    console.log('[INSTITUTIONAL DASHBOARD] Containers found, populating data...');
    
    // Extract broker data with safe defaults
    const brokerRec = brokerIntel?.broker_recommendation || {};
    const analystConsensus = brokerIntel?.analyst_consensus || {};
    const dividends = brokerIntel?.dividend_information || {};
    const earnings = brokerIntel?.earnings_information || {};
    const sectorComp = brokerIntel?.sector_comparison || {};
    const newsAnalysis = brokerIntel?.news_analysis || {};
    const corpActions = brokerIntel?.corporate_actions || {};
    
    console.log('[INSTITUTIONAL DASHBOARD] Extracted data:', {
        brokerRec,
        analystConsensus,
        dividends,
        earnings,
        sectorComp,
        newsAnalysis,
        corpActions
    });
    
    // Helper for color coding
    const getRecColor = (rec) => {
        if (!rec) return '#f59e0b';
        if (rec.includes('BUY')) return '#10b981';
        if (rec.includes('SELL')) return '#ef4444';
        return '#f59e0b';
    };
    
    // Build KPI metrics with enhanced styling
    const kpiHtml = `
        <div class="kpi-card" style="background: var(--bg-tertiary); padding: 16px; border-radius: 12px; border: 1px solid var(--border-color); text-align: center;">
            <div class="kpi-label" style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Broker Recommendation</div>
            <div class="kpi-value" style="font-size: 1.4rem; font-weight: 700; color: ${getRecColor(brokerRec.recommendation)}; margin-bottom: 4px;">${brokerRec.recommendation || '-'}</div>
            <div class="kpi-subtext" style="font-size: 0.8rem; color: var(--text-secondary);">${brokerRec.conviction || brokerRec.risk_level || '-'}</div>
        </div>
        <div class="kpi-card" style="background: var(--bg-tertiary); padding: 16px; border-radius: 12px; border: 1px solid var(--border-color); text-align: center;">
            <div class="kpi-label" style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Analyst Rating</div>
            <div class="kpi-value" style="font-size: 1.4rem; font-weight: 700; color: var(--primary); margin-bottom: 4px;">${analystConsensus.consensus_rating || '-'}</div>
            <div class="kpi-subtext" style="font-size: 0.8rem; color: var(--text-secondary);">${analystConsensus.number_of_analysts || 0} analysts</div>
        </div>
        <div class="kpi-card" style="background: var(--bg-tertiary); padding: 16px; border-radius: 12px; border: 1px solid var(--border-color); text-align: center;">
            <div class="kpi-label" style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Dividend Yield</div>
            <div class="kpi-value" style="font-size: 1.4rem; font-weight: 700; color: var(--primary); margin-bottom: 4px;">${dividends.dividend_yield ? dividends.dividend_yield.toFixed(2) + '%' : '-'}</div>
            <div class="kpi-subtext" style="font-size: 0.8rem; color: var(--text-secondary);">${dividends.last_dividend_date ? dividends.last_dividend_date.substring(0, 10) : '-'}</div>
        </div>
        <div class="kpi-card" style="background: var(--bg-tertiary); padding: 16px; border-radius: 12px; border: 1px solid var(--border-color); text-align: center;">
            <div class="kpi-label" style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Next Earnings</div>
            <div class="kpi-value" style="font-size: 1.4rem; font-weight: 700; color: var(--primary); margin-bottom: 4px;">${earnings.next_earnings_date ? earnings.next_earnings_date.substring(0, 10) : '-'}</div>
            <div class="kpi-subtext" style="font-size: 0.8rem; color: var(--text-secondary);">PE: ${earnings.pe_ratio || '-'}</div>
        </div>
        <div class="kpi-card" style="background: var(--bg-tertiary); padding: 16px; border-radius: 12px; border: 1px solid var(--border-color); text-align: center;">
            <div class="kpi-label" style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Sector</div>
            <div class="kpi-value" style="font-size: 1.4rem; font-weight: 700; color: var(--primary); margin-bottom: 4px;">${sectorComp.sector || '-'}</div>
            <div class="kpi-subtext" style="font-size: 0.8rem; color: var(--text-secondary);">${sectorComp.industry || 'Unknown'}</div>
        </div>
        <div class="kpi-card" style="background: var(--bg-tertiary); padding: 16px; border-radius: 12px; border: 1px solid var(--border-color); text-align: center;">
            <div class="kpi-label" style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">News Sentiment</div>
            <div class="kpi-value" style="font-size: 1.4rem; font-weight: 700; color: ${((_a = newsAnalysis.news_sentiment_distribution) === null || _a === void 0 ? void 0 : _a.positive) > ((_b = newsAnalysis.news_sentiment_distribution) === null || _b === void 0 ? void 0 : _b.negative) ? '#10b981' : '#ef4444'}; margin-bottom: 4px;">${newsAnalysis.total_articles || 0} articles</div>
            <div class="kpi-subtext" style="font-size: 0.8rem; color: var(--text-secondary);">${((_c = newsAnalysis.news_sentiment_distribution) === null || _c === void 0 ? void 0 : _c.positive) || 0}+ / ${((_d = newsAnalysis.news_sentiment_distribution) === null || _d === void 0 ? void 0 : _d.negative) || 0}-</div>
        </div>
    `;
    
    console.log('[INSTITUTIONAL DASHBOARD] Setting KPI HTML...');
    freshKpiContainer.innerHTML = kpiHtml;
    
    // Add enhanced dashboard insights with corporate actions
    if (freshDashChartsContainer) {
        const hasSplits = corpActions?.stock_splits && corpActions.stock_splits.length > 0;
        const hasDividends = corpActions?.recent_dividends && corpActions.recent_dividends.length > 0;
        
        freshDashChartsContainer.innerHTML = `
            <div style="padding: 20px; background: var(--bg-secondary); border-radius: 12px; margin-bottom: 16px; border: 1px solid var(--border-color);">
                <h4 style="margin-bottom: 16px; color: var(--text-primary); font-size: 1.1rem;">📊 Trading Insights</h4>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 16px;">
                    <div style="padding: 16px; background: var(--bg-tertiary); border-radius: 8px; text-align: center;">
                        <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Entry Point</div>
                        <div style="font-size: 1.4rem; font-weight: 600; color: var(--primary);">₹${brokerRec.entry_point ? brokerRec.entry_point.toFixed(2) : '-'}</div>
                    </div>
                    <div style="padding: 16px; background: var(--bg-tertiary); border-radius: 8px; text-align: center;">
                        <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Stop Loss</div>
                        <div style="font-size: 1.4rem; font-weight: 600; color: #ef4444;">₹${brokerRec.stop_loss ? brokerRec.stop_loss.toFixed(2) : '-'}</div>
                    </div>
                    <div style="padding: 16px; background: var(--bg-tertiary); border-radius: 8px; text-align: center;">
                        <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Target 1</div>
                        <div style="font-size: 1.4rem; font-weight: 600; color: #10b981;">₹${((_e = brokerRec.targets) === null || _e === void 0 ? void 0 : _e.target_1) ? brokerRec.targets.target_1.toFixed(2) : '-'}</div>
                    </div>
                    <div style="padding: 16px; background: var(--bg-tertiary); border-radius: 8px; text-align: center;">
                        <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Risk-Reward</div>
                        <div style="font-size: 1.4rem; font-weight: 600; color: var(--primary);">1:${brokerRec.risk_reward_ratio || '-'}</div>
                    </div>
                </div>
                
                ${hasSplits || hasDividends ? `
                    <div style="padding: 16px; background: rgba(245, 158, 11, 0.1); border-radius: 8px; border-left: 3px solid #f59e0b;">
                        <h5 style="margin: 0 0 12px 0; color: #f59e0b; font-size: 1rem;">⚡ Recent Corporate Actions</h5>
                        ${hasSplits ? `
                            <div style="margin-bottom: 10px;">
                                <strong style="color: var(--text-secondary);">Stock Splits:</strong>
                                <span style="color: var(--text-primary);">${corpActions.stock_splits.slice(0, 2).join(', ')}</span>
                            </div>
                        ` : ''}
                        ${hasDividends ? `
                            <div>
                                <strong style="color: var(--text-secondary);">Recent Dividends:</strong>
                                <span style="color: var(--text-primary);">${corpActions.recent_dividends.slice(0, 2).join(', ')}</span>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    console.log('[INSTITUTIONAL DASHBOARD] Dashboard populated successfully');
}
// Update prediction chart
function updatePredictionChart(aiPrediction) {
    const canvas = document.getElementById('prediction-chart');
    if (!canvas)
        return;
    // Destroy existing chart
    if (predictionChart) {
        predictionChart.destroy();
        predictionChart = null;
    }
    if (!aiPrediction || !aiPrediction.chart_data)
        return;
    const chartData = aiPrediction.chart_data;
    // Create combined labels with clear separation
    const labels = chartData.labels || [];
    const historical = chartData.historical || [];
    const predicted = chartData.predicted || [];
    // Create datasets with null separation
    const historicalData = [...historical];
    const predictedData = new Array(historical.length).fill(null);
    // Add predicted values with one connecting point
    if (predicted.length > 0) {
        // Connect last historical to first predicted
        historicalData.push(predicted[0]);
        predictedData[historicalData.length - 1] = predicted[0];
        // Add remaining predictions
        for (let i = 1; i < predicted.length; i++) {
            historicalData.push(null);
            predictedData.push(predicted[i]);
        }
    }
    const ctx = canvas.getContext('2d');
    predictionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Past Prices (Historical)',
                    data: historicalData,
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 3
                },
                {
                    label: 'Future Prediction (AI Forecast)',
                    data: predictedData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                    pointRadius: 4,
                    pointStyle: 'rectRot'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#9ca3af',
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.9)',
                    titleColor: '#f9fafb',
                    bodyColor: '#9ca3af',
                    borderColor: 'rgba(0, 212, 255, 0.3)',
                    borderWidth: 1,
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += '₹' + context.parsed.y.toFixed(2);
                            }
                            return label;
                        }
                    }
                },
                annotation: {
                    annotations: {
                        line1: {
                            type: 'line',
                            xMin: historical.length - 1,
                            xMax: historical.length - 1,
                            borderColor: 'rgba(245, 158, 11, 0.5)',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: {
                                content: 'Today →',
                                enabled: true,
                                position: 'start',
                                color: '#f59e0b'
                            }
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        callback: function (value) {
                            return '₹' + value.toFixed(2);
                        }
                    },
                    title: {
                        display: true,
                        text: 'Stock Price (₹)',
                        color: '#6b7280'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        maxRotation: 45
                    },
                    title: {
                        display: true,
                        text: 'Date / Predicted Date',
                        color: '#6b7280'
                    }
                }
            }
        }
    });
    // Update chart description with clearer explanation
    const chartDesc = document.querySelector('.chart-description');
    if (chartDesc) {
        chartDesc.innerHTML = `
            <strong style="color: #00d4ff;">Blue solid line:</strong> Actual historical prices (past 30 days) | 
            <strong style="color: #10b981;">Green dashed line:</strong> AI-predicted future prices (next 5 periods) | 
            <strong style="color: #f59e0b;">Orange line:</strong> Today (current date)
        `;
    }
}
function escapeHtml(text) {
    if (text === null || text === undefined)
        return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
function updateAIPredictionTransparency(aiPrediction, sentiment, technical) {
    var _a;
    const guideBox = document.getElementById('ai-prediction-guide');
    const detailsBox = document.getElementById('ai-transparency-details');
    if (!guideBox || !detailsBox)
        return;
    const transparency = (aiPrediction === null || aiPrediction === void 0 ? void 0 : aiPrediction.transparency) || {};
    const guideTerms = (transparency.guide_terms && transparency.guide_terms.length > 0)
        ? transparency.guide_terms
        : [
            { term: 'RSI', meaning: 'Momentum indicator; extreme values can signal potential reversal risk.' },
            { term: 'MACD', meaning: 'Trend momentum signal based on moving-average spread.' },
            { term: 'Confidence', meaning: 'Model certainty estimate, not a guarantee.' },
            { term: 'Risk Level', meaning: 'Estimated downside uncertainty from volatility and signal quality.' }
        ];
    guideBox.innerHTML = `
        <div class="ai-guide-title">🧭 AI Terms Guide</div>
        <div class="ai-guide-grid">
            ${guideTerms.slice(0, 6).map(item => `
                <div class="ai-guide-item">
                    <strong>${escapeHtml(item.term)}</strong>
                    <span>${escapeHtml(item.meaning)}</span>
                </div>
            `).join('')}
        </div>
    `;
    const summary = transparency.summary || (aiPrediction === null || aiPrediction === void 0 ? void 0 : aiPrediction.reasoning) || 'Explanation will be available after analysis.';
    const keyFactors = ((aiPrediction === null || aiPrediction === void 0 ? void 0 : aiPrediction.key_factors) || []).slice(0, 5);
    const articleDrivers = (transparency.article_drivers || []).slice(0, 3);
    const geopolitical = (transparency.geopolitical_scenarios || []).slice(0, 3);
    const trendSignals = (transparency.market_trend_signals || []).slice(0, 4);
    const technicalTrend = ((_a = technical === null || technical === void 0 ? void 0 : technical.basic) === null || _a === void 0 ? void 0 : _a.trend) || 'Neutral';
    const sentimentClass = (sentiment === null || sentiment === void 0 ? void 0 : sentiment.sentiment_classification) || 'Neutral';
    detailsBox.innerHTML = `
        <h4>🔍 Why this prediction was made</h4>
        <div class="ai-transparency-item"><strong>Summary:</strong> ${escapeHtml(summary)}</div>
        <div class="ai-transparency-item"><strong>Market Trend:</strong> ${escapeHtml(technicalTrend)} | <strong>Sentiment:</strong> ${escapeHtml(sentimentClass)}</div>
        ${keyFactors.length ? `
            <div class="ai-transparency-list">
                ${keyFactors.map(factor => `<div class="ai-transparency-item">• ${escapeHtml(factor)}</div>`).join('')}
            </div>
        ` : ''}
        ${articleDrivers.length ? `
            <h4>📰 Article drivers</h4>
            <div class="ai-transparency-list">
                ${articleDrivers.map(article => `
                    <div class="ai-transparency-item">
                        <strong>${escapeHtml(article.source || 'Source')}</strong>: ${escapeHtml(article.title || 'News update')}
                        ${article.url ? `<div><a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer">Open source</a></div>` : ''}
                    </div>
                `).join('')}
            </div>
        ` : ''}
        ${geopolitical.length ? `
            <h4>🌍 Geopolitical context considered</h4>
            <div class="ai-transparency-list">
                ${geopolitical.map(item => `<div class="ai-transparency-item">• ${escapeHtml(item)}</div>`).join('')}
            </div>
        ` : ''}
        ${trendSignals.length ? `
            <h4>📈 Market trend signals considered</h4>
            <div class="ai-transparency-list">
                ${trendSignals.map(signal => `
                    <div class="ai-transparency-item">
                        <strong>${escapeHtml(signal.factor || '')}:</strong> ${escapeHtml(signal.value || '')}
                        ${signal.impact ? `<div>${escapeHtml(signal.impact)}</div>` : ''}
                    </div>
                `).join('')}
            </div>
        ` : ''}
    `;
}
// Helper functions
function formatMetricName(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}
function formatMetricValue(key, value) {
    if (typeof value === 'number') {
        // Add % for certain metrics
        if (['roe', 'roa', 'roic', 'gross_margin', 'operating_margin',
            'profit_margin', 'revenue_growth', 'earnings_growth', 'dividend_yield'].includes(key)) {
            return `${value.toFixed(2)}%`;
        }
        return value.toFixed(2);
    }
    return value;
}
// Show article detail modal
function showArticleDetail(index) {
    if (!window.newsArticles || !window.newsArticles[index]) {
        console.error('Article not found');
        return;
    }
    const article = window.newsArticles[index];
    // Create or get modal
    let modal = document.getElementById('article-detail-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'article-detail-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 700px; max-height: 80vh; overflow-y: auto;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid var(--border-color);">
                    <h3 id="article-modal-title" style="margin: 0; flex: 1;">Article Details</h3>
                    <button class="modal-close" onclick="closeArticleDetail()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-secondary);">×</button>
                </div>
                <div id="article-content" style="padding: 20px 0;"></div>
                <div style="display: flex; gap: 12px; margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--border-color);">
                    <button onclick="closeArticleDetail()" class="btn-secondary" style="flex: 1;">Close</button>
                    <button id="article-open-btn" onclick="openArticleExternal()" class="btn-primary" style="flex: 1;">Read Full Article ↗</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal)
                closeArticleDetail();
        });
    }
    // Store only the original article URL (no title-search fallback)
    window.currentArticleUrl = (article.url || '').trim();
    const hasRealUrl = window.currentArticleUrl.length > 0;
    // Populate content
    const title = article.title || 'News Article';
    const source = article.source || 'Unknown Source';
    const url = article.url || '';
    const published = article.published_at ? new Date(article.published_at).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }) : 'Date not available';
    document.getElementById('article-modal-title').textContent = title;
    document.getElementById('article-content').innerHTML = `
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;">
                <span style="background: var(--primary); color: var(--bg-primary); padding: 6px 12px; border-radius: 4px; font-size: 0.85rem; font-weight: 600;">📰 ${source}</span>
                <span style="color: var(--text-secondary); font-size: 0.9rem;">📅 ${published}</span>
            </div>

            <h2 style="font-size: 1.4rem; color: var(--text-primary); line-height: 1.6; margin-bottom: 16px;">
                ${title}
            </h2>

            ${url ? `
                <div style="padding: 12px; background: var(--bg-secondary); border-left: 3px solid var(--primary); border-radius: 4px; margin-bottom: 16px;">
                    <strong style="color: var(--primary);">Source URL:</strong><br>
                    <a href="${url}" target="_blank" style="color: var(--primary); text-decoration: none; word-break: break-all; font-size: 0.9rem;">
                        ${url.substring(0, 80)}${url.length > 80 ? '...' : ''}
                    </a>
                </div>
            ` : `
                <div style="padding: 12px; background: rgba(239,68,68,0.1); border-left: 3px solid #ef4444; border-radius: 4px; margin-bottom: 16px;">
                    <strong style="color: #ef4444;">Original URL unavailable for this item.</strong>
                </div>
            `}

            <div style="padding: 16px; background: var(--bg-secondary); border-radius: 6px; line-height: 1.8; color: var(--text-primary);">
                <p style="margin: 0;">
                    This news article is related to your stock analysis. Click "Read Full Article" to view the complete story on the original source.
                </p>
                <br>
                <p style="margin: 0; font-size: 0.9rem; color: var(--text-secondary);">
                    <strong>💡 Tip:</strong> This article's sentiment has been analyzed and factored into your stock's overall sentiment score.
                </p>
            </div>
        </div>
    `;
    // Disable open button when URL is missing.
    const openBtn = document.getElementById('article-open-btn');
    if (openBtn) {
        openBtn.disabled = !hasRealUrl;
        openBtn.style.opacity = hasRealUrl ? '1' : '0.5';
        openBtn.style.cursor = hasRealUrl ? 'pointer' : 'not-allowed';
    }
    // Show modal
    modal.style.display = 'flex';
}
// Close article detail modal
function closeArticleDetail() {
    const modal = document.getElementById('article-detail-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}
// Open article in new tab
function openArticleExternal() {
    if (!window.currentArticleUrl) {
        showToast('Original article URL is not available for this item', 'info');
        return;
    }
    window.open(window.currentArticleUrl, '_blank', 'noopener,noreferrer');
}
// ============ ADVANCED AI FEATURES ============
// LSTM Training & Prediction
async function trainLSTM() {
    const els = getAnalysisElements();
    const symbol = normalizeSymbol(els.symbolInput ? els.symbolInput.value : '');
    if (!symbol) {
        showToast('Please enter a stock symbol', 'error');
        return;
    }
    const btn = document.getElementById('lstm-train-btn');
    const container = document.getElementById('lstm-forecast');
    const originalText = btn.textContent;
    btn.textContent = '⏳ Running LSTM forecast...';
    btn.disabled = true;
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai/lstm/train?symbol=${symbol}&epochs=8`);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'LSTM run failed');
        }
        const data = await response.json();
        if (data.status === 'success') {
            showToast('✅ LSTM trained successfully!', 'success');
            // Get predictions
            const predResponse = await fetch(`${API_BASE_URL}/api/ai/lstm/predict?symbol=${symbol}`);
            if (!predResponse.ok) {
                const err = await predResponse.json();
                throw new Error(err.detail || 'LSTM prediction failed');
            }
            const predictions = await predResponse.json();
            container.innerHTML = `
                <div style="background: rgba(0,212,255,0.1); padding: 15px; border-radius: 8px; border-left: 3px solid #00d4ff;">
                    <h4 style="color: #00d4ff; margin-top: 0;">5-Day Price Forecast (LSTM - 75% Accuracy)</h4>
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 10px;">
                        ${predictions.predictions.map((p, i) => `
                            <div style="background: var(--bg-secondary); padding: 10px; border-radius: 6px; text-align: center;">
                                <div style="color: var(--text-secondary); font-size: 0.85rem;">Day ${i + 1}</div>
                                <div style="color: #00d4ff; font-weight: bold; font-size: 1.1rem;">₹${p.toFixed(2)}</div>
                            </div>
                        `).join('')}
                    </div>
                    <p style="margin-top: 10px; color: var(--text-secondary); font-size: 0.9rem;">Confidence: ${predictions.confidence}</p>
                </div>
            `;
        }
    }
    catch (error) {
        console.error('LSTM Error:', error);
        showToast('LSTM training failed: ' + error.message, 'error');
    }
    finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}
// Transformer Training & Prediction
async function trainTransformer() {
    const els = getAnalysisElements();
    const symbol = normalizeSymbol(els.symbolInput ? els.symbolInput.value : '');
    if (!symbol) {
        showToast('Please enter a stock symbol', 'error');
        return;
    }
    const btn = document.getElementById('transformer-train-btn');
    const container = document.getElementById('transformer-forecast');
    const originalText = btn.textContent;
    btn.textContent = '⏳ Running Transformer forecast...';
    btn.disabled = true;
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai/transformer/train?symbol=${symbol}&epochs=6`);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Transformer run failed');
        }
        const data = await response.json();
        if (data.status === 'success') {
            showToast('✅ Transformer trained successfully!', 'success');
            // Get predictions
            const predResponse = await fetch(`${API_BASE_URL}/api/ai/transformer/predict?symbol=${symbol}`);
            if (!predResponse.ok) {
                const err = await predResponse.json();
                throw new Error(err.detail || 'Transformer prediction failed');
            }
            const predictions = await predResponse.json();
            container.innerHTML = `
                <div style="background: rgba(16,185,129,0.1); padding: 15px; border-radius: 8px; border-left: 3px solid #10b981;">
                    <h4 style="color: #10b981; margin-top: 0;">5-Day Price Forecast (Transformer - Faster)</h4>
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 10px;">
                        ${predictions.predictions.map((p, i) => `
                            <div style="background: var(--bg-secondary); padding: 10px; border-radius: 6px; text-align: center;">
                                <div style="color: var(--text-secondary); font-size: 0.85rem;">Day ${i + 1}</div>
                                <div style="color: #10b981; font-weight: bold; font-size: 1.1rem;">₹${p.toFixed(2)}</div>
                            </div>
                        `).join('')}
                    </div>
                    <p style="margin-top: 10px; color: var(--text-secondary); font-size: 0.9rem;">Speed: 30-80ms inference</p>
                </div>
            `;
        }
    }
    catch (error) {
        console.error('Transformer Error:', error);
        showToast('Transformer training failed: ' + error.message, 'error');
    }
    finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}
// Portfolio Optimization (RL)
async function optimizePortfolio() {
    const els = getAnalysisElements();
    const symbol = normalizeSymbol(els.symbolInput ? els.symbolInput.value : '');
    if (!symbol) {
        showToast('Please enter a stock symbol', 'error');
        return;
    }
    const btn = document.getElementById('portfolio-optimize-btn');
    const container = document.getElementById('portfolio-optimization');
    btn.textContent = '⏳ Optimizing...';
    btn.disabled = true;
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai/portfolio/optimize?symbols=${symbol}`);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Portfolio optimization failed');
        }
        const data = await response.json();
        container.innerHTML = `
            <div style="background: rgba(245,158,11,0.1); padding: 15px; border-radius: 8px; border-left: 3px solid #f59e0b;">
                <h4 style="color: #f59e0b; margin-top: 0;">Portfolio Allocation (Q-Learning)</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">Recommendation</div>
                        <div style="color: #f59e0b; font-size: 1.3rem; font-weight: bold; margin-top: 5px;">${data.recommendation}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">Allocation %</div>
                        <div style="color: #f59e0b; font-size: 1.3rem; font-weight: bold; margin-top: 5px;">${data.allocation_percentage}%</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">Sharpe Ratio</div>
                        <div style="color: #10b981; font-size: 1.2rem; font-weight: bold; margin-top: 5px;">${data.portfolio_sharpe_ratio}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">Avg Sentiment</div>
                        <div style="color: #00d4ff; font-size: 1.2rem; font-weight: bold; margin-top: 5px;">${data.average_sentiment.toFixed(3)}</div>
                    </div>
                </div>
            </div>
        `;
        showToast('✅ Portfolio optimized!', 'success');
    }
    catch (error) {
        console.error('Portfolio Error:', error);
        showToast('Portfolio optimization failed', 'error');
    }
    finally {
        btn.textContent = 'Optimize Now';
        btn.disabled = false;
    }
}
// Backtest RSI
async function backtestRSI() {
    const els = getAnalysisElements();
    const symbol = normalizeSymbol(els.symbolInput ? els.symbolInput.value : '');
    if (!symbol) {
        showToast('Please enter a stock symbol', 'error');
        return;
    }
    const btn = document.getElementById('backtest-rsi-btn');
    const resultsDiv = document.getElementById('backtest-results');
    btn.textContent = '⏳ Testing...';
    btn.disabled = true;
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai/backtest/rsi-strategy?symbol=${symbol}`);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'RSI backtest failed');
        }
        const data = await response.json();
        resultsDiv.innerHTML = `
            <div style="background: rgba(34,197,94,0.1); padding: 15px; border-radius: 8px; border-left: 3px solid #22c55e;">
                <h4 style="color: #22c55e; margin: 0 0 10px 0;">RSI Strategy Backtest Results</h4>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                    <div><span style="color: var(--text-secondary);">Total Return:</span><br><span style="color: #22c55e; font-weight: bold;">${data.total_return.toFixed(2)}%</span></div>
                    <div><span style="color: var(--text-secondary);">Sharpe Ratio:</span><br><span style="color: #22c55e; font-weight: bold;">${data.sharpe_ratio.toFixed(2)}</span></div>
                    <div><span style="color: var(--text-secondary);">Win Rate:</span><br><span style="color: #22c55e; font-weight: bold;">${data.win_rate.toFixed(2)}%</span></div>
                    <div><span style="color: var(--text-secondary);">Max Drawdown:</span><br><span style="color: #ef4444; font-weight: bold;">${data.max_drawdown.toFixed(2)}%</span></div>
                    <div><span style="color: var(--text-secondary);">Trades:</span><br><span style="color: #22c55e; font-weight: bold;">${data.num_trades}</span></div>
                    <div><span style="color: var(--text-secondary);">Profit/Trade:</span><br><span style="color: #22c55e; font-weight: bold;">${data.profit_per_trade.toFixed(2)}%</span></div>
                </div>
            </div>
        `;
        showToast('✅ RSI backtest complete!', 'success');
    }
    catch (error) {
        showToast('Backtest failed: ' + error.message, 'error');
    }
    finally {
        btn.textContent = 'Backtest RSI';
        btn.disabled = false;
    }
}
// Backtest MACD
async function backtestMACD() {
    var _a;
    const els = getAnalysisElements();
    const symbol = normalizeSymbol(els.symbolInput ? els.symbolInput.value : '');
    if (!symbol) {
        showToast('Please enter a stock symbol', 'error');
        return;
    }
    const btn = document.getElementById('backtest-macd-btn');
    const resultsDiv = document.getElementById('backtest-results');
    btn.textContent = '⏳ Testing...';
    btn.disabled = true;
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai/backtest/macd-strategy?symbol=${symbol}`);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'MACD backtest failed');
        }
        const data = await response.json();
        resultsDiv.innerHTML = `
            <div style="background: rgba(139,92,246,0.1); padding: 15px; border-radius: 8px; border-left: 3px solid #8b5cf6;">
                <h4 style="color: #8b5cf6; margin: 0 0 10px 0;">MACD Strategy Backtest Results</h4>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                    <div><span style="color: var(--text-secondary);">Total Return:</span><br><span style="color: #8b5cf6; font-weight: bold;">${data.total_return.toFixed(2)}%</span></div>
                    <div><span style="color: var(--text-secondary);">Sharpe Ratio:</span><br><span style="color: #8b5cf6; font-weight: bold;">${data.sharpe_ratio.toFixed(2)}</span></div>
                    <div><span style="color: var(--text-secondary);">Win Rate:</span><br><span style="color: #8b5cf6; font-weight: bold;">${data.win_rate.toFixed(2)}%</span></div>
                    <div><span style="color: var(--text-secondary);">Max Drawdown:</span><br><span style="color: #ef4444; font-weight: bold;">${data.max_drawdown.toFixed(2)}%</span></div>
                    <div><span style="color: var(--text-secondary);">Trades:</span><br><span style="color: #8b5cf6; font-weight: bold;">${data.num_trades}</span></div>
                    <div><span style="color: var(--text-secondary);">Profit/Trade:</span><br><span style="color: #8b5cf6; font-weight: bold;">${((_a = data.profit_per_trade) !== null && _a !== void 0 ? _a : 0).toFixed(2)}%</span></div>
                </div>
            </div>
        `;
        showToast('✅ MACD backtest complete!', 'success');
    }
    catch (error) {
        showToast('Backtest failed: ' + error.message, 'error');
    }
    finally {
        btn.textContent = 'Backtest MACD';
        btn.disabled = false;
    }
}
// Create Alert
async function createAlert() {
    const symbol = normalizeSymbol(document.getElementById('alert-symbol').value);
    const alertType = document.getElementById('alert-type').value;
    const threshold = document.getElementById('alert-threshold').value;
    if (!symbol || !threshold) {
        showToast('Please fill all fields', 'error');
        return;
    }
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai/alerts/create?symbol=${symbol}&alert_type=${alertType}&threshold=${threshold}`, {
            method: 'POST'
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Alert create failed');
        }
        const data = await response.json();
        showToast(`✅ Alert created: ${data.message}`, 'success');
        document.getElementById('alert-symbol').value = '';
        document.getElementById('alert-threshold').value = '';
        // Load alerts
        loadAlerts();
    }
    catch (error) {
        showToast(`Failed to create alert: ${error.message}`, 'error');
    }
}
// Load Alerts
async function loadAlerts() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai/alerts`);
        if (!response.ok) {
            const alertsList = document.getElementById('alerts-list');
            if (alertsList)
                alertsList.innerHTML = '<p style="color: var(--text-secondary);">Unable to load alerts right now.</p>';
            return;
        }
        const data = await response.json();
        const alertsList = document.getElementById('alerts-list');
        if (!data.alerts || data.alerts.length === 0) {
            alertsList.innerHTML = '<p style="color: var(--text-secondary);">No alerts set yet</p>';
            return;
        }
        alertsList.innerHTML = data.alerts.map(alert => `
            <div style="background: var(--bg-secondary); padding: 10px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${alert.symbol}</strong> - ${alert.message}
                    <br><small style="color: var(--text-secondary);">${new Date(alert.timestamp).toLocaleString()}</small>
                </div>
                <button class="btn-secondary" style="padding: 5px 10px; font-size: 0.85rem;" onclick="deleteAlert('${alert.id}')">Delete</button>
            </div>
        `).join('');
    }
    catch (error) {
        console.error('Failed to load alerts:', error);
    }
}
async function fetchLiveNewsNow(symbol) {
    var _a;
    try {
        const response = await fetch(`${API_BASE_URL}/api/broker/news-impact/${encodeURIComponent(symbol)}`);
        if (!response.ok)
            return;
        const data = await response.json();
        const normalizedSentiment = {
            sentiment_classification: data.sentiment_classification || 'Neutral',
            headlines_count: data.headlines_count || 0,
            breakdown: ((_a = data.news_analysis) === null || _a === void 0 ? void 0 : _a.news_sentiment_distribution) || { positive: 0, negative: 0, neutral: 0 },
            news_articles: data.analyzed_articles || [],
            sources: data.sources_used || []
        };
        updateSentimentDetails(normalizedSentiment);
        const sourcesContainer = document.getElementById('news-sources');
        if (sourcesContainer) {
            const stamp = data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
            const existingStamp = document.getElementById('live-news-refresh-stamp');
            if (existingStamp) {
                existingStamp.textContent = `Last live refresh: ${stamp}`;
            }
            else {
                sourcesContainer.innerHTML += `
                <div id="live-news-refresh-stamp" style="margin-top: 8px; font-size: 0.8rem; color: var(--text-muted);">
                    Last live refresh: ${stamp}
                </div>
            `;
            }
        }
    }
    catch (error) {
        console.warn('Live news refresh failed:', error);
    }
}
function startLiveNewsUpdates(symbol) {
    if (liveNewsInterval) {
        clearInterval(liveNewsInterval);
        liveNewsInterval = null;
    }
    if (!symbol)
        return;
    fetchLiveNewsNow(symbol);
    liveNewsInterval = setInterval(() => fetchLiveNewsNow(symbol), 90000);
}
async function evaluateAlertsNow(symbol) {
    try {
        const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : '';
        const response = await fetch(`${API_BASE_URL}/api/ai/alerts/evaluate${query}`);
        if (!response.ok)
            return;
        const data = await response.json();
        if (data.triggered_count > 0) {
            data.triggered_alerts.forEach(alert => {
                showToast(`🔔 Alert triggered: ${alert.symbol} (${alert.alert_type}) at ${alert.value}`, 'success');
            });
            await loadAlerts();
        }
    }
    catch (error) {
        console.warn('Alert evaluation failed:', error);
    }
}
function startLiveAlertsMonitoring(symbol) {
    if (liveAlertsInterval) {
        clearInterval(liveAlertsInterval);
        liveAlertsInterval = null;
    }
    evaluateAlertsNow(symbol);
    liveAlertsInterval = setInterval(() => evaluateAlertsNow(symbol), 20000);
}
// Delete Alert
async function deleteAlert(alertId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai/alerts/${alertId}`, { method: 'DELETE' });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Delete failed');
        }
        showToast('✅ Alert deleted', 'success');
        loadAlerts();
    }
    catch (error) {
        showToast('Failed to delete alert', 'error');
    }
}
async function explainPrediction() {
    var _a, _b, _c, _d;
    // Always get fresh element reference
    const els = getAnalysisElements();
    const symbol = normalizeSymbol(els.symbolInput ? els.symbolInput.value : '');
    if (!symbol) {
        showToast('Please enter a stock symbol', 'error');
        return;
    }
    if (!latestAnalysisData || normalizeSymbol(latestAnalysisData.symbol) !== symbol) {
        showToast('Run analysis first so explanation uses live prediction data.', 'error');
        return;
    }
    const ai = latestAnalysisData.ai_prediction || {};
    const technical = ((_a = latestAnalysisData.technical_analysis) === null || _a === void 0 ? void 0 : _a.basic) || {};
    const sentiment = latestAnalysisData.sentiment_analysis || {};
    const rawPrediction = String(ai.ai_prediction || 'NEUTRAL').toUpperCase();
    const decisionMap = { UP: 'BUY', DOWN: 'SELL', NEUTRAL: 'HOLD' };
    const decision = decisionMap[rawPrediction] || rawPrediction;
    const rawAiConfidence = String((_b = ai.confidence) !== null && _b === void 0 ? void 0 : '50').trim();
    const parsedAiConfidence = Number(rawAiConfidence.replace('%', ''));
    const confidence = Number.isFinite(parsedAiConfidence)
        ? (parsedAiConfidence <= 1 ? parsedAiConfidence * 100 : parsedAiConfidence)
        : 50;
    const indicators = {
        trend: technical.trend,
        rsi: technical.rsi,
        rsi_interpretation: technical.rsi_interpretation,
        macd_histogram: technical.macd_histogram,
        current_price: latestAnalysisData.current_price,
        predicted_prices: ai.predicted_prices || [],
        sentiment_score: sentiment.sentiment_score,
        sentiment_classification: sentiment.sentiment_classification,
        ml_up_probability: (_c = latestAnalysisData.ml_prediction) === null || _c === void 0 ? void 0 : _c.up_probability,
        geopolitical_scenarios: ((_d = ai.transparency) === null || _d === void 0 ? void 0 : _d.geopolitical_scenarios) || [],
        finnhub_insights: latestAnalysisData.finnhub_insights || {}
    };
    const container = document.getElementById('explainability');
    if (!container) {
        showToast('Explainability container not found', 'error');
        return;
    }
    // Show loading state
    container.innerHTML = '<div style="padding: 20px; text-align: center;">⏳ Generating professional explanation with geopolitical analysis...</div>';
    try {
        const params = new URLSearchParams({
            symbol,
            prediction: decision,
            confidence: confidence.toFixed(2),
            indicators: JSON.stringify(indicators)
        });
        const response = await fetch(`${API_BASE_URL}/api/ai/explainability/analyze?${params.toString()}`);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Explainability failed');
        }
        const data = await response.json();
        const confidencePercentRaw = Number(data.confidence_percent);
        const confidenceRatioRaw = Number(data.confidence);
        const confidencePercent = Number.isFinite(confidencePercentRaw)
            ? confidencePercentRaw
            : (Number.isFinite(confidenceRatioRaw) ? (confidenceRatioRaw <= 1 ? confidenceRatioRaw * 100 : confidenceRatioRaw) : 0);
        const geoReport = data.geopolitical_report || {};
        const geoDrivers = geoReport.macro_drivers || [];
        const geoChannels = geoReport.transmission_channels || [];
        const geoScenarios = geoReport.scenario_matrix || [];
        const stockView = geoReport.stock_specific_view || [];
        // ENHANCED GEOPOLITICAL DISPLAY
        container.innerHTML = `
            <div class="explainability-pro-card" style="background: var(--bg-secondary); border-radius: var(--radius); padding: 24px; margin-top: 16px;">
                <div class="explainability-header" style="border-bottom: 1px solid var(--border-color); padding-bottom: 16px; margin-bottom: 20px;">
                    <h4 style="color: var(--primary); margin: 0 0 8px 0; font-size: 1.3rem;">${escapeHtml(data.decision)} (${confidencePercent.toFixed(0)}% confidence)</h4>
                    <div class="explainability-subtitle" style="color: var(--text-secondary); font-size: 0.95rem;">Professional rationale combining technical, sentiment, AI pathing, and comprehensive geopolitical risk analysis.</div>
                </div>

                <div class="explainability-section" style="margin-bottom: 24px;">
                    <h5 style="color: var(--primary); margin-bottom: 12px; font-size: 1.1rem;">🎯 Decision Note</h5>
                    <p style="line-height: 1.7; color: var(--text-primary);">${escapeHtml(data.detailed_explanation || data.explanation || 'Detailed explanation unavailable.')}</p>
                </div>

                ${data.graph_explanation ? `
                    <div class="explainability-section" style="margin-bottom: 24px;">
                        <h5 style="color: var(--primary); margin-bottom: 12px; font-size: 1.1rem;">📊 Prediction Graph Analysis</h5>
                        <p style="line-height: 1.7; color: var(--text-secondary);">${escapeHtml(data.graph_explanation)}</p>
                    </div>
                ` : ''}

                ${(data.top_reasons || []).length ? `
                    <div class="explainability-section" style="margin-bottom: 24px;">
                        <h5 style="color: var(--primary); margin-bottom: 12px; font-size: 1.1rem;">🔝 Top Drivers</h5>
                        <ol style="padding-left: 20px; line-height: 1.8; color: var(--text-primary);">
                            ${(data.top_reasons || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                        </ol>
                    </div>
                ` : ''}

                ${(geoDrivers.length || geoChannels.length || geoScenarios.length || stockView.length) ? `
                    <div class="explainability-section" style="margin-bottom: 24px; background: rgba(0, 212, 255, 0.05); border: 1px solid rgba(0, 212, 255, 0.2); border-radius: 12px; padding: 20px;">
                        <h5 style="color: var(--primary); margin-bottom: 16px; font-size: 1.2rem; display: flex; align-items: center; gap: 8px;">
                            🌍 Comprehensive Geopolitical & Macro Analysis
                        </h5>
                        
                        ${geoDrivers.length ? `
                            <div style="margin-bottom: 20px;">
                                <div class="explainability-block-title" style="font-weight: 600; color: var(--primary); margin-bottom: 10px; font-size: 1rem;">📈 Macro Drivers</div>
                                <ul style="padding-left: 20px; line-height: 1.8; color: var(--text-primary);">
                                    ${geoDrivers.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${geoChannels.length ? `
                            <div style="margin-bottom: 20px;">
                                <div class="explainability-block-title" style="font-weight: 600; color: var(--primary); margin-bottom: 10px; font-size: 1rem;">🔄 Risk Transmission Channels</div>
                                <ul style="padding-left: 20px; line-height: 1.8; color: var(--text-primary);">
                                    ${geoChannels.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${geoScenarios.length ? `
                            <div style="margin-bottom: 20px;">
                                <div class="explainability-block-title" style="font-weight: 600; color: var(--primary); margin-bottom: 12px; font-size: 1rem;">🎲 Scenario Matrix</div>
                                <div class="explainability-scenario-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
                                    ${geoScenarios.map(sc => `
                                        <div class="explainability-scenario-item" style="background: var(--bg-tertiary); padding: 16px; border-radius: 8px; border-left: 4px solid var(--primary);">
                                            <strong style="color: var(--primary); display: block; margin-bottom: 8px;">${escapeHtml(sc.scenario || 'Scenario')}</strong>
                                            <div style="margin-bottom: 6px; color: var(--text-secondary);"><span style="color: var(--text-muted);">Probability:</span> ${escapeHtml(sc.probability || '-')}</div>
                                            <div style="margin-bottom: 6px; color: var(--text-secondary);"><span style="color: var(--text-muted);">Implication:</span> ${escapeHtml(sc.implication || '-')}</div>
                                            <div style="color: var(--text-secondary);"><span style="color: var(--text-muted);">Positioning:</span> ${escapeHtml(sc.positioning || '-')}</div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                        
                        ${stockView.length ? `
                            <div style="margin-bottom: 16px;">
                                <div class="explainability-block-title" style="font-weight: 600; color: var(--primary); margin-bottom: 10px; font-size: 1rem;">🏢 Stock-Specific Geopolitical View</div>
                                <ul style="padding-left: 20px; line-height: 1.8; color: var(--text-primary);">
                                    ${stockView.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}

                        ${data.geopolitical_analysis?.length ? `
                            <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-color);">
                                <div class="explainability-block-title" style="font-weight: 600; color: var(--primary); margin-bottom: 10px; font-size: 1rem;">📰 Geopolitical Analysis Summary</div>
                                <ul style="padding-left: 20px; line-height: 1.8; color: var(--text-primary);">
                                    ${data.geopolitical_analysis.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                ` : '<div style="padding: 16px; background: rgba(245, 158, 11, 0.1); border-radius: 8px; color: var(--text-secondary);">No detailed geopolitical data available for this analysis.</div>'}
            </div>
        `;
        showToast('✅ Professional explanation generated', 'success');
    }
    catch (error) {
        console.error('Explainability error:', error);
        container.innerHTML = `<div style="padding: 20px; color: #ef4444;">❌ Failed to generate explanation: ${escapeHtml(error.message)}</div>`;
        showToast(error.message, 'error');
    }
}
// Setup AI Feature Event Listeners
function setupAIFeatures() {
    const els = getAnalysisElements();

    // Setup logout button
    if (els.logoutBtn) {
        els.logoutBtn.addEventListener('click', handleLogout);
    }

    const lstmBtn = document.getElementById('lstm-train-btn');
    const transformerBtn = document.getElementById('transformer-train-btn');
    const portfolioBtn = document.getElementById('portfolio-optimize-btn');
    const backtestRSIBtn = document.getElementById('backtest-rsi-btn');
    const backtestMACDBtn = document.getElementById('backtest-macd-btn');
    const createAlertBtn = document.getElementById('create-alert-btn');
    const explainBtn = document.getElementById('explain-btn');
    if (lstmBtn)
        lstmBtn.addEventListener('click', trainLSTM);
    if (transformerBtn)
        transformerBtn.addEventListener('click', trainTransformer);
    if (portfolioBtn)
        portfolioBtn.addEventListener('click', optimizePortfolio);
    if (backtestRSIBtn)
        backtestRSIBtn.addEventListener('click', backtestRSI);
    if (backtestMACDBtn)
        backtestMACDBtn.addEventListener('click', backtestMACD);
    if (createAlertBtn)
        createAlertBtn.addEventListener('click', createAlert);
    if (explainBtn)
        explainBtn.addEventListener('click', explainPrediction);
    // Load alerts on init
    loadAlerts();
}
// Initialize app - ensure init() is called which sets up ALL event listeners
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('[ANALYSIS] DOM loaded, calling init()...');
        init().catch(e => console.error('[ANALYSIS] Init error:', e));
    });
} else {
    console.log('[ANALYSIS] DOM already loaded, calling init()...');
    init().catch(e => console.error('[ANALYSIS] Init error:', e));
}
