@echo off
echo ========================================
echo GuzoSync Backend - Start with Seeding
echo ========================================
echo.

echo 🌱 Seeding database with test data...
python init_payments.py
python seed_db_startup.py

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

