// ============ HFT MODULE - Frontend JavaScript ============

// Store global pour les données HFT
window.hftData = {
    wallets: {},
    markets: [],
    signals: [],
    stats: null
};

// ============ INITIALIZATION ============

function initHFTModule() {
    console.log('Initialisation module HFT...');
    loadHFTStatus();
    loadHFTWallets();
    loadHFTMarkets();
    loadHFTSignals();
}

// ============ API CALLS ============

function loadHFTStatus() {
    fetch('/api/hft/status')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                window.hftData.stats = data.stats;
                updateHFTStatusUI(data.stats);
            }
        })
        .catch(e => console.error('Erreur HFT status:', e));
}

function loadHFTWallets() {
    fetch('/api/hft/wallets')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Store dans le global
                window.hftData.wallets = {};
                data.wallets.forEach(w => {
                    window.hftData.wallets[w.address] = w;
                });
                renderHFTWallets(data.wallets);
            }
        })
        .catch(e => console.error('Erreur HFT wallets:', e));
}

function loadHFTMarkets() {
    fetch('/api/hft/markets')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                window.hftData.markets = data.markets;
                renderHFTMarkets(data.markets);
            }
        })
        .catch(e => console.error('Erreur HFT markets:', e));
}

function loadHFTSignals() {
    fetch('/api/hft/signals?limit=50')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                window.hftData.signals = data.signals;
                renderHFTSignals(data.signals);
            }
        })
        .catch(e => console.error('Erreur HFT signals:', e));
}

// ============ CONTROL ============

function toggleHFTScanner() {
    fetch('/api/hft/toggle', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                updateHFTScannerStatus(data.running);
            }
        })
        .catch(e => console.error('Erreur toggle HFT:', e));
}

function refreshHFTMarkets() {
    const btn = document.getElementById('hft-refresh-markets-btn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Refresh...';
    }

    fetch('/api/hft/markets/refresh', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                loadHFTMarkets();
            }
        })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Rafraichir';
            }
        });
}

// ============ WALLET MANAGEMENT ============

function addHFTWallet() {
    const address = document.getElementById('hft-new-wallet-address').value.trim();
    const nickname = document.getElementById('hft-new-wallet-name').value.trim();

    if (!address) {
        alert('Adresse requise');
        return;
    }

    fetch('/api/hft/wallets/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            address: address,
            nickname: nickname || '',
            capital_allocated: 100,
            percent_per_trade: 10
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('hft-new-wallet-address').value = '';
                document.getElementById('hft-new-wallet-name').value = '';
                loadHFTWallets();
            } else {
                alert(data.error || data.message || 'Erreur');
            }
        })
        .catch(e => {
            console.error('Erreur ajout wallet HFT:', e);
            alert('Erreur ajout wallet');
        });
}

function removeHFTWallet(address) {
    if (!confirm('Retirer ce wallet HFT ?')) return;

    fetch('/api/hft/wallets/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: address })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                loadHFTWallets();
            } else {
                alert(data.error || data.message || 'Erreur');
            }
        });
}

function openHFTWalletConfigModal(address) {
    const w = window.hftData.wallets[address];
    if (!w) {
        alert('Wallet non trouvé');
        return;
    }

    document.getElementById('hft-modal-wallet-address').value = w.address;
    document.getElementById('hft-modal-wallet-name').textContent = `${w.nickname || 'Wallet'} - ${w.address.slice(0, 10)}...`;
    document.getElementById('hft-modal-capital').value = w.capital_allocated || 100;
    document.getElementById('hft-modal-percent').value = w.percent_per_trade || 10;
    document.getElementById('hft-modal-max-trades').value = w.max_daily_trades || 50;
    document.getElementById('hft-modal-sl').value = w.sl_percent ?? '';
    document.getElementById('hft-modal-tp').value = w.tp_percent ?? '';
    document.getElementById('hft-modal-enabled').checked = w.enabled !== false && w.enabled !== 0;

    document.getElementById('hft-wallet-config-modal').style.display = 'flex';
}

