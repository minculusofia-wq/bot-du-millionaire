# -*- coding: utf-8 -*-
"""
Advanced Risk Manager - Gestion avancée du risque
Inclut circuit breaker, Kelly criterion, position sizing intelligent
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from db_manager import db_manager
import json
import os


class AdvancedRiskManager:
    """Gestionnaire de risque avancé avec circuit breaker"""

    # Valeurs par défaut (utilisées si pas de sauvegarde)
    DEFAULT_PARAMS = {
        'circuit_breaker_threshold': 15,  # 15%
        'circuit_breaker_cooldown': 3600,  # 1 heure
        'max_consecutive_losses': 5,
        'max_position_size_percent': 20,  # 20%
        'max_daily_loss_percent': 10,  # 10%
        'max_drawdown_percent': 25,  # 25%
        'kelly_safety_factor': 0.5,  # Demi-Kelly
        'save_params': False  # Pas de sauvegarde par défaut
    }

    def __init__(self, total_capital: float = 1000, config_path: str = 'config.json'):
        self.total_capital = total_capital
        self.current_balance = total_capital
        self.peak_balance = total_capital
        self.config_path = config_path

        # Charger les paramètres (depuis config.json si sauvegarde activée, sinon défaut)
        params = self._load_params()

        # Circuit Breaker Configuration
        self.circuit_breaker_active = False
        self.circuit_breaker_threshold = params['circuit_breaker_threshold'] / 100  # Convertir en fraction
        self.circuit_breaker_cooldown = params['circuit_breaker_cooldown']
        self.circuit_breaker_triggered_at = None

        # Risk Limits
        self.max_position_size_percent = params['max_position_size_percent'] / 100
        self.max_daily_loss_percent = params['max_daily_loss_percent'] / 100
        self.max_drawdown_percent = params['max_drawdown_percent'] / 100

        # Kelly Criterion
        self.kelly_safety_factor = params['kelly_safety_factor']

        # Tracking
        self.daily_pnl = 0
        self.daily_reset_time = datetime.now()
        self.consecutive_losses = 0
        self.max_consecutive_losses = params['max_consecutive_losses']

        # Sauvegarde activée ou non
        self.save_params_enabled = params['save_params']

        print(f"🛡️ Risk Manager initialisé (Sauvegarde: {'✅' if self.save_params_enabled else '❌'})")

    def _load_params(self) -> Dict:
        """
        Charge les paramètres depuis config.json si sauvegarde activée,
        sinon retourne les valeurs par défaut
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                    # Vérifier si la section risk_manager existe et si save_params est True
                    if 'risk_manager' in config and config['risk_manager'].get('save_params', False):
                        print("✅ Chargement des paramètres Risk Manager depuis config.json")
                        return config['risk_manager']
        except Exception as e:
            print(f"⚠️ Erreur chargement config Risk Manager: {e}")

        # Retourner les valeurs par défaut
        print("ℹ️ Utilisation des paramètres Risk Manager par défaut")
        return self.DEFAULT_PARAMS.copy()

    def is_circuit_breaker_active(self) -> bool:
        """
        Vérifie si le circuit breaker est actif

        Returns:
            True si le circuit breaker est actif
        """
        # Si pas activé, retourner False
        if not self.circuit_breaker_active:
            return False

        # Vérifier le cooldown
        if self.circuit_breaker_triggered_at:
            elapsed = (datetime.now() - self.circuit_breaker_triggered_at).total_seconds()
            if elapsed >= self.circuit_breaker_cooldown:
                # Cooldown terminé, désactiver le circuit breaker
                self.circuit_breaker_active = False
                self.circuit_breaker_triggered_at = None
                print("✅ Circuit breaker désactivé après cooldown")
                return False

        return True

    def check_and_trigger_circuit_breaker(self) -> bool:
        """
        Vérifie et active le circuit breaker si nécessaire

        Returns:
            True si le circuit breaker a été activé
        """
        # Vérifier le drawdown
        drawdown_check = self.check_drawdown()
        if drawdown_check['is_max_drawdown']:
            self._trigger_circuit_breaker("Max drawdown atteint")
            return True

        # Vérifier les pertes consécutives
        if self.consecutive_losses >= self.max_consecutive_losses:
            self._trigger_circuit_breaker(f"{self.consecutive_losses} pertes consécutives")
            return True

        # Vérifier la perte journalière
        daily_loss_percent = (self.daily_pnl / self.total_capital) * 100
        if daily_loss_percent <= -self.max_daily_loss_percent * 100:
            self._trigger_circuit_breaker(f"Perte journalière de {daily_loss_percent:.1f}%")
            return True

        return False

    def _trigger_circuit_breaker(self, reason: str):
        """Active le circuit breaker"""
        self.circuit_breaker_active = True
        self.circuit_breaker_triggered_at = datetime.now()
        print(f"🚨 CIRCUIT BREAKER ACTIVÉ: {reason}")
        print(f"⏳ Cooldown: {self.circuit_breaker_cooldown}s")

    def calculate_kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calcule le Kelly Criterion pour le position sizing optimal

        Kelly% = (Win Rate * Avg Win - (1 - Win Rate) * Avg Loss) / Avg Win

        Args:
            win_rate: Taux de réussite (0-1)
            avg_win: Gain moyen par trade gagnant
            avg_loss: Perte moyenne par trade perdant (valeur positive)

        Returns:
            Fraction du capital à risquer (0-1)
        """
        if avg_win <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.02  # Par défaut: 2% du capital

        # Formule de Kelly
        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        # Appliquer un facteur de sécurité (demi-Kelly)
        safe_kelly = kelly * 0.5

        # Limiter entre 0 et max_position_size
        return max(0.01, min(safe_kelly, self.max_position_size_percent))

    def get_position_size(self, trader_confidence: float, capital_alloc: float) -> float:
        """
        Calcule la taille de position optimale

        Args:
            trader_confidence: Confiance dans le trader (0-1)
            capital_alloc: Capital alloué pour ce trade

        Returns:
            Taille de position ajustée
        """
        # Ajuster selon la confiance
        adjusted_size = capital_alloc * (0.5 + trader_confidence * 0.5)

        # Appliquer la limite max par position
        max_position = self.current_balance * self.max_position_size_percent
        adjusted_size = min(adjusted_size, max_position)

        return adjusted_size

    def check_drawdown(self) -> Dict:
        """
        Vérifie le drawdown actuel

        Returns:
            Dict avec drawdown_percent et is_max_drawdown
        """
        if self.peak_balance <= 0:
            return {'drawdown_percent': 0, 'is_max_drawdown': False}

        # Mettre à jour le peak si nécessaire
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

        # Calculer le drawdown
        drawdown = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100

        is_max_dd = drawdown >= (self.max_drawdown_percent * 100)

        return {
            'drawdown_percent': round(drawdown, 2),
            'is_max_drawdown': is_max_dd,
            'peak_balance': self.peak_balance,
            'current_balance': self.current_balance
        }

    def update_balance(self, pnl: float):
        """
        Met à jour le balance et les métriques de risque

        Args:
            pnl: Profit/Loss du trade
        """
        self.current_balance += pnl

        # Mettre à jour le PnL journalier
        self._reset_daily_if_needed()
        self.daily_pnl += pnl

        # Mettre à jour les pertes consécutives
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Vérifier si circuit breaker doit être activé
        self.check_and_trigger_circuit_breaker()

    def _reset_daily_if_needed(self):
        """Réinitialise les stats journalières si nouveau jour"""
        now = datetime.now()
        if now.date() > self.daily_reset_time.date():
            self.daily_pnl = 0
            self.daily_reset_time = now
            print("🔄 Stats journalières réinitialisées")

    def get_risk_metrics(self) -> Dict:
        """
        Retourne toutes les métriques de risque

        Returns:
            Dictionnaire avec toutes les métriques
        """
        drawdown_info = self.check_drawdown()

        return {
            'circuit_breaker_active': self.is_circuit_breaker_active(),
            'current_balance': round(self.current_balance, 2),
            'peak_balance': round(self.peak_balance, 2),
            'drawdown_percent': drawdown_info['drawdown_percent'],
            'daily_pnl': round(self.daily_pnl, 2),
            'consecutive_losses': self.consecutive_losses,
            'max_position_size_percent': self.max_position_size_percent * 100,
            'max_daily_loss_percent': self.max_daily_loss_percent * 100,
            'max_drawdown_percent': self.max_drawdown_percent * 100
        }

    def get_params(self) -> Dict:
        """
        Retourne tous les paramètres configurables

        Returns:
            Dictionnaire avec tous les paramètres (en pourcentages/secondes)
        """
        return {
            'circuit_breaker_threshold': self.circuit_breaker_threshold * 100,
            'circuit_breaker_cooldown': self.circuit_breaker_cooldown,
            'max_consecutive_losses': self.max_consecutive_losses,
            'max_position_size_percent': self.max_position_size_percent * 100,
            'max_daily_loss_percent': self.max_daily_loss_percent * 100,
            'max_drawdown_percent': self.max_drawdown_percent * 100,
            'kelly_safety_factor': self.kelly_safety_factor,
            'save_params': self.save_params_enabled
        }

    def update_params(self, params: Dict) -> Dict:
        """
        Met à jour les paramètres du Risk Manager

        Args:
            params: Dictionnaire avec les nouveaux paramètres

        Returns:
            {'success': True/False, 'message': str}
        """
        try:
            # Mettre à jour les paramètres en mémoire
            if 'circuit_breaker_threshold' in params:
                self.circuit_breaker_threshold = float(params['circuit_breaker_threshold']) / 100

            if 'circuit_breaker_cooldown' in params:
                self.circuit_breaker_cooldown = int(params['circuit_breaker_cooldown'])

            if 'max_consecutive_losses' in params:
                self.max_consecutive_losses = int(params['max_consecutive_losses'])

            if 'max_position_size_percent' in params:
                self.max_position_size_percent = float(params['max_position_size_percent']) / 100

            if 'max_daily_loss_percent' in params:
                self.max_daily_loss_percent = float(params['max_daily_loss_percent']) / 100

            if 'max_drawdown_percent' in params:
                self.max_drawdown_percent = float(params['max_drawdown_percent']) / 100

            if 'kelly_safety_factor' in params:
                self.kelly_safety_factor = float(params['kelly_safety_factor'])

            if 'save_params' in params:
                self.save_params_enabled = bool(params['save_params'])

            # Sauvegarder dans config.json si activé
            if self.save_params_enabled:
                self._save_to_config()
                print("✅ Paramètres Risk Manager sauvegardés dans config.json")
            else:
                print("ℹ️ Paramètres Risk Manager mis à jour (mémoire uniquement)")

            return {
                'success': True,
                'message': 'Paramètres mis à jour avec succès',
                'saved_to_disk': self.save_params_enabled
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur: {str(e)}'
            }

    def _save_to_config(self):
        """Sauvegarde les paramètres dans config.json"""
        try:
            # Charger config existante
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # Mettre à jour la section risk_manager
            config['risk_manager'] = {
                'circuit_breaker_threshold': self.circuit_breaker_threshold * 100,
                'circuit_breaker_cooldown': self.circuit_breaker_cooldown,
                'max_consecutive_losses': self.max_consecutive_losses,
                'max_position_size_percent': self.max_position_size_percent * 100,
                'max_daily_loss_percent': self.max_daily_loss_percent * 100,
                'max_drawdown_percent': self.max_drawdown_percent * 100,
                'kelly_safety_factor': self.kelly_safety_factor,
                'save_params': self.save_params_enabled
            }

            # Sauvegarder
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"❌ Erreur sauvegarde config: {e}")

    def reset_to_defaults(self) -> Dict:
        """
        Réinitialise tous les paramètres aux valeurs par défaut

        Returns:
            {'success': True, 'message': str}
        """
        defaults = self.DEFAULT_PARAMS.copy()
        return self.update_params(defaults)


# Instance globale - Capital chargé depuis config.json
def _get_capital_from_config():
    """Charge le capital total depuis config.json"""
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('total_capital', 1000)
    except Exception as e:
        print(f"⚠️ Erreur chargement capital: {e}")
    return 1000  # Défaut si erreur

risk_manager = AdvancedRiskManager(total_capital=_get_capital_from_config())
