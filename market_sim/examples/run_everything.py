"""
COMPREHENSIVE DEMO - ALL FEATURES RUNNING TOGETHER

This demo starts everything:
1. 5-node distributed consensus cluster
2. 7 active trading agents (market makers, momentum traders, arbitrage, noise)
3. Real-time monitoring dashboard (http://localhost:8080)
4. Continuous trading activity
5. Metrics collection and visualization
6. Optional: Periodic chaos injection

Author: Blockchain Consensus Implementation Team
Date: November 2025
"""

import sys
from pathlib import Path
import time
import random
from decimal import Decimal
import threading

sys.path.insert(0, str(Path(__file__).parent.parent))

from blockchain.consensus.distributed_exchange import DistributedExchange
from blockchain.consensus.raft_node import RaftConfig
from strategies.consensus_agents import (
    SimpleMarketMaker,
    MomentumTrader,
    NoiseTrader,
    ArbitrageAgent
)
from core.models.base import Order, OrderSide
from monitoring import MetricsCollector, DashboardServer


def print_banner():
    """Print welcome banner."""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║           DISTRIBUTED CONSENSUS - COMPREHENSIVE LIVE DEMO                 ║
║                                                                            ║
║  Running:                                                                  ║
║  • 5-node Raft consensus cluster                                          ║
║  • 7 active trading agents                                                ║
║  • Real-time monitoring dashboard                                         ║
║  • Continuous order/trade execution                                       ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)


def create_cluster(num_nodes=5, symbol='AAPL'):
    """Create distributed exchange cluster."""
    print(f"\n{'='*70}")
    print(f"[1/4] Creating {num_nodes}-node cluster for {symbol}...")
    print(f"{'='*70}")

    node_ids = [f'node{i}' for i in range(1, num_nodes + 1)]
    exchanges = {}

    for node_id in node_ids:
        other_nodes = [n for n in node_ids if n != node_id]
        config = RaftConfig(
            election_timeout_min=100,
            election_timeout_max=200,
            heartbeat_interval=50
        )

        exchanges[node_id] = DistributedExchange(
            symbol=symbol,
            node_id=node_id,
            cluster_nodes=other_nodes,
            config=config
        )

    # Set up network
    for node_id, exchange in exchanges.items():
        network = {nid: ex for nid, ex in exchanges.items() if nid != node_id}
        exchange.set_network(network)

    # Start election
    first_node = list(exchanges.values())[0]
    first_node.orderbook.raft_node.start_election()
    time.sleep(0.5)

    # Find leader
    leader = None
    for exchange in exchanges.values():
        if exchange.is_leader():
            leader = exchange.node_id
            break

    print(f"✓ {num_nodes}-node cluster created")
    print(f"✓ Leader elected: {leader}")
    print(f"✓ Consensus active")

    return exchanges


def create_agents(symbol='AAPL'):
    """Create trading agents."""
    print(f"\n{'='*70}")
    print(f"[2/4] Creating trading agents...")
    print(f"{'='*70}")

    agents = [
        SimpleMarketMaker(
            agent_id='MM_001',
            symbols=[symbol],
            spread_bps=Decimal('15'),
            order_size=Decimal('100')
        ),
        SimpleMarketMaker(
            agent_id='MM_002',
            symbols=[symbol],
            spread_bps=Decimal('25'),
            order_size=Decimal('150')
        ),
        MomentumTrader(
            agent_id='MOM_001',
            symbols=[symbol],
            lookback_window=5
        ),
        MomentumTrader(
            agent_id='MOM_002',
            symbols=[symbol],
            lookback_window=10
        ),
        ArbitrageAgent(
            agent_id='ARB_001',
            symbols=[symbol],
            min_spread_bps=Decimal('40')
        ),
        NoiseTrader(
            agent_id='NOISE_001',
            symbols=[symbol],
            trade_probability=0.3
        ),
        NoiseTrader(
            agent_id='NOISE_002',
            symbols=[symbol],
            trade_probability=0.2
        ),
    ]

    print(f"✓ Created {len(agents)} trading agents:")
    print(f"  • 2 Market Makers (15-25 bps spreads)")
    print(f"  • 2 Momentum Traders (5-10 period lookback)")
    print(f"  • 1 Arbitrage Agent (40+ bps minimum)")
    print(f"  • 2 Noise Traders (20-30% activity)")

    return agents


