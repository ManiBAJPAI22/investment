"""
Comprehensive Consensus Mechanism Benchmark.

Tests all consensus mechanisms (Raft, PoW, PoS) against all dataset patterns
and generates detailed performance metrics.

Usage:
    python comprehensive_benchmark.py
    python comprehensive_benchmark.py --quick  # Run with smaller datasets
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from decimal import Decimal
from datetime import datetime
import argparse

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from blockchain.consensus.raft_node import RaftNode, RaftConfig
from blockchain.consensus.distributed_orderbook import DistributedOrderBook
from blockchain.consensus.pow_blockchain import ProofOfWorkBlockchain, Transaction
from blockchain.consensus.pos_blockchain import ProofOfStakeBlockchain
from blockchain.consensus.realistic_pos_blockchain import RealisticPoSBlockchain
from tests.performance.dataset_generators import DatasetGenerator
from core.models.base import Order, OrderSide, OrderType


class BenchmarkResult:
    """Store benchmark results for a single test."""

    def __init__(self, consensus_type: str, dataset_type: str, dataset_size: int):
        self.consensus_type = consensus_type
        self.dataset_type = dataset_type
        self.dataset_size = dataset_size
        self.start_time = time.time()
        self.end_time = None
        self.duration = 0.0
        self.throughput = 0.0
        self.transactions_processed = 0
        self.blocks_created = 0
        self.avg_latency = 0.0
        self.success_rate = 0.0
        self.errors = []
        self.extra_metrics = {}

    def complete(self, transactions_processed: int, blocks_created: int, errors: List[str] = None):
        """Mark benchmark as complete and calculate metrics."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.transactions_processed = transactions_processed
        self.blocks_created = blocks_created
        self.errors = errors or []

        if self.duration > 0:
            self.throughput = transactions_processed / self.duration

        if transactions_processed > 0:
            self.avg_latency = (self.duration / transactions_processed) * 1000  # ms
            self.success_rate = ((transactions_processed - len(self.errors)) / transactions_processed) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'consensus_type': self.consensus_type,
            'dataset_type': self.dataset_type,
            'dataset_size': self.dataset_size,
            'duration_seconds': round(self.duration, 3),
            'throughput_tx_per_sec': round(self.throughput, 2),
            'transactions_processed': self.transactions_processed,
            'blocks_created': self.blocks_created,
            'avg_latency_ms': round(self.avg_latency, 3),
            'success_rate_percent': round(self.success_rate, 2),
            'error_count': len(self.errors),
            'extra_metrics': self.extra_metrics
        }


