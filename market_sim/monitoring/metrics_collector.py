"""
Real-Time Metrics Collection for Distributed Consensus

Collects, aggregates, and exposes metrics from distributed consensus cluster
for real-time monitoring and analysis.

Features:
- Real-time metric collection from all nodes
- Time-series data aggregation
- Consensus health monitoring
- Performance metrics tracking
- Alert generation for anomalies

Author: Blockchain Consensus Implementation Team
Date: November 2025
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import json


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class HealthStatus(Enum):
    """Health status of cluster."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class NodeMetrics:
    """Metrics for a single node."""
    node_id: str
    timestamp: float

    # Raft metrics
    state: str  # LEADER, FOLLOWER, CANDIDATE
    current_term: int
    commit_index: int
    last_applied: int
    log_length: int

    # Performance metrics
    orders_submitted: int = 0
    orders_committed: int = 0
    trades_executed: int = 0
    consensus_latency_ms: float = 0.0

    # Health metrics
    is_leader: bool = False
    last_heartbeat: float = 0.0
    cpu_usage: float = 0.0
    memory_mb: float = 0.0

    # Network metrics
    peers_connected: int = 0
    messages_sent: int = 0
    messages_received: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ClusterMetrics:
    """Aggregated metrics for entire cluster."""
    timestamp: float
    cluster_size: int
    healthy_nodes: int
    leader_node: Optional[str]
    current_term: int

    # Aggregate performance
    total_orders: int = 0
    total_trades: int = 0
    throughput_ops: float = 0.0  # orders per second
    avg_latency_ms: float = 0.0

    # Health status
    health_status: HealthStatus = HealthStatus.UNKNOWN
    consensus_aligned: bool = True

    # Individual node metrics
    nodes: Dict[str, NodeMetrics] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['health_status'] = self.health_status.value
        return data


