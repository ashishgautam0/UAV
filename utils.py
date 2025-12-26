"""
Utility functions for visualization and result analysis
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import json
from datetime import datetime


def plot_convergence(convergence_data, algorithm_names, title="Fitness Convergence"):
    """
    Plot convergence curves for multiple algorithms

    Args:
        convergence_data: List of convergence histories (one per algorithm)
        algorithm_names: List of algorithm names
        title: Plot title
    """
    plt.figure(figsize=(12, 8))

    # Define colors for algorithms
    colors = {
        'Jaya': '#1f77b4',  # Blue
        'GWO': '#2ca02c',   # Green
        'GA': '#ff7f0e',    # Orange
        'WOA': '#9467bd',   # Purple
        'DE': '#8c564b',    # Brown
        'ALO': '#17becf',   # Cyan
        'ACO': '#ff7f0e'    # Orange (if ACO is used)
    }

    for history, name in zip(convergence_data, algorithm_names):
        color = colors.get(name, None)
        plt.plot(history, label=name, linewidth=2.5, color=color)

    plt.xlabel('Iteration', fontsize=16)
    plt.ylabel('Fitness Value', fontsize=16)
    plt.title(title, fontsize=20, fontweight='bold')
    plt.legend(fontsize=14, loc='best')
    plt.grid(True, alpha=0.2, linestyle='--')
    plt.tick_params(labelsize=14)

    # Set x-axis limits to show full range
    max_iterations = max(len(h) for h in convergence_data)
    plt.xlim(0, max_iterations - 1)

    plt.tight_layout()

    # Save figure
    filename = "fitness_convergence.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Convergence plot saved as: {filename}")

    plt.show()


def plot_allocation_distribution(allocation_stats, algorithm_names, title="Task Allocation Distribution"):
    """
    Plot task allocation distribution across execution locations

    Args:
        allocation_stats: List of allocation statistics dictionaries
        algorithm_names: List of algorithm names
        title: Plot title
    """
    locations = ['Local', 'GBS', 'MEC', 'Cloud']
    x = np.arange(len(algorithm_names))
    width = 0.2

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, loc in enumerate(['local_pct', 'gbs_pct', 'mec_pct', 'cloud_pct']):
        values = [stats[loc] for stats in allocation_stats]
        ax.bar(x + i * width, values, width, label=locations[i])

    ax.set_xlabel('Algorithm', fontsize=12)
    ax.set_ylabel('Percentage of Tasks (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(algorithm_names)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # Save figure
    filename = f"allocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Allocation plot saved as: {filename}")

    plt.show()


def plot_energy_breakdown(energy_breakdowns, algorithm_names, title="Energy Consumption Breakdown"):
    """
    Plot energy consumption breakdown by execution location

    Args:
        energy_breakdowns: List of energy breakdown dictionaries
        algorithm_names: List of algorithm names
        title: Plot title
    """
    locations = ['local', 'gbs', 'mec', 'cloud']
    location_labels = ['Local', 'GBS', 'MEC', 'Cloud']

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(algorithm_names))
    width = 0.2

    for i, loc in enumerate(locations):
        values = [breakdown[loc] for breakdown in energy_breakdowns]
        ax.bar(x + i * width, values, width, label=location_labels[i])

    ax.set_xlabel('Algorithm', fontsize=12)
    ax.set_ylabel('Energy Consumption (J)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(algorithm_names)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # Save figure
    filename = f"energy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Energy breakdown plot saved as: {filename}")

    plt.show()


def plot_comparison_table(results_dict, algorithm_names):
    """
    Create a comparison table of algorithm performance

    Args:
        results_dict: Dictionary with results for each algorithm
        algorithm_names: List of algorithm names
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis('tight')
    ax.axis('off')

    # Prepare table data
    headers = ['Algorithm', 'Best Fitness', 'Energy (J)', 'Load Imbalance',
               'Local %', 'GBS %', 'MEC %', 'Cloud %']

    table_data = []
    for name in algorithm_names:
        results = results_dict[name]
        detailed = results['detailed_fitness']
        stats = results['allocation_stats']

        row = [
            name,
            f"{results['best_fitness']:.6f}",
            f"{detailed['energy']:.2f}",
            f"{detailed['load_imbalance']:.4f}",
            f"{stats['local_pct']:.1f}",
            f"{stats['gbs_pct']:.1f}",
            f"{stats['mec_pct']:.1f}",
            f"{stats['cloud_pct']:.1f}"
        ]
        table_data.append(row)

    # Create table
    table = ax.table(cellText=table_data, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Style header
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Alternate row colors
    for i in range(1, len(table_data) + 1):
        for j in range(len(headers)):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')

    plt.title('Algorithm Performance Comparison', fontsize=14, fontweight='bold', pad=20)

    # Save figure
    filename = f"comparison_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Comparison table saved as: {filename}")

    plt.show()


