#!/usr/bin/env python3
"""
Stock Data Connection Tester
Tests connection to multiple data sources and fetches data for a single ticker.

Data Sources (in order of preference):
1. yfinance download() method
2. Stooq via pandas_datareader
3. FRED (for indices only)

Usage:
    python test_stock_connection.py [TICKER]
    
Examples:
    python test_stock_connection.py AAPL
    python test_stock_connection.py MSFT
    python test_stock_connection.py        # defaults to AAPL
    
Install dependencies:
    pip install yfinance pandas pandas-datareader --break-system-packages
"""

import sys
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def check_dependencies():
    """Check if required packages are installed."""
    packages = {}
    
    try:
        import pandas as pd
        packages['pandas'] = True
        print("✓ pandas installed")
    except ImportError:
        packages['pandas'] = False
        print("✗ pandas NOT installed")
    
    try:
        import yfinance as yf
        packages['yfinance'] = True
        print("✓ yfinance installed")
    except ImportError:
        packages['yfinance'] = False
        print("○ yfinance not installed (optional)")
    
    try:
        import pandas_datareader as pdr
        packages['pandas_datareader'] = True
        print("✓ pandas_datareader installed")
    except ImportError:
        packages['pandas_datareader'] = False
        print("○ pandas_datareader not installed (optional)")
    
    if not packages.get('pandas'):
        print(f"\n⚠️  pandas is required")
        print(f"Install with: pip install pandas --break-system-packages")
        return None
    
    if not packages.get('yfinance') and not packages.get('pandas_datareader'):
        print(f"\n⚠️  Need at least one data source package")
        print(f"Install with: pip install yfinance pandas-datareader --break-system-packages")
        return None
    
    return packages


def fetch_with_yfinance_download(ticker: str, start_date: str, end_date: str):
    """
    Fetch data using yfinance.download() - most reliable method.
    """
    import yfinance as yf
    
    print(f"\n  Trying yfinance.download()...")
    
    try:
        # Use download() instead of Ticker().history() - more reliable
        df = yf.download(
            ticker, 
            start=start_date, 
            end=end_date, 
            progress=False,
            show_errors=False
        )
        
        if df is not None and not df.empty:
            print(f"  ✓ Success: {len(df)} rows retrieved")
            return df, "yfinance.download()"
        else:
            print(f"  ✗ No data returned")
            return None, None
            
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return None, None


def fetch_with_yfinance_ticker(ticker: str, start_date: str, end_date: str):
    """
    Fetch data using yfinance Ticker object - backup method.
    """
    import yfinance as yf
    
    print(f"\n  Trying yfinance.Ticker()...")
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, raise_errors=False)
        
        if df is not None and not df.empty:
            print(f"  ✓ Success: {len(df)} rows retrieved")
            return df, "yfinance.Ticker()"
        else:
            print(f"  ✗ No data returned")
            return None, None
            
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return None, None


def fetch_with_stooq(ticker: str, start_date: str, end_date: str):
    """
    Fetch data from Stooq via pandas_datareader.
    Stooq is a free Polish financial data provider with US stock data.
    """
    import pandas_datareader.data as web
    
    print(f"\n  Trying Stooq (pandas_datareader)...")
    
    try:
        # Stooq uses .US suffix for US stocks
        stooq_ticker = f"{ticker}.US"
        
        df = web.DataReader(
            stooq_ticker, 
            'stooq', 
            start=start_date, 
            end=end_date
        )
        
        if df is not None and not df.empty:
            # Stooq returns data in reverse chronological order
            df = df.sort_index()
            print(f"  ✓ Success: {len(df)} rows retrieved")
            return df, "Stooq"
        else:
            print(f"  ✗ No data returned")
            return None, None
            
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return None, None


def fetch_with_tiingo(ticker: str, start_date: str, end_date: str, api_key: str = None):
    """
    Fetch data from Tiingo (requires free API key).
    """
    if not api_key:
        print(f"\n  ○ Skipping Tiingo (no API key)")
        return None, None
        
    import pandas_datareader.data as web
    
    print(f"\n  Trying Tiingo...")
    
    try:
        df = web.DataReader(
            ticker,
            'tiingo',
            start=start_date,
            end=end_date,
            api_key=api_key
        )
        
        if df is not None and not df.empty:
            print(f"  ✓ Success: {len(df)} rows retrieved")
            return df, "Tiingo"
        else:
            print(f"  ✗ No data returned")
            return None, None
            
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return None, None


def fetch_stock_data(ticker: str, packages: dict):
    """
    Try multiple data sources to fetch stock data.
    """
    import pandas as pd
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"\nDate range: {start_str} to {end_str}")
    print(f"\nTrying data sources...")
    
    df = None
    source = None
    
    # Try yfinance download first (most reliable)
    if packages.get('yfinance') and df is None:
        df, source = fetch_with_yfinance_download(ticker, start_str, end_str)
    
    # Try yfinance Ticker method
    if packages.get('yfinance') and df is None:
        df, source = fetch_with_yfinance_ticker(ticker, start_str, end_str)
    
    # Try Stooq
    if packages.get('pandas_datareader') and df is None:
        df, source = fetch_with_stooq(ticker, start_str, end_str)
    
    return df, source


