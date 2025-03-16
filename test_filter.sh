#!/bin/bash

# test_filter.sh - Test the Anvil filter scripts
# Usage: ./test_filter.sh

echo "Testing Anvil filter scripts..."

# Create a test input file
cat > test_input.txt << EOF
eth_getTransactionReceipt
eth_chainId
eth_blockNumber

    Block Number: 1
    Block Hash: 0x91662e815565ee95d8fcfdb2c658f503734a09a4e9c8a767c9f99e5b1cca0db1
    Block Time: "Sun, 16 Mar 2025 17:55:06 +0000"

    Block Number: 2
    Block Hash: 0xb8455a65051f03eedd877448065d017389784da2ac0c256e2c778b5a93154c70
    Block Time: "Sun, 16 Mar 2025 17:55:07 +0000"

    Block Number: 3
    Block Hash: 0xf10ff5117949ec32ca317e366345849b14db90c5df901fd55a6f395ce61064d8
    Block Time: "Sun, 16 Mar 2025 17:55:08 +0000"

    Block Number: 4
    Block Hash: 0xf10ff5117949ec32ca317e366345849b14db90c5df901fd55a6f395ce61064d8
    Block Time: "Sun, 16 Mar 2025 17:55:09 +0000"

    Block Number: 5
    Block Hash: 0xf10ff5117949ec32ca317e366345849b14db90c5df901fd55a6f395ce61064d8
    Block Time: "Sun, 16 Mar 2025 17:55:10 +0000"

    Block Number: 6
    Block Hash: 0xf10ff5117949ec32ca317e366345849b14db90c5df901fd55a6f395ce61064d8
    Block Time: "Sun, 16 Mar 2025 17:55:11 +0000"

    Block Number: 10
    Block Hash: 0xf10ff5117949ec32ca317e366345849b14db90c5df901fd55a6f395ce61064d8
    Block Time: "Sun, 16 Mar 2025 17:55:15 +0000"

    Block Number: 11
    Block Hash: 0xf10ff5117949ec32ca317e366345849b14db90c5df901fd55a6f395ce61064d8
    Block Time: "Sun, 16 Mar 2025 17:55:16 +0000"

listNFT called
NFT contract: 0xf1B1ABA247B9953eb36dED56e774c9F3054513D4
Token ID: 1
Seller: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
NFT transferred to contract

    Transaction: 0x229cbaae14e6de724115eb8def5e2fc0fdea55ffde2fdc87d051c7fd89af8775
    Gas used: 167912

expressInterest called
Bundle ID: 1
Buyer: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
Interest expressed successfully

    Block Number: 20
    Block Hash: 0xf10ff5117949ec32ca317e366345849b14db90c5df901fd55a6f395ce61064d8
    Block Time: "Sun, 16 Mar 2025 17:55:25 +0000"

eth_getTransactionReceipt
eth_chainId
eth_blockNumber
EOF

echo "Testing filter_anvil.sh..."
cat test_input.txt | ./filter_anvil.sh > filter_test_output.txt

echo "Testing anvil_logger.sh..."
cat test_input.txt | ./anvil_logger.sh > logger_test_output.txt

echo "Test results:"
echo "============="
echo "filter_anvil.sh output:"
cat filter_test_output.txt
echo ""
echo "============="
echo "anvil_logger.sh output:"
cat logger_test_output.txt
echo ""

# Clean up
rm test_input.txt filter_test_output.txt logger_test_output.txt

echo "Test completed." 