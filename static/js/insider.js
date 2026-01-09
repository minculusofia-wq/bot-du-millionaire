/**
 * insider.js - Insider Tracker Frontend Logic
 * Gere l'interface utilisateur pour la detection de wallets suspects sur Polymarket
 */

// ============ SCANNER CONTROL ============

function toggleInsiderScanner() {
    const enabled = document.getElementById('insider-scanner-toggle').checked;

    fetch('/api/insider/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                updateInsiderStatus(data.running);
                console.log('Scanner:', data.running ? 'Started' : 'Stopped');
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
                // Reset toggle
                document.getElementById('insider-scanner-toggle').checked = !enabled;
            }
        })
        .catch(e => {
            console.error('Toggle scanner error:', e);
            document.getElementById('insider-scanner-toggle').checked = !enabled;
        });
}

function updateInsiderStatus(running) {
    const statusEl = document.getElementById('insider-status');
    if (statusEl) {
        statusEl.textContent = running ? 'Running' : 'Stopped';
        statusEl.style.color = running ? '#00E676' : '#FF5252';
    }
}

function triggerManualScan() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Scanning...';

    fetch('/api/insider/scan_now', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert(`Scan termine: ${data.alerts_found} alerte(s) trouvee(s)`);
                loadInsiderAlerts();
                loadInsiderStats();
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        })
        .catch(e => {
            console.error('Manual scan error:', e);
            alert('Erreur de scan');
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = 'Scan Manuel';
        });
}

// ============ CONFIGURATION ============

// ============ CONFIGURATION ============

function toggleCategory(el) {
    el.classList.toggle('active');
}

function saveInsiderConfig() {
    // Collecter les categories actives
    const activeCategories = [];
    document.querySelectorAll('.category-toggle.active').forEach(el => {
        activeCategories.push(el.dataset.category);
    });

    // Construire la config structurée
    const config = {
        categories: activeCategories,

        risky_bet: {
            enabled: document.getElementById('trigger-risky-enabled').checked,
            min_amount: parseFloat(document.getElementById('trigger-risky-min').value) || 50,
            max_odds: (parseFloat(document.getElementById('trigger-risky-odds').value) || 35) / 100
        },

        whale_wakeup: {
            enabled: document.getElementById('trigger-whale-enabled').checked,
            min_amount: parseFloat(document.getElementById('trigger-whale-min').value) || 100,
            dormant_days: parseInt(document.getElementById('trigger-whale-days').value) || 30
        },

        fresh_wallet: {
            enabled: document.getElementById('trigger-fresh-enabled').checked,
            min_amount: parseFloat(document.getElementById('trigger-fresh-min').value) || 500,
            max_tx: parseInt(document.getElementById('trigger-fresh-tx').value) || 5
        }
    };

    fetch('/api/insider/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('Configuration sauvegardee!');
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        })
        .catch(e => {
            console.error('Save config error:', e);
            alert('Erreur de sauvegarde');
        });
}

// ============ LOAD DATA ============

function loadInsiderConfig() {
    fetch('/api/insider/config')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            const config = data.config;

            // Toggle scanner status
            const toggle = document.getElementById('insider-scanner-toggle');
            if (toggle) toggle.checked = config.running;

            // Categories
            const categories = config.enabled_categories || config.categories || [];
            document.querySelectorAll('.category-toggle').forEach(el => {
                if (categories.includes(el.dataset.category)) {
                    el.classList.add('active');
                } else {
                    el.classList.remove('active');
                }
            });

            // Config Triggers
            if (config.risky_bet) {
                document.getElementById('trigger-risky-enabled').checked = config.risky_bet.enabled;
                document.getElementById('trigger-risky-min').value = config.risky_bet.min_amount;
                document.getElementById('trigger-risky-odds').value = (config.risky_bet.max_odds * 100).toFixed(0);
            }

            if (config.whale_wakeup) {
                document.getElementById('trigger-whale-enabled').checked = config.whale_wakeup.enabled;
                document.getElementById('trigger-whale-min').value = config.whale_wakeup.min_amount;
                document.getElementById('trigger-whale-days').value = config.whale_wakeup.dormant_days;
            }

            if (config.fresh_wallet) {
                document.getElementById('trigger-fresh-enabled').checked = config.fresh_wallet.enabled;
                document.getElementById('trigger-fresh-min').value = config.fresh_wallet.min_amount;
                document.getElementById('trigger-fresh-tx').value = config.fresh_wallet.max_tx;
            }

            // Status display
            updateInsiderStatus(config.running);
        });
}

