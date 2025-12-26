"""
Configuration parameters for UAV Task Allocation using Jaya Algorithm
"""

import numpy as np

class Config:
    """System configuration and parameters"""

    # Task and GBS parameters
    NUM_TASKS = 520  # n: Number of tasks (as per simulation parameters)
    NUM_GBS = 3      # g: Number of Ground Base Stations (3-5)
    NUM_UAVS = 150   # Number of UAVs in the network

    # Jaya Algorithm parameters
    POPULATION_SIZE = 50    # N: Population size
    MAX_ITERATIONS = 200    # MaxIter: Maximum iterations

    # Physical parameters
    KAPPA = 1e-28                    # κ: Effective capacitance coefficient
    F_UAV = 1e9                      # f_uav: UAV CPU frequency (1 GHz)
    F_GBS = 10e9                     # f_gbs: GBS CPU frequency (10 GHz)
    F_MEC = 10e9                     # f_mec: MEC CPU frequency (10 GHz, same as GBS but with better connectivity)
    F_CLOUD = 50e9                   # f_cloud: Cloud CPU frequency (50 GHz)

    P_TX = 0.5                       # P_tx: Transmission power (0.5 W)
    P_HOVER = 100                    # P_hover: Hovering power (100 W)

    # Task parameters (ranges)
    D_MIN = 100 * 1024               # Minimum input data size (100 KB in bytes)
    D_MAX = 500 * 1024               # Maximum input data size (500 KB in bytes)
    C_MIN = 100 * 1e6                # Minimum CPU cycles (100 Megacycles)
    C_MAX = 1000 * 1e6               # Maximum CPU cycles (1000 Megacycles)

    # Output data size (typically smaller than input)
    D_OUT_RATIO = 0.2                # Output size as ratio of input size

    # Communication parameters
    BANDWIDTH = 10e6                 # Bandwidth (10 MHz)
    NOISE_POWER = 1e-13              # Noise power (W)
    PATH_LOSS_EXPONENT = 2.5         # Path loss exponent
    UAV_HEIGHT = 100                 # UAV height (meters)
    DISTANCE_TO_GBS = 200            # Average distance to GBS (meters)

    # Network delays
    T_FORWARD = 0.01                 # t_forward: Forwarding delay between GBS (10 ms)
    T_BACKHAUL = 0.05                # t_backhaul: Backhaul delay to cloud (50 ms)

    # Fitness function weights
    W1 = 0.6                         # w₁: Weight for energy (0.6 prioritizes energy)
    W2 = 0.4                         # w₂: Weight for load imbalance (1 - w₁)

    # Execution locations
    LOC_LOCAL = 0                    # Local execution at UAV
    LOC_GBS = 1                      # Execution at associated GBS
    LOC_MEC = 2                      # Execution at neighboring GBS/MEC
    LOC_CLOUD = 3                    # Execution at cloud

    @staticmethod
    def calculate_transmission_rate():
        """Calculate air-to-ground transmission rate using Shannon capacity"""
        # SNR calculation
        distance = np.sqrt(Config.UAV_HEIGHT**2 + Config.DISTANCE_TO_GBS**2)
        path_loss = distance ** Config.PATH_LOSS_EXPONENT
        received_power = Config.P_TX / path_loss
        snr = received_power / Config.NOISE_POWER

        # Shannon capacity
        rate = Config.BANDWIDTH * np.log2(1 + snr)
        return rate  # bits per second

    @staticmethod
    def generate_random_tasks(num_tasks=None):
        """Generate random task parameters"""
        if num_tasks is None:
            num_tasks = Config.NUM_TASKS

        tasks = {
            'D': np.random.uniform(Config.D_MIN, Config.D_MAX, num_tasks),  # Input data size
            'C': np.random.uniform(Config.C_MIN, Config.C_MAX, num_tasks),  # CPU cycles
        }
        tasks['D_out'] = tasks['D'] * Config.D_OUT_RATIO  # Output data size

        return tasks

    @staticmethod
    def print_config():
        """Print current configuration"""
        print("=" * 60)
        print("UAV Task Allocation Configuration")
        print("=" * 60)
        print(f"Number of tasks: {Config.NUM_TASKS}")
        print(f"Number of GBS: {Config.NUM_GBS}")
        print(f"Population size: {Config.POPULATION_SIZE}")
        print(f"Max iterations: {Config.MAX_ITERATIONS}")
        print(f"Energy weight (w₁): {Config.W1}")
        print(f"Load balance weight (w₂): {Config.W2}")
        print(f"Transmission rate: {Config.calculate_transmission_rate()/1e6:.2f} Mbps")
        print("=" * 60)


if __name__ == "__main__":
    Config.print_config()

    # Test task generation
    tasks = Config.generate_random_tasks(10)
    print("\nSample tasks:")
    print(f"Input data sizes (KB): {tasks['D'][:5] / 1024}")
    print(f"CPU cycles (Megacycles): {tasks['C'][:5] / 1e6}")
