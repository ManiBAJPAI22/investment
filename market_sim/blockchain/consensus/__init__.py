"""
Consensus mechanisms implementation.

Implements distributed consensus algorithms for fault-tolerant
distributed market state management.

NEW FEATURES (Nov 2025):
- Distributed Exchange: Combines Raft consensus with matching engine
- Multi-Agent Trading: 4 agent types for realistic market simulation
- Log compaction for Raft (prevents unbounded memory growth)
- Metrics collection and monitoring utilities
- Enhanced benchmarking suite for performance comparison
"""

from .raft_node import RaftNode, NodeState, RaftConfig
from .log_entry import LogEntry, LogEntryType
from .distributed_orderbook import DistributedOrderBook
from .distributed_exchange import DistributedExchange
from .pow_blockchain import ProofOfWorkBlockchain, Transaction, Block
from .pos_blockchain import ProofOfStakeBlockchain, Validator
from .realistic_pos_blockchain import RealisticPoSBlockchain
from .log_compaction import LogCompactor, Snapshot, CompactedRaftNode
from .metrics_collector import MetricsCollector, HealthStatus, MetricType
from .production_raft import ProductionRaftNode

__all__ = [
    # Core Raft consensus
    'RaftNode',
    'RaftConfig',
    'NodeState',
    'LogEntry',
    'LogEntryType',
    'DistributedOrderBook',
    'DistributedExchange',  # NEW
    'ProductionRaftNode',   # NEW

    # Blockchain implementations
    'ProofOfWorkBlockchain',
    'ProofOfStakeBlockchain',
    'RealisticPoSBlockchain',
    'Transaction',
    'Block',
    'Validator',

    # Performance and monitoring
    'LogCompactor',
    'Snapshot',
    'CompactedRaftNode',
    'MetricsCollector',
    'HealthStatus',
    'MetricType',
]
