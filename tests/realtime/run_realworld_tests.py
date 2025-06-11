"""
Real-world Socket.IO test runner
Tests actual Socket.IO functionality with real server and database
"""
import subprocess
import sys
import os
import time
import asyncio
import httpx
import signal
from pathlib import Path


class ServerManager:
    """Manages the FastAPI server for testing"""
    
    def __init__(self):
        self.server_process = None
        self.server_url = "http://localhost:8000"
        
    async def start_server(self):
        """Start the FastAPI server"""
        print("🚀 Starting FastAPI server for real-world tests...")
        
        # Change to project root
        project_root = Path(__file__).parent.parent.parent
        os.chdir(project_root)
        
        # Start server in background
        self.server_process = subprocess.Popen([
            sys.executable, "main.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        await self._wait_for_server()
        
    async def _wait_for_server(self, timeout=30):
        """Wait for server to be ready"""
        print("⏳ Waiting for server to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.server_url}/health")
                    if response.status_code == 200:
                        print("✅ Server is ready!")
                        return
            except:
                pass
            
            await asyncio.sleep(1)
        
        raise Exception(f"Server failed to start within {timeout} seconds")
    
    def stop_server(self):
        """Stop the FastAPI server"""
        if self.server_process:
            print("🛑 Stopping FastAPI server...")
            
            # Try graceful shutdown first
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                self.server_process.kill()
                self.server_process.wait()
            
            print("✅ Server stopped")


async def run_realworld_tests():
    """Run real-world Socket.IO tests"""
    server_manager = ServerManager()
    
    try:
        # Start server
        await server_manager.start_server()
        
        # Change to project root for tests
        project_root = Path(__file__).parent.parent.parent
        os.chdir(project_root)
        
        print("🧪 Running Real-World Socket.IO Tests...")
        print("=" * 60)
        print("🌐 Testing Features:")
        print("   🔐 Real authentication with JWT tokens")
        print("   💬 Real messaging between users")
        print("   🚌 Real bus location updates and tracking")
        print("   🔔 Real proximity alerts")
        print("   🚨 Real emergency alert system")
        print("   📢 Real admin broadcasts")
        print("   💾 Real database operations")
        print("=" * 60)
        
        # Run the real-world tests
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/realtime/test_socketio_realworld.py",
            "-v",
            "--tb=short",
            "--asyncio-mode=auto",
            "--disable-warnings"
        ], capture_output=True, text=True)
        
        print("\n" + "=" * 60)
        print("📊 Real-World Test Results:")
        print("=" * 60)
        
        if result.returncode == 0:
            print("🎉 ALL REAL-WORLD TESTS PASSED!")
            print("\n✅ Verified Features:")
            print("   🔐 Socket.IO authentication works")
            print("   💬 Real-time messaging works")
            print("   🚌 Bus tracking works")
            print("   🔔 Proximity alerts work")
            print("   🚨 Emergency alerts work")
            print("   📢 Admin broadcasts work")
            print("   💾 Database integration works")
            print("\n🚀 Socket.IO system is production-ready!")
        else:
            print("❌ SOME REAL-WORLD TESTS FAILED")
            print("\nTest Output:")
            print(result.stdout)
            if result.stderr:
                print("\nErrors:")
                print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running real-world tests: {e}")
        return False
        
    finally:
        # Always stop the server
        server_manager.stop_server()


def run_specific_realworld_test(test_name):
    """Run a specific real-world test"""
    async def _run():
        server_manager = ServerManager()
        
        try:
            await server_manager.start_server()
            
            project_root = Path(__file__).parent.parent.parent
            os.chdir(project_root)
            
            test_file = "tests/realtime/test_socketio_realworld.py"
            test_method = f"TestRealWorldSocketIO::test_{test_name}"
            
            print(f"🧪 Running real-world test: {test_method}")
            
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                f"{test_file}::{test_method}",
                "-v",
                "--tb=long",
                "--asyncio-mode=auto",
                "-s"  # Don't capture output for debugging
            ])
            
            return result.returncode == 0
            
        finally:
            server_manager.stop_server()
    
    return asyncio.run(_run())


def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ["socketio", "httpx", "pytest-asyncio"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True


def main():
    """Main entry point"""
    if not check_dependencies():
        sys.exit(1)
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_realworld_test(test_name)
        sys.exit(0 if success else 1)
    else:
        # Run all real-world tests
        success = asyncio.run(run_realworld_tests())
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
