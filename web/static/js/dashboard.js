// Dashboard JavaScript for real-time updates

const socket = io();

function updateDashboard() {
    // Update account info
    fetch('/api/account')
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    console.error('Account API error:', err);
                    if (err.error && err.error.includes('authentication')) {
                        document.getElementById('account-value').textContent = 'Auth Error';
                        document.getElementById('buying-power').textContent = 'Auth Error';
                    }
                    throw new Error(err.error || 'Failed to get account');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error('Account error:', data.error);
                document.getElementById('account-value').textContent = 'Error';
                document.getElementById('buying-power').textContent = 'Error';
                return;
            }
            if (data.portfolio_value) {
                document.getElementById('account-value').textContent = `$${parseFloat(data.portfolio_value).toFixed(2)}`;
            }
            if (data.buying_power) {
                document.getElementById('buying-power').textContent = `$${parseFloat(data.buying_power).toFixed(2)}`;
            }
        })
        .catch(error => {
            console.error('Error updating account:', error);
        });

    // Update positions
    fetch('/api/positions')
        .then(response => {
            if (!response.ok) {
                console.error('Positions API error:', response.status);
                return [];
            }
            return response.json();
        })
        .then(positions => {
            if (positions.error) {
                console.error('Positions error:', positions.error);
                return;
            }
            document.getElementById('active-positions').textContent = positions.length;
            updatePositionsTable(positions);
        });

    // Update risk summary
    fetch('/api/risk')
        .then(response => {
            if (!response.ok) {
                console.error('Risk API error:', response.status);
                return {};
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error('Risk error:', data.error);
                return;
            }
            document.getElementById('daily-betting').textContent = `$${data.daily_betting_amount.toFixed(2)}`;
            document.getElementById('used-betting').textContent = `$${data.used_betting_amount.toFixed(2)}`;
            document.getElementById('remaining-betting').textContent = `$${data.remaining_betting_amount.toFixed(2)}`;
            document.getElementById('max-loss').textContent = `$${data.max_daily_loss.toFixed(2)}`;
            document.getElementById('trades-today').textContent = data.trades_today;
            
            const canTradeBadge = document.getElementById('can-trade');
            if (data.can_trade) {
                canTradeBadge.innerHTML = '<span class="badge bg-success">Yes</span>';
            } else {
                canTradeBadge.innerHTML = '<span class="badge bg-danger">No</span>';
            }
        });

    // Update daily P&L (from positions)
    fetch('/api/positions')
        .then(response => response.json())
        .then(positions => {
            const totalPnL = positions.reduce((sum, pos) => sum + (pos.unrealized_pl || 0), 0);
            const pnlElement = document.getElementById('daily-pnl');
            pnlElement.textContent = `$${totalPnL.toFixed(2)}`;
            pnlElement.className = totalPnL >= 0 ? 'text-success' : 'text-danger';
        });
}

function updatePositionsTable(positions) {
    const tbody = document.getElementById('positions-tbody');
    
    if (!positions || positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No active positions</td></tr>';
        return;
    }

    tbody.innerHTML = positions.map(pos => {
        const pnl = pos.unrealized_pl || 0;
        const pnlPercent = pos.unrealized_plpc || 0;
        const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
        
        return `
            <tr>
                <td><strong>${pos.symbol}</strong></td>
                <td>${pos.qty}</td>
                <td>$${pos.avg_entry_price.toFixed(4)}</td>
                <td>$${pos.current_price.toFixed(4)}</td>
                <td class="${pnlClass}">$${pnl.toFixed(2)}</td>
                <td class="${pnlClass}">${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="exitPosition('${pos.symbol}')">Exit</button>
                </td>
            </tr>
        `;
    }).join('');
}

function exitPosition(symbol) {
    if (confirm(`Exit position in ${symbol}?`)) {
        fetch('/api/trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbol,
                side: 'sell',
                qty: 0  // Will need to get actual qty from position
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                alert('Order placed successfully');
                updateDashboard();
            }
        });
    }
}

