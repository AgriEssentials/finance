/**
 * Dashboard JavaScript - AI Stock Analysis Pro
 * Handles terminal dashboard functionality
 */

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized');
    
    // Initialize the original home view functionality
    initDashboard();
    
    // Load market data
    loadMarketData();
    
    // Start periodic updates
    setInterval(updateMarketData, 30000);
});

function initDashboard() {
    // Set up navigation
    const homeBtn = document.getElementById('home-nav-btn');
    const analysisBtn = document.getElementById('analysis-nav-btn');
    
    if (homeBtn) {
        homeBtn.addEventListener('click', function() {
            showHomeView();
        });
    }
    
    if (analysisBtn) {
        analysisBtn.addEventListener('click', function() {
            showAnalysisView();
        });
    }
}

function showHomeView() {
    const homeView = document.getElementById('home-view');
    if (homeView) {
        homeView.style.display = 'block';
    }
    
    // Update nav active state
    const homeBtn = document.getElementById('home-nav-btn');
    const analysisBtn = document.getElementById('analysis-nav-btn');
    if (homeBtn) homeBtn.classList.add('active');
    if (analysisBtn) analysisBtn.classList.remove('active');
}

function showAnalysisView() {
    const homeView = document.getElementById('home-view');
    if (homeView) {
        homeView.style.display = 'none';
    }
    
    // Show analysis shell if exists
    const analysisShell = document.getElementById('analysis-shell');
    if (analysisShell) {
        analysisShell.style.display = 'block';
    }
    
    // Update nav active state
    const homeBtn = document.getElementById('home-nav-btn');
    const analysisBtn = document.getElementById('analysis-nav-btn');
    if (homeBtn) homeBtn.classList.remove('active');
    if (analysisBtn) analysisBtn.classList.add('active');
}

async function loadMarketData() {
    try {
        // Load indices data
        const response = await fetch('/api/landing-data');
        if (response.ok) {
            const data = await response.json();
            updateIndicesDisplay(data.indices);
        }
        
        // Load NIFTY chart
        initMainChart();
        
        // Load sector heatmap
        initSectorHeatmap();
        
        // Load order book simulation
        initOrderBook();
        
    } catch (error) {
        console.error('Failed to load market data:', error);
    }
}

function updateMarketData() {
    // Update live data periodically
    updateIndicesValues();
    updateSystemLogs();
}

function updateIndicesDisplay(indices) {
    if (!indices) return;
    
    indices.forEach(idx => {
        const element = document.getElementById(idx.id || idx.name.toLowerCase().replace(' ', '-') + '-value');
        if (element) {
            element.textContent = idx.value ? idx.value.toLocaleString() : '--';
            element.style.color = idx.change >= 0 ? '#00c853' : '#ff1744';
        }
    });
}

function updateIndicesValues() {
    // Simulate live updates
    const nifty = document.getElementById('nifty-value');
    const sensex = document.getElementById('sensex-value');
    const vix = document.getElementById('vix-value');
    
    if (nifty) {
        const base = 22500;
        const variation = (Math.random() - 0.5) * 100;
        nifty.textContent = '₹' + (base + variation).toFixed(2);
    }
    
    if (sensex) {
        const base = 74500;
        const variation = (Math.random() - 0.5) * 300;
        sensex.textContent = '₹' + (base + variation).toFixed(2);
    }
    
    if (vix) {
        const base = 12.5;
        const variation = (Math.random() - 0.5) * 2;
        vix.textContent = (base + variation).toFixed(2);
    }
}

function initMainChart() {
    const canvas = document.getElementById('main-chart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Generate sample data
    const labels = Array.from({length: 20}, (_, i) => {
        const d = new Date();
        d.setMinutes(d.getMinutes() - (19 - i) * 5);
        return d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
    });
    
    const data = Array.from({length: 20}, (_, i) => {
        return 22500 + Math.sin(i * 0.5) * 100 + (Math.random() - 0.5) * 50;
    });
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'NIFTY 50',
                data: data,
                borderColor: '#2962ff',
                backgroundColor: 'rgba(41, 98, 255, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#666', font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#666', font: { size: 10 } }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

function initSectorHeatmap() {
    const container = document.getElementById('sector-heatmap');
    if (!container) return;
    
    const sectors = [
        'BANK', 'IT', 'AUTO', 'PHARMA', 'FMCG', 'METAL', 'OIL', 'TELECOM',
        'POWER', 'INFRA', 'REALTY', 'MEDIA', 'CONS', 'FIN', 'ENERGY'
    ];
    
    container.innerHTML = sectors.map(sector => {
        const change = (Math.random() - 0.5) * 4;
        const cls = change > 1 ? 'heat-up-strong' : change > 0 ? 'heat-up' : change < -1 ? 'heat-down-strong' : 'heat-down';
        return `<div class="heat-cell ${cls}">${sector}</div>`;
    }).join('');
}

function initOrderBook() {
    const container = document.getElementById('order-book');
    if (!container) return;
    
    const basePrice = 2500;
    let html = '<div class="ob-row" style="color:#666;font-size:0.7rem;"><span class="ob-cell">BID</span><span class="ob-cell">SIZE</span><span class="ob-cell">ASK</span></div>';
    
    for (let i = 0; i < 8; i++) {
        const bid = basePrice - (i * 0.5) - Math.random() * 0.3;
        const ask = basePrice + (i * 0.5) + Math.random() * 0.3;
        const size = Math.floor(Math.random() * 1000) + 100;
        
        html += `
            <div class="ob-row">
                <span class="ob-cell ob-bid">${bid.toFixed(2)}</span>
                <span class="ob-cell ob-vol">${size}</span>
                <span class="ob-cell ob-ask">${ask.toFixed(2)}</span>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

function updateSystemLogs() {
    const logStream = document.getElementById('log-stream');
    if (!logStream) return;
    
    const messages = [
        { type: 'info', text: 'Market data updated' },
        { type: 'success', text: 'Price feed connected' },
        { type: 'warn', text: 'Volatility spike detected' },
        { type: 'info', text: 'AI model prediction complete' }
    ];
    
    const msg = messages[Math.floor(Math.random() * messages.length)];
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    const p = document.createElement('p');
    p.className = msg.type;
    p.textContent = `[${time}] ${msg.text}`;
    
    logStream.insertBefore(p, logStream.firstChild);
    
    // Keep only last 10 messages
    while (logStream.children.length > 10) {
        logStream.removeChild(logStream.lastChild);
    }
}

// Make functions globally available
window.showHomeView = showHomeView;
window.showAnalysisView = showAnalysisView;
