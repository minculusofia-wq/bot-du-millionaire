# -*- coding: utf-8 -*-
"""
Arbitrage Engine - Détection et exécution d'opportunités d'arbitrage multi-DEX
✨ Phase 9 Optimization: Revenus passifs additionnels

Supporte: Raydium, Orca, Jupiter
Détecte les écarts de prix entre DEX et exécute automatiquement
"""
from typing import Dict, List, Tuple, Optional
import requests
from datetime import datetime
import time
from cache_manager import cache_manager


class ArbitrageEngine:
    """
    Détecte et exécute des opportunités d'arbitrage sur Solana
    Supporte: Raydium, Orca, Jupiter
    """

    def __init__(self):
        self.dex_prices = {}
        self.min_profit_threshold = 1.5  # 1.5% minimum pour être rentable (après frais)
        self.opportunities_found = 0
        self.opportunities_executed = 0
        self.last_update = None

        # URLs des APIs DEX
        self.dex_apis = {
            'Jupiter': 'https://price.jup.ag/v4/price',
            'Raydium': 'https://api.raydium.io/v2/main/price',
            'Orca': 'https://api.orca.so/v1/token/list'
        }

        # Frais estimés (% par transaction)
        self.estimated_fees = {
            'Jupiter': 0.25,  # 0.25% swap fee
            'Raydium': 0.25,  # 0.25% swap fee
            'Orca': 0.30      # 0.30% swap fee
        }

    def update_dex_prices(self, token_mint: str) -> Dict[str, float]:
        """
        Récupère les prix du token sur tous les DEX

        Args:
            token_mint: Adresse du token Solana

        Returns:
            {'Jupiter': 0.123, 'Raydium': 0.125, 'Orca': 0.124}
        """
        # Vérifier le cache (TTL: 10 secondes pour prix en temps réel)
        cache_key = f"dex_prices_{token_mint}"
        cached_prices = cache_manager.get(cache_key, namespace="prices")
        if cached_prices is not None:
            return cached_prices

        prices = {}

        # 1. Jupiter API (Price API v4)
        try:
            response = requests.get(
                f"{self.dex_apis['Jupiter']}?ids={token_mint}",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and token_mint in data['data']:
                    prices['Jupiter'] = float(data['data'][token_mint]['price'])
        except Exception as e:
            print(f"⚠️ Jupiter API erreur pour {token_mint[:8]}: {e}")

        # 2. Raydium API
        try:
            response = requests.get(self.dex_apis['Raydium'], timeout=3)
            if response.status_code == 200:
                data = response.json()
                if token_mint in data:
                    prices['Raydium'] = float(data[token_mint])
        except Exception as e:
            print(f"⚠️ Raydium API erreur pour {token_mint[:8]}: {e}")

        # 3. Orca API
        try:
            response = requests.get(self.dex_apis['Orca'], timeout=3)
            if response.status_code == 200:
                tokens = response.json()
                for token in tokens:
                    if token.get('mint') == token_mint:
                        price = token.get('price', 0)
                        if price:
                            prices['Orca'] = float(price)
                        break
        except Exception as e:
            print(f"⚠️ Orca API erreur pour {token_mint[:8]}: {e}")

        # Mettre en cache (TTL: 10 secondes)
        cache_manager.set(cache_key, prices, ttl=10, namespace="prices")

        self.dex_prices[token_mint] = prices
        self.last_update = datetime.now()

        return prices

    def detect_arbitrage(self, token_mint: str) -> Dict:
        """
        Détecte les opportunités d'arbitrage

        Args:
            token_mint: Adresse du token

        Returns:
            {
                'opportunity': True/False,
                'profit_percent': 2.3,
                'net_profit': 1.8,
                'buy_dex': 'Raydium',
                'buy_price': 0.123,
                'buy_fee': 0.25,
                'sell_dex': 'Jupiter',
                'sell_price': 0.126,
                'sell_fee': 0.25,
                'timestamp': '2025-11-27T...'
            }
        """
        # Mettre à jour les prix
        prices = self.update_dex_prices(token_mint)

        if len(prices) < 2:
            return {
                'opportunity': False,
                'profit_percent': 0,
                'net_profit': 0,
                'reason': 'Pas assez de DEX disponibles (minimum 2)',
                'available_dex': list(prices.keys())
            }

        # Trouver le prix min (où acheter) et max (où vendre)
        buy_dex = min(prices, key=prices.get)
        sell_dex = max(prices, key=prices.get)
        buy_price = prices[buy_dex]
        sell_price = prices[sell_dex]

        # Calculer le profit brut (avant frais)
        profit_percent = ((sell_price - buy_price) / buy_price) * 100

        # Calculer les frais
        buy_fee = self.estimated_fees.get(buy_dex, 0.25)
        sell_fee = self.estimated_fees.get(sell_dex, 0.25)
        total_fees = buy_fee + sell_fee

        # Profit net (après frais)
        net_profit = profit_percent - total_fees

        # Y a-t-il une opportunité rentable ?
        opportunity = net_profit >= self.min_profit_threshold

        if opportunity:
            self.opportunities_found += 1
            print(f"\n💰 OPPORTUNITÉ D'ARBITRAGE DÉTECTÉE!")
            print(f"Token: {token_mint[:8]}...")
            print(f"📊 Acheter sur {buy_dex} à {buy_price:.6f} (frais: {buy_fee}%)")
            print(f"📊 Vendre sur {sell_dex} à {sell_price:.6f} (frais: {sell_fee}%)")
            print(f"💵 Profit BRUT: +{profit_percent:.2f}%")
            print(f"💰 Profit NET: +{net_profit:.2f}%")

        return {
            'opportunity': opportunity,
            'profit_percent': round(profit_percent, 2),
            'net_profit': round(net_profit, 2),
            'buy_dex': buy_dex,
            'buy_price': buy_price,
            'buy_fee': buy_fee,
            'sell_dex': sell_dex,
            'sell_price': sell_price,
            'sell_fee': sell_fee,
            'total_fees': total_fees,
            'timestamp': datetime.now().isoformat(),
            'token_mint': token_mint
        }

    def calculate_optimal_amount(self,
                                capital: float,
                                profit_percent: float,
                                max_position: float = 0.2) -> float:
        """
        Calcule le montant optimal à trader

        Args:
            capital: Capital total disponible
            profit_percent: Profit net attendu (%)
            max_position: % maximum du capital (défaut 20%)

        Returns:
            Montant optimal en USD
        """
        # Plus le profit est élevé, plus on peut trader
        if profit_percent > 5:
            position_percent = max_position  # 20%
        elif profit_percent > 3:
            position_percent = max_position * 0.75  # 15%
        elif profit_percent > 2:
            position_percent = max_position * 0.5  # 10%
        else:
            position_percent = max_position * 0.25  # 5%

        return round(capital * position_percent, 2)

    def calculate_arbitrage_amount(self, capital: float) -> float:
        """
        Alias pour calculate_optimal_amount (compatibilité)

        Args:
            capital: Capital total

        Returns:
            Montant à utiliser (20% du capital par défaut)
        """
        return self.calculate_optimal_amount(capital, profit_percent=2.0)

    def execute_arbitrage(self,
                         opportunity: Dict,
                         amount: float,
                         mode: str = 'TEST') -> Dict:
        """
        Exécute l'arbitrage (SEMI-AUTO: nécessite confirmation)

        Args:
            opportunity: Opportunité détectée par detect_arbitrage()
            amount: Montant à trader (USD)
            mode: 'TEST' (simulation) ou 'REAL' (exécution réelle)

        Returns:
            {
                'success': True/False,
                'mode': 'TEST' ou 'REAL',
                'profit': float,
                'error': str (si erreur)
            }
        """
        if not opportunity.get('opportunity'):
            return {
                'success': False,
                'error': 'Pas d\'opportunité valide'
            }

        print(f"\n💰 EXÉCUTION ARBITRAGE")
        print(f"Token: {opportunity['token_mint'][:8]}...")
        print(f"📊 Acheter {amount:.2f}$ sur {opportunity['buy_dex']} à {opportunity['buy_price']:.6f}")
        print(f"📊 Vendre {amount:.2f}$ sur {opportunity['sell_dex']} à {opportunity['sell_price']:.6f}")
        print(f"💵 Profit NET attendu: +{opportunity['net_profit']:.2f}%")

        if mode == 'TEST':
            # Simulation
            estimated_profit = amount * (opportunity['net_profit'] / 100)
            print(f"✅ [SIMULATION] Profit estimé: +{estimated_profit:.2f} USD")

            self.opportunities_executed += 1

            return {
                'success': True,
                'mode': 'TEST',
                'profit': round(estimated_profit, 2),
                'timestamp': datetime.now().isoformat()
            }

        elif mode == 'REAL':
            # Mode REAL nécessite intégration avec solana_executor
            print("⚠️ Exécution REAL nécessite configuration complète")
            print("→ Intégration avec solana_executor requise")
            print("→ Utilisez mode TEST pour le moment")

            return {
                'success': False,
                'error': 'Mode REAL non implémenté (nécessite solana_executor)'
            }

    def scan_for_opportunities(self, token_mints: List[str]) -> List[Dict]:
        """
        Scanne plusieurs tokens pour trouver des opportunités

        Args:
            token_mints: Liste d'adresses de tokens

        Returns:
            Liste des opportunités trouvées
        """
        opportunities = []

        print(f"\n🔍 Scan de {len(token_mints)} tokens pour arbitrage...")

        for i, token_mint in enumerate(token_mints):
            try:
                opp = self.detect_arbitrage(token_mint)
                if opp['opportunity']:
                    opportunities.append(opp)
                    print(f"✅ [{i+1}/{len(token_mints)}] Opportunité trouvée: {token_mint[:8]}...")
                else:
                    print(f"⚪ [{i+1}/{len(token_mints)}] Pas d'opportunité: {token_mint[:8]}...")

                # Rate limiting pour ne pas surcharger les APIs
                time.sleep(0.5)
            except Exception as e:
                print(f"❌ [{i+1}/{len(token_mints)}] Erreur pour {token_mint[:8]}: {e}")

        print(f"\n📊 Résultat: {len(opportunities)} opportunités trouvées sur {len(token_mints)} tokens")

        return opportunities

    def get_statistics(self) -> Dict:
        """
        Retourne les statistiques de l'arbitrage

        Returns:
            {
                'opportunities_found': int,
                'opportunities_executed': int,
                'success_rate': float,
                'last_update': str
            }
        """
        success_rate = (self.opportunities_executed / self.opportunities_found * 100) \
                      if self.opportunities_found > 0 else 0

        return {
            'opportunities_found': self.opportunities_found,
            'opportunities_executed': self.opportunities_executed,
            'success_rate': round(success_rate, 1),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'min_profit_threshold': self.min_profit_threshold
        }

    def get_stats(self) -> Dict:
        """Alias pour get_statistics() (compatibilité API)"""
        return self.get_statistics()


# Instance globale
arbitrage_engine = ArbitrageEngine()
