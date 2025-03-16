#!/bin/bash

# Exit on error
set -e

# Check if Foundry is installed
if ! command -v forge &> /dev/null; then
    echo "Foundry is not installed. Please install it first: https://book.getfoundry.sh/getting-started/installation"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it first."
    exit 1
fi

# Check if INFURA_KEY is set
if grep -q "YOUR_INFURA_KEY" shapley/eth_simulation.py; then
    echo "Please set your Infura API key in eth_simulation.py"
    exit 1
fi

# Navigate to the Foundry directory
cd shapley/thefoundry

# Install dependencies if needed
if [ ! -d "lib" ] || [ -z "$(ls -A lib)" ]; then
    echo "Installing Foundry dependencies..."
    forge install
fi

# Compile contracts
echo "Compiling contracts..."
forge build

# Return to the main directory
cd ../

# Run the simulation
echo "Running Ethereum simulation..."
python3 eth_simulation.py 