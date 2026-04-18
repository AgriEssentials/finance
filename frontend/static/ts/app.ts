// @ts-nocheck
/**
 * Professional AI Stock Analysis - Frontend Application
 * Version 2.0 with Professional Features
 */

// API Base URL
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

// DOM Elements
const elements = {
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
    tabBtns: document.querySelectorAll('.tab-btn'),
    homeView: document.getElementById('home-view'),
    analysisShell: document.getElementById('analysis-shell'),
    enterTerminalBtn: document.getElementById('enter-terminal-btn'),
    homeNavBtn: document.getElementById('home-nav-btn'),
    analysisNavBtn: document.getElementById('analysis-nav-btn')
};

function setActiveNav(view) {
    if (elements.homeNavBtn) {
        elements.homeNavBtn.classList.toggle('active', view === 'home');
    }
    if (elements.analysisNavBtn) {
        elements.analysisNavBtn.classList.toggle('active', view === 'analysis');
    }
}

function showHomeView() {
    if (elements.homeView) elements.homeView.style.display = 'block';
    if (elements.analysisShell) elements.analysisShell.style.display = 'none';
    window.location.hash = '';
    setActiveNav('home');
}

function showAnalysisView() {
    if (elements.homeView) elements.homeView.style.display = 'none';
    if (elements.analysisShell) elements.analysisShell.style.display = 'block';
    window.location.hash = 'analysis';
    setActiveNav('analysis');
}

function applyInitialView() {
    if (window.location.hash === '#analysis') {
        showAnalysisView();
        return;
    }
    showHomeView();
}

// Initialize
async function init() {
    applyInitialView();
    setupEventListeners();
    await loadPopularSymbols();
    setupAdvancedTabs();
}

// Toast notification
function showToast(message, type = 'error') {
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) existingToast.remove();
    
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
    if (!symbol) return '';
    if (symbol.includes('.')) return symbol;
    return `${symbol}.NS`;
}

// Event Listeners
function setupEventListeners() {
    if (elements.enterTerminalBtn) {
        elements.enterTerminalBtn.addEventListener('click', showAnalysisView);
    }

    if (elements.homeNavBtn) {
        elements.homeNavBtn.addEventListener('click', showHomeView);
    }

    if (elements.analysisNavBtn) {
        elements.analysisNavBtn.addEventListener('click', showAnalysisView);
    }

    // Mode selection
    elements.modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = btn.dataset.mode;
        });
    });

    // Analyze button
    elements.analyzeBtn.addEventListener('click', handleAnalyze);

    // Popular symbols
    elements.popularSymbolsBtn.addEventListener('click', () => {
        elements.symbolsModal.style.display = 'flex';
        renderSymbols('nse');
    });

    elements.modalClose.addEventListener('click', () => {
        elements.symbolsModal.style.display = 'none';
    });

    elements.symbolsModal.addEventListener('click', (e) => {
        if (e.target === elements.symbolsModal) {
            elements.symbolsModal.style.display = 'none';
        }
    });

    // Tab buttons for modal
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderSymbols(btn.dataset.tab);
        });
    });

    // Enter key on input
    elements.symbolInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAnalyze();
    });
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
    } catch (error) {
        console.error('Failed to load symbols:', error);
    }
}

// Render symbols list
function renderSymbols(exchange) {
    const symbols = popularSymbols[exchange] || [];
    elements.symbolsList.innerHTML = symbols.map(symbol => `
        <div class="symbol-item" data-symbol="${symbol}">
            <span class="symbol-code">${symbol}</span>
            <span>Select →</span>
        </div>
    `).join('');

    elements.symbolsList.querySelectorAll('.symbol-item').forEach(item => {
        item.addEventListener('click', () => {
            elements.symbolInput.value = item.dataset.symbol;
            elements.symbolsModal.style.display = 'none';
        });
    });
}

