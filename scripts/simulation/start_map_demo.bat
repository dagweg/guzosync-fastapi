@echo off
echo 🚀 Starting GuzoSync Bus Map Demo
echo ================================

echo.
echo 📡 Starting FastAPI Backend...
start "FastAPI Backend" cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo ⏳ Waiting for backend to start...
timeout /t 5 /nobreak > nul

echo.
echo 🌐 Starting Next.js Frontend...
cd client
start "Next.js Frontend" cmd /k "npm run dev"

echo.
echo ✅ Both servers are starting!
echo.
echo 📍 Backend API: http://localhost:8000
echo 🗺️  Frontend App: http://localhost:3000
echo 📚 API Docs: http://localhost:8000/docs
echo.
echo 🔑 Test Login Credentials:
echo    Admin: test_control_admin@guzosync.com / Test123!
echo    Driver: test_bus_driver@guzosync.com / Test123!
echo.
echo 💡 To see the map with buses and routes:
echo    1. Open http://localhost:3000
echo    2. Login with admin credentials
echo    3. Click on any bus to see its route!
echo.
pause
