// Trade Approvals JavaScript

let refreshInterval = null;

document.addEventListener('DOMContentLoaded', function() {
    loadPendingTrades();
    checkSystemStatus();
    
    // Auto-refresh every 10 seconds
    refreshInterval = setInterval(() => {
        loadPendingTrades();
        checkSystemStatus();
    }, 10000);
});

function loadPendingTrades() {
    fetch('/api/trades/pending')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error loading pending trades:', data.error);
                showError(data.error);
                return;
            }
            
            displayPendingTrades(data);
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Failed to load pending trades');
        });
}

function displayPendingTrades(trades) {
    const container = document.getElementById('pending-trades-container');
    const noTrades = document.getElementById('no-trades');
    
    if (!trades || trades.length === 0) {
        container.style.display = 'none';
        noTrades.style.display = 'block';
        return;
    }
    
    container.style.display = 'block';
    noTrades.style.display = 'none';
    
    container.innerHTML = '';
    
    trades.forEach(trade => {
        const tradeCard = createTradeCard(trade);
        container.appendChild(tradeCard);
    });
}

function createTradeCard(trade) {
    const card = document.createElement('div');
    card.className = `card trade-card ${getBandClass(trade.trading_band)}`;
    
    const bandPosition = trade.band_position || 50;
    const dailyHigh = trade.daily_high || 0;
    const dailyLow = trade.daily_low || 0;
    const currentPrice = trade.current_price || trade.entry_price || 0;
    const upside = trade.upside_potential || {};
    const exitRoutes = trade.exit_routes || {};
    
    card.innerHTML = `
        <div class="card-header d-flex justify-content-between align-items-center">
            <div>
                <h4 class="mb-0">
                    <i class="bi bi-graph-up"></i> ${trade.symbol}
                    <span class="badge bg-warning pending-badge ms-2">PENDING</span>
                </h4>
                <small class="text-muted">Strategy: ${trade.strategy || 'Unknown'}</small>
            </div>
            <div>
                <button class="btn btn-success btn-sm me-2" onclick="approveTrade('${trade.id}')">
                    <i class="bi bi-check-circle"></i> Approve
                </button>
                <button class="btn btn-danger btn-sm" onclick="rejectTrade('${trade.id}')">
                    <i class="bi bi-x-circle"></i> Reject
                </button>
            </div>
        </div>
        <div class="card-body">
            <div class="row mb-3">
                <div class="col-md-6">
                    <h5>Trade Details</h5>
                    <table class="table table-sm">
                        <tr>
                            <td><strong>Entry Price:</strong></td>
                            <td>$${parseFloat(trade.entry_price).toFixed(4)}</td>
                        </tr>
                        <tr>
                            <td><strong>Position Size:</strong></td>
                            <td>${parseInt(trade.position_size)} shares</td>
                        </tr>
                        <tr>
                            <td><strong>Stop Loss:</strong></td>
                            <td class="text-danger">$${parseFloat(trade.stop_loss).toFixed(4)}</td>
                        </tr>
                        <tr>
                            <td><strong>Profit Target:</strong></td>
                            <td class="text-success">$${parseFloat(trade.profit_target).toFixed(4)}</td>
                        </tr>
                        <tr>
                            <td><strong>Risk Amount:</strong></td>
                            <td>$${parseFloat(trade.risk_amount).toFixed(2)}</td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h5>Daily Analysis</h5>
                    <table class="table table-sm">
                        <tr>
                            <td><strong>Daily High:</strong></td>
                            <td class="text-success">$${parseFloat(dailyHigh).toFixed(4)}</td>
                        </tr>
                        <tr>
                            <td><strong>Daily Low:</strong></td>
                            <td class="text-danger">$${parseFloat(dailyLow).toFixed(4)}</td>
                        </tr>
                        <tr>
                            <td><strong>Current Price:</strong></td>
                            <td>$${parseFloat(currentPrice).toFixed(4)}</td>
                        </tr>
                        <tr>
                            <td><strong>Trading Band:</strong></td>
                            <td>
                                <span class="badge ${getBandBadgeClass(trade.trading_band)}">
                                    ${trade.trading_band || 'N/A'}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td><strong>Band Position:</strong></td>
                            <td>
                                <div class="progress" style="height: 20px;">
                                    <div class="progress-bar" role="progressbar" 
                                         style="width: ${bandPosition}%" 
                                         aria-valuenow="${bandPosition}" 
                                         aria-valuemin="0" 
                                         aria-valuemax="100">
                                        ${bandPosition.toFixed(1)}%
                                    </div>
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-6">
                    <h5>Upside Potential</h5>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-success metric-badge">
                            To Target: +${(upside.to_profit_target_pct || 0).toFixed(2)}%
                        </span>
                        <span class="badge bg-info metric-badge">
                            To Daily High: +${(upside.to_daily_high_pct || 0).toFixed(2)}%
                        </span>
                        <span class="badge bg-primary metric-badge">
                            Max Upside: +${(upside.max_upside_pct || 0).toFixed(2)}%
                        </span>
                    </div>
                </div>
                <div class="col-md-6">
                    <h5>Exit Routes</h5>
                    <div class="exit-routes">
                        ${createExitRoute('Profit Target', exitRoutes.profit_target, 'profit')}
                        ${createExitRoute('Daily High', exitRoutes.daily_high, 'profit')}
                        ${createExitRoute('Stop Loss', exitRoutes.stop_loss, 'loss')}
                    </div>
                </div>
            </div>
            
            ${trade.signal_info ? `
            <div class="row">
                <div class="col-md-12">
                    <h5>Signal Information</h5>
                    <div class="d-flex flex-wrap gap-2">
                        ${trade.signal_info.rsi ? `
                            <span class="badge bg-secondary">RSI: ${parseFloat(trade.signal_info.rsi).toFixed(2)}</span>
                        ` : ''}
                        ${trade.signal_info.volume_ratio ? `
                            <span class="badge bg-secondary">Volume Ratio: ${parseFloat(trade.signal_info.volume_ratio).toFixed(2)}x</span>
                        ` : ''}
                        ${trade.signal_info.momentum ? `
                            <span class="badge bg-secondary">Momentum: ${(parseFloat(trade.signal_info.momentum) * 100).toFixed(2)}%</span>
                        ` : ''}
                    </div>
                </div>
            </div>
            ` : ''}
        </div>
    `;
    
    return card;
}

