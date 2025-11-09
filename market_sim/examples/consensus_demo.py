"""
Demo script showcasing the Raft consensus implementation for distributed order book.

This script demonstrates:
1. Setting up a cluster of distributed order book nodes
2. Leader election
3. Order submission and replication
4. Fault tolerance (simulated node failure)
5. Visualization of consensus behavior

Usage:
    python examples/consensus_demo.py
"""

import time
import sys
from decimal import Decimal
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blockchain.consensus.distributed_orderbook import DistributedOrderBook
from blockchain.consensus.raft_node import RaftConfig
from core.models.base import Order, OrderSide

# Make visualization optional
try:
    from analysis.visualization.consensus_visualizer import ConsensusVisualizer
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print("Note: matplotlib not available, visualizations will be skipped")


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")


def print_node_states(nodes):
    """Print the current state of all nodes."""
    print("Current Node States:")
    print("-" * 80)
    for node_id, node in sorted(nodes.items()):
        state = node.get_state()
        status = "LEADER" if state['is_leader'] else "follower"
        print(f"  {node_id}: {status:10} | Term: {state['raft_state']['term']:2} | "
              f"Log: {state['raft_state']['log_size']:3} entries | "
              f"Committed: {state['raft_state']['commit_index']:3}")
    print("-" * 80)


def demo_leader_election():
    """Demonstrate leader election in a 5-node cluster."""
    print_separator()
    print("DEMO 1: Leader Election in a 5-Node Cluster")
    print_separator()

    # Create 5-node cluster
    print("Creating 5-node cluster...")
    node_ids = [f'node{i}' for i in range(1, 6)]
    nodes = {}

    for node_id in node_ids:
        other_nodes = [n for n in node_ids if n != node_id]
        config = RaftConfig(election_timeout_min=150, election_timeout_max=300)
        nodes[node_id] = DistributedOrderBook('AAPL', node_id, other_nodes)
        nodes[node_id].raft_node.config = config

    # Set up network
    print("Setting up network connections...")
    for node in nodes.values():
        node.set_network(nodes)

    print("\nInitial state (all nodes are followers):")
    print_node_states(nodes)

    # Start election
    print("\nStarting election on node1...")
    nodes['node1'].force_election()

    print("\nAfter election:")
    print_node_states(nodes)

    leader_id = None
    for node_id, node in nodes.items():
        if node.is_leader():
            leader_id = node_id
            break

    if leader_id:
        print(f"\n✓ Leader elected: {leader_id}")
    else:
        print("\n✗ No leader elected")

    return nodes


def demo_order_submission_and_replication(nodes):
    """Demonstrate order submission and log replication."""
    print_separator()
    print("DEMO 2: Order Submission and Log Replication")
    print_separator()

    # Find leader
    leader_node = None
    for node in nodes.values():
        if node.is_leader():
            leader_node = node
            break

    if not leader_node:
        print("No leader found. Cannot submit orders.")
        return

    print(f"Leader: {leader_node.node_id}")
    print("\nSubmitting 10 orders to the leader...")

    # Submit orders
    orders_submitted = 0
    for i in range(10):
        side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL
        order = Order.create_limit_order(
            symbol='AAPL',
            side=side,
            quantity=Decimal('100'),
            price=Decimal(f'{150 + i}.00'),
            agent_id=f'agent{i}'
        )

        success = leader_node.submit_order(order)
        if success:
            orders_submitted += 1

    print(f"✓ Successfully submitted {orders_submitted} orders")

    # Replicate to followers
    print("\nReplicating log to followers...")
    for _ in range(3):
        leader_node.raft_node.replicate_log()
        time.sleep(0.1)

    print("\nAfter replication:")
    print_node_states(nodes)

    # Check consistency
    log_sizes = [node.raft_node.log.__len__() for node in nodes.values()]
    if len(set(log_sizes)) == 1:
        print(f"\n✓ All nodes have consistent logs ({log_sizes[0]} entries)")
    else:
        print(f"\n✗ Log sizes differ: {log_sizes}")


def demo_fault_tolerance(nodes):
    """Demonstrate fault tolerance with node failure."""
    print_separator()
    print("DEMO 3: Fault Tolerance - Simulating Node Failure")
    print_separator()

    # Find current leader
    current_leader = None
    for node_id, node in nodes.items():
        if node.is_leader():
            current_leader = node_id
            break

    if not current_leader:
        print("No leader found.")
        return

    print(f"Current leader: {current_leader}")
    print(f"\nSimulating failure of {current_leader}...")

    # Disconnect the leader from network
    failed_node = nodes[current_leader]
    original_network = failed_node.raft_node.network.copy()
    failed_node.raft_node.network = {}  # Isolate the node

    # Update other nodes' networks to exclude failed node
    for node_id, node in nodes.items():
        if node_id != current_leader:
            node.raft_node.network = {
                nid: n.raft_node for nid, n in nodes.items()
                if nid != current_leader and nid != node_id
            }

    print("✓ Node isolated from cluster")

    # Wait for election timeout and new election
    print("\nWaiting for new election...")
    time.sleep(0.2)

    # Force election timeout on one of the remaining nodes
    remaining_nodes = [n for nid, n in nodes.items() if nid != current_leader]
    if remaining_nodes:
        remaining_nodes[0].raft_node.last_heartbeat = \
            remaining_nodes[0].raft_node.last_heartbeat - remaining_nodes[0].raft_node.election_timeout * 2
        remaining_nodes[0].raft_node.check_election_timeout()

    print("\nAfter new election:")
    print_node_states(nodes)

    # Find new leader
    new_leader = None
    for node_id, node in nodes.items():
        if node_id != current_leader and node.is_leader():
            new_leader = node_id
            break

    if new_leader:
        print(f"\n✓ New leader elected: {new_leader}")
        print(f"  (Old leader {current_leader} is isolated)")
    else:
        print("\n✗ No new leader elected")


