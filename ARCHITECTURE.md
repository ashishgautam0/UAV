# System Architecture

This document describes the architecture of the Energy-Efficient Task Allocation in Digital Twin Enabled UAV Networks system.

---

## Table of Contents

1. [Overview](#overview)
2. [Physical System Architecture](#physical-system-architecture)
3. [Digital Twin Framework](#digital-twin-framework)
4. [Multi-Level Caching System](#multi-level-caching-system)
5. [Optimization Workflow](#optimization-workflow)
6. [Code Structure](#code-structure)
7. [Data Flow](#data-flow)

---

## Overview

The system implements an energy-efficient task allocation framework for UAV networks using a Digital Twin (DT) enabled architecture. The DT maintains real-time virtual replicas of all physical network components, providing accurate system information to the Jaya optimization algorithm for informed decision-making.

### Key Components

1. **Physical UAV Network** - 150 UAVs, 3 GBS, MEC servers, Cloud
2. **Digital Twin** - Virtual replicas of all physical components
3. **Multi-Level Cache** - Hierarchical data storage (UAV → GBS → MEC → Cloud)
4. **Jaya Algorithm** - Parameter-free optimization for task allocation
5. **Comparison Algorithms** - GWO, PSO, GA, WOA

---

## Physical System Architecture

### Network Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Server                            │
│  - Computing: 50 GHz CPU                                     │
│  - Storage: Unlimited                                        │
│  - Access: Global                                            │
└────────────────────────┬────────────────────────────────────┘
                         │ Backhaul (50ms delay)
                         │
┌────────────────────────┴────────────────────────────────────┐
│              Mobile Edge Computing (MEC) Server              │
│  - Computing: 10 GHz CPU                                     │
│  - Storage: Regional cache                                   │
│  - Aggregates: All GBS in region                            │
└────────────────────────┬────────────────────────────────────┘
                         │ Forwarding (10ms delay)
           ┌─────────────┼─────────────┐
           │             │             │
    ┌──────┴──────┐ ┌───┴─────┐ ┌────┴──────┐
    │   GBS 0     │ │  GBS 1  │ │   GBS 2   │
    │ 10 GHz CPU  │ │10 GHz   │ │ 10 GHz    │
    │ Local Cache │ │Local    │ │ Local     │
    └──────┬──────┘ └───┬─────┘ └────┬──────┘
           │            │             │
    ┌──────┴────┐  ┌────┴───┐   ┌────┴────┐
    │ UAVs 0-49 │  │UAVs    │   │ UAVs    │
    │ 1 GHz CPU │  │50-99   │   │ 100-149 │
    │ Map Cache │  │1 GHz   │   │ 1 GHz   │
    └───────────┘  └────────┘   └─────────┘
```

### Component Specifications

| Component | Count | CPU Frequency | Storage | Special Features |
|-----------|-------|---------------|---------|------------------|
| UAVs | 150 | 1 GHz | Static maps | Mobile, battery-powered |
| GBS | 3 | 10 GHz | Local env data | 500m coverage radius |
| MEC | 1 | 10 GHz | Regional cache | Aggregates GBS data |
| Cloud | 1 | 50 GHz | Unlimited | Always available |

### Task Execution Locations

Each task can be executed at one of four locations:

| Location | Code | CPU Freq | Energy Profile | Use Case |
|----------|------|----------|----------------|----------|
| **Local (UAV)** | 0 | 1 GHz | High computation, no transmission | Small, urgent tasks |
| **GBS** | 1 | 10 GHz | Balanced | Most common, moderate tasks |
| **MEC** | 2 | 10 GHz | Higher latency than GBS | When GBS is overloaded |
| **Cloud** | 3 | 50 GHz | High transmission+hover | Complex, non-urgent tasks |

---

## Digital Twin Framework

### Purpose

The Digital Twin maintains synchronized virtual replicas of all physical components, enabling:

1. **Real-time monitoring** - Track UAV locations, battery levels, network conditions
2. **Predictive optimization** - Use current state for allocation decisions
3. **System updates** - Reflect task execution outcomes
4. **Historical tracking** - Maintain task execution history

### Digital Twin Components

```python
class DigitalTwin:
    - Physical replicas:
        - uavs[150]          # UAV virtual replicas
        - gbs_nodes[3]       # GBS virtual replicas
        - mec_servers[1]     # MEC virtual replicas
        - cloud              # Cloud virtual replica

    - System state:
        - current_time       # Simulation time
        - task_history       # Past allocations
        - energy_consumed    # Historical energy
        - network_conditions # Link quality

    - Task management:
        - tasks              # Task parameters (D, C, D_out)
        - task_to_uav_mapping # Which UAV generated which task
```

### Virtual Replica Classes

#### UAV Virtual Replica
```python
class UAV:
    - uav_id: int
    - location: (x, y, z)
    - battery_level: float (0-100%)
    - assigned_gbs: int
    - onboard_cache: dict
    - computing_capacity: 1 GHz
    - tasks: list[task_id]
```

#### GBS Virtual Replica
```python
class GBS:
    - gbs_id: int
    - location: (x, y)
    - coverage_radius: 500m
    - computing_capacity: 10 GHz
    - cache: dict (local environmental data)
    - connected_uavs: list[uav_id]
    - task_load: int
```

#### MEC Virtual Replica
```python
class MECServer:
    - mec_id: int
    - associated_gbs_ids: list[gbs_id]
    - computing_capacity: 10 GHz
    - cache: dict (aggregated from GBS)
    - task_load: int
```

#### Cloud Virtual Replica
```python
class CloudServer:
    - computing_capacity: 50 GHz
    - cache: dict (complete repository)
    - task_load: int
```

---

## Multi-Level Caching System

### Cache Hierarchy

```
Level 1: UAV Cache
    ↓ (cache miss)
Level 2: GBS Cache (assigned GBS)
    ↓ (cache miss)
Level 3: MEC Cache (aggregated region)
    ↓ (cache miss)
Level 4: Cloud (always has data)
```

### Cache Content Strategy

| Level | Content Type | Examples | Size |
|-------|--------------|----------|------|
| **UAV** | Static, unchanging data | Maps, terrain | ~5 entries |
| **GBS** | Local environmental data | Weather, obstacles | ~10 entries |
| **MEC** | Regional aggregation | All GBS caches combined | ~30 entries |
| **Cloud** | Complete repository | Everything | Unlimited |

### Cache Lookup Process

```python
def lookup(task_id, uav_id):
    # 1. Check UAV cache
    if uav.check_cache(task_id):
        return (LOC_LOCAL, cache_hit=True)

    # 2. Check assigned GBS cache
    if gbs.check_cache(task_id):
        return (LOC_GBS, cache_hit=True)

    # 3. Check MEC cache
    if mec.check_cache(task_id):
        return (LOC_MEC, cache_hit=True)

    # 4. Cloud always has it
    return (LOC_CLOUD, cache_hit=True)
```

---

## Optimization Workflow

### Complete Workflow with Digital Twin

```
┌─────────────────────────────────────────────────────────┐
│ 1. INITIALIZATION                                        │
│    - Create Digital Twin with 150 UAVs, 3 GBS           │
│    - Initialize multi-level cache system                │
│    - Generate 520 task parameters                       │
│    - Assign tasks to UAVs                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. DIGITAL TWIN PROVIDES SYSTEM STATE                   │
│    - Current UAV locations and battery levels           │
│    - GBS task loads and available capacity              │
│    - Network conditions (transmission rates, quality)   │
│    - Cache status at all levels                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. JAYA ALGORITHM OPTIMIZATION                          │
│    Input: Task parameters from Digital Twin             │
│                                                          │
│    Iteration loop (200 iterations):                     │
│    ┌──────────────────────────────────────────┐        │
│    │ a. Evaluate fitness for each solution    │        │
│    │    - Calculate total energy consumption  │        │
│    │    - Calculate load imbalance across GBS│        │
│    │    - Combine: F = 0.6×f̂₁ + 0.4×f̂₂      │        │
│    │                                           │        │
│    │ b. Identify best and worst solutions     │        │
│    │                                           │        │
│    │ c. Update each solution using Jaya eq:   │        │
│    │    X_new = X + r₁(X_best - |X|)         │        │
│    │                - r₂(X_worst - |X|)       │        │
│    │                                           │        │
│    │ d. Discretize to {0,1,2,3}               │        │
│    │                                           │        │
│    │ e. Greedy selection (keep if better)     │        │
│    └──────────────────────────────────────────┘        │
│                                                          │
│    Output: Best task allocation solution                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. TASK EXECUTION (Simulated)                           │
│    - Tasks execute at assigned locations                │
│    - Energy consumed based on location and task params  │
│    - Results returned to requesting UAVs                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. DIGITAL TWIN UPDATE                                  │
│    - Update GBS task loads                              │
│    - Update MEC and Cloud task loads                    │
│    - Record energy breakdown                            │
│    - Store task execution history                       │
│    - Advance simulation time                            │
└─────────────────────────────────────────────────────────┘
```

### Integration Points

The Digital Twin is integrated at two key points:

1. **Before Optimization** - Provides current system state and task parameters
2. **After Optimization** - Updated with execution results

```python
# In main.py
digital_twin = DigitalTwin(num_uavs=150, num_gbs=3, num_tasks=520)
tasks = digital_twin.generate_tasks()

# Run Jaya with Digital Twin
jaya = JayaAlgorithm(tasks, digital_twin=digital_twin)
best_solution = jaya.optimize()

# Digital Twin automatically updated in optimize() method
# via: digital_twin.update_from_solution(solution, energy_breakdown)
```

---

## Code Structure

### File Organization

```
D:\Projects\UAV\
│
├── config.py                    # System configuration and parameters
│   └── Config class (NUM_TASKS=520, NUM_GBS=3, NUM_UAVS=150)
│
├── uav.py                       # Physical component classes
│   ├── UAV class
│   ├── GBS class
│   ├── MECServer class
│   ├── CloudServer class
│   └── CacheSystem class
│
├── digital_twin.py              # Digital Twin framework
│   └── DigitalTwin class
│       ├── initialize_physical_system()
│       ├── generate_tasks()
│       ├── get_system_state()
│       └── update_from_solution()
│
├── energy_model.py              # Energy consumption calculations
│   └── EnergyModel class
│       ├── local_energy()
│       ├── gbs_energy()
│       ├── mec_energy()
│       └── cloud_energy()
│
├── fitness.py                   # Multi-objective fitness function
│   └── FitnessFunction class
│       ├── calculate_fitness()
│       ├── calculate_load_imbalance()
│       └── get_allocation_statistics()
│
├── jaya.py                      # Jaya algorithm
│   └── JayaAlgorithm class
│       ├── initialize_population()
│       ├── update_solution()
│       └── optimize()
│
├── comparison_algorithms.py     # Other metaheuristic algorithms
│   ├── BaseOptimizer class
│   ├── GWO class
│   ├── PSO class
│   ├── GA class
│   └── WOA class
│
├── utils.py                     # Visualization and analysis
│   ├── plot_convergence()
│   ├── plot_allocation_distribution()
│   ├── plot_energy_breakdown()
│   └── print_summary_table()
│
├── main.py                      # Main simulation orchestrator
│   ├── run_single_algorithm()
│   ├── run_comparison()
│   └── main()
│
├── readme.md                    # Algorithm documentation
└── ARCHITECTURE.md             # This file
```

### Key Dependencies

```python
config.py
    ↓
uav.py → digital_twin.py
    ↓           ↓
energy_model.py → fitness.py → jaya.py
                                  ↓
                            comparison_algorithms.py
                                  ↓
                               main.py → utils.py
```

---

## Data Flow

### Task Generation Flow

```
User specifies: num_tasks=520, num_gbs=3
    ↓
DigitalTwin.__init__()
    ↓
Create 150 UAV instances
Create 3 GBS instances
Create 1 MEC instance
Create 1 Cloud instance
    ↓
generate_tasks()
    ↓
Generate 520 tasks with:
    - D_i: Input data size (100-500 KB)
    - C_i: CPU cycles (100-1000 Megacycles)
    - D_out: Output data size (20% of input)
    ↓
Assign tasks to UAVs (evenly distributed)
    ↓
Return tasks to optimization algorithm
```

### Optimization Flow

```
tasks → JayaAlgorithm.optimize()
           ↓
    Initialize population (50 solutions)
           ↓
    For each iteration (200 times):
           ↓
    ┌──────────────────────────────────┐
    │ For each solution:                │
    │   Calculate energy (f₁)          │
    │   Calculate load imbalance (f₂)  │
    │   Normalize both                  │
    │   F = 0.6×f̂₁ + 0.4×f̂₂           │
    └──────────────────────────────────┘
           ↓
    Find best and worst solutions
           ↓
    Update each solution using Jaya equation
           ↓
    Greedy selection
           ↓
    Return best_solution
           ↓
    Update Digital Twin
```

### Energy Calculation Flow

```
solution = [x₀, x₁, ..., x₅₁₉] where xᵢ ∈ {0,1,2,3}
    ↓
For each task i:
    ↓
    If xᵢ = 0 (Local):
        E = κ × Cᵢ × f_uav²

    If xᵢ = 1 (GBS):
        E_tx = (P_tx × Dᵢ) / Rᵢ
        E_hover = P_hover × (Dᵢ/Rᵢ + Cᵢ/f_gbs + D_out/Rᵢ)
        E = E_tx + E_hover

    If xᵢ = 2 (MEC):
        E_tx = (P_tx × Dᵢ) / Rᵢ
        E_hover = P_hover × (Dᵢ/Rᵢ + t_forward + Cᵢ/f_mec + D_out/Rᵢ)
        E = E_tx + E_hover

    If xᵢ = 3 (Cloud):
        E_tx = (P_tx × Dᵢ) / Rᵢ
        E_hover = P_hover × (Dᵢ/Rᵢ + t_backhaul + Cᵢ/f_cloud + D_out/Rᵢ)
        E = E_tx + E_hover
    ↓
Total Energy = Σ Eᵢ (sum over all tasks)
```

---

## Summary

This architecture implements a complete Digital Twin enabled UAV network with:

1. ✅ **Physical System** - 150 UAVs, 3 GBS, MEC, Cloud
2. ✅ **Digital Twin** - Real-time virtual replicas of all components
3. ✅ **Multi-Level Caching** - Hierarchical data storage and retrieval
4. ✅ **Energy Model** - Accurate energy calculations for all execution locations
5. ✅ **Jaya Optimization** - Parameter-free task allocation
6. ✅ **System Updates** - Digital Twin reflects execution outcomes

The system enables energy-efficient task allocation while maintaining balanced resource utilization across the UAV network infrastructure.
