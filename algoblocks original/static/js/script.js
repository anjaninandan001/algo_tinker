// AlgoBlocks main JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const symbolSelect = document.getElementById('symbol');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const initialCapitalInput = document.getElementById('initialCapital');
    const runBacktestBtn = document.getElementById('runBacktestBtn');
    const paperTradeBtn = document.getElementById('paperTradeBtn');
    const saveStrategyBtn = document.getElementById('saveStrategyBtn');
    const loadStrategyBtn = document.getElementById('loadStrategyBtn');
    const clearStrategyBtn = document.getElementById('clearStrategyBtn');
    const strategyCanvas = document.getElementById('strategyCanvas');
    const performanceMetrics = document.getElementById('performanceMetrics');
    const tradesTableBody = document.getElementById('tradesTableBody');
    const marketStatus = document.getElementById('marketStatus');
    const symbolSearch = document.getElementById('symbolSearch');
    const searchSymbolBtn = document.getElementById('searchSymbolBtn');
    
    // Block management
    let nextBlockId = 1;
    let blocks = [];
    let selectedBlock = null;
    let chartInstance = null;
    
    // Initialize date inputs with reasonable defaults
    const today = new Date();
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(today.getFullYear() - 1);
    startDateInput.value = formatDate(oneYearAgo);
    endDateInput.value = formatDate(today);
    
    // Initialize TradingView Chart
    const tradingViewChart = new TradingView.widget({
        container_id: 'tradingViewChart',
        symbol: 'AAPL',
        interval: 'D',
        timezone: 'Etc/UTC',
        theme: 'light',
        style: '1',
        locale: 'en',
        toolbar_bg: '#f1f3f6',
        enable_publishing: false,
        hide_top_toolbar: false,
        hide_legend: false,
        save_image: false,
        height: '100%',
        width: '100%'
    });
    
    // Fetch market status
    fetchMarketStatus();
    
    // Set up drag and drop functionality
    setupDragAndDrop();
    
    // Set up button event listeners
    runBacktestBtn.addEventListener('click', runBacktest);
    paperTradeBtn.addEventListener('click', startPaperTrading);
    saveStrategyBtn.addEventListener('click', saveStrategy);
    loadStrategyBtn.addEventListener('click', loadStrategy);
    clearStrategyBtn.addEventListener('click', clearStrategy);
    symbolSelect.addEventListener('change', updateSymbol);
    searchSymbolBtn.addEventListener('click', searchSymbols);
    
    // Symbol search event
    symbolSearch.addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            searchSymbols();
        }
    });
    
    // Block configuration modal elements and event listener
    const blockConfigModal = new bootstrap.Modal(document.getElementById('blockConfigModal'));
    const blockConfigBody = document.getElementById('blockConfigBody');
    const saveBlockConfigBtn = document.getElementById('saveBlockConfigBtn');
    saveBlockConfigBtn.addEventListener('click', saveBlockConfig);
    
    // Search for symbols
    function searchSymbols() {
        const query = symbolSearch.value.trim();
        if (query.length < 1) return;
        
        // Show loading in symbol select
        symbolSelect.innerHTML = '<option value="">Loading...</option>';
        
        fetch(`/api/search-symbols?query=${encodeURIComponent(query)}&per_page=100`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error("Symbol search error:", data.error);
                    return;
                }
                
                // Update symbol select with results
                symbolSelect.innerHTML = '';
                if (data.symbols && data.symbols.length > 0) {
                    data.symbols.forEach(item => {
                        const option = document.createElement('option');
                        option.value = item.symbol;
                        option.textContent = `${item.symbol} - ${item.name || ''}`;
                        symbolSelect.appendChild(option);
                    });
                    
                    // Update chart with first symbol
                    updateSymbol();
                } else {
                    symbolSelect.innerHTML = '<option value="">No results found</option>';
                }
            })
            .catch(error => {
                console.error('Error searching symbols:', error);
                symbolSelect.innerHTML = '<option value="">Error loading symbols</option>';
            });
    }
    
    // Fetch market status periodically
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
    
    // Update TradingView chart symbol
    function updateSymbol() {
        const symbol = symbolSelect.value;
        if (symbol) {
            tradingViewChart.setSymbol(symbol);
        }
    }
    
    // Setup drag and drop functionality
    function setupDragAndDrop() {
        const draggableBlocks = document.querySelectorAll('.block');
        
        // Make blocks draggable
        draggableBlocks.forEach(block => {
            block.addEventListener('dragstart', handleDragStart);
        });
        
        // Setup canvas as drop target
        strategyCanvas.addEventListener('dragover', handleDragOver);
        strategyCanvas.addEventListener('drop', handleDrop);
    }
    
    // Handle drag start
    function handleDragStart(e) {
        e.dataTransfer.setData('text/plain', JSON.stringify({
            type: this.dataset.type,
            indicatorType: this.dataset.indicatorType || null
        }));
    }
    
    // Handle drag over
    function handleDragOver(e) {
        e.preventDefault();
    }
    
    // Handle drop
    function handleDrop(e) {
        e.preventDefault();
        const canvasRect = strategyCanvas.getBoundingClientRect();
        const x = e.clientX - canvasRect.left;
        const y = e.clientY - canvasRect.top;
        
        try {
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            createBlock(data.type, data.indicatorType, x, y);
        } catch (err) {
            console.error('Error parsing drag data:', err);
        }
    }
    
    // Create a block on the canvas
    function createBlock(type, indicatorType, x, y) {
        const blockId = `block-${nextBlockId++}`;
        const block = document.createElement('div');
        block.id = blockId;
        block.className = `canvas-block ${type}`;
        block.style.left = `${x}px`;
        block.style.top = `${y}px`;
        
        let blockData = {
            id: blockId,
            type: type,
            x: x,
            y: y
        };
        
        let blockTitle, blockSettings;
        
        if (type === 'indicator' && indicatorType) {
            blockData.indicatorType = indicatorType;
            switch (indicatorType) {
                case 'SMA':
                    blockData.period = 20;
                    blockTitle = 'Simple Moving Average (SMA)';
                    blockSettings = `Period: ${blockData.period}`;
                    break;
                case 'EMA':
                    blockData.period = 20;
                    blockTitle = 'Exponential Moving Average (EMA)';
                    blockSettings = `Period: ${blockData.period}`;
                    break;
                case 'RSI':
                    blockData.period = 14;
                    blockTitle = 'Relative Strength Index (RSI)';
                    blockSettings = `Period: ${blockData.period}`;
                    break;
                case 'MACD':
                    blockData.fastPeriod = 12;
                    blockData.slowPeriod = 26;
                    blockData.signalPeriod = 9;
                    blockTitle = 'MACD';
                    blockSettings = `Fast: ${blockData.fastPeriod}, Slow: ${blockData.slowPeriod}, Signal: ${blockData.signalPeriod}`;
                    break;
                default:
                    blockTitle = indicatorType;
                    blockSettings = '';
            }
        } else if (type === 'entry') {
            blockData.conditions = [];
            blockTitle = 'Entry Rule';
            blockSettings = 'No conditions set';
        } else if (type === 'exit') {
            blockData.conditions = [];
            blockTitle = 'Exit Rule';
            blockSettings = 'No conditions set';
        }
        
        block.innerHTML = `
            <div class="block-header">
                <span>${blockTitle}</span>
                <span class="block-remove" data-id="${blockId}">&times;</span>
            </div>
            <div class="block-content">
                <div class="block-settings">${blockSettings}</div>
            </div>
        `;
        
        // Make the block draggable
        block.draggable = true;
        block.addEventListener('dragstart', function(e) {
            // Store the current position
            const rect = this.getBoundingClientRect();
            const offsetX = e.clientX - rect.left;
            const offsetY = e.clientY - rect.top;
            
            e.dataTransfer.setData('text/plain', JSON.stringify({
                id: this.id,
                offsetX: offsetX,
                offsetY: offsetY
            }));
        });
        
        // Add click event to configure the block
        block.addEventListener('click', function() {
            const id = this.id;
            const block = blocks.find(b => b.id === id);
            if (block) {
                selectedBlock = block;
                showBlockConfig(block);
            }
        });
        
        // Add remove button functionality
        block.querySelector('.block-remove').addEventListener('click', function(e) {
            e.stopPropagation();
            removeBlock(this.dataset.id);
        });
        
        strategyCanvas.appendChild(block);
        blocks.push(blockData);
        
        // Remove the placeholder if it exists
        const placeholder = strategyCanvas.querySelector('.canvas-placeholder');
        if (placeholder) {
            placeholder.style.display = 'none';
        }
    }
    
    // Show block configuration modal
    function showBlockConfig(block) {
        let content = '';
        
        // Generate form based on block type
        if (block.type === 'indicator') {
            const indicatorType = block.indicatorType;
            
            if (indicatorType === 'SMA' || indicatorType === 'EMA' || indicatorType === 'RSI') {
                content = `
                    <div class="mb-3">
                        <label class="form-label">Period</label>
                        <input type="number" class="form-control" id="config-period" value="${block.period}">
                    </div>
                `;
            } else if (indicatorType === 'MACD') {
                content = `
                    <div class="mb-3">
                        <label class="form-label">Fast Period</label>
                        <input type="number" class="form-control" id="config-fast-period" value="${block.fastPeriod}">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Slow Period</label>
                        <input type="number" class="form-control" id="config-slow-period" value="${block.slowPeriod}">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Signal Period</label>
                        <input type="number" class="form-control" id="config-signal-period" value="${block.signalPeriod}">
                    </div>
                `;
            }
        } else if (block.type === 'entry' || block.type === 'exit') {
            // For simplicity, we'll allow only one condition in this example
            // In a real application, you might want to support multiple conditions
            let indicator = '';
            let operator = '>';
            let value = '';
            
            if (block.conditions && block.conditions.length > 0) {
                indicator = block.conditions[0].indicator || '';
                operator = block.conditions[0].operator || '>';
                value = block.conditions[0].value || '';
            }
            
            // Generate indicator options from existing blocks
            let indicatorOptions = '';
            blocks.filter(b => b.type === 'indicator').forEach(b => {
                let indicatorId = '';
                
                if (b.indicatorType === 'SMA' || b.indicatorType === 'EMA') {
                    indicatorId = `${b.indicatorType}_${b.period}`;
                } else if (b.indicatorType === 'RSI') {
                    indicatorId = `RSI_${b.period}`;
                } else if (b.indicatorType === 'MACD') {
                    indicatorId = 'MACD';
                }
                
                if (indicatorId) {
                    indicatorOptions += `<option value="${indicatorId}" ${indicator === indicatorId ? 'selected' : ''}>${indicatorId}</option>`;
                }
            });
            
            // Add price options
            const priceOptions = `
                <option value="close" ${indicator === 'close' ? 'selected' : ''}>Close Price</option>
                <option value="open" ${indicator === 'open' ? 'selected' : ''}>Open Price</option>
                <option value="high" ${indicator === 'high' ? 'selected' : ''}>High Price</option>
                <option value="low" ${indicator === 'low' ? 'selected' : ''}>Low Price</option>
            `;
            
            content = `
                <div class="mb-3">
                    <label class="form-label">Indicator</label>
                    <select class="form-select" id="config-indicator">
                        <option value="">Select an indicator</option>
                        ${priceOptions}
                        ${indicatorOptions}
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Operator</label>
                    <select class="form-select" id="config-operator">
                        <option value=">" ${operator === '>' ? 'selected' : ''}>Greater than (>)</option>
                        <option value=">=" ${operator === '>=' ? 'selected' : ''}>Greater than or equal to (>=)</option>
                        <option value="<" ${operator === '<' ? 'selected' : ''}>Less than (<)</option>
                        <option value="<=" ${operator === '<=' ? 'selected' : ''}>Less than or equal to (<=)</option>
                        <option value="==" ${operator === '==' ? 'selected' : ''}>Equal to (==)</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Value</label>
                    <input type="text" class="form-control" id="config-value" value="${value}">
                    <small class="form-text text-muted">Enter a number or another indicator ID</small>
                </div>
            `;
        }
        
        // Update modal content and show it
        blockConfigBody.innerHTML = content;
        blockConfigModal.show();
    }
    
    // Save block configuration
    function saveBlockConfig() {
        if (!selectedBlock) return;
        
        // Update block based on type
        if (selectedBlock.type === 'indicator') {
            if (selectedBlock.indicatorType === 'SMA' || selectedBlock.indicatorType === 'EMA' || selectedBlock.indicatorType === 'RSI') {
                const period = parseInt(document.getElementById('config-period').value) || 14;
                selectedBlock.period = period;
                
                // Update block display
                const blockElement = document.getElementById(selectedBlock.id);
                blockElement.querySelector('.block-settings').textContent = `Period: ${period}`;
            } else if (selectedBlock.indicatorType === 'MACD') {
                const fastPeriod = parseInt(document.getElementById('config-fast-period').value) || 12;
                const slowPeriod = parseInt(document.getElementById('config-slow-period').value) || 26;
                const signalPeriod = parseInt(document.getElementById('config-signal-period').value) || 9;
                
                selectedBlock.fastPeriod = fastPeriod;
                selectedBlock.slowPeriod = slowPeriod;
                selectedBlock.signalPeriod = signalPeriod;
                
                // Update block display
                const blockElement = document.getElementById(selectedBlock.id);
                blockElement.querySelector('.block-settings').textContent = `Fast: ${fastPeriod}, Slow: ${slowPeriod}, Signal: ${signalPeriod}`;
            }
        } else if (selectedBlock.type === 'entry' || selectedBlock.type === 'exit') {
            const indicator = document.getElementById('config-indicator').value;
            const operator = document.getElementById('config-operator').value;
            const value = document.getElementById('config-value').value;
            
            // Update or create condition
            if (indicator) {
                if (!selectedBlock.conditions) {
                    selectedBlock.conditions = [];
                }
                
                if (selectedBlock.conditions.length === 0) {
                    selectedBlock.conditions.push({ indicator, operator, value });
                } else {
                    selectedBlock.conditions[0] = { indicator, operator, value };
                }
                
                // Update block display
                const blockElement = document.getElementById(selectedBlock.id);
                blockElement.querySelector('.block-settings').textContent = `${indicator} ${operator} ${value}`;
            }
        }
        
        blockConfigModal.hide();
    }
    
    // Remove a block from the canvas
    function removeBlock(blockId) {
        const blockElement = document.getElementById(blockId);
        if (blockElement) {
            blockElement.remove();
        }
        
        blocks = blocks.filter(block => block.id !== blockId);
        
        // Show placeholder if no blocks left
        if (blocks.length === 0) {
            const placeholder = strategyCanvas.querySelector('.canvas-placeholder');
            if (placeholder) {
                placeholder.style.display = 'block';
            }
        }
    }
    
    // Run backtest with current strategy
    function runBacktest() {
        if (blocks.length === 0) {
            alert('Please add at least one block to create a strategy.');
            return;
        }
        
        // Create strategy configuration
        const strategy = buildStrategyConfig();
        
        // Show loading state
        performanceMetrics.innerHTML = '<p class="text-center"><div class="spinner-border text-primary" role="status"></div><br>Running backtest...</p>';
        
        // Send to backend for processing
        fetch('/api/backtest', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                blocks: strategy,
                symbol: symbolSelect.value,
                startDate: startDateInput.value,
                endDate: endDateInput.value,
                capital: initialCapitalInput.value
            })
        })
        .then(response => response.json())
        .then(results => {
            displayBacktestResults(results);
        })
        .catch(error => {
            console.error('Error running backtest:', error);
            performanceMetrics.innerHTML = '<p class="text-danger">Error running backtest. Please try again.</p>';
        });
    }
    
    // Build strategy configuration from blocks
    function buildStrategyConfig() {
        // Temporary structure for storing indicators
        const indicators = [];
        const entryRules = [];
        const exitRules = [];
        
        // Process indicator blocks
        blocks.filter(block => block.type === 'indicator').forEach(block => {
            if (block.indicatorType === 'SMA') {
                indicators.push({
                    type: 'SMA',
                    parameters: {
                        period: block.period
                    }
                });
            } else if (block.indicatorType === 'EMA') {
                indicators.push({
                    type: 'EMA',
                    parameters: {
                        period: block.period
                    }
                });
            } else if (block.indicatorType === 'RSI') {
                indicators.push({
                    type: 'RSI',
                    parameters: {
                        period: block.period
                    }
                });
            } else if (block.indicatorType === 'MACD') {
                indicators.push({
                    type: 'MACD',
                    parameters: {
                        fast_period: block.fastPeriod,
                        slow_period: block.slowPeriod,
                        signal_period: block.signalPeriod
                    }
                });
            }
        });
        
        // Process rule blocks
        blocks.filter(block => block.type === 'entry').forEach(block => {
            block.conditions.forEach(condition => {
                entryRules.push(condition);
            });
        });
        
        blocks.filter(block => block.type === 'exit').forEach(block => {
            block.conditions.forEach(condition => {
                exitRules.push(condition);
            });
        });
        
        return {
            indicators: indicators,
            entry_rules: entryRules,
            exit_rules: exitRules
        };
    }
    
    // Display backtest results
    function displayBacktestResults(results) {
        try {
            // Generate HTML for performance metrics
            let metricsHtml = '';
            
            if (results.error) {
                metricsHtml = `<p class="text-danger">${results.error}</p>`;
            } else {
                metricsHtml = `
                    <div class="metric-row">
                        <span class="metric-label">Initial Capital</span>
                        <span class="metric-value">$${formatNumber(results.initial_capital)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Final Equity</span>
                        <span class="metric-value">$${formatNumber(results.final_equity)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Total Return</span>
                        <span class="metric-value ${results.total_return >= 0 ? 'positive' : 'negative'}">
                            ${formatNumber(results.total_return)}%
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Sharpe Ratio</span>
                        <span class="metric-value">${formatNumber(results.sharpe_ratio)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Max Drawdown</span>
                        <span class="metric-value negative">${formatNumber(results.max_drawdown)}%</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Total Trades</span>
                        <span class="metric-value">${results.total_trades}</span>
                    </div>
                `;
            }
            
            performanceMetrics.innerHTML = metricsHtml;
            
            // Display trades with error handling
            if (results.trades && Array.isArray(results.trades) && results.trades.length > 0) {
                let tradesHtml = '';
                
                results.trades.forEach(trade => {
                    if (!trade.date || !trade.type || !trade.price || !trade.shares) {
                        console.warn("Incomplete trade data:", trade);
                        return;
                    }
                    
                    tradesHtml += `
                        <tr>
                            <td>${trade.date}</td>
                            <td>${trade.type}</td>
                            <td>$${formatNumber(trade.price)}</td>
                            <td>${trade.shares}</td>
                            <td>$${formatNumber(trade.value || trade.price * trade.shares)}</td>
                        </tr>
                    `;
                });
                
                if (tradesHtml) {
                    tradesTableBody.innerHTML = tradesHtml;
                } else {
                    tradesTableBody.innerHTML = '<tr><td colspan="5" class="text-center">No valid trades generated</td></tr>';
                }
            } else {
                tradesTableBody.innerHTML = '<tr><td colspan="5" class="text-center">No trades generated</td></tr>';
            }
            
            // Update equity curve chart
            updateEquityCurveChart(results.equity_curve);
        } catch (error) {
            console.error("Error displaying backtest results:", error);
            performanceMetrics.innerHTML = `<p class="text-danger">Error displaying results: ${error.message}</p>`;
            tradesTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error displaying trades</td></tr>';
        }
    }
    
    // Update equity curve chart
    function updateEquityCurveChart(equityCurve) {
        if (!equityCurve || equityCurve.length === 0) {
            console.error("No equity curve data available");
            return;
        }
        
        // Generate dates for x-axis (improved from just using numbers)
        const startDate = new Date(startDateInput.value);
        const dates = equityCurve.map((_, index) => {
            const date = new Date(startDate);
            date.setDate(date.getDate() + index);
            return date.toLocaleDateString();
        });
        
        // Destroy old chart if exists
        if (chartInstance) {
            chartInstance.destroy();
        }
        
        try {
            // Create new chart with better configuration
            const ctx = document.getElementById('equityCurveChart').getContext('2d');
            chartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Portfolio Value',
                        data: equityCurve,
                        borderColor: equityCurve[equityCurve.length-1] > equityCurve[0] ? '#28a745' : '#dc3545',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Equity ($)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Date'
                            },
                            ticks: {
                                maxTicksLimit: 10
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `Equity: $${context.raw.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                                }
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error("Error rendering chart:", error);
        }
    }
    
    // Start paper trading
    function startPaperTrading() {
        if (blocks.length === 0) {
            alert('Please add at least one block to create a strategy.');
            return;
        }
        
        // Fill trade modal with current symbol
        document.getElementById('tradeSymbol').value = symbolSelect.value;
        
        // Show paper trade modal
        const modal = new bootstrap.Modal(document.getElementById('paperTradeModal'));
        modal.show();
        
        // Handle trade submission
        document.getElementById('submitTradeBtn').onclick = function() {
            const symbol = document.getElementById('tradeSymbol').value;
            const quantity = parseInt(document.getElementById('tradeQuantity').value);
            const side = document.getElementById('tradeSide').value;
            const orderType = document.getElementById('tradeType').value;
            const notes = document.getElementById('tradeNotes').value;
            
            // For limit orders, get price
            let price = null;
            if (orderType === 'limit') {
                price = parseFloat(document.getElementById('limitPrice').value);
                if (isNaN(price) || price <= 0) {
                    alert('Please enter a valid limit price');
                    return;
                }
            }
            
            // Submit paper trade
            fetch('/api/paper-trade', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    symbol: symbol,
                    quantity: quantity,
                    side: side,
                    orderType: orderType,
                    price: price,
                    notes: notes
                })
            })
            .then(response => response.json())
            .then(result => {
                if (result.error) {
                    alert(`Error: ${result.error}`);
                } else {
                    alert('Trade executed successfully!');
                    modal.hide();
                }
            })
            .catch(error => {
                console.error('Error submitting trade:', error);
                alert('Error submitting trade. Please try again.');
            });
        };
        
        // Toggle limit price field based on order type
        document.getElementById('tradeType').addEventListener('change', function() {
            const limitPriceGroup = document.getElementById('limitPriceGroup');
            if (this.value === 'limit') {
                limitPriceGroup.classList.remove('d-none');
            } else {
                limitPriceGroup.classList.add('d-none');
            }
        });
    }
    
    // Save current strategy to server
    function saveStrategy() {
        if (blocks.length === 0) {
            alert('Please add at least one block to create a strategy.');
            return;
        }
        
        const strategyName = prompt('Enter a name for this strategy:');
        if (!strategyName) return;
        
        const strategy = {
            name: strategyName,
            blocks: blocks,
            symbol: symbolSelect.value,
            date: new Date().toISOString()
        };
        
        fetch('/api/save-strategy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(strategy)
        })
        .then(response => response.json())
        .then(result => {
            if (result.error) {
                alert(`Error: ${result.error}`);
            } else {
                alert(`Strategy "${strategyName}" saved successfully!`);
            }
        })
        .catch(error => {
            console.error('Error saving strategy:', error);
            alert('Error saving strategy. Please try again.');
        });
    }
    
    // Load a strategy from server
    function loadStrategy() {
        fetch('/api/list-strategies')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                
                const strategies = data.strategies;
                
                if (!strategies || strategies.length === 0) {
                    alert('No saved strategies found.');
                    return;
                }
                
                const loadStrategyModal = document.getElementById('loadStrategyModal');
                const strategyList = document.getElementById('strategyList');
                
                // Clear previous list
                strategyList.innerHTML = '';
                
                // Add strategy items
                strategies.forEach(strategy => {
                    const item = document.createElement('a');
                    item.href = '#';
                    item.className = 'list-group-item list-group-item-action';
                    item.textContent = strategy;
                    item.onclick = function(e) {
                        e.preventDefault();
                        loadStrategyByName(strategy);
                        bootstrap.Modal.getInstance(loadStrategyModal).hide();
                    };
                    strategyList.appendChild(item);
                });
                
                // Show modal
                const modal = new bootstrap.Modal(loadStrategyModal);
                modal.show();
            })
            .catch(error => {
                console.error('Error listing strategies:', error);
                alert('Error loading strategies. Please try again.');
            });
    }
    
    // Load a specific strategy by name
    function loadStrategyByName(strategyName) {
        fetch(`/api/load-strategy?name=${encodeURIComponent(strategyName)}`)
            .then(response => response.json())
            .then(strategyData => {
                if (strategyData.error) {
                    alert(`Error: ${strategyData.error}`);
                    return;
                }
                
                // Clear current strategy
                clearStrategy();
                
                // Restore blocks
                if (strategyData.blocks && Array.isArray(strategyData.blocks)) {
                    strategyData.blocks.forEach(block => {
                        createBlock(block.type, block.indicatorType, block.x, block.y);
                        
                        // Restore block properties
                        const newBlock = blocks[blocks.length - 1];
                        Object.assign(newBlock, block);
                        
                        // Update block display
                        const blockElement = document.getElementById(newBlock.id);
                        if (blockElement) {
                            let settingsText = '';
                            
                            if (block.type === 'indicator') {
                                if (block.indicatorType === 'SMA' || block.indicatorType === 'EMA' || block.indicatorType === 'RSI') {
                                    settingsText = `Period: ${block.period}`;
                                } else if (block.indicatorType === 'MACD') {
                                    settingsText = `Fast: ${block.fastPeriod}, Slow: ${block.slowPeriod}, Signal: ${block.signalPeriod}`;
                                }
                            } else if (block.type === 'entry' || block.type === 'exit') {
                                if (block.conditions && block.conditions.length > 0) {
                                    const condition = block.conditions[0];
                                    settingsText = `${condition.indicator} ${condition.operator} ${condition.value}`;
                                } else {
                                    settingsText = 'No conditions set';
                                }
                            }
                            
                            blockElement.querySelector('.block-settings').textContent = settingsText;
                        }
                    });
                }
                
                // Update symbol if it was saved
                if (strategyData.symbol) {
                    // Find the option
                    const option = Array.from(symbolSelect.options).find(opt => opt.value === strategyData.symbol);
                    if (option) {
                        symbolSelect.value = strategyData.symbol;
                        updateSymbol();
                    }
                }
                
                alert(`Strategy "${strategyName}" loaded successfully.`);
            })
            .catch(error => {
                console.error('Error loading strategy:', error);
                alert('Error loading strategy. Please try again.');
            });
    }
    
    // Clear current strategy
    function clearStrategy() {
        // Remove all blocks
        blocks.forEach(block => {
            const blockElement = document.getElementById(block.id);
            if (blockElement) {
                blockElement.remove();
            }
        });
        
        // Reset blocks array
        blocks = [];
        
        // Show placeholder
        const placeholder = strategyCanvas.querySelector('.canvas-placeholder');
        if (placeholder) {
            placeholder.style.display = 'block';
        }
        
        // Clear results
        performanceMetrics.innerHTML = '<p class="text-muted text-center"><i class="bi bi-arrow-clockwise"></i> Run a backtest to see metrics</p>';
        tradesTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No trades to display</td></tr>';
        
        // Clear chart
        if (chartInstance) {
            chartInstance.destroy();
            chartInstance = null;
        }
    }
    
    // Utility: Format date as YYYY-MM-DD
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    // Utility: Format date and time
    function formatDateTime(date) {
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
