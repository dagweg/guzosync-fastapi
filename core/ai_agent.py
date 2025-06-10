"""
AI Agent service for intelligent bus route optimization and reallocation decisions.
This service analyzes various factors to determine optimal route assignments.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RouteOptimizationAgent:
    """
    AI agent responsible for intelligent route optimization and bus reallocation decisions.
    
    This agent considers multiple factors:
    - Current traffic conditions
    - Route demand and capacity
    - Historical usage patterns
    - Real-time passenger data
    - Weather conditions
    - Special events
    - Emergency situations
    """
    
    def __init__(self):
        self.optimization_weights = {
            "demand_factor": 0.4,
            "traffic_factor": 0.3,
            "capacity_factor": 0.2,
            "historical_factor": 0.1
        }
    
    async def determine_optimal_route(
        self,
        bus_id: str,
        current_route_id: str,
        reason: str,
        priority: str,
        description: str,
        mongodb_client: Any,
        exclude_routes: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Determine the optimal route for bus reallocation using AI analysis.
        
        Args:
            bus_id: ID of the bus to be reallocated
            current_route_id: Current route assignment
            reason: Reason for reallocation request
            priority: Priority level (NORMAL, HIGH, URGENT)
            description: Additional context
            mongodb_client: MongoDB client for data access
            exclude_routes: Routes to exclude from consideration
            
        Returns:
            Optimal route ID or None if no suitable route found
        """
        try:
            logger.info(f"AI Agent analyzing reallocation for bus {bus_id}")
            
            # Get all available routes
            available_routes = await self._get_available_routes(
                mongodb_client, current_route_id, exclude_routes or []
            )
            
            if not available_routes:
                logger.warning("No available routes found for optimization")
                return None
            
            # Analyze each route based on multiple factors
            route_scores = {}
            for route in available_routes:
                score = await self._calculate_route_score(
                    route, bus_id, reason, priority, mongodb_client
                )
                route_scores[route["_id"]] = score
              # Select the route with the highest score
            if route_scores:
                optimal_route_id = max(route_scores, key=lambda x: route_scores[x])
                optimal_score = route_scores[optimal_route_id]
                
                logger.info(
                    f"AI Agent selected route {optimal_route_id} "
                    f"with score {optimal_score:.2f} for bus {bus_id}"
                )
                
                return str(optimal_route_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in AI route optimization: {str(e)}")
            return None
    
    async def _get_available_routes(
        self, 
        mongodb_client: Any, 
        current_route_id: str, 
        exclude_routes: List[str]
    ) -> List[Dict[str, Any]]:
        """Get all available routes excluding current and excluded routes."""
        excluded_ids = [current_route_id] + exclude_routes
        
        routes_cursor = mongodb_client.routes.find({
            "_id": {"$nin": excluded_ids},
            "is_active": True
        })
        
        return list(await routes_cursor.to_list(length=None))
    
    async def _calculate_route_score(
        self, 
        route: Dict[str, Any], 
        bus_id: str, 
        reason: str, 
        priority: str,
        mongodb_client: Any
    ) -> float:
        """
        Calculate optimization score for a route based on multiple factors.
        
        This is a simplified implementation. In a real AI system, this would
        involve complex algorithms considering:
        - Machine learning models trained on historical data
        - Real-time traffic API integration
        - Passenger demand prediction models
        - Weather impact analysis
        - Event-based demand forecasting
        """
        try:
            # Base score
            score = 50.0
            
            # Demand factor - analyze current bus assignments on this route
            demand_score = await self._analyze_route_demand(route["_id"], mongodb_client)
            score += demand_score * self.optimization_weights["demand_factor"] * 100
            
            # Capacity factor - consider route length and complexity
            capacity_score = self._analyze_route_capacity(route)
            score += capacity_score * self.optimization_weights["capacity_factor"] * 100
            
            # Priority boost - urgent requests get preference for high-demand routes
            if priority == "URGENT":
                score += 20
            elif priority == "HIGH":
                score += 10
                
            # Reason-specific adjustments
            if reason == "EMERGENCY":
                score += 30
            elif reason == "OVERCROWDING":
                # Prefer routes with lower current demand
                score += (100 - demand_score) * 0.3
            elif reason == "SCHEDULE_OPTIMIZATION":
                # Prefer routes that need better coverage
                score += (100 - capacity_score) * 0.2
            
            return max(0.0, min(100.0, score))  # Normalize to 0-100
            
        except Exception as e:
            logger.error(f"Error calculating route score: {str(e)}")
            return 0.0
    
    async def _analyze_route_demand(self, route_id: str, mongodb_client: Any) -> float:
        """
        Analyze current demand on a route (0-100 scale).
        Higher values indicate higher demand/congestion.
        """
        try:
            # Count buses currently assigned to this route
            bus_count = await mongodb_client.buses.count_documents({
                "assigned_route_id": route_id,
                "status": {"$in": ["ACTIVE", "IN_TRANSIT"]}
            })
            
            # Get recent overcrowding reports for this route
            recent_reports = await mongodb_client.overcrowding_reports.count_documents({
                "route_id": route_id,
                "created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)}
            })
              # Simple demand calculation (would be much more sophisticated in real AI)
            demand_score = min(90.0, float(bus_count * 25) + float(recent_reports * 10))
            return demand_score
            
        except Exception as e:
            logger.error(f"Error analyzing route demand: {str(e)}")
            return 50.0  # Default medium demand
    
    def _analyze_route_capacity(self, route: Dict[str, Any]) -> float:
        """
        Analyze route capacity and complexity (0-100 scale).
        Higher values indicate better capacity/simpler routes.
        """
        try:
            # Factor in route distance and number of stops
            stop_count = len(route.get("stop_ids", []))
            distance = route.get("total_distance", 10.0)
            
            # Simple capacity score (would use ML models in real implementation)
            if stop_count <= 5:
                stop_score = 80
            elif stop_count <= 10:
                stop_score = 60
            elif stop_count <= 15:
                stop_score = 40
            else:
                stop_score = 20
            
            # Distance factor (shorter routes are easier to manage)
            if distance <= 5.0:
                distance_score = 80
            elif distance <= 15.0:
                distance_score = 60
            elif distance <= 30.0:
                distance_score = 40
            else:
                distance_score = 20
            
            return (stop_score + distance_score) / 2
            
        except Exception as e:
            logger.error(f"Error analyzing route capacity: {str(e)}")
            return 50.0  # Default medium capacity

# Global instance
route_optimization_agent = RouteOptimizationAgent()

__all__ = ["RouteOptimizationAgent", "route_optimization_agent"]
