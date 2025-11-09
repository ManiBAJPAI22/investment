"""
Proof-of-Work (PoW) Blockchain Implementation.

Implements a simplified PoW blockchain similar to Bitcoin/Ethereum 1.0
for distributed order book consensus.

Features:
- Block mining with adjustable difficulty
- Transaction validation
- Chain validation and consensus
- Longest chain rule
- Merkle tree for transaction integrity
"""

import hashlib
import time
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from uuid import UUID, uuid4
from decimal import Decimal


@dataclass
class Transaction:
    """Represents a transaction in the blockchain."""
    id: str
    timestamp: datetime
    tx_type: str  # 'order_submit', 'order_cancel', 'trade'
    data: Dict[str, Any]
    signature: Optional[str] = None

    @classmethod
    def create_order_tx(cls, order_data: Dict[str, Any]) -> 'Transaction':
        """Create a transaction for order submission."""
        return cls(
            id=str(uuid4()),
            timestamp=datetime.utcnow(),
            tx_type='order_submit',
            data=order_data
        )

    @classmethod
    def create_cancel_tx(cls, order_id: str) -> 'Transaction':
        """Create a transaction for order cancellation."""
        return cls(
            id=str(uuid4()),
            timestamp=datetime.utcnow(),
            tx_type='order_cancel',
            data={'order_id': order_id}
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize transaction to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'tx_type': self.tx_type,
            'data': self.data,
            'signature': self.signature
        }

    def hash(self) -> str:
        """Calculate transaction hash."""
        tx_string = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()


@dataclass
class Block:
    """Represents a block in the blockchain."""
    index: int
    timestamp: datetime
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    hash: str = ""
    miner: str = ""
    difficulty: int = 4

    def calculate_hash(self) -> str:
        """Calculate block hash."""
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp.isoformat(),
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'miner': self.miner
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int, miner_id: str) -> None:
        """
        Mine the block by finding a hash with required difficulty.

        Proof-of-Work: Find nonce such that hash starts with 'difficulty' zeros.
        """
        self.difficulty = difficulty
        self.miner = miner_id
        target = '0' * difficulty

        start_time = time.time()
        attempts = 0

        while True:
            self.hash = self.calculate_hash()
            attempts += 1

            if self.hash.startswith(target):
                mining_time = time.time() - start_time
                print(f"  Block mined! Hash: {self.hash[:16]}... "
                      f"(Nonce: {self.nonce}, Time: {mining_time:.3f}s, "
                      f"Attempts: {attempts:,})")
                break

            self.nonce += 1

            # Safety: prevent infinite loop in tests
            if attempts > 10_000_000:
                print(f"  Mining timeout after {attempts:,} attempts")
                break

    def is_valid(self) -> bool:
        """Validate block hash meets difficulty requirement."""
        target = '0' * self.difficulty
        return self.hash.startswith(target) and self.hash == self.calculate_hash()

    @classmethod
    def create_genesis_block(cls) -> 'Block':
        """Create the genesis (first) block."""
        genesis = cls(
            index=0,
            timestamp=datetime.utcnow(),
            transactions=[],
            previous_hash="0" * 64,
            difficulty=1
        )
        genesis.mine_block(1, "genesis")
        return genesis


