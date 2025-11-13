"""
Enhanced Dashboard Demo

Demonstrates the new visualization-rich dashboard with:
- Real-time line charts for throughput
- Orders and trades time-series graphs
- Visual progress bars
- Detailed node information table
- System health indicators

Run this and open http://localhost:8080 to see the enhanced dashboard!
"""

import sys
from pathlib import Path
import time
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from blockchain.consensus.distributed_exchange import DistributedExchange
from blockchain.consensus.raft_node import RaftConfig
from strategies.consensus_agents import (
    SimpleMarketMaker,
    MomentumTrader,
    NoiseTrader
)
from monitoring import MetricsCollector
from monitoring.dashboard_enhanced import EnhancedDashboardServer

print("\n" + "="*70)
print("ENHANCED DASHBOARD DEMONSTRATION")
print("="*70 + "\n")

# Create 5-node cluster
print("[1/3] Creating 5-node cluster...")
node_ids = ['node1', 'node2', 'node3', 'node4', 'node5']
exchanges = {}
symbol = 'AAPL'

for node_id in node_ids:
    other_nodes = [n for n in node_ids if n != node_id]
    config = RaftConfig(election_timeout_min=100, election_timeout_max=200, heartbeat_interval=50)
    exchanges[node_id] = DistributedExchange(
        symbol=symbol,
        node_id=node_id,
        cluster_nodes=other_nodes,
        config=config
    )

for node_id, exchange in exchanges.items():
    network = {nid: ex for nid, ex in exchanges.items() if nid != node_id}
    exchange.set_network(network)

exchanges['node1'].orderbook.raft_node.start_election()
time.sleep(0.5)

leader_exchange = None
for exchange in exchanges.values():
    if exchange.is_leader():
        leader_exchange = exchange
        break

print(f"✓ Cluster created, leader: {leader_exchange.node_id}")

# Create agents
print("\n[2/3] Creating trading agents...")
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
    NoiseTrader(
        agent_id='NOISE_001',
        symbols=[symbol],
        trade_probability=0.3
    ),
]
print(f"✓ Created {len(agents)} agents")

# Start monitoring with ENHANCED dashboard
print("\n[3/3] Starting ENHANCED monitoring dashboard...")
collector = MetricsCollector(collection_interval=1.0, retention_period=600)
collector.set_cluster(exchanges)
collector.start()

# Use the enhanced dashboard instead of the basic one
dashboard = EnhancedDashboardServer(
    collector=collector,
    host='localhost',
    port=8080
)
dashboard.start()

print("\n" + "="*70)
print("✅ ENHANCED DASHBOARD IS LIVE!")
print("="*70)
print(f"\n🌐 Open your browser and visit:")
print(f"   http://localhost:8080")
print(f"\n📊 New Features:")
print(f"   • Real-time line charts for throughput")
print(f"   • Orders & trades time-series visualization")
print(f"   • Visual progress bars for system health")
print(f"   • Detailed node information table")
print(f"   • Animated consensus indicators")
print(f"   • Auto-refresh every 1 second")
print(f"\n⏱️  Trading will run for 2 minutes...")
print(f"   Watch the charts update in real-time!")
print("="*70 + "\n")

# Trading loop
orders_submitted = 0
start_time = time.time()
duration = 120  # 2 minutes

try:
    tick = 0
    while time.time() - start_time < duration:
        tick += 1

        # Generate orders
        for agent in agents:
            orders = agent.on_tick(leader_exchange)
            for order in orders:
                if leader_exchange.submit_order(order):
                    orders_submitted += 1

        # Process consensus
        leader_exchange.orderbook.raft_node.replicate_log()
        for exchange in exchanges.values():
            exchange.orderbook.tick()

        # Check leader
        if not leader_exchange or not leader_exchange.is_leader():
            for exchange in exchanges.values():
                if exchange.is_leader():
                    leader_exchange = exchange
                    break

        # Status every 20 seconds
        if tick % 200 == 0:
            elapsed = int(time.time() - start_time)
            summary = collector.get_summary()
            if 'performance' in summary:
                print(f"[{elapsed}s] Orders: {orders_submitted} submitted | "
                      f"Dashboard: {summary['performance']['total_orders']} committed | "
                      f"Throughput: {summary['performance']['throughput_ops']:.1f} ops/s")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\n⚠️  Interrupted by user")

# Final stats
print("\n" + "="*70)
print("DEMO COMPLETE")
print("="*70)

summary = collector.get_summary()
print(f"\n📈 Final Statistics:")
print(f"   Orders submitted:  {orders_submitted:,}")
print(f"   Orders committed:  {summary['performance']['total_orders']:,}")
print(f"   Trades executed:   {summary['performance']['total_trades']:,}")
print(f"   Avg throughput:    {summary['performance']['throughput_ops']:.2f} ops/s")
print(f"   Cluster health:    {summary['cluster']['health_status'].upper()}")
print(f"   Nodes healthy:     {summary['cluster']['healthy_nodes']}/{summary['cluster']['size']}")

print(f"\n💡 The dashboard is still running!")
print(f"   Keep your browser open to explore the visualizations.")
print(f"   Press Ctrl+C again to shut down...")
print("="*70 + "\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\n🛑 Shutting down...")
    collector.stop()
    dashboard.stop()
    print("✓ All systems stopped\n")