def display_results(ticker: str, df, source: str):
    """Display the fetched data and statistics."""
    import pandas as pd
    
    print(f"\n{'=' * 60}")
    print(f"  RESULTS FOR: {ticker}")
    print(f"  Data Source: {source}")
    print(f"{'=' * 60}")
    
    # Normalize column names (different sources use different cases)
    df.columns = [col.title() if isinstance(col, str) else col for col in df.columns]
    
    # Find close price column
    close_col = None
    for col in ['Close', 'Adj Close', 'Adjclose']:
        if col in df.columns:
            close_col = col
            break
    
    if close_col is None:
        print("  ⚠ Could not find Close price column")
        print(f"  Available columns: {list(df.columns)}")
        return
    
    # Display last 5 days
    print(f"\nLast 5 trading days:")
    print("-" * 60)
    
    display_df = df.tail(5).copy()
    
    # Format for display
    cols_to_show = []
    for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']:
        if col in display_df.columns:
            cols_to_show.append(col)
    
    if cols_to_show:
        print(display_df[cols_to_show].to_string())
    else:
        print(display_df.to_string())
    
    print("-" * 60)
    
    # Statistics
    close_prices = df[close_col].dropna()
    
    if len(close_prices) > 0:
        print(f"\nStatistics:")
        print(f"  Data Points:   {len(close_prices)}")
        print(f"  Latest Close:  ${close_prices.iloc[-1]:.2f}")
        print(f"  30-Day High:   ${close_prices.max():.2f}")
        print(f"  30-Day Low:    ${close_prices.min():.2f}")
        print(f"  30-Day Mean:   ${close_prices.mean():.2f}")
        print(f"  Std Deviation: ${close_prices.std():.2f}")
        
        if close_prices.std() > 0:
            z_score = (close_prices.iloc[-1] - close_prices.mean()) / close_prices.std()
            print(f"  Z-Score:       {z_score:.2f}")
    
    print(f"\n{'=' * 60}")
    print(f"  ✓ CONNECTION TEST PASSED")
    print(f"{'=' * 60}")


def test_ticker(ticker: str, packages: dict):
    """
    Test fetching data for a single ticker using available sources.
    """
    print(f"\n{'=' * 60}")
    print(f"  TESTING TICKER: {ticker}")
    print(f"{'=' * 60}")
    
    df, source = fetch_stock_data(ticker, packages)
    
    if df is not None and source:
        display_results(ticker, df, source)
        return True
    else:
        print(f"\n{'=' * 60}")
        print(f"  ✗ ALL DATA SOURCES FAILED FOR: {ticker}")
        print(f"{'=' * 60}")
        print(f"\nPossible reasons:")
        print(f"  - Invalid ticker symbol")
        print(f"  - Stock may be delisted")
        print(f"  - Network connectivity issue")
        print(f"  - Data source temporarily unavailable")
        print(f"\nTry:")
        print(f"  - Verify the ticker symbol is correct")
        print(f"  - Test with a known good ticker: AAPL, MSFT, GOOGL")
        print(f"  - Check your internet connection")
        return False


def test_multiple_tickers(tickers: list, packages: dict):
    """Test multiple tickers and show results summary."""
    results = {}
    
    print(f"\n{'=' * 60}")
    print(f"  BATCH TEST: {len(tickers)} tickers")
    print(f"{'=' * 60}")
    
    for ticker in tickers:
        print(f"\nTesting {ticker}...", end=" ", flush=True)
        
        df, source = fetch_stock_data(ticker, packages)
        
        if df is not None and not df.empty:
            print(f"✓ OK ({len(df)} rows via {source})")
            results[ticker] = f"OK ({source})"
        else:
            print(f"✗ Failed")
            results[ticker] = "Failed"
    
    # Summary
    print(f"\n{'=' * 60}")
    print("  BATCH TEST SUMMARY")
    print(f"{'=' * 60}")
    
    ok_count = sum(1 for v in results.values() if v.startswith("OK"))
    print(f"  Successful: {ok_count}/{len(tickers)}")
    
    failed = [k for k, v in results.items() if not v.startswith("OK")]
    if failed:
        print(f"  Failed tickers: {', '.join(failed)}")
    
    return results


def main():
    print("=" * 60)
    print("     STOCK DATA CONNECTION TESTER")
    print("     (Multi-Source)")
    print("=" * 60)
    
    # Check dependencies first
    print("\nChecking dependencies...")
    packages = check_dependencies()
    
    if packages is None:
        sys.exit(1)
    
    # Get ticker from command line or use default
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        
        # Check if multiple tickers provided
        if ',' in ticker:
            tickers = [t.strip() for t in ticker.split(',')]
            test_multiple_tickers(tickers, packages)
        else:
            test_ticker(ticker, packages)
    else:
        # Interactive mode
        print("\nNo ticker specified. Enter a ticker to test.")
        print("Examples: AAPL, MSFT, GOOGL, AMZN")
        print("For multiple tickers, separate with commas: AAPL,MSFT,GOOGL")
        print("Type 'quit' to exit.\n")
        
        while True:
            user_input = input("Enter ticker(s): ").strip().upper()
            
            if user_input.lower() == 'quit' or user_input == '':
                print("Exiting...")
                break
            
            if ',' in user_input:
                tickers = [t.strip() for t in user_input.split(',')]
                test_multiple_tickers(tickers, packages)
            else:
                test_ticker(user_input, packages)
            
            print()


if __name__ == "__main__":
    main()
