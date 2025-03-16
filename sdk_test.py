import json
import time
import os
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from nft_bundle_sdk import NFTBundleSDK, NFTItem, Bundle, BuyerInterest, MarketplaceSummary

# Load environment variables
load_dotenv(".env.local")

# Configuration
MARKETPLACE_ADDRESS = os.getenv("MARKETPLACE_ADDRESS")
MOCK_NFT_ADDRESS = os.getenv("MOCK_NFT_ADDRESS")

# Account addresses and private keys
SELLER_ADDRESS = os.getenv("SELLER_ADDRESS")
ALICE_ADDRESS = os.getenv("ALICE_ADDRESS")
BOB_ADDRESS = os.getenv("BOB_ADDRESS")
CHARLIE_ADDRESS = os.getenv("CHARLIE_ADDRESS")
DAVE_ADDRESS = os.getenv("DAVE_ADDRESS")
TEE_ADDRESS = os.getenv("TEE_ADDRESS")  # Trusted Execution Environment address

SELLER_KEY = os.getenv("SELLER_PRIVATE_KEY")
ALICE_KEY = os.getenv("ALICE_PRIVATE_KEY")
BOB_KEY = os.getenv("BOB_PRIVATE_KEY")
CHARLIE_KEY = os.getenv("CHARLIE_PRIVATE_KEY")
DAVE_KEY = os.getenv("DAVE_PRIVATE_KEY")
TEE_KEY = os.getenv("TEE_PRIVATE_KEY")

# Path to contract ABIs
CONTRACT_ABI_PATH = "thefoundry/out/NFTBundleMarket.sol/NFTBundleMarket.json"
MOCK_NFT_ABI_PATH = "thefoundry/out/MockERC721.sol/MockERC721.json"

