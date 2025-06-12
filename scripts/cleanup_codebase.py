#!/usr/bin/env python3
"""
Codebase Cleanup and Reorganization Script

This script reorganizes the GuzoSync codebase into a clean, maintainable structure:
1. Removes temporary/debug files
2. Organizes scripts into proper directories
3. Consolidates documentation
4. Cleans up test files
5. Creates proper directory structure

Usage:
    python scripts/cleanup_codebase.py --dry-run    # Preview changes
    python scripts/cleanup_codebase.py --execute   # Apply changes
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class CodebaseCleanup:
    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir).resolve()
        self.changes: List[str] = []

    def log_change(self, action: str, source: str, target: Optional[str] = None):
        """Log a planned change"""
        if target:
            self.changes.append(f"{action}: {source} -> {target}")
        else:
            self.changes.append(f"{action}: {source}")
    
    def remove_files(self, patterns: List[str]):
        """Remove files matching patterns"""
        for pattern in patterns:
            for file_path in self.root.glob(pattern):
                if file_path.is_file():
                    self.log_change("DELETE", str(file_path.relative_to(self.root)))
    
    def move_file(self, source: str, target: str):
        """Move a file to new location"""
        source_path = self.root / source
        target_path = self.root / target
        
        if source_path.exists():
            self.log_change("MOVE", source, target)
    
    def create_directory(self, dir_path: str):
        """Create directory if it doesn't exist"""
        full_path = self.root / dir_path
        if not full_path.exists():
            self.log_change("CREATE_DIR", dir_path)
    
    def plan_cleanup(self):
        """Plan all cleanup operations"""
        logger.info("🧹 Planning codebase cleanup...")
        
        # 1. Remove temporary and debug files
        self.remove_debug_files()
        
        # 2. Organize scripts
        self.organize_scripts()
        
        # 3. Clean up test files
        self.organize_tests()
        
        # 4. Organize documentation
        self.organize_documentation()
        
        # 5. Clean up logs and cache
        self.clean_logs_and_cache()
        
        # 6. Create proper directory structure
        self.create_proper_structure()
    
    def remove_debug_files(self):
        """Remove temporary and debug files"""
        logger.info("🗑️ Removing debug and temporary files...")
        
        debug_files = [
            # Debug scripts
            "debug_bus_broadcast.py",
            "demo_bus_simulation.py", 
            "demo_realtime_working.py",
            "demo_socketio_working.py",
            "check_broadcast_ready.py",
            "check_cached_data.py",
            "comprehensive_ws_test.py",
            "fix_bus_locations.py",
            "fix_bus_simulation.py",
            "monitor_simulation.py",
            "verify_driver_assignments.py",
            
            # Test files in root
            "test_*.py",
            "attendance_heatmap_example.py",
            
            # Log files
            "*.log",
            "logs/*.log*",
            
            # Temporary files
            "socketio_fix.txt",
            "openapi_test.json",
        ]
        
        self.remove_files(debug_files)
    
    def organize_scripts(self):
        """Organize scripts into proper directories"""
        logger.info("📁 Organizing scripts...")
        
        # Create script directories
        self.create_directory("scripts/database")
        self.create_directory("scripts/deployment")
        self.create_directory("scripts/simulation")
        self.create_directory("scripts/utilities")
        
        # Move database scripts
        database_scripts = [
            ("init_db_complete.py", "scripts/database/init_db_complete.py"),
            ("init_db_api.py", "scripts/database/init_db_api.py"),
            ("import_csv_data.py", "scripts/database/import_csv_data.py"),
            ("init_payments.py", "scripts/database/init_payments.py"),
            ("seed_db_startup.py", "scripts/database/seed_db_startup.py"),
        ]
        
        for source, target in database_scripts:
            self.move_file(source, target)
        
        # Move simulation scripts
        simulation_scripts = [
            ("start_simulation.py", "scripts/simulation/start_simulation.py"),
            ("start_bus_simulation.bat", "scripts/simulation/start_bus_simulation.bat"),
            ("start_bus_simulation.sh", "scripts/simulation/start_bus_simulation.sh"),
            ("start_map_demo.bat", "scripts/simulation/start_map_demo.bat"),
            ("start_map_demo.sh", "scripts/simulation/start_map_demo.sh"),
            ("start_with_seeding.bat", "scripts/simulation/start_with_seeding.bat"),
            ("start_with_seeding.sh", "scripts/simulation/start_with_seeding.sh"),
        ]
        
        for source, target in simulation_scripts:
            self.move_file(source, target)
    
    def organize_tests(self):
        """Clean up and organize test files"""
        logger.info("🧪 Organizing test files...")
        
        # Remove duplicate/old test files
        old_test_files = [
            "tests/conftest.py.bak",
            "tests/conftest.py.fixed",
            "tests/endpoints/test_accounts_fixed.py",
        ]
        
        for file_path in old_test_files:
            if (self.root / file_path).exists():
                self.log_change("DELETE", file_path)
        
        # Move root-level test files to tests directory
        root_tests = [
            ("run_realworld_socketio_tests.py", "tests/realtime/run_realworld_socketio_tests.py"),
        ]
        
        for source, target in root_tests:
            self.move_file(source, target)
    
    def organize_documentation(self):
        """Organize documentation files"""
        logger.info("📚 Organizing documentation...")
        
        # Create documentation structure
        self.create_directory("docs/api")
        self.create_directory("docs/deployment")
        self.create_directory("docs/features")
        self.create_directory("docs/guides")
        
        # Move documentation files
        doc_moves = [
            ("DEPLOYMENT_GUIDE.md", "docs/deployment/DEPLOYMENT_GUIDE.md"),
            ("BUS_SIMULATION_SERVICE.md", "docs/features/BUS_SIMULATION_SERVICE.md"),
            ("SIMULATION_README.md", "docs/features/SIMULATION_README.md"),
            ("socket-events.md", "docs/api/socket-events.md"),
        ]
        
        for source, target in doc_moves:
            self.move_file(source, target)
    
    def clean_logs_and_cache(self):
        """Clean up logs and cache files"""
        logger.info("🧽 Cleaning logs and cache...")
        
        # Remove cache directories
        cache_patterns = [
            "__pycache__",
            "*/__pycache__",
            "*/*/__pycache__",
            "*.pyc",
            "*/*.pyc",
            "*/*/*.pyc",
        ]
        
        self.remove_files(cache_patterns)
        
        # Clean log files but keep directory structure
        log_files = [
            "deployment_initialization.log",
            "one_time_route_population.log", 
            "route_geometry_population.log",
        ]
        
        for log_file in log_files:
            if (self.root / log_file).exists():
                self.log_change("MOVE", log_file, f"logs/{log_file}")
    
    def create_proper_structure(self):
        """Create proper directory structure"""
        logger.info("🏗️ Creating proper directory structure...")
        
        # Create missing directories
        directories = [
            "config",
            "migrations/versions",
            "static",
            "uploads",
            "backups",
            "monitoring",
        ]
        
        for directory in directories:
            self.create_directory(directory)
    
    def execute_changes(self):
        """Execute all planned changes"""
        logger.info("⚡ Executing changes...")
        
        executed = 0
        for change in self.changes:
            try:
                action, details = change.split(": ", 1)
                
                if action == "DELETE":
                    file_path = self.root / details
                    if file_path.exists():
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                        logger.info(f"✅ Deleted: {details}")
                        executed += 1
                
                elif action == "MOVE":
                    source, target = details.split(" -> ")
                    source_path = self.root / source
                    target_path = self.root / target
                    
                    if source_path.exists():
                        # Create target directory if needed
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(source_path), str(target_path))
                        logger.info(f"✅ Moved: {source} -> {target}")
                        executed += 1
                
                elif action == "CREATE_DIR":
                    dir_path = self.root / details
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"✅ Created directory: {details}")
                    executed += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to execute: {change} - {e}")
        
        logger.info(f"🎉 Executed {executed} changes successfully!")
    
    def preview_changes(self):
        """Preview all planned changes"""
        logger.info("👀 Preview of planned changes:")
        logger.info("=" * 50)
        
        for change in self.changes:
            logger.info(f"  {change}")
        
        logger.info("=" * 50)
        logger.info(f"Total changes planned: {len(self.changes)}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="GuzoSync Codebase Cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--execute", action="store_true", help="Execute the cleanup")
    
    args = parser.parse_args()
    
    cleanup = CodebaseCleanup()
    cleanup.plan_cleanup()
    
    if args.dry_run:
        cleanup.preview_changes()
        logger.info("🔍 Dry run completed. Use --execute to apply changes.")
    elif args.execute:
        cleanup.preview_changes()
        
        confirm = input("\n⚠️ This will modify your codebase. Continue? (y/N): ")
        if confirm.lower() == 'y':
            cleanup.execute_changes()
            logger.info("🎉 Codebase cleanup completed!")
        else:
            logger.info("❌ Cleanup cancelled.")
    else:
        cleanup.preview_changes()
        logger.info("Use --dry-run to preview or --execute to apply changes.")


if __name__ == "__main__":
    main()
