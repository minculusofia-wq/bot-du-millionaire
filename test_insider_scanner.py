#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script pour diagnostiquer le Insider Scanner
"""
import sys
import os
import time

# Ajouter le répertoire au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Charger les variables d'environnement depuis .env
from pathlib import Path
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"\'')
    print("✅ Fichier .env chargé")

from insider_scanner import InsiderScanner

def test_scanner():
    print("\n" + "=" * 60)
    print("🧪 TEST INSIDER SCANNER")
    print("=" * 60)
    
    # 1. Créer une instance
    scanner = InsiderScanner()
    
    print("\n📋 Configuration actuelle:")
    config = scanner.get_config()
    for key, value in config.items():
        if not key.startswith('_'):
            print(f"   {key}: {value}")
    
    # 2. Tester la connexion à Gamma API
    print("\n🌐 Test Gamma API (marchés actifs)...")
    markets = scanner.get_all_active_markets(limit=5)
    print(f"   ✅ {len(markets)} marchés récupérés")
    
    if markets:
        sample = markets[0]
        print(f"   Exemple: {sample.get('question', 'N/A')[:50]}...")
        print(f"   ConditionID: {sample.get('conditionId', 'N/A')[:20]}...")
    
    # 3. Tester Goldsky API
    print("\n🌐 Test Goldsky Positions API...")
    if markets:
        condition_id = markets[0].get('conditionId')
        activities = scanner.get_recent_market_activity(condition_id, limit=10)
        print(f"   ✅ Premier scan: {len(activities)} activités (normal si 0, c'est le snapshot initial)")
        
        # Second scan pour voir les différences
        time.sleep(2)
        activities2 = scanner.get_recent_market_activity(condition_id, limit=10)
        print(f"   ✅ Second scan: {len(activities2)} nouvelles activités")
    
    # 4. Tester Polygonscan API
    print("\n🌐 Test Polygonscan API...")
    polygonscan_key = os.getenv('POLYGONSCAN_API_KEY', '')
    if polygonscan_key:
        print(f"   API Key: {polygonscan_key[:8]}...")
        # Test avec une adresse connue
        test_address = "0x9036e8c496dae179d844dd007bcb65c2f01fb811"
        tx_count = scanner.get_wallet_tx_count(test_address)
        print(f"   ✅ TX count pour adresse test: {tx_count}")
    else:
        print("   ⚠️ POLYGONSCAN_API_KEY non configurée!")
    
    # 5. Simuler un scan complet
    print("\n🔍 Exécution d'un scan complet...")
    start_time = time.time()
    alerts = scanner.scan_all_markets()
    duration = time.time() - start_time
    
    print(f"   ⏱️ Durée: {duration:.1f}s")
    print(f"   📊 Marchés scannés: {scanner.markets_scanned}")
    print(f"   🚨 Alertes générées: {len(alerts)}")
    
    if alerts:
        print("\n   Détails des alertes:")
        for alert in alerts[:3]:  # Afficher max 3
            print(f"   - {alert.alert_type}: {alert.wallet_address[:10]}... | ${alert.bet_amount:.0f} | {alert.trigger_details}")
    else:
        print("   ⚠️ Aucune alerte générée.")
        print("\n   Possibles raisons:")
        print("   1. Premier scan (snapshots en initialisation)")
        print("   2. Pas d'activité suspecte actuellement")
        print("   3. Seuils trop élevés dans la config")
    
    # 6. Statistiques finales
    print("\n📊 Statistiques du scanner:")
    stats = scanner.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ Test terminé!")
    print("=" * 60)
    
    return len(alerts) >= 0  # Succès si pas d'erreur

if __name__ == '__main__':
    try:
        success = test_scanner()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
