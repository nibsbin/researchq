#!/usr/bin/env python3
"""
Example demonstrating SQLite StorageProvider usage.

This example shows how to use the SQLiteStorageProvider for persistent
storage of question/response pairs across sessions.
"""

import asyncio
import tempfile
import os
from robora.classes import Question, QueryResponse
from robora.sqlite_storage import SQLiteStorageProvider
from robora.ask import Workflow
from robora.mock_query import MockQueryHandler, MockResponseModel


async def basic_sqlite_example():
    """Basic example of SQLite storage functionality."""
    print("=" * 60)
    print("Basic SQLite Storage Example")
    print("=" * 60)
    
    # Create a temporary SQLite database for this example
    # In real usage, you'd use a persistent path like "my_research.db"
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize SQLite storage provider
        storage = SQLiteStorageProvider(db_path=db_path)
        print(f"Initialized SQLite storage at: {db_path}")
        print(f"Initial count: {storage.count()}")
        
        # Create some test questions
        questions = [
            Question(
                word_set={"org": "Department of Defense", "country": "United States"},
                template="What is the cybersecurity posture of {org} in {country}?",
                response_model=MockResponseModel
            ),
            Question(
                word_set={"org": "NASA", "country": "United States"},
                template="What is the cybersecurity posture of {org} in {country}?",
                response_model=MockResponseModel
            ),
            Question(
                word_set={"org": "Ministry of Defence", "country": "Canada"},
                template="What is the cybersecurity posture of {org} in {country}?",
                response_model=MockResponseModel
            )
        ]
        
        # Create some test responses
        responses = [
            QueryResponse(
                full_response={"cybersecurity_level": 8, "assessment": "High security"},
                error=None
            ),
            QueryResponse(
                full_response={"cybersecurity_level": 7, "assessment": "Good security"},
                error=None
            ),
            QueryResponse(
                full_response=None,
                error="Unable to assess this organization"
            )
        ]
        
        # Save questions and responses
        print("\nSaving questions and responses...")
        for i, (question, response) in enumerate(zip(questions, responses)):
            await storage.save_response(question, response)
            print(f"  Saved question {i+1}: {question.value}")
        
        print(f"\nTotal stored responses: {storage.count()}")
        
        # Retrieve responses
        print("\nRetrieving responses...")
        for i, question in enumerate(questions):
            retrieved = await storage.get_response(question)
            if retrieved:
                if retrieved.error:
                    print(f"  Question {i+1}: Error - {retrieved.error}")
                else:
                    print(f"  Question {i+1}: Level {retrieved.full_response.get('cybersecurity_level', 'N/A')}")
            else:
                print(f"  Question {i+1}: No response found")
        
        # Demonstrate persistence by creating a new storage instance
        print("\nTesting persistence with new storage instance...")
        new_storage = SQLiteStorageProvider(db_path=db_path)
        print(f"New instance count: {new_storage.count()}")
        
        # List all stored questions
        print("\nAll stored questions:")
        stored_questions = []
        async for question in new_storage.get_stored_questions():
            stored_questions.append(question)
        
        for i, question in enumerate(stored_questions):
            print(f"  {i+1}: {question.template} -> {question.word_set}")
        
        # Clean up one response
        print(f"\nDeleting first response...")
        await new_storage.delete_response(questions[0])
        print(f"Count after deletion: {new_storage.count()}")
        
        # Clear all responses
        print(f"\nClearing all responses...")
        new_storage.clear()
        print(f"Count after clear: {new_storage.count()}")
        
    finally:
        # Clean up the temporary database
        print(f"\nCleaning up temporary database: {db_path}")
        if os.path.exists(db_path):
            os.unlink(db_path)


async def workflow_integration_example():
    """Example of using SQLite storage with the Workflow class."""
    print("\n" + "=" * 60)
    print("Workflow Integration Example")
    print("=" * 60)
    
    # Create a temporary SQLite database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Set up components
        query_handler = MockQueryHandler(MockResponseModel)
        storage = SQLiteStorageProvider(db_path=db_path)
        workflow = Workflow(query_handler=query_handler, storage=storage)
        
        print(f"Using SQLite storage: {storage}")
        
        # Create a test question
        question = Question(
            word_set={"department": "Department of Energy", "country": "Canada"},
            template="Assess the cybersecurity readiness of {department} in {country}",
            response_model=MockResponseModel
        )
        
        print(f"\nProcessing question: {question.value}")
        
        # Process question through workflow (first time)
        print("First request (will query and store):")
        answer1 = await workflow.ask(question)
        print(f"  Result: {answer1.fields}")
        print(f"  Storage count: {storage.count()}")
        
        # Process same question again (should use cached result)
        print("\nSecond request (should use cached result):")
        answer2 = await workflow.ask(question)
        print(f"  Result: {answer2.fields}")
        print(f"  Storage count: {storage.count()}")
        
        # Verify the results are the same
        if answer1.full_response == answer2.full_response:
            print("✓ Caching worked correctly - same response retrieved")
        else:
            print("✗ Caching issue - different responses")
        
        # Create a new workflow with the same storage to test persistence
        print("\nCreating new workflow with same storage...")
        new_workflow = Workflow(query_handler=query_handler, storage=storage)
        
        answer3 = await new_workflow.ask(question)
        print(f"  Result from new workflow: {answer3.fields}")
        
        if answer1.full_response == answer3.full_response:
            print("✓ Persistence worked correctly - same response from new workflow")
        else:
            print("✗ Persistence issue - different responses")
        
    finally:
        # Clean up
        print(f"\nCleaning up: {db_path}")
        if os.path.exists(db_path):
            os.unlink(db_path)


async def main():
    """Run all examples."""
    print("SQLite StorageProvider Examples")
    print("=" * 60)
    
    try:
        await basic_sqlite_example()
        await workflow_integration_example()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())