import streamlit as st
import pandas as pd
import numpy as np
import time
import json
import os
from shapley_calculator import ShapleyCalculator
from nft_bundle_sdk import NFTBundleSDK, NFTItem, Bundle, BuyerInterest
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="NFT Bundle Marketplace",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize SDK and Web3 connection
@st.cache_resource
def initialize_sdk():
    """Initialize the NFT Bundle SDK"""
    try:
        # Connect to local Anvil instance
        sdk = NFTBundleSDK(use_local=True, local_url="http://localhost:8545")
        
        # Get contract addresses from environment variables
        contract_address = os.getenv("MARKETPLACE_ADDRESS")
        mock_nft_address = os.getenv("MOCK_NFT_ADDRESS")
        
        # If environment variables are not set, try to load from deployment data
        if not contract_address or not mock_nft_address:
            try:
                with open("deployment_data.json", "r") as f:
                    deployment_data = json.load(f)
                    contract_address = deployment_data.get("marketplace_address")
                    mock_nft_address = deployment_data.get("nft_address")
            except Exception as e:
                st.error(f"Failed to load deployment data: {e}")
        
        # Convert addresses to checksum format if they exist
        if contract_address and sdk.w3.is_connected():
            try:
                contract_address = sdk.w3.to_checksum_address(contract_address)
            except Exception as e:
                st.error(f"Invalid marketplace contract address: {e}")
                
        if mock_nft_address and sdk.w3.is_connected():
            try:
                mock_nft_address = sdk.w3.to_checksum_address(mock_nft_address)
            except Exception as e:
                st.error(f"Invalid NFT contract address: {e}")
        
        return sdk, contract_address, mock_nft_address
    except Exception as e:
        st.error(f"Failed to initialize SDK: {e}")
        return None, None, None

# Initialize session state
if 'marketplace' not in st.session_state:
    print("INITIALIZING SESSION STATE: Creating marketplace")  # Debug print
    # Initialize with real data from SDK
    sdk, contract_address, mock_nft_address = initialize_sdk()
    
    if sdk:
        print(f"SDK INITIALIZED: Contract address {contract_address}, NFT address {mock_nft_address}")  # Debug print
        
        # Convert user addresses to checksum format
        user_addresses = {
            sdk.to_checksum_address('0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266'): {'balance': 1000.0, 'nfts': []},  # Seller/Owner
            sdk.to_checksum_address('0x70997970c51812dc3a010c7d01b50e0d17dc79c8'): {'balance': 1000.0, 'nfts': []},  # Alice
            sdk.to_checksum_address('0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc'): {'balance': 1000.0, 'nfts': []},  # Bob
            sdk.to_checksum_address('0x90f79bf6eb2c4f870365e785982e1f101e93b906'): {'balance': 1000.0, 'nfts': []},  # Charlie
            sdk.to_checksum_address('0x15d34aaf54267db7d7c367839aaf71a00a2c6a65'): {'balance': 1000.0, 'nfts': []}   # Dave
        }
        
        # Initialize custom bundles and NFTs
        sdk._bundles = {}
        sdk._nfts = {}
        
        st.session_state.marketplace = {
            'sdk': sdk,
            'contract_address': contract_address,
            'mock_nft_address': mock_nft_address,
            'users': user_addresses,
            'events': [],
            'custom_bundles': {},  # Store custom bundles in session state
            'custom_nfts': {}      # Store custom NFTs in session state
        }
        print("MARKETPLACE INITIALIZED: Users and events created")  # Debug print
    else:
        print("SDK INITIALIZATION FAILED: Using fallback marketplace")  # Debug print
        st.session_state.marketplace = {
            'sdk': None,
            'contract_address': None,
            'mock_nft_address': None,
            'users': {
                '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266': {'balance': 1000.0, 'nfts': []},  # Seller/Owner
                '0x70997970c51812dc3a010c7d01b50e0d17dc79c8': {'balance': 1000.0, 'nfts': []},  # Alice
                '0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc': {'balance': 1000.0, 'nfts': []},  # Bob
                '0x90f79bf6eb2c4f870365e785982e1f101e93b906': {'balance': 1000.0, 'nfts': []},  # Charlie
                '0x15d34aaf54267db7d7c367839aaf71a00a2c6a65': {'balance': 1000.0, 'nfts': []}   # Dave
            },
            'events': [],
            'custom_bundles': {},  # Store custom bundles in session state
            'custom_nfts': {}      # Store custom NFTs in session state
        }

