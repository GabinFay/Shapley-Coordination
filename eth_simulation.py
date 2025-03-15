import json
import time
import subprocess
import os
import signal
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
import random
from typing import Dict, List, Tuple, Set
from shapley_calculator import ShapleyCalculator

# Configuration
ANVIL_PORT = 8545
INFURA_KEY = "YOUR_INFURA_KEY"  # Replace with your Infura key
FORK_URL = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
FORK_BLOCK_NUMBER = 19000000  # A recent block number

# Path to the compiled contract JSON (this will be generated when we compile the contract)
CONTRACT_JSON_PATH = "shapley/thefoundry/out/NFTBundleMarket.sol/NFTBundleMarket.json"

# Mock NFT contract for testing
MOCK_NFT_JSON_PATH = "shapley/thefoundry/out/MockERC721.sol/MockERC721.json"

class AnvilProcess:
    """Manages the Anvil process for forking Ethereum mainnet"""
    def __init__(self, fork_url=None, fork_block_number=None, port=8545):
        self.fork_url = fork_url
        self.fork_block_number = fork_block_number
        self.port = port
        self.process = None
        
    def start(self):
        """Start the Anvil process"""
        cmd = ["anvil", "--port", str(self.port)]
        
        if self.fork_url:
            cmd.extend(["--fork-url", self.fork_url])
            
        if self.fork_block_number:
            cmd.extend(["--fork-block-number", str(self.fork_block_number)])
            
        # Add additional flags for better logging and deterministic behavior
        cmd.extend([
            "--block-time", "1",  # 1 second block time for faster testing
            "--accounts", "10",   # Create 10 test accounts
        ])
        
        print(f"Starting Anvil with command: {' '.join(cmd)}")
        self.process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for Anvil to start
        time.sleep(3)
        print("Anvil started successfully")
        
    def stop(self):
        """Stop the Anvil process"""
        if self.process:
            print("Stopping Anvil...")
            self.process.terminate()
            self.process.wait()
            self.process = None
            print("Anvil stopped")


