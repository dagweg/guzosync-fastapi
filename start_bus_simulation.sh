#!/bin/bash

echo "🚀 Starting GuzoSync Bus Simulation"
echo

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python -m venv venv"
    echo "Then: source venv/bin/activate"
    echo "Then: pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️ .env file not found!"
    echo "Please create .env file with MongoDB configuration"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo "🌱 Starting simulation with database seeding and route assignment..."
echo

# Start simulation with seeding and route assignment
python start_simulation.py --seed-first --assign-routes --interval 3

echo
echo "👋 Simulation ended"
