# Mapbox Integration for GuzoSync

This document describes the comprehensive Mapbox integration implemented for GuzoSync, providing real-time bus tracking, route shapes, ETA calculations, and performance optimizations.

## Features Implemented

### 1. Route Shape Data
- **GeoJSON LineString Storage**: Routes now store shape data as GeoJSON LineString objects
- **Mapbox Directions API**: Automatic route shape generation using Mapbox Directions API
- **Caching**: Route shapes are cached in Redis for performance
- **Database Storage**: Route geometry stored in MongoDB with metadata

### 2. ETA Calculation
- **Real-time ETAs**: Calculate estimated time of arrival using Mapbox Directions API
- **Traffic-aware**: Uses Mapbox's traffic-aware routing for accurate estimates
- **Speed-based Adjustments**: Adjusts ETAs based on current bus speed
- **Multiple Stops**: Calculates ETA to all stops on a route

### 3. Performance Optimization
- **Redis Caching**: Route shapes and ETA calculations cached for 1 hour
- **Geospatial Indexing**: MongoDB 2dsphere indexes for efficient location queries
- **Background Tasks**: Scheduled updates for route shapes and ETA broadcasting
- **Optimized Queries**: Compound indexes for bus tracking queries

### 4. Real-time Updates
- **WebSocket Broadcasting**: ETA updates broadcast via Socket.IO
- **Scheduled Tasks**: Background service updates ETAs every 2 minutes
- **Live Location**: Real-time bus location updates with ETA recalculation

## Backend Implementation

### Services

#### MapboxService (`core/services/mapbox_service.py`)
- Handles all Mapbox API interactions
- Manages Redis caching for performance
- Provides route shape generation and ETA calculations
- Includes fallback calculations for offline scenarios

#### RouteService (`core/services/route_service.py`)
- Manages route shape generation and caching
- Calculates bus ETAs to all stops on a route
- Integrates with MapboxService for API calls
- Handles route optimization and updates

#### BackgroundTaskService (`core/services/background_tasks.py`)
- Runs scheduled tasks for route shape updates
- Broadcasts ETA updates every 2 minutes
- Manages performance optimization tasks
- Handles cache cleanup and database indexing

### API Endpoints

#### Route Shape Endpoints
```
GET /api/routes/{route_id}/shape
- Returns route shape as GeoJSON LineString
- Includes distance and duration metadata

POST /api/routes/{route_id}/generate-shape
- Generates/regenerates route shape from bus stops
- Admin only endpoint
```

#### ETA Endpoints
```
GET /api/buses/{bus_id}/eta
- Returns ETA to all stops on assigned route
- Includes traffic-aware calculations
- Real-time speed adjustments
```

### Database Schema Updates

#### Route Model Enhancements
```python
class Route(BaseDBModel):
    # ... existing fields ...
    
    # Mapbox integration fields
    route_geometry: Optional[Dict[str, Any]] = None  # GeoJSON LineString
    route_shape_data: Optional[Dict[str, Any]] = None  # Full Mapbox response
    last_shape_update: Optional[datetime] = None
    shape_cache_key: Optional[str] = None
    geometry_simplified: Optional[Dict[str, Any]] = None
```

## Frontend Implementation

### Enhanced Map Component (`client/src/components/Map.tsx`)
- **Route Shape Visualization**: Displays route shapes as colored lines
- **ETA Display**: Shows ETA information in bus popups
- **Real-time Updates**: Listens for ETA updates via WebSocket
- **Performance Optimized**: Caches route shapes and manages map layers efficiently

### New Features
- Route shape loading and caching
- ETA data fetching and display
- Real-time ETA updates via WebSocket
- Enhanced bus popups with next stop ETA
- Route selection and highlighting
- Toggle controls for route shapes and ETAs

### Demo Page (`client/src/app/mapbox-demo/page.tsx`)
- Complete demonstration of Mapbox integration
- Route selection and shape generation
- Real-time bus tracking with ETAs
- Performance statistics and controls

## Configuration

### Environment Variables
```bash
# Backend (.env)
MAPBOX_ACCESS_TOKEN=your-mapbox-access-token
REDIS_URL=redis://localhost:6379

# Frontend (.env.local)
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=your-mapbox-access-token
```

### Dependencies Added
```bash
# Backend
mapbox==0.9.0
redis==5.0.1
geopy==2.4.1
shapely==2.0.2

# Frontend (already included)
mapbox-gl
```

## Usage

### 1. Setup
1. Get a Mapbox access token from [mapbox.com](https://mapbox.com)
2. Add the token to your environment variables
3. Install Redis for caching
4. Run database migrations to add new route fields

### 2. Generate Route Shapes
```python
# Programmatically
from core.services.route_service import route_service
await route_service.generate_route_shape(route_id, bus_stops, app_state)

# Via API
POST /api/routes/{route_id}/generate-shape
```

### 3. Get ETAs
```python
# Programmatically
from core.services.route_service import route_service
etas = await route_service.calculate_bus_eta_to_stops(bus, route_stops, app_state)

# Via API
GET /api/buses/{bus_id}/eta
```

### 4. Frontend Integration
```tsx
<Map
  buses={buses}
  busStops={busStops}
  routes={routes}
  showRouteShapes={true}
  showETAs={true}
  selectedRoute={selectedRouteId}
  onBusClick={handleBusClick}
/>
```

## Performance Considerations

### Caching Strategy
- **Route Shapes**: Cached for 24 hours in Redis
- **ETAs**: Cached for 5 minutes in Redis
- **Database Queries**: Optimized with geospatial indexes

### Background Tasks
- **Route Shape Updates**: Every 6 hours
- **ETA Broadcasting**: Every 2 minutes
- **Cache Cleanup**: Every hour
- **Index Optimization**: Every 24 hours

### Rate Limiting
- Small delays between API calls to avoid rate limiting
- Batch processing for multiple route updates
- Fallback calculations when API is unavailable

## Monitoring and Debugging

### Logs
- All Mapbox API calls are logged with timing information
- Cache hit/miss ratios are tracked
- Background task execution is monitored

### Error Handling
- Graceful fallback to straight-line distance calculations
- Retry logic for failed API calls
- Comprehensive error logging and reporting

## Future Enhancements

1. **Route Optimization**: Use Mapbox Optimization API for multi-stop routes
2. **Isochrone Analysis**: Show service areas using Mapbox Isochrone API
3. **Traffic Incidents**: Integrate real-time traffic incident data
4. **Predictive ETAs**: Machine learning-based ETA predictions
5. **Mobile Optimization**: Optimize for mobile map performance

## Demo

Visit `/mapbox-demo` in the frontend application to see the full integration in action, including:
- Real-time bus tracking
- Route shape visualization
- ETA calculations and updates
- Performance controls and statistics
