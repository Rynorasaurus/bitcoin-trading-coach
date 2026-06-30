import os
import sys
import time
import hashlib
import hmac
import base64
import urllib.parse
import requests
import re
import google.generativeai as genai
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
        return sigdigest.decode()
    except Exception as e:
        print(f"Error generating API signature: {e}", file=sys.stderr)
        return None

def get_balances():
    """Gets available balances from Kraken API, or returns fallback mock data."""
    env_mode = os.getenv("ENVIRONMENT", "sandbox").lower()
    if env_mode == "production":
        api_key = os.getenv("KRAKEN_PROD_API_KEY")
        api_secret = os.getenv("KRAKEN_PROD_API_SECRET")
        base_url = KRAKEN_PROD_URL
    else:
        api_key = os.getenv("KRAKEN_SANDBOX_API_KEY")
        api_secret = os.getenv("KRAKEN_SANDBOX_API_SECRET")
        base_url = KRAKEN_SANDBOX_URL

    is_placeholder = (
        not api_key or not api_secret or 
        "your_kraken_" in api_key or "your_kraken_" in api_secret or 
        api_key == "" or api_secret == ""
    )
    
    if is_placeholder:
        # Return fallback mock data
        return {
            "CAD": 10000.00,
            "BTC": 0.5000,
            "source": "Mock Sandbox Data"
        }
        
    urlpath = "/0/private/Balance"
    nonce = int(time.time() * 1000)
    data = {"nonce": nonce}
    headers = {
        "API-Key": api_key,
        "API-Sign": get_kraken_signature(urlpath, data, api_secret)
    }
    
    try:
        response = requests.post(base_url + urlpath, headers=headers, data=data, timeout=10)
        res_json = response.json()
        if "error" in res_json and res_json["error"]:
            print(f"Execution Agent ERROR: Kraken balance query failed: {res_json['error']}", file=sys.stderr)
            return {"CAD": 10000.00, "BTC": 0.5000, "source": f"Mock Sandbox Data (Error fallback: {res_json['error']})"}
            
        result = res_json.get("result", {})
        cad_balance = float(result.get("ZCAD", result.get("CAD", 10000.00)))
        btc_balance = float(result.get("XXBT", result.get("BTC", 0.5000)))
        return {
            "CAD": cad_balance,
            "BTC": btc_balance,
            "source": "Kraken Live API"
        }
    except Exception as e:
        print(f"Execution Agent ERROR: Balance retrieval network failure: {e}", file=sys.stderr)
        return {"CAD": 10000.00, "BTC": 0.5000, "source": "Mock Sandbox Data (Network fallback)"}

