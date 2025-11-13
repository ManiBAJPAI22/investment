"""
Real-Time Monitoring for Distributed Consensus

This module provides comprehensive monitoring capabilities for distributed
consensus systems.

Components:
- MetricsCollector: Real-time metrics collection and aggregation
- DashboardServer: HTTP server with REST API and web UI

Author: Blockchain Consensus Implementation Team
Date: November 2025
"""

from .metrics_collector import (
    MetricsCollector,
    NodeMetrics,
    ClusterMetrics,
    HealthStatus,
    MetricType
)
from .dashboard_server import DashboardServer
from .dashboard_enhanced import EnhancedDashboardServer

__all__ = [
    'MetricsCollector',
    'NodeMetrics',
    'ClusterMetrics',
    'HealthStatus',
    'MetricType',
    'DashboardServer',
    'EnhancedDashboardServer',
]
