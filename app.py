#!/usr/bin/env python3
"""
Mean Reversion Web Application
Flask server that connects the Python analysis backend to an HTML frontend.

SETUP:
    pip install flask yfinance pandas numpy scipy --break-system-packages

USAGE:
    python app.py
    
    Then open http://localhost:5000 in your browser
"""

import json
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
from pathlib import Path

# Import our analysis modules
from stock_data_manager import StockDataManager
from mean_reversion_integrated import MeanReversionAnalyzer, StockAnalysis

app = Flask(__name__)

# Initialize analyzer
analyzer = MeanReversionAnalyzer(data_dir="./stock_data")

# HTML Template with embedded JavaScript
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mean Reversion Analysis - S&P 500</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e5e7eb;
        }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 24px 16px; }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
        }
        
        .glow-green { box-shadow: 0 0 20px rgba(34, 197, 94, 0.3); }
        
        /* Header */
        .header {
            padding: 24px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }
        
        .header h1 { font-size: 28px; font-weight: 700; color: #fff; margin-bottom: 8px; }
        .header-subtitle { color: #9ca3af; }
        
        /* Controls */
        .controls {
            padding: 20px;
            margin-bottom: 24px;
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            align-items: flex-end;
        }
        
        .control-group { display: flex; flex-direction: column; gap: 6px; }
        .control-group label { font-size: 12px; color: #9ca3af; text-transform: uppercase; }
        
        .control-group input, .control-group select {
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.1);
            color: #fff;
            font-size: 14px;
            min-width: 120px;
        }
        
        .control-group input:focus, .control-group select:focus {
            outline: none;
            border-color: #3b82f6;
        }
        
        .btn {
            padding: 10px 24px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        .btn-primary { background: #3b82f6; color: #fff; }
        .btn-primary:hover { background: #2563eb; }
        .btn-primary:disabled { background: #4b5563; cursor: not-allowed; }
        
        .btn-secondary { background: #374151; color: #9ca3af; }
        .btn-secondary:hover { background: #4b5563; }
        
        /* Loading */
        .loading {
            display: none;
            align-items: center;
            gap: 10px;
            color: #9ca3af;
        }
        
        .loading.active { display: flex; }
        
        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid #374151;
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px; }
        @media (min-width: 768px) { .stats-grid { grid-template-columns: repeat(4, 1fr); } }
        
        .stat-card { padding: 16px; }
        .stat-label { color: #9ca3af; font-size: 14px; margin-bottom: 4px; }
        .stat-value { font-size: 28px; font-weight: 700; color: #fff; }
        .stat-value.green { color: #22c55e; }
        .stat-value.blue { color: #3b82f6; }
        
        /* Main Layout */
        .main-layout { display: grid; gap: 24px; }
        @media (min-width: 1024px) { .main-layout { grid-template-columns: 1fr 2fr; } }
        
        /* Stock List */
        .stock-list {
            display: flex; flex-direction: column; gap: 12px;
            max-height: 700px; overflow-y: auto; padding-right: 8px;
        }
        
        .stock-card { padding: 16px; cursor: pointer; transition: all 0.3s; }
        .stock-card:hover { transform: scale(1.02); }
        .stock-card.selected { border-color: #22c55e; box-shadow: 0 0 20px rgba(34, 197, 94, 0.3); }
        
        .stock-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .stock-ticker { font-size: 20px; font-weight: 700; color: #fff; }
        
        .direction-badge {
            font-size: 12px; padding: 4px 10px; border-radius: 9999px;
            background: rgba(34, 197, 94, 0.2); color: #22c55e;
        }
        
        .stock-price { text-align: right; }
        .stock-price-value { font-size: 22px; font-weight: 700; color: #fff; }
        .stock-gap { font-size: 13px; color: #22c55e; }
        
        .stock-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center; }
        .metric-label { color: #6b7280; font-size: 11px; }
        .metric-value { font-weight: 700; font-size: 14px; color: #22c55e; }
        .metric-value.blue { color: #3b82f6; }
        
        /* Detail Panel */
        .detail-panel { padding: 24px; }
        .detail-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
        .detail-title { font-size: 24px; font-weight: 700; color: #fff; }
        .detail-subtitle { color: #9ca3af; }
        
        .signal-badge {
            padding: 8px 16px; border-radius: 8px; font-size: 16px; font-weight: 700;
            background: rgba(34, 197, 94, 0.2); color: #22c55e;
        }
        
        .chart-container { height: 320px; margin-bottom: 24px; position: relative; }
        
        .metrics-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        @media (min-width: 768px) { .metrics-grid { grid-template-columns: repeat(4, 1fr); } }
        
        .metric-box { background: rgba(31, 41, 55, 0.5); border-radius: 8px; padding: 12px; }
        .metric-box-label { color: #6b7280; font-size: 12px; margin-bottom: 4px; }
        .metric-box-value { font-size: 18px; font-weight: 700; color: #fff; }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #9ca3af;
        }
        
        .empty-state h3 { font-size: 18px; margin-bottom: 10px; color: #fff; }
        
        /* Footer */
        .footer { margin-top: 32px; text-align: center; color: #6b7280; font-size: 14px; }
        
        /* Scrollbar */
        .stock-list::-webkit-scrollbar { width: 6px; }
        .stock-list::-webkit-scrollbar-track { background: rgba(55, 65, 81, 0.3); border-radius: 3px; }
        .stock-list::-webkit-scrollbar-thumb { background: rgba(107, 114, 128, 0.5); border-radius: 3px; }

        /* Status messages */
        .status-message {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            display: none;
        }
        .status-message.error { display: block; background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .status-message.success { display: block; background: rgba(34, 197, 94, 0.2); color: #22c55e; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="glass-card header">
            <div>
                <h1>Mean Reversion Analysis</h1>
                <p class="header-subtitle">S&P 500 - LONG (Oversold) Signals</p>
            </div>
            <div style="text-align: right;">
                <p id="timestamp" style="color: #6b7280; font-size: 12px;"></p>
            </div>
        </header>
        
        <!-- Controls -->
        <div class="glass-card controls">
            <div class="control-group">
                <label>Min Z-Score</label>
                <input type="number" id="min-zscore" value="1.5" step="0.1" min="0.5" max="4">
            </div>
            <div class="control-group">
                <label>Top Results</label>
                <input type="number" id="top-n" value="10" min="5" max="50">
            </div>
            <div class="control-group">
                <label>&nbsp;</label>
                <button class="btn btn-primary" id="run-analysis" onclick="runAnalysis()">
                    Run Analysis
                </button>
            </div>
            <div class="control-group">
                <label>&nbsp;</label>
                <button class="btn btn-secondary" onclick="updateData()">
                    Update Stock Data
                </button>
            </div>
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <span id="loading-text">Running analysis...</span>
            </div>
        </div>
        
        <!-- Status Message -->
        <div class="status-message" id="status-message"></div>
        
        <!-- Stats Summary -->
        <div class="stats-grid" id="stats-grid">
            <div class="glass-card stat-card">
                <p class="stat-label">Total Candidates</p>
                <p class="stat-value">-</p>
            </div>
            <div class="glass-card stat-card glow-green">
                <p class="stat-label">Signal Type</p>
                <p class="stat-value green">LONG</p>
            </div>
            <div class="glass-card stat-card">
                <p class="stat-label">Avg Z-Score</p>
                <p class="stat-value green">-</p>
            </div>
            <div class="glass-card stat-card">
                <p class="stat-label">Avg Probability</p>
                <p class="stat-value blue">-</p>
            </div>
        </div>
        
        <!-- Main Layout -->
        <div class="main-layout">
            <!-- Left Panel - Stock List -->
            <div>
                <div class="stock-list" id="stock-list">
                    <div class="empty-state">
                        <h3>No Analysis Results</h3>
                        <p>Click "Run Analysis" to find oversold stocks</p>
                    </div>
                </div>
            </div>
            
            <!-- Right Panel - Detail Chart -->
            <div>
                <div class="glass-card detail-panel" id="detail-panel">
                    <div class="empty-state">
                        <h3>Select a Stock</h3>
                        <p>Run analysis and select a stock to view details</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <footer class="footer">
            <p>Mean Reversion Analysis Tool | Data is for informational purposes only</p>
            <p>Always conduct your own due diligence before trading</p>
        </footer>
    </div>
    
    <script>
        let stockData = [];
        let selectedTicker = null;
        let detailChart = null;
        
        // Update timestamp
        document.getElementById('timestamp').textContent = 'Page loaded: ' + new Date().toLocaleString();
        
        function showStatus(message, type) {
            const el = document.getElementById('status-message');
            el.textContent = message;
            el.className = 'status-message ' + type;
            if (type === 'success') {
                setTimeout(() => { el.className = 'status-message'; }, 5000);
            }
        }
        
        function setLoading(loading, text) {
            const el = document.getElementById('loading');
            const textEl = document.getElementById('loading-text');
            const btn = document.getElementById('run-analysis');
            
            el.className = loading ? 'loading active' : 'loading';
            textEl.textContent = text || 'Running analysis...';
            btn.disabled = loading;
        }
        
        async function runAnalysis() {
            const minZScore = parseFloat(document.getElementById('min-zscore').value) || 1.5;
            const topN = parseInt(document.getElementById('top-n').value) || 10;
            
            setLoading(true, 'Running analysis...');
            document.getElementById('status-message').className = 'status-message';
            
            try {
                const response = await fetch(`/api/analyze?min_z_score=${minZScore}&top_n=${topN}`);
                const data = await response.json();
                
                if (data.error) {
                    showStatus(data.error, 'error');
                    setLoading(false);
                    return;
                }
                
                stockData = data.results;
                selectedTicker = stockData.length > 0 ? stockData[0].ticker : null;
                
                renderStats();
                renderStockList();
                renderDetailPanel();
                
                showStatus(`Analysis complete: ${stockData.length} candidates found`, 'success');
                document.getElementById('timestamp').textContent = 'Last analysis: ' + new Date().toLocaleString();
                
            } catch (err) {
                showStatus('Error running analysis: ' + err.message, 'error');
            }
            
            setLoading(false);
        }
        
        async function updateData() {
            setLoading(true, 'Updating stock data (this may take several minutes)...');
            document.getElementById('status-message').className = 'status-message';
            
            try {
                const response = await fetch('/api/update-data', { method: 'POST' });
                const data = await response.json();
                
                if (data.error) {
                    showStatus(data.error, 'error');
                } else {
                    showStatus(`Data updated: ${data.successful} stocks refreshed, ${data.failed} failed`, 'success');
                }
            } catch (err) {
                showStatus('Error updating data: ' + err.message, 'error');
            }
            
            setLoading(false);
        }
        
        function renderStats() {
            if (stockData.length === 0) return;
            
            const avgProb = (stockData.reduce((sum, s) => sum + s.reversion_probability, 0) / stockData.length * 100).toFixed(1);
            const avgZScore = (stockData.reduce((sum, s) => sum + s.z_score, 0) / stockData.length).toFixed(2);
            
            document.getElementById('stats-grid').innerHTML = `
                <div class="glass-card stat-card">
                    <p class="stat-label">Total Candidates</p>
                    <p class="stat-value">${stockData.length}</p>
                </div>
                <div class="glass-card stat-card glow-green">
                    <p class="stat-label">Signal Type</p>
                    <p class="stat-value green">LONG</p>
                </div>
                <div class="glass-card stat-card">
                    <p class="stat-label">Avg Z-Score</p>
                    <p class="stat-value green">${avgZScore}</p>
                </div>
                <div class="glass-card stat-card">
                    <p class="stat-label">Avg Probability</p>
                    <p class="stat-value blue">${avgProb}%</p>
                </div>
            `;
        }
        
        function renderStockList() {
            const container = document.getElementById('stock-list');
            
            if (stockData.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <h3>No Candidates Found</h3>
                        <p>Try lowering the minimum Z-Score threshold</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = stockData.map(stock => {
                const isSelected = stock.ticker === selectedTicker;
                return `
                    <div class="glass-card stock-card ${isSelected ? 'selected' : ''}" onclick="selectStock('${stock.ticker}')">
                        <div class="stock-card-header">
                            <div>
                                <div class="stock-ticker">${stock.ticker}</div>
                                <span class="direction-badge">^ LONG</span>
                            </div>
                            <div class="stock-price">
                                <div class="stock-price-value">$${stock.current_price.toFixed(2)}</div>
                                <div class="stock-gap">${stock.gap_percentage.toFixed(1)}% below mean</div>
                            </div>
                        </div>
                        <div class="stock-metrics">
                            <div>
                                <p class="metric-label">Z-Score</p>
                                <p class="metric-value">${stock.z_score.toFixed(2)}</p>
                            </div>
                            <div>
                                <p class="metric-label">RSI</p>
                                <p class="metric-value">${stock.rsi.toFixed(1)}</p>
                            </div>
                            <div>
                                <p class="metric-label">Probability</p>
                                <p class="metric-value blue">${(stock.reversion_probability * 100).toFixed(0)}%</p>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function selectStock(ticker) {
            selectedTicker = ticker;
            renderStockList();
            renderDetailPanel();
        }
        
        function renderDetailPanel() {
            const panel = document.getElementById('detail-panel');
            const stock = stockData.find(s => s.ticker === selectedTicker);
            
            if (!stock) {
                panel.innerHTML = `
                    <div class="empty-state">
                        <h3>Select a Stock</h3>
                        <p>Click on a stock card to view details</p>
                    </div>
                `;
                return;
            }
            
            panel.innerHTML = `
                <div class="detail-header">
                    <div>
                        <h2 class="detail-title">${stock.ticker}</h2>
                        <p class="detail-subtitle">100-Day Price History</p>
                    </div>
                    <div class="signal-badge">^ LONG SIGNAL</div>
                </div>
                <div class="chart-container">
                    <canvas id="detail-chart"></canvas>
                </div>
                <div class="metrics-grid">
                    <div class="metric-box">
                        <p class="metric-box-label">Current Price</p>
                        <p class="metric-box-value">$${stock.current_price.toFixed(2)}</p>
                    </div>
                    <div class="metric-box">
                        <p class="metric-box-label">100-Day Mean</p>
                        <p class="metric-box-value">$${stock.mean_price.toFixed(2)}</p>
                    </div>
                    <div class="metric-box">
                        <p class="metric-box-label">Std Deviation</p>
                        <p class="metric-box-value">$${stock.std_dev.toFixed(2)}</p>
                    </div>
                    <div class="metric-box">
                        <p class="metric-box-label">Gap from Mean</p>
                        <p class="metric-box-value" style="color: #22c55e;">${stock.gap_percentage.toFixed(1)}%</p>
                    </div>
                    <div class="metric-box">
                        <p class="metric-box-label">Z-Score</p>
                        <p class="metric-box-value" style="color: #22c55e;">${stock.z_score.toFixed(2)}</p>
                    </div>
                    <div class="metric-box">
                        <p class="metric-box-label">RSI (14)</p>
                        <p class="metric-box-value" style="color: #22c55e;">${stock.rsi.toFixed(1)}</p>
                    </div>
                    <div class="metric-box">
                        <p class="metric-box-label">Half-Life</p>
                        <p class="metric-box-value">${stock.half_life.toFixed(1)} days</p>
                    </div>
                    <div class="metric-box">
                        <p class="metric-box-label">Reversion Prob</p>
                        <p class="metric-box-value" style="color: #3b82f6;">${(stock.reversion_probability * 100).toFixed(1)}%</p>
                    </div>
                </div>
            `;
            
            // Render chart if we have price history
            if (stock.prices && stock.prices.length > 0) {
                renderDetailChart(stock);
            }
        }
        
        function renderDetailChart(stock) {
            const canvas = document.getElementById('detail-chart');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            
            if (detailChart) {
                detailChart.destroy();
            }
            
            const prices = stock.prices;
            const dates = stock.dates;
            const mean = stock.mean_price;
            const std = stock.std_dev;
            
            const meanLine = Array(prices.length).fill(mean);
            const upper1 = Array(prices.length).fill(mean + std);
            const lower1 = Array(prices.length).fill(mean - std);
            const upper2 = Array(prices.length).fill(mean + 2 * std);
            const lower2 = Array(prices.length).fill(mean - 2 * std);
            
            detailChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates.map(d => {
                        const date = new Date(d);
                        return (date.getMonth() + 1) + '/' + date.getDate();
                    }),
                    datasets: [
                        {
                            label: 'Price',
                            data: prices,
                            borderColor: '#3b82f6',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.1,
                            pointRadius: 0
                        },
                        {
                            label: 'Mean',
                            data: meanLine,
                            borderColor: '#22c55e',
                            borderWidth: 2,
                            fill: false,
                            pointRadius: 0
                        },
                        {
                            label: '+/-1 Std',
                            data: upper1,
                            borderColor: '#f59e0b',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            fill: false,
                            pointRadius: 0
                        },
                        {
                            label: '-1 Std',
                            data: lower1,
                            borderColor: '#f59e0b',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            fill: false,
                            pointRadius: 0
                        },
                        {
                            label: '+/-2 Std',
                            data: upper2,
                            borderColor: '#ef4444',
                            borderWidth: 1,
                            borderDash: [3, 3],
                            fill: false,
                            pointRadius: 0
                        },
                        {
                            label: '-2 Std',
                            data: lower2,
                            borderColor: '#ef4444',
                            borderWidth: 1,
                            borderDash: [3, 3],
                            fill: false,
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#9ca3af',
                                usePointStyle: true,
                                filter: item => ['Price', 'Mean', '+/-1 Std', '+/-2 Std'].includes(item.text)
                            }
                        },
                        tooltip: {
                            backgroundColor: '#1f2937',
                            titleColor: '#9ca3af',
                            bodyColor: '#e5e7eb',
                            callbacks: {
                                label: ctx => ctx.dataset.label === 'Price' ? 'Price: $' + ctx.raw.toFixed(2) : null
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(55, 65, 81, 0.5)' },
                            ticks: { color: '#9ca3af', maxTicksLimit: 10 }
                        },
                        y: {
                            grid: { color: 'rgba(55, 65, 81, 0.5)' },
                            ticks: {
                                color: '#9ca3af',
                                callback: value => '$' + value.toFixed(0)
                            }
                        }
                    }
                }
            });
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the main dashboard page."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/analyze')
def analyze():
    """Run mean reversion analysis and return results as JSON."""
    try:
        min_z_score = float(request.args.get('min_z_score', 1.5))
        top_n = int(request.args.get('top_n', 10))
        
        # Check if we have data
        status = analyzer.data_manager.get_data_status()
        if status['total_tickers_stored'] == 0:
            return jsonify({
                'error': 'No stock data available. Click "Update Stock Data" first.',
                'results': []
            })
        
        # Run analysis
        results = analyzer.run_analysis(top_n=top_n, min_z_score=min_z_score)
        
        # Convert to JSON-serializable format
        json_results = []
        for r in results:
            json_results.append({
                'ticker': r.ticker,
                'current_price': r.current_price,
                'mean_price': r.mean_price,
                'std_dev': r.std_dev,
                'z_score': r.z_score,
                'rsi': r.rsi,
                'gap_from_mean': r.gap_from_mean,
                'gap_percentage': r.gap_percentage,
                'reversion_probability': r.reversion_probability,
                'expected_days': r.expected_days_to_revert,
                'half_life': r.half_life,
                'signal_strength': r.signal_strength,
                'direction': r.direction,
                'prices': r.prices.tolist(),
                'dates': [d.strftime('%Y-%m-%d') for d in r.dates]
            })
        
        return jsonify({
            'results': json_results,
            'count': len(json_results),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'results': []})


@app.route('/api/update-data', methods=['POST'])
def update_data():
    """Update stock data from Yahoo Finance."""
    try:
        summary = analyzer.data_manager.update_all_stocks(force_full=True)
        return jsonify({
            'successful': summary['successful'],
            'failed': summary['failed'],
            'rows_added': summary['rows_added'],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/status')
def status():
    """Get data status."""
    try:
        status = analyzer.data_manager.get_data_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    print("=" * 60)
    print("  MEAN REVERSION WEB APPLICATION")
    print("=" * 60)
    print("\nStarting Flask server...")
    print("Open http://localhost:5000 in your browser")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
