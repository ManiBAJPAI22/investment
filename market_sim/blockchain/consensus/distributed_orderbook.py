"""
Distributed Order Book with Raft Consensus.

Implements a fault-tolerant distributed order book using Raft consensus
to ensure all nodes agree on the order book state and trade execution.
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from core.models.base import Order, Trade, OrderBook, OrderSide, OrderStatus, OrderType
from market.exchange.matching_engine import MatchingEngine
from .raft_node import RaftNode
from .log_entry import LogEntry, LogEntryType


class DistributedOrderBook:
    """
    Distributed order book with consensus-based replication.

    Uses Raft consensus to ensure all nodes maintain the same order book
    state and agree on trade execution order.
    """

    def __init__(self, symbol: str, node_id: str, cluster_nodes: List[str]):
        """
        Initialize a distributed order book node.

        Args:
            symbol: Trading symbol for this order book
            node_id: Unique identifier for this node
            cluster_nodes: List of all node IDs in the cluster
        """
        self.symbol = symbol
        self.node_id = node_id

        # Local matching engine (state machine)
        self.matching_engine = MatchingEngine(symbol)

        # Raft consensus node
        self.raft_node = RaftNode(node_id, cluster_nodes)
        self.raft_node.set_apply_callback(self._apply_log_entry)

        # Track pending orders (submitted but not yet committed)
        self.pending_orders: Dict[str, Order] = {}

        # Statistics
        self.stats = {
            'orders_submitted': 0,
            'orders_committed': 0,
            'orders_rejected': 0,
            'trades_executed': 0,
            'consensus_failures': 0
        }

    def set_network(self, network: Dict[str, 'DistributedOrderBook']) -> None:
        """Set the network of distributed order book nodes."""
        # Convert to Raft network
        raft_network = {node_id: node.raft_node for node_id, node in network.items()}
        self.raft_node.set_network(raft_network)

    # ==================== Order Submission ====================

    def submit_order(self, order: Order) -> bool:
        """
        Submit an order to the distributed order book.

        The order will be replicated via Raft consensus before execution.

        Args:
            order: The order to submit

        Returns:
            True if order was accepted by leader, False otherwise
        """
        if not self.raft_node.is_leader():
            # Forward to leader (in real impl, client would redirect)
            self.stats['orders_rejected'] += 1
            return False

        # Serialize order data
        order_data = self._serialize_order(order)

        # Append to Raft log
        success = self.raft_node.append_entry(LogEntryType.ORDER_SUBMIT, order_data)

        if success:
            self.pending_orders[str(order.id)] = order
            self.stats['orders_submitted'] += 1
            return True
        else:
            self.stats['orders_rejected'] += 1
            return False

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order in the distributed order book.

        Args:
            order_id: ID of the order to cancel

        Returns:
            True if cancellation was accepted, False otherwise
        """
        if not self.raft_node.is_leader():
            self.stats['orders_rejected'] += 1
            return False

        # Append cancellation to Raft log
        success = self.raft_node.append_entry(
            LogEntryType.ORDER_CANCEL,
            {"order_id": order_id}
        )

        if success:
            return True
        else:
            return False

    # ==================== State Machine Application ====================

    def _apply_log_entry(self, entry: LogEntry) -> None:
        """
        Apply a committed log entry to the order book state machine.

        This is called by Raft when an entry is committed.
        """
        if entry.entry_type == LogEntryType.ORDER_SUBMIT:
            self._apply_order_submit(entry)
        elif entry.entry_type == LogEntryType.ORDER_CANCEL:
            self._apply_order_cancel(entry)
        elif entry.entry_type == LogEntryType.TRADE_EXECUTE:
            # Trades are recorded, not executed separately
            pass

    def _apply_order_submit(self, entry: LogEntry) -> None:
        """Apply an order submission to the matching engine."""
        order_data = entry.data
        order = self._deserialize_order(order_data)

        # Remove from pending if present
        if str(order.id) in self.pending_orders:
            del self.pending_orders[str(order.id)]

        # Process order through matching engine
        trades = self.matching_engine.process_order(order)

        # Record executed trades
        if trades:
            self.stats['trades_executed'] += len(trades)

        self.stats['orders_committed'] += 1

    def _apply_order_cancel(self, entry: LogEntry) -> None:
        """Apply an order cancellation to the matching engine."""
        order_id = entry.data['order_id']

        # Cancel order in matching engine
        cancelled_order = self.matching_engine.cancel_order(order_id)

        if cancelled_order:
            self.stats['orders_committed'] += 1

    # ==================== Consensus Operations ====================

    def tick(self) -> None:
        """
        Process one tick of the consensus algorithm.

        Should be called periodically to maintain consensus.
        """
        # Check for election timeout
        self.raft_node.check_election_timeout()

        # If leader, send heartbeats and replicate log
        if self.raft_node.is_leader():
            self.raft_node.send_heartbeat()
            self.raft_node.replicate_log()

    def check_election_result(self) -> None:
        """Check and finalize election results."""
        self.raft_node.check_election_result()

    # ==================== Query Operations ====================

    def get_order_book_snapshot(self, depth: int = 10) -> Tuple[List[Tuple[Decimal, Decimal]],
                                                                  List[Tuple[Decimal, Decimal]]]:
        """
        Get a snapshot of the current order book.

        Args:
            depth: Number of price levels to return

        Returns:
            Tuple of (bids, asks) as lists of (price, quantity) tuples
        """
        return self.matching_engine.get_order_book_snapshot(depth)

    def get_order_book(self) -> OrderBook:
        """Get the current order book state."""
        return self.matching_engine.order_book

    def get_trades(self) -> List[Trade]:
        """Get all executed trades."""
        return self.matching_engine.trades

    def is_leader(self) -> bool:
        """Check if this node is the current leader."""
        return self.raft_node.is_leader()

    def get_leader_id(self) -> Optional[str]:
        """Get the ID of the current leader."""
        return self.raft_node.get_leader_id()

    def get_state(self) -> Dict:
        """Get comprehensive state information."""
        return {
            'symbol': self.symbol,
            'node_id': self.node_id,
            'is_leader': self.is_leader(),
            'leader_id': self.get_leader_id(),
            'raft_state': self.raft_node.get_state(),
            'order_book': {
                'symbol': self.matching_engine.order_book.symbol,
                'bid_levels': len(self.matching_engine.order_book.bids),
                'ask_levels': len(self.matching_engine.order_book.asks),
                'last_updated': self.matching_engine.order_book.last_updated.isoformat()
            },
            'stats': self.stats,
            'pending_orders': len(self.pending_orders)
        }

    # ==================== Serialization ====================

    def _serialize_order(self, order: Order) -> Dict:
        """Serialize an order to dictionary."""
        return {
            'id': str(order.id),
            'symbol': order.symbol,
            'side': order.side.value,
            'type': order.type.value,
            'quantity': str(order.quantity),
            'price': str(order.price) if order.price else None,
            'stop_price': str(order.stop_price) if order.stop_price else None,
            'agent_id': order.agent_id,
            'created_at': order.created_at.isoformat()
        }

    def _deserialize_order(self, data: Dict) -> Order:
        """Deserialize an order from dictionary."""
        from uuid import UUID

        order_type = OrderType(data['type'])
        if order_type == OrderType.MARKET:
            return Order.create_market_order(
                symbol=data['symbol'],
                side=OrderSide(data['side']),
                quantity=Decimal(data['quantity']),
                agent_id=data['agent_id']
            )
        else:
            return Order.create_limit_order(
                symbol=data['symbol'],
                side=OrderSide(data['side']),
                quantity=Decimal(data['quantity']),
                price=Decimal(data['price']),
                agent_id=data['agent_id']
            )

    # ==================== Testing Utilities ====================

    def force_election(self) -> None:
        """Force start an election (for testing)."""
        self.raft_node.start_election()

    def get_raft_node(self) -> RaftNode:
        """Get the underlying Raft node (for testing)."""
        return self.raft_node
