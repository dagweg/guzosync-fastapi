#!/bin/bash

echo "🚀 Starting GuzoSync Bus Map Demo"
echo "================================"

echo ""
echo "📡 Starting FastAPI Backend..."
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo ""
echo "⏳ Waiting for backend to start..."
sleep 5

echo ""
echo "🌐 Starting Next.js Frontend..."
cd client
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Both servers are starting!"
echo ""
echo "📍 Backend API: http://localhost:8000"
echo "🗺️  Frontend App: http://localhost:3000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "🔑 Test Login Credentials:"
echo "   Admin: test_control_admin@guzosync.com / Test123!"
echo "   Driver: test_bus_driver@guzosync.com / Test123!"
echo ""
echo "💡 To see the map with buses and routes:"
echo "   1. Open http://localhost:3000"
echo "   2. Login with admin credentials"
echo "   3. Click on any bus to see its route!"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user to stop
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
