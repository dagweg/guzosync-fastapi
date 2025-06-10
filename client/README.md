# GuzoSync Client - FastAPI Real-time Testing Frontend

A Next.js webapp with Mapbox integration specifically designed to test the real-time WebSocket and REST API features of your GuzoSync FastAPI backend. This is a pure frontend client that connects directly to your Python backend.

## Features

### 🗺️ Interactive Map

- **Mapbox Integration**: High-quality maps with real-time bus tracking
- **Live Bus Locations**: Real-time updates via WebSocket connections
- **Bus Status Visualization**: Color-coded markers for different bus statuses
- **Bus Stop Display**: Interactive markers for all bus stops
- **Admin Location Updates**: Click-to-update bus locations (admin only)

### 🚌 Bus Tracking

- **Real-time Updates**: Live bus location, speed, and heading data
- **Bus Search**: Filter buses by license plate or model
- **Status Monitoring**: Track operational, idle, maintenance, and breakdown statuses
- **Historical Data**: View last known locations and update times

### 💬 Real-time Chat

- **Multiple Channels**: General, route-specific, and emergency channels
- **Live Messaging**: Real-time message delivery via WebSocket
- **User Presence**: See active participants in each channel
- **Message History**: Persistent chat history

### 🔔 Notifications

- **Real-time Alerts**: Instant notifications for system events
- **Priority Levels**: Critical, high, medium, and low priority notifications
- **Filtering**: Filter by notification type (trip updates, route alerts, etc.)
- **Historical View**: Access to past notifications

### 🔐 Authentication

- **JWT-based Auth**: Secure token-based authentication
- **Role-based Access**: Different features for passengers, drivers, and admins
- **Auto-reconnection**: Automatic WebSocket reconnection with token refresh

## Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Maps**: Mapbox GL JS
- **Real-time**: WebSocket connections
- **HTTP Client**: Axios
- **State Management**: Zustand
- **Notifications**: React Hot Toast
- **Icons**: Lucide React

## Getting Started

### Prerequisites

1. **FastAPI Backend Running**: Ensure your GuzoSync FastAPI backend is running on `http://localhost:8000`
   - Start your FastAPI server: `uvicorn main:app --reload --port 8000`
   - Verify it's accessible at `http://localhost:8000/docs`
2. **Database with Demo Data**: Make sure your backend has demo users and bus data
3. **Mapbox Token**: Get a free Mapbox access token from [mapbox.com](https://mapbox.com)

### Installation

1. **Navigate to client directory**:

   ```bash
   cd client
   ```

2. **Install dependencies**:

   ```bash
   npm install
   ```

3. **Configure environment variables**:

   ```bash
   cp .env.local.example .env.local
   ```

   Update `.env.local` with your Mapbox token:

   ```env
   MAPBOX_ACCESS_TOKEN=your_actual_mapbox_token_here
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
   ```

4. **Start the development server**:

   ```bash
   npm run dev
   ```

5. **Open your browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Demo Credentials

Use the credentials from your FastAPI backend database. If you haven't created demo users yet, you can:

1. **Use the registration endpoint** to create test users
2. **Check your backend's demo data initialization**
3. **Use the default credentials** (if configured in your backend):
   - Example: `admin@example.com` / `password123`

**Note**: The credentials depend on your FastAPI backend's demo data setup.

## Testing Real-time Features

### Bus Tracking

1. Login as any user
2. Navigate to the Map view
3. Select a bus from the Bus Tracker panel
4. Watch for real-time location updates (green "Live" indicator)

### Admin Location Updates

1. Login as admin (`admin@guzosync.com`)
2. Select a bus from the tracker
3. Click anywhere on the map to update the bus location
4. See the update broadcast to all connected clients

### Chat System

1. Navigate to the Chat panel
2. Join different conversation channels
3. Send messages and see real-time delivery
4. Open multiple browser tabs to test multi-user chat

### Notifications

1. Navigate to the Notifications panel
2. Watch for real-time system notifications
3. Filter by notification type
4. Test different priority levels

## WebSocket Events

The client subscribes to these WebSocket events:

- `bus_location_update`: Real-time bus position updates
- `chat_message`: Live chat messages
- `notification`: System notifications
- `room_joined`/`room_left`: Room management confirmations
- `ping`/`pong`: Connection heartbeat

## API Integration

The client integrates with these backend endpoints:

- **Authentication**: `/api/accounts/login`, `/api/accounts/logout`
- **User Data**: `/api/account/me`
- **Bus Data**: `/api/buses`, `/api/buses/{id}`
- **Routes**: `/api/routes`
- **Bus Stops**: `/api/buses/stops`
- **Chat**: `/api/conversations/{id}/messages`
- **Notifications**: `/api/notifications`

## Project Structure

```
client/
├── src/
│   ├── app/                 # Next.js app router pages
│   │   ├── layout.tsx       # Root layout with providers
│   │   ├── page.tsx         # Main dashboard
│   │   └── login/           # Authentication pages
│   ├── components/          # React components
│   │   ├── Map.tsx          # Mapbox map component
│   │   ├── BusTracker.tsx   # Bus tracking sidebar
│   │   ├── ChatPanel.tsx    # Real-time chat interface
│   │   ├── NotificationPanel.tsx # Notifications display
│   │   └── WebSocketProvider.tsx # WebSocket context
│   ├── lib/                 # Utility libraries
│   │   ├── api.ts           # HTTP API client
│   │   └── websocket.ts     # WebSocket client class
│   └── types/               # TypeScript type definitions
├── public/                  # Static assets
└── package.json            # Dependencies and scripts
```

## Development Tips

### Testing WebSocket Connections

- Open browser dev tools → Network tab → WS filter to monitor WebSocket traffic
- Use the connection status indicator in the header
- Check console logs for WebSocket events

### Testing Different User Roles

- Use different browser profiles or incognito windows
- Admin users can update bus locations by clicking on the map
- Different roles see different UI elements

### Debugging API Issues

- Check the Network tab for failed HTTP requests
- Verify the backend is running on the correct port
- Ensure JWT tokens are being sent with requests

## Troubleshooting

### Common Issues

1. **Map not loading**: Check your Mapbox access token in `.env.local`
2. **WebSocket connection failed**: Verify backend is running and WebSocket endpoint is accessible
3. **Authentication errors**: Check if backend JWT configuration matches
4. **API requests failing**: Verify backend URL in environment variables

### Browser Console Errors

- Check for CORS issues if running on different domains
- Verify all environment variables are properly set
- Look for WebSocket connection errors in the console

## Contributing

1. Follow the existing code structure and naming conventions
2. Add TypeScript types for new features
3. Test real-time features with multiple browser windows
4. Update this README when adding new features

## License

This project is part of the GuzoSync bus tracking system.