class SepoliaSimulation:
    """Simulation for the NFT Bundle Marketplace on Ethereum Sepolia"""
    def __init__(self):
        # Connect to local Ethereum node
        self.w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        
        # Check connection
        if not self.w3.is_connected():
            raise Exception("Failed to connect to Ethereum node")
            
        print(f"Connected to Ethereum node. Chain ID: {self.w3.eth.chain_id}")
        
        # Set up accounts
        self.seller = Account.from_key(SELLER_KEY)
        self.alice = Account.from_key(ALICE_KEY)
        self.bob = Account.from_key(BOB_KEY)
        self.charlie = Account.from_key(CHARLIE_KEY)
        self.dave = Account.from_key(DAVE_KEY)
        self.tee = Account.from_key(TEE_KEY)  # TEE account
        
        print("Accounts set up successfully")
        
        # Load contract ABIs
        with open(CONTRACT_ABI_PATH, 'r') as f:
            contract_json = json.load(f)
            self.marketplace_abi = contract_json['abi']
        
        with open(MOCK_NFT_ABI_PATH, 'r') as f:
            nft_json = json.load(f)
            self.nft_abi = nft_json['abi']
        
        # Create contract instances
        self.marketplace = self.w3.eth.contract(
            address=MARKETPLACE_ADDRESS,
            abi=self.marketplace_abi
        )
        
        self.nft = self.w3.eth.contract(
            address=MOCK_NFT_ADDRESS,
            abi=self.nft_abi
        )
        
        print("Contract instances created")
        
        # Initialize the SDK
        self.sdk = NFTBundleSDK(use_local=True)
        
        # Simulation data
        self.nft_tokens = []
        self.item_ids = []
        self.bundle_id = None
        
    def _send_transaction(self, function, account, value=0):
        """Helper to send a transaction"""
        txn = function.build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price,
            'value': value
        })
        
        signed_txn = account.sign_transaction(txn)
        
        # Handle different web3.py versions
        if hasattr(signed_txn, 'raw_transaction'):
            txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        else:
            txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
        receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        
        # Check for debug events
        self._check_debug_events(receipt)
        
        return receipt
    
    def _check_debug_events(self, receipt):
        """Check for debug events in transaction receipt"""
        if 'logs' not in receipt:
            return
            
        # Define event signatures
        debug_event = self.w3.keccak(text="Debug(string)").hex()
        debug_address_event = self.w3.keccak(text="DebugAddress(string,address)").hex()
        debug_uint_event = self.w3.keccak(text="DebugUint(string,uint256)").hex()
        debug_bool_event = self.w3.keccak(text="DebugBool(string,bool)").hex()
        debug_error_event = self.w3.keccak(text="DebugError(string,string)").hex()
        
        # Process logs
        for log in receipt['logs']:
            if log['address'].lower() != MARKETPLACE_ADDRESS.lower():
                continue
                
            if len(log['topics']) == 0:
                continue
                
            topic = log['topics'][0].hex()
            
            try:
                if topic == debug_event:
                    # Debug(string)
                    data = log['data']
                    decoded = self.w3.codec.decode_abi(['string'], bytes.fromhex(data[2:]))
                    print(f"🔍 DEBUG: {decoded[0]}")
                    
                elif topic == debug_address_event:
                    # DebugAddress(string,address)
                    data = log['data']
                    decoded = self.w3.codec.decode_abi(['string', 'address'], bytes.fromhex(data[2:]))
                    print(f"🔍 DEBUG ADDRESS: {decoded[0]} {decoded[1]}")
                    
                elif topic == debug_uint_event:
                    # DebugUint(string,uint256)
                    data = log['data']
                    decoded = self.w3.codec.decode_abi(['string', 'uint256'], bytes.fromhex(data[2:]))
                    print(f"🔍 DEBUG UINT: {decoded[0]} {decoded[1]}")
                    
                elif topic == debug_bool_event:
                    # DebugBool(string,bool)
                    data = log['data']
                    decoded = self.w3.codec.decode_abi(['string', 'bool'], bytes.fromhex(data[2:]))
                    print(f"🔍 DEBUG BOOL: {decoded[0]} {decoded[1]}")
                    
                elif topic == debug_error_event:
                    # DebugError(string,string)
                    data = log['data']
                    decoded = self.w3.codec.decode_abi(['string', 'string'], bytes.fromhex(data[2:]))
                    print(f"🔍 DEBUG ERROR: {decoded[0]} {decoded[1]}")
            except Exception as e:
                print(f"Error decoding debug event: {e}")
    
    def mint_nfts(self):
        """Mint NFTs to the seller"""
        print("\n=== Minting NFTs ===")
        
        # Art collection with themed names
        art_collection_names = ["Sunset Horizon", "Mountain Peak", "Ocean Wave"]
        
        self.nft_tokens = []  # Clear any existing tokens
        
        for i, name in enumerate(art_collection_names):
            token_id = i
            print(f"Minting NFT: {name} (Token ID: {token_id})")
            
            receipt = self._send_transaction(
                self.nft.functions.mint(self.seller.address, token_id, name),
                self.seller
            )
            
            self.nft_tokens.append(token_id)
            print(f"NFT minted: {name} (Token ID: {token_id})")
        
        print(f"Minted {len(self.nft_tokens)} NFTs to {self.seller.address}")
        
        # Verify minting
        for token_id in self.nft_tokens:
            owner = self.nft.functions.ownerOf(token_id).call()
            if owner.lower() == self.seller.address.lower():
                print(f"✅ Verified: Token ID {token_id} owned by seller")
            else:
                print(f"❌ Error: Token ID {token_id} not owned by seller, but by {owner}")
        
        return self.nft_tokens
    
    def approve_nfts(self):
        """Approve NFTs for the marketplace"""
        print("\n=== Approving NFTs for Marketplace ===")
        
        for token_id in self.nft_tokens:
            print(f"Approving Token ID: {token_id}")
            
            receipt = self._send_transaction(
                self.nft.functions.approve(MARKETPLACE_ADDRESS, token_id),
                self.seller
            )
            
            print(f"Token ID {token_id} approved for marketplace")
        
        print(f"Approved {len(self.nft_tokens)} NFTs for marketplace")
    
    def set_tee_as_calculator(self):
        """Set the TEE address as the authorized Shapley calculator"""
        print("\n=== Setting TEE as Shapley Calculator ===")
        
        print(f"Current Shapley calculator: {self.marketplace.functions.shapleyCalculator().call()}")
        print(f"Setting TEE address {self.tee.address} as Shapley calculator")
        
        receipt = self._send_transaction(
            self.marketplace.functions.setShapleyCalculator(self.tee.address),
            self.seller  # Only the owner can set the Shapley calculator
        )
        
        # Verify the change
        new_calculator = self.marketplace.functions.shapleyCalculator().call()
        if new_calculator.lower() == self.tee.address.lower():
            print(f"✅ Verified: TEE address {self.tee.address} is now the Shapley calculator")
        else:
            print(f"❌ Error: Shapley calculator is {new_calculator}, expected {self.tee.address}")
    
    def list_nfts(self):
        """List NFTs in the marketplace"""
        print("\n=== Listing NFTs in Marketplace ===")
        
        self.item_ids = []  # Clear any existing item IDs
        
        for token_id in self.nft_tokens:
            print(f"Listing Token ID: {token_id}")
            
            receipt = self._send_transaction(
                self.marketplace.functions.listNFT(MOCK_NFT_ADDRESS, token_id),
                self.seller
            )
            
            # Try to get item ID from event logs
            item_id = None
            try:
                for log in receipt['logs']:
                    # Check if this log is from our marketplace contract
                    if log['address'].lower() == MARKETPLACE_ADDRESS.lower():
                        # Try to decode the log
                        topics = log['topics']
                        if len(topics) >= 3:  # NFTListed event has at least 3 topics
                            # The first topic is the event signature, second is indexed itemId
                            item_id = int(topics[1].hex(), 16)
                            break
            except Exception as e:
                print(f"Error extracting item ID from logs: {e}")
            
            # If we couldn't get the item ID from logs, get it from the contract
            if item_id is None:
                # Get the current item count and use that as our item ID
                item_count = self.marketplace.functions.getItemCount().call()
                item_id = item_count  # The most recently listed item
            
            self.item_ids.append(item_id)
            print(f"Token ID {token_id} listed as Item ID {item_id}")
            
            # Verify the listing
            item_info = self.marketplace.functions.getItemInfo(item_id).call()
            if item_info[2] == token_id:  # Check if token ID matches
                print(f"✅ Verified: Item ID {item_id} has Token ID {token_id}")
            else:
                print(f"❌ Error: Item ID {item_id} has Token ID {item_info[2]}, expected {token_id}")
        
        print(f"Listed {len(self.item_ids)} NFTs in marketplace")
        return self.item_ids
    
    def create_bundle(self):
        """Create a bundle of NFTs with metadata"""
        print("\n=== Creating Bundle ===")
        
        # Bundle parameters
        price = self.w3.to_wei(0.15, 'ether')  # 0.15 ETH
        required_buyers = 3  # Require 3 buyers
        name = "Art Collection Bundle"
        description = "A beautiful collection of landscape art NFTs"
        
        print(f"Creating bundle with {len(self.item_ids)} items: {self.item_ids}")
        print(f"Name: {name}")
        print(f"Description: {description}")
        print(f"Price: {self.w3.from_wei(price, 'ether')} ETH")
        print(f"Required buyers: {required_buyers}")
        
        # Use the new createBundleWithMetadata function
        receipt = self._send_transaction(
            self.marketplace.functions.createBundleWithMetadata(
                self.item_ids, price, required_buyers, name, description
            ),
            self.seller
        )
        
        # Try to get bundle ID from event logs
        bundle_id = None
        try:
            for log in receipt['logs']:
                # Check if this log is from our marketplace contract
                if log['address'].lower() == MARKETPLACE_ADDRESS.lower():
                    # Try to decode the log
                    topics = log['topics']
                    if len(topics) >= 2:  # BundleCreated event has at least 2 topics
                        # The first topic is the event signature, second is indexed bundleId
                        bundle_id = int(topics[1].hex(), 16)
                        break
        except Exception as e:
            print(f"Error extracting bundle ID from logs: {e}")
        
        # If we couldn't get the bundle ID from logs, get it from the contract
        if bundle_id is None:
            # Get the current bundle count and use that as our bundle ID
            bundle_count = self.marketplace.functions.getBundleCount().call()
            bundle_id = bundle_count  # The most recently created bundle
        
        self.bundle_id = bundle_id
        print(f"Bundle created with ID: {self.bundle_id}")
        
        # Verify bundle creation using SDK
        bundle = self.sdk.get_bundle(self.bundle_id)
        if bundle:
            print(f"\nBundle details from SDK:")
            print(f"Name: {bundle.name}")
            print(f"Description: {bundle.description}")
            print(f"Price: {bundle.price} ETH")
            print(f"Required buyers: {bundle.required_buyers}")
            print(f"Items: {bundle.item_ids}")
            
            # Verify items in bundle
            if set(bundle.item_ids) == set(self.item_ids):
                print(f"✅ Verified: Bundle contains expected items")
            else:
                print(f"❌ Error: Bundle contains items {bundle.item_ids}, expected {self.item_ids}")
        
        return self.bundle_id
    
    def express_interests(self):
        """Express interests from buyers"""
        print("\n=== Expressing Interests ===")
        
        # Alice is interested in item 1
        alice_items = [self.item_ids[0]]
        print(f"Alice expressing interest in items: {alice_items}")
        
        receipt = self._send_transaction(
            self.marketplace.functions.expressInterest(self.bundle_id, alice_items),
            self.alice
        )
        
        print(f"Alice expressed interest in bundle {self.bundle_id}")
        
        # Bob is interested in item 2
        bob_items = [self.item_ids[1]]
        print(f"Bob expressing interest in items: {bob_items}")
        
        receipt = self._send_transaction(
            self.marketplace.functions.expressInterest(self.bundle_id, bob_items),
            self.bob
        )
        
        print(f"Bob expressed interest in bundle {self.bundle_id}")
        
        # Charlie is interested in item 3
        charlie_items = [self.item_ids[2]]
        print(f"Charlie expressing interest in items: {charlie_items}")
        
        receipt = self._send_transaction(
            self.marketplace.functions.expressInterest(self.bundle_id, charlie_items),
            self.charlie
        )
        
        print(f"Charlie expressed interest in bundle {self.bundle_id}")
        
        # Verify interests using SDK's new getAllBuyerInterests method
        try:
            all_interests = self.sdk.get_all_buyer_interests(self.bundle_id)
            print(f"\nBundle {self.bundle_id} has {len(all_interests)} interested buyers")
            for interest in all_interests:
                print(f"Buyer {interest.buyer} is interested in items: {interest.items_of_interest}")
        except Exception as e:
            print(f"Error using getAllBuyerInterests: {e}")
            # Fallback to the old method
            bundle = self.sdk.get_bundle(self.bundle_id)
            if bundle:
                print(f"\nBundle {self.bundle_id} has {len(bundle.interested_buyers)} interested buyers")
                for buyer in bundle.interested_buyers:
                    interest = self.sdk.get_buyer_interest(self.bundle_id, buyer)
                    if interest:
                        print(f"Buyer {buyer} is interested in items: {interest.items_of_interest}")
    
    def request_attestation(self):
        """Request attestation for Shapley value calculation"""
        print("\n=== Requesting Attestation ===")
        
        receipt = self._send_transaction(
            self.marketplace.functions.requestAttestation(self.bundle_id),
            self.alice  # Any buyer can request attestation
        )
        
        print(f"Attestation requested for bundle {self.bundle_id}")
    
    def set_shapley_values(self):
        """Set Shapley values as the TEE"""
        print("\n=== Setting Shapley Values ===")
        
        # Get bundle info
        bundle_info = self.marketplace.functions.getBundleInfo(self.bundle_id).call()
        bundle_price = bundle_info[1]  # Price in wei
        interested_buyers = bundle_info[4]  # List of interested buyers
        
        print(f"Bundle price: {self.w3.from_wei(bundle_price, 'ether')} ETH")
        print(f"Interested buyers: {interested_buyers}")
        print(f"Number of interested buyers: {len(interested_buyers)}")
        
        # Calculate Shapley values (in this case, equal distribution for simplicity)
        num_buyers = len(interested_buyers)
        equal_share = bundle_price // num_buyers
        
        # Ensure the last value makes the sum equal to the bundle price
        shapley_values = [equal_share] * (num_buyers - 1)
        shapley_values.append(bundle_price - sum(shapley_values))
        
        print(f"Setting Shapley values: {[self.w3.from_wei(v, 'ether') for v in shapley_values]}")
        print(f"Total of Shapley values: {self.w3.from_wei(sum(shapley_values), 'ether')} ETH")
        print(f"Bundle price: {self.w3.from_wei(bundle_price, 'ether')} ETH")
        
        # Make sure the TEE account has enough gas
        if self.w3.eth.get_balance(self.tee.address) < self.w3.to_wei(0.1, 'ether'):
            # Send some ETH to the TEE account for gas
            tx = {
                'to': self.tee.address,
                'value': self.w3.to_wei(0.1, 'ether'),
                'gas': 21000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.seller.address)
            }
            signed_tx = self.seller.sign_transaction(tx)
            self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"Sent ETH to TEE account for gas")
            time.sleep(2)  # Wait for transaction to be processed
        
        # Verify the TEE is the authorized calculator
        current_calculator = self.marketplace.functions.shapleyCalculator().call()
        print(f"Current Shapley calculator: {current_calculator}")
        print(f"TEE address: {self.tee.address}")
        
        if current_calculator.lower() != self.tee.address.lower():
            print(f"⚠️ Warning: TEE address is not the current Shapley calculator!")
            print(f"Setting TEE as calculator before proceeding...")
            self.set_tee_as_calculator()
        
        # Set the Shapley values
        receipt = self._send_transaction(
            self.marketplace.functions.setShapleyValues(self.bundle_id, interested_buyers, shapley_values),
            self.tee  # TEE account sets the values
        )
        
        print(f"Shapley values set for bundle {self.bundle_id}")
        
        # Verify Shapley values directly from contract
        print(f"\nVerifying Shapley values from contract:")
        shapley_dict = {}
        for i, buyer in enumerate(interested_buyers):
            shapley_value = self.marketplace.functions.getShapleyValue(self.bundle_id, buyer).call()
            print(f"Buyer {buyer}: {self.w3.from_wei(shapley_value, 'ether')} ETH")
            shapley_dict[buyer] = shapley_value
            
            # Verify the value matches what we set
            if shapley_value != shapley_values[i]:
                print(f"⚠️ Warning: Shapley value mismatch for {buyer}!")
                print(f"  Set: {self.w3.from_wei(shapley_values[i], 'ether')} ETH")
                print(f"  Got: {self.w3.from_wei(shapley_value, 'ether')} ETH")
        
        # Wait for transaction to be processed
        time.sleep(3)
        
        # Return the values for later use
        return shapley_dict
    
    def complete_purchases(self, shapley_values):
        """Complete purchases by all buyers"""
        print("\n=== Completing Purchases ===")
        
        # Verify Shapley values are set before proceeding
        print("Verifying Shapley values are set for all buyers...")
        all_set = True
        for buyer_address, expected_value in shapley_values.items():
            actual_value = self.marketplace.functions.getShapleyValue(self.bundle_id, buyer_address).call()
            if actual_value == 0:
                print(f"⚠️ Warning: Shapley value not set for {buyer_address}")
                all_set = False
            elif actual_value != expected_value:
                print(f"⚠️ Warning: Shapley value mismatch for {buyer_address}")
                print(f"  Expected: {self.w3.from_wei(expected_value, 'ether')} ETH")
                print(f"  Actual: {self.w3.from_wei(actual_value, 'ether')} ETH")
                all_set = False
        
        if not all_set:
            print("⚠️ Some Shapley values are not set correctly. Attempting to set them again...")
            shapley_values = self.set_shapley_values()
            time.sleep(3)  # Wait for transaction to be processed
        
        # Alice completes purchase
        alice_value = shapley_values.get(self.alice.address, 0)
        print(f"Alice paying {self.w3.from_wei(alice_value, 'ether')} ETH")
        
        # Verify Alice's Shapley value is set
        alice_shapley = self.marketplace.functions.getShapleyValue(self.bundle_id, self.alice.address).call()
        print(f"Alice's Shapley value from contract: {self.w3.from_wei(alice_shapley, 'ether')} ETH")
        
        if alice_shapley == 0:
            print("⚠️ Alice's Shapley value is not set! Cannot complete purchase.")
            return
        
        receipt = self._send_transaction(
            self.marketplace.functions.completeBundlePurchase(self.bundle_id),
            self.alice,
            value=alice_value
        )
        
        print(f"Alice completed purchase for bundle {self.bundle_id}")
        time.sleep(2)  # Wait for transaction to be processed
        
        # Check if Alice has paid
        has_paid = self.marketplace.functions.hasBuyerPaid(self.bundle_id, self.alice.address).call()
        print(f"Has Alice paid? {has_paid}")
        
        # Bob completes purchase
        bob_value = shapley_values.get(self.bob.address, 0)
        print(f"Bob paying {self.w3.from_wei(bob_value, 'ether')} ETH")
        
        # Verify Bob's Shapley value is set
        bob_shapley = self.marketplace.functions.getShapleyValue(self.bundle_id, self.bob.address).call()
        print(f"Bob's Shapley value from contract: {self.w3.from_wei(bob_shapley, 'ether')} ETH")
        
        if bob_shapley == 0:
            print("⚠️ Bob's Shapley value is not set! Cannot complete purchase.")
            return
        
        receipt = self._send_transaction(
            self.marketplace.functions.completeBundlePurchase(self.bundle_id),
            self.bob,
            value=bob_value
        )
        
        print(f"Bob completed purchase for bundle {self.bundle_id}")
        time.sleep(2)  # Wait for transaction to be processed
        
        # Check if Bob has paid
        has_paid = self.marketplace.functions.hasBuyerPaid(self.bundle_id, self.bob.address).call()
        print(f"Has Bob paid? {has_paid}")
        
        # Charlie completes purchase
        charlie_value = shapley_values.get(self.charlie.address, 0)
        print(f"Charlie paying {self.w3.from_wei(charlie_value, 'ether')} ETH")
        
        # Verify Charlie's Shapley value is set
        charlie_shapley = self.marketplace.functions.getShapleyValue(self.bundle_id, self.charlie.address).call()
        print(f"Charlie's Shapley value from contract: {self.w3.from_wei(charlie_shapley, 'ether')} ETH")
        
        if charlie_shapley == 0:
            print("⚠️ Charlie's Shapley value is not set! Cannot complete purchase.")
            return
        
        receipt = self._send_transaction(
            self.marketplace.functions.completeBundlePurchase(self.bundle_id),
            self.charlie,
            value=charlie_value
        )
        
        print(f"Charlie completed purchase for bundle {self.bundle_id}")
        time.sleep(2)  # Wait for transaction to be processed
        
        # Check if Charlie has paid
        has_paid = self.marketplace.functions.hasBuyerPaid(self.bundle_id, self.charlie.address).call()
        print(f"Has Charlie paid? {has_paid}")
        
        # Get the number of buyers who have paid
        paid_count = self.marketplace.functions.getBundlePaidCount(self.bundle_id).call()
        print(f"Number of buyers who have paid: {paid_count}")
        print(f"Required buyers: {self.marketplace.functions.getBundleInfo(self.bundle_id).call()[2]}")
        
        # Get bundle info to check if it's completed
        bundle_info = self.marketplace.functions.getBundleInfo(self.bundle_id).call()
        completed = bundle_info[5]  # completed is the 6th element
        print(f"Bundle {self.bundle_id} completed (from contract): {completed}")
        
        # Verify bundle completion using SDK
        bundle = self.sdk.get_bundle(self.bundle_id)
        if bundle:
            print(f"Bundle {self.bundle_id} completed (from SDK): {bundle.completed}")
            print(f"Paid count (from SDK): {bundle.paid_count}")
    
    def verify_nft_ownership(self):
        """Verify NFT ownership after bundle completion"""
        print("\n=== Verifying NFT Ownership ===")
        
        # Get bundle info to check completion status
        bundle_info = self.marketplace.functions.getBundleInfo(self.bundle_id).call()
        completed = bundle_info[5]  # completed is the 6th element
        print(f"Bundle completion status: {completed}")
        
        # Get buyer interests to know which NFTs they should own
        alice_interest = self.marketplace.functions.getBuyerInterests(self.bundle_id, self.alice.address).call()
        bob_interest = self.marketplace.functions.getBuyerInterests(self.bundle_id, self.bob.address).call()
        charlie_interest = self.marketplace.functions.getBuyerInterests(self.bundle_id, self.charlie.address).call()
        
        print(f"Alice should own items: {alice_interest}")
        print(f"Bob should own items: {bob_interest}")
        print(f"Charlie should own items: {charlie_interest}")
        
        # Check payment status - use direct contract call to verify
        alice_paid = self.marketplace.functions.hasBuyerPaid(self.bundle_id, self.alice.address).call()
        bob_paid = self.marketplace.functions.hasBuyerPaid(self.bundle_id, self.bob.address).call()
        charlie_paid = self.marketplace.functions.hasBuyerPaid(self.bundle_id, self.charlie.address).call()
        
        print(f"Alice paid: {alice_paid}")
        print(f"Bob paid: {bob_paid}")
        print(f"Charlie paid: {charlie_paid}")
        
        # Add a delay to allow transactions to be processed
        print("Waiting for transactions to be processed...")
        time.sleep(5)  # Increase wait time to ensure transactions are processed
        
        # Map item IDs to token IDs for verification
        item_to_token = {}
        for item_id in self.item_ids:
            try:
                item_info = self.marketplace.functions.getItemInfo(item_id).call()
                token_id = item_info[2]
                item_to_token[item_id] = token_id
                print(f"Item ID {item_id} corresponds to Token ID {token_id}")
            except Exception as e:
                print(f"Error getting info for Item ID {item_id}: {e}")
        
        # Verify Alice's NFTs
        for item_id in alice_interest:
            if item_id not in item_to_token:
                print(f"❌ Error: Item ID {item_id} not found in mapping")
                continue
            
            token_id = item_to_token[item_id]
            
            try:
                # Check owner
                owner = self.nft.functions.ownerOf(token_id).call()
                expected_owner = self.alice.address
                if owner.lower() == expected_owner.lower():
                    print(f"✅ Alice correctly owns Token ID {token_id} (Item ID {item_id})")
                else:
                    print(f"❌ Alice should own Token ID {token_id} (Item ID {item_id}), but owner is {owner}")
                    print(f"   Expected owner: {expected_owner}")
            except Exception as e:
                print(f"❌ Error checking ownership of Token ID {token_id}: {e}")
        
        # Verify Bob's NFTs
        for item_id in bob_interest:
            if item_id not in item_to_token:
                print(f"❌ Error: Item ID {item_id} not found in mapping")
                continue
            
            token_id = item_to_token[item_id]
            
            try:
                # Check owner
                owner = self.nft.functions.ownerOf(token_id).call()
                expected_owner = self.bob.address
                if owner.lower() == expected_owner.lower():
                    print(f"✅ Bob correctly owns Token ID {token_id} (Item ID {item_id})")
                else:
                    print(f"❌ Bob should own Token ID {token_id} (Item ID {item_id}), but owner is {owner}")
                    print(f"   Expected owner: {expected_owner}")
            except Exception as e:
                print(f"❌ Error checking ownership of Token ID {token_id}: {e}")
        
        # Verify Charlie's NFTs
        for item_id in charlie_interest:
            if item_id not in item_to_token:
                print(f"❌ Error: Item ID {item_id} not found in mapping")
                continue
            
            token_id = item_to_token[item_id]
            
            try:
                # Check owner
                owner = self.nft.functions.ownerOf(token_id).call()
                expected_owner = self.charlie.address
                if owner.lower() == expected_owner.lower():
                    print(f"✅ Charlie correctly owns Token ID {token_id} (Item ID {item_id})")
                else:
                    print(f"❌ Charlie should own Token ID {token_id} (Item ID {item_id}), but owner is {owner}")
                    print(f"   Expected owner: {expected_owner}")
            except Exception as e:
                print(f"❌ Error checking ownership of Token ID {token_id}: {e}")
    
    def get_marketplace_summary(self):
        """Get a summary of the marketplace activity"""
        print("\n=== Marketplace Summary ===")
        
        try:
            # Use the SDK's new getMarketplaceSummary method
            summary = self.sdk.get_marketplace_summary()
            
            print(f"Total items: {summary.total_items}")
            print(f"Total bundles: {summary.total_bundles}")
            print(f"Active items: {summary.active_items}")
            print(f"Active bundles: {summary.active_bundles}")
            print(f"Completed bundles: {summary.completed_bundles}")
        except Exception as e:
            print(f"Error getting marketplace summary: {e}")
    
    def run_simulation(self):
        """Run the full simulation"""
        try:
            # Step 1: Mint NFTs to seller
            self.mint_nfts()
            
            # Step 2: Approve NFTs for marketplace
            self.approve_nfts()
            
            # Step 3: Set TEE as the authorized Shapley calculator
            self.set_tee_as_calculator()
            
            # Step 4: List NFTs in marketplace
            self.list_nfts()
            
            # Step 5: Create a bundle with metadata
            self.create_bundle()
            
            # Step 6: Express interests from buyers
            self.express_interests()
            
            # Step 7: Request attestation for Shapley values
            self.request_attestation()
            
            # Step 8: Set Shapley values (as TEE)
            shapley_values = self.set_shapley_values()
            
            # Step 9: Complete purchases by all buyers
            self.complete_purchases(shapley_values)
            
            # Step 10: Verify NFT ownership
            self.verify_nft_ownership()
            
            # Step 11: Get marketplace summary
            self.get_marketplace_summary()
            
            print("\n=== Simulation Completed Successfully ===")
            
        except Exception as e:
            print(f"\n❌ Error in simulation: {e}")
            import traceback
            traceback.print_exc()


def run_sepolia_simulation():
    """Run the Sepolia simulation"""
    print("=== Starting NFT Bundle Marketplace Sepolia Simulation ===")
    
    # Create and run the simulation
    simulation = SepoliaSimulation()
    simulation.run_simulation()


if __name__ == "__main__":
    run_sepolia_simulation()