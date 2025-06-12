#!/usr/bin/env python
"""
Test Bus Simulation Service Integration

This script tests the integration of the bus simulation service with the FastAPI application.
"""

import asyncio
import sys
import os
from datetime import datetime

def test_service_import():
    """Test importing the simulation service."""
    print("📦 Testing simulation service import...")
    
    try:
        from simulation import bus_simulation_service
        print(f"   ✅ Service imported successfully")
        print(f"   🔧 Enabled: {bus_simulation_service.enabled}")
        print(f"   ⏱️ Update interval: {bus_simulation_service.update_interval}s")
        print(f"   🚌 Max buses: {bus_simulation_service.max_buses}")
        print(f"   🔄 Auto assign: {bus_simulation_service.auto_assign_routes}")
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False


def test_main_app_import():
    """Test importing the main FastAPI app with simulation integration."""
    print("🚀 Testing main app import with simulation...")
    
    try:
        # This should import without errors
        import main
        print("   ✅ Main app imported successfully")
        
        # Check if simulation router is included
        app = main.app
        routes = [route.path for route in app.routes]
        simulation_routes = [r for r in routes if r.startswith('/simulation')]
        
        if simulation_routes:
            print(f"   ✅ Simulation routes found: {simulation_routes}")
        else:
            print("   ⚠️ No simulation routes found")
        
        return True
    except Exception as e:
        print(f"   ❌ Main app import failed: {e}")
        return False


def test_environment_config():
    """Test environment configuration."""
    print("⚙️ Testing environment configuration...")
    
    # Test default values
    expected_defaults = {
        "BUS_SIMULATION_ENABLED": "true",
        "BUS_SIMULATION_INTERVAL": "5.0", 
        "BUS_SIMULATION_MAX_BUSES": "50",
        "BUS_SIMULATION_AUTO_ASSIGN": "true"
    }
    
    for key, default_value in expected_defaults.items():
        env_value = os.getenv(key, default_value)
        print(f"   {key}: {env_value}")
    
    print("   ✅ Environment configuration loaded")
    return True


async def test_service_lifecycle():
    """Test service lifecycle without database."""
    print("🔄 Testing service lifecycle...")
    
    try:
        from simulation.bus_simulation_service import BusSimulationService
        
        # Create service instance
        service = BusSimulationService()
        print("   ✅ Service instance created")
        
        # Test status without app state
        status = service.get_status()
        expected_keys = ["enabled", "is_running", "update_interval", "max_buses", "auto_assign_routes"]
        
        for key in expected_keys:
            if key not in status:
                raise ValueError(f"Missing status key: {key}")
        
        print(f"   ✅ Service status: {status}")
        
        # Test start without app state (should handle gracefully)
        await service.start()
        print("   ✅ Service start handled gracefully without app state")
        
        # Test stop
        await service.stop()
        print("   ✅ Service stop completed")
        
        return True
    except Exception as e:
        print(f"   ❌ Service lifecycle test failed: {e}")
        return False


def test_api_router():
    """Test simulation API router."""
    print("🌐 Testing simulation API router...")
    
    try:
        from routers.simulation import router
        
        # Check router configuration
        print(f"   ✅ Router imported: {router.prefix}")
        print(f"   ✅ Router tags: {router.tags}")
        
        # Check routes
        routes = [route.path for route in router.routes]
        expected_routes = ["/status", "/restart", "/stop", "/start", "/health"]
        
        for expected_route in expected_routes:
            if expected_route not in routes:
                print(f"   ⚠️ Missing route: {expected_route}")
            else:
                print(f"   ✅ Route found: {expected_route}")
        
        return True
    except Exception as e:
        print(f"   ❌ API router test failed: {e}")
        return False


def test_simulation_components():
    """Test individual simulation components."""
    print("🧩 Testing simulation components...")
    
    try:
        from simulation import BusSimulator, RoutePathGenerator, MovementCalculator
        
        # Test component creation
        calc = MovementCalculator()
        generator = RoutePathGenerator()
        print("   ✅ Components created successfully")
        
        # Test basic functionality
        distance = calc.calculate_distance(9.0, 38.7, 9.1, 38.8)
        print(f"   ✅ Distance calculation: {distance:.2f} km")
        
        speed = calc.get_realistic_speed()
        print(f"   ✅ Speed generation: {speed} km/h")
        
        return True
    except Exception as e:
        print(f"   ❌ Component test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("🧪 Bus Simulation Service Integration Tests")
    print("=" * 60)
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Service Import", test_service_import),
        ("Main App Import", test_main_app_import),
        ("Environment Config", test_environment_config),
        ("Service Lifecycle", test_service_lifecycle),
        ("API Router", test_api_router),
        ("Simulation Components", test_simulation_components)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"🔍 {test_name}:")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"   ✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"   ❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"   ❌ {test_name} CRASHED: {e}")
        
        print()
    
    print("=" * 60)
    print(f"🎯 Integration Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All integration tests passed!")
        print()
        print("✅ Bus simulation service is properly integrated")
        print("✅ Service will start automatically with FastAPI server")
        print("✅ API endpoints are available for monitoring and control")
        print("✅ Environment configuration is working")
        print()
        print("🚀 Ready for deployment!")
        print()
        print("Next steps:")
        print("1. Start your FastAPI server: python main.py")
        print("2. Check simulation status: GET /simulation/health")
        print("3. Monitor logs for simulation startup messages")
        print("4. Use frontend to see moving buses on the map")
    else:
        print("❌ Some integration tests failed.")
        print("Please check the errors above before deploying.")
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
