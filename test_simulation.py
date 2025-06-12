#!/usr/bin/env python
"""
Test script for the bus simulation system.
This script tests the simulation components without requiring a full database setup.
"""

import asyncio
import sys
from datetime import datetime

def test_movement_calculator():
    """Test the movement calculator."""
    print("🧮 Testing MovementCalculator...")
    
    try:
        from simulation.movement_calculator import MovementCalculator
        
        calc = MovementCalculator()
        
        # Test distance calculation
        distance = calc.calculate_distance(9.0, 38.7, 9.1, 38.8)
        print(f"   Distance calculation: {distance:.2f} km")
        
        # Test bearing calculation
        bearing = calc.calculate_bearing(9.0, 38.7, 9.1, 38.8)
        print(f"   Bearing calculation: {bearing:.1f} degrees")
        
        # Test intermediate point
        lat, lon = calc.calculate_intermediate_point(9.0, 38.7, 9.1, 38.8, 0.5)
        print(f"   Intermediate point: ({lat:.4f}, {lon:.4f})")
        
        # Test speed generation
        speed = calc.get_realistic_speed()
        print(f"   Realistic speed: {speed} km/h")
        
        # Test stop duration
        duration = calc.calculate_stop_duration()
        print(f"   Stop duration: {duration} seconds")
        
        # Test next position calculation
        new_lat, new_lon, remaining = calc.calculate_next_position(
            9.0, 38.7, 9.1, 38.8, 30.0, 60.0  # 30 km/h for 60 seconds
        )
        print(f"   Next position: ({new_lat:.4f}, {new_lon:.4f}), remaining: {remaining:.2f} km")
        
        print("   ✅ MovementCalculator tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ MovementCalculator test failed: {e}")
        return False


def test_route_path_generator():
    """Test the route path generator."""
    print("🛣️ Testing RoutePathGenerator...")
    
    try:
        from simulation.route_path_generator import RoutePathGenerator
        
        generator = RoutePathGenerator()
        
        # Create mock bus stops
        bus_stops = [
            {
                'id': 'stop1',
                'name': 'Stop 1',
                'location': {'latitude': 9.0, 'longitude': 38.7}
            },
            {
                'id': 'stop2', 
                'name': 'Stop 2',
                'location': {'latitude': 9.05, 'longitude': 38.75}
            },
            {
                'id': 'stop3',
                'name': 'Stop 3', 
                'location': {'latitude': 9.1, 'longitude': 38.8}
            }
        ]
        
        # Generate route path
        waypoints = generator.generate_route_path(bus_stops)
        print(f"   Generated {len(waypoints)} waypoints")
        
        # Test circular route
        circular_waypoints = generator.create_circular_route(waypoints)
        print(f"   Circular route has {len(circular_waypoints)} waypoints")
        
        # Verify waypoint structure
        if waypoints:
            first_waypoint = waypoints[0]
            required_fields = ['latitude', 'longitude', 'type', 'sequence', 'is_bus_stop']
            for field in required_fields:
                if field not in first_waypoint:
                    raise ValueError(f"Missing field: {field}")
            
            print(f"   First waypoint: {first_waypoint['type']} at ({first_waypoint['latitude']:.4f}, {first_waypoint['longitude']:.4f})")
        
        print("   ✅ RoutePathGenerator tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ RoutePathGenerator test failed: {e}")
        return False


def test_bus_state():
    """Test the BusState class."""
    print("🚌 Testing BusState...")
    
    try:
        from simulation.bus_simulator import BusState
        
        # Create mock bus data
        bus_data = {
            'id': 'bus123',
            'license_plate': 'AA-1234',
            'assigned_route_id': 'route123',
            'current_location': {
                'latitude': 9.0,
                'longitude': 38.7
            },
            'speed': 25.0,
            'heading': 45.0,
            'bus_status': 'OPERATIONAL'
        }
        
        # Create bus state
        bus_state = BusState(bus_data)
        
        # Verify initialization
        assert bus_state.bus_id == 'bus123'
        assert bus_state.license_plate == 'AA-1234'
        assert bus_state.route_id == 'route123'
        assert bus_state.latitude == 9.0
        assert bus_state.longitude == 38.7
        assert bus_state.speed == 25.0
        assert bus_state.heading == 45.0
        assert bus_state.is_active == True
        
        print(f"   Bus state initialized: {bus_state.license_plate} at ({bus_state.latitude}, {bus_state.longitude})")
        print("   ✅ BusState tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ BusState test failed: {e}")
        return False


def test_imports():
    """Test all simulation imports."""
    print("📦 Testing simulation imports...")
    
    try:
        from simulation import BusSimulator, RoutePathGenerator, MovementCalculator
        print("   ✅ Main imports successful")
        
        from simulation.bus_simulator import BusState
        print("   ✅ BusState import successful")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import test failed: {e}")
        return False


async def test_simulation_initialization():
    """Test simulation initialization without database."""
    print("🚀 Testing simulation initialization...")
    
    try:
        from simulation.bus_simulator import BusSimulator
        
        # Create a mock database object
        class MockDB:
            def __init__(self):
                self.buses = MockCollection([])
                self.routes = MockCollection([])
                self.bus_stops = MockCollection([])
        
        class MockCollection:
            def __init__(self, data):
                self.data = data
            
            def find(self, query=None):
                return MockCursor(self.data)
            
            def find_one(self, query=None):
                return asyncio.create_task(self._find_one())
            
            async def _find_one(self):
                return self.data[0] if self.data else None
        
        class MockCursor:
            def __init__(self, data):
                self.data = data
            
            def limit(self, count):
                return self
            
            async def to_list(self, length=None):
                return self.data
        
        # Create simulator with mock database
        mock_db = MockDB()
        simulator = BusSimulator(mock_db, update_interval=1.0)
        
        # Test configuration
        assert simulator.update_interval == 1.0
        assert simulator.max_buses_to_simulate == 50
        assert simulator.is_running == False
        
        # Test status
        status = simulator.get_simulation_status()
        expected_keys = ['is_running', 'total_buses', 'active_buses', 'update_interval', 'routes_loaded']
        for key in expected_keys:
            if key not in status:
                raise ValueError(f"Missing status key: {key}")
        
        print(f"   Simulator status: {status}")
        print("   ✅ Simulation initialization tests passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Simulation initialization test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Running Bus Simulation Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_movement_calculator,
        test_route_path_generator,
        test_bus_state,
        test_simulation_initialization
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Test {test.__name__} crashed: {e}")
            failed += 1
        
        print()
    
    print("=" * 50)
    print(f"🎯 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The simulation system is ready to use.")
        print()
        print("Next steps:")
        print("1. Ensure your database is seeded with buses, routes, and stops")
        print("2. Run: python start_simulation.py --seed-first --assign-routes")
        print("3. Monitor with: python monitor_simulation.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        sys.exit(1)