# Helper functions
def log_event(event_type, data):
    """Log an event to the marketplace"""
    event = {
        'type': event_type,
        'timestamp': time.time(),
        'data': data
    }
    st.session_state.marketplace['events'].append(event)
    print(f"EVENT LOGGED: {event_type} - {data}")  # Debug print
    return event

# Restore custom bundles and NFTs from session state to SDK
if 'marketplace' in st.session_state and st.session_state.marketplace['sdk']:
    sdk = st.session_state.marketplace['sdk']
    
    # Test: Create a test bundle if none exist
    if 'custom_bundles' in st.session_state.marketplace and not st.session_state.marketplace['custom_bundles']:
        print("DEBUG: Creating a test bundle in session state")
        test_bundle = Bundle(
            bundle_id=999,
            item_ids=[1, 2, 3],
            price=5.0,
            required_buyers=3,
            active=True,
            interested_buyers=[],
            completed=False,
            paid_count=0,
            name="Test Bundle",
            description="This is a test bundle created at app startup"
        )
        st.session_state.marketplace['custom_bundles'][999] = test_bundle
        if not hasattr(sdk, '_bundles'):
            sdk._bundles = {}
        sdk._bundles[999] = test_bundle
    
    # Restore custom bundles
    if 'custom_bundles' in st.session_state.marketplace and st.session_state.marketplace['custom_bundles']:
        if not hasattr(sdk, '_bundles'):
            sdk._bundles = {}
        
        print(f"DEBUG: Restoring {len(st.session_state.marketplace['custom_bundles'])} bundles from session state")
        for bundle_id, bundle in st.session_state.marketplace['custom_bundles'].items():
            # Ensure bundle_id is an integer
            bundle_id = int(bundle_id)
            sdk._bundles[bundle_id] = bundle
            print(f"DEBUG: Restored bundle {bundle_id}: {bundle.name}, active={bundle.active}, completed={bundle.completed}")
        
        print(f"RESTORED: {len(sdk._bundles)} bundles from session state")
        print(f"DEBUG: SDK _bundles keys: {list(sdk._bundles.keys())}")
    
    # Restore custom NFTs
    if 'custom_nfts' in st.session_state.marketplace and st.session_state.marketplace['custom_nfts']:
        if not hasattr(sdk, '_nfts'):
            sdk._nfts = {}
        
        for item_id, nft in st.session_state.marketplace['custom_nfts'].items():
            sdk._nfts[int(item_id)] = nft
        
        print(f"RESTORED: {len(sdk._nfts)} NFTs from session state")

def get_user_friendly_name(address):
    """Convert Ethereum address to a user-friendly name"""
    address_map = {
        '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266': 'Seller',
        '0x70997970c51812dc3a010c7d01b50e0d17dc79c8': 'Alice',
        '0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc': 'Bob',
        '0x90f79bf6eb2c4f870365e785982e1f101e93b906': 'Charlie',
        '0x15d34aaf54267db7d7c367839aaf71a00a2c6a65': 'Dave'
    }
    
    # Also add checksum versions of the addresses if SDK is available
    if 'marketplace' in st.session_state and st.session_state.marketplace['sdk']:
        sdk = st.session_state.marketplace['sdk']
        for addr, name in list(address_map.items()):
            try:
                checksum_addr = sdk.to_checksum_address(addr)
                if checksum_addr != addr:
                    address_map[checksum_addr] = name
            except:
                pass
    
    return address_map.get(address, address[:6] + '...' + address[-4:])

def get_nft_image_url(item_id):
    """Generate a placeholder image URL for an NFT"""
    return f"https://picsum.photos/seed/{item_id}/200/200"

