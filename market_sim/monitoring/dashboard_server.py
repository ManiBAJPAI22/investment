"""
Real-Time Monitoring Dashboard Server

HTTP server providing REST API and web UI for monitoring distributed consensus cluster.

Features:
- REST API for metrics and cluster status
- Real-time updates via polling
- Web-based dashboard UI
- Alert management
- Performance visualization

Author: Blockchain Consensus Implementation Team
Date: November 2025
"""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

from .metrics_collector import MetricsCollector


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for dashboard."""

    # Class variable to hold metrics collector
    collector: Optional[MetricsCollector] = None

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)

        # API endpoints
        if path == '/api/metrics':
            self._handle_metrics(query)
        elif path == '/api/metrics/history':
            self._handle_metrics_history(query)
        elif path == '/api/node':
            self._handle_node_metrics(query)
        elif path == '/api/alerts':
            self._handle_alerts()
        elif path == '/api/summary':
            self._handle_summary()
        elif path == '/api/health':
            self._handle_health()
        elif path == '/api/orderbook':
            self._handle_orderbook()
        # Static files
        elif path == '/' or path == '/index.html':
            self._serve_dashboard()
        elif path == '/dashboard.js':
            self._serve_javascript()
        elif path == '/style.css':
            self._serve_css()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/api/alerts/clear':
            self._handle_clear_alerts()
        else:
            self.send_error(404, "Not Found")

    def _handle_metrics(self, query: Dict):
        """Return current metrics."""
        if not self.collector:
            self._send_json_response({'error': 'Collector not initialized'}, 503)
            return

        metrics = self.collector.get_current_metrics()
        if metrics:
            self._send_json_response(metrics)
        else:
            self._send_json_response({'error': 'No metrics available'}, 503)

    def _handle_metrics_history(self, query: Dict):
        """Return metrics history."""
        if not self.collector:
            self._send_json_response({'error': 'Collector not initialized'}, 503)
            return

        duration = int(query.get('duration', ['60'])[0])
        history = self.collector.get_metrics_history(duration)
        self._send_json_response({'history': history})

    def _handle_node_metrics(self, query: Dict):
        """Return node-specific metrics."""
        if not self.collector:
            self._send_json_response({'error': 'Collector not initialized'}, 503)
            return

        node_id = query.get('node_id', [None])[0]
        if not node_id:
            self._send_json_response({'error': 'node_id required'}, 400)
            return

        duration = int(query.get('duration', ['60'])[0])
        history = self.collector.get_node_metrics(node_id, duration)
        self._send_json_response({'node_id': node_id, 'history': history})

    def _handle_alerts(self):
        """Return recent alerts."""
        if not self.collector:
            self._send_json_response({'error': 'Collector not initialized'}, 503)
            return

        alerts = self.collector.get_alerts()
        self._send_json_response({'alerts': alerts})

    def _handle_summary(self):
        """Return monitoring summary."""
        if not self.collector:
            self._send_json_response({'error': 'Collector not initialized'}, 503)
            return

        summary = self.collector.get_summary()
        self._send_json_response(summary)

    def _handle_health(self):
        """Return health check."""
        if not self.collector:
            self._send_json_response({'status': 'unhealthy', 'reason': 'Collector not initialized'}, 503)
            return

        metrics = self.collector.get_current_metrics()
        if metrics:
            self._send_json_response({
                'status': 'healthy',
                'cluster_health': metrics['health_status'],
                'timestamp': metrics['timestamp']
            })
        else:
            self._send_json_response({'status': 'unhealthy', 'reason': 'No metrics'}, 503)

    def _handle_orderbook(self):
        """Return current order book."""
        if not self.collector:
            self._send_json_response({'error': 'Collector not initialized'}, 503)
            return

        orderbook = self.collector.get_order_book(depth=10)
        self._send_json_response(orderbook)

    def _handle_clear_alerts(self):
        """Clear all alerts."""
        if not self.collector:
            self._send_json_response({'error': 'Collector not initialized'}, 503)
            return

        self.collector.clear_alerts()
        self._send_json_response({'success': True})

    def _send_json_response(self, data: Dict[str, Any], status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _serve_dashboard(self):
        """Serve main dashboard HTML."""
        html = self._get_dashboard_html()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_javascript(self):
        """Serve dashboard JavaScript."""
        js = self._get_dashboard_js()
        self.send_response(200)
        self.send_header('Content-Type', 'application/javascript')
        self.end_headers()
        self.wfile.write(js.encode())

    def _serve_css(self):
        """Serve dashboard CSS."""
        css = self._get_dashboard_css()
        self.send_response(200)
        self.send_header('Content-Type', 'text/css')
        self.end_headers()
        self.wfile.write(css.encode())

    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Distributed Consensus Monitor</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="5">
</head>
<body>
    <div class="container">
        <h1>🔍 Distributed Consensus Monitoring Dashboard</h1>

        <div class="status-bar" id="statusBar">
            <div class="status-item">
                <span class="label">Cluster Health:</span>
                <span id="clusterHealth" class="value">Loading...</span>
            </div>
            <div class="status-item">
                <span class="label">Leader:</span>
                <span id="leaderNode" class="value">Loading...</span>
            </div>
            <div class="status-item">
                <span class="label">Term:</span>
                <span id="currentTerm" class="value">0</span>
            </div>
            <div class="status-item">
                <span class="label">Nodes:</span>
                <span id="nodeCount" class="value">0/0</span>
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Performance</h3>
                <div class="metric">
                    <span class="metric-label">Total Orders:</span>
                    <span id="totalOrders" class="metric-value">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Trades:</span>
                    <span id="totalTrades" class="metric-value">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Throughput:</span>
                    <span id="throughput" class="metric-value">0 ops/s</span>
                </div>
            </div>

            <div class="metric-card">
                <h3>Consensus</h3>
                <div class="metric">
                    <span class="metric-label">Aligned:</span>
                    <span id="consensusAligned" class="metric-value">Yes</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Current Term:</span>
                    <span id="consensusTerm" class="metric-value">0</span>
                </div>
            </div>

            <div class="metric-card">
                <h3>Alerts</h3>
                <div class="metric">
                    <span class="metric-label">Active Alerts:</span>
                    <span id="alertCount" class="metric-value">0</span>
                </div>
                <div id="recentAlerts" class="alert-list">
                    <em>No alerts</em>
                </div>
            </div>
        </div>

        <div class="nodes-section">
            <h2>Node Status</h2>
            <div id="nodesGrid" class="nodes-grid">
                <!-- Nodes will be populated by JavaScript -->
            </div>
        </div>

        <div class="footer">
            Last updated: <span id="lastUpdate">Never</span>
        </div>
    </div>
    <script src="/dashboard.js"></script>
</body>
</html>'''

    def _get_dashboard_css(self) -> str:
        """Generate dashboard CSS."""
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
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    background: white;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

h1 {
    color: #667eea;
    margin-bottom: 30px;
    text-align: center;
    font-size: 2em;
}

h2 {
    color: #764ba2;
    margin: 30px 0 20px 0;
    font-size: 1.5em;
}

h3 {
    color: #667eea;
    margin-bottom: 15px;
    font-size: 1.2em;
}

.status-bar {
    display: flex;
    justify-content: space-around;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 30px;
}

.status-item {
    text-align: center;
}

.status-item .label {
    display: block;
    font-size: 0.9em;
    color: #666;
    margin-bottom: 8px;
}

.status-item .value {
    display: block;
    font-size: 1.5em;
    font-weight: bold;
    color: #333;
}

.health-healthy { color: #10b981; }
.health-degraded { color: #f59e0b; }
.health-unhealthy { color: #ef4444; }
.health-unknown { color: #6b7280; }

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.metric-card {
    background: #f9fafb;
    padding: 20px;
    border-radius: 8px;
    border: 2px solid #e5e7eb;
}

.metric {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #e5e7eb;
}

.metric:last-child {
    border-bottom: none;
}

.metric-label {
    font-weight: 500;
    color: #6b7280;
}

.metric-value {
    font-weight: bold;
    color: #111827;
}

.alert-list {
    margin-top: 15px;
    max-height: 150px;
    overflow-y: auto;
}

.alert-item {
    padding: 8px;
    margin: 5px 0;
    border-radius: 4px;
    font-size: 0.9em;
}

.alert-critical {
    background: #fee2e2;
    color: #991b1b;
    border-left: 4px solid #ef4444;
}

.alert-warning {
    background: #fef3c7;
    color: #92400e;
    border-left: 4px solid #f59e0b;
}

.nodes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 15px;
}

.node-card {
    background: #f9fafb;
    padding: 15px;
    border-radius: 8px;
    border: 2px solid #e5e7eb;
}

.node-card.leader {
    border-color: #10b981;
    background: #ecfdf5;
}

.node-card.follower {
    border-color: #3b82f6;
    background: #eff6ff;
}

.node-card.candidate {
    border-color: #f59e0b;
    background: #fffbeb;
}

.node-header {
    font-weight: bold;
    margin-bottom: 10px;
    font-size: 1.1em;
}

.node-state {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    margin-left: 8px;
}

.state-leader {
    background: #10b981;
    color: white;
}

.state-follower {
    background: #3b82f6;
    color: white;
}

.state-candidate {
    background: #f59e0b;
    color: white;
}

.node-detail {
    font-size: 0.9em;
    margin: 5px 0;
    color: #6b7280;
}

.footer {
    text-align: center;
    margin-top: 30px;
    padding-top: 20px;
    border-top: 2px solid #e5e7eb;
    color: #6b7280;
    font-size: 0.9em;
}
'''

    def _get_dashboard_js(self) -> str:
        """Generate dashboard JavaScript."""
        return '''
// Dashboard JavaScript
let lastUpdateTime = null;

async function fetchMetrics() {
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();
        updateDashboard(data);
        lastUpdateTime = new Date();
        document.getElementById('lastUpdate').textContent = lastUpdateTime.toLocaleTimeString();
    } catch (error) {
        console.error('Error fetching metrics:', error);
    }
}

function updateDashboard(data) {
    // Update status bar
    const healthStatus = data.cluster.health_status;
    const healthElement = document.getElementById('clusterHealth');
    healthElement.textContent = healthStatus.toUpperCase();
    healthElement.className = 'value health-' + healthStatus;

    document.getElementById('leaderNode').textContent = data.cluster.leader || 'None';
    document.getElementById('currentTerm').textContent = data.consensus.current_term;
    document.getElementById('nodeCount').textContent =
        `${data.cluster.healthy_nodes}/${data.cluster.size}`;

    // Update performance metrics
    document.getElementById('totalOrders').textContent = data.performance.total_orders;
    document.getElementById('totalTrades').textContent = data.performance.total_trades;
    document.getElementById('throughput').textContent =
        `${data.performance.throughput_ops.toFixed(2)} ops/s`;

    // Update consensus metrics
    document.getElementById('consensusAligned').textContent =
        data.consensus.aligned ? 'Yes' : 'No';
    document.getElementById('consensusTerm').textContent = data.consensus.current_term;

    // Update alerts
    document.getElementById('alertCount').textContent = data.alerts.count;
    updateAlerts(data.alerts.recent);
}

function updateAlerts(alerts) {
    const alertContainer = document.getElementById('recentAlerts');

    if (!alerts || alerts.length === 0) {
        alertContainer.innerHTML = '<em>No alerts</em>';
        return;
    }

    alertContainer.innerHTML = alerts.map(alert =>
        `<div class="alert-item alert-${alert.severity}">
            ${alert.message}
        </div>`
    ).join('');
}

// Fetch metrics immediately and then every 2 seconds
fetchMetrics();
setInterval(fetchMetrics, 2000);
'''

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass  # Silent mode


class DashboardServer:
    """
    Dashboard server for monitoring distributed consensus.

    Provides REST API and web UI for real-time monitoring.
    """

    def __init__(
        self,
        collector: MetricsCollector,
        host: str = 'localhost',
        port: int = 8080
    ):
        """
        Initialize dashboard server.

        Args:
            collector: MetricsCollector instance
            host: Server host
            port: Server port
        """
        self.collector = collector
        self.host = host
        self.port = port

        # Set collector in handler class
        DashboardHandler.collector = collector

        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start dashboard server."""
        self.server = HTTPServer((self.host, self.port), DashboardHandler)

        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True
        )
        self.server_thread.start()

        print(f"\n{'='*70}")
        print(f"Dashboard server started at http://{self.host}:{self.port}")
        print(f"{'='*70}\n")

    def stop(self) -> None:
        """Stop dashboard server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def get_url(self) -> str:
        """Get dashboard URL."""
        return f"http://{self.host}:{self.port}"
