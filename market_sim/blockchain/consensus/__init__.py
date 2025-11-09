"""
Consensus mechanisms implementation.

Implements distributed consensus algorithms for fault-tolerant
distributed market state management.

NEW FEATURES (Nov 2025):
- Log compaction for Raft (prevents unbounded memory growth)
- Metrics collection and monitoring utilities
- Enhanced benchmarking suite for performance comparison
"""

from .raft_node import RaftNode, NodeState, RaftConfig
from .log_entry import LogEntry, LogEntryType
from .distributed_orderbook import DistributedOrderBook
from .pow_blockchain import ProofOfWorkBlockchain, Transaction, Block
from .pos_blockchain import ProofOfStakeBlockchain, Validator
from .realistic_pos_blockchain import RealisticPoSBlockchain
from .log_compaction import LogCompactor, Snapshot, CompactedRaftNode
from .metrics_collector import MetricsCollector, HealthStatus, MetricType

__all__ = [
    # Core Raft consensus
    'RaftNode',
    'RaftConfig',
    'NodeState',
    'LogEntry',
    'LogEntryType',
    'DistributedOrderBook',

    # Blockchain implementations
    'ProofOfWorkBlockchain',
    'ProofOfStakeBlockchain',
    'RealisticPoSBlockchain',
    'Transaction',
    'Block',
    'Validator',

    # Performance and monitoring (NEW)
    'LogCompactor',
    'Snapshot',
    'CompactedRaftNode',
    'MetricsCollector',
    'HealthStatus',
    'MetricType',
]
