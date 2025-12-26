"""
Digital Twin for UAV Network
Maintains real-time virtual replicas of physical UAV network components
"""

import numpy as np
import time
from config import Config
from uav import UAV, GBS, MECServer, CloudServer, CacheSystem


class DigitalTwin:
    """
    Digital Twin Framework for UAV Network

    Maintains real-time virtual representations of:
    - UAV locations, battery levels, computing capacity
    - GBS resources and cache status
    - Network link conditions
    - Task allocation and execution status

    The DT provides accurate system information to the optimization algorithm
    and is updated after task execution to reflect current system state.
    """

    def __init__(self, num_uavs=None, num_gbs=None, num_tasks=None):
        """
        Initialize Digital Twin with physical system components

        Args:
            num_uavs: Number of UAVs (default: Config.NUM_UAVS)
            num_gbs: Number of GBS (default: Config.NUM_GBS)
            num_tasks: Number of tasks (default: Config.NUM_TASKS)
        """
        self.num_uavs = num_uavs or Config.NUM_UAVS
        self.num_gbs = num_gbs or Config.NUM_GBS
        self.num_tasks = num_tasks or Config.NUM_TASKS

        # Physical system components (virtual replicas)
        self.uavs = []
        self.gbs_nodes = []
        self.mec_servers = []
        self.cloud = None
        self.cache_system = None

        # System state tracking
        self.current_time = 0.0
        self.task_history = []
        self.energy_consumed = []
        self.network_conditions = {}

        # Task parameters
        self.tasks = None
        self.task_to_uav_mapping = {}  # Maps task_id to uav_id

        # Initialize the system
        self._initialize_physical_system()
        self._initialize_network_conditions()

        print(f"Digital Twin initialized: {self.num_uavs} UAVs, {self.num_gbs} GBS, {self.num_tasks} tasks")

    def _initialize_physical_system(self):
        """Initialize virtual replicas of physical components"""
        # Create UAVs and distribute them across GBS
        print(f"Creating {self.num_uavs} UAV virtual replicas...")
        for i in range(self.num_uavs):
            assigned_gbs = i % self.num_gbs  # Distribute UAVs evenly
            uav = UAV(uav_id=i, assigned_gbs=assigned_gbs)
            self.uavs.append(uav)

        # Create GBS nodes
        print(f"Creating {self.num_gbs} GBS virtual replicas...")
        for i in range(self.num_gbs):
            gbs = GBS(gbs_id=i)
            self.gbs_nodes.append(gbs)

        # Assign UAVs to GBS based on coverage
        for uav in self.uavs:
            gbs = self.gbs_nodes[uav.assigned_gbs]
            gbs.connected_uavs.append(uav.uav_id)

        # Create MEC servers (typically 1-2 MEC servers cover all GBS)
        print(f"Creating MEC server...")
        mec = MECServer(mec_id=0, associated_gbs_ids=list(range(self.num_gbs)))
        self.mec_servers.append(mec)

        # Create Cloud server
        print(f"Creating Cloud server...")
        self.cloud = CloudServer()

        # Initialize cache system
        print(f"Initializing multi-level cache system...")
        self.cache_system = CacheSystem(self.uavs, self.gbs_nodes, self.mec_servers, self.cloud)
        self.cache_system.populate_static_caches()

    def _initialize_network_conditions(self):
        """Initialize network conditions and communication parameters"""
        self.network_conditions = {
            'transmission_rate': Config.calculate_transmission_rate(),
            'bandwidth': Config.BANDWIDTH,
            'noise_power': Config.NOISE_POWER,
            'quality': 'good',  # good, moderate, poor
            'congestion': 'low'  # low, medium, high
        }

    def generate_tasks(self, tasks=None):
        """
        Generate task parameters and assign to UAVs

        Args:
            tasks: Pre-generated tasks (if None, generates new tasks)

        Returns:
            Task parameters dictionary
        """
        if tasks is None:
            print(f"Generating {self.num_tasks} task parameters...")
            self.tasks = Config.generate_random_tasks(self.num_tasks)
        else:
            self.tasks = tasks

        # Assign tasks to UAVs (distribute evenly)
        print(f"Assigning tasks to UAVs...")
        for task_id in range(self.num_tasks):
            uav_id = task_id % self.num_uavs
            self.task_to_uav_mapping[task_id] = uav_id
            self.uavs[uav_id].tasks.append(task_id)

        return self.tasks

    def get_system_state(self):
        """
        Get complete system state for optimization algorithm

        Returns:
            Dictionary containing current state of all components
        """
        state = {
            'timestamp': self.current_time,
            'uavs': [uav.get_state() for uav in self.uavs],
            'gbs': [gbs.get_state() for gbs in self.gbs_nodes],
            'mec': [mec.get_state() for mec in self.mec_servers],
            'cloud': self.cloud.get_state(),
            'network': self.network_conditions,
            'tasks': self.tasks,
            'task_to_uav': self.task_to_uav_mapping
        }
        return state

    def update_from_solution(self, solution, energy_breakdown):
        """
        Update Digital Twin based on task allocation solution

        This simulates task execution and updates system state accordingly

        Args:
            solution: Array of execution locations for all tasks
            energy_breakdown: Energy consumed by location type
        """
        print(f"\nUpdating Digital Twin with task allocation results...")

        # Update task loads for each GBS
        gbs_task_counts = {i: 0 for i in range(self.num_gbs)}

        for task_id, location in enumerate(solution):
            location = int(location)
            uav_id = self.task_to_uav_mapping[task_id]
            uav = self.uavs[uav_id]

            # Count tasks assigned to each GBS
            if location == Config.LOC_GBS:
                gbs_task_counts[uav.assigned_gbs] += 1

            # Update energy consumption (simplified)
            # In reality, would use actual energy per task
            avg_energy = sum(energy_breakdown.values()) / len(solution)
            self.energy_consumed.append(avg_energy)

        # Update GBS task loads
        for gbs_id, count in gbs_task_counts.items():
            self.gbs_nodes[gbs_id].update_task_load(count)

        # Update MEC and Cloud loads
        mec_tasks = sum(1 for loc in solution if int(loc) == Config.LOC_MEC)
        cloud_tasks = sum(1 for loc in solution if int(loc) == Config.LOC_CLOUD)

        if self.mec_servers:
            self.mec_servers[0].task_load = mec_tasks
        self.cloud.task_load = cloud_tasks

        # Record task execution in history
        self.task_history.append({
            'timestamp': self.current_time,
            'solution': solution.copy(),
            'energy_breakdown': energy_breakdown.copy()
        })

        # Advance time
        self.current_time += 1.0

        print(f"Digital Twin updated at t={self.current_time}")
        print(f"  GBS loads: {[gbs.task_load for gbs in self.gbs_nodes]}")
        print(f"  MEC load: {self.mec_servers[0].task_load if self.mec_servers else 0}")
        print(f"  Cloud load: {self.cloud.task_load}")

    def get_allocation_statistics(self):
        """Get statistics about current task allocation"""
        if not self.task_history:
            return None

        latest = self.task_history[-1]
        solution = latest['solution']

        stats = {
            'local_count': sum(1 for loc in solution if int(loc) == Config.LOC_LOCAL),
            'gbs_count': sum(1 for loc in solution if int(loc) == Config.LOC_GBS),
            'mec_count': sum(1 for loc in solution if int(loc) == Config.LOC_MEC),
            'cloud_count': sum(1 for loc in solution if int(loc) == Config.LOC_CLOUD),
            'total_tasks': len(solution)
        }

        # Calculate percentages
        stats['local_pct'] = 100 * stats['local_count'] / stats['total_tasks']
        stats['gbs_pct'] = 100 * stats['gbs_count'] / stats['total_tasks']
        stats['mec_pct'] = 100 * stats['mec_count'] / stats['total_tasks']
        stats['cloud_pct'] = 100 * stats['cloud_count'] / stats['total_tasks']

        return stats

    def monitor_uav_batteries(self):
        """Monitor and report UAV battery levels"""
        low_battery_uavs = [uav for uav in self.uavs if uav.battery_level < 30]

        if low_battery_uavs:
            print(f"\nWarning: {len(low_battery_uavs)} UAVs have low battery (<30%)")
            for uav in low_battery_uavs[:5]:  # Show first 5
                print(f"  UAV {uav.uav_id}: {uav.battery_level:.1f}%")

        return {
            'average_battery': np.mean([uav.battery_level for uav in self.uavs]),
            'min_battery': min(uav.battery_level for uav in self.uavs),
            'max_battery': max(uav.battery_level for uav in self.uavs),
            'low_battery_count': len(low_battery_uavs)
        }

    def print_status(self):
        """Print current Digital Twin status"""
        print("\n" + "=" * 70)
        print("DIGITAL TWIN STATUS")
        print("=" * 70)
        print(f"Simulation time: {self.current_time}")
        print(f"Number of UAVs: {self.num_uavs}")
        print(f"Number of GBS: {self.num_gbs}")
        print(f"Number of tasks: {self.num_tasks}")

        # Battery status
        battery_stats = self.monitor_uav_batteries()
        print(f"\nUAV Battery Status:")
        print(f"  Average: {battery_stats['average_battery']:.1f}%")
        print(f"  Min: {battery_stats['min_battery']:.1f}%")
        print(f"  Max: {battery_stats['max_battery']:.1f}%")

        # Network status
        print(f"\nNetwork Conditions:")
        print(f"  Transmission rate: {self.network_conditions['transmission_rate']/1e6:.2f} Mbps")
        print(f"  Quality: {self.network_conditions['quality']}")
        print(f"  Congestion: {self.network_conditions['congestion']}")

        # Task allocation if available
        if self.task_history:
            stats = self.get_allocation_statistics()
            print(f"\nCurrent Task Allocation:")
            print(f"  Local (UAV): {stats['local_count']} ({stats['local_pct']:.1f}%)")
            print(f"  GBS: {stats['gbs_count']} ({stats['gbs_pct']:.1f}%)")
            print(f"  MEC: {stats['mec_count']} ({stats['mec_pct']:.1f}%)")
            print(f"  Cloud: {stats['cloud_count']} ({stats['cloud_pct']:.1f}%)")

        print("=" * 70)


if __name__ == "__main__":
    # Test Digital Twin
    print("Testing Digital Twin Framework")
    print("=" * 70)

    # Create Digital Twin
    dt = DigitalTwin(num_uavs=10, num_gbs=3, num_tasks=20)

    # Generate tasks
    tasks = dt.generate_tasks()

    # Print status
    dt.print_status()

    # Simulate a task allocation solution
    print("\nSimulating task allocation...")
    solution = np.random.randint(0, 4, dt.num_tasks)
    energy_breakdown = {
        'local': 100.0,
        'gbs': 200.0,
        'mec': 150.0,
        'cloud': 250.0
    }

    # Update Digital Twin
    dt.update_from_solution(solution, energy_breakdown)

    # Print updated status
    dt.print_status()

    print("\nDigital Twin test completed successfully!")
