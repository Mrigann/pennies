// Trading interface JavaScript

let currentStock = null;
let buyingPower = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadWatchlist();
    loadAccountInfo();
    loadRecentTrades();
    
    // Update estimated cost as user types
    document.getElementById('trade-qty').addEventListener('input', updateTradeSummary);
    document.getElementById('trade-limit-price').addEventListener('input', updateTradeSummary);
    document.getElementById('trade-order-type').addEventListener('change', function() {
        const limitRow = document.getElementById('limit-price-row');
        if (this.value === 'limit') {
            limitRow.style.display = 'block';
            document.getElementById('trade-limit-price').required = true;
        } else {
            limitRow.style.display = 'none';
            document.getElementById('trade-limit-price').required = false;
        }
        updateTradeSummary();
    });
    
    // Auto-refresh watchlist every 30 seconds
    setInterval(loadWatchlist, 30000);
    setInterval(loadRecentTrades, 10000);
});

function searchStock() {
    const symbol = document.getElementById('stock-search').value.toUpperCase().trim();
    if (!symbol) {
        alert('Please enter a stock symbol');
        return;
    }
    
    fetch(`/api/stock/quote/${symbol}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }
            displayStockDetails(data);
            selectStockForTrading(data);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error searching for stock');
        });
}

function displayStockDetails(data) {
    const resultsDiv = document.getElementById('search-results');
    const detailsDiv = document.getElementById('stock-details');
    
    resultsDiv.style.display = 'none';
    detailsDiv.style.display = 'block';
    
    const change = data.change || 0;
    const changePercent = data.change_percent || 0;
    const changeClass = change >= 0 ? 'price-up' : 'price-down';
    const changeSign = change >= 0 ? '+' : '';
    
    detailsDiv.innerHTML = `
        <div class="card">
            <div class="card-body">
                <h4>${data.symbol}</h4>
                <h2 class="${changeClass}">$${data.price.toFixed(4)}</h2>
                <div class="${changeClass}">
                    ${changeSign}$${change.toFixed(4)} (${changeSign}${changePercent.toFixed(2)}%)
                </div>
                <hr>
                <div class="row">
                    <div class="col-6">
                        <small class="text-muted">Volume:</small><br>
                        <strong>${(data.volume || 0).toLocaleString()}</strong>
                    </div>
                    <div class="col-6">
                        <small class="text-muted">High:</small><br>
                        <strong>$${(data.high || 0).toFixed(4)}</strong>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-6">
                        <small class="text-muted">Low:</small><br>
                        <strong>$${(data.low || 0).toFixed(4)}</strong>
                    </div>
                    <div class="col-6">
                        <button class="btn btn-primary btn-sm" onclick="addToWatchlistFromSearch('${data.symbol}')">
                            <i class="bi bi-plus-circle"></i> Add to Watchlist
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function selectStockForTrading(data) {
    currentStock = data;
    document.getElementById('trade-symbol').value = data.symbol;
    document.getElementById('selected-stock').style.display = 'block';
    document.getElementById('selected-symbol').textContent = data.symbol;
    document.getElementById('selected-price').textContent = `$${data.price.toFixed(4)}`;
    
    const change = data.change || 0;
    const changePercent = data.change_percent || 0;
    const changeClass = change >= 0 ? 'price-up' : 'price-down';
    const changeSign = change >= 0 ? '+' : '';
    
    document.getElementById('selected-change').innerHTML = 
        `<span class="${changeClass}">${changeSign}$${change.toFixed(4)} (${changeSign}${changePercent.toFixed(2)}%)</span>`;
    
    updateTradeSummary();
}

function updateTradeSummary() {
    const qty = parseFloat(document.getElementById('trade-qty').value) || 0;
    const orderType = document.getElementById('trade-order-type').value;
    let price = currentStock ? currentStock.price : 0;
    
    if (orderType === 'limit') {
        const limitPrice = parseFloat(document.getElementById('trade-limit-price').value);
        if (limitPrice) {
            price = limitPrice;
        }
    }
    
    const estimatedCost = qty * price;
    document.getElementById('estimated-cost').textContent = `$${estimatedCost.toFixed(2)}`;
    
    const buyingPowerEl = document.getElementById('buying-power-display');
    if (buyingPower > 0) {
        buyingPowerEl.textContent = `$${buyingPower.toFixed(2)}`;
        if (estimatedCost > buyingPower) {
            buyingPowerEl.className = 'fw-bold text-danger';
        } else {
            buyingPowerEl.className = 'fw-bold text-success';
        }
    }
}

function executeTrade() {
    const symbol = document.getElementById('trade-symbol').value.toUpperCase().trim();
    const side = document.getElementById('trade-side').value;
    const qty = parseFloat(document.getElementById('trade-qty').value);
    const orderType = document.getElementById('trade-order-type').value;
    const limitPrice = orderType === 'limit' ? parseFloat(document.getElementById('trade-limit-price').value) : null;
    
    if (!symbol || !qty || qty <= 0) {
        alert('Please fill in all required fields');
        return;
    }
    
    if (orderType === 'limit' && !limitPrice) {
        alert('Please enter a limit price');
        return;
    }
    
    if (!confirm(`Confirm ${side.toUpperCase()} ${qty} shares of ${symbol}?`)) {
        return;
    }
    
    const tradeData = {
        symbol: symbol,
        qty: qty,
        side: side,
        order_type: orderType
    };
    
    if (limitPrice) {
        tradeData.limit_price = limitPrice;
    }
    
    fetch('/api/trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tradeData)
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('trade-result');
        if (data.error) {
            resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
        } else {
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <strong>Order Placed Successfully!</strong><br>
                    Order ID: ${data.id}<br>
                    Status: ${data.status}
                </div>
            `;
            clearTradeForm();
            loadRecentTrades();
            loadAccountInfo();
        }
        resultDiv.style.display = 'block';
        setTimeout(() => {
            resultDiv.style.display = 'none';
        }, 5000);
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('trade-result').innerHTML = 
            `<div class="alert alert-danger">Error executing trade: ${error.message}</div>`;
        document.getElementById('trade-result').style.display = 'block';
    });
}

function clearTradeForm() {
    document.getElementById('trade-form').reset();
    document.getElementById('limit-price-row').style.display = 'none';
    document.getElementById('selected-stock').style.display = 'none';
    currentStock = null;
    updateTradeSummary();
}

function loadWatchlist() {
    fetch('/api/watchlist')
        .then(response => response.json())
        .then(data => {
            const watchlistDiv = document.getElementById('watchlist-items');
            
            if (!data.symbols || data.symbols.length === 0) {
                watchlistDiv.innerHTML = '<div class="text-center p-3 text-muted">Watchlist is empty</div>';
                return;
            }
            
            watchlistDiv.innerHTML = data.symbols.map(symbol => `
                <div class="watchlist-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${symbol}</strong>
                        <button class="btn btn-sm btn-link text-primary" onclick="loadWatchlistStock('${symbol}')">
                            <i class="bi bi-arrow-right-circle"></i> Trade
                        </button>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="removeFromWatchlist('${symbol}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `).join('');
        })
        .catch(error => {
            console.error('Error loading watchlist:', error);
        });
}

function loadWatchlistStock(symbol) {
    document.getElementById('stock-search').value = symbol;
    searchStock();
    // Scroll to trading panel
    document.querySelector('.trade-panel').scrollIntoView({ behavior: 'smooth' });
}

function addToWatchlist() {
    const modal = new bootstrap.Modal(document.getElementById('addWatchlistModal'));
    modal.show();
}

function confirmAddToWatchlist() {
    const symbol = document.getElementById('watchlist-symbol-input').value.toUpperCase().trim();
    if (!symbol) {
        alert('Please enter a symbol');
        return;
    }
    
    fetch('/api/watchlist/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: symbol })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            bootstrap.Modal.getInstance(document.getElementById('addWatchlistModal')).hide();
            document.getElementById('watchlist-symbol-input').value = '';
            loadWatchlist();
        }
    })
    .catch(error => {
        alert('Error adding to watchlist');
    });
}

