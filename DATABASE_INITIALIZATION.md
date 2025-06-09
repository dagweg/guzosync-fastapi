# Database Initialization Guide

This document explains how to initialize the GuzoSync database with mock data using two different approaches.

## 🚀 Quick Start (Recommended)

### API-Based Initialization (Recommended)

Use the API-based approach to ensure all data goes through proper application layer validation:

```bash
# Start the FastAPI server first
uvicorn main:app --reload

# In another terminal, run the API-based initialization
python init_db_api.py
```

### Direct Database Initialization (Legacy)

⚠️ **Not recommended for production or testing**. This bypasses application validation:

```bash
python init_db.py --drop
```

## 📊 Approaches Comparison

| Aspect                  | API-Based (`init_db_api.py`)              | Direct DB (`init_db.py`)        |
| ----------------------- | ----------------------------------------- | ------------------------------- |
| **Data Validation**     | ✅ Full validation via Pydantic schemas   | ❌ No validation                |
| **Business Logic**      | ✅ All business rules applied             | ❌ Business logic bypassed      |
| **Data Transformation** | ✅ Proper data transformation             | ❌ Raw data insertion           |
| **Consistency**         | ✅ Consistent with app behavior           | ❌ May create inconsistent data |
| **Security**            | ✅ Authentication & authorization checked | ❌ No security checks           |
| **Error Handling**      | ✅ Proper error responses                 | ❌ Database-level errors only   |
| **Testing**             | ✅ Tests the actual API endpoints         | ❌ Doesn't test API layer       |
| **Speed**               | ⚠️ Slower (HTTP overhead)                 | ✅ Faster (direct DB access)    |
| **Dependencies**        | ⚠️ Requires running server                | ✅ Direct MongoDB connection    |

## 🔧 API-Based Initialization Details

### Prerequisites

1. **Running FastAPI Server**: The API endpoints must be accessible
2. **Environment Variables**: Ensure `.env` file is properly configured
3. **Dependencies**: Install required packages:
   ```bash
   pip install aiohttp
   ```

### What It Creates

The API-based script creates:

- **20 Users** (70% passengers, 30% staff) with proper role validation
- **15 Bus Stops** with location validation and business rules
- **8 Routes** connecting bus stops with proper relationships
- **12 Buses** with capacity and type validation
- **20 Payments & Tickets** with proper payment flow simulation

### Authentication Flow

1. Creates admin user (if not exists)
2. Logs in as admin to get access token
3. Uses admin token to create staff users via control center endpoints
4. Uses passenger credentials to create payments and tickets

### Error Handling

- Gracefully handles existing data (users, bus stops, etc.)
- Continues processing even if some requests fail
- Provides detailed error reporting
- Maintains referential integrity

### Command Line Options

```bash
# Use custom API URL
python init_db_api.py --api-url http://localhost:8080

# Increase timeout for slow connections
python init_db_api.py --timeout 60
```

## 🗃️ Direct Database Initialization Details

### Use Cases

Only use direct database initialization for:

- **Emergency data seeding** when API is not available
- **Performance testing** with large datasets
- **Development setup** where data consistency is not critical

### Limitations

- **No validation**: Invalid data may be inserted
- **No business logic**: Bypasses application rules
- **No authentication**: Ignores access controls
- **Inconsistent state**: May create data that breaks application assumptions
- **Test unreliability**: Tests won't catch issues that would occur via API

### Command Line Options

```bash
# Drop existing data and recreate
python init_db.py --drop

# Keep existing data and add new data
python init_db.py
```

## 🎯 Best Practices

1. **Always use API-based initialization** for:

   - Testing environments
   - Demo setups
   - Development workflows
   - QA environments

2. **Use direct database initialization only for**:

   - Emergency scenarios
   - Performance benchmarking
   - Initial development setup

3. **Before using either approach**:
   - Backup existing data if needed
   - Verify environment configuration
   - Test with small datasets first

## 🔍 Verification

After running either script, verify the data:

```bash
# Check user creation
curl -X POST http://localhost:8000/api/accounts/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test_passenger@guzosync.com", "password": "Test123!"}'

# Check bus stops
curl -X GET http://localhost:8000/api/buses/stops \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check routes
curl -X GET http://localhost:8000/api/routes/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🛠️ Troubleshooting

### API-Based Issues

- **Server not running**: Start with `uvicorn main:app --reload`
- **Authentication failures**: Check admin user credentials
- **Connection errors**: Verify API_BASE_URL in `.env`
- **Timeout errors**: Increase timeout with `--timeout` flag

### Direct Database Issues

- **MongoDB connection**: Check MONGODB_URL in `.env`
- **Permission errors**: Ensure MongoDB access rights
- **Collection conflicts**: Use `--drop` flag to reset

### Common Issues

- **Missing dependencies**: Run `pip install -r requirements.txt`
- **Environment variables**: Ensure `.env` file exists and is properly configured
- **Port conflicts**: Make sure no other services are using the same ports

## 📝 Test Users Created

Both scripts create test users with predictable credentials:

| Role            | Email                             | Password  |
| --------------- | --------------------------------- | --------- |
| PASSENGER       | test_passenger@guzosync.com       | Test123!  |
| BUS_DRIVER      | test_bus_driver@guzosync.com      | Test123!  |
| QUEUE_REGULATOR | test_queue_regulator@guzosync.com | Test123!  |
| CONTROL_STAFF   | test_control_staff@guzosync.com   | Test123!  |
| CONTROL_ADMIN   | admin@guzosync.com                | Admin123! |
