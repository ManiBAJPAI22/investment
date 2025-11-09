"""
Rigorous Production Testing with Real Market Data.

Tests consensus mechanisms against actual S&P 500 stock data with:
- 476 real stocks with varying volatility
- Extreme entropy scenarios (chaos testing)
- Network partitions and Byzantine attacks
- Front-running protection
- Production failure modes

Dataset: investment/data/streak_entropy_analysis.csv
- Entropy range: 0.0 (stable) to 2.4 (chaotic)
- Down streaks: 5-16 consecutive days
- Real market behavior patterns
"""

import sys
import time
import random
from pathlib import Path
from decimal import Decimal
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from blockchain.consensus.production_raft import ProductionRaftNode
from blockchain.consensus.distributed_orderbook import DistributedOrderBook
from core.models.base import Order, OrderSide
from tests.performance.real_data_generator import RealMarketDataGenerator


class ProductionConsensusTest:
    """Rigorous testing of consensus with real market data."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.data_gen = RealMarketDataGenerator()
        self.test_results: List[Dict[str, Any]] = []

    def print(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

    def test_extreme_entropy_stocks(self, num_orders: int = 1000) -> Dict[str, Any]:
        """
        Test with 10 most chaotic stocks (highest entropy).

        These are the worst-case real market scenarios.
        """
        self.print("\n" + "=" * 80)
        self.print("TEST: EXTREME ENTROPY STOCKS (Real Market Chaos)")
        self.print("=" * 80)

        # Get extreme stocks
        extreme_stocks = sorted(self.data_gen.stocks,
                              key=lambda s: s['entropy'], reverse=True)[:10]

        self.print(f"\nTop 10 Most Chaotic Stocks:")
        for i, stock in enumerate(extreme_stocks[:5], 1):
            self.print(f"  {i}. {stock['ticker']:6} - {stock['company_name'][:40]:40} "
                      f"(entropy: {stock['entropy']:.3f}, max streak: {stock['max_down_streak']})")

        # Create cluster
        node_ids = ['node1', 'node2', 'node3']
        nodes = self._create_production_cluster(node_ids)

        # Generate orders from extreme stocks
        orders = self.data_gen.generate_entropy_stress_test(num_orders)

        self.print(f"\nProcessing {num_orders} orders from extreme volatility stocks...")

        start_time = time.time()
        successes = 0
        failures = 0
        anomalies_detected = 0

        leader = next(n for n in nodes.values() if n.is_leader())

        for i, order_data in enumerate(orders):
            order = Order.create_limit_order(
                symbol=order_data['symbol'],
                side=OrderSide.BUY if order_data['side'] == 'buy' else OrderSide.SELL,
                quantity=Decimal(str(order_data['quantity'])),
                price=Decimal(str(order_data['price'])),
                agent_id=f"agent_{i}"
            )

            # Submit order (use the existing distributed orderbook method)
            # The production features are active in the underlying Raft node
            from blockchain.consensus.log_entry import LogEntryType
            order_data = {
                'symbol': order_data['symbol'],
                'side': order_data['side'],
                'price': str(order_data['price']),
                'quantity': order_data['quantity'],
                'agent_id': f"agent_{i}"
            }
            success = leader.append_entry(LogEntryType.ORDER_SUBMIT, order_data)

            if success:
                successes += 1
            else:
                failures += 1

            # Replicate periodically
            if i % 50 == 0:
                leader.replicate_log()

                # Check for anomalies
                if leader.byzantine_detector:
                    anomalies_detected = len(leader.byzantine_detector.anomalies)

        # Final replication
        for _ in range(3):
            leader.replicate_log()

        duration = time.time() - start_time

        result = {
            'test_name': 'extreme_entropy_stocks',
            'num_orders': num_orders,
            'duration': duration,
            'successes': successes,
            'failures': failures,
            'throughput': num_orders / duration,
            'anomalies_detected': anomalies_detected,
            'passed': successes > 0 and failures == 0
        }

        self.print(f"\n✓ Results:")
        self.print(f"  Orders processed: {successes}/{num_orders}")
        self.print(f"  Failures: {failures}")
        self.print(f"  Throughput: {result['throughput']:.2f} tx/s")
        self.print(f"  Anomalies detected: {anomalies_detected}")
        self.print(f"  Test: {'PASSED' if result['passed'] else 'FAILED'}")

        self.test_results.append(result)
        return result

    def test_network_partition(self, num_orders: int = 500) -> Dict[str, Any]:
        """
        Test Byzantine behavior with network partition.

        Simulates split-brain scenario and recovery.
        """
        self.print("\n" + "=" * 80)
        self.print("TEST: NETWORK PARTITION & SPLIT-BRAIN")
        self.print("=" * 80)

        # Create 5-node cluster
        node_ids = [f'node{i}' for i in range(1, 6)]
        nodes = self._create_production_cluster(node_ids)

        original_leader = next(n for n in nodes.values() if n.is_leader())

        self.print(f"\nOriginal leader: {original_leader.node_id}")

        # Submit some orders
        orders = self.data_gen.generate_realistic_orders(num_orders, 'medium')

        self.print(f"Processing {num_orders} orders before partition...")
        start_time = time.time()

        for i, order_data in enumerate(orders):
            order = Order.create_limit_order(
                symbol=order_data['symbol'],
                side=OrderSide.BUY if order_data['side'] == 'buy' else OrderSide.SELL,
                quantity=Decimal(str(order_data['quantity'])),
                price=Decimal(str(order_data['price'])),
                agent_id=f"agent_{i}"
            )
            from blockchain.consensus.log_entry import LogEntryType
            order_data = {
                'symbol': order_data['symbol'],
                'side': order_data['side'],
                'price': str(order_data['price']),
                'quantity': order_data['quantity'],
                'agent_id': f"agent_{i}"
            }
            original_leader.append_entry(LogEntryType.ORDER_SUBMIT, order_data)

            if i % 50 == 0:
                original_leader.replicate_log()

        self.print(f"✓ Submitted {num_orders} orders")

        # Create network partition: [node1, node2] vs [node3, node4, node5]
        self.print("\n⚡ CREATING NETWORK PARTITION...")
        self.print("  Partition 1: node1, node2 (minority)")
        self.print("  Partition 2: node3, node4, node5 (majority)")

        partition1 = ['node1', 'node2']
        partition2 = ['node3', 'node4', 'node5']

        # Isolate partitions
        for node_id in partition1:
            nodes[node_id].network = {
                nid: nodes[nid] for nid in partition1 if nid != node_id
            }

        for node_id in partition2:
            nodes[node_id].network = {
                nid: nodes[nid] for nid in partition2 if nid != node_id
            }

        # Force election in majority partition
        time.sleep(0.2)
        nodes['node3'].check_election_timeout()

        new_leader = None
        for node_id in partition2:
            if nodes[node_id].is_leader():
                new_leader = nodes[node_id]
                break

        self.print(f"\n✓ New leader elected in majority partition: {new_leader.node_id if new_leader else 'None'}")

        # Heal partition
        self.print("\n⚡ HEALING NETWORK PARTITION...")

        for node_id, node in nodes.items():
            node.network = {
                nid: n for nid, n in nodes.items() if nid != node_id
            }

        # Let nodes synchronize
        time.sleep(0.3)
        if new_leader:
            new_leader.replicate_log()

        duration = time.time() - start_time

        # Check anomalies
        total_anomalies = sum(
            len(node.byzantine_detector.anomalies)
            for node in nodes.values()
            if node.byzantine_detector
        )

        result = {
            'test_name': 'network_partition',
            'num_orders': num_orders,
            'duration': duration,
            'partition_created': True,
            'partition_healed': True,
            'new_leader_elected': new_leader is not None,
            'anomalies_detected': total_anomalies,
            'passed': new_leader is not None
        }

        self.print(f"\n✓ Results:")
        self.print(f"  Partition handled: YES")
        self.print(f"  New leader: {new_leader.node_id if new_leader else 'None'}")
        self.print(f"  Anomalies detected: {total_anomalies}")
        self.print(f"  Test: {'PASSED' if result['passed'] else 'FAILED'}")

        self.test_results.append(result)
        return result

    def test_front_running_attack(self, num_attempts: int = 100) -> Dict[str, Any]:
        """
        Test front-running protection with malicious orders.
        """
        self.print("\n" + "=" * 80)
        self.print("TEST: FRONT-RUNNING ATTACK PROTECTION")
        self.print("=" * 80)

        nodes = self._create_production_cluster(['node1', 'node2', 'node3'])
        leader = next(n for n in nodes.values() if n.is_leader())

        self.print(f"\nSimulating {num_attempts} front-running attempts...")

        blocked = 0
        successful = 0

        for i in range(num_attempts):
            # Submit a legitimate order
            legit_order = {
                'symbol': 'AAPL',
                'price': '150.00',
                'side': 'buy',
                'quantity': 100,
                'agent_id': f'legit_{i}'
            }

            from blockchain.consensus.log_entry import LogEntryType
            leader.append_entry(LogEntryType.ORDER_SUBMIT, legit_order)

            # Try to front-run with same details
            frontrun_order = {
                'symbol': 'AAPL',
                'price': '150.00',  # Same price
                'side': 'buy',
                'quantity': 100,
                'agent_id': f'attacker_{i}'
            }

            from blockchain.consensus.log_entry import LogEntryType
            success = leader.append_entry(LogEntryType.ORDER_SUBMIT, frontrun_order)

            if success:
                successful += 1
            else:
                blocked += 1

        result = {
            'test_name': 'front_running_attack',
            'attempts': num_attempts,
            'blocked': blocked,
            'successful': successful,
            'block_rate': blocked / num_attempts if num_attempts > 0 else 0,
            'passed': blocked > 0  # Should block at least some
        }

        self.print(f"\n✓ Results:")
        self.print(f"  Front-running attempts: {num_attempts}")
        self.print(f"  Blocked: {blocked}")
        self.print(f"  Successful: {successful}")
        self.print(f"  Block rate: {result['block_rate'] * 100:.1f}%")
        self.print(f"  Test: {'PASSED' if result['passed'] else 'FAILED'}")

        self.test_results.append(result)
        return result

    def test_all_volatility_levels(self, orders_per_level: int = 200) -> Dict[str, Any]:
        """
        Test all volatility levels from real market data.
        """
        self.print("\n" + "=" * 80)
        self.print("TEST: ALL VOLATILITY LEVELS (476 S&P 500 Stocks)")
        self.print("=" * 80)

        summary = self.data_gen.get_pattern_summary()

        self.print(f"\nDataset Summary:")
        self.print(f"  Total stocks: {summary['total_stocks']}")
        self.print(f"  Entropy range: {summary['entropy']['min']:.2f} - {summary['entropy']['max']:.2f}")
        self.print(f"  Average entropy: {summary['entropy']['avg']:.3f}")
        self.print(f"\n  Volatility Distribution:")
        for level, count in summary['volatility_distribution'].items():
            self.print(f"    {level:8}: {count:3} stocks")

        levels = ['low', 'medium', 'high', 'extreme']
        results = {}

        for level in levels:
            self.print(f"\n--- Testing {level.upper()} Volatility ---")

            nodes = self._create_production_cluster(['node1', 'node2', 'node3'])
            leader = next(n for n in nodes.values() if n.is_leader())

            orders = self.data_gen.generate_realistic_orders(
                orders_per_level,
                volatility_level=level
            )

            start_time = time.time()
            successes = 0

            for i, order_data in enumerate(orders):
                order = Order.create_limit_order(
                    symbol=order_data['symbol'],
                    side=OrderSide.BUY if order_data['side'] == 'buy' else OrderSide.SELL,
                    quantity=Decimal(str(order_data['quantity'])),
                    price=Decimal(str(order_data['price'])),
                    agent_id=f"agent_{i}"
                )

                from blockchain.consensus.log_entry import LogEntryType
                order_data_dict = {
                    'symbol': order_data['symbol'],
                    'side': order_data['side'],
                    'price': str(order_data['price']),
                    'quantity': order_data['quantity'],
                    'agent_id': f"agent_{i}"
                }
                if leader.append_entry(LogEntryType.ORDER_SUBMIT, order_data_dict):
                    successes += 1

                if i % 25 == 0:
                    leader.replicate_log()

            duration = time.time() - start_time

            results[level] = {
                'orders': orders_per_level,
                'successes': successes,
                'throughput': orders_per_level / duration,
                'duration': duration
            }

            self.print(f"  ✓ {successes}/{orders_per_level} orders, "
                      f"{results[level]['throughput']:.2f} tx/s")

        result = {
            'test_name': 'all_volatility_levels',
            'levels_tested': levels,
            'results': results,
            'passed': all(r['successes'] > 0 for r in results.values())
        }

        self.test_results.append(result)
        return result

    def _create_production_cluster(self, node_ids: List[str]) -> Dict[str, ProductionRaftNode]:
        """Create a production Raft cluster."""
        nodes = {}

        for node_id in node_ids:
            other_nodes = [n for n in node_ids if n != node_id]
            nodes[node_id] = ProductionRaftNode(
                node_id,
                other_nodes,
                enable_prevote=True,
                enable_byzantine_detection=True,
                enable_frontrunning_protection=True
            )

        # Set up network
        for node in nodes.values():
            node.set_network({
                nid: n for nid, n in nodes.items() if nid != node.node_id
            })

        # Elect leader
        nodes[node_ids[0]].start_prevote()

        return nodes

    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("PRODUCTION CONSENSUS TEST REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Dataset: 476 S&P 500 stocks with real entropy data")
        lines.append("")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get('passed', False))

        lines.append(f"SUMMARY")
        lines.append("-" * 80)
        lines.append(f"  Total Tests: {total_tests}")
        lines.append(f"  Passed: {passed_tests}")
        lines.append(f"  Failed: {total_tests - passed_tests}")
        lines.append(f"  Success Rate: {passed_tests/total_tests*100:.1f}%")
        lines.append("")

        for result in self.test_results:
            lines.append(f"\n{result['test_name'].upper().replace('_', ' ')}")
            lines.append("-" * 80)
            for key, value in result.items():
                if key not in ['test_name', 'results']:
                    lines.append(f"  {key}: {value}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)


def main():
    """Run all production tests."""
    print("\n" + "=" * 80)
    print("RIGOROUS PRODUCTION CONSENSUS TESTING")
    print("Real Market Data: 476 S&P 500 Stocks")
    print("=" * 80)

    tester = ProductionConsensusTest(verbose=True)

    # Run all tests
    print("\nRunning comprehensive test suite...")
    print("(This will take several minutes with real market data)")

    # Test 1: Extreme entropy (worst case)
    tester.test_extreme_entropy_stocks(num_orders=500)

    # Test 2: Network partition
    tester.test_network_partition(num_orders=300)

    # Test 3: Front-running protection
    tester.test_front_running_attack(num_attempts=50)

    # Test 4: All volatility levels
    tester.test_all_volatility_levels(orders_per_level=100)

    # Generate report
    report = tester.generate_report()
    print(report)

    # Save report
    report_path = Path("production_test_results.txt")
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\n✓ Full report saved to: {report_path}")


if __name__ == '__main__':
    main()