def express_interest(bundle_id, buyer, item_ids):
    """Express interest in a bundle"""
    print(f"EXPRESSING INTEREST: Bundle {bundle_id}, Buyer {buyer}, Items {item_ids}")  # Debug print
    sdk = st.session_state.marketplace['sdk']
    if not sdk:
        st.error("SDK not initialized")
        print("ERROR: SDK not initialized")  # Debug print
        return False
    
    # Convert buyer address to checksum format
    try:
        success = sdk.express_interest(bundle_id, buyer, item_ids)
    except Exception as e:
        st.error(f"Error expressing interest: {e}")
        print(f"ERROR: {e}")  # Debug print
        return False
    
    if success:
        print(f"SUCCESS: Interest expressed for bundle {bundle_id}")  # Debug print
        log_event("BuyerInterested", {
            'bundle_id': bundle_id,
            'buyer': buyer,
            'item_ids': item_ids
        })
        
        # Check if we have enough buyers for Shapley calculation
        bundle = sdk.get_bundle(bundle_id)
        if len(bundle.interested_buyers) >= bundle.required_buyers:
            print(f"NOTICE: Bundle {bundle_id} has enough buyers for Shapley calculation")  # Debug print
            # Calculate Shapley values
            shapley_values = sdk.calculate_shapley_values(bundle_id)
            
            log_event("ShapleyValuesSet", {
                'bundle_id': bundle_id,
                'buyers': list(shapley_values.keys()),
                'values': list(shapley_values.values())
            })
    else:
        print(f"FAILED: Interest expression for bundle {bundle_id}")  # Debug print
    
    return success

def complete_purchase(bundle_id, buyer):
    """Complete a purchase for a buyer"""
    print(f"COMPLETING PURCHASE: Bundle {bundle_id}, Buyer {buyer}")  # Debug print
    sdk = st.session_state.marketplace['sdk']
    if not sdk:
        st.error("SDK not initialized")
        print("ERROR: SDK not initialized")  # Debug print
        return False
    
    # Get buyer's interest
    try:
        interest = sdk.get_buyer_interest(bundle_id, buyer)
        if not interest:
            st.error(f"No interest found for buyer {buyer} in bundle {bundle_id}")
            print(f"ERROR: No interest found for buyer {buyer} in bundle {bundle_id}")  # Debug print
            return False
    except Exception as e:
        st.error(f"Error getting buyer interest: {e}")
        print(f"ERROR: {e}")  # Debug print
        return False
    
    # Check if Shapley value is set
    if interest.shapley_value <= 0:
        st.error(f"Shapley value not set for buyer {buyer}")
        print(f"ERROR: Shapley value not set for buyer {buyer}")  # Debug print
        return False
    
    # Check if buyer has enough balance
    if st.session_state.marketplace['users'][buyer]['balance'] < interest.shapley_value:
        st.error(f"Insufficient balance for buyer {buyer}")
        print(f"ERROR: Insufficient balance for buyer {buyer}")  # Debug print
        return False
    
    # Deduct from buyer's balance
    st.session_state.marketplace['users'][buyer]['balance'] -= interest.shapley_value
    print(f"BALANCE UPDATED: Buyer {buyer} new balance: ${st.session_state.marketplace['users'][buyer]['balance']:.2f}")  # Debug print
    
    # Complete purchase in SDK
    try:
        success = sdk.complete_bundle_purchase(bundle_id, buyer)
    except Exception as e:
        st.error(f"Error completing purchase: {e}")
        print(f"ERROR: {e}")  # Debug print
        return False
    
    if success:
        print(f"SUCCESS: Purchase completed for bundle {bundle_id} by buyer {buyer}")  # Debug print
        log_event("BuyerPaid", {
            'bundle_id': bundle_id,
            'buyer': buyer,
            'amount': interest.shapley_value
        })
        
        # Check if bundle is completed
        bundle = sdk.get_bundle(bundle_id)
        if bundle.completed:
            print(f"BUNDLE COMPLETED: Bundle {bundle_id} is now complete")  # Debug print
            # Update user's NFTs
            user_nfts = sdk.get_user_nfts(buyer)
            for nft in user_nfts:
                if nft.item_id in interest.items_of_interest:
                    st.session_state.marketplace['users'][buyer]['nfts'].append({
                        'item_id': nft.item_id,
                        'name': nft.name,
                        'image_url': nft.image_url or get_nft_image_url(nft.item_id)
                    })
                    print(f"NFT TRANSFERRED: Item {nft.item_id} transferred to {buyer}")  # Debug print
            
            log_event("BundlePurchased", {
                'bundle_id': bundle_id,
                'buyers': bundle.interested_buyers
            })
    else:
        print(f"FAILED: Purchase completion for bundle {bundle_id} by buyer {buyer}")  # Debug print
    
    return success

