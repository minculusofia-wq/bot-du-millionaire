"""
Gestionnaire de vente automatique et manuelle
- Détecte les ventes du trader
- Vend automatiquement en respectant TP/SL
- Permet vente manuelle
- Identique en MODE TEST et MODE REEL
"""

import json
from datetime import datetime
from typing import Dict, Optional, List
from db_manager import db_manager

class AutoSellManager:
    """Gère la vente automatique et manuelle"""
    
    def __init__(self):
        self.open_positions = self._load_open_positions()
        self.auto_sell_enabled = True  # Enabled by default
        self.auto_sell_settings = self._load_auto_sell_settings()
        
    def _load_open_positions(self) -> Dict:
        """Charge les positions ouvertes"""
        try:
            with open('open_positions.json', 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_open_positions(self):
        """Sauvegarde les positions ouvertes"""
        with open('open_positions.json', 'w') as f:
            json.dump(self.open_positions, f, indent=2)
        
        # Synchroniser avec la DB
        for pos_id, position in self.open_positions.items():
            db_manager.execute(
                """
                INSERT OR REPLACE INTO open_positions 
                (position_id, trader_name, entry_price, amount, entry_time, tp_percent, sl_percent, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pos_id,
                    position.get('trader_name', ''),
                    position.get('entry_price', 0),
                    position.get('amount', 0),
                    position.get('entry_time', datetime.now().isoformat()),
                    position.get('tp_percent', 10),
                    position.get('sl_percent', 5),
                    position.get('status', 'OPEN')
                )
            )
    
    def _load_auto_sell_settings(self) -> Dict:
        """Charge les paramètres de vente automatique"""
        try:
            with open('auto_sell_config.json', 'r') as f:
                return json.load(f)
        except:
            return {
                'enabled': True,
                'auto_sell_on_trader_sell': True,
                'respect_tp_sl': True,
                'tp_levels': [
                    {'percent_of_position': 33, 'profit_target': 10},
                    {'percent_of_position': 33, 'profit_target': 25},
                    {'percent_of_position': 34, 'profit_target': 50}
                ],
                'sl_level': {'percent_of_position': 100, 'loss_limit': 5}
            }
    
    def _save_auto_sell_settings(self):
        """Sauvegarde les paramètres"""
        with open('auto_sell_config.json', 'w') as f:
            json.dump(self.auto_sell_settings, f, indent=2)
    
    def open_position(self, 
                     trader_name: str,
                     entry_price: float,
                     amount: float,
                     tp_percent: float = 10,
                     sl_percent: float = 5) -> Dict:
        """
        Ouvre une nouvelle position
        IDENTIQUE en TEST et REAL
        """
        position_id = f"{trader_name}_{datetime.now().timestamp()}"
        
        position = {
            'position_id': position_id,
            'trader_name': trader_name,
            'entry_price': entry_price,
            'amount': amount,
            'tp_percent': tp_percent,
            'sl_percent': sl_percent,
            'entry_time': datetime.now().isoformat(),
            'status': 'OPEN',
            'current_price': entry_price,
            'pnl': 0,
            'pnl_percent': 0,
            'tp_price': entry_price * (1 + tp_percent / 100),
            'sl_price': entry_price * (1 - sl_percent / 100),
            'sell_reason': None,
            'exit_time': None,
            'exit_price': None
        }
        
        self.open_positions[position_id] = position
        self._save_open_positions()
        
        return position
    
    def update_position_price(self, position_id: str, current_price: float) -> Optional[Dict]:
        """
        Met à jour le prix d'une position et vérifie les conditions de sortie
        Respecte automatiquement TP/SL
        """
        if position_id not in self.open_positions:
            return None
        
        position = self.open_positions[position_id]
        
        if position['status'] != 'OPEN':
            return position
        
        # Calculer PnL
        pnl = (current_price - position['entry_price']) * position['amount']
        pnl_percent = ((current_price - position['entry_price']) / position['entry_price']) * 100
        
        position['current_price'] = current_price
        position['pnl'] = pnl
        position['pnl_percent'] = pnl_percent
        
        # Vérifier les conditions de sortie automatiques
        exit_reason = self._check_auto_sell_conditions(position, current_price)
        
        if exit_reason:
            # Fermer automatiquement
            self.close_position(position_id, current_price, exit_reason, 'AUTO')
            return self.open_positions.get(position_id)
        
        self._save_open_positions()
        return position
    
    def _check_auto_sell_conditions(self, position: Dict, current_price: float) -> Optional[str]:
        """
        Vérifie les conditions de vente automatique
        TP et SL sont vérifiés
        """
        if position['status'] != 'OPEN':
            return None
        
        # Vérifier TP
        if current_price >= position['tp_price']:
            return 'TP_HIT'
        
        # Vérifier SL
        if current_price <= position['sl_price']:
            return 'SL_HIT'
        
        return None
    
    def close_position(self, 
                      position_id: str, 
                      exit_price: float,
                      reason: str,
                      sell_type: str = 'MANUAL') -> Dict:
        """
        Ferme une position (automatique ou manuelle)
        IDENTIQUE en TEST et REAL
        
        sell_type: 'AUTO' = automatique, 'MANUAL' = manuel, 'TRADER_SELL' = trader vend
        """
        if position_id not in self.open_positions:
            return {'error': f'Position {position_id} not found'}
        
        position = self.open_positions[position_id]
        
        # Calculer PnL final
        final_pnl = (exit_price - position['entry_price']) * position['amount']
        final_pnl_percent = ((exit_price - position['entry_price']) / position['entry_price']) * 100
        
        # Mettre à jour la position
        position['status'] = 'CLOSED'
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now().isoformat()
        position['sell_reason'] = reason
        position['sell_type'] = sell_type
        position['final_pnl'] = final_pnl
        position['final_pnl_percent'] = final_pnl_percent
        
        self._save_open_positions()
        
        # Log dans la DB
        db_manager.execute(
            """
            INSERT INTO trade_history 
            (trader_name, entry_price, exit_price, amount, pnl, pnl_percent, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position['trader_name'],
                position['entry_price'],
                exit_price,
                position['amount'],
                final_pnl,
                final_pnl_percent,
                f"{reason}_{sell_type}",
                datetime.now().isoformat()
            )
        )
        
        return position
    
    def manual_sell(self, position_id: str, current_price: float) -> Dict:
        """
        Vente manuelle par l'utilisateur
        IDENTIQUE en TEST et REAL
        """
        if position_id not in self.open_positions:
            return {'error': f'Position {position_id} not found'}
        
        return self.close_position(position_id, current_price, 'MANUAL_SELL', 'MANUAL')
    
    def get_open_positions(self, trader_name: str = None) -> List[Dict]:
        """Récupère les positions ouvertes"""
        positions = []
        for pos_id, position in self.open_positions.items():
            if position['status'] == 'OPEN':
                if trader_name is None or position['trader_name'] == trader_name:
                    positions.append(position)
        return positions
    
    def get_closed_positions(self, trader_name: str = None) -> List[Dict]:
        """Récupère les positions fermées"""
        positions = []
        for pos_id, position in self.open_positions.items():
            if position['status'] == 'CLOSED':
                if trader_name is None or position['trader_name'] == trader_name:
                    positions.append(position)
        return positions
    
    def get_position_summary(self) -> Dict:
        """Résumé de toutes les positions"""
        open_positions = self.get_open_positions()
        closed_positions = self.get_closed_positions()
        
        total_open_pnl = sum(p['pnl'] for p in open_positions)
        total_closed_pnl = sum(p.get('final_pnl', 0) for p in closed_positions)
        total_pnl = total_open_pnl + total_closed_pnl
        
        return {
            'open_positions_count': len(open_positions),
            'closed_positions_count': len(closed_positions),
            'total_open_pnl': total_open_pnl,
            'total_closed_pnl': total_closed_pnl,
            'total_pnl': total_pnl,
            'open_positions': open_positions,
            'closed_positions': closed_positions[-10:]  # Dernières 10
        }
    
    def update_auto_sell_settings(self, settings: Dict) -> Dict:
        """Met à jour les paramètres de vente auto"""
        self.auto_sell_settings.update(settings)
        self._save_auto_sell_settings()
        return self.auto_sell_settings
    
    def get_auto_sell_settings(self) -> Dict:
        """Récupère les paramètres actuels"""
        return self.auto_sell_settings
    
    def detect_trader_sell(self, trader_name: str, trader_transactions: List[Dict]) -> List[Dict]:
        """
        Détecte quand le trader vend
        Récupère les positions ouvertes correspondantes et les ferme
        """
        closed_positions = []
        
        # Récupérer les positions ouvertes du trader
        open_positions = self.get_open_positions(trader_name)
        
        for transaction in trader_transactions:
            if transaction.get('type') == 'SELL':
                # Le trader a vendu
                # Fermer les positions ouvertes correspondantes au prorata
                for position in open_positions:
                    if position['status'] == 'OPEN':
                        exit_price = transaction.get('price', position['current_price'])
                        closed = self.close_position(
                            position['position_id'],
                            exit_price,
                            'TRADER_SOLD',
                            'AUTO'
                        )
                        closed_positions.append(closed)
        
        return closed_positions

# Instance globale
auto_sell_manager = AutoSellManager()
