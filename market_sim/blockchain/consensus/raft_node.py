"""
Raft Consensus Algorithm Implementation.

Implements the Raft consensus algorithm for distributed fault-tolerant
state machine replication, adapted for distributed market state management.

References:
- Ongaro & Ousterhout, "In Search of an Understandable Consensus Algorithm"
- https://raft.github.io/
"""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any
from uuid import UUID, uuid4

from .log_entry import LogEntry, LogEntryType


class NodeState(Enum):
    """Possible states for a Raft node."""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class RaftConfig:
    """Configuration parameters for Raft node."""
    # Election timeout range (milliseconds)
    election_timeout_min: int = 150
    election_timeout_max: int = 300

    # Heartbeat interval (milliseconds)
    heartbeat_interval: int = 50

    # Request timeout (milliseconds)
    request_timeout: int = 100

    # Minimum cluster size for quorum
    min_cluster_size: int = 3


@dataclass
class VoteRequest:
    """Request for vote from candidate."""
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass
class VoteResponse:
    """Response to vote request."""
    term: int
    vote_granted: bool


@dataclass
class AppendEntriesRequest:
    """Request to append entries (heartbeat or log replication)."""
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: List[LogEntry]
    leader_commit: int


@dataclass
class AppendEntriesResponse:
    """Response to append entries request."""
    term: int
    success: bool
    match_index: int


