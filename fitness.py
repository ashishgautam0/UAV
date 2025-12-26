"""
Fitness function for UAV task allocation
Combines energy consumption and load imbalance objectives
"""

import numpy as np
from config import Config
from energy_model import EnergyModel


class FitnessFunction:
    """Multi-objective fitness function with normalization"""

    def __init__(self, tasks):
        """
        Initialize fitness function

        Args:
            tasks: Dictionary with task parameters
        """
        self.energy_model = EnergyModel(tasks)
        self.num_tasks = len(tasks['D'])

        # For normalization (will be updated during optimization)
        self.f1_min = float('inf')
        self.f1_max = float('-inf')
        self.f2_min = float('inf')
        self.f2_max = float('-inf')

        # Track if normalization bounds are initialized
        self.bounds_initialized = False

    def calculate_load_imbalance(self, solution):
        """
        Calculate load imbalance across GBS (standard deviation)

        f₂ = √[(1/g) × Σ (n_j - μ)²]

        Args:
            solution: Array of execution locations for all tasks

        Returns:
            Load imbalance (standard deviation)
        """
        # Count tasks assigned to each GBS
        # Note: Only locations 1 and 2 use GBS (location 0=local, 3=cloud)
        gbs_loads = np.zeros(Config.NUM_GBS)

        for task_idx, location in enumerate(solution):
            loc = int(location)
            if loc == Config.LOC_GBS:
                # Assign to a random GBS (or use task_idx % NUM_GBS for deterministic)
                gbs_idx = task_idx % Config.NUM_GBS
                gbs_loads[gbs_idx] += 1
            elif loc == Config.LOC_MEC:
                # MEC tasks also go through GBS
                gbs_idx = task_idx % Config.NUM_GBS
                gbs_loads[gbs_idx] += 1

        # Calculate average load
        mu = np.mean(gbs_loads)

        # Calculate standard deviation
        variance = np.mean((gbs_loads - mu) ** 2)
        load_imbalance = np.sqrt(variance)

        return load_imbalance

    def update_bounds(self, f1, f2):
        """
        Update normalization bounds for f1 and f2
        Only expands bounds, never shrinks them

        Args:
            f1: Energy consumption value
            f2: Load imbalance value
        """
        # Only expand bounds (never shrink)
        if f1 < self.f1_min:
            self.f1_min = f1
        if f1 > self.f1_max:
            self.f1_max = f1
        if f2 < self.f2_min:
            self.f2_min = f2
        if f2 > self.f2_max:
            self.f2_max = f2

    def normalize_value(self, value, min_val, max_val):
        """
        Normalize value to [0, 1] range

        Args:
            value: Value to normalize
            min_val: Minimum value in range
            max_val: Maximum value in range

        Returns:
            Normalized value
        """
        range_val = max_val - min_val
        if range_val < 1e-10:  # Range too small - use relative position
            # If range is tiny, return 0.5 (middle of normalized range)
            # This prevents all values from becoming 0.0 during convergence
            return 0.5
        return (value - min_val) / range_val

    def calculate_fitness(self, solution, update_bounds=True):
        """
        Calculate combined fitness function

        F = w₁ × f̂₁ + (1 - w₁) × f̂₂

        Args:
            solution: Array of execution locations for all tasks
            update_bounds: Whether to update normalization bounds

        Returns:
            Fitness value (lower is better)
        """
        # Calculate raw objectives
        f1 = self.energy_model.calculate_total_energy(solution)
        f2 = self.calculate_load_imbalance(solution)

        # Update bounds if requested
        if update_bounds:
            self.update_bounds(f1, f2)

        # Normalize objectives
        if self.bounds_initialized and self.f1_max > self.f1_min and self.f2_max > self.f2_min:
            f1_norm = self.normalize_value(f1, self.f1_min, self.f1_max)
            f2_norm = self.normalize_value(f2, self.f2_min, self.f2_max)
        else:
            # If bounds not initialized, use raw values
            f1_norm = f1
            f2_norm = f2

        # Combined fitness
        fitness = Config.W1 * f1_norm + Config.W2 * f2_norm

        return fitness

    def calculate_detailed_fitness(self, solution):
        """
        Calculate detailed fitness information including raw and normalized values

        Args:
            solution: Array of execution locations for all tasks

        Returns:
            Dictionary with detailed fitness information
        """
        f1 = self.energy_model.calculate_total_energy(solution)
        f2 = self.calculate_load_imbalance(solution)

        result = {
            'fitness': self.calculate_fitness(solution, update_bounds=False),
            'energy': f1,
            'load_imbalance': f2,
        }

        # Add normalized values if bounds are initialized
        if self.bounds_initialized and self.f1_max > self.f1_min and self.f2_max > self.f2_min:
            result['energy_norm'] = self.normalize_value(f1, self.f1_min, self.f1_max)
            result['load_imbalance_norm'] = self.normalize_value(f2, self.f2_min, self.f2_max)

        return result

    def initialize_bounds(self, population):
        """
        Initialize normalization bounds from a population

        Args:
            population: Array of solutions (population_size × num_tasks)
        """
        energies = []
        imbalances = []

        for solution in population:
            f1 = self.energy_model.calculate_total_energy(solution)
            f2 = self.calculate_load_imbalance(solution)
            energies.append(f1)
            imbalances.append(f2)

        self.f1_min = min(energies)
        self.f1_max = max(energies)
        self.f2_min = min(imbalances)
        self.f2_max = max(imbalances)

        # Ensure minimum range to avoid division issues
        if self.f1_max - self.f1_min < 1e-6:
            # Expand range by 10% of the mean value or use a default range
            mean_val = (self.f1_max + self.f1_min) / 2
            if abs(mean_val) > 1e-10:
                self.f1_min = mean_val * 0.95
                self.f1_max = mean_val * 1.05
            else:
                self.f1_min = -0.1
                self.f1_max = 0.1

        if self.f2_max - self.f2_min < 1e-6:
            mean_val = (self.f2_max + self.f2_min) / 2
            if abs(mean_val) > 1e-10:
                self.f2_min = mean_val * 0.95
                self.f2_max = mean_val * 1.05
            else:
                self.f2_min = -0.1
                self.f2_max = 0.1

        self.bounds_initialized = True

    def get_allocation_statistics(self, solution):
        """
        Get statistics about task allocation

        Args:
            solution: Array of execution locations for all tasks

        Returns:
            Dictionary with allocation statistics
        """
        locations = np.array([int(x) for x in solution])

        stats = {
            'local_count': np.sum(locations == Config.LOC_LOCAL),
            'gbs_count': np.sum(locations == Config.LOC_GBS),
            'mec_count': np.sum(locations == Config.LOC_MEC),
            'cloud_count': np.sum(locations == Config.LOC_CLOUD),
        }

        # Add percentages
        total = len(solution)
        stats['local_pct'] = (stats['local_count'] / total) * 100
        stats['gbs_pct'] = (stats['gbs_count'] / total) * 100
        stats['mec_pct'] = (stats['mec_count'] / total) * 100
        stats['cloud_pct'] = (stats['cloud_count'] / total) * 100

        return stats


