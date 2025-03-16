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
FORK_URL = f"https://sepolia.infura.io/v3/{INFURA_KEY}"  # Using Sepolia testnet
FORK_BLOCK_NUMBER = 5000000  # A recent Sepolia block number

# Path to the compiled contract JSON
CONTRACT_JSON_PATH = "thefoundry/out/NFTBundleMarket.sol/NFTBundleMarket.json"
MOCK_NFT_JSON_PATH = "thefoundry/out/MockERC721.sol/MockERC721.json"

class AnvilProcess:
    """Manages the Anvil process for forking Ethereum Sepolia testnet"""
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


class SepoliaSimulation:
    """Simulation for the NFT Bundle Marketplace on Ethereum Sepolia"""
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
        
        # Store deployed contract addresses and other simulation data
        self.simulation_data = {
            "marketplace_address": None,
            "nft_address": None,
            "accounts": [account.address for account in self.accounts],
            "nfts": [],
            "bundles": [],
            "almost_full_bundle": None,
            "almost_purchased_bundle": None
        }
        
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
                    "SepoliaNFT", 
                    "SNFT",
                    from_account=self.accounts[0]
                )
                print(f"MockNFT deployed at: {self.mock_nft.address}")
                self.simulation_data["nft_address"] = self.mock_nft.address
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
                self.simulation_data["marketplace_address"] = self.nft_bundle_market.address
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
    
    def mint_nfts(self, to_account, count=3, start_id=0, names=None):
        """Mint NFTs to a specific account"""
        nfts = []
        
        if names is None:
            names = [f"Artwork {i+start_id}" for i in range(count)]
        
        for i in range(count):
            token_id = i + start_id
            name = names[i] if i < len(names) else f"Artwork {token_id}"
            
            # Mint NFT
            txn = self.mock_nft.functions.mint(
                to_account.address, 
                token_id, 
                name
            ).build_transaction({
                'from': self.accounts[0].address,
                'nonce': self.w3.eth.get_transaction_count(self.accounts[0].address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_txn = self.accounts[0].sign_transaction(txn)
            txn_hash = self._send_raw_transaction(signed_txn)
            self.w3.eth.wait_for_transaction_receipt(txn_hash)
            
            nfts.append(token_id)  # Store token ID
            
            # Add to simulation data
            self.simulation_data["nfts"].append({
                "token_id": token_id,
                "name": name,
                "owner": to_account.address
            })
            
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
    
    def create_bundle(self, seller_account, item_ids, price, required_buyers, name=None):
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
        
        bundle_info = {
            "id": bundle_id,
            "name": name if name else f"Bundle {bundle_id}",
            "item_ids": item_ids,
            "price": price,
            "required_buyers": required_buyers,
            "seller": seller_account.address,
            "interested_buyers": [],
            "completed": False
        }
        
        self.simulation_data["bundles"].append(bundle_info)
        
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
        
        # Update simulation data
        for bundle in self.simulation_data["bundles"]:
            if bundle["id"] == bundle_id:
                if buyer_account.address not in bundle["interested_buyers"]:
                    bundle["interested_buyers"].append({
                        "address": buyer_account.address,
                        "items": item_ids
                    })
                break
        
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
        
        # Update simulation data
        for bundle in self.simulation_data["bundles"]:
            if bundle["id"] == bundle_id:
                bundle["shapley_values"] = {
                    buyers[i]: values[i] for i in range(len(buyers))
                }
                break
        
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
        receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        # Update simulation data
        for bundle in self.simulation_data["bundles"]:
            if bundle["id"] == bundle_id:
                for buyer in bundle["interested_buyers"]:
                    if buyer["address"] == buyer_account.address:
                        buyer["paid"] = True
                
                # Check if all buyers have paid
                all_paid = all(buyer.get("paid", False) for buyer in bundle["interested_buyers"])
                if all_paid:
                    bundle["completed"] = True
                    
                    # Update NFT ownership
                    for buyer in bundle["interested_buyers"]:
                        for item_id in buyer["items"]:
                            for nft in self.simulation_data["nfts"]:
                                if nft["token_id"] == item_id:
                                    nft["owner"] = buyer["address"]
                break
        
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
    
    def calculate_shapley_values(self, bundle_id, bundle_price):
        """Calculate Shapley values for a bundle using our ShapleyCalculator"""
        bundle_info = self.get_bundle_info(bundle_id)
        
        # Get buyer interests
        buyer_interests = {}
        for buyer in bundle_info['interested_buyers']:
            items = self.nft_bundle_market.functions.getBuyerInterests(bundle_id, buyer).call()
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
    
    def save_simulation_data(self, filename="sepolia_simulation_data.json"):
        """Save simulation data to a JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.simulation_data, f, indent=2)
        print(f"Simulation data saved to {filename}")


def setup_sepolia_environment():
    """Set up a simulated Sepolia environment with NFTs and bundles in different states"""
    print("=== Starting NFT Bundle Marketplace Sepolia Simulation ===")
    
    # Start Anvil process
    anvil = AnvilProcess(fork_url=FORK_URL, fork_block_number=FORK_BLOCK_NUMBER, port=ANVIL_PORT)
    
    try:
        anvil.start()
        
        # Connect to the local Ethereum node
        provider = Web3.HTTPProvider(f"http://localhost:{ANVIL_PORT}")
        simulation = SepoliaSimulation(provider)
        
        # Set up contracts
        if not simulation.setup_contracts():
            print("Failed to set up contracts. Exiting simulation.")
            return
        
        # Get accounts for simulation
        seller = simulation.accounts[0]  # Contract deployer/owner
        alice = simulation.accounts[1]
        bob = simulation.accounts[2]
        charlie = simulation.accounts[3]
        dave = simulation.accounts[4]
        
        print("\n=== Accounts ===")
        print(f"Seller: {seller.address}")
        print(f"Alice: {alice.address}")
        print(f"Bob: {bob.address}")
        print(f"Charlie: {charlie.address}")
        print(f"Dave: {dave.address}")
        
        # Create NFT collections with themed names
        art_collection_names = ["Sunset Horizon", "Mountain Peak", "Ocean Wave", "Forest Path", "Desert Dunes"]
        game_collection_names = ["Dragon Slayer", "Magic Wand", "Ancient Sword", "Mystic Shield", "Golden Armor"]
        music_collection_names = ["Vinyl Record", "Electric Guitar", "Grand Piano", "Drum Set", "Saxophone"]
        
        # Mint NFTs to seller
        art_tokens = simulation.mint_nfts(seller, count=5, start_id=0, names=art_collection_names)
        game_tokens = simulation.mint_nfts(seller, count=5, start_id=100, names=game_collection_names)
        music_tokens = simulation.mint_nfts(seller, count=5, start_id=200, names=music_collection_names)
        
        # Approve NFTs for marketplace
        simulation.approve_nfts(seller, art_tokens + game_tokens + music_tokens)
        
        # List NFTs in marketplace
        art_item_ids = []
        for token_id in art_tokens:
            item_id = simulation.list_nft(seller, token_id)
            art_item_ids.append(item_id)
        
        game_item_ids = []
        for token_id in game_tokens:
            item_id = simulation.list_nft(seller, token_id)
            game_item_ids.append(item_id)
        
        music_item_ids = []
        for token_id in music_tokens:
            item_id = simulation.list_nft(seller, token_id)
            music_item_ids.append(item_id)
        
        print("\n=== NFTs Listed ===")
        print(f"Art Collection Item IDs: {art_item_ids}")
        print(f"Game Collection Item IDs: {game_item_ids}")
        print(f"Music Collection Item IDs: {music_item_ids}")
        
        # Create bundles with different themes
        art_bundle_id = simulation.create_bundle(seller, art_item_ids, 0.15, 3, "Art Collection Bundle")
        game_bundle_id = simulation.create_bundle(seller, game_item_ids, 0.2, 3, "Game Items Bundle")
        music_bundle_id = simulation.create_bundle(seller, music_item_ids, 0.18, 3, "Music Collection Bundle")
        
        # Create a mixed bundle
        mixed_items = [art_item_ids[0], game_item_ids[1], music_item_ids[2]]
        mixed_bundle_id = simulation.create_bundle(seller, mixed_items, 0.1, 3, "Mixed Collection Bundle")
        
        print("\n=== Bundles Created ===")
        print(f"Art Bundle ID: {art_bundle_id}")
        print(f"Game Bundle ID: {game_bundle_id}")
        print(f"Music Bundle ID: {music_bundle_id}")
        print(f"Mixed Bundle ID: {mixed_bundle_id}")
        
        # Set up a 2/3 almost full bundle (for interest)
        # This bundle has 2 out of 3 required buyers expressing interest
        simulation.express_interest(alice, art_bundle_id, [art_item_ids[0], art_item_ids[1]])
        simulation.express_interest(bob, art_bundle_id, [art_item_ids[2], art_item_ids[3]])
        
        # Store this as our almost full bundle
        simulation.simulation_data["almost_full_bundle"] = art_bundle_id
        
        print("\n=== Almost Full Bundle Setup ===")
        print(f"Bundle ID: {art_bundle_id}")
        print(f"Alice is interested in items: {[art_item_ids[0], art_item_ids[1]]}")
        print(f"Bob is interested in items: {[art_item_ids[2], art_item_ids[3]]}")
        print(f"Waiting for one more buyer to express interest")
        
        # Set up a 2/3 almost purchased bundle
        # This bundle has all 3 required buyers expressing interest, and 2 have completed purchase
        simulation.express_interest(alice, game_bundle_id, [game_item_ids[0], game_item_ids[1]])
        simulation.express_interest(bob, game_bundle_id, [game_item_ids[2], game_item_ids[3]])
        simulation.express_interest(charlie, game_bundle_id, [game_item_ids[1], game_item_ids[4]])
        
        # Request attestation and set Shapley values
        simulation.request_attestation(alice, game_bundle_id)
        
        # Calculate and set
        # Calculate and set Shapley values
        bundle_price = 0.2  # Game bundle price
        shapley_values = simulation.calculate_shapley_values(game_bundle_id, bundle_price)
        
        buyer_addresses = [alice.address, bob.address, charlie.address]
        values = [shapley_values.get(addr, bundle_price/3) for addr in buyer_addresses]
        
        simulation.set_shapley_values(seller, game_bundle_id, buyer_addresses, values)
        
        # Complete purchase for 2 out of 3 buyers
        simulation.complete_bundle_purchase(alice, game_bundle_id, values[0])
        simulation.complete_bundle_purchase(bob, game_bundle_id, values[1])
        
        # Store this as our almost purchased bundle
        simulation.simulation_data["almost_purchased_bundle"] = game_bundle_id
        
        print("\n=== Almost Purchased Bundle Setup ===")
        print(f"Bundle ID: {game_bundle_id}")
        print(f"Alice has paid her share: {values[0]} ETH")
        print(f"Bob has paid his share: {values[1]} ETH")
        print(f"Charlie still needs to pay: {values[2]} ETH")
        
        # Set up a fully completed bundle for reference
        simulation.express_interest(alice, music_bundle_id, [music_item_ids[0], music_item_ids[1]])
        simulation.express_interest(bob, music_bundle_id, [music_item_ids[2], music_item_ids[3]])
        simulation.express_interest(charlie, music_bundle_id, [music_item_ids[1], music_item_ids[4]])
        
        # Request attestation and set Shapley values
        simulation.request_attestation(alice, music_bundle_id)
        
        # Calculate and set Shapley values
        bundle_price = 0.18  # Music bundle price
        shapley_values = simulation.calculate_shapley_values(music_bundle_id, bundle_price)
        
        buyer_addresses = [alice.address, bob.address, charlie.address]
        values = [shapley_values.get(addr, bundle_price/3) for addr in buyer_addresses]
        
        simulation.set_shapley_values(seller, music_bundle_id, buyer_addresses, values)
        
        # Complete purchase for all buyers
        simulation.complete_bundle_purchase(alice, music_bundle_id, values[0])
        simulation.complete_bundle_purchase(bob, music_bundle_id, values[1])
        simulation.complete_bundle_purchase(charlie, music_bundle_id, values[2])
        
        print("\n=== Completed Bundle Setup ===")
        print(f"Bundle ID: {music_bundle_id}")
        print(f"All buyers have paid their shares")
        print(f"NFTs have been distributed to the buyers")
        
        # Set up the mixed bundle with just one interested buyer
        simulation.express_interest(dave, mixed_bundle_id, [mixed_items[0], mixed_items[2]])
        
        print("\n=== Mixed Bundle Setup ===")
        print(f"Bundle ID: {mixed_bundle_id}")
        print(f"Dave is interested in items: {[mixed_items[0], mixed_items[2]]}")
        print(f"Waiting for more buyers to express interest")
        
        # Save all simulation data to a file
        simulation.save_simulation_data()
        
        print("\n=== Simulation Environment Ready ===")
        print("You can now connect your frontend to the local Anvil node")
        print(f"Marketplace Contract: {simulation.simulation_data['marketplace_address']}")
        print(f"NFT Contract: {simulation.simulation_data['nft_address']}")
        print(f"Almost Full Bundle ID (2/3 interested): {simulation.simulation_data['almost_full_bundle']}")
        print(f"Almost Purchased Bundle ID (2/3 paid): {simulation.simulation_data['almost_purchased_bundle']}")
        
        # Keep the Anvil process running
        print("\nPress Ctrl+C to stop the simulation...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping simulation...")
        
    except Exception as e:
        print(f"Error in simulation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop Anvil process
        anvil.stop()


def run_sepolia_simulation():
    """Run the Sepolia simulation"""
    setup_sepolia_environment()


if __name__ == "__main__":
    run_sepolia_simulation()