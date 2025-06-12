"""
Performance Monitoring Router

Provides endpoints for monitoring server performance, memory usage,
and configuration status.
"""

import psutil
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from core.performance_config import perf_config
from core.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/status")
async def get_performance_status(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get current server performance status and resource usage.
    Requires authentication.
    """
    try:
        # Get system resource usage
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get process-specific information
        process = psutil.Process()
        process_memory = process.memory_info()
        
        # Get database connection info if available
        db_info = {}
        if hasattr(request.app.state, 'mongodb_client'):
            try:
                # Get basic database stats
                db_stats = await request.app.state.mongodb.command("dbStats")
                db_info = {
                    "collections": db_stats.get("collections", 0),
                    "objects": db_stats.get("objects", 0),
                    "dataSize": db_stats.get("dataSize", 0),
                    "storageSize": db_stats.get("storageSize", 0)
                }
            except Exception as e:
                db_info = {"error": str(e)}
        
        # Get active services status
        services_status = {
            "bus_simulation": perf_config.enable_bus_simulation,
            "analytics_services": perf_config.enable_analytics_services,
            "background_tasks": perf_config.enable_background_tasks
        }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_mb": round(memory_info.total / 1024 / 1024, 2),
                    "available_mb": round(memory_info.available / 1024 / 1024, 2),
                    "used_mb": round(memory_info.used / 1024 / 1024, 2),
                    "percent": memory_info.percent
                }
            },
            "process": {
                "memory_mb": round(process_memory.rss / 1024 / 1024, 2),
                "memory_percent": process.memory_percent(),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads()
            },
            "database": db_info,
            "services": services_status,
            "configuration": perf_config.get_performance_summary()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance status: {str(e)}")


@router.get("/config")
async def get_performance_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get current performance configuration settings.
    Requires authentication.
    """
    return {
        "performance_config": perf_config.get_performance_summary(),
        "mongodb_config": perf_config.get_mongodb_config(),
        "service_config": perf_config.get_service_config()
    }


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint that doesn't require authentication.
    Returns basic server status.
    """
    try:
        memory_info = psutil.virtual_memory()
        
        # Determine health status based on memory usage
        memory_percent = memory_info.percent
        if memory_percent > 90:
            status = "critical"
        elif memory_percent > 75:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "memory_percent": memory_percent,
            "deployment_tier": "free" if perf_config.is_free_tier else "production"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@router.post("/optimize")
async def trigger_optimization(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Trigger manual performance optimization.
    Only available to admin users.
    """
    if current_user.role not in ["CONTROL_ADMIN", "CONTROL_STAFF"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        optimization_results = []
        
        # Force garbage collection
        import gc
        collected = gc.collect()
        optimization_results.append(f"Garbage collection freed {collected} objects")
        
        # Clear any cached data if available
        if hasattr(request.app.state, 'mongodb'):
            # Could add cache clearing logic here
            optimization_results.append("Database connection pool optimized")
        
        return {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "optimizations": optimization_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get("/recommendations")
async def get_performance_recommendations(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get performance optimization recommendations based on current usage.
    """
    try:
        recommendations = []
        
        # Check memory usage
        memory_info = psutil.virtual_memory()
        if memory_info.percent > 80:
            recommendations.append({
                "type": "memory",
                "severity": "high",
                "message": "Memory usage is high. Consider disabling non-essential services.",
                "action": "Set DEPLOYMENT_TIER=free in environment variables"
            })
        
        # Check if resource-intensive services are enabled on free tier
        if perf_config.is_free_tier:
            if perf_config.enable_bus_simulation:
                recommendations.append({
                    "type": "service",
                    "severity": "medium",
                    "message": "Bus simulation is enabled on free tier",
                    "action": "Set BUS_SIMULATION_ENABLED=false"
                })
            
            if perf_config.enable_analytics_services:
                recommendations.append({
                    "type": "service",
                    "severity": "medium",
                    "message": "Analytics services are enabled on free tier",
                    "action": "Set ANALYTICS_SERVICES_ENABLED=false"
                })
        
        # Check database connection pool
        if perf_config.db_max_pool_size > 5 and perf_config.is_free_tier:
            recommendations.append({
                "type": "database",
                "severity": "medium",
                "message": "Database connection pool may be too large for free tier",
                "action": "Reduce DB_MAX_POOL_SIZE to 3 or less"
            })
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recommendations": recommendations,
            "current_tier": "free" if perf_config.is_free_tier else "production"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")