def start_monitoring(exchanges):
    """Start monitoring dashboard."""
    print(f"\n{'='*70}")
    print(f"[3/4] Starting monitoring dashboard...")
    print(f"{'='*70}")

    # Create metrics collector
    collector = MetricsCollector(
        collection_interval=1.0,
        retention_period=600  # 10 minutes
    )
    collector.set_cluster(exchanges)
    collector.start()

    # Create dashboard server
    dashboard = DashboardServer(
        collector=collector,
        host='localhost',
        port=8080
    )
    dashboard.start()

    print(f"✓ Metrics collector started (1s interval)")
    print(f"✓ Dashboard server started")
    print(f"✓ Web UI available at: http://localhost:8080")
    print(f"✓ REST API available (7 endpoints)")

    return collector, dashboard


def trading_loop(exchanges, agents, duration_seconds=300, enable_chaos=False):
    """Main trading loop."""
    print(f"\n{'='*70}")
    print(f"[4/4] Starting live trading simulation...")
    print(f"{'='*70}")
    print(f"Duration: {duration_seconds} seconds ({duration_seconds//60} minutes)")
    print(f"Chaos injection: {'Enabled' if enable_chaos else 'Disabled'}")
    print(f"{'='*70}\n")

    start_time = time.time()
    tick = 0
    orders_submitted = 0
    orders_failed = 0
    failed_nodes = set()

    # Get initial leader
    leader_exchange = None
    for exchange in exchanges.values():
        if exchange.is_leader():
            leader_exchange = exchange
            break

    print(f"Starting trading with leader: {leader_exchange.node_id}\n")

    while time.time() - start_time < duration_seconds:
        tick += 1
        current_time = time.time() - start_time

        # Optional: Inject chaos
        if enable_chaos and tick % 100 == 30:
            # Fail a node
            available_nodes = [nid for nid in exchanges.keys() if nid not in failed_nodes]
            if available_nodes and len(available_nodes) > 3:  # Keep quorum
                target = random.choice(available_nodes)
                print(f"[{int(current_time)}s] 💥 Injecting chaos: {target} crashed")
                failed_nodes.add(target)
                exchanges[target].orderbook.raft_node.network = {}

        elif enable_chaos and tick % 100 == 60 and failed_nodes:
            # Recover a node
            target = random.choice(list(failed_nodes))
            print(f"[{int(current_time)}s] ✓ Recovery: {target} restored")
            failed_nodes.remove(target)
            network_map = {ex.node_id: ex.orderbook for ex in exchanges.values()}
            other_nodes = {nid: ob for nid, ob in network_map.items() if nid != target}
            exchanges[target].orderbook.raft_node.network = other_nodes

        # Each agent generates orders
        for agent in agents:
            if leader_exchange and leader_exchange.node_id not in failed_nodes:
                orders = agent.on_tick(leader_exchange)

                for order in orders:
                    success = leader_exchange.submit_order(order)
                    if success:
                        orders_submitted += 1
                    else:
                        orders_failed += 1

        # CRITICAL: Process Raft consensus - replicate logs and commit entries
        if leader_exchange and leader_exchange.node_id not in failed_nodes:
            leader_exchange.orderbook.raft_node.replicate_log()

        for exchange in exchanges.values():
            if exchange.node_id not in failed_nodes:
                exchange.orderbook.tick()

        # Check leader status
        if not leader_exchange or leader_exchange.node_id in failed_nodes:
            # Find new leader
            for exchange in exchanges.values():
                if exchange.node_id not in failed_nodes and exchange.is_leader():
                    leader_exchange = exchange
                    break

        # Print status every 30 seconds
        if tick % 300 == 0:
            trades = leader_exchange.metrics.get('trades_executed', 0) if leader_exchange else 0
            elapsed = int(current_time)
            print(f"[{elapsed}s] Orders: {orders_submitted} submitted | "
                  f"Trades: {trades} | "
                  f"Leader: {leader_exchange.node_id if leader_exchange else 'None'} | "
                  f"Failed nodes: {len(failed_nodes)}")

        time.sleep(0.1)  # 100ms tick

    # Final summary
    print(f"\n{'='*70}")
    print("TRADING SIMULATION COMPLETE")
    print(f"{'='*70}")
    print(f"Total runtime: {duration_seconds}s")
    print(f"Orders submitted: {orders_submitted}")
    print(f"Orders failed: {orders_failed}")
    if orders_submitted + orders_failed > 0:
        success_rate = orders_submitted / (orders_submitted + orders_failed) * 100
        print(f"Success rate: {success_rate:.1f}%")

    if leader_exchange:
        trades = leader_exchange.metrics.get('trades_executed', 0)
        print(f"Trades executed: {trades}")
        print(f"Final leader: {leader_exchange.node_id}")

    print(f"{'='*70}\n")


