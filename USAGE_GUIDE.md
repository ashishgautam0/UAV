# UAV Task Allocation - Usage Guide

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
UAV/
├── config.py                    # System configuration and parameters
├── energy_model.py              # Energy consumption calculations
├── fitness.py                   # Fitness function (energy + load balance)
├── jaya.py                      # Jaya algorithm implementation
├── comparison_algorithms.py     # GWO, PSO, GA, WOA implementations
├── utils.py                     # Visualization and result utilities
├── main.py                      # Main simulation script
├── requirements.txt             # Python dependencies
└── readme.md                    # Algorithm documentation
```

## Quick Start

### 1. Run a Quick Test
```bash
python main.py
```

This runs a quick test with:
- 100 tasks
- 3 GBS
- 30 population size
- 20 iterations

### 2. Run Full Simulation

Edit `main.py` and uncomment the full simulation section:

```python
# In main.py, uncomment these lines:
print("\n2. Running full simulation (500 tasks, 200 iterations)...")
full_results = run_comparison(
    num_tasks=500,
    num_gbs=4,
    population_size=50,
    max_iterations=200,
    seed=42
)

# Print results
print_summary_table(full_results, algorithm_names)

# Save results
save_results_to_json(full_results)

# Generate plots
print("\nGenerating visualization plots...")
plot_all_results(full_results, algorithm_names)
```

Then run:
```bash
python main.py
```

## Testing Individual Components

### Test Configuration
```bash
python config.py
```

### Test Energy Model
```bash
python energy_model.py
```

### Test Fitness Function
```bash
python fitness.py
```

### Test Jaya Algorithm
```bash
python jaya.py
```

### Test Comparison Algorithms
```bash
python comparison_algorithms.py
```

### Test Utilities
```bash
python utils.py
```

## Customization

### 1. Modify Parameters in config.py

```python
# Task and GBS parameters
Config.NUM_TASKS = 500      # Number of tasks
Config.NUM_GBS = 4          # Number of Ground Base Stations

# Algorithm parameters
Config.POPULATION_SIZE = 50
Config.MAX_ITERATIONS = 200

# Fitness weights
Config.W1 = 0.6             # Energy weight (0.6 = prioritize energy)
Config.W2 = 0.4             # Load balance weight (1 - W1)
```

### 2. Run Custom Simulation

Create a custom script:

```python
from config import Config
from jaya import JayaAlgorithm
import numpy as np

# Set parameters
Config.NUM_TASKS = 300
Config.NUM_GBS = 5

# Generate tasks
tasks = Config.generate_random_tasks()

# Run Jaya
jaya = JayaAlgorithm(tasks, population_size=40, max_iterations=100)
best_solution = jaya.optimize()
jaya.print_results()
```

### 3. Compare Specific Algorithms

```python
from comparison_algorithms import GWO, PSO
from config import Config

tasks = Config.generate_random_tasks(200)

# Run GWO
gwo = GWO(tasks, population_size=30, max_iterations=50)
gwo.optimize()
print(f"GWO Best Fitness: {gwo.best_fitness}")

