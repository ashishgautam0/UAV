"""
Main simulation script for UAV Task Allocation using Jaya Algorithm
Compares Jaya with GWO, PSO, GA, and WOA
"""

import numpy as np
import time
from config import Config
from digital_twin import DigitalTwin
from comparison_algorithms import (GA, WOA, DE, ALO, HSA,
                                   AIA, CS, FA, Rao)
from utils import (plot_all_results, print_summary_table, save_results_to_json)


def run_single_algorithm(algorithm_class, tasks, name, digital_twin=None, **kwargs):
    """
    Run a single optimization algorithm

    Args:
        algorithm_class: Algorithm class to instantiate
        tasks: Task parameters
        name: Algorithm name
        digital_twin: Optional Digital Twin instance
        **kwargs: Additional algorithm parameters

    Returns:
        Dictionary with results
    """
    print(f"\n{'=' * 70}")
    print(f"Running {name}")
    print(f"{'=' * 70}")

    start_time = time.time()

    # Create and run algorithm
    # if algorithm_class == JayaAlgorithm:
        # algorithm = algorithm_class(tasks, verbose=True, digital_twin=digital_twin)
    # else:
    algorithm = algorithm_class(tasks, verbose=True, digital_twin=digital_twin, **kwargs)

    best_solution = algorithm.optimize()
    end_time = time.time()

    # Get results
    if hasattr(algorithm, 'get_results'):
        results = algorithm.get_results()
    else:
        # For comparison algorithms that don't have get_results
        detailed_fitness = algorithm.fitness_func.calculate_detailed_fitness(best_solution)
        stats = algorithm.fitness_func.get_allocation_statistics(best_solution)
        energy_breakdown = algorithm.fitness_func.energy_model.calculate_energy_breakdown(best_solution)

        results = {
            'best_solution': best_solution,
            'best_fitness': algorithm.best_fitness,
            'convergence_history': algorithm.convergence_history,
            'energy_history': algorithm.energy_history if hasattr(algorithm, 'energy_history') else [],
            'load_imbalance_history': algorithm.load_imbalance_history if hasattr(algorithm, 'load_imbalance_history') else [],
            'detailed_fitness': detailed_fitness,
            'allocation_stats': stats,
            'energy_breakdown': energy_breakdown,
            'num_iterations': algorithm.max_iterations,
            'population_size': algorithm.population_size
        }

    results['execution_time'] = end_time - start_time

    print(f"\n{name} completed in {results['execution_time']:.2f} seconds")
    print(f"Best fitness: {results['best_fitness']:.6f}")

    return results


def run_comparison(num_tasks=520, num_gbs=3, population_size=50, max_iterations=200, seed=42, use_digital_twin=True):
    """
    Run comparison of all algorithms with Digital Twin integration

    Args:
        num_tasks: Number of tasks
        num_gbs: Number of GBS
        population_size: Population size for all algorithms
        max_iterations: Maximum iterations for all algorithms
        seed: Random seed for reproducibility
        use_digital_twin: Whether to use Digital Twin framework

    Returns:
        Dictionary with results for all algorithms
    """
    # Set random seed
    np.random.seed(seed)

    # Update configuration
    Config.NUM_TASKS = num_tasks
    Config.NUM_GBS = num_gbs
    Config.POPULATION_SIZE = population_size
    Config.MAX_ITERATIONS = max_iterations

    print("\n" + "=" * 70)
    print("UAV TASK ALLOCATION - ALGORITHM COMPARISON")
    print("=" * 70)
    Config.print_config()

    # Initialize Digital Twin (if enabled)
    digital_twin = None
    if use_digital_twin:
        print("\n" + "=" * 70)
        print("Initializing Digital Twin Framework")
        print("=" * 70)
        digital_twin = DigitalTwin(num_uavs=Config.NUM_UAVS, num_gbs=num_gbs, num_tasks=num_tasks)
        tasks = digital_twin.generate_tasks()
        digital_twin.print_status()
    else:
        # Generate tasks without Digital Twin
        print("\nGenerating task parameters...")
        tasks = Config.generate_random_tasks()
        print(f"Generated {num_tasks} tasks")

    # Define algorithms to compare
    algorithms = [
        ('DE', DE, {'F': 0.8, 'CR': 0.9}),
        ('GA', GA, {'crossover_rate': 0.8, 'mutation_rate': 0.1}),
        ('WOA', WOA, {}),
        ('ALO', ALO, {}),
        ('HSA', HSA, {'HMCR': 0.9, 'PAR': 0.3, 'BW': 1}),
        ('AIA', AIA, {'clone_rate': 10, 'mutation_rate': 0.3}),
        ('CS', CS, {'pa': 0.25, 'beta': 1.5}),
        ('FA', FA, {'alpha': 0.5, 'beta0': 1.0, 'gamma': 1.0}),
        ('Rao', Rao, {}),
    ]

    # Run all algorithms
    results_dict = {}
    for name, algo_class, params in algorithms:
        results_dict[name] = run_single_algorithm(algo_class, tasks, name, digital_twin=digital_twin, **params)

    # Print final Digital Twin status if enabled
    if use_digital_twin and digital_twin is not None:
        print("\n" + "=" * 70)
        print("FINAL DIGITAL TWIN STATUS (After Jaya Optimization)")
        print("=" * 70)
        digital_twin.print_status()

    return results_dict


def main():
    """Main function to run simulations"""

    # Run comparison with default parameters
    print("\n" + "=" * 70)
    print("STARTING SIMULATION")
    print("=" * 70)

    algorithm_names = ['DE', 'GA', 'WOA', 'ALO', 'HSA', 'AIA', 'CS', 'FA', 'Rao']

    # Run full simulation with Digital Twin
    print("\nRunning full simulation with Digital Twin (520 tasks, 200 iterations)...")
    results = run_comparison(
        num_tasks=520,
        num_gbs=3,
        population_size=50,
        max_iterations=200,
        seed=42,
        use_digital_twin=True
    )

    # Print results
    print_summary_table(results, algorithm_names)

    # Save and visualize results
    save_results_to_json(results, filename="results.json")
    print("\nGenerating visualization plots...")
    plot_all_results(results, algorithm_names, prefix="")
    

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETED")
    print("=" * 70)


def run_sensitivity_analysis():
    """Run sensitivity analysis on different parameters"""
    print("\n" + "=" * 70)
    print("SENSITIVITY ANALYSIS")
    print("=" * 70)

    # Test different task sizes
    task_sizes = [100, 200, 300, 500]
    results_by_size = {}

    for size in task_sizes:
        print(f"\n\nTesting with {size} tasks...")
        results = run_comparison(
            num_tasks=size,
            num_gbs=4,
            population_size=50,
            max_iterations=100,
            seed=42
        )
        results_by_size[size] = results

    # Print comparison
    print("\n" + "=" * 70)
    print("SENSITIVITY ANALYSIS RESULTS")
    print("=" * 70)

    for size, results in results_by_size.items():
        print(f"\n{size} tasks:")
        algorithm_names = ['DE', 'GA', 'WOA', 'ALO', 'HSA', 'AIA', 'CS', 'FA', 'Rao']
        for name in algorithm_names:
            print(f"  {name}: {results[name]['best_fitness']:.6f} "
                  f"({results[name]['execution_time']:.2f}s)")


if __name__ == "__main__":
    # Run main simulation
    main()

    # Uncomment to run sensitivity analysis
    # run_sensitivity_analysis()
