"""
NotificationAggregator - Gestion fluide des notifications de trades

Fonctionnalites:
- Deduplication par tx_hash (evite doublons WebSocket/polling)
- Distribution fluide (notifications espacees dans le temps)
- Cooldown configurable entre notifications
- Priority queue pour trades urgents (gros montants)
"""

import threading
import time
import logging
from queue import Queue, Empty
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TradeNotification:
    """Representation d'une notification de trade."""
    tx_hash: str
    wallet_address: str
    trader_name: str
    action: str  # 'BUY' ou 'SELL'
    market_question: str
    amount: float
    outcome: str
    timestamp: datetime
    source: str  # 'websocket' ou 'polling'
    priority: int = 0  # 0=normal, 1=high (gros montant)

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour emission WebSocket."""
        return {
            'tx_hash': self.tx_hash,
            'wallet': self.wallet_address,
            'trader_name': self.trader_name,
            'action': self.action,
            'market': self.market_question,
            'amount': self.amount,
            'outcome': self.outcome,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'source': self.source,
            'priority': 'high' if self.priority == 1 else 'normal'
        }


class NotificationAggregator:
    """
    Aggregateur intelligent de notifications de trades.

    Logique FLUIDE:
    - Trades haute priorite (>= seuil) -> IMMEDIATS
    - Autres trades -> mis en queue et distribues avec delai entre chaque
    - Deduplication par tx_hash (evite doublons WebSocket + polling)
    - Distribution fluide: 1 notification toutes les X ms
    """

    def __init__(self,
                 emit_callback: Callable,
                 emit_interval_ms: int = 500,
                 high_value_threshold: float = 1000):
        """
        Initialise l'aggregateur.

        Args:
            emit_callback: Fonction pour emettre les notifications (socketio.emit style)
            emit_interval_ms: Intervalle entre emissions en ms (defaut: 500ms)
            high_value_threshold: Seuil pour trades prioritaires (defaut: $1000)
        """
        self.emit_callback = emit_callback
        self.emit_interval_ms = emit_interval_ms
        self.high_value_threshold = high_value_threshold

        # Queue de notifications a distribuer
        self._notification_queue: Queue = Queue()
        self._seen_hashes: Dict[str, float] = {}  # tx_hash -> timestamp
        self._lock = threading.Lock()
        self._dedup_ttl = 3600  # 1 heure de retention pour deduplication

        # Worker thread pour distribution fluide
        self._running = True
        self._worker_thread: Optional[threading.Thread] = None

        # Stats
        self.stats = {
            'total_received': 0,
            'duplicates_filtered': 0,
            'immediate_sent': 0,
            'queued_sent': 0,
            'high_priority_sent': 0
        }

        # Demarrer le worker de distribution
        self._start_worker()

        logger.info(f"NotificationAggregator initialise: emit_interval={emit_interval_ms}ms, high_value_threshold=${high_value_threshold}")

    def _start_worker(self):
        """Demarre le worker thread pour distribution fluide."""
        def worker_loop():
            logger.info("Worker de distribution fluide demarre")
            while self._running:
                try:
                    # Attendre une notification (timeout pour permettre l'arret)
                    trade = self._notification_queue.get(timeout=1.0)

                    # Emettre la notification
                    self._emit_single(trade)
                    self.stats['queued_sent'] += 1

                    # Attendre avant la prochaine emission (fluidite)
                    time.sleep(self.emit_interval_ms / 1000)

                except Empty:
                    # Pas de notification en attente, continuer
                    continue
                except Exception as e:
                    logger.error(f"Erreur worker distribution: {e}")

            logger.info("Worker de distribution arrete")

        self._worker_thread = threading.Thread(target=worker_loop, daemon=True)
        self._worker_thread.start()

    def add_trade(self, trade: TradeNotification) -> bool:
        """
        Ajoute un trade au systeme de notification.

        Args:
            trade: Notification de trade a traiter

        Returns:
            True si accepte et programme pour emission, False si doublon
        """
        with self._lock:
            self.stats['total_received'] += 1

            # Deduplication par tx_hash
            if self._is_duplicate(trade.tx_hash):
                self.stats['duplicates_filtered'] += 1
                logger.debug(f"Doublon filtre: {trade.tx_hash[:16]}...")
                return False

            self._mark_seen(trade.tx_hash)

            # Determiner la priorite (gros montant = haute priorite)
            if trade.amount >= self.high_value_threshold:
                trade.priority = 1

            # Trade haute priorite = emission immediate (bypass la queue)
            if trade.priority == 1:
                logger.info(f"Trade haute priorite (${trade.amount:.0f}): emission immediate")
                self.stats['high_priority_sent'] += 1
                self._emit_single(trade)
                return True

            # Ajouter a la queue pour distribution fluide
            self._notification_queue.put(trade)
            queue_size = self._notification_queue.qsize()
            logger.debug(f"Trade ajoute a la queue (taille: {queue_size})")
            return True

    def add_trade_from_signal(self, signal: Dict) -> bool:
        """
        Cree un TradeNotification depuis un signal dict et l'ajoute.

        Args:
            signal: Dict avec les champs du signal de trade

        Returns:
            True si accepte, False si doublon
        """
        try:
            # Parser le timestamp
            ts = signal.get('timestamp')
            if isinstance(ts, str):
                try:
                    timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except ValueError:
                    timestamp = datetime.now()
            elif isinstance(ts, datetime):
                timestamp = ts
            else:
                timestamp = datetime.now()

            # Generer un tx_hash si absent (pour polling)
            tx_hash = signal.get('tx_hash')
            if not tx_hash:
                # Generer un hash unique base sur wallet + timestamp + market
                import hashlib
                hash_input = f"{signal.get('wallet', '')}_{signal.get('timestamp', '')}_{signal.get('market_question', '')}"
                tx_hash = f"poll_{hashlib.md5(hash_input.encode()).hexdigest()[:16]}"

            trade = TradeNotification(
                tx_hash=tx_hash,
                wallet_address=signal.get('wallet', ''),
                trader_name=signal.get('trader_name', 'Unknown'),
                action=signal.get('action', 'UNKNOWN'),
                market_question=signal.get('market_question', signal.get('market', '')),
                amount=float(signal.get('amount', 0)),
                outcome=signal.get('outcome', ''),
                timestamp=timestamp,
                source=signal.get('source', 'polling')
            )

            return self.add_trade(trade)

        except Exception as e:
            logger.error(f"Erreur creation TradeNotification depuis signal: {e}")
            return False

    def _is_duplicate(self, tx_hash: str) -> bool:
        """Verifie si ce tx_hash a deja ete traite."""
        if tx_hash in self._seen_hashes:
            return True

        # Nettoyer periodiquement les vieux hashes
        now = time.time()
        expired = [h for h, t in self._seen_hashes.items() if now - t > self._dedup_ttl]
        for h in expired:
            del self._seen_hashes[h]

        return False

    def _mark_seen(self, tx_hash: str):
        """Marque un tx_hash comme vu."""
        self._seen_hashes[tx_hash] = time.time()

    def _emit_single(self, trade: TradeNotification):
        """Emet une seule notification."""
        self.stats['immediate_sent'] += 1

        try:
            self.emit_callback('trade_signal', trade.to_dict())
            logger.info(f"📤 Notification: {trade.trader_name} {trade.action} ${trade.amount:.2f}")
        except Exception as e:
            logger.error(f"Erreur emission notification: {e}")

    def get_stats(self) -> Dict:
        """Retourne les statistiques de l'aggregateur."""
        with self._lock:
            return {
                **self.stats,
                'queue_size': self._notification_queue.qsize(),
                'seen_hashes_count': len(self._seen_hashes),
                'emit_interval_ms': self.emit_interval_ms,
                'high_value_threshold': self.high_value_threshold,
                'worker_running': self._running and self._worker_thread and self._worker_thread.is_alive()
            }

    def flush(self):
        """Force l'emission de toutes les notifications en attente."""
        count = 0
        while not self._notification_queue.empty():
            try:
                trade = self._notification_queue.get_nowait()
                self._emit_single(trade)
                count += 1
            except Empty:
                break
        if count > 0:
            logger.info(f"Flush force: {count} notifications emises")

    def clear_seen_hashes(self):
        """Vide le cache de deduplication."""
        with self._lock:
            count = len(self._seen_hashes)
            self._seen_hashes.clear()
            logger.info(f"Cache de deduplication vide: {count} hashes supprimes")

    def update_config(self, emit_interval_ms: int = None, high_value_threshold: float = None):
        """
        Met a jour la configuration a chaud.

        Args:
            emit_interval_ms: Nouvel intervalle entre emissions (optionnel)
            high_value_threshold: Nouveau seuil haute priorite (optionnel)
        """
        if emit_interval_ms is not None:
            self.emit_interval_ms = emit_interval_ms
            logger.info(f"Intervalle d'emission mis a jour: {emit_interval_ms}ms")

        if high_value_threshold is not None:
            self.high_value_threshold = high_value_threshold
            logger.info(f"Seuil haute priorite mis a jour: ${high_value_threshold}")

    def stop(self):
        """Arrete le worker de distribution."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        logger.info("NotificationAggregator arrete")
