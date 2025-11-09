"""
Comprehensive Consensus Mechanism Comparison Tests.

Compares Raft vs PoW vs PoS with large datasets:
- Throughput (transactions per second)
- Latency (time to finality)
- Scalability (handling increasing load)
- Resource efficiency
- Fault tolerance
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import random
from decimal import Decimal
from typing import List, Dict, Any

from blockchain.consensus.distributed_orderbook import DistributedOrderBook
from blockchain.consensus.pow_blockchain import ProofOfWorkBlockchain, Transaction as PoWTransaction
from blockchain.consensus.pos_blockchain import ProofOfStakeBlockchain
from core.models.base import Order, OrderSide


class ConsensusPerformanceTester:
    """Test and compare consensus mechanisms."""

    def __init__(self):
        self.results = {
            'raft': {},
            'pow': {},
            'pos': {}
        }

    def generate_orders(self, count: int) -> List[Dict[str, Any]]:
        """Generate test orders."""
        orders = []
        for i in range(count):
            order = {
                'id': f'order_{i}',
                'symbol': 'AAPL',
                'side': 'buy' if i % 2 == 0 else 'sell',
                'quantity': str(random.randint(100, 1000)),
                'price': f'{150 + random.randint(-10, 10)}.00',
                'agent_id': f'trader_{i % 100}'
            }
            orders.append(order)
        return orders

    def test_raft_throughput(self, num_orders: int = 1000) -> Dict[str, Any]:
        """Test Raft consensus throughput."""
        print(f"\n{'='*80}")
        print(f"RAFT CONSENSUS - Throughput Test ({num_orders} orders)")
        print('='*80)

        # Setup cluster
        nodes = {}
        for i in range(1, 4):
            node_id = f'node{i}'
            other_nodes = [f'node{j}' for j in range(1, 4) if j != i]
            nodes[node_id] = DistributedOrderBook('AAPL', node_id, other_nodes)

        for node in nodes.values():
            node.set_network(nodes)

        nodes['node1'].force_election()
        time.sleep(0.05)

        leader = next(n for n in nodes.values() if n.is_leader())

        # Generate orders
        print(f"Generating {num_orders} orders...")
        orders = self.generate_orders(num_orders)

        # Submit orders
        print("Submitting orders...")
        start_time = time.time()

        submitted = 0
        for order_data in orders:
            order = Order.create_limit_order(
                symbol=order_data['symbol'],
                side=OrderSide.BUY if order_data['side'] == 'buy' else OrderSide.SELL,
                quantity=Decimal(order_data['quantity']),
                price=Decimal(order_data['price']),
                agent_id=order_data['agent_id']
            )

            if leader.submit_order(order):
                submitted += 1

            # Batch replication
            if submitted % 50 == 0:
                leader.raft_node.replicate_log()

        # Final replication
        for _ in range(5):
            leader.raft_node.replicate_log()
            time.sleep(0.01)

        elapsed = time.time() - start_time

        results = {
            'orders_submitted': submitted,
            'time_elapsed': elapsed,
            'throughput': submitted / elapsed if elapsed > 0 else 0,
            'avg_latency_ms': (elapsed / submitted * 1000) if submitted > 0 else 0,
            'log_size': len(leader.raft_node.log),
            'consistency': all(len(n.raft_node.log) == len(leader.raft_node.log)
                             for n in nodes.values())
        }

        print(f"\nResults:")
        print(f"  Submitted: {results['orders_submitted']} orders")
        print(f"  Time: {results['time_elapsed']:.2f}s")
        print(f"  Throughput: {results['throughput']:.0f} orders/sec")
        print(f"  Avg Latency: {results['avg_latency_ms']:.2f}ms")
        print(f"  Consistency: {'✓ YES' if results['consistency'] else '✗ NO'}")

        return results

    def test_pow_throughput(self, num_orders: int = 100, difficulty: int = 3) -> Dict[str, Any]:
        """Test PoW blockchain throughput."""
        print(f"\n{'='*80}")
        print(f"PROOF-OF-WORK - Throughput Test ({num_orders} orders, difficulty={difficulty})")
        print('='*80)

        # Create blockchain
        blockchain = ProofOfWorkBlockchain('miner1', difficulty=difficulty)

        # Generate orders
        print(f"Generating {num_orders} orders...")
        orders = self.generate_orders(num_orders)

        # Submit transactions
        print("Adding transactions to blockchain...")
        start_time = time.time()

        for order_data in orders:
            tx = PoWTransaction.create_order_tx(order_data)
            blockchain.add_transaction(tx)

        tx_time = time.time() - start_time

        # Mine blocks
        print(f"Mining blocks (this may take a while with difficulty={difficulty})...")
        mine_start = time.time()

        blocks_mined = 0
        while blockchain.pending_transactions and blocks_mined < 10:
            block = blockchain.mine_pending_transactions()
            if block:
                blocks_mined += 1

        mine_time = time.time() - mine_start
        total_time = time.time() - start_time

        # Calculate throughput
        confirmed_tx = sum(len(block.transactions) for block in blockchain.chain[1:])

        results = {
            'orders_submitted': num_orders,
            'blocks_mined': blocks_mined,
            'confirmed_transactions': confirmed_tx,
            'total_time': total_time,
            'mining_time': mine_time,
            'throughput': confirmed_tx / total_time if total_time > 0 else 0,
            'avg_block_time': mine_time / blocks_mined if blocks_mined > 0 else 0,
            'avg_latency_ms': (total_time / confirmed_tx * 1000) if confirmed_tx > 0 else 0,
            'chain_valid': blockchain.is_chain_valid()
        }

        print(f"\nResults:")
        print(f"  Transactions: {results['confirmed_transactions']}/{num_orders}")
        print(f"  Blocks mined: {results['blocks_mined']}")
        print(f"  Total time: {results['total_time']:.2f}s")
        print(f"  Mining time: {results['mining_time']:.2f}s")
        print(f"  Throughput: {results['throughput']:.1f} tx/sec")
        print(f"  Avg block time: {results['avg_block_time']:.2f}s")
        print(f"  Avg latency: {results['avg_latency_ms']:.0f}ms")
        print(f"  Chain valid: {'✓ YES' if results['chain_valid'] else '✗ NO'}")

        return results

    def test_pos_throughput(self, num_orders: int = 500) -> Dict[str, Any]:
        """Test PoS blockchain throughput."""
        print(f"\n{'='*80}")
        print(f"PROOF-OF-STAKE - Throughput Test ({num_orders} orders)")
        print('='*80)

        # Create validators
        validators = {}
        for i in range(1, 4):
            validator_id = f'validator{i}'
            stake = Decimal(str(100 + i * 50))  # Different stakes
            validators[validator_id] = ProofOfStakeBlockchain(validator_id, stake)

        # Register cross-validators
        for vid, blockchain in validators.items():
            for other_vid, other_chain in validators.items():
                if vid != other_vid:
                    blockchain.register_validator(other_vid, other_chain.validators[other_vid].stake)

        # Generate orders
        print(f"Generating {num_orders} orders...")
        orders = self.generate_orders(num_orders)

        # Add transactions to all validators
        print("Adding transactions...")
        start_time = time.time()

        for order_data in orders:
            tx = PoWTransaction.create_order_tx(order_data)
            for blockchain in validators.values():
                blockchain.add_transaction(tx)

        tx_time = time.time() - start_time

        # Propose and validate blocks
        print("Proposing and validating blocks...")
        propose_start = time.time()

        blocks_created = 0
        rounds = 0
        max_rounds = 20

        while any(bc.pending_transactions for bc in validators.values()) and rounds < max_rounds:
            rounds += 1

            # Each validator attempts to propose
            for blockchain in validators.values():
                block = blockchain.propose_block()

                if block:
                    # Simulate validation by other validators
                    approvals = {blockchain.node_id}

                    for other_id, other_bc in validators.items():
                        if other_id != blockchain.node_id:
                            if other_bc.validate_block(block, other_id):
                                approvals.add(other_id)

                    # Add block if approved
                    if blockchain.add_block(block, approvals):
                        blocks_created += 1

                        # Sync block to other validators
                        for other_bc in validators.values():
                            if other_bc.node_id != blockchain.node_id:
                                other_bc.chain.append(block)
                                other_bc.pending_transactions = other_bc.pending_transactions[100:]

            time.sleep(0.01)  # Simulate block time

        propose_time = time.time() - propose_start
        total_time = time.time() - start_time

        # Get results from first validator
        main_validator = list(validators.values())[0]
        confirmed_tx = sum(len(block.transactions) for block in main_validator.chain[1:])

        results = {
            'orders_submitted': num_orders,
            'blocks_created': blocks_created,
            'confirmed_transactions': confirmed_tx,
            'rounds': rounds,
            'total_time': total_time,
            'block_creation_time': propose_time,
            'throughput': confirmed_tx / total_time if total_time > 0 else 0,
            'avg_block_time': propose_time / blocks_created if blocks_created > 0 else 0,
            'avg_latency_ms': (total_time / confirmed_tx * 1000) if confirmed_tx > 0 else 0,
            'chain_valid': main_validator.is_chain_valid()
        }

        print(f"\nResults:")
        print(f"  Transactions: {results['confirmed_transactions']}/{num_orders}")
        print(f"  Blocks created: {results['blocks_created']}")
        print(f"  Total time: {results['total_time']:.2f}s")
        print(f"  Block creation: {results['block_creation_time']:.2f}s")
        print(f"  Throughput: {results['throughput']:.1f} tx/sec")
        print(f"  Avg block time: {results['avg_block_time']:.2f}s")
        print(f"  Avg latency: {results['avg_latency_ms']:.0f}ms")
        print(f"  Chain valid: {'✓ YES' if results['chain_valid'] else '✗ NO'}")

        return results

    def run_comprehensive_comparison(self):
        """Run comprehensive comparison of all three mechanisms."""
        print("\n" + "="*80)
        print(" " * 20 + "CONSENSUS MECHANISM COMPARISON")
        print(" " * 25 + "Large Dataset Tests")
        print("="*80)

        # Test 1: Small dataset (quick comparison)
        print("\n\n" + "="*80)
        print("TEST 1: Small Dataset (100 orders)")
        print("="*80)

        raft_small = self.test_raft_throughput(100)
        pow_small = self.test_pow_throughput(100, difficulty=2)
        pos_small = self.test_pos_throughput(100)

        # Test 2: Medium dataset
        print("\n\n" + "="*80)
        print("TEST 2: Medium Dataset (500 orders)")
        print("="*80)

        raft_medium = self.test_raft_throughput(500)
        pow_medium = self.test_pow_throughput(100, difficulty=3)  # Fewer for PoW (slow)
        pos_medium = self.test_pos_throughput(500)

        # Test 3: Large dataset (Raft only - others too slow)
        print("\n\n" + "="*80)
        print("TEST 3: Large Dataset (2000 orders)")
        print("="*80)

        raft_large = self.test_raft_throughput(2000)
        pos_large = self.test_pos_throughput(1000)

        # Print comparison summary
        self.print_comparison_summary({
            'raft_small': raft_small,
            'pow_small': pow_small,
            'pos_small': pos_small,
            'raft_medium': raft_medium,
            'pow_medium': pow_medium,
            'pos_medium': pos_medium,
            'raft_large': raft_large,
            'pos_large': pos_large
        })

    def print_comparison_summary(self, results: Dict[str, Dict[str, Any]]):
        """Print formatted comparison summary."""
        print("\n\n" + "="*80)
        print(" " * 25 + "COMPARISON SUMMARY")
        print("="*80)

        print("\n" + "-"*80)
        print("THROUGHPUT (Transactions per Second)")
        print("-"*80)
        print(f"{'Algorithm':<20} {'Small (100)':<15} {'Medium (500)':<15} {'Large (2000)':<15}")
        print("-"*80)

        raft_tput = [
            results['raft_small']['throughput'],
            results['raft_medium']['throughput'],
            results['raft_large']['throughput']
        ]
        pow_tput = [
            results['pow_small']['throughput'],
            results['pow_medium']['throughput'],
            0  # Not tested for large
        ]
        pos_tput = [
            results['pos_small']['throughput'],
            results['pos_medium']['throughput'],
            results['pos_large']['throughput']
        ]

        print(f"{'Raft':<20} {raft_tput[0]:>10.0f} tx/s {raft_tput[1]:>10.0f} tx/s {raft_tput[2]:>10.0f} tx/s")
        print(f"{'PoW (Bitcoin-like)':<20} {pow_tput[0]:>10.1f} tx/s {pow_tput[1]:>10.1f} tx/s {'N/A':>14}")
        print(f"{'PoS (Ethereum-like)':<20} {pos_tput[0]:>10.1f} tx/s {pos_tput[1]:>10.1f} tx/s {pos_tput[2]:>10.1f} tx/s")

        print("\n" + "-"*80)
        print("LATENCY (Average Transaction Latency)")
        print("-"*80)
        print(f"{'Algorithm':<20} {'Small (100)':<15} {'Medium (500)':<15} {'Large (2000)':<15}")
        print("-"*80)

        raft_lat = [
            results['raft_small']['avg_latency_ms'],
            results['raft_medium']['avg_latency_ms'],
            results['raft_large']['avg_latency_ms']
        ]
        pow_lat = [
            results['pow_small']['avg_latency_ms'],
            results['pow_medium']['avg_latency_ms'],
            0
        ]
        pos_lat = [
            results['pos_small']['avg_latency_ms'],
            results['pos_medium']['avg_latency_ms'],
            results['pos_large']['avg_latency_ms']
        ]

        print(f"{'Raft':<20} {raft_lat[0]:>10.2f} ms {raft_lat[1]:>10.2f} ms {raft_lat[2]:>10.2f} ms")
        print(f"{'PoW (Bitcoin-like)':<20} {pow_lat[0]:>10.0f} ms {pow_lat[1]:>10.0f} ms {'N/A':>14}")
        print(f"{'PoS (Ethereum-like)':<20} {pos_lat[0]:>10.0f} ms {pos_lat[1]:>10.0f} ms {pos_lat[2]:>10.0f} ms")

        print("\n" + "="*80)
        print("KEY TAKEAWAYS")
        print("="*80)

        # Determine winner in each category
        best_throughput = max(raft_tput[1], pow_tput[1], pos_tput[1])
        best_latency = min(raft_lat[1], pow_lat[1], pos_lat[1])

        if raft_tput[1] == best_throughput:
            print("✓ RAFT: Best throughput - " + str(int(best_throughput)) + " tx/sec")
        if raft_lat[1] == best_latency:
            print("✓ RAFT: Best latency - " + f"{best_latency:.2f}ms")

        print("\nPerformance Rankings:")
        print("  1. Raft (Crash Fault Tolerance) - FASTEST")
        print(f"     • {int(raft_tput[1]):,} tx/sec throughput")
        print(f"     • {raft_lat[1]:.2f}ms latency")
        print("     • Use case: Private/consortium exchanges")
        print("")
        print(f"  2. Proof-of-Stake - MODERATE")
        print(f"     • {int(pos_tput[1]):,} tx/sec throughput")
        print(f"     • {pos_lat[1]:.0f}ms latency")
        print("     • Use case: Public permissioned blockchains")
        print("")
        print("  3. Proof-of-Work - SLOWEST")
        print(f"     • {int(pow_tput[1])} tx/sec throughput")
        print(f"     • {pow_lat[1]:.0f}ms latency")
        print("     • Use case: Public permissionless blockchains")

        print("\n" + "="*80)


if __name__ == '__main__':
    tester = ConsensusPerformanceTester()
    tester.run_comprehensive_comparison()
