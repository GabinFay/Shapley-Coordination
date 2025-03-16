import json
import os
from web3 import Web3
from eth_account import Account
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Load environment variables
from dotenv import load_dotenv
load_dotenv(".env.local")  # Load from local environment file

# Configuration
MARKETPLACE_ADDRESS = os.getenv("MARKETPLACE_ADDRESS")
MOCK_NFT_ADDRESS = os.getenv("MOCK_NFT_ADDRESS")

# Path to contract ABIs
CONTRACT_ABI_PATH = "thefoundry/out/NFTBundleMarket.sol/NFTBundleMarket.json"
MOCK_NFT_ABI_PATH = "thefoundry/out/MockERC721.sol/MockERC721.json"

@dataclass
class NFTItem:
    item_id: int
    nft_contract: str
    token_id: int
    seller: str
    name: str
    image_url: str = ""
    sold: bool = False

@dataclass
class Bundle:
    bundle_id: int
    item_ids: List[int]
    price: float
    required_buyers: int
    active: bool
    interested_buyers: List[str]
    completed: bool
    name: str = ""
    description: str = ""
    paid_count: int = 0

@dataclass
class BuyerInterest:
    bundle_id: int
    buyer: str
    items_of_interest: List[int]
    shapley_value: float = 0
    has_paid: bool = False

@dataclass
class MarketplaceSummary:
    total_items: int
    total_bundles: int
    active_items: int
    active_bundles: int
    completed_bundles: int

