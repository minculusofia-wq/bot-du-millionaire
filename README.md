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
5. **Paramètres** - Configuration API et gestion des risques

### ✨ Nouveautés v2.4 (Dernière Mise à Jour)
- **🔍 Insider Scanner v2.4** : Intégration profonde de la blockchain via **Goldsky** et **Polygonscan** pour une analyse précise des positions et du PnL des wallets.
- **📊 Stats Persistantes** : Les wallets sauvegardés mémorisent désormais leur **PnL** et **WinRate** en base de données, avec affiche direct sur les cartes de l'interface.
- **🔄 Synchronisation Auto** : Vos wallets suivis pour le Copy Trading sont automatiquement synchronisés avec le module Insider au démarrage.
- **🎨 Interface Adaptative** : Fenêtres de configuration (modals) désormais entièrement scrollables et badges de source (`SCANNER` / `MANUAL`) ajoutés.
- **🛠️ Robustesse Backend** : Profilage en arrière-plan et réconciliation automatique des données pour une expérience fluide.

### ⚡ Optimisations v2.2
- **🛡️ Sécurité Maximale (Machine Binding)** : Vos identifiants sont désormais physiquement liés à votre matériel (UUID). Même en cas de vol du fichier `.env`, ils sont indéchiffrables sur une autre machine.
- **🚀 Réactivité Accrue** : Intervalle de surveillance réduit à **5 secondes** pour une copie quasi instantanée.
- **🧠 Kelly Criterion Dynamique** : La taille des positions s'adapte maintenant aux prix réels du carnet d'ordres (Market Odds) en temps réel.
- **⚙️ Interface Identifiants** : Gérez vos clés API directement via l'interface web (Paramètres), chiffrées automatiquement via SecretManager.

### ⚡ Optimisations v2.1
- **🔐 Anti-double vente** : Système de locks pour éviter les ventes simultanées d'une même position.
- **🔄 Réconciliation au démarrage** : Vérification et nettoyage automatique des positions orphelines.
- **📝 Logging structuré** : Logs colorés, rotation automatique, fichiers séparés (bot.log, errors.log, trades.log).

### 🕵️ Insider Trading Scanner (Nouveau v2.4)
Un système avancé de détection de comportements suspects sur Polymarket :
- **Détection d'Anomalies** : Identifie les mises improbables (gros montants sur faibles probabilités), les profils suspects (nouveaux wallets) et les "whale movements".
- **Intégration Goldsky & Polygonscan** : Analyse profonde de l'historique des wallets et de l'activité du marché via subgraphs et API blockchain.
- **Alertes Temps Réel** : Notification immédiate lors de la détection de patterns de trading non-naturels.
- **Scoring Intelligent** : Algorithme de notation (0-100) pour évaluer la "suspicion" d'une transaction.

---

## 🚀 Installation

### Prérequis
- Python 3.9 ou supérieur
- Compte Polymarket avec clés API (pour le trading réel)
- Wallet Polygon (USDC)

### Installation
```bash
git clone https://github.com/votre-repo/bot-du-millionaire.git
cd bot-du-millionaire
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
   ```

### Lancement
```bash
python bot.py
```
Accédez à l'interface sur : **http://localhost:5000**

---

## 🔒 Sécurité
- ⚠️ **Vos clés privées restent sur votre machine**. Elles ne sont jamais envoyées ailleurs que sur les serveurs de Polymarket/Polygon pour signer.
- ✅ Il est recommandé d'utiliser un wallet dédié au bot, et non votre wallet principal.
- ✅ Commencez avec de petits montants.

## ⚠️ Avertissement
Ce logiciel est fourni à titre expérimental. Le trading de crypto-monnaies et les marchés de prédiction comportent des risques financiers importants. L'auteur n'est pas responsable des pertes potentielles. Usez de prudence.
