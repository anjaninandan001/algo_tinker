// static/js/portfolio.js

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const refreshBtn = document.getElementById('refreshPortfolioBtn');
    const cashBalance = document.getElementById('cashBalance');
    const totalTrades = document.getElementById('totalTrades');
    const winRate = document.getElementById('winRate');
    const profitLoss = document.getElementById('profitLoss');
    const positionsTableBody = document.getElementById('positionsTableBody');
    const tradesTableBody = document.getElementById('tradesTableBody');
    const marketStatus = document.getElementById('marketStatus');

    // Fetch market status
    fetchMarketStatus();

    // Add refresh button event listener
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshPortfolio);
    }

    // Fetch market status
    function fetchMarketStatus() {
        fetch('/api/markets')
            .then(response => response.json())
            .then(data => {
                if (data.is_open) {
                    marketStatus.innerHTML = 'Market Status: <span class="text-success">Open</span>';
                } else {
                    const nextOpen = new Date(data.next_open);
                    marketStatus.innerHTML = `Market Status: <span class="text-danger">Closed</span> (Opens ${formatDateTime(nextOpen)})`;
                }
            })
            .catch(error => {
                console.error('Error fetching market status:', error);
                marketStatus.textContent = 'Market Status: Unknown';
            });
    }

    // Refresh portfolio data
    function refreshPortfolio() {
        // Show loading spinner
        refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Refreshing...';
        refreshBtn.disabled = true;

        fetch('/api/portfolio/update')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error("Portfolio error:", data.error);
                    alert("Error refreshing portfolio: " + data.error);
                    return;
                }
                updatePortfolioUI(data.portfolio);
            })
            .catch(error => {
                console.error('Error refreshing portfolio:', error);
                alert("Error refreshing portfolio");
            })
            .finally(() => {
                // Reset button
                refreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i> Refresh';
                refreshBtn.disabled = false;
            });
    }

    // Update portfolio UI with new data
    function updatePortfolioUI(portfolio) {
        if (!portfolio) return;

        // Update cash balance
        cashBalance.textContent = `$${formatNumber(portfolio.cash)}`;

        // Update statistics
        if (portfolio.stats) {
            totalTrades.textContent = portfolio.stats.total_trades;
            winRate.textContent = `${formatNumber(portfolio.stats.win_rate)}%`;

            const pl = portfolio.stats.profit_loss;
            profitLoss.textContent = `$${formatNumber(pl)}`;
            profitLoss.className = pl > 0 ? 'metric-value positive' : pl < 0 ? 'metric-value negative' : 'metric-value';
        }

        // Update positions table
        if (portfolio.stats && portfolio.stats.active_positions) {
            if (portfolio.stats.active_positions.length > 0) {
                let positionsHTML = '';

                portfolio.stats.active_positions.forEach(position => {
                    positionsHTML += `
                        <tr>
                            <td>${position.symbol}</td>
                            <td>${position.quantity}</td>
                            <td>$${formatNumber(position.avg_price)}</td>
                            <td>$${formatNumber(position.total_cost)}</td>
                            <td class="text-success">-</td>
                        </tr>
                    `;
                });

                positionsTableBody.innerHTML = positionsHTML;
            } else {
                positionsTableBody.innerHTML = '<tr><td colspan="5" class="text-center">No active positions</td></tr>';
            }
        }

        // Update trades table
        if (portfolio.trades && portfolio.trades.length > 0) {
            let tradesHTML = '';

            // Show most recent trades first
            portfolio.trades.slice().reverse().forEach(trade => {
                tradesHTML += `
                    <tr>
                        <td>${trade.timestamp}</td>
                        <td>${trade.symbol}</td>
                        <td>
                            <span class="badge ${trade.side === 'buy' ? 'bg-success' : 'bg-danger'}">
                                ${trade.side.toUpperCase()}
                            </span>
                        </td>
                        <td>${trade.quantity}</td>
                        <td>$${formatNumber(trade.price)}</td>
                        <td>$${formatNumber(trade.price * trade.quantity)}</td>
                        <td>${trade.status}</td>
                        <td>${trade.notes || ''}</td>
                    </tr>
                `;
            });

            tradesTableBody.innerHTML = tradesHTML;
        } else {
            tradesTableBody.innerHTML = '<tr><td colspan="8" class="text-center">No trades found</td></tr>';
        }
    }

    // Utility: Format date and time
    function formatDateTime(date) {
        if (!(date instanceof Date)) date = new Date(date);
        return date.toLocaleString();
    }

    // Utility: Format number with commas and decimals
    function formatNumber(value) {
        return parseFloat(value).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
});
