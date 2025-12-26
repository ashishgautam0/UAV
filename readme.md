    # Plot convergence comparison
        plt.figure(figsize=(10, 6))
        plt.plot(scenario_results['QPSO']['convergence'], 'b-', label='BQPSO', linewidth=2)
        plt.plot(scenario_results['GA']['convergence'], 'r--', label='GA', linewidth=2)
        plt.plot(scenario_results['DE']['convergence'], 'g-.', label='DE', linewidth=2)
        plt.plot(scenario_results['PSO']['convergence'], 'm:', label='PSO', linewidth=2)
        plt.xlabel('Generation', fontsize=12)
        plt.ylabel('Best Fitness', fontsize=12)
        plt.title(f'Convergence Comparison - Scenario S{idx+1}', fontsize=14)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.show()
    
    # Print summary
    print(f"\n{'='*60}")
    print("EXPERIMENT SUMMARY")
    print(f"{'='*60}")
    
    for scenario, scenario_results in results.items():
        print(f"\n{scenario}:")
        for algo, metrics in scenario_results.items():
            print(f"  {algo}: Fitness = {metrics['fitness']:.4f}")
            if 'latency' in metrics:
                print(f"       Latency = {metrics['latency']:.4f} s, Energy = {metrics['energy']:.4f} J")
                print(f"       Throughput = {metrics['throughput']:.4f}, Imbalance = {metrics['imbalance']:.4f}")
                print(f"       Channel Gain = {metrics['channel_gain']:.6f}, Trans Rate = {metrics['transmission_rate']:.4f} Mbps")
                print(f"       Noise Power = {metrics['noise_power']:.2e} W")
    
    # Create 3D performance comparison
    plot_3d_performance(results)
    
    return results
    
