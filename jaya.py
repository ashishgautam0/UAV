"""
Jaya Algorithm for UAV Task Allocation
Parameter-free optimization algorithm (only requires population size and iterations)
"""

import numpy as np
from config import Config
from fitness import FitnessFunction


class JayaAlgorithm:
    """
    Jaya Algorithm implementation for task allocation

    The algorithm has only TWO parameters:
    - Population size (N)
    - Maximum iterations (MaxIter)
    """

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True, digital_twin=None):
        """
        Initialize Jaya algorithm

        Args:
            tasks: Dictionary with task parameters
            population_size: Population size (default from Config)
            max_iterations: Maximum iterations (default from Config)
            verbose: Whether to print progress
            digital_twin: Optional Digital Twin instance for system state tracking
        """
        self.tasks = tasks
        self.num_tasks = len(tasks['D'])
        self.population_size = population_size or Config.POPULATION_SIZE
        self.max_iterations = max_iterations or Config.MAX_ITERATIONS
        self.verbose = verbose
        self.digital_twin = digital_twin

        # Fitness function
        self.fitness_func = FitnessFunction(tasks)

        # Population
        self.population = None
        self.fitness_values = None

        # Best and worst solutions
        self.best_solution = None
        self.best_fitness = float('inf')
        self.worst_solution = None
        self.worst_fitness = float('-inf')

        # Convergence history
        self.convergence_history = []
        self.energy_history = []
        self.load_imbalance_history = []

    def initialize_population(self):
        """
        Initialize population with random solutions
        Each solution is a vector of execution locations
        """
        self.population = np.random.randint(
            0, 4,  # Locations: {0, 1, 2, 3}
            size=(self.population_size, self.num_tasks)
        )

        # Initialize normalization bounds
        self.fitness_func.initialize_bounds(self.population)

        # Evaluate initial population
        self.evaluate_population()

        if self.verbose:
            print(f"Population initialized: {self.population_size} solutions")
            print(f"Best initial fitness: {self.best_fitness:.6f}")

    def evaluate_population(self):
        """Evaluate fitness for all solutions in population"""
        self.fitness_values = np.array([
            self.fitness_func.calculate_fitness(solution, update_bounds=True)
            for solution in self.population
        ])

        # Update best and worst solutions
        best_idx = np.argmin(self.fitness_values)
        worst_idx = np.argmax(self.fitness_values)

        if self.fitness_values[best_idx] < self.best_fitness:
            self.best_fitness = self.fitness_values[best_idx]
            self.best_solution = self.population[best_idx].copy()

        self.worst_fitness = self.fitness_values[worst_idx]
        self.worst_solution = self.population[worst_idx].copy()

    def discretize(self, value):
        """
        Convert continuous value to discrete location {0, 1, 2, 3}

        Args:
            value: Continuous value

        Returns:
            Discrete location in {0, 1, 2, 3}
        """
        # Round and apply modulo 4
        discrete_value = int(round(value)) % 4

        # Ensure value is in valid range
        return max(0, min(3, discrete_value))

    def update_solution(self, solution_idx):
        """
        Update a single solution using Jaya equation

        X_k,i(t+1) = X_k,i(t) + r₁ × (X_best,i - |X_k,i(t)|) - r₂ × (X_worst,i - |X_k,i(t)|)

        Args:
            solution_idx: Index of solution to update

        Returns:
            New solution (discrete)
        """
        current_solution = self.population[solution_idx]
        new_solution = np.zeros(self.num_tasks, dtype=int)

        for i in range(self.num_tasks):
            # Random numbers
            r1 = np.random.random()
            r2 = np.random.random()

            # Jaya update equation
            current_val = current_solution[i]
            new_val = (
                current_val +
                r1 * (self.best_solution[i] - abs(current_val)) -
                r2 * (self.worst_solution[i] - abs(current_val))
            )

            # Discretize to {0, 1, 2, 3}
            new_solution[i] = self.discretize(new_val)

        return new_solution

    def optimize(self):
        """
        Run Jaya algorithm optimization

        Returns:
            Best solution found
        """
        # Initialize population
        self.initialize_population()

        # Main optimization loop
        for iteration in range(self.max_iterations):
            # Update each solution
            for k in range(self.population_size):
                # Generate new solution
                new_solution = self.update_solution(k)

                # Evaluate new solution
                new_fitness = self.fitness_func.calculate_fitness(new_solution, update_bounds=True)

                # Greedy selection: accept if better
                if new_fitness < self.fitness_values[k]:
                    self.population[k] = new_solution
                    self.fitness_values[k] = new_fitness

            # Update best and worst after all updates
            self.evaluate_population()

            # Store convergence history
            self.convergence_history.append(self.best_fitness)

            # Store energy and load imbalance history
            detailed = self.fitness_func.calculate_detailed_fitness(self.best_solution)
            self.energy_history.append(detailed['energy'])
            self.load_imbalance_history.append(detailed['load_imbalance'])

            # Print progress
            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: "
                      f"Best fitness = {self.best_fitness:.6f}")

        if self.verbose:
            print(f"\nOptimization completed!")
            print(f"Final best fitness: {self.best_fitness:.6f}")

        # Update Digital Twin if provided
        if self.digital_twin is not None:
            energy_breakdown = self.fitness_func.energy_model.calculate_energy_breakdown(self.best_solution)
            self.digital_twin.update_from_solution(self.best_solution, energy_breakdown)

        return self.best_solution

    def get_results(self):
        """
        Get detailed results of optimization

        Returns:
            Dictionary with results
        """
        detailed_fitness = self.fitness_func.calculate_detailed_fitness(self.best_solution)
        stats = self.fitness_func.get_allocation_statistics(self.best_solution)
        energy_breakdown = self.fitness_func.energy_model.calculate_energy_breakdown(self.best_solution)

        results = {
            'best_solution': self.best_solution,
            'best_fitness': self.best_fitness,
            'convergence_history': self.convergence_history,
            'energy_history': self.energy_history,
            'load_imbalance_history': self.load_imbalance_history,
            'detailed_fitness': detailed_fitness,
            'allocation_stats': stats,
            'energy_breakdown': energy_breakdown,
            'num_iterations': self.max_iterations,
            'population_size': self.population_size
        }

        return results

    def print_results(self):
        """Print detailed results"""
        results = self.get_results()

        print("\n" + "=" * 70)
        print("JAYA ALGORITHM RESULTS")
        print("=" * 70)

        print(f"\nAlgorithm Parameters:")
        print(f"  Population size: {results['population_size']}")
        print(f"  Iterations: {results['num_iterations']}")

        print(f"\nFitness Values:")
        print(f"  Combined fitness: {results['detailed_fitness']['fitness']:.6f}")
        print(f"  Total energy: {results['detailed_fitness']['energy']:.4f} J")
        print(f"  Load imbalance: {results['detailed_fitness']['load_imbalance']:.4f}")

        print(f"\nTask Allocation:")
        stats = results['allocation_stats']
        print(f"  Local (UAV):  {stats['local_count']:3d} tasks ({stats['local_pct']:5.1f}%)")
        print(f"  GBS:          {stats['gbs_count']:3d} tasks ({stats['gbs_pct']:5.1f}%)")
        print(f"  MEC:          {stats['mec_count']:3d} tasks ({stats['mec_pct']:5.1f}%)")
        print(f"  Cloud:        {stats['cloud_count']:3d} tasks ({stats['cloud_pct']:5.1f}%)")

        print(f"\nEnergy Breakdown:")
        breakdown = results['energy_breakdown']
        total_energy = sum(breakdown.values())
        for loc, energy in breakdown.items():
            pct = (energy / total_energy * 100) if total_energy > 0 else 0
            print(f"  {loc.capitalize():8s}: {energy:10.4f} J ({pct:5.1f}%)")

        print("=" * 70)


if __name__ == "__main__":
    # Test Jaya algorithm
    print("Testing Jaya Algorithm for UAV Task Allocation")
    print("=" * 70)

    # Set random seed for reproducibility
    np.random.seed(42)

    # Generate tasks
    Config.NUM_TASKS = 100  # Smaller for testing
    tasks = Config.generate_random_tasks()

    # Run Jaya algorithm
    jaya = JayaAlgorithm(
        tasks=tasks,
        population_size=20,
        max_iterations=50,
        verbose=True
    )

    best_solution = jaya.optimize()
    jaya.print_results()
