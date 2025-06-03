# Database Initialization Scripts

The GuzoSync backend includes scripts to initialize the database with mock data for development and testing purposes.

## Mock Data Initialization

The `init_db.py` script creates a complete set of mock data across all collections in the database.

### Prerequisites

- MongoDB server running
- `.env` file configured with proper MongoDB connection parameters:
  ```
  MONGODB_URL=mongodb://localhost:27017
  DATABASE_NAME=guzosync
  ```

### Usage

Run the following command to initialize the database with mock data:

```bash
python -m init_db
```

To drop existing collections before creating new mock data (clear the database):

```bash
python -m init_db --drop
```

### Generated Data

The script creates the following mock data:

- Users with different roles (passengers, drivers, regulators, control staff, admins)
- Test users with predictable credentials (email: test\_[role]@guzosync.com, password: Test123!)
- Bus stops in the Addis Ababa area
- Routes connecting various stops
- Buses with different types and statuses
- Trip schedules
- Trips with various statuses
- Payments and tickets
- Feedback and incident reports
- Notifications
- Attendance records

## Payment Methods Initialization

The `init_payments.py` script initializes payment method configurations in the database.

```bash
python -m init_payments
```

This sets up the supported payment methods with their configurations, fees, and display information.
