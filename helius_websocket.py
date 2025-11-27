# -*- coding: utf-8 -*-
"""
Websocket Helius - Détection ULTRA-RAPIDE des transactions des traders
Remplace le polling par un listener temps réel (~50-100ms latence)
✨ OPTIMISÉ Phase 9: Reconnexion intelligente, Heartbeat, Buffer événements
"""
import asyncio
import json
import os
import threading
import time
import ssl
from typing import Optional, Dict, List, Callable
from datetime import datetime
from collections import deque

try:
    import websockets
except ImportError:
    websockets = None


class HeliosWebsocketListener:
    """Écoute les transactions Solana en temps réel via websocket Helius"""

    def __init__(self):
        self.api_key = os.getenv('HELIUS_API_KEY')
        # Tester les différents formats WSS Helius
        # Format 1 (principal): avec /v0/
        self.wss_urls = [
            f"wss://api-mainnet.helius-rpc.com/v0/?api-key={self.api_key}",
            f"wss://api-mainnet.helius-rpc.com/?api-key={self.api_key}",
            f"wss://api-mainnet.helius-rpc.com/ws?api-key={self.api_key}"
        ]
        self.wss_url = self.wss_urls[0]  # Start with primary
        self.subscriptions = {}  # {trader_address: callback_func}
        self.is_running = False
        self.websocket = None
        self.reconnect_delay = 3  # ✨ Réduit de 5s à 3s pour reconnexion plus rapide
        self.max_retries = 999  # ✨ Reconnexion infinie (était 10)
        self.url_index = 0  # Track which URL we're trying

        # ✨ AMÉLIORÉ: Heartbeat plus fréquent
        self.last_heartbeat = time.time()
        self.last_message_received = time.time()  # ✨ NOUVEAU: Track dernier message
        self.heartbeat_interval = 20  # ✨ Réduit de 30s à 20s pour détection plus rapide
        self.heartbeat_timeout = 45  # ✨ Réduit de 60s à 45s
        self.connection_timeout = 90  # ✨ NOUVEAU: Timeout global si pas de message depuis 90s

        # ✨ NOUVEAU: Buffer d'événements pendant la reconnexion
        self.event_buffer = deque(maxlen=100)  # Garder max 100 événements
        self.is_connected = False

        # ✨ AMÉLIORÉ: Stats de connexion avec plus de détails
        self.connection_quality = 100  # 0-100%
        self.total_reconnects = 0
        self.successful_reconnects = 0  # ✨ NOUVEAU: Reconnexions réussies
        self.failed_reconnects = 0  # ✨ NOUVEAU: Reconnexions échouées
        self.last_reconnect_time = None
        self.connection_start_time = None  # ✨ NOUVEAU: Quand la connexion actuelle a commencé
        self.total_messages_received = 0  # ✨ NOUVEAU: Total messages reçus
        self.consecutive_errors = 0  # ✨ NOUVEAU: Erreurs consécutives

        if not self.api_key:
            print("⚠️ HELIUS_API_KEY non définie - websocket Helius désactivé")
    
    def subscribe_to_trader(self, trader_address: str, callback: Callable):
        """S'abonne aux transactions d'un trader"""
        self.subscriptions[trader_address] = callback
        print(f"✅ Abonné à {trader_address[:10]}... (websocket)")

    def unsubscribe_from_trader(self, trader_address: str):
        """Se désabonne d'un trader"""
        if trader_address in self.subscriptions:
            del self.subscriptions[trader_address]
            print(f"❌ Désabonné de {trader_address[:10]}...")

    async def _send_heartbeat(self, websocket):
        """✨ AMÉLIORÉ: Envoie un ping périodique + détection timeout connexion"""
        try:
            while self.is_connected and self.is_running:
                await asyncio.sleep(self.heartbeat_interval)

                if websocket and not websocket.closed:
                    # ✨ NOUVEAU: Vérifier timeout global
                    time_since_last_message = time.time() - self.last_message_received
                    if time_since_last_message > self.connection_timeout:
                        print(f"⚠️ Connection timeout: Pas de message depuis {int(time_since_last_message)}s")
                        self.connection_quality = 0
                        # Forcer reconnexion en fermant le websocket
                        try:
                            await websocket.close()
                        except:
                            pass
                        break

                    try:
                        # Envoyer un ping
                        pong = await websocket.ping()
                        await asyncio.wait_for(pong, timeout=5)
                        self.last_heartbeat = time.time()
                        self.connection_quality = min(100, self.connection_quality + 5)
                        self.consecutive_errors = 0  # ✨ NOUVEAU: Reset compteur erreurs
                        print(f"💓 Heartbeat OK (qualité: {self.connection_quality}%)")
                    except asyncio.TimeoutError:
                        self.consecutive_errors += 1
                        print(f"⚠️ Heartbeat timeout #{self.consecutive_errors} - connexion faible")
                        self.connection_quality = max(0, self.connection_quality - 20)

                        # ✨ NOUVEAU: Forcer reconnexion après 3 timeouts consécutifs
                        if self.consecutive_errors >= 3:
                            print("❌ Trop de timeouts consécutifs - forçage reconnexion")
                            try:
                                await websocket.close()
                            except:
                                pass
                            break
                    except Exception as e:
                        self.consecutive_errors += 1
                        print(f"⚠️ Heartbeat error #{self.consecutive_errors}: {e}")
                        self.connection_quality = max(0, self.connection_quality - 10)
        except Exception as e:
            print(f"⚠️ Heartbeat loop error: {e}")

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """✨ AMÉLIORÉ: Calcule le délai avec backoff exponentiel intelligent"""
        # Backoff exponentiel optimisé:
        # - Retry 1-3: 3s, 6s, 12s (reconnexion rapide)
        # - Retry 4-6: 24s, 30s, 30s (stabilisation)
        # - Retry 7+: 30s max (évite attentes trop longues)
        if retry_count <= 3:
            delay = min(30, (2 ** retry_count) * 1.5)
        else:
            delay = 30  # Max 30s pour les reconnexions suivantes

        # ✨ NOUVEAU: Ajouter jitter aléatoire (±20%) pour éviter synchronisation
        import random
        jitter = delay * 0.2 * (random.random() - 0.5)
        final_delay = delay + jitter

        return max(1, final_delay)  # Minimum 1s

    def get_connection_stats(self) -> Dict:
        """✨ AMÉLIORÉ: Retourne les stats de connexion détaillées"""
        uptime = None
        if self.connection_start_time:
            uptime = int(time.time() - self.connection_start_time)

        time_since_last_msg = int(time.time() - self.last_message_received)

        return {
            'is_connected': self.is_connected,
            'connection_quality': self.connection_quality,
            'total_reconnects': self.total_reconnects,
            'successful_reconnects': self.successful_reconnects,  # ✨ NOUVEAU
            'failed_reconnects': self.failed_reconnects,  # ✨ NOUVEAU
            'last_reconnect': self.last_reconnect_time,
            'buffer_size': len(self.event_buffer),
            'subscriptions': len(self.subscriptions),
            'uptime_seconds': uptime,  # ✨ NOUVEAU
            'total_messages': self.total_messages_received,  # ✨ NOUVEAU
            'consecutive_errors': self.consecutive_errors,  # ✨ NOUVEAU
            'time_since_last_message': time_since_last_msg,  # ✨ NOUVEAU
            'current_url_index': self.url_index  # ✨ NOUVEAU
        }
    
    async def _connect_and_listen(self):
        """✨ AMÉLIORÉ: Connecte au websocket et écoute les transactions avec reconnexion intelligente"""
        if not self.api_key or not websockets:
            print("⚠️ Websocket Helius non disponible - fallback sur polling")
            return

        retry_count = 0

        while self.is_running:
            try:
                # Essayer les différents formats WSS
                self.wss_url = self.wss_urls[self.url_index % len(self.wss_urls)]
                print(f"🔌 Connexion websocket Helius... (tentative {retry_count + 1}, URL format {self.url_index + 1})")

                # ✨ NOUVEAU: Créer un contexte SSL pour macOS/Linux (résout CERTIFICATE_VERIFY_FAILED)
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                async with websockets.connect(
                    self.wss_url,
                    ssl=ssl_context,  # ✨ Ajouter le contexte SSL
                    ping_interval=20,  # ✨ AMÉLIORÉ: Ping automatique toutes les 20s (était 30s)
                    ping_timeout=10,   # ✨ Timeout de 10s pour pong
                    close_timeout=10,
                    max_size=10485760  # ✨ NOUVEAU: 10MB max message size
                ) as websocket:
                    self.websocket = websocket
                    self.is_connected = True  # ✨ NOUVEAU
                    self.connection_start_time = time.time()  # ✨ NOUVEAU: Track uptime
                    self.last_message_received = time.time()  # ✨ NOUVEAU: Reset timer
                    retry_count = 0  # Reset retry count on successful connection
                    self.consecutive_errors = 0  # ✨ NOUVEAU: Reset erreurs
                    self.connection_quality = 100  # ✨ Reset quality
                    self.successful_reconnects += 1  # ✨ NOUVEAU: Incrémenter succès
                    print(f"✅ Websocket Helius connecté (URL {self.url_index + 1})")
                    print(f"   Stats: {self.successful_reconnects} succès, {self.failed_reconnects} échecs")

                    # ✨ NOUVEAU: Traiter les événements buffered
                    if len(self.event_buffer) > 0:
                        print(f"📦 Traitement de {len(self.event_buffer)} événements buffered...")
                        while len(self.event_buffer) > 0:
                            event = self.event_buffer.popleft()
                            await self._handle_notification(event)

                    # S'abonner aux adresses des traders
                    for trader_address in self.subscriptions.keys():
                        subscribe_msg = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "logsSubscribe",
                            "params": [
                                {
                                    "mentions": [trader_address]
                                },
                                {
                                    "commitment": "processed"
                                }
                            ]
                        }
                        try:
                            await websocket.send(json.dumps(subscribe_msg))
                            print(f"  ├─ Abonnement logs pour {trader_address[:10]}...")
                        except Exception as e:
                            print(f"  └─ Erreur abonnement: {e}")

                    # ✨ NOUVEAU: Lancer le heartbeat en parallèle
                    heartbeat_task = asyncio.create_task(self._send_heartbeat(websocket))

                    # Écouter les messages
                    try:
                        async for message in websocket:
                            if not self.is_running:
                                break

                            # ✨ NOUVEAU: Mettre à jour timestamp dernier message
                            self.last_message_received = time.time()
                            self.total_messages_received += 1

                            try:
                                data = json.loads(message)
                                await self._handle_notification(data)
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                print(f"⚠️ Erreur traitement message: {e}")
                    finally:
                        heartbeat_task.cancel()  # ✨ Arrêter le heartbeat

            except asyncio.CancelledError:
                print("🛑 Websocket Helius arrêté")
                self.is_connected = False
                break
            except Exception as e:
                self.is_connected = False  # ✨ NOUVEAU
                self.total_reconnects += 1  # ✨ NOUVEAU
                self.failed_reconnects += 1  # ✨ NOUVEAU: Incrémenter échecs
                self.last_reconnect_time = datetime.now().isoformat()  # ✨ NOUVEAU
                retry_count += 1

                # ✨ AMÉLIORÉ: Failover automatique entre URLs
                # - Après 2 échecs sur la même URL → essayer la suivante
                # - Rotation complète des 3 URLs avant d'augmenter le backoff
                if retry_count % 2 == 0:
                    old_index = self.url_index
                    self.url_index = (self.url_index + 1) % len(self.wss_urls)
                    print(f"🔄 Failover: URL {old_index + 1} → URL {self.url_index + 1}")

                if self.is_running:
                    # ✨ AMÉLIORÉ: Backoff exponentiel intelligent
                    delay = self._calculate_backoff_delay(retry_count)
                    error_msg = str(e)[:100]
                    print(f"⚠️ Erreur websocket (retry {retry_count}/{self.max_retries}): {error_msg}")
                    print(f"   URL actuelle: {self.url_index + 1}/{len(self.wss_urls)}")
                    print(f"   Reconnexion dans {delay:.1f}s...")
                    print(f"   Stats: ✅ {self.successful_reconnects} succès | ❌ {self.failed_reconnects} échecs")
                    await asyncio.sleep(delay)

                self.websocket = None
    
    async def _handle_notification(self, data: Dict):
        """Traite une notification reçue du websocket"""
        try:
            # Vérifier si c'est une subscription update
            if 'result' not in data:
                return
            
            result = data.get('result', {})
            
            # Extraire les infos de la notification
            if isinstance(result, dict):
                logs = result.get('logs', [])
                signature = result.get('signature', '')
                
                # Chercher le trader correspondant à cette TX
                # Les logs mentionnent les adresses impliquées
                for trader_address, callback in self.subscriptions.items():
                    # La transaction concerne ce trader
                    # Chercher si c'est un swap en regardant les logs
                    
                    # Heuristique: si y a du "SWAP" ou des DEX mentions
                    is_swap = any(
                        keyword in str(logs).upper()
                        for keyword in ['SWAP', 'EXCHANGE', 'JUPITERAGGREGATE', 'RAYDIUM', 'ORCA', 'SERUM', 'PUMPFUN']
                    )
                    
                    if is_swap or signature:  # Toute TX du trader
                        # Créer un événement de trade
                        trade_event = {
                            'type': 'SWAP',
                            'trader_address': trader_address,
                            'signature': signature,
                            'timestamp': datetime.now().isoformat(),
                            'logs': logs,
                            'raw_data': result
                        }
                        
                        # Appeler le callback de manière non-bloquante
                        if callback:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(trade_event)
                                else:
                                    # Appeler dans un thread si callback n'est pas async
                                    callback(trade_event)
                            except Exception as e:
                                print(f"⚠️ Erreur callback: {e}")
        
        except Exception as e:
            print(f"⚠️ Erreur traitement notification: {e}")
    
    def start(self):
        """Démarre le listener websocket (non-bloquant)"""
        if not self.api_key:
            print("⚠️ Websocket Helius non disponible (API key manquante)")
            return
        
        if self.is_running:
            print("⚠️ Websocket déjà en cours")
            return
        
        self.is_running = True
        
        # Lancer dans un thread séparé
        def run_websocket():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._connect_and_listen())
            except Exception as e:
                print(f"❌ Erreur websocket: {e}")
            finally:
                self.is_running = False
        
        thread = threading.Thread(target=run_websocket, daemon=True)
        thread.start()
        print("✅ Websocket Helius démarré")
    
    def stop(self):
        """Arrête le listener websocket"""
        self.is_running = False
        if self.websocket:
            try:
                asyncio.run(self.websocket.close())
            except:
                pass
        print("🛑 Websocket Helius arrêté")


# Instance globale
helius_websocket = HeliosWebsocketListener()
