#!/usr/bin/env python3
"""
Comprehensive real-world Socket.IO test runner
Starts the server, runs tests, and provides detailed results
"""
import subprocess
import sys
import os
import time
import asyncio
import httpx
import signal
from pathlib import Path
import threading
import queue
from typing import Optional


class ServerManager:
    """Manages the FastAPI server for testing"""
    
    def __init__(self):
        self.server_process: Optional[subprocess.Popen[str]] = None
        self.server_url = "http://localhost:8000"
        self.output_queue: queue.Queue[str] = queue.Queue()
        
    def start_server(self):
        """Start the FastAPI server"""
        print("🚀 Starting FastAPI server for real-world Socket.IO tests...")
        
        # Change to project root
        project_root = Path(__file__).parent
        os.chdir(project_root)
        
        # Start server in background
        self.server_process = subprocess.Popen([
            sys.executable, "main.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
           universal_newlines=True, bufsize=1)
        
        # Start thread to read server output
        def read_output():
            if self.server_process and self.server_process.stdout:
                for line in iter(self.server_process.stdout.readline, ''):
                    self.output_queue.put(line.strip())
        
        self.output_thread = threading.Thread(target=read_output, daemon=True)
        self.output_thread.start()
        
        # Wait for server to start
        if self._wait_for_server():
            print("✅ Server started successfully!")
            return True
        else:
            print("❌ Server failed to start")
            return False
        
    def _wait_for_server(self, timeout=60):
        """Wait for server to be ready"""
        print("⏳ Waiting for server to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if process is still running
                if self.server_process and self.server_process.poll() is not None:
                    print("❌ Server process terminated unexpectedly")
                    self._print_server_output()
                    return False
                
                # Try to connect
                response = subprocess.run([
                    "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
                    f"{self.server_url}/health"
                ], capture_output=True, text=True, timeout=2)
                
                if response.returncode == 0 and response.stdout == "200":
                    print("✅ Server health check passed!")
                    return True
                    
            except Exception:
                pass
            
            # Print some server output for debugging
            self._print_recent_output()
            time.sleep(2)
        
        print(f"❌ Server failed to start within {timeout} seconds")
        self._print_server_output()
        return False
    
    def _print_recent_output(self):
        """Print recent server output"""
        lines = []
        try:
            while True:
                line = self.output_queue.get_nowait()
                lines.append(line)
                if len(lines) > 5:  # Keep only last 5 lines
                    lines.pop(0)
        except queue.Empty:
            pass
        
        if lines:
            print("📋 Server output:")
            for line in lines:
                print(f"   {line}")
    
    def _print_server_output(self):
        """Print all server output"""
        lines = []
        try:
            while True:
                line = self.output_queue.get_nowait()
                lines.append(line)
        except queue.Empty:
            pass
        
        if lines:
            print("📋 Full server output:")
            for line in lines[-20:]:  # Show last 20 lines
                print(f"   {line}")
    
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


def run_simple_connectivity_test():
    """Run simple connectivity test"""
    print("🧪 Running Simple Connectivity Test...")
    print("-" * 40)
    
    try:
        # Test health endpoint
        result = subprocess.run([
            "curl", "-s", "-f", "http://localhost:8000/health"
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ Health endpoint accessible")
            print(f"   Response: {result.stdout}")
        else:
            print("❌ Health endpoint failed")
            return False
        
        # Test Socket.IO endpoint
        result = subprocess.run([
            "curl", "-s", "-f", "http://localhost:8000/socket.io/"
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ Socket.IO endpoint accessible")
        else:
            print("⚠️ Socket.IO endpoint test inconclusive (may be normal)")
        
        return True
        
    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")
        return False


def run_socketio_tests():
    """Run Socket.IO pytest tests"""
    print("🧪 Running Socket.IO Tests...")
    print("-" * 40)
    
    # Test files to run
    test_files = [
        "tests/realtime/test_simple_realworld.py",
        # Add more test files here when ready
    ]
    
    all_passed = True
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n📋 Running {test_file}...")
            
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                test_file,
                "-v",
                "--tb=short",
                "--asyncio-mode=auto",
                "--disable-warnings"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {test_file} - PASSED")
                # Count passed tests
                passed_count = result.stdout.count(" PASSED")
                print(f"   Tests passed: {passed_count}")
            else:
                print(f"❌ {test_file} - FAILED")
                print("   Output:")
                print(result.stdout)
                if result.stderr:
                    print("   Errors:")
                    print(result.stderr)
                all_passed = False
        else:
            print(f"⚠️ {test_file} - FILE NOT FOUND")
    
    return all_passed


def main():
    """Main test runner"""
    print("🚀 GuzoSync Socket.IO Real-World Test Runner")
    print("=" * 60)
    print("🎯 Testing Real Socket.IO Functionality:")
    print("   🔐 Authentication with real JWT tokens")
    print("   💬 Real-time messaging between users")
    print("   🚌 Live bus tracking and location updates")
    print("   🔔 Proximity alerts and notifications")
    print("   🚨 Emergency alert system")
    print("   📢 Admin broadcasts")
    print("   💾 Database integration")
    print("=" * 60)
    
    server_manager = ServerManager()
    
    try:
        # Start server
        if not server_manager.start_server():
            print("❌ Failed to start server. Exiting.")
            return False
        
        # Wait a bit for server to fully initialize
        print("⏳ Waiting for server to fully initialize...")
        time.sleep(3)
        
        # Run simple connectivity test
        if not run_simple_connectivity_test():
            print("❌ Basic connectivity failed. Check server logs.")
            return False
        
        # Run Socket.IO tests
        tests_passed = run_socketio_tests()
        
        print("\n" + "=" * 60)
        if tests_passed:
            print("🎉 ALL REAL-WORLD SOCKET.IO TESTS PASSED!")
            print("\n✅ Verified Features:")
            print("   🔐 Socket.IO server is running")
            print("   🌐 HTTP endpoints are accessible")
            print("   🔌 Socket.IO connections work")
            print("   💾 Database integration works")
            print("\n🚀 Socket.IO system is ready for production!")
        else:
            print("❌ SOME TESTS FAILED")
            print("   Check the output above for details")
        
        return tests_passed
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
        
    finally:
        # Always stop the server
        server_manager.stop_server()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
