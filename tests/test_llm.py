"""
Pytest tests for the researchq.llm module
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from researchq.llm import query_sonar, query_sonar_with_context


class TestQuerySonar:
    """Test cases for the query_sonar function"""

    @pytest.fixture
    def mock_response(self):
        """Mock response from Perplexity API"""
        return {
            "choices": [
                {
                    "message": {
                        "content": "Here are the major AI developments from today...",
                        "role": "assistant"
                    }
                }
            ],
            "model": "sonar",
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150
            }
        }

    @pytest.mark.asyncio
    async def test_query_sonar_default_prompt(self, mock_response):
        """Test query_sonar with default prompt"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b'{"test": "content"}'
            mock_instance.post.return_value = mock_response_obj

            # Call function
            result = await query_sonar()

            # Assertions
            assert result == mock_response
            mock_instance.post.assert_called_once()
            
            # Check the call arguments
            call_args = mock_instance.post.call_args
            assert call_args[0][0] == "https://api.perplexity.ai/chat/completions"
            
            # Check headers
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Bearer ")
            assert headers["Content-Type"] == "application/json"
            
            # Check JSON payload
            json_data = call_args[1]["json"]
            assert json_data["model"] == "sonar"
            assert len(json_data["messages"]) == 1
            assert json_data["messages"][0]["role"] == "user"
            assert "AI developments" in json_data["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_query_sonar_custom_prompt(self, mock_response):
        """Test query_sonar with custom prompt"""
        custom_prompt = "What is the weather like today?"
        
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b'{"test": "content"}'
            mock_instance.post.return_value = mock_response_obj

            # Call function
            result = await query_sonar(prompt=custom_prompt)

            # Assertions
            assert result == mock_response
            
            # Check the call arguments
            call_args = mock_instance.post.call_args
            json_data = call_args[1]["json"]
            assert json_data["messages"][0]["content"] == custom_prompt

    @pytest.mark.asyncio
    async def test_query_sonar_custom_model(self, mock_response):
        """Test query_sonar with custom model"""
        custom_model = "sonar-pro"
        
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b'{"test": "content"}'
            mock_instance.post.return_value = mock_response_obj

            # Call function
            result = await query_sonar(model=custom_model)

            # Assertions
            assert result == mock_response
            
            # Check the call arguments
            call_args = mock_instance.post.call_args
            json_data = call_args[1]["json"]
            assert json_data["model"] == custom_model

    @pytest.mark.asyncio
    async def test_query_sonar_http_error(self):
        """Test query_sonar handles HTTP errors"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock to raise an HTTP status error
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = MagicMock()
            mock_response_obj.raise_for_status.side_effect = httpx.HTTPStatusError("404 Not Found", request=None, response=None)
            mock_instance.post.return_value = mock_response_obj

            # Call function and expect exception
            with pytest.raises(httpx.HTTPStatusError):
                await query_sonar()

    @pytest.mark.asyncio
    async def test_query_sonar_json_decode_error(self):
        """Test query_sonar handles JSON decode errors"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = MagicMock()
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b'invalid json'
            mock_response_obj.json.side_effect = ValueError("Invalid JSON")
            mock_response_obj.status_code = 200
            mock_response_obj.text = "invalid json response"
            mock_instance.post.return_value = mock_response_obj

            # Call function and expect exception
            with pytest.raises(ValueError, match="Failed to parse JSON response"):
                await query_sonar()

    @pytest.mark.asyncio
    async def test_query_sonar_empty_response(self):
        """Test query_sonar handles empty response"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = MagicMock()
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b''  # Empty content
            mock_instance.post.return_value = mock_response_obj

            # Call function and expect exception
            with pytest.raises(ValueError, match="Empty response from API"):
                await query_sonar()


class TestQuerySonarWithContext:
    """Test cases for the query_sonar_with_context function"""

    @pytest.fixture
    def mock_response(self):
        """Mock response from Perplexity API"""
        return {
            "choices": [
                {
                    "message": {
                        "content": "Based on our previous conversation...",
                        "role": "assistant"
                    }
                }
            ],
            "model": "sonar",
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 200,
                "total_tokens": 350
            }
        }

    @pytest.fixture
    def sample_context(self):
        """Sample conversation context"""
        return [
            {"role": "user", "content": "Hello, can you help me?"},
            {"role": "assistant", "content": "Of course! How can I assist you today?"},
            {"role": "user", "content": "I have a question about AI."}
        ]

    @pytest.mark.asyncio
    async def test_query_sonar_with_context_basic(self, mock_response, sample_context):
        """Test query_sonar_with_context with basic context"""
        current_prompt = "What are the latest developments?"
        
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b'{"test": "content"}'
            mock_instance.post.return_value = mock_response_obj

            # Call function
            result = await query_sonar_with_context(current_prompt, sample_context)

            # Assertions
            assert result == mock_response
            
            # Check the call arguments
            call_args = mock_instance.post.call_args
            json_data = call_args[1]["json"]
            
            # Should have context messages plus the new prompt
            expected_messages = sample_context + [{"role": "user", "content": current_prompt}]
            assert json_data["messages"] == expected_messages
            assert json_data["model"] == "sonar"

    @pytest.mark.asyncio
    async def test_query_sonar_with_context_empty_context(self, mock_response):
        """Test query_sonar_with_context with empty context"""
        current_prompt = "What are the latest developments?"
        empty_context = []
        
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b'{"test": "content"}'
            mock_instance.post.return_value = mock_response_obj

            # Call function
            result = await query_sonar_with_context(current_prompt, empty_context)

            # Assertions
            assert result == mock_response
            
            # Check the call arguments
            call_args = mock_instance.post.call_args
            json_data = call_args[1]["json"]
            
            # Should only have the current prompt
            assert len(json_data["messages"]) == 1
            assert json_data["messages"][0]["role"] == "user"
            assert json_data["messages"][0]["content"] == current_prompt

    @pytest.mark.asyncio
    async def test_query_sonar_with_context_custom_model(self, mock_response, sample_context):
        """Test query_sonar_with_context with custom model"""
        current_prompt = "What are the latest developments?"
        custom_model = "sonar-large"
        
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b'{"test": "content"}'
            mock_instance.post.return_value = mock_response_obj

            # Call function
            result = await query_sonar_with_context(current_prompt, sample_context, model=custom_model)

            # Assertions
            assert result == mock_response
            
            # Check the call arguments
            call_args = mock_instance.post.call_args
            json_data = call_args[1]["json"]
            assert json_data["model"] == custom_model

    @pytest.mark.asyncio
    async def test_query_sonar_with_context_http_error(self, sample_context):
        """Test query_sonar_with_context handles HTTP errors"""
        current_prompt = "What are the latest developments?"
        
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock to raise an HTTP status error
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = MagicMock()
            mock_response_obj.raise_for_status.side_effect = httpx.HTTPStatusError("500 Server Error", request=None, response=None)
            mock_instance.post.return_value = mock_response_obj

            # Call function and expect exception
            with pytest.raises(httpx.HTTPStatusError):
                await query_sonar_with_context(current_prompt, sample_context)


class TestAPIConfiguration:
    """Test API configuration and setup"""

    @pytest.mark.asyncio
    async def test_api_key_usage(self):
        """Test that API key is properly used in requests"""
        with patch('httpx.AsyncClient') as mock_client, \
             patch('researchq.llm.PERPLEXITY_API_KEY', 'test-api-key'):
            
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.return_value.json.return_value = {"test": "response"}

            # Call function
            await query_sonar()

            # Check that API key is used correctly
            call_args = mock_instance.post.call_args
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test-api-key"

    @pytest.mark.asyncio
    async def test_correct_endpoint_used(self):
        """Test that the correct API endpoint is used"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = {"test": "response"}
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b'{"test": "response"}'
            mock_instance.post.return_value = mock_response_obj

            # Call function
            await query_sonar()

            # Check that correct endpoint is called
            call_args = mock_instance.post.call_args
            assert call_args[0][0] == "https://api.perplexity.ai/chat/completions"


class TestIntegrationScenarios:
    """Integration-style tests for common usage scenarios"""

    @pytest.mark.asyncio
    async def test_conversation_flow(self):
        """Test a typical conversation flow using both functions"""
        mock_responses = [
            {
                "choices": [{"message": {"content": "Initial response", "role": "assistant"}}]
            },
            {
                "choices": [{"message": {"content": "Follow-up response", "role": "assistant"}}]
            }
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_response_obj = AsyncMock()
            mock_response_obj.raise_for_status.return_value = None
            mock_response_obj.content = b'{"test": "content"}'
            mock_instance.post.return_value = mock_response_obj
            mock_response_obj.json.side_effect = mock_responses

            # First query
            initial_response = await query_sonar("Tell me about AI")
            assert initial_response == mock_responses[0]
            
            # Build context for follow-up
            context = [
                {"role": "user", "content": "Tell me about AI"},
                {"role": "assistant", "content": "Initial response"}
            ]
            
            # Follow-up query with context
            followup_response = await query_sonar_with_context("Can you elaborate?", context)
            assert followup_response == mock_responses[1]
            
            # Verify both calls were made
            assert mock_instance.post.call_count == 2


if __name__ == "__main__":
    # Run the tests when called directly
    pytest.main([__file__, "-v"])
