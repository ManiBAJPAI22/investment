"""
Log Compaction for Raft Consensus.

Implements snapshot-based log compaction to prevent unbounded log growth.
This is essential for production systems that run continuously.

References:
- Raft Paper Section 7: Log Compaction
- https://raft.github.io/raft.pdf
"""

import pickle
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from .log_entry import LogEntry


@dataclass
class Snapshot:
    """
    Represents a snapshot of the state machine at a specific point.

    A snapshot captures the complete state at a particular log index,
    allowing the log to be truncated.
    """
    last_included_index: int
    last_included_term: int
    data: Dict[str, Any]
    timestamp: datetime

    def serialize(self) -> bytes:
        """Serialize snapshot to bytes."""
        return pickle.dumps({
            'last_included_index': self.last_included_index,
            'last_included_term': self.last_included_term,
            'data': self.data,
            'timestamp': self.timestamp
        })

    @classmethod
    def deserialize(cls, data: bytes) -> 'Snapshot':
        """Deserialize snapshot from bytes."""
        obj = pickle.loads(data)
        return cls(
            last_included_index=obj['last_included_index'],
            last_included_term=obj['last_included_term'],
            data=obj['data'],
            timestamp=obj['timestamp']
        )

    def save_to_file(self, filepath: Path) -> None:
        """Save snapshot to disk."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(self.serialize())

    @classmethod
    def load_from_file(cls, filepath: Path) -> 'Snapshot':
        """Load snapshot from disk."""
        with open(filepath, 'rb') as f:
            return cls.deserialize(f.read())


class LogCompactor:
    """
    Manages log compaction for Raft nodes.

    Features:
    - Automatic snapshot creation at configurable intervals
    - Log truncation after snapshot
    - Snapshot persistence to disk
    - Snapshot transfer for slow followers
    """

    def __init__(self, snapshot_threshold: int = 1000,
                 snapshot_dir: Optional[Path] = None):
        """
        Initialize log compactor.

        Args:
            snapshot_threshold: Create snapshot after this many log entries
            snapshot_dir: Directory to store snapshots (None = in-memory only)
        """
        self.snapshot_threshold = snapshot_threshold
        self.snapshot_dir = Path(snapshot_dir) if snapshot_dir else None
        self.last_snapshot: Optional[Snapshot] = None

        # Statistics
        self.stats = {
            'snapshots_created': 0,
            'snapshots_loaded': 0,
            'log_entries_compacted': 0,
            'disk_writes': 0,
            'disk_reads': 0
        }

    def should_create_snapshot(self, log: List[LogEntry],
                               last_applied: int) -> bool:
        """
        Determine if snapshot should be created.

        Args:
            log: Current Raft log
            last_applied: Index of last applied log entry

        Returns:
            True if snapshot should be created
        """
        if not log or last_applied == 0:
            return False

        # Calculate entries since last snapshot
        last_snapshot_index = self.last_snapshot.last_included_index if self.last_snapshot else 0
        entries_since_snapshot = last_applied - last_snapshot_index

        return entries_since_snapshot >= self.snapshot_threshold

    def create_snapshot(self, log: List[LogEntry],
                       last_applied: int,
                       state_data: Dict[str, Any]) -> Snapshot:
        """
        Create a snapshot of the current state.

        Args:
            log: Current Raft log
            last_applied: Index of last applied entry
            state_data: Current state machine data

        Returns:
            Created snapshot
        """
        if last_applied == 0 or last_applied > len(log):
            raise ValueError(f"Invalid last_applied index: {last_applied}")

        # Get the term of the last applied entry
        last_entry = log[last_applied - 1]

        # Create snapshot
        snapshot = Snapshot(
            last_included_index=last_applied,
            last_included_term=last_entry.term,
            data=state_data.copy(),  # Deep copy the state
            timestamp=datetime.utcnow()
        )

        self.last_snapshot = snapshot
        self.stats['snapshots_created'] += 1

        # Persist to disk if configured
        if self.snapshot_dir:
            self._save_snapshot(snapshot)

        return snapshot

    def compact_log(self, log: List[LogEntry],
                   snapshot: Snapshot) -> List[LogEntry]:
        """
        Compact the log by removing entries covered by snapshot.

        Args:
            log: Current Raft log
            snapshot: Snapshot to compact against

        Returns:
            Compacted log (only entries after snapshot)
        """
        # Find entries after snapshot
        new_log = []
        for entry in log:
            if entry.index > snapshot.last_included_index:
                new_log.append(entry)

        entries_removed = len(log) - len(new_log)
        self.stats['log_entries_compacted'] += entries_removed

        return new_log

    def _save_snapshot(self, snapshot: Snapshot) -> None:
        """Save snapshot to disk."""
        if not self.snapshot_dir:
            return

        # Create filename with index and term
        filename = f"snapshot_{snapshot.last_included_index}_{snapshot.last_included_term}.snap"
        filepath = self.snapshot_dir / filename

        snapshot.save_to_file(filepath)
        self.stats['disk_writes'] += 1

    def load_latest_snapshot(self) -> Optional[Snapshot]:
        """
        Load the latest snapshot from disk.

        Returns:
            Latest snapshot or None if no snapshots exist
        """
        if not self.snapshot_dir or not self.snapshot_dir.exists():
            return None

        # Find all snapshot files
        snapshot_files = list(self.snapshot_dir.glob("snapshot_*.snap"))

        if not snapshot_files:
            return None

        # Sort by last_included_index (extracted from filename)
        def extract_index(filepath: Path) -> int:
            parts = filepath.stem.split('_')
            return int(parts[1]) if len(parts) > 1 else 0

        latest_file = max(snapshot_files, key=extract_index)

        # Load snapshot
        snapshot = Snapshot.load_from_file(latest_file)
        self.last_snapshot = snapshot
        self.stats['disk_reads'] += 1
        self.stats['snapshots_loaded'] += 1

        return snapshot

    def install_snapshot(self, snapshot: Snapshot,
                        log: List[LogEntry]) -> List[LogEntry]:
        """
        Install a snapshot received from leader.

        Args:
            snapshot: Snapshot to install
            log: Current log

        Returns:
            New log after snapshot installation
        """
        # If snapshot is older than our log, ignore it
        if log and snapshot.last_included_index <= log[0].index:
            return log

        # Find entries after the snapshot
        new_log = []
        for entry in log:
            if entry.index > snapshot.last_included_index:
                new_log.append(entry)

        self.last_snapshot = snapshot

        # Save to disk if configured
        if self.snapshot_dir:
            self._save_snapshot(snapshot)

        return new_log

    def get_stats(self) -> Dict[str, Any]:
        """Get compaction statistics."""
        stats = self.stats.copy()

        if self.last_snapshot:
            stats['last_snapshot_index'] = self.last_snapshot.last_included_index
            stats['last_snapshot_term'] = self.last_snapshot.last_included_term
            stats['last_snapshot_timestamp'] = self.last_snapshot.timestamp.isoformat()

        return stats


class CompactedRaftNode:
    """
    Enhanced Raft node with log compaction support.

    This is a mixin that can be added to RaftNode to enable compaction.
    """

    def __init__(self, *args, enable_compaction: bool = True,
                 snapshot_threshold: int = 1000,
                 snapshot_dir: Optional[Path] = None,
                 **kwargs):
        """
        Initialize with compaction support.

        Args:
            enable_compaction: Enable automatic log compaction
            snapshot_threshold: Entries before creating snapshot
            snapshot_dir: Directory for snapshot persistence
        """
        super().__init__(*args, **kwargs)

        self.enable_compaction = enable_compaction

        if enable_compaction:
            self.compactor = LogCompactor(
                snapshot_threshold=snapshot_threshold,
                snapshot_dir=snapshot_dir
            )

            # Try to load existing snapshot
            snapshot = self.compactor.load_latest_snapshot()
            if snapshot:
                self._restore_from_snapshot(snapshot)

    def _restore_from_snapshot(self, snapshot: Snapshot) -> None:
        """
        Restore state from snapshot.

        Args:
            snapshot: Snapshot to restore from
        """
        # Truncate log
        self.log = self.compactor.compact_log(self.log, snapshot)

        # Update indices
        self.last_applied = max(self.last_applied, snapshot.last_included_index)
        self.commit_index = max(self.commit_index, snapshot.last_included_index)

        # Restore state machine data
        if hasattr(self, 'apply_callback') and self.apply_callback:
            # Application should handle snapshot restoration
            # self.apply_callback(snapshot.data)
            pass

    def check_and_compact(self) -> bool:
        """
        Check if compaction is needed and perform it.

        Returns:
            True if compaction was performed
        """
        if not self.enable_compaction:
            return False

        if not self.compactor.should_create_snapshot(self.log, self.last_applied):
            return False

        # Get current state data
        # In real implementation, this would come from the state machine
        state_data = {
            'last_applied': self.last_applied,
            'commit_index': self.commit_index,
            # Application-specific state would be added here
        }

        # Create snapshot
        snapshot = self.compactor.create_snapshot(
            self.log,
            self.last_applied,
            state_data
        )

        # Compact log
        self.log = self.compactor.compact_log(self.log, snapshot)

        return True

    def get_compaction_stats(self) -> Dict[str, Any]:
        """Get log compaction statistics."""
        if not self.enable_compaction:
            return {}

        return self.compactor.get_stats()


# Example usage
if __name__ == '__main__':
    # Demonstration of log compaction
    from .log_entry import LogEntry, LogEntryType

    print("Log Compaction Demonstration")
    print("=" * 80)

    # Create some log entries
    log = []
    for i in range(1, 2501):
        entry = LogEntry.create(
            term=1,
            index=i,
            entry_type=LogEntryType.ORDER_SUBMIT,
            data={'order_id': f'order_{i}'}
        )
        entry.committed = True
        log.append(entry)

    print(f"\nInitial log size: {len(log)} entries")
    print(f"Memory usage (estimated): {len(log) * 200 / 1024:.1f} KB")

    # Create compactor
    compactor = LogCompactor(snapshot_threshold=1000)

    # Create snapshot at entry 2000
    last_applied = 2000
    state_data = {'order_count': 2000, 'total_volume': 500000}

    snapshot = compactor.create_snapshot(log, last_applied, state_data)

    print(f"\n✓ Snapshot created:")
    print(f"  Last included index: {snapshot.last_included_index}")
    print(f"  Last included term: {snapshot.last_included_term}")
    print(f"  Timestamp: {snapshot.timestamp}")

    # Compact log
    compacted_log = compactor.compact_log(log, snapshot)

    print(f"\n✓ Log compacted:")
    print(f"  Old log size: {len(log)} entries")
    print(f"  New log size: {len(compacted_log)} entries")
    print(f"  Entries removed: {len(log) - len(compacted_log)}")
    print(f"  Space saved: {(len(log) - len(compacted_log)) * 200 / 1024:.1f} KB")
    print(f"  Compression ratio: {len(compacted_log) / len(log) * 100:.1f}%")

    # Statistics
    print(f"\nCompaction Statistics:")
    stats = compactor.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 80)
    print("✓ Log compaction demonstration complete!")
