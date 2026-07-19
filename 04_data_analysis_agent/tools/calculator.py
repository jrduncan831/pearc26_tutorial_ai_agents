import os
import argparse
import numpy as np
from scipy.integrate import solve_ivp
from matplotlib import pyplot as plt


def main(): 

    parser = argparse.ArgumentParser(description="Parser for input parameters")
    parser.add_argument('--num1', type = float, help="first number")
    parser.add_argument('--num2', type = float, help="second number")
    args = parser.parse_args()


    print(str(args.num1) + " + " + str(args.num2) + " = " + str(args.num1+args.num2))

if __name__ == "__main__":
    main() 