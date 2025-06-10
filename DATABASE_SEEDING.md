# GuzoSync Database Seeding Documentation

This document describes the comprehensive database seeding system for the GuzoSync backend application.

## Overview

The database seeding system provides realistic test data for all collections in the GuzoSync database, including real bus stops from Addis Ababa imported from GeoJSON data. This ensures that the application can be tested with realistic data that closely resembles production scenarios.

## Files

### Core Seeding Scripts

1. **`init_db_complete.py`** - Complete database seeding with all models
2. **`seed_db_startup.py`** - Startup seeding script for server initialization
3. **`start_with_seeding.bat`** - Windows batch script to seed and start server
4. **`start_with_seeding.sh`** - Unix/Linux shell script to seed and start server

### Data Sources

- **`busStops.geojson`** - Real bus stop data for Addis Ababa from OpenStreetMap

## Features

### Real Bus Stop Data
- Imports actual bus stops from Addis Ababa using GeoJSON format
- Extracts names in multiple languages (English, Amharic)
- Generates fallback names for stops without explicit names
- Prevents duplicate imports by checking existing stops

### Comprehensive Data Models

The seeding system creates realistic data for all database collections:

#### Core Transport Data
- **Users** (30 users with different roles)
- **Buses** (18 buses with various types and statuses)
- **Bus Stops** (Imported from GeoJSON + generated)
- **Routes** (12 routes connecting multiple stops)
- **Schedules** (25 schedules with realistic departure times)
- **Trips** (40 trips with various statuses)

#### Financial Data
- **Payments** (35 payments with different methods and statuses)
- **Tickets** (40 tickets linked to completed payments)

#### User Interaction Data
- **Feedback** (25 feedback records with ratings and comments)
- **Incidents** (15 incident reports with various severities)
- **Notifications** (40 notifications of different types)
- **Notification Settings** (Settings for all users)

#### Operational Data
- **Attendance Records** (50 check-in/check-out records)
- **Daily Attendance** (30 daily attendance summaries)
- **Approval Requests** (10 staff approval requests)

#### Communication Data
- **Conversations** (20 conversations between users)
- **Messages** (Multiple messages per conversation)

#### Regulatory Data
- **Reallocation Requests** (12 bus reallocation requests)
- **Overcrowding Reports** (10 overcrowding incident reports)

## Usage

### Quick Start (Recommended)

For development and testing, use the startup scripts that automatically seed the database:

**Windows:**
```bash
start_with_seeding.bat
```

**Unix/Linux:**
```bash
chmod +x start_with_seeding.sh
./start_with_seeding.sh
```

### Manual Seeding

#### Complete Database Seeding
```bash
python init_db_complete.py
```

#### Startup Seeding (Smart Seeding)
```bash
# Seed only if database is empty
python seed_db_startup.py

# Force re-seed even if data exists
python seed_db_startup.py --force

# Create minimal data only
python seed_db_startup.py --minimal
```

## Test User Credentials

The seeding system creates test users for each role with predictable credentials:

| Role | Email | Password |
|------|-------|----------|
| Passenger | test_passenger@guzosync.com | Test123! |
| Bus Driver | test_bus_driver@guzosync.com | Test123! |
| Queue Regulator | test_queue_regulator@guzosync.com | Test123! |
| Control Staff | test_control_staff@guzosync.com | Test123! |
| Control Admin | test_control_admin@guzosync.com | Test123! |

**Note:** Temporary passwords for queue regulators and bus drivers are printed to console during registration for debugging purposes.

## Data Relationships

The seeding system ensures proper data relationships:

- **Routes** reference actual bus stops
- **Trips** are linked to buses, routes, and drivers
- **Tickets** are connected to completed payments
- **Feedback** references specific trips and buses
- **Schedules** assign buses and drivers to routes
- **Attendance** records are created for staff users only

## Configuration

### Environment Variables

The seeding scripts use the following environment variables:

```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=guzosync
```

### Customization

You can customize the seeding by modifying the count parameters in the scripts:

```python
# In init_db_complete.py or seed_db_startup.py
users = await create_users(db, count=30)        # Adjust user count
buses = await create_buses(db, count=18)        # Adjust bus count
routes = await create_routes(db, bus_stops, count=12)  # Adjust route count
```

## GeoJSON Bus Stop Import

The system includes a specialized function to import real bus stops from the `busStops.geojson` file:

### Features
- Validates GeoJSON format and structure
- Extracts coordinates (handles GeoJSON longitude/latitude order)
- Supports multiple name fields (name, name:en, name:am)
- Generates fallback names for unnamed stops
- Prevents duplicate imports
- Assigns random but realistic capacity values

### GeoJSON Structure Expected
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Bus Stop Name",
        "name:en": "English Name",
        "name:am": "Amharic Name"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [longitude, latitude]
      }
    }
  ]
}
```

## Performance Considerations

The seeding system uses a hybrid approach for optimal performance:

1. **Bulk Operations** - Uses MongoDB's `insert_many()` for efficient bulk inserts
2. **Pydantic Validation** - Validates data structure using Pydantic models
3. **UUID Generation** - Ensures consistent UUID usage across all records
4. **Smart Relationships** - Creates realistic relationships between entities

## Error Handling

The seeding system includes comprehensive error handling:

- **Connection Errors** - Validates MongoDB connection before seeding
- **File Errors** - Handles missing or invalid GeoJSON files gracefully
- **Data Errors** - Continues seeding even if individual records fail
- **Rollback** - Can clear database if seeding fails partway through

## Monitoring and Logging

The seeding process provides detailed progress information:

- Progress indicators for each collection
- Count of successfully created records
- Warnings for skipped or failed records
- Summary statistics at completion
- Error details for troubleshooting

## Best Practices

1. **Always seed before testing** - Use the startup scripts to ensure fresh data
2. **Use minimal seeding for CI/CD** - Faster seeding for automated testing
3. **Force re-seed for clean tests** - Use `--force` flag when needed
4. **Monitor seeding output** - Check for warnings or errors during seeding
5. **Backup production data** - Never run seeding scripts on production databases

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check if MongoDB is running
   - Verify connection string in environment variables

2. **GeoJSON File Not Found**
   - Ensure `busStops.geojson` exists in the project root
   - Check file permissions

3. **Seeding Partially Fails**
   - Check MongoDB disk space
   - Verify database permissions
   - Review error messages for specific issues

4. **Duplicate Key Errors**
   - Use `--force` flag to clear existing data
   - Check for existing test data

### Getting Help

If you encounter issues with database seeding:

1. Check the console output for specific error messages
2. Verify your MongoDB connection and permissions
3. Ensure all required files (especially `busStops.geojson`) are present
4. Try minimal seeding first to isolate issues
