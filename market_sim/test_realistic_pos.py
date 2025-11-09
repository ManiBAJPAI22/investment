"""Quick test of realistic PoS implementation."""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent))

from blockchain.consensus.realistic_pos_blockchain import RealisticPoSBlockchain
from blockchain.consensus.pow_blockchain import Transaction

def test_realistic_pos():
    """Test realistic PoS with signatures and network simulation."""
    print("\n" + "="*60)
    print("Testing Realistic PoS Blockchain")
    print("="*60)

    # Create validator network
    print("\n1. Creating 3 validators with Ed25519 keys...")
    validators = RealisticPoSBlockchain.create_realistic_network(
        num_validators=3,
        stake_per_validator=Decimal('200'),
        network_latency_ms=50.0,
        enable_signatures=True
    )
    print(f"✓ Created {len(validators)} validators")

    # Add some transactions
    print("\n2. Adding 10 test transactions...")
    for i in range(10):
        tx = Transaction.create_order_tx({
            'id': f'order_{i}',
            'symbol': 'TEST',
            'side': 'buy' if i % 2 == 0 else 'sell',
            'quantity': 100,
            'price': 50.0
        })

        # Broadcast to all validators
        for validator_bc in validators.values():
            validator_bc.add_transaction(tx)

    print("✓ Transactions added to all validators")

    # Propose and validate a block
    print("\n3. Proposing block with signatures...")

    # Try to propose (one will be selected)
    block = None
    proposing_validator = None

    for vid, validator_bc in validators.items():
        block = validator_bc.propose_block()
        if block:
            proposing_validator = vid
            print(f"✓ Validator {vid} was selected and proposed block")
            break

    if not block:
        print("✗ No validator was selected")
        return False

    # Validate block with signature verification
    print("\n4. Validating block (checking signatures)...")
    validators_approved = set([block.miner])

    for vid, validator_bc in validators.items():
        if vid != block.miner:
            if validator_bc.validate_block(block, vid):
                validators_approved.add(vid)
                print(f"✓ Validator {vid} approved (signature verified)")

    print(f"\n5. Consensus reached: {len(validators_approved)}/3 validators approved")

    # Add block
    main_validator = validators[proposing_validator]
    if main_validator.add_block(block, validators_approved):
        print("✓ Block added to blockchain")

        # Get crypto stats
        info = main_validator.get_chain_info()
        crypto_stats = info.get('crypto_stats', {})

        print("\n" + "="*60)
        print("REALISTIC PoS PERFORMANCE METRICS")
        print("="*60)
        print(f"Signatures created: {crypto_stats.get('signatures_created', 0)}")
        print(f"Signatures verified: {crypto_stats.get('signatures_verified', 0)}")
        print(f"Avg signature time: {info.get('avg_signature_time_ms', 0):.3f} ms")
        print(f"Avg verification time: {info.get('avg_verification_time_ms', 0):.3f} ms")
        print(f"Network latency (configured): {info.get('network_latency_ms', 0):.1f} ms")
        print(f"Total network time: {crypto_stats.get('network_time_total_ms', 0):.1f} ms")
        print("="*60)

        return True
    else:
        print("✗ Failed to add block")
        return False


if __name__ == '__main__':
    success = test_realistic_pos()
    sys.exit(0 if success else 1)
