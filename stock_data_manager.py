#!/usr/bin/env python3
"""
Stock Data Manager - S&P 500
Fetches and maintains historical price data for S&P 500 stocks.
Supports incremental updates to only fetch new data since last retrieval.

SETUP INSTRUCTIONS:
-------------------
Before running, install required dependencies:

    pip install yfinance pandas requests beautifulsoup4 --break-system-packages

Or for virtual environment:
    pip install yfinance pandas requests beautifulsoup4

USAGE:
------
    # Interactive mode
    python stock_data_manager.py
    
    # Programmatic usage
    from stock_data_manager import StockDataManager
    manager = StockDataManager()
    manager.update_all_stocks()
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time
import sys

import pandas as pd

# Check for optional dependencies
YFINANCE_AVAILABLE = False
REQUESTS_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    pass

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check and report on required dependencies."""
    missing = []
    
    if not YFINANCE_AVAILABLE:
        missing.append("yfinance")
    if not REQUESTS_AVAILABLE:
        missing.append("requests beautifulsoup4")
    
    if missing:
        print("\n" + "=" * 60)
        print("MISSING DEPENDENCIES")
        print("=" * 60)
        print("\nThe following packages are required but not installed:")
        for pkg in missing:
            print("  - %s" % pkg)
        print("\nInstall with:")
        print("  pip install %s --break-system-packages" % ' '.join(missing))
        print("\nOr in a virtual environment:")
        print("  pip install %s" % ' '.join(missing))
        print("=" * 60 + "\n")
        return False
    return True


