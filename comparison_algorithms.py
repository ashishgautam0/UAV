"""
Comparison algorithms for UAV task allocation:
- Genetic Algorithm (GA)
- Whale Optimization Algorithm (WOA)
- Differential Evolution (DE)
- Ant-Lion Optimization (ALO)
- Harmony Search Algorithm (HSA)
- Firework Algorithm (FWA)
- Artificial Immune Algorithm (AIA)
- Charged System Algorithm (CSA)
- Cuckoo Search (CS)
- Firefly Algorithm (FA)
- Bacteria Foraging Optimization (BFO)
- Rao Algorithm (Rao)
"""

import numpy as np
import math
from config import Config
from fitness import FitnessFunction


class BaseOptimizer:
    """Base class for optimization algorithms"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True, digital_twin=None):
        self.tasks = tasks
        self.num_tasks = len(tasks['D'])
        self.population_size = population_size or Config.POPULATION_SIZE
        self.max_iterations = max_iterations or Config.MAX_ITERATIONS
        self.verbose = verbose
        self.digital_twin = digital_twin

        self.fitness_func = FitnessFunction(tasks)
        self.population = None
        self.fitness_values = None
        self.best_solution = None
        self.best_fitness = float('inf')
        self.convergence_history = []
        self.energy_history = []
        self.load_imbalance_history = []

    def discretize(self, value):
        """Convert continuous value to discrete location {0, 1, 2, 3}"""
        discrete_value = int(round(value)) % 4
        return max(0, min(3, discrete_value))

    def initialize_population(self):
        """Initialize population with random solutions"""
        self.population = np.random.randint(0, 4, size=(self.population_size, self.num_tasks))
        self.fitness_func.initialize_bounds(self.population)
        self.evaluate_population()

    def evaluate_population(self):
        """Evaluate fitness for all solutions"""
        self.fitness_values = np.array([
            self.fitness_func.calculate_fitness(solution, update_bounds=True)
            for solution in self.population
        ])

        best_idx = np.argmin(self.fitness_values)
        if self.fitness_values[best_idx] < self.best_fitness:
            self.best_fitness = self.fitness_values[best_idx]
            self.best_solution = self.population[best_idx].copy()

    def update_digital_twin(self):
        """Update Digital Twin with optimization results if available"""
        if self.digital_twin is not None and self.best_solution is not None:
            energy_breakdown = self.fitness_func.energy_model.calculate_energy_breakdown(self.best_solution)
            self.digital_twin.update_from_solution(self.best_solution, energy_breakdown)

    def track_metrics(self):
        """Track energy and load imbalance for current best solution"""
        if self.best_solution is not None:
            detailed = self.fitness_func.calculate_detailed_fitness(self.best_solution)
            self.energy_history.append(detailed['energy'])
            self.load_imbalance_history.append(detailed['load_imbalance'])


class GWO(BaseOptimizer):
    """Grey Wolf Optimizer"""

    def optimize(self):
        """Run GWO optimization"""
        self.initialize_population()

        # Initialize alpha, beta, delta wolves
        sorted_indices = np.argsort(self.fitness_values)
        alpha = self.population[sorted_indices[0]].copy()
        beta = self.population[sorted_indices[1]].copy()
        delta = self.population[sorted_indices[2]].copy()

        for iteration in range(self.max_iterations):
            # Linearly decrease a from 2 to 0
            a = 2 - iteration * (2.0 / self.max_iterations)

            for i in range(self.population_size):
                new_solution = np.zeros(self.num_tasks, dtype=int)

                for j in range(self.num_tasks):
                    # Update position based on alpha, beta, delta
                    r1, r2 = np.random.random(), np.random.random()
                    A1 = 2 * a * r1 - a
                    C1 = 2 * r2

                    D_alpha = abs(C1 * alpha[j] - self.population[i][j])
                    X1 = alpha[j] - A1 * D_alpha

                    r1, r2 = np.random.random(), np.random.random()
                    A2 = 2 * a * r1 - a
                    C2 = 2 * r2

                    D_beta = abs(C2 * beta[j] - self.population[i][j])
                    X2 = beta[j] - A2 * D_beta

                    r1, r2 = np.random.random(), np.random.random()
                    A3 = 2 * a * r1 - a
                    C3 = 2 * r2

                    D_delta = abs(C3 * delta[j] - self.population[i][j])
                    X3 = delta[j] - A3 * D_delta

                    # Average and discretize
                    new_val = (X1 + X2 + X3) / 3.0
                    new_solution[j] = self.discretize(new_val)

                # Evaluate new solution
                new_fitness = self.fitness_func.calculate_fitness(new_solution, update_bounds=True)
                if new_fitness < self.fitness_values[i]:
                    self.population[i] = new_solution
                    self.fitness_values[i] = new_fitness

            # Update alpha, beta, delta
            sorted_indices = np.argsort(self.fitness_values)
            alpha = self.population[sorted_indices[0]].copy()
            beta = self.population[sorted_indices[1]].copy()
            delta = self.population[sorted_indices[2]].copy()

            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class SMA(BaseOptimizer):
    """Slime Mould Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True, digital_twin=None):
        """
        Initialize Slime Mould Algorithm

        Based on the oscillatory behavior and foraging strategy of slime mould
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.z = 0.03  # Exploration probability threshold

    def calculate_smell_index(self, fitness_values):
        """
        Calculate smell index (S) for all slime moulds based on fitness ranking

        Args:
            fitness_values: Array of fitness values

        Returns:
            Smell index array (higher values for better solutions)
        """
        # Sort fitness in ascending order (best to worst for minimization)
        sorted_indices = np.argsort(fitness_values)

        # Assign smell index based on rank
        smell_index = np.zeros(self.population_size)
        for rank, idx in enumerate(sorted_indices):
            if rank < self.population_size / 2:
                # First half gets positive smell index (better fitness)
                smell_index[idx] = 1 - rank / (self.population_size / 2)
            else:
                # Second half gets lower smell index
                smell_index[idx] = 1 - rank / self.population_size

        return smell_index

    def calculate_weight(self, smell_index, iteration, idx):
        """
        Calculate weight W for position update

        Args:
            smell_index: Smell index for the slime mould
            iteration: Current iteration
            idx: Index of current slime mould

        Returns:
            Weight value
        """
        # Condition for weight calculation
        best_idx = np.argmin(self.fitness_values)

        if idx < self.population_size / 2:
            # First half (better fitness)
            return 1 + np.random.random()
        else:
            # Second half (worse fitness)
            return 1 - np.random.random()

    def optimize(self):
        """Run Slime Mould Algorithm"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            # Calculate smell index for all slime moulds
            smell_index = self.calculate_smell_index(self.fitness_values)

            # Best fitness value (for calculating p)
            best_fitness = np.min(self.fitness_values)
            worst_fitness = np.max(self.fitness_values)

            # Calculate parameter a (decreases from ~1 to ~-1)
            # Clamp to avoid arctanh(±1) which gives ±infinity
            val = -(iteration / self.max_iterations) + 1
            val = np.clip(val, -0.99999, 0.99999)  # Avoid exact ±1
            a = np.arctanh(val)

            # Calculate parameter b (decreases from 1 to 0)
            b = 1 - iteration / self.max_iterations

            # Update each slime mould position
            for i in range(self.population_size):
                # Calculate p (probability based on smell index)
                if worst_fitness - best_fitness > 1e-10:
                    p = np.tanh(abs(self.fitness_values[i] - best_fitness))
                else:
                    p = 0.5

                new_solution = np.zeros(self.num_tasks)

                for j in range(self.num_tasks):
                    r = np.random.random()

                    if r < self.z:
                        # Random position (exploration)
                        new_solution[j] = np.random.randint(0, 4)
                    else:
                        if r < p:
                            # Approach food (exploitation)
                            # Select two random individuals
                            rand_idx_A = np.random.randint(0, self.population_size)
                            rand_idx_B = np.random.randint(0, self.population_size)

                            # Calculate vb (oscillation in [-a, a])
                            vb = np.random.uniform(-a, a)

                            # Calculate weight
                            W = self.calculate_weight(smell_index, iteration, i)

                            # Position update
                            new_val = self.best_solution[j] + vb * (
                                W * self.population[rand_idx_A][j] - self.population[rand_idx_B][j]
                            )
                        else:
                            # Wrap food (local search)
                            # Calculate vc (oscillation in [-b, b])
                            vc = np.random.uniform(-b, b)

                            new_val = vc * self.population[i][j]

                        new_solution[j] = self.discretize(new_val)

                # Evaluate new solution
                new_fitness = self.fitness_func.calculate_fitness(new_solution, update_bounds=True)

                # Greedy selection
                if new_fitness < self.fitness_values[i]:
                    self.population[i] = new_solution
                    self.fitness_values[i] = new_fitness

            # Update best solution
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class GA(BaseOptimizer):
    """Genetic Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True,
                 crossover_rate=0.8, mutation_rate=0.1, digital_twin=None):
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate

    def tournament_selection(self, tournament_size=3):
        """Select parent using tournament selection"""
        indices = np.random.choice(self.population_size, tournament_size, replace=False)
        tournament_fitness = self.fitness_values[indices]
        winner_idx = indices[np.argmin(tournament_fitness)]
        return self.population[winner_idx].copy()

    def crossover(self, parent1, parent2):
        """Single-point crossover"""
        if np.random.random() < self.crossover_rate:
            point = np.random.randint(1, self.num_tasks)
            child1 = np.concatenate([parent1[:point], parent2[point:]])
            child2 = np.concatenate([parent2[:point], parent1[point:]])
            return child1, child2
        return parent1.copy(), parent2.copy()

    def mutate(self, solution):
        """Random mutation"""
        mutated = solution.copy()
        for i in range(self.num_tasks):
            if np.random.random() < self.mutation_rate:
                mutated[i] = np.random.randint(0, 4)
        return mutated

    def optimize(self):
        """Run GA optimization"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            new_population = []

            # Elitism: keep best solution
            best_idx = np.argmin(self.fitness_values)
            new_population.append(self.population[best_idx].copy())

            # Generate new population
            while len(new_population) < self.population_size:
                # Selection
                parent1 = self.tournament_selection()
                parent2 = self.tournament_selection()

                # Crossover
                child1, child2 = self.crossover(parent1, parent2)

                # Mutation
                child1 = self.mutate(child1)
                child2 = self.mutate(child2)

                new_population.append(child1)
                if len(new_population) < self.population_size:
                    new_population.append(child2)

            self.population = np.array(new_population[:self.population_size])
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class WOA(BaseOptimizer):
    """Whale Optimization Algorithm"""

    def optimize(self):
        """Run WOA optimization"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            # Linearly decrease a from 2 to 0
            a = 2 - iteration * (2.0 / self.max_iterations)

            for i in range(self.population_size):
                new_solution = np.zeros(self.num_tasks, dtype=int)

                for j in range(self.num_tasks):
                    r = np.random.random()
                    A = 2 * a * r - a
                    C = 2 * r
                    p = np.random.random()

                    if p < 0.5:
                        if abs(A) < 1:
                            # Encircling prey
                            D = abs(C * self.best_solution[j] - self.population[i][j])
                            new_val = self.best_solution[j] - A * D
                        else:
                            # Search for prey (random whale)
                            rand_idx = np.random.randint(0, self.population_size)
                            D = abs(C * self.population[rand_idx][j] - self.population[i][j])
                            new_val = self.population[rand_idx][j] - A * D
                    else:
                        # Bubble-net attacking
                        D_prime = abs(self.best_solution[j] - self.population[i][j])
                        b = 1
                        l = np.random.uniform(-1, 1)
                        new_val = D_prime * np.exp(b * l) * np.cos(2 * np.pi * l) + self.best_solution[j]

                    new_solution[j] = self.discretize(new_val)

                # Evaluate new solution
                new_fitness = self.fitness_func.calculate_fitness(new_solution, update_bounds=True)
                if new_fitness < self.fitness_values[i]:
                    self.population[i] = new_solution
                    self.fitness_values[i] = new_fitness

            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class DE(BaseOptimizer):
    """Differential Evolution Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True,
                 F=0.8, CR=0.9, digital_twin=None):
        """
        Initialize Differential Evolution

        Args:
            F: Mutation factor (0.5-1.0, typically 0.8)
            CR: Crossover probability (0.0-1.0, typically 0.9)
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.F = F      # Mutation factor
        self.CR = CR    # Crossover probability

    def mutate(self, idx):
        """
        DE/rand/1 mutation: v_i = x_r1 + F * (x_r2 - x_r3)

        Args:
            idx: Index of current solution

        Returns:
            Mutant vector
        """
        # Select three random distinct individuals (different from idx)
        candidates = [i for i in range(self.population_size) if i != idx]
        r1, r2, r3 = np.random.choice(candidates, 3, replace=False)

        # Create mutant vector
        mutant = np.zeros(self.num_tasks)
        for j in range(self.num_tasks):
            mutant[j] = self.population[r1][j] + self.F * (self.population[r2][j] - self.population[r3][j])

        return mutant

    def crossover(self, target, mutant):
        """
        Binomial crossover

        Args:
            target: Target vector (current solution)
            mutant: Mutant vector

        Returns:
            Trial vector
        """
        trial = np.zeros(self.num_tasks, dtype=int)

        # Ensure at least one dimension is from mutant
        j_rand = np.random.randint(0, self.num_tasks)

        for j in range(self.num_tasks):
            if np.random.random() < self.CR or j == j_rand:
                # Take from mutant
                trial[j] = self.discretize(mutant[j])
            else:
                # Take from target
                trial[j] = target[j]

        return trial

    def optimize(self):
        """Run Differential Evolution optimization"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            for i in range(self.population_size):
                # 1. Mutation
                mutant = self.mutate(i)

                # 2. Crossover
                trial = self.crossover(self.population[i], mutant)

                # 3. Selection (greedy)
                trial_fitness = self.fitness_func.calculate_fitness(trial, update_bounds=True)

                if trial_fitness < self.fitness_values[i]:
                    self.population[i] = trial
                    self.fitness_values[i] = trial_fitness

            # Update best solution
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class ACO(BaseOptimizer):
    """Ant Colony Optimization Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True,
                 alpha=1.0, beta=2.0, rho=0.5, Q=100, digital_twin=None):
        """
        Initialize Ant Colony Optimization

        Args:
            alpha: Pheromone importance factor (default: 1.0)
            beta: Heuristic information importance factor (default: 2.0)
            rho: Pheromone evaporation rate (0-1, default: 0.5)
            Q: Pheromone deposit factor (default: 100)
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.alpha = alpha      # Pheromone importance
        self.beta = beta        # Heuristic importance
        self.rho = rho          # Evaporation rate
        self.Q = Q              # Pheromone deposit factor

        # Pheromone matrix: [num_tasks x 4 locations]
        self.pheromone = np.ones((self.num_tasks, 4))

    def calculate_heuristic(self, task_idx, location):
        """
        Calculate heuristic value (inverse of energy)

        Args:
            task_idx: Task index
            location: Execution location (0-3)

        Returns:
            Heuristic value (higher is better)
        """
        # Use inverse of energy as heuristic (lower energy = higher desirability)
        energy = self.fitness_func.energy_model.calculate_task_energy(task_idx, location)
        # Avoid division by zero
        return 1.0 / (energy + 1e-10)

    def construct_solution(self):
        """
        Construct a solution using ACO probabilistic rules

        Returns:
            Solution vector (task allocation)
        """
        solution = np.zeros(self.num_tasks, dtype=int)

        for task_idx in range(self.num_tasks):
            # Calculate probabilities for each location
            probabilities = []

            for location in range(4):
                tau = self.pheromone[task_idx, location] ** self.alpha
                eta = self.calculate_heuristic(task_idx, location) ** self.beta
                probabilities.append(tau * eta)

            # Normalize probabilities
            total = sum(probabilities)
            if total > 0:
                probabilities = [p / total for p in probabilities]
            else:
                probabilities = [0.25, 0.25, 0.25, 0.25]  # Equal probability

            # Select location based on probabilities
            solution[task_idx] = np.random.choice(4, p=probabilities)

        return solution

    def update_pheromone(self, solutions, fitness_values):
        """
        Update pheromone trails based on solutions quality

        Args:
            solutions: List of ant solutions
            fitness_values: Corresponding fitness values
        """
        # Evaporation
        self.pheromone *= (1 - self.rho)

        # Deposit pheromone
        for solution, fitness in zip(solutions, fitness_values):
            # Better solutions (lower fitness) deposit more pheromone
            deposit = self.Q / (fitness + 1e-10)

            for task_idx, location in enumerate(solution):
                self.pheromone[task_idx, int(location)] += deposit

        # Ensure pheromone doesn't become too small
        self.pheromone = np.maximum(self.pheromone, 0.01)

    def optimize(self):
        """Run ACO optimization"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            # Construct solutions for all ants
            ant_solutions = []
            ant_fitness = []

            for ant in range(self.population_size):
                # Construct solution using pheromone and heuristic
                solution = self.construct_solution()
                fitness = self.fitness_func.calculate_fitness(solution, update_bounds=True)

                ant_solutions.append(solution)
                ant_fitness.append(fitness)

                # Update best solution
                if fitness < self.best_fitness:
                    self.best_fitness = fitness
                    self.best_solution = solution.copy()

            # Update pheromone trails
            self.update_pheromone(ant_solutions, ant_fitness)

            # Update population with current ant solutions
            self.population = np.array(ant_solutions)
            self.fitness_values = np.array(ant_fitness)

            # Track metrics
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class ALO(BaseOptimizer):
    """Ant-Lion Optimization Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True, digital_twin=None):
        """
        Initialize Ant-Lion Optimization

        Based on the hunting behavior of antlions in nature
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        # Antlions population (also solutions)
        self.antlions = None
        self.antlion_fitness = None

    def random_walk(self, dim):
        """
        Perform random walk for ant movement

        Args:
            dim: Dimension (number of tasks)

        Returns:
            Random walk array
        """
        # Generate random steps
        steps = np.random.choice([-1, 1], size=dim)
        # Cumulative sum gives the random walk
        walk = np.cumsum(steps)
        return walk

    def roulette_wheel_selection(self):
        """
        Select an antlion using roulette wheel selection based on fitness

        Returns:
            Index of selected antlion
        """
        # Convert fitness to weights (lower fitness = higher weight for minimization)
        if np.max(self.antlion_fitness) - np.min(self.antlion_fitness) < 1e-10:
            # If all fitness are same, select randomly
            return np.random.randint(0, self.population_size)

        # Invert fitness for minimization (better fitness = higher selection probability)
        max_fitness = np.max(self.antlion_fitness)
        weights = max_fitness - self.antlion_fitness + 1e-10

        # Normalize to probabilities
        probabilities = weights / np.sum(weights)

        # Select based on probabilities
        return np.random.choice(self.population_size, p=probabilities)

    def optimize(self):
        """Run Ant-Lion Optimization"""
        # Initialize ants (population)
        self.initialize_population()

        # Initialize antlions (copy of initial population)
        self.antlions = self.population.copy()
        self.antlion_fitness = self.fitness_values.copy()

        # Elite antlion (best solution)
        elite_idx = np.argmin(self.antlion_fitness)
        elite_antlion = self.antlions[elite_idx].copy()
        elite_fitness = self.antlion_fitness[elite_idx]

        for iteration in range(self.max_iterations):
            # Ratio for boundary reduction (decreases from 1 to 0)
            I = 1 - iteration / self.max_iterations

            for i in range(self.population_size):
                # Select an antlion using roulette wheel
                antlion_idx = self.roulette_wheel_selection()
                selected_antlion = self.antlions[antlion_idx]

                # Random walk around selected antlion
                c_lower = selected_antlion - I * 2  # Lower bound
                c_upper = selected_antlion + I * 2  # Upper bound

                # Ensure bounds are within [0, 3]
                c_lower = np.maximum(c_lower, 0)
                c_upper = np.minimum(c_upper, 3)

                # Random walk toward selected antlion
                if np.random.random() < 0.5:
                    walk_antlion = np.random.uniform(c_lower, c_upper, self.num_tasks)
                else:
                    # Perform random walk and normalize to bounds
                    raw_walk = self.random_walk(self.num_tasks)
                    # Normalize walk to [c_lower, c_upper]
                    if np.max(raw_walk) - np.min(raw_walk) > 1e-10:
                        normalized_walk = (raw_walk - np.min(raw_walk)) / (np.max(raw_walk) - np.min(raw_walk))
                        walk_antlion = c_lower + normalized_walk * (c_upper - c_lower)
                    else:
                        walk_antlion = selected_antlion.copy()

                # Random walk around elite antlion
                e_lower = elite_antlion - I * 2
                e_upper = elite_antlion + I * 2
                e_lower = np.maximum(e_lower, 0)
                e_upper = np.minimum(e_upper, 3)

                if np.random.random() < 0.5:
                    walk_elite = np.random.uniform(e_lower, e_upper, self.num_tasks)
                else:
                    raw_walk = self.random_walk(self.num_tasks)
                    if np.max(raw_walk) - np.min(raw_walk) > 1e-10:
                        normalized_walk = (raw_walk - np.min(raw_walk)) / (np.max(raw_walk) - np.min(raw_walk))
                        walk_elite = e_lower + normalized_walk * (e_upper - e_lower)
                    else:
                        walk_elite = elite_antlion.copy()

                # Ant position = average of two random walks
                new_position = (walk_antlion + walk_elite) / 2.0

                # Discretize to {0, 1, 2, 3}
                new_solution = np.array([self.discretize(val) for val in new_position])

                # Evaluate ant fitness
                new_fitness = self.fitness_func.calculate_fitness(new_solution, update_bounds=True)

                # Update ant position
                self.population[i] = new_solution
                self.fitness_values[i] = new_fitness

                # If ant is fitter than its corresponding antlion, update antlion
                if new_fitness < self.antlion_fitness[antlion_idx]:
                    self.antlions[antlion_idx] = new_solution.copy()
                    self.antlion_fitness[antlion_idx] = new_fitness

                # Update elite if this ant is better
                if new_fitness < elite_fitness:
                    elite_antlion = new_solution.copy()
                    elite_fitness = new_fitness

            # Update best solution
            self.evaluate_population()

            # Update elite from antlions
            elite_idx = np.argmin(self.antlion_fitness)
            if self.antlion_fitness[elite_idx] < elite_fitness:
                elite_antlion = self.antlions[elite_idx].copy()
                elite_fitness = self.antlion_fitness[elite_idx]

            # Track metrics
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class FOA(BaseOptimizer):
    """Fossa Optimization Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True, digital_twin=None):
        """
        Initialize Fossa Optimization Algorithm

        Based on the hunting behavior and territorial strategies of the fossa
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)

    def exploration_phase(self, x, fitness, alpha_idx, iteration):
        """
        Exploration Phase: Fossas explore large territories searching for prey

        Args:
            x: Current population
            fitness: Fitness values
            alpha_idx: Index of alpha fossa (best solution)
            iteration: Current iteration

        Returns:
            Updated population
        """
        newx = x.copy()
        alpha_fossa = x[alpha_idx, :]

        for i in range(self.population_size):
            if i == alpha_idx:
                continue

            # Exploration coefficient (decreases over iterations)
            a = 2 - 2 * iteration / self.max_iterations

            # Random fossa for information sharing
            r_idx = np.random.randint(0, self.population_size)
            random_fossa = x[r_idx, :]

            for j in range(self.num_tasks):
                r1 = np.random.random()
                r2 = np.random.random()

                # Coefficient vectors
                A = 2 * a * r1 - a
                C = 2 * r2

                if np.abs(A) >= 1:
                    # Exploration: move away from alpha or towards random fossa
                    D = np.abs(C * random_fossa[j] - x[i, j])
                    newx[i, j] = random_fossa[j] - A * D
                else:
                    # Move towards alpha fossa (best solution)
                    D = np.abs(C * alpha_fossa[j] - x[i, j])
                    newx[i, j] = alpha_fossa[j] - A * D

            # Discretize to {0, 1, 2, 3}
            newx[i, :] = np.array([self.discretize(val) for val in newx[i, :]])

        return newx

    def exploitation_phase(self, x, fitness, alpha_idx, iteration):
        """
        Exploitation Phase: Fossas focus on promising hunting areas

        Args:
            x: Current population
            fitness: Fitness values
            alpha_idx: Index of alpha fossa
            iteration: Current iteration

        Returns:
            Updated population
        """
        newx = x.copy()
        alpha_fossa = x[alpha_idx, :]

        # Spiral coefficient
        b = 1

        for i in range(self.population_size):
            if i == alpha_idx:
                continue

            # Levy flight for better exploration-exploitation balance
            l_param = np.random.uniform(-1, 1, self.num_tasks)

            for j in range(self.num_tasks):
                # Distance to alpha
                distance = np.abs(alpha_fossa[j] - x[i, j])

                # Spiral position update (mimicking fossa's hunting pattern)
                theta = np.random.uniform(0, 2 * np.pi)
                r = np.random.random()

                # Spiral equation
                newx[i, j] = distance * np.exp(b * theta) * np.cos(theta) + alpha_fossa[j]

                # Add randomness with Levy flight
                if np.random.random() < 0.5:
                    newx[i, j] += l_param[j] * (x[i, j] - alpha_fossa[j])

            # Discretize to {0, 1, 2, 3}
            newx[i, :] = np.array([self.discretize(val) for val in newx[i, :]])

        return newx

    def territorial_behavior(self, x, fitness, alpha_idx):
        """
        Territorial Behavior: Fossas defend and mark their territory

        Args:
            x: Current population
            fitness: Fitness values
            alpha_idx: Index of alpha fossa

        Returns:
            Updated population
        """
        newx = x.copy()
        alpha_fossa = x[alpha_idx, :]

        # Sort by fitness to get hierarchy
        sorted_indices = np.argsort(fitness)

        for i in range(self.population_size):
            if i == alpha_idx:
                continue

            # Territorial influence decreases with rank
            rank = np.where(sorted_indices == i)[0][0]
            territorial_factor = 1 - (rank / self.population_size)

            # Beta and delta fossas (second and third best)
            beta_idx = sorted_indices[1] if len(sorted_indices) > 1 else sorted_indices[0]
            delta_idx = sorted_indices[2] if len(sorted_indices) > 2 else sorted_indices[0]

            beta_fossa = x[beta_idx, :]
            delta_fossa = x[delta_idx, :]

            for j in range(self.num_tasks):
                # Weighted influence from top fossas
                w1 = 0.5  # Alpha weight
                w2 = 0.3  # Beta weight
                w3 = 0.2  # Delta weight

                r = np.random.random()

                # Territory-based position update
                newx[i, j] = (w1 * alpha_fossa[j] +
                             w2 * beta_fossa[j] +
                             w3 * delta_fossa[j]) * territorial_factor + \
                             x[i, j] * (1 - territorial_factor) * r

            # Discretize to {0, 1, 2, 3}
            newx[i, :] = np.array([self.discretize(val) for val in newx[i, :]])

        return newx

    def optimize(self):
        """Run Fossa Optimization Algorithm"""
        # Initialize population
        self.initialize_population()

        for iteration in range(self.max_iterations):
            # Find alpha fossa (best solution)
            alpha_idx = np.argmin(self.fitness_values)

            # Determine phase based on iteration
            p = np.random.random()

            if p < 0.5:
                # Exploration phase
                newx = self.exploration_phase(self.population, self.fitness_values, alpha_idx, iteration)
            else:
                # Exploitation phase
                newx = self.exploitation_phase(self.population, self.fitness_values, alpha_idx, iteration)

            # Every few iterations, apply territorial behavior
            if iteration % 5 == 0:
                newx = self.territorial_behavior(newx, self.fitness_values, alpha_idx)

            # Evaluate new solutions
            for i in range(self.population_size):
                newfitness = self.fitness_func.calculate_fitness(newx[i, :], update_bounds=True)

                # Greedy selection
                if newfitness < self.fitness_values[i]:
                    self.fitness_values[i] = newfitness
                    self.population[i, :] = newx[i, :]

            # Update best solution
            self.evaluate_population()

            # Track metrics
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class HSA(BaseOptimizer):
    """Harmony Search Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True,
                 HMCR=0.9, PAR=0.3, BW=1, digital_twin=None):
        """
        Initialize Harmony Search Algorithm

        Based on the musical improvisation process where musicians search for
        a perfect state of harmony. The algorithm uses a Harmony Memory (HM)
        to store good solutions and improvises new harmonies.

        Args:
            HMCR: Harmony Memory Consideration Rate (0-1, default: 0.9)
                  Probability of selecting a value from harmony memory
            PAR: Pitch Adjustment Rate (0-1, default: 0.3)
                 Probability of adjusting a selected value
            BW: Bandwidth (default: 1)
                Range for pitch adjustment in discrete space
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.HMCR = HMCR  # Harmony Memory Consideration Rate
        self.PAR = PAR    # Pitch Adjustment Rate
        self.BW = BW      # Bandwidth for adjustment
        self.HMS = self.population_size  # Harmony Memory Size

    def improvise_new_harmony(self):
        """
        Improvise a new harmony (solution) using three rules:
        1. Memory consideration (with probability HMCR)
        2. Pitch adjustment (with probability PAR)
        3. Random selection (with probability 1-HMCR)

        Returns:
            New harmony (solution array)
        """
        new_harmony = np.zeros(self.num_tasks, dtype=int)

        for j in range(self.num_tasks):
            if np.random.random() < self.HMCR:
                # Rule 1: Select from Harmony Memory
                random_harmony_idx = np.random.randint(0, self.HMS)
                new_harmony[j] = self.population[random_harmony_idx][j]

                # Rule 2: Pitch Adjustment
                if np.random.random() < self.PAR:
                    # Adjust the pitch (add or subtract bandwidth)
                    adjustment = np.random.choice([-self.BW, self.BW])
                    new_val = new_harmony[j] + adjustment
                    new_harmony[j] = self.discretize(new_val)
            else:
                # Rule 3: Random selection
                new_harmony[j] = np.random.randint(0, 4)

        return new_harmony

    def update_harmony_memory(self, new_harmony, new_fitness):
        """
        Update Harmony Memory if the new harmony is better than the worst harmony

        Args:
            new_harmony: New harmony to consider
            new_fitness: Fitness of the new harmony

        Returns:
            True if HM was updated, False otherwise
        """
        # Find the worst harmony in memory
        worst_idx = np.argmax(self.fitness_values)
        worst_fitness = self.fitness_values[worst_idx]

        # If new harmony is better than worst, replace it
        if new_fitness < worst_fitness:
            self.population[worst_idx] = new_harmony.copy()
            self.fitness_values[worst_idx] = new_fitness
            return True

        return False

    def optimize(self):
        """Run Harmony Search Algorithm optimization"""
        # Initialize Harmony Memory with random solutions
        self.initialize_population()

        for iteration in range(self.max_iterations):
            # Improvise a new harmony
            new_harmony = self.improvise_new_harmony()

            # Evaluate the new harmony
            new_fitness = self.fitness_func.calculate_fitness(new_harmony, update_bounds=True)

            # Update Harmony Memory if new harmony is better
            self.update_harmony_memory(new_harmony, new_fitness)

            # Update best solution and track convergence
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class FWA(BaseOptimizer):
    """Firework Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True,
                 m=50, a=0.04, b=0.8, A_hat=40, m_hat=5, digital_twin=None):
        """
        Initialize Firework Algorithm

        Based on the explosion of fireworks in the night sky. Fireworks explode
        to generate sparks, where better fireworks generate more sparks with
        smaller explosion amplitude.

        Args:
            m: Total number of sparks (default: 50)
            a: Constant for controlling minimum explosion sparks (default: 0.04)
            b: Constant for controlling maximum explosion sparks (default: 0.8)
            A_hat: Maximum explosion amplitude (default: 40)
            m_hat: Number of Gaussian mutation sparks (default: 5)
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.m = m            # Total number of sparks
        self.a = a            # Lower bound constant
        self.b = b            # Upper bound constant
        self.A_hat = A_hat    # Maximum amplitude
        self.m_hat = m_hat    # Gaussian mutation sparks
        self.epsilon = 1e-10  # Small constant to avoid division by zero

    def calculate_num_sparks(self, fitness_values):
        """
        Calculate number of sparks for each firework based on fitness

        Better fireworks (lower fitness) generate more sparks

        Args:
            fitness_values: Array of fitness values

        Returns:
            Array of number of sparks for each firework
        """
        # Find max and sum of fitness
        y_max = np.max(fitness_values)
        y_sum = np.sum(y_max - fitness_values) + self.epsilon

        # Calculate number of sparks for each firework
        num_sparks = np.zeros(self.population_size, dtype=int)

        for i in range(self.population_size):
            s_i = self.m * (y_max - fitness_values[i] + self.epsilon) / y_sum

            # Bound the number of sparks
            if s_i < self.a * self.m:
                num_sparks[i] = int(np.round(self.a * self.m))
            elif s_i > self.b * self.m:
                num_sparks[i] = int(np.round(self.b * self.m))
            else:
                num_sparks[i] = int(np.round(s_i))

        return num_sparks

    def calculate_explosion_amplitude(self, fitness_values):
        """
        Calculate explosion amplitude for each firework

        Better fireworks (lower fitness) have smaller explosion amplitude

        Args:
            fitness_values: Array of fitness values

        Returns:
            Array of explosion amplitudes
        """
        # Find min and sum
        y_min = np.min(fitness_values)
        y_sum = np.sum(fitness_values - y_min) + self.epsilon

        # Calculate amplitude for each firework
        amplitudes = np.zeros(self.population_size)

        for i in range(self.population_size):
            amplitudes[i] = self.A_hat * (fitness_values[i] - y_min + self.epsilon) / y_sum

        return amplitudes

    def generate_sparks(self, firework, amplitude, num_sparks):
        """
        Generate explosion sparks for a firework

        Args:
            firework: Current firework position
            amplitude: Explosion amplitude
            num_sparks: Number of sparks to generate

        Returns:
            List of spark positions
        """
        sparks = []

        for _ in range(num_sparks):
            # Randomly select dimensions to explode
            num_dims = np.random.randint(1, self.num_tasks + 1)
            dims = np.random.choice(self.num_tasks, num_dims, replace=False)

            # Create new spark
            spark = firework.copy()

            # Modify selected dimensions
            for dim in dims:
                # Displacement with explosion amplitude
                displacement = amplitude * np.random.uniform(-1, 1)
                new_val = spark[dim] + displacement
                spark[dim] = self.discretize(new_val)

            sparks.append(spark)

        return sparks

    def generate_gaussian_sparks(self, firework):
        """
        Generate Gaussian mutation sparks for exploration

        Args:
            firework: Current firework position

        Returns:
            Gaussian mutated spark
        """
        # Randomly select dimensions
        num_dims = np.random.randint(1, self.num_tasks + 1)
        dims = np.random.choice(self.num_tasks, num_dims, replace=False)

        # Create new spark
        spark = firework.copy()

        # Apply Gaussian mutation
        for dim in dims:
            gaussian_noise = np.random.normal(0, 1)
            new_val = spark[dim] * gaussian_noise
            spark[dim] = self.discretize(new_val)

        return spark

    def select_next_generation(self, all_candidates, all_fitness, num_keep):
        """
        Select fireworks for next generation using distance-based selection

        Args:
            all_candidates: All candidate solutions (fireworks + sparks)
            all_fitness: Fitness values for all candidates
            num_keep: Number of solutions to keep

        Returns:
            Selected population and their fitness values
        """
        # Always keep the best solution
        best_idx = np.argmin(all_fitness)
        selected_pop = [all_candidates[best_idx]]
        selected_fitness = [all_fitness[best_idx]]

        # Remove best from candidates
        remaining_indices = [i for i in range(len(all_candidates)) if i != best_idx]

        # Select remaining based on distance (for diversity)
        while len(selected_pop) < num_keep and len(remaining_indices) > 0:
            # Calculate distances from selected population
            distances = np.zeros(len(remaining_indices))

            for idx, candidate_idx in enumerate(remaining_indices):
                candidate = all_candidates[candidate_idx]
                # Sum of distances to all selected solutions
                total_distance = 0
                for selected in selected_pop:
                    # Hamming distance for discrete solutions
                    total_distance += np.sum(candidate != selected)
                distances[idx] = total_distance

            # Select candidate with maximum distance (most diverse)
            if np.sum(distances) > 0:
                probabilities = distances / np.sum(distances)
                selected_relative_idx = np.random.choice(len(remaining_indices), p=probabilities)
            else:
                selected_relative_idx = np.random.randint(0, len(remaining_indices))

            selected_idx = remaining_indices[selected_relative_idx]
            selected_pop.append(all_candidates[selected_idx])
            selected_fitness.append(all_fitness[selected_idx])

            # Remove selected from remaining
            remaining_indices.pop(selected_relative_idx)

        return np.array(selected_pop), np.array(selected_fitness)

    def optimize(self):
        """Run Firework Algorithm optimization"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            # Calculate number of sparks and explosion amplitude for each firework
            num_sparks_array = self.calculate_num_sparks(self.fitness_values)
            amplitudes = self.calculate_explosion_amplitude(self.fitness_values)

            # Generate explosion sparks for all fireworks
            all_candidates = list(self.population)
            all_fitness = list(self.fitness_values)

            for i in range(self.population_size):
                # Generate explosion sparks
                sparks = self.generate_sparks(
                    self.population[i],
                    amplitudes[i],
                    num_sparks_array[i]
                )

                # Evaluate sparks
                for spark in sparks:
                    fitness = self.fitness_func.calculate_fitness(spark, update_bounds=True)
                    all_candidates.append(spark)
                    all_fitness.append(fitness)

            # Generate Gaussian mutation sparks
            for _ in range(self.m_hat):
                # Select random firework for Gaussian mutation
                firework_idx = np.random.randint(0, self.population_size)
                gaussian_spark = self.generate_gaussian_sparks(self.population[firework_idx])
                fitness = self.fitness_func.calculate_fitness(gaussian_spark, update_bounds=True)
                all_candidates.append(gaussian_spark)
                all_fitness.append(fitness)

            # Select next generation
            self.population, self.fitness_values = self.select_next_generation(
                all_candidates,
                all_fitness,
                self.population_size
            )

            # Update best solution and track convergence
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class AIA(BaseOptimizer):
    """Artificial Immune Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True,
                 clone_rate=10, mutation_rate=0.3, digital_twin=None):
        """
        Initialize Artificial Immune Algorithm

        Based on the biological immune system's ability to recognize and eliminate
        antigens. Uses clonal selection and hypermutation mechanisms.

        Args:
            clone_rate: Number of clones per antibody (default: 10)
            mutation_rate: Mutation rate for clones (default: 0.3)
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.clone_rate = clone_rate
        self.mutation_rate = mutation_rate

    def clone_and_mutate(self, antibody, fitness):
        """
        Clone an antibody and apply hypermutation
        Better antibodies get more clones with less mutation

        Args:
            antibody: Antibody to clone
            fitness: Fitness of the antibody

        Returns:
            List of mutated clones
        """
        clones = []

        for _ in range(self.clone_rate):
            clone = antibody.copy()

            # Mutation rate inversely proportional to fitness (for minimization)
            # Better solutions (lower fitness) have lower mutation rate
            adaptive_rate = self.mutation_rate * (1 + fitness / (np.max(self.fitness_values) + 1e-10))

            for j in range(self.num_tasks):
                if np.random.random() < adaptive_rate:
                    clone[j] = np.random.randint(0, 4)

            clones.append(clone)

        return clones

    def optimize(self):
        """Run Artificial Immune Algorithm optimization"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            all_clones = []
            all_clone_fitness = []

            # Clone and mutate each antibody
            for i in range(self.population_size):
                clones = self.clone_and_mutate(self.population[i], self.fitness_values[i])

                for clone in clones:
                    fitness = self.fitness_func.calculate_fitness(clone, update_bounds=True)
                    all_clones.append(clone)
                    all_clone_fitness.append(fitness)

            # Select best clones to replace worst antibodies
            if len(all_clones) > 0:
                best_clone_idx = np.argmin(all_clone_fitness)
                worst_antibody_idx = np.argmax(self.fitness_values)

                if all_clone_fitness[best_clone_idx] < self.fitness_values[worst_antibody_idx]:
                    self.population[worst_antibody_idx] = all_clones[best_clone_idx]
                    self.fitness_values[worst_antibody_idx] = all_clone_fitness[best_clone_idx]

            # Update best solution and track convergence
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class CS(BaseOptimizer):
    """Cuckoo Search Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True,
                 pa=0.25, beta=1.5, digital_twin=None):
        """
        Initialize Cuckoo Search Algorithm

        Based on the brood parasitism behavior of cuckoo birds. Uses Levy flights
        for exploration and abandons worst nests with probability pa.

        Args:
            pa: Probability of abandoned nests (default: 0.25)
            beta: Levy flight parameter (default: 1.5)
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.pa = pa
        self.beta = beta

    def levy_flight(self):
        """Generate Levy flight step using Mantegna's method"""
        sigma = (math.gamma(1 + self.beta) * np.sin(np.pi * self.beta / 2) /
                (math.gamma((1 + self.beta) / 2) * self.beta * 2 ** ((self.beta - 1) / 2))) ** (1 / self.beta)

        u = np.random.normal(0, sigma, self.num_tasks)
        v = np.random.normal(0, 1, self.num_tasks)

        step = u / (np.abs(v) ** (1 / self.beta))
        return step

    def optimize(self):
        """Run Cuckoo Search optimization"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            # Get a cuckoo randomly by Levy flights
            cuckoo_idx = np.random.randint(0, self.population_size)
            cuckoo = self.population[cuckoo_idx].copy()

            # Levy flight
            step = self.levy_flight()
            new_cuckoo = np.zeros(self.num_tasks, dtype=int)
            for j in range(self.num_tasks):
                new_cuckoo[j] = self.discretize(cuckoo[j] + step[j])

            # Evaluate new solution
            new_fitness = self.fitness_func.calculate_fitness(new_cuckoo, update_bounds=True)

            # Choose a random nest
            random_nest_idx = np.random.randint(0, self.population_size)

            # Replace if better
            if new_fitness < self.fitness_values[random_nest_idx]:
                self.population[random_nest_idx] = new_cuckoo
                self.fitness_values[random_nest_idx] = new_fitness

            # Abandon worst nests with probability pa
            worst_nests = np.argsort(self.fitness_values)[-int(self.pa * self.population_size):]

            for nest_idx in worst_nests:
                if np.random.random() < self.pa:
                    self.population[nest_idx] = np.random.randint(0, 4, size=self.num_tasks)
                    self.fitness_values[nest_idx] = self.fitness_func.calculate_fitness(
                        self.population[nest_idx], update_bounds=True
                    )

            # Update best solution and track convergence
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class FA(BaseOptimizer):
    """Firefly Algorithm"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True,
                 alpha=0.5, beta0=1.0, gamma=1.0, digital_twin=None):
        """
        Initialize Firefly Algorithm

        Based on the flashing behavior of fireflies. Fireflies are attracted to
        brighter fireflies (better solutions).

        Args:
            alpha: Randomization parameter (default: 0.5)
            beta0: Attractiveness at distance 0 (default: 1.0)
            gamma: Light absorption coefficient (default: 1.0)
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.alpha = alpha
        self.beta0 = beta0
        self.gamma = gamma

    def distance(self, firefly1, firefly2):
        """Calculate Hamming distance between two fireflies"""
        return np.sum(firefly1 != firefly2)

    def attractiveness(self, distance):
        """Calculate attractiveness based on distance"""
        return self.beta0 * np.exp(-self.gamma * distance ** 2)

    def optimize(self):
        """Run Firefly Algorithm optimization"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            # Decrease alpha over iterations
            alpha_t = self.alpha * (0.95 ** iteration)

            # Move fireflies
            for i in range(self.population_size):
                for j in range(self.population_size):
                    # If firefly j is brighter (better fitness)
                    if self.fitness_values[j] < self.fitness_values[i]:
                        # Calculate distance
                        r = self.distance(self.population[i], self.population[j])

                        # Calculate attractiveness
                        beta = self.attractiveness(r)

                        # Move firefly i towards j
                        new_solution = np.zeros(self.num_tasks, dtype=int)
                        for k in range(self.num_tasks):
                            # Attraction term + randomization
                            move = beta * (self.population[j][k] - self.population[i][k]) + \
                                   alpha_t * (np.random.random() - 0.5)
                            new_solution[k] = self.discretize(self.population[i][k] + move)

                        # Evaluate and update
                        new_fitness = self.fitness_func.calculate_fitness(new_solution, update_bounds=True)
                        if new_fitness < self.fitness_values[i]:
                            self.population[i] = new_solution
                            self.fitness_values[i] = new_fitness

            # Update best solution and track convergence
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class BFO(BaseOptimizer):
    """Bacteria Foraging Optimization"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True,
                 Nc=4, Ns=4, Ped=0.25, digital_twin=None):
        """
        Initialize Bacteria Foraging Optimization

        Based on the foraging behavior of E. coli bacteria. Includes chemotaxis,
        reproduction, and elimination-dispersal events.

        Args:
            Nc: Number of chemotactic steps (default: 4)
            Ns: Number of swim steps (default: 4)
            Ped: Probability of elimination-dispersal (default: 0.25)
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)
        self.Nc = Nc
        self.Ns = Ns
        self.Ped = Ped
        self.C = 1  # Step size

    def chemotaxis(self):
        """Chemotaxis: Movement and foraging"""
        for i in range(self.population_size):
            # Random direction (tumble)
            delta = np.random.uniform(-1, 1, self.num_tasks)
            delta_norm = np.linalg.norm(delta)

            if delta_norm > 0:
                delta = delta / delta_norm

            # Move in direction
            new_solution = np.zeros(self.num_tasks, dtype=int)
            for j in range(self.num_tasks):
                new_solution[j] = self.discretize(self.population[i][j] + self.C * delta[j])

            new_fitness = self.fitness_func.calculate_fitness(new_solution, update_bounds=True)

            # If better, swim in same direction
            if new_fitness < self.fitness_values[i]:
                self.population[i] = new_solution
                self.fitness_values[i] = new_fitness

                # Swimming
                for _ in range(self.Ns):
                    swim_solution = np.zeros(self.num_tasks, dtype=int)
                    for j in range(self.num_tasks):
                        swim_solution[j] = self.discretize(self.population[i][j] + self.C * delta[j])

                    swim_fitness = self.fitness_func.calculate_fitness(swim_solution, update_bounds=True)

                    if swim_fitness < self.fitness_values[i]:
                        self.population[i] = swim_solution
                        self.fitness_values[i] = swim_fitness
                    else:
                        break

    def reproduction(self):
        """Reproduction: Healthier bacteria survive"""
        # Sort by fitness
        sorted_indices = np.argsort(self.fitness_values)

        # Keep best half, eliminate worst half
        half = self.population_size // 2

        # Best bacteria reproduce
        for i in range(half, self.population_size):
            self.population[i] = self.population[sorted_indices[i - half]].copy()
            self.fitness_values[i] = self.fitness_values[sorted_indices[i - half]]

    def elimination_dispersal(self):
        """Elimination-dispersal: Random bacteria eliminated and dispersed"""
        for i in range(self.population_size):
            if np.random.random() < self.Ped:
                self.population[i] = np.random.randint(0, 4, size=self.num_tasks)
                self.fitness_values[i] = self.fitness_func.calculate_fitness(
                    self.population[i], update_bounds=True
                )

    def optimize(self):
        """Run Bacteria Foraging Optimization"""
        self.initialize_population()

        iterations_per_cycle = max(1, self.max_iterations // (self.Nc + 2))

        for iteration in range(self.max_iterations):
            cycle = iteration // iterations_per_cycle

            # Chemotaxis
            if cycle % 3 == 0:
                for _ in range(self.Nc):
                    self.chemotaxis()

            # Reproduction
            elif cycle % 3 == 1:
                self.reproduction()

            # Elimination-dispersal
            else:
                self.elimination_dispersal()

            # Update best solution and track convergence
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


class Rao(BaseOptimizer):
    """Rao Algorithm (Rao-1)"""

    def __init__(self, tasks, population_size=None, max_iterations=None, verbose=True, digital_twin=None):
        """
        Initialize Rao Algorithm

        A simple and powerful metaphor-less algorithm that doesn't require
        algorithm-specific parameters. Uses best and worst solutions to update.
        """
        super().__init__(tasks, population_size, max_iterations, verbose, digital_twin)

    def optimize(self):
        """Run Rao Algorithm optimization"""
        self.initialize_population()

        for iteration in range(self.max_iterations):
            # Find best and worst solutions
            best_idx = np.argmin(self.fitness_values)
            worst_idx = np.argmax(self.fitness_values)

            best_solution = self.population[best_idx]
            worst_solution = self.population[worst_idx]

            # Update each solution
            for i in range(self.population_size):
                new_solution = np.zeros(self.num_tasks, dtype=int)

                for j in range(self.num_tasks):
                    # Rao-1 equation
                    r1 = np.random.random()
                    r2 = np.random.random()

                    new_val = self.population[i][j] + \
                              r1 * (best_solution[j] - self.population[i][j]) - \
                              r2 * (worst_solution[j] - self.population[i][j])

                    new_solution[j] = self.discretize(new_val)

                # Evaluate and greedy selection
                new_fitness = self.fitness_func.calculate_fitness(new_solution, update_bounds=True)

                if new_fitness < self.fitness_values[i]:
                    self.population[i] = new_solution
                    self.fitness_values[i] = new_fitness

            # Update best solution and track convergence
            self.evaluate_population()
            self.convergence_history.append(self.best_fitness)
            self.track_metrics()

            if self.verbose and (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.max_iterations}: Best fitness = {self.best_fitness:.6f}")

        self.update_digital_twin()
        return self.best_solution


if __name__ == "__main__":
    # Test comparison algorithms
    print("Testing Comparison Algorithms")
    print("=" * 70)

    np.random.seed(42)
    Config.NUM_TASKS = 50
    tasks = Config.generate_random_tasks()

    algorithms = [
        ("GWO", GWO(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("SMA", SMA(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("GA", GA(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("WOA", WOA(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("DE", DE(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("ACO", ACO(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("ALO", ALO(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("HSA", HSA(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("FWA", FWA(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("AIA", AIA(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("CS", CS(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("FA", FA(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("BFO", BFO(tasks, population_size=20, max_iterations=30, verbose=False)),
        ("Rao", Rao(tasks, population_size=20, max_iterations=30, verbose=False)),
    ]

    for name, algorithm in algorithms:
        print(f"\n{name}:")
        algorithm.optimize()
        print(f"  Best fitness: {algorithm.best_fitness:.6f}")
