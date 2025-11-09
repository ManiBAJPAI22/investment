"""
Proof-of-Stake (PoS) Blockchain Implementation.

Implements a simplified PoS blockchain similar to Ethereum 2.0
for distributed order book consensus.

Features:
- Validator selection based on stake
- Block proposing and validation
- Stake-weighted consensus
- Slashing for malicious behavior
- More energy-efficient than PoW
"""

import hashlib
import time
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Set
from uuid import uuid4
from decimal import Decimal

from .pow_blockchain import Transaction, Block


@dataclass
class Validator:
    """Represents a validator in PoS system."""
    id: str
    stake: Decimal
    is_active: bool = True
    blocks_proposed: int = 0
    blocks_validated: int = 0
    slashed: bool = False

    def __hash__(self):
        return hash(self.id)


class ProofOfStakeBlockchain:
    """
    Proof-of-Stake blockchain for distributed order book.

    Implements stake-weighted validator selection and consensus.
    """

    def __init__(self, node_id: str, initial_stake: Decimal = Decimal('100')):
        """
        Initialize PoS blockchain.

        Args:
            node_id: Unique identifier for this node
            initial_stake: Initial stake for this validator
        """
        self.node_id = node_id
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []

        # Consensus parameters (SET BEFORE validator registration)
        self.min_stake = Decimal('10')
        self.block_time = 3  # Target seconds between blocks
        self.min_validators = 3

        # Statistics (MUST be before register_validator)
        self.stats = {
            'blocks_created': 0,
            'transactions_processed': 0,
            'total_stake': Decimal('0'),
            'slashing_events': 0,
            'validator_changes': 0
        }

        # Validator management
        self.validators: Dict[str, Validator] = {}
        self.register_validator(node_id, initial_stake)

        # Create genesis block
        genesis = Block(
            index=0,
            timestamp=datetime.utcnow(),
            transactions=[],
            previous_hash="0" * 64,
            difficulty=0
        )
        genesis.hash = genesis.calculate_hash()
        genesis.miner = "genesis"
        self.chain.append(genesis)

    def register_validator(self, validator_id: str, stake: Decimal) -> bool:
        """
        Register a new validator.

        Args:
            validator_id: Validator identifier
            stake: Amount of stake

        Returns:
            True if registered successfully
        """
        if stake < self.min_stake:
            return False

        if validator_id not in self.validators:
            self.validators[validator_id] = Validator(
                id=validator_id,
                stake=stake,
                is_active=True
            )
            self.stats['total_stake'] += stake
            self.stats['validator_changes'] += 1
            return True

        return False

    def add_stake(self, validator_id: str, amount: Decimal) -> bool:
        """Add stake to a validator."""
        if validator_id in self.validators:
            self.validators[validator_id].stake += amount
            self.stats['total_stake'] += amount
            return True
        return False

    def select_validator(self) -> Optional[Validator]:
        """
        Select validator using stake-weighted random selection.

        Higher stake = higher probability of selection.
        """
        active_validators = [v for v in self.validators.values()
                            if v.is_active and not v.slashed]

        if not active_validators:
            return None

        # Calculate total active stake
        total_stake = sum(v.stake for v in active_validators)

        if total_stake == 0:
            return None

        # Weighted random selection
        rand_value = random.uniform(0, float(total_stake))
        cumulative = Decimal('0')

        for validator in active_validators:
            cumulative += validator.stake
            if float(cumulative) >= rand_value:
                return validator

        return active_validators[-1]

    def get_latest_block(self) -> Block:
        """Get the latest block in the chain."""
        return self.chain[-1]

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pending pool."""
        if not transaction.id or not transaction.tx_type:
            return False

        self.pending_transactions.append(transaction)
        return True

    def propose_block(self) -> Optional[Block]:
        """
        Propose a new block (called by selected validator).

        Returns:
            Proposed block or None
        """
        if not self.pending_transactions:
            return None

        # Select validator
        validator = self.select_validator()
        if not validator:
            print(f"[{self.node_id}] No validator selected")
            return None

        # Only this node can propose if selected
        if validator.id != self.node_id:
            return None

        print(f"\n[{self.node_id}] Selected as validator "
              f"(stake: {validator.stake})")

        # Create block
        block = Block(
            index=len(self.chain),
            timestamp=datetime.utcnow(),
            transactions=self.pending_transactions[:100],
            previous_hash=self.get_latest_block().hash,
            difficulty=0,  # No mining in PoS
            miner=validator.id
        )

        # In PoS, no mining needed - just sign the block
        block.nonce = 0
        block.hash = block.calculate_hash()

        validator.blocks_proposed += 1

        return block

    def validate_block(self, block: Block, validator_id: str) -> bool:
        """
        Validate a proposed block.

        Args:
            block: Block to validate
            validator_id: ID of validating validator

        Returns:
            True if block is valid
        """
        # Check validator exists and is active
        if validator_id not in self.validators:
            return False

        validator = self.validators[validator_id]
        if not validator.is_active or validator.slashed:
            return False

        # Validate block structure
        if block.previous_hash != self.get_latest_block().hash:
            return False

        if block.index != len(self.chain):
            return False

        if block.hash != block.calculate_hash():
            return False

        validator.blocks_validated += 1
        return True

    def add_block(self, block: Block, validators_approved: Set[str]) -> bool:
        """
        Add block to chain if approved by majority of validators.

        Args:
            block: Block to add
            validators_approved: Set of validator IDs that approved

        Returns:
            True if block was added
        """
        # Check we have minimum validators
        if len(self.validators) < self.min_validators:
            print(f"[{self.node_id}] Not enough validators")
            return False

        # Calculate stake of approving validators
        approving_stake = sum(
            self.validators[vid].stake
            for vid in validators_approved
            if vid in self.validators
        )

        # Need >50% of total stake to approve
        required_stake = self.stats['total_stake'] * Decimal('0.5')

        if approving_stake <= required_stake:
            print(f"[{self.node_id}] Insufficient stake approval "
                  f"({approving_stake} / {required_stake})")
            return False

        # Add block
        self.chain.append(block)

        # Remove transactions from pending
        self.pending_transactions = self.pending_transactions[100:]

        # Update stats
        self.stats['blocks_created'] += 1
        self.stats['transactions_processed'] += len(block.transactions)

        print(f"[{self.node_id}] Block #{block.index} added "
              f"({len(block.transactions)} transactions)")

        return True

    def slash_validator(self, validator_id: str, reason: str) -> bool:
        """
        Slash a validator for malicious behavior.

        Args:
            validator_id: Validator to slash
            reason: Reason for slashing

        Returns:
            True if validator was slashed
        """
        if validator_id not in self.validators:
            return False

        validator = self.validators[validator_id]
        if validator.slashed:
            return False

        print(f"[{self.node_id}] Slashing validator {validator_id}: {reason}")

        # Slash validator
        validator.slashed = True
        validator.is_active = False

        # Forfeit stake (could be redistributed)
        slashed_amount = validator.stake
        validator.stake = Decimal('0')

        self.stats['total_stake'] -= slashed_amount
        self.stats['slashing_events'] += 1

        return True

    def is_chain_valid(self, chain: Optional[List[Block]] = None) -> bool:
        """Validate the blockchain."""
        if chain is None:
            chain = self.chain

        if not chain:
            return False

        # Check genesis
        if chain[0].index != 0:
            return False

        # Validate each block
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

            if current.previous_hash != previous.hash:
                return False

            if current.index != previous.index + 1:
                return False

            if current.hash != current.calculate_hash():
                return False

        return True

    def get_all_confirmed_transactions(self, confirmations: int = 2) -> List[Transaction]:
        """Get all confirmed transactions."""
        transactions = []
        cutoff = len(self.chain) - confirmations

        for i, block in enumerate(self.chain):
            if i <= cutoff:
                transactions.extend(block.transactions)

        return transactions

    def get_chain_info(self) -> Dict[str, Any]:
        """Get blockchain information."""
        active_validators = sum(1 for v in self.validators.values()
                               if v.is_active and not v.slashed)

        return {
            'node_id': self.node_id,
            'chain_length': len(self.chain),
            'pending_transactions': len(self.pending_transactions),
            'validators': len(self.validators),
            'active_validators': active_validators,
            'total_stake': float(self.stats['total_stake']),
            'latest_block_hash': self.get_latest_block().hash,
            'stats': self.stats
        }

    def get_validator_info(self, validator_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a validator."""
        if validator_id not in self.validators:
            return None

        v = self.validators[validator_id]
        return {
            'id': v.id,
            'stake': float(v.stake),
            'is_active': v.is_active,
            'slashed': v.slashed,
            'blocks_proposed': v.blocks_proposed,
            'blocks_validated': v.blocks_validated
        }