class RaftNode:
    """
    Raft consensus algorithm node implementation.

    Implements the three roles: Follower, Candidate, and Leader.
    Handles leader election, log replication, and maintains consistency.
    """

    def __init__(self, node_id: str, cluster_nodes: List[str],
                 config: Optional[RaftConfig] = None):
        """
        Initialize a Raft node.

        Args:
            node_id: Unique identifier for this node
            cluster_nodes: List of all node IDs in the cluster
            config: Configuration parameters
        """
        self.node_id = node_id
        self.cluster_nodes = [n for n in cluster_nodes if n != node_id]
        self.config = config or RaftConfig()

        # Persistent state (should be persisted to stable storage)
        self.current_term: int = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []

        # Volatile state on all servers
        self.commit_index: int = 0
        self.last_applied: int = 0
        self.state: NodeState = NodeState.FOLLOWER
        self.leader_id: Optional[str] = None

        # Volatile state on leaders (reinitialized after election)
        self.next_index: Dict[str, int] = {}  # For each server, index of next log entry to send
        self.match_index: Dict[str, int] = {}  # For each server, index of highest log entry known to be replicated

        # Election and heartbeat timers
        self.last_heartbeat: datetime = datetime.utcnow()
        self.election_timeout: timedelta = self._random_election_timeout()

        # Vote tracking
        self.votes_received: Set[str] = set()

        # Network simulation (in real impl, this would be actual network)
        self.network: Dict[str, 'RaftNode'] = {}

        # State machine application callback
        self.apply_callback: Optional[Callable[[LogEntry], Any]] = None

        # Statistics
        self.stats = {
            'elections_started': 0,
            'elections_won': 0,
            'heartbeats_sent': 0,
            'heartbeats_received': 0,
            'log_entries_appended': 0,
            'terms': []
        }

    def _random_election_timeout(self) -> timedelta:
        """Generate a random election timeout."""
        timeout_ms = random.randint(
            self.config.election_timeout_min,
            self.config.election_timeout_max
        )
        return timedelta(milliseconds=timeout_ms)

    def set_network(self, network: Dict[str, 'RaftNode']) -> None:
        """Set the network of nodes for communication."""
        self.network = network

    def set_apply_callback(self, callback: Callable[[LogEntry], Any]) -> None:
        """Set callback function to apply committed log entries."""
        self.apply_callback = callback

    # ==================== State Transitions ====================

    def become_follower(self, term: int, leader_id: Optional[str] = None) -> None:
        """Transition to follower state."""
        self.state = NodeState.FOLLOWER
        self.current_term = term
        self.voted_for = None
        self.leader_id = leader_id
        self.last_heartbeat = datetime.utcnow()
        self.election_timeout = self._random_election_timeout()

    def become_candidate(self) -> None:
        """Transition to candidate state and start election."""
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}
        self.last_heartbeat = datetime.utcnow()
        self.election_timeout = self._random_election_timeout()
        self.stats['elections_started'] += 1
        self.stats['terms'].append({
            'term': self.current_term,
            'started_at': datetime.utcnow().isoformat(),
            'role': 'candidate'
        })

    def become_leader(self) -> None:
        """Transition to leader state."""
        self.state = NodeState.LEADER
        self.leader_id = self.node_id
        self.stats['elections_won'] += 1

        # Initialize leader state
        last_log_index = len(self.log)
        self.next_index = {node: last_log_index + 1 for node in self.cluster_nodes}
        self.match_index = {node: 0 for node in self.cluster_nodes}

        # Append no-op entry to commit entries from previous terms
        self._append_log_entry(LogEntry.create_no_op(self.current_term, len(self.log) + 1))

    # ==================== Election ====================

    def check_election_timeout(self) -> None:
        """Check if election timeout has elapsed."""
        if self.state == NodeState.LEADER:
            return

        time_since_heartbeat = datetime.utcnow() - self.last_heartbeat
        if time_since_heartbeat > self.election_timeout:
            self.start_election()

    def start_election(self) -> None:
        """Start a new election."""
        self.become_candidate()

        # Request votes from all other nodes
        last_log_index = len(self.log)
        last_log_term = self.log[-1].term if self.log else 0

        vote_request = VoteRequest(
            term=self.current_term,
            candidate_id=self.node_id,
            last_log_index=last_log_index,
            last_log_term=last_log_term
        )

        for node_id in self.cluster_nodes:
            if node_id in self.network:
                response = self.network[node_id].handle_vote_request(vote_request)
                if response.vote_granted:
                    self.votes_received.add(node_id)

        # Check if we have majority
        self.check_election_result()

    def handle_vote_request(self, request: VoteRequest) -> VoteResponse:
        """Handle incoming vote request."""
        # Update term if request has higher term
        if request.term > self.current_term:
            self.become_follower(request.term)

        # Deny vote if request term is outdated
        if request.term < self.current_term:
            return VoteResponse(term=self.current_term, vote_granted=False)

        # Check if we can vote for this candidate
        can_vote = (
            (self.voted_for is None or self.voted_for == request.candidate_id) and
            self._is_log_up_to_date(request.last_log_index, request.last_log_term)
        )

        if can_vote:
            self.voted_for = request.candidate_id
            self.last_heartbeat = datetime.utcnow()

        return VoteResponse(term=self.current_term, vote_granted=can_vote)

    def _is_log_up_to_date(self, candidate_last_index: int, candidate_last_term: int) -> bool:
        """Check if candidate's log is at least as up-to-date as ours."""
        if not self.log:
            return True

        our_last_term = self.log[-1].term
        our_last_index = len(self.log)

        # Log is more up-to-date if last term is higher,
        # or same term but longer log
        if candidate_last_term != our_last_term:
            return candidate_last_term >= our_last_term
        return candidate_last_index >= our_last_index

    def check_election_result(self) -> None:
        """Check if we have received majority of votes."""
        if self.state != NodeState.CANDIDATE:
            return

        total_nodes = len(self.cluster_nodes) + 1  # +1 for self
        votes_needed = (total_nodes // 2) + 1

        if len(self.votes_received) >= votes_needed:
            self.become_leader()

    # ==================== Log Replication ====================

    def append_entry(self, entry_type: LogEntryType, data: Dict[str, Any]) -> bool:
        """
        Append a new entry to the log (only on leader).

        Returns True if successfully appended, False otherwise.
        """
        if self.state != NodeState.LEADER:
            return False

        entry = LogEntry.create(
            term=self.current_term,
            index=len(self.log) + 1,
            entry_type=entry_type,
            data=data
        )

        self._append_log_entry(entry)
        return True

    def _append_log_entry(self, entry: LogEntry) -> None:
        """Internal method to append entry to log."""
        self.log.append(entry)
        self.stats['log_entries_appended'] += 1

        # Update own match index
        self.match_index[self.node_id] = len(self.log)

    def replicate_log(self) -> None:
        """Replicate log to all followers (called by leader)."""
        if self.state != NodeState.LEADER:
            return

        for node_id in self.cluster_nodes:
            if node_id not in self.network:
                continue

            next_idx = self.next_index[node_id]
            prev_log_index = next_idx - 1
            prev_log_term = self.log[prev_log_index - 1].term if prev_log_index > 0 else 0

            # Get entries to send
            entries = self.log[next_idx - 1:] if next_idx <= len(self.log) else []

            request = AppendEntriesRequest(
                term=self.current_term,
                leader_id=self.node_id,
                prev_log_index=prev_log_index,
                prev_log_term=prev_log_term,
                entries=entries,
                leader_commit=self.commit_index
            )

            response = self.network[node_id].handle_append_entries(request)
            self._handle_append_entries_response(node_id, response, len(entries))

    def send_heartbeat(self) -> None:
        """Send heartbeat to all followers (empty AppendEntries)."""
        if self.state != NodeState.LEADER:
            return

        self.stats['heartbeats_sent'] += 1

        for node_id in self.cluster_nodes:
            if node_id not in self.network:
                continue

            prev_log_index = len(self.log)
            prev_log_term = self.log[-1].term if self.log else 0

            request = AppendEntriesRequest(
                term=self.current_term,
                leader_id=self.node_id,
                prev_log_index=prev_log_index,
                prev_log_term=prev_log_term,
                entries=[],
                leader_commit=self.commit_index
            )

            self.network[node_id].handle_append_entries(request)

    def handle_append_entries(self, request: AppendEntriesRequest) -> AppendEntriesResponse:
        """Handle incoming append entries request (heartbeat or log replication)."""
        self.stats['heartbeats_received'] += 1

        # Update term if request has higher term
        if request.term > self.current_term:
            self.become_follower(request.term, request.leader_id)
        elif request.term == self.current_term:
            if self.state == NodeState.CANDIDATE:
                self.become_follower(request.term, request.leader_id)
            else:
                self.leader_id = request.leader_id
                self.last_heartbeat = datetime.utcnow()

        # Reject if request term is outdated
        if request.term < self.current_term:
            return AppendEntriesResponse(
                term=self.current_term,
                success=False,
                match_index=0
            )

        # Reset election timeout
        self.last_heartbeat = datetime.utcnow()

        # Check if log contains entry at prevLogIndex with matching term
        if request.prev_log_index > 0:
            if request.prev_log_index > len(self.log):
                return AppendEntriesResponse(
                    term=self.current_term,
                    success=False,
                    match_index=len(self.log)
                )

            if self.log[request.prev_log_index - 1].term != request.prev_log_term:
                # Delete conflicting entries
                self.log = self.log[:request.prev_log_index - 1]
                return AppendEntriesResponse(
                    term=self.current_term,
                    success=False,
                    match_index=len(self.log)
                )

        # Append new entries
        if request.entries:
            # Remove any conflicting entries
            insert_index = request.prev_log_index
            for entry in request.entries:
                if insert_index < len(self.log):
                    if self.log[insert_index].term != entry.term:
                        self.log = self.log[:insert_index]
                        self.log.append(entry)
                    # Else entry already exists, skip
                else:
                    self.log.append(entry)
                insert_index += 1

        # Update commit index
        if request.leader_commit > self.commit_index:
            self.commit_index = min(request.leader_commit, len(self.log))
            self._apply_committed_entries()

        return AppendEntriesResponse(
            term=self.current_term,
            success=True,
            match_index=len(self.log)
        )

    def _handle_append_entries_response(self, node_id: str, response: AppendEntriesResponse,
                                        num_entries_sent: int) -> None:
        """Handle response to append entries request."""
        if response.term > self.current_term:
            self.become_follower(response.term)
            return

        if self.state != NodeState.LEADER:
            return

        if response.success:
            # Update next_index and match_index for follower
            self.match_index[node_id] = response.match_index
            self.next_index[node_id] = response.match_index + 1

            # Update commit index
            self._update_commit_index()
        else:
            # Decrement next_index and retry
            self.next_index[node_id] = max(1, response.match_index + 1)

    def _update_commit_index(self) -> None:
        """Update commit index based on majority replication."""
        # Find highest index replicated on majority of servers
        all_match_indices = [self.match_index[node] for node in self.cluster_nodes]
        all_match_indices.append(len(self.log))  # Include self
        all_match_indices.sort(reverse=True)

        # Median gives us the majority index
        majority_idx = len(all_match_indices) // 2
        new_commit_index = all_match_indices[majority_idx]

        # Only commit entries from current term
        if new_commit_index > self.commit_index:
            if new_commit_index <= len(self.log) and self.log[new_commit_index - 1].term == self.current_term:
                self.commit_index = new_commit_index
                self._apply_committed_entries()

    def _apply_committed_entries(self) -> None:
        """Apply committed log entries to state machine."""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]
            entry.committed = True

            if self.apply_callback and entry.entry_type != LogEntryType.NO_OP:
                self.apply_callback(entry)

    # ==================== Public API ====================

    def get_state(self) -> Dict[str, Any]:
        """Get current node state."""
        return {
            'node_id': self.node_id,
            'state': self.state.value,
            'term': self.current_term,
            'leader_id': self.leader_id,
            'log_size': len(self.log),
            'commit_index': self.commit_index,
            'last_applied': self.last_applied,
            'voted_for': self.voted_for,
            'stats': self.stats
        }

    def is_leader(self) -> bool:
        """Check if this node is the current leader."""
        return self.state == NodeState.LEADER

    def get_leader_id(self) -> Optional[str]:
        """Get the ID of the current leader."""
        return self.leader_id

    def get_log(self) -> List[LogEntry]:
        """Get the replicated log."""
        return self.log.copy()

    def get_committed_log(self) -> List[LogEntry]:
        """Get only the committed portion of the log."""
        return self.log[:self.commit_index]
