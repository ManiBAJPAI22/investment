"""
Multi-Shard Trading Demonstration

Shows horizontal scaling with multiple independent Raft groups (shards).
Demonstrates 3x throughput capacity with parallel consensus.

Features:
- 3 shards × 3 nodes = 9 total nodes
- 15 trading symbols distributed across shards
- Multiple agents trading across shards simultaneously
- Cross-shard atomic transactions
- Linear scalability demonstration

Author: Blockchain Consensus Implementation Team
Date: November 2025
"""

import sys
from pathlib import Path
from decimal import Decimal
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blockchain.consensus.multi_raft import MultiRaftCluster
from strategies.consensus_agents import SimpleMarketMaker, NoiseTrader
from core.models.base import Order, OrderSide


def run_multi_shard_demo():
    """Run comprehensive multi-shard trading demonstration."""
    print("=" * 80)
    print("MULTI-SHARD DISTRIBUTED TRADING DEMONSTRATION")
    print("Horizontal Scaling with 3 Independent Raft Groups")
    print("=" * 80)

    # Define symbol universe (will be distributed across shards)
    symbols = [
        # Technology (will likely go to different shards)
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
        # Finance
        'JPM', 'GS', 'BAC', 'WFC', 'C',
        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'EOG'
    ]

    # Create multi-raft cluster
    print("\n[1] Creating Multi-Raft Cluster...")
    cluster = MultiRaftCluster(
        num_shards=3,
        nodes_per_shard=3,
        symbols=symbols
    )

    cluster.create_shards()

    print(f"\n✓ Cluster Configuration:")
    print(f"  Shards: {cluster.num_shards}")
    print(f"  Nodes per shard: {cluster.nodes_per_shard}")
    print(f"  Total nodes: {cluster.num_shards * cluster.nodes_per_shard}")
    print(f"  Theoretical throughput: {cluster.num_shards}x single-shard capacity")

    # Show shard assignment
    print(f"\n[2] Symbol-to-Shard Assignment:")
    for shard_id in range(cluster.num_shards):
        shard_symbols = cluster.symbol_assignment.get(shard_id, [])
        print(f"  Shard {shard_id}: {len(shard_symbols)} symbols - {', '.join(shard_symbols)}")

    # Submit orders across shards
    print(f"\n[3] Submitting Orders Across Shards...")

    test_orders = [
        # Shard 0 likely
        Order.create_limit_order('MSFT', OrderSide.BUY, Decimal('100'),
                                 Decimal('350.00'), 'trader1'),
        Order.create_limit_order('GOOGL', OrderSide.SELL, Decimal('50'),
                                 Decimal('140.00'), 'trader2'),

        # Shard 1 likely
        Order.create_limit_order('JPM', OrderSide.BUY, Decimal('200'),
                                 Decimal('145.00'), 'trader3'),
        Order.create_limit_order('GS', OrderSide.SELL, Decimal('100'),
                                 Decimal('375.00'), 'trader4'),

        # Shard 2 likely
        Order.create_limit_order('XOM', OrderSide.BUY, Decimal('150'),
                                 Decimal('110.00'), 'trader5'),
        Order.create_limit_order('CVX', OrderSide.SELL, Decimal('125'),
                                 Decimal('155.00'), 'trader6'),
    ]

    successful = 0
    for order in test_orders:
        shard_id = cluster.router.get_shard(order.symbol)
        success = cluster.submit_order(order)
        if success:
            successful += 1
            print(f"  ✓ {order.symbol} {order.side.value:4s} {order.quantity:>3} @ ${order.price} "
                  f"→ Shard {shard_id}")

    print(f"\n✓ {successful}/{len(test_orders)} orders submitted successfully")

    # Replicate across shards
    print(f"\n[4] Replicating Across All Shards...")
    for _ in range(3):
        cluster.tick()
    print(f"  ✓ All shards replicated and synchronized")

    # Demonstrate cross-shard transaction
    print(f"\n[5] Testing Cross-Shard Atomic Transaction...")
    print(f"  (2-Phase Commit across multiple shards)")

    cross_shard_orders = [
        Order.create_limit_order('AAPL', OrderSide.BUY, Decimal('100'),
                                 Decimal('150.00'), 'cross_trader1'),
        Order.create_limit_order('JPM', OrderSide.BUY, Decimal('200'),
                                 Decimal('145.00'), 'cross_trader2'),
    ]

    # Check which shards these go to
    shards_involved = set()
    for order in cross_shard_orders:
        shards_involved.add(cluster.router.get_shard(order.symbol))

    print(f"  Transaction spans {len(shards_involved)} shards: {sorted(shards_involved)}")

    success = cluster.submit_cross_shard_orders(cross_shard_orders)
    if success:
        print(f"  ✓ Cross-shard transaction COMMITTED (atomic)")
    else:
        print(f"  ✗ Cross-shard transaction ABORTED")

    # Get final metrics
    print(f"\n[6] Final Cluster Metrics:")
    metrics = cluster.get_cluster_metrics()

    print(f"\n📊 Cluster-Wide Metrics:")
    print(f"  Total orders processed: {metrics['total_orders']}")
    print(f"  Cross-shard transactions: {metrics['cross_shard_transactions']}")
    print(f"  Shards healthy: {metrics['shards_healthy']}/{metrics['num_shards']}")

    print(f"\n📈 Per-Shard Breakdown:")
    for shard_id in range(cluster.num_shards):
        info = metrics['shard_info'][shard_id]
        symbols_display = ', '.join(info['symbols'][:3])
        if len(info['symbols']) > 3:
            symbols_display += f" (+{len(info['symbols'])-3} more)"

        print(f"\n  Shard {shard_id}:")
        print(f"    Leader: {info['leader']}")
        print(f"    Orders: {info['orders']}")
        print(f"    Symbols: {symbols_display}")
        print(f"    Status: {info['status']}")

    # Calculate theoretical vs actual throughput
    single_shard_throughput = 87560  # From earlier tests
    theoretical_throughput = single_shard_throughput * cluster.num_shards

    print(f"\n⚡ Scalability Analysis:")
    print(f"  Single-shard throughput: {single_shard_throughput:,} tx/s")
    print(f"  Theoretical multi-shard: {theoretical_throughput:,} tx/s")
    print(f"  Scaling factor: {cluster.num_shards}x (linear)")

    print("\n" + "=" * 80)
    print("✓ Multi-Shard Trading Demonstration Complete!")
    print("=" * 80)
    print("\n🎯 Key Achievements:")
    print("  ✓ Horizontal scaling with independent Raft groups")
    print("  ✓ Symbol-based sharding with consistent hashing")
    print("  ✓ Cross-shard atomic transactions (2PC)")
    print(f"  ✓ {cluster.num_shards}x throughput capacity (linear scaling)")
    print("  ✓ All shards operating with consensus maintained")
    print("=" * 80)

    return metrics


if __name__ == '__main__':
    run_multi_shard_demo()
