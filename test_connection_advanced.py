import json
import os
import requests
import socket
import time
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_port_open(host, port):
    """Check if a port is open using a socket connection"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)  # 2 second timeout
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

def test_http_request():
    """Test a direct HTTP request to the Anvil node"""
    try:
        response = requests.post(
            "http://localhost:8545",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ HTTP request successful: {result}")
            return True
        else:
            print(f"❌ HTTP request failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ HTTP request exception: {e}")
        return False

def test_web3_connection():
    """Test Web3 connection with different providers"""
    # Test with HTTPProvider
    print("\nTesting Web3 HTTPProvider...")
    w3_http = Web3(Web3.HTTPProvider("http://localhost:8545"))
    
    try:
        if w3_http.is_connected():
            print("✅ Connected with HTTPProvider")
            print(f"Chain ID: {w3_http.eth.chain_id}")
            print(f"Block number: {w3_http.eth.block_number}")
            return w3_http
        else:
            print("❌ Failed to connect with HTTPProvider")
    except Exception as e:
        print(f"❌ HTTPProvider exception: {e}")
    
    # Test with WebsocketProvider
    print("\nTesting Web3 WebsocketProvider...")
    try:
        w3_ws = Web3(Web3.WebsocketProvider("ws://localhost:8545"))
        if w3_ws.is_connected():
            print("✅ Connected with WebsocketProvider")
            print(f"Chain ID: {w3_ws.eth.chain_id}")
            return w3_ws
        else:
            print("❌ Failed to connect with WebsocketProvider")
    except Exception as e:
        print(f"❌ WebsocketProvider exception: {e}")
    
    # Test with IPCProvider (if on Unix)
    if os.name == 'posix':
        print("\nTesting Web3 IPCProvider...")
        try:
            ipc_path = "/tmp/anvil.ipc"  # This path might be different
            w3_ipc = Web3(Web3.IPCProvider(ipc_path))
            if w3_ipc.is_connected():
                print("✅ Connected with IPCProvider")
                return w3_ipc
            else:
                print("❌ Failed to connect with IPCProvider")
        except Exception as e:
            print(f"❌ IPCProvider exception: {e}")
    
    return None

def main():
    print("Advanced Anvil Connection Test")
    print("=============================")
    
    # Check if port 8545 is open
    print("\nChecking if port 8545 is open...")
    if check_port_open("localhost", 8545):
        print("✅ Port 8545 is open")
    else:
        print("❌ Port 8545 is closed")
    
    # Test direct HTTP request
    print("\nTesting direct HTTP request...")
    http_success = test_http_request()
    
    # Test Web3 connection
    w3 = test_web3_connection()
    
    if w3:
        # Get contract addresses from environment variables
        marketplace_address = os.getenv("MARKETPLACE_ADDRESS")
        nft_address = os.getenv("MOCK_NFT_ADDRESS")
        
        print(f"\nMarketplace contract address: {marketplace_address}")
        print(f"NFT contract address: {nft_address}")
        
        # Try to load contract ABIs
        try:
            with open("thefoundry/out/NFTBundleMarket.sol/NFTBundleMarket.json", 'r') as f:
                contract_json = json.load(f)
                print("✅ Successfully loaded marketplace contract ABI")
        except Exception as e:
            print(f"❌ Failed to load marketplace contract ABI: {e}")
            return
        
        try:
            with open("thefoundry/out/MockERC721.sol/MockERC721.json", 'r') as f:
                nft_json = json.load(f)
                print("✅ Successfully loaded NFT contract ABI")
        except Exception as e:
            print(f"❌ Failed to load NFT contract ABI: {e}")
            return
        
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
        print("\n❌ All Web3 connection methods failed")
        
        # Suggest solutions
        print("\nPossible solutions:")
        print("1. Check if Anvil is configured to accept external connections")
        print("2. Try restarting Anvil with: anvil --host 0.0.0.0 --port 8545")
        print("3. Check for firewall or security settings blocking connections")
        print("4. Try using a different port")
        print("5. Check if there's another service using port 8545")

if __name__ == "__main__":
    main() 