def save_results_to_json(results_dict, filename=None):
    """
    Save algorithm results to JSON file

    Args:
        results_dict: Dictionary with results for each algorithm
        filename: Output filename (auto-generated if None)
    """
    if filename is None:
        filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Convert numpy arrays to lists for JSON serialization
    json_results = {}
    for algo_name, results in results_dict.items():
        json_results[algo_name] = {
            'best_fitness': float(results['best_fitness']),
            'detailed_fitness': {
                k: float(v) if isinstance(v, (np.floating, float)) else v
                for k, v in results['detailed_fitness'].items()
            },
            'allocation_stats': {
                k: int(v) if 'count' in k else float(v)
                for k, v in results['allocation_stats'].items()
            },
            'energy_breakdown': {
                k: float(v) for k, v in results['energy_breakdown'].items()
            },
            'convergence_history': [float(x) for x in results['convergence_history']],
            'num_iterations': int(results['num_iterations']),
            'population_size': int(results['population_size'])
        }

    with open(filename, 'w') as f:
        json.dump(json_results, f, indent=2)

    print(f"Results saved to: {filename}")
    return filename


def print_summary_table(results_dict, algorithm_names):
    """
    Print a formatted summary table to console

    Args:
        results_dict: Dictionary with results for each algorithm
        algorithm_names: List of algorithm names
    """
    print("\n" + "=" * 100)
    print("ALGORITHM PERFORMANCE COMPARISON")
    print("=" * 100)

    # Header
    print(f"{'Algorithm':<12} {'Fitness':>12} {'Energy (J)':>12} {'Load Imb.':>12} "
          f"{'Local %':>10} {'GBS %':>10} {'MEC %':>10} {'Cloud %':>10}")
    print("-" * 100)

    # Data rows
    for name in algorithm_names:
        results = results_dict[name]
        detailed = results['detailed_fitness']
        stats = results['allocation_stats']

        print(f"{name:<12} {results['best_fitness']:>12.6f} {detailed['energy']:>12.2f} "
              f"{detailed['load_imbalance']:>12.4f} {stats['local_pct']:>10.1f} "
              f"{stats['gbs_pct']:>10.1f} {stats['mec_pct']:>10.1f} {stats['cloud_pct']:>10.1f}")

    print("=" * 100)

    # Find best algorithm for each metric
    best_fitness_algo = min(algorithm_names, key=lambda x: results_dict[x]['best_fitness'])
    best_energy_algo = min(algorithm_names, key=lambda x: results_dict[x]['detailed_fitness']['energy'])
    best_balance_algo = min(algorithm_names, key=lambda x: results_dict[x]['detailed_fitness']['load_imbalance'])

    print(f"\nBest overall fitness: {best_fitness_algo}")
    print(f"Best energy efficiency: {best_energy_algo}")
    print(f"Best load balance: {best_balance_algo}")
    print("=" * 100 + "\n")


def plot_all_results(results_dict, algorithm_names, prefix=""):
    """
    Generate all visualization plots

    Args:
        results_dict: Dictionary with results for each algorithm
        algorithm_names: List of algorithm names
        prefix: Prefix for output filenames (e.g., "quick_test", "full_simulation")
    """
    # Extract data
    convergence_data = [results_dict[name]['convergence_history'] for name in algorithm_names]
    energy_data = [results_dict[name]['energy_history'] for name in algorithm_names]
    load_imbalance_data = [results_dict[name]['load_imbalance_history'] for name in algorithm_names]
    allocation_stats = [results_dict[name]['allocation_stats'] for name in algorithm_names]
    energy_breakdowns = [results_dict[name]['energy_breakdown'] for name in algorithm_names]

    # Create plots with prefix
    plot_convergence_with_prefix(convergence_data, algorithm_names, prefix, title="Fitness Convergence")
    plot_energy_convergence_with_prefix(energy_data, algorithm_names, prefix)
    plot_load_imbalance_convergence_with_prefix(load_imbalance_data, algorithm_names, prefix)
    plot_allocation_distribution_with_prefix(allocation_stats, algorithm_names, prefix)
    plot_energy_breakdown_with_prefix(energy_breakdowns, algorithm_names, prefix)
    plot_comparison_table_with_prefix(results_dict, algorithm_names, prefix)


