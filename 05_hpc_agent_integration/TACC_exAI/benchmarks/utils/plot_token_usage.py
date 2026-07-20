#!/usr/bin/env python3
"""
plot_token_histograms.py

Raw token counts on log scale WITH evenly spaced log-space bins.
"""

import json
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.ticker as ticker

def load_token_data(json_file: str) -> tuple:
    """Load token data and separate errors vs successes."""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    errors = []
    successes = []
    
    for entry in data:
        token_count = entry['token_count']
        if entry['is_error']:
            errors.append(token_count)
        else:
            successes.append(token_count)
    
    return np.array(errors), np.array(successes)

def plot_token_histograms(errors: np.ndarray, successes: np.ndarray, output_file: str):
    """Raw tokens on log scale with log-space bins."""
    
    # Create LOGARITHMICALLY SPACED BINS (20 equal intervals in log space)
    min_token, max_token = np.min(errors), np.max(errors)  # Use full range
    log_bins = np.logspace(np.log10(min_token), np.log10(max_token), 21)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    
    # Plot RAW tokens with log-space bins
    ax.hist(errors, bins=log_bins, alpha=0.6, color='#D55E00', 
            label=f'Errors (n={len(errors)})', edgecolor='white', linewidth=0.8)
    ax.hist(successes, bins=log_bins, alpha=0.6, color='#0072B2',
            label=f'Successes (n={len(successes)})', edgecolor='white', linewidth=0.8)
    
    # Geometric means (proper for log scale)
    error_mean = np.mean(errors)
    success_mean = np.mean(successes)
    
    ax.axvline(error_mean, color='#D55E00', lw=4, alpha=0.9, 
               label=f'Error Mean: {error_mean:.0f}')
    ax.axvline(success_mean, color='#0072B2', lw=4, alpha=0.9, 
               label=f'Success Mean: {success_mean:.0f}')
    
    # Log scale display + clean 10^x ticks
    ax.set_xscale('log')
    ax.xaxis.set_major_formatter(ticker.LogFormatterSciNotation(labelOnlyBase=False))
    
    ax.set_xlabel('Token Count (Log Scale)', fontsize=16, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=16, fontweight='bold')
    ax.set_title('LLM Token Count Distribution (Log-Spaced Bins)\nErrors vs Successes', 
                 fontsize=20, fontweight='bold')
    
    ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=13)
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.8)
    ax.tick_params(axis='both', which='major', labelsize=13)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Log-spaced bins plot saved: {output_file}")
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Plot token histograms with log-space bins')
    parser.add_argument('input_json', type=str, help='Path to _errors.json file')
    parser.add_argument('output_png', type=str, nargs='?', default='token_distribution_log.png', 
                       help='Output PNG file')
    
    args = parser.parse_args()
    
    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: File not found: {args.input_json}")
        sys.exit(1)
    
    print("Loading token data...")
    errors, successes = load_token_data(args.input_json)
    
    print(f"Errors: {len(errors)}, Successes: {len(successes)}")
    print(f"Token range: {np.min(errors):.0f} to {np.max(errors):.0f}")
    
    plot_token_histograms(errors, successes, args.output_png)

if __name__ == "__main__":
    main()
