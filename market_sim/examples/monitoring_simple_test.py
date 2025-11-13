"""
Simple test for monitoring dashboard

Tests basic functionality without browser or long simulation.
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from blockchain.consensus.distributed_exchange import DistributedExchange
from monitoring import MetricsCollector, DashboardServer


def main():
    print("\n" + "="*70)
    print("MONITORING DASHBOARD - SIMPLE TEST")
    print("="*70 + "\n")

    # Create simple 3-node cluster
    print("Creating 3-node cluster...")
    node_ids = ['node1', 'node2', 'node3']
    exchanges = {}

    for node_id in node_ids:
        other_nodes = [n for n in node_ids if n != node_id]
        exchanges[node_id] = DistributedExchange(
            symbol='TEST',
            node_id=node_id,
            cluster_nodes=other_nodes
        )

    # Connect network
    for node_id, exchange in exchanges.items():
        network = {nid: ex for nid, ex in exchanges.items() if nid != node_id}
        exchange.set_network(network)

    # Elect leader
    exchanges['node1'].orderbook.raft_node.start_election()
    time.sleep(0.5)

    # Find leader
    leader = None
    for node_id, exchange in exchanges.items():
        if exchange.is_leader():
            leader = node_id
            break

    print(f"✓ Cluster created, leader: {leader}\n")

    # Create metrics collector
    print("Starting metrics collector...")
    collector = MetricsCollector(collection_interval=1.0)
    collector.set_cluster(exchanges)
    collector.start()
    print("✓ Metrics collector started\n")

    # Create dashboard
    print("Starting dashboard server on port 8080...")
    dashboard = DashboardServer(
        collector=collector,
        host='localhost',
        port=8080
    )
    dashboard.start()

    # Wait for metrics
    print("Collecting metrics for 10 seconds...\n")
    for i in range(10):
        time.sleep(1)
        summary = collector.get_summary()

        if 'cluster' in summary:
            print(f"[{i+1}s] Cluster: {summary['cluster']['healthy_nodes']}/{summary['cluster']['size']} healthy, "
                  f"Leader: {summary['cluster']['leader']}, "
                  f"Status: {summary['cluster']['health_status']}")

    # Test API endpoints
    print("\n" + "="*70)
    print("Testing API endpoints...")
    print("="*70 + "\n")

    import urllib.request
    import json

    def test_endpoint(path, name):
        try:
            with urllib.request.urlopen(f'http://localhost:8080{path}') as response:
                data = json.loads(response.read())
                print(f"✓ {name}: {len(json.dumps(data))} bytes")
                return True
        except Exception as e:
            print(f"✗ {name}: {e}")
            return False

    test_endpoint('/api/health', 'Health check')
    test_endpoint('/api/summary', 'Summary endpoint')
    test_endpoint('/api/metrics', 'Metrics endpoint')
    test_endpoint('/api/alerts', 'Alerts endpoint')

    print("\n" + "="*70)
    print("MONITORING TEST COMPLETE")
    print("="*70)
    print(f"\nDashboard running at: http://localhost:8080")
    print("You can view it in your browser.")
    print("\nPress Ctrl+C to stop...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")

    collector.stop()
    dashboard.stop()
    print("✓ Stopped")


if __name__ == '__main__':
    main()
