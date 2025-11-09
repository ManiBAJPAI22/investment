"""
Metrics Collection and Monitoring for Consensus Systems.

Provides centralized metrics collection, health monitoring, and
performance tracking for distributed consensus implementations.

Features:
- Real-time performance metrics
- Health status monitoring
- Prometheus-compatible metric export
- Time-series data collection
- Alerting on anomalies
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque
import statistics


class HealthStatus(Enum):
    """Health status of a node or system."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"  # Monotonically increasing
    GAUGE = "gauge"      # Can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"  # Statistical summary


@dataclass
class Metric:
    """Represents a single metric."""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    help_text: str = ""


@dataclass
class HealthCheck:
    """Represents a health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Centralized metrics collection for consensus systems.

    Tracks performance, health, and operational metrics for
    distributed consensus implementations.
    """

    def __init__(self, node_id: str, history_size: int = 1000):
        """
        Initialize metrics collector.

        Args:
            node_id: Identifier for this node
            history_size: Number of historical data points to keep
        """
        self.node_id = node_id
        self.history_size = history_size

        # Metrics storage
        self.metrics: Dict[str, Metric] = {}
        self.metric_history: Dict[str, deque] = {}

        # Health checks
        self.health_checks: Dict[str, HealthCheck] = {}

        # Performance tracking
        self.operation_latencies: deque = deque(maxlen=history_size)
        self.throughput_samples: deque = deque(maxlen=history_size)

        # Alerts
        self.alerts: List[Dict[str, Any]] = []
        self.alert_callbacks: List[Callable] = []

        # Initialize standard metrics
        self._init_standard_metrics()

    def _init_standard_metrics(self) -> None:
        """Initialize standard consensus metrics."""
        # Consensus metrics
        self.register_metric("elections_started", MetricType.COUNTER,
                           "Number of elections started")
        self.register_metric("elections_won", MetricType.COUNTER,
                           "Number of elections won")
        self.register_metric("log_entries_total", MetricType.COUNTER,
                           "Total log entries appended")
        self.register_metric("log_size", MetricType.GAUGE,
                           "Current log size")
        self.register_metric("commit_index", MetricType.GAUGE,
                           "Current commit index")

        # Performance metrics
        self.register_metric("operation_latency_ms", MetricType.HISTOGRAM,
                           "Operation latency in milliseconds")
        self.register_metric("throughput_tps", MetricType.GAUGE,
                           "Throughput in transactions per second")

        # Health metrics
        self.register_metric("is_leader", MetricType.GAUGE,
                           "Whether this node is the leader (1=yes, 0=no)")
        self.register_metric("cluster_size", MetricType.GAUGE,
                           "Number of nodes in cluster")
        self.register_metric("healthy_nodes", MetricType.GAUGE,
                           "Number of healthy nodes")

    def register_metric(self, name: str, metric_type: MetricType,
                       help_text: str = "") -> None:
        """
        Register a new metric.

        Args:
            name: Metric name
            metric_type: Type of metric
            help_text: Description of the metric
        """
        self.metrics[name] = Metric(
            name=name,
            type=metric_type,
            value=0.0,
            timestamp=datetime.utcnow(),
            labels={'node': self.node_id},
            help_text=help_text
        )
        self.metric_history[name] = deque(maxlen=self.history_size)

    def record_metric(self, name: str, value: float,
                     labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels
        """
        if name not in self.metrics:
            # Auto-register unknown metrics as gauges
            self.register_metric(name, MetricType.GAUGE)

        metric = self.metrics[name]
        metric.value = value
        metric.timestamp = datetime.utcnow()

        if labels:
            metric.labels.update(labels)

        # Store in history
        self.metric_history[name].append((metric.timestamp, value))

    def increment_counter(self, name: str, amount: float = 1.0) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            amount: Amount to increment
        """
        if name in self.metrics:
            self.record_metric(name, self.metrics[name].value + amount)
        else:
            self.record_metric(name, amount)

    def record_latency(self, operation: str, latency_ms: float) -> None:
        """
        Record operation latency.

        Args:
            operation: Operation name
            latency_ms: Latency in milliseconds
        """
        self.operation_latencies.append({
            'operation': operation,
            'latency_ms': latency_ms,
            'timestamp': datetime.utcnow()
        })

        self.record_metric(f"{operation}_latency_ms", latency_ms)

    def record_throughput(self, transactions: int, duration_s: float) -> None:
        """
        Record throughput measurement.

        Args:
            transactions: Number of transactions
            duration_s: Duration in seconds
        """
        tps = transactions / duration_s if duration_s > 0 else 0

        self.throughput_samples.append({
            'tps': tps,
            'timestamp': datetime.utcnow()
        })

        self.record_metric("throughput_tps", tps)

    def update_from_raft_node(self, raft_node: Any) -> None:
        """
        Update metrics from a Raft node.

        Args:
            raft_node: RaftNode instance
        """
        state = raft_node.get_state()

        # Update consensus metrics
        self.record_metric("elections_started",
                          state['stats']['elections_started'])
        self.record_metric("elections_won",
                          state['stats']['elections_won'])
        self.record_metric("log_size", state['log_size'])
        self.record_metric("commit_index", state['commit_index'])
        self.record_metric("is_leader", 1.0 if raft_node.is_leader() else 0.0)

    def update_from_orderbook(self, orderbook: Any) -> None:
        """
        Update metrics from a distributed order book.

        Args:
            orderbook: DistributedOrderBook instance
        """
        state = orderbook.get_state()
        stats = state['stats']

        # Update order book metrics
        self.record_metric("orders_submitted", stats['orders_submitted'])
        self.record_metric("orders_committed", stats['orders_committed'])
        self.record_metric("orders_rejected", stats['orders_rejected'])
        self.record_metric("trades_executed", stats['trades_executed'])

    def add_health_check(self, name: str, status: HealthStatus,
                        message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Add or update a health check.

        Args:
            name: Health check name
            status: Health status
            message: Status message
            details: Optional additional details
        """
        self.health_checks[name] = HealthCheck(
            name=name,
            status=status,
            message=message,
            timestamp=datetime.utcnow(),
            details=details or {}
        )

        # Check for alerts
        if status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]:
            self._trigger_alert(name, status, message)

    def get_overall_health(self) -> HealthStatus:
        """
        Get overall health status.

        Returns:
            Overall health status
        """
        if not self.health_checks:
            return HealthStatus.UNKNOWN

        statuses = [check.status for check in self.health_checks.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def get_metric_stats(self, name: str, window: Optional[timedelta] = None) -> Dict[str, float]:
        """
        Get statistics for a metric.

        Args:
            name: Metric name
            window: Time window (None = all history)

        Returns:
            Dictionary with min, max, avg, p50, p95, p99
        """
        if name not in self.metric_history:
            return {}

        history = list(self.metric_history[name])

        # Filter by time window
        if window:
            cutoff = datetime.utcnow() - window
            history = [(ts, val) for ts, val in history if ts >= cutoff]

        if not history:
            return {}

        values = [val for _, val in history]

        return {
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'median': statistics.median(values),
            'p95': self._percentile(values, 0.95),
            'p99': self._percentile(values, 0.99),
            'count': len(values)
        }

    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * p
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)

    def _trigger_alert(self, name: str, status: HealthStatus, message: str) -> None:
        """Trigger an alert."""
        alert = {
            'name': name,
            'status': status.value,
            'message': message,
            'node_id': self.node_id,
            'timestamp': datetime.utcnow().isoformat()
        }

        self.alerts.append(alert)

        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")

    def register_alert_callback(self, callback: Callable) -> None:
        """Register a callback for alerts."""
        self.alert_callbacks.append(callback)

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []

        for name, metric in self.metrics.items():
            # HELP line
            if metric.help_text:
                lines.append(f"# HELP {name} {metric.help_text}")

            # TYPE line
            type_map = {
                MetricType.COUNTER: "counter",
                MetricType.GAUGE: "gauge",
                MetricType.HISTOGRAM: "histogram",
                MetricType.SUMMARY: "summary"
            }
            lines.append(f"# TYPE {name} {type_map[metric.type]}")

            # Metric line with labels
            labels_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
            lines.append(f"{name}{{{labels_str}}} {metric.value}")

        return "\n".join(lines)

    def get_report(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics report.

        Returns:
            Dictionary with all metrics and health information
        """
        return {
            'node_id': self.node_id,
            'timestamp': datetime.utcnow().isoformat(),
            'overall_health': self.get_overall_health().value,
            'metrics': {
                name: {
                    'value': metric.value,
                    'type': metric.type.value,
                    'timestamp': metric.timestamp.isoformat()
                }
                for name, metric in self.metrics.items()
            },
            'health_checks': {
                name: {
                    'status': check.status.value,
                    'message': check.message,
                    'timestamp': check.timestamp.isoformat()
                }
                for name, check in self.health_checks.items()
            },
            'recent_alerts': self.alerts[-10:],  # Last 10 alerts
            'performance': {
                'latency': self.get_metric_stats('operation_latency_ms',
                                                 timedelta(minutes=5)),
                'throughput': self.get_metric_stats('throughput_tps',
                                                    timedelta(minutes=5))
            }
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        for metric in self.metrics.values():
            metric.value = 0.0
            metric.timestamp = datetime.utcnow()

        self.metric_history.clear()
        self.operation_latencies.clear()
        self.throughput_samples.clear()


# Example usage
if __name__ == '__main__':
    print("Metrics Collector Demonstration")
    print("=" * 80)

    # Create collector
    collector = MetricsCollector("node1")

    # Simulate some metrics
    print("\nRecording metrics...")
    for i in range(10):
        collector.increment_counter("elections_started")
        collector.record_metric("log_size", i * 100)
        collector.record_latency("append_entries", 0.5 + i * 0.1)
        time.sleep(0.01)

    # Add health checks
    collector.add_health_check(
        "leader_election",
        HealthStatus.HEALTHY,
        "Leader elected successfully"
    )

    collector.add_health_check(
        "log_replication",
        HealthStatus.HEALTHY,
        "Log replication working normally"
    )

    # Get report
    report = collector.get_report()

    print("\n✓ Metrics Report:")
    print(f"  Node ID: {report['node_id']}")
    print(f"  Overall Health: {report['overall_health']}")

    print(f"\n  Key Metrics:")
    for name, data in list(report['metrics'].items())[:5]:
        print(f"    {name}: {data['value']}")

    print(f"\n  Health Checks:")
    for name, data in report['health_checks'].items():
        print(f"    {name}: {data['status']} - {data['message']}")

    # Export Prometheus format
    print("\n✓ Prometheus Export:")
    print(collector.export_prometheus()[:300] + "...")

    print("\n" + "=" * 80)
    print("✓ Metrics collector demonstration complete!")
