import json
import os
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    print("Testing connection to Anvil...")
    
    # Connect to local Anvil instance
    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
    
    # Check connection
    if w3.is_connected():
        print("✅ Successfully connected to Anvil!")
        print(f"Chain ID: {w3.eth.chain_id}")
        
        # Get some basic info
        block_number = w3.eth.block_number
        print(f"Current block number: {block_number}")
        
        # Get accounts
        accounts = w3.eth.accounts
        print(f"Available accounts: {len(accounts)}")
        for i, account in enumerate(accounts[:5]):  # Show first 5 accounts
            balance = w3.eth.get_balance(account)
            print(f"  Account {i}: {account} - Balance: {w3.from_wei(balance, 'ether')} ETH")
        
        # Get contract addresses from environment variables
        marketplace_address = os.getenv("MARKETPLACE_ADDRESS")
        nft_address = os.getenv("MOCK_NFT_ADDRESS")
        
        print(f"Marketplace contract address: {marketplace_address}")
        print(f"NFT contract address: {nft_address}")
        
        # Try to load contract ABIs
        try:
            with open("thefoundry/out/NFTBundleMarket.sol/NFTBundleMarket.json", 'r') as f:
                contract_json = json.load(f)
                print("✅ Successfully loaded marketplace contract ABI")
        except Exception as e:
            print(f"❌ Failed to load marketplace contract ABI: {e}")
        
        try:
            with open("thefoundry/out/MockERC721.sol/MockERC721.json", 'r') as f:
                nft_json = json.load(f)
                print("✅ Successfully loaded NFT contract ABI")
        except Exception as e:
            print(f"❌ Failed to load NFT contract ABI: {e}")
        
        # Try to instantiate contracts
        if marketplace_address:
            try:
                contract = w3.eth.contract(address=marketplace_address, abi=contract_json['abi'])
                print("✅ Successfully instantiated marketplace contract")
            except Exception as e:
                print(f"❌ Failed to instantiate marketplace contract: {e}")
        
        if nft_address:
            try:
                nft_contract = w3.eth.contract(address=nft_address, abi=nft_json['abi'])
                print("✅ Successfully instantiated NFT contract")
            except Exception as e:
                print(f"❌ Failed to instantiate NFT contract: {e}")
    else:
        print("❌ Failed to connect to Anvil")
        print("Make sure Anvil is running on port 8545")

if __name__ == "__main__":
    test_connection() 