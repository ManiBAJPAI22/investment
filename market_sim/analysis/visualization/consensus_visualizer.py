"""
Visualization tools for Raft consensus algorithm.

Provides visualizations for:
- Leader election process
- Node states over time
- Log replication and commit progress
- Consensus statistics and metrics
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from blockchain.consensus.raft_node import RaftNode, NodeState
from blockchain.consensus.distributed_orderbook import DistributedOrderBook


@dataclass
class NodeStateSnapshot:
    """Snapshot of a node's state at a point in time."""
    timestamp: datetime
    node_id: str
    state: NodeState
    term: int
    leader_id: Optional[str]
    log_size: int
    commit_index: int


class ConsensusVisualizer:
    """
    Visualizer for Raft consensus algorithm.

    Provides various visualization methods to understand and debug
    the consensus algorithm behavior.
    """

    def __init__(self):
        """Initialize the consensus visualizer."""
        self.state_history: List[NodeStateSnapshot] = []
        self.state_colors = {
            NodeState.FOLLOWER: '#3498db',    # Blue
            NodeState.CANDIDATE: '#f39c12',   # Orange
            NodeState.LEADER: '#2ecc71'       # Green
        }

    def record_state(self, nodes: Dict[str, RaftNode]) -> None:
        """
        Record the current state of all nodes.

        Args:
            nodes: Dictionary mapping node IDs to RaftNode instances
        """
        timestamp = datetime.utcnow()
        for node_id, node in nodes.items():
            snapshot = NodeStateSnapshot(
                timestamp=timestamp,
                node_id=node_id,
                state=node.state,
                term=node.current_term,
                leader_id=node.leader_id,
                log_size=len(node.log),
                commit_index=node.commit_index
            )
            self.state_history.append(snapshot)

    def plot_state_timeline(self, output_file: Optional[str] = None) -> None:
        """
        Plot the state of all nodes over time.

        Args:
            output_file: Optional file path to save the plot
        """
        if not self.state_history:
            print("No state history to plot")
            return

        # Get unique node IDs
        node_ids = sorted(list(set(s.node_id for s in self.state_history)))

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))

        # Group snapshots by node
        node_snapshots = {node_id: [] for node_id in node_ids}
        for snapshot in self.state_history:
            node_snapshots[snapshot.node_id].append(snapshot)

        # Plot state for each node
        for idx, node_id in enumerate(node_ids):
            snapshots = node_snapshots[node_id]

            for i in range(len(snapshots) - 1):
                start_time = (snapshots[i].timestamp - self.state_history[0].timestamp).total_seconds()
                end_time = (snapshots[i + 1].timestamp - self.state_history[0].timestamp).total_seconds()

                color = self.state_colors[snapshots[i].state]
                ax.barh(idx, end_time - start_time, left=start_time, height=0.8,
                       color=color, edgecolor='black', linewidth=0.5)

        # Formatting
        ax.set_yticks(range(len(node_ids)))
        ax.set_yticklabels(node_ids)
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Node ID', fontsize=12)
        ax.set_title('Raft Consensus - Node States Over Time', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)

        # Legend
        legend_elements = [
            mpatches.Patch(color=self.state_colors[NodeState.FOLLOWER], label='Follower'),
            mpatches.Patch(color=self.state_colors[NodeState.CANDIDATE], label='Candidate'),
            mpatches.Patch(color=self.state_colors[NodeState.LEADER], label='Leader')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

        plt.tight_layout()

        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Saved state timeline to {output_file}")
        else:
            plt.show()

    def plot_term_progression(self, output_file: Optional[str] = None) -> None:
        """
        Plot the term progression across all nodes.

        Args:
            output_file: Optional file path to save the plot
        """
        if not self.state_history:
            print("No state history to plot")
            return

        # Get unique node IDs
        node_ids = sorted(list(set(s.node_id for s in self.state_history)))

        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot term for each node
        for node_id in node_ids:
            node_snapshots = [s for s in self.state_history if s.node_id == node_id]
            times = [(s.timestamp - self.state_history[0].timestamp).total_seconds()
                    for s in node_snapshots]
            terms = [s.term for s in node_snapshots]

            ax.plot(times, terms, marker='o', label=node_id, linewidth=2, markersize=4)

        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Term', fontsize=12)
        ax.set_title('Raft Consensus - Term Progression', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(alpha=0.3)

        plt.tight_layout()

        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Saved term progression to {output_file}")
        else:
            plt.show()

    def plot_log_replication(self, output_file: Optional[str] = None) -> None:
        """
        Plot log size and commit index progression.

        Args:
            output_file: Optional file path to save the plot
        """
        if not self.state_history:
            print("No state history to plot")
            return

        node_ids = sorted(list(set(s.node_id for s in self.state_history)))

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Plot log size
        for node_id in node_ids:
            node_snapshots = [s for s in self.state_history if s.node_id == node_id]
            times = [(s.timestamp - self.state_history[0].timestamp).total_seconds()
                    for s in node_snapshots]
            log_sizes = [s.log_size for s in node_snapshots]

            ax1.plot(times, log_sizes, marker='o', label=node_id, linewidth=2, markersize=4)

        ax1.set_xlabel('Time (seconds)', fontsize=11)
        ax1.set_ylabel('Log Size', fontsize=11)
        ax1.set_title('Log Replication - Log Size Over Time', fontsize=12, fontweight='bold')
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(alpha=0.3)

        # Plot commit index
        for node_id in node_ids:
            node_snapshots = [s for s in self.state_history if s.node_id == node_id]
            times = [(s.timestamp - self.state_history[0].timestamp).total_seconds()
                    for s in node_snapshots]
            commit_indices = [s.commit_index for s in node_snapshots]

            ax2.plot(times, commit_indices, marker='s', label=node_id, linewidth=2, markersize=4)

        ax2.set_xlabel('Time (seconds)', fontsize=11)
        ax2.set_ylabel('Commit Index', fontsize=11)
        ax2.set_title('Log Replication - Commit Progress Over Time', fontsize=12, fontweight='bold')
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(alpha=0.3)

        plt.tight_layout()

        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Saved log replication plot to {output_file}")
        else:
            plt.show()

    def plot_leader_elections(self, output_file: Optional[str] = None) -> None:
        """
        Plot leader election events over time.

        Args:
            output_file: Optional file path to save the plot
        """
        if not self.state_history:
            print("No state history to plot")
            return

        # Find leader changes
        leader_changes = []
        current_leader = None

        for snapshot in self.state_history:
            if snapshot.state == NodeState.LEADER and snapshot.node_id != current_leader:
                leader_changes.append({
                    'time': (snapshot.timestamp - self.state_history[0].timestamp).total_seconds(),
                    'leader': snapshot.node_id,
                    'term': snapshot.term
                })
                current_leader = snapshot.node_id

        if not leader_changes:
            print("No leader elections found in history")
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot leader changes as vertical lines
        for i, change in enumerate(leader_changes):
            color = plt.cm.Set3(i % 12)
            ax.axvline(x=change['time'], color=color, linestyle='--', linewidth=2,
                      label=f"Term {change['term']}: {change['leader']}")
            ax.text(change['time'], i * 0.1, f"Term {change['term']}",
                   rotation=90, verticalalignment='bottom', fontsize=9)

        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_title('Raft Consensus - Leader Election Events', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=9, ncol=2)
        ax.set_yticks([])
        ax.grid(axis='x', alpha=0.3)

        plt.tight_layout()

        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Saved leader elections plot to {output_file}")
        else:
            plt.show()

    def plot_statistics(self, nodes: Dict[str, RaftNode], output_file: Optional[str] = None) -> None:
        """
        Plot consensus statistics for all nodes.

        Args:
            nodes: Dictionary mapping node IDs to RaftNode instances
            output_file: Optional file path to save the plot
        """
        node_ids = sorted(nodes.keys())

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        # Elections started
        elections_started = [nodes[nid].stats['elections_started'] for nid in node_ids]
        ax1.bar(node_ids, elections_started, color='#3498db', edgecolor='black')
        ax1.set_ylabel('Count', fontsize=11)
        ax1.set_title('Elections Started', fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)

        # Elections won
        elections_won = [nodes[nid].stats['elections_won'] for nid in node_ids]
        ax2.bar(node_ids, elections_won, color='#2ecc71', edgecolor='black')
        ax2.set_ylabel('Count', fontsize=11)
        ax2.set_title('Elections Won', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)

        # Heartbeats sent
        heartbeats_sent = [nodes[nid].stats['heartbeats_sent'] for nid in node_ids]
        ax3.bar(node_ids, heartbeats_sent, color='#e74c3c', edgecolor='black')
        ax3.set_ylabel('Count', fontsize=11)
        ax3.set_xlabel('Node ID', fontsize=11)
        ax3.set_title('Heartbeats Sent', fontsize=12, fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)

        # Log entries appended
        log_entries = [nodes[nid].stats['log_entries_appended'] for nid in node_ids]
        ax4.bar(node_ids, log_entries, color='#9b59b6', edgecolor='black')
        ax4.set_ylabel('Count', fontsize=11)
        ax4.set_xlabel('Node ID', fontsize=11)
        ax4.set_title('Log Entries Appended', fontsize=12, fontweight='bold')
        ax4.grid(axis='y', alpha=0.3)

        plt.suptitle('Raft Consensus - Node Statistics', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()

        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Saved statistics plot to {output_file}")
        else:
            plt.show()

    def plot_distributed_orderbook_stats(self, nodes: Dict[str, DistributedOrderBook],
                                         output_file: Optional[str] = None) -> None:
        """
        Plot distributed order book statistics.

        Args:
            nodes: Dictionary mapping node IDs to DistributedOrderBook instances
            output_file: Optional file path to save the plot
        """
        node_ids = sorted(nodes.keys())

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        # Orders submitted
        orders_submitted = [nodes[nid].stats['orders_submitted'] for nid in node_ids]
        ax1.bar(node_ids, orders_submitted, color='#3498db', edgecolor='black')
        ax1.set_ylabel('Count', fontsize=11)
        ax1.set_title('Orders Submitted', fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)

        # Orders committed
        orders_committed = [nodes[nid].stats['orders_committed'] for nid in node_ids]
        ax2.bar(node_ids, orders_committed, color='#2ecc71', edgecolor='black')
        ax2.set_ylabel('Count', fontsize=11)
        ax2.set_title('Orders Committed', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)

        # Orders rejected
        orders_rejected = [nodes[nid].stats['orders_rejected'] for nid in node_ids]
        ax3.bar(node_ids, orders_rejected, color='#e74c3c', edgecolor='black')
        ax3.set_ylabel('Count', fontsize=11)
        ax3.set_xlabel('Node ID', fontsize=11)
        ax3.set_title('Orders Rejected', fontsize=12, fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)

        # Trades executed
        trades_executed = [nodes[nid].stats['trades_executed'] for nid in node_ids]
        ax4.bar(node_ids, trades_executed, color='#f39c12', edgecolor='black')
        ax4.set_ylabel('Count', fontsize=11)
        ax4.set_xlabel('Node ID', fontsize=11)
        ax4.set_title('Trades Executed', fontsize=12, fontweight='bold')
        ax4.grid(axis='y', alpha=0.3)

        plt.suptitle('Distributed Order Book - Statistics', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()

        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Saved distributed order book statistics to {output_file}")
        else:
            plt.show()

    def generate_all_plots(self, nodes: Dict[str, RaftNode],
                          output_dir: str = '.') -> None:
        """
        Generate all visualization plots.

        Args:
            nodes: Dictionary mapping node IDs to RaftNode instances
            output_dir: Directory to save plots
        """
        import os
        os.makedirs(output_dir, exist_ok=True)

        print("Generating all consensus visualizations...")

        self.plot_state_timeline(f"{output_dir}/state_timeline.png")
        self.plot_term_progression(f"{output_dir}/term_progression.png")
        self.plot_log_replication(f"{output_dir}/log_replication.png")
        self.plot_leader_elections(f"{output_dir}/leader_elections.png")
        self.plot_statistics(nodes, f"{output_dir}/node_statistics.png")

        print(f"All visualizations saved to {output_dir}/")

    def clear_history(self) -> None:
        """Clear the recorded state history."""
        self.state_history.clear()


def create_consensus_animation(nodes: Dict[str, RaftNode],
                               interval: int = 100,
                               frames: int = 100) -> FuncAnimation:
    """
    Create an animated visualization of the consensus algorithm.

    Args:
        nodes: Dictionary mapping node IDs to RaftNode instances
        interval: Milliseconds between frames
        frames: Number of frames to generate

    Returns:
        Animation object
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    visualizer = ConsensusVisualizer()

    def update(frame):
        ax.clear()

        # Record state
        visualizer.record_state(nodes)

        # Simulate some consensus activity
        for node in nodes.values():
            node.check_election_timeout()
            if node.is_leader():
                node.send_heartbeat()

        # Plot current state
        node_ids = list(nodes.keys())
        states = [nodes[nid].state.value for nid in node_ids]
        colors = [visualizer.state_colors[nodes[nid].state] for nid in node_ids]

        ax.bar(node_ids, [1] * len(node_ids), color=colors, edgecolor='black', linewidth=2)
        ax.set_ylim(0, 1.5)
        ax.set_ylabel('State', fontsize=12)
        ax.set_title(f'Raft Consensus - Frame {frame}', fontsize=14, fontweight='bold')

        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#3498db', label='Follower'),
            Patch(facecolor='#f39c12', label='Candidate'),
            Patch(facecolor='#2ecc71', label='Leader')
        ]
        ax.legend(handles=legend_elements, loc='upper right')

    anim = FuncAnimation(fig, update, frames=frames, interval=interval, repeat=True)
    return anim
