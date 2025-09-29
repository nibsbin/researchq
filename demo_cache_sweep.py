"""Demo script to showcase the cache sweep functionality."""

import asyncio
from robora.workflow import Workflow
from robora.classes import QuestionSet
from robora.session_storage import SessionStorageProvider
from robora.mock_query import MockQueryHandler
from examples.pydantic_models import SimpleYesNoResponse


async def demo_cache_sweep():
    """Demonstrate the cache sweep functionality."""
    print("=== Cache Sweep Demo ===\n")
    
    # Setup
    storage = SessionStorageProvider()
    query_handler = MockQueryHandler(response_model=SimpleYesNoResponse)
    workflow = Workflow(query_handler, storage, workers=2)
    
    # Create question set
    word_sets = {
        "country": ["France", "Germany", "Canada", "United States"]
    }
    template = "Does {country} have a national cybersecurity strategy?"
    question_set = QuestionSet(template, word_sets, SimpleYesNoResponse)
    
    print("First run - all questions will be cache misses:")
    print("-" * 50)
    
    first_answers = []
    async for answer in workflow.ask_multiple_stream(question_set):
        first_answers.append(answer)
    
    print(f"\nFirst run complete. Got {len(first_answers)} answers.")
    print(f"Storage now contains {storage.count()} cached responses.\n")
    
    print("Second run - all questions should be cache hits:")
    print("-" * 50)
    
    second_answers = []
    async for answer in workflow.ask_multiple_stream(question_set):
        second_answers.append(answer)
    
    print(f"\nSecond run complete. Got {len(second_answers)} answers.")
    print(f"Storage still contains {storage.count()} cached responses (no new queries).\n")
    
    # Demonstrate mixed scenario
    print("Third run with additional country - mixed cache hits/misses:")
    print("-" * 60)
    
    word_sets_extended = {
        "country": ["France", "Germany", "Canada", "United States", "Japan"]
    }
    extended_question_set = QuestionSet(template, word_sets_extended, SimpleYesNoResponse)
    
    third_answers = []
    async for answer in workflow.ask_multiple_stream(extended_question_set):
        third_answers.append(answer)
    
    print(f"\nThird run complete. Got {len(third_answers)} answers.")
    print(f"Storage now contains {storage.count()} cached responses.\n")
    
    # Demonstrate overwrite functionality
    print("Fourth run with overwrite=True - should bypass all cache:")
    print("-" * 55)
    
    fourth_answers = []
    async for answer in workflow.ask_multiple_stream(question_set, overwrite=True):
        fourth_answers.append(answer)
    
    print(f"\nFourth run complete. Got {len(fourth_answers)} answers.")
    print(f"Storage now contains {storage.count()} cached responses (responses updated).\n")
    
    print("=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_cache_sweep())