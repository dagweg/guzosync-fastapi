# 🚌 GuzoSync Backend

A comprehensive bus tracking and management system built with FastAPI, featuring real-time location tracking, route management, and passenger services for Addis Ababa's public transportation.

## ✨ Features

- **🗺️ Real-time Bus Tracking**: Live location updates via WebSocket/Socket.IO with Mapbox integration
- **🛣️ Route Management**: Comprehensive route and bus stop management with real road geometry
- **👥 User Management**: Multi-role system (passengers, drivers, regulators, admins)
- **💳 Payment Integration**: Chapa payment gateway integration
- **📊 Analytics**: Comprehensive analytics and reporting dashboard
- **📋 Attendance Tracking**: Driver and passenger attendance management
- **💬 Feedback System**: User feedback and incident reporting
- **✅ Approval Workflows**: Queue regulator and driver approval system
- **🚌 Bus Simulation**: Real-time bus movement simulation for testing

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.8+)
- **Database**: MongoDB with UUID-based records
- **Cache**: Redis for performance optimization
- **Real-time**: WebSocket + Socket.IO for live updates
- **Authentication**: JWT-based security
- **Payment**: Chapa API integration
- **Maps**: Mapbox API for route geometry and navigation
- **Testing**: Pytest with comprehensive test coverage

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- MongoDB (local or Atlas)
- Redis (optional but recommended)
- Mapbox account (for route geometry)

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd guzosync-backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration (see Environment Variables section)
```

5. **Complete deployment initialization:**
```bash
# Full initialization (database + route geometry)
python scripts/deploy_initialize.py --full

# Or check current status
python scripts/deploy_initialize.py --check
```

6. **Start the server:**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Socket.IO Events**: See `docs/api/socket-events.md`

## 🔧 Environment Variables

```env
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=guzosync

# Redis (optional)
REDIS_URL=redis://localhost:6379

# JWT Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Chapa Payment
CHAPA_SECRET_KEY=your-chapa-secret-key

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Mapbox (required for route geometry)
MAPBOX_ACCESS_TOKEN=pk.your-mapbox-token
```

## 📁 Project Structure

```
guzosync-backend/
├── 📁 core/                          # Core application logic
├── 📁 models/                        # Data models (Pydantic)
├── 📁 routers/                       # API route handlers
├── 📁 schemas/                       # Request/response schemas
├── 📁 simulation/                    # Bus simulation system
├── 📁 scripts/                       # Utility scripts
├── 📁 tests/                         # Test suite
├── 📁 docs/                          # Documentation
├── 📁 data/                          # Data files (routes, stops)
├── 📁 logs/                          # Application logs
├── main.py                           # FastAPI application entry point
└── requirements.txt                  # Python dependencies
```

See `PROJECT_STRUCTURE.md` for detailed structure documentation.

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest tests/endpoints/          # API endpoint tests
pytest tests/realtime/           # Real-time feature tests
```

## 🚌 Bus Simulation

Start the bus simulation for testing real-time features:

```bash
# Start simulation with default settings
python scripts/simulation/start_simulation.py

# Start with custom parameters
python scripts/simulation/start_simulation.py --max-buses 10 --interval 3
```

This simulates buses moving along real routes with Mapbox geometry and broadcasts live location updates.

## 🚀 Deployment

### For Production Deployment:

1. **Complete initialization:**
```bash
python scripts/deploy_initialize.py --full
```

2. **Start the application:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

3. **Optional: Start bus simulation:**
```bash
python scripts/simulation/start_simulation.py
```

See `docs/deployment/DEPLOYMENT_GUIDE.md` for detailed deployment instructions.

## 📊 Key Features

### Real-time Tracking
- Live bus location updates every 3-5 seconds
- WebSocket and Socket.IO support
- Proximity-based passenger notifications
- Real road path simulation with Mapbox

### Route Management
- 198 real Addis Ababa bus routes
- 1,340+ bus stops with GPS coordinates
- Mapbox-powered route geometry
- Realistic distance and duration calculations

### User Management
- Multi-role authentication system
- Approval workflows for drivers and regulators
- Attendance tracking with heatmap visualization
- Comprehensive user analytics

### Payment Integration
- Chapa payment gateway integration
- Transaction history and reporting
- Multiple payment methods support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `docs/` directory
- **Issues**: Open an issue on GitHub
- **API Reference**: Visit `/docs` endpoint when running the server

---

**Built with ❤️ for Addis Ababa's public transportation system** 🚌