function createExitRoute(label, route, type) {
    if (!route || !route.price) {
        return '';
    }
    
    const price = parseFloat(route.price).toFixed(4);
    const distancePct = route.distance_pct ? parseFloat(route.distance_pct).toFixed(2) : '0.00';
    const distanceDollars = route.distance_dollars ? parseFloat(route.distance_dollars).toFixed(4) : '0.0000';
    
    return `
        <div class="exit-route ${type}">
            <strong>${label}:</strong> $${price} 
            (${distancePct >= 0 ? '+' : ''}${distancePct}% / $${distanceDollars >= 0 ? '+' : ''}${distanceDollars})
        </div>
    `;
}

function getBandClass(band) {
    if (!band) return '';
    if (band.includes('Upper')) return 'upper-band';
    if (band.includes('Lower')) return 'lower-band';
    if (band.includes('Middle')) return 'middle-band';
    return '';
}

function getBandBadgeClass(band) {
    if (!band) return 'bg-secondary';
    if (band.includes('Upper')) return 'bg-danger';
    if (band.includes('Lower')) return 'bg-success';
    if (band.includes('Middle')) return 'bg-warning';
    return 'bg-secondary';
}

function approveTrade(tradeId) {
    if (!confirm('Are you sure you want to approve and execute this trade?')) {
        return;
    }
    
    fetch('/api/trades/approve', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ trade_id: tradeId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error approving trade: ' + data.error);
        } else {
            alert('Trade approved and executed successfully!');
            loadPendingTrades();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to approve trade');
    });
}

function rejectTrade(tradeId) {
    if (!confirm('Are you sure you want to reject this trade?')) {
        return;
    }
    
    fetch('/api/trades/reject', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ trade_id: tradeId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error rejecting trade: ' + data.error);
        } else {
            alert('Trade rejected');
            loadPendingTrades();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to reject trade');
    });
}

function showError(message) {
    const container = document.getElementById('pending-trades-container');
    container.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <i class="bi bi-exclamation-triangle"></i> ${message}
        </div>
    `;
}

function checkSystemStatus() {
    fetch('/api/system/status')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error checking system status:', data.error);
                return;
            }
            
            const statusBadge = document.getElementById('system-status');
            const startBtn = document.getElementById('start-system-btn');
            const stopBtn = document.getElementById('stop-system-btn');
            
            if (data.running) {
                statusBadge.textContent = `Status: Running (${data.pending_trades_count} pending)`;
                statusBadge.className = 'badge bg-success me-2';
                startBtn.style.display = 'none';
                stopBtn.style.display = 'inline-block';
            } else {
                statusBadge.textContent = 'Status: Stopped';
                statusBadge.className = 'badge bg-secondary me-2';
                startBtn.style.display = 'inline-block';
                stopBtn.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error checking system status:', error);
        });
}

function startSystem() {
    fetch('/api/system/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error starting system: ' + data.error);
        } else {
            alert('Trading system started!');
            checkSystemStatus();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to start trading system');
    });
}

function stopSystem() {
    if (!confirm('Are you sure you want to stop the trading system? This will prevent new trades from being queued.')) {
        return;
    }
    
    fetch('/api/system/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error stopping system: ' + data.error);
        } else {
            alert('Trading system stopped!');
            checkSystemStatus();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to stop trading system');
    });
}

