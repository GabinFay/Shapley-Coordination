#!/bin/bash

# Navigate to the thefoundry directory
cd thefoundry

# Compile all contracts
echo "Compiling contracts..."
forge build

# Check if compilation was successful
if [ $? -eq 0 ]; then
    echo "Contracts compiled successfully!"
    
    # Check if the MockERC721 contract was compiled
    if [ ! -f "out/MockERC721.sol/MockERC721.json" ]; then
        echo "Warning: MockERC721.json not found. Make sure MockERC721.sol is properly imported and compiled."
    fi
    
    # Check if the NFTBundleMarket contract was compiled
    if [ ! -f "out/NFTBundleMarket.sol/NFTBundleMarket.json" ]; then
        echo "Warning: NFTBundleMarket.json not found. Make sure NFTBundleMarket.sol is properly imported and compiled."
    fi
else
    echo "Contract compilation failed!"
    exit 1
fi

cd ..
echo "Done!" 