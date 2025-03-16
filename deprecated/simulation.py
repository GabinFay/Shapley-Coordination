import time
import random
from typing import Dict, List, Tuple, Set
from shapley_calculator import ShapleyCalculator

class MockNFT:
    """Mock NFT for simulation purposes"""
    def __init__(self, token_id: int, name: str):
        self.token_id = token_id
        self.name = name
        self.owner = None
        
    def __str__(self):
        return f"NFT #{self.token_id}: {self.name} (Owner: {self.owner})"


class MockUser:
    """Mock user for simulation purposes"""
    def __init__(self, address: str, balance: float = 1000.0):
        self.address = address
        self.balance = balance
        self.nfts = []
        self.interested_bundles = {}  # bundle_id -> list of item_ids
        
    def add_nft(self, nft: MockNFT):
        self.nfts.append(nft)
        nft.owner = self.address
        
    def list_nft(self, nft: MockNFT, marketplace):
        if nft in self.nfts and nft.owner == self.address:
            self.nfts.remove(nft)
            return marketplace.list_nft(self.address, nft)
        return None
    
    def express_interest(self, bundle_id: int, item_ids: List[int], marketplace):
        self.interested_bundles[bundle_id] = item_ids
        marketplace.express_interest(bundle_id, self.address, item_ids)
        
    def pay_for_bundle(self, bundle_id: int, amount: float, marketplace):
        if self.balance >= amount:
            self.balance -= amount
            marketplace.complete_purchase(bundle_id, self.address, amount)
            return True
        return False
    
    def __str__(self):
        return f"User {self.address} (Balance: ${self.balance:.2f}, NFTs: {len(self.nfts)})"


class MockMarketplace:
    """Mock marketplace for simulation purposes"""
    def __init__(self):
        self.nfts = {}  # item_id -> NFT
        self.bundles = {}  # bundle_id -> Bundle
        self.item_id_counter = 0
        self.bundle_id_counter = 0
        self.shapley_calculator = None
        self.events = []
        
    def list_nft(self, seller_address: str, nft: MockNFT) -> int:
        """List an NFT in the marketplace"""
        self.item_id_counter += 1
        item_id = self.item_id_counter
        
        self.nfts[item_id] = {
            'nft': nft,
            'seller': seller_address,
            'sold': False
        }
        
        self.log_event("NFTListed", {
            'item_id': item_id,
            'token_id': nft.token_id,
            'seller': seller_address
        })
        
        return item_id
    
    def create_bundle(self, seller_address: str, item_ids: List[int], price: float, required_buyers: int) -> int:
        """Create a bundle of NFTs"""
        # Validate items
        for item_id in item_ids:
            if item_id not in self.nfts:
                print(f"Item {item_id} does not exist")
                return None
            
            if self.nfts[item_id]['seller'] != seller_address:
                print(f"Item {item_id} does not belong to seller {seller_address}")
                return None
            
            if self.nfts[item_id]['sold']:
                print(f"Item {item_id} is already sold")
                return None
        
        self.bundle_id_counter += 1
        bundle_id = self.bundle_id_counter
        
        self.bundles[bundle_id] = {
            'item_ids': item_ids,
            'price': price,
            'required_buyers': required_buyers,
            'seller': seller_address,
            'active': True,
            'completed': False,
            'interested_buyers': {},  # address -> list of item_ids
            'payments': {},  # address -> amount
            'shapley_values': {}  # address -> amount
        }
        
        self.log_event("BundleCreated", {
            'bundle_id': bundle_id,
            'item_ids': item_ids,
            'price': price,
            'required_buyers': required_buyers,
            'seller': seller_address
        })
        
        return bundle_id
    
    def express_interest(self, bundle_id: int, buyer_address: str, item_ids: List[int]):
        """Express interest in a bundle"""
        if bundle_id not in self.bundles:
            print(f"Bundle {bundle_id} does not exist")
            return False
        
        bundle = self.bundles[bundle_id]
        
        if not bundle['active'] or bundle['completed']:
            print(f"Bundle {bundle_id} is not active or already completed")
            return False
        
        if buyer_address in bundle['interested_buyers']:
            print(f"Buyer {buyer_address} already expressed interest in bundle {bundle_id}")
            return False
        
        # Validate items of interest
        for item_id in item_ids:
            if item_id not in bundle['item_ids']:
                print(f"Item {item_id} is not in bundle {bundle_id}")
                return False
        
        bundle['interested_buyers'][buyer_address] = item_ids
        
        self.log_event("BuyerInterested", {
            'bundle_id': bundle_id,
            'buyer': buyer_address,
            'item_ids': item_ids
        })
        
        # Check if we have enough buyers
        if len(bundle['interested_buyers']) >= bundle['required_buyers']:
            self.log_event("BundleReadyForPurchase", {
                'bundle_id': bundle_id,
                'buyers': list(bundle['interested_buyers'].keys())
            })
            
            # Calculate Shapley values
            self.calculate_shapley_values(bundle_id)
        
        return True
    
    def calculate_shapley_values(self, bundle_id: int):
        """Calculate Shapley values for a bundle"""
        bundle = self.bundles[bundle_id]
        
        # Initialize Shapley calculator with bundle price
        calculator = ShapleyCalculator(bundle['price'])
        
        # Calculate Shapley values
        shapley_values = calculator.calculate_values(bundle['interested_buyers'])
        bundle['shapley_values'] = shapley_values
        
        self.log_event("ShapleyValuesSet", {
            'bundle_id': bundle_id,
            'buyers': list(shapley_values.keys()),
            'values': list(shapley_values.values())
        })
        
        return shapley_values
    
    def complete_purchase(self, bundle_id: int, buyer_address: str, amount: float):
        """Complete a purchase for a buyer"""
        if bundle_id not in self.bundles:
            print(f"Bundle {bundle_id} does not exist")
            return False
        
        bundle = self.bundles[bundle_id]
        
        if not bundle['active'] or bundle['completed']:
            print(f"Bundle {bundle_id} is not active or already completed")
            return False
        
        if buyer_address not in bundle['interested_buyers']:
            print(f"Buyer {buyer_address} is not interested in bundle {bundle_id}")
            return False
        
        if buyer_address not in bundle['shapley_values']:
            print(f"Shapley value not set for buyer {buyer_address}")
            return False
        
        shapley_value = bundle['shapley_values'][buyer_address]
        
        if amount < shapley_value:
            print(f"Insufficient payment: {amount} < {shapley_value}")
            return False
        
        # Record payment
        bundle['payments'][buyer_address] = amount
        
        # Check if all buyers have paid
        all_paid = True
        for buyer in bundle['interested_buyers']:
            if buyer not in bundle['payments']:
                all_paid = False
                break
        
        if all_paid:
            # Complete the bundle purchase
            bundle['completed'] = True
            bundle['active'] = False
            
            # Mark items as sold and transfer to buyers
            for buyer, item_ids in bundle['interested_buyers'].items():
                for item_id in item_ids:
                    if item_id in self.nfts:
                        self.nfts[item_id]['sold'] = True
                        nft = self.nfts[item_id]['nft']
                        nft.owner = buyer
            
            self.log_event("BundlePurchased", {
                'bundle_id': bundle_id,
                'buyers': list(bundle['interested_buyers'].keys())
            })
        
        return True
    
    def log_event(self, event_type: str, data: dict):
        """Log an event"""
        event = {
            'type': event_type,
            'timestamp': time.time(),
            'data': data
        }
        self.events.append(event)
        print(f"EVENT: {event_type} - {data}")