function switchMode() {
    const mode = document.getElementById('mode-select').value;
    const warning = document.getElementById('mode-warning');
    
    if (mode === 'live') {
        if (!confirm('WARNING: This will switch to LIVE TRADING with real money. Are you sure?')) {
            return;
        }
        warning.style.display = 'block';
    } else {
        warning.style.display = 'none';
    }

    fetch('/api/mode/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            document.getElementById('mode-display').textContent = mode.toUpperCase();
            alert(`Switched to ${mode} trading mode`);
        }
    });
}

// Scanner functions
let scannerRunning = false;

function toggleScanner() {
    const endpoint = scannerRunning ? '/api/scanner/stop' : '/api/scanner/start';
    const method = 'POST';
    
    fetch(endpoint, { method })
        .then(response => response.json())
        .then(data => {
            if (data.success || !data.error) {
                scannerRunning = !scannerRunning;
                updateScannerStatus();
                if (scannerRunning) {
                    updateSignals();
                    // Start periodic signal updates
                    if (!window.signalUpdateInterval) {
                        window.signalUpdateInterval = setInterval(updateSignals, 10000); // Every 10 seconds
                    }
                } else {
                    // Stop periodic updates
                    if (window.signalUpdateInterval) {
                        clearInterval(window.signalUpdateInterval);
                        window.signalUpdateInterval = null;
                    }
                }
            } else {
                alert('Error: ' + (data.error || 'Failed to toggle scanner'));
            }
        })
        .catch(error => {
            console.error('Error toggling scanner:', error);
            alert('Error toggling scanner');
        });
}

function updateScannerStatus() {
    fetch('/api/scanner/status')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Scanner status error:', data.error);
                return;
            }
            scannerRunning = data.running;
            const statusBadge = document.getElementById('scanner-status');
            const btn = document.getElementById('start-scanner-btn');
            
            if (scannerRunning) {
                statusBadge.textContent = 'Scanner: Running';
                statusBadge.className = 'badge bg-success me-2';
                btn.textContent = 'Stop Scanner';
                btn.className = 'btn btn-sm btn-danger';
            } else {
                statusBadge.textContent = 'Scanner: Stopped';
                statusBadge.className = 'badge bg-secondary me-2';
                btn.textContent = 'Start Scanner';
                btn.className = 'btn btn-sm btn-success';
            }
        })
        .catch(error => {
            console.error('Error getting scanner status:', error);
        });
}

