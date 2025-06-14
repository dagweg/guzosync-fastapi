@echo off
echo ========================================
echo GuzoSync Backend - Start with Seeding
echo ========================================
echo.

echo 🌱 Seeding database with test data...
python scripts\database\init_payments.py
python scripts\database\init_db_complete.py

if %ERRORLEVEL% NEQ 0 (
    echo ❌ Database seeding failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ✅ Database seeding completed successfully!
echo.
echo 🚀 Starting FastAPI server...
echo.

