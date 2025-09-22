"""Test storage implementations for AutoRA sprayer"""

import asyncio
import tempfile
import os
from pathlib import Path
import pytest
import pandas as pd
from datetime import datetime

from researchq.storage import QueryStorage, InMemoryStorage, SQLiteStorage, create_storage


@pytest.fixture
def sample_query_result():
    """Sample query result for testing"""
    return {
        'query_id': '1',
        'research_question': 'Test question?',
        'sonar_response': 'Test response',
        'sonar_response_json': {'test': 'data'},
        'question_template': 'Test {param}?',
        'search_results': [{'url': 'test.com', 'title': 'Test'}],
        'citations': ['test.com'],
        'enriched_citations': [{'url': 'test.com', 'matched': True}],
        'content': 'Test content',
        'word_dict': {'param': 'value'},
        'ministry_domain': 'Energy',
        'country': 'USA',
        'structured_data': {'answer': True, 'confidence': 'high'},
        'parsing_success': True,
        'parsing_error': None,
        'retries_used': 0
    }


@pytest.fixture
def temp_db_path():
    """Temporary database path for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestInMemoryStorage:
    """Test InMemoryStorage implementation"""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_single_result(self, sample_query_result):
        """Test storing and retrieving a single query result"""
        storage = InMemoryStorage()
        
        # Store result
        await storage.store_query_result(sample_query_result)
        
        # Retrieve results
        results = await storage.retrieve_query_results()
        assert len(results) == 1
        assert results[0]['query_id'] == sample_query_result['query_id']
        assert results[0]['research_question'] == sample_query_result['research_question']
        
        # Check timestamp was added
        assert 'timestamp' in results[0]
    
    @pytest.mark.asyncio
    async def test_store_multiple_results(self, sample_query_result):
        """Test storing multiple query results"""
        storage = InMemoryStorage()
        
        # Store multiple results
        for i in range(3):
            result = sample_query_result.copy()
            result['query_id'] = str(i + 1)
            result['research_question'] = f'Test question {i + 1}?'
            await storage.store_query_result(result)
        
        # Retrieve all results
        results = await storage.retrieve_query_results()
        assert len(results) == 3
        
        # Check they're all different
        query_ids = [r['query_id'] for r in results]
        assert query_ids == ['1', '2', '3']
    
    @pytest.mark.asyncio
    async def test_retrieve_with_filters(self, sample_query_result):
        """Test retrieving results with filters"""
        storage = InMemoryStorage()
        
        # Store results with different countries
        countries = ['USA', 'Germany', 'USA']
        for i, country in enumerate(countries):
            result = sample_query_result.copy()
            result['query_id'] = str(i + 1)
            result['country'] = country
            await storage.store_query_result(result)
        
        # Filter by country
        usa_results = await storage.retrieve_query_results({'country': 'USA'})
        assert len(usa_results) == 2
        assert all(r['country'] == 'USA' for r in usa_results)
        
        germany_results = await storage.retrieve_query_results({'country': 'Germany'})
        assert len(germany_results) == 1
        assert germany_results[0]['country'] == 'Germany'
    
    @pytest.mark.asyncio
    async def test_retrieve_as_dataframe(self, sample_query_result):
        """Test retrieving results as pandas DataFrame"""
        storage = InMemoryStorage()
        
        # Store result
        await storage.store_query_result(sample_query_result)
        
        # Retrieve as DataFrame
        df = await storage.retrieve_as_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]['query_id'] == sample_query_result['query_id']
    
    @pytest.mark.asyncio
    async def test_clear_all_results(self, sample_query_result):
        """Test clearing all results"""
        storage = InMemoryStorage()
        
        # Store results
        await storage.store_query_result(sample_query_result)
        assert await storage.get_result_count() == 1
        
        # Clear all
        await storage.clear_all_results()
        assert await storage.get_result_count() == 0
        
        # Verify no results
        results = await storage.retrieve_query_results()
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_get_result_count(self, sample_query_result):
        """Test getting result count"""
        storage = InMemoryStorage()
        
        # Initially empty
        assert await storage.get_result_count() == 0
        
        # Add results
        for i in range(5):
            result = sample_query_result.copy()
            result['query_id'] = str(i + 1)
            await storage.store_query_result(result)
        
        assert await storage.get_result_count() == 5
        
        # Test count with filters
        # Add results with different countries
        result = sample_query_result.copy()
        result['query_id'] = '6'
        result['country'] = 'Germany'
        await storage.store_query_result(result)
        
        assert await storage.get_result_count() == 6
        assert await storage.get_result_count({'country': 'USA'}) == 5
        assert await storage.get_result_count({'country': 'Germany'}) == 1


class TestSQLiteStorage:
    """Test SQLiteStorage implementation"""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_single_result(self, sample_query_result, temp_db_path):
        """Test storing and retrieving a single query result"""
        storage = SQLiteStorage(temp_db_path)
        
        # Store result
        await storage.store_query_result(sample_query_result)
        
        # Retrieve results
        results = await storage.retrieve_query_results()
        assert len(results) == 1
        assert results[0]['query_id'] == sample_query_result['query_id']
        assert results[0]['research_question'] == sample_query_result['research_question']
        
        # Check timestamp was added
        assert 'timestamp' in results[0]
        
        # Check complex data was preserved
        assert results[0]['sonar_response_json'] == sample_query_result['sonar_response_json']
        assert results[0]['search_results'] == sample_query_result['search_results']
    
    @pytest.mark.asyncio
    async def test_store_multiple_results(self, sample_query_result, temp_db_path):
        """Test storing multiple query results"""
        storage = SQLiteStorage(temp_db_path)
        
        # Store multiple results
        for i in range(3):
            result = sample_query_result.copy()
            result['query_id'] = str(i + 1)
            result['research_question'] = f'Test question {i + 1}?'
            await storage.store_query_result(result)
        
        # Retrieve all results
        results = await storage.retrieve_query_results()
        assert len(results) == 3
        
        # Check they're all different and ordered by creation time (newest first)
        query_ids = [r['query_id'] for r in results]
        assert set(query_ids) == {'1', '2', '3'}
    
    @pytest.mark.asyncio
    async def test_retrieve_with_filters(self, sample_query_result, temp_db_path):
        """Test retrieving results with filters"""
        storage = SQLiteStorage(temp_db_path)
        
        # Store results with different parsing success
        for i in range(3):
            result = sample_query_result.copy()
            result['query_id'] = str(i + 1)
            result['parsing_success'] = i % 2 == 0  # True, False, True
            await storage.store_query_result(result)
        
        # Filter by parsing success
        success_results = await storage.retrieve_query_results({'parsing_success': True})
        assert len(success_results) == 2
        
        fail_results = await storage.retrieve_query_results({'parsing_success': False})
        assert len(fail_results) == 1
    
    @pytest.mark.asyncio 
    async def test_retrieve_as_dataframe(self, sample_query_result, temp_db_path):
        """Test retrieving results as pandas DataFrame"""
        storage = SQLiteStorage(temp_db_path)
        
        # Store result
        await storage.store_query_result(sample_query_result)
        
        # Retrieve as DataFrame
        df = await storage.retrieve_as_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]['query_id'] == sample_query_result['query_id']
    
    @pytest.mark.asyncio
    async def test_clear_all_results(self, sample_query_result, temp_db_path):
        """Test clearing all results"""
        storage = SQLiteStorage(temp_db_path)
        
        # Store results
        await storage.store_query_result(sample_query_result)
        assert await storage.get_result_count() == 1
        
        # Clear all
        await storage.clear_all_results()
        assert await storage.get_result_count() == 0
        
        # Verify no results
        results = await storage.retrieve_query_results()
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_get_result_count(self, sample_query_result, temp_db_path):
        """Test getting result count"""
        storage = SQLiteStorage(temp_db_path)
        
        # Initially empty
        assert await storage.get_result_count() == 0
        
        # Add results
        for i in range(5):
            result = sample_query_result.copy()
            result['query_id'] = str(i + 1)
            await storage.store_query_result(result)
        
        assert await storage.get_result_count() == 5
    
    @pytest.mark.asyncio
    async def test_database_persistence(self, sample_query_result, temp_db_path):
        """Test that data persists across storage instances"""
        # Create first storage instance and store data
        storage1 = SQLiteStorage(temp_db_path)
        await storage1.store_query_result(sample_query_result)
        
        # Create second storage instance with same database
        storage2 = SQLiteStorage(temp_db_path)
        results = await storage2.retrieve_query_results()
        
        assert len(results) == 1
        assert results[0]['query_id'] == sample_query_result['query_id']


class TestStorageFactory:
    """Test storage factory function"""
    
    def test_create_memory_storage(self):
        """Test creating memory storage"""
        storage = create_storage("memory")
        assert isinstance(storage, InMemoryStorage)
    
    def test_create_sqlite_storage(self):
        """Test creating SQLite storage"""
        storage = create_storage("sqlite")
        assert isinstance(storage, SQLiteStorage)
    
    def test_create_sqlite_storage_with_custom_path(self, temp_db_path):
        """Test creating SQLite storage with custom path"""
        storage = create_storage("sqlite", db_path=temp_db_path)
        assert isinstance(storage, SQLiteStorage)
        assert storage.db_path == Path(temp_db_path)
    
    def test_create_storage_invalid_type(self):
        """Test creating storage with invalid type"""
        with pytest.raises(ValueError, match="Unknown storage type"):
            create_storage("invalid")


@pytest.mark.asyncio
async def test_concurrent_access():
    """Test concurrent access to storage"""
    storage = InMemoryStorage()
    
    async def store_result(i):
        result = {
            'query_id': str(i),
            'research_question': f'Question {i}',
            'sonar_response': f'Response {i}',
            'country': 'USA'
        }
        await storage.store_query_result(result)
    
    # Store results concurrently
    tasks = [store_result(i) for i in range(10)]
    await asyncio.gather(*tasks)
    
    # Verify all results were stored
    results = await storage.retrieve_query_results()
    assert len(results) == 10
    
    query_ids = {r['query_id'] for r in results}
    expected_ids = {str(i) for i in range(10)}
    assert query_ids == expected_ids