"""
Start Monitoring Dashboard Server

Starts a persistent monitoring dashboard that you can explore in the browser.
Runs a 5-node cluster with live metrics collection.

Press Ctrl+C to stop.
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from blockchain.consensus.distributed_exchange import DistributedExchange
from monitoring import MetricsCollector, DashboardServer

print("\n" + "="*70)
print("STARTING MONITORING DASHBOARD")
print("="*70 + "\n")

# Create 5-node cluster
print("Creating 5-node cluster...")
node_ids = ['node1', 'node2', 'node3', 'node4', 'node5']
exchanges = {}

for node_id in node_ids:
    other_nodes = [n for n in node_ids if n != node_id]
    exchanges[node_id] = DistributedExchange(
        symbol='DEMO',
        node_id=node_id,
        cluster_nodes=other_nodes
    )

# Connect network
for node_id, exchange in exchanges.items():
    network = {nid: ex for nid, ex in exchanges.items() if nid != node_id}
    exchange.set_network(network)

# Elect leader
exchanges['node1'].orderbook.raft_node.start_election()
time.sleep(0.3)

leader = None
for node_id, exchange in exchanges.items():
    if exchange.is_leader():
        leader = node_id
        break

print(f"✓ Cluster created, leader: {leader}\n")

# Create metrics collector
print("Starting metrics collector...")
collector = MetricsCollector(collection_interval=1.0, retention_period=300)
collector.set_cluster(exchanges)
collector.start()
print("✓ Metrics collector started\n")

# Create dashboard server
print("Starting dashboard server on port 8080...")
dashboard = DashboardServer(
    collector=collector,
    host='localhost',
    port=8080
)
dashboard.start()

print("\n" + "="*70)
print("✅ DASHBOARD IS RUNNING")
print("="*70)
print(f"\nOpen your browser and visit:")
print(f"  http://localhost:8080")
print(f"\nThe dashboard shows:")
print(f"  • Cluster health status")
print(f"  • Leader information")
print(f"  • Performance metrics")
print(f"  • Node status for all 5 nodes")
print(f"\nPress Ctrl+C to stop the server")
print("="*70 + "\n")

# Keep running
try:
    while True:
        time.sleep(1)

        # Print status every 10 seconds
        if int(time.time()) % 10 == 0:
            summary = collector.get_summary()
            if 'cluster' in summary:
                print(f"[Status] Cluster: {summary['cluster']['healthy_nodes']}/{summary['cluster']['size']} healthy, "
                      f"Leader: {summary['cluster']['leader']}, "
                      f"Health: {summary['cluster']['health_status']}")

except KeyboardInterrupt:
    print("\n\nShutting down...")
    collector.stop()
    dashboard.stop()
    print("✓ Dashboard stopped")
