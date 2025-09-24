"""Tests for SQLite storage provider implementation."""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from robora.sqlite_storage import SQLiteStorageProvider
from robora.classes import Question, QueryResponse


class MockResponseModel:
    """Mock response model for testing."""
    __name__ = "MockResponseModel"


class TestSQLiteStorageProvider:
    """Test the SQLiteStorageProvider implementation."""
    
    def setup_method(self):
        """Set up test fixtures with temporary database."""
        # Create a temporary database file for each test
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.storage = SQLiteStorageProvider(db_path=self.db_path)
        self.question = Question(
            word_set={"org": "TestOrg"},
            template="Test question about {org}",
            response_model=MockResponseModel
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove the temporary database file
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_response(self):
        """Test saving and retrieving responses."""
        test_response = QueryResponse(
            full_response={"test": "data", "cybersecurity_level": 7},
            error=None
        )
        
        # Save response
        await self.storage.save_response(self.question, test_response)
        assert self.storage.count() == 1
        
        # Retrieve response
        retrieved = await self.storage.get_response(self.question)
        assert retrieved is not None
        assert retrieved.full_response == test_response.full_response
        assert retrieved.error == test_response.error
    
    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_response(self):
        """Test retrieving a response that doesn't exist."""
        nonexistent_question = Question(
            word_set={"org": "NonExistent"},
            template="Question about {org}",
            response_model=MockResponseModel
        )
        
        retrieved = await self.storage.get_response(nonexistent_question)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_save_response_with_error(self):
        """Test saving and retrieving a response with an error."""
        error_response = QueryResponse(
            full_response=None,
            error="Test error message"
        )
        
        await self.storage.save_response(self.question, error_response)
        retrieved = await self.storage.get_response(self.question)
        
        assert retrieved is not None
        assert retrieved.full_response is None
        assert retrieved.error == "Test error message"
    
    @pytest.mark.asyncio
    async def test_multiple_responses(self):
        """Test storing multiple responses."""
        question1 = Question(
            word_set={"org": "Org1"},
            template="Question about {org}",
            response_model=MockResponseModel
        )
        question2 = Question(
            word_set={"org": "Org2"},
            template="Question about {org}",
            response_model=MockResponseModel
        )
        
        response1 = QueryResponse(full_response={"data": "response1"}, error=None)
        response2 = QueryResponse(full_response={"data": "response2"}, error=None)
        
        await self.storage.save_response(question1, response1)
        await self.storage.save_response(question2, response2)
        
        assert self.storage.count() == 2
        
        resp1 = await self.storage.get_response(question1)
        resp2 = await self.storage.get_response(question2)
        
        assert resp1.full_response["data"] == "response1"
        assert resp2.full_response["data"] == "response2"
    
    @pytest.mark.asyncio
    async def test_update_existing_response(self):
        """Test updating an existing response (INSERT OR REPLACE)."""
        original_response = QueryResponse(
            full_response={"version": "original"},
            error=None
        )
        updated_response = QueryResponse(
            full_response={"version": "updated"},
            error=None
        )
        
        # Save original
        await self.storage.save_response(self.question, original_response)
        assert self.storage.count() == 1
        
        # Update with new response
        await self.storage.save_response(self.question, updated_response)
        assert self.storage.count() == 1  # Should still be 1 (replaced, not added)
        
        # Verify the update
        retrieved = await self.storage.get_response(self.question)
        assert retrieved.full_response["version"] == "updated"
    
    @pytest.mark.asyncio
    async def test_delete_response(self):
        """Test deleting responses."""
        test_response = QueryResponse(full_response={"test": "data"}, error=None)
        
        # Save and verify it exists
        await self.storage.save_response(self.question, test_response)
        assert self.storage.count() == 1
        
        # Delete and verify it's gone
        await self.storage.delete_response(self.question)
        assert self.storage.count() == 0
        
        # Verify we can't retrieve it
        retrieved = await self.storage.get_response(self.question)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_response(self):
        """Test deleting a response that doesn't exist (should not error)."""
        nonexistent_question = Question(
            word_set={"org": "NonExistent"},
            template="Question about {org}",
            response_model=MockResponseModel
        )
        
        # Should not raise an error
        await self.storage.delete_response(nonexistent_question)
        assert self.storage.count() == 0
    
    @pytest.mark.asyncio
    async def test_get_stored_questions(self):
        """Test retrieving all stored questions."""
        question1 = Question(
            word_set={"org": "Org1"},
            template="Question about {org}",
            response_model=MockResponseModel
        )
        question2 = Question(
            word_set={"org": "Org2", "country": "Country2"},
            template="Question about {org} in {country}",
            response_model=MockResponseModel
        )
        
        response1 = QueryResponse(full_response={"data": "response1"}, error=None)
        response2 = QueryResponse(full_response={"data": "response2"}, error=None)
        
        await self.storage.save_response(question1, response1)
        await self.storage.save_response(question2, response2)
        
        # Collect all stored questions
        stored_questions = []
        async for question in self.storage.get_stored_questions():
            stored_questions.append(question)
        
        assert len(stored_questions) == 2
        
        # Verify questions are properly deserialized
        # Note: Questions won't be exactly equal due to response_model being None after deserialization
        question_templates = [q.template for q in stored_questions]
        question_word_sets = [q.word_set for q in stored_questions]
        
        assert "Question about {org}" in question_templates
        assert "Question about {org} in {country}" in question_templates
        assert {"org": "Org1"} in question_word_sets
        assert {"org": "Org2", "country": "Country2"} in question_word_sets
    
    def test_utility_methods(self):
        """Test utility methods."""
        assert self.storage.count() == 0
        
        # Test clear on empty database
        self.storage.clear()
        assert self.storage.count() == 0
        
        # Add some data and test clear
        test_response = QueryResponse(full_response={"test": "data"}, error=None)
        asyncio.run(self.storage.save_response(self.question, test_response))
        assert self.storage.count() == 1
        
        self.storage.clear()
        assert self.storage.count() == 0
    
    def test_repr_and_str(self):
        """Test string representations."""
        repr_str = repr(self.storage)
        str_str = str(self.storage)
        
        assert "SQLiteStorageProvider" in repr_str
        assert str(self.db_path) in repr_str
        assert "stored_responses=0" in repr_str
        
        assert "SQLiteStorageProvider" in str_str
        assert "0 stored responses" in str_str
        assert str(self.db_path) in str_str
    
    def test_database_persistence(self):
        """Test that data persists across provider instances."""
        # Save data with first instance
        test_response = QueryResponse(full_response={"persistent": "data"}, error=None)
        asyncio.run(self.storage.save_response(self.question, test_response))
        assert self.storage.count() == 1
        
        # Create new instance with same database
        new_storage = SQLiteStorageProvider(db_path=self.db_path)
        assert new_storage.count() == 1
        
        # Verify we can retrieve the data
        retrieved = asyncio.run(new_storage.get_response(self.question))
        assert retrieved is not None
        assert retrieved.full_response["persistent"] == "data"
    
    def test_question_hashing_consistency(self):
        """Test that question hashing works consistently for storage/retrieval."""
        # Create two identical questions
        question1 = Question(
            word_set={"org": "TestOrg", "country": "TestCountry"},
            template="Test {org} in {country}",
            response_model=MockResponseModel
        )
        question2 = Question(
            word_set={"org": "TestOrg", "country": "TestCountry"},
            template="Test {org} in {country}",
            response_model=MockResponseModel
        )
        
        # They should have the same hash
        assert hash(question1) == hash(question2)
        
        # Save with question1, retrieve with question2
        test_response = QueryResponse(full_response={"test": "hash_consistency"}, error=None)
        asyncio.run(self.storage.save_response(question1, test_response))
        
        retrieved = asyncio.run(self.storage.get_response(question2))
        assert retrieved is not None
        assert retrieved.full_response["test"] == "hash_consistency"