class NFTBundleSDK:
    """SDK for interacting with the NFT Bundle Marketplace contract"""
    
    def __init__(self, use_local=True, local_url="http://localhost:8545"):
        """Initialize the SDK with contract connections"""
        # Connect to Ethereum node
        if use_local:
            self.w3 = Web3(Web3.HTTPProvider(local_url))
        else:
            self.w3 = Web3(Web3.HTTPProvider("https://sepolia.infura.io/v3/" + os.getenv("INFURA_KEY", "")))
        
        # Check connection
        if not self.w3.is_connected():
            raise Exception("Failed to connect to Ethereum node")
        
        # Load contract ABIs
        with open(CONTRACT_ABI_PATH, 'r') as f:
            contract_json = json.load(f)
            self.contract_abi = contract_json['abi']
        
        with open(MOCK_NFT_ABI_PATH, 'r') as f:
            nft_json = json.load(f)
            self.nft_abi = nft_json['abi']
        
        # Contract instances
        self.contract = self.w3.eth.contract(address=MARKETPLACE_ADDRESS, abi=self.contract_abi)
        self.mock_nft = self.w3.eth.contract(address=MOCK_NFT_ADDRESS, abi=self.nft_abi)
    
    def get_marketplace_summary(self) -> MarketplaceSummary:
        """Get a summary of the marketplace activity"""
        try:
            summary = self.contract.functions.getMarketplaceSummary().call()
            return MarketplaceSummary(
                total_items=summary[0],
                total_bundles=summary[1],
                active_items=summary[2],
                active_bundles=summary[3],
                completed_bundles=summary[4]
            )
        except Exception as e:
            print(f"Error getting marketplace summary: {e}")
            # Fallback to calculating summary manually
            total_items = self.contract.functions.getItemCount().call()
            total_bundles = self.contract.functions.getBundleCount().call()
            active_bundles = len(self.contract.functions.getActiveBundles().call())
            completed_bundles = len(self.contract.functions.getCompletedBundles().call())
            
            # Count active items
            active_items = 0
            for item_id in range(1, total_items + 1):
                try:
                    item_info = self.contract.functions.getItemInfo(item_id).call()
                    if not item_info[3]:  # not sold
                        active_items += 1
                except:
                    pass
            
            return MarketplaceSummary(
                total_items=total_items,
                total_bundles=total_bundles,
                active_items=active_items,
                active_bundles=active_bundles,
                completed_bundles=completed_bundles
            )
    
    def get_all_nfts(self) -> List[NFTItem]:
        """Get all NFT items from the marketplace"""
        # Get the total number of items
        total_items = self.contract.functions.getItemCount().call()
        
        nft_items = []
        for item_id in range(1, total_items + 1):
            try:
                item = self.get_nft(item_id)
                if item:
                    nft_items.append(item)
            except Exception as e:
                print(f"Error getting NFT item {item_id}: {e}")
        
        return nft_items
    
    def get_nft(self, item_id: int) -> Optional[NFTItem]:
        """Get a specific NFT item"""
        try:
            item_info = self.contract.functions.getItemInfo(item_id).call()
            
            # Parse item info
            nft_contract = item_info[0]
            token_id = item_info[2]
            seller = item_info[1]
            sold = item_info[3]
            
            # Get NFT name
            try:
                name = self.mock_nft.functions.tokenURI(token_id).call()
            except:
                name = f"NFT #{token_id}"
            
            return NFTItem(
                item_id=item_id,
                nft_contract=nft_contract,
                token_id=token_id,
                seller=seller,
                name=name,
                sold=sold
            )
        except Exception as e:
            print(f"Error getting NFT item {item_id}: {e}")
            return None
    
    def get_all_bundles(self) -> List[Bundle]:
        """Get all bundles"""
        # Get the total number of bundles
        total_bundles = self.contract.functions.getBundleCount().call()
        
        bundles = []
        for bundle_id in range(1, total_bundles + 1):
            try:
                bundle = self.get_bundle(bundle_id)
                if bundle:
                    bundles.append(bundle)
            except Exception as e:
                print(f"Error getting bundle {bundle_id}: {e}")
        
        return bundles
    
    def get_bundle(self, bundle_id: int) -> Optional[Bundle]:
        """Get a specific bundle"""
        try:
            bundle_info = self.contract.functions.getBundleInfo(bundle_id).call()
            
            # Parse bundle info
            item_ids = bundle_info[0]
            price = self.w3.from_wei(bundle_info[1], 'ether')
            required_buyers = bundle_info[2]
            active = bundle_info[3]
            interested_buyers = bundle_info[4]
            completed = bundle_info[5]
            paid_count = bundle_info[6]
            name = bundle_info[7]
            description = bundle_info[8]
            
            # If name is empty, create a default name
            if not name:
                name = f"Bundle #{bundle_id}"
                if item_ids:
                    try:
                        first_item = self.get_nft(item_ids[0])
                        if first_item:
                            name = f"Bundle of {first_item.name} and others"
                    except:
                        pass
            
            # If description is empty, create a default description
            if not description:
                description = f"A bundle of {len(item_ids)} NFTs"
            
            return Bundle(
                bundle_id=bundle_id,
                item_ids=item_ids,
                price=float(price),
                required_buyers=required_buyers,
                active=active,
                interested_buyers=interested_buyers,
                completed=completed,
                name=name,
                description=description,
                paid_count=paid_count
            )
        except Exception as e:
            print(f"Error getting bundle {bundle_id}: {e}")
            return None
    
    def get_bundle_items(self, bundle_id: int) -> List[NFTItem]:
        """Get all NFT items in a bundle"""
        bundle = self.get_bundle(bundle_id)
        if not bundle:
            return []
        
        return [self.get_nft(item_id) for item_id in bundle.item_ids if self.get_nft(item_id)]
    
    def get_all_buyer_interests(self, bundle_id: int) -> List[BuyerInterest]:
        """Get all buyer interests for a bundle with a single contract call"""
        try:
            # Use the new getAllBuyerInterests function
            interests_data = self.contract.functions.getAllBuyerInterests(bundle_id).call()
            
            buyers = interests_data[0]
            item_interests = interests_data[1]
            has_paid_status = interests_data[2]
            shapley_values = interests_data[3]
            
            interests = []
            for i in range(len(buyers)):
                # Convert from wei to ether for display
                shapley_value = float(self.w3.from_wei(shapley_values[i], 'ether'))
                
                interest = BuyerInterest(
                    bundle_id=bundle_id,
                    buyer=buyers[i],
                    items_of_interest=item_interests[i],
                    shapley_value=shapley_value,
                    has_paid=has_paid_status[i]
                )
                interests.append(interest)
            
            return interests
        except Exception as e:
            print(f"Error getting all buyer interests for bundle {bundle_id}: {e}")
            # Fallback to the old method
            return self.get_buyer_interests(bundle_id)
    
    def get_buyer_interests(self, bundle_id: int) -> List[BuyerInterest]:
        """Get all buyer interests for a bundle (legacy method)"""
        bundle = self.get_bundle(bundle_id)
        if not bundle:
            return []
        
        interests = []
        for buyer in bundle.interested_buyers:
            interest = self.get_buyer_interest(bundle_id, buyer)
            if interest:
                interests.append(interest)
        
        return interests
    
    def get_buyer_interest(self, bundle_id: int, buyer: str) -> Optional[BuyerInterest]:
        """Get a specific buyer's interest in a bundle"""
        try:
            # Get items of interest
            items_of_interest = self.contract.functions.getBuyerInterests(bundle_id, buyer).call()
            
            # Check if buyer has paid
            has_paid = self.contract.functions.hasBuyerPaid(bundle_id, buyer).call()
            
            # Get Shapley value if available
            shapley_value = 0
            try:
                shapley_value_wei = self.contract.functions.getShapleyValue(bundle_id, buyer).call()
                shapley_value = float(self.w3.from_wei(shapley_value_wei, 'ether'))
            except Exception as e:
                print(f"Warning: Could not get Shapley value: {e}")
                # Try a different approach
                try:
                    # Get all interests and find this buyer
                    all_interests = self.contract.functions.getAllBuyerInterests(bundle_id).call()
                    buyers = all_interests[0]
                    shapley_values = all_interests[3]
                    
                    for i, b in enumerate(buyers):
                        if b.lower() == buyer.lower():
                            shapley_value = float(self.w3.from_wei(shapley_values[i], 'ether'))
                            break
                except Exception as e2:
                    print(f"Warning: Alternative method also failed: {e2}")
            
            return BuyerInterest(
                bundle_id=bundle_id,
                buyer=buyer,
                items_of_interest=items_of_interest,
                shapley_value=shapley_value,
                has_paid=has_paid
            )
        except Exception as e:
            print(f"Error getting buyer interest for bundle {bundle_id}, buyer {buyer}: {e}")
            return None
    
    def get_user_nfts(self, user_address: str) -> List[NFTItem]:
        """Get NFTs owned by a user"""
        user_nfts = []
        
        try:
            # Use the new contract function to get owned NFTs
            token_ids = self.contract.functions.getNFTsOwnedByAddress(MOCK_NFT_ADDRESS, user_address).call()
            
            for token_id in token_ids:
                try:
                    # Get token name
                    try:
                        name = self.mock_nft.functions.tokenURI(token_id).call()
                    except:
                        name = f"NFT #{token_id}"
                    
                    # Create NFT item
                    nft_item = NFTItem(
                        item_id=0,  # We don't know the item ID here
                        nft_contract=MOCK_NFT_ADDRESS,
                        token_id=token_id,
                        seller="",  # We don't know the seller here
                        name=name,
                        sold=True  # It's owned by someone
                    )
                    
                    user_nfts.append(nft_item)
                except Exception as e:
                    print(f"Error processing token {token_id}: {e}")
            
            return user_nfts
            
        except Exception as e:
            # Fallback to the old method if the new function is not available
            print(f"Warning: getNFTsOwnedByAddress not available, using fallback: {e}")
            
            try:
                # Try to get all NFTs from the mock contract using totalSupply
                total_supply = self.mock_nft.functions.totalSupply().call()
                
                for token_id in range(total_supply):
                    try:
                        owner = self.mock_nft.functions.ownerOf(token_id).call()
                        if owner.lower() == user_address.lower():
                            # Get token name
                            try:
                                name = self.mock_nft.functions.tokenURI(token_id).call()
                            except:
                                name = f"NFT #{token_id}"
                            
                            # Create NFT item
                            nft_item = NFTItem(
                                item_id=0,  # We don't know the item ID here
                                nft_contract=MOCK_NFT_ADDRESS,
                                token_id=token_id,
                                seller="",  # We don't know the seller here
                                name=name,
                                sold=True  # It's owned by someone
                            )
                            
                            user_nfts.append(nft_item)
                    except Exception as e:
                        # This might happen if the token doesn't exist
                        pass
            except Exception as e:
                # If totalSupply is not available, try a different approach
                print(f"Warning: totalSupply not available, trying alternative approach: {e}")
                
                # Try to check ownership for tokens 0-10 (a reasonable range for testing)
                for token_id in range(10):
                    try:
                        owner = self.mock_nft.functions.ownerOf(token_id).call()
                        if owner.lower() == user_address.lower():
                            # Get token name
                            try:
                                name = self.mock_nft.functions.tokenURI(token_id).call()
                            except:
                                name = f"NFT #{token_id}"
                            
                            # Create NFT item
                            nft_item = NFTItem(
                                item_id=0,  # We don't know the item ID here
                                nft_contract=MOCK_NFT_ADDRESS,
                                token_id=token_id,
                                seller="",  # We don't know the seller here
                                name=name,
                                sold=True  # It's owned by someone
                            )
                            
                            user_nfts.append(nft_item)
                    except Exception:
                        # This might happen if the token doesn't exist
                        pass
            
            return user_nfts
    
    def create_bundle_with_metadata(self, seller_address: str, item_ids: List[int], price: float, required_buyers: int, name: str, description: str) -> int:
        """Create a bundle with metadata (requires transaction)"""
        # This is a helper method that would need to be called with a transaction
        # In a real application, you would need to sign and send this transaction
        price_wei = self.w3.to_wei(price, 'ether')
        
        # Build the transaction (but don't send it)
        tx_data = self.contract.functions.createBundleWithMetadata(
            item_ids, price_wei, required_buyers, name, description
        ).build_transaction({
            'from': seller_address,
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(seller_address)
        })
        
        # Return the transaction data for the caller to sign and send
        return tx_data 