function loadInsiderStats() {
    fetch('/api/insider/stats')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            const stats = data.stats;

            const alertsCount = document.getElementById('insider-alerts-count');
            if (alertsCount) alertsCount.textContent = stats.alerts_generated || 0;

            const marketsCount = document.getElementById('insider-markets-count');
            if (marketsCount) marketsCount.textContent = stats.markets_scanned || 0;

            const lastScan = document.getElementById('insider-last-scan');
            if (lastScan) {
                lastScan.textContent = stats.last_scan
                    ? new Date(stats.last_scan).toLocaleTimeString()
                    : 'Never';
            }

            updateInsiderStatus(stats.running);
        });
}

function loadInsiderAlerts() {
    fetch('/api/insider/alerts?limit=50')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            renderAlertFeed(data.alerts);
        });
}

container.innerHTML = alerts.map(alert => {
    // Mapping des types d'alerte pour badge CSS
    const typeClass = (alert.alert_type || '').toLowerCase();
    const typeLabel = (alert.alert_type || 'UNKNOWN').replace('_', ' ');

    const stats = alert.wallet_stats || {};
    const pnlClass = (stats.pnl || 0) >= 0 ? 'positive' : 'negative';

    return `
        <div class="insider-alert-card type-${typeClass}">
            <div class="alert-header">
                <div>
                    <span class="alert-type-badge ${typeClass}">${typeLabel}</span>
                    <span class="alert-wallet-address">${truncateAddress(alert.wallet_address)}</span>
                    ${alert.nickname ? `<span class="alert-nickname">(${escapeHtml(alert.nickname)})</span>` : ''}
                </div>
                <div class="alert-time">${formatTime(alert.timestamp)}</div>
            </div>

            <div class="alert-market">${escapeHtml(alert.market_question || 'Unknown Market')}</div>

            <!-- NOUVEAU: Details precis du Trigger -->
            <div class="alert-trigger-info" style="background: rgba(255, 255, 255, 0.05); padding: 8px; border-radius: 4px; margin: 10px 0; border-left: 3px solid #00B0FF;">
                <div style="font-weight: bold; font-size: 0.9em; color: #fff;">💡 ${escapeHtml(alert.trigger_details || '')}</div>
                <div style="font-size: 1.1em; color: #00E676; margin-top: 4px;">💰 ${escapeHtml(alert.bet_details || '')}</div>
            </div>

            <div class="alert-stats-row" style="display: flex; gap: 15px; font-size: 0.8em; color: #888; margin-bottom: 10px;">
                <span>PnL: <span class="${pnlClass}">$${(stats.pnl || 0).toFixed(0)}</span></span>
                <span>WinRate: ${(stats.win_rate || 0).toFixed(0)}%</span>
                <span>Trades: ${stats.total_trades || 0}</span>
            </div>

            <div class="alert-actions" style="display: flex; gap: 10px;">
                <a href="${alert.market_url || '#'}" target="_blank" class="btn btn-primary btn-sm" style="flex: 2; text-decoration: none; text-align: center; display: flex; align-items: center; justify-content: center; background-color: #2D9CDB;">
                    ↗ Voir sur Polymarket
                </a>
                <button class="btn btn-secondary btn-sm" onclick="followInsiderWallet('${alert.wallet_address}')" style="flex: 1;">
                    Follow
                </button>
                <button class="btn btn-secondary btn-sm" onclick="saveInsiderWallet('${alert.wallet_address}')" style="flex: 1;">
                    Save
                </button>
            </div>
        </div>
        `;
}).join('');
}

// ============ WALLET ACTIONS ============

function followInsiderWallet(address) {
    // Utiliser la modale de config wallet existante
    if (typeof openWalletConfigModal === 'function') {
        // Creer une entree temporaire dans walletsData si necessaire
        if (!window.walletsData) window.walletsData = {};
        if (!window.walletsData[address]) {
            window.walletsData[address] = {
                address: address,
                name: 'Insider ' + address.slice(0, 8),
                capital_allocated: 0,
                percent_per_trade: 0,
                active: false
            };
        }
        openWalletConfigModal(address);
    } else {
        alert('Modal de configuration non disponible');
    }
}

function saveInsiderWallet(address) {
    const nickname = prompt('Nickname pour ce wallet (optionnel):');

    fetch('/api/insider/save_wallet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            address: address,
            nickname: nickname || ''
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('Wallet sauvegarde!');
                loadSavedWallets();
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        })
        .catch(e => {
            console.error('Save wallet error:', e);
            alert('Erreur de sauvegarde');
        });
}

// ============ SAVED WALLETS ============

function loadSavedWallets() {
    fetch('/api/insider/saved')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            renderSavedWallets(data.wallets);
        });
}

