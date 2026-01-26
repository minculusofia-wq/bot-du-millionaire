# Bot du Millionnaire - Polymarket Copy Trading 🚀

**Bot de copy trading automatisé pour Polymarket** (Polygon).

> **État du Projet** : ✅ Fonctionnel - Mode Réel Uniquement

---

## 📊 Fonctionnalités Principales

### 🎯 Polymarket Copy Trading
- ✅ **Suivi de wallets Polymarket** (Polygon)
- ✅ **Copie automatique des trades** des wallets suivis
- ✅ **Exécution Réelle** : Trades placés directement sur le CLOB (Central Limit Order Book)
- ✅ **Gestion des positions** : Min/Max USD configurables
- ✅ **Pourcentage de copie** : Ajustable (1-100%)
- ✅ **Statistiques en temps réel** : Signaux détectés, trades copiés, profit total, win rate
- ✅ **Vente de positions** : Interface pour revendre partiellement ou totalement ses positions


### 🌐 Interface Web Moderne
1. **Dashboard** - Vue d'ensemble, status et graphiques PnL
2. **Live Trading** - Flux des trades en temps réel
3. **Wallets Suivis** - Gestion des "Whales" à copier (avec configs individuelles)
4. **Historique** - Historique complet des trades et PnL
5. **⚡ HFT Copy** - Copy-trading des apex HFT traders (15-min crypto markets)
6. **Insider Scanner** - Détection de comportements suspects
7. **Paramètres** - Configuration API et gestion des risques

### ✨ Nouveautés v3.0 (Module HFT)
- **⚡ HFT Copy-Trading** : Nouveau module dédié au copy-trading des apex HFT traders (0x8dxd, PurpleThunderBicycleMountain).
- **🎯 Marchés 15-min Crypto** : Détection automatique des marchés BTC/ETH à 15 minutes via Gamma API.
- **🚀 Latence Optimisée** : Polling Goldsky toutes les 5 secondes pour une détection rapide des trades.
- **💰 Configuration Indépendante** : Wallets HFT séparés avec capital et % par trade configurables.
- **📊 Stats Live** : Signaux détectés, trades exécutés, taux d'exécution en temps réel.
- **🔧 Exécution Rapide** : 0.5% max slippage, 2s timeout, sans validation lourde.
- **🖥️ Auto-ouverture navigateur** : Le frontend s'ouvre automatiquement au lancement du bot.

### ✨ Nouveautés v2.9 (Audit & Optimisation)
- **🚀 Migration Polygonscan V2** : Passage à l'API Etherscan V2 pour une détection infaillible des wallets (V1 dépréciée).
- **⚖️ Seuils de Détection Optimisés** : Ajustement des cotes (0.35) et des montants ($300) pour capturer plus de signaux pertinents.
- **🛡️ Robustesse API** : Meilleure gestion des erreurs et logging détaillé pour le monitoring.

### ✨ Nouveautés v2.8
- **🚨 Scanner Insider Robuste** : Système de suppression d'alertes infaillible (Feed & Pending).
- **💾 Configuration Persistante** : Vos réglages scanner survivent au redémarrage.
- **🔗 Intégration Flux** : Liens directs vers les marchés Polymarket depuis le banner et le tableau.
- **📊 Données Précises** : Normalisation des montants USDC et affichage propre.

## 📋 Pré-requis Obligatoires
Pour utiliser ce bot, vous devez avoir des fonds sur **Polygon (MATIC)** :
1.  **USDC (Polygon)** : Sur votre compte Polymarket (Proxy) pour trader.
2.  **MATIC (Polygon)** : Sur votre wallet MetaMask/EOA pour les frais de réseau (1-2$ suffisent).

### ⚡ Optimisations v2.4
- **🔍 Insider Scanner Integrations** : Goldsky & Polygonscan pour une précision maximale.
- **🔄 Sync Auto** : Synchronisation entre le Copy Trading et le Scanner.
- **🎨 Interface** : Amélioration des modals et badges de source.