class ConsensusBenchmark:
    """Benchmark framework for testing consensus mechanisms."""

    def __init__(self, dataset_sizes: Dict[str, int] = None):
        """
        Initialize benchmark framework.

        Args:
            dataset_sizes: Dict mapping size labels to counts
                          Default: {'small': 100, 'medium': 500, 'large': 2000}
        """
        self.dataset_sizes = dataset_sizes or {
            'small': 100,
            'medium': 500,
            'large': 2000
        }
        self.results: List[BenchmarkResult] = []

    def benchmark_raft(self, orders: List[Dict[str, Any]], dataset_info: Tuple[str, str]) -> BenchmarkResult:
        """Benchmark Raft consensus."""
        dataset_type, size_label = dataset_info
        result = BenchmarkResult('Raft', dataset_type, len(orders))

        print(f"\n{'='*60}")
        print(f"Testing Raft with {dataset_type} ({size_label}: {len(orders)} orders)")
        print(f"{'='*60}")

        try:
            # Create 5-node Raft cluster
            cluster_nodes = [f'node{i}' for i in range(1, 6)]
            nodes = {}

            for node_id in cluster_nodes:
                nodes[node_id] = DistributedOrderBook(
                    symbol='TEST',  # Use a common symbol for all nodes
                    node_id=node_id,
                    cluster_nodes=cluster_nodes
                )

            # Connect nodes
            for node_id, node in nodes.items():
                for other_id, other_node in nodes.items():
                    if node_id != other_id:
                        node.raft_node.network[other_id] = other_node.raft_node

            # Wait for leader election - give more time for proper election
            time.sleep(1.0)
            for _ in range(20):
                for node in nodes.values():
                    node.tick()
                time.sleep(0.05)

            # Find leader
            leader = None
            for node in nodes.values():
                if node.is_leader():
                    leader = node
                    break

            if not leader:
                print("  ERROR: No leader elected after 20 rounds!")
                for node_id, node in nodes.items():
                    print(f"    {node_id}: state={node.raft_node.state}, term={node.raft_node.current_term}")
                result.errors.append("No leader elected")
                result.complete(0, 0, result.errors)
                return result

            print(f"  Leader elected: {leader.node_id}, term={leader.raft_node.current_term}")

            # Submit orders
            submitted = 0
            errors = []

            for order_data in orders:
                try:
                    # Convert order data to Order object using factory method
                    side = OrderSide.BUY if order_data['side'] == 'buy' else OrderSide.SELL
                    order = Order.create_limit_order(
                        symbol=order_data['symbol'],
                        side=side,
                        quantity=Decimal(str(order_data['quantity'])),
                        price=Decimal(str(order_data['price'])),
                        agent_id='benchmark_agent'
                    )

                    if leader.submit_order(order):
                        submitted += 1

                        # Periodic replication and ticking - more frequent for faster commits
                        if submitted % 10 == 0:
                            # Multiple rounds of replication to ensure commit
                            for _ in range(5):
                                leader.raft_node.replicate_log()
                                for node in nodes.values():
                                    node.tick()
                                time.sleep(0.02)

                            if submitted % 50 == 0:
                                print(f"  Processed {submitted}/{len(orders)} orders...")

                except Exception as e:
                    errors.append(f"Order submission error: {str(e)}")

            # Final replication - ensure ALL orders are committed
            print(f"  Finalizing consensus...")
            for _ in range(20):
                leader.raft_node.replicate_log()
                for node in nodes.values():
                    node.tick()
                time.sleep(0.05)

            # Collect metrics from leader state
            state = leader.get_state()
            raft_state = state.get('raft_state', {})

            # Count committed orders (transactions actually processed)
            committed_count = leader.stats['orders_committed']
            log_entries = len(leader.raft_node.log)

            print(f"  Final status: submitted={submitted}, committed={committed_count}, log_entries={log_entries}")

            result.extra_metrics = {
                'log_entries': log_entries,
                'commit_index': raft_state.get('commit_index', 0),
                'cluster_size': len(nodes),
                'leader_term': leader.raft_node.current_term
            }

            # Use committed count as transactions processed (more accurate)
            result.complete(committed_count, 0, errors)  # Raft doesn't have "blocks"

        except Exception as e:
            import traceback
            error_msg = f"Benchmark error: {str(e)}\n{traceback.format_exc()}"
            print(f"  ERROR in Raft benchmark: {error_msg}")
            result.errors.append(error_msg)
            result.complete(0, 0, result.errors)

        return result

    def benchmark_pow(self, orders: List[Dict[str, Any]], dataset_info: Tuple[str, str],
                     difficulty: int = 3) -> BenchmarkResult:
        """Benchmark Proof-of-Work consensus."""
        dataset_type, size_label = dataset_info
        result = BenchmarkResult('PoW', dataset_type, len(orders))

        print(f"\n{'='*60}")
        print(f"Testing PoW (difficulty={difficulty}) with {dataset_type} ({size_label}: {len(orders)} orders)")
        print(f"{'='*60}")

        try:
            blockchain = ProofOfWorkBlockchain(node_id='miner1', difficulty=difficulty)

            # Add transactions
            submitted = 0
            errors = []

            for order_data in orders:
                try:
                    tx = Transaction.create_order_tx(order_data)
                    if blockchain.add_transaction(tx):
                        submitted += 1

                        # Mine blocks periodically
                        if submitted % 100 == 0:
                            block = blockchain.mine_pending_transactions()
                            if block:
                                print(f"  Mined block #{block.index} with {len(block.transactions)} transactions")
                            print(f"  Processed {submitted}/{len(orders)} orders...")

                except Exception as e:
                    errors.append(f"Transaction error: {str(e)}")

            # Mine remaining transactions
            while blockchain.pending_transactions:
                block = blockchain.mine_pending_transactions()
                if block:
                    print(f"  Mined block #{block.index} with {len(block.transactions)} transactions")

            # Collect metrics
            chain_info = blockchain.get_chain_info()
            result.extra_metrics = {
                'chain_length': chain_info['chain_length'],
                'difficulty': difficulty,
                'total_mining_time': blockchain.stats['total_mining_time'],
                'blocks_mined': blockchain.stats['blocks_mined']
            }

            result.complete(
                blockchain.stats['transactions_processed'],
                blockchain.stats['blocks_mined'],
                errors
            )

        except Exception as e:
            result.errors.append(f"Benchmark error: {str(e)}")
            result.complete(0, 0, result.errors)

        return result

    def benchmark_pos(self, orders: List[Dict[str, Any]], dataset_info: Tuple[str, str], realistic_mode: bool = False) -> BenchmarkResult:
        """
        Benchmark Proof-of-Stake consensus.

        Args:
            orders: List of order data to process
            dataset_info: Tuple of (dataset_type, size_label)
            realistic_mode: If True, use RealisticPoSBlockchain with crypto+network simulation
        """
        dataset_type, size_label = dataset_info
        consensus_label = 'PoS-Realistic' if realistic_mode else 'PoS'
        result = BenchmarkResult(consensus_label, dataset_type, len(orders))

        print(f"\n{'='*60}")
        print(f"Testing {consensus_label} with {dataset_type} ({size_label}: {len(orders)} orders)")
        print(f"{'='*60}")

        try:
            # Use realistic or standard PoS blockchain
            if realistic_mode:
                # Use factory method to create realistic validator network
                validators = RealisticPoSBlockchain.create_realistic_network(
                    num_validators=3,
                    stake_per_validator=Decimal('200'),
                    network_latency_ms=50.0,  # 50ms WAN latency
                    enable_signatures=True
                )
                print("✓ Using Realistic PoS (Ed25519 signatures + 50ms network latency)")
            else:
                # Standard PoS (fast, in-memory)
                validators = {}
                stakes = {
                    'validator1': Decimal('200'),
                    'validator2': Decimal('200'),
                    'validator3': Decimal('200')
                }

                # Create first validator to get genesis block
                first_validator = ProofOfStakeBlockchain(
                    node_id='validator1',
                    initial_stake=stakes['validator1']
                )
                validators['validator1'] = first_validator
                genesis_block = first_validator.chain[0]

                # Create other validators with the SAME genesis block
                for validator_id in ['validator2', 'validator3']:
                    validator = ProofOfStakeBlockchain(
                        node_id=validator_id,
                        initial_stake=stakes[validator_id]
                    )
                    # Replace their genesis with the shared one
                    validator.chain[0] = genesis_block
                    validators[validator_id] = validator

                # Register all validators in EACH blockchain instance
                # This ensures all validators know about each other
                for validator_id, blockchain in validators.items():
                    for other_id, other_stake in stakes.items():
                        if other_id != validator_id:  # Don't re-register self
                            blockchain.register_validator(other_id, other_stake)

                print("✓ Using Standard PoS (in-memory, no crypto overhead)")

            # Use validator with highest stake (all equal, so any works)
            main_validator = validators['validator3']

            # Add transactions
            submitted = 0
            errors = []
            blocks_created = 0

            for order_data in orders:
                try:
                    tx = Transaction.create_order_tx(order_data)

                    # Add transaction to ALL validators (simulates network broadcast)
                    for validator_bc in validators.values():
                        validator_bc.add_transaction(tx)

                    submitted += 1

                    # Propose blocks periodically (every 50 for quicker processing)
                    if submitted % 50 == 0:
                        # Try to get a proposal from any validator (they select randomly)
                        # Keep trying until someone is selected (max 20 attempts)
                        block = None
                        proposing_validator = None

                        for attempt in range(20):
                            for vid, validator_bc in validators.items():
                                block = validator_bc.propose_block()
                                if block:
                                    proposing_validator = vid
                                    break
                            if block:
                                break

                        if block:
                            # Collect validator approvals
                            validators_approved = set([block.miner])  # Proposer auto-approves

                            # Get approval from all other validators
                            for vid, validator_bc in validators.items():
                                if vid != block.miner:
                                    if validator_bc.validate_block(block, vid):
                                        validators_approved.add(vid)

                            # Try to add block with collected approvals
                            if main_validator.add_block(block, validators_approved):
                                blocks_created += 1

                                # Sync all validators - remove transactions from their pending pools
                                for vid, validator_bc in validators.items():
                                    if vid != proposing_validator:
                                        validator_bc.pending_transactions = validator_bc.pending_transactions[len(block.transactions):]

                    if submitted % 100 == 0:
                        print(f"  Processed {submitted}/{len(orders)} orders...")

                except Exception as e:
                    errors.append(f"Transaction error: {str(e)}")

            # Propose remaining transactions
            max_attempts = 100  # Prevent infinite loop
            attempts = 0

            while main_validator.pending_transactions and attempts < max_attempts:
                attempts += 1

                # Try to get a proposal from any validator (they select randomly)
                # Keep trying until someone is selected (max 20 inner attempts)
                block = None
                proposing_validator = None

                for inner_attempt in range(20):
                    for vid, validator_bc in validators.items():
                        block = validator_bc.propose_block()
                        if block:
                            proposing_validator = vid
                            break
                    if block:
                        break

                if block:
                    # Collect approvals from all validators
                    validators_approved = set([block.miner])
                    for vid, validator_bc in validators.items():
                        if vid != block.miner:
                            if validator_bc.validate_block(block, vid):
                                validators_approved.add(vid)

                    # Add block to all validators' chains
                    if main_validator.add_block(block, validators_approved):
                        blocks_created += 1

                        # Sync all validators - remove the same transactions from their pending pools
                        for vid, validator_bc in validators.items():
                            if vid != proposing_validator:
                                validator_bc.pending_transactions = validator_bc.pending_transactions[len(block.transactions):]
                    else:
                        break
                else:
                    break

            # Collect metrics
            chain_info = main_validator.get_chain_info()
            result.extra_metrics = {
                'chain_length': chain_info['chain_length'],
                'total_stake': chain_info['total_stake'],
                'active_validators': chain_info['active_validators'],
                'blocks_created': chain_info['stats']['blocks_created']
            }

            result.complete(
                main_validator.stats['transactions_processed'],
                blocks_created,
                errors
            )

        except Exception as e:
            result.errors.append(f"Benchmark error: {str(e)}")
            result.complete(0, 0, result.errors)

        return result

    def run_comprehensive_benchmark(self, quick_mode: bool = False, realistic_mode: bool = False) -> List[BenchmarkResult]:
        """
        Run comprehensive benchmark across all consensus mechanisms and datasets.

        Args:
            quick_mode: If True, use smaller datasets for faster testing
            realistic_mode: If True, use realistic PoS with crypto+network simulation
        """
        if quick_mode:
            self.dataset_sizes = {'quick': 50}

        print("\n" + "="*80)
        print("COMPREHENSIVE CONSENSUS MECHANISM BENCHMARK")
        print("="*80)
        print(f"Dataset sizes: {self.dataset_sizes}")
        print(f"Realistic mode: {'ENABLED (crypto+network)' if realistic_mode else 'DISABLED (fast)'}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("="*80)

        # Generate all datasets
        datasets = {}
        for size_label, size in self.dataset_sizes.items():
            print(f"\nGenerating {size_label} datasets ({size} orders each)...")
            datasets[size_label] = DatasetGenerator.get_all_patterns(size)
            print(f"  Generated {len(datasets[size_label])} different patterns")

        # Run benchmarks
        for size_label, dataset_dict in datasets.items():
            for dataset_type, orders in dataset_dict.items():
                dataset_info = (dataset_type, size_label)

                # Test Raft
                result = self.benchmark_raft(orders, dataset_info)
                self.results.append(result)
                print(f"\n✓ Raft: {result.throughput:.2f} tx/sec")

                # Test PoW (lower difficulty for large datasets)
                difficulty = 2 if size_label == 'large' else 3
                result = self.benchmark_pow(orders, dataset_info, difficulty)
                self.results.append(result)
                print(f"✓ PoW: {result.throughput:.2f} tx/sec")

                # Test PoS (realistic or fast mode)
                result = self.benchmark_pos(orders, dataset_info, realistic_mode)
                self.results.append(result)
                consensus_label = 'PoS-Realistic' if realistic_mode else 'PoS'
                print(f"✓ {consensus_label}: {result.throughput:.2f} tx/sec")

        return self.results

    def save_results(self, filepath: str = None):
        """Save benchmark results to JSON file."""
        if filepath is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filepath = f"benchmark_results_{timestamp}.json"

        results_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'dataset_sizes': self.dataset_sizes,
            'total_tests': len(self.results),
            'results': [r.to_dict() for r in self.results]
        }

        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"\n✓ Results saved to {filepath}")
        return filepath

    def print_summary(self):
        """Print summary of benchmark results."""
        print("\n" + "="*80)
        print("BENCHMARK SUMMARY")
        print("="*80)

        # Group by consensus type
        by_consensus = {}
        for result in self.results:
            if result.consensus_type not in by_consensus:
                by_consensus[result.consensus_type] = []
            by_consensus[result.consensus_type].append(result)

        for consensus_type, results in by_consensus.items():
            print(f"\n{consensus_type} Consensus:")
            print(f"  Tests run: {len(results)}")

            avg_throughput = sum(r.throughput for r in results) / len(results)
            max_throughput = max(r.throughput for r in results)
            min_throughput = min(r.throughput for r in results)

            print(f"  Throughput:")
            print(f"    Average: {avg_throughput:.2f} tx/sec")
            print(f"    Max: {max_throughput:.2f} tx/sec")
            print(f"    Min: {min_throughput:.2f} tx/sec")

            total_errors = sum(len(r.errors) for r in results)
            if total_errors > 0:
                print(f"  Total errors: {total_errors}")


def main():
    """Run comprehensive benchmark."""
    parser = argparse.ArgumentParser(description='Comprehensive Consensus Benchmark')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick test with smaller datasets')
    parser.add_argument('--realistic', action='store_true',
                       help='Use realistic PoS with Ed25519 signatures and 50ms network latency')
    parser.add_argument('--output', type=str, default=None,
                       help='Output JSON file path')

    args = parser.parse_args()

    # Run benchmark
    benchmark = ConsensusBenchmark()
    results = benchmark.run_comprehensive_benchmark(
        quick_mode=args.quick,
        realistic_mode=args.realistic
    )

    # Print summary
    benchmark.print_summary()

    # Save results
    output_path = benchmark.save_results(args.output)

    print("\n" + "="*80)
    print("BENCHMARK COMPLETE")
    print("="*80)
    print(f"Total tests: {len(results)}")
    print(f"Results saved to: {output_path}")
    print("\nNext: Run visualization script to generate charts")
    print(f"  python analysis/visualization/advanced_visualizer.py {output_path}")
    print("="*80)


if __name__ == '__main__':
    main()
