#!/bin/bash

echo "========================================"
echo "GuzoSync Backend - Start with Seeding"
echo "========================================"
echo

echo "🌱 Seeding database with test data..."
python init_payments.py
python seed_db_startup.py

if [ $? -ne 0 ]; then
    echo "❌ Database seeding failed!"
    echo "Please check the error messages above."
    exit 1
fi

echo
echo "✅ Database seeding completed successfully!"
echo
echo "🚀 Starting FastAPI server..."
echo
