# GuzoSync Performance Optimization Guide

## Problem
The FastAPI server was consuming excessive RAM (>512MB) and running slowly, causing timeouts on free tier hosting services.

## Root Causes Identified

### 1. Multiple Resource-Intensive Background Services
- **Bus Simulation Service**: Running 5 buses with 5-second updates
- **Real-time Analytics Service**: 3 background tasks updating every 30-60 seconds  
- **Background Tasks Service**: 4 tasks including ETA broadcasting, route updates
- **Scheduled Analytics Service**: Additional analytics processing
- **WebSocket Manager**: Managing real-time connections

### 2. Memory-Heavy Database Operations
- Bus simulation fetching all operational buses repeatedly
- ETA broadcasting querying all buses every minute
- Analytics services running continuous database queries
- Multiple concurrent database cursors with `to_list(length=None)` loading entire result sets into memory

### 3. Inefficient Database Queries
- Using `to_list(length=None)` which loads all results into memory at once
- No pagination or streaming for large datasets
- Multiple services querying the same data independently

## Applied Optimizations

### 1. Service Management
```bash
# Disable resource-intensive services for free tier
BUS_SIMULATION_ENABLED=false
ANALYTICS_SERVICES_ENABLED=false
BACKGROUND_TASKS_ENABLED=false
```

### 2. Database Connection Optimization
```bash
# Reduced connection pool for free tier
DB_MAX_POOL_SIZE=3          # Down from 10
DB_MIN_POOL_SIZE=1          # Added minimum
DB_CONNECTION_TIMEOUT=3000  # Reduced timeout
DB_MAX_IDLE_TIME=30000     # Close idle connections
```

### 3. Query Limits
```bash
# Limit query result sizes
MAX_BUSES_PER_QUERY=5      # Down from unlimited
MAX_STOPS_PER_QUERY=10     # Down from unlimited
```

### 4. Update Intervals
```bash
# Reduced update frequencies
ANALYTICS_UPDATE_INTERVAL=600      # 10 minutes (was 30 seconds)
ETA_BROADCAST_INTERVAL=600         # 10 minutes (was 2 minutes)
ROUTE_SHAPE_UPDATE_INTERVAL=86400  # 24 hours (was 6 hours)
```

### 5. Logging Optimization
```bash
LOG_LEVEL=WARNING  # Reduced from INFO
```

## Quick Setup

### Option 1: Automatic Optimization Script
```bash
# Apply free tier optimizations
python scripts/optimize_for_free_tier.py

# Revert to production settings
python scripts/optimize_for_free_tier.py --revert
```

### Option 2: Manual Environment Configuration
Add to your `.env` file:
```bash
DEPLOYMENT_TIER=free
BUS_SIMULATION_ENABLED=false
ANALYTICS_SERVICES_ENABLED=false
BACKGROUND_TASKS_ENABLED=false
LOG_LEVEL=WARNING
DB_MAX_POOL_SIZE=3
```

## Performance Monitoring

### Health Check Endpoint
```bash
GET /performance/health
```
Returns basic server health without authentication.

### Detailed Performance Status
```bash
GET /performance/status
```
Returns detailed metrics (requires authentication):
- System CPU and memory usage
- Process-specific memory consumption
- Database statistics
- Active services status

### Performance Recommendations
```bash
GET /performance/recommendations
```
Returns optimization suggestions based on current usage.

## Expected Results

### Before Optimization
- **RAM Usage**: >512MB
- **Startup Time**: 30+ seconds
- **Response Time**: Slow due to resource contention
- **Status**: Frequent timeouts on free tier

### After Optimization
- **RAM Usage**: ~200-300MB
- **Startup Time**: 5-10 seconds
- **Response Time**: Improved for basic operations
- **Status**: Stable on free tier hosting

## Disabled Features (Free Tier)

When optimized for free tier, these features are disabled:
- Real-time bus simulation
- Live analytics dashboard updates
- Automatic route shape updates
- ETA broadcasting to WebSocket clients
- Background performance optimization tasks

## Re-enabling Features for Production

To restore full functionality for production deployment:

```bash
# Method 1: Use the script
python scripts/optimize_for_free_tier.py --revert

# Method 2: Update environment variables
DEPLOYMENT_TIER=production
BUS_SIMULATION_ENABLED=true
ANALYTICS_SERVICES_ENABLED=true
BACKGROUND_TASKS_ENABLED=true
LOG_LEVEL=INFO
DB_MAX_POOL_SIZE=10
```

## Configuration Reference

### Performance Tiers

| Setting | Free Tier | Production |
|---------|-----------|------------|
| Bus Simulation | Disabled | Enabled |
| Analytics Services | Disabled | Enabled |
| Background Tasks | Disabled | Enabled |
| DB Pool Size | 3 | 10 |
| Query Limits | 5-10 items | 50-100 items |
| Update Intervals | 10+ minutes | 30 seconds - 2 minutes |
| Log Level | WARNING | INFO |

### Environment Variables

| Variable | Description | Free Tier | Production |
|----------|-------------|-----------|------------|
| `DEPLOYMENT_TIER` | Deployment environment | `free` | `production` |
| `BUS_SIMULATION_ENABLED` | Enable bus simulation | `false` | `true` |
| `ANALYTICS_SERVICES_ENABLED` | Enable analytics | `false` | `true` |
| `BACKGROUND_TASKS_ENABLED` | Enable background tasks | `false` | `true` |
| `DB_MAX_POOL_SIZE` | Max DB connections | `3` | `10` |
| `LOG_LEVEL` | Logging verbosity | `WARNING` | `INFO` |

## Troubleshooting

### Still High Memory Usage?
1. Check if all optimizations are applied: `GET /performance/config`
2. Monitor active processes: `GET /performance/status`
3. Run manual optimization: `POST /performance/optimize`

### Features Not Working?
1. Check if feature is disabled for free tier
2. Verify environment variables are set correctly
3. Restart server after configuration changes

### Database Connection Issues?
1. Verify MongoDB connection string
2. Check if connection pool settings are appropriate
3. Monitor database statistics in performance status

## Support

For issues or questions about performance optimization:
1. Check the performance monitoring endpoints
2. Review the configuration with `GET /performance/config`
3. Use the automatic optimization script for quick fixes
