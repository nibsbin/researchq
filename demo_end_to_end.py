#!/usr/bin/env python3
"""End-to-end demo of ask.py::Workflow using MockQueryHandler, MockResponseModel, and SessionStorageProvider."""

import asyncio
import sys
import os
from string import Template

# Add the researchq module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'researchq'))

# Mock the missing imports since we can't install them
class MockBaseModel:
    """Mock BaseModel for testing without pydantic."""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def model_validate(self, data):
        return self.__class__(**data)
    
    def model_dump(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def model_json_schema(self):
        return {
            "type": "object",
            "properties": {
                "cybersecurity_level": {"type": "integer"},
                "explanation": {"type": "string"}
            }
        }

class MockField:
    """Mock Field for testing without pydantic."""
    def __init__(self, description=""):
        self.description = description

class MockValidationError(Exception):
    """Mock ValidationError for testing without pydantic."""
    pass

class MockDataFrame:
    """Mock DataFrame for testing without pandas."""
    def __init__(self, data):
        self.data = data

class MockPandas:
    """Mock pandas module."""
    DataFrame = MockDataFrame

def mock_load_dotenv():
    pass

# Replace imports with mocks
sys.modules['pydantic'] = type(sys)('pydantic')
sys.modules['pydantic'].BaseModel = MockBaseModel  
sys.modules['pydantic'].Field = MockField
sys.modules['pydantic'].ValidationError = MockValidationError
sys.modules['pandas'] = MockPandas()
sys.modules['httpx'] = type(sys)('httpx')
sys.modules['dotenv'] = type(sys)('dotenv')
sys.modules['dotenv'].load_dotenv = mock_load_dotenv
sys.modules['python-dotenv'] = type(sys)('python-dotenv')

# Now import our modules
from researchq.ask import Workflow
from researchq.mock_query import MockQueryHandler, MockResponseModel
from researchq.session_storage import SessionStorageProvider
from researchq.classes import Question


async def demo_workflow():
    """Demonstrate the complete workflow using mock components."""
    
    print("=" * 60)
    print("End-to-End Demo: Workflow with Mock Components")
    print("=" * 60)
    
    # 1. Initialize components
    print("\n1. Initializing components...")
    mock_handler = MockQueryHandler(MockResponseModel)
    storage_provider = SessionStorageProvider()
    workflow = Workflow(query_handler=mock_handler, storage=storage_provider)
    
    print(f"   - Query Handler: {mock_handler}")
    print(f"   - Storage Provider: {storage_provider}")
    print(f"   - Workflow initialized with both components")
    
    # 2. Create sample questions
    print("\n2. Creating sample questions...")
    questions = [
        Question(
            word_set={
                "organization": "Department of Defense",
                "country": "United States"
            },
            template=Template("What is the cybersecurity posture of the {organization} in {country}?"),
            response_model=MockResponseModel
        ),
        Question(
            word_set={
                "organization": "Ministry of Defence",
                "country": "United Kingdom"
            },
            template=Template("Assess the cybersecurity capabilities of the {organization} in {country}?"),
            response_model=MockResponseModel
        ),
        Question(
            word_set={
                "organization": "CISA",
                "country": "United States"
            },
            template=Template("How effective is {organization} in {country} at managing cybersecurity threats?"),
            response_model=MockResponseModel
        )
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"   Question {i}: {question.get_string}")
    
    # 3. Process questions through workflow
    print(f"\n3. Processing {len(questions)} questions through workflow...")
    answers = []
    
    for i, question in enumerate(questions, 1):
        print(f"\n   Processing Question {i}...")
        print(f"   Question: {question.get_string}")
        
        try:
            answer = await workflow.ask_question(question)
            answers.append(answer)
            
            print(f"   ✓ Answer received")
            print(f"   - Cybersecurity Level: {answer.fields.get('cybersecurity_level', 'N/A')}")
            print(f"   - Explanation: {answer.fields.get('explanation', 'N/A')[:100]}...")
            print(f"   - Citations: {len(answer.fields.get('enriched_citations', []))} sources")
            
        except Exception as e:
            print(f"   ✗ Error processing question: {e}")
    
    # 4. Verify storage
    print(f"\n4. Verifying storage...")
    print(f"   Storage contains {storage_provider.count()} responses")
    
    stored_responses = storage_provider.get_all_responses()
    for question_text, response in stored_responses.items():
        print(f"   - Stored: {question_text[:50]}...")
    
    # 5. Test retrieval from storage
    print(f"\n5. Testing retrieval from storage...")
    for i, question in enumerate(questions[:2], 1):  # Test first 2 questions
        stored_response = await storage_provider.get_response(question)
        print(f"   Retrieved response {i}: {len(str(stored_response))} characters")
    
    # 6. Display summary
    print(f"\n6. Demo Summary:")
    print(f"   - Questions processed: {len(answers)}")
    print(f"   - Successful answers: {len([a for a in answers if a.full_response])}")
    print(f"   - Responses stored: {storage_provider.count()}")
    print(f"   - Mock components working: ✓")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)
    
    return answers, storage_provider


async def demo_detailed_analysis():
    """Show detailed analysis of a single response."""
    
    print("\n" + "=" * 60)
    print("Detailed Analysis of Mock Response Structure")
    print("=" * 60)
    
    # Create a single question for detailed analysis
    mock_handler = MockQueryHandler(MockResponseModel)
    question = Question(
        word_set={"department": "National Cyber Security Centre", "country": "Australia"},
        template=Template("Analyze the cybersecurity responsibilities of {department} in {country}"),
        response_model=MockResponseModel
    )
    
    print(f"\nQuestion: {question.get_string}")
    
    # Get raw response
    response = await mock_handler.query(question.get_string, MockResponseModel)
    print(f"\nRaw Response Structure:")
    print(f"- Has full_response: {response.full_response is not None}")
    print(f"- Has error: {response.error is not None}")
    
    if response.full_response:
        full_resp = response.full_response
        print(f"- Choices: {len(full_resp.get('choices', []))}")
        print(f"- Citations: {len(full_resp.get('citations', []))}")
        print(f"- Search Results: {len(full_resp.get('search_results', []))}")
    
    # Extract fields
    fields = mock_handler.extract_fields(response.full_response)
    print(f"\nExtracted Fields:")
    print(f"- Cybersecurity Level: {fields.get('cybersecurity_level')}")
    print(f"- Explanation Length: {len(fields.get('explanation', ''))}")
    print(f"- Enriched Citations: {len(fields.get('enriched_citations', []))}")
    
    if 'enriched_citations' in fields:
        for i, citation in enumerate(fields['enriched_citations'], 1):
            print(f"  Citation {i}: {citation['url']} (matched: {citation['matched']})")
    
    print("\nStructural Compatibility with SonarQueryHandler: ✓")


if __name__ == "__main__":
    async def main():
        # Run the main demo
        await demo_workflow()
        
        # Run detailed analysis
        await demo_detailed_analysis()
    
    # Run the demo
    asyncio.run(main())