"""
Bus Route Simulation Package

This package provides comprehensive bus simulation functionality for the GuzoSync system.
It simulates realistic bus movement along assigned routes, updating locations in real-time
through the existing WebSocket infrastructure.

Components:
- bus_simulator.py: Main simulation engine
- route_path_generator.py: Generate realistic paths between bus stops
- movement_calculator.py: Calculate realistic bus movement and physics
"""

from .bus_simulator import BusSimulator
from .route_path_generator import RoutePathGenerator
from .movement_calculator import MovementCalculator
from .bus_simulation_service import bus_simulation_service

__all__ = ['BusSimulator', 'RoutePathGenerator', 'MovementCalculator', 'bus_simulation_service']