def request_attestation(bundle_id):
    """Request attestation for Shapley value calculation"""
    print(f"REQUESTING ATTESTATION: Bundle {bundle_id}")  # Debug print
    sdk = st.session_state.marketplace['sdk']
    if not sdk:
        st.error("SDK not initialized")
        print("ERROR: SDK not initialized")  # Debug print
        return False
    
    # In our SDK, this is equivalent to calculating Shapley values
    shapley_values = sdk.calculate_shapley_values(bundle_id)
    
    if shapley_values:
        print(f"ATTESTATION SUCCESSFUL: Shapley values calculated for bundle {bundle_id}")  # Debug print
        print(f"SHAPLEY VALUES: {shapley_values}")  # Debug print
        
        log_event("AttestationRequested", {
            'bundle_id': bundle_id
        })
        
        log_event("ShapleyValuesSet", {
            'bundle_id': bundle_id,
            'buyers': list(shapley_values.keys()),
            'values': list(shapley_values.values())
        })
        
        return True
    
    print(f"ATTESTATION FAILED: Could not calculate Shapley values for bundle {bundle_id}")  # Debug print
    return False

# Sidebar for user selection
st.sidebar.title("NFT Bundle Marketplace")

# Define user addresses with proper checksum format if SDK is available
if 'marketplace' in st.session_state and st.session_state.marketplace['sdk']:
    sdk = st.session_state.marketplace['sdk']
    user_options = list(st.session_state.marketplace['users'].keys())
else:
    # Fallback if SDK is not available
    user_options = [
        '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266',
        '0x70997970c51812dc3a010c7d01b50e0d17dc79c8',
        '0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc',
        '0x90f79bf6eb2c4f870365e785982e1f101e93b906',
        '0x15d34aaf54267db7d7c367839aaf71a00a2c6a65'
    ]

user = st.sidebar.selectbox(
    "Select User",
    user_options,
    format_func=get_user_friendly_name
)
print(f"USER SELECTED: {user} ({get_user_friendly_name(user)})")  # Debug print

# Display user balance
if user in st.session_state.marketplace['users']:
    user_balance = st.session_state.marketplace['users'][user]['balance']
    st.sidebar.write(f"Balance: ${user_balance:.2f}")
else:
    st.sidebar.error(f"User {user} not found in marketplace users")

# Display contract information
st.sidebar.subheader("Contract Information")
if st.session_state.marketplace['sdk'] and st.session_state.marketplace['sdk'].w3.is_connected():
    st.sidebar.success("✅ Connected to Ethereum node")
    st.sidebar.write(f"Chain ID: {st.session_state.marketplace['sdk'].w3.eth.chain_id}")
    st.sidebar.write(f"Marketplace Contract: {st.session_state.marketplace['contract_address']}")
    st.sidebar.write(f"NFT Contract: {st.session_state.marketplace['mock_nft_address']}")
else:
    st.sidebar.error("❌ Not connected to Ethereum node")
    if st.sidebar.button("Retry Connection"):
        st.rerun()

# Main content
st.title("NFT Bundle Marketplace with Shapley Value Pricing")
st.write("A marketplace for selling NFT bundles with fair pricing using Shapley values")

# Add a demo guide
with st.expander("📚 Demo Guide - How to Use This App", expanded=True):
    st.markdown("""
    ### Welcome to the NFT Bundle Marketplace Demo!
    
    This demo showcases how NFT bundles can be sold using Shapley value pricing for fair distribution of value.
    
    #### Demo Walkthrough:
    1. **As a Seller (default user)**: 
       - You already have 5 NFTs minted and 2 bundles created
       - Create a new bundle with the remaining NFT
    
    2. **As Buyers (Alice, Bob, Charlie)**:
       - Express interest in specific NFTs within bundles
       - Request attestation (Shapley value calculation)
       - Complete purchases based on calculated fair prices
    
    3. **Observe the Marketplace**:
       - See how bundles are completed when all required buyers pay
       - Check the event log to track all actions
       - View your NFT collection after purchases
    
    #### Try it yourself:
    - Switch between users using the sidebar
    - Create a bundle as the Seller
    - Express interest in bundles as Buyers
    - Complete the purchase flow
    
    This demonstrates a decentralized marketplace where bundle pricing is determined fairly based on buyer interest!
    """)

# Create tabs for different sections
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Available NFTs", "Bundles", "Create Bundle", "My NFTs", "Events"])

