#!/bin/bash

# start_anvil.sh - Start Anvil with filtered output
# Usage: ./start_anvil.sh [--log logfile.log] [anvil options]

# Check if anvil is installed
if ! command -v anvil &> /dev/null; then
    echo "Error: anvil command not found. Please install Foundry."
    exit 1
fi

# Check if the filter script exists
if [ ! -f "./anvil_logger.sh" ]; then
    echo "Error: anvil_logger.sh not found in the current directory."
    exit 1
fi

# Check if the filter script is executable
if [ ! -x "./anvil_logger.sh" ]; then
    echo "Making anvil_logger.sh executable..."
    chmod +x ./anvil_logger.sh
fi

# Check if we should use logging
LOG_FILE=""
LOG_OPTION=""

if [[ "$1" == "--log" && -n "$2" ]]; then
    LOG_FILE="$2"
    LOG_OPTION="--log $LOG_FILE"
    shift 2
fi

# Default Anvil options
ANVIL_OPTIONS="--host 0.0.0.0 --port 8545 --block-time 1 --accounts 10 --tracing"

# Add any additional options passed to this script
if [ $# -gt 0 ]; then
    ANVIL_OPTIONS="$ANVIL_OPTIONS $@"
fi

echo "Starting Anvil with filtered output..."
echo "Anvil options: $ANVIL_OPTIONS"
if [[ -n "$LOG_FILE" ]]; then
    echo "Logging to: $LOG_FILE"
fi

# Start Anvil and pipe through the filter
# Use exec to replace the current process with anvil
exec anvil $ANVIL_OPTIONS | ./anvil_logger.sh $LOG_OPTION 