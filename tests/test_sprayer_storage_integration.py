"""Test integration of storage with sprayer functionality"""

import asyncio
import tempfile
import os
import pytest
from unittest.mock import AsyncMock, patch

from autora.storage import InMemoryStorage, SQLiteStorage, create_storage
from autora.sprayer import spray, process_single_query


@pytest.fixture
def temp_db_path():
    """Temporary database path for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_query_response():
    """Mock response from LLM query"""
    return {
        'choices': [{
            'message': {
                'content': 'Mock response content'
            }
        }],
        'usage': {'total_tokens': 100},
        'citations': ['http://example.com'],
        'search_results': [{'url': 'http://example.com', 'title': 'Example'}]
    }


class TestSprayerStorageIntegration:
    """Test integration between sprayer and storage"""
    
    @pytest.mark.asyncio
    async def test_process_single_query_with_memory_storage(self, mock_query_response):
        """Test process_single_query stores results in memory storage"""
        storage = InMemoryStorage()
        
        task_data = {
            'word_dict': {'ministry_domain': 'Energy', 'country': 'USA'},
            'question_template': 'Does {ministry_domain} in {country} have responsibilities?',
            'response_model': None,
            'query_id': 1,
            'total_queries': 1
        }
        
        # Mock the LLM query
        with patch('autora.sprayer.query_sonar', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_query_response
            
            # Process query with storage
            result = await process_single_query(task_data, storage)
            
            # Verify result structure
            assert result['query_id'] == '1'
            assert result['ministry_domain'] == 'Energy'
            assert result['country'] == 'USA'
            assert 'research_question' in result
            assert 'sonar_response' in result
            
            # Verify data was stored
            stored_results = await storage.retrieve_query_results()
            assert len(stored_results) == 1
            assert stored_results[0]['query_id'] == '1'
            assert stored_results[0]['ministry_domain'] == 'Energy'
    
    @pytest.mark.asyncio
    async def test_process_single_query_with_sqlite_storage(self, mock_query_response, temp_db_path):
        """Test process_single_query stores results in SQLite storage"""
        storage = SQLiteStorage(temp_db_path)
        
        task_data = {
            'word_dict': {'ministry_domain': 'Transport', 'country': 'Germany'},
            'question_template': 'Does {ministry_domain} in {country} have cybersecurity?',
            'response_model': None,
            'query_id': 1,
            'total_queries': 1
        }
        
        # Mock the LLM query
        with patch('autora.sprayer.query_sonar', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_query_response
            
            # Process query with storage
            result = await process_single_query(task_data, storage)
            
            # Verify result structure
            assert result['query_id'] == '1'
            assert result['ministry_domain'] == 'Transport'
            assert result['country'] == 'Germany'
            
            # Verify data was stored in database
            stored_results = await storage.retrieve_query_results()
            assert len(stored_results) == 1
            assert stored_results[0]['query_id'] == '1'
            assert stored_results[0]['ministry_domain'] == 'Transport'
            assert stored_results[0]['country'] == 'Germany'
    
    @pytest.mark.asyncio
    async def test_spray_with_memory_storage(self, mock_query_response):
        """Test spray function with memory storage"""
        word_sets = {
            'ministry_domain': ['Energy', 'Transport'],
            'country': ['USA']
        }
        questions = ['Does {ministry_domain} in {country} have cybersecurity responsibilities?']
        
        # Mock the LLM query
        with patch('autora.sprayer.query_sonar', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_query_response
            
            # Run spray with memory storage
            df = await spray(
                word_sets=word_sets,
                research_questions=questions,
                storage="memory",
                max_queries=2
            )
            
            # Verify DataFrame
            assert len(df) == 2
            assert 'ministry_domain' in df.columns
            assert 'country' in df.columns
            assert 'research_question' in df.columns
            
            # Check data content
            ministries = set(df['ministry_domain'].tolist())
            assert ministries == {'Energy', 'Transport'}
            
            countries = set(df['country'].tolist()) 
            assert countries == {'USA'}
    
    @pytest.mark.asyncio
    async def test_spray_with_sqlite_storage(self, mock_query_response, temp_db_path):
        """Test spray function with SQLite storage"""
        word_sets = {
            'ministry_domain': ['Energy'],
            'country': ['USA', 'Germany']
        }
        questions = ['Does {ministry_domain} in {country} have cybersecurity responsibilities?']
        
        storage_config = {'db_path': temp_db_path}
        
        # Mock the LLM query
        with patch('autora.sprayer.query_sonar', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_query_response
            
            # Run spray with SQLite storage
            df = await spray(
                word_sets=word_sets,
                research_questions=questions,
                storage="sqlite",
                storage_config=storage_config,
                max_queries=2
            )
            
            # Verify DataFrame
            assert len(df) == 2
            assert 'ministry_domain' in df.columns
            assert 'country' in df.columns
            
            # Check data content
            countries = set(df['country'].tolist())
            assert countries == {'USA', 'Germany'}
            
            # Verify data persists in database
            storage = SQLiteStorage(temp_db_path)
            stored_results = await storage.retrieve_query_results()
            assert len(stored_results) == 2
    
    @pytest.mark.asyncio
    async def test_spray_with_storage_instance(self, mock_query_response):
        """Test spray function with a storage instance"""
        storage = InMemoryStorage()
        
        word_sets = {
            'ministry_domain': ['Energy'],
            'country': ['USA']
        }
        questions = ['Does {ministry_domain} in {country} have cybersecurity responsibilities?']
        
        # Mock the LLM query
        with patch('autora.sprayer.query_sonar', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_query_response
            
            # Run spray with storage instance
            df = await spray(
                word_sets=word_sets,
                research_questions=questions,
                storage=storage,
                max_queries=1
            )
            
            # Verify DataFrame
            assert len(df) == 1
            
            # Verify data is in the same storage instance
            stored_results = await storage.retrieve_query_results()
            assert len(stored_results) == 1
            assert stored_results[0]['ministry_domain'] == 'Energy'
            assert stored_results[0]['country'] == 'USA'
    
    @pytest.mark.asyncio
    async def test_spray_backward_compatibility(self, mock_query_response):
        """Test spray function maintains backward compatibility (no storage param)"""
        word_sets = {
            'ministry_domain': ['Energy'],
            'country': ['USA']
        }
        questions = ['Does {ministry_domain} in {country} have cybersecurity responsibilities?']
        
        # Mock the LLM query
        with patch('autora.sprayer.query_sonar', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_query_response
            
            # Run spray without storage parameter (should default to memory)
            df = await spray(
                word_sets=word_sets,
                research_questions=questions,
                max_queries=1
            )
            
            # Verify DataFrame
            assert len(df) == 1
            assert 'ministry_domain' in df.columns
            assert 'country' in df.columns
            assert 'research_question' in df.columns
    
    @pytest.mark.asyncio
    async def test_spray_with_structured_response(self, temp_db_path):
        """Test spray function with structured responses and storage"""
        from examples.pydantic_models import SimpleYesNoResponse
        
        word_sets = {
            'ministry_domain': ['Energy'],
            'country': ['USA']
        }
        questions = ['Does {ministry_domain} in {country} have cybersecurity responsibilities?']
        
        # Mock structured response
        mock_structured_result = {
            'raw_response': {
                'choices': [{'message': {'content': 'Mock structured content'}}],
                'usage': {'total_tokens': 50}
            },
            'structured_data': SimpleYesNoResponse(
                answer=True,
                confidence='high',
                explanation='Test explanation'
            ),
            'parsing_success': True,
            'parsing_error': None,
            'retries_used': 0
        }
        
        # Mock the structured LLM query
        with patch('autora.sprayer.query_sonar_structured', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_structured_result
            
            # Run spray with structured response and SQLite storage
            df = await spray(
                word_sets=word_sets,
                research_questions=questions,
                response_model=SimpleYesNoResponse,
                storage="sqlite",
                storage_config={'db_path': temp_db_path},
                max_queries=1
            )
            
            # Verify DataFrame includes structured data columns
            assert len(df) == 1
            assert 'structured_data' in df.columns
            assert 'parsing_success' in df.columns
            assert 'parsing_error' in df.columns
            assert 'retries_used' in df.columns
            
            # Verify structured data content
            row = df.iloc[0]
            assert row['parsing_success'] == True
            assert isinstance(row['structured_data'], dict)
            assert row['structured_data']['answer'] == True
            assert row['structured_data']['confidence'] == 'high'
    
    @pytest.mark.asyncio
    async def test_error_handling_with_storage(self, temp_db_path):
        """Test error handling still works with storage"""
        storage = SQLiteStorage(temp_db_path)
        
        task_data = {
            'word_dict': {'ministry_domain': 'Energy', 'country': 'USA'},
            'question_template': 'Does {ministry_domain} in {country} have responsibilities?',
            'response_model': None,
            'query_id': 1,
            'total_queries': 1
        }
        
        # Mock an exception in the LLM query
        with patch('autora.sprayer.query_sonar', new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = Exception("API Error")
            
            # Process query with storage
            result = await process_single_query(task_data, storage)
            
            # Verify error was handled
            assert 'Error: API Error' in result['sonar_response']
            # For unstructured queries, parsing_success/error are not set
            # They're only set for structured queries with response_model
            
            # Verify error result was still stored
            stored_results = await storage.retrieve_query_results()
            assert len(stored_results) == 1
            assert 'Error: API Error' in stored_results[0]['sonar_response']
    
    def test_invalid_storage_type(self):
        """Test error handling for invalid storage types"""
        word_sets = {'ministry_domain': ['Energy'], 'country': ['USA']}
        questions = ['Test question']
        
        # Test invalid storage type
        with pytest.raises(ValueError, match="storage must be None, a string, or a QueryStorage instance"):
            # This should fail during validation before any async operations
            async def run_test():
                await spray(word_sets=word_sets, research_questions=questions, storage=123)
            
            # Run the async test
            asyncio.run(run_test())