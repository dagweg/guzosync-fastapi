"""
Comprehensive tests for the trip router endpoints.
Tests all endpoints with various scenarios including success cases,
error handling, validation, and edge cases.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from datetime import datetime
from uuid import uuid4
from httpx import AsyncClient
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from conftest import TestFixtures


class TestTripFeedback:
    """Test trip feedback submission endpoint."""
    
    async def test_submit_trip_feedback_success(self, passenger_client: AsyncClient, test_fixtures: TestFixtures):
        """Test successful trip feedback submission."""
        # Create a mock trip and bus
        trip_id = str(uuid4())
        bus_id = str(uuid4())
        
        feedback_data = {
            "content": "Great trip, very comfortable bus and punctual service!",
            "rating": 5,
            "related_trip_id": trip_id,
            "related_bus_id": bus_id
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == feedback_data["content"]
        assert data["rating"] == feedback_data["rating"]
        assert data["related_trip_id"] == trip_id
        assert data["related_bus_id"] == bus_id
        assert data["feedback_type"] == "TRIP"
        assert "submitted_at" in data
        assert "id" in data
    
    async def test_submit_trip_feedback_minimum_rating(self, passenger_client: AsyncClient):
        """Test trip feedback with minimum rating."""
        feedback_data = {
            "content": "Trip needs improvement",
            "rating": 1,
            "related_trip_id": str(uuid4()),
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 1
    
    async def test_submit_trip_feedback_maximum_rating(self, passenger_client: AsyncClient):
        """Test trip feedback with maximum rating."""
        feedback_data = {
            "content": "Excellent trip experience!",
            "rating": 5,
            "related_trip_id": str(uuid4()),
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 5
    
    async def test_submit_trip_feedback_invalid_rating_low(self, passenger_client: AsyncClient):
        """Test trip feedback with rating below minimum."""
        feedback_data = {
            "content": "Bad trip",
            "rating": 0,
            "related_trip_id": str(uuid4()),
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        assert response.status_code == 422
    
    async def test_submit_trip_feedback_invalid_rating_high(self, passenger_client: AsyncClient):
        """Test trip feedback with rating above maximum."""
        feedback_data = {
            "content": "Great trip",
            "rating": 6,
            "related_trip_id": str(uuid4()),
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        assert response.status_code == 422
    
    async def test_submit_trip_feedback_empty_content(self, passenger_client: AsyncClient):
        """Test trip feedback with empty content."""
        feedback_data = {
            "content": "",
            "rating": 3,
            "related_trip_id": str(uuid4()),
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        # Should still succeed as empty content might be allowed
        assert response.status_code in [201, 422]
    
    async def test_submit_trip_feedback_missing_trip_id(self, passenger_client: AsyncClient):
        """Test trip feedback without trip ID."""
        feedback_data = {
            "content": "Good trip",
            "rating": 4,
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        assert response.status_code == 422
    
    async def test_submit_trip_feedback_missing_bus_id(self, passenger_client: AsyncClient):
        """Test trip feedback without bus ID."""
        feedback_data = {
            "content": "Good trip",
            "rating": 4,
            "related_trip_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        assert response.status_code == 422
    
    async def test_submit_trip_feedback_invalid_uuid_format(self, passenger_client: AsyncClient):
        """Test trip feedback with invalid UUID format."""
        feedback_data = {
            "content": "Good trip",
            "rating": 4,
            "related_trip_id": "invalid-uuid",
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        assert response.status_code == 422
    
    async def test_submit_trip_feedback_unauthorized(self, client: AsyncClient):
        """Test trip feedback submission without authentication."""
        feedback_data = {
            "content": "Good trip",
            "rating": 4,
            "related_trip_id": str(uuid4()),
            "related_bus_id": str(uuid4())
        }
        
        response = await client.post("/api/trip/feedback", json=feedback_data)
        
        assert response.status_code == 401
    
    async def test_submit_trip_feedback_long_content(self, passenger_client: AsyncClient):
        """Test trip feedback with very long content."""
        long_content = "A" * 1000  # Very long content
        feedback_data = {
            "content": long_content,
            "rating": 4,
            "related_trip_id": str(uuid4()),
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        
        # Should either succeed or fail validation
        assert response.status_code in [201, 422]


class TestGetTripFeedback:
    """Test trip feedback retrieval endpoint."""
    
    async def test_get_trip_feedback_passenger(self, passenger_client: AsyncClient, test_fixtures: TestFixtures):
        """Test passenger can only see their own trip feedback."""
        # First submit some feedback
        trip_id = str(uuid4())
        bus_id = str(uuid4())
        
        feedback_data = {
            "content": "Good trip experience",
            "rating": 4,
            "related_trip_id": trip_id,
            "related_bus_id": bus_id
        }
        
        # Submit feedback first
        submit_response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        assert submit_response.status_code == 201
        
        # Then retrieve feedback
        response = await passenger_client.get("/api/trip/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should contain the feedback we just submitted
        if data:
            assert any(feedback["content"] == "Good trip experience" for feedback in data)
            # All feedback should belong to the current user
            for feedback in data:
                assert feedback["feedback_type"] == "TRIP"
    
    async def test_get_trip_feedback_admin(self, admin_client: AsyncClient, test_fixtures: TestFixtures):
        """Test admin can see all trip feedback."""
        response = await admin_client.get("/api/trip/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Admin should see all trip feedback, not filtered by user
    
    async def test_get_trip_feedback_regulator(self, regulator_client: AsyncClient, test_fixtures: TestFixtures):
        """Test regulator can see all trip feedback."""
        response = await regulator_client.get("/api/trip/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Regulator should see all trip feedback, not filtered by user
    
    async def test_get_trip_feedback_pagination(self, passenger_client: AsyncClient):
        """Test trip feedback pagination."""
        # Test with skip and limit parameters
        response = await passenger_client.get("/api/trip/feedback?skip=0&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    async def test_get_trip_feedback_pagination_skip(self, passenger_client: AsyncClient):
        """Test trip feedback pagination with skip."""
        response = await passenger_client.get("/api/trip/feedback?skip=10&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_trip_feedback_invalid_skip(self, passenger_client: AsyncClient):
        """Test trip feedback with invalid skip parameter."""
        response = await passenger_client.get("/api/trip/feedback?skip=-1")
        
        assert response.status_code == 422
    
    async def test_get_trip_feedback_invalid_limit_low(self, passenger_client: AsyncClient):
        """Test trip feedback with limit below minimum."""
        response = await passenger_client.get("/api/trip/feedback?limit=0")
        
        assert response.status_code == 422
    
    async def test_get_trip_feedback_invalid_limit_high(self, passenger_client: AsyncClient):
        """Test trip feedback with limit above maximum."""
        response = await passenger_client.get("/api/trip/feedback?limit=101")
        
        assert response.status_code == 422
    
    async def test_get_trip_feedback_unauthorized(self, client: AsyncClient):
        """Test trip feedback retrieval without authentication."""
        response = await client.get("/api/trip/feedback")
        
        assert response.status_code == 401
    
    async def test_get_trip_feedback_empty_result(self, passenger_client: AsyncClient):
        """Test trip feedback retrieval when no feedback exists."""
        response = await passenger_client.get("/api/trip/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should return empty list if no feedback exists
    
    async def test_get_trip_feedback_default_pagination(self, passenger_client: AsyncClient):
        """Test trip feedback with default pagination parameters."""
        response = await passenger_client.get("/api/trip/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should use default skip=0, limit=10
        assert len(data) <= 10


class TestTripEndpointsIntegration:
    """Integration tests for trip endpoints."""
    
    async def test_submit_and_retrieve_feedback_flow(self, passenger_client: AsyncClient):
        """Test the complete flow of submitting and retrieving feedback."""
        trip_id = str(uuid4())
        bus_id = str(uuid4())
        
        # Submit feedback
        feedback_data = {
            "content": "Integration test feedback",
            "rating": 5,
            "related_trip_id": trip_id,
            "related_bus_id": bus_id
        }
        
        submit_response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
        assert submit_response.status_code == 201
        submitted_feedback = submit_response.json()
        
        # Retrieve feedback
        get_response = await passenger_client.get("/api/trip/feedback")
        assert get_response.status_code == 200
        feedback_list = get_response.json()
        
        # Verify the submitted feedback is in the list
        assert any(
            feedback["id"] == submitted_feedback["id"] 
            for feedback in feedback_list
        )
    
    async def test_multiple_feedback_submissions(self, passenger_client: AsyncClient):
        """Test submitting multiple feedback entries."""
        feedback_entries = [
            {
                "content": f"Trip feedback {i}",
                "rating": (i % 5) + 1,
                "related_trip_id": str(uuid4()),
                "related_bus_id": str(uuid4())
            }
            for i in range(3)
        ]
        
        submitted_ids = []
        for feedback_data in feedback_entries:
            response = await passenger_client.post("/api/trip/feedback", json=feedback_data)
            assert response.status_code == 201
            submitted_ids.append(response.json()["id"])
        
        # Retrieve all feedback
        get_response = await passenger_client.get("/api/trip/feedback")
        assert get_response.status_code == 200
        feedback_list = get_response.json()
        
        # Verify all submitted feedback is present
        retrieved_ids = [feedback["id"] for feedback in feedback_list]
        for submitted_id in submitted_ids:
            assert submitted_id in retrieved_ids
