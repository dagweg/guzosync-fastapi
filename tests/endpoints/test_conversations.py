import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from fastapi import status
from uuid import uuid4

from tests.conftest import TestFixtures


class TestConversationsRouter:
    """Test cases for conversations router endpoints."""

    @pytest.mark.asyncio
    async def test_get_conversations_empty(
        self, passenger_client: AsyncClient
    ):
        """Test retrieving conversations when none exist."""
        response = await passenger_client.get("/api/conversations")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_conversations_with_data(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test retrieving conversations with data."""
        # Create test conversations
        conversations = [
            {
                "_id": test_fixtures.object_ids[0],
                "id": test_fixtures.uuids[0],
                "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
                "last_message_at": datetime.utcnow()
            },
            {
                "_id": test_fixtures.object_ids[1],
                "id": test_fixtures.uuids[1],
                "participants": [test_fixtures.passenger_user["_id"], test_fixtures.driver_user["_id"]],
                "last_message_at": datetime.utcnow() - timedelta(hours=1)
            }
        ]
        
        await mongodb.conversations.insert_many(conversations)
        
        response = await passenger_client.get("/api/conversations")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        # Should be sorted by last_message_at descending
        assert data[0]["id"] == str(test_fixtures.uuids[0])
        assert data[1]["id"] == str(test_fixtures.uuids[1])

    @pytest.mark.asyncio
    async def test_get_conversations_only_user_conversations(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test that only conversations where user is participant are returned."""
        conversations = [
            {
                "_id": test_fixtures.object_ids[0],
                "id": test_fixtures.uuids[0],
                "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
                "last_message_at": datetime.utcnow()
            },
            {
                "_id": test_fixtures.object_ids[1],
                "id": test_fixtures.uuids[1],
                "participants": [test_fixtures.admin_user["_id"], test_fixtures.driver_user["_id"]],  # Passenger not in this one
                "last_message_at": datetime.utcnow()
            }
        ]
        
        await mongodb.conversations.insert_many(conversations)
        
        response = await passenger_client.get("/api/conversations")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(test_fixtures.uuids[0])

    @pytest.mark.asyncio
    async def test_get_conversations_pagination(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test conversations pagination."""
        # Create multiple conversations
        conversations = []
        for i in range(15):
            conversations.append({
                "_id": test_fixtures.object_ids[i % len(test_fixtures.object_ids)],
                "id": test_fixtures.uuids[i % len(test_fixtures.uuids)],
                "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
                "last_message_at": datetime.utcnow() - timedelta(minutes=i)
            })
        
        await mongodb.conversations.insert_many(conversations)
        
        # Test first page
        response = await passenger_client.get("/api/conversations?skip=0&limit=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 5
        
        # Test second page
        response = await passenger_client.get("/api/conversations?skip=5&limit=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_get_conversations_unauthorized(
        self, test_client: AsyncClient
    ):
        """Test retrieving conversations without authentication."""
        response = await test_client.get("/api/conversations")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_conversation_messages_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test retrieving messages from a conversation."""
        # Create test conversation
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
            "last_message_at": datetime.utcnow()
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        # Create test messages
        messages = [
            {
                "_id": test_fixtures.object_ids[1],
                "id": test_fixtures.uuids[1],
                "conversation_id": test_fixtures.uuids[0],
                "sender_id": test_fixtures.passenger_user["_id"],
                "content": "Hello!",
                "message_type": "TEXT",
                "sent_at": datetime.utcnow() - timedelta(minutes=2)
            },
            {
                "_id": test_fixtures.object_ids[2],
                "id": test_fixtures.uuids[2],
                "conversation_id": test_fixtures.uuids[0],
                "sender_id": test_fixtures.admin_user["_id"],
                "content": "Hi there!",
                "message_type": "TEXT",
                "sent_at": datetime.utcnow() - timedelta(minutes=1)
            }
        ]
        
        await mongodb.messages.insert_many(messages)
        
        response = await passenger_client.get(f"/api/conversations/{test_fixtures.uuids[0]}/messages")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        # Should be sorted by sent_at descending
        assert data[0]["content"] == "Hi there!"
        assert data[1]["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_get_conversation_messages_not_participant(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test retrieving messages from conversation where user is not participant."""
        # Create conversation without passenger as participant
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.admin_user["_id"], test_fixtures.driver_user["_id"]],
            "last_message_at": datetime.utcnow()
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        response = await passenger_client.get(f"/api/conversations/{test_fixtures.uuids[0]}/messages")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_conversation_messages_not_found(
        self, passenger_client: AsyncClient
    ):
        """Test retrieving messages from non-existent conversation."""
        response = await passenger_client.get(f"/api/conversations/{uuid4()}/messages")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_conversation_messages_pagination(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test message pagination."""
        # Create test conversation
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
            "last_message_at": datetime.utcnow()
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        # Create multiple messages
        messages = []
        for i in range(15):
            messages.append({
                "_id": test_fixtures.object_ids[i % len(test_fixtures.object_ids)],
                "id": test_fixtures.uuids[i % len(test_fixtures.uuids)],
                "conversation_id": test_fixtures.uuids[0],
                "sender_id": test_fixtures.passenger_user["_id"],
                "content": f"Message {i}",
                "message_type": "TEXT",
                "sent_at": datetime.utcnow() - timedelta(minutes=i)
            })
        
        await mongodb.messages.insert_many(messages)
        
        # Test first page
        response = await passenger_client.get(f"/api/conversations/{test_fixtures.uuids[0]}/messages?skip=0&limit=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_send_message_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test sending a message successfully."""
        # Create test conversation
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
            "last_message_at": datetime.utcnow() - timedelta(hours=1)
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        message_data = {
            "content": "Hello, this is a test message!",
            "message_type": "TEXT"
        }
        
        response = await passenger_client.post(
            f"/api/conversations/{test_fixtures.uuids[0]}/messages", 
            json=message_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"] == "Hello, this is a test message!"
        assert data["message_type"] == "TEXT"
        assert data["sender_id"] == str(test_fixtures.passenger_user["_id"])
        assert data["conversation_id"] == str(test_fixtures.uuids[0])

    @pytest.mark.asyncio
    async def test_send_message_updates_conversation_timestamp(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test that sending a message updates conversation last_message_at."""
        old_timestamp = datetime.utcnow() - timedelta(hours=1)
        
        # Create test conversation
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
            "last_message_at": old_timestamp
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        message_data = {
            "content": "Test message",
            "message_type": "TEXT"
        }
        
        before_send = datetime.utcnow()
        
        response = await passenger_client.post(
            f"/api/conversations/{test_fixtures.uuids[0]}/messages", 
            json=message_data
        )
        
        after_send = datetime.utcnow()
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check that conversation timestamp was updated
        updated_conversation = await mongodb.conversations.find_one({"id": test_fixtures.uuids[0]})
        assert updated_conversation["last_message_at"] > old_timestamp
        assert before_send <= updated_conversation["last_message_at"] <= after_send

    @pytest.mark.asyncio
    async def test_send_message_not_participant(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test sending message to conversation where user is not participant."""
        # Create conversation without passenger as participant
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.admin_user["_id"], test_fixtures.driver_user["_id"]],
            "last_message_at": datetime.utcnow()
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        message_data = {
            "content": "Test message",
            "message_type": "TEXT"
        }
        
        response = await passenger_client.post(
            f"/api/conversations/{test_fixtures.uuids[0]}/messages", 
            json=message_data
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_send_message_conversation_not_found(
        self, passenger_client: AsyncClient
    ):
        """Test sending message to non-existent conversation."""
        message_data = {
            "content": "Test message",
            "message_type": "TEXT"
        }
        
        response = await passenger_client.post(
            f"/api/conversations/{uuid4()}/messages", 
            json=message_data
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_send_message_invalid_data(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test sending message with invalid data."""
        # Create test conversation
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
            "last_message_at": datetime.utcnow()
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        # Missing content
        message_data = {
            "message_type": "TEXT"
        }
        
        response = await passenger_client.post(
            f"/api/conversations/{test_fixtures.uuids[0]}/messages", 
            json=message_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_send_message_empty_content(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test sending message with empty content."""
        # Create test conversation
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
            "last_message_at": datetime.utcnow()
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        message_data = {
            "content": "",
            "message_type": "TEXT"
        }
        
        response = await passenger_client.post(
            f"/api/conversations/{test_fixtures.uuids[0]}/messages", 
            json=message_data
        )
        
        # Might succeed with empty content depending on validation
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]

    @pytest.mark.asyncio
    async def test_send_message_default_type(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test sending message with default message type."""
        # Create test conversation
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
            "last_message_at": datetime.utcnow()
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        message_data = {
            "content": "Test message without type"
        }
        
        response = await passenger_client.post(
            f"/api/conversations/{test_fixtures.uuids[0]}/messages", 
            json=message_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["message_type"] == "TEXT"

    @pytest.mark.asyncio
    async def test_message_timestamp_accuracy(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test that message timestamp is accurate."""
        # Create test conversation
        conversation = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
            "last_message_at": datetime.utcnow()
        }
        
        await mongodb.conversations.insert_one(conversation)
        
        before_send = datetime.utcnow()
        
        message_data = {
            "content": "Timestamp test message",
            "message_type": "TEXT"
        }
        
        response = await passenger_client.post(
            f"/api/conversations/{test_fixtures.uuids[0]}/messages", 
            json=message_data
        )
        
        after_send = datetime.utcnow()
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Parse timestamp and verify it's within the request window
        timestamp = datetime.fromisoformat(data["sent_at"].replace('Z', '+00:00'))
        timestamp = timestamp.replace(tzinfo=None)  # Remove timezone for comparison
        
        assert before_send <= timestamp <= after_send

    @pytest.mark.asyncio
    async def test_conversations_sorted_by_last_message(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test that conversations are sorted by last message time."""
        base_time = datetime.utcnow()
        
        conversations = [
            {
                "_id": test_fixtures.object_ids[0],
                "id": test_fixtures.uuids[0],
                "participants": [test_fixtures.passenger_user["_id"], test_fixtures.admin_user["_id"]],
                "last_message_at": base_time - timedelta(hours=2)  # Older
            },
            {
                "_id": test_fixtures.object_ids[1],
                "id": test_fixtures.uuids[1],
                "participants": [test_fixtures.passenger_user["_id"], test_fixtures.driver_user["_id"]],
                "last_message_at": base_time - timedelta(hours=1)  # Newer
            }
        ]
        
        await mongodb.conversations.insert_many(conversations)
        
        response = await passenger_client.get("/api/conversations")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        # Newer conversation should be first
        assert data[0]["id"] == str(test_fixtures.uuids[1])
        assert data[1]["id"] == str(test_fixtures.uuids[0])

    @pytest.mark.asyncio
    async def test_unauthorized_endpoints(
        self, test_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test that all endpoints require authentication."""
        endpoints = [
            "/api/conversations",
            f"/api/conversations/{test_fixtures.uuids[0]}/messages",
        ]
        
        for endpoint in endpoints:
            response = await test_client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test POST endpoint
        message_data = {"content": "test", "message_type": "TEXT"}
        response = await test_client.post(
            f"/api/conversations/{test_fixtures.uuids[0]}/messages", 
            json=message_data
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