def plot_convergence_with_prefix(convergence_data, algorithm_names, prefix="", title="Fitness Convergence"):
    """Plot convergence curves with custom filename prefix"""
    plt.figure(figsize=(12, 8))

    colors = {
        'Jaya': '#1f77b4', 'GWO': '#2ca02c',
        'GA': '#ff7f0e', 'WOA': '#9467bd', 'DE': '#8c564b',
        'ACO': '#e377c2', 'ALO': '#17becf'
    }

    for history, name in zip(convergence_data, algorithm_names):
        color = colors.get(name, None)
        plt.plot(history, label=name, linewidth=2.5, color=color)

    plt.xlabel('Iteration', fontsize=16)
    plt.ylabel('Fitness Value', fontsize=16)
    plt.title(title, fontsize=20, fontweight='bold')
    plt.legend(fontsize=14, loc='best')
    plt.grid(True, alpha=0.2, linestyle='--')
    plt.tick_params(labelsize=14)

    max_iterations = max(len(h) for h in convergence_data)
    plt.xlim(0, max_iterations - 1)
    plt.tight_layout()

    filename = f"{prefix}_fitness_convergence.png" if prefix else "fitness_convergence.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Convergence plot saved as: {filename}")
    plt.close()


def plot_energy_convergence_with_prefix(energy_data, algorithm_names, prefix="", title="Energy Convergence"):
    """Plot energy convergence curves with custom filename prefix"""
    plt.figure(figsize=(12, 8))

    colors = {
        'Jaya': '#1f77b4', 'GWO': '#2ca02c',
        'GA': '#ff7f0e', 'WOA': '#9467bd', 'DE': '#8c564b',
        'ACO': '#e377c2', 'ALO': '#17becf'
    }

    for history, name in zip(energy_data, algorithm_names):
        if len(history) > 0:  # Only plot if history exists
            color = colors.get(name, None)
            plt.plot(history, label=name, linewidth=2.5, color=color)

    plt.xlabel('Iteration', fontsize=16)
    plt.ylabel('Energy Consumption (J)', fontsize=16)
    plt.title(title, fontsize=20, fontweight='bold')
    plt.legend(fontsize=14, loc='best')
    plt.grid(True, alpha=0.2, linestyle='--')
    plt.tick_params(labelsize=14)

    max_iterations = max(len(h) for h in energy_data if len(h) > 0)
    plt.xlim(0, max_iterations - 1)
    plt.tight_layout()

    filename = f"{prefix}_energy_convergence.png" if prefix else "energy_convergence.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Energy convergence plot saved as: {filename}")
    plt.close()


def plot_load_imbalance_convergence_with_prefix(load_imbalance_data, algorithm_names, prefix="", title="Load Imbalance Convergence"):
    """Plot load imbalance convergence curves with custom filename prefix"""
    plt.figure(figsize=(12, 8))

    colors = {
        'Jaya': '#1f77b4', 'GWO': '#2ca02c',
        'GA': '#ff7f0e', 'WOA': '#9467bd', 'DE': '#8c564b',
        'ACO': '#e377c2', 'ALO': '#17becf'
    }

    for history, name in zip(load_imbalance_data, algorithm_names):
        if len(history) > 0:  # Only plot if history exists
            color = colors.get(name, None)
            plt.plot(history, label=name, linewidth=2.5, color=color)

    plt.xlabel('Iteration', fontsize=16)
    plt.ylabel('Load Imbalance (Std. Deviation)', fontsize=16)
    plt.title(title, fontsize=20, fontweight='bold')
    plt.legend(fontsize=14, loc='best')
    plt.grid(True, alpha=0.2, linestyle='--')
    plt.tick_params(labelsize=14)

    max_iterations = max(len(h) for h in load_imbalance_data if len(h) > 0)
    plt.xlim(0, max_iterations - 1)
    plt.tight_layout()

    filename = f"{prefix}_load_imbalance_convergence.png" if prefix else "load_imbalance_convergence.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Load imbalance convergence plot saved as: {filename}")
    plt.close()


