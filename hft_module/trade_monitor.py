# -*- coding: utf-8 -*-
"""
HFT Trade Monitor - Surveillance temps réel des trades HFT
Utilise Goldsky Subgraph pour détecter les changements de positions.
Optimisé pour une latence minimale sur les marchés 15-min crypto.
"""
import os
import threading
import time
import logging
import requests
from typing import Dict, List, Set, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HFTTradeMonitor")


@dataclass
class HFTSignal:
    """Signal de trade HFT détecté"""
    id: str
    wallet_address: str
    wallet_name: str
    token_id: str
    condition_id: str
    side: str           # BUY ou SELL
    price: float
    size: float         # En shares
    value_usd: float    # En USD
    market_question: str
    crypto_asset: str   # BTC, ETH
    direction: str      # UP, DOWN
    tx_hash: str
    timestamp: datetime
    latency_ms: int     # Temps entre trade on-chain et détection

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


class HFTTradeMonitor:
    """
    Moniteur de trades HFT ultra-rapide.
    Utilise Goldsky Subgraph pour détecter les changements de positions.
    """

    # APIs
    GOLDSKY_POSITIONS = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"
    GAMMA_API = "https://gamma-api.polymarket.com"

    def __init__(self, market_discovery=None):
        self.market_discovery = market_discovery
        self.tracked_wallets: Dict[str, Dict] = {}  # {address: config}
        self.callbacks: List[Callable] = []

        # État
        self._running = False
        self._poll_thread = None
        self._poll_interval = 5  # 5 secondes - rapide pour HFT

        # Cache positions précédentes pour détecter les changements
        self._last_positions: Dict[str, Dict] = {}  # {wallet: {asset_id: balance}}

        # Cache pour éviter les doublons de signaux
        self._processed_signals: Set[str] = set()
        self._max_cache_size = 500

        # Buffer de signaux récents
        self.recent_signals: deque = deque(maxlen=100)

        # Stats
        self.signals_detected = 0
        self.last_signal_time: Optional[datetime] = None
        self.polls_count = 0

        logger.info("HFTTradeMonitor initialisé (Goldsky + Gamma)")

    def add_wallet(self, address: str, name: str = "HFT Wallet", config: Dict = None):
        """Ajoute un wallet à surveiller"""
        addr = address.lower()
        self.tracked_wallets[addr] = {
            'address': addr,
            'name': name,
            'config': config or {},
            'added_at': datetime.now().isoformat()
        }
        # Initialiser le cache de positions
        self._last_positions[addr] = {}
        logger.info(f"HFT Wallet ajouté: {name} ({addr[:10]}...)")

    def remove_wallet(self, address: str):
        """Retire un wallet de la surveillance"""
        addr = address.lower()
        if addr in self.tracked_wallets:
            del self.tracked_wallets[addr]
        if addr in self._last_positions:
            del self._last_positions[addr]
        logger.info(f"HFT Wallet retiré: {addr[:10]}...")

    def add_callback(self, callback: Callable):
        """Ajoute un callback appelé lors de la détection d'un signal"""
        self.callbacks.append(callback)

    def _notify_callbacks(self, signal: HFTSignal):
        """Notifie tous les callbacks"""
        for callback in self.callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"Erreur callback: {e}")

    # =========================================================================
    # GOLDSKY SUBGRAPH - Positions actuelles
    # =========================================================================

    def _get_user_positions(self, address: str) -> Dict[str, float]:
        """Récupère les positions actuelles d'un wallet via Goldsky"""
        query = """
        {
          userBalances(first: 100, where: {user: "%s", balance_gt: "0"}) {
            id
            balance
            asset {
              id
              condition {
                id
              }
            }
          }
        }
        """ % address.lower()

        try:
            resp = requests.post(
                self.GOLDSKY_POSITIONS,
                json={'query': query},
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )

            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'].get('userBalances'):
                    positions = {}
                    for bal in data['data']['userBalances']:
                        asset_id = bal['asset']['id']
                        # Balance en micro-unités, convertir en unités normales
                        balance = float(bal['balance']) / 1e6
                        positions[asset_id] = balance
                    return positions
            return {}
        except Exception as e:
            logger.debug(f"Erreur get_user_positions: {e}")
            return {}

    # =========================================================================
    # GAMMA API - Infos marché
    # =========================================================================

    def _get_market_info(self, token_id: str) -> Dict:
        """Récupère les infos d'un marché via Gamma API"""
        try:
            resp = requests.get(
                f"{self.GAMMA_API}/markets",
                params={'clob_token_ids': token_id},
                timeout=5
            )
            if resp.status_code == 200:
                markets = resp.json()
                if markets and len(markets) > 0:
                    market = markets[0]
                    return {
                        'question': market.get('question', ''),
                        'condition_id': market.get('condition_id', ''),
                        'yes_price': float(market.get('outcomePrices', '["0.5","0.5"]').strip('[]').split(',')[0].strip('"') or 0.5),
                    }
        except Exception as e:
            logger.debug(f"Erreur get_market_info: {e}")

        return {}

    # =========================================================================
    # DÉTECTION DE TRADES
    # =========================================================================

    def _detect_position_changes(self, wallet_addr: str, wallet_info: Dict) -> List[HFTSignal]:
        """Détecte les changements de position pour un wallet"""
        signals = []
        detection_time = datetime.now()

        # Récupérer positions actuelles
        current_positions = self._get_user_positions(wallet_addr)
        previous_positions = self._last_positions.get(wallet_addr, {})

        # Détecter les changements
        all_assets = set(current_positions.keys()) | set(previous_positions.keys())

        for asset_id in all_assets:
            current_bal = current_positions.get(asset_id, 0)
            previous_bal = previous_positions.get(asset_id, 0)
            diff = current_bal - previous_bal

            # Seuil minimum de changement ($1)
            if abs(diff) < 1:
                continue

            # Créer un ID unique pour éviter les doublons
            signal_id = f"{wallet_addr[:8]}_{asset_id[:16]}_{int(detection_time.timestamp())}"
            if signal_id in self._processed_signals:
                continue

            # Déterminer le side
            side = 'BUY' if diff > 0 else 'SELL'

            # Récupérer les infos du marché
            market_info = self._get_market_info(asset_id)

            # Vérifier si c'est un marché 15-min crypto (via market_discovery)
            crypto_asset = ''
            direction = ''
            market_question = market_info.get('question', '')

            if self.market_discovery:
                market_data = self.market_discovery.get_market_by_token(asset_id)
                if market_data:
                    crypto_asset = market_data.crypto_asset
                    direction = market_data.direction
                    market_question = market_data.question

            # Estimer le prix
            price = market_info.get('yes_price', 0.5)
            if price <= 0:
                price = 0.5

            # Créer le signal
            signal = HFTSignal(
                id=signal_id,
                wallet_address=wallet_addr,
                wallet_name=wallet_info.get('name', 'HFT Wallet'),
                token_id=asset_id,
                condition_id=market_info.get('condition_id', ''),
                side=side,
                price=price,
                size=abs(diff),
                value_usd=abs(diff) * price,
                market_question=market_question,
                crypto_asset=crypto_asset,
                direction=direction,
                tx_hash='',
                timestamp=detection_time,
                latency_ms=0
            )

            signals.append(signal)
            self._processed_signals.add(signal_id)

            # Nettoyer le cache si trop grand
            if len(self._processed_signals) > self._max_cache_size:
                self._processed_signals = set(list(self._processed_signals)[-250:])

        # Mettre à jour le cache
        self._last_positions[wallet_addr] = current_positions

        return signals

    # =========================================================================
    # POLLING LOOP
    # =========================================================================

    def _poll_loop(self):
        """Boucle de polling principale"""
        logger.info(f"HFT Poll loop démarrée (interval: {self._poll_interval}s)")

        while self._running:
            try:
                self.polls_count += 1

                for wallet_addr, wallet_info in list(self.tracked_wallets.items()):
                    if not self._running:
                        break

                    # Détecter les changements
                    signals = self._detect_position_changes(wallet_addr, wallet_info)

                    for signal in signals:
                        self.signals_detected += 1
                        self.last_signal_time = signal.timestamp
                        self.recent_signals.append(signal)

                        logger.info(
                            f"⚡ HFT Signal: {signal.wallet_name} | {signal.side} "
                            f"{signal.crypto_asset or 'TOKEN'} | ${signal.value_usd:.2f}"
                        )

                        # Notifier les callbacks
                        self._notify_callbacks(signal)

            except Exception as e:
                logger.error(f"Erreur poll loop: {e}")

            time.sleep(self._poll_interval)

    # =========================================================================
    # CONTROL
    # =========================================================================

    def start(self):
        """Démarre le monitoring"""
        if self._running:
            logger.warning("HFTTradeMonitor déjà en cours")
            return

        self._running = True

        # Initialiser les positions de base pour chaque wallet
        for wallet_addr in self.tracked_wallets:
            positions = self._get_user_positions(wallet_addr)
            self._last_positions[wallet_addr] = positions
            logger.info(f"Positions initiales: {wallet_addr[:10]}... ({len(positions)} positions)")

        # Démarrer le polling
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        logger.info(f"HFTTradeMonitor démarré ({len(self.tracked_wallets)} wallets)")

    def stop(self):
        """Arrête le monitoring"""
        self._running = False
        logger.info("HFTTradeMonitor arrêté")

    def get_recent_signals(self, limit: int = 50) -> List[Dict]:
        """Retourne les signaux récents"""
        return [s.to_dict() for s in list(self.recent_signals)[-limit:]]

    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return {
            'running': self._running,
            'tracked_wallets': len(self.tracked_wallets),
            'signals_detected': self.signals_detected,
            'last_signal': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'poll_interval': self._poll_interval,
            'polls_count': self.polls_count,
            'recent_signals_count': len(self.recent_signals)
        }