// Handle analyze
async function handleAnalyze() {
    showAnalysisView();
    const symbol = elements.symbolInput.value.trim().toUpperCase();
    const portfolioValue = parseFloat(elements.portfolioInput.value) || 1000000;
    
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
        const response = await fetch(
            `${API_BASE_URL}/api/professional/analyze?symbol=${encodeURIComponent(symbol)}&mode=${currentMode}&portfolio_value=${portfolioValue}`
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }

        const data = await response.json();
        displayResults(data);
        await fetchAndRenderProfessionalDashboard(symbol, currentMode);
        showToast('Professional analysis completed!', 'success');

    } catch (error) {
        console.error('Analysis error:', error);
        showToast(`Analysis failed: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

async function fetchAndRenderProfessionalDashboard(symbol, mode) {
    ensureDashboardSection();

    try {
        console.log('[DASHBOARD] Fetching professional dashboard data...');
        const response = await fetch(
            `${API_BASE_URL}/api/professional/dashboard?symbol=${encodeURIComponent(symbol)}&mode=${mode}`
        );
        if (!response.ok) {
            throw new Error('Advanced dashboard data unavailable');
        }

        const data = await response.json();
        console.log('[DASHBOARD] Received data:', data);
        renderDashboardKpis(data.kpis || {});
        renderDashboardCharts(data.charts || {});
        console.log('[DASHBOARD] Dashboard rendered successfully');
    } catch (error) {
        console.error('Dashboard error:', error);
        showToast('Dashboard data unavailable: ' + error.message, 'info');
    }
}

function ensureDashboardSection() {
    if (document.getElementById('pro-dashboard-card')) return;

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
    const container = document.getElementById('pro-kpis');
    if (!container) return;

    const regime = kpis.volatility_regime || '-';
    const regimeColor = regime === 'HIGH_VOL' ? '#ef4444' : regime === 'LOW_VOL' ? '#10b981' : '#f59e0b';

    container.innerHTML = `
        <div class="metric-card"><div class="metric-label">Ann. Volatility</div><div class="metric-value">${kpis.annualized_volatility_pct ?? '-'}%</div></div>
        <div class="metric-card"><div class="metric-label">Volatility Regime</div><div class="metric-value" style="color:${regimeColor}">${regime}</div></div>
        <div class="metric-card"><div class="metric-label">Max Drawdown</div><div class="metric-value">${kpis.max_drawdown_pct ?? '-'}%</div></div>
        <div class="metric-card"><div class="metric-label">VaR 95%</div><div class="metric-value">${kpis.var_95_pct ?? '-'}%</div></div>
        <div class="metric-card"><div class="metric-label">CVaR 95%</div><div class="metric-value">${kpis.cvar_95_pct ?? '-'}%</div></div>
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

// Set loading state
function setLoading(loading) {
    const btnText = elements.analyzeBtn.querySelector('.btn-text');
    const btnLoader = elements.analyzeBtn.querySelector('.btn-loader');
    
    if (loading) {
        elements.analyzeBtn.disabled = true;
        btnText.textContent = 'Analyzing...';
        btnLoader.style.display = 'inline';
    } else {
        elements.analyzeBtn.disabled = false;
        btnText.textContent = 'Run Professional Analysis';
        btnLoader.style.display = 'none';
    }
}

// Display results
function displayResults(data) {
    console.log('[DISPLAY RESULTS] Received full data:', data);
    latestAnalysisData = data;

    showAnalysisView();

    // Show results, hide empty state
    elements.emptyState.style.display = 'none';
    elements.resultsSection.style.display = 'block';
    elements.resultsSection.classList.add('active');

    // Update price card
    document.getElementById('result-symbol').textContent = data.symbol;
    document.getElementById('result-mode').textContent = data.mode;
    document.getElementById('result-price').textContent = data.current_price.toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    document.getElementById('price-timestamp').textContent = 
        `Last updated: ${new Date(data.timestamp).toLocaleString('en-IN')}`;

    // Update professional recommendation
    updateProfessionalRecommendation(data.professional_recommendation);

    // Update key metrics
    document.getElementById('metric-trend').textContent = data.technical_analysis.basic.trend;
    document.getElementById('metric-rsi').textContent = 
        `${data.technical_analysis.basic.rsi} (${data.technical_analysis.basic.rsi_interpretation})`;
    document.getElementById('metric-ai').textContent = data.ai_prediction.ai_prediction || 'NEUTRAL';
    document.getElementById('metric-risk').textContent = data.risk_management.basic.risk_level;

    // Update position sizing
    updatePositionSizing(data.risk_management.professional?.position_sizing);

    // Update fundamental analysis
    updateFundamentalAnalysis(data.fundamental_analysis);

    // Update advanced indicators
    updateAdvancedIndicators(data.technical_analysis.advanced);

    // Update technical details
    updateTechnicalDetails(data.technical_analysis.basic);

    // Update risk details
    updateRiskDetails(data.risk_management);

    // Update Finnhub advanced insights
    updateFinnhubInsights(data.finnhub_insights, data.external_api_signal);

    // Update sentiment
    updateSentimentDetails(data.sentiment_analysis);

    // Update institutional dashboard
    console.log('[DISPLAY RESULTS] Checking broker_intelligence:', data.broker_intelligence);
    if (data.broker_intelligence) {
        console.log('[DISPLAY RESULTS] Calling updateInstitutionalDashboard...');
        updateInstitutionalDashboard(data.broker_intelligence);
    } else {
        console.warn('[DISPLAY RESULTS] No broker_intelligence data found!');
    }

    // Update chart
    updatePredictionChart(data.ai_prediction);
    updateAIPredictionTransparency(
        data.ai_prediction,
        data.sentiment_analysis,
        data.technical_analysis
    );

    // Scroll to results
    elements.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Start live refresh loops for news and alerts
    startLiveNewsUpdates(data.symbol);
    startLiveAlertsMonitoring(data.symbol);
}

// Update professional recommendation
function updateProfessionalRecommendation(rec) {
    if (!rec) return;
    
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
    } else {
        reasoningCard.style.display = 'none';
    }
}

// Update position sizing
function updatePositionSizing(sizing) {
    if (!sizing) return;
    
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
    if (!advanced) return;
    
    // Get active tab
    const activeTab = document.querySelector('.advanced-tabs .tab-btn.active');
    const tabName = activeTab ? activeTab.dataset.tab : 'fibonacci';
    
    const container = document.getElementById('advanced-indicators-content');
    
    let html = '';
    switch(tabName) {
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
    const basic = risk.basic || {};
    const container = document.getElementById('risk-details');
    const items = [
        { label: 'Risk Level', value: basic.risk_level },
        { label: 'Stop Loss', value: `₹${basic.stop_loss?.stop_loss_price || '-'}` },
        { label: 'Stop Loss %', value: `${basic.stop_loss?.stop_loss_percent || '-'}%` },
        { label: 'Take Profit', value: `₹${basic.take_profit?.take_profit_price || '-'}` },
        { label: 'Risk-Reward Ratio', value: `1:${basic.take_profit?.risk_reward_ratio || '-'}` }
    ];
    
    container.innerHTML = items.map(item => `
        <div class="detail-item">
            <span class="detail-label">${item.label}</span>
            <span class="detail-value">${item.value}</span>
        </div>
    `).join('');
}

function updateFinnhubInsights(insights, externalSignal) {
    const card = document.getElementById('finnhub-card');
    const container = document.getElementById('finnhub-insights');
    if (!card || !container) return;

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
        { label: 'External API Composite Stance', value: externalSignal?.stance ? `${externalSignal.stance} (${externalSignal.confidence_percent || '-'}%)` : '-' },
        { label: 'External Composite Score', value: externalSignal?.composite_score ?? '-' },
        { label: 'Articles Analyzed (multi-API)', value: coverage.analyzed_articles ?? '-' },
        { label: 'Consensus', value: rec.consensus || '-' },
        { label: 'Total Analyst Ratings', value: rec.total_ratings ?? '-' },
        { label: 'Strong Buy / Buy / Hold / Sell / Strong Sell', value: `${rec.strong_buy ?? 0} / ${rec.buy ?? 0} / ${rec.hold ?? 0} / ${rec.sell ?? 0} / ${rec.strong_sell ?? 0}` },
        { label: 'Current Price (Finnhub)', value: asRupee(quote.current) },
        { label: 'Mean Target', value: asRupee(target.target_mean) },
        { label: 'Target High / Low', value: `${asRupee(target.target_high)} / ${asRupee(target.target_low)}` },
        { label: 'Upside vs Current', value: asPercent(target.upside_percent_vs_current) },
        { label: 'Daily Change', value: `${asRupee(quote.change)} (${asPercent(quote.change_percent)})` },
        { label: 'Company / Industry', value: profile.name ? `${profile.name} (${profile.finnhub_industry || '-'})` : '-' },
        { label: 'News Sentiment Driver', value: drivers.news_sentiment_score ?? '-' },
        { label: 'News Pos:Neg', value: drivers.news_positive_vs_negative ?? '-' },
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
    } else {
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
                        const displaySource = article.source || 'News Source';
                        const displayTitle = article.title || 'Stock News Update';
                        const severity = article.impact_severity || 'Low';
                        const impactScore = article.impact_score ?? '-';
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
            item.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'var(--bg-tertiary)';
                this.style.borderLeft = '4px solid var(--primary)';
                this.style.paddingLeft = '8px';
            });

            item.addEventListener('mouseleave', function() {
                this.style.backgroundColor = 'transparent';
                this.style.borderLeft = 'none';
                this.style.paddingLeft = '12px';
            });

            item.addEventListener('click', function() {
                const articleIndex = parseInt(this.dataset.articleIndex);
                showArticleDetail(articleIndex);
            });
        });
    } else {
        articlesContainer.innerHTML = '';
    }
}

