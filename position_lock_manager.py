# -*- coding: utf-8 -*-
"""
Position Lock Manager
Empêche les opérations concurrentes sur une même position (anti-double vente).
"""
import threading
import time
import logging
from typing import Dict, Optional, Set
from contextlib import contextmanager
from datetime import datetime, timedelta

logger = logging.getLogger("PositionLockManager")


class PositionLockManager:
    """
    Gestionnaire de verrous pour les positions.
    Empêche deux threads de vendre la même position simultanément.
    """

    def __init__(self, lock_timeout: int = 30):
        """
        Args:
            lock_timeout: Durée max d'un verrou en secondes (évite les deadlocks)
        """
        self._locks: Dict[int, threading.Lock] = {}
        self._lock_times: Dict[int, datetime] = {}
        self._master_lock = threading.Lock()
        self._locked_positions: Set[int] = set()
        self.lock_timeout = lock_timeout

        # Thread de nettoyage des verrous expirés
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

        logger.info(f"🔒 PositionLockManager initialisé (timeout: {lock_timeout}s)")

    def _get_lock(self, position_id: int) -> threading.Lock:
        """Récupère ou crée un verrou pour une position."""
        with self._master_lock:
            if position_id not in self._locks:
                self._locks[position_id] = threading.Lock()
            return self._locks[position_id]

    def acquire(self, position_id: int, blocking: bool = True, timeout: float = 10) -> bool:
        """
        Acquiert le verrou sur une position.

        Args:
            position_id: ID de la position
            blocking: Attendre si déjà verrouillé
            timeout: Timeout en secondes si blocking=True

        Returns:
            True si verrou acquis, False sinon
        """
        lock = self._get_lock(position_id)

        acquired = lock.acquire(blocking=blocking, timeout=timeout)

        if acquired:
            with self._master_lock:
                self._locked_positions.add(position_id)
                self._lock_times[position_id] = datetime.now()
            logger.debug(f"🔐 Position #{position_id} verrouillée")
        else:
            logger.warning(f"⚠️ Impossible de verrouiller position #{position_id} (déjà en cours)")

        return acquired

    def release(self, position_id: int):
        """Libère le verrou sur une position."""
        lock = self._get_lock(position_id)

        try:
            lock.release()
            with self._master_lock:
                self._locked_positions.discard(position_id)
                self._lock_times.pop(position_id, None)
            logger.debug(f"🔓 Position #{position_id} déverrouillée")
        except RuntimeError:
            # Lock pas acquis par ce thread
            pass

    def is_locked(self, position_id: int) -> bool:
        """Vérifie si une position est verrouillée."""
        with self._master_lock:
            return position_id in self._locked_positions

    @contextmanager
    def lock(self, position_id: int, timeout: float = 10):
        """
        Context manager pour verrouiller une position.

        Usage:
            with position_lock.lock(position_id):
                # Opérations sur la position

        Raises:
            PositionLockError si impossible d'acquérir le verrou
        """
        if not self.acquire(position_id, blocking=True, timeout=timeout):
            raise PositionLockError(f"Position #{position_id} déjà en cours de traitement")

        try:
            yield
        finally:
            self.release(position_id)

    def try_lock(self, position_id: int) -> bool:
        """
        Tente d'acquérir le verrou sans bloquer.

        Returns:
            True si verrou acquis, False si déjà verrouillé
        """
        return self.acquire(position_id, blocking=False)

    def _cleanup_loop(self):
        """Nettoie les verrous expirés (protection anti-deadlock)."""
        while True:
            time.sleep(10)  # Check toutes les 10s
            self._cleanup_expired()

    def _cleanup_expired(self):
        """Libère les verrous dépassant le timeout."""
        now = datetime.now()
        expired = []

        with self._master_lock:
            for pos_id, lock_time in list(self._lock_times.items()):
                if now - lock_time > timedelta(seconds=self.lock_timeout):
                    expired.append(pos_id)

        for pos_id in expired:
            logger.warning(f"⚠️ Verrou expiré sur position #{pos_id} - libération forcée")
            self.release(pos_id)

    def get_locked_positions(self) -> Set[int]:
        """Retourne l'ensemble des positions actuellement verrouillées."""
        with self._master_lock:
            return self._locked_positions.copy()

    def get_stats(self) -> Dict:
        """Statistiques du lock manager."""
        with self._master_lock:
            return {
                'active_locks': len(self._locked_positions),
                'locked_positions': list(self._locked_positions),
                'lock_timeout': self.lock_timeout
            }


class PositionLockError(Exception):
    """Exception levée quand un verrou ne peut être acquis."""
    pass


# Instance globale
position_lock = PositionLockManager()
