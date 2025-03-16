import json
import time
import subprocess
import os
import signal
from web3 import Web3
from eth_account import Account
import random
from typing import Dict, List, Tuple, Set
from shapley_calculator import ShapleyCalculator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ANVIL_PORT = 8545
INFURA_KEY = os.getenv("INFURA_KEY")  # Get Infura key from environment variable
FORK_URL = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
FORK_BLOCK_NUMBER = 19000000  # A recent block number

# Path to the compiled contract JSON (this will be generated when we compile the contract)
CONTRACT_JSON_PATH = "thefoundry/out/NFTBundleMarket.sol/NFTBundleMarket.json"

# We need to compile the MockERC721 contract first
MOCK_NFT_JSON_PATH = "thefoundry/out/MockERC721.sol/MockERC721.json"

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
            "--hardfork", "shanghai"  # Use Shanghai hardfork for newer EVM features
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
        
        # Check connection
        if not self.w3.is_connected():
            raise Exception("Failed to connect to Ethereum node")
            
        print(f"Connected to Ethereum node. Chain ID: {self.w3.eth.chain_id}")
        print(f"Current block number: {self.w3.eth.block_number}")
        
        # Get test accounts - fixed to handle Anvil's account format
        self.accounts = []
        for addr in self.w3.eth.accounts:
            # For Anvil, we can derive private keys using a known pattern
            # Anvil's default accounts use a known pattern for private keys
            # The first account has key: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
            # We'll use these hardcoded private keys for the first 10 accounts
            if addr.lower() == '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266'.lower():
                self.accounts.append(Account.from_key('0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'))
            elif addr.lower() == '0x70997970c51812dc3a010c7d01b50e0d17dc79c8'.lower():
                self.accounts.append(Account.from_key('0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d'))
            elif addr.lower() == '0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc'.lower():
                self.accounts.append(Account.from_key('0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a'))
            elif addr.lower() == '0x90f79bf6eb2c4f870365e785982e1f101e93b906'.lower():
                self.accounts.append(Account.from_key('0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6'))
            elif addr.lower() == '0x15d34aaf54267db7d7c367839aaf71a00a2c6a65'.lower():
                self.accounts.append(Account.from_key('0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a'))
            elif addr.lower() == '0x9965507d1a55bcc2695c58ba16fb37d819b0a4dc'.lower():
                self.accounts.append(Account.from_key('0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba'))
            elif addr.lower() == '0x976ea74026e726554db657fa54763abd0c3a0aa9'.lower():
                self.accounts.append(Account.from_key('0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e'))
            elif addr.lower() == '0x14dc79964da2c08b23698b3d3cc7ca32193d9955'.lower():
                self.accounts.append(Account.from_key('0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356'))
            elif addr.lower() == '0x23618e81e3f5cdf7f54c3d65f7fbc0abf5b21e8f'.lower():
                self.accounts.append(Account.from_key('0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97'))
            elif addr.lower() == '0xa0ee7a142d267c1f36714e4a8f75612f20a79720'.lower():
                self.accounts.append(Account.from_key('0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6'))
            else:
                print(f"Warning: No known private key for address {addr}")
        
        if not self.accounts:
            raise Exception("Failed to set up test accounts")
            
        print(f"Successfully set up {len(self.accounts)} test accounts")
        
        # Set default account for transactions
        self.w3.eth.default_account = self.accounts[0].address
        
        # Contract instances
        self.nft_bundle_market = None
        self.mock_nft = None
        
        # Counters for IDs (to handle event log issues)
        self.current_item_id = 0
        self.current_bundle_id = 0
        
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
        
        print(f"Deploying contract from account: {from_account.address}")
        
        try:
            # Estimate gas for deployment
            print("Estimating gas for deployment...")
            gas_estimate = contract.constructor(*args).estimate_gas()
            print(f"Gas estimate: {gas_estimate}")
            
            # Build transaction
            print("Building transaction...")
            txn = contract.constructor(*args).build_transaction({
                'from': from_account.address,
                'nonce': self.w3.eth.get_transaction_count(from_account.address),
                'gas': int(gas_estimate * 1.2),  # Add 20% buffer
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            print("Signing transaction...")
            signed_txn = from_account.sign_transaction(txn)
            print("Sending transaction...")
            txn_hash = self._send_raw_transaction(signed_txn)
            print(f"Transaction hash: {txn_hash.hex()}")
            
            # Wait for transaction receipt
            print("Waiting for transaction receipt...")
            txn_receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
            
            # Get contract address
            contract_address = txn_receipt['contractAddress']
            print(f"Contract deployed at: {contract_address}")
            
            # Return contract instance
            return self.w3.eth.contract(address=contract_address, abi=contract.abi)
        except Exception as e:
            print(f"Error in deploy_contract: {e}")
            # Print more details if available
            if hasattr(e, 'args') and len(e.args) > 0:
                print(f"Error details: {e.args}")
            raise
    
    def setup_contracts(self):
        """Set up the NFT Bundle Market and Mock NFT contracts"""
        try:
            # Load contract definitions
            print("Loading contract definitions...")
            nft_bundle_market_contract = self.load_contract(CONTRACT_JSON_PATH)
            mock_nft_contract = self.load_contract(MOCK_NFT_JSON_PATH)
            
            # Deploy contracts with more detailed error handling
            print("Deploying MockNFT contract...")
            try:
                self.mock_nft = self.deploy_contract(
                    mock_nft_contract, 
                    "MockNFT", 
                    "MNFT",
                    from_account=self.accounts[0]
                )
                print(f"MockNFT deployed at: {self.mock_nft.address}")
            except Exception as e:
                print(f"Error deploying MockNFT contract: {e}")
                raise
            
            print("Deploying NFTBundleMarket contract...")
            try:
                self.nft_bundle_market = self.deploy_contract(
                    nft_bundle_market_contract,
                    from_account=self.accounts[0]
                )
                print(f"NFTBundleMarket deployed at: {self.nft_bundle_market.address}")
            except Exception as e:
                print(f"Error deploying NFTBundleMarket contract: {e}")
                raise
            
            print("Contracts deployed successfully")
            return True
        except Exception as e:
            print(f"Error setting up contracts: {e}")
            return False
    
    def _send_raw_transaction(self, signed_txn):
        """Helper method to handle different signed transaction formats"""
        if hasattr(signed_txn, 'raw_transaction'):
            # For web3.py 7.x
            return self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        else:
            # For older versions
            return self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    
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
            txn_hash = self._send_raw_transaction(signed_txn)
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
            txn_hash = self._send_raw_transaction(signed_txn)
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
        txn_hash = self._send_raw_transaction(signed_txn)
        receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        # Try to parse the NFTListed event to get the item ID
        try:
            logs = self.nft_bundle_market.events.NFTListed().process_receipt(receipt)
            if logs and len(logs) > 0:
                item_id = logs[0]['args']['itemId']
            else:
                # If event logs can't be processed, use our counter
                self.current_item_id += 1
                item_id = self.current_item_id
        except Exception as e:
            print(f"Warning: Could not process NFTListed event: {e}")
            # Fallback to counter
            self.current_item_id += 1
            item_id = self.current_item_id
        
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
        txn_hash = self._send_raw_transaction(signed_txn)
        receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        # Try to parse the BundleCreated event to get the bundle ID
        try:
            logs = self.nft_bundle_market.events.BundleCreated().process_receipt(receipt)
            if logs and len(logs) > 0:
                bundle_id = logs[0]['args']['bundleId']
            else:
                # If event logs can't be processed, use our counter
                self.current_bundle_id += 1
                bundle_id = self.current_bundle_id
        except Exception as e:
            print(f"Warning: Could not process BundleCreated event: {e}")
            # Fallback to counter
            self.current_bundle_id += 1
            bundle_id = self.current_bundle_id
        
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
        txn_hash = self._send_raw_transaction(signed_txn)
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
        txn_hash = self._send_raw_transaction(signed_txn)
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
        txn_hash = self._send_raw_transaction(signed_txn)
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
        txn_hash = self._send_raw_transaction(signed_txn)
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
            # Use lowercase addresses as keys for consistency
            buyer_interests[buyer.lower()] = items
        
        # Calculate Shapley values
        calculator = ShapleyCalculator(float(bundle_price))
        shapley_values = calculator.calculate_values(buyer_interests)
        
        # Convert the result back to the original address format
        result = {}
        for buyer in bundle_info['interested_buyers']:
            if buyer.lower() in shapley_values:
                result[buyer] = shapley_values[buyer.lower()]
        
        # If we couldn't calculate values, use equal distribution
        if not result:
            num_buyers = len(bundle_info['interested_buyers'])
            if num_buyers > 0:
                equal_share = float(bundle_price) / num_buyers
                for buyer in bundle_info['interested_buyers']:
                    result[buyer] = equal_share
        
        return result


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


def run_complex_simulation():
    """Run a more complex simulation of the NFT bundle marketplace on Ethereum with multiple bundles"""
    print("=== Starting Complex NFT Bundle Marketplace Ethereum Simulation ===")
    print("=== This simulation demonstrates the benefits of cooperation through bundle pricing ===")
    
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
        
        # Mint NFTs to seller - we'll call them A, B, C for clarity
        token_ids = simulation.mint_nfts(seller, count=3)
        
        # Approve NFTs for marketplace
        simulation.approve_nfts(seller, token_ids)
        
        # List NFTs in marketplace
        item_ids = []
        for token_id in token_ids:
            item_id = simulation.list_nft(seller, token_id)
            item_ids.append(item_id)
        
        # For clarity, let's name our NFTs
        nft_a, nft_b, nft_c = item_ids
        
        print("\n=== NFTs Listed ===")
        print(f"NFT A (Item ID): {nft_a}")
        print(f"NFT B (Item ID): {nft_b}")
        print(f"NFT C (Item ID): {nft_c}")
        
        # Create bundles with different combinations and prices that incentivize cooperation
        # Individual NFT prices (higher)
        price_a = 0.05  # 0.05 ETH
        price_b = 0.05  # 0.05 ETH
        price_c = 0.05  # 0.05 ETH
        
        # Pair bundle prices (lower than sum of individuals)
        price_ab = 0.08  # 0.08 ETH (instead of 0.10)
        price_bc = 0.08  # 0.08 ETH (instead of 0.10)
        price_ac = 0.08  # 0.08 ETH (instead of 0.10)
        
        # Triple bundle price (even lower)
        price_abc = 0.10  # 0.10 ETH (instead of 0.15)
        
        # Create all bundles
        bundle_a = simulation.create_bundle(seller, [nft_a], price_a, 1)
        bundle_b = simulation.create_bundle(seller, [nft_b], price_b, 1)
        bundle_c = simulation.create_bundle(seller, [nft_c], price_c, 1)
        bundle_ab = simulation.create_bundle(seller, [nft_a, nft_b], price_ab, 2)
        bundle_bc = simulation.create_bundle(seller, [nft_b, nft_c], price_bc, 2)
        bundle_ac = simulation.create_bundle(seller, [nft_a, nft_c], price_ac, 2)
        bundle_abc = simulation.create_bundle(seller, [nft_a, nft_b, nft_c], price_abc, 3)
        
        print("\n=== Bundles Created ===")
        print(f"Bundle A: ID {bundle_a}, Price {price_a} ETH")
        print(f"Bundle B: ID {bundle_b}, Price {price_b} ETH")
        print(f"Bundle C: ID {bundle_c}, Price {price_c} ETH")
        print(f"Bundle AB: ID {bundle_ab}, Price {price_ab} ETH (Discount: {price_a + price_b - price_ab} ETH)")
        print(f"Bundle BC: ID {bundle_bc}, Price {price_bc} ETH (Discount: {price_b + price_c - price_bc} ETH)")
        print(f"Bundle AC: ID {bundle_ac}, Price {price_ac} ETH (Discount: {price_a + price_c - price_ac} ETH)")
        print(f"Bundle ABC: ID {bundle_abc}, Price {price_abc} ETH (Discount: {price_a + price_b + price_c - price_abc} ETH)")
        
        # Scenario 1: Individual purchases (no cooperation)
        print("\n=== Scenario 1: Individual Purchases (No Cooperation) ===")
        
        # Alice buys NFT A
        simulation.express_interest(alice, bundle_a, [nft_a])
        simulation.request_attestation(alice, bundle_a)
        shapley_values = simulation.calculate_shapley_values(bundle_a, price_a)
        simulation.set_shapley_values(seller, bundle_a, [alice.address], [shapley_values[alice.address]])
        simulation.complete_bundle_purchase(alice, bundle_a, shapley_values[alice.address])
        
        # Bob buys NFT B
        simulation.express_interest(bob, bundle_b, [nft_b])
        simulation.request_attestation(bob, bundle_b)
        shapley_values = simulation.calculate_shapley_values(bundle_b, price_b)
        simulation.set_shapley_values(seller, bundle_b, [bob.address], [shapley_values[bob.address]])
        simulation.complete_bundle_purchase(bob, bundle_b, shapley_values[bob.address])
        
        # Charlie buys NFT C
        simulation.express_interest(charlie, bundle_c, [nft_c])
        simulation.request_attestation(charlie, bundle_c)
        shapley_values = simulation.calculate_shapley_values(bundle_c, price_c)
        simulation.set_shapley_values(seller, bundle_c, [charlie.address], [shapley_values[charlie.address]])
        simulation.complete_bundle_purchase(charlie, bundle_c, shapley_values[charlie.address])
        
        print(f"Total cost without cooperation: {price_a + price_b + price_c} ETH")
        
        # Scenario 2: Pair cooperation (Alice and Bob cooperate)
        print("\n=== Scenario 2: Pair Cooperation (Alice and Bob) ===")
        
        # Mint new NFTs for this scenario
        new_token_ids = simulation.mint_nfts(seller, count=3)
        simulation.approve_nfts(seller, new_token_ids)
        
        # List new NFTs
        new_item_ids = []
        for token_id in new_token_ids:
            item_id = simulation.list_nft(seller, token_id)
            new_item_ids.append(item_id)
        
        new_nft_a, new_nft_b, new_nft_c = new_item_ids
        
        # Create new bundles
        new_bundle_ab = simulation.create_bundle(seller, [new_nft_a, new_nft_b], price_ab, 2)
        new_bundle_c = simulation.create_bundle(seller, [new_nft_c], price_c, 1)
        
        # Alice and Bob express interest in bundle AB
        simulation.express_interest(alice, new_bundle_ab, [new_nft_a])
        simulation.express_interest(bob, new_bundle_ab, [new_nft_b])
        
        # Calculate Shapley values for bundle AB
        simulation.request_attestation(alice, new_bundle_ab)
        shapley_values_ab = simulation.calculate_shapley_values(new_bundle_ab, price_ab)
        
        print("Shapley Values for Bundle AB:")
        for buyer, value in shapley_values_ab.items():
            print(f"{buyer}: {value} ETH")
        
        # Set Shapley values and complete purchase
        # We need to ensure we have values for both buyers
        alice_value = shapley_values_ab.get(alice.address, price_ab / 2)  # Default to half if not found
        bob_value = shapley_values_ab.get(bob.address, price_ab / 2)      # Default to half if not found
        
        # If we don't have values for both buyers in the dictionary, recalculate manually
        if alice.address not in shapley_values_ab or bob.address not in shapley_values_ab:
            print("Recalculating Shapley values manually...")
            # For a pair with equal interests, Shapley values should be equal
            alice_value = price_ab / 2
            bob_value = price_ab / 2
            print(f"Manual Shapley Values: Alice: {alice_value} ETH, Bob: {bob_value} ETH")
        
        simulation.set_shapley_values(seller, new_bundle_ab, [alice.address, bob.address], 
                                     [alice_value, bob_value])
        simulation.complete_bundle_purchase(alice, new_bundle_ab, alice_value)
        simulation.complete_bundle_purchase(bob, new_bundle_ab, bob_value)
        
        # Charlie buys NFT C individually
        simulation.express_interest(charlie, new_bundle_c, [new_nft_c])
        simulation.request_attestation(charlie, new_bundle_c)
        shapley_values_c = simulation.calculate_shapley_values(new_bundle_c, price_c)
        
        # Ensure we have a value for Charlie
        charlie_value = shapley_values_c.get(charlie.address, price_c)  # Default to full price if not found
        
        simulation.set_shapley_values(seller, new_bundle_c, [charlie.address], [charlie_value])
        simulation.complete_bundle_purchase(charlie, new_bundle_c, charlie_value)
        
        print(f"Total cost with pair cooperation: {price_ab + price_c} ETH")
        print(f"Savings compared to individual purchases: {price_a + price_b + price_c - (price_ab + price_c)} ETH")
        
        # Scenario 3: Full cooperation (All three buyers)
        print("\n=== Scenario 3: Full Cooperation (All Three Buyers) ===")
        
        # Mint new NFTs for this scenario
        final_token_ids = simulation.mint_nfts(seller, count=3)
        simulation.approve_nfts(seller, final_token_ids)
        
        # List new NFTs
        final_item_ids = []
        for token_id in final_token_ids:
            item_id = simulation.list_nft(seller, token_id)
            final_item_ids.append(item_id)
        
        final_nft_a, final_nft_b, final_nft_c = final_item_ids
        
        # Create the ABC bundle
        final_bundle_abc = simulation.create_bundle(seller, [final_nft_a, final_nft_b, final_nft_c], price_abc, 3)
        
        # All buyers express interest
        simulation.express_interest(alice, final_bundle_abc, [final_nft_a])
        simulation.express_interest(bob, final_bundle_abc, [final_nft_b])
        simulation.express_interest(charlie, final_bundle_abc, [final_nft_c])
        
        # Calculate Shapley values
        simulation.request_attestation(alice, final_bundle_abc)
        shapley_values_abc = simulation.calculate_shapley_values(final_bundle_abc, price_abc)
        
        print("Shapley Values for Bundle ABC:")
        for buyer, value in shapley_values_abc.items():
            print(f"{buyer}: {value} ETH")
        
        # Ensure we have values for all buyers
        alice_value_abc = shapley_values_abc.get(alice.address, price_abc / 3)  # Default to equal share if not found
        bob_value_abc = shapley_values_abc.get(bob.address, price_abc / 3)      # Default to equal share if not found
        charlie_value_abc = shapley_values_abc.get(charlie.address, price_abc / 3)  # Default to equal share if not found
        
        # If we don't have values for all buyers in the dictionary, recalculate manually
        if alice.address not in shapley_values_abc or bob.address not in shapley_values_abc or charlie.address not in shapley_values_abc:
            print("Recalculating Shapley values manually...")
            # For three buyers with equal interests, Shapley values should be equal
            alice_value_abc = price_abc / 3
            bob_value_abc = price_abc / 3
            charlie_value_abc = price_abc / 3
            print(f"Manual Shapley Values: Alice: {alice_value_abc} ETH, Bob: {bob_value_abc} ETH, Charlie: {charlie_value_abc} ETH")
        
        # Set Shapley values and complete purchase
        simulation.set_shapley_values(seller, final_bundle_abc, 
                                     [alice.address, bob.address, charlie.address],
                                     [alice_value_abc, bob_value_abc, charlie_value_abc])
        
        simulation.complete_bundle_purchase(alice, final_bundle_abc, alice_value_abc)
        simulation.complete_bundle_purchase(bob, final_bundle_abc, bob_value_abc)
        simulation.complete_bundle_purchase(charlie, final_bundle_abc, charlie_value_abc)
        
        print(f"Total cost with full cooperation: {price_abc} ETH")
        print(f"Savings compared to individual purchases: {price_a + price_b + price_c - price_abc} ETH")
        print(f"Savings compared to pair cooperation: {price_ab + price_c - price_abc} ETH")
        
        print("\n=== Simulation Complete ===")
        print("=== Summary of Cooperation Benefits ===")
        print(f"Individual purchases total cost: {price_a + price_b + price_c} ETH")
        print(f"Pair cooperation (AB + C) total cost: {price_ab + price_c} ETH")
        print(f"Full cooperation (ABC) total cost: {price_abc} ETH")
        print(f"Maximum savings through cooperation: {price_a + price_b + price_c - price_abc} ETH")
        
    except Exception as e:
        print(f"Error in simulation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop Anvil process
        anvil.stop()


if __name__ == "__main__":
    # Uncomment the simulation you want to run
    # run_ethereum_simulation()  # Original simple simulation
    run_complex_simulation()  # Complex simulation with multiple bundles 