function renderSavedWallets(wallets) {
    const container = document.getElementById('saved-wallets-list');
    if (!container) return;

    if (!wallets || wallets.length === 0) {
        container.innerHTML = `
            <p style="color: #888; text-align: center; padding: 20px;">
                Aucun wallet sauvegarde. Utilisez le bouton "Save" sur une alerte pour ajouter.
            </p>
        `;
        return;
    }

    container.innerHTML = wallets.map(w => {
        const sourceBadge = w.source === 'MANUAL'
            ? '<span class="source-badge manual">MANUAL</span>'
            : '<span class="source-badge scanner">SCANNER</span>';

        const pnlClass = (w.pnl || 0) >= 0 ? 'positive' : 'negative';

        return `
        <div class="saved-wallet-card">
            <div class="saved-wallet-info">
                <div class="saved-wallet-header" style="display: flex; align-items: center; gap: 8px;">
                    <div class="saved-wallet-nickname">${escapeHtml(w.nickname) || 'Unnamed Wallet'}</div>
                    ${sourceBadge}
                </div>
                <div class="saved-wallet-address">${w.address}</div>
                <div class="saved-wallet-stats-brief" style="display: flex; gap: 15px; margin-top: 5px; font-size: 0.9em;">
                    <span class="${pnlClass}">$${(w.pnl || 0).toFixed(2)}</span>
                    <span style="color: #888;">${(w.win_rate || 0).toFixed(1)}% WR</span>
                </div>
                <div class="saved-wallet-meta">
                    Saved: ${formatTime(w.saved_at)} |
                    Alerts: ${w.total_alerts || 0}
                </div>
            </div>
            <div class="saved-wallet-actions">
                <button class="btn btn-secondary btn-sm" onclick="viewWalletStats('${w.address}')">
                    Refresh
                </button>
                <button class="btn btn-primary btn-sm" onclick="followInsiderWallet('${w.address}')">
                    Follow
                </button>
                <button class="btn btn-danger btn-sm" onclick="removeSavedWallet('${w.address}')">
                    Remove
                </button>
            </div>
        </div>
    `}).join('');
}

function viewWalletStats(address) {
    fetch(`/api/insider/wallet_stats/${address}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const stats = data.stats;
                alert(`
Wallet: ${truncateAddress(address)}

PnL: $${(stats.pnl || 0).toFixed(2)}
Win Rate: ${(stats.win_rate || 0).toFixed(1)}%
ROI: ${(stats.roi || 0).toFixed(1)}%
Total Trades: ${stats.total_trades || 0}

Alertes enregistrees: ${data.alerts_count || 0}
            `);
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        });
}

function removeSavedWallet(address) {
    if (!confirm('Retirer ce wallet de la liste?')) return;

    fetch(`/api/insider/saved/${address}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                loadSavedWallets();
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        });
}

// ============ WEBSOCKET ============

function initInsiderWebSocket() {
    if (typeof socket !== 'undefined') {
        socket.on('insider_alert', (alert) => {
            console.log('New insider alert:', alert);
            // Recharger le feed
            loadInsiderAlerts();
            loadInsiderStats();

            // Notification optionnelle (si permissions accordees)
            if (Notification.permission === 'granted') {
                new Notification('Insider Alert!', {
                    body: `Score ${alert.suspicion_score}: ${(alert.market_question || '').slice(0, 50)}...`,
                    icon: '/static/img/alert-icon.png'
                });
            }
        });
    }
}

// ============ UTILITIES ============

function formatCriteria(criteria) {
    const labels = {
        'unlikely_bet': 'Unlikely Bet',
        'abnormal_behavior': 'Abnormal',
        'suspicious_profile': 'New Wallet'
    };
    return labels[criteria] || criteria;
}

function truncateAddress(addr) {
    if (!addr) return 'Unknown';
    return addr.slice(0, 10) + '...' + addr.slice(-8);
}

function formatTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ INITIALIZATION ============

function initInsiderTracker() {
    loadInsiderConfig();
    loadInsiderStats();
    loadInsiderAlerts();
    loadSavedWallets();
    initInsiderWebSocket();
}

// Export pour main.js
window.initInsiderTracker = initInsiderTracker;
window.toggleInsiderScanner = toggleInsiderScanner;
window.onInsiderPresetChange = onInsiderPresetChange;
window.toggleCategory = toggleCategory;
window.updateWeightDisplay = updateWeightDisplay;
window.saveInsiderConfig = saveInsiderConfig;
window.triggerManualScan = triggerManualScan;
window.followInsiderWallet = followInsiderWallet;
window.saveInsiderWallet = saveInsiderWallet;
window.viewWalletStats = viewWalletStats;
window.removeSavedWallet = removeSavedWallet;
