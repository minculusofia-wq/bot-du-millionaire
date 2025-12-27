# -*- coding: utf-8 -*-
"""
Startup Reconciler
Réconcilie l'état des positions au démarrage du bot.
Détecte les positions orphelines et les synchronise avec l'état réel.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from db_manager import db_manager

logger = logging.getLogger("StartupReconciler")


class StartupReconciler:
    """
    Réconcilie les positions au démarrage du bot.

    Responsabilités:
    - Détecter les positions OPEN qui auraient dû être fermées
    - Marquer les positions périmées comme STALE
    - Nettoyer les positions incohérentes
    - Générer un rapport de réconciliation
    """

    def __init__(self, executor=None):
        """
        Args:
            executor: PolymarketExecutor pour récupérer les prix actuels
        """
        self.executor = executor
        self.report = {
            'timestamp': None,
            'positions_checked': 0,
            'positions_updated': 0,
            'positions_closed': 0,
            'positions_stale': 0,
            'errors': [],
            'details': []
        }

    def reconcile(self) -> Dict:
        """
        Exécute la réconciliation complète au démarrage.

        Returns:
            Rapport de réconciliation
        """
        logger.info("🔄 Démarrage de la réconciliation des positions...")
        self.report['timestamp'] = datetime.now().isoformat()

        try:
            # 1. Récupérer toutes les positions OPEN
            open_positions = db_manager.get_bot_positions(status='OPEN')
            self.report['positions_checked'] = len(open_positions)

            if not open_positions:
                logger.info("✅ Aucune position ouverte à réconcilier")
                return self.report

            logger.info(f"📊 {len(open_positions)} positions ouvertes à vérifier")

            # 2. Vérifier chaque position
            for position in open_positions:
                self._check_position(position)

            # 3. Générer le résumé
            self._generate_summary()

            return self.report

        except Exception as e:
            logger.error(f"❌ Erreur lors de la réconciliation: {e}")
            self.report['errors'].append(str(e))
            return self.report

    def _check_position(self, position: Dict):
        """Vérifie et réconcilie une position individuelle."""
        pos_id = position.get('id')
        token_id = position.get('token_id')
        market = position.get('market_slug', 'unknown')
        opened_at = position.get('opened_at')

        try:
            # 1. Vérifier l'âge de la position
            age_issue = self._check_position_age(position)

            # 2. Vérifier si le prix est disponible
            price_issue = self._check_price_availability(position)

            # 3. Vérifier les données manquantes
            data_issue = self._check_data_integrity(position)

            # 4. Décider de l'action à prendre
            if age_issue == 'STALE':
                self._mark_as_stale(position, "Position trop ancienne sans mise à jour")
            elif price_issue:
                self._mark_as_stale(position, f"Prix non disponible: {price_issue}")
            elif data_issue:
                self._log_issue(position, f"Données incomplètes: {data_issue}")
            else:
                # Position OK - mettre à jour le prix si possible
                self._update_position_price(position)

        except Exception as e:
            self.report['errors'].append(f"Position #{pos_id}: {str(e)}")
            logger.error(f"❌ Erreur check position #{pos_id}: {e}")

    def _check_position_age(self, position: Dict) -> str:
        """
        Vérifie si la position est trop ancienne.

        Returns:
            'OK', 'WARNING', ou 'STALE'
        """
        last_updated = position.get('last_updated') or position.get('opened_at')
        if not last_updated:
            return 'STALE'

        try:
            last_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            age = datetime.now() - last_dt.replace(tzinfo=None)

            # Position non mise à jour depuis plus de 7 jours = STALE
            if age > timedelta(days=7):
                return 'STALE'
            # Position non mise à jour depuis plus de 24h = WARNING
            elif age > timedelta(hours=24):
                return 'WARNING'
            return 'OK'
        except:
            return 'STALE'

    def _check_price_availability(self, position: Dict) -> str:
        """Vérifie si le prix est disponible pour la position."""
        if not self.executor:
            return None  # Pas d'executor, on ne peut pas vérifier

        token_id = position.get('token_id')
        if not token_id:
            return "Token ID manquant"

        try:
            price = self.executor.get_market_price(token_id, 'SELL')
            if not price or price <= 0:
                return "Prix non disponible sur le marché"
            return None
        except Exception as e:
            return str(e)

    def _check_data_integrity(self, position: Dict) -> str:
        """Vérifie l'intégrité des données de la position."""
        issues = []

        required_fields = ['token_id', 'shares', 'entry_price']
        for field in required_fields:
            if not position.get(field):
                issues.append(f"{field} manquant")

        if position.get('shares', 0) <= 0:
            issues.append("shares <= 0")

        if position.get('entry_price', 0) <= 0:
            issues.append("entry_price <= 0")

        return ", ".join(issues) if issues else None

    def _mark_as_stale(self, position: Dict, reason: str):
        """Marque une position comme STALE."""
        pos_id = position.get('id')
        logger.warning(f"⚠️ Position #{pos_id} marquée STALE: {reason}")

        db_manager.execute_query('''
            UPDATE bot_positions
            SET status = 'STALE', last_updated = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), pos_id), commit=True)

        self.report['positions_stale'] += 1
        self.report['details'].append({
            'position_id': pos_id,
            'action': 'MARKED_STALE',
            'reason': reason
        })

    def _update_position_price(self, position: Dict):
        """Met à jour le prix actuel de la position."""
        if not self.executor:
            return

        pos_id = position.get('id')
        token_id = position.get('token_id')

        try:
            current_price = self.executor.get_market_price(token_id, 'SELL')
            if current_price and current_price > 0:
                entry_price = position.get('entry_price', 0)
                shares = position.get('shares', 0)

                # Calcul du PnL non réalisé
                unrealized_pnl = (current_price - entry_price) * shares

                db_manager.execute_query('''
                    UPDATE bot_positions
                    SET current_price = ?, unrealized_pnl = ?, last_updated = ?
                    WHERE id = ?
                ''', (current_price, unrealized_pnl, datetime.now().isoformat(), pos_id), commit=True)

                self.report['positions_updated'] += 1
                logger.debug(f"📊 Position #{pos_id} mise à jour: ${current_price:.4f}")

        except Exception as e:
            logger.error(f"❌ Erreur mise à jour prix #{pos_id}: {e}")

    def _log_issue(self, position: Dict, issue: str):
        """Log un problème sans action corrective."""
        pos_id = position.get('id')
        logger.warning(f"⚠️ Position #{pos_id}: {issue}")
        self.report['details'].append({
            'position_id': pos_id,
            'action': 'LOGGED',
            'issue': issue
        })

    def _generate_summary(self):
        """Génère le résumé de la réconciliation."""
        logger.info("=" * 50)
        logger.info("📋 RAPPORT DE RÉCONCILIATION")
        logger.info("=" * 50)
        logger.info(f"   Positions vérifiées: {self.report['positions_checked']}")
        logger.info(f"   Positions mises à jour: {self.report['positions_updated']}")
        logger.info(f"   Positions STALE: {self.report['positions_stale']}")
        logger.info(f"   Erreurs: {len(self.report['errors'])}")
        logger.info("=" * 50)

    def get_stale_positions(self) -> List[Dict]:
        """Récupère les positions marquées comme STALE."""
        return db_manager.get_bot_positions(status='STALE')

    def cleanup_stale_positions(self, max_age_days: int = 30) -> int:
        """
        Nettoie les positions STALE trop anciennes.

        Args:
            max_age_days: Âge maximum en jours avant suppression

        Returns:
            Nombre de positions supprimées
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)

        result = db_manager.execute_query('''
            DELETE FROM bot_positions
            WHERE status = 'STALE' AND opened_at < ?
        ''', (cutoff.isoformat(),), commit=True)

        deleted = result.rowcount if hasattr(result, 'rowcount') else 0
        logger.info(f"🗑️ {deleted} positions STALE supprimées (>{max_age_days} jours)")
        return deleted


def run_startup_reconciliation(executor=None) -> Dict:
    """
    Fonction helper pour exécuter la réconciliation au démarrage.

    Args:
        executor: PolymarketExecutor (optionnel)

    Returns:
        Rapport de réconciliation
    """
    reconciler = StartupReconciler(executor)
    return reconciler.reconcile()


# Export
__all__ = ['StartupReconciler', 'run_startup_reconciliation']
