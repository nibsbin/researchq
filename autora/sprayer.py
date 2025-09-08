"""Sprays research questions at mass entities"""

import pandas as pd
import asyncio
from itertools import product
from typing import Dict, List, Any
import traceback
import json
from autora.llm import query_sonar

#======== Define word sets and research questions ========

word_sets = {
    "ministry_domain": ["Energy", "Finance", "Transport"],
    "country": ["USA", "Germany", "Azerbaijan"],
}

research_questions = [
    "Does the department/ministry of {ministry_domain} in {country} have cybersecurity responsibilities?",




    "Does the department/ministry of {ministry_domain} in {country} handle cyber terrorism within its scope of responsibilities?",



    "Is the department/ministry of {ministry_domain} in {country} internally or externally focused?"
]

#=========================================================

async def create_research_table() -> pd.DataFrame:
    """
    Create a 2D table by permuting word sets and research questions,
    querying Sonar API for each combination.
    
    Returns:
        pd.DataFrame: Table with columns for word set combinations, research questions, and API responses
    """
    # Generate all combinations of word sets
    word_set_keys = list(word_sets.keys())
    word_set_values = [word_sets[key] for key in word_set_keys]
    word_combinations = list(product(*word_set_values))
    
    # Prepare data for the table
    table_data = []
    total_queries = len(word_combinations) * len(research_questions)
    
    print(f"Creating table with {len(word_combinations)} word combinations and {len(research_questions)} research questions...")
    print(f"Total API calls to make: {total_queries}")
    
    query_count = 0
    
    # Create rows for each combination of word sets and research questions
    for i, word_combo in enumerate(word_combinations):
        # Create a dictionary mapping word set keys to their values for this combination
        word_dict = dict(zip(word_set_keys, word_combo))
        print(f"\nProcessing combination {i+1}/{len(word_combinations)}: {word_dict}")
        
        for j, question_template in enumerate(research_questions):
            query_count += 1
            
            # Format the research question with the current word combination
            formatted_question = question_template.format(**word_dict)
            print(f"  Query {query_count}/{total_queries}: {formatted_question[:80]}...")
            
            # Query Sonar API
            try:
                response = await query_sonar(formatted_question)
                # Save the entire JSON response
                response_json = response
                response_content = response.get('choices', [{}])[0].get('message', {}).get('content', 'No response')
                print(f"    ✓ Got response ({len(response_content)} chars)")
            except Exception as e:
                response_json = {"error": str(e), "traceback": traceback.format_exc()}
                response_content = f"Error: {str(e)}"
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
            
            table_data.append(row_data)
            
            # Add a small delay to be respectful to the API
            await asyncio.sleep(0.5)
    
    # Create DataFrame
    df = pd.DataFrame(table_data)
    
    # Reorder columns for better readability
    base_columns = word_set_keys
    other_columns = ['question_template', 'research_question', 'sonar_response', 'sonar_response_json']
    df = df[base_columns + other_columns]
    
    return df


async def save_research_table(filename: str = "research_table") -> pd.DataFrame:
    """
    Create and save the research table to CSV and JSON files.
    
    Args:
        filename: Base name for the output files (without extension)
        
    Returns:
        pd.DataFrame: The created table
    """
    print("=" * 50)
    print("AutoRA Research Sprayer - Creating 2D Table")
    print("=" * 50)
    
    df = await create_research_table()
    
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
    
    print(f"\n{'='*20} TABLE SUMMARY {'='*20}")
    print(f"Word set combinations: {len(df.groupby(list(word_sets.keys())))}")
    print(f"Research questions: {len(research_questions)}")
    print(f"Total rows: {len(df)}")
    
    print(f"\n{'='*20} SAMPLE DATA {'='*20}")
    # Set pandas display options for better formatting
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 80)
    print(df.head(3))
    
    print(f"\n{'='*20} COLUMN INFO {'='*20}")
    print("Columns in the table:")
    for i, col in enumerate(df.columns, 1):
        print(f"{i:2d}. {col}")
    
    return df


def run_research_spray():
    """
    Main function to run the research spray process.
    """
    return asyncio.run(save_research_table())


# Add a demo function for testing specific combinations
async def demo_single_query():
    """
    Demo function to test a single query.
    """
    test_question = "Does the department/ministry of Energy in USA have sophisticated cybersecurity responsibilities?"
    print(f"Testing single query: {test_question}")
    
    try:
        response = await query_sonar(test_question)
        content = response.get('choices', [{}])[0].get('message', {}).get('content', 'No response')
        print(f"\nResponse content: {content[:200]}...")
        print(f"\nFull JSON response:")
        print(json.dumps(response, indent=2))
        return response
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Full error: {traceback.format_exc()}")
        return None


def main():
    """Main entry point for the sprayer"""
    print("AutoRA Research Sprayer")
    print("======================")
    print("Choose an option:")
    print("1. Run demo single query")
    print("2. Run full research spray")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\nRunning demo single query...")
        asyncio.run(demo_single_query())
    elif choice == "2":
        print("\nRunning full research spray...")
        run_research_spray()
    else:
        print("Invalid choice. Running demo by default...")
        asyncio.run(demo_single_query())


if __name__ == "__main__":
    main()
    