def main():
    """Run comprehensive demo."""
    print_banner()

    # Configuration
    NUM_NODES = 5
    SYMBOL = 'AAPL'
    DURATION = 300  # 5 minutes
    ENABLE_CHAOS = False  # Set to True for chaos injection

    print("Configuration:")
    print(f"  • Cluster size: {NUM_NODES} nodes")
    print(f"  • Trading symbol: {SYMBOL}")
    print(f"  • Duration: {DURATION}s ({DURATION//60} minutes)")
    print(f"  • Chaos injection: {'Enabled' if ENABLE_CHAOS else 'Disabled'}")

    try:
        # Create cluster
        exchanges = create_cluster(NUM_NODES, SYMBOL)

        # Create agents
        agents = create_agents(SYMBOL)

        # Start monitoring
        collector, dashboard = start_monitoring(exchanges)

        print(f"\n{'='*70}")
        print("🚀 ALL SYSTEMS OPERATIONAL")
        print(f"{'='*70}")
        print(f"\n📊 Open your browser to view real-time metrics:")
        print(f"   http://localhost:8080")
        print(f"\n📈 The dashboard shows:")
        print(f"   • Cluster health and leader status")
        print(f"   • Real-time order/trade counts")
        print(f"   • Throughput (orders per second)")
        print(f"   • Individual node status")
        print(f"   • Consensus alignment")
        print(f"\n⏱️  Trading will run for {DURATION//60} minutes...")
        print(f"   Press Ctrl+C to stop early")
        print(f"{'='*70}\n")

        # Small delay to let user open browser
        time.sleep(3)

        # Run trading loop
        trading_loop(exchanges, agents, DURATION, ENABLE_CHAOS)

        # Keep dashboard running for a bit
        print("Trading complete. Dashboard still running for 30 seconds...")
        print("View final metrics at: http://localhost:8080\n")
        time.sleep(30)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    finally:
        print("\nShutting down...")
        if 'collector' in locals():
            collector.stop()
        if 'dashboard' in locals():
            dashboard.stop()
        print("✓ All systems stopped")

    # Final summary
    print(f"\n{'='*70}")
    print("SESSION SUMMARY")
    print(f"{'='*70}")

    if 'collector' in locals():
        summary = collector.get_summary()
        if 'cluster' in summary:
            print(f"\nCluster:")
            print(f"  • Size: {summary['cluster']['size']} nodes")
            print(f"  • Healthy: {summary['cluster']['healthy_nodes']} nodes")
            print(f"  • Final leader: {summary['cluster']['leader']}")
            print(f"  • Health status: {summary['cluster']['health_status']}")

            print(f"\nPerformance:")
            print(f"  • Total orders: {summary['performance']['total_orders']}")
            print(f"  • Total trades: {summary['performance']['total_trades']}")
            print(f"  • Avg throughput: {summary['performance']['throughput_ops']:.2f} ops/s")

            print(f"\nConsensus:")
            print(f"  • Current term: {summary['consensus']['current_term']}")
            print(f"  • Aligned: {'Yes' if summary['consensus']['aligned'] else 'No'}")

    print(f"\n{'='*70}")
    print("Thank you for using the Distributed Consensus System!")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