def plot_allocation_distribution_with_prefix(allocation_stats, algorithm_names, prefix="", title="Task Allocation Distribution"):
    """Plot allocation distribution with custom filename prefix"""
    locations = ['Local', 'GBS', 'MEC', 'Cloud']
    x = np.arange(len(algorithm_names))
    width = 0.2

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, loc in enumerate(['local_pct', 'gbs_pct', 'mec_pct', 'cloud_pct']):
        values = [stats[loc] for stats in allocation_stats]
        ax.bar(x + i * width, values, width, label=locations[i])

    ax.set_xlabel('Algorithm', fontsize=12)
    ax.set_ylabel('Percentage of Tasks (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(algorithm_names)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()

    filename = f"{prefix}_allocation.png" if prefix else f"allocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Allocation plot saved as: {filename}")
    plt.close()


def plot_energy_breakdown_with_prefix(energy_breakdowns, algorithm_names, prefix="", title="Energy Consumption Breakdown"):
    """Plot energy breakdown with custom filename prefix"""
    locations = ['local', 'gbs', 'mec', 'cloud']
    location_labels = ['Local', 'GBS', 'MEC', 'Cloud']

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(algorithm_names))
    width = 0.2

    for i, loc in enumerate(locations):
        values = [breakdown[loc] for breakdown in energy_breakdowns]
        ax.bar(x + i * width, values, width, label=location_labels[i])

    ax.set_xlabel('Algorithm', fontsize=12)
    ax.set_ylabel('Energy Consumption (J)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(algorithm_names)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()

    filename = f"{prefix}_energy.png" if prefix else f"energy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Energy breakdown plot saved as: {filename}")
    plt.close()


def plot_comparison_table_with_prefix(results_dict, algorithm_names, prefix=""):
    """Create comparison table with custom filename prefix"""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis('tight')
    ax.axis('off')

    headers = ['Algorithm', 'Best Fitness', 'Energy (J)', 'Load Imbalance',
               'Local %', 'GBS %', 'MEC %', 'Cloud %']

    table_data = []
    for name in algorithm_names:
        results = results_dict[name]
        detailed = results['detailed_fitness']
        stats = results['allocation_stats']

        row = [
            name, f"{results['best_fitness']:.6f}", f"{detailed['energy']:.2f}",
            f"{detailed['load_imbalance']:.4f}", f"{stats['local_pct']:.1f}",
            f"{stats['gbs_pct']:.1f}", f"{stats['mec_pct']:.1f}", f"{stats['cloud_pct']:.1f}"
        ]
        table_data.append(row)

    table = ax.table(cellText=table_data, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')

    for i in range(1, len(table_data) + 1):
        for j in range(len(headers)):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')

    plt.title('Algorithm Performance Comparison', fontsize=14, fontweight='bold', pad=20)

    filename = f"{prefix}_comparison_table.png" if prefix else f"comparison_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Comparison table saved as: {filename}")
    plt.close()


if __name__ == "__main__":
    # Test utility functions with dummy data
    print("Testing utility functions with dummy data...")

    algorithm_names = ['Jaya', 'GWO', 'GA', 'WOA', 'DE', 'ALO']

    # Create dummy results
    results_dict = {}
    for name in algorithm_names:
        results_dict[name] = {
            'best_fitness': np.random.uniform(0.3, 0.7),
            'detailed_fitness': {
                'energy': np.random.uniform(1000, 2000),
                'load_imbalance': np.random.uniform(0.5, 2.0)
            },
            'allocation_stats': {
                'local_pct': np.random.uniform(10, 30),
                'gbs_pct': np.random.uniform(20, 40),
                'mec_pct': np.random.uniform(20, 40),
                'cloud_pct': np.random.uniform(10, 30)
            },
            'energy_breakdown': {
                'local': np.random.uniform(200, 400),
                'gbs': np.random.uniform(300, 600),
                'mec': np.random.uniform(300, 600),
                'cloud': np.random.uniform(100, 300)
            },
            'convergence_history': list(np.linspace(0.9, 0.4, 50) + np.random.random(50) * 0.1),
            'num_iterations': 50,
            'population_size': 20
        }

    print_summary_table(results_dict, algorithm_names)
    save_results_to_json(results_dict)
