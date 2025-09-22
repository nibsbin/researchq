"""
Comprehensive examples demonstrating structured responses with AutoRA
"""

import asyncio
import pandas as pd
from researchq.sprayer import spray, save_research_table
from examples.pydantic_models import SimpleYesNoResponse, CybersecurityAssessment, DepartmentInfo


async def example_1_simple_yes_no():
    """Example 1: Simple yes/no questions with structured responses"""
    print("=" * 60)
    print("Example 1: Simple Yes/No Questions")
    print("=" * 60)
    
    word_sets = {
        "department": ["Energy", "Defense"],
        "country": ["USA", "UK"]
    }
    
    questions = [
        "Does the {department} department in {country} have cybersecurity responsibilities?"
    ]
    
    df = await spray(
        word_sets=word_sets,
        research_questions=questions,
        delay_seconds=1.0,
        response_model=SimpleYesNoResponse
    )
    
    print(f"\nResults: {len(df)} rows")
    for _, row in df.iterrows():
        print(f"\n{row['department']} in {row['country']}:")
        if row['parsing_success']:
            data = row['structured_data']
            print(f"  Answer: {data['answer']}")
            print(f"  Confidence: {data['confidence']}")
            print(f"  Explanation: {data['explanation'][:100]}...")
        else:
            print(f"  Error: {row['parsing_error']}")
    
    return df


async def example_2_cybersecurity_assessment():
    """Example 2: Detailed cybersecurity assessments"""
    print("\n" + "=" * 60)
    print("Example 2: Detailed Cybersecurity Assessments")
    print("=" * 60)
    
    word_sets = {
        "ministry": ["Transport"],
        "country": ["Germany"]
    }
    
    questions = [
        "Provide a comprehensive cybersecurity assessment for the {ministry} ministry in {country}, including their responsibilities, scope, and key functions."
    ]
    
    df = await spray(
        word_sets=word_sets,
        research_questions=questions,
        delay_seconds=1.0,
        response_model=CybersecurityAssessment
    )
    
    print(f"\nResults: {len(df)} rows")
    for _, row in df.iterrows():
        print(f"\n{row['ministry']} Ministry in {row['country']}:")
        if row['parsing_success']:
            data = row['structured_data']
            print(f"  Has Cybersecurity Responsibilities: {data['has_cybersecurity_responsibilities']}")
            print(f"  Confidence: {data['confidence']}")
            print(f"  Scope: {data['scope']}")
            print(f"  Key Responsibilities: {data['key_responsibilities']}")
            print(f"  Handles Cyber Terrorism: {data['handles_cyber_terrorism']}")
            if data['additional_notes']:
                print(f"  Notes: {data['additional_notes'][:100]}...")
        else:
            print(f"  Error: {row['parsing_error']}")
    
    return df


async def example_3_mixed_questions():
    """Example 3: Multiple different questions with the same structure"""
    print("\n" + "=" * 60)
    print("Example 3: Multiple Questions, Same Structure")
    print("=" * 60)
    
    word_sets = {
        "sector": ["Energy"],
        "country": ["France"]
    }
    
    questions = [
        "Does the {sector} sector in {country} have dedicated cybersecurity regulations?",
        "Is the {sector} sector in {country} considered critical infrastructure?",
        "Does {country} have a national cybersecurity strategy that covers the {sector} sector?"
    ]
    
    df = await spray(
        word_sets=word_sets,
        research_questions=questions,
        delay_seconds=1.0,
        response_model=SimpleYesNoResponse
    )
    
    print(f"\nResults: {len(df)} rows")
    for _, row in df.iterrows():
        print(f"\nQuestion: {row['research_question']}")
        if row['parsing_success']:
            data = row['structured_data']
            print(f"  Answer: {data['answer']}")
            print(f"  Confidence: {data['confidence']}")
            print(f"  Sources: {len(data['sources'])} cited")
        else:
            print(f"  Error: {row['parsing_error']}")
    
    return df


async def example_4_save_structured_table():
    """Example 4: Save structured results to files"""
    print("\n" + "=" * 60)
    print("Example 4: Save Structured Table to Files")
    print("=" * 60)
    
    word_sets = {
        "ministry": ["Energy", "Transport"],
        "country": ["USA", "Germany"]
    }
    
    questions = [
        "Does the {ministry} ministry/department in {country} have cybersecurity responsibilities?"
    ]
    
    # Save structured results to files
    df = await save_research_table(
        filename="structured_cybersecurity_assessment",
        word_sets_param=word_sets,
        research_questions_param=questions,
        delay_seconds=1.0,
        response_model=SimpleYesNoResponse
    )
    
    print(f"\nFiles saved with structured data!")
    print(f"Structured parsing success rate: {df['parsing_success'].mean():.1%}")
    
    return df


async def example_5_compare_structured_vs_unstructured():
    """Example 5: Compare structured vs unstructured responses"""
    print("\n" + "=" * 60)
    print("Example 5: Structured vs Unstructured Comparison")
    print("=" * 60)
    
    word_sets = {
        "country": ["Canada"]
    }
    
    questions = [
        "Does {country} have a national cybersecurity strategy?"
    ]
    
    # Unstructured query
    print("Running unstructured query...")
    df_unstructured = await spray(
        word_sets=word_sets,
        research_questions=questions,
        delay_seconds=1.0
        # No response_model = unstructured
    )
    
    # Structured query
    print("Running structured query...")
    df_structured = await spray(
        word_sets=word_sets,
        research_questions=questions,
        delay_seconds=1.0,
        response_model=SimpleYesNoResponse
    )
    
    print("\n--- Unstructured Response ---")
    unstructured_response = df_unstructured.iloc[0]['sonar_response']
    print(f"Length: {len(unstructured_response)} chars")
    print(f"Preview: {unstructured_response[:200]}...")
    
    print("\n--- Structured Response ---")
    if df_structured.iloc[0]['parsing_success']:
        structured_data = df_structured.iloc[0]['structured_data']
        print(f"Answer: {structured_data['answer']}")
        print(f"Confidence: {structured_data['confidence']}")
        print(f"Explanation: {structured_data['explanation'][:200]}...")
        print(f"Sources: {structured_data['sources']}")
    else:
        print(f"Parsing failed: {df_structured.iloc[0]['parsing_error']}")
    
    return df_unstructured, df_structured


async def main():
    """Run all examples"""
    print("AutoRA Structured Response Examples")
    print("=" * 60)
    
    try:
        # Run examples sequentially
        await example_1_simple_yes_no()
        await example_2_cybersecurity_assessment()
        await example_3_mixed_questions()
        await example_4_save_structured_table()
        await example_5_compare_structured_vs_unstructured()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())