class StockDataManager:
    """
    Manages stock price data storage and retrieval with incremental updates.
    """
    
    def __init__(self, data_dir: str = "./stock_data"):
        """
        Initialize the data manager.
        
        Args:
            data_dir: Directory to store all stock data files
        """
        self.data_dir = Path(data_dir)
        self.price_data_dir = self.data_dir / "prices"
        self.metadata_file = self.data_dir / "metadata.json"
        self.tickers_file = self.data_dir / "sp500_tickers.json"
        self.delisted_file = self.data_dir / "delisted_tickers.json"
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.price_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup file logging
        file_handler = logging.FileHandler(self.data_dir / 'stock_data_manager.log')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        # Load or initialize metadata
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict:
        """Load metadata from file or create new."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {
            "last_ticker_update": None,
            "tickers": [],
            "stock_updates": {}  # ticker -> last_update_date
        }
    
    def _save_metadata(self):
        """Save metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def _load_delisted_tickers(self) -> List[str]:
        """Load list of known delisted/failed tickers."""
        if self.delisted_file.exists():
            with open(self.delisted_file, 'r') as f:
                data = json.load(f)
                return data.get("tickers", [])
        return []
    
    def _save_delisted_tickers(self, tickers: List[str]):
        """Save list of delisted/failed tickers."""
        with open(self.delisted_file, 'w') as f:
            json.dump({
                "tickers": tickers,
                "updated": datetime.now().isoformat()
            }, f, indent=2)
    
    def clear_delisted_tickers(self):
        """Clear the list of delisted tickers to retry them."""
        self._save_delisted_tickers([])
        logger.info("Cleared delisted tickers list")
    
    def fetch_sp500_tickers(self, force_refresh: bool = False) -> List[str]:
        """
        Fetch current S&P 500 ticker list.
        
        Args:
            force_refresh: If True, fetch fresh list even if cached
            
        Returns:
            List of ticker symbols
        """
        # Check if we have recent tickers (less than 7 days old)
        if not force_refresh and self.metadata.get("last_ticker_update"):
            last_update = datetime.fromisoformat(self.metadata["last_ticker_update"])
            if datetime.now() - last_update < timedelta(days=7):
                logger.info("Using cached ticker list (%d tickers)" % len(self.metadata['tickers']))
                return self.metadata["tickers"]
        
        logger.info("Loading S&P 500 ticker list...")
        
        # Use curated list
        tickers = self._get_sp500_tickers()
        
        # Update metadata
        self.metadata["tickers"] = tickers
        self.metadata["last_ticker_update"] = datetime.now().isoformat()
        self._save_metadata()
        
        # Save tickers to separate file
        with open(self.tickers_file, 'w') as f:
            json.dump({"tickers": tickers, "count": len(tickers), 
                      "updated": datetime.now().isoformat()}, f, indent=2)
        
        return tickers
    
    def _get_sp500_tickers(self) -> List[str]:
        """
        Return the S&P 500 ticker list.
        """
        # Complete S&P 500 components as of late 2024
        tickers = [
            # A
            "A", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI", "ADM",
            "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG", "AKAM",
            "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN", "AMP",
            "AMT", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH", "APTV",
            "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK", "AXON", "AXP", "AZO",
            # B
            "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX", "BEN", "BF.B", "BG",
            "BIIB", "BIO", "BK", "BKNG", "BKR", "BLDR", "BLK", "BMY", "BR", "BRK.B",
            "BRO", "BSX", "BWA", "BX", "BXP",
            # C
            "C", "CAG", "CAH", "CARR", "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL",
            "CDNS", "CDW", "CE", "CEG", "CF", "CFG", "CHD", "CHRW", "CHTR", "CI",
            "CINF", "CL", "CLX", "CMA", "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC",
            "CNP", "COF", "COO", "COP", "COR", "COST", "CPAY", "CPB", "CPRT", "CPT",
            "CRL", "CRM", "CSCO", "CSGP", "CSX", "CTAS", "CTLT", "CTRA", "CTSH", "CTVA",
            "CVS", "CVX",
            # D
            "D", "DAL", "DAY", "DD", "DE", "DECK", "DFS", "DG", "DGX", "DHI",
            "DHR", "DIS", "DLR", "DLTR", "DOC", "DOV", "DOW", "DPZ", "DRI", "DTE",
            "DUK", "DVA", "DVN",
            # E
            "DXCM", "EA", "EBAY", "ECL", "ED", "EFX", "EG", "EIX", "EL", "ELV",
            "EMN", "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ES", "ESS",
            "ETN", "ETR", "ETSY", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR",
            # F
            "F", "FANG", "FAST", "FCX", "FDS", "FDX", "FE", "FFIV", "FI", "FICO",
            "FIS", "FITB", "FLT", "FMC", "FOX", "FOXA", "FRT", "FSLR", "FTNT", "FTV",
            # G
            "GD", "GDDY", "GE", "GEHC", "GEN", "GEV", "GILD", "GIS", "GL", "GLW",
            "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW",
            # H
            "HAL", "HAS", "HBAN", "HCA", "HD", "HES", "HIG", "HII", "HLT", "HOLX",
            "HON", "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUM", "HWM",
            # I
            "IBM", "ICE", "IDXX", "IEX", "IFF", "ILMN", "INCY", "INTC", "INTU", "INVH",
            "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW",
            # J
            "J", "JBHT", "JBL", "JCI", "JKHY", "JNJ", "JNPR", "JPM",
            # K
            "K", "KDP", "KEY", "KEYS", "KHC", "KIM", "KKR", "KLAC", "KMB", "KMI",
            "KMX", "KO", "KR",
            # L
            "KVUE", "L", "LDOS", "LEN", "LH", "LHX", "LIN", "LKQ", "LLY", "LMT",
            "LNT", "LOW", "LRCX", "LULU", "LUV", "LVS", "LW", "LYB", "LYV",
            # M
            "MA", "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT",
            "MET", "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST",
            "MO", "MOH", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI",
            "MSFT", "MSI", "MTB", "MTCH", "MTD", "MU",
            # N
            "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC", "NOW",
            "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWS", "NWSA",
            # O
            "O", "ODFL", "OKE", "OMC", "ON", "ORCL", "ORLY", "OTIS", "OXY",
            # P
            "PANW", "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEG", "PEP", "PFE", "PFG",
            "PG", "PGR", "PH", "PHM", "PKG", "PLD", "PM", "PNC", "PNR", "PNW",
            "PODD", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PWR", "PXD",
            # Q-R
            "QCOM", "QRVO", "RCL", "REG", "REGN", "RF", "RJF", "RL", "RMD", "ROK",
            "ROL", "ROP", "ROST", "RSG", "RTX",
            # S
            "SBAC", "SBUX", "SCHW", "SHW", "SJM", "SLB", "SMCI", "SNA", "SNPS", "SO",
            "SOLV", "SPG", "SPGI", "SRE", "STE", "STLD", "STT", "STX", "STZ", "SWK",
            "SWKS", "SYF", "SYK", "SYY",
            # T
            "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", "TGT",
            "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA",
            "TSN", "TT", "TTWO", "TXN", "TXT", "TYL",
            # U
            "UAL", "UBER", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB",
            # V
            "V", "VICI", "VLO", "VLTO", "VMC", "VRSK", "VRSN", "VRTX", "VST", "VTR",
            "VTRS", "VZ",
            # W
            "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WM", "WMB",
            "WMT", "WRB", "WST", "WTW", "WY", "WYNN",
            # X-Z
            "XEL", "XOM", "XYL", "YUM", "ZBH", "ZBRA", "ZTS"
        ]
        
        # Remove duplicates and sort
        tickers = sorted(list(set(tickers)))
        return tickers
    
    def fetch_stock_data(self, ticker: str, start_date: Optional[str] = None, 
                         end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data for a single ticker using yf.Ticker().
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD), defaults to 1 year ago
            end_date: End date (YYYY-MM-DD), defaults to today
            
        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        if not YFINANCE_AVAILABLE:
            logger.error("yfinance not installed. Cannot fetch data.")
            return None
            
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore')
                
                # Use yf.Ticker() method
                stock = yf.Ticker(ticker)
                df = stock.history(start=start_date, end=end_date, raise_errors=False)
            
            if df is None or df.empty:
                logger.debug("%s: No data returned (may be delisted)" % ticker)
                return None
            
            # Check for minimum data quality
            if len(df) < 5:
                logger.debug("%s: Insufficient data points (%d)" % (ticker, len(df)))
                return None
            
            # Reset index to make Date a column
            df = df.reset_index()
            df['Ticker'] = ticker
            
            # Handle date column - find it first
            date_col = None
            for col in ['Date', 'Datetime', 'index']:
                if col in df.columns:
                    date_col = col
                    break
            
            if date_col is None:
                date_col = df.columns[0]
            
            # Handle timezone in date column
            try:
                df[date_col] = pd.to_datetime(df[date_col])
                if df[date_col].dt.tz is not None:
                    df[date_col] = df[date_col].dt.tz_localize(None)
            except Exception:
                df[date_col] = pd.to_datetime(df[date_col].astype(str).str[:10])
            
            # Rename columns to standard format
            column_mapping = {
                date_col: 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Dividends': 'dividends',
                'Stock Splits': 'stock_splits'
            }
            
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            # Ensure required columns exist
            if 'close' not in df.columns:
                logger.debug("%s: Missing close price data" % ticker)
                return None
            
            # Fill missing volume with 0
            if 'volume' not in df.columns:
                df['volume'] = 0
            
            # Select columns in standard order
            output_cols = ['date', 'Ticker', 'open', 'high', 'low', 'close', 'volume']
            available_cols = [c for c in output_cols if c in df.columns]
            
            return df[available_cols]
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'no timezone found' in error_msg or 'delisted' in error_msg:
                logger.debug("%s: Likely delisted or invalid symbol" % ticker)
            else:
                logger.warning("Error fetching data for %s: %s" % (ticker, e))
            return None
    
    def update_stock_data(self, ticker: str, force_full: bool = False) -> Tuple[bool, int]:
        """
        Update data for a single stock (incremental or full).
        
        Args:
            ticker: Stock ticker symbol
            force_full: If True, fetch full history instead of incremental
            
        Returns:
            Tuple of (success: bool, rows_added: int)
        """
        csv_path = self.price_data_dir / ("%s.csv" % ticker)
        
        # Determine date range
        if csv_path.exists() and not force_full:
            # Load existing data
            existing_df = pd.read_csv(csv_path)
            existing_df['date'] = pd.to_datetime(existing_df['date'])
            last_date = existing_df['date'].max()
            
            # Check if data is recent (within 3 days accounting for weekends)
            days_old = (datetime.now() - pd.Timestamp(last_date).to_pydatetime()).days
            if days_old <= 3:
                logger.debug("%s: Data is current (last: %s)" % (ticker, last_date.strftime('%Y-%m-%d')))
                return True, 0
            
            # Fetch only new data
            start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            new_df = self.fetch_stock_data(ticker, start_date, end_date)
            
            if new_df is None or new_df.empty:
                # No new data available
                return True, 0
            
            # Append new data
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df['date'] = pd.to_datetime(combined_df['date'])
            combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
            combined_df = combined_df.sort_values('date')
            
            rows_added = len(combined_df) - len(existing_df)
            
            # Save updated data
            combined_df.to_csv(csv_path, index=False)
            
            # Update metadata
            self.metadata["stock_updates"][ticker] = datetime.now().isoformat()
            self._save_metadata()
            
            return True, rows_added
        else:
            # Fetch full history
            df = self.fetch_stock_data(ticker)
            
            if df is None or df.empty:
                return False, 0
            
            # Save data
            df.to_csv(csv_path, index=False)
            
            # Update metadata
            self.metadata["stock_updates"][ticker] = datetime.now().isoformat()
            self._save_metadata()
            
            return True, len(df)
    
    def update_all_stocks(self, force_full: bool = False, skip_delisted: bool = True) -> Dict:
        """
        Update data for all stocks in the ticker list.
        
        Args:
            force_full: If True, fetch full history for all stocks
            skip_delisted: If True, skip known delisted/failed tickers
            
        Returns:
            Summary dict with counts and details
        """
        tickers = self.fetch_sp500_tickers()
        
        # Load delisted tickers to skip
        delisted_tickers = []
        if skip_delisted:
            delisted_tickers = self._load_delisted_tickers()
            if delisted_tickers:
                logger.info("Skipping %d known delisted tickers" % len(delisted_tickers))
        
        # Filter out delisted tickers
        tickers_to_process = [t for t in tickers if t not in delisted_tickers]
        
        total = len(tickers_to_process)
        success_count = 0
        failed_count = 0
        skipped_count = len(delisted_tickers)
        total_rows_added = 0
        failed_tickers = []
        new_failures = []
        
        logger.info("Updating %d stocks..." % total)
        
        batch_size = 50
        for i, ticker in enumerate(tickers_to_process):
            success, rows_added = self.update_stock_data(ticker, force_full)
            
            if success:
                success_count += 1
                total_rows_added += rows_added
            else:
                failed_count += 1
                failed_tickers.append(ticker)
                new_failures.append(ticker)
            
            # Progress update
            if (i + 1) % 25 == 0:
                logger.info("Progress: %d/%d (%.1f%%)" % (i + 1, total, (i + 1) / total * 100))
            
            # Rate limiting - pause every batch
            if (i + 1) % batch_size == 0 and i + 1 < total:
                logger.info("Pausing to avoid rate limiting...")
                time.sleep(2)
        
        # Update delisted tickers list with new failures
        if new_failures:
            all_delisted = list(set(delisted_tickers + new_failures))
            self._save_delisted_tickers(all_delisted)
            logger.info("Added %d tickers to delisted list" % len(new_failures))
        
        summary = {
            "total_processed": total,
            "successful": success_count,
            "failed": failed_count,
            "skipped_delisted": skipped_count,
            "rows_added": total_rows_added,
            "failed_tickers": failed_tickers,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save summary
        with open(self.data_dir / "last_update_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info("Update complete: %d successful, %d failed, %d skipped" % 
                   (success_count, failed_count, skipped_count))
        
        return summary
    
    def get_stock_data(self, ticker: str, days: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Get locally stored stock data for analysis.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of recent days to return (None for all)
            
        Returns:
            DataFrame with stock data or None if not found
        """
        csv_path = self.price_data_dir / ("%s.csv" % ticker)
        
        if not csv_path.exists():
            logger.warning("No data found for %s" % ticker)
            return None
        
        df = pd.read_csv(csv_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        if days is not None:
            df = df.tail(days)
        
        return df
    
    def get_data_status(self) -> Dict:
        """
        Get status of stored data.
        
        Returns:
            Dict with storage statistics
        """
        csv_files = list(self.price_data_dir.glob("*.csv"))
        
        total_rows = 0
        oldest_date = None
        newest_date = None
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                total_rows += len(df)
                df['date'] = pd.to_datetime(df['date'])
                
                file_oldest = df['date'].min()
                file_newest = df['date'].max()
                
                if oldest_date is None or file_oldest < oldest_date:
                    oldest_date = file_oldest
                if newest_date is None or file_newest > newest_date:
                    newest_date = file_newest
            except Exception:
                continue
        
        delisted = self._load_delisted_tickers()
        
        return {
            "total_tickers_stored": len(csv_files),
            "total_data_points": total_rows,
            "oldest_data": oldest_date.strftime('%Y-%m-%d') if oldest_date else None,
            "newest_data": newest_date.strftime('%Y-%m-%d') if newest_date else None,
            "delisted_tickers": len(delisted),
            "storage_path": str(self.data_dir)
        }


def interactive_menu():
    """Run interactive menu for data management."""
    if not check_dependencies():
        sys.exit(1)
    
    manager = StockDataManager()
    
    while True:
        print("\n" + "=" * 60)
        print("  S&P 500 STOCK DATA MANAGER")
        print("=" * 60)
        print("\n1. Fetch/Update S&P 500 ticker list")
        print("2. Update all stock data (incremental)")
        print("3. Force full refresh of all data")
        print("4. Update specific ticker(s)")
        print("5. View data status")
        print("6. Get stock data for analysis")
        print("7. Clear delisted tickers list")
        print("8. Exit")
        
        choice = input("\nSelect option (1-8): ").strip()
        
        if choice == "1":
            tickers = manager.fetch_sp500_tickers(force_refresh=True)
            print("\nFetched %d S&P 500 tickers" % len(tickers))
            
        elif choice == "2":
            print("\nStarting incremental update...")
            summary = manager.update_all_stocks(force_full=False)
            print("\nUpdate Summary:")
            print("  Successful: %d" % summary['successful'])
            print("  Failed: %d" % summary['failed'])
            print("  Skipped (delisted): %d" % summary['skipped_delisted'])
            print("  Rows added: %d" % summary['rows_added'])
            
        elif choice == "3":
            confirm = input("This will re-download ALL data. Continue? (y/n): ")
            if confirm.lower() == 'y':
                summary = manager.update_all_stocks(force_full=True)
                print("\nFull refresh complete")
                print("  Successful: %d" % summary['successful'])
                print("  Failed: %d" % summary['failed'])
                
        elif choice == "4":
            tickers_input = input("Enter ticker(s) separated by comma: ").strip().upper()
            tickers = [t.strip() for t in tickers_input.split(",")]
            for ticker in tickers:
                success, rows = manager.update_stock_data(ticker, force_full=True)
                if success:
                    print("  %s: Updated (%d rows)" % (ticker, rows))
                else:
                    print("  %s: Failed" % ticker)
                    
        elif choice == "5":
            status = manager.get_data_status()
            print("\nData Status:")
            print("  Tickers stored: %d" % status['total_tickers_stored'])
            print("  Total data points: %s" % "{:,}".format(status['total_data_points']))
            print("  Date range: %s to %s" % (status['oldest_data'], status['newest_data']))
            print("  Delisted tickers: %d" % status['delisted_tickers'])
            print("  Storage path: %s" % status['storage_path'])
            
        elif choice == "6":
            ticker = input("Enter ticker: ").strip().upper()
            days = input("Days of data (blank for all): ").strip()
            days = int(days) if days else None
            
            df = manager.get_stock_data(ticker, days)
            if df is not None:
                print("\n%s - %d rows" % (ticker, len(df)))
                print(df.tail(10).to_string(index=False))
            else:
                print("No data found for %s" % ticker)
                
        elif choice == "7":
            confirm = input("Clear delisted tickers list? (y/n): ")
            if confirm.lower() == 'y':
                manager.clear_delisted_tickers()
                print("Delisted tickers list cleared")
                
        elif choice == "8":
            print("Exiting...")
            break
        else:
            print("Invalid option")


if __name__ == "__main__":
    interactive_menu()