def run_simulation():
    """Run a full simulation of the NFT bundle marketplace"""
    print("=== Starting NFT Bundle Marketplace Simulation ===")
    
    # Create marketplace
    marketplace = MockMarketplace()
    
    # Create users
    alice = MockUser("0xAlice")
    bob = MockUser("0xBob")
    charlie = MockUser("0xCharlie")
    dave = MockUser("0xDave")  # Seller
    
    print("\n=== Users Created ===")
    print(alice)
    print(bob)
    print(charlie)
    print(dave)
    
    # Create NFTs
    nft_a = MockNFT(1, "Artwork A")
    nft_b = MockNFT(2, "Artwork B")
    nft_c = MockNFT(3, "Artwork C")
    
    # Assign NFTs to seller
    dave.add_nft(nft_a)
    dave.add_nft(nft_b)
    dave.add_nft(nft_c)
    
    print("\n=== NFTs Created and Assigned to Seller ===")
    print(nft_a)
    print(nft_b)
    print(nft_c)
    
    # List NFTs in marketplace
    item_a = dave.list_nft(nft_a, marketplace)
    item_b = dave.list_nft(nft_b, marketplace)
    item_c = dave.list_nft(nft_c, marketplace)
    
    print("\n=== NFTs Listed in Marketplace ===")
    print(f"Item A ID: {item_a}")
    print(f"Item B ID: {item_b}")
    print(f"Item C ID: {item_c}")
    
    # Create bundles
    bundle_ab = marketplace.create_bundle(dave.address, [item_a, item_b], 150.0, 2)
    bundle_bc = marketplace.create_bundle(dave.address, [item_b, item_c], 160.0, 2)
    bundle_ac = marketplace.create_bundle(dave.address, [item_a, item_c], 170.0, 2)
    bundle_abc = marketplace.create_bundle(dave.address, [item_a, item_b, item_c], 200.0, 3)
    
    print("\n=== Bundles Created ===")
    print(f"Bundle AB ID: {bundle_ab} - Price: $150.0 - Required Buyers: 2")
    print(f"Bundle BC ID: {bundle_bc} - Price: $160.0 - Required Buyers: 2")
    print(f"Bundle AC ID: {bundle_ac} - Price: $170.0 - Required Buyers: 2")
    print(f"Bundle ABC ID: {bundle_abc} - Price: $200.0 - Required Buyers: 3")
    
    # Simulate buyers expressing interest in the ABC bundle
    print("\n=== Buyers Express Interest in Bundle ABC ===")
    alice.express_interest(bundle_abc, [item_a, item_b], marketplace)
    bob.express_interest(bundle_abc, [item_b, item_c], marketplace)
    charlie.express_interest(bundle_abc, [item_a, item_c], marketplace)
    
    # At this point, Shapley values should be calculated automatically
    
    # Get Shapley values
    shapley_values = marketplace.bundles[bundle_abc]['shapley_values']
    
    print("\n=== Shapley Values for Bundle ABC ===")
    for buyer, value in shapley_values.items():
        print(f"{buyer}: ${value:.2f}")
    
    # Buyers pay for the bundle
    print("\n=== Buyers Pay for Bundle ABC ===")
    alice.pay_for_bundle(bundle_abc, shapley_values['0xAlice'], marketplace)
    bob.pay_for_bundle(bundle_abc, shapley_values['0xBob'], marketplace)
    charlie.pay_for_bundle(bundle_abc, shapley_values['0xCharlie'], marketplace)
    
    # Check final state
    print("\n=== Final State ===")
    print(alice)
    print(bob)
    print(charlie)
    print(dave)
    
    print("\n=== NFT Ownership ===")
    print(nft_a)
    print(nft_b)
    print(nft_c)
    
    print("\n=== Simulation Complete ===")


if __name__ == "__main__":
    run_simulation() 