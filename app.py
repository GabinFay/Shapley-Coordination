import streamlit as st
import pandas as pd
import numpy as np
import time
import json
from shapley_calculator import ShapleyCalculator

# Set page config
st.set_page_config(
    page_title="NFT Bundle Marketplace",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'marketplace' not in st.session_state:
    # Mock data structures
    st.session_state.marketplace = {
        'nfts': {},  # item_id -> NFT details
        'bundles': {},  # bundle_id -> Bundle details
        'users': {
            '0xAlice': {'balance': 1000.0, 'nfts': []},
            '0xBob': {'balance': 1000.0, 'nfts': []},
            '0xCharlie': {'balance': 1000.0, 'nfts': []},
            '0xDave': {'balance': 1000.0, 'nfts': []}
        },
        'next_item_id': 1,
        'next_bundle_id': 1,
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
    return event

def list_nft(seller, name, image_url=None):
    """List an NFT in the marketplace"""
    item_id = st.session_state.marketplace['next_item_id']
    st.session_state.marketplace['next_item_id'] += 1
    
    st.session_state.marketplace['nfts'][item_id] = {
        'name': name,
        'image_url': image_url or f"https://picsum.photos/seed/{item_id}/200/200",
        'seller': seller,
        'sold': False
    }
    
    log_event("NFTListed", {
        'item_id': item_id,
        'name': name,
        'seller': seller
    })
    
    return item_id

def create_bundle(seller, item_ids, price, required_buyers):
    """Create a bundle of NFTs"""
    # Validate items
    for item_id in item_ids:
        if item_id not in st.session_state.marketplace['nfts']:
            st.error(f"Item {item_id} does not exist")
            return None
        
        if st.session_state.marketplace['nfts'][item_id]['seller'] != seller:
            st.error(f"Item {item_id} does not belong to seller {seller}")
            return None
        
        if st.session_state.marketplace['nfts'][item_id]['sold']:
            st.error(f"Item {item_id} is already sold")
            return None
    
    bundle_id = st.session_state.marketplace['next_bundle_id']
    st.session_state.marketplace['next_bundle_id'] += 1
    
    st.session_state.marketplace['bundles'][bundle_id] = {
        'item_ids': item_ids,
        'price': price,
        'required_buyers': required_buyers,
        'seller': seller,
        'active': True,
        'completed': False,
        'interested_buyers': {},  # address -> list of item_ids
        'payments': {},  # address -> amount
        'shapley_values': {}  # address -> amount
    }
    
    log_event("BundleCreated", {
        'bundle_id': bundle_id,
        'item_ids': item_ids,
        'price': price,
        'required_buyers': required_buyers,
        'seller': seller
    })
    
    return bundle_id

def express_interest(bundle_id, buyer, item_ids):
    """Express interest in a bundle"""
    if bundle_id not in st.session_state.marketplace['bundles']:
        st.error(f"Bundle {bundle_id} does not exist")
        return False
    
    bundle = st.session_state.marketplace['bundles'][bundle_id]
    
    if not bundle['active'] or bundle['completed']:
        st.error(f"Bundle {bundle_id} is not active or already completed")
        return False
    
    if buyer in bundle['interested_buyers']:
        st.error(f"Buyer {buyer} already expressed interest in bundle {bundle_id}")
        return False
    
    # Validate items of interest
    for item_id in item_ids:
        if item_id not in bundle['item_ids']:
            st.error(f"Item {item_id} is not in bundle {bundle_id}")
            return False
    
    bundle['interested_buyers'][buyer] = item_ids
    
    log_event("BuyerInterested", {
        'bundle_id': bundle_id,
        'buyer': buyer,
        'item_ids': item_ids
    })
    
    # Check if we have enough buyers
    if len(bundle['interested_buyers']) >= bundle['required_buyers']:
        log_event("BundleReadyForPurchase", {
            'bundle_id': bundle_id,
            'buyers': list(bundle['interested_buyers'].keys())
        })
        
        # Calculate Shapley values
        calculate_shapley_values(bundle_id)
    
    return True

def calculate_shapley_values(bundle_id):
    """Calculate Shapley values for a bundle"""
    bundle = st.session_state.marketplace['bundles'][bundle_id]
    
    # Initialize Shapley calculator with bundle price
    calculator = ShapleyCalculator(bundle['price'])
    
    # Calculate Shapley values
    shapley_values = calculator.calculate_values(bundle['interested_buyers'])
    bundle['shapley_values'] = shapley_values
    
    log_event("ShapleyValuesSet", {
        'bundle_id': bundle_id,
        'buyers': list(shapley_values.keys()),
        'values': list(shapley_values.values())
    })
    
    return shapley_values

def complete_purchase(bundle_id, buyer, amount):
    """Complete a purchase for a buyer"""
    if bundle_id not in st.session_state.marketplace['bundles']:
        st.error(f"Bundle {bundle_id} does not exist")
        return False
    
    bundle = st.session_state.marketplace['bundles'][bundle_id]
    
    if not bundle['active'] or bundle['completed']:
        st.error(f"Bundle {bundle_id} is not active or already completed")
        return False
    
    if buyer not in bundle['interested_buyers']:
        st.error(f"Buyer {buyer} is not interested in bundle {bundle_id}")
        return False
    
    if buyer not in bundle['shapley_values']:
        st.error(f"Shapley value not set for buyer {buyer}")
        return False
    
    shapley_value = bundle['shapley_values'][buyer]
    
    if amount < shapley_value:
        st.error(f"Insufficient payment: {amount} < {shapley_value}")
        return False
    
    # Deduct from buyer's balance
    if st.session_state.marketplace['users'][buyer]['balance'] < amount:
        st.error(f"Insufficient balance for buyer {buyer}")
        return False
    
    st.session_state.marketplace['users'][buyer]['balance'] -= amount
    
    # Record payment
    bundle['payments'][buyer] = amount
    
    # Check if all buyers have paid
    all_paid = True
    for interested_buyer in bundle['interested_buyers']:
        if interested_buyer not in bundle['payments']:
            all_paid = False
            break
    
    if all_paid:
        # Complete the bundle purchase
        bundle['completed'] = True
        bundle['active'] = False
        
        # Mark items as sold and transfer to buyers
        for interested_buyer, item_ids in bundle['interested_buyers'].items():
            for item_id in item_ids:
                if item_id in st.session_state.marketplace['nfts']:
                    st.session_state.marketplace['nfts'][item_id]['sold'] = True
                    
                    # Add NFT to buyer's collection
                    nft_info = st.session_state.marketplace['nfts'][item_id].copy()
                    st.session_state.marketplace['users'][interested_buyer]['nfts'].append({
                        'item_id': item_id,
                        'name': nft_info['name'],
                        'image_url': nft_info['image_url']
                    })
                    
                    # Pay the seller
                    seller = nft_info['seller']
                    payment = bundle['shapley_values'][interested_buyer]
                    st.session_state.marketplace['users'][seller]['balance'] += payment
        
        log_event("BundlePurchased", {
            'bundle_id': bundle_id,
            'buyers': list(bundle['interested_buyers'].keys())
        })
    
    return True

def request_attestation(bundle_id):
    """Request attestation for Shapley value calculation"""
    if bundle_id not in st.session_state.marketplace['bundles']:
        st.error(f"Bundle {bundle_id} does not exist")
        return False
    
    bundle = st.session_state.marketplace['bundles'][bundle_id]
    
    if not bundle['active'] or bundle['completed']:
        st.error(f"Bundle {bundle_id} is not active or already completed")
        return False
    
    if len(bundle['interested_buyers']) < bundle['required_buyers']:
        st.error(f"Not enough interested buyers for bundle {bundle_id}")
        return False
    
    log_event("AttestationRequested", {
        'bundle_id': bundle_id
    })
    
    # In a real implementation, this would trigger a request to the TEE
    # For this demo, we'll just recalculate the Shapley values
    calculate_shapley_values(bundle_id)
    
    return True

# Initialize demo data if needed
if 'demo_initialized' not in st.session_state:
    # Create some NFTs
    nft1 = list_nft('0xDave', 'Artwork A')
    nft2 = list_nft('0xDave', 'Artwork B')
    nft3 = list_nft('0xDave', 'Artwork C')
    
    # Create some bundles
    bundle1 = create_bundle('0xDave', [nft1, nft2], 150.0, 2)
    bundle2 = create_bundle('0xDave', [nft2, nft3], 160.0, 2)
    bundle3 = create_bundle('0xDave', [nft1, nft3], 170.0, 2)
    bundle4 = create_bundle('0xDave', [nft1, nft2, nft3], 200.0, 3)
    
    st.session_state.demo_initialized = True

# Sidebar for user selection
st.sidebar.title("NFT Bundle Marketplace")
user = st.sidebar.selectbox(
    "Select User",
    ['0xAlice', '0xBob', '0xCharlie', '0xDave']
)

# Display user balance
user_balance = st.session_state.marketplace['users'][user]['balance']
st.sidebar.write(f"Balance: ${user_balance:.2f}")

# Main content
st.title("NFT Bundle Marketplace with Shapley Value Pricing")
st.write("A marketplace for selling NFT bundles with fair pricing using Shapley values")

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Available NFTs", "Bundles", "My NFTs", "Events"])

with tab1:
    st.header("Available NFTs")
    
    # Display available NFTs
    available_nfts = []
    for item_id, nft in st.session_state.marketplace['nfts'].items():
        if not nft['sold']:
            available_nfts.append({
                'Item ID': item_id,
                'Name': nft['name'],
                'Seller': nft['seller'],
                'Image': nft['image_url']
            })
    
    if available_nfts:
        # Display in a grid
        cols = st.columns(3)
        for i, nft in enumerate(available_nfts):
            with cols[i % 3]:
                st.image(nft['Image'], width=150)
                st.write(f"**{nft['Name']}**")
                st.write(f"Item ID: {nft['Item ID']}")
                st.write(f"Seller: {nft['Seller']}")
    else:
        st.write("No NFTs available")
    
    # Seller section - List NFT
    if user == '0xDave':  # Only Dave can list NFTs in this demo
        st.subheader("List a New NFT")
        with st.form("list_nft_form"):
            nft_name = st.text_input("NFT Name")
            image_url = st.text_input("Image URL (optional)")
            
            submit_button = st.form_submit_button("List NFT")
            if submit_button and nft_name:
                item_id = list_nft(user, nft_name, image_url)
                st.success(f"NFT listed successfully! Item ID: {item_id}")
                st.rerun()

with tab2:
    st.header("NFT Bundles")
    
    # Display active bundles
    active_bundles = []
    for bundle_id, bundle in st.session_state.marketplace['bundles'].items():
        if bundle['active'] and not bundle['completed']:
            # Get NFT names
            nft_names = []
            for item_id in bundle['item_ids']:
                if item_id in st.session_state.marketplace['nfts']:
                    nft_names.append(st.session_state.marketplace['nfts'][item_id]['name'])
            
            active_bundles.append({
                'Bundle ID': bundle_id,
                'Items': ', '.join(nft_names),
                'Item IDs': bundle['item_ids'],
                'Price': bundle['price'],
                'Required Buyers': bundle['required_buyers'],
                'Current Buyers': len(bundle['interested_buyers']),
                'Seller': bundle['seller']
            })
    
    if active_bundles:
        for bundle in active_bundles:
            with st.expander(f"Bundle {bundle['Bundle ID']}: {bundle['Items']} - ${bundle['Price']}"):
                st.write(f"Seller: {bundle['Seller']}")
                st.write(f"Required Buyers: {bundle['Required Buyers']}")
                st.write(f"Current Interested Buyers: {bundle['Current Buyers']}")
                
                # Display items in the bundle
                st.subheader("Items in Bundle")
                item_cols = st.columns(len(bundle['Item IDs']))
                for i, item_id in enumerate(bundle['Item IDs']):
                    if item_id in st.session_state.marketplace['nfts']:
                        nft = st.session_state.marketplace['nfts'][item_id]
                        with item_cols[i]:
                            st.image(nft['image_url'], width=100)
                            st.write(f"**{nft['name']}**")
                            st.write(f"Item ID: {item_id}")
                
                # Buyer section - Express Interest
                if user != bundle['Seller']:
                    bundle_data = st.session_state.marketplace['bundles'][bundle['Bundle ID']]
                    
                    if user not in bundle_data['interested_buyers']:
                        st.subheader("Express Interest")
                        
                        # Multi-select for items
                        selected_items = st.multiselect(
                            "Select items you're interested in",
                            options=bundle['Item IDs'],
                            format_func=lambda x: f"{x}: {st.session_state.marketplace['nfts'][x]['name']}"
                        )
                        
                        if st.button("Express Interest", key=f"express_{bundle['Bundle ID']}"):
                            if selected_items:
                                success = express_interest(bundle['Bundle ID'], user, selected_items)
                                if success:
                                    st.success("Interest expressed successfully!")
                                    st.rerun()
                            else:
                                st.error("Please select at least one item")
                    else:
                        st.info("You have already expressed interest in this bundle")
                        
                        # If Shapley values are calculated, show payment option
                        if user in bundle_data.get('shapley_values', {}):
                            shapley_value = bundle_data['shapley_values'][user]
                            st.write(f"Your Shapley value: ${shapley_value:.2f}")
                            
                            if user not in bundle_data.get('payments', {}):
                                if st.button("Pay Now", key=f"pay_{bundle['Bundle ID']}"):
                                    success = complete_purchase(bundle['Bundle ID'], user, shapley_value)
                                    if success:
                                        st.success("Payment successful!")
                                        st.rerun()
                            else:
                                st.success("You have already paid for this bundle")
                
                # Attestation request button (for any user)
                if bundle['Current Buyers'] >= bundle['Required Buyers']:
                    bundle_data = st.session_state.marketplace['bundles'][bundle['Bundle ID']]
                    if not bundle_data.get('shapley_values'):
                        if st.button("Request Attestation", key=f"attest_{bundle['Bundle ID']}"):
                            success = request_attestation(bundle['Bundle ID'])
                            if success:
                                st.success("Attestation requested successfully!")
                                st.rerun()
    else:
        st.write("No active bundles")
    
    # Seller section - Create Bundle
    if user == '0xDave':  # Only Dave can create bundles in this demo
        st.subheader("Create a New Bundle")
        
        # Get available NFTs for this seller
        seller_nfts = []
        for item_id, nft in st.session_state.marketplace['nfts'].items():
            if not nft['sold'] and nft['seller'] == user:
                seller_nfts.append((item_id, nft['name']))
        
        if seller_nfts:
            with st.form("create_bundle_form"):
                selected_nfts = st.multiselect(
                    "Select NFTs for the bundle",
                    options=[item_id for item_id, _ in seller_nfts],
                    format_func=lambda x: f"{x}: {next((name for id, name in seller_nfts if id == x), '')}"
                )
                
                bundle_price = st.number_input("Bundle Price ($)", min_value=0.01, value=100.0, step=10.0)
                required_buyers = st.number_input("Required Buyers", min_value=1, value=2, step=1)
                
                submit_button = st.form_submit_button("Create Bundle")
                if submit_button:
                    if selected_nfts:
                        if required_buyers <= len(selected_nfts):
                            bundle_id = create_bundle(user, selected_nfts, bundle_price, required_buyers)
                            if bundle_id:
                                st.success(f"Bundle created successfully! Bundle ID: {bundle_id}")
                                st.rerun()
                        else:
                            st.error("Required buyers cannot exceed the number of NFTs in the bundle")
                    else:
                        st.error("Please select at least one NFT")
        else:
            st.write("You don't have any NFTs to bundle")

with tab3:
    st.header("My NFTs")
    
    # Display user's NFTs
    user_nfts = st.session_state.marketplace['users'][user]['nfts']
    
    if user_nfts:
        # Display in a grid
        cols = st.columns(3)
        for i, nft in enumerate(user_nfts):
            with cols[i % 3]:
                st.image(nft['image_url'], width=150)
                st.write(f"**{nft['name']}**")
                st.write(f"Item ID: {nft['item_id']}")
    else:
        st.write("You don't own any NFTs")

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
st.markdown("NFT Bundle Marketplace with Shapley Value Pricing - Proof of Concept") 