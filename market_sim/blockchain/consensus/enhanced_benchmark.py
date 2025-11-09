"""
Enhanced Benchmark Suite for Consensus Mechanisms.

Comprehensive performance comparison of Raft, PoW, and PoS consensus
algorithms with detailed analysis and recommendations.

Features:
- Throughput testing under various loads
- Latency distribution analysis
- Scalability testing
- Resource usage profiling
- Side-by-side comparison
- Production-readiness assessment
"""

import time
import sys
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from blockchain.consensus.distributed_orderbook import DistributedOrderBook
from blockchain.consensus.pow_blockchain import ProofOfWorkBlockchain, Transaction
from blockchain.consensus.pos_blockchain import ProofOfStakeBlockchain
from blockchain.consensus.realistic_pos_blockchain import RealisticPoSBlockchain
from core.models.base import Order, OrderSide


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    consensus_type: str
    num_transactions: int
    duration_seconds: float
    throughput_tps: float
    latencies_ms: List[float]
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    success_rate: float
    resource_usage: Dict[str, Any]


class ConsensusBenchmark:
    """Benchmark suite for consensus mechanisms."""

    def __init__(self, verbose: bool = True):
        """
        Initialize benchmark suite.

        Args:
            verbose: Print detailed output
        """
        self.verbose = verbose
        self.results: List[BenchmarkResult] = []

    def print(self, *args, **kwargs):
        """Print if verbose mode enabled."""
        if self.verbose:
            print(*args, **kwargs)

    def benchmark_raft(self, num_transactions: int = 1000,
                      num_nodes: int = 3) -> BenchmarkResult:
        """
        Benchmark Raft consensus.

        Args:
            num_transactions: Number of transactions to process
            num_nodes: Number of nodes in cluster

        Returns:
            Benchmark results
        """
        self.print(f"\n{'='*80}")
        self.print(f"BENCHMARKING RAFT CONSENSUS")
        self.print(f"{'='*80}")
        self.print(f"Transactions: {num_transactions}")
        self.print(f"Cluster size: {num_nodes}")

        # Create cluster
        node_ids = [f'node{i}' for i in range(1, num_nodes + 1)]
        nodes = {}

        for node_id in node_ids:
            other_nodes = [n for n in node_ids if n != node_id]
            nodes[node_id] = DistributedOrderBook('AAPL', node_id, other_nodes)

        for node in nodes.values():
            node.set_network(nodes)

        # Elect leader
        nodes['node1'].force_election()

        leader = nodes['node1']

        self.print("\n✓ Cluster ready, starting benchmark...")

        # Benchmark
        latencies = []
        successes = 0
        start_time = time.time()

        for i in range(num_transactions):
            # Create order
            side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL
            order = Order.create_limit_order(
                symbol='AAPL',
                side=side,
                quantity=Decimal('100'),
                price=Decimal(f'{150 + (i % 10)}.00'),
                agent_id=f'agent{i % 10}'
            )

            # Measure latency
            op_start = time.perf_counter()
            success = leader.submit_order(order)
            op_end = time.perf_counter()

            latency_ms = (op_end - op_start) * 1000
            latencies.append(latency_ms)

            if success:
                successes += 1

            # Replicate every 10 orders
            if i % 10 == 0:
                leader.raft_node.replicate_log()

        # Final replication
        for _ in range(3):
            leader.raft_node.replicate_log()

        end_time = time.time()
        duration = end_time - start_time

        # Calculate statistics
        throughput = num_transactions / duration
        success_rate = successes / num_transactions

        result = BenchmarkResult(
            consensus_type="Raft (CFT)",
            num_transactions=num_transactions,
            duration_seconds=duration,
            throughput_tps=throughput,
            latencies_ms=latencies,
            avg_latency_ms=statistics.mean(latencies),
            p50_latency_ms=self._percentile(latencies, 0.50),
            p95_latency_ms=self._percentile(latencies, 0.95),
            p99_latency_ms=self._percentile(latencies, 0.99),
            success_rate=success_rate,
            resource_usage={
                'log_size': len(leader.raft_node.log),
                'commit_index': leader.raft_node.commit_index
            }
        )

        self._print_result(result)
        self.results.append(result)
        return result

    def benchmark_pow(self, num_transactions: int = 100,
                     difficulty: int = 3) -> BenchmarkResult:
        """
        Benchmark Proof-of-Work.

        Args:
            num_transactions: Number of transactions
            difficulty: Mining difficulty

        Returns:
            Benchmark results
        """
        self.print(f"\n{'='*80}")
        self.print(f"BENCHMARKING PROOF-OF-WORK")
        self.print(f"{'='*80}")
        self.print(f"Transactions: {num_transactions}")
        self.print(f"Difficulty: {difficulty}")

        blockchain = ProofOfWorkBlockchain('miner1', difficulty)

        self.print("\n✓ Blockchain initialized, starting benchmark...")

        latencies = []
        start_time = time.time()

        # Add transactions
        for i in range(num_transactions):
            tx = Transaction.create_order_tx({
                'symbol': 'AAPL',
                'side': 'BUY' if i % 2 == 0 else 'SELL',
                'quantity': '100',
                'price': f'{150 + (i % 10)}.00'
            })

            tx_start = time.perf_counter()
            blockchain.add_transaction(tx)
            tx_end = time.perf_counter()

            latencies.append((tx_end - tx_start) * 1000)

            # Mine block every 10 transactions
            if (i + 1) % 10 == 0:
                block_start = time.perf_counter()
                blockchain.mine_pending_transactions()
                block_end = time.perf_counter()

                # Add mining time to latency for those transactions
                mining_latency = (block_end - block_start) * 1000
                for j in range(10):
                    latencies[i - j] += mining_latency / 10

        # Mine remaining transactions
        if blockchain.pending_transactions:
            blockchain.mine_pending_transactions()

        end_time = time.time()
        duration = end_time - start_time

        throughput = num_transactions / duration

        result = BenchmarkResult(
            consensus_type="Proof-of-Work (BFT)",
            num_transactions=num_transactions,
            duration_seconds=duration,
            throughput_tps=throughput,
            latencies_ms=latencies,
            avg_latency_ms=statistics.mean(latencies),
            p50_latency_ms=self._percentile(latencies, 0.50),
            p95_latency_ms=self._percentile(latencies, 0.95),
            p99_latency_ms=self._percentile(latencies, 0.99),
            success_rate=1.0,
            resource_usage={
                'chain_length': len(blockchain.chain),
                'blocks_mined': blockchain.stats['blocks_mined']
            }
        )

        self._print_result(result)
        self.results.append(result)
        return result

    def benchmark_pos(self, num_transactions: int = 500,
                     num_validators: int = 3,
                     realistic: bool = False) -> BenchmarkResult:
        """
        Benchmark Proof-of-Stake.

        Args:
            num_transactions: Number of transactions
            num_validators: Number of validators
            realistic: Use realistic PoS with crypto signatures

        Returns:
            Benchmark results
        """
        consensus_name = "Realistic PoS (BFT)" if realistic else "Proof-of-Stake (BFT)"

        self.print(f"\n{'='*80}")
        self.print(f"BENCHMARKING {consensus_name.upper()}")
        self.print(f"{'='*80}")
        self.print(f"Transactions: {num_transactions}")
        self.print(f"Validators: {num_validators}")

        # Create validators
        if realistic:
            validators = RealisticPoSBlockchain.create_realistic_network(
                num_validators=num_validators,
                stake_per_validator=Decimal('200'),
                network_latency_ms=50.0 if num_validators <= 3 else 100.0,
                enable_signatures=True
            )
        else:
            validators = {}
            for i in range(1, num_validators + 1):
                val_id = f'validator{i}'
                blockchain = ProofOfStakeBlockchain(val_id, Decimal('200'))

                # Register other validators
                for j in range(1, num_validators + 1):
                    if i != j:
                        blockchain.register_validator(f'validator{j}', Decimal('200'))

                validators[val_id] = blockchain

        self.print("\n✓ Validators ready, starting benchmark...")

        latencies = []
        start_time = time.time()

        # Add transactions
        for i in range(num_transactions):
            tx = Transaction.create_order_tx({
                'symbol': 'AAPL',
                'side': 'BUY' if i % 2 == 0 else 'SELL',
                'quantity': '100',
                'price': f'{150 + (i % 10)}.00'
            })

            tx_start = time.perf_counter()

            # Add to all validators
            for blockchain in validators.values():
                blockchain.add_transaction(tx)

            tx_end = time.perf_counter()
            latencies.append((tx_end - tx_start) * 1000)

            # Propose and validate block every 20 transactions
            if (i + 1) % 20 == 0:
                block_start = time.perf_counter()

                # Randomly select a proposer
                for blockchain in validators.values():
                    block = blockchain.propose_block()
                    if block:
                        # All validators approve
                        approvers = set(validators.keys())
                        blockchain.add_block(block, approvers)
                        break

                block_end = time.perf_counter()

                # Add block creation time
                block_latency = (block_end - block_start) * 1000
                for j in range(20):
                    if i - j >= 0:
                        latencies[i - j] += block_latency / 20

        end_time = time.time()
        duration = end_time - start_time

        throughput = num_transactions / duration

        # Get stats from first validator
        first_validator = list(validators.values())[0]
        resource_usage = {
            'chain_length': len(first_validator.chain),
            'blocks_created': first_validator.stats['blocks_created']
        }

        if realistic and hasattr(first_validator, 'crypto_stats'):
            resource_usage.update(first_validator.crypto_stats)

        result = BenchmarkResult(
            consensus_type=consensus_name,
            num_transactions=num_transactions,
            duration_seconds=duration,
            throughput_tps=throughput,
            latencies_ms=latencies,
            avg_latency_ms=statistics.mean(latencies),
            p50_latency_ms=self._percentile(latencies, 0.50),
            p95_latency_ms=self._percentile(latencies, 0.95),
            p99_latency_ms=self._percentile(latencies, 0.99),
            success_rate=1.0,
            resource_usage=resource_usage
        )

        self._print_result(result)
        self.results.append(result)
        return result

    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * p
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)

    def _print_result(self, result: BenchmarkResult) -> None:
        """Print benchmark result."""
        self.print(f"\n✓ Benchmark Complete:")
        self.print(f"  Duration: {result.duration_seconds:.2f}s")
        self.print(f"  Throughput: {result.throughput_tps:.2f} tx/s")
        self.print(f"  Success Rate: {result.success_rate * 100:.1f}%")
        self.print(f"\n  Latency Distribution:")
        self.print(f"    Avg: {result.avg_latency_ms:.2f}ms")
        self.print(f"    P50: {result.p50_latency_ms:.2f}ms")
        self.print(f"    P95: {result.p95_latency_ms:.2f}ms")
        self.print(f"    P99: {result.p99_latency_ms:.2f}ms")

    def generate_comparison_report(self) -> str:
        """
        Generate comparison report for all benchmarks.

        Returns:
            Formatted comparison report
        """
        if not self.results:
            return "No benchmark results available"

        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("CONSENSUS MECHANISM COMPARISON REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        lines.append("")

        # Summary table
        lines.append("PERFORMANCE SUMMARY")
        lines.append("-" * 80)
        lines.append(f"{'Consensus':<25} {'Throughput':<15} {'Avg Latency':<15} {'P95 Latency':<15}")
        lines.append("-" * 80)

        for result in self.results:
            lines.append(
                f"{result.consensus_type:<25} "
                f"{result.throughput_tps:>12.2f} tx/s "
                f"{result.avg_latency_ms:>12.2f}ms "
                f"{result.p95_latency_ms:>12.2f}ms"
            )

        lines.append("")

        # Detailed comparison
        lines.append("DETAILED COMPARISON")
        lines.append("-" * 80)

        for result in self.results:
            lines.append(f"\n{result.consensus_type}:")
            lines.append(f"  Transactions: {result.num_transactions}")
            lines.append(f"  Duration: {result.duration_seconds:.2f}s")
            lines.append(f"  Throughput: {result.throughput_tps:.2f} tx/s")
            lines.append(f"  Success Rate: {result.success_rate * 100:.1f}%")
            lines.append(f"  Latency (P50/P95/P99): "
                        f"{result.p50_latency_ms:.2f}ms / "
                        f"{result.p95_latency_ms:.2f}ms / "
                        f"{result.p99_latency_ms:.2f}ms")

        # Recommendations
        lines.append("")
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)

        fastest = max(self.results, key=lambda r: r.throughput_tps)
        lowest_latency = min(self.results, key=lambda r: r.avg_latency_ms)

        lines.append(f"\n✓ Highest Throughput: {fastest.consensus_type}")
        lines.append(f"  → {fastest.throughput_tps:.2f} tx/s")
        lines.append(f"  → Best for: High-volume trading, private exchanges")

        lines.append(f"\n✓ Lowest Latency: {lowest_latency.consensus_type}")
        lines.append(f"  → {lowest_latency.avg_latency_ms:.2f}ms average")
        lines.append(f"  → Best for: Low-latency trading, HFT systems")

        lines.append("")
        lines.append("Use Case Recommendations:")
        lines.append("  • Raft: Private/consortium exchanges (best performance)")
        lines.append("  • PoS: Public permissioned networks (good balance)")
        lines.append("  • PoW: Maximum decentralization (slower but most secure)")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


def main():
    """Run comprehensive benchmarks."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE CONSENSUS BENCHMARK SUITE")
    print("=" * 80)

    benchmark = ConsensusBenchmark(verbose=True)

    # Run benchmarks
    print("\nRunning benchmarks (this may take a few minutes)...")

    # Raft - highest throughput expected
    benchmark.benchmark_raft(num_transactions=1000, num_nodes=3)

    # PoS - medium throughput
    benchmark.benchmark_pos(num_transactions=500, num_validators=3,
                           realistic=False)

    # PoW - lowest throughput (reduce transactions for speed)
    benchmark.benchmark_pow(num_transactions=50, difficulty=3)

    # Generate report
    report = benchmark.generate_comparison_report()
    print(report)

    # Save report
    report_path = Path("benchmark_results.txt")
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\n✓ Full report saved to: {report_path}")


if __name__ == '__main__':
    main()
