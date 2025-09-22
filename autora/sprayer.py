"""Sprays research questions at mass entities"""

import pandas as pd
import asyncio
from itertools import product
from typing import Dict, List, Any, Optional, Type, Union, Tuple
import traceback
import json
import time
from pydantic import BaseModel
from autora.llm import query_sonar, query_sonar_structured
from autora.storage import QueryStorage, create_storage

#======== Define word sets and research questions ========

word_sets = {
    "ministry_domain": ["Energy",  "Transport"],
    "country": ["USA", "Azerbaijan"],
}

research_questions = [
    "Does the department/ministry of {ministry_domain} in {country} have cybersecurity responsibilities?",




    "Does the department/ministry of {ministry_domain} in {country} handle cyber terrorism within its scope of responsibilities?",



    "Is the department/ministry of {ministry_domain} in {country} internally or externally focused?"
]

#=========================================================

async def process_single_query(task_data: Dict[str, Any], storage: Optional[QueryStorage] = None) -> Dict[str, Any]:
    """
    Process a single query task and return/store the result row data.
    
    Args:
        task_data: Dictionary containing task information
        storage: Optional QueryStorage instance to persist results
        
    Returns:
        Dictionary containing the processed row data
    """
    word_dict = task_data['word_dict']
    question_template = task_data['question_template']
    response_model = task_data['response_model']
    query_id = task_data['query_id']
    total_queries = task_data['total_queries']
    
    print(f"\nProcessing query {query_id}/{total_queries}: {word_dict}")
    
    # Format the research question with the current word combination
    formatted_question = question_template.format(**word_dict)
    print(f"  Query {query_id}/{total_queries}: {formatted_question[:80]}...")
    
    # Query Sonar API (structured or unstructured)
    try:
        if response_model is not None:
            # Use structured query with Pydantic model
            structured_result = await query_sonar_structured(formatted_question, response_model)
            response_json = structured_result['raw_response']
            response_content = response_json.get('choices', [{}])[0].get('message', {}).get('content', 'No response') if response_json else 'No response'
            
            # Add structured response data
            structured_data = structured_result['structured_data']
            parsing_success = structured_result['parsing_success']
            parsing_error = structured_result['parsing_error']
            retries_used = structured_result['retries_used']
            
            if parsing_success:
                print(f"    ✓ Got structured response ({len(response_content)} chars, {retries_used} retries)")
            else:
                print(f"    ⚠ Got response but parsing failed ({len(response_content)} chars, {retries_used} retries): {parsing_error}")
        else:
            # Use regular unstructured query
            response = await query_sonar(formatted_question)
            response_json = response
            response_content = response.get('choices', [{}])[0].get('message', {}).get('content', 'No response')
            structured_data = None
            parsing_success = None
            parsing_error = None
            retries_used = 0
            print(f"    ✓ Got response ({len(response_content)} chars)")
            
    except Exception as e:
        response_json = {"error": str(e), "traceback": traceback.format_exc()}
        response_content = f"Error: {str(e)}"
        structured_data = None
        parsing_success = False
        parsing_error = str(e)
        retries_used = 0
        print(f"    ✗ Error: {str(e)}")
        # Print full traceback for debugging
        print(f"    Full error: {traceback.format_exc()}")
        # Continue with other queries even if one fails
    
    # Create enriched citations by cross-referencing with search results
    enriched_citations = []
    if isinstance(response_json, dict):
        citations = response_json.get('citations', [])
        search_results = response_json.get('search_results', [])
        
        # Create a lookup dictionary for search results by URL
        search_lookup = {result.get('url', ''): result for result in search_results}
        
        for citation_url in citations:
            enriched_citation = {
                'url': citation_url,
                'title': None,
                'snippet': None,
                'date': None,
                'last_updated': None,
                'matched': False
            }
            
            # Try to find matching search result
            if citation_url in search_lookup:
                search_result = search_lookup[citation_url]
                enriched_citation.update({
                    'title': search_result.get('title'),
                    'snippet': search_result.get('snippet'),
                    'date': search_result.get('date'),
                    'last_updated': search_result.get('last_updated'),
                    'matched': True
                })
            
            enriched_citations.append(enriched_citation)
    
    # Create row data
    row_data = word_dict.copy()
    row_data.update({
        'query_id': str(query_id),
        'research_question': formatted_question,
        'sonar_response': response_content,
        'sonar_response_json': response_json,
        'question_template': question_template,
        'search_results': response_json.get('search_results', []) if isinstance(response_json, dict) else [],
        'citations': response_json.get('citations', []) if isinstance(response_json, dict) else [],
        'enriched_citations': enriched_citations,
        'content': response_json.get('choices', [{}])[0].get('message', {}).get('content', '') if isinstance(response_json, dict) else '',
        'word_dict': word_dict  # Store word_dict for storage abstraction
    })
    
    # Add structured response data if using a response model
    if response_model is not None:
        row_data.update({
            'structured_data': structured_data.model_dump() if structured_data else None,
            'parsing_success': parsing_success,
            'parsing_error': parsing_error,
            'retries_used': retries_used
        })
    
    # Store result if storage is provided
    if storage is not None:
        await storage.store_query_result(row_data)
    
    return row_data


