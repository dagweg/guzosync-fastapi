# Troubleshooting Guide - GuzoSync FastAPI Client

## Common Issues and Solutions

### 🔌 Connection Issues

#### "API connection failed" or "Network Error"
**Problem**: The Next.js client can't connect to your FastAPI backend.

**Solutions**:
1. **Check if FastAPI is running**:
   ```bash
   # In your backend directory
   uvicorn main:app --reload --port 8000
   ```

2. **Verify the backend URL**:
   - Open `http://localhost:8000/docs` in your browser
   - You should see the FastAPI Swagger documentation

3. **Check environment variables**:
   ```bash
   # In client/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
   ```

4. **Test backend connection**:
   ```bash
   cd client
   npm run test-backend
   ```

#### "WebSocket connection failed"
**Problem**: Real-time features aren't working.

**Solutions**:
1. **Check WebSocket endpoint**: Visit `ws://localhost:8000/ws/connect` (should show upgrade error in browser)
2. **Verify JWT token**: Make sure you're logged in and have a valid token
3. **Check CORS settings**: Ensure your FastAPI backend allows WebSocket connections from `localhost:3000`

### 🔐 Authentication Issues

#### "Authentication failed" or "401 Unauthorized"
**Problem**: Can't log in or API requests are rejected.

**Solutions**:
1. **Check user credentials**:
   - Use credentials from your FastAPI backend database
   - Try registering a new user first

2. **Verify JWT configuration**:
   - Check `JWT_SECRET` in your FastAPI backend
   - Ensure token expiration settings are correct

3. **Clear browser storage**:
   ```javascript
   // In browser console
   localStorage.clear();
   ```

#### "No users found" or "Invalid credentials"
**Problem**: Demo users don't exist in the database.

**Solutions**:
1. **Initialize demo data**: Run your backend's database initialization script
2. **Create users manually**: Use the registration endpoint
3. **Check database connection**: Ensure MongoDB is running and accessible

### 🗺️ Map Issues

#### "Map not loading" or blank map
**Problem**: Mapbox integration isn't working.

**Solutions**:
1. **Get Mapbox token**:
   - Sign up at [mapbox.com](https://mapbox.com)
   - Get a free access token
   - Add it to `.env.local`:
     ```
     MAPBOX_ACCESS_TOKEN=pk.eyJ1IjoieW91cnVzZXJuYW1lIiwiYSI6ImNsb...
     ```

2. **Check token validity**:
   - Ensure the token is not expired
   - Verify it has the correct permissions

#### "Bus markers not showing"
**Problem**: Buses appear in the tracker but not on the map.

**Solutions**:
1. **Check bus data**: Ensure buses have `current_location` data
2. **Verify coordinates**: Coordinates should be in [longitude, latitude] format
3. **Check console errors**: Look for JavaScript errors in browser dev tools

### 📡 Real-time Issues

#### "Live updates not working"
**Problem**: Bus locations or chat messages aren't updating in real-time.

**Solutions**:
1. **Check WebSocket connection**: Look for the green "Connected" indicator
2. **Verify room subscriptions**: Check browser console for "Joined room" messages
3. **Test with multiple tabs**: Open the app in multiple browser tabs

#### "Chat messages not sending"
**Problem**: Messages don't appear or fail to send.

**Solutions**:
1. **Check conversation endpoints**: Ensure `/api/conversations/{id}/messages` exists
2. **Verify room joining**: Make sure you've joined the conversation room
3. **Check authentication**: Ensure you're logged in with a valid token

### 🐛 Development Issues

#### "Module not found" errors
**Problem**: Import errors or missing dependencies.

**Solutions**:
1. **Reinstall dependencies**:
   ```bash
   cd client
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Check TypeScript paths**: Verify `@/*` imports are configured correctly

#### "CORS errors"
**Problem**: Browser blocks requests due to CORS policy.

**Solutions**:
1. **Configure FastAPI CORS**:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

### 🔧 Quick Diagnostics

#### Run these commands to diagnose issues:

1. **Test backend connection**:
   ```bash
   npm run test-backend
   ```

2. **Check environment variables**:
   ```bash
   cat .env.local
   ```

3. **Verify API endpoints**:
   ```bash
   curl http://localhost:8000/api/config/languages
   ```

4. **Test WebSocket**:
   ```bash
   # Install wscat: npm install -g wscat
   wscat -c ws://localhost:8000/ws/connect?token=test
   ```

### 📞 Getting Help

If you're still having issues:

1. **Check browser console**: Look for error messages in Developer Tools
2. **Check FastAPI logs**: Look at your backend server logs
3. **Verify data**: Ensure your backend has demo buses, routes, and stops
4. **Test endpoints**: Use the FastAPI Swagger docs at `http://localhost:8000/docs`

### 🎯 Expected Behavior

When everything is working correctly:

- ✅ Connection status shows "Connected" for both API and WebSocket
- ✅ Map loads with Mapbox tiles
- ✅ Bus markers appear on the map
- ✅ Real-time updates show "Live" indicators
- ✅ Chat messages send and receive instantly
- ✅ Notifications appear as toast messages
- ✅ Admin users can click on map to update bus locations

### 📋 Checklist

Before reporting issues, verify:

- [ ] FastAPI backend is running on port 8000
- [ ] Database is initialized with demo data
- [ ] Mapbox token is valid and configured
- [ ] Environment variables are set correctly
- [ ] No CORS errors in browser console
- [ ] WebSocket connection is established
- [ ] User is logged in with valid credentials
