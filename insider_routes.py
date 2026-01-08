# -*- coding: utf-8 -*-
"""
Flask Routes pour Insider Tracker
API endpoints pour la detection et le suivi de wallets suspects sur Polymarket
"""
from flask import Blueprint, jsonify, request
from insider_scanner import insider_scanner
from db_manager import db_manager

# Blueprint pour les routes insider
insider_bp = Blueprint('insider', __name__, url_prefix='/api/insider')


@insider_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """
    GET /api/insider/alerts
    Recupere le feed d'alertes (les plus recentes)

    Query params:
      - limit: int (default 100)
      - min_score: int (default 0)
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        min_score = request.args.get('min_score', 0, type=int)

        alerts = db_manager.get_insider_alerts(limit=limit, min_score=min_score)

        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@insider_bp.route('/markets', methods=['GET'])
def get_scanned_markets():
    """
    GET /api/insider/markets
    Retourne les infos sur les marches scannes
    """
    try:
        stats = insider_scanner.get_stats()

        return jsonify({
            'success': True,
            'categories': stats.get('enabled_categories', []),
            'markets_scanned': stats.get('markets_scanned', 0),
            'last_scan': stats.get('last_scan')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@insider_bp.route('/save_wallet', methods=['POST'])
def save_wallet():
    """
    POST /api/insider/save_wallet
    Sauvegarde un wallet pour suivi ulterieur

    Body: {address: str, nickname?: str, notes?: str}
    """
    try:
        data = request.get_json() or {}
        address = data.get('address', '').strip()
        nickname = data.get('nickname', '').strip()
        notes = data.get('notes', '').strip()

        if not address:
            return jsonify({'success': False, 'error': 'Address required'}), 400

        if not address.startswith('0x') or len(address) != 42:
            return jsonify({'success': False, 'error': 'Invalid Polygon address'}), 400

        # Sauvegarder en DB
        wallet_id = db_manager.save_insider_wallet({
            'address': address,
            'nickname': nickname,
            'notes': notes
        })

        return jsonify({
            'success': True,
            'wallet_id': wallet_id,
            'message': 'Wallet saved successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@insider_bp.route('/saved', methods=['GET'])
def get_saved_wallets():
    """
    GET /api/insider/saved
    Recupere la liste des wallets sauvegardes
    """
    try:
        wallets = db_manager.get_saved_insider_wallets()

        return jsonify({
            'success': True,
            'wallets': wallets,
            'count': len(wallets)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@insider_bp.route('/saved/<address>', methods=['DELETE'])
def delete_saved_wallet(address):
    """
    DELETE /api/insider/saved/<address>
    Supprime un wallet de la liste sauvegardee
    """
    try:
        db_manager.delete_insider_wallet(address)

        return jsonify({
            'success': True,
            'message': 'Wallet removed successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@insider_bp.route('/wallet_stats/<address>', methods=['GET'])
def get_wallet_stats(address):
    """
    GET /api/insider/wallet_stats/<address>
    Recupere les statistiques de performance d'un wallet
    """
    try:
        # Stats live depuis Polymarket
        stats = insider_scanner.get_wallet_performance(address)

        # Historique des alertes pour ce wallet
        alerts_history = db_manager.get_wallet_alerts_history(address, limit=20)

        return jsonify({
            'success': True,
            'address': address,
            'stats': stats,
            'alerts_history': alerts_history,
            'alerts_count': len(alerts_history)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@insider_bp.route('/config', methods=['GET', 'POST'])
def scanner_config():
    """
    GET/POST /api/insider/config
    Recupere ou met a jour la configuration du scanner
    """
    if request.method == 'GET':
        try:
            config = insider_scanner.get_config()
            return jsonify({
                'success': True,
                'config': config
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # POST - Mise a jour config
    try:
        data = request.get_json() or {}

        # Valider et appliquer les changements
        new_config = {}

        # Scoring preset
        if 'scoring_preset' in data:
            new_config['scoring_preset'] = data['scoring_preset']

        # Seuil d'alerte
        if 'alert_threshold' in data:
            threshold = int(data['alert_threshold'])
            if 0 <= threshold <= 100:
                new_config['alert_threshold'] = threshold

        # Categories
        if 'categories' in data and isinstance(data['categories'], list):
            new_config['categories'] = data['categories']

        # Poids custom
        if 'custom_weights' in data and isinstance(data['custom_weights'], dict):
            weights = data['custom_weights']
            # Normaliser si necessaire
            total = sum(weights.values())
            if total > 0:
                new_config['custom_weights'] = {
                    k: int(v * 100 / total) for k, v in weights.items()
                }

        # Seuils de detection
        threshold_fields = [
            'min_bet_amount', 'max_odds_threshold', 'dormant_days',
            'dormant_min_bet', 'max_tx_count', 'new_wallet_min_bet'
        ]
        for field in threshold_fields:
            if field in data:
                try:
                    if field == 'max_odds_threshold':
                        # Convertir pourcentage en decimal
                        val = float(data[field])
                        new_config[field] = val / 100 if val > 1 else val
                    else:
                        new_config[field] = float(data[field])
                except (ValueError, TypeError):
                    pass

        # Intervalle de scan
        if 'scan_interval' in data:
            try:
                interval = int(data['scan_interval'])
                if 10 <= interval <= 300:
                    insider_scanner.scan_interval = interval
            except (ValueError, TypeError):
                pass

        # Appliquer la config
        if new_config:
            insider_scanner.set_config(new_config)

        return jsonify({
            'success': True,
            'message': 'Configuration updated',
            'config': insider_scanner.get_config()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@insider_bp.route('/toggle', methods=['POST'])
def toggle_scanner():
    """
    POST /api/insider/toggle
    Demarre ou arrete le scanner

    Body: {enabled: bool}
    """
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', False)

        if enabled:
            insider_scanner.start_scanning()
            message = 'Scanner started'
        else:
            insider_scanner.stop_scanning()
            message = 'Scanner stopped'

        return jsonify({
            'success': True,
            'running': insider_scanner.running,
            'message': message
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@insider_bp.route('/stats', methods=['GET'])
def get_scanner_stats():
    """
    GET /api/insider/stats
    Recupere les statistiques du scanner
    """
    try:
        stats = insider_scanner.get_stats()

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@insider_bp.route('/scan_now', methods=['POST'])
def trigger_scan():
    """
    POST /api/insider/scan_now
    Declenche un scan manuel immediat (sans demarrer la boucle)
    """
    try:
        alerts = insider_scanner.scan_all_markets()

        return jsonify({
            'success': True,
            'alerts_found': len(alerts),
            'alerts': [a.to_dict() for a in alerts] if alerts else [],
            'message': f'Scan complete: {len(alerts)} alert(s) found'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
