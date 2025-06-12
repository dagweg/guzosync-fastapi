# Conversation API Guide

This document explains how conversations are created and managed in the GuzoSync chat system.

## Overview

The conversation system enables communication between field staff (bus drivers and queue regulators) and control center staff through both REST API endpoints and real-time WebSocket events.

## How Conversations Are Created

### 1. **Field Staff Initiated (Primary Method)**

**Who can create:** Bus Drivers and Queue Regulators only

**Endpoint:** `POST /api/conversations/create`

**Process:**
1. Field staff member creates a support conversation
2. System automatically adds ALL active control center staff as participants
3. Initial message is sent with the conversation
4. Real-time notifications are sent to control center

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/conversations/create" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Route Change Request",
    "content": "I need assistance with changing my route due to road construction."
  }'
```

**Response:**
```json
{
  "id": "conv_uuid_123",
  "participants": ["driver_id", "control_staff_1", "control_staff_2"],
  "title": "Route Change Request",
  "status": "ACTIVE",
  "created_by": "driver_id",
  "last_message_at": "2024-01-15T10:30:00Z"
}
```

### 2. **WebSocket Method (Real-time)**

**Event:** `create_support_conversation`

**Example:**
```javascript
ws.send(JSON.stringify({
  type: 'create_support_conversation',
  data: {
    title: 'Emergency Route Issue',
    content: 'Bus breakdown on Route 5, need immediate assistance'
  }
}));
```

## API Endpoints

### 1. **Create Conversation**
- **Method:** `POST /api/conversations/create`
- **Auth:** Required (Field staff only)
- **Body:** `CreateConversationRequest`

### 2. **Get User's Conversations**
- **Method:** `GET /api/conversations`
- **Auth:** Required
- **Query Params:** `skip`, `limit`
- **Returns:** List of conversations user is part of

### 3. **Get Conversation Messages**
- **Method:** `GET /api/conversations/{conversation_id}/messages`
- **Auth:** Required (Must be conversation participant)
- **Query Params:** `skip`, `limit`
- **Returns:** List of messages in conversation

### 4. **Send Message**
- **Method:** `POST /api/conversations/{conversation_id}/messages`
- **Auth:** Required (Must be conversation participant)
- **Body:** `SendMessageRequest`

### 5. **Close Conversation**
- **Method:** `POST /api/conversations/{conversation_id}/close`
- **Auth:** Required (Control staff only)

### 6. **Get Chat Statistics**
- **Method:** `GET /api/conversations/stats`
- **Auth:** Required (Control staff only)

## Access Control Rules

### Field Staff (Bus Drivers & Queue Regulators)
- ✅ **Can create** conversations with control center
- ✅ **Can send messages** in conversations they're part of
- ✅ **Can view** their own conversations and messages
- ❌ **Cannot close** conversations
- ❌ **Cannot create** conversations with other field staff
- ❌ **Cannot view** chat statistics

### Control Staff & Control Admin
- ❌ **Cannot create** new conversations (only respond to existing ones)
- ✅ **Can send messages** in any conversation they're part of
- ✅ **Can view** all conversations they're part of
- ✅ **Can close** conversations
- ✅ **Can view** chat statistics
- ✅ **Automatically added** to all new support conversations

## Database Schema

### Conversations Collection
```javascript
{
  "_id": "conv_uuid_123",           // MongoDB document ID (same as id)
  "id": "conv_uuid_123",            // Primary UUID identifier
  "participants": [                 // Array of user UUIDs
    "user_uuid_1",
    "user_uuid_2"
  ],
  "title": "Support: Route Change Request",
  "status": "ACTIVE",               // ACTIVE | CLOSED
  "created_by": "user_uuid_1",      // Creator's UUID
  "last_message_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T10:25:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Messages Collection
```javascript
{
  "_id": "msg_uuid_456",            // MongoDB document ID (same as id)
  "id": "msg_uuid_456",             // Primary UUID identifier
  "conversation_id": "conv_uuid_123", // Reference to conversation
  "sender_id": "user_uuid_1",       // Sender's UUID
  "content": "Message text content",
  "message_type": "TEXT",           // TEXT | SYSTEM
  "sent_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Real-time Integration

### WebSocket Events
- **Conversation Creation:** Triggers real-time notifications to control center
- **Message Sending:** Broadcasts to all conversation participants
- **Typing Indicators:** Shows when users are typing
- **Read Receipts:** Confirms message delivery

### Support Room Notifications
Control staff can join support rooms to monitor new conversations:
- `support:general_support` - All support requests
- `support:driver_support` - Driver-specific issues
- `support:regulator_support` - Queue regulator issues
- `support:emergency_support` - Emergency situations

## Testing the API

### Prerequisites
1. **Server running:** `uvicorn main:app --reload`
2. **Test users created** with appropriate roles:
   - Bus Driver: `driver1@example.com`
   - Control Staff: `control1@example.com`

### Run Tests
```bash
# Test REST API endpoints
python tests/test_conversation_api.py

# Test WebSocket functionality
python examples/chat_demo.py
```

## Common Issues and Solutions

### 1. **Conversation Not Found**
- **Cause:** Using wrong conversation ID format
- **Solution:** Ensure using UUID string, not MongoDB ObjectId

### 2. **Access Denied**
- **Cause:** User not in conversation participants
- **Solution:** Verify user is part of conversation

### 3. **Control Staff Can't Create Conversations**
- **Cause:** By design - only field staff can initiate
- **Solution:** Field staff must create, control staff responds

### 4. **Messages Not Appearing**
- **Cause:** Database field mapping issues
- **Solution:** Verify using `id` field instead of `_id`

## API Response Examples

### Successful Conversation Creation
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "participants": [
    "driver_uuid_123",
    "control_uuid_456",
    "control_uuid_789"
  ],
  "title": "Support: Route Change Request",
  "status": "ACTIVE",
  "created_by": "driver_uuid_123",
  "last_message_at": "2024-01-15T10:30:00.000Z",
  "created_at": "2024-01-15T10:30:00.000Z",
  "updated_at": "2024-01-15T10:30:00.000Z"
}
```

### Message List Response
```json
[
  {
    "id": "msg_uuid_001",
    "conversation_id": "conv_uuid_123",
    "sender_id": "driver_uuid_123",
    "content": "I need assistance with my route",
    "message_type": "TEXT",
    "sent_at": "2024-01-15T10:30:00.000Z",
    "created_at": "2024-01-15T10:30:00.000Z",
    "updated_at": "2024-01-15T10:30:00.000Z"
  },
  {
    "id": "msg_uuid_002",
    "conversation_id": "conv_uuid_123",
    "sender_id": "control_uuid_456",
    "content": "How can I help you?",
    "message_type": "TEXT",
    "sent_at": "2024-01-15T10:31:00.000Z",
    "created_at": "2024-01-15T10:31:00.000Z",
    "updated_at": "2024-01-15T10:31:00.000Z"
  }
]
```

### Error Response
```json
{
  "detail": "Your role is not authorized to use the chat system"
}
```

## Integration with Frontend

### React/Next.js Example
```javascript
// Create conversation
const createConversation = async (title, content) => {
  const response = await fetch('/api/conversations/create', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ title, content })
  });
  
  return response.json();
};

// Get conversations
const getConversations = async () => {
  const response = await fetch('/api/conversations', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
};

// Send message
const sendMessage = async (conversationId, content) => {
  const response = await fetch(`/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ content, message_type: 'TEXT' })
  });
  
  return response.json();
};
```

The conversation API is now fully functional with proper UUID handling and field mapping!