function addToWatchlistFromSearch(symbol) {
    fetch('/api/watchlist/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: symbol })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            loadWatchlist();
            alert(`${symbol} added to watchlist`);
        }
    })
    .catch(error => {
        alert('Error adding to watchlist');
    });
}

function removeFromWatchlist(symbol) {
    if (!confirm(`Remove ${symbol} from watchlist?`)) {
        return;
    }
    
    fetch('/api/watchlist/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: symbol })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            loadWatchlist();
        }
    })
    .catch(error => {
        alert('Error removing from watchlist');
    });
}

function loadAccountInfo() {
    fetch('/api/account')
        .then(response => response.json())
        .then(data => {
            if (data.buying_power) {
                buyingPower = parseFloat(data.buying_power);
                updateTradeSummary();
            }
        })
        .catch(error => {
            console.error('Error loading account info:', error);
        });
}

function loadRecentTrades() {
    fetch('/api/orders/recent')
        .then(response => response.json())
        .then(orders => {
            const tbody = document.getElementById('recent-trades');
            
            if (!orders || orders.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No recent trades</td></tr>';
                return;
            }
            
            tbody.innerHTML = orders.slice(0, 10).map(order => {
                const time = order.submitted_at ? new Date(order.submitted_at).toLocaleTimeString() : 'N/A';
                const statusClass = order.status === 'filled' ? 'success' : 
                                  order.status === 'pending' ? 'warning' : 'secondary';
                
                return `
                    <tr>
                        <td>${time}</td>
                        <td><strong>${order.symbol}</strong></td>
                        <td><span class="badge bg-${order.side === 'buy' ? 'success' : 'danger'}">${order.side.toUpperCase()}</span></td>
                        <td>${order.qty}</td>
                        <td>$${(order.filled_avg_price || 0).toFixed(4)}</td>
                        <td><span class="badge bg-${statusClass}">${order.status}</span></td>
                    </tr>
                `;
            }).join('');
        })
        .catch(error => {
            console.error('Error loading recent trades:', error);
        });
}

