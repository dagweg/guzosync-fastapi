"""
Real-time chat/conversation service
"""
from datetime import datetime, timezone

from core.websocket_manager import websocket_manager
from core.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """Service for real-time chat/conversations"""
    
    @staticmethod
    async def send_real_time_message(
        conversation_id: str,
        sender_id: str,
        content: str,
        message_id: str,
        message_type: str = "TEXT",
        app_state=None
    ):
        """Send real-time message to conversation participants"""
        try:
            # Get conversation participants
            participants = []
            if app_state and app_state.mongodb:
                conversation = await app_state.mongodb.conversations.find_one({"id": conversation_id})
                if conversation:
                    participants = conversation.get("participants", [])
            
            # Create real-time message
            websocket_message = {
                "type": "new_message",
                "conversation_id": str(conversation_id),
                "message": {
                    "id": message_id,
                    "sender_id": str(sender_id),
                    "content": content,
                    "message_type": message_type,
                    "sent_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Send to conversation room
            room_id = f"conversation:{conversation_id}"
            ws_message = {
                "type": "new_message",
                **websocket_message
            }
            await websocket_manager.send_room_message(
                room_id,
                ws_message,
                exclude_user=str(sender_id)  # Don't send back to sender
            )

            # Send individual notifications to participants who aren't in the room
            for participant_id in participants:
                if str(participant_id) != str(sender_id):
                    # Check if user is in the conversation room
                    room_users = websocket_manager.get_users_in_room(room_id)
                    if str(participant_id) not in room_users:
                        # Send as personal notification
                        notification_message = {
                            "type": "message_notification",
                            "conversation_id": str(conversation_id),
                            "from_user_id": str(sender_id),
                            "preview": content[:100] + "..." if len(content) > 100 else content,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await websocket_manager.send_personal_message(
                            str(participant_id),
                            notification_message
                        )
            
            logger.info(f"Sent real-time message in conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error sending real-time message: {e}")
    
    @staticmethod
    async def join_conversation(user_id: str, conversation_id: str, app_state=None):
        """Join user to a conversation room"""
        try:
            # Verify user is participant in conversation
            if app_state and app_state.mongodb:
                conversation = await app_state.mongodb.conversations.find_one({
                    "id": conversation_id,
                    "participants": {"$in": [str(user_id)]}
                })

                if not conversation:
                    logger.warning(f"User {user_id} not authorized for conversation {conversation_id}")
                    return False
            
            # Join conversation room
            room_id = f"conversation:{conversation_id}"
            await websocket_manager.join_room_user(user_id, room_id)

            # Send confirmation
            message = {
                "type": "conversation_joined",
                "conversation_id": str(conversation_id),
                "room_id": room_id,
                "message": f"Joined conversation {conversation_id}"
            }

            await websocket_manager.send_personal_message(user_id, message)
            logger.info(f"User {user_id} joined conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error joining conversation: {e}")
            return False
    
    @staticmethod
    async def leave_conversation(user_id: str, conversation_id: str):
        """Remove user from conversation room"""
        room_id = f"conversation:{conversation_id}"
        await websocket_manager.leave_room_user(user_id, room_id)
        logger.info(f"User {user_id} left conversation {conversation_id}")
    
    @staticmethod
    async def notify_typing(conversation_id: str, user_id: str, is_typing: bool):
        """Notify conversation participants about typing status"""
        try:
            room_id = f"conversation:{conversation_id}"
            message = {
                "type": "typing_status",
                "conversation_id": str(conversation_id),
                "user_id": user_id,
                "is_typing": is_typing,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            ws_message = {
                "type": "typing_status",
                **message
            }
            await websocket_manager.send_room_message(
                room_id,
                ws_message,
                exclude_user=user_id  # Don't send back to typing user
            )
            
        except Exception as e:
            logger.error(f"Error sending typing notification: {e}")
    
    @staticmethod
    async def notify_message_read(conversation_id: str, user_id: str, message_id: str):
        """Notify when a message has been read"""
        try:
            room_id = f"conversation:{conversation_id}"
            message = {
                "type": "message_read",
                "conversation_id": str(conversation_id),
                "user_id": user_id,
                "message_id": message_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            ws_message = {
                "type": "message_read",
                **message
            }
            await websocket_manager.send_room_message(
                room_id,
                ws_message,
                exclude_user=user_id
            )
            
        except Exception as e:
            logger.error(f"Error sending message read notification: {e}")

    @staticmethod
    async def broadcast_to_support_room(room_type: str, message: dict, exclude_user: str = ""):
        """Broadcast message to a specific support room"""
        try:
            room_id = f"support:{room_type}"
            await websocket_manager.send_room_message(room_id, message, exclude_user)
            logger.info(f"Broadcasted message to support room: {room_type}")
        except Exception as e:
            logger.error(f"Error broadcasting to support room {room_type}: {e}")

    @staticmethod
    async def notify_control_center_new_conversation(conversation_id: str, title: str, creator_id: str, app_state=None):
        """Notify control center staff about new support conversations"""
        try:
            # Get creator details
            creator_name = "Field Staff"
            creator_role = "UNKNOWN"

            if app_state and app_state.mongodb:
                creator = await app_state.mongodb.users.find_one({"id": creator_id})
                if creator:
                    creator_name = f"{creator.get('first_name', '')} {creator.get('last_name', '')}".strip()
                    if not creator_name:
                        creator_name = creator.get('email', 'Field Staff')
                    creator_role = creator.get('role', 'UNKNOWN')

            # Create notification message
            notification = {
                "type": "new_support_conversation",
                "conversation_id": conversation_id,
                "title": title,
                "creator_id": creator_id,
                "creator_name": creator_name,
                "creator_role": creator_role,
                "message": f"New support request from {creator_name} ({creator_role}): {title}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Broadcast to general support room
            await ChatService.broadcast_to_support_room("general_support", notification)

            # Also send to role-specific support room
            if creator_role == "BUS_DRIVER":
                await ChatService.broadcast_to_support_room("driver_support", notification)
            elif creator_role == "QUEUE_REGULATOR":
                await ChatService.broadcast_to_support_room("regulator_support", notification)

            logger.info(f"Notified control center about new conversation: {conversation_id}")

        except Exception as e:
            logger.error(f"Error notifying control center about new conversation: {e}")

    @staticmethod
    async def get_conversation_messages(conversation_id: str, user_id: str, limit: int = 50, skip: int = 0, app_state=None):
        """Get messages from a conversation with real-time delivery"""
        try:
            messages = []

            if app_state and app_state.mongodb:
                # Verify user has access to conversation
                conversation = await app_state.mongodb.conversations.find_one({
                    "id": conversation_id,
                    "participants": {"$in": [user_id]}
                })

                if not conversation:
                    logger.warning(f"User {user_id} not authorized for conversation {conversation_id}")
                    return {"success": False, "error": "Conversation not found or access denied"}

                # Get messages
                message_docs = await app_state.mongodb.messages.find({
                    "conversation_id": conversation_id
                }).sort("sent_at", -1).skip(skip).limit(limit).to_list(length=limit)

                # Transform messages
                for msg_doc in reversed(message_docs):  # Reverse to get chronological order
                    messages.append({
                        "id": msg_doc.get("id", str(msg_doc.get("_id", ""))),
                        "conversation_id": msg_doc.get("conversation_id", ""),
                        "sender_id": msg_doc.get("sender_id", ""),
                        "content": msg_doc.get("content", ""),
                        "message_type": msg_doc.get("message_type", "TEXT"),
                        "sent_at": msg_doc.get("sent_at", "").isoformat() if msg_doc.get("sent_at") else None
                    })

            return {
                "success": True,
                "messages": messages,
                "count": len(messages),
                "conversation_id": conversation_id
            }

        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            return {"success": False, "error": str(e)}


# Global chat service instance
chat_service = ChatService()