if __name__ == "__main__":
    # Test fitness function
    print("Testing Fitness Function")
    print("=" * 60)

    # Generate sample tasks
    tasks = Config.generate_random_tasks(100)
    fitness_func = FitnessFunction(tasks)

    # Create random solutions
    np.random.seed(42)
    population = np.random.randint(0, 4, size=(10, 100))

    # Initialize bounds
    fitness_func.initialize_bounds(population)
    print(f"Normalization bounds initialized:")
    print(f"  Energy: [{fitness_func.f1_min:.4f}, {fitness_func.f1_max:.4f}]")
    print(f"  Load imbalance: [{fitness_func.f2_min:.4f}, {fitness_func.f2_max:.4f}]")

    # Test fitness calculation
    solution = population[0]
    detailed = fitness_func.calculate_detailed_fitness(solution)
    print(f"\nSolution fitness:")
    print(f"  Combined fitness: {detailed['fitness']:.6f}")
    print(f"  Energy: {detailed['energy']:.4f} J")
    print(f"  Load imbalance: {detailed['load_imbalance']:.4f}")

    # Allocation statistics
    stats = fitness_func.get_allocation_statistics(solution)
    print(f"\nAllocation statistics:")
    print(f"  Local: {stats['local_count']} ({stats['local_pct']:.1f}%)")
    print(f"  GBS: {stats['gbs_count']} ({stats['gbs_pct']:.1f}%)")
    print(f"  MEC: {stats['mec_count']} ({stats['mec_pct']:.1f}%)")
    print(f"  Cloud: {stats['cloud_count']} ({stats['cloud_pct']:.1f}%)")
