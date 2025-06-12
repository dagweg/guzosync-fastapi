#!/usr/bin/env python
"""
Free Tier Performance Optimization Script

This script optimizes the GuzoSync FastAPI server for deployment on free tier
hosting services with limited RAM (512MB or less).

Usage:
    python scripts/optimize_for_free_tier.py
    python scripts/optimize_for_free_tier.py --revert  # To revert optimizations
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def update_env_file(optimize: bool = True):
    """Update .env file with performance optimizations"""
    env_path = project_root / ".env"
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    # Read current .env content
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Performance settings
    if optimize:
        settings = {
            "DEPLOYMENT_TIER": "free",
            "BUS_SIMULATION_ENABLED": "false",
            "ANALYTICS_SERVICES_ENABLED": "false", 
            "BACKGROUND_TASKS_ENABLED": "false",
            "LOG_LEVEL": "WARNING",
            "DB_MAX_POOL_SIZE": "3",
            "DB_MIN_POOL_SIZE": "1",
            "DB_CONNECTION_TIMEOUT": "3000",
            "MAX_BUSES_PER_QUERY": "5",
            "MAX_STOPS_PER_QUERY": "10"
        }
        print("🔧 Applying free tier optimizations...")
    else:
        settings = {
            "DEPLOYMENT_TIER": "production",
            "BUS_SIMULATION_ENABLED": "true",
            "ANALYTICS_SERVICES_ENABLED": "true",
            "BACKGROUND_TASKS_ENABLED": "true", 
            "LOG_LEVEL": "INFO",
            "DB_MAX_POOL_SIZE": "10",
            "DB_MIN_POOL_SIZE": "2",
            "DB_CONNECTION_TIMEOUT": "5000",
            "MAX_BUSES_PER_QUERY": "50",
            "MAX_STOPS_PER_QUERY": "100"
        }
        print("🔄 Reverting to production settings...")
    
    # Update or add settings
    updated_lines = []
    settings_found = set()
    
    for line in lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key = line.split('=')[0].strip()
            if key in settings:
                updated_lines.append(f"{key}={settings[key]}\n")
                settings_found.add(key)
            else:
                updated_lines.append(line + '\n')
        else:
            updated_lines.append(line + '\n')
    
    # Add missing settings
    for key, value in settings.items():
        if key not in settings_found:
            updated_lines.append(f"{key}={value}\n")
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    return True

def show_performance_tips():
    """Show performance optimization tips"""
    print("\n" + "="*60)
    print("🚀 PERFORMANCE OPTIMIZATION TIPS")
    print("="*60)
    print()
    print("✅ Applied optimizations:")
    print("   • Disabled bus simulation")
    print("   • Disabled analytics services")
    print("   • Disabled background tasks")
    print("   • Reduced database connection pool")
    print("   • Limited query result sizes")
    print("   • Reduced logging verbosity")
    print()
    print("📊 Expected improvements:")
    print("   • RAM usage: ~200-300MB (down from 512MB+)")
    print("   • Startup time: ~5-10 seconds (down from 30+ seconds)")
    print("   • Response time: Improved for basic operations")
    print()
    print("⚠️  Disabled features:")
    print("   • Real-time bus simulation")
    print("   • Live analytics dashboard")
    print("   • Automatic route shape updates")
    print("   • ETA broadcasting")
    print()
    print("🔧 To re-enable features for production:")
    print("   python scripts/optimize_for_free_tier.py --revert")
    print()
    print("📈 Monitor performance:")
    print("   GET /performance/health - Basic health check")
    print("   GET /performance/status - Detailed performance metrics")
    print("   GET /performance/recommendations - Optimization suggestions")

def main():
    parser = argparse.ArgumentParser(description='Optimize GuzoSync for free tier deployment')
    parser.add_argument('--revert', action='store_true', help='Revert optimizations')
    args = parser.parse_args()
    
    print("🎯 GuzoSync Free Tier Performance Optimizer")
    print("=" * 50)
    
    if args.revert:
        print("🔄 Reverting performance optimizations...")
        success = update_env_file(optimize=False)
        if success:
            print("✅ Reverted to production settings")
            print("🚀 Restart the server to apply changes")
        else:
            print("❌ Failed to revert settings")
            return 1
    else:
        print("🔧 Optimizing for free tier deployment...")
        success = update_env_file(optimize=True)
        if success:
            print("✅ Free tier optimizations applied")
            show_performance_tips()
        else:
            print("❌ Failed to apply optimizations")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