function closeHFTWalletConfigModal() {
    document.getElementById('hft-wallet-config-modal').style.display = 'none';
}

function saveHFTWalletConfig() {
    const address = document.getElementById('hft-modal-wallet-address').value;
    const capital = parseFloat(document.getElementById('hft-modal-capital').value) || 100;
    const percent = parseFloat(document.getElementById('hft-modal-percent').value) || 10;
    const maxTrades = parseInt(document.getElementById('hft-modal-max-trades').value) || 50;
    const slPercent = document.getElementById('hft-modal-sl').value;
    const tpPercent = document.getElementById('hft-modal-tp').value;
    const enabled = document.getElementById('hft-modal-enabled').checked;

    fetch('/api/hft/wallets/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            address: address,
            capital_allocated: capital,
            percent_per_trade: percent,
            max_daily_trades: maxTrades,
            sl_percent: slPercent ? parseFloat(slPercent) : null,
            tp_percent: tpPercent ? parseFloat(tpPercent) : null,
            enabled: enabled
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                closeHFTWalletConfigModal();
                loadHFTWallets();
            } else {
                alert(data.error || data.message || 'Erreur');
            }
        });
}

// ============ UI RENDERING ============

function updateHFTStatusUI(stats) {
    // Scanner status
    const statusBadge = document.getElementById('hft-scanner-status');
    if (statusBadge) {
        if (stats.running) {
            statusBadge.textContent = 'ACTIF';
            statusBadge.className = 'status-badge status-on';
        } else {
            statusBadge.textContent = 'INACTIF';
            statusBadge.className = 'status-badge status-off';
        }
    }

    // Toggle button
    const toggleBtn = document.getElementById('hft-toggle-btn');
    if (toggleBtn) {
        toggleBtn.textContent = stats.running ? 'Arreter' : 'Demarrer';
    }

    // Stats
    const signalsEl = document.getElementById('hft-signals-count');
    if (signalsEl) signalsEl.textContent = stats.signals_received || 0;

    const executedEl = document.getElementById('hft-executed-count');
    if (executedEl) executedEl.textContent = stats.signals_executed || 0;

    const rateEl = document.getElementById('hft-execution-rate');
    if (rateEl) rateEl.textContent = `${stats.execution_rate || 0}%`;

    const marketsEl = document.getElementById('hft-active-markets-count');
    if (marketsEl && stats.market_discovery) {
        marketsEl.textContent = stats.market_discovery.active_markets || 0;
    }

    const latencyEl = document.getElementById('hft-avg-latency');
    if (latencyEl && stats.executor) {
        // On n'a pas encore de latence moyenne dans executor, on affiche "-"
        latencyEl.textContent = '-';
    }
}

function updateHFTScannerStatus(running) {
    const statusBadge = document.getElementById('hft-scanner-status');
    const toggleBtn = document.getElementById('hft-toggle-btn');

    if (statusBadge) {
        if (running) {
            statusBadge.textContent = 'ACTIF';
            statusBadge.className = 'status-badge status-on';
        } else {
            statusBadge.textContent = 'INACTIF';
            statusBadge.className = 'status-badge status-off';
        }
    }

    if (toggleBtn) {
        toggleBtn.textContent = running ? 'Arreter' : 'Demarrer';
    }
}