class MetricsCollector:
    """
    Real-time metrics collector for distributed consensus cluster.

    Collects metrics from all nodes, aggregates them, and provides
    real-time monitoring capabilities.
    """

    def __init__(
        self,
        collection_interval: float = 1.0,
        retention_period: int = 300,  # 5 minutes
        alert_callback: Optional[Callable] = None
    ):
        """
        Initialize metrics collector.

        Args:
            collection_interval: How often to collect metrics (seconds)
            retention_period: How long to retain metrics (seconds)
            alert_callback: Callback for alerts (optional)
        """
        self.collection_interval = collection_interval
        self.retention_period = retention_period
        self.alert_callback = alert_callback

        # Cluster to monitor
        self.cluster: Dict[str, Any] = {}

        # Time-series data
        self.metrics_history: deque = deque(maxlen=retention_period)
        self.node_metrics_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=retention_period)
        )

        # Current metrics
        self.current_metrics: Optional[ClusterMetrics] = None

        # Collection thread
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Alert state
        self.alerts: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            'max_latency_ms': 1000,
            'min_healthy_nodes': 2,
            'max_term_difference': 5,
        }

    def set_cluster(self, cluster: Dict[str, Any]) -> None:
        """
        Set the cluster to monitor.

        Args:
            cluster: Dictionary of node_id -> DistributedExchange
        """
        with self._lock:
            self.cluster = cluster

    def start(self) -> None:
        """Start metrics collection."""
        if self._running:
            return

        self._running = True
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True
        )
        self._collection_thread.start()

    def stop(self) -> None:
        """Stop metrics collection."""
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5.0)

    def _collection_loop(self) -> None:
        """Main collection loop."""
        while self._running:
            try:
                self._collect_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"Error in metrics collection: {e}")

    def _collect_metrics(self) -> None:
        """Collect metrics from all nodes."""
        with self._lock:
            if not self.cluster:
                return

            timestamp = time.time()
            node_metrics = {}

            # Collect from each node
            for node_id, exchange in self.cluster.items():
                metrics = self._collect_node_metrics(node_id, exchange, timestamp)
                node_metrics[node_id] = metrics

                # Add to history
                self.node_metrics_history[node_id].append(metrics)

            # Aggregate cluster metrics
            cluster_metrics = self._aggregate_cluster_metrics(
                node_metrics,
                timestamp
            )

            self.current_metrics = cluster_metrics
            self.metrics_history.append(cluster_metrics)

            # Check for alerts
            self._check_alerts(cluster_metrics)

    def _collect_node_metrics(
        self,
        node_id: str,
        exchange: Any,
        timestamp: float
    ) -> NodeMetrics:
        """Collect metrics from a single node."""
        raft_node = exchange.orderbook.raft_node

        # Get Raft state
        state_map = {
            0: "FOLLOWER",
            1: "CANDIDATE",
            2: "LEADER"
        }

        return NodeMetrics(
            node_id=node_id,
            timestamp=timestamp,
            state=state_map.get(raft_node.state.value, "UNKNOWN"),
            current_term=raft_node.current_term,
            commit_index=raft_node.commit_index,
            last_applied=raft_node.last_applied,
            log_length=len(raft_node.log),
            orders_submitted=exchange.orderbook.stats.get('orders_submitted', 0),
            orders_committed=exchange.orderbook.stats.get('orders_committed', 0),
            trades_executed=exchange.metrics.get('trades_executed', 0),
            is_leader=exchange.is_leader(),
            peers_connected=len(raft_node.network),
            messages_sent=raft_node.stats.get('heartbeats_sent', 0),
            messages_received=raft_node.stats.get('heartbeats_received', 0),
        )

    def _aggregate_cluster_metrics(
        self,
        node_metrics: Dict[str, NodeMetrics],
        timestamp: float
    ) -> ClusterMetrics:
        """Aggregate metrics across all nodes."""
        if not node_metrics:
            return ClusterMetrics(
                timestamp=timestamp,
                cluster_size=0,
                healthy_nodes=0,
                leader_node=None,
                current_term=0,
                health_status=HealthStatus.UNKNOWN
            )

        # Find leader
        leader_node = None
        max_term = 0
        for node_id, metrics in node_metrics.items():
            if metrics.is_leader:
                leader_node = node_id
            max_term = max(max_term, metrics.current_term)

        # Count healthy nodes
        healthy_nodes = sum(
            1 for m in node_metrics.values()
            if m.peers_connected > 0 or m.is_leader
        )

        # Calculate aggregate performance
        total_orders = sum(m.orders_committed for m in node_metrics.values())
        total_trades = sum(m.trades_executed for m in node_metrics.values())

        # Calculate throughput from history
        throughput = self._calculate_throughput()

        # Determine health status
        health_status = self._determine_health_status(
            len(node_metrics),
            healthy_nodes,
            leader_node is not None,
            node_metrics
        )

        # Check consensus alignment
        commit_indexes = [m.commit_index for m in node_metrics.values()]
        consensus_aligned = (max(commit_indexes) - min(commit_indexes)) <= 10

        return ClusterMetrics(
            timestamp=timestamp,
            cluster_size=len(node_metrics),
            healthy_nodes=healthy_nodes,
            leader_node=leader_node,
            current_term=max_term,
            total_orders=total_orders,
            total_trades=total_trades,
            throughput_ops=throughput,
            health_status=health_status,
            consensus_aligned=consensus_aligned,
            nodes=node_metrics
        )

    def _calculate_throughput(self) -> float:
        """Calculate current throughput (ops/second)."""
        if len(self.metrics_history) < 2:
            return 0.0

        recent = list(self.metrics_history)[-10:]  # Last 10 samples
        if len(recent) < 2:
            return 0.0

        time_diff = recent[-1].timestamp - recent[0].timestamp
        if time_diff == 0:
            return 0.0

        order_diff = recent[-1].total_orders - recent[0].total_orders
        return order_diff / time_diff

    def _determine_health_status(
        self,
        cluster_size: int,
        healthy_nodes: int,
        has_leader: bool,
        node_metrics: Dict[str, NodeMetrics]
    ) -> HealthStatus:
        """Determine overall cluster health."""
        quorum_size = cluster_size // 2 + 1

        if not has_leader or healthy_nodes < quorum_size:
            return HealthStatus.UNHEALTHY

        if healthy_nodes < cluster_size:
            return HealthStatus.DEGRADED

        # Check for term disagreements
        terms = [m.current_term for m in node_metrics.values()]
        if max(terms) - min(terms) > 2:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def _check_alerts(self, metrics: ClusterMetrics) -> None:
        """Check for alert conditions."""
        alerts = []

        # Check health status
        if metrics.health_status == HealthStatus.UNHEALTHY:
            alerts.append({
                'severity': 'critical',
                'message': f'Cluster unhealthy: {metrics.healthy_nodes}/{metrics.cluster_size} nodes healthy',
                'timestamp': metrics.timestamp
            })

        # Check for missing leader
        if not metrics.leader_node:
            alerts.append({
                'severity': 'critical',
                'message': 'No leader elected',
                'timestamp': metrics.timestamp
            })

        # Check consensus alignment
        if not metrics.consensus_aligned:
            alerts.append({
                'severity': 'warning',
                'message': 'Consensus misalignment detected',
                'timestamp': metrics.timestamp
            })

        # Store alerts
        self.alerts.extend(alerts)

        # Trigger callback
        if alerts and self.alert_callback:
            for alert in alerts:
                self.alert_callback(alert)

    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current cluster metrics."""
        with self._lock:
            if self.current_metrics:
                return self.current_metrics.to_dict()
            return None

    def get_metrics_history(
        self,
        duration_seconds: int = 60
    ) -> List[Dict[str, Any]]:
        """Get metrics history for specified duration."""
        with self._lock:
            cutoff = time.time() - duration_seconds
            history = [
                m.to_dict()
                for m in self.metrics_history
                if m.timestamp >= cutoff
            ]
            return history

    def get_node_metrics(
        self,
        node_id: str,
        duration_seconds: int = 60
    ) -> List[Dict[str, Any]]:
        """Get metrics history for specific node."""
        with self._lock:
            if node_id not in self.node_metrics_history:
                return []

            cutoff = time.time() - duration_seconds
            history = [
                m.to_dict()
                for m in self.node_metrics_history[node_id]
                if m.timestamp >= cutoff
            ]
            return history

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        with self._lock:
            return self.alerts[-limit:]

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        with self._lock:
            self.alerts.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring summary."""
        metrics = self.get_current_metrics()
        if not metrics:
            return {'error': 'No metrics available'}

        return {
            'cluster': {
                'size': metrics['cluster_size'],
                'healthy_nodes': metrics['healthy_nodes'],
                'leader': metrics['leader_node'],
                'health_status': metrics['health_status'],
            },
            'performance': {
                'total_orders': metrics['total_orders'],
                'total_trades': metrics['total_trades'],
                'throughput_ops': round(metrics['throughput_ops'], 2),
            },
            'consensus': {
                'current_term': metrics['current_term'],
                'aligned': metrics['consensus_aligned'],
            },
            'alerts': {
                'count': len(self.alerts),
                'recent': self.get_alerts(limit=5),
            }
        }

    def get_order_book(self, depth: int = 10) -> Dict[str, Any]:
        """Get current order book from the leader node."""
        with self._lock:
            if not self.cluster:
                return {'error': 'No cluster configured'}

            # Find the leader exchange
            leader_exchange = None
            for exchange in self.cluster.values():
                if exchange.is_leader():
                    leader_exchange = exchange
                    break

            if not leader_exchange:
                return {'error': 'No leader found'}

            # Get order book snapshot from leader's matching engine
            bids, asks = leader_exchange.orderbook.matching_engine.get_order_book_snapshot(depth)

            # Convert Decimal to float for JSON serialization
            return {
                'symbol': leader_exchange.symbol,
                'leader': leader_exchange.node_id,
                'timestamp': time.time(),
                'bids': [[float(price), float(qty)] for price, qty in bids],
                'asks': [[float(price), float(qty)] for price, qty in asks],
            }
