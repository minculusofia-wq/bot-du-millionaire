#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Test Complet Phase 9
Valide tous les modules avant commit
"""
import sys

def run_tests():
    """Execute tous les tests et retourne True si tous passent"""
    print("🧪 TESTS PHASE 9 - Validation Complète\n")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    # Test 1: Import modules de base
    print("\n📦 Test 1: Import modules de base...")
    total_tests += 1
    try:
        import jito_integration
        import retry_handler
        import health_checker
        import performance_logger
        print("✅ PASS: Tous les modules s'importent")
        passed_tests += 1
    except ImportError as e:
        print(f"❌ FAIL: Erreur import - {e}")
        return False
    
    # Test 2: Import module d'intégration
    print("\n🔗 Test 2: Import module d'intégration...")
    total_tests += 1
    try:
        import integration_phase9
        print("✅ PASS: integration_phase9 s'importe")
        passed_tests += 1
    except ImportError as e:
        print(f"❌ FAIL: Erreur import integration - {e}")
        return False
    
    # Test 3: Instances globales
    print("\n🌍 Test 3: Vérification instances globales...")
    total_tests += 1
    try:
        from jito_integration import jito_integration as jito
        from retry_handler import default_retry_handler
        from health_checker import health_checker
        from performance_logger import performance_logger
        from integration_phase9 import phase9
        
        assert jito is not None
        assert default_retry_handler is not None
        assert health_checker is not None
        assert performance_logger is not None
        assert phase9 is not None
        print("✅ PASS: Toutes les instances existent")
        passed_tests += 1
    except (AssertionError, ImportError) as e:
        print(f"❌ FAIL: Instance manquante - {e}")
        return False
    
    # Test 4: Fonctionnalités Jito
    print("\n🛡️ Test 4: Fonctionnalités Jito...")
    total_tests += 1
    try:
        from jito_integration import jito_integration, JitoRegion
        
        # Test calcul priority fee
        fee_low = jito_integration.calculate_priority_fee('low')
        fee_high = jito_integration.calculate_priority_fee('high')
        assert fee_low < fee_high, "Priority fees incorrects"
        
        # Test régions
        assert len(jito_integration.regions) == 4, "Nombre régions incorrect"
        
        # Test stats
        stats = jito_integration.get_stats()
        assert 'total_transactions' in stats
        
        print("✅ PASS: Jito fonctionnel")
        passed_tests += 1
    except Exception as e:
        print(f"❌ FAIL: Jito - {e}")
        return False
    
    # Test 5: Retry Handler
    print("\n🔄 Test 5: Retry Handler...")
    total_tests += 1
    try:
        from retry_handler import default_retry_handler, retry
        
        # Test fonction simple
        def test_func():
            return "success"
        
        result = default_retry_handler.execute(test_func)
        assert result == "success"
        
        # Test décorateur
        @retry(max_attempts=2)
        def decorated():
            return "decorated_success"
        
        result2 = decorated()
        assert result2 == "decorated_success"
        
        print("✅ PASS: Retry handler fonctionnel")
        passed_tests += 1
    except Exception as e:
        print(f"❌ FAIL: Retry - {e}")
        return False
    
    # Test 6: Health Checker
    print("\n🏥 Test 6: Health Checker...")
    total_tests += 1
    try:
        from health_checker import health_checker
        
        # Test services initialisés
        assert len(health_checker.services) >= 2, "Services manquants"
        
        # Test health check
        overall = health_checker.get_overall_health()
        assert 'overall_healthy' in overall
        assert 'total_services' in overall
        
        print(f"✅ PASS: Health checker - {overall['healthy_count']}/{overall['total_services']} services")
        passed_tests += 1
    except Exception as e:
        print(f"❌ FAIL: Health checker - {e}")
        return False
    
    # Test 7: Performance Logger
    print("\n📊 Test 7: Performance Logger...")
    total_tests += 1
    try:
        from performance_logger import performance_logger
        
        # Test log trade
        performance_logger.log_trade_execution({
            'trader': 'TEST',
            'latency_ms': 100,
            'slippage_percent': 0.5,
            'success': True
        })
        
        # Test stats
        stats = performance_logger.get_stats()
        assert stats['total_trades'] >= 1
        
        print("✅ PASS: Performance logger fonctionnel")
        passed_tests += 1
    except Exception as e:
        print(f"❌ FAIL: Performance logger - {e}")
        return False
    
    # Test 8: Module d'intégration
    print("\n🎯 Test 8: Module d'intégration...")
    total_tests += 1
    try:
        from integration_phase9 import phase9
        
        # Test get_all_stats
        stats = phase9.get_all_stats()
        assert 'jito' in stats
        assert 'retry' in stats
        assert 'health' in stats
        assert 'performance' in stats
        
        # Test check_system_health
        health = phase9.check_system_health()
        assert 'overall' in health
        assert 'checks' in health
        
        print("✅ PASS: Module d'intégration complet")
        passed_tests += 1
    except Exception as e:
        print(f"❌ FAIL: Intégration - {e}")
        return False
    
    # Test 9: Documentation existe
    print("\n📚 Test 9: Documentation...")
    total_tests += 1
    try:
        import os
        assert os.path.exists('PHASE9_GUIDE.md'), "PHASE9_GUIDE.md manquant"
        assert os.path.exists('phase9_routes.md'), "phase9_routes.md manquant"
        print("✅ PASS: Documentation présente")
        passed_tests += 1
    except AssertionError as e:
        print(f"❌ FAIL: Documentation - {e}")
        return False
    
    # Résumé
    print("\n" + "=" * 60)
    print(f"\n📊 RÉSULTAT: {passed_tests}/{total_tests} tests passés")
    
    if passed_tests == total_tests:
        print("\n🎉 ✅ TOUS LES TESTS RÉUSSIS - Prêt pour commit !")
        return True
    else:
        print(f"\n❌ ÉCHEC: {total_tests - passed_tests} test(s) échoué(s)")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
