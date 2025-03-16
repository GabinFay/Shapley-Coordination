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
        
        # If environment variables are not set, try to load from simulation data
        if not contract_address or not mock_nft_address:
            try:
                with open("sepolia_simulation_data.json", "r") as f:
                    simulation_data = json.load(f)
                    contract_address = simulation_data.get("marketplace_address")
                    mock_nft_address = simulation_data.get("nft_address")
            except Exception as e:
                st.error(f"Failed to load simulation data: {e}")
        
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
        st.session_state.marketplace = {
            'sdk': sdk,
            'contract_address': contract_address,
            'mock_nft_address': mock_nft_address,
            'users': {
                '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266': {'balance': 1000.0, 'nfts': []},  # Seller/Owner
                '0x70997970c51812dc3a010c7d01b50e0d17dc79c8': {'balance': 1000.0, 'nfts': []},  # Alice
                '0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc': {'balance': 1000.0, 'nfts': []},  # Bob
                '0x90f79bf6eb2c4f870365e785982e1f101e93b906': {'balance': 1000.0, 'nfts': []},  # Charlie
                '0x15d34aaf54267db7d7c367839aaf71a00a2c6a65': {'balance': 1000.0, 'nfts': []}   # Dave
            },
            'events': []
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
            'events': []
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

def get_user_friendly_name(address):
    """Convert Ethereum address to a user-friendly name"""
    address_map = {
        '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266': 'Seller',
        '0x70997970c51812dc3a010c7d01b50e0d17dc79c8': 'Alice',
        '0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc': 'Bob',
        '0x90f79bf6eb2c4f870365e785982e1f101e93b906': 'Charlie',
        '0x15d34aaf54267db7d7c367839aaf71a00a2c6a65': 'Dave'
    }
    return address_map.get(address.lower(), address[:6] + '...' + address[-4:])

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
    
    success = sdk.express_interest(bundle_id, buyer, item_ids)
    
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
    interest = sdk.get_buyer_interest(bundle_id, buyer)
    if not interest:
        st.error(f"No interest found for buyer {buyer} in bundle {bundle_id}")
        print(f"ERROR: No interest found for buyer {buyer} in bundle {bundle_id}")  # Debug print
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
    success = sdk.complete_bundle_purchase(bundle_id, buyer)
    
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
user = st.sidebar.selectbox(
    "Select User",
    ['0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266', 
     '0x70997970c51812dc3a010c7d01b50e0d17dc79c8', 
     '0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc', 
     '0x15d34aaf54267db7d7c367839aaf71a00a2c6a65',
     '0x90f79bf6eb2c4f870365e785982e1f101e93b906'],
    format_func=get_user_friendly_name
)
print(f"USER SELECTED: {user} ({get_user_friendly_name(user)})")  # Debug print

# Display user balance
user_balance = st.session_state.marketplace['users'][user]['balance']
st.sidebar.write(f"Balance: ${user_balance:.2f}")

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

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Available NFTs", "Bundles", "My NFTs", "Events"])

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
            st.write("No NFTs available")
    else:
        st.error("SDK not initialized. Cannot display NFTs.")

with tab2:
    st.header("NFT Bundles")
    
    # Display active bundles
    if st.session_state.marketplace['sdk']:
        bundles = st.session_state.marketplace['sdk'].get_all_bundles()
        active_bundles = [bundle for bundle in bundles if bundle.active and not bundle.completed]
        
        if active_bundles:
            for bundle in active_bundles:
                # Get NFT items in the bundle
                bundle_items = st.session_state.marketplace['sdk'].get_bundle_items(bundle.bundle_id)
                nft_names = [item.name for item in bundle_items if item]
                
                with st.expander(f"Bundle {bundle.bundle_id}: {bundle.name} - ${bundle.price}"):
                    st.write(f"Seller: {get_user_friendly_name(bundle_items[0].seller if bundle_items else 'Unknown')}")
                    st.write(f"Required Buyers: {bundle.required_buyers}")
                    st.write(f"Current Interested Buyers: {len(bundle.interested_buyers)}")
                    
                    # Display items in the bundle
                    st.subheader("Items in Bundle")
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
                            
                            # Multi-select for items - store in session state to prevent auto-rerun
                            selected_items = st.multiselect(
                                "Select items you're interested in",
                                options=bundle.item_ids,
                                default=st.session_state[bundle_key],
                                format_func=lambda x: f"{x}: {st.session_state.marketplace['sdk'].get_nft(x).name if st.session_state.marketplace['sdk'].get_nft(x) else 'Unknown'}"
                            )
                            # Update session state with selected items
                            st.session_state[bundle_key] = selected_items
                            
                            if st.button("Express Interest", key=f"express_{bundle.bundle_id}"):
                                if selected_items:
                                    print(f"BUTTON CLICKED: Express Interest for bundle {bundle.bundle_id}")  # Debug print
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
                            st.info("You have already expressed interest in this bundle")
                            
                            # If Shapley values are calculated, show payment option
                            if buyer_interest.shapley_value > 0:
                                st.write(f"Your Shapley value: ${buyer_interest.shapley_value:.2f}")
                                
                                if not buyer_interest.has_paid:
                                    if st.button("Pay Now", key=f"pay_{bundle.bundle_id}"):
                                        print(f"BUTTON CLICKED: Pay Now for bundle {bundle.bundle_id}")  # Debug print
                                        success = complete_purchase(bundle.bundle_id, user)
                                        if success:
                                            st.success("Payment successful!")
                                            st.rerun()
                                else:
                                    st.success("You have already paid for this bundle")
                    
                    # Attestation request button (for any user)
                    if len(bundle.interested_buyers) >= bundle.required_buyers:
                        # Check if Shapley values are already calculated
                        buyer_interests = st.session_state.marketplace['sdk'].get_buyer_interests(bundle.bundle_id)
                        shapley_values_calculated = any(interest.shapley_value > 0 for interest in buyer_interests)
                        
                        if not shapley_values_calculated:
                            if st.button("Request Attestation", key=f"attest_{bundle.bundle_id}"):
                                print(f"BUTTON CLICKED: Request Attestation for bundle {bundle.bundle_id}")  # Debug print
                                success = request_attestation(bundle.bundle_id)
                                if success:
                                    st.success("Attestation requested successfully!")
                                    st.rerun()
        else:
            st.write("No active bundles")
    else:
        st.error("SDK not initialized. Cannot display bundles.")

with tab3:
    st.header("My NFTs")
    
    # Display user's NFTs
    if st.session_state.marketplace['sdk']:
        user_nfts = st.session_state.marketplace['sdk'].get_user_nfts(user)
        
        if user_nfts:
            # Display in a grid
            cols = st.columns(3)
            for i, nft in enumerate(user_nfts):
                with cols[i % 3]:
                    st.image(nft.image_url or get_nft_image_url(nft.item_id), width=150)
                    st.write(f"**{nft.name}**")
                    st.write(f"Item ID: {nft.item_id}")
        else:
            st.write("You don't own any NFTs")
    else:
        st.error("SDK not initialized. Cannot display user NFTs.")

with tab4:
    st.header("Event Log")
    
    # Display events in reverse chronological order
    events = st.session_state.marketplace['events'][::-1]
    
    if events:
        for event in events:
            event_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['timestamp']))
            with st.expander(f"{event_time} - {event['type']}"):
                st.json(event['data'])
    else:
        st.write("No events recorded")

# Add a footer
st.markdown("---")
st.markdown("NFT Bundle Marketplace with Shapley Value Pricing - Sepolia Testnet Demo") 