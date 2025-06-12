# Bus Simulation Background Service

The bus simulation system now runs as a **background service** that starts automatically when the FastAPI server starts. This ensures that bus simulation is always available in production deployments without requiring separate processes.

## 🚀 **Automatic Startup**

The simulation service is integrated into the FastAPI application lifecycle:

1. **Server Starts** → Bus simulation service initializes
2. **Database Ready** → Simulation begins automatically  
3. **Server Stops** → Simulation shuts down gracefully

## ⚙️ **Configuration**

Control the simulation service via environment variables in your `.env` file:

```bash
# Enable/disable simulation service
BUS_SIMULATION_ENABLED=true

# Update interval in seconds (how often buses move)
BUS_SIMULATION_INTERVAL=5.0

# Maximum number of buses to simulate (performance limit)
BUS_SIMULATION_MAX_BUSES=50

# Automatically assign routes to buses without assignments
BUS_SIMULATION_AUTO_ASSIGN=true
```

## 📊 **Service Behavior**

### **Startup Sequence**
1. Service checks if simulation should start (buses, routes, stops exist)
2. If conditions not met, enters **monitoring mode** (retries every minute)
3. When ready, automatically assigns routes to buses (if enabled)
4. Initializes simulation and starts bus movement
5. Continues running in background

### **Self-Healing**
- Monitors simulation health every minute
- Automatically restarts if simulation stops unexpectedly
- Retries failed startups up to 5 times
- Gracefully handles database disconnections

### **Performance**
- Runs asynchronously without blocking the main server
- Configurable update intervals (default: 5 seconds)
- Limits number of buses for optimal performance
- Efficient database queries with caching

## 🌐 **API Endpoints**

### **Public Health Check**
```http
GET /simulation/health
```
Returns basic simulation status (no authentication required):
```json
{
  "simulation_enabled": true,
  "simulation_running": true,
  "active_buses": 15,
  "total_buses": 20
}
```

### **Detailed Status** (Control Staff Only)
```http
GET /simulation/status
Authorization: Bearer <token>
```
Returns comprehensive simulation information:
```json
{
  "status": "success",
  "simulation": {
    "enabled": true,
    "is_running": true,
    "total_buses": 20,
    "active_buses": 15,
    "routes_loaded": 8,
    "update_interval": 5.0,
    "max_buses": 50,
    "auto_assign_routes": true
  }
}
```

### **Control Operations** (Admin Only)
```http
POST /simulation/start     # Start simulation
POST /simulation/stop      # Stop simulation  
POST /simulation/restart   # Restart simulation
```

## 🔧 **Integration with Existing Systems**

### **WebSocket Broadcasting**
- Uses existing `bus_tracking_service` for location updates
- Broadcasts to `bus_tracking:{bus_id}` and `route_tracking:{route_id}` rooms
- Compatible with existing frontend map displays
- No changes needed to WebSocket clients

### **Database Integration**
- Works with existing MongoDB collections (`buses`, `routes`, `bus_stops`)
- Updates bus locations in real-time
- Respects existing data relationships
- No schema changes required

### **Background Tasks**
- Integrates with existing background task system
- Starts/stops with other services (analytics, route updates)
- Shares app state and database connections
- Follows same error handling patterns

## 🚀 **Deployment**

### **Production Deployment**
The simulation service starts automatically with your FastAPI server:

```bash
# Standard deployment - simulation starts automatically
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Docker deployment
docker run -p 8000:8000 your-guzosync-image

# Render/Heroku deployment
# No special configuration needed - service starts automatically
```

### **Environment-Specific Configuration**

**Development:**
```bash
BUS_SIMULATION_ENABLED=true
BUS_SIMULATION_INTERVAL=3.0    # Faster updates for testing
BUS_SIMULATION_MAX_BUSES=10    # Fewer buses for development
```

**Production:**
```bash
BUS_SIMULATION_ENABLED=true
BUS_SIMULATION_INTERVAL=5.0    # Standard updates
BUS_SIMULATION_MAX_BUSES=100   # More buses for production
```

**Staging/Testing:**
```bash
BUS_SIMULATION_ENABLED=false   # Disable for testing
```

## 📈 **Monitoring**

### **Health Monitoring**
- Check `/health` endpoint for basic status
- Monitor logs for simulation events
- Use `/simulation/status` for detailed information

### **Log Messages**
```
🚀 Starting bus simulation service...
✅ Bus simulation service started successfully
🚌 Conditions met, attempting to start simulation...
🔍 Starting bus simulation monitoring loop
⚠️ Simulation stopped unexpectedly, attempting restart...
🛑 Stopping bus simulation service...
```

### **Performance Metrics**
- Active buses count
- Update frequency
- Memory usage (via standard monitoring)
- WebSocket message rates

## 🔄 **Lifecycle Management**

### **Server Startup**
1. FastAPI app starts
2. Database connection established
3. Background services initialize
4. **Bus simulation service starts**
5. Simulation begins (if conditions met)

### **Server Shutdown**
1. Shutdown signal received
2. **Bus simulation service stops gracefully**
3. Background tasks cancelled
4. Database connections closed
5. Server exits

### **Graceful Restart**
```bash
# Service automatically restarts with server
systemctl restart guzosync

# Or via API (admin only)
curl -X POST http://localhost:8000/simulation/restart \
  -H "Authorization: Bearer <admin-token>"
```

## 🛠️ **Troubleshooting**

### **Simulation Not Starting**
1. Check environment variables: `BUS_SIMULATION_ENABLED=true`
2. Verify database has buses, routes, and stops
3. Check logs for error messages
4. Use `/simulation/status` to see detailed status

### **No Buses Moving**
1. Ensure buses have `bus_status: "OPERATIONAL"`
2. Check if routes are assigned: `BUS_SIMULATION_AUTO_ASSIGN=true`
3. Verify routes have bus stops
4. Check WebSocket connections

### **Performance Issues**
1. Reduce update frequency: `BUS_SIMULATION_INTERVAL=10.0`
2. Limit buses: `BUS_SIMULATION_MAX_BUSES=20`
3. Monitor system resources
4. Check database query performance

## 🎯 **Benefits of Background Service**

✅ **Automatic Operation** - No manual intervention required  
✅ **Production Ready** - Starts with server deployment  
✅ **Self-Healing** - Automatically recovers from failures  
✅ **Configurable** - Environment-based configuration  
✅ **Monitorable** - Health checks and status endpoints  
✅ **Scalable** - Performance limits and optimization  
✅ **Integrated** - Works with existing systems seamlessly  

The bus simulation now runs as a first-class service in your GuzoSync backend, providing realistic bus movement data for testing and demonstration purposes without any additional deployment complexity.
