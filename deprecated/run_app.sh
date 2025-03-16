#!/bin/bash

# Check if Anvil is already running
if pgrep -x "anvil" > /dev/null
then
    echo "Anvil is already running"
else
    echo "Starting Anvil fork of Sepolia..."
    # Run the Sepolia simulation in the background
    python sepolia_simulation.py &
    # Wait for Anvil to start
    sleep 5
fi

# Run the Streamlit app
echo "Starting Streamlit app..."
streamlit run app.py 