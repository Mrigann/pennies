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
    document.getElementById('use-scaling').addEventListener('change', updateScalingPreview);
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
    
    // Update scaling preview if enabled
    updateScalingPreview();
}

function updateScalingPreview() {
    const useScaling = document.getElementById('use-scaling').checked;
    const previewDiv = document.getElementById('scaling-preview');
    const qty = parseFloat(document.getElementById('trade-qty').value) || 0;
    const symbol = document.getElementById('trade-symbol').value.toUpperCase().trim();
    
    if (!useScaling || qty < 2 || !symbol) {
        previewDiv.style.display = 'none';
        return;
    }
    
    // Get current price for preview
    if (currentStock && currentStock.price) {
        const entryPrice = currentStock.price;
        const stopLoss = entryPrice * (1 - 0.01); // 1% stop loss
        
        // Calculate scaling plan
        fetch('/api/scaling/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbol,
                entry_price: entryPrice,
                position_size: qty,
                stop_loss: stopLoss
            })
        })
        .then(response => response.json())
        .then(plan => {
            if (plan.error) {
                previewDiv.style.display = 'none';
                return;
            }
            
            const quickExit = plan.quick_exit;
            const runnerExits = plan.runner_exits;
            
            let runnerHtml = '';
            for (const [key, exit] of Object.entries(runnerExits)) {
                runnerHtml += `
                    <div class="small">
                        <strong>${key.toUpperCase()}:</strong> ${exit.size} shares @ $${exit.price.toFixed(4)} (${exit.target_pct.toFixed(2)}% profit)
                    </div>
                `;
            }
            
            document.getElementById('scaling-plan-details').innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <div class="text-success">
                            <strong>Quick Exit:</strong> ${quickExit.size} shares @ $${quickExit.price.toFixed(4)}<br>
                            <small>Target: ${quickExit.target_pct.toFixed(2)}% profit</small>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="text-primary">
                            <strong>Runner Positions:</strong><br>
                            ${runnerHtml}
                        </div>
                    </div>
                </div>
                <div class="mt-2">
                    <small class="text-muted">
                        Expected Profit: $${plan.expected_profit.total_profit.toFixed(2)} 
                        (${plan.expected_profit.total_profit_pct.toFixed(2)}%)
                    </small>
                </div>
            `;
            
            previewDiv.style.display = 'block';
        })
        .catch(error => {
            console.error('Error calculating scaling plan:', error);
            previewDiv.style.display = 'none';
        });
    }
}

function executeTrade() {
    const symbol = document.getElementById('trade-symbol').value.toUpperCase().trim();
    const side = document.getElementById('trade-side').value;
    const qty = parseFloat(document.getElementById('trade-qty').value);
    const orderType = document.getElementById('trade-order-type').value;
    const limitPrice = orderType === 'limit' ? parseFloat(document.getElementById('trade-limit-price').value) : null;
    const useScaling = document.getElementById('use-scaling').checked;
    
    if (!symbol || !qty || qty <= 0) {
        alert('Please fill in all required fields');
        return;
    }
    
    if (orderType === 'limit' && !limitPrice) {
        alert('Please enter a limit price');
        return;
    }
    
    if (useScaling && qty < 2) {
        alert('Scaling strategy requires at least 2 shares');
        return;
    }
    
    const scalingText = useScaling ? ' with scaling exit strategy' : '';
    if (!confirm(`Confirm ${side.toUpperCase()} ${qty} shares of ${symbol}${scalingText}?`)) {
        return;
    }
    
    const tradeData = {
        symbol: symbol,
        qty: qty,
        side: side,
        order_type: orderType,
        use_scaling: useScaling
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
            let scalingInfo = '';
            if (data.scaling_plan) {
                const plan = data.scaling_plan;
                scalingInfo = `
                    <hr>
                    <strong>Scaling Exit Plan Created:</strong><br>
                    <small>
                        Quick Exit: ${plan.quick_exit.size} shares @ $${plan.quick_exit.price.toFixed(4)}<br>
                        Runner: ${Object.values(plan.runner_exits).reduce((sum, e) => sum + e.size, 0)} shares for higher targets<br>
                        Expected Profit: $${plan.expected_profit.total_profit.toFixed(2)}
                    </small>
                `;
            }
            
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <strong>Order Placed Successfully!</strong><br>
                    Order ID: ${data.id}<br>
                    Status: ${data.status}
                    ${scalingInfo}
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

function optimizePositionSize() {
    const symbol = document.getElementById('trade-symbol').value.toUpperCase().trim();
    const entryPrice = currentStock ? currentStock.price : parseFloat(document.getElementById('trade-limit-price').value);
    
    if (!symbol || !entryPrice || entryPrice <= 0) {
        alert('Please select a stock first or enter a limit price');
        return;
    }
    
    // Get account info for available capital
    fetch('/api/account')
        .then(response => response.json())
        .then(account => {
            const availableCapital = parseFloat(account.buying_power || 0);
            const stopLoss = entryPrice * (1 - 0.01); // 1% stop loss
            
            // Calculate optimized size
            fetch('/api/scaling/optimize-size', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    entry_price: entryPrice,
                    stop_loss: stopLoss,
                    available_capital: availableCapital
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                const optimalSize = data.optimal_size;
                const details = data.sizing_details;
                
                if (optimalSize <= 0) {
                    alert('Position too small for scaling strategy. Minimum 2 shares required.');
                    return;
                }
                
                document.getElementById('optimized-size-value').textContent = optimalSize;
                document.getElementById('optimized-size-details').innerHTML = `
                    <div class="row">
                        <div class="col-6">
                            <strong>Quick Exit:</strong> ${details.quick_exit_size} shares<br>
                            <strong>Runner:</strong> ${details.runner_size} shares
                        </div>
                        <div class="col-6">
                            <strong>Risk:</strong> $${details.risk_amount.toFixed(2)}<br>
                            <strong>Capital Required:</strong> $${details.capital_required.toFixed(2)}
                        </div>
                    </div>
                `;
                document.getElementById('optimized-size-result').style.display = 'block';
            })
            .catch(error => {
                console.error('Error optimizing size:', error);
                alert('Error calculating optimal size');
            });
        })
        .catch(error => {
            console.error('Error getting account:', error);
            alert('Error getting account information');
        });
}

function useOptimizedSize() {
    const optimizedSize = document.getElementById('optimized-size-value').textContent;
    document.getElementById('trade-qty').value = optimizedSize;
    updateTradeSummary();
}

function clearTradeForm() {
    document.getElementById('trade-form').reset();
    document.getElementById('limit-price-row').style.display = 'none';
    document.getElementById('selected-stock').style.display = 'none';
    document.getElementById('optimized-size-result').style.display = 'none';
    document.getElementById('scaling-preview').style.display = 'none';
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

// Filter state
let currentFilters = {
    status: 'all',
    time: 'all',
    limit: '',
    sort: 'time',
    order: 'desc'
};

function toggleFilters() {
    const filterControls = document.getElementById('filter-controls');
    filterControls.style.display = filterControls.style.display === 'none' ? 'block' : 'none';
}

function applyFilters() {
    // Get filter values
    currentFilters.status = document.getElementById('filter-status').value;
    currentFilters.time = document.getElementById('filter-time').value;
    currentFilters.limit = document.getElementById('filter-limit').value;
    currentFilters.sort = document.getElementById('filter-sort').value;
    currentFilters.order = document.getElementById('filter-order').value;
    
    loadRecentTrades();
}

function resetFilters() {
    document.getElementById('filter-status').value = 'all';
    document.getElementById('filter-time').value = 'all';
    document.getElementById('filter-limit').value = '';
    document.getElementById('filter-sort').value = 'time';
    document.getElementById('filter-order').value = 'desc';
    
    currentFilters = {
        status: 'all',
        time: 'all',
        limit: '',
        sort: 'time',
        order: 'desc'
    };
    
    loadRecentTrades();
}

function sortBy(column) {
    const currentSort = document.getElementById('filter-sort').value;
    const currentOrder = document.getElementById('filter-order').value;
    
    if (currentSort === column) {
        // Toggle order
        document.getElementById('filter-order').value = currentOrder === 'desc' ? 'asc' : 'desc';
    } else {
        // Change sort column
        document.getElementById('filter-sort').value = column;
        document.getElementById('filter-order').value = 'desc';
    }
    
    applyFilters();
}

function loadRecentTrades() {
    // Build query string
    const params = new URLSearchParams();
    if (currentFilters.status !== 'all') params.append('status', currentFilters.status);
    if (currentFilters.time !== 'all') params.append('time', currentFilters.time);
    if (currentFilters.limit) params.append('limit', currentFilters.limit);
    if (currentFilters.sort) params.append('sort', currentFilters.sort);
    if (currentFilters.order) params.append('order', currentFilters.order);
    
    const url = '/api/orders/recent' + (params.toString() ? '?' + params.toString() : '');
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('recent-trades');
            const orders = data.orders || [];
            
            // Update filter count
            const filterCount = document.getElementById('filter-count');
            if (filterCount) {
                filterCount.textContent = `Showing ${orders.length} order${orders.length !== 1 ? 's' : ''}`;
            }
            
            if (!orders || orders.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No orders found</td></tr>';
                return;
            }
            
            tbody.innerHTML = orders.map(order => {
                const submittedAt = order.submitted_at || '';
                let timeDisplay = 'N/A';
                let dateDisplay = '';
                
                if (submittedAt) {
                    try {
                        const date = new Date(submittedAt);
                        timeDisplay = date.toLocaleTimeString();
                        dateDisplay = date.toLocaleDateString();
                    } catch (e) {
                        timeDisplay = submittedAt;
                    }
                }
                
                const status = (order.status || '').toLowerCase();
                let statusClass = 'secondary';
                if (status === 'filled') statusClass = 'success';
                else if (status === 'open' || status === 'pending') statusClass = 'warning';
                else if (status === 'cancelled') statusClass = 'danger';
                else if (status === 'partially_filled') statusClass = 'info';
                
                const price = order.filled_avg_price || order.limit_price || order.stop_price || 0;
                const side = (order.side || '').toLowerCase();
                
                return `
                    <tr>
                        <td>
                            <div class="small">${timeDisplay}</div>
                            <div class="text-muted" style="font-size: 0.75rem;">${dateDisplay}</div>
                        </td>
                        <td><strong>${order.symbol || 'N/A'}</strong></td>
                        <td><span class="badge bg-${side === 'buy' ? 'success' : 'danger'}">${(side || '').toUpperCase()}</span></td>
                        <td>${order.qty || 0}</td>
                        <td>$${parseFloat(price).toFixed(4)}</td>
                        <td><span class="badge bg-${statusClass}">${(order.status || '').toUpperCase()}</span></td>
                    </tr>
                `;
            }).join('');
        })
        .catch(error => {
            console.error('Error loading recent trades:', error);
            const tbody = document.getElementById('recent-trades');
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error loading orders</td></tr>';
        });
}