// Update institutional dashboard with broker intelligence
function updateInstitutionalDashboard(brokerIntel) {
    console.log('[INSTITUTIONAL DASHBOARD] Received data:', brokerIntel);

    const dashboardContainer = document.getElementById('institutional-dashboard');
    if (!dashboardContainer) {
        console.error('[INSTITUTIONAL DASHBOARD] Container not found');
        return;
    }

    const kpiContainer = document.getElementById('kpi-metrics');
    const dashChartsContainer = document.getElementById('dashboard-charts');

    if (!kpiContainer) {
        console.error('[INSTITUTIONAL DASHBOARD] KPI container not found');
        return;
    }
    if (!dashChartsContainer) {
        console.error('[INSTITUTIONAL DASHBOARD] Charts container not found');
        return;
    }

    console.log('[INSTITUTIONAL DASHBOARD] Containers found, populating data...');

    // Extract broker data
    const brokerRec = brokerIntel.broker_recommendation || {};
    const analystConsensus = brokerIntel.analyst_consensus || {};
    const dividends = brokerIntel.dividend_information || {};
    const earnings = brokerIntel.earnings_information || {};
    const sectorComp = brokerIntel.sector_comparison || {};
    const newsAnalysis = brokerIntel.news_analysis || {};

    console.log('[INSTITUTIONAL DASHBOARD] Extracted data:', {
        brokerRec,
        analystConsensus,
        dividends,
        earnings,
        sectorComp,
        newsAnalysis
    });

    // Build KPI metrics
    const kpiHtml = `
        <div class="kpi-card">
            <div class="kpi-label">Broker Recommendation</div>
            <div class="kpi-value" style="color: ${brokerRec.recommendation && brokerRec.recommendation.includes('BUY') ? '#10b981' : brokerRec.recommendation && brokerRec.recommendation.includes('SELL') ? '#ef4444' : '#f59e0b'}">${brokerRec.recommendation || '-'}</div>
            <div class="kpi-subtext">${brokerRec.conviction || brokerRec.risk_level || '-'}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Analyst Rating</div>
            <div class="kpi-value">${analystConsensus.consensus_rating || '-'}</div>
            <div class="kpi-subtext">${analystConsensus.number_of_analysts || 0} analysts</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Dividend Yield</div>
            <div class="kpi-value">${dividends.dividend_yield ? dividends.dividend_yield.toFixed(2) + '%' : '-'}</div>
            <div class="kpi-subtext">${dividends.last_dividend_date ? dividends.last_dividend_date.substring(0, 10) : '-'}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Next Earnings</div>
            <div class="kpi-value">${earnings.next_earnings_date ? earnings.next_earnings_date.substring(0, 10) : '-'}</div>
            <div class="kpi-subtext">PE: ${earnings.pe_ratio || '-'}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Sector</div>
            <div class="kpi-value">${sectorComp.sector || '-'}</div>
            <div class="kpi-subtext">${sectorComp.industry || 'Unknown'}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">News Sentiment</div>
            <div class="kpi-value" style="color: ${newsAnalysis.news_sentiment_distribution?.positive > newsAnalysis.news_sentiment_distribution?.negative ? '#10b981' : '#ef4444'}">${newsAnalysis.total_articles || 0} articles</div>
            <div class="kpi-subtext">${newsAnalysis.news_sentiment_distribution?.positive || 0}+ / ${newsAnalysis.news_sentiment_distribution?.negative || 0}-</div>
        </div>
    `;

    console.log('[INSTITUTIONAL DASHBOARD] Setting KPI HTML...');
    kpiContainer.innerHTML = kpiHtml;

    // Add basic dashboard insights
    dashChartsContainer.innerHTML = `
        <div style="padding: 20px; background: var(--bg-secondary); border-radius: var(--radius); margin-bottom: 16px;">
            <h4 style="margin-bottom: 12px; color: var(--text-primary);">📊 Trading Insights</h4>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                <div style="padding: 12px; background: var(--bg-tertiary); border-radius: 6px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 4px;">Entry Point</div>
                    <div style="font-size: 1.2rem; font-weight: 600; color: var(--primary);">₹${brokerRec.entry_point ? brokerRec.entry_point.toFixed(2) : '-'}</div>
                </div>
                <div style="padding: 12px; background: var(--bg-tertiary); border-radius: 6px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 4px;">Stop Loss</div>
                    <div style="font-size: 1.2rem; font-weight: 600; color: #ef4444;">₹${brokerRec.stop_loss ? brokerRec.stop_loss.toFixed(2) : '-'}</div>
                </div>
                <div style="padding: 12px; background: var(--bg-tertiary); border-radius: 6px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 4px;">Target 1</div>
                    <div style="font-size: 1.2rem; font-weight: 600; color: #10b981;">₹${brokerRec.targets?.target_1 ? brokerRec.targets.target_1.toFixed(2) : '-'}</div>
                </div>
                <div style="padding: 12px; background: var(--bg-tertiary); border-radius: 6px;">
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 4px;">Risk-Reward</div>
                    <div style="font-size: 1.2rem; font-weight: 600; color: var(--primary);">1:${brokerRec.risk_reward_ratio || '-'}</div>
                </div>
            </div>
        </div>
    `;

    console.log('[INSTITUTIONAL DASHBOARD] Dashboard populated successfully');
}

