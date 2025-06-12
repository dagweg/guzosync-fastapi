# WebSocket Chat Events Documentation

This document describes the WebSocket events for real-time communication between bus drivers/queue regulators and control staff/control admin.

## Connection

Connect to WebSocket endpoint:

```
ws://localhost:8000/api/websocket/connect?token=YOUR_JWT_TOKEN
```

## Chat-Related WebSocket Events

### 1. Send Chat Message

Send a message to an existing conversation.

**Client → Server:**

```json
{
  "type": "send_chat_message",
  "data": {
    "conversation_id": "conv_123",
    "content": "Hello, I need assistance with route changes."
  }
}
```

**Server → Client Response:**

```json
{
  "success": true,
  "message": "Message sent successfully",
  "message_id": "msg_456",
  "conversation_id": "conv_123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Real-time Message Broadcast (to all conversation participants):**

```json
{
  "type": "new_message",
  "conversation_id": "conv_123",
  "message": {
    "id": "msg_456",
    "sender_id": "user_789",
    "content": "Hello, I need assistance with route changes.",
    "message_type": "TEXT",
    "sent_at": "2024-01-15T10:30:00Z"
  }
}
```

### 2. Create Support Conversation

Create a new conversation between field staff and control center.

**Client → Server (Bus Driver/Queue Regulator only):**

```json
{
  "type": "create_support_conversation",
  "data": {
    "title": "Route Change Request",
    "content": "I need to discuss changing my route due to road construction."
  }
}
```

**Server → Client Response:**

```json
{
  "success": true,
  "message": "Support conversation created successfully",
  "conversation_id": "conv_789",
  "title": "Support: Route Change Request",
  "participants": ["user_123", "control_456", "control_789"],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 3. Get Active Conversations

Retrieve all active conversations for the current user.

**Client → Server:**

```json
{
  "type": "get_active_conversations",
  "data": {}
}
```

**Server → Client Response:**

```json
{
  "success": true,
  "conversations": [
    {
      "id": "conv_123",
      "title": "Support: Route Change Request",
      "status": "ACTIVE",
      "created_by": "user_456",
      "last_message_at": "2024-01-15T10:30:00Z",
      "participants": [
        {
          "id": "user_456",
          "email": "driver@example.com",
          "role": "BUS_DRIVER",
          "first_name": "John",
          "last_name": "Doe"
        },
        {
          "id": "control_123",
          "email": "control@example.com",
          "role": "CONTROL_STAFF",
          "first_name": "Jane",
          "last_name": "Smith"
        }
      ],
      "last_message": {
        "id": "msg_789",
        "content": "I'll help you with that route change.",
        "sender_id": "control_123",
        "sent_at": "2024-01-15T10:30:00Z"
      }
    }
  ],
  "count": 1,
  "timestamp": "2024-01-15T10:35:00Z"
}
```

### 4. Join Conversation Room

Join a conversation room to receive real-time messages.

**Client → Server:**

```json
{
  "type": "join_conversation",
  "data": {
    "conversation_id": "conv_123"
  }
}
```

**Server → Client Response:**

```json
{
  "success": true,
  "message": "Joined conversation conv_123",
  "conversation_id": "conv_123"
}
```

### 5. Join Support Room

Join a general support room (Control Staff/Admin only).

**Client → Server (Control Staff/Admin only):**

```json
{
  "type": "join_support_room",
  "data": {
    "room_type": "general_support"
  }
}
```

**Available room types:**

- `general_support` - General support discussions
- `emergency_support` - Emergency situations
- `driver_support` - Driver-specific support
- `regulator_support` - Queue regulator support

**Server → Client Response:**

```json
{
  "success": true,
  "message": "Joined general support room successfully",
  "room_id": "support:general_support",
  "room_type": "general_support",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 6. Typing Indicator

Show when someone is typing in a conversation.

**Client → Server:**

```json
{
  "type": "typing_indicator",
  "data": {
    "conversation_id": "conv_123",
    "is_typing": true
  }
}
```

**Server → Client Response:**

```json
{
  "success": true
}
```

**Real-time Typing Broadcast (to other conversation participants):**

```json
{
  "type": "typing_status",
  "conversation_id": "conv_123",
  "user_id": "user_456",
  "is_typing": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 7. Get Conversation Messages

Retrieve messages from a specific conversation.

**Client → Server:**

```json
{
  "type": "get_conversation_messages",
  "data": {
    "conversation_id": "conv_123",
    "limit": 50,
    "skip": 0
  }
}
```

**Server → Client Response:**

```json
{
  "success": true,
  "messages": [
    {
      "id": "msg_123",
      "conversation_id": "conv_123",
      "sender_id": "user_456",
      "content": "Hello, I need assistance.",
      "message_type": "TEXT",
      "sent_at": "2024-01-15T10:25:00Z"
    },
    {
      "id": "msg_124",
      "conversation_id": "conv_123",
      "sender_id": "control_789",
      "content": "How can I help you?",
      "message_type": "TEXT",
      "sent_at": "2024-01-15T10:26:00Z"
    }
  ],
  "count": 2,
  "conversation_id": "conv_123"
}
```

### 8. Mark Message as Read

Mark a message as read and notify other participants.

**Client → Server:**

```json
{
  "type": "mark_message_read",
  "data": {
    "conversation_id": "conv_123",
    "message_id": "msg_456"
  }
}
```

**Server → Client Response:**

```json
{
  "success": true
}
```

**Real-time Read Receipt Broadcast (to other conversation participants):**

```json
{
  "type": "message_read",
  "conversation_id": "conv_123",
  "user_id": "user_789",
  "message_id": "msg_456",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Role-Based Access Control

### Bus Drivers & Queue Regulators Can:

- Create support conversations with control center
- Send messages in conversations they're part of
- Join conversation rooms for conversations they're participants in
- Use typing indicators and read receipts

### Control Staff & Control Admin Can:

- Send messages in any conversation they're part of
- Join support rooms for monitoring field staff requests
- Join conversation rooms for conversations they're participants in
- Use typing indicators and read receipts
- Receive notifications when new support conversations are created

## Error Responses

All events can return error responses:

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

Common error scenarios:

- User not authenticated
- Insufficient permissions for the requested action
- Conversation not found or access denied
- Missing required parameters
- Database connection issues

## Integration Example

```javascript
// Connect to WebSocket
const ws = new WebSocket(
  "ws://localhost:8000/api/websocket/connect?token=" + authToken
);

// Send a chat message
ws.send(
  JSON.stringify({
    type: "send_chat_message",
    data: {
      conversation_id: "conv_123",
      content: "Hello, I need help with my route.",
    },
  })
);

// Listen for real-time messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "new_message") {
    // Display new message in chat UI
    displayMessage(data.message);
  } else if (data.type === "typing_status") {
    // Show/hide typing indicator
    updateTypingIndicator(data.user_id, data.is_typing);
  }
};
```
