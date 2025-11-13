"""
Real-Time Monitoring Dashboard Demonstration

Demonstrates real-time monitoring of distributed consensus cluster with:
- Live metrics collection
- Web-based dashboard
- Trading simulation
- Node failures and recovery
- Performance tracking

Author: Blockchain Consensus Implementation Team
Date: November 2025
"""

import sys
from pathlib import Path
import time
import random
from decimal import Decimal
import webbrowser
import threading

# Add parent directory to path
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


def create_monitored_cluster(num_nodes: int = 5, symbol: str = 'AAPL'):
    """Create a distributed exchange cluster with monitoring."""
    print(f"\n{'='*70}")
    print(f"Creating {num_nodes}-node cluster for {symbol}...")
    print(f"{'='*70}")

    node_ids = [f'node{i}' for i in range(1, num_nodes + 1)]
    exchanges = {}

    # Create exchange nodes
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

    # Set up network connections
    for node_id, exchange in exchanges.items():
        network = {nid: ex for nid, ex in exchanges.items() if nid != node_id}
        exchange.set_network(network)

    # Start election
    first_node = list(exchanges.values())[0]
    first_node.orderbook.raft_node.start_election()

    # Wait for leader
    time.sleep(0.5)

    # Find leader
    leader = None
    for exchange in exchanges.values():
        if exchange.is_leader():
            leader = exchange.node_id
            print(f"✓ Leader elected: {leader}")
            break

    print(f"✓ Cluster created: {num_nodes} nodes")
    print(f"{'='*70}\n")

    return exchanges


def create_trading_agents(symbol: str):
    """Create trading agents."""
    print("Creating trading agents...")

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
            lookback_period=5
        ),
        ArbitrageAgent(
            agent_id='ARB_001',
            symbols=[symbol],
            min_spread_bps=Decimal('40')
        ),
        NoiseTrader(
            agent_id='NOISE_001',
            symbols=[symbol],
            order_probability=0.3
        ),
    ]

    print(f"✓ Created {len(agents)} trading agents")
    return agents


def run_trading_simulation(
    exchanges: dict,
    agents: list,
    num_ticks: int = 200,
    inject_failures: bool = True
):
    """Run trading simulation with optional failures."""
    print(f"\n{'='*70}")
    print(f"Starting trading simulation: {num_ticks} ticks")
    print(f"Failure injection: {'Enabled' if inject_failures else 'Disabled'}")
    print(f"{'='*70}\n")

    # Get leader
    leader_exchange = None
    for exchange in exchanges.values():
        if exchange.is_leader():
            leader_exchange = exchange
            break

    failed_nodes = set()
    orders_submitted = 0
    orders_failed = 0

    for tick in range(num_ticks):
        # Inject failures at specific ticks
        if inject_failures:
            if tick == 30 and 'node1' not in failed_nodes:
                print(f"[Tick {tick}] 💥 Simulating node1 failure...")
                failed_nodes.add('node1')
                exchanges['node1'].orderbook.raft_node.network = {}

            elif tick == 60 and 'node1' in failed_nodes:
                print(f"[Tick {tick}] ✓ Recovering node1...")
                failed_nodes.remove('node1')
                network_map = {ex.node_id: ex.orderbook for ex in exchanges.values()}
                other_nodes = {nid: ob for nid, ob in network_map.items() if nid != 'node1'}
                exchanges['node1'].orderbook.raft_node.network = other_nodes

            elif tick == 100 and 'node2' not in failed_nodes:
                print(f"[Tick {tick}] 💥 Simulating node2 failure...")
                failed_nodes.add('node2')
                exchanges['node2'].orderbook.raft_node.network = {}

            elif tick == 130 and 'node2' in failed_nodes:
                print(f"[Tick {tick}] ✓ Recovering node2...")
                failed_nodes.remove('node2')
                network_map = {ex.node_id: ex.orderbook for ex in exchanges.values()}
                other_nodes = {nid: ob for nid, ob in network_map.items() if nid != 'node2'}
                exchanges['node2'].orderbook.raft_node.network = other_nodes

        # Each agent generates orders
        for agent in agents:
            # Get current market state from leader
            if leader_exchange and leader_exchange.node_id not in failed_nodes:
                market = leader_exchange.get_market_summary()
                orders = agent.generate_orders(market)

                for order in orders:
                    # Try to submit to leader
                    success = leader_exchange.submit_order(order)
                    if success:
                        orders_submitted += 1
                    else:
                        orders_failed += 1

        # Check if leader failed, elect new one
        if leader_exchange and leader_exchange.node_id in failed_nodes:
            time.sleep(0.2)  # Wait for election
            for exchange in exchanges.values():
                if exchange.node_id not in failed_nodes and exchange.is_leader():
                    leader_exchange = exchange
                    print(f"[Tick {tick}] ✓ New leader elected: {leader_exchange.node_id}")
                    break

        # Print progress every 50 ticks
        if tick % 50 == 0 and tick > 0:
            print(f"[Tick {tick}] Orders: {orders_submitted} submitted, {orders_failed} failed")

        time.sleep(0.1)  # 100ms per tick

    print(f"\n{'='*70}")
    print(f"Simulation complete!")
    print(f"Total orders submitted: {orders_submitted}")
    print(f"Total orders failed: {orders_failed}")
    print(f"Success rate: {orders_submitted / (orders_submitted + orders_failed) * 100:.1f}%")
    print(f"{'='*70}\n")


