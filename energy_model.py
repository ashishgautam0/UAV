"""
Energy consumption model for UAV task allocation
Implements energy calculations for all four execution locations
"""

import numpy as np
from config import Config


class EnergyModel:
    """Energy consumption calculations for different execution modes"""

    def __init__(self, tasks):
        """
        Initialize energy model with task parameters

        Args:
            tasks: Dictionary with keys 'D', 'C', 'D_out' (numpy arrays)
        """
        self.tasks = tasks
        self.num_tasks = len(tasks['D'])
        self.transmission_rate = Config.calculate_transmission_rate()

    def local_energy(self, task_idx):
        """
        Calculate energy for local execution at UAV (x_i = 0)

        E_i^local = κ × C_i × f_uav²

        Args:
            task_idx: Index of the task

        Returns:
            Energy consumption in Joules
        """
        C_i = self.tasks['C'][task_idx]
        energy = Config.KAPPA * C_i * (Config.F_UAV ** 2)
        return energy

    def gbs_energy(self, task_idx):
        """
        Calculate energy for GBS execution (x_i = 1)

        E_i^gbs = E_i^tx + E_i^hover
        E_i^tx = (P_tx × D_i) / R_i
        E_i^hover = P_hover × (D_i/R_i + C_i/f_gbs + D_i^out/R_i)

        Args:
            task_idx: Index of the task

        Returns:
            Energy consumption in Joules
        """
        D_i = self.tasks['D'][task_idx]
        C_i = self.tasks['C'][task_idx]
        D_out = self.tasks['D_out'][task_idx]
        R_i = self.transmission_rate

        # Transmission energy (convert data size to bits)
        E_tx = (Config.P_TX * D_i * 8) / R_i

        # Hovering energy during transmission, computation, and receiving
        t_tx = (D_i * 8) / R_i                    # Transmission time
        t_comp = C_i / Config.F_GBS               # Computation time
        t_rx = (D_out * 8) / R_i                  # Receiving time

        E_hover = Config.P_HOVER * (t_tx + t_comp + t_rx)

        return E_tx + E_hover

    def mec_energy(self, task_idx):
        """
        Calculate energy for neighboring GBS/MEC execution (x_i = 2)

        E_i^mec = E_i^tx + E_i^hover_extended
        E_i^hover_extended = P_hover × (D_i/R_i + t_forward + C_i/f_mec + D_i^out/R_i)

        Args:
            task_idx: Index of the task

        Returns:
            Energy consumption in Joules
        """
        D_i = self.tasks['D'][task_idx]
        C_i = self.tasks['C'][task_idx]
        D_out = self.tasks['D_out'][task_idx]
        R_i = self.transmission_rate

        # Transmission energy
        E_tx = (Config.P_TX * D_i * 8) / R_i

        # Hovering energy with forwarding delay
        t_tx = (D_i * 8) / R_i
        t_forward = Config.T_FORWARD
        t_comp = C_i / Config.F_MEC
        t_rx = (D_out * 8) / R_i

        E_hover = Config.P_HOVER * (t_tx + t_forward + t_comp + t_rx)

        return E_tx + E_hover

    def cloud_energy(self, task_idx):
        """
        Calculate energy for cloud execution (x_i = 3)

        E_i^cloud = E_i^tx + E_i^hover_cloud
        E_i^hover_cloud = P_hover × (D_i/R_i + t_backhaul + C_i/f_cloud + D_i^out/R_i)

        Args:
            task_idx: Index of the task

        Returns:
            Energy consumption in Joules
        """
        D_i = self.tasks['D'][task_idx]
        C_i = self.tasks['C'][task_idx]
        D_out = self.tasks['D_out'][task_idx]
        R_i = self.transmission_rate

        # Transmission energy
        E_tx = (Config.P_TX * D_i * 8) / R_i

        # Hovering energy with backhaul delay
        t_tx = (D_i * 8) / R_i
        t_backhaul = Config.T_BACKHAUL
        t_comp = C_i / Config.F_CLOUD
        t_rx = (D_out * 8) / R_i

        E_hover = Config.P_HOVER * (t_tx + t_backhaul + t_comp + t_rx)

        return E_tx + E_hover

    def calculate_task_energy(self, task_idx, location):
        """
        Calculate energy for a single task at a given location

        Args:
            task_idx: Index of the task
            location: Execution location (0=local, 1=GBS, 2=MEC, 3=cloud)

        Returns:
            Energy consumption in Joules
        """
        if location == Config.LOC_LOCAL:
            return self.local_energy(task_idx)
        elif location == Config.LOC_GBS:
            return self.gbs_energy(task_idx)
        elif location == Config.LOC_MEC:
            return self.mec_energy(task_idx)
        elif location == Config.LOC_CLOUD:
            return self.cloud_energy(task_idx)
        else:
            raise ValueError(f"Invalid location: {location}")

    def calculate_total_energy(self, solution):
        """
        Calculate total energy consumption for a complete solution

        Args:
            solution: Array of execution locations for all tasks

        Returns:
            Total energy consumption (f₁)
        """
        total_energy = 0.0
        for task_idx, location in enumerate(solution):
            total_energy += self.calculate_task_energy(task_idx, int(location))

        return total_energy

    def calculate_energy_breakdown(self, solution):
        """
        Calculate energy breakdown by execution location

        Args:
            solution: Array of execution locations for all tasks

        Returns:
            Dictionary with energy per location type
        """
        energy_breakdown = {
            'local': 0.0,
            'gbs': 0.0,
            'mec': 0.0,
            'cloud': 0.0
        }

        location_names = ['local', 'gbs', 'mec', 'cloud']

        for task_idx, location in enumerate(solution):
            loc = int(location)
            energy = self.calculate_task_energy(task_idx, loc)
            energy_breakdown[location_names[loc]] += energy

        return energy_breakdown


if __name__ == "__main__":
    # Test energy model
    print("Testing Energy Model")
    print("=" * 60)

    # Generate sample tasks
    tasks = Config.generate_random_tasks(10)
    energy_model = EnergyModel(tasks)

    # Test single task at different locations
    task_idx = 0
    print(f"\nTask 0 parameters:")
    print(f"  Input data: {tasks['D'][0]/1024:.2f} KB")
    print(f"  CPU cycles: {tasks['C'][0]/1e6:.2f} Megacycles")
    print(f"  Output data: {tasks['D_out'][0]/1024:.2f} KB")

    print(f"\nEnergy consumption for task 0:")
    print(f"  Local:  {energy_model.local_energy(0):.6f} J")
    print(f"  GBS:    {energy_model.gbs_energy(0):.6f} J")
    print(f"  MEC:    {energy_model.mec_energy(0):.6f} J")
    print(f"  Cloud:  {energy_model.cloud_energy(0):.6f} J")

    # Test complete solution
    solution = np.random.randint(0, 4, 10)
    print(f"\nSample solution: {solution}")
    print(f"Total energy: {energy_model.calculate_total_energy(solution):.4f} J")

    breakdown = energy_model.calculate_energy_breakdown(solution)
    print(f"\nEnergy breakdown:")
    for loc, energy in breakdown.items():
        print(f"  {loc.capitalize()}: {energy:.4f} J")
