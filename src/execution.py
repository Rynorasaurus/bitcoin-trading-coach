import os
import sys
import time
import hashlib
import hmac
import base64
import urllib.parse
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Kraken API Base URLs
KRAKEN_PROD_URL = "https://api.kraken.com"
KRAKEN_SANDBOX_URL = "https://demo-api.kraken.com"

def get_kraken_signature(urlpath, data, secret):
    """Generates the signature required by Kraken private API endpoints."""
    try:
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    except Exception as e:
        print(f"Error generating API signature: {e}", file=sys.stderr)
        return None

def execute_trade(pair, direction, order_type, volume, price=None, confirm=False):
    """Executes a trade on Kraken (Sandbox or Prod) with strict confirmation checks."""
    print("Execution Agent: Received order request...")
    
    # 1. Gatekeeper Check: Manual Confirmation
    if not confirm:
        print("Execution Agent ERROR: Trade rejected. Manual confirmation is REQUIRED but was not provided.", file=sys.stderr)
        return {"status": "REJECTED", "error": "No manual confirmation provided."}
        
    # 2. Determine Environment and load Keys
    env_mode = os.getenv("ENVIRONMENT", "sandbox").lower()
    
    if env_mode == "production":
        api_key = os.getenv("KRAKEN_PROD_API_KEY")
        api_secret = os.getenv("KRAKEN_PROD_API_SECRET")
        base_url = KRAKEN_PROD_URL
        print("Execution Agent WARNING: Running in PRODUCTION mode (REAL FUNDS)!")
    else:
        env_mode = "sandbox"
        api_key = os.getenv("KRAKEN_SANDBOX_API_KEY")
        api_secret = os.getenv("KRAKEN_SANDBOX_API_SECRET")
        base_url = KRAKEN_SANDBOX_URL
        print("Execution Agent: Running in SANDBOX mode (Mock trading).")

    # 3. Security Check: API Key Validation
    is_placeholder = (
        not api_key or not api_secret or 
        "your_kraken_" in api_key or "your_kraken_" in api_secret or 
        api_key == "" or api_secret == ""
    )
    
    if is_placeholder:
        print("Execution Agent: API credentials are missing or default placeholders.")
        print(f"Execution Agent: [SIMULATION MODE ACTIVE] Simulating {direction} order for {volume} {pair}...")
        time.sleep(1) # Simulate network delay
        mock_tx_id = f"MOCK-TX-{int(time.time())}"
        print(f"Execution Agent: Order simulated successfully. TxID: {mock_tx_id}")
        return {
            "status": "SUCCESS (SIMULATION)",
            "txid": mock_tx_id,
            "pair": pair,
            "direction": direction,
            "volume": volume,
            "price": price,
            "environment": env_mode
        }

    # 4. Make Live API Call to Kraken
    urlpath = "/0/private/AddOrder"
    nonce = int(time.time() * 1000)
    
    data = {
        "nonce": nonce,
        "pair": pair,
        "type": direction.lower(), # 'buy' or 'sell'
        "ordertype": order_type.lower(), # 'limit' or 'market'
        "volume": str(volume),
    }
    
    if price:
        data["price"] = str(price)
        
    headers = {
        "API-Key": api_key,
        "API-Sign": get_kraken_signature(urlpath, data, api_secret)
    }
    
    try:
        response = requests.post(base_url + urlpath, headers=headers, data=data, timeout=10)
        res_json = response.json()
        
        if "error" in res_json and res_json["error"]:
            err_msg = ", ".join(res_json["error"])
            print(f"Execution Agent ERROR: Kraken API returned error: {err_msg}", file=sys.stderr)
            return {"status": "FAILED", "error": err_msg}
            
        txid = res_json.get("result", {}).get("txid", ["UNKNOWN"])[0]
        print(f"Execution Agent: Order successfully placed! TxID: {txid}")
        return {
            "status": "SUCCESS",
            "txid": txid,
            "pair": pair,
            "direction": direction,
            "volume": volume,
            "price": price,
            "environment": env_mode
        }
    except Exception as e:
        print(f"Execution Agent ERROR: Network or API failure: {e}", file=sys.stderr)
        return {"status": "FAILED", "error": str(e)}

if __name__ == "__main__":
    # Test 1: Try running without confirmation (should fail)
    print("--- Test 1: No Confirmation ---")
    execute_trade("XBTUSD", "buy", "limit", 0.01, price=50000, confirm=False)
    
    # Test 2: Try running with confirmation (should succeed in simulation mode)
    print("\n--- Test 2: With Confirmation ---")
    execute_trade("XBTUSD", "buy", "limit", 0.01, price=50000, confirm=True)