with tab1:
    st.header("Available NFTs")
    
    # Display available NFTs
    if st.session_state.marketplace['sdk']:
        nfts = st.session_state.marketplace['sdk'].get_all_nfts()
        available_nfts = [nft for nft in nfts if not nft.sold]
        
        if available_nfts:
            # Display in a grid
            cols = st.columns(3)
            for i, nft in enumerate(available_nfts):
                with cols[i % 3]:
                    st.image(nft.image_url or get_nft_image_url(nft.item_id), width=150)
                    st.write(f"**{nft.name}**")
                    st.write(f"Item ID: {nft.item_id}")
                    st.write(f"Seller: {get_user_friendly_name(nft.seller)}")
        else:
            st.info("No NFTs available for individual purchase. They might be in bundles!")
    else:
        st.error("SDK not initialized. Cannot display NFTs.")

with tab2:
    st.header("NFT Bundles")
    
    # Display active bundles
    if st.session_state.marketplace['sdk']:
        sdk = st.session_state.marketplace['sdk']
        print(f"DEBUG: SDK _bundles attribute exists: {hasattr(sdk, '_bundles')}")
        if hasattr(sdk, '_bundles'):
            print(f"DEBUG: SDK _bundles content: {sdk._bundles}")
        
        bundles = st.session_state.marketplace['sdk'].get_all_bundles()
        print(f"DEBUG: Found {len(bundles)} bundles in total")
        
        # Debug: Print all bundles
        for b in bundles:
            print(f"DEBUG: Bundle {b.bundle_id}: {b.name}, active={b.active}, completed={b.completed}")
            
        active_bundles = [bundle for bundle in bundles if bundle.active and not bundle.completed]
        completed_bundles = [bundle for bundle in bundles if bundle.completed]
        
        # Debug: Print filtered bundles
        print(f"DEBUG: Active bundles: {[b.bundle_id for b in active_bundles]}")
        print(f"DEBUG: Completed bundles: {[b.bundle_id for b in completed_bundles]}")
        
        print(f"DEBUG: Found {len(active_bundles)} active bundles")
        print(f"DEBUG: Found {len(completed_bundles)} completed bundles")
        
        if active_bundles:
            st.subheader("Active Bundles")
            for bundle in active_bundles:
                # Get NFT items in the bundle
                bundle_items = st.session_state.marketplace['sdk'].get_bundle_items(bundle.bundle_id)
                nft_names = [item.name for item in bundle_items if item]
                
                with st.expander(f"Bundle {bundle.bundle_id}: {bundle.name} - {bundle.price} ETH", expanded=True):
                    st.write(f"**Description:** {bundle.description}")
                    st.write(f"**Seller:** {get_user_friendly_name(bundle_items[0].seller if bundle_items else 'Unknown')}")
                    st.write(f"**Required Buyers:** {bundle.required_buyers}")
                    st.write(f"**Current Interested Buyers:** {len(bundle.interested_buyers)}")
                    
                    # Progress bar for bundle completion
                    progress = len(bundle.interested_buyers) / bundle.required_buyers
                    st.progress(min(progress, 1.0), text=f"Interest Progress: {len(bundle.interested_buyers)}/{bundle.required_buyers} buyers")
                    
                    # Display items in the bundle
                    st.subheader("Items in Bundle")
                    if bundle.item_ids:
                        item_cols = st.columns(len(bundle.item_ids))
                        for i, item_id in enumerate(bundle.item_ids):
                            item = st.session_state.marketplace['sdk'].get_nft(item_id)
                            if item:
                                with item_cols[i]:
                                    st.image(item.image_url or get_nft_image_url(item.item_id), width=100)
                                    st.write(f"**{item.name}**")
                                    st.write(f"Item ID: {item.item_id}")
                    
                    # Buyer section - Express Interest
                    if user != bundle_items[0].seller if bundle_items else None:
                        buyer_interest = st.session_state.marketplace['sdk'].get_buyer_interest(bundle.bundle_id, user)
                        
                        if not buyer_interest:
                            st.subheader("Express Interest")
                            
                            # Initialize session state for this bundle if not exists
                            bundle_key = f"selected_items_{bundle.bundle_id}"
                            if bundle_key not in st.session_state:
                                st.session_state[bundle_key] = []
                            
                            # Use a form to prevent reloading issues
                            with st.form(key=f"express_interest_form_{bundle.bundle_id}"):
                                # Multi-select for items - store in session state to prevent auto-rerun
                                selected_items = st.multiselect(
                                    "Select items you're interested in",
                                    options=bundle.item_ids,
                                    default=st.session_state[bundle_key],
                                    format_func=lambda x: f"{x}: {st.session_state.marketplace['sdk'].get_nft(x).name if st.session_state.marketplace['sdk'].get_nft(x) else 'Unknown'}"
                                )
                                
                                # Submit button
                                submit_interest = st.form_submit_button("Express Interest")
                            
                            # Handle form submission outside the form
                            if submit_interest:
                                if selected_items:
                                    print(f"BUTTON CLICKED: Express Interest for bundle {bundle.bundle_id}")  # Debug print
                                    # Update session state with selected items
                                    st.session_state[bundle_key] = selected_items
                                    success = express_interest(bundle.bundle_id, user, selected_items)
                                    if success:
                                        st.success("Interest expressed successfully!")
                                        # Clear the selection after successful submission
                                        st.session_state[bundle_key] = []
                                        st.rerun()
                                else:
                                    print(f"ERROR: No items selected for bundle {bundle.bundle_id}")  # Debug print
                                    st.error("Please select at least one item")
                        else:
                            st.info(f"You have expressed interest in {len(buyer_interest.items_of_interest)} items in this bundle")
                            
                            # Show which items the user is interested in
                            st.write("Your items of interest:")
                            if buyer_interest.items_of_interest:
                                interest_cols = st.columns(len(buyer_interest.items_of_interest))
                                for i, item_id in enumerate(buyer_interest.items_of_interest):
                                    item = st.session_state.marketplace['sdk'].get_nft(item_id)
                                    if item:
                                        with interest_cols[i]:
                                            st.image(item.image_url or get_nft_image_url(item.item_id), width=80)
                                            st.write(f"**{item.name}**")
                            else:
                                st.info("No specific items selected in your interest.")
                            
                            # If Shapley values are calculated, show payment option
                            if buyer_interest.shapley_value > 0:
                                st.write(f"Your Shapley value: {buyer_interest.shapley_value:.2f} ETH")
                                
                                if not buyer_interest.has_paid:
                                    if st.button("Pay Now", key=f"pay_{bundle.bundle_id}"):
                                        print(f"BUTTON CLICKED: Pay Now for bundle {bundle.bundle_id}")  # Debug print
                                        success = complete_purchase(bundle.bundle_id, user)
                                        if success:
                                            st.success("Payment successful!")
                                            st.rerun()
                                else:
                                    st.success("You have already paid for this bundle")
                    
                    # Show all interested buyers
                    if bundle.interested_buyers:
                        st.subheader("Interested Buyers")
                        interests = st.session_state.marketplace['sdk'].get_all_buyer_interests(bundle.bundle_id)
                        
                        # Create a table of buyers and their interests
                        interest_data = []
                        for interest in interests:
                            buyer_name = get_user_friendly_name(interest.buyer)
                            items = [st.session_state.marketplace['sdk'].get_nft(item_id).name 
                                    for item_id in interest.items_of_interest 
                                    if st.session_state.marketplace['sdk'].get_nft(item_id)]
                            shapley = f"{interest.shapley_value:.2f} ETH" if interest.shapley_value > 0 else "Not calculated"
                            status = "Paid" if interest.has_paid else "Not paid"
                            
                            interest_data.append({
                                "Buyer": buyer_name,
                                "Interested In": ", ".join(items),
                                "Shapley Value": shapley,
                                "Status": status
                            })
                        
                        if interest_data:
                            st.table(interest_data)
                    
                    # Attestation request button (for any user)
                    if len(bundle.interested_buyers) >= bundle.required_buyers:
                        # Check if Shapley values are already calculated
                        buyer_interests = st.session_state.marketplace['sdk'].get_buyer_interests(bundle.bundle_id)
                        shapley_values_calculated = any(interest.shapley_value > 0 for interest in buyer_interests)
                        
                        if not shapley_values_calculated:
                            st.subheader("Request Shapley Value Calculation")
                            st.write("The bundle has enough interested buyers. Request attestation to calculate fair prices.")
                            if st.button("Request Attestation", key=f"attest_{bundle.bundle_id}"):
                                print(f"BUTTON CLICKED: Request Attestation for bundle {bundle.bundle_id}")  # Debug print
                                success = request_attestation(bundle.bundle_id)
                                if success:
                                    st.success("Attestation requested successfully! Shapley values have been calculated.")
                                    st.rerun()
        else:
            st.info("No active bundles available.")
        
        # Display completed bundles
        if completed_bundles:
            st.subheader("Completed Bundles")
            for bundle in completed_bundles:
                with st.expander(f"Bundle {bundle.bundle_id}: {bundle.name} - {bundle.price} ETH (Completed)"):
                    st.write(f"**Description:** {bundle.description}")
                    st.write(f"**Required Buyers:** {bundle.required_buyers}")
                    st.write(f"**Buyers who paid:** {bundle.paid_count}")
                    
                    # Display items in the bundle
                    st.subheader("Items in Bundle")
                    bundle_items = st.session_state.marketplace['sdk'].get_bundle_items(bundle.bundle_id)
                    if bundle.item_ids:
                        item_cols = st.columns(len(bundle.item_ids))
                        for i, item_id in enumerate(bundle.item_ids):
                            item = st.session_state.marketplace['sdk'].get_nft(item_id)
                            if item:
                                with item_cols[i]:
                                    st.image(item.image_url or get_nft_image_url(item.item_id), width=100)
                                    st.write(f"**{item.name}**")
                                    st.write(f"Item ID: {item.item_id}")
                    else:
                        st.info("No items in this bundle.")
    else:
        st.error("SDK not initialized. Cannot display bundles.")

