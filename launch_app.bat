@echo off
title Mean Reversion Analysis - S&P 500

echo ============================================================
echo   MEAN REVERSION ANALYSIS - S&P 500
echo   Starting Application...
echo ============================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Python found!
echo.

:: Change to the directory where this batch file is located
cd /d "%~dp0"

:: Check if required files exist
if not exist "app.py" (
    echo ERROR: app.py not found in current directory
    echo Please make sure all files are in the same folder:
    echo   - launch_app.bat
    echo   - app.py
    echo   - stock_data_manager.py
    echo   - mean_reversion_integrated.py
    echo.
    pause
    exit /b 1
)

:: Install dependencies if needed
echo Checking dependencies...
pip show flask >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Flask...
    pip install flask --break-system-packages 2>nul || pip install flask
)

pip show yfinance >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing yfinance...
    pip install yfinance --break-system-packages 2>nul || pip install yfinance
)

pip show scipy >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing scipy...
    pip install scipy --break-system-packages 2>nul || pip install scipy
)

echo.
echo ============================================================
echo   Dependencies OK - Starting Server
echo ============================================================
echo.
echo   Opening browser to http://localhost:5000
echo.
echo   Press Ctrl+C to stop the server
echo ============================================================
echo.

:: Wait a moment then open browser
start "" "http://localhost:5000"

:: Run the Flask app
python app.py

:: If we get here, the server stopped
echo.
echo Server stopped.
pause
