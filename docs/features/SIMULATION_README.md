# GuzoSync Bus Route Simulation System

This comprehensive bus simulation system simulates realistic bus movement along assigned routes in the GuzoSync backend system. It provides real-time location updates via WebSocket and integrates seamlessly with the existing infrastructure.

## 🚀 Features

- **Realistic Bus Movement**: Simulates buses moving along their assigned routes with realistic speeds, acceleration, and traffic conditions
- **Route Following**: Buses follow waypoints generated from bus stops and route geometry
- **Bus Stop Behavior**: Buses stop at bus stops for realistic durations (30-120 seconds)
- **Traffic Simulation**: Random traffic delays and speed variations
- **Real-time Updates**: Location updates broadcast via existing WebSocket infrastructure
- **Circular Routes**: Buses continuously loop on their routes for ongoing simulation
- **Performance Optimized**: Configurable update intervals and bus limits
- **Database Integration**: Works with existing MongoDB collections and data

## 📁 File Structure

```
simulation/
├── __init__.py                 # Package initialization
├── bus_simulator.py           # Main simulation engine
├── movement_calculator.py     # Movement physics and calculations
└── route_path_generator.py    # Route waypoint generation

start_simulation.py            # Main simulation startup script
monitor_simulation.py          # Real-time monitoring tool
start_bus_simulation.bat       # Windows startup script
start_bus_simulation.sh        # Linux/Mac startup script
SIMULATION_README.md          # This documentation
```

## 🛠️ Installation & Setup

### Prerequisites

1. **Database Setup**: Ensure MongoDB is running and the GuzoSync database is seeded
2. **Python Environment**: Python 3.8+ with virtual environment
3. **Dependencies**: All requirements from `requirements.txt` installed

### Quick Start

#### Windows

```bash
# Run the batch file (handles everything automatically)
start_bus_simulation.bat
```

#### Linux/Mac

```bash
# Make script executable and run
chmod +x start_bus_simulation.sh
./start_bus_simulation.sh
```

#### Manual Start

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate.bat  # Windows

# Start simulation with seeding and route assignment
python scripts/simulation/start_simulation.py --seed-first --assign-routes --interval 3
```

## 🎮 Usage

### Basic Commands

```bash
# Start simulation with default settings (5-second updates)
python scripts/simulation/start_simulation.py

# Start with faster updates (3-second intervals)
python scripts/simulation/start_simulation.py --interval 3

# Limit number of buses for performance
python scripts/simulation/start_simulation.py --max-buses 20

# Seed database first (if empty)
python scripts/simulation/start_simulation.py --seed-first

# Assign routes to buses without assignments
python scripts/simulation/start_simulation.py --assign-routes

# Combine options
python scripts/simulation/start_simulation.py --seed-first --assign-routes --interval 2 --max-buses 30
```

### Monitoring

```bash
# Start real-time monitoring dashboard
python monitor_simulation.py
```

The monitor shows:

- Total buses, routes, and stops
- Number of actively moving buses
- Recent bus activity with locations and speeds
- Simulation health status

## ⚙️ Configuration

### Simulation Parameters

Edit `simulation/bus_simulator.py` to adjust:

```python
class BusSimulator:
    def __init__(self, db, update_interval=5.0):
        self.update_interval = update_interval  # Update frequency
        self.max_buses_to_simulate = 50        # Performance limit
        self.route_completion_behavior = 'loop' # 'loop' or 'reverse'
```

### Movement Parameters

Edit `simulation/movement_calculator.py`:

```python
class MovementCalculator:
    def __init__(self):
        self.min_speed = 5.0      # Minimum speed (km/h)
        self.max_speed = 60.0     # Maximum speed (km/h)
        self.average_speed = 25.0 # Average city speed (km/h)
        self.stop_duration_min = 30   # Min stop time (seconds)
        self.stop_duration_max = 120  # Max stop time (seconds)
        self.traffic_variation = 0.3  # 30% speed variation