// Update prediction chart
function updatePredictionChart(aiPrediction) {
    const canvas = document.getElementById('prediction-chart');
    if (!canvas) return;
    
    // Destroy existing chart
    if (predictionChart) {
        predictionChart.destroy();
        predictionChart = null;
    }
    
    if (!aiPrediction || !aiPrediction.chart_data) return;
    
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
                        label: function(context) {
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
                        callback: function(value) {
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
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function updateAIPredictionTransparency(aiPrediction, sentiment, technical) {
    const guideBox = document.getElementById('ai-prediction-guide');
    const detailsBox = document.getElementById('ai-transparency-details');
    if (!guideBox || !detailsBox) return;

    const transparency = aiPrediction?.transparency || {};
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

    const summary = transparency.summary || aiPrediction?.reasoning || 'Explanation will be available after analysis.';
    const keyFactors = (aiPrediction?.key_factors || []).slice(0, 5);
    const articleDrivers = (transparency.article_drivers || []).slice(0, 3);
    const geopolitical = (transparency.geopolitical_scenarios || []).slice(0, 3);
    const trendSignals = (transparency.market_trend_signals || []).slice(0, 4);
    const technicalTrend = technical?.basic?.trend || 'Neutral';
    const sentimentClass = sentiment?.sentiment_classification || 'Neutral';

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
            if (e.target === modal) closeArticleDetail();
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
    const symbol = normalizeSymbol(elements.symbolInput.value);
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
                                <div style="color: var(--text-secondary); font-size: 0.85rem;">Day ${i+1}</div>
                                <div style="color: #00d4ff; font-weight: bold; font-size: 1.1rem;">₹${p.toFixed(2)}</div>
                            </div>
                        `).join('')}
                    </div>
                    <p style="margin-top: 10px; color: var(--text-secondary); font-size: 0.9rem;">Confidence: ${predictions.confidence}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('LSTM Error:', error);
        showToast('LSTM training failed: ' + error.message, 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Transformer Training & Prediction
async function trainTransformer() {
    const symbol = normalizeSymbol(elements.symbolInput.value);
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
                                <div style="color: var(--text-secondary); font-size: 0.85rem;">Day ${i+1}</div>
                                <div style="color: #10b981; font-weight: bold; font-size: 1.1rem;">₹${p.toFixed(2)}</div>
                            </div>
                        `).join('')}
                    </div>
                    <p style="margin-top: 10px; color: var(--text-secondary); font-size: 0.9rem;">Speed: 30-80ms inference</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Transformer Error:', error);
        showToast('Transformer training failed: ' + error.message, 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Portfolio Optimization (RL)
async function optimizePortfolio() {
    const symbol = normalizeSymbol(elements.symbolInput.value);
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
    } catch (error) {
        console.error('Portfolio Error:', error);
        showToast('Portfolio optimization failed', 'error');
    } finally {
        btn.textContent = 'Optimize Now';
        btn.disabled = false;
    }
}

// Backtest RSI
async function backtestRSI() {
    const symbol = normalizeSymbol(elements.symbolInput.value);
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
    } catch (error) {
        showToast('Backtest failed: ' + error.message, 'error');
    } finally {
        btn.textContent = 'Backtest RSI';
        btn.disabled = false;
    }
}

// Backtest MACD
async function backtestMACD() {
    const symbol = normalizeSymbol(elements.symbolInput.value);
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
                    <div><span style="color: var(--text-secondary);">Profit/Trade:</span><br><span style="color: #8b5cf6; font-weight: bold;">${(data.profit_per_trade ?? 0).toFixed(2)}%</span></div>
                </div>
            </div>
        `;
        showToast('✅ MACD backtest complete!', 'success');
    } catch (error) {
        showToast('Backtest failed: ' + error.message, 'error');
    } finally {
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
    } catch (error) {
        showToast(`Failed to create alert: ${error.message}`, 'error');
    }
}

// Load Alerts
async function loadAlerts() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/ai/alerts`);
        if (!response.ok) {
            const alertsList = document.getElementById('alerts-list');
            if (alertsList) alertsList.innerHTML = '<p style="color: var(--text-secondary);">Unable to load alerts right now.</p>';
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
    } catch (error) {
        console.error('Failed to load alerts:', error);
    }
}