async def spray(
    word_sets: Dict[str, List[str]] = None,
    research_questions: List[str] = None,
    max_concurrent: int = 1,
    delay_between_batches: float = 0.5,
    response_model: Optional[Type[BaseModel]] = None,
    max_queries: Optional[int] = None,
    storage: Optional[Union[QueryStorage, str]] = None,
    storage_config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Create a 2D table by permuting word sets and research questions,
    querying Sonar API for each combination. Supports both sequential and concurrent execution.
    
    Args:
        word_sets: Dictionary of word sets to use for combinations.
                  If None, uses the global word_sets variable.
        research_questions: List of research question templates.
                           If None, uses the global research_questions variable.
        max_concurrent: Maximum number of concurrent API calls (default: 1 for sequential)
                       Set to > 1 for concurrent execution
        delay_between_batches: Delay between batches in seconds (default: 0.5)
                              For sequential (max_concurrent=1), this is delay between each query
        response_model: Optional Pydantic model class to structure the response.
                       If provided, uses structured queries with JSON schema validation.
        max_queries: Optional limit on total queries to process
        storage: Storage instance or storage type string ("memory" or "sqlite").
                If None, uses in-memory storage for backward compatibility.
        storage_config: Additional configuration for storage (e.g., {"db_path": "custom.db"})
    
    Returns:
        pd.DataFrame: Table with columns for word set combinations, research questions, and API responses.
                     If response_model is provided, includes additional columns for structured data.
                     Data is retrieved from storage to ensure consistency.
    """
    # Set up storage
    if storage is None:
        storage_instance = create_storage("memory")
    elif isinstance(storage, str):
        config = storage_config or {}
        storage_instance = create_storage(storage, **config)
    elif isinstance(storage, QueryStorage):
        storage_instance = storage
    else:
        raise ValueError("storage must be None, a string, or a QueryStorage instance")
    
    # Use provided parameters or fall back to global variables
    current_word_sets = word_sets if word_sets is not None else globals()['word_sets']
    current_research_questions = research_questions if research_questions is not None else globals()['research_questions']
    
    # Generate all combinations of word sets
    word_set_keys = list(current_word_sets.keys())
    word_set_values = [current_word_sets[key] for key in word_set_keys]
    word_combinations = list(product(*word_set_values))
    
    total_queries = len(word_combinations) * len(current_research_questions)
    if max_queries is not None:
        total_queries = min(total_queries, max_queries)
    
    execution_mode = "concurrent" if max_concurrent > 1 else "sequential"
    print(f"Creating spray with {len(word_combinations)} word combinations and {len(current_research_questions)} research questions...")
    print(f"Total API calls to make: {total_queries}")
    print(f"Execution mode: {execution_mode} (max_concurrent={max_concurrent})")
    print(f"Storage type: {type(storage_instance).__name__}")
    
    # Prepare all query tasks
    all_tasks = []
    query_count = 0
    
    # Create all query tasks
    for i, word_combo in enumerate(word_combinations):
        # Create a dictionary mapping word set keys to their values for this combination
        word_dict = dict(zip(word_set_keys, word_combo))
        
        for j, question_template in enumerate(current_research_questions):
            if max_queries is not None and query_count >= max_queries:
                break
            query_count += 1
            
            # Create task for this query
            task_data = {
                'word_dict': word_dict,
                'question_template': question_template,
                'response_model': response_model,
                'query_id': query_count,
                'total_queries': total_queries
            }
            all_tasks.append(task_data)
        
        if max_queries is not None and query_count >= max_queries:
            break
    
    # Process tasks based on concurrency setting
    start_time = time.time()
    
    if max_concurrent <= 1:
        # Sequential processing
        for i, task_data in enumerate(all_tasks):
            await process_single_query(task_data, storage_instance)
            
            # Add configurable delay between queries (except for the last one)
            if i < len(all_tasks) - 1:
                await asyncio.sleep(delay_between_batches)
    else:
        # Concurrent processing with semaphore
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(task_data):
            async with semaphore:
                await process_single_query(task_data, storage_instance)
                # Add delay to respect rate limits
                await asyncio.sleep(delay_between_batches)
        
        # Process all tasks concurrently
        tasks = [process_with_semaphore(task_data) for task_data in all_tasks]
        await asyncio.gather(*tasks)
    
    elapsed_time = time.time() - start_time
    print(f"\n✓ Completed {len(all_tasks)} queries in {elapsed_time:.2f} seconds")
    if len(all_tasks) > 0:
        print(f"  Average time per query: {elapsed_time/len(all_tasks):.2f}s")
    
    # Retrieve results from storage as DataFrame
    df = await storage_instance.retrieve_as_dataframe()
    
    # Reorder columns for better readability if we have data
    if len(df) > 0:
        base_columns = word_set_keys
        other_columns = [
            'question_template', 'research_question', 'sonar_response_json',
            'search_results', 'citations', 'enriched_citations', 'content'
        ]
        
        # Add structured response columns if using a response model
        if response_model is not None:
            other_columns.extend(['structured_data', 'parsing_success', 'parsing_error', 'retries_used'])
        
        # Filter to only include columns that exist in the DataFrame
        available_columns = [col for col in base_columns + other_columns if col in df.columns]
        df = df[available_columns]
    
    return df





async def save_research_table(
    filename: str = "research_table",
    word_sets_param: Dict[str, List[str]] = None,
    research_questions_param: List[str] = None,
    max_concurrent: int = 1,
    delay_between_batches: float = 0.5,
    response_model: Optional[Type[BaseModel]] = None,
    storage_type: str = "memory",
    storage_config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Create and save the research table to CSV and JSON files.
    
    Args:
        filename: Base name for the output files (without extension)
        word_sets_param: Dictionary of word sets to use for combinations.
                        If None, uses the global word_sets variable.
        research_questions_param: List of research question templates.
                                If None, uses the global research_questions variable.
        max_concurrent: Maximum number of concurrent API calls (default: 1)
        delay_between_batches: Delay between batches in seconds (default: 0.5)
        response_model: Optional Pydantic model class to structure the response.
                       If provided, uses structured queries with JSON schema validation.
        storage_type: Type of storage to use ("memory" or "sqlite")
        storage_config: Additional configuration for storage
        
    Returns:
        pd.DataFrame: The created table
    """
    print("=" * 50)
    print("AutoRA Research Sprayer - Creating 2D Table")
    print("=" * 50)
    
    df = await spray(
        word_sets=word_sets_param,
        research_questions=research_questions_param,
        max_concurrent=max_concurrent,
        delay_between_batches=delay_between_batches,
        response_model=response_model,
        storage=storage_type,
        storage_config=storage_config
    )
    
    print(f"\n{'='*20} SAVING RESULTS {'='*20}")
    
    # Save as CSV (with JSON as string for compatibility)
    csv_filename = f"{filename}.csv"
    df_csv = df.copy()
    df_csv['sonar_response_json'] = df_csv['sonar_response_json'].apply(lambda x: json.dumps(x) if isinstance(x, dict) else str(x))
    df_csv.to_csv(csv_filename, index=False)
    print(f"✓ Saved CSV to {csv_filename}")
    
    # Save as JSON (preserving full JSON structure)
    json_filename = f"{filename}.json"
    df.to_json(json_filename, orient='records', indent=2)
    print(f"✓ Saved JSON to {json_filename}")
    
    print(f"✓ Table created with {len(df)} rows and {len(df.columns)} columns")
    
    # Use current parameters for summary
    current_word_sets = word_sets_param if word_sets_param is not None else word_sets
    current_research_questions = research_questions_param if research_questions_param is not None else research_questions
    
    print(f"\n{'='*20} TABLE SUMMARY {'='*20}")
    if len(df) > 0:
        print(f"Word set combinations: {len(df.groupby(list(current_word_sets.keys())))}")
        print(f"Research questions: {len(current_research_questions)}")
        print(f"Total rows: {len(df)}")
        
        print(f"\n{'='*20} SAMPLE DATA {'='*20}")
        # Show first few rows in a prettier format
        word_set_keys = list(current_word_sets.keys())
        for i, (idx, row) in enumerate(df.head(3).iterrows()):
            print(f"\n--- Row {i+1} ---")
            # Show word set values
            for key in word_set_keys:
                if key in row:
                    print(f"{key}: {row[key]}")
            print(f"Question: {row['research_question']}")
            response_preview = row['sonar_response'][:150] + "..." if len(str(row['sonar_response'])) > 150 else row['sonar_response']
            print(f"Response: {response_preview}")
        
        if len(df) > 3:
            print(f"\n... and {len(df) - 3} more rows")
    
    print(f"\n{'='*20} COLUMN INFO {'='*20}")
    print("Columns in the table:")
    for i, col in enumerate(df.columns, 1):
        print(f"{i:2d}. {col}")
    
    return df


# Add demo functions for testing specific combinations
async def demo_single_query():
    """
    Demo function to test a single query using spray() with minimal parameters (unstructured).
    """
    # Create minimal word sets for just one combination
    demo_word_sets = {
        "ministry_domain": ["Energy"],
        "country": ["USA"]
    }
    
    # Use just one research question
    demo_questions = [
        "Does the department/ministry of {ministry_domain} in {country} have cybersecurity responsibilities?"
    ]
    
    print("Testing single UNSTRUCTURED query using spray() with minimal parameters...")
    print(f"Word sets: {demo_word_sets}")
    print(f"Questions: {demo_questions}")
    
    try:
        # Use spray with max_queries=1 to get a single query
        df = await spray(
            word_sets=demo_word_sets,
            research_questions=demo_questions,
            max_concurrent=1,  # Sequential for demo
            delay_between_batches=0.1,  # Faster for demo
            max_queries=1  # Only process one query
        )
        
        print(f"\n{'='*20} DEMO RESULTS {'='*20}")
        print(f"✓ Created table with {len(df)} row(s)")
        
        if len(df) > 0:
            row = df.iloc[0]
            print(f"\n📋 Query Details:")
            for col in ['ministry_domain', 'country']:
                if col in row:
                    print(f"   {col}: {row[col]}")
            if 'research_question' in row:
                print(f"   Question: {row['research_question']}")
            
            print(f"\n💬 API Response:")
            if 'sonar_response' in row:
                response_content = str(row['sonar_response'])
                # Format the response nicely with line breaks
                lines = response_content.split('\n')
                for line in lines[:10]:  # Show first 10 lines
                    if line.strip():
                        print(f"   {line}")
                
                if len(lines) > 10:
                    print(f"   ... ({len(lines) - 10} more lines)")
                
                print(f"\n📊 Response Stats:")
                print(f"   Characters: {len(response_content)}")
            
            if 'sonar_response_json' in row and isinstance(row['sonar_response_json'], dict):
                json_data = row['sonar_response_json']
                if 'usage' in json_data:
                    usage = json_data['usage']
                    print(f"   Tokens used: {usage.get('total_tokens', 'N/A')}")
                    if 'cost' in usage:
                        print(f"   Cost: ${usage['cost'].get('total_cost', 0)}")
                if 'citations' in json_data:
                    print(f"   Citations: {len(json_data['citations'])}")
        
        return df
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Full error: {traceback.format_exc()}")
        return None


async def demo_structured_query():
    """
    Demo function to test a single structured query using spray() with a Pydantic model.
    """
    from examples.pydantic_models import SimpleYesNoResponse
    
    # Create minimal word sets for just one combination
    demo_word_sets = {
        "ministry_domain": ["Energy"],
        "country": ["USA"]
    }
    
    # Use just one research question
    demo_questions = [
        "Does the department/ministry of {ministry_domain} in {country} have cybersecurity responsibilities?"
    ]
    
    print("Testing single STRUCTURED query using spray() with Pydantic model...")
    print(f"Word sets: {demo_word_sets}")
    print(f"Questions: {demo_questions}")
    print(f"Response model: SimpleYesNoResponse")
    
    try:
        # Use spray with structured response model and max_queries=1
        df = await spray(
            word_sets=demo_word_sets,
            research_questions=demo_questions,
            max_concurrent=1,  # Sequential for demo
            delay_between_batches=0.1,  # Faster for demo
            response_model=SimpleYesNoResponse,
            max_queries=1  # Only process one query
        )
        
        print(f"\n{'='*20} STRUCTURED DEMO RESULTS {'='*20}")
        print(f"✓ Created table with {len(df)} row(s)")
        print(f"✓ Columns: {list(df.columns)}")
        
        if len(df) > 0:
            row = df.iloc[0]
            print(f"\n📋 Query Details:")
            for col in ['ministry_domain', 'country']:
                if col in row:
                    print(f"   {col}: {row[col]}")
            if 'research_question' in row:
                print(f"   Question: {row['research_question']}")
            if 'parsing_success' in row:
                print(f"   Parsing Success: {row['parsing_success']}")
            if 'retries_used' in row:
                print(f"   Retries Used: {row['retries_used']}")
            
            if 'parsing_success' in row and row['parsing_success'] and 'structured_data' in row:
                structured = row['structured_data']
                print(f"\n🎯 Structured Response:")
                print(f"   Answer: {structured.get('answer', 'N/A')}")
                print(f"   Confidence: {structured.get('confidence', 'N/A')}")
                print(f"   Explanation: {structured.get('explanation', 'N/A')}")
                print(f"   Sources: {structured.get('sources', 'N/A')}")
            elif 'parsing_error' in row:
                print(f"   Parsing Error: {row['parsing_error']}")
            
            print(f"\n💬 Raw API Response:")
            if 'sonar_response' in row:
                response_content = str(row['sonar_response'])
                lines = response_content.split('\n')
                for line in lines[:5]:  # Show first 5 lines
                    if line.strip():
                        print(f"   {line}")
                
                if len(lines) > 5:
                    print(f"   ... ({len(lines) - 5} more lines)")
        
        return df
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Full error: {traceback.format_exc()}")
        return None




async def save_research_table_concurrent(
    filename: str = "research_table_concurrent",
    word_sets_param: Dict[str, List[str]] = None,
    research_questions_param: List[str] = None,
    max_concurrent: int = 5,
    delay_between_batches: float = 1.0,
    response_model: Optional[Type[BaseModel]] = None,
    storage_type: str = "memory",
    storage_config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Create and save the research table using concurrent processing.
    
    Args:
        filename: Base name for the output files (without extension)
        word_sets_param: Dictionary of word sets to use for combinations.
        research_questions_param: List of research question templates.
        max_concurrent: Maximum number of concurrent API calls
        delay_between_batches: Delay between batches in seconds
        response_model: Optional Pydantic model class to structure the response.
        storage_type: Type of storage to use ("memory" or "sqlite")
        storage_config: Additional configuration for storage
        
    Returns:
        pd.DataFrame: The created table
    """
    print("=" * 50)
    print("AutoRA Research Sprayer - Concurrent Processing")
    print("=" * 50)
    
    df = await spray(
        word_sets=word_sets_param,
        research_questions=research_questions_param,
        max_concurrent=max_concurrent,
        delay_between_batches=delay_between_batches,
        response_model=response_model,
        storage=storage_type,
        storage_config=storage_config
    )
    
    print(f"\n{'='*20} SAVING RESULTS {'='*20}")
    
    # Save as CSV (with JSON as string for compatibility)
    csv_filename = f"{filename}.csv"
    df_csv = df.copy()
    if 'sonar_response_json' in df_csv.columns:
        df_csv['sonar_response_json'] = df_csv['sonar_response_json'].apply(lambda x: json.dumps(x) if isinstance(x, dict) else str(x))
    df_csv.to_csv(csv_filename, index=False)
    print(f"✓ Saved CSV to {csv_filename}")
    
    # Save as JSON (preserving full JSON structure)
    json_filename = f"{filename}.json"
    df.to_json(json_filename, orient='records', indent=2)
    print(f"✓ Saved JSON to {json_filename}")
    
    print(f"✓ Table created with {len(df)} rows and {len(df.columns)} columns")
    
    # Use current parameters for summary
    current_word_sets = word_sets_param if word_sets_param is not None else word_sets
    current_research_questions = research_questions_param if research_questions_param is not None else research_questions
    
    print(f"\n{'='*20} TABLE SUMMARY {'='*20}")
    if len(df) > 0:
        # Get available word set keys from DataFrame columns
        word_set_keys = [key for key in current_word_sets.keys() if key in df.columns]
        if word_set_keys:
            print(f"Word set combinations: {len(df.groupby(word_set_keys))}")
        print(f"Research questions: {len(current_research_questions)}")
        print(f"Total rows: {len(df)}")
        
        print(f"\n{'='*20} SAMPLE DATA {'='*20}")
        # Show first few rows in a prettier format
        for i, (idx, row) in enumerate(df.head(3).iterrows()):
            print(f"\n--- Row {i+1} ---")
            # Show word set values
            for key in word_set_keys:
                if key in row:
                    print(f"{key}: {row[key]}")
            if 'research_question' in row:
                print(f"Question: {row['research_question']}")
            if 'sonar_response' in row:
                response_preview = str(row['sonar_response'])[:150] + "..." if len(str(row['sonar_response'])) > 150 else str(row['sonar_response'])
                print(f"Response: {response_preview}")
        
        if len(df) > 3:
            print(f"\n... and {len(df) - 3} more rows")
    
    print(f"\n{'='*20} COLUMN INFO {'='*20}")
    print("Columns in the table:")
    for i, col in enumerate(df.columns, 1):
        print(f"{i:2d}. {col}")
    
    return df


def main():
    """Main entry point for the sprayer"""
    print("AutoRA Research Sprayer")
    print("=" * 25)
    print("Choose an option:")
    print("1. Demo single query (unstructured)")
    print("2. Demo single query (structured with Pydantic)")
    print("3. Full research spray (save to files)")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        print("\nRunning demo single unstructured query...")
        asyncio.run(demo_single_query())
    elif choice == "2":
        print("\nRunning demo single structured query...")
        asyncio.run(demo_structured_query())
    elif choice == "3":
        print("\nRunning full research spray...")
        asyncio.run(save_research_table_concurrent())
    else:
        print("Invalid choice. Running unstructured demo by default...")
        asyncio.run(demo_single_query())


if __name__ == "__main__":
    main()

