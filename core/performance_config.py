"""
Performance Configuration for GuzoSync FastAPI Server

This module contains performance optimization settings that can be toggled
based on deployment environment (free tier vs production).
"""

import os
from typing import Dict, Any


class PerformanceConfig:
    """Performance configuration settings"""
    
    def __init__(self):
        # Environment detection
        self.is_free_tier = os.getenv("DEPLOYMENT_TIER", "free").lower() == "free"
        self.is_production = os.getenv("NODE_ENV", "development").lower() == "production"
        
        # Service enablement flags
        self.enable_bus_simulation = self._get_bool_env("BUS_SIMULATION_ENABLED", not self.is_free_tier)
        self.enable_analytics_services = self._get_bool_env("ANALYTICS_SERVICES_ENABLED", not self.is_free_tier)
        self.enable_background_tasks = self._get_bool_env("BACKGROUND_TASKS_ENABLED", not self.is_free_tier)
        
        # Database connection settings
        self.db_max_pool_size = int(os.getenv("DB_MAX_POOL_SIZE", "3" if self.is_free_tier else "10"))
        self.db_min_pool_size = int(os.getenv("DB_MIN_POOL_SIZE", "1"))
        self.db_connection_timeout = int(os.getenv("DB_CONNECTION_TIMEOUT", "3000" if self.is_free_tier else "5000"))
        self.db_max_idle_time = int(os.getenv("DB_MAX_IDLE_TIME", "30000"))
        
        # Query limits
        self.max_buses_per_query = int(os.getenv("MAX_BUSES_PER_QUERY", "5" if self.is_free_tier else "50"))
        self.max_stops_per_query = int(os.getenv("MAX_STOPS_PER_QUERY", "10" if self.is_free_tier else "100"))
        
        # Update intervals (in seconds)
        self.analytics_update_interval = int(os.getenv("ANALYTICS_UPDATE_INTERVAL", "600" if self.is_free_tier else "30"))
        self.eta_broadcast_interval = int(os.getenv("ETA_BROADCAST_INTERVAL", "600" if self.is_free_tier else "120"))
        self.route_shape_update_interval = int(os.getenv("ROUTE_SHAPE_UPDATE_INTERVAL", "86400" if self.is_free_tier else "21600"))  # 24h vs 6h
        self.cache_cleanup_interval = int(os.getenv("CACHE_CLEANUP_INTERVAL", "21600" if self.is_free_tier else "3600"))  # 6h vs 1h
        
        # Bus simulation settings
        self.bus_simulation_interval = float(os.getenv("BUS_SIMULATION_INTERVAL", "30.0" if self.is_free_tier else "5.0"))
        self.max_simulated_buses = int(os.getenv("BUS_SIMULATION_MAX_BUSES", "2" if self.is_free_tier else "20"))
        
        # Logging settings
        self.log_level = os.getenv("LOG_LEVEL", "WARNING" if self.is_free_tier else "INFO")
        
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with default"""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")
    
    def get_mongodb_config(self) -> Dict[str, Any]:
        """Get MongoDB connection configuration"""
        return {
            "maxPoolSize": self.db_max_pool_size,
            "minPoolSize": self.db_min_pool_size,
            "serverSelectionTimeoutMS": self.db_connection_timeout,
            "connectTimeoutMS": self.db_connection_timeout,
            "socketTimeoutMS": self.db_connection_timeout,
            "maxIdleTimeMS": self.db_max_idle_time,
            "retryWrites": True,
            "uuidRepresentation": "unspecified"
        }
    
    def get_service_config(self) -> Dict[str, Any]:
        """Get service enablement configuration"""
        return {
            "bus_simulation": self.enable_bus_simulation,
            "analytics_services": self.enable_analytics_services,
            "background_tasks": self.enable_background_tasks
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance configuration summary"""
        return {
            "deployment_tier": "free" if self.is_free_tier else "production",
            "services_enabled": {
                "bus_simulation": self.enable_bus_simulation,
                "analytics": self.enable_analytics_services,
                "background_tasks": self.enable_background_tasks
            },
            "database_config": {
                "max_pool_size": self.db_max_pool_size,
                "connection_timeout": self.db_connection_timeout,
                "max_buses_per_query": self.max_buses_per_query
            },
            "update_intervals": {
                "analytics": f"{self.analytics_update_interval}s",
                "eta_broadcast": f"{self.eta_broadcast_interval}s",
                "route_shapes": f"{self.route_shape_update_interval}s"
            },
            "log_level": self.log_level
        }


# Global performance configuration instance
perf_config = PerformanceConfig()