def plot_3d_performance(results):
    """Create visually appealing 3D bar charts showing performance comparison"""
    
    # Extract data
    scenarios = list(results.keys())
    algorithms = ['QPSO', 'GA', 'DE', 'PSO']
    display_algorithms = ['BQPSO' if a == 'QPSO' else a for a in algorithms]
    
    # Create data arrays for each metric
    fitness_data = []
    latency_data = []
    energy_data = []
    throughput_data = []
    imbalance_data = []
    channel_gain_data = []
    transmission_rate_data = []
    noise_power_data = []

    for algo in algorithms:
        fitness_row = []
        latency_row = []
        energy_row = []
        throughput_row = []
        imbalance_row = []
        channel_gain_row = []
        transmission_rate_row = []
        noise_power_row = []
        for scenario in scenarios:
            fitness_row.append(results[scenario][algo]['fitness'])
            latency_row.append(results[scenario][algo]['latency'])
            energy_row.append(results[scenario][algo]['energy'])
            throughput_row.append(results[scenario][algo]['throughput'])
            imbalance_row.append(results[scenario][algo]['imbalance'])
            channel_gain_row.append(results[scenario][algo]['channel_gain'])
            transmission_rate_row.append(results[scenario][algo]['transmission_rate'])
            noise_power_row.append(results[scenario][algo]['noise_power'])
        fitness_data.append(fitness_row)
        latency_data.append(latency_row)
        energy_data.append(energy_row)
        throughput_data.append(throughput_row)
        imbalance_data.append(imbalance_row)
        channel_gain_data.append(channel_gain_row)
        transmission_rate_data.append(transmission_rate_row)
        noise_power_data.append(noise_power_row)
    
    # Enhanced color schemes with gradients
    color_maps = {
        'QPSO': ['#00CED1', '#20B2AA', '#48D1CC', '#40E0D0'],  # Turquoise gradient
        'GA': ['#4169E1', '#0000FF', '#1E90FF', '#6495ED'],     # Blue gradient  
        'DE': ['#9932CC', '#8A2BE2', '#9370DB', '#BA55D3'],     # Purple gradient
        'PSO': ['#FF1493', '#FF69B4', '#DA70D6', '#DDA0DD']     # Pink gradient
    }
    
    # Metrics configuration
    metrics = [
        ('Fitness', fitness_data, '×10³', '#2E8B57'),
        ('Latency', latency_data, '(s)', '#CD853F'),
        ('Energy Consumption', energy_data, '(J)', '#B22222'),
        ('Throughput', throughput_data, '', '#4B0082'),
        ('Load Imbalance', imbalance_data, '', '#8B4513'),
        ('Channel Gain', channel_gain_data, '(average)', '#FF6347'),
        ('Transmission Rate', transmission_rate_data, '(Mbps)', '#32CD32'),
        ('Noise Power', noise_power_data, '(W)', '#9370DB')
    ]
    
    for metric_name, data, unit, title_color in metrics:
        # Create figure with better size and DPI
        fig = plt.figure(figsize=(16, 12), facecolor='white', dpi=100)
        
        # Create multiple subplots for different viewing angles
        # Adjusted angles to ensure QPSO appears first (leftmost) in the view
        for view_idx, (elev, azim, subplot_title) in enumerate([
            (25, 225, 'View 1: Standard Angle'),
            (25, 315, 'View 2: Rotated 90°'),
            (25, 45, 'View 3: Rotated 180°'),
            (25, 135, 'View 4: Rotated 270°')
        ]):
            ax = fig.add_subplot(2, 2, view_idx + 1, projection='3d')
            
            # Set background color
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            
            # Make pane edges more subtle
            ax.xaxis.pane.set_edgecolor('lightgray')
            ax.yaxis.pane.set_edgecolor('lightgray')
            ax.zaxis.pane.set_edgecolor('lightgray')
            ax.xaxis.pane.set_alpha(0.1)
            ax.yaxis.pane.set_alpha(0.1)
            ax.zaxis.pane.set_alpha(0.1)
            
            # Create bar positions with better spacing and separation
            xpos = []
            ypos = []
            zpos = []
            dx = []
            dy = []
            dz = []
            colors = []
            
            bar_width = 0.6
            spacing = 0.2
            for i, algo in enumerate(algorithms):
                for j, scenario in enumerate(scenarios):
                    # Swapped positioning: Algorithms on X, Scenarios on Y
                    x_offset = i * 1.0  # Algorithms spread along X
                    y_offset = j * 1.0  # Scenarios spread along Y
                    
                    xpos.append(x_offset)
                    ypos.append(y_offset)
                    zpos.append(0)
                    dx.append(bar_width)
                    dy.append(bar_width)
                    dz.append(data[i][j])
                    colors.append(color_maps[algo][j % len(color_maps[algo])])
            
            # Create 3D bars with enhanced visual effects
            bars = ax.bar3d(xpos, ypos, zpos, dx, dy, dz, 
                           color=colors, alpha=1.0,  # Fully opaque bars
                           edgecolor='black', linewidth=0.5,
                           shade=True)
            
            
            # Enhanced axis labels (swapped)
            ax.set_xlabel('', fontsize=10, fontweight='bold')
            ax.set_ylabel('', fontsize=10, fontweight='bold')
            ax.set_zlabel(f'{metric_name} {unit}', fontsize=10, fontweight='bold')
            
            # Set ticks with better formatting (swapped)
            ax.set_xticks([i * 1.0 for i in range(len(algorithms))])
            ax.set_xticklabels(display_algorithms, fontsize=9, rotation=0, ha='center')
            ax.set_yticks([i * 1.0 for i in range(len(scenarios))])
            ax.set_yticklabels(scenarios, fontsize=9, rotation=0, ha='center')
            
            # Set viewing angle
            ax.view_init(elev=elev, azim=azim)
            
            # Add grid
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            
            # Add subplot title
            ax.set_title(subplot_title, fontsize=11, fontweight='bold', pad=10)
        
        # Main title for the entire figure
        fig.suptitle(f'{metric_name} Performance Comparison\nAcross Different Scenarios (Multiple Views)', 
                    fontsize=16, fontweight='bold', color=title_color, y=0.95)
        
        # Legend removed - no legend box will be shown
        # legend_elements = []
        # for algo in algorithms:
        #     legend_elements.append(plt.Rectangle((0,0),1,1, 
        #                                        facecolor=color_maps[algo][0], 
        #                                        alpha=0.7, 
        #                                        edgecolor='black',
        #                                        label=algo))
        # 
        # fig.legend(handles=legend_elements, loc='center', 
        #           bbox_to_anchor=(0.5, 0.02), ncol=4, fontsize=12, 
        #           frameon=True, fancybox=True, shadow=True)
        
        # Adjust layout
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.1, top=0.85)
        plt.show()
        
        # Also create an interactive single view with better positioning
        fig2 = plt.figure(figsize=(14, 10), facecolor='white', dpi=100)
        ax2 = fig2.add_subplot(111, projection='3d')
        
        # Set background
        ax2.xaxis.pane.fill = False
        ax2.yaxis.pane.fill = False
        ax2.zaxis.pane.fill = False
        ax2.xaxis.pane.set_edgecolor('lightgray')
        ax2.yaxis.pane.set_edgecolor('lightgray')
        ax2.zaxis.pane.set_edgecolor('lightgray')
        ax2.xaxis.pane.set_alpha(0.1)
        ax2.yaxis.pane.set_alpha(0.1)
        ax2.zaxis.pane.set_alpha(0.1)
        
        # Create bars with optimal positioning
        xpos2 = []
        ypos2 = []
        zpos2 = []
        dx2 = []
        dy2 = []
        dz2 = []
        colors2 = []
        
        bar_width2 = 0.6
        spacing = 0.1
        
        for i, algo in enumerate(algorithms):
            for j, scenario in enumerate(scenarios):
                # Swapped positioning: Algorithms on X, Scenarios on Y
                x_base = i * 1.2  # Algorithms spread along X
                y_base = j * 1.2  # Scenarios spread along Y
                
                xpos2.append(x_base)
                ypos2.append(y_base)
                zpos2.append(0)
                dx2.append(bar_width2)
                dy2.append(bar_width2)
                dz2.append(data[i][j])
                colors2.append(color_maps[algo][j % len(color_maps[algo])])
        
        # Create bars
        bars2 = ax2.bar3d(xpos2, ypos2, zpos2, dx2, dy2, dz2, 
                         color=colors2, alpha=1.0, 
                         edgecolor='black', linewidth=0.5,
                         shade=True)
        
        # Labels and formatting (removed Scenarios label, changed S to L)
        ax2.set_xlabel('', fontsize=14, fontweight='bold', labelpad=10)
        ax2.set_ylabel('', fontsize=14, fontweight='bold', labelpad=10)
        ax2.set_zlabel(f'{metric_name}', fontsize=14, fontweight='bold', labelpad=10)
        
        ax2.set_title(f'{metric_name} Performance Comparison (Interactive View)\nRotate to see all values', 
                     fontsize=16, fontweight='bold', color=title_color, pad=20)
        
        # Set optimal viewing angle FIRST (before setting ticks)
        # Changed azim from 45 to 225 to flip the x-axis direction
        ax2.view_init(elev=30, azim=225)
        
        # Set ticks (changed S to L for scenarios)
        # Note: Due to 3D perspective, we need to check if labels appear reversed
        ax2.set_xticks([i * 1.2 for i in range(len(algorithms))])
        ax2.set_xticklabels(display_algorithms, fontsize=12, fontweight='bold')
        ax2.set_yticks([i * 1.2 for i in range(len(scenarios))])
        scenario_labels = [scenario.replace('S', 'L') for scenario in scenarios]
        ax2.set_yticklabels(scenario_labels, fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Legend removed - no legend box will be shown
        # legend_elements2 = []
        # for algo in algorithms:
        #     legend_elements2.append(plt.Rectangle((0,0),1,1, 
        #                                         facecolor=color_maps[algo][0], 
        #                                         alpha=0.8, 
        #                                         edgecolor='black',
        #                                         label=algo))
        # 
        # ax2.legend(handles=legend_elements2, loc='upper left', 
        #           bbox_to_anchor=(0.02, 0.98), fontsize=11, 
        #           frameon=True, fancybox=True, shadow=True,
        #           framealpha=0.9)
        
        plt.tight_layout()
        plt.show()
