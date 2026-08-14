@echo off
REM Migration runner for Windows
REM Usage: run_migrations.bat

echo.
echo ================================================================
echo SuperAdvocate Database Migration Runner
echo ================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

echo Installing/updating dependencies...
pip install -q -r requirements.txt

echo.
echo Running migrations...
python run_migrations.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Migration failed. Check the output above for details.
    exit /b 1
)

echo.
echo ================================================================
echo SUCCESS: Database migration completed
echo ================================================================
echo.
pause
