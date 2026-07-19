import os
import argparse
import numpy as np
from scipy.integrate import solve_ivp
from matplotlib import pyplot as plt

def velocity(x, gamma):
    # Function that computes induced velocity for each vortex in xi
    # x: an array containing vortex positions, of shape [N,2]
    # gamma: an array container vortex strengths, of shape [N,]
    
    # Gram matrix.
    d2 = -2 * x @ x.T
    
    # Squared pairwise distances.
    diag = -0.5 * np.einsum('ii->i', d2)
    d2 += diag + diag[:, None]

    # Prevent division by zero
    d2[d2==0] = 1.
    
    # Velocity by Biot-Savart
    #U = np.nansum( gamma[None,:,None]*(x[:, None, :] - x) * d2[..., None]**-1, axis=1)
    diff = x[:,None,:] - x[None, :, :]
    diff = np.stack((-diff[..., 1], diff[..., 0]), axis=-1)
    U = np.nansum(gamma[None,:,None] * diff * d2[..., None]**-1, axis=1)

    # Return velocity
    return U

def ode(t, x, gamma, N):
    x = x.reshape(N,2)
    u = velocity(x, gamma)
    return u.flatten()

def write_output(y, nwrite, write_dir):
    xmin = y[:,:,0].min()
    xmax = y[:,:,0].max()
    ymin = y[:,:,1].min()
    ymax = y[:,:,1].max()
    for ind in range(nwrite):
        fig = plt.figure(figsize=(3,3))
        plt.plot(y[ind,:,0],y[ind,:,1],
            marker='o',
            linestyle='None',
            ms=12,
            markeredgecolor=(0.6,0.6,0.6),
            markerfacecolor=(0.6,0.78,0.92),
            markeredgewidth=1)
        plt.xlim(xmin-1,xmax+1)
        plt.ylim(ymin-1,ymax+1)
        plt.grid()
        plt.savefig(os.path.join(write_dir,'snapshot_' + str(ind) + '.png'), dpi = 300)
        plt.close()


def main(): 

    parser = argparse.ArgumentParser(description="Parser for input parameters")
    parser.add_argument('--xpos', type = float, nargs='+', help="initial x position(s) of vortex particles")
    parser.add_argument('--ypos', type = float, nargs='+', help="initial y position(s) of vortex particles")
    parser.add_argument('--gamma', type = float, nargs='+', help="initial strength(s) of vortex particles")
    parser.add_argument('--tsim', type = float, help="total time over which simulation is advanced")
    parser.add_argument('--num_snapshots', type = int, help="the desired number of output snapshots")
    parser.add_argument('--write_dir', type = str, help="address for output snapshots",default='./images/vortex_method')
    args = parser.parse_args()


    xpos = np.expand_dims(np.array(args.xpos),axis=1)
    ypos = np.expand_dims(np.array(args.ypos),axis=1)
    N = len(xpos)
    x0 = np.concatenate((xpos,ypos),axis=-1).flatten()

    gamma = np.array(args.gamma)

    t_span = (0,args.tsim)
    t_eval = np.linspace(0,args.tsim,args.num_snapshots)

    atol = 1e-10
    rtol = 1e-6  

    sol = solve_ivp(
        ode,
        y0=x0,
        t_span = t_span,
        t_eval = t_eval,
        method='RK45',
        rtol=rtol,
        atol=atol,
        args=(gamma,N)
        )

    yout = np.transpose(sol.y,(-1,0))
    yout = yout.reshape((len(t_eval),N,2))
    write_output(yout, len(t_eval), args.write_dir) 

    print("All figures generated and saved")

if __name__ == "__main__":
    main()      