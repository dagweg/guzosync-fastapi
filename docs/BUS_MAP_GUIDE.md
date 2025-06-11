# 🗺️ GuzoSync Bus Map Guide

## Overview

The GuzoSync Bus Map provides real-time visualization of buses, bus stops, and routes with interactive features for comprehensive fleet management.

## Features

### 🚌 Bus Visualization
- **Real-time bus locations** with live updates via WebSocket
- **Color-coded status indicators**:
  - 🟢 Green: Operational
  - 🟡 Yellow: Idle
  - 🔴 Red: Maintenance/Breakdown
- **Bus information popups** with details like license plate, capacity, and status
- **Live location updates** with timestamps and speed information

### 🚏 Bus Stop Display
- **All bus stops** shown as green markers
- **Stop information** including name, capacity, and status
- **Interactive popups** with stop details

### 🛣️ Route Visualization
- **Dynamic route shapes** loaded from Mapbox
- **Route highlighting** when a bus is selected
- **Start and end destination markers**
- **Route information** including distance and duration

### 📱 Interactive Features
- **Click any bus** to see detailed information and its route
- **Bus details panel** showing:
  - Basic bus information (license plate, type, capacity, status)
  - Assigned driver details
  - Current route information with start/end destinations
  - Current trip status and timing
  - Real-time location data
- **Route visualization** automatically displayed when bus is selected
- **Admin location updates** (click map to update bus location)

## Quick Start

### 1. Setup Environment
```bash
# Copy environment template
cp client/.env.local.example client/.env.local

# Add your Mapbox token to client/.env.local
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
```

### 2. Start the Application
**Windows:**
```bash
start_map_demo.bat
```

**Linux/Mac:**
```bash
chmod +x start_map_demo.sh
./start_map_demo.sh
```

### 3. Access the Map
1. Open http://localhost:3000
2. Login with admin credentials:
   - Email: `test_control_admin@guzosync.com`
   - Password: `Test123!`
3. Click on any bus to see its route and details!

## API Endpoints Used

### Bus Endpoints
- `GET /api/buses` - Get all buses
- `GET /api/buses/{bus_id}/details` - Get comprehensive bus details
- `GET /api/buses/{bus_id}/eta` - Get bus ETA to stops
- `PUT /api/buses/{bus_id}` - Update bus location (admin only)

### Route Endpoints
- `GET /api/routes` - Get all routes
- `GET /api/routes/{route_id}` - Get route details
- `GET /api/routes/{route_id}/shape` - Get route geometry

### Bus Stop Endpoints
- `GET /api/buses/stops` - Get all bus stops
- `GET /api/buses/stops/{stop_id}` - Get stop details

## Real-time Features

### WebSocket Integration
- **Live bus location updates** via WebSocket connections
- **ETA updates** for buses approaching stops
- **Automatic map updates** when data changes
- **Connection status indicator** in the header

### Data Refresh
- **Bus locations** update in real-time via WebSocket
- **ETA calculations** refresh every 2 minutes
- **Route shapes** cached for performance
- **Bus details** fetched on-demand when clicked

## Map Controls

### Navigation
- **Zoom in/out** using mouse wheel or controls
- **Pan** by dragging the map
- **Fullscreen mode** available
- **Navigation controls** in top-right corner

### Legend
- **Bus status colors** explained
- **Bus stop markers** identified
- **Route line styles** differentiated
- **Interactive elements** highlighted

## Troubleshooting

### Map Not Loading
1. **Check Mapbox token**: Ensure `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` is set
2. **Get free token**: Visit https://mapbox.com to get a free token
3. **Check console**: Look for JavaScript errors in browser console

### No Buses Showing
1. **Check backend**: Ensure FastAPI server is running on port 8000
2. **Check data**: Verify database has bus data (run seeding scripts)
3. **Check authentication**: Ensure you're logged in with valid credentials

### Routes Not Displaying
1. **Check route data**: Ensure routes exist in database
2. **Check Mapbox API**: Verify route shape generation is working
3. **Check network**: Ensure API calls are successful

## Advanced Features

### Admin Functions
- **Update bus locations** by clicking on the map (admin only)
- **View comprehensive bus details** including driver and trip information
- **Real-time fleet monitoring** with status indicators

### Performance Optimizations
- **Route shape caching** to reduce API calls
- **Efficient marker management** for smooth performance
- **Lazy loading** of detailed information
- **WebSocket connection pooling** for real-time updates

## Development

### Adding New Features
1. **Bus details**: Extend the `BusDetailedResponse` schema
2. **Map layers**: Add new Mapbox layers in the Map component
3. **Real-time data**: Add new WebSocket message types
4. **API endpoints**: Create new endpoints in FastAPI backend

### Customization
- **Map style**: Change Mapbox style in Map component
- **Colors**: Modify bus status colors in `getBusStatusColor` function
- **Layout**: Adjust panel sizes and positions
- **Data refresh**: Modify refresh intervals for different data types

## Support

For issues or questions:
1. Check the browser console for errors
2. Verify API endpoints are responding
3. Ensure WebSocket connection is established
4. Check database has seeded data

The map provides a comprehensive view of your bus fleet with real-time updates and detailed information at your fingertips!