function updateSignals() {
    fetch('/api/scanner/signals')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Signals error:', data.error);
                return;
            }
            
            const container = document.getElementById('signals-container');
            const signals = data.signals || {};
            
            if (Object.keys(signals).length === 0) {
                container.innerHTML = '<p class="text-muted text-center">No signals available yet. Scanner is monitoring symbols...</p>';
                return;
            }
            
            // Sort signals by confidence (highest first)
            const sortedSignals = Object.values(signals).sort((a, b) => {
                return (b.confidence || 0) - (a.confidence || 0);
            });
            
            container.innerHTML = sortedSignals.map(signal => {
                const signalClass = signal.signal === 'BUY' ? 'success' : signal.signal === 'SELL' ? 'danger' : 'secondary';
                const confidence = (signal.confidence || 0) * 100;
                
                // Format probabilities
                const probs = signal.probabilities || {};
                const probHtml = Object.entries(probs).map(([target, prob]) => {
                    const probClass = prob > 50 ? 'success' : prob > 30 ? 'warning' : 'secondary';
                    return `<span class="badge bg-${probClass} me-1">${target}: ${prob}%</span>`;
                }).join('');
                
                // Format timeframe analysis
                const tfAnalysis = signal.timeframe_analysis || {};
                const tfHtml = Object.entries(tfAnalysis).map(([tf, data]) => {
                    const tfSignal = data.signal || 'NEUTRAL';
                    const tfClass = tfSignal === 'BUY' ? 'success' : tfSignal === 'SELL' ? 'danger' : 'secondary';
                    return `<div class="col-md-3">
                        <strong>${tf}:</strong> <span class="badge bg-${tfClass}">${tfSignal}</span>
                        <small class="text-muted d-block">RSI: ${(data.rsi || 0).toFixed(1)} | MSI: ${(data.msi || 0).toFixed(1)}</small>
                    </div>`;
                }).join('');
                
                // Format daily stats
                const dailyStats = signal.daily_stats || {};
                const dailyHigh = dailyStats.daily_high || signal.entry_price || 0;
                const dailyLow = dailyStats.daily_low || signal.entry_price || 0;
                const dailyAvg = dailyStats.daily_average || signal.entry_price || 0;
                const dailyOpen = dailyStats.daily_open || signal.entry_price || 0;
                const currentPrice = signal.entry_price || 0;
                
                // Calculate position relative to daily range
                const vsHigh = dailyStats.current_vs_high_pct || 0;
                const vsLow = dailyStats.current_vs_low_pct || 0;
                const vsAvg = dailyStats.current_vs_avg_pct || 0;
                
                // Determine if price is near high or low
                const pricePosition = vsLow > 70 ? 'high' : vsLow < 30 ? 'low' : 'mid';
                const positionClass = pricePosition === 'high' ? 'warning' : pricePosition === 'low' ? 'info' : 'secondary';
                
                return `
                    <div class="card mb-3">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col-md-2">
                                    <h4 class="mb-0">${signal.symbol}</h4>
                                    <span class="badge bg-${signalClass}">${signal.signal}</span>
                                    <div class="mt-2">
                                        <small class="text-muted">Confidence: ${confidence.toFixed(1)}%</small>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-light mb-2">
                                        <div class="card-body p-2">
                                            <div class="mb-1"><strong>Daily Price Range:</strong></div>
                                            <div class="d-flex justify-content-between">
                                                <span class="text-success"><strong>High:</strong> $${dailyHigh.toFixed(4)}</span>
                                                <span class="text-danger"><strong>Low:</strong> $${dailyLow.toFixed(4)}</span>
                                            </div>
                                            <div class="mt-1">
                                                <span class="text-primary"><strong>Avg:</strong> $${dailyAvg.toFixed(4)}</span>
                                                <span class="ms-2 text-muted"><strong>Open:</strong> $${dailyOpen.toFixed(4)}</span>
                                            </div>
                                            <div class="mt-1">
                                                <span class="badge bg-${positionClass}">Current: $${currentPrice.toFixed(4)}</span>
                                                ${vsHigh > 0 ? `<small class="text-muted d-block">${vsHigh.toFixed(1)}% below high</small>` : ''}
                                                ${vsLow > 0 ? `<small class="text-muted d-block">${vsLow.toFixed(1)}% above low</small>` : ''}
                                            </div>
                                        </div>
                                    </div>
                                    <div><strong>Entry:</strong> $${(signal.entry_price || 0).toFixed(4)}</div>
                                    <div><strong>Stop Loss:</strong> $${(signal.stop_loss || 0).toFixed(4)} (${(signal.stop_loss_pct || 0).toFixed(2)}%)</div>
                                </div>
                                <div class="col-md-4">
                                    <div class="mb-2"><strong>Profit Probabilities:</strong></div>
                                    <div>${probHtml || 'N/A'}</div>
                                </div>
                                <div class="col-md-3">
                                    <div class="mb-2"><strong>Indicators:</strong></div>
                                    <small>RSI: ${(signal.indicators?.rsi || 0).toFixed(1)} | MSI: ${(signal.indicators?.msi || 0).toFixed(1)}</small><br>
                                    <small>Volume: ${(signal.indicators?.volume_ratio || 0).toFixed(2)}x</small>
                                    ${signal.bid_ask ? `
                                        <div class="mt-2 p-2 bg-light rounded">
                                            <div class="mb-1"><strong>Bid/Ask Analysis:</strong></div>
                                            <div class="d-flex justify-content-between">
                                                <span class="text-success">Bid: $${(signal.bid_ask.bid_price || 0).toFixed(4)} (${signal.bid_ask.bid_size || 0})</span>
                                                <span class="text-danger">Ask: $${(signal.bid_ask.ask_price || 0).toFixed(4)} (${signal.bid_ask.ask_size || 0})</span>
                                            </div>
                                            <div class="mt-1">
                                                <span class="badge bg-${signal.bid_ask.order_flow === 'BULLISH' ? 'success' : signal.bid_ask.order_flow === 'BEARISH' ? 'danger' : 'secondary'}">${signal.bid_ask.order_flow || 'NEUTRAL'}</span>
                                                <small class="text-muted ms-1">Spread: ${(signal.bid_ask.spread_pct || 0).toFixed(2)}%</small>
                                            </div>
                                            <div class="mt-1">
                                                <small><strong>Entry:</strong> ${signal.entry_recommendation || 'MARKET'} @ $${(signal.optimal_entry || signal.entry_price || 0).toFixed(4)}</small>
                                            </div>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                            <div class="row mt-2">
                                <div class="col-md-12">
                                    <strong>Multi-Timeframe Analysis:</strong>
                                    <div class="row mt-1">${tfHtml || '<div class="col-md-12 text-muted">No timeframe data</div>'}</div>
                                </div>
                            </div>
                            <div class="mt-2">
                                <button class="btn btn-sm btn-primary" onclick="viewSignalDetails('${signal.symbol}')">View Details</button>
                                ${signal.signal === 'BUY' ? `<button class="btn btn-sm btn-success" onclick="executeTradeFromSignal('${signal.symbol}')">Take Position</button>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        })
        .catch(error => {
            console.error('Error updating signals:', error);
        });
}

function viewSignalDetails(symbol) {
    fetch(`/api/scanner/signal/${symbol}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }
            
            const dailyStats = data.daily_stats || {};
            const bidAsk = data.bid_ask || {};
            const details = `Signal Details for ${symbol}:\n\n` +
                  `Signal: ${data.signal}\n` +
                  `Confidence: ${(data.confidence * 100).toFixed(1)}%\n\n` +
                  `Price Information:\n` +
                  `  Current: $${data.entry_price?.toFixed(4)}\n` +
                  `  Daily High: $${dailyStats.daily_high?.toFixed(4) || 'N/A'}\n` +
                  `  Daily Low: $${dailyStats.daily_low?.toFixed(4) || 'N/A'}\n` +
                  `  Daily Average: $${dailyStats.daily_average?.toFixed(4) || 'N/A'}\n` +
                  `  Daily Open: $${dailyStats.daily_open?.toFixed(4) || 'N/A'}\n` +
                  `  Position: ${dailyStats.current_vs_low_pct?.toFixed(1) || 0}% above low, ${dailyStats.current_vs_high_pct?.toFixed(1) || 0}% below high\n\n` +
                  `Bid/Ask Analysis:\n` +
                  `  Bid: $${bidAsk.bid_price?.toFixed(4) || 'N/A'} (Size: ${bidAsk.bid_size || 0})\n` +
                  `  Ask: $${bidAsk.ask_price?.toFixed(4) || 'N/A'} (Size: ${bidAsk.ask_size || 0})\n` +
                  `  Spread: $${bidAsk.spread?.toFixed(4) || 'N/A'} (${bidAsk.spread_pct?.toFixed(2) || 0}%)\n` +
                  `  Order Flow: ${bidAsk.order_flow || 'NEUTRAL'}\n` +
                  `  Volume Imbalance: ${(bidAsk.imbalance_ratio * 100 || 0).toFixed(1)}%\n` +
                  `  Liquidity Score: ${(bidAsk.liquidity_score || 0).toFixed(1)}/100\n\n` +
                  `Entry Recommendation:\n` +
                  `  Optimal Entry: $${data.optimal_entry?.toFixed(4) || data.entry_price?.toFixed(4)}\n` +
                  `  Recommendation: ${data.entry_recommendation || 'MARKET'}\n\n` +
                  `Risk Management:\n` +
                  `  Entry: $${data.entry_price?.toFixed(4)}\n` +
                  `  Stop Loss: $${data.stop_loss?.toFixed(4)} (${data.stop_loss_pct?.toFixed(2)}%)\n\n` +
                  `Indicators:\n` +
                  `  RSI: ${data.indicators?.rsi?.toFixed(1)}\n` +
                  `  MSI: ${data.indicators?.msi?.toFixed(1)}\n` +
                  `  MACD: ${data.indicators?.macd?.toFixed(4)}\n` +
                  `  Volume Ratio: ${data.indicators?.volume_ratio?.toFixed(2)}x`;
            
            alert(details);
        })
        .catch(error => {
            console.error('Error getting signal details:', error);
        });
}

