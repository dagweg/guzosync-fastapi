"""
Movement Calculator for Bus Simulation

This module handles realistic bus movement calculations including:
- Speed variations based on traffic conditions
- Acceleration and deceleration
- Stop timing at bus stops
- Heading calculations
- Distance calculations between coordinates
"""

import math
import random
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta


class MovementCalculator:
    """Calculate realistic bus movement and physics."""
    
    def __init__(self):
        # Realistic bus parameters (in km/h)
        self.min_speed = 5.0  # Minimum speed in traffic
        self.max_speed = 60.0  # Maximum speed on open roads
        self.average_speed = 25.0  # Average city speed
        self.acceleration = 2.0  # m/s² acceleration
        self.deceleration = 3.0  # m/s² deceleration
        
        # Stop parameters
        self.stop_duration_min = 30  # Minimum stop time in seconds
        self.stop_duration_max = 120  # Maximum stop time in seconds
        
        # Traffic simulation parameters
        self.traffic_variation = 0.3  # 30% speed variation due to traffic
        
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        Returns distance in kilometers.
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r
    
    def calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the bearing (heading) from point 1 to point 2.
        Returns bearing in degrees (0-360).
        """
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def calculate_intermediate_point(
        self, 
        lat1: float, lon1: float, 
        lat2: float, lon2: float, 
        fraction: float
    ) -> Tuple[float, float]:
        """
        Calculate an intermediate point between two coordinates.
        fraction: 0.0 = start point, 1.0 = end point
        """
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Distance between points
        d = 2 * math.asin(math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2 + 
            math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        ))
        
        a = math.sin((1 - fraction) * d) / math.sin(d)
        b = math.sin(fraction * d) / math.sin(d)
        
        x = a * math.cos(lat1) * math.cos(lon1) + b * math.cos(lat2) * math.cos(lon2)
        y = a * math.cos(lat1) * math.sin(lon1) + b * math.cos(lat2) * math.sin(lon2)
        z = a * math.sin(lat1) + b * math.sin(lat2)
        
        lat = math.atan2(z, math.sqrt(x**2 + y**2))
        lon = math.atan2(y, x)
        
        return math.degrees(lat), math.degrees(lon)
    
    def get_realistic_speed(self, base_speed: Optional[float] = None) -> float:
        """
        Generate a realistic speed considering traffic conditions.
        Returns speed in km/h.
        """
        if base_speed is None:
            base_speed = self.average_speed
        
        # Apply traffic variation
        traffic_factor = 1.0 + random.uniform(-self.traffic_variation, self.traffic_variation)
        speed = base_speed * traffic_factor
        
        # Ensure speed is within realistic bounds
        speed = max(self.min_speed, min(self.max_speed, speed))
        
        return round(speed, 1)
    
    def calculate_stop_duration(self) -> int:
        """
        Calculate realistic stop duration at a bus stop.
        Returns duration in seconds.
        """
        # Use weighted random for more realistic distribution
        # Most stops are short, some are longer
        weights = [0.4, 0.3, 0.2, 0.1]  # 40% short, 30% medium, 20% long, 10% very long
        durations = [
            random.randint(30, 45),   # Short stop
            random.randint(45, 75),   # Medium stop
            random.randint(75, 105),  # Long stop
            random.randint(105, 120)  # Very long stop
        ]
        
        return random.choices(durations, weights=weights)[0]
    
    def calculate_next_position(
        self,
        current_lat: float,
        current_lon: float,
        target_lat: float,
        target_lon: float,
        speed_kmh: float,
        time_delta_seconds: float
    ) -> Tuple[float, float, float]:
        """
        Calculate the next position based on current position, target, speed, and time.
        
        Returns:
            Tuple of (new_lat, new_lon, distance_remaining_km)
        """
        # Calculate distance to target
        total_distance = self.calculate_distance(current_lat, current_lon, target_lat, target_lon)
        
        # Calculate distance that can be traveled in the given time
        distance_per_second = speed_kmh / 3600  # Convert km/h to km/s
        travel_distance = distance_per_second * time_delta_seconds
        
        # If we can reach the target in this time step
        if travel_distance >= total_distance:
            return target_lat, target_lon, 0.0
        
        # Calculate fraction of the journey completed
        fraction = travel_distance / total_distance if total_distance > 0 else 0
        
        # Calculate intermediate position
        new_lat, new_lon = self.calculate_intermediate_point(
            current_lat, current_lon, target_lat, target_lon, fraction
        )
        
        remaining_distance = total_distance - travel_distance
        
        return new_lat, new_lon, remaining_distance
    
    def simulate_traffic_delay(self) -> float:
        """
        Simulate random traffic delays.
        Returns delay factor (1.0 = no delay, 0.5 = 50% slower, etc.)
        """
        # 80% chance of normal traffic, 20% chance of delays
        if random.random() < 0.8:
            return 1.0  # Normal traffic
        else:
            # Traffic delay: 20% to 70% slower
            return random.uniform(0.3, 0.8)