function renderHFTWallets(wallets) {
    const container = document.getElementById('hft-wallets-list');
    if (!container) return;

    if (!wallets || wallets.length === 0) {
        container.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">Aucun wallet HFT</p>';
        return;
    }

    let html = '';
    wallets.forEach(w => {
        const statusClass = w.enabled ? 'status-on' : 'status-off';
        const statusText = w.enabled ? 'Actif' : 'Inactif';

        html += `
            <div class="wallet-item">
                <div class="wallet-info">
                    <div class="wallet-name">${escapeHtml(w.nickname || 'HFT Wallet')}</div>
                    <div class="wallet-address">${w.address}</div>
                    <div class="wallet-config">
                        Capital: $${w.capital_allocated || 100} | ${w.percent_per_trade || 10}% par trade
                    </div>
                </div>
                <div class="wallet-actions">
                    <span class="status-badge ${statusClass}" style="font-size: 10px;">${statusText}</span>
                    <button class="btn btn-secondary btn-sm" onclick="openHFTWalletConfigModal('${w.address}')">Config</button>
                    <button class="btn btn-danger btn-sm" onclick="removeHFTWallet('${w.address}')">X</button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderHFTMarkets(markets) {
    const container = document.getElementById('hft-markets-list');
    if (!container) return;

    if (!markets || markets.length === 0) {
        container.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">Aucun marche 15-min actif</p>';
        return;
    }

    let html = '<table class="flux-table"><thead><tr><th>Asset</th><th>Question</th><th>Temps Restant</th><th>Prix YES</th></tr></thead><tbody>';

    markets.forEach(m => {
        const timeRemaining = formatTimeRemaining(m.time_remaining_seconds);
        const cryptoBadge = m.crypto_asset === 'BTC' ? 'btc-badge' : 'eth-badge';

        html += `
            <tr>
                <td><span class="crypto-badge ${cryptoBadge}">${m.crypto_asset} ${m.direction}</span></td>
                <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(m.question.substring(0, 60))}...</td>
                <td>${timeRemaining}</td>
                <td>${(m.yes_price * 100).toFixed(1)}%</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderHFTSignals(signals) {
    const container = document.getElementById('hft-signals-feed');
    if (!container) return;

    if (!signals || signals.length === 0) {
        container.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">En attente de signaux...</p>';
        return;
    }

    let html = '';
    signals.slice(0, 20).forEach(s => {
        const sideClass = s.side === 'BUY' ? 'signal-buy' : 'signal-sell';
        const time = new Date(s.timestamp).toLocaleTimeString('fr-FR');

        html += `
            <div class="signal-item ${sideClass}">
                <div class="signal-time">${time}</div>
                <div class="signal-info">
                    <strong>${s.wallet_name || s.wallet_address?.slice(0, 10) || 'Unknown'}</strong>
                    <span class="signal-side">${s.side}</span>
                    ${s.crypto_asset ? `<span class="crypto-badge">${s.crypto_asset}</span>` : ''}
                </div>
                <div class="signal-details">
                    ${s.value_usd ? `$${s.value_usd.toFixed(2)}` : ''}
                    ${s.latency_ms ? `(${s.latency_ms}ms)` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// ============ UTILITIES ============

function formatTimeRemaining(seconds) {
    if (!seconds || seconds <= 0) return 'Termine';

    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;

    if (mins > 0) {
        return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ WEBSOCKET EVENTS ============

// Ces events sont emis par le serveur via SocketIO
if (typeof socket !== 'undefined') {
    socket.on('hft_signal', function (data) {
        console.log('HFT Signal recu:', data);
        // Ajouter au debut de la liste
        window.hftData.signals.unshift(data);
        // Limiter a 100 signaux
        if (window.hftData.signals.length > 100) {
            window.hftData.signals = window.hftData.signals.slice(0, 100);
        }
        renderHFTSignals(window.hftData.signals);

        // Mettre a jour les stats
        loadHFTStatus();
    });

    socket.on('hft_trade_executed', function (data) {
        console.log('HFT Trade execute:', data);
        loadHFTStatus();
    });

    socket.on('hft_status', function (data) {
        console.log('HFT Status update:', data);
        updateHFTScannerStatus(data.running);
    });
}

// ============ AUTO-REFRESH ============

// Refresh automatique toutes les 30 secondes si l'onglet HFT est actif
setInterval(function () {
    const hftTab = document.getElementById('tab-hft');
    if (hftTab && hftTab.classList.contains('active')) {
        loadHFTStatus();
        loadHFTMarkets();
    }
}, 30000);
