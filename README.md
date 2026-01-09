# Mean Reversion Analysis - S&P 500

A Python web application that analyzes S&P 500 stocks for mean reversion (oversold) opportunities.

## Quick Start (Windows)

1. **Download all files** to the same folder:
   - `launch_app.bat` (or `launch_app.ps1`)
   - `app.py`
   - `stock_data_manager.py`
   - `mean_reversion_integrated.py`

2. **Double-click `launch_app.bat`**
   - This will install dependencies automatically
   - Opens your browser to `http://localhost:5000`

3. **First time setup:**
   - Click "Update Stock Data" (takes 5-10 minutes to download S&P 500 data)
   - Then click "Run Analysis" to find oversold stocks

## Requirements

- **Python 3.8+** - Download from https://www.python.org/downloads/
  - IMPORTANT: Check "Add Python to PATH" during installation
- **Internet connection** for downloading stock data

## Files Included

| File | Description |
|------|-------------|
| `launch_app.bat` | Windows batch file - double-click to start |
| `launch_app.ps1` | PowerShell alternative launcher |
| `app.py` | Flask web server with HTML frontend |
| `stock_data_manager.py` | Downloads and manages S&P 500 price data |
| `mean_reversion_integrated.py` | Mean reversion analysis algorithms |

## Manual Installation

If the automatic launcher doesn't work:

```bash
# Install dependencies
pip install flask yfinance pandas numpy scipy

# Run the app
python app.py

# Open browser to http://localhost:5000
```

## How to Use

1. **Update Stock Data** - Downloads latest prices for all S&P 500 stocks
   - Only needed first time or to refresh data
   - Data is stored locally in `./stock_data/` folder

2. **Set Parameters:**
   - **Min Z-Score**: Lower = more candidates (default 1.5)
   - **Top Results**: Number of stocks to show (default 10)

3. **Run Analysis** - Finds oversold stocks based on:
   - Z-Score (standard deviations below 100-day mean)
   - RSI (Relative Strength Index < 35)
   - Half-Life (Ornstein-Uhlenbeck mean reversion speed)

4. **View Results:**
   - Click any stock card to see detailed chart
   - Green areas show price below mean (buying opportunity)

## Understanding the Signals

All signals are **LONG (Buy)** recommendations for oversold stocks:

| Metric | Good Value | Meaning |
|--------|------------|---------|
| Z-Score | < -2.0 | Price is 2+ std devs below mean |
| RSI | < 30 | Stock is oversold |
| Half-Life | < 15 days | Fast mean reversion expected |
| Probability | > 80% | High chance of reverting in 30 days |

## Troubleshooting

**"Python not found"**
- Install Python from python.org
- Make sure to check "Add Python to PATH"
- Restart your computer after installation

**"Module not found"**
- Run: `pip install flask yfinance pandas numpy scipy`

**"No stock data available"**
- Click "Update Stock Data" button first
- Wait for download to complete (5-10 minutes)

**Browser doesn't open**
- Manually go to http://localhost:5000

## Disclaimer

This tool is for informational and educational purposes only. It is not financial advice. Always conduct your own research before making investment decisions. Past performance does not guarantee future results.
