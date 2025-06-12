# Real-time Chat System for GuzoSync

This document describes the real-time communication system implemented for GuzoSync, enabling seamless communication between field staff (bus drivers and queue regulators) and control center staff.

## Overview

The chat system provides:
- **Real-time messaging** via WebSockets
- **Role-based access control** ensuring proper communication channels
- **Support conversation creation** for field staff to contact control center
- **Support room monitoring** for control staff to handle multiple requests
- **Message persistence** with real-time delivery
- **Typing indicators** and read receipts for better UX

## Architecture

### Components

1. **WebSocket Event Handlers** (`core/realtime/websocket_events.py`)
   - Handles all chat-related WebSocket events
   - Manages conversation creation, messaging, and room management

2. **Chat Service** (`core/realtime/chat.py`)
   - Core chat functionality and business logic
   - Message broadcasting and room management
   - Support room notifications

3. **WebSocket Manager** (`core/websocket_manager.py`)
   - Manages WebSocket connections and rooms
   - Handles user authentication and connection lifecycle

4. **Database Models** (`models/conversation.py`)
   - Conversation and Message models
   - Persistent storage for chat history

## User Roles and Permissions

### Field Staff (Bus Drivers & Queue Regulators)
- ✅ Create support conversations with control center
- ✅ Send messages in conversations they're part of
- ✅ Join conversation rooms for their conversations
- ✅ Use typing indicators and read receipts
- ❌ Cannot join general support rooms
- ❌ Cannot create conversations with other field staff

### Control Staff & Control Admin
- ✅ Send messages in any conversation they're part of
- ✅ Join support rooms for monitoring field requests
- ✅ Join conversation rooms for their conversations
- ✅ Use typing indicators and read receipts
- ✅ Receive notifications for new support conversations
- ✅ Access role-specific support rooms

## WebSocket Events

### Core Chat Events

1. **create_support_conversation** - Field staff creates new support request
2. **send_chat_message** - Send message to existing conversation
3. **get_active_conversations** - Retrieve user's active conversations
4. **get_conversation_messages** - Get message history for conversation
5. **join_conversation** - Join conversation room for real-time updates
6. **join_support_room** - Control staff joins support monitoring rooms
7. **typing_indicator** - Show typing status to other participants
8. **mark_message_read** - Mark messages as read with receipts

### Support Room Types

- **general_support** - All support requests
- **driver_support** - Bus driver specific requests
- **regulator_support** - Queue regulator specific requests
- **emergency_support** - Emergency situations

## Database Schema

### Conversations Collection
```javascript
{
  "_id": ObjectId,
  "id": "uuid_string",
  "participants": ["user_id_1", "user_id_2", ...],
  "title": "Support: Route Change Request",
  "status": "ACTIVE" | "CLOSED",
  "created_by": "user_id",
  "last_message_at": ISODate,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### Messages Collection
```javascript
{
  "_id": ObjectId,
  "id": "uuid_string", 
  "conversation_id": "conversation_uuid",
  "sender_id": "user_id",
  "content": "Message text",
  "message_type": "TEXT" | "SYSTEM",
  "sent_at": ISODate,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

## Usage Examples

### Frontend Integration

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/api/websocket/connect?token=' + authToken);

// Create support conversation (field staff only)
ws.send(JSON.stringify({
  type: 'create_support_conversation',
  data: {
    title: 'Route Change Request',
    content: 'I need to discuss changing my route due to road construction.'
  }
}));

// Send chat message
ws.send(JSON.stringify({
  type: 'send_chat_message',
  data: {
    conversation_id: 'conv_123',
    content: 'Hello, I need assistance.'
  }
}));

// Join support room (control staff only)
ws.send(JSON.stringify({
  type: 'join_support_room',
  data: {
    room_type: 'general_support'
  }
}));

// Listen for real-time messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'new_message':
      displayMessage(data.message);
      break;
    case 'typing_status':
      updateTypingIndicator(data.user_id, data.is_typing);
      break;
    case 'new_support_conversation':
      notifyNewSupportRequest(data);
      break;
  }
};
```

### Backend API Integration

The chat system integrates with existing REST API endpoints:

- `GET /api/conversations` - Get user's conversations
- `GET /api/conversations/{id}/messages` - Get conversation messages
- `POST /api/conversations/create` - Create new conversation
- `POST /api/conversations/{id}/messages` - Send message via REST

## Testing

### Manual Testing

1. **Start the server**: `uvicorn main:app --reload`
2. **Run test script**: `python tests/test_chat_websocket.py`
3. **Use WebSocket client** to connect and test events

### Test Users Required

Create test users with appropriate roles:
```python
# Bus Driver
{
  "email": "driver1@example.com",
  "password": "password123",
  "role": "BUS_DRIVER"
}

# Control Staff
{
  "email": "control1@example.com", 
  "password": "password123",
  "role": "CONTROL_STAFF"
}
```

## Monitoring and Logging

The system provides comprehensive logging:

- **Connection events** - User connections/disconnections
- **Message events** - Message sending/receiving
- **Room events** - Room joins/leaves
- **Error events** - Failed operations and exceptions

Log levels:
- `INFO` - Normal operations
- `WARNING` - Non-critical issues
- `ERROR` - Critical failures
- `DEBUG` - Detailed debugging information

## Security Considerations

1. **Authentication** - JWT token required for WebSocket connection
2. **Authorization** - Role-based access control for all operations
3. **Conversation Access** - Users can only access conversations they're part of
4. **Input Validation** - All message content is validated
5. **Rate Limiting** - Consider implementing rate limiting for message sending

## Performance Considerations

1. **Connection Management** - Automatic cleanup of disconnected users
2. **Room Management** - Empty rooms are automatically deleted
3. **Message Pagination** - Messages are paginated to prevent large payloads
4. **Database Indexing** - Ensure proper indexes on conversation participants and timestamps

## Future Enhancements

1. **File Attachments** - Support for image/document sharing
2. **Message Reactions** - Emoji reactions to messages
3. **Message Threading** - Reply to specific messages
4. **Push Notifications** - Mobile push notifications for offline users
5. **Message Search** - Full-text search across conversation history
6. **Voice Messages** - Audio message support
7. **Video Calls** - Integration with video calling services

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check JWT token validity
   - Verify server is running
   - Check network connectivity

2. **Messages Not Received**
   - Ensure user is in conversation room
   - Check WebSocket connection status
   - Verify conversation permissions

3. **Support Room Access Denied**
   - Verify user role (only control staff can join)
   - Check authentication status

### Debug Commands

```javascript
// Check connection status
ws.send(JSON.stringify({type: 'ping', timestamp: Date.now()}));

// Get active conversations
ws.send(JSON.stringify({type: 'get_active_conversations', data: {}}));

// Test room joining
ws.send(JSON.stringify({type: 'join_room', room_id: 'test_room'}));
```

For detailed WebSocket event documentation, see `docs/websocket-chat-events.md`.
