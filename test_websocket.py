#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test WebSocket Helius"""
import os
import asyncio
import ssl

# Charger .env
from pathlib import Path
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"\'')

try:
    import websockets
    print("✅ Module websockets importé")
except ImportError:
    print("❌ Module websockets manquant")
    print("   Installez avec: pip install websockets")
    exit(1)

api_key = os.getenv('HELIUS_API_KEY')
print(f"✅ Helius API Key: {api_key[:10]}...***" if api_key else "❌ Helius API Key manquante")

wss_urls = [
    f"wss://api-mainnet.helius-rpc.com/v0/?api-key={api_key}",
    f"wss://api-mainnet.helius-rpc.com/?api-key={api_key}",
    f"wss://api-mainnet.helius-rpc.com/ws?api-key={api_key}"
]

async def test_connection(url_index):
    url = wss_urls[url_index]
    print(f"\n🔌 Test connexion URL {url_index + 1}/3...")
    print(f"   URL: {url[:50]}...")

    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with websockets.connect(
            url,
            ssl=ssl_context,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        ) as websocket:
            print(f"✅ Connexion réussie sur URL {url_index + 1}")
            print(f"   État: {websocket.state.name}")

            # Tester un ping
            pong = await websocket.ping()
            await asyncio.wait_for(pong, timeout=5)
            print(f"✅ Ping/Pong OK")

            return True
    except Exception as e:
        print(f"❌ Erreur URL {url_index + 1}: {type(e).__name__}")
        print(f"   Message: {str(e)[:100]}")
        return False

async def main():
    print("=" * 60)
    print("TEST WEBSOCKET HELIUS")
    print("=" * 60)

    for i in range(3):
        success = await test_connection(i)
        if success:
            print(f"\n✅ URL {i + 1} fonctionne!")
            break
        await asyncio.sleep(1)
    else:
        print("\n❌ Aucune URL ne fonctionne")
        print("\nSolutions possibles:")
        print("1. Vérifier votre clé API Helius")
        print("2. Vérifier votre connexion internet")
        print("3. Vérifier que Helius API est accessible")

if __name__ == "__main__":
    asyncio.run(main())
