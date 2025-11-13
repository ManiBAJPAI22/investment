"""
PERSISTENT DEMO - Runs Until Stopped

Starts everything and runs continuously until you press Ctrl+C:
- 5-node distributed consensus cluster
- 7 trading agents
- ENHANCED monitoring dashboard with real-time charts & visualizations
- Continuous trading activity

Press Ctrl+C to stop.
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
    NoiseTrader,
    ArbitrageAgent
)
from monitoring import MetricsCollector, EnhancedDashboardServer

print("\n" + "="*70)
print("PERSISTENT DISTRIBUTED CONSENSUS DEMO")
print("="*70)
print("Starting systems... (will run until you press Ctrl+C)")
print("="*70 + "\n")

# Create cluster
print("[1/3] Creating 5-node cluster...")
node_ids = ['node1', 'node2', 'node3', 'node4', 'node5']
exchanges = {}
symbol = 'AAPL'

for node_id in node_ids:
    other_nodes = [n for n in node_ids if n != node_id]
    config = RaftConfig(election_timeout_min=100, election_timeout_max=200, heartbeat_interval=50)
    exchanges[node_id] = DistributedExchange(symbol=symbol, node_id=node_id, cluster_nodes=other_nodes, config=config)

for node_id, exchange in exchanges.items():
    network = {nid: ex for nid, ex in exchanges.items() if nid != node_id}
    exchange.set_network(network)

first_node = list(exchanges.values())[0]
first_node.orderbook.raft_node.start_election()
time.sleep(0.5)

leader = None
for exchange in exchanges.values():
    if exchange.is_leader():
        leader = exchange.node_id
        break

print(f"✓ Cluster created, leader: {leader}")

# Create agents
print("\n[2/3] Creating 7 trading agents...")
agents = [
    SimpleMarketMaker(agent_id='MM_001', symbols=[symbol], spread_bps=Decimal('15'), order_size=Decimal('100')),
    SimpleMarketMaker(agent_id='MM_002', symbols=[symbol], spread_bps=Decimal('25'), order_size=Decimal('150')),
    MomentumTrader(agent_id='MOM_001', symbols=[symbol], lookback_window=5),
    MomentumTrader(agent_id='MOM_002', symbols=[symbol], lookback_window=10),
    ArbitrageAgent(agent_id='ARB_001', symbols=[symbol], min_spread_bps=Decimal('40')),
    NoiseTrader(agent_id='NOISE_001', symbols=[symbol], trade_probability=0.3),
    NoiseTrader(agent_id='NOISE_002', symbols=[symbol], trade_probability=0.2),
]
print(f"✓ Created {len(agents)} agents")

# Start monitoring
print("\n[3/3] Starting ENHANCED monitoring dashboard...")
collector = MetricsCollector(collection_interval=1.0, retention_period=600)
collector.set_cluster(exchanges)
collector.start()

dashboard = EnhancedDashboardServer(collector=collector, host='localhost', port=8080)
dashboard.start()

print("\n" + "="*70)
print("✅ ALL SYSTEMS RUNNING")
print("="*70)
print(f"\n🌐 Enhanced Dashboard: http://localhost:8080")
print(f"📊 Features: Real-time charts, visualizations, node details")
print(f"📈 Trading: Continuous (runs until Ctrl+C)")
print(f"🎯 Press Ctrl+C to stop\n")
print("="*70 + "\n")

# Trading loop
orders_submitted = 0
tick = 0

try:
    leader_exchange = None
    for exchange in exchanges.values():
        if exchange.is_leader():
            leader_exchange = exchange
            break

    while True:
        tick += 1

        # Each agent generates orders
        for agent in agents:
            if leader_exchange:
                orders = agent.on_tick(leader_exchange)
                for order in orders:
                    if leader_exchange.submit_order(order):
                        orders_submitted += 1

        # CRITICAL: Process Raft consensus - replicate logs and commit entries
        if leader_exchange:
            leader_exchange.orderbook.raft_node.replicate_log()

        for exchange in exchanges.values():
            exchange.orderbook.tick()

        # Check leader
        if not leader_exchange or not leader_exchange.is_leader():
            for exchange in exchanges.values():
                if exchange.is_leader():
                    leader_exchange = exchange
                    break

        # Status every 30 seconds
        if tick % 300 == 0:
            summary = collector.get_summary()
            if 'cluster' in summary:
                print(f"[{tick//10}s] Orders: {orders_submitted} | "
                      f"Leader: {summary['cluster']['leader']} | "
                      f"Health: {summary['cluster']['health_status']}")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\n⚠️  Stopping...")

finally:
    print("\nShutting down...")
    collector.stop()
    dashboard.stop()

    summary = collector.get_summary()
    if 'cluster' in summary:
        print(f"\n✅ Final Stats:")
        print(f"   Orders: {summary['performance']['total_orders']}")
        print(f"   Trades: {summary['performance']['total_trades']}")
        print(f"   Nodes: {summary['cluster']['healthy_nodes']}/{summary['cluster']['size']}")

    print("\n✓ Stopped cleanly\n")
