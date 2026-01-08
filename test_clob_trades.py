from polymarket_client import polymarket_client
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def test_trades():
    print("🚀 Testing CLOB Trades API...")
    
    if not polymarket_client.authenticated:
        print("❌ Client not authenticated. Cannot test private API.")
        return

    # 0. Inspect Client Methods
    if polymarket_client.client:
        print("\n0️⃣ Inspecting py-clob-client methods:")
        methods = dir(polymarket_client.client)
        relevant = [m for m in methods if 'trade' in m or 'get' in m]
        print(relevant)
        
        print("\n0️⃣.1️⃣ Help for get_trades (User History?):")
        try:
            help(polymarket_client.client.get_trades)
        except:
            print("No help available")

        print("\n0️⃣.2️⃣ Help for get_market_trades_events (Global?):")
        try:
            help(polymarket_client.client.get_market_trades_events)
        except:
            print("No help available")
    
    # 1. Get a market to find a valid Token ID
    print("\n1️⃣ Fetching active markets...")
    markets = polymarket_client.get_markets(limit=5)
    
    target_token_id = None
    for m in markets:
        clob_ids = m.get('clobTokenIds', [])
        if clob_ids:
            target_token_id = clob_ids[0]
            print(f"   ✅ Found Market: {m.get('question')} (ID: {target_token_id})")
            break
            
    if not target_token_id:
        print("❌ No markets with clobTokenIds found.")
        return

    # 2. Fetch Trades (Standard Attempt)
    print(f"\n2️⃣ Fetching trades (Standard Path Signature)...")
    trades = polymarket_client.get_trades(target_token_id, limit=5)
    print(f"   Result: {len(trades)} trades")

    # 3. Test Alternative Signature (Path without Query)
    print(f"\n3️⃣ Testing Alternative Signature (Path only)...")
    path = "/trades"
    params = {'token_id': target_token_id, 'limit': '5'}
    
    # Manually sign with just path
    import time, hmac, hashlib
    timestamp = str(int(time.time() * 1000))
    # SIG = timestamp + method + path + body
    message = timestamp + "GET" + path + "" # Body empty
    
    secret = polymarket_client.api_secret
    key = polymarket_client.api_key
    passphrase = polymarket_client.api_passphrase
    
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    
    headers = {
        'POLY-API-KEY': key,
        'POLY-SIGNATURE': signature,
        'POLY-TIMESTAMP': timestamp,
        'POLY-PASSPHRASE': passphrase,
    }
    
    import requests
    try:
        r = requests.get(f"{polymarket_client.CLOB_HOST}{path}", params=params, headers=headers)
        print(f"   Alt Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   ✅ SUCCESS! {len(r.json())} trades found.")
            print(r.json()[0] if r.json() else "Empty list")
        else:
            print(f"   ❌ FAILED: {r.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_trades()
