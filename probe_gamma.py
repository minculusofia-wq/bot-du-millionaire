import requests
import json

GAMMA_API = "https://gamma-api.polymarket.com"

print("🔍 PROBING GAMMA API FOR TRADES...\n")

# 1. Get a condition ID or Market ID
resp = requests.get(f"{GAMMA_API}/markets", params={'limit': 1, 'active': 'true', 'closed': 'false'})
market = resp.json()[0]
market_id = market['id']
slug = market['slug']
print(f"ℹ️ Sample Market: {slug} (ID: {market_id})")

# 2. Try various endpoints
endpoints = [
    f"/markets/{market_id}/activity",
    f"/markets/{market_id}/trades",
    f"/events/{market_id}/activity",
    f"/activity?market_id={market_id}",
    f"/trades?market={market_id}"
]

for ep in endpoints:
    url = f"{GAMMA_API}{ep}"
    print(f"👉 Testing {url} ...")
    try:
        r = requests.get(url, timeout=3)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   ✅ PAYLOAD: {str(r.json())[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n🏁 Probe Finished")
