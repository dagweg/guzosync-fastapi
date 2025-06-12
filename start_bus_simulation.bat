@echo off
echo 🚀 Starting GuzoSync Bus Simulation
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\activate.bat
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if .env file exists
if not exist ".env" (
    echo ⚠️ .env file not found!
    echo Please create .env file with MongoDB configuration
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

echo 🌱 Starting simulation with database seeding and route assignment...
echo.

REM Start simulation with seeding and route assignment
python start_simulation.py --seed-first --assign-routes --interval 3

echo.
echo 👋 Simulation ended
pause
