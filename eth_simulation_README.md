# Ethereum Simulation for NFT Bundle Marketplace

This simulation demonstrates the NFT Bundle Marketplace contract running on a forked Ethereum mainnet using Anvil from Foundry.

## Prerequisites

1. [Foundry](https://book.getfoundry.sh/getting-started/installation) installed
2. Python 3.8+ with required packages:
   - web3
   - eth-account

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install Foundry dependencies:
   ```bash
   cd thefoundry
   forge install
   ```

3. Compile the contracts:
   ```bash
   cd thefoundry
   forge build
   ```

## Running the Simulation

1. Set your Infura API key in `eth_simulation.py`:
   ```python
   INFURA_KEY = "YOUR_INFURA_KEY"  # Replace with your Infura key
   ```

2. Run the simulation:
   ```bash
   python eth_simulation.py
   ```

## How the Simulation Works

1. **Forking Ethereum Mainnet**: The simulation starts by forking Ethereum mainnet using Anvil, creating a local testnet with pre-funded accounts.

2. **Contract Deployment**: The NFTBundleMarket and MockERC721 contracts are deployed to the local testnet.

3. **NFT Creation**: The simulation mints NFTs to the seller account.

4. **Bundle Creation**: The seller creates a bundle of NFTs with a specified price.

5. **Buyer Interest**: Multiple buyers express interest in different NFTs within the bundle.

6. **Shapley Value Calculation**: The simulation calculates Shapley values for each buyer based on their interests.

7. **Bundle Purchase**: Buyers complete the purchase by paying their Shapley values.

## Troubleshooting

- **Anvil Connection Issues**: Make sure no other process is using port 8545.
- **Contract Compilation Errors**: Ensure you have the latest version of Foundry installed.
- **Missing Contract JSON**: Make sure you've compiled the contracts with `forge build`.

## Manual Testing with Anvil

You can also manually test with Anvil by running:

```bash
# Start Anvil with a fork of Ethereum mainnet
anvil --fork-url https://mainnet.infura.io/v3/YOUR_INFURA_KEY

# In another terminal, deploy the contracts
cd thefoundry
forge script script/DeployContracts.s.sol --rpc-url http://localhost:8545 --broadcast
``` 