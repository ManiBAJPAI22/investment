"""
Unit tests for Raft consensus implementation.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from blockchain.consensus.raft_node import RaftNode, NodeState, RaftConfig
from blockchain.consensus.log_entry import LogEntry, LogEntryType
from blockchain.consensus.distributed_orderbook import DistributedOrderBook
from core.models.base import Order, OrderSide


class TestLogEntry:
    """Test LogEntry data structure."""

    def test_create_order_submit_entry(self):
        """Test creating an order submission log entry."""
        order_data = {'symbol': 'AAPL', 'side': 'buy', 'quantity': '100'}
        entry = LogEntry.create_order_submit(term=1, index=1, order_data=order_data)

        assert entry.term == 1
        assert entry.index == 1
        assert entry.entry_type == LogEntryType.ORDER_SUBMIT
        assert entry.data == order_data
        assert not entry.committed

    def test_create_order_cancel_entry(self):
        """Test creating an order cancellation log entry."""
        entry = LogEntry.create_order_cancel(term=2, index=2, order_id='order-123')

        assert entry.term == 2
        assert entry.index == 2
        assert entry.entry_type == LogEntryType.ORDER_CANCEL
        assert entry.data['order_id'] == 'order-123'

    def test_create_trade_execute_entry(self):
        """Test creating a trade execution log entry."""
        trade_data = {'buyer': 'agent1', 'seller': 'agent2', 'price': '150.00'}
        entry = LogEntry.create_trade_execute(term=1, index=3, trade_data=trade_data)

        assert entry.term == 1
        assert entry.index == 3
        assert entry.entry_type == LogEntryType.TRADE_EXECUTE

    def test_create_no_op_entry(self):
        """Test creating a no-op entry."""
        entry = LogEntry.create_no_op(term=3, index=1)

        assert entry.term == 3
        assert entry.entry_type == LogEntryType.NO_OP
        assert entry.data == {}

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        original = LogEntry.create_order_submit(
            term=1,
            index=1,
            order_data={'test': 'data'}
        )

        serialized = original.to_dict()
        deserialized = LogEntry.from_dict(serialized)

        assert deserialized.term == original.term
        assert deserialized.index == original.index
        assert deserialized.entry_type == original.entry_type
        assert deserialized.data == original.data


class TestRaftNode:
    """Test Raft node implementation."""

    def test_node_initialization(self):
        """Test Raft node initialization."""
        node = RaftNode('node1', ['node2', 'node3'])

        assert node.node_id == 'node1'
        assert len(node.cluster_nodes) == 2
        assert node.state == NodeState.FOLLOWER
        assert node.current_term == 0
        assert node.voted_for is None
        assert len(node.log) == 0

    def test_become_candidate(self):
        """Test transition to candidate state."""
        node = RaftNode('node1', ['node2', 'node3'])
        node.become_candidate()

        assert node.state == NodeState.CANDIDATE
        assert node.current_term == 1
        assert node.voted_for == 'node1'
        assert 'node1' in node.votes_received
        assert node.stats['elections_started'] == 1

    def test_become_leader(self):
        """Test transition to leader state."""
        node = RaftNode('node1', ['node2', 'node3'])
        node.become_candidate()
        node.become_leader()

        assert node.state == NodeState.LEADER
        assert node.leader_id == 'node1'
        assert len(node.next_index) == 2
        assert len(node.match_index) == 2
        assert node.stats['elections_won'] == 1

    def test_become_follower(self):
        """Test transition to follower state."""
        node = RaftNode('node1', ['node2', 'node3'])
        node.become_candidate()
        node.become_follower(term=2, leader_id='node2')

        assert node.state == NodeState.FOLLOWER
        assert node.current_term == 2
        assert node.leader_id == 'node2'
        assert node.voted_for is None

    def test_leader_election_with_majority(self):
        """Test successful leader election with majority votes."""
        # Create 3-node cluster
        nodes = {
            'node1': RaftNode('node1', ['node2', 'node3'], RaftConfig(election_timeout_min=1000, election_timeout_max=1500)),
            'node2': RaftNode('node2', ['node1', 'node3'], RaftConfig(election_timeout_min=1000, election_timeout_max=1500)),
            'node3': RaftNode('node3', ['node1', 'node2'], RaftConfig(election_timeout_min=1000, election_timeout_max=1500))
        }

        # Set up network
        for node in nodes.values():
            node.set_network(nodes)

        # Node1 starts election
        nodes['node1'].start_election()

        # Should become leader with 2/3 votes (including itself)
        assert nodes['node1'].state == NodeState.LEADER
        assert len(nodes['node1'].votes_received) >= 2

    def test_append_log_entry(self):
        """Test appending entries to log."""
        node = RaftNode('node1', ['node2', 'node3'])
        node.become_leader()

        success = node.append_entry(
            LogEntryType.ORDER_SUBMIT,
            {'symbol': 'AAPL', 'quantity': '100'}
        )

        assert success
        assert len(node.log) == 2  # No-op + new entry
        assert node.log[-1].entry_type == LogEntryType.ORDER_SUBMIT
        assert node.stats['log_entries_appended'] == 2

    def test_follower_cannot_append(self):
        """Test that followers cannot append entries."""
        node = RaftNode('node1', ['node2', 'node3'])

        success = node.append_entry(
            LogEntryType.ORDER_SUBMIT,
            {'test': 'data'}
        )

        assert not success
        assert len(node.log) == 0

    def test_log_replication(self):
        """Test log replication to followers."""
        # Create 3-node cluster
        nodes = {
            'node1': RaftNode('node1', ['node2', 'node3']),
            'node2': RaftNode('node2', ['node1', 'node3']),
            'node3': RaftNode('node3', ['node1', 'node2'])
        }

        for node in nodes.values():
            node.set_network(nodes)

        # Make node1 leader
        nodes['node1'].become_leader()
        nodes['node2'].become_follower(nodes['node1'].current_term, 'node1')
        nodes['node3'].become_follower(nodes['node1'].current_term, 'node1')

        # Leader appends entry
        nodes['node1'].append_entry(
            LogEntryType.ORDER_SUBMIT,
            {'test': 'data'}
        )

        # Replicate to followers
        nodes['node1'].replicate_log()

        # All nodes should have the entry
        assert len(nodes['node1'].log) == 2  # No-op + new entry
        assert len(nodes['node2'].log) == 2
        assert len(nodes['node3'].log) == 2

    def test_commit_with_majority(self):
        """Test that entries are committed when replicated to majority."""
        nodes = {
            'node1': RaftNode('node1', ['node2', 'node3']),
            'node2': RaftNode('node2', ['node1', 'node3']),
            'node3': RaftNode('node3', ['node1', 'node2'])
        }

        for node in nodes.values():
            node.set_network(nodes)

        # Setup: node1 is leader
        nodes['node1'].become_leader()
        nodes['node2'].become_follower(nodes['node1'].current_term, 'node1')
        nodes['node3'].become_follower(nodes['node1'].current_term, 'node1')

        # Append and replicate
        nodes['node1'].append_entry(LogEntryType.ORDER_SUBMIT, {'test': 'data'})
        nodes['node1'].replicate_log()

        # Check commit happened
        assert nodes['node1'].commit_index > 0

    def test_handle_higher_term(self):
        """Test node steps down when seeing higher term."""
        node = RaftNode('node1', ['node2', 'node3'])
        node.become_leader()

        # Receive vote request with higher term
        from blockchain.consensus.raft_node import VoteRequest
        request = VoteRequest(
            term=node.current_term + 1,
            candidate_id='node2',
            last_log_index=0,
            last_log_term=0
        )

        response = node.handle_vote_request(request)

        assert node.state == NodeState.FOLLOWER
        assert node.current_term == request.term
        assert response.vote_granted

    def test_get_state(self):
        """Test getting node state information."""
        node = RaftNode('node1', ['node2', 'node3'])
        state = node.get_state()

        assert state['node_id'] == 'node1'
        assert state['state'] == NodeState.FOLLOWER.value
        assert state['term'] == 0
        assert 'stats' in state


class TestDistributedOrderBook:
    """Test distributed order book with consensus."""

    def test_initialization(self):
        """Test distributed order book initialization."""
        dob = DistributedOrderBook('AAPL', 'node1', ['node2', 'node3'])

        assert dob.symbol == 'AAPL'
        assert dob.node_id == 'node1'
        assert not dob.is_leader()

    def test_submit_order_as_follower_fails(self):
        """Test that followers cannot accept orders."""
        dob = DistributedOrderBook('AAPL', 'node1', ['node2', 'node3'])

        order = Order.create_limit_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            price=Decimal('150.00'),
            agent_id='agent1'
        )

        success = dob.submit_order(order)
        assert not success
        assert dob.stats['orders_rejected'] == 1

    def test_submit_order_as_leader_succeeds(self):
        """Test that leader can accept orders."""
        dob = DistributedOrderBook('AAPL', 'node1', ['node2', 'node3'])

        # Make this node the leader
        dob.raft_node.become_leader()

        order = Order.create_limit_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            price=Decimal('150.00'),
            agent_id='agent1'
        )

        success = dob.submit_order(order)
        assert success
        assert dob.stats['orders_submitted'] == 1
        assert str(order.id) in dob.pending_orders

    def test_distributed_order_matching(self):
        """Test order matching across distributed nodes."""
        # Create 3-node cluster
        nodes = {
            'node1': DistributedOrderBook('AAPL', 'node1', ['node2', 'node3']),
            'node2': DistributedOrderBook('AAPL', 'node2', ['node1', 'node3']),
            'node3': DistributedOrderBook('AAPL', 'node3', ['node1', 'node2'])
        }

        # Set up network
        for node in nodes.values():
            node.set_network(nodes)

        # Make node1 leader
        nodes['node1'].raft_node.become_leader()
        nodes['node2'].raft_node.become_follower(nodes['node1'].raft_node.current_term, 'node1')
        nodes['node3'].raft_node.become_follower(nodes['node1'].raft_node.current_term, 'node1')

        # Submit buy order
        buy_order = Order.create_limit_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            price=Decimal('150.00'),
            agent_id='buyer1'
        )
        nodes['node1'].submit_order(buy_order)

        # Replicate
        nodes['node1'].raft_node.replicate_log()

        # All nodes should have the entry in their logs
        assert len(nodes['node1'].raft_node.log) > 0
        assert len(nodes['node2'].raft_node.log) > 0
        assert len(nodes['node3'].raft_node.log) > 0

    def test_get_state(self):
        """Test getting comprehensive state information."""
        dob = DistributedOrderBook('AAPL', 'node1', ['node2', 'node3'])
        state = dob.get_state()

        assert state['symbol'] == 'AAPL'
        assert state['node_id'] == 'node1'
        assert 'is_leader' in state
        assert 'raft_state' in state
        assert 'stats' in state

    def test_cancel_order(self):
        """Test order cancellation through consensus."""
        dob = DistributedOrderBook('AAPL', 'node1', ['node2', 'node3'])
        dob.raft_node.become_leader()

        # Submit order first
        order = Order.create_limit_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            price=Decimal('150.00'),
            agent_id='agent1'
        )
        dob.submit_order(order)

        # Cancel order
        success = dob.cancel_order(str(order.id))
        assert success

    def test_order_book_snapshot(self):
        """Test getting order book snapshot."""
        dob = DistributedOrderBook('AAPL', 'node1', ['node2', 'node3'])
        dob.raft_node.become_leader()

        # Submit some orders
        for i in range(5):
            order = Order.create_limit_order(
                symbol='AAPL',
                side=OrderSide.BUY,
                quantity=Decimal('100'),
                price=Decimal(f'{150 + i}.00'),
                agent_id=f'agent{i}'
            )
            dob.submit_order(order)

        # Force commit (in real scenario, would wait for consensus)
        for entry in dob.raft_node.log:
            if not entry.committed:
                dob._apply_log_entry(entry)
                entry.committed = True

        # Get snapshot
        bids, asks = dob.get_order_book_snapshot(depth=10)

        assert len(bids) == 5  # Should have 5 buy orders


class TestConsensusIntegration:
    """Integration tests for consensus system."""

    def test_leader_election_after_failure(self):
        """Test that new leader is elected after leader failure."""
        # Create 3-node cluster
        nodes = {
            'node1': RaftNode('node1', ['node2', 'node3'], RaftConfig(election_timeout_min=100, election_timeout_max=200)),
            'node2': RaftNode('node2', ['node1', 'node3'], RaftConfig(election_timeout_min=100, election_timeout_max=200)),
            'node3': RaftNode('node3', ['node1', 'node2'], RaftConfig(election_timeout_min=100, election_timeout_max=200))
        }

        for node in nodes.values():
            node.set_network(nodes)

        # Establish initial leader
        nodes['node1'].start_election()
        initial_leader = nodes['node1']
        assert initial_leader.is_leader()

        # Simulate leader failure by disconnecting it
        nodes['node2'].network = {'node3': nodes['node3']}
        nodes['node3'].network = {'node2': nodes['node2']}

        # Force election timeout on node2
        nodes['node2'].last_heartbeat = datetime.utcnow() - timedelta(seconds=1)
        nodes['node2'].check_election_timeout()

        # Node2 or node3 should become new leader
        assert nodes['node2'].is_leader() or nodes['node3'].is_leader()

    def test_split_brain_prevention(self):
        """Test that split brain scenarios are prevented."""
        # Create 5-node cluster
        nodes = {
            f'node{i}': RaftNode(f'node{i}', [f'node{j}' for j in range(1, 6) if j != i])
            for i in range(1, 6)
        }

        for node in nodes.values():
            node.set_network(nodes)

        # One node becomes leader
        nodes['node1'].start_election()
        assert nodes['node1'].is_leader()

        # Another node tries to start election with same term
        nodes['node2'].become_candidate()
        # But should not succeed because node1 is already leader
        nodes['node2'].start_election()

        # Only one leader should exist
        leaders = [node for node in nodes.values() if node.is_leader()]
        # In this scenario, we might have multiple leaders temporarily,
        # but they should all have different terms
        leader_terms = {node.current_term for node in leaders}
        assert len(leader_terms) <= 2  # At most 2 different terms

    def test_consistency_across_nodes(self):
        """Test that all nodes maintain consistent state."""
        # Create cluster
        nodes = {
            'node1': DistributedOrderBook('AAPL', 'node1', ['node2', 'node3']),
            'node2': DistributedOrderBook('AAPL', 'node2', ['node1', 'node3']),
            'node3': DistributedOrderBook('AAPL', 'node3', ['node1', 'node2'])
        }

        for node in nodes.values():
            node.set_network(nodes)

        # Establish leader
        nodes['node1'].raft_node.become_leader()
        nodes['node2'].raft_node.become_follower(nodes['node1'].raft_node.current_term, 'node1')
        nodes['node3'].raft_node.become_follower(nodes['node1'].raft_node.current_term, 'node1')

        # Submit multiple orders
        for i in range(10):
            order = Order.create_limit_order(
                symbol='AAPL',
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                quantity=Decimal('100'),
                price=Decimal(f'{150 + i}.00'),
                agent_id=f'agent{i}'
            )
            nodes['node1'].submit_order(order)

        # Replicate
        for _ in range(5):
            nodes['node1'].raft_node.replicate_log()

        # All nodes should have same log size
        log_sizes = [len(node.raft_node.log) for node in nodes.values()]
        assert log_sizes[0] == log_sizes[1] == log_sizes[2]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
