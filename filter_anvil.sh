#!/bin/bash

# filter_anvil.sh - Filter Anvil output to show only important logs
# Usage: anvil [your-anvil-options] | ./filter_anvil.sh

# Set colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Initialize variables
CURRENT_BLOCK=0
SKIP_CURRENT_BLOCK=0

# Process each line of input
while IFS= read -r line; do
    # Skip common noise patterns
    if [[ $line =~ ^(eth_getTransactionReceipt|eth_chainId|eth_blockNumber|eth_accounts|eth_gasPrice|eth_getTransactionCount|eth_estimateGas|eth_call|eth_getBalance|web3_clientVersion) ]]; then
        continue
    fi
    
    # Extract block number and decide whether to show this block
    if [[ $line =~ "Block Number:" ]]; then
        block_num=$(echo "$line" | grep -o '[0-9]\+' | head -1)
        if [[ -n "$block_num" ]]; then
            CURRENT_BLOCK=$block_num
            # Only show first 5 blocks and then every 10th block
            if (( CURRENT_BLOCK > 5 )) && (( CURRENT_BLOCK % 10 != 0 )); then
                SKIP_CURRENT_BLOCK=1
                continue
            else
                SKIP_CURRENT_BLOCK=0
                echo "$line"
            fi
        fi
        continue
    fi
    
    # Skip block hash and time lines if we're skipping this block
    if [[ $SKIP_CURRENT_BLOCK -eq 1 ]] && [[ $line =~ "Block Hash:" || $line =~ "Block Time:" ]]; then
        continue
    fi
    
    # Highlight important contract logs
    if [[ $line =~ "contract initialized" || $line =~ "called" || $line =~ "successfully" ]]; then
        echo -e "${GREEN}$line${NC}"
    # Highlight transactions
    elif [[ $line =~ "Transaction:" ]]; then
        echo -e "${BLUE}$line${NC}"
    # Highlight contract creation
    elif [[ $line =~ "Contract created:" ]]; then
        echo -e "${YELLOW}$line${NC}"
    # Highlight gas usage
    elif [[ $line =~ "Gas used:" ]]; then
        echo -e "${YELLOW}$line${NC}"
    # Print other lines normally
    else
        echo "$line"
    fi
done 