@echo off
echo Setting up GuzoSync Client...
echo.

echo Installing dependencies...
npm install

echo.
echo Testing FastAPI backend connection...
npm run test-backend

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Make sure your FastAPI backend is running on http://localhost:8000
echo 2. Get a Mapbox access token from https://mapbox.com
echo 3. Update .env.local with your Mapbox token
echo 4. Run 'npm run dev' to start the development server
echo 5. Open http://localhost:3000 in your browser
echo.
echo Demo credentials:
echo Use the credentials from your FastAPI backend database
echo Default example: admin@example.com / password123
echo.
pause