def demo_order_book_state():
    """Demonstrate querying order book state."""
    print_separator()
    print("DEMO 4: Order Book State")
    print_separator()

    # Create simple 3-node cluster
    node_ids = ['node1', 'node2', 'node3']
    nodes = {}

    for node_id in node_ids:
        other_nodes = [n for n in node_ids if n != node_id]
        nodes[node_id] = DistributedOrderBook('AAPL', node_id, other_nodes)

    for node in nodes.values():
        node.set_network(nodes)

    # Make node1 leader
    nodes['node1'].raft_node.become_leader()
    nodes['node2'].raft_node.become_follower(nodes['node1'].raft_node.current_term, 'node1')
    nodes['node3'].raft_node.become_follower(nodes['node1'].raft_node.current_term, 'node1')

    print("Submitting buy and sell orders...")

    # Submit buy orders
    for i in range(5):
        order = Order.create_limit_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            price=Decimal(f'{150 - i}.00'),
            agent_id=f'buyer{i}'
        )
        nodes['node1'].submit_order(order)

    # Submit sell orders
    for i in range(5):
        order = Order.create_limit_order(
            symbol='AAPL',
            side=OrderSide.SELL,
            quantity=Decimal('100'),
            price=Decimal(f'{151 + i}.00'),
            agent_id=f'seller{i}'
        )
        nodes['node1'].submit_order(order)

    # Replicate and commit
    for _ in range(3):
        nodes['node1'].raft_node.replicate_log()

    # Force apply all entries
    for node in nodes.values():
        for entry in node.raft_node.log:
            if not entry.committed:
                node._apply_log_entry(entry)
                entry.committed = True

    print("\nOrder Book Snapshot (from leader):")
    bids, asks = nodes['node1'].get_order_book_snapshot(depth=10)

    print("\nBids (Buy Orders):")
    print("  Price      | Quantity")
    print("  " + "-" * 25)
    for price, qty in bids[:5]:
        print(f"  ${price:7.2f} | {qty:8.2f}")

    print("\nAsks (Sell Orders):")
    print("  Price      | Quantity")
    print("  " + "-" * 25)
    for price, qty in asks[:5]:
        print(f"  ${price:7.2f} | {qty:8.2f}")

    return nodes


def demo_visualizations(nodes):
    """Generate visualizations of consensus behavior."""
    print_separator()
    print("DEMO 5: Generating Visualizations")
    print_separator()

    if not VISUALIZATION_AVAILABLE:
        print("Skipping visualizations (matplotlib not installed)")
        print("To enable visualizations, install matplotlib: pip install matplotlib")
        return

    print("Creating visualizer and recording states...")
    visualizer = ConsensusVisualizer()

    # Simulate some activity and record states
    for i in range(20):
        visualizer.record_state({nid: n.raft_node for nid, n in nodes.items()})

        # Simulate activity
        for node in nodes.values():
            if node.is_leader():
                node.raft_node.send_heartbeat()

        time.sleep(0.05)

    print("\nGenerating visualization plots...")

    try:
        import os
        output_dir = 'consensus_visualizations'
        os.makedirs(output_dir, exist_ok=True)

        visualizer.plot_state_timeline(f"{output_dir}/state_timeline.png")
        visualizer.plot_term_progression(f"{output_dir}/term_progression.png")
        visualizer.plot_log_replication(f"{output_dir}/log_replication.png")
        visualizer.plot_statistics({nid: n.raft_node for nid, n in nodes.items()},
                                  f"{output_dir}/statistics.png")
        visualizer.plot_distributed_orderbook_stats(nodes,
                                                    f"{output_dir}/orderbook_stats.png")

        print(f"\n✓ Visualizations saved to '{output_dir}/' directory")
        print(f"  - state_timeline.png")
        print(f"  - term_progression.png")
        print(f"  - log_replication.png")
        print(f"  - statistics.png")
        print(f"  - orderbook_stats.png")

    except Exception as e:
        print(f"\n✗ Error generating visualizations: {e}")
        print("  (matplotlib might not be available or display not configured)")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 80)
    print(" " * 20 + "RAFT CONSENSUS DEMONSTRATION")
    print(" " * 15 + "Distributed Order Book Implementation")
    print("=" * 80)

    # Demo 1: Leader Election
    nodes = demo_leader_election()

    # Demo 2: Order Submission and Replication
    demo_order_submission_and_replication(nodes)

    # Demo 3: Fault Tolerance
    demo_fault_tolerance(nodes)

    # Demo 4: Order Book State
    orderbook_nodes = demo_order_book_state()

    # Demo 5: Visualizations
    demo_visualizations(orderbook_nodes)

    print_separator()
    print("✓ All demonstrations completed successfully!")
    print_separator()

    print("\nKey Concepts Demonstrated:")
    print("  1. Leader Election - Nodes elect a leader using majority voting")
    print("  2. Log Replication - Leader replicates state changes to followers")
    print("  3. Fault Tolerance - Cluster continues operating despite node failures")
    print("  4. Consistency - All nodes maintain identical order book state")
    print("  5. Distributed Order Matching - Orders are processed consistently across nodes")

    print("\nReferences:")
    print("  - Ongaro & Ousterhout: 'In Search of an Understandable Consensus Algorithm'")
    print("  - https://raft.github.io/")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    main()
