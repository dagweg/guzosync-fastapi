"""
Route Path Generator for Bus Simulation

This module generates realistic paths for buses to follow along their assigned routes.
It creates waypoints between bus stops and handles route geometry.
"""

import random
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import logging

from models.base import Location

#logger = logging.getLogger(__name__)


class RoutePathGenerator:
    """Generate realistic paths for bus routes."""
    
    def __init__(self):
        self.waypoint_density = 0.5  # km between waypoints
        self.path_variation = 0.001  # Degree variation for realistic paths
        
    def generate_route_path(
        self, 
        bus_stops: List[Dict[str, Any]], 
        route_geometry: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate a complete path for a route including all waypoints.
        
        Args:
            bus_stops: List of bus stops in route order
            route_geometry: Optional GeoJSON geometry from Mapbox
            
        Returns:
            List of waypoints with coordinates and metadata
        """
        if len(bus_stops) < 2:
            #logger.warning("Route needs at least 2 stops to generate path")
            return []
        
        waypoints = []
        
        # If we have Mapbox geometry, use it
        if route_geometry and route_geometry.get('type') == 'LineString':
            waypoints = self._generate_from_geometry(route_geometry, bus_stops)
        else:
            # Generate simple path between stops
            waypoints = self._generate_simple_path(bus_stops)
        
        return waypoints
    
    def _generate_from_geometry(
        self,
        geometry: Dict[str, Any],
        bus_stops: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate waypoints from Mapbox route geometry."""
        waypoints = []
        coordinates = geometry.get('coordinates', [])

        if not coordinates:
            #logger.warning("No coordinates in geometry, falling back to simple path")
            return self._generate_simple_path(bus_stops)

        #logger.info(f"🗺️ Generating waypoints from Mapbox geometry with {len(coordinates)} coordinate points")

        # Convert coordinates to waypoints with enhanced metadata
        for i, coord in enumerate(coordinates):
            if len(coord) >= 2:
                waypoint = {
                    'latitude': coord[1],  # GeoJSON uses [lon, lat]
                    'longitude': coord[0],
                    'type': 'road_point',  # Changed from 'path_point' to indicate real road
                    'sequence': i,
                    'is_bus_stop': False,
                    'stop_id': None,
                    'stop_name': None,
                    'estimated_speed': self._estimate_speed_for_road_segment(i, len(coordinates)),
                    'road_type': self._classify_road_segment(i, len(coordinates)),
                    'source': 'mapbox'  # Indicate this is from real road data
                }
                waypoints.append(waypoint)

        # Mark bus stop waypoints and ensure they're properly positioned
        waypoints = self._mark_bus_stop_waypoints(waypoints, bus_stops)

        # Add intermediate waypoints if segments are too long
        waypoints = self._densify_long_segments(waypoints)

        #logger.info(f"✅ Generated {len(waypoints)} waypoints from Mapbox geometry")
        return waypoints
    
    def _generate_simple_path(self, bus_stops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate a simple path between bus stops."""
        waypoints: List[Dict[str, Any]] = []
        
        for i in range(len(bus_stops)):
            stop = bus_stops[i]
            location = stop.get('location', {})
            
            if not location.get('latitude') or not location.get('longitude'):
                continue
            
            # Add bus stop as waypoint
            waypoint = {
                'latitude': location['latitude'],
                'longitude': location['longitude'],
                'type': 'bus_stop',
                'sequence': len(waypoints),
                'is_bus_stop': True,
                'stop_id': stop.get('id'),
                'stop_name': stop.get('name'),
                'estimated_speed': 0  # Stop at bus stops
            }
            waypoints.append(waypoint)
            
            # Add intermediate waypoints to next stop
            if i < len(bus_stops) - 1:
                next_stop = bus_stops[i + 1]
                next_location = next_stop.get('location', {})
                
                if (next_location.get('latitude') and next_location.get('longitude')):
                    intermediate_points = self._generate_intermediate_waypoints(
                        location['latitude'], location['longitude'],
                        next_location['latitude'], next_location['longitude']
                    )
                    
                    for point in intermediate_points:
                        waypoint = {
                            'latitude': point[0],
                            'longitude': point[1],
                            'type': 'path_point',
                            'sequence': len(waypoints),
                            'is_bus_stop': False,
                            'stop_id': None,
                            'estimated_speed': self._get_segment_speed()
                        }
                        waypoints.append(waypoint)
        
        return waypoints
    
    def _generate_intermediate_waypoints(
        self, 
        lat1: float, lon1: float, 
        lat2: float, lon2: float
    ) -> List[Tuple[float, float]]:
        """Generate intermediate waypoints between two stops."""
        from .movement_calculator import MovementCalculator
        
        calc = MovementCalculator()
        distance = calc.calculate_distance(lat1, lon1, lat2, lon2)
        
        # Calculate number of waypoints based on distance
        num_waypoints = max(1, int(distance / self.waypoint_density))
        
        waypoints = []
        for i in range(1, num_waypoints):
            fraction = i / num_waypoints
            
            # Add some random variation for realistic paths
            lat_variation = random.uniform(-self.path_variation, self.path_variation)
            lon_variation = random.uniform(-self.path_variation, self.path_variation)
            
            intermediate_lat, intermediate_lon = calc.calculate_intermediate_point(
                lat1, lon1, lat2, lon2, fraction
            )
            
            # Apply variation
            intermediate_lat += lat_variation
            intermediate_lon += lon_variation
            
            waypoints.append((intermediate_lat, intermediate_lon))
        
        return waypoints
    
    def _mark_bus_stop_waypoints(
        self, 
        waypoints: List[Dict[str, Any]], 
        bus_stops: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Mark waypoints that are close to bus stops."""
        from .movement_calculator import MovementCalculator
        
        calc = MovementCalculator()
        
        for stop in bus_stops:
            stop_location = stop.get('location', {})
            if not stop_location.get('latitude') or not stop_location.get('longitude'):
                continue
            
            stop_lat = stop_location['latitude']
            stop_lon = stop_location['longitude']
            
            # Find closest waypoint to this bus stop
            closest_waypoint = None
            min_distance = float('inf')
            
            for waypoint in waypoints:
                distance = calc.calculate_distance(
                    waypoint['latitude'], waypoint['longitude'],
                    stop_lat, stop_lon
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_waypoint = waypoint
            
            # If waypoint is within 100m of bus stop, mark it as a bus stop
            if closest_waypoint and min_distance < 0.1:  # 100m
                closest_waypoint['is_bus_stop'] = True
                closest_waypoint['stop_id'] = stop.get('id')
                closest_waypoint['stop_name'] = stop.get('name')
                closest_waypoint['estimated_speed'] = 0  # Stop at bus stops
        
        return waypoints
    
    def _estimate_speed_for_segment(self, segment_index: int, total_segments: int) -> float:
        """Estimate appropriate speed for a route segment."""
        # Vary speed based on position in route
        if segment_index < total_segments * 0.1 or segment_index > total_segments * 0.9:
            # Slower at route ends (urban areas)
            return random.uniform(15, 25)
        else:
            # Faster in middle sections
            return random.uniform(25, 45)

    def _estimate_speed_for_road_segment(self, segment_index: int, total_segments: int) -> float:
        """Estimate appropriate speed for a road segment based on Mapbox data."""
        # More realistic speed estimation for actual roads
        position_ratio = segment_index / total_segments if total_segments > 0 else 0

        # Urban areas (start/end of routes) - slower speeds
        if position_ratio < 0.15 or position_ratio > 0.85:
            return random.uniform(15, 30)  # City streets
        # Suburban areas - medium speeds
        elif position_ratio < 0.3 or position_ratio > 0.7:
            return random.uniform(25, 40)  # Arterial roads
        # Highway/main road sections - faster speeds
        else:
            return random.uniform(35, 50)  # Main roads/highways

    def _classify_road_segment(self, segment_index: int, total_segments: int) -> str:
        """Classify the type of road segment."""
        position_ratio = segment_index / total_segments if total_segments > 0 else 0

        if position_ratio < 0.15 or position_ratio > 0.85:
            return "urban"
        elif position_ratio < 0.3 or position_ratio > 0.7:
            return "suburban"
        else:
            return "highway"
    
    def _get_segment_speed(self) -> float:
        """Get a random speed for a route segment."""
        # Weighted random speed distribution
        speeds = [15, 20, 25, 30, 35, 40]
        weights = [0.1, 0.2, 0.3, 0.2, 0.15, 0.05]
        return random.choices(speeds, weights=weights)[0]
    
    def create_circular_route(self, waypoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Make a route circular by connecting the last waypoint back to the first.
        This allows buses to continuously loop on their routes.
        """
        if len(waypoints) < 2:
            return waypoints
        
        circular_waypoints = waypoints.copy()
        
        # Add waypoints from last stop back to first stop
        first_waypoint = waypoints[0]
        last_waypoint = waypoints[-1]
        
        if (first_waypoint['latitude'] != last_waypoint['latitude'] or 
            first_waypoint['longitude'] != last_waypoint['longitude']):
            
            # Generate path back to start
            return_waypoints = self._generate_intermediate_waypoints(
                last_waypoint['latitude'], last_waypoint['longitude'],
                first_waypoint['latitude'], first_waypoint['longitude']
            )
            
            for point in return_waypoints:
                waypoint = {
                    'latitude': point[0],
                    'longitude': point[1],
                    'type': 'return_path',
                    'sequence': len(circular_waypoints),
                    'is_bus_stop': False,
                    'stop_id': None,
                    'estimated_speed': self._get_segment_speed()
                }
                circular_waypoints.append(waypoint)
        
        return circular_waypoints

    def _densify_long_segments(self, waypoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add intermediate waypoints for long segments to ensure smooth movement."""
        if len(waypoints) < 2:
            return waypoints

        from .movement_calculator import MovementCalculator
        calc = MovementCalculator()

        densified_waypoints = []
        max_segment_distance = 0.2  # 200 meters max between waypoints

        for i in range(len(waypoints)):
            densified_waypoints.append(waypoints[i])

            # Check if we need to add intermediate points to next waypoint
            if i < len(waypoints) - 1:
                current = waypoints[i]
                next_wp = waypoints[i + 1]

                distance = calc.calculate_distance(
                    current['latitude'], current['longitude'],
                    next_wp['latitude'], next_wp['longitude']
                )

                # If segment is too long, add intermediate waypoints
                if distance > max_segment_distance:
                    num_intermediate = int(distance / max_segment_distance)

                    for j in range(1, num_intermediate + 1):
                        fraction = j / (num_intermediate + 1)

                        intermediate_lat, intermediate_lon = calc.calculate_intermediate_point(
                            current['latitude'], current['longitude'],
                            next_wp['latitude'], next_wp['longitude'],
                            fraction
                        )

                        intermediate_waypoint = {
                            'latitude': intermediate_lat,
                            'longitude': intermediate_lon,
                            'type': 'intermediate_road_point',
                            'sequence': len(densified_waypoints),
                            'is_bus_stop': False,
                            'stop_id': None,
                            'stop_name': None,
                            'estimated_speed': current.get('estimated_speed', 25.0),
                            'road_type': current.get('road_type', 'urban'),
                            'source': 'densified'
                        }
                        densified_waypoints.append(intermediate_waypoint)

        #logger.debug(f"🔄 Densified waypoints from {len(waypoints)} to {len(densified_waypoints)}")
        return densified_waypoints
