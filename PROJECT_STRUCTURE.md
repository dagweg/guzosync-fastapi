# 🏗️ GuzoSync Project Structure

Clean, organized codebase structure for maintainable development.

## 📁 Directory Structure

```
guzosync-backend/
├── 📁 core/                          # Core application logic
│   ├── 📁 realtime/                  # Real-time communication
│   │   ├── bus_tracking.py           # Bus location tracking
│   │   ├── chat.py                   # Chat functionality
│   │   ├── notifications.py          # Real-time notifications
│   │   ├── socketio_events.py        # Socket.IO event handlers
│   │   └── websocket_events.py       # WebSocket event handlers
│   ├── 📁 services/                  # Business logic services
│   │   ├── background_tasks.py       # Background job processing
│   │   ├── mapbox_service.py         # Mapbox API integration
│   │   └── route_service.py          # Route management logic
│   ├── analytics_service.py          # Analytics and reporting
│   ├── chapa_service.py             # Payment processing
│   ├── config.py                    # Application configuration
│   ├── dependencies.py              # FastAPI dependencies
│   ├── email_service.py             # Email notifications
│   ├── jwt.py                       # JWT authentication
│   ├── mongo_utils.py               # MongoDB utilities
│   ├── security.py                  # Security utilities
│   ├── socketio_manager.py          # Socket.IO management
│   └── websocket_manager.py         # WebSocket management
│
├── 📁 models/                        # Data models
│   ├── analytics.py                 # Analytics models
│   ├── approval.py                  # Approval workflow models
│   ├── attendance.py                # Attendance tracking models
│   ├── base.py                      # Base model classes
│   ├── conversation.py              # Chat/messaging models
│   ├── feedback.py                  # Feedback models
│   ├── notifications.py             # Notification models
│   ├── operations.py                # Operational models
│   ├── payment.py                   # Payment models
│   ├── regulators.py                # Queue regulator models
│   ├── transport.py                 # Transport (bus/route) models
│   └── user.py                      # User models
│
├── 📁 routers/                       # API route handlers
│   ├── account.py                   # Account management
│   ├── analytics.py                 # Analytics endpoints
│   ├── approvals.py                 # Approval workflow
│   ├── attendance.py                # Attendance tracking
│   ├── buses.py                     # Bus management
│   ├── conversations.py             # Chat/messaging
│   ├── feedback.py                  # Feedback collection
│   ├── notifications.py             # Notification management
│   ├── payments.py                  # Payment processing
│   ├── regulators.py                # Queue regulator management
│   ├── routes.py                    # Route management
│   ├── socketio.py                  # Socket.IO endpoints
│   └── websocket.py                 # WebSocket endpoints
│
├── 📁 schemas/                       # Pydantic schemas
│   ├── analytics.py                 # Analytics request/response schemas
│   ├── approval.py                  # Approval schemas
│   ├── attendance.py                # Attendance schemas
│   ├── base.py                      # Base schema classes
│   ├── conversation.py              # Chat schemas
│   ├── feedback.py                  # Feedback schemas
│   ├── notification.py              # Notification schemas
│   ├── payment.py                   # Payment schemas
│   ├── regulators.py                # Regulator schemas
│   ├── route.py                     # Route schemas
│   ├── transport.py                 # Transport schemas
│   ├── trip.py                      # Trip schemas
│   └── user.py                      # User schemas
│
├── 📁 simulation/                    # Bus simulation system
│   ├── bus_simulation_service.py    # Simulation service
│   ├── bus_simulator.py             # Core bus simulator
│   ├── movement_calculator.py       # Movement calculations
│   └── route_path_generator.py      # Route path generation
│
├── 📁 scripts/                      # Utility scripts
│   ├── 📁 database/                 # Database management
│   │   ├── init_db_complete.py      # Complete database initialization
│   │   ├── import_csv_data.py       # CSV data import
│   │   ├── init_payments.py         # Payment system setup
│   │   └── seed_db_startup.py       # Startup seeding
│   ├── 📁 deployment/               # Deployment scripts
│   │   ├── deploy_initialize.py     # Deployment initialization
│   │   ├── populate_all_routes_once.py # Route geometry population
│   │   └── populate_route_geometry.py  # Individual route population
│   ├── 📁 simulation/               # Simulation scripts
│   │   ├── start_simulation.py      # Start bus simulation
│   │   ├── start_bus_simulation.sh  # Linux simulation starter
│   │   └── start_bus_simulation.bat # Windows simulation starter
│   ├── 📁 utilities/                # Utility scripts
│   │   └── cleanup_codebase.py      # Codebase cleanup
│
├── 📁 tests/                        # Test suite
│   ├── 📁 endpoints/                # API endpoint tests
│   │   ├── test_account.py          # Account endpoint tests
│   │   ├── test_analytics.py        # Analytics endpoint tests
│   │   ├── test_attendance.py       # Attendance endpoint tests
│   │   ├── test_buses.py            # Bus endpoint tests
│   │   ├── test_routes.py           # Route endpoint tests
│   │   └── ...                      # Other endpoint tests
│   ├── 📁 realtime/                 # Real-time feature tests
│   │   ├── test_socketio_basic.py   # Basic Socket.IO tests
│   │   ├── test_socketio_bus_tracking.py # Bus tracking tests
│   │   ├── test_socketio_messaging.py    # Messaging tests
│   │   └── run_realworld_tests.py   # Real-world integration tests
│   ├── conftest.py                  # Test configuration
│   ├── test_analytics.py            # Analytics service tests
│   ├── test_auth_flow.py            # Authentication tests
│   └── test_email_service.py        # Email service tests
│
├── 📁 docs/                         # Documentation
│   ├── 📁 api/                      # API documentation
│   │   ├── socket-events.md         # Socket.IO event documentation
│   │   ├── apis.doc                 # API specifications
│   │   └── request-response.doc     # Request/response examples
│   ├── 📁 deployment/               # Deployment guides
│   │   ├── DEPLOYMENT_GUIDE.md      # Complete deployment guide
│   │   └── RENDER_DEPLOYMENT_GUIDE.md # Render.com deployment
│   ├── 📁 features/                 # Feature documentation
│   │   ├── ANALYTICS_FEATURE_REPORT.md # Analytics features
│   │   ├── APPROVAL_WORKFLOW_DOCUMENTATION.md # Approval workflow
│   │   ├── ATTENDANCE_REDESIGN_SUMMARY.md # Attendance system
│   │   ├── BUS_SIMULATION_SERVICE.md # Bus simulation
│   │   ├── MAPBOX_INTEGRATION.md    # Mapbox integration
│   │   └── REALTIME_API_DOCUMENTATION.md # Real-time features
│   ├── 📁 guides/                   # User guides
│   │   ├── DATABASE_INITIALIZATION.md # Database setup
│   │   ├── FRONTEND_WEBSOCKET_INTEGRATION.md # Frontend integration
│   │   └── UUID_MIGRATION_GUIDE.md  # UUID migration
│   └── schema.doc                   # Database schema
│
├── 📁 config/                       # Configuration files
│   ├── .env.example                 # Environment variables template
│   ├── logging.conf                 # Logging configuration
│   └── settings.py                  # Application settings
│
├── 📁 data/                         # Data files
│   ├── routes.txt                   # Route data
│   └── stops.txt                    # Bus stop data
│
├── 📁 logs/                         # Log files
│   ├── guzosync.log                 # Application logs
│   ├── simulation.log               # Simulation logs
│   └── deployment_initialization.log # Deployment logs
│
├── 📁 static/                       # Static files
│   └── (frontend assets if needed)
│
├── 📁 templates/                    # Email templates
│   └── 📁 email/                    # Email templates
│
├── 📁 uploads/                      # File uploads
│   └── (user uploaded files)
│
├── 📁 backups/                      # Database backups
│   └── (backup files)
│
├── 📁 monitoring/                   # Monitoring and health checks
│   └── (monitoring scripts)
│
├── main.py                          # FastAPI application entry point
├── requirements.txt                 # Python dependencies
├── requirements-test.txt            # Test dependencies
├── pytest.ini                      # Pytest configuration
├── mypy.ini                        # MyPy type checking configuration
├── README.md                       # Project overview
└── PROJECT_STRUCTURE.md            # This file
```