# Run PSO
pso = PSO(tasks, population_size=30, max_iterations=50, c1=2.0, c2=2.0, w=0.7)
pso.optimize()
print(f"PSO Best Fitness: {pso.best_fitness}")
```

## Output Files

When running the full simulation, the following files are generated:

1. **JSON Results**: `results_YYYYMMDD_HHMMSS.json`
   - Contains detailed results for all algorithms
   - Can be loaded for later analysis

2. **Convergence Plot**: `convergence_YYYYMMDD_HHMMSS.png`
   - Shows fitness convergence over iterations
   - Compares all algorithms

3. **Allocation Plot**: `allocation_YYYYMMDD_HHMMSS.png`
   - Shows task allocation distribution
   - Percentage of tasks at each location

4. **Energy Plot**: `energy_YYYYMMDD_HHMMSS.png`
   - Shows energy consumption breakdown
   - Energy by execution location

5. **Comparison Table**: `comparison_table_YYYYMMDD_HHMMSS.png`
   - Summary table of all metrics

## Understanding the Results

### Fitness Value
- **Lower is better**
- Combines energy consumption and load imbalance
- F = 0.6 × energy_normalized + 0.4 × load_imbalance_normalized

### Energy Consumption
- **Lower is better**
- Total energy in Joules
- Includes transmission, computation, and hovering energy

### Load Imbalance
- **Lower is better**
- Standard deviation of task distribution across GBS
- 0 = perfectly balanced

### Execution Locations
- **Local (0)**: Executed at UAV (high energy, no transmission)
- **GBS (1)**: Executed at associated GBS (balanced)
- **MEC (2)**: Executed at neighboring GBS (forwarding delay)
- **Cloud (3)**: Executed at cloud (high latency, low computation energy)

## Algorithm Parameters

### Jaya (Only 2 parameters!)
- Population size
- Max iterations

### GWO (Grey Wolf Optimizer)
- Population size
- Max iterations
- a: linearly decreases from 2 to 0

### PSO (Particle Swarm Optimization)
- Population size
- Max iterations
- c1: cognitive parameter (default 2.0)
- c2: social parameter (default 2.0)
- w: inertia weight (default 0.7)

### GA (Genetic Algorithm)
- Population size
- Max iterations
- crossover_rate (default 0.8)
- mutation_rate (default 0.1)

### WOA (Whale Optimization Algorithm)
- Population size
- Max iterations
- a: linearly decreases from 2 to 0
- b: logarithmic spiral shape (default 1)

## Tips for Best Results

1. **Increase iterations for better convergence**: 200+ iterations recommended
2. **Larger population for complex problems**: 50+ for 500 tasks
3. **Adjust energy weight (W1)** based on priorities:
   - W1 = 0.7-0.8: Prioritize energy efficiency
   - W1 = 0.5: Equal priority
   - W1 = 0.3-0.4: Prioritize load balance

4. **Run multiple times with different seeds** for statistical significance
5. **Use sensitivity analysis** to understand parameter effects

## Troubleshooting

### Memory Issues
- Reduce NUM_TASKS or POPULATION_SIZE
- Run algorithms sequentially instead of all at once

### Slow Execution
- Reduce MAX_ITERATIONS
- Use smaller population size for testing
- Run quick test first

### Import Errors
- Ensure all files are in the same directory
- Check that requirements.txt is installed

## Example Output

```
==================================================================
UAV TASK ALLOCATION - ALGORITHM COMPARISON
==================================================================
Number of tasks: 500
Number of GBS: 4
Population size: 50
Max iterations: 200
Energy weight (w₁): 0.6
Load balance weight (w₂): 0.4
Transmission rate: 25.42 Mbps
==================================================================

======================================================================
Running Jaya
======================================================================
Population initialized: 50 solutions
Best initial fitness: 0.542315
Iteration 20/200: Best fitness = 0.421873
Iteration 40/200: Best fitness = 0.398654
...
Iteration 200/200: Best fitness = 0.312456

Jaya completed in 45.23 seconds
Best fitness: 0.312456

====================================================================================================
ALGORITHM PERFORMANCE COMPARISON
====================================================================================================
Algorithm       Fitness    Energy (J) Load Imb.    Local %    GBS %    MEC %  Cloud %
----------------------------------------------------------------------------------------------------
Jaya           0.312456     1234.56    0.8765       15.2      35.6      38.4      10.8
GWO            0.325478     1289.34    0.9123       14.8      34.2      39.6      11.4
PSO            0.334521     1312.67    0.9456       13.6      36.8      37.2      12.4
GA             0.341234     1345.23    0.9834       12.4      38.4      35.8      13.4
WOA            0.329876     1298.45    0.9234       14.2      35.8      38.6      11.4
====================================================================================================

Best overall fitness: Jaya
Best energy efficiency: Jaya
Best load balance: Jaya
====================================================================================================
```