class ProofOfWorkBlockchain:
    """
    Proof-of-Work blockchain for distributed order book.

    Implements Bitcoin-style consensus with longest chain rule.
    """

    def __init__(self, node_id: str, difficulty: int = 4):
        """
        Initialize PoW blockchain.

        Args:
            node_id: Unique identifier for this node
            difficulty: Mining difficulty (number of leading zeros)
        """
        self.node_id = node_id
        self.difficulty = difficulty
        self.chain: List[Block] = [Block.create_genesis_block()]
        self.pending_transactions: List[Transaction] = []
        self.mining_reward = Decimal('0.01')  # Reward for mining a block

        # Statistics
        self.stats = {
            'blocks_mined': 0,
            'transactions_processed': 0,
            'total_mining_time': 0.0,
            'chain_reorganizations': 0
        }

    def get_latest_block(self) -> Block:
        """Get the latest block in the chain."""
        return self.chain[-1]

    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add a transaction to pending pool.

        Args:
            transaction: Transaction to add

        Returns:
            True if transaction was added successfully
        """
        # Validate transaction (simplified)
        if not transaction.id or not transaction.tx_type:
            return False

        self.pending_transactions.append(transaction)
        return True

    def mine_pending_transactions(self) -> Optional[Block]:
        """
        Mine a new block with pending transactions.

        Returns:
            The newly mined block, or None if no transactions
        """
        if not self.pending_transactions:
            return None

        # Create new block
        block = Block(
            index=len(self.chain),
            timestamp=datetime.utcnow(),
            transactions=self.pending_transactions[:100],  # Max 100 tx per block
            previous_hash=self.get_latest_block().hash,
            difficulty=self.difficulty
        )

        # Mine the block (Proof-of-Work)
        print(f"\n[{self.node_id}] Mining block #{block.index} "
              f"with {len(block.transactions)} transactions...")

        start_time = time.time()
        block.mine_block(self.difficulty, self.node_id)
        mining_time = time.time() - start_time

        # Add to chain
        self.chain.append(block)

        # Remove mined transactions from pending
        self.pending_transactions = self.pending_transactions[100:]

        # Update stats
        self.stats['blocks_mined'] += 1
        self.stats['transactions_processed'] += len(block.transactions)
        self.stats['total_mining_time'] += mining_time

        return block

    def is_chain_valid(self, chain: Optional[List[Block]] = None) -> bool:
        """
        Validate the blockchain.

        Args:
            chain: Chain to validate (defaults to own chain)

        Returns:
            True if chain is valid
        """
        if chain is None:
            chain = self.chain

        # Check genesis block
        if chain[0].index != 0 or chain[0].previous_hash != "0" * 64:
            return False

        # Validate each block
        for i in range(1, len(chain)):
            current_block = chain[i]
            previous_block = chain[i - 1]

            # Check hash is valid
            if not current_block.is_valid():
                return False

            # Check previous hash link
            if current_block.previous_hash != previous_block.hash:
                return False

            # Check index
            if current_block.index != previous_block.index + 1:
                return False

        return True

    def resolve_conflicts(self, peer_chains: List[List[Block]]) -> bool:
        """
        Consensus algorithm: Longest valid chain wins.

        Args:
            peer_chains: Chains from other nodes

        Returns:
            True if our chain was replaced
        """
        longest_chain = self.chain
        replaced = False

        # Find longest valid chain
        for chain in peer_chains:
            if len(chain) > len(longest_chain) and self.is_chain_valid(chain):
                longest_chain = chain
                replaced = True

        if replaced:
            self.chain = longest_chain
            self.stats['chain_reorganizations'] += 1
            print(f"[{self.node_id}] Chain replaced with longer chain "
                  f"(length: {len(self.chain)})")

        return replaced

    def get_block_by_index(self, index: int) -> Optional[Block]:
        """Get block by index."""
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None

    def get_transactions_from_block(self, block_index: int) -> List[Transaction]:
        """Get all transactions from a block."""
        block = self.get_block_by_index(block_index)
        return block.transactions if block else []

    def get_all_confirmed_transactions(self, confirmations: int = 1) -> List[Transaction]:
        """
        Get all confirmed transactions.

        Args:
            confirmations: Number of blocks for confirmation

        Returns:
            List of confirmed transactions
        """
        transactions = []
        cutoff_index = len(self.chain) - confirmations

        for i, block in enumerate(self.chain):
            if i <= cutoff_index:
                transactions.extend(block.transactions)

        return transactions

    def get_chain_info(self) -> Dict[str, Any]:
        """Get blockchain information."""
        return {
            'node_id': self.node_id,
            'chain_length': len(self.chain),
            'difficulty': self.difficulty,
            'pending_transactions': len(self.pending_transactions),
            'latest_block_hash': self.get_latest_block().hash,
            'stats': self.stats
        }

    def calculate_hash_rate(self) -> float:
        """Calculate average hash rate (hashes per second)."""
        if self.stats['total_mining_time'] == 0:
            return 0.0

        # Approximate: Each difficulty increase requires 16x more hashes
        total_hashes = sum(
            16 ** block.difficulty
            for block in self.chain[1:]  # Skip genesis
        )

        return total_hashes / self.stats['total_mining_time']


def merkle_root(transactions: List[Transaction]) -> str:
    """
    Calculate Merkle root of transactions.

    Used for efficient transaction verification in blockchain.
    """
    if not transactions:
        return hashlib.sha256(b'').hexdigest()

    # Hash each transaction
    tx_hashes = [tx.hash() for tx in transactions]

    # Build Merkle tree
    while len(tx_hashes) > 1:
        if len(tx_hashes) % 2 != 0:
            tx_hashes.append(tx_hashes[-1])  # Duplicate last if odd

        new_hashes = []
        for i in range(0, len(tx_hashes), 2):
            combined = tx_hashes[i] + tx_hashes[i + 1]
            new_hash = hashlib.sha256(combined.encode()).hexdigest()
            new_hashes.append(new_hash)

        tx_hashes = new_hashes

    return tx_hashes[0]