## 🎯 Key Principles

### 1. **Separation of Concerns**
- **Models**: Data structure and validation
- **Schemas**: API request/response formats
- **Routers**: HTTP endpoint handlers
- **Services**: Business logic
- **Core**: Infrastructure and utilities

### 2. **Feature-Based Organization**
- Real-time features grouped in `core/realtime/`
- Simulation features in `simulation/`
- Analytics features clearly separated

### 3. **Environment Separation**
- Development scripts in `scripts/`
- Test files in `tests/`
- Documentation in `docs/`
- Configuration in `config/`

### 4. **Clean Dependencies**
- Core services are independent
- Models define data contracts
- Schemas handle API contracts
- Routers orchestrate requests

## 🚀 Benefits

### **Maintainability**
- Clear file organization
- Easy to find related code
- Consistent naming conventions

### **Scalability**
- Modular architecture
- Easy to add new features
- Clear separation of concerns

### **Testing**
- Organized test structure
- Easy to test individual components
- Clear test categories

### **Documentation**
- Comprehensive documentation structure
- API documentation separate from guides
- Feature-specific documentation

### **Deployment**
- Organized deployment scripts
- Clear environment separation
- Easy configuration management

## 🔧 Usage

### **Running Cleanup**
```bash
# Preview changes
python scripts/cleanup_codebase.py --dry-run

# Execute cleanup
python scripts/cleanup_codebase.py --execute
```

### **Development Workflow**
1. **Models**: Define data structures in `models/`
2. **Schemas**: Create API contracts in `schemas/`
3. **Services**: Implement business logic in `core/services/`
4. **Routers**: Create API endpoints in `routers/`
5. **Tests**: Write tests in `tests/`
6. **Documentation**: Update docs in `docs/`

This structure provides a solid foundation for continued development and maintenance of the GuzoSync platform! 🎉
