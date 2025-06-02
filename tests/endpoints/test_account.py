import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any

from tests.conftest import TestFixtures


class TestAccountRouter:
    """Test cases for account router endpoints"""

    @pytest.mark.asyncio
    async def test_get_current_user_info_success(self, authenticated_client):
        """Test getting current user information"""
        response = await authenticated_client.get("/api/account/me")
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "role" in data
        assert "password" not in data  # Password should not be exposed

    @pytest.mark.asyncio
    async def test_get_current_user_info_unauthenticated(self, test_client):
        """Test getting current user info without authentication"""
        response = await test_client.get("/api/account/me")
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_user_info_success(self, authenticated_client, mock_mongodb):
        """Test successful user information update"""
        # Mock successful update
        mock_mongodb.users.update_one.return_value = AsyncMock(modified_count=1)
        
        # Mock updated user data
        updated_user_data = authenticated_client.test_user_data.copy()
        updated_user_data["first_name"] = "Updated"
        updated_user_data["last_name"] = "Name"
        mock_mongodb.users.find_one.return_value = updated_user_data
        
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone_number": "+1987654321"
        }
        
        response = await authenticated_client.put("/api/account/me", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        
        # Verify database update was called (UUID helper may try multiple queries)
        assert mock_mongodb.users.update_one.call_count >= 1

    @pytest.mark.asyncio
    async def test_update_user_info_partial_update(self, authenticated_client, mock_mongodb):
        """Test partial user information update"""
        # Mock successful update
        mock_mongodb.users.update_one.return_value = AsyncMock(modified_count=1)
        
        # Mock updated user data
        updated_user_data = authenticated_client.test_user_data.copy()
        updated_user_data["first_name"] = "OnlyFirstName"
        mock_mongodb.users.find_one.return_value = updated_user_data
        
        update_data = {
            "first_name": "OnlyFirstName"
            # Only updating first name, other fields should remain unchanged
        }
        
        response = await authenticated_client.put("/api/account/me", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "OnlyFirstName"

    @pytest.mark.asyncio
    async def test_update_user_info_no_changes(self, authenticated_client, mock_mongodb):
        """Test update with no actual changes"""
        # Mock user data unchanged
        mock_mongodb.users.find_one.return_value = authenticated_client.test_user_data
        
        update_data: Dict[str, Any] = {}  # No changes
        
        response = await authenticated_client.put("/api/account/me", json=update_data)
        
        assert response.status_code == 200
        # No database update should be called since no changes
        mock_mongodb.users.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_info_invalid_data(self, authenticated_client):
        """Test update with invalid data"""
        invalid_data = {
            "email": "invalid-email-format",  # Invalid email
            "first_name": "",  # Empty name
            "phone_number": "invalid-phone"  # Invalid phone
        }
        response = await authenticated_client.put("/api/account/me", json=invalid_data)
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_user_info_unauthenticated(self, test_client):
        """Test update without authentication"""
        update_data = {
            "first_name": "Updated"
        }
        
        response = await test_client.put("/api/account/me", json=update_data)
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_notification_settings_success(self, authenticated_client, mock_mongodb):
        """Test successful notification settings update"""
        # Mock existing settings found
        mock_mongodb.notification_settings.find_one.return_value = {"_id": "existing"}
        
        # Mock successful update using AsyncMock
        mock_update_result = AsyncMock()
        mock_update_result.matched_count = 1
        mock_mongodb.notification_settings.update_one = AsyncMock(return_value=mock_update_result)
        
        # Mock the direct insert_one call as AsyncMock 
        mock_mongodb.notification_settings.insert_one = AsyncMock()
        
        # Mock updated settings - using correct schema with email_enabled
        updated_settings = {
            "_id": "ObjectId",
            "id": str(uuid4()),
            "user_id": authenticated_client.test_user.id,
            "email_enabled": True,
        }
        mock_mongodb.notification_settings.find_one.return_value = updated_settings
        
        settings_data = {
            "email_notifications": True,
        }
        
        response = await authenticated_client.put("/api/account/notification-settings", json=settings_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email_enabled"] == True    
        
    @pytest.mark.asyncio
    async def test_update_notification_settings_create_new(self, authenticated_client, mock_mongodb):
        """Test creating new notification settings if none exist"""
        # Mock no existing settings found on first call, then return created settings
        mock_mongodb.notification_settings.find_one.side_effect = [
            None,  # First call - no existing settings
            {      # Second call - return created settings
                "_id": "ObjectId",
                "id": str(uuid4()),
                "user_id": authenticated_client.test_user.id,
                "email_enabled": True,
            }
        ]
        
        # Mock successful insert as AsyncMock
        mock_insert_result = AsyncMock()
        mock_insert_result.inserted_id = "ObjectId"        
        mock_mongodb.notification_settings.insert_one = AsyncMock(return_value=mock_insert_result)
        
        settings_data = {
            "email_notifications": True,
        }
        
        response = await authenticated_client.put("/api/account/notification-settings", json=settings_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email_enabled"] == True

    @pytest.mark.asyncio
    async def test_update_notification_settings_unauthenticated(self, test_client):
        """Test update notification settings without authentication"""
        settings_data = {
            "email_notifications": True
        }
        response = await test_client.put("/api/account/notification-settings", json=settings_data)
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_preferred_language_success(self, authenticated_client, mock_mongodb):
        """Test successful language preference update"""
        # Mock successful update
        mock_mongodb.users.update_one.return_value = AsyncMock(modified_count=1)
        
        language_data = {
            "language": "am"  # Amharic
        }
        
        response = await authenticated_client.put("/api/account/language", json=language_data)
        
        assert response.status_code == 200
        data = response.json()        
        assert "language updated" in data["message"].lower()
        
        # Verify database update was called (UUID helper may try multiple queries)
        assert mock_mongodb.users.update_one.call_count >= 1

    @pytest.mark.asyncio
    async def test_update_preferred_language_invalid(self, authenticated_client):
        """Test update with invalid language code"""
        language_data = {
            "language": "invalid_language_code"
        }
        
        response = await authenticated_client.put("/api/account/language", json=language_data)
        
        assert response.status_code == 400
        assert "invalid language" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_preferred_language_unauthenticated(self, test_client):
        """Test update language without authentication"""
        language_data = {
            "language": "en"
        }
        response = await test_client.put("/api/account/language", json=language_data)
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_account_data_consistency(self, authenticated_client, mock_mongodb):
        """Test that account operations maintain data consistency"""
        # Test multiple operations in sequence
        
        # First update user info
        update_data = {
            "first_name": "Consistent",
            "last_name": "User"
        }
        
        updated_user_data = authenticated_client.test_user_data.copy()
        updated_user_data.update(update_data)
        mock_mongodb.users.find_one.return_value = updated_user_data
        mock_mongodb.users.update_one.return_value = AsyncMock(modified_count=1)
        
        response1 = await authenticated_client.put("/api/account/me", json=update_data)
        assert response1.status_code == 200
        
        # Then get user info and verify consistency
        response2 = await authenticated_client.get("/api/account/me")
        assert response2.status_code == 200
        
        data = response2.json()
        assert data["first_name"] == "Consistent"
        assert data["last_name"] == "User"

    @pytest.mark.asyncio
    async def test_account_edge_cases(self, authenticated_client, mock_mongodb):
        """Test edge cases for account operations"""
        # Test with very long names
        long_name = "A" * 100
        update_data = {
            "first_name": long_name,
            "last_name": long_name
        }
        
        response = await authenticated_client.put("/api/account/me", json=update_data)
        # Should either succeed or fail with appropriate validation error
        assert response.status_code in [200, 422]
        
        # Test with special characters
        special_data = {
            "first_name": "João",  # Unicode character
            "last_name": "Smith-Jones"  # Hyphenated name
        }
        
        updated_user_data = authenticated_client.test_user_data.copy()
        updated_user_data.update(special_data)
        mock_mongodb.users.find_one.return_value = updated_user_data
        mock_mongodb.users.update_one.return_value = AsyncMock(modified_count=1)
        
        response = await authenticated_client.put("/api/account/me", json=special_data)
        assert response.status_code == 200