def main():
    """Run monitoring demonstration."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║      REAL-TIME MONITORING DASHBOARD DEMONSTRATION                 ║
║      Distributed Consensus Performance Monitoring                 ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    # Configuration
    NUM_NODES = 5
    SYMBOL = 'AAPL'
    NUM_TICKS = 200
    DASHBOARD_PORT = 8080

    # Create cluster
    exchanges = create_monitored_cluster(NUM_NODES, SYMBOL)

    # Create metrics collector
    print("Initializing metrics collector...")
    collector = MetricsCollector(
        collection_interval=1.0,
        retention_period=300
    )
    collector.set_cluster(exchanges)
    collector.start()
    print("✓ Metrics collector started\n")

    # Create dashboard server
    print("Starting dashboard server...")
    dashboard = DashboardServer(
        collector=collector,
        host='localhost',
        port=DASHBOARD_PORT
    )
    dashboard.start()

    # Wait for server to start
    time.sleep(1.0)

    # Open browser
    dashboard_url = dashboard.get_url()
    print(f"Opening dashboard in browser: {dashboard_url}")
    try:
        webbrowser.open(dashboard_url)
    except:
        print("Could not open browser automatically. Please visit:")
        print(f"  {dashboard_url}")

    print(f"\nDashboard is now running. You can view real-time metrics at:")
    print(f"  {dashboard_url}")
    print(f"\nPress Ctrl+C to stop the simulation.\n")

    # Create trading agents
    agents = create_trading_agents(SYMBOL)

    # Run simulation in background thread
    simulation_thread = threading.Thread(
        target=run_trading_simulation,
        args=(exchanges, agents, NUM_TICKS, True),
        daemon=True
    )
    simulation_thread.start()

    # Show live metrics in terminal
    try:
        tick = 0
        while simulation_thread.is_alive():
            time.sleep(5.0)  # Update every 5 seconds

            summary = collector.get_summary()
            if 'cluster' in summary:
                tick += 1
                print(f"\n[Terminal Update {tick}]")
                print(f"Cluster: {summary['cluster']['healthy_nodes']}/{summary['cluster']['size']} nodes healthy")
                print(f"Leader: {summary['cluster']['leader']}")
                print(f"Health: {summary['cluster']['health_status']}")
                print(f"Orders: {summary['performance']['total_orders']}")
                print(f"Trades: {summary['performance']['total_trades']}")
                print(f"Throughput: {summary['performance']['throughput_ops']:.2f} ops/s")

                if summary['alerts']['count'] > 0:
                    print(f"⚠️  Active alerts: {summary['alerts']['count']}")

    except KeyboardInterrupt:
        print("\n\nShutting down...")

    # Wait for simulation to complete
    simulation_thread.join(timeout=5.0)

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL METRICS SUMMARY")
    print(f"{'='*70}")

    final_summary = collector.get_summary()
    if 'cluster' in final_summary:
        print(f"\nCluster:")
        print(f"  Size: {final_summary['cluster']['size']}")
        print(f"  Healthy nodes: {final_summary['cluster']['healthy_nodes']}")
        print(f"  Final leader: {final_summary['cluster']['leader']}")
        print(f"  Health status: {final_summary['cluster']['health_status']}")

        print(f"\nPerformance:")
        print(f"  Total orders: {final_summary['performance']['total_orders']}")
        print(f"  Total trades: {final_summary['performance']['total_trades']}")
        print(f"  Average throughput: {final_summary['performance']['throughput_ops']:.2f} ops/s")

        print(f"\nConsensus:")
        print(f"  Current term: {final_summary['consensus']['current_term']}")
        print(f"  Aligned: {'Yes' if final_summary['consensus']['aligned'] else 'No'}")

        print(f"\nAlerts:")
        print(f"  Total alerts: {final_summary['alerts']['count']}")

    print(f"\n{'='*70}")
    print(f"Dashboard still running at: {dashboard_url}")
    print(f"Press Enter to shut down...")
    print(f"{'='*70}")

    input()

    # Cleanup
    collector.stop()
    dashboard.stop()
    print("\n✓ Monitoring dashboard stopped")


if __name__ == '__main__':
    main()
