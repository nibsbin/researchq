"""Test script demonstrating structured responses with Pydantic models"""

import asyncio
import pytest
from researchq.sprayer import spray
from examples.pydantic_models import CybersecurityAssessment, SimpleYesNoResponse


@pytest.mark.asyncio
async def test_structured_spray():
    """Test the spray function with structured responses"""
    
    # Test with simple yes/no questions
    print("=" * 60)
    print("Testing spray() with SimpleYesNoResponse model")
    print("=" * 60)
    
    simple_word_sets = {
        "ministry_domain": ["Energy"],
        "country": ["USA"]
    }
    
    simple_questions = [
        "Does the department/ministry of {ministry_domain} in {country} have cybersecurity responsibilities?"
    ]
    
    try:
        df_simple = await spray(
            word_sets=simple_word_sets,
            research_questions=simple_questions,
            delay_between_batches=1.0,  # Slower for testing
            response_model=SimpleYesNoResponse
        )
        
        print(f"\n✓ Created structured table with {len(df_simple)} rows")
        print(f"✓ Columns: {list(df_simple.columns)}")
        
        if len(df_simple) > 0:
            row = df_simple.iloc[0]
            print(f"\n📋 Sample Row Data:")
            print(f"   Ministry: {row['ministry_domain']}")
            print(f"   Country: {row['country']}")
            print(f"   Question: {row['research_question']}")
            print(f"   Parsing Success: {row['parsing_success']}")
            
            if row['parsing_success']:
                structured = row['structured_data']
                print(f"\n🎯 Structured Response:")
                print(f"   Answer: {structured['answer']}")
                print(f"   Confidence: {structured['confidence']}")
                print(f"   Explanation: {structured['explanation']}")
                print(f"   Sources: {structured['sources']}")
            else:
                print(f"   Parsing Error: {row['parsing_error']}")
            
            print(f"\n📝 Raw Response Preview: {row['sonar_response'][:200]}...")
    
    except Exception as e:
        print(f"Error in simple test: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with more complex cybersecurity assessment
    print("\n" + "=" * 60)
    print("Testing spray() with CybersecurityAssessment model")
    print("=" * 60)
    
    complex_word_sets = {
        "ministry_domain": ["Transport"],
        "country": ["Azerbaijan"]
    }
    
    complex_questions = [
        "Provide a comprehensive cybersecurity assessment for the department/ministry of {ministry_domain} in {country}"
    ]
    
    try:
        df_complex = await spray(
            word_sets=complex_word_sets,
            research_questions=complex_questions,
            delay_between_batches=1.0,
            response_model=CybersecurityAssessment
        )
        
        print(f"\n✓ Created complex structured table with {len(df_complex)} rows")
        
        if len(df_complex) > 0:
            row = df_complex.iloc[0]
            print(f"\n📋 Sample Row Data:")
            print(f"   Ministry: {row['ministry_domain']}")
            print(f"   Country: {row['country']}")
            print(f"   Parsing Success: {row['parsing_success']}")
            print(f"   Retries Used: {row['retries_used']}")
            
            if row['parsing_success']:
                structured = row['structured_data']
                print(f"\n🎯 Structured Cybersecurity Assessment:")
                print(f"   Has Responsibilities: {structured['has_cybersecurity_responsibilities']}")
                print(f"   Confidence: {structured['confidence']}")
                print(f"   Scope: {structured['scope']}")
                print(f"   Key Responsibilities: {structured['key_responsibilities']}")
                print(f"   Handles Cyber Terrorism: {structured['handles_cyber_terrorism']}")
                print(f"   Additional Notes: {structured['additional_notes']}")
            else:
                print(f"   Parsing Error: {row['parsing_error']}")
    
    except Exception as e:
        print(f"Error in complex test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_structured_spray())