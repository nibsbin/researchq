"""Tests for mock components implementation."""

import pytest
import asyncio
from string import Template
from researchq.mock_query import MockQueryHandler, MockResponseModel
from researchq.session_storage import SessionStorageProvider
from researchq.classes import Question
from researchq.ask import Workflow


class TestMockResponseModel:
    """Test the MockResponseModel Pydantic model."""
    
    def test_model_creation(self):
        """Test creating a MockResponseModel instance."""
        model = MockResponseModel(
            cybersecurity_level=8,
            explanation="High security implementation with comprehensive controls"
        )
        assert model.cybersecurity_level == 8
        assert "comprehensive controls" in model.explanation
    
    def test_model_validation(self):
        """Test model validation."""
        # Valid data
        data = {"cybersecurity_level": 5, "explanation": "Medium security level"}
        model = MockResponseModel.model_validate(data)
        assert model.cybersecurity_level == 5
        
        # Test field types
        with pytest.raises(Exception):  # Should fail with wrong type
            MockResponseModel(cybersecurity_level="not_a_number", explanation="test")


class TestMockQueryHandler:
    """Test the MockQueryHandler implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = MockQueryHandler(MockResponseModel)
    
    @pytest.mark.asyncio
    async def test_query_returns_response(self):
        """Test that query returns a valid QueryResponse."""
        response = await self.handler.query("Test question", MockResponseModel)
        
        assert response.full_response is not None
        assert response.error is None
        assert "choices" in response.full_response
        assert "citations" in response.full_response
        assert "search_results" in response.full_response
    
    def test_extract_fields(self):
        """Test field extraction from mock response."""
        # Create a mock response structure
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"cybersecurity_level": 6, "explanation": "Test explanation"}'
                    }
                }
            ],
            "citations": ["https://test.com"],
            "search_results": [
                {
                    "url": "https://test.com",
                    "title": "Test Title",
                    "snippet": "Test snippet"
                }
            ]
        }
        
        fields = self.handler.extract_fields(mock_response)
        
        assert fields["cybersecurity_level"] == 6
        assert fields["explanation"] == "Test explanation"
        assert "enriched_citations" in fields
        assert len(fields["enriched_citations"]) == 1
        assert fields["enriched_citations"][0]["matched"] is True
    
    def test_extract_fields_empty_response(self):
        """Test field extraction with empty response."""
        fields = self.handler.extract_fields({})
        assert fields == {}
        
        fields = self.handler.extract_fields(None)
        assert fields == {}


class TestSessionStorageProvider:
    """Test the SessionStorageProvider implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.storage = SessionStorageProvider()
        self.question = Question(
            word_set={"org": "TestOrg"},
            template=Template("Test question about {org}"),
            response_model=MockResponseModel
        )
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_response(self):
        """Test saving and retrieving responses."""
        test_response = {"test": "data", "cybersecurity_level": 7}
        
        # Save response
        await self.storage.save_response(self.question, test_response)
        assert self.storage.count() == 1
        
        # Retrieve response
        retrieved = await self.storage.get_response(self.question)
        assert "test" in str(retrieved)
        assert "cybersecurity_level" in str(retrieved)
    
    @pytest.mark.asyncio
    async def test_multiple_responses(self):
        """Test storing multiple responses."""
        question1 = Question(
            word_set={"org": "Org1"},
            template=Template("Question about {org}"),
            response_model=MockResponseModel
        )
        question2 = Question(
            word_set={"org": "Org2"},
            template=Template("Question about {org}"),
            response_model=MockResponseModel
        )
        
        await self.storage.save_response(question1, {"data": "response1"})
        await self.storage.save_response(question2, {"data": "response2"})
        
        assert self.storage.count() == 2
        
        resp1 = await self.storage.get_response(question1)
        resp2 = await self.storage.get_response(question2)
        
        assert "response1" in str(resp1)
        assert "response2" in str(resp2)
    
    def test_utility_methods(self):
        """Test utility methods."""
        assert self.storage.count() == 0
        
        # Test clear
        self.storage._storage["test"] = {"data": "test"}
        assert self.storage.count() == 1
        
        self.storage.clear()
        assert self.storage.count() == 0
        
        # Test get_all_responses
        self.storage._storage["test1"] = {"data": "test1"}
        self.storage._storage["test2"] = {"data": "test2"}
        
        all_responses = self.storage.get_all_responses()
        assert len(all_responses) == 2
        assert "test1" in all_responses
        assert "test2" in all_responses


class TestWorkflowIntegration:
    """Test integration of all components with Workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_handler = MockQueryHandler(MockResponseModel)
        self.storage = SessionStorageProvider()
        self.workflow = Workflow(query_handler=self.mock_handler, storage=self.storage)
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete workflow with mock components."""
        question = Question(
            word_set={"department": "TestDept", "country": "TestCountry"},
            template=Template("Assess {department} in {country}"),
            response_model=MockResponseModel
        )
        
        # Process question through workflow
        answer = await self.workflow.ask_question(question)
        
        # Verify answer structure
        assert answer.word_set == question.word_set
        assert answer.question_value == question.get_string()
        assert answer.full_response is not None
        assert answer.fields is not None
        
        # Verify fields contain expected data
        assert "cybersecurity_level" in answer.fields
        assert "explanation" in answer.fields
        assert "enriched_citations" in answer.fields
        
        # Verify storage worked
        assert self.storage.count() == 1
        
        # Verify we can retrieve from storage
        stored_response = await self.storage.get_response(question)
        assert stored_response != "No response found for this question"