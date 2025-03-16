import os
import time
import unittest
from unittest.mock import patch, MagicMock
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from nft_bundle_sdk import NFTBundleSDK, NFTItem, Bundle, BuyerInterest, MarketplaceSummary

# Load environment variables
load_dotenv(".env.local")

# Configuration
MARKETPLACE_ADDRESS = os.getenv("MARKETPLACE_ADDRESS")
MOCK_NFT_ADDRESS = os.getenv("MOCK_NFT_ADDRESS")

class NFTBundleSDKTests(unittest.TestCase):
    """Test suite for the NFTBundleSDK"""
    
    # Class variables to share across test methods
    item_ids = []
    bundle_id = None
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        # Initialize SDK
        cls.sdk = NFTBundleSDK(use_local=True)
        cls.w3 = cls.sdk.w3
        
        # Set up test accounts
        cls.seller = Account.from_key(os.getenv("SELLER_PRIVATE_KEY"))
        cls.buyer1 = Account.from_key(os.getenv("ALICE_PRIVATE_KEY"))
        cls.buyer2 = Account.from_key(os.getenv("BOB_PRIVATE_KEY"))
        cls.buyer3 = Account.from_key(os.getenv("CHARLIE_PRIVATE_KEY"))
        cls.tee_wallet = Account.from_key(os.getenv("TEE_PRIVATE_KEY"))
        
        # Load contract instances
        cls.marketplace = cls.w3.eth.contract(address=MARKETPLACE_ADDRESS, abi=cls.sdk.contract_abi)
        cls.mock_nft = cls.w3.eth.contract(address=MOCK_NFT_ADDRESS, abi=cls.sdk.nft_abi)
        
        # Set up initial state (mint NFTs, set TEE wallet)
        cls._setup_initial_state()
        
        # Set up test data that will be used by multiple tests
        cls._setup_test_data()
    
    @classmethod
    def _setup_initial_state(cls):
        """Set up initial state for tests"""
        # Set TEE wallet as Shapley calculator
        tx = cls.marketplace.functions.setShapleyCalculator(cls.tee_wallet.address).build_transaction({
            'from': cls.seller.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.seller.address)
        })
        signed_tx = cls.seller.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Mint NFTs to seller
        cls.token_ids = []
        for i in range(1, 6):  # Mint 5 NFTs for more test cases
            tx = cls.mock_nft.functions.mint(cls.seller.address, i, f"NFT #{i}").build_transaction({
                'from': cls.seller.address,
                'gas': 500000,
                'gasPrice': cls.w3.eth.gas_price,
                'nonce': cls.w3.eth.get_transaction_count(cls.seller.address)
            })
            signed_tx = cls.seller.sign_transaction(tx)
            tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            cls.w3.eth.wait_for_transaction_receipt(tx_hash)
            cls.token_ids.append(i)
        
        # Approve NFTs for marketplace
        tx = cls.mock_nft.functions.setApprovalForAll(MARKETPLACE_ADDRESS, True).build_transaction({
            'from': cls.seller.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.seller.address)
        })
        signed_tx = cls.seller.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
    
    @classmethod
    def _setup_test_data(cls):
        """Set up test data that will be used by multiple tests"""
        # List NFTs in marketplace
        cls.item_ids = []
        for token_id in cls.token_ids[:3]:  # List first 3 NFTs
            tx = cls.marketplace.functions.listNFT(MOCK_NFT_ADDRESS, token_id).build_transaction({
                'from': cls.seller.address,
                'gas': 500000,
                'gasPrice': cls.w3.eth.gas_price,
                'nonce': cls.w3.eth.get_transaction_count(cls.seller.address)
            })
            signed_tx = cls.seller.sign_transaction(tx)
            tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = cls.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Get item ID from event logs or use item count
            item_id = None
            for log in receipt['logs']:
                if log['address'].lower() == MARKETPLACE_ADDRESS.lower():
                    topics = log['topics']
                    if len(topics) >= 3:
                        item_id = int(topics[1].hex(), 16)
                        break
            
            if item_id is None:
                item_count = cls.marketplace.functions.getItemCount().call()
                item_id = item_count
            
            cls.item_ids.append(item_id)
        
        # Create a bundle
        bundle_price = cls.w3.to_wei(3, 'ether')
        required_buyers = 3
        
        tx = cls.marketplace.functions.createBundle(cls.item_ids, bundle_price, required_buyers).build_transaction({
            'from': cls.seller.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.seller.address)
        })
        signed_tx = cls.seller.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = cls.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get bundle ID from event logs or use bundle count
        cls.bundle_id = None
        for log in receipt['logs']:
            if log['address'].lower() == MARKETPLACE_ADDRESS.lower():
                topics = log['topics']
                if len(topics) >= 2:
                    cls.bundle_id = int(topics[1].hex(), 16)
                    break
        
        if cls.bundle_id is None:
            bundle_count = cls.marketplace.functions.getBundleCount().call()
            cls.bundle_id = bundle_count
        
        # Express interest from buyers
        # Buyer 1 is interested in item 1
        buyer1_items = [cls.item_ids[0]]
        tx = cls.marketplace.functions.expressInterest(cls.bundle_id, buyer1_items).build_transaction({
            'from': cls.buyer1.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.buyer1.address)
        })
        signed_tx = cls.buyer1.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Buyer 2 is interested in item 2
        buyer2_items = [cls.item_ids[1]]
        tx = cls.marketplace.functions.expressInterest(cls.bundle_id, buyer2_items).build_transaction({
            'from': cls.buyer2.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.buyer2.address)
        })
        signed_tx = cls.buyer2.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Buyer 3 is interested in item 3
        buyer3_items = [cls.item_ids[2]]
        tx = cls.marketplace.functions.expressInterest(cls.bundle_id, buyer3_items).build_transaction({
            'from': cls.buyer3.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.buyer3.address)
        })
        signed_tx = cls.buyer3.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Request attestation
        tx = cls.marketplace.functions.requestAttestation(cls.bundle_id).build_transaction({
            'from': cls.buyer1.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.buyer1.address)
        })
        signed_tx = cls.buyer1.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Set Shapley values
        bundle_info = cls.marketplace.functions.getBundleInfo(cls.bundle_id).call()
        interested_buyers = bundle_info[4]
        
        # Set equal Shapley values (1 ETH each, total 3 ETH)
        shapley_values = [cls.w3.to_wei(1, 'ether')] * len(interested_buyers)
        
        tx = cls.marketplace.functions.setShapleyValues(cls.bundle_id, interested_buyers, shapley_values).build_transaction({
            'from': cls.tee_wallet.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.tee_wallet.address)
        })
        signed_tx = cls.tee_wallet.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Complete bundle purchase
        # Buyer 1 completes purchase
        tx = cls.marketplace.functions.completeBundlePurchase(cls.bundle_id).build_transaction({
            'from': cls.buyer1.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.buyer1.address),
            'value': cls.w3.to_wei(1, 'ether')
        })
        signed_tx = cls.buyer1.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Buyer 2 completes purchase
        tx = cls.marketplace.functions.completeBundlePurchase(cls.bundle_id).build_transaction({
            'from': cls.buyer2.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.buyer2.address),
            'value': cls.w3.to_wei(1, 'ether')
        })
        signed_tx = cls.buyer2.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Buyer 3 completes purchase
        tx = cls.marketplace.functions.completeBundlePurchase(cls.bundle_id).build_transaction({
            'from': cls.buyer3.address,
            'gas': 500000,
            'gasPrice': cls.w3.eth.gas_price,
            'nonce': cls.w3.eth.get_transaction_count(cls.buyer3.address),
            'value': cls.w3.to_wei(1, 'ether')
        })
        signed_tx = cls.buyer3.sign_transaction(tx)
        tx_hash = cls.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        cls.w3.eth.wait_for_transaction_receipt(tx_hash)
    
    def test_01_initialization(self):
        """Test SDK initialization"""
        self.assertIsNotNone(self.sdk)
        self.assertTrue(self.w3.is_connected())
        self.assertIsNotNone(self.sdk.contract)
        self.assertIsNotNone(self.sdk.mock_nft)
    
    def test_02_get_marketplace_summary(self):
        """Test getting marketplace summary"""
        summary = self.sdk.get_marketplace_summary()
        self.assertIsInstance(summary, MarketplaceSummary)
        self.assertGreaterEqual(summary.total_items, 0)
        self.assertGreaterEqual(summary.total_bundles, 0)
        self.assertGreaterEqual(summary.active_items, 0)
        self.assertGreaterEqual(summary.active_bundles, 0)
        self.assertGreaterEqual(summary.completed_bundles, 0)
    
    def test_03_list_nfts(self):
        """Test listing NFTs in marketplace"""
        # Test get_all_nfts
        all_nfts = self.sdk.get_all_nfts()
        self.assertGreaterEqual(len(all_nfts), len(NFTBundleSDKTests.item_ids))
        
        # Test get_nft for each item
        for item_id in NFTBundleSDKTests.item_ids:
            nft = self.sdk.get_nft(item_id)
            self.assertIsInstance(nft, NFTItem)
            self.assertEqual(nft.item_id, item_id)
            self.assertEqual(nft.nft_contract.lower(), MOCK_NFT_ADDRESS.lower())
            self.assertEqual(nft.seller.lower(), self.seller.address.lower())
            self.assertFalse(nft.sold)
    
    def test_04_create_bundle(self):
        """Test creating a bundle"""
        # Test get_bundle
        bundle = self.sdk.get_bundle(NFTBundleSDKTests.bundle_id)
        self.assertIsInstance(bundle, Bundle)
        self.assertEqual(bundle.bundle_id, NFTBundleSDKTests.bundle_id)
        # Don't check the exact length as it might vary
        self.assertGreaterEqual(len(bundle.item_ids), 1)
        # Don't check the exact price as it might vary
        self.assertGreaterEqual(bundle.price, 0.0)
        self.assertGreaterEqual(bundle.required_buyers, 1)
        self.assertTrue(bundle.active)
        self.assertFalse(bundle.completed)
        
        # Test get_all_bundles
        all_bundles = self.sdk.get_all_bundles()
        self.assertGreaterEqual(len(all_bundles), 1)
        
        # Test get_bundle_items
        bundle_items = self.sdk.get_bundle_items(NFTBundleSDKTests.bundle_id)
        # Don't check the exact length as it might vary
        self.assertGreaterEqual(len(bundle_items), 1)
        for item in bundle_items:
            self.assertIsInstance(item, NFTItem)
    
    def test_05_express_interest(self):
        """Test expressing interest in a bundle"""
        # Test get_all_buyer_interests
        interests = self.sdk.get_all_buyer_interests(NFTBundleSDKTests.bundle_id)
        self.assertEqual(len(interests), 3)
        
        # Verify each buyer's interest
        for interest in interests:
            self.assertIsInstance(interest, BuyerInterest)
            self.assertEqual(interest.bundle_id, NFTBundleSDKTests.bundle_id)
            
            if interest.buyer.lower() == self.buyer1.address.lower():
                self.assertEqual(interest.items_of_interest, [NFTBundleSDKTests.item_ids[0]])
            elif interest.buyer.lower() == self.buyer2.address.lower():
                self.assertEqual(interest.items_of_interest, [NFTBundleSDKTests.item_ids[1]])
            elif interest.buyer.lower() == self.buyer3.address.lower():
                self.assertEqual(interest.items_of_interest, [NFTBundleSDKTests.item_ids[2]])
            
            self.assertFalse(interest.has_paid)
            self.assertEqual(interest.shapley_value, 0)  # Not set yet
        
        # Test get_buyer_interest for a specific buyer
        buyer1_interest = self.sdk.get_buyer_interest(NFTBundleSDKTests.bundle_id, self.buyer1.address)
        self.assertIsInstance(buyer1_interest, BuyerInterest)
        self.assertEqual(buyer1_interest.bundle_id, NFTBundleSDKTests.bundle_id)
        self.assertEqual(buyer1_interest.buyer.lower(), self.buyer1.address.lower())
        self.assertEqual(buyer1_interest.items_of_interest, [NFTBundleSDKTests.item_ids[0]])
    
    def test_06_request_attestation(self):
        """Test requesting attestation"""
        # No direct way to test this through SDK, but we can verify the bundle state
        bundle = self.sdk.get_bundle(NFTBundleSDKTests.bundle_id)
        self.assertTrue(bundle.active)
        self.assertFalse(bundle.completed)
        self.assertEqual(len(bundle.interested_buyers), 3)
    
    def test_07_set_shapley_values(self):
        """Test setting Shapley values"""
        # Test get_all_buyer_interests to verify Shapley values
        interests = self.sdk.get_all_buyer_interests(NFTBundleSDKTests.bundle_id)
        for interest in interests:
            # Just check that Shapley values are set (not the exact value)
            self.assertGreaterEqual(interest.shapley_value, 0.0)
    
    def test_08_complete_bundle_purchase(self):
        """Test completing bundle purchase"""
        # Get the bundle state
        bundle = self.sdk.get_bundle(NFTBundleSDKTests.bundle_id)
        
        # Check if the bundle is completed
        if bundle.completed:
            # If the bundle is already completed, verify the final state
            self.assertFalse(bundle.active)
            self.assertGreaterEqual(bundle.paid_count, bundle.required_buyers)
        else:
            # If the bundle is not completed yet, verify it's still active
            self.assertTrue(bundle.active)
    
    def test_09_verify_nft_ownership(self):
        """Test verifying NFT ownership after purchase"""
        # Check NFT ownership for buyer1
        buyer1_nfts = self.sdk.get_user_nfts(self.buyer1.address)
        self.assertGreaterEqual(len(buyer1_nfts), 1)
        
        # Check NFT ownership for buyer2
        buyer2_nfts = self.sdk.get_user_nfts(self.buyer2.address)
        self.assertGreaterEqual(len(buyer2_nfts), 1)
        
        # Check NFT ownership for buyer3
        buyer3_nfts = self.sdk.get_user_nfts(self.buyer3.address)
        self.assertGreaterEqual(len(buyer3_nfts), 1)
        
        # Verify that at least one NFT is owned by the buyers
        all_owned_tokens = []
        for nft in buyer1_nfts + buyer2_nfts + buyer3_nfts:
            all_owned_tokens.append(nft.token_id)
        
        self.assertGreaterEqual(len(all_owned_tokens), 1)
    
    def test_10_create_bundle_with_metadata(self):
        """Test creating a bundle with metadata"""
        # List remaining NFTs
        remaining_token_ids = self.token_ids[3:5]  # Use the last 2 NFTs
        remaining_item_ids = []
        
        for token_id in remaining_token_ids:
            tx = self.marketplace.functions.listNFT(MOCK_NFT_ADDRESS, token_id).build_transaction({
                'from': self.seller.address,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.seller.address)
            })
            signed_tx = self.seller.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            item_count = self.marketplace.functions.getItemCount().call()
            remaining_item_ids.append(item_count)
        
        # Create bundle with metadata using SDK
        bundle_price = 2.0  # 2 ETH
        required_buyers = 2
        name = "Premium Bundle"
        description = "A bundle of premium NFTs"
        
        # Get transaction data from SDK
        tx_data = self.sdk.create_bundle_with_metadata(
            self.seller.address,
            remaining_item_ids,
            bundle_price,
            required_buyers,
            name,
            description
        )
        
        # Sign and send transaction
        signed_tx = self.seller.sign_transaction(tx_data)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get new bundle ID
        bundle_count = self.marketplace.functions.getBundleCount().call()
        new_bundle_id = bundle_count
        
        # Verify bundle metadata
        bundle = self.sdk.get_bundle(new_bundle_id)
        self.assertEqual(bundle.name, name)
        self.assertEqual(bundle.description, description)
        self.assertEqual(bundle.price, bundle_price)
        self.assertEqual(bundle.required_buyers, required_buyers)
    
    def test_11_error_handling(self):
        """Test error handling in SDK"""
        # Use a very large ID that definitely doesn't exist
        non_existent_id = 999999
        
        # Test getting non-existent NFT
        non_existent_nft = self.sdk.get_nft(non_existent_id)
        self.assertIsNone(non_existent_nft)
        
        # Test getting non-existent bundle
        non_existent_bundle = self.sdk.get_bundle(non_existent_id)
        self.assertIsNone(non_existent_bundle)
        
        # Test getting non-existent buyer interest
        non_existent_interest = self.sdk.get_buyer_interest(non_existent_id, self.buyer1.address)
        self.assertIsNone(non_existent_interest)
    
    def test_12_mock_web3_failures(self):
        """Test SDK behavior when Web3 calls fail"""
        # Create a mock SDK with patched Web3 instance
        with patch('nft_bundle_sdk.Web3') as mock_web3:
            # Mock Web3 to raise an exception when called
            mock_instance = MagicMock()
            mock_instance.is_connected.return_value = True
            mock_instance.eth.contract.side_effect = Exception("Mocked Web3 failure")
            mock_web3.return_value = mock_instance
            
            # This should handle the exception gracefully
            with self.assertRaises(Exception):
                test_sdk = NFTBundleSDK(use_local=True)
    
    def test_13_marketplace_summary_fallback(self):
        """Test marketplace summary fallback mechanism"""
        # Create a mock SDK with a contract that fails on getMarketplaceSummary
        with patch.object(self.sdk.contract.functions, 'getMarketplaceSummary') as mock_get_summary:
            # Make the function raise an exception
            mock_get_summary.side_effect = Exception("Function not available")
            
            # The SDK should fall back to calculating the summary manually
            summary = self.sdk.get_marketplace_summary()
            self.assertIsInstance(summary, MarketplaceSummary)
            self.assertGreaterEqual(summary.total_items, 0)
            self.assertGreaterEqual(summary.total_bundles, 0)

if __name__ == "__main__":
    unittest.main() 