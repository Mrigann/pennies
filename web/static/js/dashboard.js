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
    
    updateDashboard();
    setInterval(updateDashboard, 5000);  // Update every 5 seconds
});

// WebSocket connection
socket.on('connect', function() {
    console.log('Connected to trading system');
});

socket.on('status', function(data) {
    console.log('Status:', data);
});

