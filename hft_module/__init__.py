# -*- coding: utf-8 -*-
"""
HFT Copy-Trading Module
=======================
Module dédié au copy-trading des apex HFT traders sur les marchés crypto 15-min de Polymarket.

Composants:
- market_discovery: Détection des marchés 15-min crypto via Gamma API
- trade_monitor: WebSocket monitoring temps réel (Polymarket + Polygon)
- hft_executor: Exécution rapide sans validation lourde
- hft_scanner: Orchestrateur principal
"""

from .market_discovery import HFTMarketDiscovery
from .trade_monitor import HFTTradeMonitor
from .hft_executor import HFTExecutor
from .hft_scanner import HFTScanner

__all__ = [
    'HFTMarketDiscovery',
    'HFTTradeMonitor',
    'HFTExecutor',
    'HFTScanner'
]

__version__ = '1.0.0'
