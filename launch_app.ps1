# Mean Reversion Analysis - S&P 500
# PowerShell Launch Script
# Right-click and "Run with PowerShell" or double-click

$Host.UI.RawUI.WindowTitle = "Mean Reversion Analysis - S&P 500"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MEAN REVERSION ANALYSIS - S&P 500" -ForegroundColor Cyan
Write-Host "  Starting Application..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check required files
$requiredFiles = @("app.py", "stock_data_manager.py", "mean_reversion_integrated.py")
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "ERROR: $file not found" -ForegroundColor Red
        Write-Host "Please ensure all files are in the same folder" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Host "All required files found" -ForegroundColor Green
Write-Host ""

# Install dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow

$packages = @("flask", "yfinance", "pandas", "numpy", "scipy")
foreach ($pkg in $packages) {
    $installed = pip show $pkg 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing $pkg..." -ForegroundColor Yellow
        pip install $pkg 2>&1 | Out-Null
    }
}

Write-Host "Dependencies OK" -ForegroundColor Green
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Starting Flask Server..." -ForegroundColor Cyan
Write-Host "  Opening browser to http://localhost:5000" -ForegroundColor Green
Write-Host "" 
Write-Host "  Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Open browser after short delay
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:5000"
} | Out-Null

# Run Flask app
python app.py

Write-Host ""
Write-Host "Server stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
