"""
Log entry structures for Raft consensus algorithm.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict
from uuid import UUID, uuid4


class LogEntryType(Enum):
    """Types of log entries in the replicated state machine."""
    ORDER_SUBMIT = "order_submit"
    ORDER_CANCEL = "order_cancel"
    TRADE_EXECUTE = "trade_execute"
    STATE_SNAPSHOT = "state_snapshot"
    NO_OP = "no_op"


@dataclass
class LogEntry:
    """
    Represents a single entry in the Raft log.

    Each log entry contains:
    - term: The term when entry was received by leader
    - index: Position in the log
    - entry_type: Type of operation
    - data: The actual command/data to be applied
    - timestamp: When the entry was created
    """
    id: UUID
    term: int
    index: int
    entry_type: LogEntryType
    data: Dict[str, Any]
    timestamp: datetime
    committed: bool = False

    @classmethod
    def create(cls, term: int, index: int, entry_type: LogEntryType,
               data: Dict[str, Any]) -> 'LogEntry':
        """Create a new log entry."""
        return cls(
            id=uuid4(),
            term=term,
            index=index,
            entry_type=entry_type,
            data=data,
            timestamp=datetime.utcnow(),
            committed=False
        )

    @classmethod
    def create_order_submit(cls, term: int, index: int, order_data: Dict[str, Any]) -> 'LogEntry':
        """Create a log entry for order submission."""
        return cls.create(term, index, LogEntryType.ORDER_SUBMIT, order_data)

    @classmethod
    def create_order_cancel(cls, term: int, index: int, order_id: str) -> 'LogEntry':
        """Create a log entry for order cancellation."""
        return cls.create(term, index, LogEntryType.ORDER_CANCEL, {"order_id": order_id})

    @classmethod
    def create_trade_execute(cls, term: int, index: int, trade_data: Dict[str, Any]) -> 'LogEntry':
        """Create a log entry for trade execution."""
        return cls.create(term, index, LogEntryType.TRADE_EXECUTE, trade_data)

    @classmethod
    def create_no_op(cls, term: int, index: int) -> 'LogEntry':
        """Create a no-op log entry (used by new leaders)."""
        return cls.create(term, index, LogEntryType.NO_OP, {})

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for serialization."""
        return {
            'id': str(self.id),
            'term': self.term,
            'index': self.index,
            'entry_type': self.entry_type.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'committed': self.committed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create log entry from dictionary."""
        return cls(
            id=UUID(data['id']),
            term=data['term'],
            index=data['index'],
            entry_type=LogEntryType(data['entry_type']),
            data=data['data'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            committed=data['committed']
        )