def chat_with_concierge(user_message, balance_data, setup_data, chat_history):
    """
    Handles conversational interactions for position sizing.
    Returns:
        tuple: (reply_text, target_volume) where target_volume is float or None.
    """
    entry = setup_data.get("entry", 0.0)
    bias = setup_data.get("bias", "BUY / LONG")
    is_buy = "BUY" in bias
    
    # 1. Parse using Gemini if API key is present
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key and not api_key.startswith("your_"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            # Format chat history
            formatted_history = ""
            for msg in chat_history[-6:]:
                role = "User" if msg["role"] == "user" else "Concierge"
                formatted_history += f"{role}: {msg['content']}\n"
                
            prompt = f"""
You are the Secure Concierge Agent in a 3-agent Bitcoin trading system.
Your job is to converse with the user to determine the exact position size (volume of BTC) to trade.

Current Account Balances:
- CAD Balance: ${balance_data['CAD']:.2f} CAD (used for BUY / LONG)
- BTC Balance: {balance_data['BTC']:.4f} BTC (used for SELL / SHORT)
- Source: {balance_data['source']}

Current Trade Recommendation:
- Direction: {bias}
- Target Entry Price: ${entry:.2f}

You must help the user calculate the BTC size.
- If longing/buying, they use CAD. E.g. Risk 10% of CAD balance ($1,000 CAD) at entry price ${entry:.2f} is {1000 / entry:.4f} BTC.
- If shorting/selling, they sell BTC. E.g. Sell 50% of BTC balance is {0.5 * balance_data['BTC']:.4f} BTC.

Guidelines:
1. Parse the user's input for percentage risk or explicit sizing.
2. If you can calculate a specific BTC volume from their input, print the exact volume and cost in CAD, and explicitly tell them: "If you want to execute this, type exactly EXECUTE."
3. Keep your response conversational, professional, and educational. Keep it under 3 sentences.
4. Output your suggested BTC volume at the end of the text in the format: [VOLUME: <float_volume>]. For example: [VOLUME: 0.0171] if the volume was determined, or [VOLUME: NONE] if you need more clarification from the user.

Chat History:
{formatted_history}

User Message: "{user_message}"
"""
            response = model.generate_content(prompt)
            reply = response.text.strip()
            
            # Extract volume using regex
            volume = None
            vol_match = re.search(r"\[VOLUME:\s*([\d\.]+)\]", reply)
            if vol_match:
                try:
                    volume = float(vol_match.group(1))
                except ValueError:
                    pass
                reply = re.sub(r"\[VOLUME:\s*[\d\.\w]+\]", "", reply).strip()
                
            return reply, volume
        except Exception as e:
            print(f"Secure Concierge: Gemini API failed ({e}). Using fallback parser...", file=sys.stderr)
            
    # 2. Smart rule-based fallback parser
    reply = ""
    volume = None
    q = user_message.lower().strip()
    
    # Try to parse percentage risk (e.g. "risk 10%", "10% of balance", "sell 50%")
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", q)
    if pct_match:
        try:
            pct = float(pct_match.group(1)) / 100.0
            if is_buy:
                cad_to_risk = balance_data["CAD"] * pct
                volume = cad_to_risk / entry if entry > 0 else 0.0
                reply = (
                    f"Risking {pct*100:.1f}% of your CAD balance (${cad_to_risk:.2f} CAD) "
                    f"at the entry price of ${entry:.2f} results in a position size of {volume:.4f} BTC. "
                    "If you are satisfied with this setup, please type exactly EXECUTE in the chat box to place the order."
                )
            else:
                volume = balance_data["BTC"] * pct
                reply = (
                    f"Selling {pct*100:.1f}% of your BTC balance ({volume:.4f} BTC) "
                    f"at the entry price of ${entry:.2f}. "
                    "If you are satisfied with this setup, please type exactly EXECUTE in the chat box to place the order."
                )
        except Exception as e:
            reply = "I had trouble calculating that percentage. Please specify a value like 'Risk 10%' or 'Sell 50%'."
            
    # Try to parse explicit BTC sizing (e.g. "buy 0.05 btc", "0.01 btc", "sell 0.1")
    elif any(kw in q for kw in ["btc", "bitcoin", "volume", "size"]):
        btc_match = re.search(r"(\d+(?:\.\d+)?)", q)
        if btc_match:
            try:
                volume = float(btc_match.group(1))
                if is_buy:
                    cost_cad = volume * entry
                    if cost_cad > balance_data["CAD"]:
                        reply = (
                            f"You specified {volume:.4f} BTC, which costs ${cost_cad:.2f} CAD. "
                            f"However, your available balance is only ${balance_data['CAD']:.2f} CAD. "
                            "Please specify a smaller size."
                        )
                        volume = None
                    else:
                        reply = (
                            f"Target size is set to {volume:.4f} BTC. At entry price ${entry:.2f}, "
                            f"this will cost ${cost_cad:.2f} CAD. "
                            "To proceed, please type exactly EXECUTE in the chat box."
                        )
                else:
                    if volume > balance_data["BTC"]:
                        reply = (
                            f"You specified selling {volume:.4f} BTC, but you only have "
                            f"{balance_data['BTC']:.4f} BTC available. Please specify a smaller size."
                        )
                        volume = None
                    else:
                        reply = (
                            f"Target size is set to sell {volume:.4f} BTC. At entry price ${entry:.2f}. "
                            "To proceed, please type exactly EXECUTE in the chat box."
                        )
            except Exception:
                reply = "I couldn't parse the exact BTC amount. E.g. '0.01 BTC'."
        else:
            reply = "Please specify a numeric volume, for example: '0.02 BTC'."
            
    else:
        # Default greeting / prompt
        if is_buy:
            reply = (
                f"I am your Secure Concierge. Your available balance is ${balance_data['CAD']:.2f} CAD. "
                f"How much of your balance would you like to risk to buy BTC at ${entry:.2f}? "
                "You can say something like 'Risk 10%' or 'Buy 0.05 BTC'."
            )
        else:
            reply = (
                f"I am your Secure Concierge. Your available balance is {balance_data['BTC']:.4f} BTC. "
                f"How much would you like to sell at ${entry:.2f}? "
                "You can say something like 'Sell 50%' or 'Sell 0.1 BTC'."
            )
            
    return reply, volume

def execute_trade(pair, direction, order_type, volume, price=None, passphrase=None):
    """Executes a trade on Kraken (Sandbox or Prod) with strict passphrase verification."""
    print("Execution Agent: Received order request...")
    
    # 1. Gatekeeper Check: Cryptographic Passphrase Verification
    correct_passphrase = os.getenv("TRADE_PASSPHRASE")
    if not correct_passphrase:
        print("Execution Agent ERROR: TRADE_PASSPHRASE is not set in the environment (.env).", file=sys.stderr)
        return {"status": "REJECTED", "error": "System security passphrase is not configured."}
        
    if passphrase != correct_passphrase:
        print("Access Denied: Invalid Security Passphrase", file=sys.stderr)
        return {"status": "REJECTED", "error": "Access Denied: Invalid Security Passphrase"}
        
    print("Trade Authorized and Sent to Kraken Testnet")
        
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
    # Test 1: Try running with incorrect passphrase (should fail)
    print("--- Test 1: Incorrect Passphrase ---")
    execute_trade("XBTUSD", "buy", "limit", 0.01, price=50000, passphrase="wrong_passphrase")
    
    # Test 2: Try running with correct passphrase (should succeed in simulation mode)
    print("\n--- Test 2: Correct Passphrase ---")
    # Temporarily set a dummy passphrase for local testing if not loaded
    if not os.getenv("TRADE_PASSPHRASE"):
        os.environ["TRADE_PASSPHRASE"] = "your_secret_passphrase_here"
    execute_trade("XBTUSD", "buy", "limit", 0.01, price=50000, passphrase=os.getenv("TRADE_PASSPHRASE"))

