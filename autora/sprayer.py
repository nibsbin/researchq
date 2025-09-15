"""Sprays research questions at mass entities"""

import pandas as pd
import asyncio
from itertools import product
from typing import Dict, List, Any, Optional, Type, Union
import traceback
import json
from pydantic import BaseModel
from autora.llm import query_sonar, query_sonar_structured

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

async def spray(
    word_sets_param: Dict[str, List[str]] = None,
    research_questions_param: List[str] = None,
    delay_seconds: float = 0.5,
    response_model: Optional[Type[BaseModel]] = None
) -> pd.DataFrame:
    """
    Create a 2D table by permuting word sets and research questions,
    querying Sonar API for each combination.
    
    Args:
        word_sets_param: Dictionary of word sets to use for combinations.
                        If None, uses the global word_sets variable.
        research_questions_param: List of research question templates.
                                If None, uses the global research_questions variable.
        delay_seconds: Delay between API calls in seconds (default: 0.5)
        response_model: Optional Pydantic model class to structure the response.
                       If provided, uses structured queries with JSON schema validation.
    
    Returns:
        pd.DataFrame: Table with columns for word set combinations, research questions, and API responses.
                     If response_model is provided, includes additional columns for structured data.
    """
    # Use provided parameters or fall back to global variables
    current_word_sets = word_sets_param if word_sets_param is not None else word_sets
    current_research_questions = research_questions_param if research_questions_param is not None else research_questions
    
    # Generate all combinations of word sets
    word_set_keys = list(current_word_sets.keys())
    word_set_values = [current_word_sets[key] for key in word_set_keys]
    word_combinations = list(product(*word_set_values))
    
    # Prepare data for the table
    table_data = []
    total_queries = len(word_combinations) * len(current_research_questions)
    
    print(f"Creating table with {len(word_combinations)} word combinations and {len(current_research_questions)} research questions...")
    print(f"Total API calls to make: {total_queries}")
    
    query_count = 0
    
    # Create rows for each combination of word sets and research questions
    for i, word_combo in enumerate(word_combinations):
        # Create a dictionary mapping word set keys to their values for this combination
        word_dict = dict(zip(word_set_keys, word_combo))
        print(f"\nProcessing combination {i+1}/{len(word_combinations)}: {word_dict}")
        
        for j, question_template in enumerate(current_research_questions):
            query_count += 1
            
            # Format the research question with the current word combination
            formatted_question = question_template.format(**word_dict)
            print(f"  Query {query_count}/{total_queries}: {formatted_question[:80]}...")
            
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
            
            # Create row data
            row_data = word_dict.copy()
            row_data.update({
                'research_question': formatted_question,
                'sonar_response': response_content,
                'sonar_response_json': response_json,
                'question_template': question_template
            })
            
            # Add structured response data if using a response model
            if response_model is not None:
                row_data.update({
                    'structured_data': structured_data.model_dump() if structured_data else None,
                    'parsing_success': parsing_success,
                    'parsing_error': parsing_error,
                    'retries_used': retries_used
                })
            
            table_data.append(row_data)
            
            # Add configurable delay to be respectful to the API
            await asyncio.sleep(delay_seconds)
    
    # Create DataFrame
    df = pd.DataFrame(table_data)
    
    # Reorder columns for better readability
    base_columns = word_set_keys
    other_columns = ['question_template', 'research_question', 'sonar_response', 'sonar_response_json']
    
    # Add structured response columns if using a response model
    if response_model is not None:
        other_columns.extend(['structured_data', 'parsing_success', 'parsing_error', 'retries_used'])
    
    df = df[base_columns + other_columns]
    
    return df


async def save_research_table(
    filename: str = "research_table",
    word_sets_param: Dict[str, List[str]] = None,
    research_questions_param: List[str] = None,
    delay_seconds: float = 0.5,
    response_model: Optional[Type[BaseModel]] = None
) -> pd.DataFrame:
    """
    Create and save the research table to CSV and JSON files.
    
    Args:
        filename: Base name for the output files (without extension)
        word_sets_param: Dictionary of word sets to use for combinations.
                        If None, uses the global word_sets variable.
        research_questions_param: List of research question templates.
                                If None, uses the global research_questions variable.
        delay_seconds: Delay between API calls in seconds (default: 0.5)
        response_model: Optional Pydantic model class to structure the response.
                       If provided, uses structured queries with JSON schema validation.
        
    Returns:
        pd.DataFrame: The created table
    """
    print("=" * 50)
    print("AutoRA Research Sprayer - Creating 2D Table")
    print("=" * 50)
    
    df = await spray(word_sets_param, research_questions_param, delay_seconds, response_model)
    
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
            print(f"{key}: {row[key]}")
        print(f"Question: {row['research_question']}")
        response_preview = row['sonar_response'][:150] + "..." if len(row['sonar_response']) > 150 else row['sonar_response']
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
        # Use spray with minimal parameters to create a 1-cell table
        df = await spray(
            word_sets_param=demo_word_sets,
            research_questions_param=demo_questions,
            delay_seconds=0.1  # Faster for demo
        )
        
        print(f"\n{'='*20} DEMO RESULTS {'='*20}")
        print(f"✓ Created table with {len(df)} row(s)")
        
        if len(df) > 0:
            row = df.iloc[0]
            print(f"\n📋 Query Details:")
            print(f"   Ministry/Domain: {row['ministry_domain']}")
            print(f"   Country: {row['country']}")
            print(f"   Question: {row['research_question']}")
            
            print(f"\n💬 API Response:")
            response_content = row['sonar_response']
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
        # Use spray with structured response model
        df = await spray(
            word_sets_param=demo_word_sets,
            research_questions_param=demo_questions,
            delay_seconds=0.1,  # Faster for demo
            response_model=SimpleYesNoResponse
        )
        
        print(f"\n{'='*20} STRUCTURED DEMO RESULTS {'='*20}")
        print(f"✓ Created table with {len(df)} row(s)")
        print(f"✓ Columns: {list(df.columns)}")
        
        if len(df) > 0:
            row = df.iloc[0]
            print(f"\n📋 Query Details:")
            print(f"   Ministry/Domain: {row['ministry_domain']}")
            print(f"   Country: {row['country']}")
            print(f"   Question: {row['research_question']}")
            print(f"   Parsing Success: {row['parsing_success']}")
            print(f"   Retries Used: {row['retries_used']}")
            
            if row['parsing_success']:
                structured = row['structured_data']
                print(f"\n🎯 Structured Response:")
                print(f"   Answer: {structured['answer']}")
                print(f"   Confidence: {structured['confidence']}")
                print(f"   Explanation: {structured['explanation']}")
                print(f"   Sources: {structured['sources']}")
            else:
                print(f"   Parsing Error: {row['parsing_error']}")
            
            print(f"\n💬 Raw API Response:")
            response_content = row['sonar_response']
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


def main():
    """Main entry point for the sprayer"""
    print("AutoRA Research Sprayer")
    print("======================")
    print("Choose an option:")
    print("1. Run demo single query (unstructured)")
    print("2. Run demo single query (structured with Pydantic)")
    print("3. Run full research spray")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        print("\nRunning demo single unstructured query...")
        asyncio.run(demo_single_query())
    elif choice == "2":
        print("\nRunning demo single structured query...")
        asyncio.run(demo_structured_query())
    elif choice == "3":
        print("\nRunning full research spray...")
        asyncio.run(save_research_table())
    else:
        print("Invalid choice. Running unstructured demo by default...")
        asyncio.run(demo_single_query())


if __name__ == "__main__":
    main()

