# 🚀 GuzoSync Deployment Guide

Complete guide for deploying GuzoSync with full route geometry initialization.

## 📋 Prerequisites

### 1. Environment Variables

Ensure these are set in your `.env` file or environment:

```bash
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=guzosync

# Mapbox (Required for route geometry)
MAPBOX_ACCESS_TOKEN=pk.your_mapbox_token_here

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379
```

### 2. Dependencies

```bash
pip install -r requirements.txt
```

### 3. Services Running

- ✅ MongoDB server
- ✅ Redis server (optional but recommended)

## 🚀 Deployment Commands

### Option 1: Complete Fresh Deployment

```bash
# Complete initialization: seeding + route geometry
python scripts/deploy_initialize.py --full
```

### Option 2: Routes Only (if database already seeded)

```bash
# Only populate route geometry (if you already have data)
python scripts/deploy_initialize.py --routes-only
```

### Option 3: Check Status

```bash
# Check current deployment status
python scripts/deploy_initialize.py --check
```

## 📊 What Each Command Does

### `--full` (Recommended for new deployments)

1. ✅ **Database Connection Check**
2. ✅ **Mapbox Token Validation**
3. 🌱 **Database Seeding** (`init_db_complete.py`)
   - Creates routes, bus stops, buses
   - Creates users (admin, drivers, passengers)
   - Imports real Addis Ababa transit data
4. 🗺️ **Route Geometry Population**
   - Calls Mapbox API for all routes
   - Caches geometry permanently in database
   - Realistic distances and road paths
5. ✅ **Final Validation**

### `--routes-only` (For existing databases)

1. ✅ **Prerequisites Check**
2. 🗺️ **Route Geometry Population Only**
3. ✅ **Validation**

## ⏱️ Expected Timeline

| Operation                   | Time              | API Calls |
| --------------------------- | ----------------- | --------- |
| Database Seeding            | 2-5 minutes       | 0         |
| Route Geometry (198 routes) | 15-25 minutes     | 198       |
| **Total**                   | **20-30 minutes** | **198**   |

## 💰 Mapbox Token Usage

- **One-time cost**: 198 API calls for all routes
- **Future usage**: 0 API calls (uses cached data)
- **Free tier**: 100,000 requests/month (plenty for this)

## 🔍 Monitoring Progress

The script provides detailed logging:

```bash
# Watch the log file in real-time
tail -f deployment_initialization.log
```

Example output:

```
2025-06-12 11:15:26 | INFO | 🚀 Starting FULL deployment initialization
2025-06-12 11:15:26 | INFO | ✅ Database connection successful
2025-06-12 11:15:26 | INFO | ✅ Mapbox access token configured
2025-06-12 11:15:30 | INFO | ✅ Database seeding completed successfully
2025-06-12 11:15:35 | INFO | 🗺️ Starting route geometry population...
2025-06-12 11:25:45 | INFO | ✅ Route geometry population completed successfully
2025-06-12 11:25:46 | INFO | 🎉 DEPLOYMENT INITIALIZATION COMPLETE!
```

## 🎯 Success Indicators

After successful deployment, you should see:

```
📊 Deployment Status:
   🚌 Routes: 198
   🚏 Bus Stops: 1340
   🚐 Buses: 18
   👥 Users: 25
   🗺️ Routes with Mapbox geometry: 198/198
   📈 Geometry completion: 100.0%
🎉 Deployment fully initialized and ready!
```

## 🚨 Troubleshooting

### Common Issues:

#### 1. Mapbox Token Error

```bash
❌ MAPBOX_ACCESS_TOKEN not configured
```

**Solution**: Add your Mapbox token to `.env` file

#### 2. Database Connection Failed

```bash
❌ Database connection failed
```

**Solution**: Ensure MongoDB is running and URL is correct

#### 3. Route Population Timeout

```bash
❌ Route geometry population timed out (30 minutes)
```

**Solution**: Run `--routes-only` to retry just the geometry population

#### 4. Partial Completion

```bash
⚠️ 50 routes still need geometry
```

**Solution**: Run `--routes-only` to complete remaining routes

## 🔄 Re-running Safely

All scripts are **idempotent** - safe to run multiple times:

- ✅ Database seeding skips existing data
- ✅ Route geometry uses cached data when available
- ✅ No duplicate data creation

## 🚌 After Deployment

Once initialization is complete, you can:

1. **Start the API server**:

   ```bash
   uvicorn main:app --reload
   ```

2. **Start bus simulation**:

   ```bash
   python scripts/simulation/start_simulation.py
   ```

3. **Access the API**:
   - Swagger UI: `http://localhost:8000/docs`
   - Routes API: `http://localhost:8000/api/routes`

## 📈 Production Considerations

### For Production Deployment:

1. **Environment Variables**: Use proper production values
2. **Database**: Use MongoDB Atlas or dedicated server
3. **Redis**: Use Redis Cloud or dedicated instance
4. **Monitoring**: Set up logging and monitoring
5. **Backup**: Regular database backups
6. **Security**: Proper authentication and HTTPS

### Scaling:

- **Route geometry is cached permanently** - no ongoing API costs
- **Bus simulation scales** with available server resources
- **WebSocket connections** scale with concurrent users

## 🎉 You're Ready!

After successful deployment, your GuzoSync instance will have:

- ✅ **198 routes** with real road geometry
- ✅ **1,340 bus stops** across Addis Ababa
- ✅ **18 buses** ready for simulation
- ✅ **Real-time tracking** capabilities
- ✅ **Zero ongoing API costs** for route data

Your deployment is production-ready! 🚀
