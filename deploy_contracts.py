import json
import os
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ANVIL_PORT = 8545
ANVIL_HOST = "0.0.0.0"

# Path to the compiled contract JSON
CONTRACT_JSON_PATH = "thefoundry/out/NFTBundleMarket.sol/NFTBundleMarket.json"
MOCK_NFT_JSON_PATH = "thefoundry/out/MockERC721.sol/MockERC721.json"

class ContractDeployer:
    """Handles deployment of contracts to the local Anvil node"""
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
        
        # Store deployed contract addresses and other simulation data
        self.deployment_data = {
            "marketplace_address": None,
            "nft_address": None,
            "accounts": {
                "seller": self.accounts[0].address,
                "alice": self.accounts[1].address,
                "bob": self.accounts[2].address,
                "charlie": self.accounts[3].address,
                "dave": self.accounts[4].address,
                "tee": self.accounts[5].address  # TEE (Trusted Execution Environment) account
            },
            "private_keys": {
                "seller": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
                "alice": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
                "bob": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
                "charlie": "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
                "dave": "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
                "tee": "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"
            }
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
    
    def _send_raw_transaction(self, signed_txn):
        """Helper method to handle different signed transaction formats"""
        if hasattr(signed_txn, 'raw_transaction'):
            # For web3.py 7.x
            return self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        else:
            # For older versions
            return self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    
    def deploy_contracts(self):
        """Deploy the NFT Bundle Market and Mock NFT contracts"""
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
                self.deployment_data["nft_address"] = self.mock_nft.address
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
                self.deployment_data["marketplace_address"] = self.nft_bundle_market.address
            except Exception as e:
                print(f"Error deploying NFTBundleMarket contract: {e}")
                raise
            
            # Set up the marketplace with initial data
            print("Setting up marketplace with initial data...")
            self.setup_initial_marketplace_data()
            
            print("Contracts deployed successfully")
            return True
        except Exception as e:
            print(f"Error deploying contracts: {e}")
            return False
    
    def setup_initial_marketplace_data(self):
        """Set up initial marketplace data - mint NFTs and create bundles"""
        seller = self.accounts[0]
        
        try:
            # 1. Mint 5 NFTs for the seller
            print("Minting NFTs for seller...")
            nft_ids = []
            nft_names = ["Cosmic Horizon", "Digital Dream", "Ethereal Whisper", "Quantum Pulse", "Virtual Echo"]
            
            for i in range(1, 6):
                name = nft_names[i-1]
                print(f"Minting NFT #{i}: {name}")
                tx = self.mock_nft.functions.mint(
                    seller.address, 
                    i, 
                    name
                ).build_transaction({
                    'from': seller.address,
                    'gas': 200000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(seller.address)
                })
                
                signed_tx = seller.sign_transaction(tx)
                tx_hash = self._send_raw_transaction(signed_tx)
                self.w3.eth.wait_for_transaction_receipt(tx_hash)
                nft_ids.append(i)
                print(f"Minted NFT with ID {i}")
            
            # 2. Approve NFTs for marketplace
            print("Approving NFTs for marketplace...")
            tx = self.mock_nft.functions.setApprovalForAll(
                self.nft_bundle_market.address, 
                True
            ).build_transaction({
                'from': seller.address,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(seller.address)
            })
            
            signed_tx = seller.sign_transaction(tx)
            tx_hash = self._send_raw_transaction(signed_tx)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            print("Approved all NFTs for marketplace")
            
            # 3. List NFTs in marketplace
            print("Listing NFTs in marketplace...")
            item_ids = []
            for nft_id in nft_ids:
                tx = self.nft_bundle_market.functions.listNFT(
                    self.mock_nft.address,
                    nft_id
                ).build_transaction({
                    'from': seller.address,
                    'gas': 200000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(seller.address)
                })
                
                signed_tx = seller.sign_transaction(tx)
                tx_hash = self._send_raw_transaction(signed_tx)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                # Get item ID from event logs
                item_id = None
                for log in receipt['logs']:
                    if log['address'].lower() == self.nft_bundle_market.address.lower():
                        topics = log['topics']
                        if len(topics) >= 3:
                            item_id = int(topics[1].hex(), 16)
                            break
                
                if item_id is None:
                    item_count = self.nft_bundle_market.functions.getItemCount().call()
                    item_id = item_count
                
                item_ids.append(item_id)
                print(f"Listed NFT with ID {nft_id} as item ID {item_id}")
            
            # 4. Create two bundles
            print("Creating bundles...")
            
            # Bundle 1: First two NFTs
            bundle1_items = item_ids[:2]
            bundle1_price = self.w3.to_wei(2, 'ether')
            bundle1_required_buyers = 2
            
            tx = self.nft_bundle_market.functions.createBundleWithMetadata(
                bundle1_items,
                bundle1_price,
                bundle1_required_buyers,
                "Cosmic Digital Bundle",
                "A beautiful collection of cosmic and digital art"
            ).build_transaction({
                'from': seller.address,
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(seller.address)
            })
            
            signed_tx = seller.sign_transaction(tx)
            tx_hash = self._send_raw_transaction(signed_tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Get bundle ID from event logs
            bundle1_id = None
            for log in receipt['logs']:
                if log['address'].lower() == self.nft_bundle_market.address.lower():
                    topics = log['topics']
                    if len(topics) >= 2:
                        bundle1_id = int(topics[1].hex(), 16)
                        break
            
            if bundle1_id is None:
                bundle_count = self.nft_bundle_market.functions.getBundleCount().call()
                bundle1_id = bundle_count
            
            print(f"Created bundle 1 with ID {bundle1_id}")
            
            # Bundle 2: Next two NFTs
            bundle2_items = item_ids[2:4]
            bundle2_price = self.w3.to_wei(3, 'ether')
            bundle2_required_buyers = 2
            
            tx = self.nft_bundle_market.functions.createBundleWithMetadata(
                bundle2_items,
                bundle2_price,
                bundle2_required_buyers,
                "Ethereal Quantum Bundle",
                "Experience the ethereal and quantum realms in this unique collection"
            ).build_transaction({
                'from': seller.address,
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(seller.address)
            })
            
            signed_tx = seller.sign_transaction(tx)
            tx_hash = self._send_raw_transaction(signed_tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Get bundle ID from event logs
            bundle2_id = None
            for log in receipt['logs']:
                if log['address'].lower() == self.nft_bundle_market.address.lower():
                    topics = log['topics']
                    if len(topics) >= 2:
                        bundle2_id = int(topics[1].hex(), 16)
                        break
            
            if bundle2_id is None:
                bundle_count = self.nft_bundle_market.functions.getBundleCount().call()
                bundle2_id = bundle_count
            
            print(f"Created bundle 2 with ID {bundle2_id}")
            
            # 5. Set TEE wallet as Shapley calculator
            tee_wallet = self.accounts[5]
            tx = self.nft_bundle_market.functions.setShapleyCalculator(
                tee_wallet.address
            ).build_transaction({
                'from': seller.address,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(seller.address)
            })
            
            signed_tx = seller.sign_transaction(tx)
            tx_hash = self._send_raw_transaction(signed_tx)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Set TEE wallet as Shapley calculator: {tee_wallet.address}")
            
            # Store the created items and bundles in deployment data
            self.deployment_data["initial_setup"] = {
                "nft_ids": nft_ids,
                "item_ids": item_ids,
                "bundle1_id": bundle1_id,
                "bundle2_id": bundle2_id,
                "tee_wallet": tee_wallet.address
            }
            
            print("Initial marketplace data setup complete")
            
        except Exception as e:
            print(f"Error setting up initial marketplace data: {e}")
            import traceback
            traceback.print_exc()
    
    def save_deployment_data(self, filename="deployment_data.json"):
        """Save deployment data to a JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.deployment_data, f, indent=2)
        print(f"Deployment data saved to {filename}")
        
        # Also save as environment variables for easy access
        with open("deployment.env", "w") as f:
            f.write(f"MARKETPLACE_ADDRESS={self.deployment_data['marketplace_address']}\n")
            f.write(f"MOCK_NFT_ADDRESS={self.deployment_data['nft_address']}\n")
            
            # Write account addresses
            for name, address in self.deployment_data["accounts"].items():
                f.write(f"{name.upper()}_ADDRESS={address}\n")
                
            # Write private keys
            for name, key in self.deployment_data["private_keys"].items():
                f.write(f"{name.upper()}_PRIVATE_KEY={key}\n")
                
        print("Environment variables saved to deployment.env")


def deploy_to_running_anvil():
    """Deploy contracts to an already running Anvil instance"""
    print("=== Deploying Contracts to Running Anvil Instance ===")
    
    try:
        # Connect to the local Ethereum node
        provider = Web3.HTTPProvider(f"http://{ANVIL_HOST}:{ANVIL_PORT}")
        deployer = ContractDeployer(provider)
        
        # Deploy contracts
        if not deployer.deploy_contracts():
            print("Failed to deploy contracts. Exiting.")
            return
        
        # Save deployment data
        deployer.save_deployment_data()
        
        print("\n=== Deployment Complete ===")
        print(f"Marketplace Contract: {deployer.deployment_data['marketplace_address']}")
        print(f"NFT Contract: {deployer.deployment_data['nft_address']}")
        print("Deployment data saved to deployment.env and deployment_data.json")
        
    except Exception as e:
        print(f"Error in deployment: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    deploy_to_running_anvil() 