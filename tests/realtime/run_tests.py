"""
Test runner script for Socket.IO real-time functionality tests
"""
import pytest
import sys
import os
from pathlib import Path

def main():
    """Run all Socket.IO real-time tests with comprehensive coverage"""

    # Add the project root to the Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # Test configuration
    test_args = [
        "tests/realtime/",  # Run all real-time tests
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker checking
        "--disable-warnings",  # Disable warnings for cleaner output
        "-x",  # Stop on first failure
        "--asyncio-mode=auto",  # Auto-detect asyncio tests
    ]

    # Add coverage if coverage is installed
    try:
        test_args.extend([
            "--cov=core.realtime",
            "--cov=core.socketio_manager",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/realtime",
            "--cov-fail-under=80"
        ])
        print("✅ Running Socket.IO tests with coverage reporting")
    except ImportError:
        print("⚠️  Coverage not available, running tests without coverage")

    print("🚀 Running Socket.IO real-time functionality tests...")
    print("=" * 60)
    print("🧪 Testing Features:")
    print("   💬 Basic messaging between queue regulators/bus drivers ↔ control staff/admin")
    print("   🔔 Notification system with proximity alerts")
    print("   🚌 Real-time bus tracking with Mapbox integration")
    print("   🔗 Integration workflows combining all features")
    print("=" * 60)

    # Run the tests
    exit_code = pytest.main(test_args)

    print("=" * 60)
    if exit_code == 0:
        print("✅ All Socket.IO tests passed!")
        print("🎉 Socket.IO real-time features are working correctly!")
        if 'coverage' in locals():
            print("📊 Coverage report generated in htmlcov/realtime/")
    else:
        print("❌ Some Socket.IO tests failed")
        sys.exit(exit_code)

def run_specific_test(test_name):
    """Run a specific test file"""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    test_file = f"tests/realtime/test_socketio_{test_name}.py"

    if os.path.exists(test_file):
        print(f"🧪 Running {test_file}...")
        exit_code = pytest.main([
            test_file,
            "-v",
            "--tb=long",
            "--asyncio-mode=auto"
        ])
        return exit_code == 0
    else:
        print(f"❌ Test file {test_file} not found!")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
        sys.exit(0 if success else 1)
    else:
        # Run all tests
        main()