with tab3:
    st.header("Create Bundle")
    
    # Only show for seller
    if user.lower() == '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266'.lower():  # Seller address - case insensitive comparison
        # Get available NFTs for bundling
        if st.session_state.marketplace['sdk']:
            nfts = st.session_state.marketplace['sdk'].get_all_nfts()
            available_nfts = [nft for nft in nfts if not nft.sold]
            
            if available_nfts:
                st.write("Create a new bundle with your available NFTs")
                
                # Initialize session state for bundle creation
                if "create_bundle_items" not in st.session_state:
                    st.session_state.create_bundle_items = []
                
                # Form for bundle creation to prevent reloading issues
                with st.form(key="bundle_creation_form"):
                    # Select NFTs for the bundle
                    selected_items = st.multiselect(
                        "Select NFTs to include in the bundle",
                        options=[nft.item_id for nft in available_nfts],
                        default=st.session_state.create_bundle_items,
                        format_func=lambda x: f"{x}: {next((nft.name for nft in available_nfts if nft.item_id == x), 'Unknown')}"
                    )
                    
                    # Display selected NFTs
                    if selected_items:
                        st.subheader("Selected NFTs")
                        cols = st.columns(len(selected_items))
                        for i, item_id in enumerate(selected_items):
                            nft = next((nft for nft in available_nfts if nft.item_id == item_id), None)
                            if nft:
                                with cols[i]:
                                    st.image(nft.image_url or get_nft_image_url(nft.item_id), width=100)
                                    st.write(f"**{nft.name}**")
                    
                    # Bundle details
                    col1, col2 = st.columns(2)
                    with col1:
                        bundle_name = st.text_input("Bundle Name", value="My Awesome Bundle")
                        bundle_description = st.text_area("Bundle Description", value="A collection of unique digital art")
                    
                    with col2:
                        bundle_price = st.number_input("Bundle Price (ETH)", min_value=0.1, value=3.0, step=0.1)
                        # Set the default value for required buyers to match the number of selected NFTs
                        # with a minimum of 1 and maximum of 5
                        default_required = min(max(len(selected_items), 1), 5)
                        required_buyers = st.number_input(
                            "Required Buyers (recommended to match number of selected NFTs)",
                            min_value=1,
                            max_value=5,
                            value=default_required,
                            step=1
                        )
                    
                    # Create bundle button
                    submit_button = st.form_submit_button("Create Bundle")
                    
                # Handle form submission outside the form to avoid reloading issues
                if submit_button and selected_items:
                    # Store selected items in session state
                    st.session_state.create_bundle_items = selected_items
                    
                    # Call SDK to create bundle
                    if st.session_state.marketplace['sdk']:
                        try:
                            # Build transaction data
                            tx_data = st.session_state.marketplace['sdk'].create_bundle_with_metadata(
                                user,
                                selected_items,
                                bundle_price,
                                required_buyers,
                                bundle_name,
                                bundle_description
                            )
                            
                            # In a real app, this would be a transaction that gets signed and sent
                            # For this demo, we'll simulate a successful transaction by directly calling
                            # the SDK's internal methods to update its state
                            
                            # Get the next bundle ID (current count + 1)
                            bundle_count = len(st.session_state.marketplace['sdk'].get_all_bundles())
                            new_bundle_id = bundle_count + 1
                            
                            # Create a new Bundle object and add it to the SDK's internal state
                            new_bundle = Bundle(
                                bundle_id=new_bundle_id,
                                item_ids=selected_items,
                                price=bundle_price,
                                required_buyers=required_buyers,
                                active=True,
                                interested_buyers=[],
                                completed=False,
                                paid_count=0,
                                name=bundle_name,
                                description=bundle_description
                            )
                            
                            # Debug print the bundle object
                            print(f"DEBUG: New bundle object: {new_bundle}")
                            
                            # Add the bundle to the SDK's internal state
                            # This is a hack for the demo - in a real app, this would happen on-chain
                            if not hasattr(st.session_state.marketplace['sdk'], '_bundles'):
                                st.session_state.marketplace['sdk']._bundles = {}
                            
                            # Ensure bundle_id is an integer
                            new_bundle_id = int(new_bundle_id)
                            st.session_state.marketplace['sdk']._bundles[new_bundle_id] = new_bundle
                            
                            # Also store in session state for persistence between page refreshes
                            if 'custom_bundles' not in st.session_state.marketplace:
                                st.session_state.marketplace['custom_bundles'] = {}
                            st.session_state.marketplace['custom_bundles'][new_bundle_id] = new_bundle
                            
                            print(f"DEBUG: Created new bundle with ID {new_bundle_id}")
                            print(f"DEBUG: SDK now has {len(st.session_state.marketplace['sdk']._bundles)} bundles in _bundles")
                            print(f"DEBUG: Session state now has {len(st.session_state.marketplace['custom_bundles'])} bundles in custom_bundles")
                            print(f"DEBUG: Bundle active={new_bundle.active}, completed={new_bundle.completed}")
                            
                            # Mark the NFTs as sold (added to a bundle)
                            for item_id in selected_items:
                                nft = st.session_state.marketplace['sdk'].get_nft(item_id)
                                if nft:
                                    # Create a custom attribute to store NFTs if it doesn't exist
                                    if not hasattr(st.session_state.marketplace['sdk'], '_nfts'):
                                        st.session_state.marketplace['sdk']._nfts = {}
                                    
                                    # Update the NFT to mark it as sold
                                    nft.sold = True
                                    st.session_state.marketplace['sdk']._nfts[item_id] = nft
                                    
                                    # Also store in session state for persistence
                                    st.session_state.marketplace['custom_nfts'][int(item_id)] = nft
                            
                            # Log the event (in a real app, this would be a transaction)
                            log_event("BundleCreated", {
                                'bundle_id': new_bundle_id,
                                'seller': user,
                                'item_ids': selected_items,
                                'price': bundle_price,
                                'required_buyers': required_buyers,
                                'name': bundle_name,
                                'description': bundle_description
                            })
                            
                            st.success(f"Bundle '{bundle_name}' created successfully!")
                            st.session_state.create_bundle_items = []  # Clear selection
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating bundle: {e}")
                    else:
                        st.error("SDK not initialized. Cannot create bundle.")
            else:
                st.info("You don't have any available NFTs to create a bundle.")
    else:
        st.info("Only the seller can create bundles. Please switch to the seller account in the sidebar.")

