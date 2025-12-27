# -*- coding: utf-8 -*-
"""
Logging Configuration
Système de logging structuré avec rotation des fichiers et niveaux configurables.
"""
import os
import sys
import logging
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional

# Répertoire des logs
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')


class ColoredFormatter(logging.Formatter):
    """Formatter avec couleurs pour la console."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Vert
        'WARNING': '\033[33m',   # Jaune
        'ERROR': '\033[31m',     # Rouge
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        # Ajouter la couleur
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname_colored = f"{color}{record.levelname}{self.RESET}"

        # Format de base
        message = super().format(record)

        # Remplacer le levelname par la version colorée
        return message.replace(record.levelname, record.levelname_colored)


class JSONFormatter(logging.Formatter):
    """Formatter JSON pour les logs structurés."""

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Ajouter les extras si présents
        if hasattr(record, 'extra_data'):
            log_data['data'] = record.extra_data

        # Ajouter l'exception si présente
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    level: str = 'INFO',
    log_to_file: bool = True,
    log_to_console: bool = True,
    json_logs: bool = False,
    max_file_size_mb: int = 10,
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure le système de logging pour l'application.

    Args:
        level: Niveau de log ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_to_file: Activer les logs fichier
        log_to_console: Activer les logs console
        json_logs: Utiliser le format JSON pour les fichiers
        max_file_size_mb: Taille max des fichiers de log en MB
        backup_count: Nombre de fichiers de backup à conserver

    Returns:
        Logger racine configuré
    """
    # Créer le répertoire de logs si nécessaire
    if log_to_file and not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Récupérer le logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Supprimer les handlers existants
    root_logger.handlers.clear()

    # Format standard
    standard_format = '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Handler Console
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Utiliser le formatter coloré si terminal supporté
        if sys.stdout.isatty():
            console_formatter = ColoredFormatter(standard_format, datefmt=date_format)
        else:
            console_formatter = logging.Formatter(standard_format, datefmt=date_format)

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Handler Fichier
    if log_to_file:
        # Fichier principal avec rotation par taille
        main_log_path = os.path.join(LOG_DIR, 'bot.log')
        file_handler = RotatingFileHandler(
            main_log_path,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Fichier capture tout

        if json_logs:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(standard_format, datefmt=date_format))

        root_logger.addHandler(file_handler)

        # Fichier d'erreurs séparé
        error_log_path = os.path.join(LOG_DIR, 'errors.log')
        error_handler = RotatingFileHandler(
            error_log_path,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(standard_format, datefmt=date_format))
        root_logger.addHandler(error_handler)

        # Fichier trades (pour audit)
        trades_log_path = os.path.join(LOG_DIR, 'trades.log')
        trades_handler = RotatingFileHandler(
            trades_log_path,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=10,  # Garder plus de backups pour les trades
            encoding='utf-8'
        )
        trades_handler.setLevel(logging.INFO)
        trades_handler.addFilter(TradeLogFilter())
        trades_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(trades_handler)

    # Log du démarrage
    root_logger.info(f"Logging configuré - Niveau: {level}, Fichier: {log_to_file}, Console: {log_to_console}")

    return root_logger


class TradeLogFilter(logging.Filter):
    """Filtre pour capturer uniquement les logs de trading."""

    TRADE_LOGGERS = ['PolymarketExecutor', 'PolymarketTracker', 'TrailingStopMonitor']

    def filter(self, record):
        return record.name in self.TRADE_LOGGERS or 'trade' in record.getMessage().lower()


def get_logger(name: str) -> logging.Logger:
    """
    Récupère un logger configuré pour un module.

    Args:
        name: Nom du logger (généralement __name__)

    Returns:
        Logger configuré
    """
    return logging.getLogger(name)


def log_trade(
    logger: logging.Logger,
    action: str,
    position_id: Optional[int] = None,
    market: Optional[str] = None,
    side: Optional[str] = None,
    amount: Optional[float] = None,
    price: Optional[float] = None,
    pnl: Optional[float] = None,
    **extra
):
    """
    Log structuré pour les trades.

    Args:
        logger: Logger à utiliser
        action: Type d'action (BUY, SELL, CLOSE, etc.)
        position_id: ID de la position
        market: Slug du marché
        side: Côté (BUY/SELL)
        amount: Montant
        price: Prix
        pnl: PnL réalisé
        **extra: Données supplémentaires
    """
    trade_data = {
        'action': action,
        'position_id': position_id,
        'market': market,
        'side': side,
        'amount': amount,
        'price': price,
        'pnl': pnl,
        **extra
    }

    # Filtrer les None
    trade_data = {k: v for k, v in trade_data.items() if v is not None}

    # Créer un record avec les données
    record = logger.makeRecord(
        logger.name, logging.INFO, '', 0,
        f"TRADE: {action} - {json.dumps(trade_data, default=str)}",
        None, None
    )
    record.extra_data = trade_data

    logger.handle(record)


# Configuration par défaut au chargement du module
def init_default_logging():
    """Initialise le logging avec la configuration par défaut."""
    level = os.getenv('LOG_LEVEL', 'INFO')
    log_to_file = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    json_logs = os.getenv('JSON_LOGS', 'false').lower() == 'true'

    setup_logging(
        level=level,
        log_to_file=log_to_file,
        json_logs=json_logs
    )


# Export
__all__ = ['setup_logging', 'get_logger', 'log_trade', 'init_default_logging', 'LOG_DIR']
