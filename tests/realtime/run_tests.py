"""
Test runner script for real-time functionality tests
"""
import pytest
import sys
import os
from pathlib import Path

def main():
    """Run all real-time tests with comprehensive coverage"""
    
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
            "--cov=core.websocket_manager", 
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/realtime",
            "--cov-fail-under=85"
        ])
        print("✅ Running tests with coverage reporting")
    except ImportError:
        print("⚠️  Coverage not available, running tests without coverage")
    
    print("🚀 Running real-time functionality tests...")
    print("=" * 60)
    
    # Run the tests
    exit_code = pytest.main(test_args)
    
    print("=" * 60)
    if exit_code == 0:
        print("✅ All real-time tests passed!")
        if 'coverage' in locals():
            print("📊 Coverage report generated in htmlcov/realtime/")
    else:
        print("❌ Some tests failed")
        sys.exit(exit_code)

if __name__ == "__main__":
    main()