with tab4:
    st.header("My NFTs")
    
    # Display user's NFTs
    if st.session_state.marketplace['sdk']:
        user_nfts = st.session_state.marketplace['sdk'].get_user_nfts(user)
        
        if user_nfts:
            st.write(f"You own {len(user_nfts)} NFTs")
            
            # Display in a grid
            cols = st.columns(3)
            for i, nft in enumerate(user_nfts):
                with cols[i % 3]:
                    st.image(nft.image_url or get_nft_image_url(nft.token_id), width=150)
                    st.write(f"**{nft.name}**")
                    st.write(f"Token ID: {nft.token_id}")
        else:
            st.info("You don't own any NFTs yet. Express interest in a bundle and complete a purchase to own NFTs!")
    else:
        st.error("SDK not initialized. Cannot display user NFTs.")

with tab5:
    st.header("Event Log")
    
    # Display events in reverse chronological order
    events = st.session_state.marketplace['events'][::-1]
    
    if events:
        for event in events:
            event_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['timestamp']))
            with st.expander(f"{event_time} - {event['type']}"):
                st.json(event['data'])
    else:
        st.info("No events recorded yet. Actions in the marketplace will be logged here.")

# Add a footer
st.markdown("---")
st.markdown("NFT Bundle Marketplace with Shapley Value Pricing - Demo Application") 