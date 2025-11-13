"""
Enhanced Dashboard Server with Visualizations

Provides a rich web UI with:
- Real-time line charts (orders, trades, throughput)
- Visual progress bars for node sync status
- Detailed node information table
- System health indicators
"""

from .dashboard_server import DashboardServer, DashboardHandler
from .metrics_collector import MetricsCollector
from typing import Optional
import json

class EnhancedDashboardHandler(DashboardHandler):
    """Enhanced request handler with visualization support."""

    # Inherit the collector class variable from parent
    collector: Optional[MetricsCollector] = None

    def _get_dashboard_html(self) -> str:
        """Generate enhanced dashboard HTML with Chart.js visualizations."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Distributed Consensus Monitor</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <div class="container">
        <h1>📊 Distributed Consensus Monitoring Dashboard</h1>

        <!-- Status Bar -->
        <div class="status-bar">
            <div class="status-item">
                <span class="label">Cluster Health:</span>
                <span id="clusterHealth" class="value health-healthy">HEALTHY</span>
            </div>
            <div class="status-item">
                <span class="label">Leader:</span>
                <span id="leaderNode" class="value">node1</span>
            </div>
            <div class="status-item">
                <span class="label">Term:</span>
                <span id="currentTerm" class="value">1</span>
            </div>
            <div class="status-item">
                <span class="label">Nodes:</span>
                <span id="nodeCount" class="value">5/5</span>
            </div>
        </div>

        <!-- Performance Metrics with Visualizations -->
        <div class="charts-grid">
            <div class="chart-card">
                <h3>📈 Order Throughput (ops/sec)</h3>
                <div class="chart-loading" id="throughputLoading">
                    <div class="spinner"></div>
                    <div class="loading-text">Collecting data<span class="dots"></span></div>
                    <div class="progress-info">
                        <span id="throughputProgressText">0/3 data points</span>
                        <div class="progress-bar">
                            <div class="progress-fill" id="throughputProgressBar"></div>
                        </div>
                    </div>
                </div>
                <canvas id="throughputChart" style="display: none;"></canvas>
                <div class="chart-stats">
                    <span>Current: <strong id="currentThroughput" class="live-number">0</strong> ops/s</span>
                    <span>Avg: <strong id="avgThroughput" class="live-number">0</strong> ops/s</span>
                </div>
            </div>

            <div class="chart-card">
                <h3>📦 Orders & Trades</h3>
                <div class="chart-loading" id="ordersLoading">
                    <div class="spinner"></div>
                    <div class="loading-text">Collecting data<span class="dots"></span></div>
                    <div class="progress-info">
                        <span id="ordersProgressText">0/3 data points</span>
                        <div class="progress-bar">
                            <div class="progress-fill" id="ordersProgressBar"></div>
                        </div>
                    </div>
                </div>
                <canvas id="ordersTradesChart" style="display: none;"></canvas>
                <div class="chart-stats">
                    <span>Orders: <strong id="totalOrders" class="live-number">0</strong></span>
                    <span>Trades: <strong id="totalTrades" class="live-number">0</strong></span>
                    <span>Match Rate: <strong id="matchRate" class="live-number">0%</strong></span>
                </div>
            </div>
        </div>

        <!-- Consensus Metrics -->
        <div class="metrics-grid">
            <div class="metric-card consensus-card">
                <h3>🔄 Consensus Status</h3>
                <div class="consensus-visual">
                    <div class="consensus-indicator" id="consensusIndicator">
                        <div class="indicator-circle aligned"></div>
                        <span>ALIGNED</span>
                    </div>
                    <div class="consensus-details">
                        <div>Current Term: <strong id="consensusTerm">1</strong></div>
                        <div>Commit Index: <strong id="commitIndex">0</strong></div>
                        <div>Log Length: <strong id="logLength">0</strong></div>
                    </div>
                </div>
            </div>

            <div class="metric-card">
                <h3>⚡ System Performance</h3>
                <div class="performance-bars">
                    <div class="perf-item">
                        <label>Throughput</label>
                        <div class="progress-bar">
                            <div id="throughputBar" class="progress-fill" style="width: 0%"></div>
                        </div>
                        <span id="throughputPercent">0%</span>
                    </div>
                    <div class="perf-item">
                        <label>Node Health</label>
                        <div class="progress-bar">
                            <div id="healthBar" class="progress-fill health" style="width: 100%"></div>
                        </div>
                        <span id="healthPercent">100%</span>
                    </div>
                </div>
            </div>

            <div class="metric-card alerts-card">
                <h3>🔔 Alerts</h3>
                <div class="alert-status">
                    <div class="alert-count" id="alertCount">0</div>
                    <div class="alert-label">Active Alerts</div>
                </div>
                <div id="recentAlerts" class="alert-list">
                    <em>No alerts</em>
                </div>
            </div>
        </div>

        <!-- Live Activity Feed -->
        <div class="activity-section">
            <h2>📊 Live Activity Feed</h2>
            <div class="activity-container">
                <div id="activityFeed" class="activity-feed">
                    <div class="activity-item">
                        <span class="activity-icon">🚀</span>
                        <span class="activity-text">System started - waiting for activity...</span>
                        <span class="activity-time">now</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Detailed Node Information -->
        <div class="nodes-section">
            <h2>🖥️ Node Status Details</h2>
            <div class="nodes-table-container">
                <table class="nodes-table">
                    <thead>
                        <tr>
                            <th>Node</th>
                            <th>Role</th>
                            <th>Status</th>
                            <th>Commit Index</th>
                            <th>Orders</th>
                            <th>Trades</th>
                            <th>Messages</th>
                            <th>Sync Status</th>
                        </tr>
                    </thead>
                    <tbody id="nodesTableBody">
                        <!-- Populated by JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Order Book -->
        <div class="orderbook-section">
            <h2>📖 Live Order Book - <span id="orderbookSymbol">AAPL</span></h2>
            <div class="orderbook-container">
                <div class="orderbook-side asks-side">
                    <h3 style="color: #ef4444;">ASKS (Sell Orders)</h3>
                    <table class="orderbook-table">
                        <thead>
                            <tr>
                                <th>Price</th>
                                <th>Quantity</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody id="asksTableBody">
                            <tr><td colspan="3"><em>Loading...</em></td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="spread-indicator" id="spreadIndicator">
                    <div class="spread-label">Spread</div>
                    <div class="spread-value">--</div>
                </div>
                <div class="orderbook-side bids-side">
                    <h3 style="color: #10b981;">BIDS (Buy Orders)</h3>
                    <table class="orderbook-table">
                        <thead>
                            <tr>
                                <th>Price</th>
                                <th>Quantity</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody id="bidsTableBody">
                            <tr><td colspan="3"><em>Loading...</em></td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <span><span class="status-indicator"></span> System Running</span>
            <span>Last updated: <span id="lastUpdate">Never</span></span>
            <span>Auto-refresh: <strong>Every 1 second</strong></span>
        </div>
    </div>

    <script src="/dashboard.js"></script>
</body>
</html>'''

    def _get_dashboard_css(self) -> str:
        """Generate enhanced CSS with better styling."""
        return '''
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #333;
    padding: 20px;
    min-height: 100vh;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
}

h1 {
    text-align: center;
    color: white;
    margin-bottom: 30px;
    font-size: 2.5em;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}

h2 {
    color: white;
    margin: 30px 0 20px 0;
    font-size: 1.8em;
}

h3 {
    color: #667eea;
    margin-bottom: 15px;
    font-size: 1.2em;
}

/* Status Bar */
.status-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 25px;
}

.status-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 10px;
}

.status-item .label {
    font-size: 0.9em;
    color: #666;
    margin-bottom: 5px;
}

.status-item .value {
    font-size: 1.5em;
    font-weight: bold;
    color: #333;
}

.health-healthy {
    color: #10b981 !important;
}

.health-degraded {
    color: #f59e0b !important;
}

.health-unhealthy {
    color: #ef4444 !important;
}

/* Charts Grid */
.charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
    gap: 20px;
    margin-bottom: 25px;
}

.chart-card {
    background: white;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.chart-card canvas {
    max-height: 250px;
}

.chart-stats {
    display: flex;
    justify-content: space-around;
    margin-top: 15px;
    padding-top: 15px;
    border-top: 2px solid #f3f4f6;
    font-size: 0.9em;
    color: #666;
}

.chart-stats strong {
    color: #667eea;
    font-size: 1.2em;
}

/* Metrics Grid */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 25px;
}

.metric-card {
    background: white;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

/* Consensus Card */
.consensus-visual {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.consensus-indicator {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 15px;
    background: #f0fdf4;
    border-radius: 8px;
    font-weight: bold;
    color: #10b981;
}

.indicator-circle {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    animation: pulse 2s infinite;
}

.indicator-circle.aligned {
    background: #10b981;
}

.indicator-circle.misaligned {
    background: #ef4444;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* Loading Indicators */
.chart-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    gap: 15px;
}

.spinner {
    width: 50px;
    height: 50px;
    border: 4px solid #f3f4f6;
    border-top: 4px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.loading-text {
    color: #667eea;
    font-size: 1.1em;
    font-weight: 500;
}

.dots::after {
    content: '...';
    animation: dots 1.5s steps(4, end) infinite;
}

@keyframes dots {
    0%, 20% { content: '.'; }
    40% { content: '..'; }
    60%, 100% { content: '...'; }
}

.progress-info {
    width: 100%;
    max-width: 300px;
    text-align: center;
}

.progress-info span {
    color: #667eea;
    font-size: 0.95em;
    font-weight: 600;
    display: block;
    margin-bottom: 8px;
}

.progress-bar {
    width: 100%;
    height: 8px;
    background: #e5e7eb;
    border-radius: 4px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    transition: width 0.3s ease;
    border-radius: 4px;
}

/* Live Number Animation */
.live-number {
    display: inline-block;
    animation: pulse-number 2s ease-in-out infinite;
}

@keyframes pulse-number {
    0%, 100% {
        transform: scale(1);
        color: inherit;
    }
    50% {
        transform: scale(1.05);
        color: #667eea;
    }
}

.consensus-details {
    display: flex;
    flex-direction: column;
    gap: 10px;
    font-size: 0.95em;
    color: #666;
}

.consensus-details strong {
    color: #667eea;
    font-size: 1.1em;
}

/* Performance Bars */
.performance-bars {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.perf-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.perf-item label {
    font-weight: 600;
    color: #666;
    font-size: 0.9em;
}

.progress-bar {
    height: 24px;
    background: #f3f4f6;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    transition: width 0.5s ease;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 10px;
    color: white;
    font-weight: bold;
    font-size: 0.85em;
}

.progress-fill.health {
    background: linear-gradient(90deg, #10b981 0%, #059669 100%);
}

.perf-item span {
    font-weight: bold;
    color: #667eea;
    text-align: right;
    font-size: 0.9em;
}

/* Alerts Card */
.alerts-card {
    display: flex;
    flex-direction: column;
}

.alert-status {
    text-align: center;
    padding: 20px;
    background: #f0fdf4;
    border-radius: 8px;
    margin-bottom: 15px;
}

.alert-count {
    font-size: 3em;
    font-weight: bold;
    color: #10b981;
}

.alert-label {
    font-size: 0.9em;
    color: #666;
    margin-top: 5px;
}

.alert-list {
    font-size: 0.9em;
    color: #666;
}

/* Nodes Section */
.nodes-section {
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 25px;
}

.nodes-table-container {
    overflow-x: auto;
}

.nodes-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}

.nodes-table thead {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.nodes-table th {
    padding: 15px;
    text-align: left;
    font-weight: 600;
    font-size: 0.9em;
}

.nodes-table td {
    padding: 15px;
    border-bottom: 1px solid #f3f4f6;
    font-size: 0.9em;
}

.nodes-table tbody tr:hover {
    background: #f9fafb;
}

.node-role {
    padding: 4px 12px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 0.85em;
    display: inline-block;
}

.role-leader {
    background: #fef3c7;
    color: #d97706;
}

.role-follower {
    background: #dbeafe;
    color: #2563eb;
}

.node-status {
    padding: 4px 12px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 0.85em;
    display: inline-block;
}

.status-healthy {
    background: #d1fae5;
    color: #059669;
}

.status-degraded {
    background: #fed7aa;
    color: #ea580c;
}

.sync-bar {
    width: 100px;
    height: 8px;
    background: #f3f4f6;
    border-radius: 4px;
    overflow: hidden;
    display: inline-block;
    vertical-align: middle;
}

.sync-fill {
    height: 100%;
    background: linear-gradient(90deg, #10b981 0%, #059669 100%);
    transition: width 0.5s ease;
}

/* Order Book */
.orderbook-section {
    margin: 30px 0;
}

.orderbook-container {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 20px;
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.orderbook-side h3 {
    margin-bottom: 15px;
    text-align: center;
}

.orderbook-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Monaco', 'Courier New', monospace;
}

.orderbook-table thead th {
    background: #f3f4f6;
    padding: 10px;
    text-align: right;
    font-weight: 600;
    color: #374151;
    border-bottom: 2px solid #e5e7eb;
}

.orderbook-table tbody td {
    padding: 8px 10px;
    text-align: right;
    border-bottom: 1px solid #f3f4f6;
    transition: background-color 0.2s;
}

.orderbook-table tbody tr:hover {
    background: #f9fafb;
}

.asks-side .price {
    color: #ef4444;
    font-weight: 600;
}

.bids-side .price {
    color: #10b981;
    font-weight: 600;
}

.spread-indicator {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 8px;
    color: white;
    min-width: 120px;
}

.spread-label {
    font-size: 0.9em;
    opacity: 0.9;
    margin-bottom: 8px;
}

.spread-value {
    font-size: 1.5em;
    font-weight: 700;
    font-family: 'Monaco', 'Courier New', monospace;
}

/* Activity Feed */
.activity-section {
    margin: 30px 0;
}

.activity-container {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    max-height: 400px;
    overflow-y: auto;
}

.activity-feed {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.activity-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: #f9fafb;
    border-radius: 8px;
    border-left: 4px solid #667eea;
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateX(-20px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.activity-icon {
    font-size: 1.5em;
    flex-shrink: 0;
}

.activity-text {
    flex: 1;
    color: #374151;
    font-size: 0.95em;
}

.activity-time {
    color: #9ca3af;
    font-size: 0.85em;
    flex-shrink: 0;
}

.activity-item.order {
    border-left-color: #3b82f6;
}

.activity-item.trade {
    border-left-color: #10b981;
}

.activity-item.consensus {
    border-left-color: #8b5cf6;
}

.activity-item.error {
    border-left-color: #ef4444;
}

/* Footer */
.footer {
    text-align: center;
    color: white;
    padding: 20px;
    font-size: 0.9em;
    display: flex;
    justify-content: space-between;
    background: rgba(255,255,255,0.1);
    border-radius: 12px;
}

.status-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    background: #10b981;
    border-radius: 50%;
    margin-right: 8px;
    animation: blink 2s ease-in-out infinite;
}

@keyframes blink {
    0%, 100% {
        opacity: 1;
        box-shadow: 0 0 8px #10b981;
    }
    50% {
        opacity: 0.5;
        box-shadow: 0 0 4px #10b981;
    }
}

/* Responsive */
@media (max-width: 768px) {
    .charts-grid {
        grid-template-columns: 1fr;
    }

    .metrics-grid {
        grid-template-columns: 1fr;
    }

    h1 {
        font-size: 1.8em;
    }
}
'''

    def _get_dashboard_js(self) -> str:
        """Generate enhanced JavaScript with Chart.js visualizations."""
        return '''
// Chart instances
let throughputChart = null;
let ordersTradesChart = null;

// Data storage for charts
const maxDataPoints = 15; // Last 15 data points
const throughputData = [];
const ordersData = [];
const tradesData = [];
const timestamps = [];

// Initialize charts
function initCharts() {
    const throughputCtx = document.getElementById('throughputChart').getContext('2d');
    const ordersTradesCtx = document.getElementById('ordersTradesChart').getContext('2d');

    // Throughput Chart
    throughputChart = new Chart(throughputCtx, {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [{
                label: 'Throughput (ops/s)',
                data: throughputData,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'ops/sec' }
                },
                x: {
                    display: false
                }
            }
        }
    });

    // Orders & Trades Chart
    ordersTradesChart = new Chart(ordersTradesCtx, {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [
                {
                    label: 'Orders',
                    data: ordersData,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Trades',
                    data: tradesData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: { display: true, position: 'top' }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'Orders' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: 'Trades' },
                    grid: { drawOnChartArea: false }
                },
                x: {
                    display: false
                }
            }
        }
    });
}

// Activity feed state tracking
let lastOrdersCount = 0;
let lastTradesCount = 0;
let lastCommitIndex = 0;
const maxActivityItems = 10;

// Add activity to feed
function addActivity(icon, text, type = '') {
    const feed = document.getElementById('activityFeed');
    const now = new Date().toLocaleTimeString();

    const item = document.createElement('div');
    item.className = `activity-item ${type}`;
    item.innerHTML = `
        <span class="activity-icon">${icon}</span>
        <span class="activity-text">${text}</span>
        <span class="activity-time">${now}</span>
    `;

    // Add to top of feed
    feed.insertBefore(item, feed.firstChild);

    // Keep only last maxActivityItems
    while (feed.children.length > maxActivityItems) {
        feed.removeChild(feed.lastChild);
    }
}

// Track and generate activities
function trackActivities(data) {
    // Track new orders
    if (data.total_orders > lastOrdersCount) {
        const newOrders = data.total_orders - lastOrdersCount;
        addActivity('📝', `${newOrders} new order${newOrders > 1 ? 's' : ''} committed`, 'order');
        lastOrdersCount = data.total_orders;
    }

    // Track new trades
    if (data.total_trades > lastTradesCount) {
        const newTrades = data.total_trades - lastTradesCount;
        addActivity('💰', `${newTrades} trade${newTrades > 1 ? 's' : ''} executed`, 'trade');
        lastTradesCount = data.total_trades;
    }

    // Track consensus progress
    const leaderNode = Object.values(data.nodes || {}).find(n => n.is_leader);
    if (leaderNode && leaderNode.commit_index > lastCommitIndex) {
        const blocks = leaderNode.commit_index - lastCommitIndex;
        if (blocks >= 100) { // Only show for significant progress
            addActivity('🔄', `Consensus reached on ${blocks} block${blocks > 1 ? 's' : ''}`, 'consensus');
        }
        lastCommitIndex = leaderNode.commit_index;
    }

    // Track leader changes
    if (data.leader_node && window.lastLeader && data.leader_node !== window.lastLeader) {
        addActivity('👑', `Leadership changed to ${data.leader_node}`, 'consensus');
    }
    window.lastLeader = data.leader_node;

    // Track cluster health
    if (data.health_status === 'degraded' && !window.lastDegraded) {
        addActivity('⚠️', 'Cluster health degraded', 'error');
        window.lastDegraded = true;
    } else if (data.health_status === 'healthy' && window.lastDegraded) {
        addActivity('✅', 'Cluster health restored', 'consensus');
        window.lastDegraded = false;
    }
}

// Update charts with new data
function updateCharts(data) {
    const now = new Date().toLocaleTimeString();

    // Add new data
    timestamps.push(now);
    throughputData.push(data.throughput_ops || 0);
    ordersData.push(data.total_orders || 0);
    tradesData.push(data.total_trades || 0);

    // Keep only last maxDataPoints
    if (timestamps.length > maxDataPoints) {
        timestamps.shift();
        throughputData.shift();
        ordersData.shift();
        tradesData.shift();
    }

    // Update progress bars
    const progressPercent = Math.min((timestamps.length / 3) * 100, 100);
    document.getElementById('throughputProgressBar').style.width = progressPercent + '%';
    document.getElementById('ordersProgressBar').style.width = progressPercent + '%';
    document.getElementById('throughputProgressText').textContent = `${timestamps.length}/3 data points`;
    document.getElementById('ordersProgressText').textContent = `${timestamps.length}/3 data points`;

    // Show charts after collecting enough data points (at least 3)
    if (timestamps.length >= 3) {
        // Hide loading indicators and show charts
        const throughputLoading = document.getElementById('throughputLoading');
        const ordersLoading = document.getElementById('ordersLoading');
        const throughputCanvas = document.getElementById('throughputChart');
        const ordersCanvas = document.getElementById('ordersTradesChart');

        if (throughputLoading && throughputLoading.style.display !== 'none') {
            throughputLoading.style.display = 'none';
            throughputCanvas.style.display = 'block';
        }
        if (ordersLoading && ordersLoading.style.display !== 'none') {
            ordersLoading.style.display = 'none';
            ordersCanvas.style.display = 'block';
        }
    }

    // Update charts
    if (throughputChart) {
        throughputChart.update('none');
    }
    if (ordersTradesChart) {
        ordersTradesChart.update('none');
    }

    // Update stats
    document.getElementById('currentThroughput').textContent = (data.throughput_ops || 0).toFixed(2);
    const avgThroughput = throughputData.reduce((a, b) => a + b, 0) / throughputData.length;
    document.getElementById('avgThroughput').textContent = avgThroughput.toFixed(2);

    document.getElementById('totalOrders').textContent = (data.total_orders || 0).toLocaleString();
    document.getElementById('totalTrades').textContent = (data.total_trades || 0).toLocaleString();
    const matchRate = data.total_orders > 0 ? (data.total_trades / data.total_orders * 100) : 0;
    document.getElementById('matchRate').textContent = matchRate.toFixed(1) + '%';

    // Update performance bars
    const maxThroughput = 500; // Assumed max for visualization
    const throughputPercent = Math.min((data.throughput_ops / maxThroughput) * 100, 100);
    document.getElementById('throughputBar').style.width = throughputPercent + '%';
    document.getElementById('throughputPercent').textContent = throughputPercent.toFixed(0) + '%';

    const healthPercent = (data.healthy_nodes / data.cluster_size) * 100;
    document.getElementById('healthBar').style.width = healthPercent + '%';
    document.getElementById('healthPercent').textContent = healthPercent.toFixed(0) + '%';
}

// Update node table
function updateNodeTable(nodes) {
    const tbody = document.getElementById('nodesTableBody');
    tbody.innerHTML = '';

    for (const [nodeId, node] of Object.entries(nodes)) {
        const row = tbody.insertRow();

        // Node ID
        row.insertCell().textContent = nodeId;

        // Role
        const roleCell = row.insertCell();
        const role = node.is_leader ? 'LEADER' : 'FOLLOWER';
        const roleClass = node.is_leader ? 'role-leader' : 'role-follower';
        roleCell.innerHTML = `<span class="node-role ${roleClass}">${role}</span>`;

        // Status
        const statusCell = row.insertCell();
        const status = node.peers_connected > 0 || node.is_leader ? 'HEALTHY' : 'DISCONNECTED';
        const statusClass = status === 'HEALTHY' ? 'status-healthy' : 'status-degraded';
        statusCell.innerHTML = `<span class="node-status ${statusClass}">${status}</span>`;

        // Commit Index
        row.insertCell().textContent = node.commit_index.toLocaleString();

        // Orders
        row.insertCell().textContent = node.orders_committed.toLocaleString();

        // Trades
        row.insertCell().textContent = node.trades_executed.toLocaleString();

        // Messages (sent/received)
        row.insertCell().textContent = `↑${node.messages_sent} ↓${node.messages_received}`;

        // Sync Status
        const syncCell = row.insertCell();
        const syncPercent = node.log_length > 0 ? (node.commit_index / node.log_length) * 100 : 100;
        syncCell.innerHTML = `
            <div class="sync-bar">
                <div class="sync-fill" style="width: ${syncPercent}%"></div>
            </div>
            <span style="margin-left: 8px;">${syncPercent.toFixed(0)}%</span>
        `;
    }
}

// Update order book
async function updateOrderBook() {
    try {
        const response = await fetch('/api/orderbook');
        const data = await response.json();

        if (data.error) {
            console.error('Error fetching order book:', data.error);
            return;
        }

        // Update symbol
        document.getElementById('orderbookSymbol').textContent = data.symbol || 'N/A';

        // Update asks (sell orders) - show in reverse order (lowest price at bottom)
        const asksBody = document.getElementById('asksTableBody');
        if (data.asks && data.asks.length > 0) {
            let asksCumulative = 0;
            asksBody.innerHTML = data.asks.slice().reverse().map(([price, qty]) => {
                asksCumulative += qty;
                return `
                    <tr>
                        <td class="price">$${price.toFixed(2)}</td>
                        <td>${qty.toFixed(0)}</td>
                        <td style="color: #6b7280;">${asksCumulative.toFixed(0)}</td>
                    </tr>
                `;
            }).join('');
        } else {
            asksBody.innerHTML = '<tr><td colspan="3" style="text-align: center;"><em>No asks</em></td></tr>';
        }

        // Update bids (buy orders)
        const bidsBody = document.getElementById('bidsTableBody');
        if (data.bids && data.bids.length > 0) {
            let bidsCumulative = 0;
            bidsBody.innerHTML = data.bids.map(([price, qty]) => {
                bidsCumulative += qty;
                return `
                    <tr>
                        <td class="price">$${price.toFixed(2)}</td>
                        <td>${qty.toFixed(0)}</td>
                        <td style="color: #6b7280;">${bidsCumulative.toFixed(0)}</td>
                    </tr>
                `;
            }).join('');
        } else {
            bidsBody.innerHTML = '<tr><td colspan="3" style="text-align: center;"><em>No bids</em></td></tr>';
        }

        // Calculate and display spread
        if (data.bids && data.bids.length > 0 && data.asks && data.asks.length > 0) {
            const bestBid = data.bids[0][0];
            const bestAsk = data.asks[0][0];
            const spread = bestAsk - bestBid;
            const spreadPercent = ((spread / bestBid) * 100).toFixed(3);

            document.getElementById('spreadIndicator').innerHTML = `
                <div class="spread-label">Spread</div>
                <div class="spread-value">$${spread.toFixed(2)}</div>
                <div style="font-size: 0.85em; opacity: 0.9;">(${spreadPercent}%)</div>
            `;
        } else {
            document.getElementById('spreadIndicator').innerHTML = `
                <div class="spread-label">Spread</div>
                <div class="spread-value">--</div>
            `;
        }

    } catch (error) {
        console.error('Error updating order book:', error);
    }
}

// Fetch and update data
async function updateDashboard() {
    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();

        // Update status bar
        const healthClass = data.health_status === 'healthy' ? 'health-healthy' :
                          data.health_status === 'degraded' ? 'health-degraded' : 'health-unhealthy';
        document.getElementById('clusterHealth').className = 'value ' + healthClass;
        document.getElementById('clusterHealth').textContent = data.health_status.toUpperCase();
        document.getElementById('leaderNode').textContent = data.leader_node || 'None';
        document.getElementById('currentTerm').textContent = data.current_term;
        document.getElementById('nodeCount').textContent = `${data.healthy_nodes}/${data.cluster_size}`;

        // Update consensus indicator
        const indicator = document.getElementById('consensusIndicator');
        if (data.consensus_aligned) {
            indicator.innerHTML = '<div class="indicator-circle aligned"></div><span>ALIGNED</span>';
            indicator.style.background = '#f0fdf4';
            indicator.style.color = '#10b981';
        } else {
            indicator.innerHTML = '<div class="indicator-circle misaligned"></div><span>MISALIGNED</span>';
            indicator.style.background = '#fef2f2';
            indicator.style.color = '#ef4444';
        }

        document.getElementById('consensusTerm').textContent = data.current_term;

        // Get leader node for commit index and log length
        const leaderNode = Object.values(data.nodes).find(n => n.is_leader);
        if (leaderNode) {
            document.getElementById('commitIndex').textContent = leaderNode.commit_index.toLocaleString();
            document.getElementById('logLength').textContent = leaderNode.log_length.toLocaleString();
        }

        // Update charts
        updateCharts(data);

        // Track activities
        trackActivities(data);

        // Update node table
        updateNodeTable(data.nodes);

        // Update order book
        updateOrderBook();

        // Update timestamp
        document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();

    } catch (error) {
        console.error('Error fetching metrics:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    updateDashboard();
    setInterval(updateDashboard, 1000); // Update every 1 second
});
'''


class EnhancedDashboardServer(DashboardServer):
    """Enhanced dashboard server with visualizations."""

    def __init__(self, collector, host='localhost', port=8080):
        # Override the handler class
        self.collector = collector
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None

    def start(self):
        """Start the enhanced dashboard server."""
        from http.server import HTTPServer
        import threading

        # Set collector as class variable (same as original dashboard)
        EnhancedDashboardHandler.collector = self.collector

        self.server = HTTPServer((self.host, self.port), EnhancedDashboardHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        print(f"\n{'='*70}")
        print(f"Enhanced Dashboard server started at http://{self.host}:{self.port}")
        print(f"{'='*70}\n")
