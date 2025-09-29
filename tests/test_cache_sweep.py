"""Tests for cache sweep functionality in ask_multiple_stream."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from robora.workflow import Workflow
from robora.classes import Question, QuestionSet, QueryResponse
from robora.session_storage import SessionStorageProvider
from robora.mock_query import MockQueryHandler
from examples.pydantic_models import SimpleYesNoResponse


class TestCacheSweep:
    
    @pytest_asyncio.fixture
    async def workflow(self):
        """Create a workflow with mock query handler and session storage."""
        storage = SessionStorageProvider()
        query_handler = MockQueryHandler(response_model=SimpleYesNoResponse)
        return Workflow(query_handler, storage, workers=2)
    
    @pytest.fixture
    def question_set(self):
        """Create a simple question set for testing."""
        word_sets = {
            "country": ["France", "Germany", "Canada"]
        }
        template = "Does {country} have a cybersecurity strategy?"
        return QuestionSet(template, word_sets, SimpleYesNoResponse)
    
    @pytest.mark.asyncio
    async def test_cache_sweep_all_cache_misses(self, workflow, question_set, capsys):
        """Test cache sweep when all questions are cache misses."""
        answers = []
        async for answer in workflow.ask_multiple_stream(question_set):
            answers.append(answer)
        
        # Should have 3 answers (3 countries)
        assert len(answers) == 3
        
        # Check output for cache statistics
        captured = capsys.readouterr()
        assert "cache sweep complete - 0 cached, 3 need querying" in captured.out
        
    @pytest.mark.asyncio
    async def test_cache_sweep_with_cached_responses(self, workflow, question_set, capsys):
        """Test cache sweep when some responses are cached."""
        # First, populate cache by running once
        first_run_answers = []
        async for answer in workflow.ask_multiple_stream(question_set):
            first_run_answers.append(answer)
        
        # Check storage has items
        storage_count = workflow.storage.count()
        print(f"Storage has {storage_count} items after first run")
        
        # Clear captured output from first run
        capsys.readouterr()
        
        # Second run should use cached responses
        second_run_answers = []
        async for answer in workflow.ask_multiple_stream(question_set):
            second_run_answers.append(answer)
            
        # Should have same number of answers
        assert len(second_run_answers) == 3
        
        # Check output for cache statistics
        captured = capsys.readouterr()
        print(f"Captured output: {captured.out}")
        assert "cache sweep complete - 3 cached, 0 need querying" in captured.out
        assert "Returning cached response for:" in captured.out
        
    @pytest.mark.asyncio
    async def test_cache_sweep_mixed_cache_hits_and_misses(self, workflow, question_set, capsys):
        """Test cache sweep with some cached and some new questions."""
        # First, run with subset of questions to populate cache partially
        word_sets_partial = {
            "country": ["France", "Germany"]  # Only 2 countries
        }
        template = "Does {country} have a cybersecurity strategy?"
        partial_question_set = QuestionSet(template, word_sets_partial, SimpleYesNoResponse)
        
        # Populate partial cache
        partial_answers = []
        async for answer in workflow.ask_multiple_stream(partial_question_set):
            partial_answers.append(answer)
        
        # Clear captured output
        capsys.readouterr()
        
        # Now run with full question set (includes Canada which isn't cached)
        full_answers = []
        async for answer in workflow.ask_multiple_stream(question_set):
            full_answers.append(answer)
            
        # Should have 3 answers total
        assert len(full_answers) == 3
        
        # Check output for cache statistics - 2 cached (France, Germany), 1 new (Canada)
        captured = capsys.readouterr()
        assert "cache sweep complete - 2 cached, 1 need querying" in captured.out
        
    @pytest.mark.asyncio
    async def test_overwrite_bypasses_cache(self, workflow, question_set, capsys):
        """Test that overwrite=True bypasses cache completely."""
        # First run to populate cache
        first_answers = []
        async for answer in workflow.ask_multiple_stream(question_set):
            first_answers.append(answer)
        
        # Clear captured output
        capsys.readouterr()
        
        # Second run with overwrite=True should ignore cache
        second_answers = []
        async for answer in workflow.ask_multiple_stream(question_set, overwrite=True):
            second_answers.append(answer)
            
        # Should have same number of answers
        assert len(second_answers) == 3
        
        # Check output - should show all as needing querying
        captured = capsys.readouterr()
        assert "cache sweep complete - 0 cached, 3 need querying" in captured.out