```

### Route Generation

Edit `simulation/route_path_generator.py`:

```python
class RoutePathGenerator:
    def __init__(self):
        self.waypoint_density = 0.5   # km between waypoints
        self.path_variation = 0.001   # Path randomization
```

## 🔧 How It Works

### 1. Initialization

- Loads operational buses with assigned routes from database
- Generates waypoints for each route using bus stops
- Creates circular routes for continuous simulation
- Initializes bus states with current or starting positions

### 2. Simulation Loop

- Updates all active buses every `update_interval` seconds
- Calculates realistic movement based on physics
- Handles bus stops with appropriate dwell times
- Applies traffic delays and speed variations
- Broadcasts location updates via WebSocket

### 3. Movement Calculation

- Uses Haversine formula for accurate distance calculations
- Calculates bearing/heading between waypoints
- Applies realistic acceleration and speed limits
- Simulates traffic conditions and delays

### 4. Route Following

- Buses follow generated waypoints in sequence
- Stop at bus stops for realistic durations
- Continue to next waypoint after stop completion
- Loop back to start when route is completed

## 📊 Database Requirements

The simulation requires these collections with data:

### Buses Collection

```javascript
{
  id: "uuid",
  license_plate: "AA-1234",
  bus_status: "OPERATIONAL",
  assigned_route_id: "route-uuid",
  current_location: {
    latitude: 9.0123,
    longitude: 38.7456
  },
  // ... other fields
}
```

### Routes Collection

```javascript
{
  id: "uuid",
  name: "Route Name",
  stop_ids: ["stop1-uuid", "stop2-uuid", ...],
  is_active: true,
  route_geometry: { /* Optional GeoJSON */ },
  // ... other fields
}
```

### Bus Stops Collection

```javascript
{
  id: "uuid",
  name: "Stop Name",
  location: {
    latitude: 9.0123,
    longitude: 38.7456
  },
  is_active: true,
  // ... other fields
}
```

## 🌐 WebSocket Integration

The simulation integrates with the existing WebSocket system:

- Uses `core.realtime.bus_tracking.bus_tracking_service`
- Broadcasts to `bus_tracking:{bus_id}` rooms
- Broadcasts to `route_tracking:{route_id}` rooms
- Sends location updates to all subscribed clients

### WebSocket Message Format

```javascript
{
  type: "bus_location_update",
  bus_id: "uuid",
  location: {
    latitude: 9.0123,
    longitude: 38.7456
  },
  heading: 45.5,
  speed: 25.3,
  timestamp: "2024-01-01T12:00:00Z"
}
```

## 🚨 Troubleshooting

### Common Issues

1. **No buses moving**

   - Check if buses have assigned routes: `--assign-routes`
   - Verify database has operational buses
   - Check MongoDB connection

2. **Simulation not starting**

   - Ensure database is seeded: `--seed-first`
   - Check .env file configuration
   - Verify virtual environment is activated

3. **Performance issues**

   - Reduce update interval: `--interval 10`
   - Limit buses: `--max-buses 10`
   - Check system resources

4. **WebSocket not working**
   - Ensure FastAPI server is running
   - Check WebSocket manager initialization
   - Verify client connections

### Logs

Check simulation logs:

- Console output for real-time status
- `logs/simulation.log` for detailed logging
- `logs/guzosync.log` for application logs

## 🔮 Future Enhancements

- **Route Optimization**: Dynamic route adjustments based on traffic
- **Passenger Simulation**: Simulate passenger boarding/alighting
- **Weather Effects**: Speed adjustments based on weather conditions
- **Breakdown Simulation**: Random bus breakdowns and recovery
- **Schedule Adherence**: Track on-time performance
- **Multi-Route Buses**: Buses that switch between routes
- **Real-time Traffic**: Integration with traffic APIs

## 📝 Contributing

To extend the simulation:

1. **Add new movement behaviors** in `movement_calculator.py`
2. **Enhance route generation** in `route_path_generator.py`
3. **Extend bus states** in `bus_simulator.py`
4. **Add monitoring features** in `monitor_simulation.py`

## 📄 License

This simulation system is part of the GuzoSync project and follows the same licensing terms.
