#!/usr/bin/env python3
"""Demo script to test storage functionality with AutoRA sprayer"""

import asyncio
import tempfile
import os
from researchq.storage import InMemoryStorage, SQLiteStorage, create_storage


async def demo_storage_basic():
    """Demo basic storage functionality"""
    print("=== Demo: Basic Storage Functionality ===\n")
    
    # Test sample data
    sample_result = {
        'query_id': '1',
        'research_question': 'Does the Ministry of Energy in USA have cybersecurity responsibilities?',
        'sonar_response': 'Mock response content...',
        'sonar_response_json': {'mock': 'data'},
        'ministry_domain': 'Energy',
        'country': 'USA',
        'parsing_success': True,
        'word_dict': {'ministry_domain': 'Energy', 'country': 'USA'}
    }
    
    # Test InMemoryStorage
    print("1. Testing InMemoryStorage:")
    memory_storage = InMemoryStorage()
    await memory_storage.store_query_result(sample_result)
    
    results = await memory_storage.retrieve_query_results()
    print(f"   Stored and retrieved {len(results)} result(s)")
    print(f"   Query ID: {results[0]['query_id']}")
    print(f"   Question: {results[0]['research_question'][:50]}...")
    
    df = await memory_storage.retrieve_as_dataframe()
    print(f"   DataFrame shape: {df.shape}")
    print(f"   DataFrame columns: {list(df.columns)[:5]}...")  # Show first 5 columns
    
    # Test SQLiteStorage
    print("\n2. Testing SQLiteStorage:")
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        sqlite_storage = SQLiteStorage(db_path)
        await sqlite_storage.store_query_result(sample_result)
        
        results = await sqlite_storage.retrieve_query_results()
        print(f"   Stored and retrieved {len(results)} result(s)")
        print(f"   Query ID: {results[0]['query_id']}")
        print(f"   Question: {results[0]['research_question'][:50]}...")
        
        df = await sqlite_storage.retrieve_as_dataframe()
        print(f"   DataFrame shape: {df.shape}")
        print(f"   DataFrame columns: {list(df.columns)[:5]}...")  # Show first 5 columns
        
        # Test persistence
        sqlite_storage2 = SQLiteStorage(db_path)
        results2 = await sqlite_storage2.retrieve_query_results()
        print(f"   Persistence test: Retrieved {len(results2)} result(s) from new storage instance")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    # Test storage factory
    print("\n3. Testing Storage Factory:")
    mem_storage = create_storage("memory")
    print(f"   Created memory storage: {type(mem_storage).__name__}")
    
    sqlite_storage = create_storage("sqlite", db_path="test_factory.db")
    print(f"   Created SQLite storage: {type(sqlite_storage).__name__}")
    
    # Cleanup
    if os.path.exists("test_factory.db"):
        os.unlink("test_factory.db")
    
    print("\nBasic storage demo completed successfully!")


async def demo_storage_filtering():
    """Demo storage filtering functionality"""
    print("\n=== Demo: Storage Filtering ===\n")
    
    storage = InMemoryStorage()
    
    # Store multiple results with different attributes
    results_data = [
        {'query_id': '1', 'country': 'USA', 'ministry_domain': 'Energy', 'parsing_success': True},
        {'query_id': '2', 'country': 'USA', 'ministry_domain': 'Transport', 'parsing_success': False},
        {'query_id': '3', 'country': 'Germany', 'ministry_domain': 'Energy', 'parsing_success': True},
        {'query_id': '4', 'country': 'Germany', 'ministry_domain': 'Transport', 'parsing_success': True},
    ]
    
    for result in results_data:
        result['research_question'] = f"Test question for {result['ministry_domain']} in {result['country']}"
        result['sonar_response'] = f"Test response {result['query_id']}"
        result['word_dict'] = {'country': result['country'], 'ministry_domain': result['ministry_domain']}
        await storage.store_query_result(result)
    
    print(f"Stored {len(results_data)} results")
    
    # Test filtering
    print("\nFiltering tests:")
    
    # Filter by country
    usa_results = await storage.retrieve_query_results({'country': 'USA'})
    print(f"   USA results: {len(usa_results)}")
    
    germany_results = await storage.retrieve_query_results({'country': 'Germany'})
    print(f"   Germany results: {len(germany_results)}")
    
    # Filter by parsing success
    success_results = await storage.retrieve_query_results({'parsing_success': True})
    print(f"   Successful parsing: {len(success_results)}")
    
    failed_results = await storage.retrieve_query_results({'parsing_success': False})
    print(f"   Failed parsing: {len(failed_results)}")
    
    # Filter by multiple criteria
    usa_energy_results = await storage.retrieve_query_results({
        'country': 'USA', 
        'ministry_domain': 'Energy'
    })
    print(f"   USA Energy results: {len(usa_energy_results)}")
    
    # Test count operations
    total_count = await storage.get_result_count()
    usa_count = await storage.get_result_count({'country': 'USA'})
    print(f"   Total count: {total_count}, USA count: {usa_count}")
    
    print("\nFiltering demo completed successfully!")


async def main():
    """Run all storage demos"""
    try:
        await demo_storage_basic()
        await demo_storage_filtering()
        print("\n🎉 All storage demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())