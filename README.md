# Bundle Marketplace with Shapley Value Pricing

This project implements a proof-of-concept for an bundle marketplace where multiple buyers can cooperatively purchase bundles of assets (groceries, cars, online orders) represented as unique ERC-721s (NFT) with fair pricing based on Shapley value calculations.

## Overview

The marketplace allows sellers to create bundles of items with a total price and a required number of buyers. Buyers can express interest in specific assets within a bundle. Once enough buyers express interest, the system calculates Shapley values to determine a fair price for each buyer based on their preferences and factors in possible subcoalitions.

### Key Features

- **NFT Bundling**: Sellers can bundle multiple assets together with a single price
- **Cooperative Buying**: Multiple buyers can join together to purchase a bundle
- **Fair Pricing**: Shapley value calculation ensures each buyer pays a fair price based on their preferences
- **TEE Integration**: Simulated Trusted Execution Environment (TEE) for secure Shapley value calculation
- **Smart Contract**: Escrow functionality for secure transactions

## Components

1. **Smart Contract (`NFTBundleMarket.sol`)**: Handles the on-chain logic for NFT escrow, bundle creation, and purchase coordination
2. **Shapley Calculator (`shapley_calculator.py`)**: Implements the Shapley value calculation algorithm
3. **Simulation (`simulation.py`)**: Provides a simulation of the marketplace for testing
4. **Streamlit App (`app.py`)**: User interface for interacting with the marketplace

## Getting Started

### Prerequisites

- Python 3.8+
- Solidity compiler (for smart contract deployment)
- EVM-compatible blockchain (for production deployment)

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the Simulation

To run the simulation and see how the marketplace works:

```
python simulation.py
```

### Running the Streamlit App

To start the Streamlit app:

```
streamlit run app.py
```

## Usage

### For Sellers

1. List your NFTs in the marketplace
2. Create bundles with your NFTs, setting a total price and required number of buyers
3. Wait for buyers to express interest and complete purchases

### For Buyers

1. Browse available bundles
2. Express interest in specific NFTs within a bundle
3. Once enough buyers express interest, request attestation for Shapley value calculation
4. Pay your fair share based on the calculated Shapley value
5. Receive your NFTs once all buyers have paid

## Shapley Value Calculation

The Shapley value provides a fair way to distribute the total cost of a bundle among buyers based on their marginal contributions. It considers all possible orderings of buyers and calculates each buyer's average marginal contribution.

For example, if three buyers are interested in different combinations of NFTs in a bundle:
- Buyer 1 wants NFTs A and B
- Buyer 2 wants NFTs B and C
- Buyer 3 wants NFTs A and C

The Shapley value calculation will determine how much each buyer should pay based on the value they contribute to the overall purchase.

## Future Enhancements

- Integration with a real blockchain network
- Actual TEE implementation for secure Shapley value calculation
- Support for ERC-1155 tokens (semi-fungible NFTs)
- Auction-based pricing for bundles
- Time-limited bundles

## License

MIT 
