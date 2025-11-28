# 🔧 MIGRATION: Élimination MODE TEST + Capital Réel Uniquement

## Modifications à effectuer:

### 1. bot_logic.py
- ❌ Supprimer `self.virtual_balance`
- ❌ Supprimer `total_capital` de config
- ✅ Utiliser uniquement `get_wallet_balance_dynamic()` (wallet réel)

### 2. config.json
- ❌ Supprimer `"total_capital": 1000`
- ❌ Supprimer toute référence MODE TEST
- ✅ Garder uniquement wallet_private_key

### 3. Interface (bot.py)
- ✅ Changer limite traders: 2 → 3
- ✅ Afficher capital réel du wallet uniquement
- ❌ Supprimer toggle MODE TEST/REAL
- ❌ Supprimer affichage capital fictif

### 4. backend
- ✅ 3 traders actifs max (déjà dans config)

## Ordre d'exécution:
1. Modifier bot_logic.py (éliminer virtual_balance)
2. Modifier config.json (supprimer total_capital)
3. Modifier bot.py interface (3 traders, wallet réel only)
4. Tester compilation
5. Commit GitHub
