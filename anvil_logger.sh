#!/bin/bash

# anvil_logger.sh - Filter Anvil output and optionally save to a log file
# Usage: anvil [your-anvil-options] | ./anvil_logger.sh [--log filename.log]

# Set colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if we should log to a file
LOG_FILE=""
if [[ "$1" == "--log" && -n "$2" ]]; then
    LOG_FILE="$2"
    echo "Logging filtered output to $LOG_FILE"
    # Clear the log file if it exists
    > "$LOG_FILE"
fi

# Function to output with optional logging
output() {
    local text="$1"
    local color="$2"
    
    # Print to terminal with color
    echo -e "${color}${text}${NC}"
    
    # Log to file without color codes if requested
    if [[ -n "$LOG_FILE" ]]; then
        echo "$text" >> "$LOG_FILE"
    fi
}

# Print header
output "=== FILTERED ANVIL OUTPUT ===" "$CYAN"
output "Only showing important contract interactions and occasional block updates" "$CYAN"
output "=================================================" "$CYAN"
echo ""

# Track contract events for summary
declare -a CONTRACT_EVENTS_NAMES
declare -a CONTRACT_EVENTS_COUNTS
TRANSACTION_COUNT=0
CURRENT_BLOCK=0

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
                output "$line" ""
            fi
        fi
        continue
    fi
    
    # Skip block hash and time lines if we're skipping this block
    if [[ $SKIP_CURRENT_BLOCK -eq 1 ]] && [[ $line =~ "Block Hash:" || $line =~ "Block Time:" ]]; then
        continue
    fi
    
    # Track contract events for summary
    if [[ $line =~ "called" ]]; then
        event=$(echo "$line" | awk '{print $1}')
        
        # Check if event already exists in our arrays
        found=0
        for i in "${!CONTRACT_EVENTS_NAMES[@]}"; do
            if [[ "${CONTRACT_EVENTS_NAMES[$i]}" == "$event" ]]; then
                CONTRACT_EVENTS_COUNTS[$i]=$((CONTRACT_EVENTS_COUNTS[$i] + 1))
                found=1
                break
            fi
        done
        
        # If not found, add it
        if [[ $found -eq 0 ]]; then
            CONTRACT_EVENTS_NAMES+=("$event")
            CONTRACT_EVENTS_COUNTS+=(1)
        fi
    fi
    
    # Count transactions
    if [[ $line =~ "Transaction:" ]]; then
        TRANSACTION_COUNT=$((TRANSACTION_COUNT + 1))
    fi
    
    # Highlight important contract logs
    if [[ $line =~ "contract initialized" || $line =~ "called" || $line =~ "successfully" || $line =~ "transferred" ]]; then
        output "$line" "$GREEN"
    # Highlight transactions
    elif [[ $line =~ "Transaction:" ]]; then
        output "$line" "$BLUE"
    # Highlight contract creation
    elif [[ $line =~ "Contract created:" ]]; then
        output "$line" "$YELLOW"
    # Highlight gas usage
    elif [[ $line =~ "Gas used:" ]]; then
        output "$line" "$YELLOW"
    # Highlight errors
    elif [[ $line =~ [Ee]rror || $line =~ [Ff]ailed ]]; then
        output "$line" "$RED"
    # Print other lines normally
    else
        output "$line" ""
    fi
done

# Print summary at the end
echo ""
output "=== SESSION SUMMARY ===" "$CYAN"
output "Total Transactions: $TRANSACTION_COUNT" "$CYAN"
output "Contract Events:" "$CYAN"
for i in "${!CONTRACT_EVENTS_NAMES[@]}"; do
    output "  - ${CONTRACT_EVENTS_NAMES[$i]}: ${CONTRACT_EVENTS_COUNTS[$i]}" "$CYAN"
done
output "=================================================" "$CYAN" 