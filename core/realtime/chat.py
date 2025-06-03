"""
Real-time chat/conversation service
"""
from datetime import datetime
from uuid import UUID
from core.websocket_manager import websocket_manager
from core.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """Service for real-time chat/conversations"""
    
    @staticmethod
    async def send_real_time_message(
        conversation_id: UUID,
        sender_id: UUID,
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
                    "sent_at": datetime.utcnow().isoformat()
                }
            }
            
            # Send to conversation room
            room_id = f"conversation:{conversation_id}"
            await websocket_manager.send_room_message(
                room_id, 
                websocket_message, 
                exclude_user=str(sender_id)  # Don't send back to sender
            )
            
            # Send individual notifications to participants who aren't in the room
            for participant_id in participants:
                if str(participant_id) != str(sender_id):
                    # Check if user is in the conversation room
                    room_users = websocket_manager.get_room_users(room_id)
                    if str(participant_id) not in room_users:
                        # Send as personal notification
                        notification_message = {
                            "type": "message_notification",
                            "conversation_id": str(conversation_id),
                            "from_user_id": str(sender_id),
                            "preview": content[:100] + "..." if len(content) > 100 else content,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket_manager.send_personal_message(
                            str(participant_id), 
                            notification_message
                        )
            
            logger.info(f"Sent real-time message in conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error sending real-time message: {e}")
    
    @staticmethod
    async def join_conversation(user_id: str, conversation_id: UUID, app_state=None):
        """Join user to a conversation room"""
        try:
            # Verify user is participant in conversation
            if app_state and app_state.mongodb:
                conversation = await app_state.mongodb.conversations.find_one({
                    "id": conversation_id,
                    "participants": UUID(user_id)
                })
                
                if not conversation:
                    logger.warning(f"User {user_id} not authorized for conversation {conversation_id}")
                    return False
            
            # Join conversation room
            room_id = f"conversation:{conversation_id}"
            websocket_manager.join_room(user_id, room_id)
            
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
    def leave_conversation(user_id: str, conversation_id: UUID):
        """Remove user from conversation room"""
        room_id = f"conversation:{conversation_id}"
        websocket_manager.leave_room(user_id, room_id)
        logger.info(f"User {user_id} left conversation {conversation_id}")
    
    @staticmethod
    async def notify_typing(conversation_id: UUID, user_id: str, is_typing: bool):
        """Notify conversation participants about typing status"""
        try:
            room_id = f"conversation:{conversation_id}"
            message = {
                "type": "typing_status",
                "conversation_id": str(conversation_id),
                "user_id": user_id,
                "is_typing": is_typing,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_room_message(
                room_id, 
                message, 
                exclude_user=user_id  # Don't send back to typing user
            )
            
        except Exception as e:
            logger.error(f"Error sending typing notification: {e}")
    
    @staticmethod
    async def notify_message_read(conversation_id: UUID, user_id: str, message_id: str):
        """Notify when a message has been read"""
        try:
            room_id = f"conversation:{conversation_id}"
            message = {
                "type": "message_read",
                "conversation_id": str(conversation_id),
                "user_id": user_id,
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_room_message(
                room_id, 
                message, 
                exclude_user=user_id
            )
            
        except Exception as e:
            logger.error(f"Error sending message read notification: {e}")


# Global chat service instance
chat_service = ChatService()