class EthereumSimulation:
    """Simulation for the NFT Bundle Marketplace on Ethereum"""
    def __init__(self, web3_provider):
        self.w3 = Web3(web3_provider)
        # Add middleware for POA chains (might be needed for some forks)
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Check connection
        if not self.w3.is_connected():
            raise Exception("Failed to connect to Ethereum node")
            
        print(f"Connected to Ethereum node. Chain ID: {self.w3.eth.chain_id}")
        print(f"Current block number: {self.w3.eth.block_number}")
        
        # Get test accounts
        self.accounts = [self.w3.eth.account.from_key(private_key) 
                        for private_key in self.w3.eth.accounts]
        
        # Set default account for transactions
        self.w3.eth.default_account = self.accounts[0].address
        
        # Contract instances
        self.nft_bundle_market = None
        self.mock_nft = None
        
    def load_contract(self, contract_json_path, address=None):
        """Load a contract from its compiled JSON file"""
        with open(contract_json_path, 'r') as f:
            contract_json = json.load(f)
            
        abi = contract_json['abi']
        bytecode = contract_json.get('bytecode', {}).get('object', '')
        
        contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        
        if address:
            return self.w3.eth.contract(address=address, abi=abi)
        
        return contract
    
    def deploy_contract(self, contract, *args, from_account=None):
        """Deploy a contract to the blockchain"""
        if from_account is None:
            from_account = self.accounts[0]
            
        # Estimate gas for deployment
        gas_estimate = contract.constructor(*args).estimate_gas()
        
        # Build transaction
        txn = contract.constructor(*args).build_transaction({
            'from': from_account.address,
            'nonce': self.w3.eth.get_transaction_count(from_account.address),
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_txn = from_account.sign_transaction(txn)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for transaction receipt
        txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        # Get contract address
        contract_address = txn_receipt['contractAddress']
        print(f"Contract deployed at: {contract_address}")
        
        # Return contract instance
        return self.w3.eth.contract(address=contract_address, abi=contract.abi)
    
    def setup_contracts(self):
        """Set up the NFT Bundle Market and Mock NFT contracts"""
        try:
            # Load contract definitions
            nft_bundle_market_contract = self.load_contract(CONTRACT_JSON_PATH)
            mock_nft_contract = self.load_contract(MOCK_NFT_JSON_PATH)
            
            # Deploy contracts
            self.mock_nft = self.deploy_contract(
                mock_nft_contract, 
                "MockNFT", 
                "MNFT",
                from_account=self.accounts[0]
            )
            
            self.nft_bundle_market = self.deploy_contract(
                nft_bundle_market_contract,
                from_account=self.accounts[0]
            )
            
            print("Contracts deployed successfully")
            return True
        except Exception as e:
            print(f"Error setting up contracts: {e}")
            return False
    
    def mint_nfts(self, to_account, count=3):
        """Mint NFTs to a specific account"""
        nfts = []
        for i in range(count):
            # Mint NFT
            txn = self.mock_nft.functions.mint(
                to_account.address, 
                i, 
                f"Artwork {i}"
            ).build_transaction({
                'from': self.accounts[0].address,
                'nonce': self.w3.eth.get_transaction_count(self.accounts[0].address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_txn = self.accounts[0].sign_transaction(txn)
            txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            self.w3.eth.wait_for_transaction_receipt(txn_hash)
            
            nfts.append(i)  # Store token ID
            
        print(f"Minted {count} NFTs to {to_account.address}")
        return nfts
    
    def approve_nfts(self, owner_account, token_ids):
        """Approve NFTs for the marketplace contract"""
        for token_id in token_ids:
            txn = self.mock_nft.functions.approve(
                self.nft_bundle_market.address,
                token_id
            ).build_transaction({
                'from': owner_account.address,
                'nonce': self.w3.eth.get_transaction_count(owner_account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_txn = owner_account.sign_transaction(txn)
            txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            self.w3.eth.wait_for_transaction_receipt(txn_hash)
            
        print(f"Approved {len(token_ids)} NFTs for marketplace")
    
    def list_nft(self, seller_account, token_id):
        """List an NFT in the marketplace"""
        txn = self.nft_bundle_market.functions.listNFT(
            self.mock_nft.address,
            token_id
        ).build_transaction({
            'from': seller_account.address,
            'nonce': self.w3.eth.get_transaction_count(seller_account.address),
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_txn = seller_account.sign_transaction(txn)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        # Parse the NFTListed event to get the item ID
        logs = self.nft_bundle_market.events.NFTListed().process_receipt(receipt)
        item_id = logs[0]['args']['itemId']
        
        print(f"Listed NFT with token ID {token_id} as item ID {item_id}")
        return item_id
    
    def create_bundle(self, seller_account, item_ids, price, required_buyers):
        """Create a bundle of NFTs"""
        txn = self.nft_bundle_market.functions.createBundle(
            item_ids,
            self.w3.to_wei(price, 'ether'),
            required_buyers
        ).build_transaction({
            'from': seller_account.address,
            'nonce': self.w3.eth.get_transaction_count(seller_account.address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_txn = seller_account.sign_transaction(txn)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        # Parse the BundleCreated event to get the bundle ID
        logs = self.nft_bundle_market.events.BundleCreated().process_receipt(receipt)
        bundle_id = logs[0]['args']['bundleId']
        
        print(f"Created bundle {bundle_id} with {len(item_ids)} items for {price} ETH")
        return bundle_id
    
    def express_interest(self, buyer_account, bundle_id, item_ids):
        """Express interest in a bundle"""
        txn = self.nft_bundle_market.functions.expressInterest(
            bundle_id,
            item_ids
        ).build_transaction({
            'from': buyer_account.address,
            'nonce': self.w3.eth.get_transaction_count(buyer_account.address),
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_txn = buyer_account.sign_transaction(txn)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        print(f"Buyer {buyer_account.address} expressed interest in bundle {bundle_id}")
    
    def request_attestation(self, account, bundle_id):
        """Request attestation for Shapley value calculation"""
        txn = self.nft_bundle_market.functions.requestAttestation(
            bundle_id
        ).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_txn = account.sign_transaction(txn)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        print(f"Attestation requested for bundle {bundle_id}")
    
    def set_shapley_values(self, calculator_account, bundle_id, buyers, values):
        """Set Shapley values for a bundle"""
        # Convert values to wei
        values_wei = [self.w3.to_wei(value, 'ether') for value in values]
        
        txn = self.nft_bundle_market.functions.setShapleyValues(
            bundle_id,
            buyers,
            values_wei
        ).build_transaction({
            'from': calculator_account.address,
            'nonce': self.w3.eth.get_transaction_count(calculator_account.address),
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_txn = calculator_account.sign_transaction(txn)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        print(f"Shapley values set for bundle {bundle_id}")
    
    def complete_bundle_purchase(self, buyer_account, bundle_id, value):
        """Complete a bundle purchase"""
        txn = self.nft_bundle_market.functions.completeBundlePurchase(
            bundle_id
        ).build_transaction({
            'from': buyer_account.address,
            'nonce': self.w3.eth.get_transaction_count(buyer_account.address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price,
            'value': self.w3.to_wei(value, 'ether')
        })
        
        signed_txn = buyer_account.sign_transaction(txn)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        print(f"Buyer {buyer_account.address} completed purchase for bundle {bundle_id}")
    
    def get_bundle_info(self, bundle_id):
        """Get information about a bundle"""
        bundle_info = self.nft_bundle_market.functions.getBundleInfo(bundle_id).call()
        
        return {
            'item_ids': bundle_info[0],
            'price': self.w3.from_wei(bundle_info[1], 'ether'),
            'required_buyers': bundle_info[2],
            'active': bundle_info[3],
            'interested_buyers': bundle_info[4],
            'completed': bundle_info[5]
        }
    
    def get_buyer_interests(self, bundle_id, buyer_address):
        """Get the items a buyer is interested in for a specific bundle"""
        return self.nft_bundle_market.functions.getBuyerInterests(bundle_id, buyer_address).call()
    
    def get_shapley_value(self, bundle_id, buyer_address):
        """Get the Shapley value for a buyer in a bundle"""
        value_wei = self.nft_bundle_market.functions.shapleyValues(bundle_id, buyer_address).call()
        return self.w3.from_wei(value_wei, 'ether')
    
    def calculate_shapley_values(self, bundle_id, bundle_price):
        """Calculate Shapley values for a bundle using our ShapleyCalculator"""
        bundle_info = self.get_bundle_info(bundle_id)
        
        # Get buyer interests
        buyer_interests = {}
        for buyer in bundle_info['interested_buyers']:
            items = self.get_buyer_interests(bundle_id, buyer)
            buyer_interests[buyer] = items
        
        # Calculate Shapley values
        calculator = ShapleyCalculator(float(bundle_price))
        shapley_values = calculator.calculate_values(buyer_interests)
        
        return shapley_values


def run_ethereum_simulation():
    """Run a full simulation of the NFT bundle marketplace on Ethereum"""
    print("=== Starting NFT Bundle Marketplace Ethereum Simulation ===")
    
    # Start Anvil process
    anvil = AnvilProcess(fork_url=FORK_URL, fork_block_number=FORK_BLOCK_NUMBER, port=ANVIL_PORT)
    
    try:
        anvil.start()
        
        # Connect to the local Ethereum node
        provider = Web3.HTTPProvider(f"http://localhost:{ANVIL_PORT}")
        simulation = EthereumSimulation(provider)
        
        # Set up contracts
        if not simulation.setup_contracts():
            print("Failed to set up contracts. Exiting simulation.")
            return
        
        # Get accounts for simulation
        seller = simulation.accounts[0]  # Contract deployer/owner
        alice = simulation.accounts[1]
        bob = simulation.accounts[2]
        charlie = simulation.accounts[3]
        
        print("\n=== Accounts ===")
        print(f"Seller: {seller.address}")
        print(f"Alice: {alice.address}")
        print(f"Bob: {bob.address}")
        print(f"Charlie: {charlie.address}")
        
        # Mint NFTs to seller
        token_ids = simulation.mint_nfts(seller, count=3)
        
        # Approve NFTs for marketplace
        simulation.approve_nfts(seller, token_ids)
        
        # List NFTs in marketplace
        item_ids = []
        for token_id in token_ids:
            item_id = simulation.list_nft(seller, token_id)
            item_ids.append(item_id)
        
        print("\n=== NFTs Listed ===")
        print(f"Item IDs: {item_ids}")
        
        # Create bundle with all NFTs
        bundle_price = 0.1  # 0.1 ETH
        bundle_id = simulation.create_bundle(seller, item_ids, bundle_price, 3)
        
        print("\n=== Bundle Created ===")
        print(f"Bundle ID: {bundle_id}")
        print(f"Bundle Price: {bundle_price} ETH")
        
        # Buyers express interest
        simulation.express_interest(alice, bundle_id, [item_ids[0], item_ids[1]])
        simulation.express_interest(bob, bundle_id, [item_ids[1], item_ids[2]])
        simulation.express_interest(charlie, bundle_id, [item_ids[0], item_ids[2]])
        
        print("\n=== Buyers Expressed Interest ===")
        
        # Request attestation
        simulation.request_attestation(alice, bundle_id)
        
        # Calculate Shapley values
        shapley_values = simulation.calculate_shapley_values(bundle_id, bundle_price)
        
        print("\n=== Shapley Values Calculated ===")
        for buyer, value in shapley_values.items():
            print(f"{buyer}: {value} ETH")
        
        # Set Shapley values in the contract
        buyer_addresses = [alice.address, bob.address, charlie.address]
        values = [shapley_values[addr] for addr in buyer_addresses]
        
        simulation.set_shapley_values(seller, bundle_id, buyer_addresses, values)
        
        print("\n=== Shapley Values Set in Contract ===")
        
        # Complete bundle purchase
        simulation.complete_bundle_purchase(alice, bundle_id, shapley_values[alice.address])
        simulation.complete_bundle_purchase(bob, bundle_id, shapley_values[bob.address])
        simulation.complete_bundle_purchase(charlie, bundle_id, shapley_values[charlie.address])
        
        print("\n=== Bundle Purchase Completed ===")
        
        # Get final bundle state
        final_bundle_info = simulation.get_bundle_info(bundle_id)
        
        print("\n=== Final Bundle State ===")
        print(f"Bundle ID: {bundle_id}")
        print(f"Active: {final_bundle_info['active']}")
        print(f"Completed: {final_bundle_info['completed']}")
        
        print("\n=== Simulation Complete ===")
        
    except Exception as e:
        print(f"Error in simulation: {e}")
    finally:
        # Stop Anvil process
        anvil.stop()


if __name__ == "__main__":
    run_ethereum_simulation() 