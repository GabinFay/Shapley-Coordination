import os
import time
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from nft_bundle_sdk import NFTBundleSDK

# Load environment variables
load_dotenv(".env.local")

# Configuration
MARKETPLACE_ADDRESS = os.getenv("MARKETPLACE_ADDRESS")
MOCK_NFT_ADDRESS = os.getenv("MOCK_NFT_ADDRESS")

def test_nft_bundle_lifecycle():
    """Test the full lifecycle of an NFT bundle using the SDK"""
    print("=== Starting NFT Bundle Lifecycle Test ===")
    
    # Initialize SDK
    sdk = NFTBundleSDK(use_local=True)
    w3 = sdk.w3
    
    # Set up test accounts (similar to the Foundry test)
    seller = Account.from_key(os.getenv("SELLER_PRIVATE_KEY"))
    buyer1 = Account.from_key(os.getenv("ALICE_PRIVATE_KEY"))
    buyer2 = Account.from_key(os.getenv("BOB_PRIVATE_KEY"))
    buyer3 = Account.from_key(os.getenv("CHARLIE_PRIVATE_KEY"))
    tee_wallet = Account.from_key(os.getenv("TEE_PRIVATE_KEY"))
    
    print(f"Seller: {seller.address}")
    print(f"Buyer1: {buyer1.address}")
    print(f"Buyer2: {buyer2.address}")
    print(f"Buyer3: {buyer3.address}")
    print(f"TEE Wallet: {tee_wallet.address}")
    
    # Load contract instances
    marketplace = w3.eth.contract(address=MARKETPLACE_ADDRESS, abi=sdk.contract_abi)
    mock_nft = w3.eth.contract(address=MOCK_NFT_ADDRESS, abi=sdk.nft_abi)
    
    # Step 1: Set TEE wallet as Shapley calculator
    print("\n=== Setting TEE Wallet as Shapley Calculator ===")
    tx = marketplace.functions.setShapleyCalculator(tee_wallet.address).build_transaction({
        'from': seller.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(seller.address)
    })
    signed_tx = seller.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"TEE wallet set as Shapley calculator: {tee_wallet.address}")
    
    # Step 2: Mint NFTs to seller
    print("\n=== Minting NFTs to Seller ===")
    token_ids = []
    for i in range(1, 4):  # Mint 3 NFTs with IDs 1, 2, 3 (like in the Foundry test)
        tx = mock_nft.functions.mint(seller.address, i, f"NFT #{i}").build_transaction({
            'from': seller.address,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(seller.address)
        })
        signed_tx = seller.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        token_ids.append(i)
        print(f"Minted NFT with token ID: {i}")
    
    # Step 3: Approve NFTs for marketplace
    print("\n=== Approving NFTs for Marketplace ===")
    tx = mock_nft.functions.setApprovalForAll(MARKETPLACE_ADDRESS, True).build_transaction({
        'from': seller.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(seller.address)
    })
    signed_tx = seller.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Approved all NFTs for marketplace")
    
    # Step 4: List NFTs in marketplace
    print("\n=== Listing NFTs in Marketplace ===")
    item_ids = []
    for token_id in token_ids:
        tx = marketplace.functions.listNFT(MOCK_NFT_ADDRESS, token_id).build_transaction({
            'from': seller.address,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(seller.address)
        })
        signed_tx = seller.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get item ID from event logs or use item count
        item_id = None
        for log in receipt['logs']:
            if log['address'].lower() == MARKETPLACE_ADDRESS.lower():
                topics = log['topics']
                if len(topics) >= 3:
                    item_id = int(topics[1].hex(), 16)
                    break
        
        if item_id is None:
            item_count = marketplace.functions.getItemCount().call()
            item_id = item_count
        
        item_ids.append(item_id)
        print(f"Listed NFT with token ID {token_id} as item ID {item_id}")
    
    # Step 5: Create a bundle
    print("\n=== Creating Bundle ===")
    bundle_price = w3.to_wei(3, 'ether')  # 3 ETH, same as in Foundry test
    required_buyers = 3
    
    tx = marketplace.functions.createBundle(item_ids, bundle_price, required_buyers).build_transaction({
        'from': seller.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(seller.address)
    })
    signed_tx = seller.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Get bundle ID from event logs or use bundle count
    bundle_id = None
    for log in receipt['logs']:
        if log['address'].lower() == MARKETPLACE_ADDRESS.lower():
            topics = log['topics']
            if len(topics) >= 2:
                bundle_id = int(topics[1].hex(), 16)
                break
    
    if bundle_id is None:
        bundle_count = marketplace.functions.getBundleCount().call()
        bundle_id = bundle_count
    
    print(f"Created bundle with ID: {bundle_id}")
    
    # Verify bundle using SDK
    bundle = sdk.get_bundle(bundle_id)
    print(f"Bundle details from SDK:")
    print(f"Price: {bundle.price} ETH")
    print(f"Required buyers: {bundle.required_buyers}")
    print(f"Items: {bundle.item_ids}")
    
    # Step 6: Buyers express interest
    print("\n=== Expressing Interests ===")
    
    # Buyer 1 is interested in item 1
    buyer1_items = [item_ids[0]]
    tx = marketplace.functions.expressInterest(bundle_id, buyer1_items).build_transaction({
        'from': buyer1.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(buyer1.address)
    })
    signed_tx = buyer1.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Buyer1 expressed interest in item: {buyer1_items}")
    
    # Buyer 2 is interested in item 2
    buyer2_items = [item_ids[1]]
    tx = marketplace.functions.expressInterest(bundle_id, buyer2_items).build_transaction({
        'from': buyer2.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(buyer2.address)
    })
    signed_tx = buyer2.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Buyer2 expressed interest in item: {buyer2_items}")
    
    # Buyer 3 is interested in item 3
    buyer3_items = [item_ids[2]]
    tx = marketplace.functions.expressInterest(bundle_id, buyer3_items).build_transaction({
        'from': buyer3.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(buyer3.address)
    })
    signed_tx = buyer3.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Buyer3 expressed interest in item: {buyer3_items}")
    
    # Verify interests using SDK
    interests = sdk.get_all_buyer_interests(bundle_id)
    print(f"Bundle has {len(interests)} interested buyers")
    for interest in interests:
        print(f"Buyer {interest.buyer} is interested in items: {interest.items_of_interest}")
    
    # Step 7: Request attestation
    print("\n=== Requesting Attestation ===")
    tx = marketplace.functions.requestAttestation(bundle_id).build_transaction({
        'from': buyer1.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(buyer1.address)
    })
    signed_tx = buyer1.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Attestation requested for bundle {bundle_id}")
    
    # Step 8: TEE sets Shapley values
    print("\n=== Setting Shapley Values ===")
    
    # Get interested buyers
    bundle_info = marketplace.functions.getBundleInfo(bundle_id).call()
    interested_buyers = bundle_info[4]
    
    # Set equal Shapley values (1 ETH each, total 3 ETH)
    shapley_values = [w3.to_wei(1, 'ether')] * len(interested_buyers)
    
    tx = marketplace.functions.setShapleyValues(bundle_id, interested_buyers, shapley_values).build_transaction({
        'from': tee_wallet.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(tee_wallet.address)
    })
    signed_tx = tee_wallet.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Shapley values set for bundle {bundle_id}")
    
    # Verify Shapley values
    for buyer in interested_buyers:
        shapley_value = marketplace.functions.getShapleyValue(bundle_id, buyer).call()
        print(f"Buyer {buyer} Shapley value: {w3.from_wei(shapley_value, 'ether')} ETH")
    
    # Step 9: Buyers complete purchases
    print("\n=== Completing Purchases ===")
    
    # Record balances before
    seller_balance_before = w3.eth.get_balance(seller.address)
    buyer1_balance_before = w3.eth.get_balance(buyer1.address)
    buyer2_balance_before = w3.eth.get_balance(buyer2.address)
    buyer3_balance_before = w3.eth.get_balance(buyer3.address)
    
    # Buyer 1 completes purchase
    tx = marketplace.functions.completeBundlePurchase(bundle_id).build_transaction({
        'from': buyer1.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(buyer1.address),
        'value': w3.to_wei(1, 'ether')
    })
    signed_tx = buyer1.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Buyer1 completed purchase")
    
    # Buyer 2 completes purchase
    tx = marketplace.functions.completeBundlePurchase(bundle_id).build_transaction({
        'from': buyer2.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(buyer2.address),
        'value': w3.to_wei(1, 'ether')
    })
    signed_tx = buyer2.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Buyer2 completed purchase")
    
    # Check bundle status after 2 buyers
    bundle_info = marketplace.functions.getBundleInfo(bundle_id).call()
    completed = bundle_info[5]
    paid_count = bundle_info[6]
    print(f"Bundle completed: {completed}")
    print(f"Paid count: {paid_count}")
    
    # Buyer 3 completes purchase
    tx = marketplace.functions.completeBundlePurchase(bundle_id).build_transaction({
        'from': buyer3.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(buyer3.address),
        'value': w3.to_wei(1, 'ether')
    })
    signed_tx = buyer3.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Buyer3 completed purchase")
    
    # Step 10: Verify final state
    print("\n=== Verifying Final State ===")
    
    # Check bundle status
    bundle_info = marketplace.functions.getBundleInfo(bundle_id).call()
    active = bundle_info[3]
    completed = bundle_info[5]
    paid_count = bundle_info[6]
    print(f"Bundle active: {active}")
    print(f"Bundle completed: {completed}")
    print(f"Paid count: {paid_count}")
    
    # Check NFT ownership
    for i, item_id in enumerate(item_ids):
        item_info = marketplace.functions.getItemInfo(item_id).call()
        token_id = item_info[2]
        
        if i == 0:  # First item should be owned by buyer1
            owner = mock_nft.functions.ownerOf(token_id).call()
            print(f"Item {item_id} (Token {token_id}) owner: {owner}")
            print(f"Expected owner (Buyer1): {buyer1.address}")
            assert owner.lower() == buyer1.address.lower(), f"Item {item_id} not owned by Buyer1"
        elif i == 1:  # Second item should be owned by buyer2
            owner = mock_nft.functions.ownerOf(token_id).call()
            print(f"Item {item_id} (Token {token_id}) owner: {owner}")
            print(f"Expected owner (Buyer2): {buyer2.address}")
            assert owner.lower() == buyer2.address.lower(), f"Item {item_id} not owned by Buyer2"
        elif i == 2:  # Third item should be owned by buyer3
            owner = mock_nft.functions.ownerOf(token_id).call()
            print(f"Item {item_id} (Token {token_id}) owner: {owner}")
            print(f"Expected owner (Buyer3): {buyer3.address}")
            assert owner.lower() == buyer3.address.lower(), f"Item {item_id} not owned by Buyer3"
    
    # Check balances
    seller_balance_after = w3.eth.get_balance(seller.address)
    buyer1_balance_after = w3.eth.get_balance(buyer1.address)
    buyer2_balance_after = w3.eth.get_balance(buyer2.address)
    buyer3_balance_after = w3.eth.get_balance(buyer3.address)
    
    # Account for gas costs in the balance checks
    seller_balance_change = seller_balance_after - seller_balance_before
    buyer1_balance_change = buyer1_balance_after - buyer1_balance_before
    buyer2_balance_change = buyer2_balance_after - buyer2_balance_before
    buyer3_balance_change = buyer3_balance_after - buyer3_balance_before

    print(f"Seller balance change: {w3.from_wei(seller_balance_change, 'ether') if seller_balance_change >= 0 else -w3.from_wei(abs(seller_balance_change), 'ether')} ETH")
    print(f"Buyer1 balance change: {w3.from_wei(buyer1_balance_change, 'ether') if buyer1_balance_change >= 0 else -w3.from_wei(abs(buyer1_balance_change), 'ether')} ETH")
    print(f"Buyer2 balance change: {w3.from_wei(buyer2_balance_change, 'ether') if buyer2_balance_change >= 0 else -w3.from_wei(abs(buyer2_balance_change), 'ether')} ETH")
    print(f"Buyer3 balance change: {w3.from_wei(buyer3_balance_change, 'ether') if buyer3_balance_change >= 0 else -w3.from_wei(abs(buyer3_balance_change), 'ether')} ETH")
    
    # Get marketplace summary using SDK
    summary = sdk.get_marketplace_summary()
    print("\nMarketplace Summary:")
    print(f"Total items: {summary.total_items}")
    print(f"Total bundles: {summary.total_bundles}")
    print(f"Active items: {summary.active_items}")
    print(f"Active bundles: {summary.active_bundles}")
    print(f"Completed bundles: {summary.completed_bundles}")
    
    print("\n=== Test Completed Successfully ===")

if __name__ == "__main__":
    test_nft_bundle_lifecycle()