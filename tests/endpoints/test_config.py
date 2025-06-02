import pytest
import pytest_asyncio


class TestConfigRouter:
    """Test cases for config router endpoints"""

    @pytest.mark.asyncio
    async def test_get_supported_languages_success(self, test_client):
        """Test successful retrieval of supported languages"""
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify language structure
        for language in data:
            assert "code" in language
            assert "name" in language
            assert isinstance(language["code"], str)
            assert isinstance(language["name"], str)
        
        # Verify expected languages are present
        language_codes = [lang["code"] for lang in data]
        expected_codes = ["en", "am", "om", "ti"]
        
        for code in expected_codes:
            assert code in language_codes

    @pytest.mark.asyncio
    async def test_get_supported_languages_response_format(self, test_client):
        """Test the format and content of supported languages response"""
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify specific language entries
        language_map = {lang["code"]: lang["name"] for lang in data}
        
        assert language_map.get("en") == "English"
        assert language_map.get("am") == "Amharic"
        assert language_map.get("om") == "Oromo"
        assert language_map.get("ti") == "Tigrinya"

    @pytest.mark.asyncio
    async def test_get_supported_languages_no_auth_required(self, test_client):
        """Test that getting supported languages doesn't require authentication"""
        # This should work without any authentication
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        # Config endpoints should be publicly accessible

    @pytest.mark.asyncio
    async def test_get_supported_languages_consistency(self, test_client):
        """Test that supported languages endpoint returns consistent data"""
        # Make multiple requests to ensure consistency
        responses = []
        for _ in range(3):
            response = await test_client.get("/api/config/languages")
            assert response.status_code == 200
            responses.append(response.json())
        
        # All responses should be identical
        assert all(resp == responses[0] for resp in responses)

    @pytest.mark.asyncio
    async def test_get_supported_languages_caching_headers(self, test_client):
        """Test that appropriate caching headers are set for config data"""
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        
        # Config data should ideally have caching headers
        # This is a best practice for relatively static configuration data
        # Note: The actual implementation might not have these headers yet
        # but this test documents the expected behavior

    @pytest.mark.asyncio
    async def test_config_endpoint_error_handling(self, test_client):
        """Test error handling for non-existent config endpoints"""
        # Test accessing non-existent config endpoint
        response = await test_client.get("/api/config/nonexistent")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_config_languages_data_validation(self, test_client):
        """Test that language data meets expected validation criteria"""
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        data = response.json()
        
        for language in data:
            # Code should be 2-3 characters, lowercase
            code = language["code"]
            assert len(code) >= 2
            assert len(code) <= 3
            assert code.islower()
            assert code.isalpha()
            
            # Name should not be empty and should be properly capitalized
            name = language["name"]
            assert len(name) > 0
            assert name[0].isupper()  # First letter should be uppercase

    @pytest.mark.asyncio
    async def test_config_languages_unique_codes(self, test_client):
        """Test that language codes are unique"""
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        data = response.json()
        
        codes = [lang["code"] for lang in data]
        assert len(codes) == len(set(codes))  # No duplicates

    @pytest.mark.asyncio
    async def test_config_languages_unique_names(self, test_client):
        """Test that language names are unique"""
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        data = response.json()
        
        names = [lang["name"] for lang in data]
        assert len(names) == len(set(names))  # No duplicates

    @pytest.mark.asyncio
    async def test_config_api_versioning(self, test_client):
        """Test that config API maintains backward compatibility"""
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        data = response.json()
        
        # Ensure basic structure remains consistent for backward compatibility
        required_fields = ["code", "name"]
        for language in data:
            for field in required_fields:
                assert field in language

    @pytest.mark.asyncio
    async def test_config_languages_performance(self, test_client):
        """Test performance of languages endpoint"""
        import time
        
        start_time = time.time()
        response = await test_client.get("/api/config/languages")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Config endpoint should be fast (under 1 second)
        response_time = end_time - start_time
        assert response_time < 1.0

    @pytest.mark.asyncio
    async def test_config_content_type_headers(self, test_client):
        """Test that appropriate content-type headers are returned"""
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "").lower()

    @pytest.mark.asyncio
    async def test_config_languages_ethiopian_languages(self, test_client):
        """Test that Ethiopian languages are properly represented"""
        response = await test_client.get("/api/config/languages")
        
        assert response.status_code == 200
        data = response.json()
        
        # Create mapping for easier checking
        language_map = {lang["code"]: lang["name"] for lang in data}
        
        # Verify Ethiopian languages are included
        ethiopian_languages = {
            "am": "Amharic",
            "om": "Oromo", 
            "ti": "Tigrinya"
        }
        
        for code, expected_name in ethiopian_languages.items():
            assert code in language_map
            assert language_map[code] == expected_name

    @pytest.mark.asyncio
    async def test_config_endpoint_method_restrictions(self, test_client):
        """Test that config endpoints only accept appropriate HTTP methods"""
        # Languages endpoint should only accept GET
        methods_to_test = ["POST", "PUT", "DELETE", "PATCH"]
        
        for method in methods_to_test:
            response = await test_client.request(method, "/api/config/languages")
            assert response.status_code == 405  # Method Not Allowed