async function fetchLiveNewsNow(symbol) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/broker/news-impact/${encodeURIComponent(symbol)}`);
        if (!response.ok) return;

        const data = await response.json();
        const normalizedSentiment = {
            sentiment_classification: data.sentiment_classification || 'Neutral',
            headlines_count: data.headlines_count || 0,
            breakdown: data.news_analysis?.news_sentiment_distribution || { positive: 0, negative: 0, neutral: 0 },
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
            } else {
                sourcesContainer.innerHTML += `
                <div id="live-news-refresh-stamp" style="margin-top: 8px; font-size: 0.8rem; color: var(--text-muted);">
                    Last live refresh: ${stamp}
                </div>
            `;
            }
        }
    } catch (error) {
        console.warn('Live news refresh failed:', error);
    }
}

function startLiveNewsUpdates(symbol) {
    if (liveNewsInterval) {
        clearInterval(liveNewsInterval);
        liveNewsInterval = null;
    }

    if (!symbol) return;
    fetchLiveNewsNow(symbol);
    liveNewsInterval = setInterval(() => fetchLiveNewsNow(symbol), 90000);
}

async function evaluateAlertsNow(symbol) {
    try {
        const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : '';
        const response = await fetch(`${API_BASE_URL}/api/ai/alerts/evaluate${query}`);
        if (!response.ok) return;
        const data = await response.json();

        if (data.triggered_count > 0) {
            data.triggered_alerts.forEach(alert => {
                showToast(`🔔 Alert triggered: ${alert.symbol} (${alert.alert_type}) at ${alert.value}`, 'success');
            });
            await loadAlerts();
        }
    } catch (error) {
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
    } catch (error) {
        showToast('Failed to delete alert', 'error');
    }
}

async function explainPrediction() {
    const symbol = normalizeSymbol(elements.symbolInput.value);
    if (!symbol) {
        showToast('Please enter a stock symbol', 'error');
        return;
    }
    if (!latestAnalysisData || normalizeSymbol(latestAnalysisData.symbol) !== symbol) {
        showToast('Run analysis first so explanation uses live prediction data.', 'error');
        return;
    }

    const ai = latestAnalysisData.ai_prediction || {};
    const technical = latestAnalysisData.technical_analysis?.basic || {};
    const sentiment = latestAnalysisData.sentiment_analysis || {};
    const rawPrediction = String(ai.ai_prediction || 'NEUTRAL').toUpperCase();
    const decisionMap = { UP: 'BUY', DOWN: 'SELL', NEUTRAL: 'HOLD' };
    const decision = decisionMap[rawPrediction] || rawPrediction;
    const rawAiConfidence = String(ai.confidence ?? '50').trim();
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
        ml_up_probability: latestAnalysisData.ml_prediction?.up_probability,
        geopolitical_scenarios: ai.transparency?.geopolitical_scenarios || [],
        finnhub_insights: latestAnalysisData.finnhub_insights || {}
    };

    const container = document.getElementById('explainability');
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

        container.innerHTML = `
            <div class="explainability-pro-card">
                <div class="explainability-header">
                    <h4>${escapeHtml(data.decision)} (${confidencePercent.toFixed(0)}% confidence)</h4>
                    <div class="explainability-subtitle">Professional rationale combining technical, sentiment, AI pathing, and geopolitical risk channels.</div>
                </div>

                <div class="explainability-section">
                    <h5>Decision Note</h5>
                    <p>${escapeHtml(data.detailed_explanation || data.explanation || 'Detailed explanation unavailable.')}</p>
                </div>

                ${data.graph_explanation ? `
                    <div class="explainability-section">
                        <h5>Why upcoming dates in the prediction graph look this way</h5>
                        <p>${escapeHtml(data.graph_explanation)}</p>
                    </div>
                ` : ''}

                ${(data.top_reasons || []).length ? `
                    <div class="explainability-section">
                        <h5>Top Drivers</h5>
                        <ol>
                            ${(data.top_reasons || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                        </ol>
                    </div>
                ` : ''}

                ${(geoDrivers.length || geoChannels.length || geoScenarios.length || stockView.length) ? `
                    <div class="explainability-section">
                        <h5>Professional Geopolitical Analysis</h5>
                        ${geoDrivers.length ? `
                            <div class="explainability-block-title">Macro Drivers</div>
                            <ul>${geoDrivers.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
                        ` : ''}
                        ${geoChannels.length ? `
                            <div class="explainability-block-title">Transmission Channels</div>
                            <ul>${geoChannels.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
                        ` : ''}
                        ${geoScenarios.length ? `
                            <div class="explainability-block-title">Scenario Matrix</div>
                            <div class="explainability-scenario-grid">
                                ${geoScenarios.map(sc => `
                                    <div class="explainability-scenario-item">
                                        <strong>${escapeHtml(sc.scenario || 'Scenario')}</strong>
                                        <div><span>Probability:</span> ${escapeHtml(sc.probability || '-')}</div>
                                        <div><span>Implication:</span> ${escapeHtml(sc.implication || '-')}</div>
                                        <div><span>Positioning:</span> ${escapeHtml(sc.positioning || '-')}</div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                        ${stockView.length ? `
                            <div class="explainability-block-title">Stock-Specific Geopolitical View</div>
                            <ul>${stockView.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
                        ` : ''}
                    </div>
                ` : ''}
            </div>
        `;
        showToast('✅ Explanation generated', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Setup AI Feature Event Listeners
function setupAIFeatures() {
    const lstmBtn = document.getElementById('lstm-train-btn');
    const transformerBtn = document.getElementById('transformer-train-btn');
    const portfolioBtn = document.getElementById('portfolio-optimize-btn');
    const backtestRSIBtn = document.getElementById('backtest-rsi-btn');
    const backtestMACDBtn = document.getElementById('backtest-macd-btn');
    const createAlertBtn = document.getElementById('create-alert-btn');
    const explainBtn = document.getElementById('explain-btn');

    if (lstmBtn) lstmBtn.addEventListener('click', trainLSTM);
    if (transformerBtn) transformerBtn.addEventListener('click', trainTransformer);
    if (portfolioBtn) portfolioBtn.addEventListener('click', optimizePortfolio);
    if (backtestRSIBtn) backtestRSIBtn.addEventListener('click', backtestRSI);
    if (backtestMACDBtn) backtestMACDBtn.addEventListener('click', backtestMACD);
    if (createAlertBtn) createAlertBtn.addEventListener('click', createAlert);
    if (explainBtn) explainBtn.addEventListener('click', explainPrediction);

    // Load alerts on init
    loadAlerts();
}

// Initialize app
init();
setupAIFeatures();
