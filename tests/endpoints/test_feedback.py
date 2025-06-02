import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from datetime import datetime, timedelta
from uuid import uuid4


from tests.conftest import TestFixtures


class TestFeedbackRouter:
    """Test cases for feedback router endpoints"""

    @pytest.mark.asyncio
    async def test_submit_feedback_success(self, authenticated_client, mock_mongodb):
        """Test successful feedback submission"""
        # Mock successful feedback insertion
        feedback_id = str(uuid4())
        mock_mongodb.feedback.insert_one.return_value = AsyncMock(inserted_id="ObjectId")
        
        created_feedback = {
            "_id": "ObjectId",
            "id": feedback_id,
            "submitted_by_user_id": authenticated_client.test_user.id,
            "content": "Great service!",
            "rating": 5,
            "related_trip_id": str(uuid4()),
            "created_at": datetime.utcnow()
        }
        mock_mongodb.feedback.find_one.return_value = created_feedback
        
        feedback_data = {
            "content": "Great service!",
            "rating": 5,
            "related_trip_id": str(uuid4()),
            "related_bus_id": str(uuid4())
        }
        
        response = await authenticated_client.post("/api/feedback", json=feedback_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Great service!"
        assert data["rating"] == 5
        assert data["submitted_by_user_id"] == authenticated_client.test_user.id

    @pytest.mark.asyncio
    async def test_submit_feedback_minimal_data(self, authenticated_client, mock_mongodb):
        """Test feedback submission with minimal required data"""
        feedback_id = str(uuid4())
        mock_mongodb.feedback.insert_one.return_value = AsyncMock(inserted_id="ObjectId")
        
        created_feedback = {
            "_id": "ObjectId",
            "id": feedback_id,
            "submitted_by_user_id": authenticated_client.test_user.id,
            "content": "Quick feedback",
            "rating": 3,
            "created_at": datetime.utcnow()
        }
        mock_mongodb.feedback.find_one.return_value = created_feedback
        
        feedback_data = {
            "content": "Quick feedback",
            "rating": 3
        }
        
        response = await authenticated_client.post("/api/feedback", json=feedback_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Quick feedback"
        assert data["rating"] == 3

    @pytest.mark.asyncio
    async def test_submit_feedback_invalid_rating(self, authenticated_client):
        """Test feedback submission with invalid rating"""
        feedback_data = {
            "content": "Test feedback",
            "rating": 6  # Invalid rating (should be 1-5)
        }
        
        response = await authenticated_client.post("/api/feedback", json=feedback_data)
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_feedback_empty_content(self, authenticated_client):
        """Test feedback submission with empty content"""
        feedback_data = {
            "content": "",  # Empty content
            "rating": 4
        }
        
        response = await authenticated_client.post("/api/feedback", json=feedback_data)
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_feedback_unauthenticated(self, test_client):
        """Test feedback submission without authentication"""
        feedback_data = {
            "content": "Test feedback",
            "rating": 4
        }
        
        response = await test_client.post("/api/feedback", json=feedback_data)
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_feedback_success(self, authenticated_client, mock_mongodb):
        """Test successful retrieval of user's feedback"""
        # Mock user's feedback
        feedback_list = [
            {
                "_id": "ObjectId1",
                "id": str(uuid4()),
                "submitted_by_user_id": authenticated_client.test_user.id,
                "content": "Excellent service",
                "rating": 5,
                "created_at": datetime.utcnow()
            },
            {
                "_id": "ObjectId2",
                "id": str(uuid4()),
                "submitted_by_user_id": authenticated_client.test_user.id,
                "content": "Could be better",
                "rating": 3,
                "created_at": datetime.utcnow()
            }
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = feedback_list
        mock_mongodb.feedback.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["content"] == "Excellent service"
        assert data[1]["content"] == "Could be better"

    @pytest.mark.asyncio
    async def test_get_feedback_pagination(self, authenticated_client, mock_mongodb):
        """Test feedback retrieval with pagination"""
        feedback_list = [
            {
                "_id": f"ObjectId{i}",
                "id": str(uuid4()),
                "submitted_by_user_id": authenticated_client.test_user.id,
                "content": f"Feedback {i}",
                "rating": 4,
                "created_at": datetime.utcnow()
            } for i in range(5)
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = feedback_list[:2]  # Return first 2
        mock_mongodb.feedback.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/feedback?skip=0&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Verify pagination parameters
        mock_cursor.skip.assert_called_with(0)
        mock_cursor.limit.assert_called_with(2)

    @pytest.mark.asyncio
    async def test_get_feedback_empty(self, authenticated_client, mock_mongodb):
        """Test feedback retrieval when user has no feedback"""
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = []
        mock_mongodb.feedback.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_feedback_admin_access(self, admin_client, mock_mongodb):
        """Test admin can access all feedback"""
        # Mock all feedback (from all users)
        all_feedback = [
            {
                "_id": "ObjectId1",
                "id": str(uuid4()),
                "submitted_by_user_id": str(uuid4()),  # Different user
                "content": "User 1 feedback",
                "rating": 4,
                "created_at": datetime.utcnow()
            },
            {
                "_id": "ObjectId2",
                "id": str(uuid4()),
                "submitted_by_user_id": str(uuid4()),  # Different user
                "content": "User 2 feedback",
                "rating": 5,
                "created_at": datetime.utcnow()
            }
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = all_feedback
        mock_mongodb.feedback.find.return_value = mock_cursor
        
        response = await admin_client.get("/api/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_feedback_unauthenticated(self, test_client):
        """Test feedback retrieval without authentication"""
        response = await test_client.get("/api/feedback")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_feedback_with_trip_context(self, authenticated_client, mock_mongodb):
        """Test feedback submission with trip context"""
        trip_id = str(uuid4())
        bus_id = str(uuid4())
        
        feedback_id = str(uuid4())
        mock_mongodb.feedback.insert_one.return_value = AsyncMock(inserted_id="ObjectId")
        
        created_feedback = {
            "_id": "ObjectId",
            "id": feedback_id,
            "submitted_by_user_id": authenticated_client.test_user.id,
            "content": "Trip was smooth",
            "rating": 4,
            "related_trip_id": trip_id,
            "related_bus_id": bus_id,
            "created_at": datetime.utcnow()
        }
        mock_mongodb.feedback.find_one.return_value = created_feedback
        
        feedback_data = {
            "content": "Trip was smooth",
            "rating": 4,
            "related_trip_id": trip_id,
            "related_bus_id": bus_id
        }
        
        response = await authenticated_client.post("/api/feedback", json=feedback_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["related_trip_id"] == trip_id
        assert data["related_bus_id"] == bus_id

    @pytest.mark.asyncio
    async def test_feedback_content_validation(self, authenticated_client, mock_mongodb):
        """Test feedback content validation"""
        # Test with very long content
        long_content = "A" * 2000
        
        feedback_data = {
            "content": long_content,
            "rating": 4
        }
        
        response = await authenticated_client.post("/api/feedback", json=feedback_data)
        
        # Should either accept or reject with appropriate validation error
        assert response.status_code in [201, 422]
        
        # Test with special characters and Unicode
        unicode_content = "Great service! 😊 የጥሩ አገልግሎት!"
        
        feedback_id = str(uuid4())
        mock_mongodb.feedback.insert_one.return_value = AsyncMock(inserted_id="ObjectId")
        
        created_feedback = {
            "_id": "ObjectId",
            "id": feedback_id,
            "submitted_by_user_id": authenticated_client.test_user.id,
            "content": unicode_content,
            "rating": 5,
            "created_at": datetime.utcnow()
        }
        mock_mongodb.feedback.find_one.return_value = created_feedback
        
        unicode_feedback_data = {
            "content": unicode_content,
            "rating": 5
        }
        
        response = await authenticated_client.post("/api/feedback", json=unicode_feedback_data)
        
        if response.status_code == 201:
            data = response.json()
            assert data["content"] == unicode_content

    @pytest.mark.asyncio
    async def test_feedback_rating_distribution(self, authenticated_client, mock_mongodb):
        """Test feedback with different rating values"""
        for rating in [1, 2, 3, 4, 5]:
            feedback_id = str(uuid4())
            mock_mongodb.feedback.insert_one.return_value = AsyncMock(inserted_id="ObjectId")
            
            created_feedback = {
                "_id": "ObjectId",
                "id": feedback_id,
                "submitted_by_user_id": authenticated_client.test_user.id,
                "content": f"Rating {rating} feedback",
                "rating": rating,
                "created_at": datetime.utcnow()
            }
            mock_mongodb.feedback.find_one.return_value = created_feedback
            
            feedback_data = {
                "content": f"Rating {rating} feedback",
                "rating": rating
            }
            
            response = await authenticated_client.post("/api/feedback", json=feedback_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["rating"] == rating

    @pytest.mark.asyncio
    async def test_feedback_timestamps(self, authenticated_client, mock_mongodb):
        """Test feedback timestamps are properly set"""
        feedback_id = str(uuid4())
        from datetime import datetime
        current_time = datetime.utcnow()
        
        mock_mongodb.feedback.insert_one.return_value = AsyncMock(inserted_id="ObjectId")
        
        created_feedback = {
            "_id": "ObjectId",
            "id": feedback_id,
            "submitted_by_user_id": authenticated_client.test_user.id,
            "content": "Timestamp test",
            "rating": 4,
            "created_at": current_time,
            "updated_at": current_time
        }
        mock_mongodb.feedback.find_one.return_value = created_feedback
        
        feedback_data = {
            "content": "Timestamp test",
            "rating": 4
        }
        
        response = await authenticated_client.post("/api/feedback", json=feedback_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "created_at" in data
        # Verify timestamp is recent (within last minute)
        from datetime import datetime, timedelta
        created_at = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        assert abs((datetime.utcnow() - created_at.replace(tzinfo=None)).total_seconds()) < 60

    @pytest.mark.asyncio
    async def test_feedback_sorting(self, authenticated_client, mock_mongodb):
        """Test feedback is returned in correct order (newest first)"""
        # Create feedback with different timestamps
        old_time = datetime.utcnow() - timedelta(days=1)
        new_time = datetime.utcnow()
        
        feedback_list = [
            {
                "_id": "ObjectId1",
                "id": str(uuid4()),
                "submitted_by_user_id": authenticated_client.test_user.id,
                "content": "Newer feedback",
                "rating": 5,
                "created_at": new_time
            },
            {
                "_id": "ObjectId2",
                "id": str(uuid4()),
                "submitted_by_user_id": authenticated_client.test_user.id,
                "content": "Older feedback",
                "rating": 4,
                "created_at": old_time
            }
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = feedback_list
        mock_mongodb.feedback.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/feedback")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify sorting was applied (newest first)
        mock_cursor.sort.assert_called_with("created_at", -1)