### ⚡ Optimisations v2.2
- **🛡️ Sécurité Maximale (Machine Binding)** : Vos identifiants sont désormais physiquement liés à votre matériel (UUID). Même en cas de vol du fichier `.env`, ils sont indéchiffrables sur une autre machine.
- **🚀 Réactivité Accrue** : Intervalle de surveillance réduit à **5 secondes** pour une copie quasi instantanée.
- **🧠 Kelly Criterion Dynamique** : La taille des positions s'adapte maintenant aux prix réels du carnet d'ordres (Market Odds) en temps réel.
- **⚙️ Interface Identifiants** : Gérez vos clés API directement via l'interface web (Paramètres), chiffrées automatiquement via SecretManager.

### ⚡ Optimisations v2.1
- **🔐 Anti-double vente** : Système de locks pour éviter les ventes simultanées d'une même position.
- **🔄 Réconciliation au démarrage** : Vérification et nettoyage automatique des positions orphelines.
- **📝 Logging structuré** : Logs colorés, rotation automatique, fichiers séparés (bot.log, errors.log, trades.log).

### 🕵️ Insider Trading Scanner
Un système avancé de détection de comportements suspects sur Polymarket :
- **Détection d'Anomalies** : Identifie les mises improbables (gros montants sur faibles probabilités), les profils suspects (nouveaux wallets) et les "whale movements".
- **Intégration Goldsky & Polygonscan** : Analyse profonde de l'historique des wallets et de l'activité du marché via subgraphs et API blockchain.
- **Alertes Temps Réel** : Notification immédiate lors de la détection de patterns de trading non-naturels.
- **Scoring Intelligent** : Algorithme de notation (0-100) pour évaluer la "suspicion" d'une transaction.

---

## ⚡ Module HFT Copy-Trading

Le module HFT permet de copier les apex HFT traders sur les marchés crypto 15-min de Polymarket.

### Architecture
```
+------------------+     +------------------+     +------------------+
|  Market Filter   | --> |  Trade Monitor   | --> |  Fast Executor   |
| (Gamma API 60s)  |     | (Goldsky 5s)     |     | (CLOB <2s)       |
+------------------+     +------------------+     +------------------+
```

### Utilisation
1. Allez sur l'onglet **⚡ HFT Copy**
2. Ajoutez les wallets HFT à suivre (ex: 0x8dxd, PurpleThunder)
3. Configurez le capital et le % par trade pour chaque wallet
4. Activez le scanner avec le bouton **Démarrer**

### Wallets HFT Recommandés
- **0x8dxd** : `0x63ce342161250d705dc0b16df89036c8e5f9ba9a`
- **PurpleThunderBicycleMountain** : `0x589222a5124a96765443b97a3498d89ffd824ad2`

---

## 🚀 Installation

### Prérequis
- Python 3.9 ou supérieur
- Compte Polymarket avec clés API (pour le trading réel)
- Wallet Polygon (USDC)

### Installation
```bash
git clone https://github.com/minculusofia-wq/bot-du-millionaire-copy-trade-polymarket.git
cd bot-du-millionaire-copy-trade-polymarket
pip install -r requirements.txt
```

### Configuration
1. Copiez le fichier d'exemple :
   ```bash
   cp .env.example .env
   ```
2. Configurez vos clés dans `.env` :
   ```bash
   # API Polymarket (Requis pour placer des ordres)
   POLYMARKET_API_KEY=votre_clé
   POLYMARKET_SECRET=votre_secret
   POLYMARKET_PASSPHRASE=votre_passphrase

   # Clé privée Polygon (Requis pour signer les tx)
   POLYGON_PRIVATE_KEY=votre_clé_privée

   # Polygonscan API (Recommandé pour le tracking)
   POLYGONSCAN_API_KEY=votre_clé_polygonscan
   ```

### Lancement
```bash
./start_bot.sh
```
Le navigateur s'ouvre automatiquement sur : **http://localhost:5000**

---

## 🔒 Sécurité
- ⚠️ **Vos clés privées restent sur votre machine**. Elles ne sont jamais envoyées ailleurs que sur les serveurs de Polymarket/Polygon pour signer.
- ✅ Il est recommandé d'utiliser un wallet dédié au bot, et non votre wallet principal.
- ✅ Commencez avec de petits montants.

## ⚠️ Avertissement
Ce logiciel est fourni à titre expérimental. Le trading de crypto-monnaies et les marchés de prédiction comportent des risques financiers importants. L'auteur n'est pas responsable des pertes potentielles. Usez de prudence.
