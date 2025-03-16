# Anvil Output Filter

This set of scripts helps filter and highlight the important parts of Anvil's output, making it easier to see contract interactions and events without the noise of transaction receipts and block mining notifications.

## Available Scripts

### 1. `filter_anvil.sh`

A simple filter that removes common noise patterns and highlights important logs.

**Usage:**
```bash
anvil [your-anvil-options] | ./filter_anvil.sh
```

### 2. `anvil_logger.sh`

An advanced filter that not only cleans up the output but also provides a summary of events and can save logs to a file.

**Usage:**
```bash
# Basic usage
anvil [your-anvil-options] | ./anvil_logger.sh

# Save logs to a file
anvil [your-anvil-options] | ./anvil_logger.sh --log my_anvil_logs.log
```

### 3. `start_anvil.sh`

A convenient wrapper script that starts Anvil with common options and pipes the output through the filter.

**Usage:**
```bash
# Basic usage with default options
./start_anvil.sh

# Save logs to a file
./start_anvil.sh --log my_anvil_logs.log

# Add custom Anvil options
./start_anvil.sh --fork-url https://sepolia.infura.io/v3/YOUR_API_KEY --fork-block-number 5000000

# Combine logging and custom options
./start_anvil.sh --log my_anvil_logs.log --fork-url https://sepolia.infura.io/v3/YOUR_API_KEY
```

## Features

- **Noise Reduction**: Filters out repetitive messages like `eth_getTransactionReceipt`, `eth_chainId`, etc.
- **Block Filtering**: Shows only important blocks or every 10th block after the initial setup
- **Color Highlighting**:
  - 🟢 Green: Contract interactions and successful operations
  - 🔵 Blue: Transaction hashes
  - 🟡 Yellow: Contract creation and gas usage
  - 🔴 Red: Errors and failures
- **Event Tracking**: The advanced logger tracks and summarizes contract events
- **Log Saving**: Option to save filtered logs to a file for later review

## Customization

You can customize the filtering behavior by editing the scripts:

- To change which messages are filtered out, modify the regex patterns in the `if [[ $line =~ ... ]]` conditions
- To change the highlighting colors, modify the color variables at the top of the scripts
- To change which block numbers are shown, adjust the conditions in the block filtering section 