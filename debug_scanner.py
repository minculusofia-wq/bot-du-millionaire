import logging
import sys
import time
import os
import requests
from insider_scanner import InsiderScanner
from dotenv import load_dotenv

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def run_diagnostic():
    print("🚀 Starting Scanner Diagnostic...")
    
    # Load env manually just in case
    load_dotenv()
    
    poly_key = os.getenv('POLYGONSCAN_API_KEY')
    print(f"🔑 POLYGONSCAN_API_KEY present: {'YES' if poly_key else 'NO'}")
    
    scanner = InsiderScanner()
    
    # 1. Test Gamma API (Markets) - Try Crypto for higher volume
    print("\n[1] Testing Gamma API (Start with Crypto)...")
    markets = scanner.get_markets_by_category('crypto', limit=10)
    print(f"✅ Found {len(markets)} crypto markets.")
    
    if not markets:
        print("❌ Failed to fetch markets. Aborting.")
        return

    # Print top 3 markets details
    for i, m in enumerate(markets[:3]):
        print(f"   [{i}] {m.get('question')} (Vol: ${m.get('volume', 0)}) - ID: {m.get('conditionId')}")

    # 2. Test Goldsky    # Inspect Gamma Market 'events'
    target_market = markets[0] if markets else None
    if target_market:
        print(f"\n   🔎 Inspecting Gamma Market 'events' field...")
        events = target_market.get('events', [])
        print(f"      Events Type: {type(events)}")
        print(f"      Length: {len(events)}")
        if events:
            print(f"      First Event: {events[0]}")
        else:
            print("      ⚠️ Events list is empty.")
    
    # Check if we can find recent trades in 'clobTokenIds' via Gamma?
    # No, Gamma seems to be metadata.
    
    print("\n✅ Diagnostic Complete.")

if __name__ == "__main__":
    run_diagnostic()
