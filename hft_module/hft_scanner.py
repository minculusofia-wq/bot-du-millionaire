# -*- coding: utf-8 -*-
"""
HFT Scanner - Orchestrateur principal du module HFT
Coordonne la découverte de marchés, le monitoring des trades et l'exécution.
"""
import os
import json
import threading
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime

from .market_discovery import HFTMarketDiscovery
from .trade_monitor import HFTTradeMonitor, HFTSignal
from .hft_executor import HFTExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HFTScanner")


class HFTScanner:
    """
    Scanner HFT principal.
    Orchestre tous les composants du module HFT.
    """

    CONFIG_FILE = 'hft_config.json'

    DEFAULT_CONFIG = {
        'enabled': False,
        'auto_start': False,
        'market_refresh_interval': 60,
        'max_slippage_bps': 50,
        'execution_timeout_sec': 2,
        'poll_interval': 5,
        'tracked_wallets': []
    }

    def __init__(self, socketio=None, db_manager=None, polymarket_client=None):
        self.socketio = socketio
        self.db_manager = db_manager
        self.polymarket_client = polymarket_client

        # Configuration
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()

        # Composants
        self.market_discovery = HFTMarketDiscovery(
            refresh_interval=self.config.get('market_refresh_interval', 60)
        )

        self.trade_monitor = HFTTradeMonitor(
            market_discovery=self.market_discovery
        )
        self.trade_monitor._poll_interval = self.config.get('poll_interval', 5)

        self.executor = HFTExecutor(
            polymarket_client=polymarket_client,
            db_manager=db_manager,
            socketio=socketio
        )
        self.executor.set_config({
            'max_slippage_bps': self.config.get('max_slippage_bps', 50),
            'timeout_sec': self.config.get('execution_timeout_sec', 2)
        })

        # Connecter le callback de signal
        self.trade_monitor.add_callback(self._on_signal_detected)

        # État
        self._running = False
        self._lock = threading.Lock()

        # Charger les wallets
        self._load_wallets()

        # Stats
        self.signals_received = 0
        self.signals_executed = 0
        self.start_time: Optional[datetime] = None

        logger.info("HFTScanner initialisé")

    def _load_wallets(self):
        """Charge les wallets depuis la config"""
        wallets = self.config.get('tracked_wallets', [])
        for wallet in wallets:
            if wallet.get('enabled', True):
                self.trade_monitor.add_wallet(
                    address=wallet.get('address', ''),
                    name=wallet.get('nickname', 'HFT Wallet'),
                    config=wallet
                )

    def load_config(self):
        """Charge la configuration depuis le fichier"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    saved_config = json.load(f)
                    # Merger avec config par défaut
                    for key, value in saved_config.items():
                        self.config[key] = value
                logger.info("Configuration HFT chargée")
        except Exception as e:
            logger.error(f"Erreur chargement config HFT: {e}")

    def save_config(self):
        """Sauvegarde la configuration"""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuration HFT sauvegardée")
        except Exception as e:
            logger.error(f"Erreur sauvegarde config HFT: {e}")

    def set_config(self, new_config: Dict):
        """Met à jour la configuration"""
        with self._lock:
            for key, value in new_config.items():
                if key in self.config:
                    self.config[key] = value

            # Appliquer aux composants
            if 'market_refresh_interval' in new_config:
                self.market_discovery.refresh_interval = new_config['market_refresh_interval']

            if 'poll_interval' in new_config:
                self.trade_monitor._poll_interval = new_config['poll_interval']

            if 'max_slippage_bps' in new_config or 'execution_timeout_sec' in new_config:
                self.executor.set_config(new_config)

            self.save_config()

    def get_config(self) -> Dict:
        """Retourne la configuration"""
        return {
            **self.config,
            'running': self._running
        }

    def _on_signal_detected(self, signal: HFTSignal):
        """Callback appelé quand un signal HFT est détecté"""
        self.signals_received += 1

        logger.info(f"HFT Signal reçu: {signal.wallet_name} | {signal.side}")

        # Notifier l'UI
        if self.socketio:
            self.socketio.emit('hft_signal', signal.to_dict(), namespace='/')

        # Vérifier si on doit exécuter
        if not self.config.get('enabled', False):
            logger.debug("HFT désactivé, signal ignoré")
            return

        # Récupérer la config du wallet
        wallet_config = self._get_wallet_config(signal.wallet_address)
        if not wallet_config:
            logger.warning(f"Wallet {signal.wallet_address[:10]}... non configuré")
            return

        if not wallet_config.get('enabled', True):
            logger.debug(f"Wallet {signal.wallet_name} désactivé")
            return

        # Exécuter le trade
        result = self.executor.execute_copy_trade(signal.to_dict(), wallet_config)

        if result.get('status') == 'executed':
            self.signals_executed += 1
            logger.info(f"HFT Trade exécuté: ${result.get('value_usd', 0):.2f}")
        else:
            logger.warning(f"HFT Trade échoué: {result.get('message', 'Unknown')}")

    def _get_wallet_config(self, address: str) -> Optional[Dict]:
        """Récupère la configuration d'un wallet"""
        addr = address.lower()
        for wallet in self.config.get('tracked_wallets', []):
            if wallet.get('address', '').lower() == addr:
                return wallet
        return None

    # =========================================================================
    # GESTION DES WALLETS
    # =========================================================================

    def add_wallet(self, address: str, nickname: str = '', config: Dict = None) -> Dict:
        """Ajoute un wallet HFT à suivre"""
        addr = address.lower()

        # Vérifier si déjà présent
        for w in self.config.get('tracked_wallets', []):
            if w.get('address', '').lower() == addr:
                return {'success': False, 'message': 'Wallet déjà suivi'}

        wallet_config = {
            'address': addr,
            'nickname': nickname or f"HFT_{addr[:6]}",
            'capital_allocated': config.get('capital_allocated', 100) if config else 100,
            'percent_per_trade': config.get('percent_per_trade', 10) if config else 10,
            'max_daily_trades': config.get('max_daily_trades', 50) if config else 50,
            'enabled': True,
            'added_at': datetime.now().isoformat()
        }

        self.config['tracked_wallets'].append(wallet_config)
        self.save_config()

        # Ajouter au monitor
        self.trade_monitor.add_wallet(addr, wallet_config['nickname'], wallet_config)

        logger.info(f"Wallet HFT ajouté: {wallet_config['nickname']}")

        return {'success': True, 'wallet': wallet_config}

    def remove_wallet(self, address: str) -> Dict:
        """Retire un wallet HFT"""
        addr = address.lower()

        wallets = self.config.get('tracked_wallets', [])
        new_wallets = [w for w in wallets if w.get('address', '').lower() != addr]

        if len(new_wallets) == len(wallets):
            return {'success': False, 'message': 'Wallet non trouvé'}

        self.config['tracked_wallets'] = new_wallets
        self.save_config()

        # Retirer du monitor
        self.trade_monitor.remove_wallet(addr)

        logger.info(f"Wallet HFT retiré: {addr[:10]}...")

        return {'success': True}

    def update_wallet(self, address: str, updates: Dict) -> Dict:
        """Met à jour la configuration d'un wallet"""
        addr = address.lower()

        for wallet in self.config.get('tracked_wallets', []):
            if wallet.get('address', '').lower() == addr:
                for key, value in updates.items():
                    if key != 'address':  # Ne pas modifier l'adresse
                        wallet[key] = value

                self.save_config()
                logger.info(f"Wallet HFT mis à jour: {addr[:10]}...")

                return {'success': True, 'wallet': wallet}

        return {'success': False, 'message': 'Wallet non trouvé'}

    def get_wallets(self) -> List[Dict]:
        """Retourne la liste des wallets HFT"""
        return self.config.get('tracked_wallets', [])

    # =========================================================================
    # CONTRÔLE DU SCANNER
    # =========================================================================

    def start(self):
        """Démarre le scanner HFT"""
        if self._running:
            logger.warning("Scanner HFT déjà en cours")
            return

        self._running = True
        self.start_time = datetime.now()

        # Démarrer les composants
        self.market_discovery.start()
        self.trade_monitor.start()

        self.config['enabled'] = True
        self.save_config()

        logger.info("Scanner HFT démarré")

        # Notification
        if self.socketio:
            self.socketio.emit('hft_status', {'running': True}, namespace='/')

    def stop(self):
        """Arrête le scanner HFT"""
        self._running = False

        # Arrêter les composants
        self.market_discovery.stop()
        self.trade_monitor.stop()

        self.config['enabled'] = False
        self.save_config()

        logger.info("Scanner HFT arrêté")

        # Notification
        if self.socketio:
            self.socketio.emit('hft_status', {'running': False}, namespace='/')

    def toggle(self) -> bool:
        """Toggle le scanner et retourne le nouvel état"""
        if self._running:
            self.stop()
        else:
            self.start()
        return self._running

    # =========================================================================
    # STATS & EXPORT
    # =========================================================================

    def get_stats(self) -> Dict:
        """Retourne les statistiques complètes"""
        return {
            'running': self._running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'signals_received': self.signals_received,
            'signals_executed': self.signals_executed,
            'execution_rate': round(
                self.signals_executed / max(1, self.signals_received) * 100, 1
            ),
            'market_discovery': self.market_discovery.get_stats(),
            'trade_monitor': self.trade_monitor.get_stats(),
            'executor': self.executor.get_stats(),
            'tracked_wallets': len(self.config.get('tracked_wallets', []))
        }

    def get_active_markets(self) -> List[Dict]:
        """Retourne les marchés 15-min actifs"""
        markets = self.market_discovery.get_all_active_markets()
        return [m.to_dict() for m in markets]

    def get_recent_signals(self, limit: int = 50) -> List[Dict]:
        """Retourne les signaux récents"""
        return self.trade_monitor.get_recent_signals(limit)

    def get_trades_history(self, limit: int = 100) -> List[Dict]:
        """Retourne l'historique des trades HFT"""
        if self.db_manager:
            return self.db_manager.get_hft_trades(limit)
        return []
