#!/usr/bin/env python3
"""Demo script showing sprayer integration with storage"""

import asyncio
import tempfile
import os
from unittest.mock import AsyncMock, patch

from autora.sprayer import spray, process_single_query
from autora.storage import InMemoryStorage, SQLiteStorage


async def demo_sprayer_with_storage():
    """Demo sprayer functionality with storage backends"""
    print("=== Demo: Sprayer with Storage Integration ===\n")
    
    # Mock LLM response to avoid API calls
    mock_response = {
        'choices': [{
            'message': {
                'content': 'Based on my research, the Department of Energy in the USA does have cybersecurity responsibilities...'
            }
        }],
        'usage': {'total_tokens': 150, 'cost': {'total_cost': 0.01}},
        'citations': ['https://www.energy.gov/cybersecurity'],
        'search_results': [
            {
                'url': 'https://www.energy.gov/cybersecurity',
                'title': 'Cybersecurity at DOE',
                'snippet': 'The Department of Energy...'
            }
        ]
    }
    
    # Test data
    word_sets = {
        'ministry_domain': ['Energy', 'Transport'],
        'country': ['USA', 'Germany']
    }
    
    questions = [
        'Does the department/ministry of {ministry_domain} in {country} have cybersecurity responsibilities?'
    ]
    
    with patch('autora.sprayer.query_sonar', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_response
        
        # Test 1: Memory Storage
        print("1. Testing with InMemoryStorage:")
        df_memory = await spray(
            word_sets=word_sets,
            research_questions=questions,
            storage="memory",
            max_queries=2,  # Limit for demo
            delay_between_batches=0.1
        )
        
        print(f"   Created DataFrame with {len(df_memory)} rows")
        print(f"   Columns: {list(df_memory.columns)[:5]}...")
        print(f"   Sample data:")
        for i, row in df_memory.head(2).iterrows():
            print(f"     Row {i+1}: {row['ministry_domain']} in {row['country']}")
        
        # Test 2: SQLite Storage
        print("\n2. Testing with SQLiteStorage:")
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            df_sqlite = await spray(
                word_sets=word_sets,
                research_questions=questions,
                storage="sqlite",
                storage_config={'db_path': db_path},
                max_queries=2,  # Limit for demo
                delay_between_batches=0.1
            )
            
            print(f"   Created DataFrame with {len(df_sqlite)} rows")
            print(f"   Columns: {list(df_sqlite.columns)[:5]}...")
            
            # Test persistence by creating new storage instance
            sqlite_storage = SQLiteStorage(db_path)
            stored_results = await sqlite_storage.retrieve_query_results()
            print(f"   Persistence check: {len(stored_results)} results in database")
            
            # Test filtering
            usa_results = await sqlite_storage.retrieve_query_results({'country': 'USA'})
            print(f"   Filtered USA results: {len(usa_results)}")
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
        
        # Test 3: Storage Instance
        print("\n3. Testing with custom storage instance:")
        custom_storage = InMemoryStorage()
        
        df_custom = await spray(
            word_sets={'ministry_domain': ['Energy'], 'country': ['USA']},
            research_questions=questions,
            storage=custom_storage,
            max_queries=1,
            delay_between_batches=0.1
        )
        
        print(f"   Created DataFrame with {len(df_custom)} rows")
        
        # Verify we can access the same storage instance
        stored_count = await custom_storage.get_result_count()
        print(f"   Custom storage contains {stored_count} results")
        
        # Test 4: Backward compatibility (no storage parameter)
        print("\n4. Testing backward compatibility (no storage param):")
        df_compat = await spray(
            word_sets={'ministry_domain': ['Transport'], 'country': ['Germany']},
            research_questions=questions,
            max_queries=1,
            delay_between_batches=0.1
        )
        
        print(f"   Created DataFrame with {len(df_compat)} rows (uses default memory storage)")
        print(f"   Available columns: {list(df_compat.columns)}")
        # Check if 'sonar_response' column exists, otherwise use 'content'
        response_col = 'sonar_response' if 'sonar_response' in df_compat.columns else 'content'
        if response_col in df_compat.columns:
            print(f"   Sample response content: {df_compat.iloc[0][response_col][:50]}...")
        
    print("\n🎉 Sprayer storage integration demo completed successfully!")


async def demo_structured_with_storage():
    """Demo structured responses with storage"""
    print("\n=== Demo: Structured Responses with Storage ===\n")
    
    try:
        from examples.pydantic_models import SimpleYesNoResponse
        
        # Mock structured response
        mock_structured_result = {
            'raw_response': {
                'choices': [{'message': {'content': 'Mock structured content'}}],
                'usage': {'total_tokens': 75}
            },
            'structured_data': SimpleYesNoResponse(
                answer=True,
                confidence='high',
                explanation='The Department of Energy has significant cybersecurity responsibilities.'
            ),
            'parsing_success': True,
            'parsing_error': None,
            'retries_used': 0
        }
        
        word_sets = {'ministry_domain': ['Energy'], 'country': ['USA']}
        questions = ['Does {ministry_domain} in {country} have cybersecurity responsibilities?']
        
        with patch('autora.sprayer.query_sonar_structured', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_structured_result
            
            # Create temporary database for structured data
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name
            
            try:
                df = await spray(
                    word_sets=word_sets,
                    research_questions=questions,
                    response_model=SimpleYesNoResponse,
                    storage="sqlite",
                    storage_config={'db_path': db_path},
                    max_queries=1,
                    delay_between_batches=0.1
                )
                
                print(f"Created structured DataFrame with {len(df)} rows")
                print(f"Structured columns: {[col for col in df.columns if 'structured' in col or 'parsing' in col]}")
                
                row = df.iloc[0]
                print(f"Parsing success: {row['parsing_success']}")
                print(f"Structured answer: {row['structured_data']['answer']}")
                print(f"Confidence: {row['structured_data']['confidence']}")
                print(f"Explanation: {row['structured_data']['explanation'][:50]}...")
                
                # Verify storage contains structured data
                storage = SQLiteStorage(db_path)
                results = await storage.retrieve_query_results()
                print(f"Storage contains {len(results)} structured results")
                
            finally:
                if os.path.exists(db_path):
                    os.unlink(db_path)
        
        print("\n🎯 Structured responses with storage demo completed!")
        
    except ImportError:
        print("Skipping structured demo - pydantic models not available")


async def main():
    """Run all demos"""
    try:
        await demo_sprayer_with_storage()
        await demo_structured_with_storage()
        print("\n✅ All sprayer storage demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())