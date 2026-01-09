#!/usr/bin/env python3
"""
Mean Reversion Analysis Application - S&P 500
Analyzes S&P 500 stocks using locally stored price data.
Uses the StockDataManager for data retrieval.

Dependencies:
    pip install yfinance pandas numpy scipy matplotlib --break-system-packages
"""

import numpy as np
from scipy import special
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from pathlib import Path
import warnings
import sys

# Import the stock data manager
from stock_data_manager import StockDataManager

warnings.filterwarnings('ignore')


@dataclass
class StockAnalysis:
    """Data class to hold analysis results for a stock."""
    ticker: str
    current_price: float
    mean_price: float
    std_dev: float
    z_score: float
    rsi: float
    gap_from_mean: float
    gap_percentage: float
    reversion_probability: float
    expected_days_to_revert: float
    half_life: float
    signal_strength: str
    direction: str
    prices: np.ndarray
    dates: List[datetime]
    composite_score: float = 0.0
    data_quality: str = "GOOD"


class MeanReversionAnalyzer:
    """
    Analyzes stocks for mean reversion opportunities.
    Integrates with StockDataManager for data access.
    """
    
    def __init__(self, data_dir: str = "./stock_data"):
        """
        Initialize the analyzer with data manager.
        
        Args:
            data_dir: Directory where stock data is stored
        """
        self.data_manager = StockDataManager(data_dir=data_dir)
        self.min_data_points = 50  # Minimum days of data required
        self.analysis_window = 100  # Days to analyze
        
    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index with smoothed averages."""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Use exponential moving average for smoother RSI
        alpha = 1.0 / period
        avg_gain = gains[0]
        avg_loss = losses[0]
        
        for i in range(1, len(gains)):
            avg_gain = alpha * gains[i] + (1 - alpha) * avg_gain
            avg_loss = alpha * losses[i] + (1 - alpha) * avg_loss
        
        if avg_loss < 0.0001:
            return 95.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return max(5, min(95, rsi))

    def calculate_half_life(self, prices: np.ndarray) -> float:
        """
        Calculate half-life of mean reversion using OLS regression.
        Based on Ornstein-Uhlenbeck process estimation.
        """
        if len(prices) < 20:
            return 30.0
        
        lag_prices = prices[:-1]
        delta_prices = np.diff(prices)
        
        X = np.column_stack([np.ones(len(lag_prices)), lag_prices])
        y = delta_prices
        
        try:
            result = np.linalg.lstsq(X, y, rcond=None)
            beta = result[0][1]
            if beta >= 0:
                return 45.0
            half_life = -np.log(2) / beta
            return min(max(half_life, 3), 60)
        except:
            return 30.0

    def calculate_reversion_probability(self, z_score: float, rsi: float, 
                                        half_life: float) -> float:
        """
        Calculate probability of reverting to mean within 30 days.
        Combines Z-score extremity, RSI, and half-life.
        """
        # Z-score contribution
        z_extremity = 2 * (1 - 0.5 * (1 + special.erf(abs(z_score) / np.sqrt(2))))
        z_prob = 0.4 + 0.4 * (1 - z_extremity)
        
        # RSI contribution
        if rsi < 30:
            rsi_prob = 0.5 + 0.4 * (30 - rsi) / 30
        elif rsi > 70:
            rsi_prob = 0.5 + 0.4 * (rsi - 70) / 30
        else:
            rsi_prob = 0.3 + 0.2 * min(abs(rsi - 50), 20) / 20
        
        # Half-life contribution
        if half_life < 60:
            hl_prob = 1 - np.exp(-30 * np.log(2) / half_life)
        else:
            hl_prob = 0.3
        
        # Agreement bonus/penalty
        z_rsi_agreement = 1.0
        if (z_score < 0 and rsi < 40) or (z_score > 0 and rsi > 60):
            z_rsi_agreement = 1.15
        elif (z_score < 0 and rsi > 60) or (z_score > 0 and rsi < 40):
            z_rsi_agreement = 0.85
        
        combined = (z_prob * 0.35 + rsi_prob * 0.35 + hl_prob * 0.30) * z_rsi_agreement
        
        return min(max(combined, 0.15), 0.92)

    def analyze_stock(self, ticker: str) -> Optional[StockAnalysis]:
        """
        Perform mean reversion analysis on a single stock.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            StockAnalysis object or None if insufficient data
        """
        # Get data from manager
        df = self.data_manager.get_stock_data(ticker, days=self.analysis_window)
        
        if df is None or len(df) < self.min_data_points:
            return None
        
        # Extract prices and dates
        prices = df['close'].values
        dates = pd.to_datetime(df['date']).tolist()
        
        # Calculate metrics
        current_price = prices[-1]
        mean_price = np.mean(prices)
        std_dev = np.std(prices)
        
        if std_dev < 0.01:  # Avoid division by zero
            return None
        
        z_score = (current_price - mean_price) / std_dev
        rsi = self.calculate_rsi(prices)
        half_life = self.calculate_half_life(prices)
        
        gap_from_mean = current_price - mean_price
        gap_percentage = (gap_from_mean / mean_price) * 100
        
        reversion_probability = self.calculate_reversion_probability(z_score, rsi, half_life)
        
        # Expected days to revert
        expected_days = half_life * (1 + 0.5 * abs(z_score))
        expected_days = min(max(expected_days, 3), 45)
        
        # Signal strength
        abs_z = abs(z_score)
        is_oversold = z_score < 0 and rsi < 35
        is_overbought = z_score > 0 and rsi > 65
        
        if abs_z > 2.0 and (is_oversold or is_overbought):
            signal_strength = "STRONG"
        elif abs_z > 1.8 and (rsi < 40 or rsi > 60):
            signal_strength = "MODERATE"
        elif abs_z > 1.5:
            signal_strength = "WEAK"
        else:
            signal_strength = "MINIMAL"
        
        # Trade direction
        direction = "LONG (Oversold)" if z_score < 0 else "SHORT (Overbought)"
        
        # Data quality assessment
        data_quality = "GOOD" if len(df) >= 90 else "LIMITED"
        
        return StockAnalysis(
            ticker=ticker,
            current_price=round(current_price, 2),
            mean_price=round(mean_price, 2),
            std_dev=round(std_dev, 2),
            z_score=round(z_score, 2),
            rsi=round(rsi, 1),
            gap_from_mean=round(gap_from_mean, 2),
            gap_percentage=round(gap_percentage, 1),
            reversion_probability=round(reversion_probability, 3),
            expected_days_to_revert=round(expected_days, 1),
            half_life=round(half_life, 1),
            signal_strength=signal_strength,
            direction=direction,
            prices=prices,
            dates=dates,
            data_quality=data_quality
        )

    def run_analysis(self, tickers: Optional[List[str]] = None, 
                    top_n: int = 10,
                    min_z_score: float = 1.5) -> List[StockAnalysis]:
        """
        Run mean reversion analysis on multiple stocks.
        Returns only LONG (oversold) candidates.
        
        Args:
            tickers: List of tickers to analyze (defaults to all available)
            top_n: Number of top candidates to return
            min_z_score: Minimum absolute Z-score for candidates
            
        Returns:
            List of top StockAnalysis results (LONG signals only)
        """
        if tickers is None:
            # Get all available tickers from stored data
            tickers = [f.stem for f in Path(self.data_manager.price_data_dir).glob("*.csv")]
        
        if not tickers:
            print("No stock data available. Please run stock_data_manager.py first.")
            return []
        
        print("\nAnalyzing %d stocks..." % len(tickers))
        
        results = []
        failed = 0
        
        for i, ticker in enumerate(tickers):
            if (i + 1) % 100 == 0:
                print("  Progress: %d/%d" % (i + 1, len(tickers)))
            
            analysis = self.analyze_stock(ticker)
            if analysis is not None:
                results.append(analysis)
            else:
                failed += 1
        
        print("  Analyzed: %d stocks (%d skipped due to insufficient data)" % (len(results), failed))
        
        # Filter for LONG signals only (negative Z-score = oversold)
        # and meet minimum Z-score threshold
        candidates = [r for r in results if r.z_score <= -min_z_score]
        print("  LONG Candidates (Z <= -%.1f): %d" % (min_z_score, len(candidates)))
        
        # Calculate composite score and sort
        for c in candidates:
            c.composite_score = c.reversion_probability * (1 + abs(c.z_score) / 3)
        
        candidates.sort(key=lambda x: x.composite_score, reverse=True)
        
        return candidates[:top_n]

    def create_visualization(self, top_stocks: List[StockAnalysis], 
                            output_path: str = "./mean_reversion_charts.png"):
        """Create visualization for top candidates."""
        if not top_stocks:
            print("No stocks to visualize")
            return
        
        n_stocks = len(top_stocks)
        n_cols = 2
        n_rows = (n_stocks + 1) // 2
        
        fig = plt.figure(figsize=(20, 5 * n_rows))
        fig.patch.set_facecolor('white')
        
        fig.suptitle('Top LONG (Oversold) Candidates - S&P 500\n'
                    '100-Day Price History | Z-Score + RSI Analysis', 
                    fontsize=18, fontweight='bold', y=0.995)
        
        for i, stock in enumerate(top_stocks):
            ax = fig.add_subplot(n_rows, n_cols, i + 1)
            self._create_stock_chart(stock, ax)
        
        plt.tight_layout(rect=[0, 0.02, 1, 0.97])
        
        fig.text(0.5, 0.01, 
                'Generated: %s | Data from local storage' % datetime.now().strftime("%Y-%m-%d %H:%M"),
                ha='center', fontsize=9, color='gray')
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print("\nCharts saved to: %s" % output_path)
        
        # Also save PDF
        pdf_path = output_path.replace('.png', '.pdf')
        plt.savefig(pdf_path, bbox_inches='tight', facecolor='white', edgecolor='none')
        print("PDF saved to: %s" % pdf_path)
        
        plt.close()

    def _create_stock_chart(self, analysis: StockAnalysis, ax: plt.Axes):
        """Create chart for a single stock."""
        prices = analysis.prices
        dates = analysis.dates
        mean = analysis.mean_price
        std = analysis.std_dev
        
        ax.plot(dates, prices, 'b-', linewidth=1.8, label='Daily Close', alpha=0.9)
        ax.axhline(y=mean, color='#228B22', linestyle='-', linewidth=2.5, 
                  label='100-Day Mean: $%.2f' % mean)
        
        ax.axhline(y=mean + std, color='#FFA500', linestyle='--', linewidth=1.5, alpha=0.8)
        ax.axhline(y=mean - std, color='#FFA500', linestyle='--', linewidth=1.5, alpha=0.8,
                  label='+/-1 Std ($%.2f)' % std)
        ax.axhline(y=mean + 2*std, color='#DC143C', linestyle=':', linewidth=1.5, alpha=0.7)
        ax.axhline(y=mean - 2*std, color='#DC143C', linestyle=':', linewidth=1.5, alpha=0.7,
                  label='+/-2 Std')
        
        gap_color = '#FF6B6B' if analysis.z_score > 0 else '#90EE90'
        ax.fill_between(dates, prices, mean, alpha=0.35, color=gap_color)
        
        ax.scatter([dates[-1]], [prices[-1]], color='#DC143C', s=120, zorder=5, 
                  marker='o', edgecolors='white', linewidth=2)
        
        offset = 15 if analysis.z_score > 0 else -25
        ax.annotate('$%.2f' % prices[-1], (dates[-1], prices[-1]), 
                   xytext=(5, offset), textcoords='offset points', 
                   fontsize=10, fontweight='bold', color='#DC143C')
        
        ax.set_title("%s" % analysis.ticker, fontsize=14, fontweight='bold', pad=10)
        ax.set_xlabel('Date', fontsize=9)
        ax.set_ylabel('Price ($)', fontsize=9)
        ax.legend(loc='upper left', fontsize=7, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        
        textstr = ("Z-Score: %+.2f\n"
                  "RSI(14): %.1f\n"
                  "Gap: %+.1f%%\n"
                  "Half-Life: %.0fd\n"
                  "Prob(30d): %.0f%%\n"
                  "Signal: %s" % (analysis.z_score, analysis.rsi, analysis.gap_percentage,
                                  analysis.half_life, analysis.reversion_probability*100,
                                  analysis.signal_strength))
        
        props = dict(boxstyle='round,pad=0.5', facecolor='#FFFACD', alpha=0.9, edgecolor='#DAA520')
        ax.text(0.98, 0.02, textstr, transform=ax.transAxes, fontsize=8,
               verticalalignment='bottom', horizontalalignment='right', bbox=props,
               family='monospace')
        
        # Use ASCII-safe arrows
        direction_text = "^ LONG" if "LONG" in analysis.direction else "v SHORT"
        direction_color = '#228B22' if "LONG" in analysis.direction else '#DC143C'
        ax.text(0.02, 0.98, direction_text, transform=ax.transAxes, fontsize=11,
               verticalalignment='top', fontweight='bold', color=direction_color)

    def generate_report(self, top_stocks: List[StockAnalysis], 
                       output_path: str = "./mean_reversion_report.txt"):
        """Generate text report for top candidates."""
        report = "=" * 80 + "\n"
        report += "        MEAN REVERSION ANALYSIS REPORT - S&P 500 STOCKS\n"
        report += "                 Generated: %s\n" % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report += "=" * 80 + "\n\n"
        
        report += "DATA SOURCE: Local stock data storage\n"
        report += "-" * 80 + "\n\n"
        
        report += "METHODOLOGY\n"
        report += "-" * 80 + "\n"
        report += "Indicators Used:\n"
        report += "  * Z-Score: Standard deviations from 100-day mean\n"
        report += "  * RSI (14-day): Overbought (>70) / Oversold (<30)\n"
        report += "  * Half-Life: Ornstein-Uhlenbeck estimated reversion speed\n"
        report += "  * Probability: Combined metric for 30-day reversion\n\n"
        
        report += "=" * 80 + "\n"
        report += "                    TOP %d LONG (OVERSOLD) CANDIDATES\n" % len(top_stocks)
        report += "=" * 80 + "\n\n"
        
        for i, stock in enumerate(top_stocks, 1):
            report += "-" * 80 + "\n"
            report += "  #%d  %s\n" % (i, stock.ticker)
            report += "-" * 80 + "\n"
            report += "  Current Price:       $%10.2f\n" % stock.current_price
            report += "  100-Day Mean:        $%10.2f\n" % stock.mean_price
            report += "  Standard Deviation:  $%10.2f\n" % stock.std_dev
            report += "  Gap from Mean:       $%10.2f  (%+.1f%%)\n" % (stock.gap_from_mean, stock.gap_percentage)
            report += "  \n"
            report += "  Z-Score:             %10.2f\n" % stock.z_score
            report += "  RSI (14):            %10.1f\n" % stock.rsi
            report += "  Half-Life:           %10.1f days\n" % stock.half_life
            report += "  \n"
            report += "  Reversion Prob:      %10.1f%%\n" % (stock.reversion_probability*100)
            report += "  Expected Days:       %10.1f\n" % stock.expected_days_to_revert
            report += "  Signal Strength:     %10s\n" % stock.signal_strength
            report += "  Trade Direction:     %s\n" % stock.direction
            report += "  Data Quality:        %s\n\n" % stock.data_quality
        
        report += "=" * 80 + "\n"
        report += "RISK DISCLAIMER\n"
        report += "-" * 80 + "\n"
        report += "This analysis is for informational purposes only.\n"
        report += "Mean reversion strategies carry significant risk.\n"
        report += "Always conduct your own due diligence before trading.\n"
        report += "=" * 80 + "\n"
        
        # Write with explicit UTF-8 encoding
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("Report saved to: %s" % output_path)
        return report


def main():
    """Main execution function."""
    print("=" * 70)
    print("     MEAN REVERSION ANALYSIS - S&P 500")
    print("     (Using Local Stock Data)")
    print("=" * 70)
    
    # Initialize analyzer
    analyzer = MeanReversionAnalyzer(data_dir="./stock_data")
    
    # Check data availability
    status = analyzer.data_manager.get_data_status()
    
    if status["total_tickers_stored"] == 0:
        print("\n[!] No stock data found!")
        print("Please run stock_data_manager.py first to download data.")
        print("\nUsage:")
        print("  1. python stock_data_manager.py")
        print("  2. Select option 2 to download all stock data")
        print("  3. Then run this analysis again")
        return
    
    print("\nData Status:")
    print("  Stocks available: %d" % status['total_tickers_stored'])
    print("  Data points: %s" % "{:,}".format(status['total_data_points']))
    print("  Date range: %s to %s" % (status['oldest_data'], status['newest_data']))
    
    # Run analysis
    top_stocks = analyzer.run_analysis(top_n=10, min_z_score=1.5)
    
    if not top_stocks:
        print("\nNo candidates found meeting criteria.")
        return
    
    # Print summary table
    print("\n" + "-" * 95)
    print("%-5s%-8s%10s%10s%10s%8s%10s%-12s" % ('Rank', 'Ticker', 'Price', 'Mean', 'Z-Score', 'RSI', 'Prob', 'Signal'))
    print("-" * 95)
    
    for i, stock in enumerate(top_stocks, 1):
        print("%-5d%-8s$%8.2f$%8.2f%+10.2f%8.1f%9.1f%%  %-10s" % (
            i, stock.ticker, stock.current_price, stock.mean_price,
            stock.z_score, stock.rsi, stock.reversion_probability*100,
            stock.signal_strength))
    
    print("-" * 95)
    
    # Generate outputs
    analyzer.generate_report(top_stocks, "./mean_reversion_report.txt")
    analyzer.create_visualization(top_stocks, "./mean_reversion_charts.png")
    
    print("\n" + "=" * 70)
    print("                      ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
