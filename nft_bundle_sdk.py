import json
import os
from web3 import Web3
from eth_account import Account
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
INFURA_KEY = os.getenv("INFURA_KEY")
NETWORK_URL = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
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
    image_url: str
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
    name: str
    description: str

@dataclass
class BuyerInterest:
    bundle_id: int
    buyer: str
    items_of_interest: List[int]
    shapley_value: float = 0
    has_paid: bool = False

class NFTBundleSDK:
    """SDK for interacting with the NFT Bundle Marketplace contract"""
    
    def __init__(self, use_local=True, local_url="http://localhost:8545"):
        """Initialize the SDK with contract connections"""
        # Connect to Ethereum node
        if use_local:
            self.w3 = Web3(Web3.HTTPProvider(local_url))
        else:
            self.w3 = Web3(Web3.HTTPProvider(NETWORK_URL))
        
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
        self.contract = self.w3.eth.contract(address=CONTRACT_ADDRESS, abi=self.contract_abi)
        self.mock_nft = self.w3.eth.contract(address=MOCK_NFT_ADDRESS, abi=self.nft_abi)
        
        # In-memory storage for demo data
        self.nft_items = {}
        self.bundles = {}
        self.buyer_interests = {}
        self.shapley_values = {}
        
        # Load demo data
        self._load_demo_data()
    
    def _load_demo_data(self):
        """Load demo data for testing"""
        # Create some demo NFT items
        self._create_demo_nfts()
        
        # Create demo bundles
        self._create_demo_bundles()
        
        # Create demo buyer interests
        self._create_demo_buyer_interests()
    
    def _create_demo_nfts(self):
        """Create demo NFT items"""
        # Create 10 NFT items with different themes
        themes = ["Space", "Ocean", "Forest", "Desert", "Mountain", 
                 "City", "Abstract", "Animal", "Portrait", "Landscape"]
        
        for i in range(1, 11):
            self.nft_items[i] = NFTItem(
                item_id=i,
                nft_contract=MOCK_NFT_ADDRESS,
                token_id=i,
                seller="0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",  # Demo seller
                name=f"{themes[i-1]} NFT #{i}",
                image_url=f"https://example.com/nft/{i}.jpg",
                sold=False
            )
    
    def _create_demo_bundles(self):
        """Create demo bundles"""
        # Bundle 1: A completed bundle (3/3 buyers)
        self.bundles[1] = Bundle(
            bundle_id=1,
            item_ids=[1, 2, 3],
            price=0.3,
            required_buyers=3,
            active=False,
            interested_buyers=[
                "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",  # Alice
                "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",  # Bob
                "0x90f79bf6eb2c4f870365e785982e1f101e93b906"   # Charlie
            ],
            completed=True,
            name="Space Collection",
            description="A collection of space-themed NFTs"
        )
        
        # Bundle 2: An active bundle with enough interest (2/2 buyers)
        self.bundles[2] = Bundle(
            bundle_id=2,
            item_ids=[4, 5],
            price=0.2,
            required_buyers=2,
            active=True,
            interested_buyers=[
                "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",  # Alice
                "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc"   # Bob
            ],
            completed=False,
            name="Ocean Collection",
            description="A collection of ocean-themed NFTs"
        )
        
        # Bundle 3: An active bundle with partial interest (2/3 buyers)
        self.bundles[3] = Bundle(
            bundle_id=3,
            item_ids=[6, 7, 8],
            price=0.3,
            required_buyers=3,
            active=True,
            interested_buyers=[
                "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",  # Alice
                "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc"   # Bob
            ],
            completed=False,
            name="Nature Collection",
            description="A collection of nature-themed NFTs"
        )
        
        # Bundle 4: An active bundle with no interest yet
        self.bundles[4] = Bundle(
            bundle_id=4,
            item_ids=[9, 10],
            price=0.15,
            required_buyers=2,
            active=True,
            interested_buyers=[],
            completed=False,
            name="Art Collection",
            description="A collection of art-themed NFTs"
        )
    
    def _create_demo_buyer_interests(self):
        """Create demo buyer interests"""
        # Bundle 1 interests (completed bundle)
        self.buyer_interests[(1, "0x70997970c51812dc3a010c7d01b50e0d17dc79c8")] = BuyerInterest(
            bundle_id=1,
            buyer="0x70997970c51812dc3a010c7d01b50e0d17dc79c8",  # Alice
            items_of_interest=[1],
            shapley_value=0.1,
            has_paid=True
        )
        
        self.buyer_interests[(1, "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc")] = BuyerInterest(
            bundle_id=1,
            buyer="0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",  # Bob
            items_of_interest=[2],
            shapley_value=0.1,
            has_paid=True
        )
        
        self.buyer_interests[(1, "0x90f79bf6eb2c4f870365e785982e1f101e93b906")] = BuyerInterest(
            bundle_id=1,
            buyer="0x90f79bf6eb2c4f870365e785982e1f101e93b906",  # Charlie
            items_of_interest=[3],
            shapley_value=0.1,
            has_paid=True
        )
        
        # Bundle 2 interests (ready for purchase)
        self.buyer_interests[(2, "0x70997970c51812dc3a010c7d01b50e0d17dc79c8")] = BuyerInterest(
            bundle_id=2,
            buyer="0x70997970c51812dc3a010c7d01b50e0d17dc79c8",  # Alice
            items_of_interest=[4],
            shapley_value=0.1,
            has_paid=False
        )
        
        self.buyer_interests[(2, "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc")] = BuyerInterest(
            bundle_id=2,
            buyer="0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",  # Bob
            items_of_interest=[5],
            shapley_value=0.1,
            has_paid=False
        )
        
        # Bundle 3 interests (partial interest)
        self.buyer_interests[(3, "0x70997970c51812dc3a010c7d01b50e0d17dc79c8")] = BuyerInterest(
            bundle_id=3,
            buyer="0x70997970c51812dc3a010c7d01b50e0d17dc79c8",  # Alice
            items_of_interest=[6, 7],
            shapley_value=0,
            has_paid=False
        )
        
        self.buyer_interests[(3, "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc")] = BuyerInterest(
            bundle_id=3,
            buyer="0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",  # Bob
            items_of_interest=[7, 8],
            shapley_value=0,
            has_paid=False
        )
    
    def get_all_nfts(self) -> List[NFTItem]:
        """Get all NFT items"""
        return list(self.nft_items.values())
    
    def get_nft(self, item_id: int) -> Optional[NFTItem]:
        """Get a specific NFT item"""
        return self.nft_items.get(item_id)
    
    def get_all_bundles(self) -> List[Bundle]:
        """Get all bundles"""
        return list(self.bundles.values())
    
    def get_bundle(self, bundle_id: int) -> Optional[Bundle]:
        """Get a specific bundle"""
        return self.bundles.get(bundle_id)
    
    def get_bundle_items(self, bundle_id: int) -> List[NFTItem]:
        """Get all NFT items in a bundle"""
        bundle = self.bundles.get(bundle_id)
        if not bundle:
            return []
        
        return [self.nft_items.get(item_id) for item_id in bundle.item_ids]
    
    def get_buyer_interests(self, bundle_id: int) -> List[BuyerInterest]:
        """Get all buyer interests for a bundle"""
        return [interest for key, interest in self.buyer_interests.items() 
                if key[0] == bundle_id]
    
    def get_buyer_interest(self, bundle_id: int, buyer: str) -> Optional[BuyerInterest]:
        """Get a specific buyer's interest in a bundle"""
        return self.buyer_interests.get((bundle_id, buyer))
    
    def express_interest(self, bundle_id: int, buyer: str, items_of_interest: List[int]) -> bool:
        """Express interest in a bundle"""
        bundle = self.bundles.get(bundle_id)
        if not bundle or not bundle.active or bundle.completed:
            return False
        
        # Validate items of interest
        for item_id in items_of_interest:
            if item_id not in bundle.item_ids:
                return False
        
        # Add buyer interest
        self.buyer_interests[(bundle_id, buyer)] = BuyerInterest(
            bundle_id=bundle_id,
            buyer=buyer,
            items_of_interest=items_of_interest,
            shapley_value=0,
            has_paid=False
        )
        
        # Update bundle
        if buyer not in bundle.interested_buyers:
            bundle.interested_buyers.append(buyer)
        
        return True
    
    def calculate_shapley_values(self, bundle_id: int) -> Dict[str, float]:
        """Calculate Shapley values for a bundle"""
        from shapley_calculator import ShapleyCalculator
        
        bundle = self.bundles.get(bundle_id)
        if not bundle:
            return {}
        
        # Get buyer interests
        buyer_interests = {}
        for interest in self.get_buyer_interests(bundle_id):
            buyer_interests[interest.buyer] = interest.items_of_interest
        
        # Calculate Shapley values
        calculator = ShapleyCalculator(bundle.price)
        shapley_values = calculator.calculate_values(buyer_interests)
        
        # Update buyer interests with Shapley values
        for buyer, value in shapley_values.items():
            if (bundle_id, buyer) in self.buyer_interests:
                self.buyer_interests[(bundle_id, buyer)].shapley_value = value
        
        return shapley_values
    
    def complete_bundle_purchase(self, bundle_id: int, buyer: str) -> bool:
        """Complete a bundle purchase for a buyer"""
        bundle = self.bundles.get(bundle_id)
        interest = self.buyer_interests.get((bundle_id, buyer))
        
        if not bundle or not interest or not bundle.active or bundle.completed:
            return False
        
        # Mark as paid
        interest.has_paid = True
        
        # Check if all buyers have paid
        all_paid = True
        for b in bundle.interested_buyers:
            b_interest = self.buyer_interests.get((bundle_id, b))
            if not b_interest or not b_interest.has_paid:
                all_paid = False
                break
        
        # If all buyers have paid, complete the bundle
        if all_paid:
            bundle.completed = True
            bundle.active = False
            
            # Mark items as sold
            for item_id in bundle.item_ids:
                if item_id in self.nft_items:
                    self.nft_items[item_id].sold = True
        
        return True
    
    def create_bundle(self, item_ids: List[int], price: float, required_buyers: int, 
                     name: str, description: str) -> int:
        """Create a new bundle"""
        # Validate items
        for item_id in item_ids:
            if item_id not in self.nft_items or self.nft_items[item_id].sold:
                return 0
        
        # Create new bundle ID
        bundle_id = max(self.bundles.keys()) + 1 if self.bundles else 1
        
        # Create bundle
        self.bundles[bundle_id] = Bundle(
            bundle_id=bundle_id,
            item_ids=item_ids,
            price=price,
            required_buyers=required_buyers,
            active=True,
            interested_buyers=[],
            completed=False,
            name=name,
            description=description
        )
        
        return bundle_id
    
    def get_user_nfts(self, user_address: str) -> List[NFTItem]:
        """Get NFTs owned by a user"""
        # For demo purposes, we'll consider NFTs from completed bundles
        user_nfts = []
        
        for bundle_id, bundle in self.bundles.items():
            if bundle.completed:
                interest = self.buyer_interests.get((bundle_id, user_address))
                if interest and interest.has_paid:
                    for item_id in interest.items_of_interest:
                        if item_id in self.nft_items:
                            user_nfts.append(self.nft_items[item_id])
        
        return user_nfts
    
    def get_seller_bundles(self, seller_address: str) -> List[Bundle]:
        """Get bundles created by a seller"""
        seller_bundles = []
        
        for bundle in self.bundles.values():
            # Check if all items in the bundle belong to the seller
            seller_owns_all = True
            for item_id in bundle.item_ids:
                if item_id not in self.nft_items or self.nft_items[item_id].seller != seller_address:
                    seller_owns_all = False
                    break
            
            if seller_owns_all:
                seller_bundles.append(bundle)
        
        return seller_bundles 