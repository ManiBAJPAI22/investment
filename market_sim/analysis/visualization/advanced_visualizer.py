"""
Advanced Consensus Benchmark Visualizer.

Generates comprehensive visualizations comparing all consensus mechanisms
across different dataset patterns.

Usage:
    python advanced_visualizer.py benchmark_results.json
    python advanced_visualizer.py benchmark_results.json --output ./charts
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import sys

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Install with: pip install matplotlib")


class AdvancedVisualizer:
    """Generate advanced visualizations for benchmark results."""

    def __init__(self, results_file: str, output_dir: str = None):
        """
        Initialize visualizer.

        Args:
            results_file: Path to benchmark results JSON
            output_dir: Directory to save charts (default: folder named after benchmark)
        """
        self.results_file = results_file
        self.results_path = Path(results_file)

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Extract benchmark identifier from filename
            # E.g., "benchmark_results_20251109_105436.json" -> "benchmark_20251109_105436"
            filename = self.results_path.stem  # Gets filename without extension
            if filename.startswith('benchmark_results_'):
                benchmark_id = filename.replace('benchmark_results_', 'benchmark_')
            else:
                benchmark_id = filename

            # Create folder in the same directory as the results file
            self.output_dir = self.results_path.parent / benchmark_id

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load results
        with open(results_file, 'r') as f:
            data = json.load(f)

        self.timestamp = data['timestamp']
        self.dataset_sizes = data['dataset_sizes']
        self.results = data['results']

        print(f"Loaded {len(self.results)} benchmark results from {results_file}")

    def plot_throughput_comparison(self):
        """Plot throughput comparison across consensus mechanisms and datasets."""
        if not MATPLOTLIB_AVAILABLE:
            print("Skipping throughput comparison (matplotlib not available)")
            return

        # Group by dataset type and consensus
        dataset_types = sorted(set(r['dataset_type'] for r in self.results))
        consensus_types = sorted(set(r['consensus_type'] for r in self.results))

        # Prepare data
        data = {ct: {dt: [] for dt in dataset_types} for ct in consensus_types}

        for result in self.results:
            ct = result['consensus_type']
            dt = result['dataset_type']
            throughput = result['throughput_tx_per_sec']
            data[ct][dt].append(throughput)

        # Calculate averages
        avg_data = {ct: {dt: np.mean(vals) if vals else 0
                        for dt, vals in datasets.items()}
                   for ct, datasets in data.items()}

        # Create plot
        fig, ax = plt.subplots(figsize=(14, 8))

        x = np.arange(len(dataset_types))
        width = 0.25

        colors = {'Raft': '#2ecc71', 'PoW': '#e74c3c', 'PoS': '#3498db'}

        for i, consensus_type in enumerate(consensus_types):
            values = [avg_data[consensus_type][dt] for dt in dataset_types]
            offset = width * (i - 1)
            bars = ax.bar(x + offset, values, width,
                         label=consensus_type,
                         color=colors.get(consensus_type, '#95a5a6'))

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.0f}',
                           ha='center', va='bottom', fontsize=9)

        ax.set_xlabel('Dataset Pattern', fontsize=12, fontweight='bold')
        ax.set_ylabel('Throughput (transactions/sec)', fontsize=12, fontweight='bold')
        ax.set_title('Consensus Mechanism Throughput Comparison\nAcross Different Trading Patterns',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(dataset_types, rotation=45, ha='right')
        ax.legend(loc='upper left', fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        plt.tight_layout()
        output_path = self.output_dir / 'throughput_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Saved throughput comparison to {output_path}")

    def plot_latency_comparison(self):
        """Plot latency comparison across consensus mechanisms."""
        if not MATPLOTLIB_AVAILABLE:
            print("Skipping latency comparison (matplotlib not available)")
            return

        dataset_types = sorted(set(r['dataset_type'] for r in self.results))
        consensus_types = sorted(set(r['consensus_type'] for r in self.results))

        # Prepare data
        data = {ct: {dt: [] for dt in dataset_types} for ct in consensus_types}

        for result in self.results:
            ct = result['consensus_type']
            dt = result['dataset_type']
            latency = result['avg_latency_ms']
            data[ct][dt].append(latency)

        # Calculate averages
        avg_data = {ct: {dt: np.mean(vals) if vals else 0
                        for dt, vals in datasets.items()}
                   for ct, datasets in data.items()}

        # Create plot
        fig, ax = plt.subplots(figsize=(14, 8))

        x = np.arange(len(dataset_types))
        width = 0.25

        colors = {'Raft': '#2ecc71', 'PoW': '#e74c3c', 'PoS': '#3498db'}

        for i, consensus_type in enumerate(consensus_types):
            values = [avg_data[consensus_type][dt] for dt in dataset_types]
            offset = width * (i - 1)
            bars = ax.bar(x + offset, values, width,
                         label=consensus_type,
                         color=colors.get(consensus_type, '#95a5a6'))

            # Add value labels
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.2f}',
                           ha='center', va='bottom', fontsize=9)

        ax.set_xlabel('Dataset Pattern', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Latency (milliseconds)', fontsize=12, fontweight='bold')
        ax.set_title('Consensus Mechanism Latency Comparison\nAcross Different Trading Patterns',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(dataset_types, rotation=45, ha='right')
        ax.legend(loc='upper left', fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        plt.tight_layout()
        output_path = self.output_dir / 'latency_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Saved latency comparison to {output_path}")

    def plot_success_rate_heatmap(self):
        """Plot success rate heatmap."""
        if not MATPLOTLIB_AVAILABLE:
            print("Skipping success rate heatmap (matplotlib not available)")
            return

        dataset_types = sorted(set(r['dataset_type'] for r in self.results))
        consensus_types = sorted(set(r['consensus_type'] for r in self.results))

        # Prepare data matrix
        data_matrix = np.zeros((len(consensus_types), len(dataset_types)))

        for i, ct in enumerate(consensus_types):
            for j, dt in enumerate(dataset_types):
                matching = [r for r in self.results
                           if r['consensus_type'] == ct and r['dataset_type'] == dt]
                if matching:
                    avg_success = np.mean([r['success_rate_percent'] for r in matching])
                    data_matrix[i, j] = avg_success

        # Create heatmap
        fig, ax = plt.subplots(figsize=(12, 6))

        im = ax.imshow(data_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

        # Set ticks
        ax.set_xticks(np.arange(len(dataset_types)))
        ax.set_yticks(np.arange(len(consensus_types)))
        ax.set_xticklabels(dataset_types, rotation=45, ha='right')
        ax.set_yticklabels(consensus_types)

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Success Rate (%)', rotation=270, labelpad=20, fontweight='bold')

        # Add text annotations
        for i in range(len(consensus_types)):
            for j in range(len(dataset_types)):
                value = data_matrix[i, j]
                color = 'white' if value < 50 else 'black'
                ax.text(j, i, f'{value:.1f}%',
                       ha='center', va='center', color=color, fontweight='bold')

        ax.set_title('Success Rate Heatmap\nConsensus Mechanisms vs Trading Patterns',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Dataset Pattern', fontsize=12, fontweight='bold')
        ax.set_ylabel('Consensus Mechanism', fontsize=12, fontweight='bold')

        plt.tight_layout()
        output_path = self.output_dir / 'success_rate_heatmap.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Saved success rate heatmap to {output_path}")

    def plot_performance_by_dataset_size(self):
        """Plot performance metrics by dataset size."""
        if not MATPLOTLIB_AVAILABLE:
            print("Skipping dataset size performance (matplotlib not available)")
            return

        consensus_types = sorted(set(r['consensus_type'] for r in self.results))

        # Group by consensus and size
        data = {ct: {'sizes': [], 'throughputs': []} for ct in consensus_types}

        for result in self.results:
            ct = result['consensus_type']
            size = result['dataset_size']
            throughput = result['throughput_tx_per_sec']

            data[ct]['sizes'].append(size)
            data[ct]['throughputs'].append(throughput)

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 7))

        colors = {'Raft': '#2ecc71', 'PoW': '#e74c3c', 'PoS': '#3498db'}
        markers = {'Raft': 'o', 'PoW': 's', 'PoS': '^'}

        for ct in consensus_types:
            sizes = data[ct]['sizes']
            throughputs = data[ct]['throughputs']

            # Sort by size
            sorted_pairs = sorted(zip(sizes, throughputs))
            if sorted_pairs:
                sizes, throughputs = zip(*sorted_pairs)

                ax.plot(sizes, throughputs,
                       marker=markers.get(ct, 'o'),
                       label=ct,
                       color=colors.get(ct, '#95a5a6'),
                       linewidth=2,
                       markersize=8,
                       alpha=0.7)

        ax.set_xlabel('Dataset Size (number of orders)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Throughput (transactions/sec)', fontsize=12, fontweight='bold')
        ax.set_title('Scalability Analysis\nThroughput vs Dataset Size',
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='best', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()
        output_path = self.output_dir / 'scalability_analysis.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Saved scalability analysis to {output_path}")

    def plot_performance_radar(self):
        """Plot radar chart comparing consensus mechanisms across metrics."""
        if not MATPLOTLIB_AVAILABLE:
            print("Skipping radar chart (matplotlib not available)")
            return

        consensus_types = sorted(set(r['consensus_type'] for r in self.results))

        # Calculate average metrics for each consensus type
        metrics = {}
        for ct in consensus_types:
            ct_results = [r for r in self.results if r['consensus_type'] == ct]

            metrics[ct] = {
                'Throughput': np.mean([r['throughput_tx_per_sec'] for r in ct_results]),
                'Success Rate': np.mean([r['success_rate_percent'] for r in ct_results]),
                'Low Latency': 100 - min(100, np.mean([r['avg_latency_ms'] for r in ct_results])),
            }

        # Normalize metrics to 0-100 scale
        max_throughput = max(m['Throughput'] for m in metrics.values())
        for ct in metrics:
            metrics[ct]['Throughput'] = (metrics[ct]['Throughput'] / max_throughput) * 100 if max_throughput > 0 else 0

        # Setup radar chart
        categories = ['Throughput', 'Success Rate', 'Low Latency']
        N = len(categories)

        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle

        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        colors = {'Raft': '#2ecc71', 'PoW': '#e74c3c', 'PoS': '#3498db'}

        for ct in consensus_types:
            values = [metrics[ct][cat] for cat in categories]
            values += values[:1]  # Complete the circle

            ax.plot(angles, values,
                   'o-', linewidth=2, label=ct,
                   color=colors.get(ct, '#95a5a6'))
            ax.fill(angles, values,
                   alpha=0.15, color=colors.get(ct, '#95a5a6'))

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=12, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.7)

        ax.set_title('Consensus Mechanism Performance Radar\n(Normalized Metrics)',
                    fontsize=14, fontweight='bold', pad=30, y=1.08)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)

        plt.tight_layout()
        output_path = self.output_dir / 'performance_radar.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Saved performance radar to {output_path}")

    def plot_detailed_breakdown(self):
        """Plot detailed breakdown for each consensus mechanism."""
        if not MATPLOTLIB_AVAILABLE:
            print("Skipping detailed breakdown (matplotlib not available)")
            return

        consensus_types = sorted(set(r['consensus_type'] for r in self.results))

        for ct in consensus_types:
            ct_results = [r for r in self.results if r['consensus_type'] == ct]

            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'{ct} Consensus - Detailed Performance Breakdown',
                        fontsize=16, fontweight='bold')

            # 1. Throughput by dataset type
            dataset_types = sorted(set(r['dataset_type'] for r in ct_results))
            throughputs = [np.mean([r['throughput_tx_per_sec'] for r in ct_results
                                   if r['dataset_type'] == dt]) for dt in dataset_types]

            ax1.barh(dataset_types, throughputs, color='#3498db', alpha=0.7)
            ax1.set_xlabel('Throughput (tx/sec)', fontweight='bold')
            ax1.set_title('Throughput by Dataset Pattern', fontweight='bold')
            ax1.grid(axis='x', alpha=0.3)

            # 2. Latency distribution
            latencies = [r['avg_latency_ms'] for r in ct_results]
            ax2.hist(latencies, bins=15, color='#e74c3c', alpha=0.7, edgecolor='black')
            ax2.set_xlabel('Latency (ms)', fontweight='bold')
            ax2.set_ylabel('Frequency', fontweight='bold')
            ax2.set_title('Latency Distribution', fontweight='bold')
            ax2.grid(axis='y', alpha=0.3)

            # 3. Processing time vs dataset size
            sizes = [r['dataset_size'] for r in ct_results]
            durations = [r['duration_seconds'] for r in ct_results]
            ax3.scatter(sizes, durations, alpha=0.6, s=100, c='#2ecc71')
            ax3.set_xlabel('Dataset Size (orders)', fontweight='bold')
            ax3.set_ylabel('Processing Time (seconds)', fontweight='bold')
            ax3.set_title('Processing Time vs Dataset Size', fontweight='bold')
            ax3.grid(True, alpha=0.3)

            # 4. Success rates
            success_rates = [r['success_rate_percent'] for r in ct_results]
            ax4.boxplot(success_rates, vert=True)
            ax4.set_ylabel('Success Rate (%)', fontweight='bold')
            ax4.set_title('Success Rate Distribution', fontweight='bold')
            ax4.grid(axis='y', alpha=0.3)
            ax4.set_xticklabels([ct])

            plt.tight_layout()
            output_path = self.output_dir / f'{ct.lower()}_detailed_breakdown.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            print(f"✓ Saved {ct} detailed breakdown to {output_path}")

    def generate_text_report(self):
        """Generate comprehensive text report."""
        output_path = self.output_dir / 'benchmark_report.txt'

        with open(output_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("COMPREHENSIVE CONSENSUS MECHANISM BENCHMARK REPORT\n")
            f.write("="*80 + "\n\n")

            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Dataset Sizes: {self.dataset_sizes}\n")
            f.write(f"Total Tests: {len(self.results)}\n\n")

            # Group by consensus type
            consensus_types = sorted(set(r['consensus_type'] for r in self.results))

            for ct in consensus_types:
                ct_results = [r for r in self.results if r['consensus_type'] == ct]

                f.write("="*80 + "\n")
                f.write(f"{ct} CONSENSUS MECHANISM\n")
                f.write("="*80 + "\n\n")

                f.write(f"Tests Run: {len(ct_results)}\n\n")

                # Overall statistics
                avg_throughput = np.mean([r['throughput_tx_per_sec'] for r in ct_results])
                max_throughput = max(r['throughput_tx_per_sec'] for r in ct_results)
                min_throughput = min(r['throughput_tx_per_sec'] for r in ct_results)
                avg_latency = np.mean([r['avg_latency_ms'] for r in ct_results])
                avg_success = np.mean([r['success_rate_percent'] for r in ct_results])

                f.write("OVERALL STATISTICS:\n")
                f.write(f"  Average Throughput: {avg_throughput:.2f} tx/sec\n")
                f.write(f"  Max Throughput: {max_throughput:.2f} tx/sec\n")
                f.write(f"  Min Throughput: {min_throughput:.2f} tx/sec\n")
                f.write(f"  Average Latency: {avg_latency:.3f} ms\n")
                f.write(f"  Average Success Rate: {avg_success:.2f}%\n\n")

                # Per-dataset breakdown
                dataset_types = sorted(set(r['dataset_type'] for r in ct_results))

                f.write("PERFORMANCE BY DATASET PATTERN:\n\n")

                for dt in dataset_types:
                    dt_results = [r for r in ct_results if r['dataset_type'] == dt]

                    dt_avg_throughput = np.mean([r['throughput_tx_per_sec'] for r in dt_results])
                    dt_avg_latency = np.mean([r['avg_latency_ms'] for r in dt_results])
                    dt_avg_success = np.mean([r['success_rate_percent'] for r in dt_results])

                    f.write(f"  {dt}:\n")
                    f.write(f"    Throughput: {dt_avg_throughput:.2f} tx/sec\n")
                    f.write(f"    Latency: {dt_avg_latency:.3f} ms\n")
                    f.write(f"    Success Rate: {dt_avg_success:.2f}%\n\n")

            # Comparison summary
            f.write("="*80 + "\n")
            f.write("CONSENSUS MECHANISM COMPARISON\n")
            f.write("="*80 + "\n\n")

            # Winner by throughput
            throughput_by_consensus = {
                ct: np.mean([r['throughput_tx_per_sec']
                           for r in self.results if r['consensus_type'] == ct])
                for ct in consensus_types
            }
            winner = max(throughput_by_consensus, key=throughput_by_consensus.get)

            f.write(f"HIGHEST THROUGHPUT: {winner} ({throughput_by_consensus[winner]:.2f} tx/sec)\n\n")

            # Best for each dataset pattern
            dataset_types = sorted(set(r['dataset_type'] for r in self.results))

            f.write("BEST CONSENSUS FOR EACH PATTERN:\n\n")

            for dt in dataset_types:
                dt_throughputs = {
                    ct: np.mean([r['throughput_tx_per_sec']
                               for r in self.results
                               if r['consensus_type'] == ct and r['dataset_type'] == dt])
                    for ct in consensus_types
                }
                best = max(dt_throughputs, key=dt_throughputs.get)
                f.write(f"  {dt}: {best} ({dt_throughputs[best]:.2f} tx/sec)\n")

            f.write("\n" + "="*80 + "\n")
            f.write("END OF REPORT\n")
            f.write("="*80 + "\n")

        print(f"✓ Saved text report to {output_path}")

    def generate_all_visualizations(self):
        """Generate all visualizations and reports."""
        print("\n" + "="*80)
        print("GENERATING VISUALIZATIONS")
        print("="*80 + "\n")

        if not MATPLOTLIB_AVAILABLE:
            print("⚠ matplotlib not available - only text report will be generated")
            print("Install matplotlib with: pip install matplotlib\n")

        # Generate all plots
        self.plot_throughput_comparison()
        self.plot_latency_comparison()
        self.plot_success_rate_heatmap()
        self.plot_performance_by_dataset_size()
        self.plot_performance_radar()
        self.plot_detailed_breakdown()

        # Generate text report
        self.generate_text_report()

        print("\n" + "="*80)
        print("VISUALIZATION COMPLETE")
        print("="*80)
        print(f"All files saved to: {self.output_dir}")
        print("="*80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate advanced visualizations for consensus benchmarks'
    )
    parser.add_argument('results_file', type=str,
                       help='Path to benchmark results JSON file')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output directory for charts (default: same as results file)')

    args = parser.parse_args()

    # Check if results file exists
    if not Path(args.results_file).exists():
        print(f"Error: Results file not found: {args.results_file}")
        sys.exit(1)

    # Generate visualizations
    visualizer = AdvancedVisualizer(args.results_file, args.output)
    visualizer.generate_all_visualizations()


if __name__ == '__main__':
    main()
