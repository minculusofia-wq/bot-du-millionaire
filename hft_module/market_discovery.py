# -*- coding: utf-8 -*-
"""
HFT Market Discovery - Détection des marchés crypto 15-min sur Polymarket
Scanne l'API Gamma pour identifier les marchés à durée courte (15 minutes) sur BTC/ETH.
"""
import requests
import threading
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HFTMarketDiscovery")


@dataclass
class CryptoMarket:
    """Structure d'un marché crypto 15-min"""
    condition_id: str
    question: str
    slug: str
    end_date: datetime
    duration_minutes: int
    yes_token_id: str
    no_token_id: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: float
    crypto_asset: str  # BTC, ETH, etc.
    direction: str     # UP, DOWN, ABOVE, BELOW

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'end_date': self.end_date.isoformat() if self.end_date else None
        }

    @property
    def time_remaining_seconds(self) -> int:
        """Temps restant avant résolution en secondes"""
        if not self.end_date:
            return 0
        delta = self.end_date - datetime.now()
        return max(0, int(delta.total_seconds()))

    @property
    def is_active(self) -> bool:
        """Le marché est-il encore actif?"""
        return self.time_remaining_seconds > 0


class HFTMarketDiscovery:
    """
    Découvre et cache les marchés crypto 15-min actifs.
    Refresh automatique toutes les 60 secondes.
    """

    GAMMA_API = "https://gamma-api.polymarket.com"

    # Keywords pour identifier les marchés crypto
    CRYPTO_KEYWORDS = ['btc', 'eth', 'bitcoin', 'ethereum', 'crypto']
    DIRECTION_KEYWORDS = ['up', 'down', 'above', 'below', 'higher', 'lower', 'rise', 'fall']

    # Durée acceptable pour un marché 15-min (en minutes)
    MIN_DURATION_MINUTES = 10
    MAX_DURATION_MINUTES = 20

    def __init__(self, refresh_interval: int = 60):
        self.refresh_interval = refresh_interval
        self.active_markets: Dict[str, CryptoMarket] = {}  # {condition_id: CryptoMarket}
        self.token_to_condition: Dict[str, str] = {}  # {token_id: condition_id}

        self._running = False
        self._refresh_thread = None
        self._last_refresh: Optional[datetime] = None
        self._lock = threading.Lock()

        # Stats
        self.total_markets_checked = 0
        self.markets_found = 0

        logger.info(f"HFTMarketDiscovery initialisé (refresh: {refresh_interval}s)")

    def is_15min_crypto_market(self, market: Dict) -> Optional[CryptoMarket]:
        """
        Vérifie si un marché est un marché crypto 15-min.
        Retourne un CryptoMarket si oui, None sinon.
        """
        question = (market.get('question') or '').lower()

        # 1. Vérifier les keywords crypto
        crypto_asset = None
        for kw in self.CRYPTO_KEYWORDS:
            if kw in question:
                if 'btc' in kw or 'bitcoin' in kw:
                    crypto_asset = 'BTC'
                elif 'eth' in kw or 'ethereum' in kw:
                    crypto_asset = 'ETH'
                else:
                    crypto_asset = 'CRYPTO'
                break

        if not crypto_asset:
            return None

        # 2. Vérifier les keywords de direction
        direction = None
        for kw in self.DIRECTION_KEYWORDS:
            if kw in question:
                if kw in ['up', 'above', 'higher', 'rise']:
                    direction = 'UP'
                else:
                    direction = 'DOWN'
                break

        if not direction:
            return None

        # 3. Vérifier la durée (15 minutes)
        end_date_str = market.get('endDate')
        start_date_str = market.get('startDate') or market.get('createdAt')

        if not end_date_str:
            return None

        try:
            # Parser les dates
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            # Convertir en datetime naive pour comparaison
            end_date = end_date.replace(tzinfo=None)

            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                start_date = start_date.replace(tzinfo=None)
                duration_minutes = (end_date - start_date).total_seconds() / 60
            else:
                # Si pas de start_date, on estime basé sur le temps restant
                duration_minutes = 15  # Assume 15 min

            # Vérifier si dans la plage acceptée
            if not (self.MIN_DURATION_MINUTES <= duration_minutes <= self.MAX_DURATION_MINUTES):
                return None

        except (ValueError, TypeError) as e:
            logger.debug(f"Erreur parsing date: {e}")
            return None

        # 4. Vérifier que le marché est encore actif
        if end_date <= datetime.now():
            return None

        # 5. Extraire les infos du marché
        condition_id = market.get('conditionId', '')
        clob_token_ids = market.get('clobTokenIds', [])
        outcome_prices = market.get('outcomePrices', [])

        yes_token = clob_token_ids[0] if len(clob_token_ids) > 0 else ''
        no_token = clob_token_ids[1] if len(clob_token_ids) > 1 else ''

        yes_price = float(outcome_prices[0]) if len(outcome_prices) > 0 and outcome_prices[0] else 0.5
        no_price = float(outcome_prices[1]) if len(outcome_prices) > 1 and outcome_prices[1] else 0.5

        return CryptoMarket(
            condition_id=condition_id,
            question=market.get('question', ''),
            slug=market.get('slug', ''),
            end_date=end_date,
            duration_minutes=int(duration_minutes),
            yes_token_id=yes_token,
            no_token_id=no_token,
            yes_price=yes_price,
            no_price=no_price,
            volume=float(market.get('volume', 0) or 0),
            liquidity=float(market.get('liquidity', 0) or 0),
            crypto_asset=crypto_asset,
            direction=direction
        )

    def fetch_markets(self) -> List[Dict]:
        """Récupère les marchés actifs depuis Gamma API"""
        all_markets = []

        try:
            # Fetch marchés crypto
            params = {
                'active': 'true',
                'tag': 'crypto',
                'limit': 200,
                'order': 'endDate',
                'ascending': 'true'  # Les plus proches de la fin en premier
            }

            resp = requests.get(f"{self.GAMMA_API}/markets", params=params, timeout=15)
            if resp.status_code == 200:
                markets = resp.json()
                all_markets.extend(markets)
                logger.debug(f"Fetched {len(markets)} crypto markets from Gamma")

            # Fetch aussi sans tag pour être sûr de ne rien rater
            params_all = {
                'active': 'true',
                'limit': 200,
                'order': 'endDate',
                'ascending': 'true'
            }

            resp2 = requests.get(f"{self.GAMMA_API}/markets", params=params_all, timeout=15)
            if resp2.status_code == 200:
                markets2 = resp2.json()
                # Ajouter les marchés pas déjà présents
                existing_ids = {m.get('conditionId') for m in all_markets}
                for m in markets2:
                    if m.get('conditionId') not in existing_ids:
                        all_markets.append(m)

        except Exception as e:
            logger.error(f"Erreur fetch markets: {e}")

        return all_markets

    def refresh(self) -> int:
        """
        Rafraîchit la liste des marchés 15-min crypto actifs.
        Retourne le nombre de marchés trouvés.
        """
        raw_markets = self.fetch_markets()
        self.total_markets_checked += len(raw_markets)

        new_markets = {}
        new_token_map = {}

        for market in raw_markets:
            crypto_market = self.is_15min_crypto_market(market)
            if crypto_market and crypto_market.is_active:
                new_markets[crypto_market.condition_id] = crypto_market

                # Mapper les tokens vers le condition_id
                if crypto_market.yes_token_id:
                    new_token_map[crypto_market.yes_token_id] = crypto_market.condition_id
                if crypto_market.no_token_id:
                    new_token_map[crypto_market.no_token_id] = crypto_market.condition_id

        with self._lock:
            self.active_markets = new_markets
            self.token_to_condition = new_token_map
            self._last_refresh = datetime.now()

        self.markets_found = len(new_markets)

        if new_markets:
            logger.info(f"HFT Markets: {len(new_markets)} marchés 15-min crypto actifs")
            for m in list(new_markets.values())[:3]:  # Log les 3 premiers
                logger.debug(f"  - {m.crypto_asset} {m.direction}: {m.question[:50]}... ({m.time_remaining_seconds}s restant)")
        else:
            logger.debug("Aucun marché 15-min crypto actif trouvé")

        return len(new_markets)

    def get_market_by_token(self, token_id: str) -> Optional[CryptoMarket]:
        """Récupère un marché par son token ID"""
        with self._lock:
            condition_id = self.token_to_condition.get(token_id)
            if condition_id:
                return self.active_markets.get(condition_id)
        return None

    def get_market_by_condition(self, condition_id: str) -> Optional[CryptoMarket]:
        """Récupère un marché par son condition ID"""
        with self._lock:
            return self.active_markets.get(condition_id)

    def get_all_active_markets(self) -> List[CryptoMarket]:
        """Retourne tous les marchés actifs"""
        with self._lock:
            return [m for m in self.active_markets.values() if m.is_active]

    def get_all_token_ids(self) -> List[str]:
        """Retourne tous les token IDs des marchés actifs"""
        with self._lock:
            tokens = []
            for market in self.active_markets.values():
                if market.yes_token_id:
                    tokens.append(market.yes_token_id)
                if market.no_token_id:
                    tokens.append(market.no_token_id)
            return tokens

    def start(self):
        """Démarre le refresh automatique"""
        if self._running:
            return

        self._running = True

        # Premier refresh immédiat
        self.refresh()

        def refresh_loop():
            while self._running:
                time.sleep(self.refresh_interval)
                if self._running:
                    try:
                        self.refresh()
                    except Exception as e:
                        logger.error(f"Erreur refresh loop: {e}")

        self._refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self._refresh_thread.start()
        logger.info("HFTMarketDiscovery démarré")

    def stop(self):
        """Arrête le refresh automatique"""
        self._running = False
        logger.info("HFTMarketDiscovery arrêté")

    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        with self._lock:
            return {
                'running': self._running,
                'active_markets': len(self.active_markets),
                'token_count': len(self.token_to_condition),
                'last_refresh': self._last_refresh.isoformat() if self._last_refresh else None,
                'refresh_interval': self.refresh_interval,
                'total_checked': self.total_markets_checked,
                'markets': [m.to_dict() for m in self.active_markets.values()]
            }
