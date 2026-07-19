import sys
import subprocess
import os
import argparse
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from pathlib import Path

def main():

    parser = argparse.ArgumentParser(description="Parser for input parameters")
    parser.add_argument('--theta0', type = float, help="initial angle in degrees")
    parser.add_argument('--num_periods', type = float, help="the number of oscillation periods")
    parser.add_argument('--write_dir', type = str, help="address for output snapshots",default='./images/pendulum')
    args = parser.parse_args()

    # Parameters
    g = 9.81  # gravitational acceleration (m/s^2)
    L = 1.0   # length of pendulum (m)
    theta0 = np.radians(args.theta0)  # Initial angle in radians
    
    # Define the differential equation for pendulum motion
    def pendulum_ode(t, y):
        theta, omega = y
        dtheta_dt = omega
        domega_dt = -(g / L) * np.sin(theta)
        return [dtheta_dt, domega_dt]
    
    # Initial conditions
    y0 = [theta0, 0]  # theta, omega
    
    # Time span for 3 periods
    T_theory = 2 * np.pi * np.sqrt(L / g)  # Period for small angles
    t_span = (0, 3 * T_theory)
    t_eval = np.linspace(0, args.num_periods * T_theory, 1000)
    
    # Solve the ODE
    solution = solve_ivp(pendulum_ode, t_span, y0, t_eval=t_eval, method='RK45', rtol=1e-8, atol=1e-8)
    
    # Extract time and angle from solution
    t = solution.t
    theta = solution.y[0]
    
    # Find the period by detecting zero crossings (we'll use peak detection for more accuracy)
    peaks_indices = []
    for i in range(1, len(theta)-1):
        if theta[i-1] < theta[i] > theta[i+1]:  # Local maximum
            peaks_indices.append(i)
    
    # Calculate the actual periods between successive peaks
    periods = []
    for i in range(len(peaks_indices) - 1):
        t1 = t[peaks_indices[i]]
        t2 = t[peaks_indices[i+1]]
        periods.append(t2 - t1)
    
    # Calculate average frequency over the 3 periods
    avg_period = np.mean(periods[-3:]) if len(periods) >= 3 else np.mean(periods)
    avg_frequency = 1 / avg_period
    
    # Compare with theoretical frequency (small angle approximation)
    theoretical_frequency = 1 / T_theory
    
    print(f"Average simulated frequency: {avg_frequency:.4f} Hz")
    print(f"Theoretical frequency (small angle): {theoretical_frequency:.4f} Hz")
    
    # Plot the motion of pendulum over one period
    period_indices = peaks_indices[:2]
    if len(period_indices) >= 2:
        start_time = t[period_indices[0]]
        end_time = t[period_indices[1]]
        period_time_indices = np.where((t >= start_time) & (t <= end_time))[0]

        # Save snapshots
        save_dir = Path(args.write_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # We want 10 snapshots equally spaced in time over one period
        snapshot_indices = np.linspace(period_time_indices[0], period_time_indices[-1], 10, dtype=int)
        
        for i, idx in enumerate(snapshot_indices):
            plt.figure(figsize=(3, 3))
            theta_current = theta[idx]  # Current angle
            x = L * np.sin(theta_current)
            y = -L * np.cos(theta_current)
            plt.plot([0, x], [0, y], 'o-', linewidth=2, markersize=12,
            markeredgecolor=(0.6,0.6,0.6),
            markerfacecolor=(0.6,0.78,0.92),
            markeredgewidth=1)
            plt.xlim(-L*1.2, L*1.2)
            plt.ylim(-L*1.2, 0.1)
            plt.grid(True)
            plt.title(f'Pendulum Position at t = {t[idx]:.2f}s')
            
            # Save image
            filename = save_dir / f"pendulum_{i+1:02d}.png"
            plt.savefig(filename)
            plt.close()
            
        print(f"Saved 10 snapshots to {save_dir}")
    else:
        print("Not enough data points for a complete period to save images.")

if __name__ == "__main__":
    main()