function executeTradeFromSignal(symbol) {
    if (confirm(`Execute trade for ${symbol} based on signal?`)) {
        // Navigate to trade page with symbol pre-filled
        window.location.href = `/trade?symbol=${symbol}`;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Update trading mode display
    fetch('/api/mode/current')
        .then(response => response.json())
        .then(data => {
            if (data.mode) {
                document.getElementById('mode-display').textContent = data.mode.toUpperCase();
            }
        })
        .catch(() => {
            document.getElementById('mode-display').textContent = 'UNKNOWN';
        });
    
    // Check scanner status
    updateScannerStatus();
    
    updateDashboard();
    setInterval(updateDashboard, 5000);  // Update every 5 seconds
    
    // Update signals if scanner is running
    updateSignals();
    setInterval(() => {
        if (scannerRunning) {
            updateSignals();
        }
    }, 10000);  // Update signals every 10 seconds
});

// WebSocket connection
socket.on('connect', function() {
    console.log('Connected to trading system');
});

socket.on('status', function(data) {
    console.log('Status:', data);
});

// Notifications
function loadNotifications() {
    fetch('/api/notifications?limit=10&unread_only=true')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('notification-badge');
            const count = data.notifications ? data.notifications.length : 0;
            
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
            
            // Update notifications list
            const list = document.getElementById('notifications-list');
            if (data.notifications && data.notifications.length > 0) {
                list.innerHTML = data.notifications.map(n => `
                    <div class="border-bottom pb-2 mb-2" onclick="markRead(${n.id})" style="cursor: pointer;">
                        <div class="d-flex justify-content-between">
                            <strong style="font-size: 0.8rem;">${n.title}</strong>
                            <span class="badge bg-${n.type === 'success' ? 'success' : n.type === 'warning' ? 'warning' : n.type === 'error' ? 'danger' : 'info'}" style="font-size: 0.7rem;">${n.type}</span>
                        </div>
                        <div style="font-size: 0.75rem; color: #6c757d;">${n.message}</div>
                        <div style="font-size: 0.7rem; color: #999;">${new Date(n.timestamp).toLocaleString()}</div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<p class="text-muted text-center mb-0" style="font-size: 0.8rem;">No new notifications</p>';
            }
        })
        .catch(error => console.error('Error loading notifications:', error));
}

function toggleNotifications() {
    const panel = document.getElementById('notifications-panel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    if (panel.style.display === 'block') {
        loadNotifications();
    }
}

function markRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read`, { method: 'POST' })
        .then(() => loadNotifications());
}

function markAllRead() {
    fetch('/api/notifications/read-all', { method: 'POST' })
        .then(() => loadNotifications());
}

// Load notifications periodically
setInterval(loadNotifications, 10000);
loadNotifications();

