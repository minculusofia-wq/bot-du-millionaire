# -*- coding: utf-8 -*-
"""
HFT Routes - API Flask pour le module HFT
Routes dédiées au copy-trading HFT, séparées du reste de l'application.
"""
from flask import Blueprint, jsonify, request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HFTRoutes")

hft_bp = Blueprint('hft', __name__, url_prefix='/api/hft')

# Référence au scanner HFT (injecté depuis bot.py)
hft_scanner = None


def init_hft_routes(scanner):
    """Initialise les routes avec le scanner HFT"""
    global hft_scanner
    hft_scanner = scanner
    logger.info("Routes HFT initialisées")


# ============================================================================
# STATUS & CONTROL
# ============================================================================

@hft_bp.route('/status', methods=['GET'])
def hft_status():
    """Status complet du module HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    return jsonify({
        'success': True,
        'stats': hft_scanner.get_stats()
    })


@hft_bp.route('/toggle', methods=['POST'])
def hft_toggle():
    """Démarre ou arrête le scanner HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    running = hft_scanner.toggle()

    return jsonify({
        'success': True,
        'running': running
    })


@hft_bp.route('/start', methods=['POST'])
def hft_start():
    """Démarre le scanner HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    hft_scanner.start()

    return jsonify({
        'success': True,
        'running': True
    })


@hft_bp.route('/stop', methods=['POST'])
def hft_stop():
    """Arrête le scanner HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    hft_scanner.stop()

    return jsonify({
        'success': True,
        'running': False
    })


# ============================================================================
# CONFIGURATION
# ============================================================================

@hft_bp.route('/config', methods=['GET'])
def hft_get_config():
    """Récupère la configuration HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    return jsonify({
        'success': True,
        'config': hft_scanner.get_config()
    })


@hft_bp.route('/config', methods=['POST'])
def hft_set_config():
    """Met à jour la configuration HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    data = request.get_json() or {}

    hft_scanner.set_config(data)

    return jsonify({
        'success': True,
        'config': hft_scanner.get_config()
    })


# ============================================================================
# WALLETS
# ============================================================================

@hft_bp.route('/wallets', methods=['GET'])
def hft_get_wallets():
    """Liste des wallets HFT suivis"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    return jsonify({
        'success': True,
        'wallets': hft_scanner.get_wallets()
    })


@hft_bp.route('/wallets/add', methods=['POST'])
def hft_add_wallet():
    """Ajoute un wallet HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    data = request.get_json() or {}

    address = data.get('address', '').strip()
    nickname = data.get('nickname', '').strip()

    if not address:
        return jsonify({'error': 'Adresse requise'}), 400

    # Config optionnelle
    config = {
        'capital_allocated': float(data.get('capital_allocated', 100)),
        'percent_per_trade': float(data.get('percent_per_trade', 10)),
        'max_daily_trades': int(data.get('max_daily_trades', 50))
    }

    result = hft_scanner.add_wallet(address, nickname, config)

    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 400


@hft_bp.route('/wallets/remove', methods=['POST'])
def hft_remove_wallet():
    """Retire un wallet HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    data = request.get_json() or {}
    address = data.get('address', '').strip()

    if not address:
        return jsonify({'error': 'Adresse requise'}), 400

    result = hft_scanner.remove_wallet(address)

    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 400


@hft_bp.route('/wallets/update', methods=['POST'])
def hft_update_wallet():
    """Met à jour la configuration d'un wallet HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    data = request.get_json() or {}
    address = data.get('address', '').strip()

    if not address:
        return jsonify({'error': 'Adresse requise'}), 400

    # Extraire les updates
    updates = {}
    if 'nickname' in data:
        updates['nickname'] = data['nickname']
    if 'capital_allocated' in data:
        updates['capital_allocated'] = float(data['capital_allocated'])
    if 'percent_per_trade' in data:
        updates['percent_per_trade'] = float(data['percent_per_trade'])
    if 'max_daily_trades' in data:
        updates['max_daily_trades'] = int(data['max_daily_trades'])
    if 'enabled' in data:
        updates['enabled'] = bool(data['enabled'])
    if 'sl_percent' in data:
        updates['sl_percent'] = float(data['sl_percent']) if data['sl_percent'] is not None else None
    if 'tp_percent' in data:
        updates['tp_percent'] = float(data['tp_percent']) if data['tp_percent'] is not None else None

    result = hft_scanner.update_wallet(address, updates)

    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 400


# ============================================================================
# MARKETS
# ============================================================================

@hft_bp.route('/markets', methods=['GET'])
def hft_get_markets():
    """Liste des marchés 15-min crypto actifs"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    return jsonify({
        'success': True,
        'markets': hft_scanner.get_active_markets()
    })


@hft_bp.route('/markets/refresh', methods=['POST'])
def hft_refresh_markets():
    """Force le refresh des marchés"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    count = hft_scanner.market_discovery.refresh()

    return jsonify({
        'success': True,
        'markets_found': count
    })


# ============================================================================
# SIGNALS & TRADES
# ============================================================================

@hft_bp.route('/signals', methods=['GET'])
def hft_get_signals():
    """Signaux récents"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    limit = request.args.get('limit', 50, type=int)

    return jsonify({
        'success': True,
        'signals': hft_scanner.get_recent_signals(limit)
    })


@hft_bp.route('/trades', methods=['GET'])
def hft_get_trades():
    """Historique des trades HFT"""
    if not hft_scanner:
        return jsonify({'error': 'Module HFT non initialisé'}), 503

    limit = request.args.get('limit', 100, type=int)

    return jsonify({
        'success': True,
        'trades': hft_scanner.get_trades_history(limit)
    })
