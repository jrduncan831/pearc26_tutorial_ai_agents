import os
import argparse
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from sklearn.decomposition import PCA
from matplotlib import pyplot as plt



def main(): 

    parser = argparse.ArgumentParser(description="Parser for input parameters")
    parser.add_argument('--file', type = str, help="the path of the file")
    parser.add_argument('--num_modes', type = int, help="number of nodes to retain in PCA")
    args = parser.parse_args()

    data_file = args.file
    num_modes = args.num_modes
    mat_data = loadmat(data_file)
    
    # Assuming the data variable is stored in the mat file under key 'VORTALL' (common name for such files)
    # If it has a different key, that should be adjusted
    X = mat_data['VORTALL']
    
    # Perform PCA
    pca = PCA()
    pca.fit(X)
    
    # Compute cumulative variance explained
    cumulative_variance = np.cumsum(pca.explained_variance_ratio_)
    
    # Plot first 10 modes
    plt.figure(figsize=(8, 5))
    plt.plot(range(1, min(num_modes+1, len(cumulative_variance) + 1)), cumulative_variance[:num_modes], marker='o')
    plt.xlabel('Number of Modes')
    plt.ylabel('Cumulative Variance Explained')
    plt.title('Cumulative Variance for First 10 PCA Modes')
    plt.grid(True)
    
    # Ensure directory exists
    output_dir = './images/pca'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save plot
    plot_path = os.path.join(output_dir, 'cumulative_var.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"PCA complete. Plot saved to {plot_path}")

if __name__ == "__main__":
    main()      