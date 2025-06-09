import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4
from bson import ObjectId

from tests.conftest import TestFixtures


class TestAccountsRouter:
    """Test cases for accounts router endpoints"""

    @pytest.mark.asyncio
    async def test_register_user_success(self, test_client, mock_mongodb):
        """Test successful user registration"""
        # Mock user doesn't exist initially and no pending approval requests
        mock_mongodb.users.find_one = AsyncMock(return_value=None)
        mock_mongodb.approval_requests.find_one = AsyncMock(return_value=None)
        
        # Mock successful user creation
        user_id = str(uuid4())
        mock_mongodb.users.insert_one = AsyncMock(return_value=AsyncMock(inserted_id=ObjectId()))
        created_user = TestFixtures.create_test_user(user_id=user_id, email="john.doe@example.com")
        
        # Mock the find_one call after creation to return the created user
        mock_mongodb.users.find_one = AsyncMock(side_effect=[None, None, created_user])
        
        # Test data
        registration_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "password": "SecurePassword123!",
            "phone_number": "+1234567890",
            "role": "PASSENGER"
        }
        
        with patch('core.security.get_password_hash') as mock_hash:
            mock_hash.return_value = "hashed_password"
            
            response = await test_client.post("/api/accounts/register", json=registration_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == registration_data["email"]
        assert data["first_name"] == registration_data["first_name"]
        assert data["last_name"] == registration_data["last_name"]
        assert "password" not in data
        
        # Verify user was created in database
        mock_mongodb.users.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_email_exists(self, test_client, mock_mongodb):
        """Test registration with existing email"""
        # Mock user already exists
        existing_user = TestFixtures.create_test_user()
        mock_mongodb.users.find_one = AsyncMock(return_value=existing_user)
        
        registration_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "existing@example.com",
            "password": "SecurePassword123!",
            "phone_number": "+1234567890",
            "role": "PASSENGER"
        }
        
        response = await test_client.post("/api/accounts/register", json=registration_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_user_invalid_data(self, test_client, mock_mongodb):
        """Test registration with invalid data"""
        invalid_data = {
            "first_name": "",  # Empty name
            "email": "invalid-email",  # Invalid email format
            "password": "123",  # Too short password
        }
        
        response = await test_client.post("/api/accounts/register", json=invalid_data)
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, test_client, mock_mongodb):
        """Test successful login"""
        # Mock user exists with correct password
        user_data = TestFixtures.create_test_user()
        mock_mongodb.users.find_one = AsyncMock(return_value=user_data)
        
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]  # Use the same password from test user
        }
        
        response = await test_client.post("/api/accounts/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, test_client, mock_mongodb):
        """Test login with invalid credentials"""
        # Mock user exists but password is wrong
        user_data = TestFixtures.create_test_user()
        mock_mongodb.users.find_one = AsyncMock(return_value=user_data)
        
        login_data = {
            "email": user_data["email"],
            "password": "wrong_password"
        }
        
        response = await test_client.post("/api/accounts/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect email or password" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, test_client, mock_mongodb):
        """Test login with non-existent user"""
        # Mock user doesn't exist
        mock_mongodb.users.find_one = AsyncMock(return_value=None)
        
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = await test_client.post("/api/accounts/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect email or password" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, test_client, mock_mongodb):
        """Test login with inactive user"""
        # Mock inactive user
        user_data = TestFixtures.create_test_user(is_active=False)
        mock_mongodb.users.find_one = AsyncMock(return_value=user_data)
        
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]  # Use correct password
        }
        
        response = await test_client.post("/api/accounts/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect email or password" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_logout_success(self, authenticated_client):
        """Test successful logout"""
        response = await authenticated_client.post("/api/accounts/logout")
        
        assert response.status_code == 200
        assert "logged out successfully" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, test_client):
        """Test logout without authentication"""
        response = await test_client.post("/api/accounts/logout")
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_request_password_reset_success(self, test_client, mock_mongodb):
        """Test successful password reset request"""
        # Mock user exists
        user_data = TestFixtures.create_test_user()
        mock_mongodb.users.find_one = AsyncMock(return_value=user_data)
        mock_mongodb.users.update_one = AsyncMock(return_value=AsyncMock(modified_count=1))
        
        reset_data = {
            "email": user_data["email"]
        }
        
        with patch('core.email_service.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            response = await test_client.post("/api/accounts/password/reset/request", json=reset_data)
        
        assert response.status_code == 200
        assert "password reset instructions sent to your email" in response.json()["message"].lower()
        
        # Verify reset token was set
        mock_mongodb.users.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_password_reset_user_not_found(self, test_client, mock_mongodb):
        """Test password reset request for non-existent user"""
        # Mock user doesn't exist
        mock_mongodb.users.find_one = AsyncMock(return_value=None)
        
        reset_data = {
            "email": "nonexistent@example.com"
        }
        response = await test_client.post("/api/accounts/password/reset/request", json=reset_data)
        
        assert response.status_code == 200
        assert "if your email is registered, you will receive a password reset link" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_confirm_password_reset_success(self, test_client, mock_mongodb):
        """Test successful password reset confirmation"""
        # Mock user with valid reset token
        user_data = TestFixtures.create_test_user()
        user_data["password_reset_token"] = "valid_token"
        user_data["password_reset_expires"] = datetime.utcnow() + timedelta(hours=1)
        mock_mongodb.users.find_one = AsyncMock(return_value=user_data)
        mock_mongodb.users.update_one = AsyncMock(return_value=AsyncMock(modified_count=1))
        
        reset_data = {
            "token": "valid_token",
            "new_password": "NewSecurePassword123!"
        }
        
        with patch('core.security.get_password_hash') as mock_hash:
            mock_hash.return_value = "new_hashed_password"
            
            response = await test_client.post("/api/accounts/password/reset/confirm", json=reset_data)
        
        assert response.status_code == 200
        assert "password has been reset successfully" in response.json()["message"].lower()
        
        # Verify password was updated and token cleared
        mock_mongodb.users.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_password_reset_invalid_token(self, test_client, mock_mongodb):
        """Test password reset confirmation with invalid token"""
        # Mock user not found with token
        mock_mongodb.users.find_one = AsyncMock(return_value=None)
        
        reset_data = {
            "token": "invalid_token",
            "new_password": "NewSecurePassword123!"
        }
        
        response = await test_client.post("/api/accounts/password/reset/confirm", json=reset_data)
        
        assert response.status_code == 400
        assert "invalid or expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_confirm_password_reset_expired_token(self, test_client, mock_mongodb):
        """Test password reset confirmation with expired token"""
        # Mock that no user is found when searching with expiry filter (simulates expired token)
        mock_mongodb.users.find_one = AsyncMock(return_value=None)
        
        reset_data = {
            "token": "expired_token",
            "new_password": "NewSecurePassword123!"
        }
        
        response = await test_client.post("/api/accounts/password/reset/confirm", json=reset_data)
        
        assert response.status_code == 400
        assert "invalid or expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_user_validation_errors(self, test_client):
        """Test registration with various validation errors"""
        test_cases = [
            # Missing required fields
            {"email": "test@example.com"},
            # Invalid email
            {"email": "invalid-email", "password": "Password123!", "first_name": "John", "last_name": "Doe"},
            # Weak password
            {"email": "test@example.com", "password": "weak", "first_name": "John", "last_name": "Doe"},
            # Invalid role
            {"email": "test@example.com", "password": "Password123!", "first_name": "John", "last_name": "Doe", "role": "INVALID_ROLE"},
        ]
        
        for test_data in test_cases:
            response = await test_client.post("/api/accounts/register", json=test_data)
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_validation_errors(self, test_client):
        """Test login with validation errors"""
        test_cases = [
            # Missing email
            {"password": "password123"},
            # Missing password
            {"email": "test@example.com"},
            # Invalid email format
            {"email": "invalid-email", "password": "password123"},
            # Empty fields
            {"email": "", "password": ""},
        ]
        
        for test_data in test_cases:
            response = await test_client.post("/api/accounts/login", json=test_data)
            assert response.status_code == 422
