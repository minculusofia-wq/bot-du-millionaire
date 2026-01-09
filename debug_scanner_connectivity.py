import requests
import time
import os

# Configuration from insider_scanner.py
GAMMA_API = "https://gamma-api.polymarket.com"
GOLDSKY_ACTIVITY = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/0.0.4/gn"
POLYGONSCAN_API = "https://api.polygonscan.com/api"

print("🔍 STARTING TECHNICAL AUDIT OF SCANNER APIs...\n")

# 1. TEST GAMMA API (Markets)
print("1️⃣ Testing Gamma API (Polymarket Markets)...")
try:
    params = {'limit': 5, 'active': 'true', 'order': 'volume', 'ascending': 'false'}
    t0 = time.time()
    resp = requests.get(f"{GAMMA_API}/markets", params=params, timeout=10)
    latency = (time.time() - t0) * 1000
    
    if resp.status_code == 200:
        markets = resp.json()
        print(f"   ✅ SUCCESS: Found {len(markets)} active markets. Latency: {latency:.0f}ms")
        if len(markets) > 0:
            print(f"   ℹ️ Sample Market: {markets[0].get('question')}")
            # Keep a condition ID for next test
            condition_id = markets[0].get('conditionId')
        else:
            print("   ⚠️ WARNING: API returned 0 markets.")
            condition_id = None
    else:
        print(f"   ❌ FAILURE: Status Check {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")
        condition_id = None
except Exception as e:
    print(f"   ❌ EXCEPTION: {e}")
    condition_id = None

print("-" * 50)

# 2. TEST GOLDSKY API (Probing for correct entities)
GOLDSKY_ACTIVITY = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/0.0.4/gn"
GOLDSKY_POSITIONS = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"

print("\n2️⃣ Testing Goldsky API (Probing)...")

# Test A: fpmmTrades on Activity Subgraph
print("   🔍 Probing 'fpmmTrades' on Activity Subgraph...")
query_a = """
{
  fpmmTrades(first: 5, orderBy: creationTimestamp, orderDirection: desc) {
    id
    creator { id }
    outcomeTokenAmount
    creationTimestamp
  }
}
"""
try:
    resp = requests.post(GOLDSKY_ACTIVITY, json={'query': query_a}, timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        if 'errors' not in data:
            print("      ✅ FOUND 'fpmmTrades'!")
            print(f"      Sample: {data['data']['fpmmTrades'][:1]}")
        else:
            print(f"      ❌ Error: {data['errors'][0]['message']}")
except Exception as e:
    print(f"      ❌ Exception: {e}")

# Test C: splitTrades (Exchange 1)
print("   🔍 Probing 'splitTrades'...")
query_c = """
{
  splitTrades(first: 5, orderBy: timestamp, orderDirection: desc) {
    id
    timestamp
    collateralAmount
  }
}
"""
try:
    resp = requests.post(GOLDSKY_ACTIVITY, json={'query': query_c}, timeout=5)
    if 'errors' not in resp.json():
        print("      ✅ FOUND 'splitTrades'!")
    else:
        print(f"      ❌ Error: {resp.json()['errors'][0]['message']}")
except:
    pass

# Test D: userBalances with Condition Filter (The Fix Candidate)
print("   🔍 Testing 'userBalances' with Condition Filter...")
# We need to filter userBalances where asset -> condition -> id == condition_id
if condition_id:
    # Note: Goldsky (The Graph) syntax for nested filter: asset_: { condition: "..." }
    query_d = """
    {
      userBalances(
        first: 5,
        where: { asset_: { condition: "%s" }, balance_gt: "0" }
      ) {
        id
        user
        balance
        asset { id }
      }
    }
    """ % condition_id
    try:
        resp = requests.post(GOLDSKY_POSITIONS, json={'query': query_d}, timeout=5)
        data = resp.json()
        if 'errors' not in data:
            print("      ✅ FOUND 'userBalances' by CONDITION!")
            print(f"      Sample: {data['data']['userBalances'][:1]}")
        else:
            print(f"      ❌ Error: {data['errors'][0]['message']}")
    except Exception as e:
        print(f"      ❌ Exception: {e}")

print("-" * 50)

# 3. TEST POLYGONSCAN API (Wallet History)
print("\n3️⃣ Testing Polygonscan API (Wallet History)...")
params = {
    'module': 'account',
    'action': 'txlist',
    'address': '0x8888888888888888888888888888888888888888', # Random burner address just to check API response
    'page': 1,
    'offset': 1,
    'apikey': os.getenv('POLYGONSCAN_API_KEY', '') # Will use env var if set
}

try:
    t0 = time.time()
    resp = requests.get(POLYGONSCAN_API, params=params, timeout=10)
    latency = (time.time() - t0) * 1000
    
    if resp.status_code == 200:
        data = resp.json()
        status = data.get('status')
        message = data.get('message')
        
        if status == '1' or message == 'No transactions found':
             print(f"   ✅ SUCCESS: API reachable. Latency: {latency:.0f}ms")
        elif message == 'NOTOK':
             print(f"   ⚠️ WARNING: API Key might be invalid or missing. Message: {data.get('result')}")
        else:
             print(f"   ℹ️ INFO: API Response: {message}")
    else:
         print(f"   ❌ FAILURE: Status {resp.status_code}")

except Exception as e:
    print(f"   ❌ EXCEPTION: {e}")

print("\n🏁 DIAGNOSTIC COMPLETED")
