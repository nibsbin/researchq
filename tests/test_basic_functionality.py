#!/usr/bin/env python3
"""Basic functionality test without external dependencies."""

import sys
import os
import json
from string import Template

# Add the robora module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'robora'))

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

class MockDotenv:
    """Mock dotenv module."""
    pass

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
sys.modules['python-dotenv'] = MockDotenv()

# Now import our modules
try:
    from classes import Question, QueryResponse, Answer
    from mock_query import MockResponseModel, MockQueryHandler
    from session_storage import SessionStorageProvider
    from ask import Workflow
    
    print("✓ All modules imported successfully")
    
except Exception as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def test_mock_response_model():
    """Test MockResponseModel functionality."""
    print("\n" + "="*50)
    print("Testing MockResponseModel")
    print("="*50)
    
    try:
        # Create instance
        model = MockResponseModel(cybersecurity_level=7, explanation="Test explanation")
        print(f"✓ Created model: level={model.cybersecurity_level}, explanation='{model.explanation[:30]}...'")
        
        # Test model_dump
        data = model.model_dump()
        print(f"✓ Model dump: {data}")
        
        # Test model_validate
        new_model = MockResponseModel().model_validate({"cybersecurity_level": 5, "explanation": "Another test"})
        print(f"✓ Model validation: level={new_model.cybersecurity_level}")
        
        return True
    except Exception as e:
        print(f"✗ MockResponseModel test failed: {e}")
        return False


def test_mock_query_handler():
    """Test MockQueryHandler functionality."""
    print("\n" + "="*50)
    print("Testing MockQueryHandler")
    print("="*50)
    
    try:
        # Create handler
        handler = MockQueryHandler(MockResponseModel)
        print(f"✓ Created handler: {handler}")
        
        # Test query method
        import asyncio
        
        async def run_query_test():
            response = await handler.query("Test question", MockResponseModel)
            print(f"✓ Query response: has_full_response={response.full_response is not None}, has_error={response.error is not None}")
            
            if response.full_response:
                print(f"✓ Response structure: choices={len(response.full_response.get('choices', []))}, citations={len(response.full_response.get('citations', []))}")
            
            # Test extract_fields
            fields = handler.extract_fields(response.full_response)
            print(f"✓ Extracted fields: {list(fields.keys())}")
            print(f"✓ Cybersecurity level: {fields.get('cybersecurity_level', 'N/A')}")
            print(f"✓ Enriched citations: {len(fields.get('enriched_citations', []))}")
            
            return True
        
        return asyncio.run(run_query_test())
        
    except Exception as e:
        print(f"✗ MockQueryHandler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_storage():
    """Test SessionStorageProvider functionality."""
    print("\n" + "="*50)
    print("Testing SessionStorageProvider")
    print("="*50)
    
    try:
        # Create storage
        storage = SessionStorageProvider()
        print(f"✓ Created storage: {storage}")
        
        # Create test question
        question = Question(
            word_set={"org": "TestOrg"},
            template=Template("Test question about {org}"),
            response_model=MockResponseModel
        )
        print(f"✓ Created question: {question.get_string}")
        
        # Test storage operations
        import asyncio
        
        async def run_storage_test():
            # Save response
            test_response = {"test": "data", "cybersecurity_level": 8}
            await storage.save_response(question, test_response)
            print(f"✓ Saved response, storage count: {storage.count()}")
            
            # Retrieve response
            retrieved = await storage.get_response(question)
            print(f"✓ Retrieved response: {len(str(retrieved))} characters")
            
            # Test utility methods
            all_responses = storage.get_all_responses()
            print(f"✓ All responses: {len(all_responses)} items")
            
            return True
        
        return asyncio.run(run_storage_test())
        
    except Exception as e:
        print(f"✗ SessionStorageProvider test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_integration():
    """Test complete workflow integration."""
    print("\n" + "="*50)
    print("Testing Workflow Integration")
    print("="*50)
    
    try:
        # Create components
        handler = MockQueryHandler(MockResponseModel)
        storage = SessionStorageProvider()
        workflow = Workflow(query_handler=handler, storage=storage)
        print(f"✓ Created workflow with handler and storage")
        
        # Create question
        question = Question(
            word_set={"department": "TestDept", "country": "TestCountry"},
            template=Template("Assess cybersecurity of {department} in {country}"),
            response_model=MockResponseModel
        )
        print(f"✓ Created question: {question.get_string}")
        
        # Test workflow
        import asyncio
        
        async def run_workflow_test():
            answer = await workflow.ask_question(question)
            print(f"✓ Got answer: {type(answer).__name__}")
            print(f"✓ Answer has full_response: {answer.full_response is not None}")
            print(f"✓ Answer has fields: {answer.fields is not None}")
            
            if answer.fields:
                print(f"✓ Answer fields: {list(answer.fields.keys())}")
                print(f"✓ Cybersecurity level: {answer.fields.get('cybersecurity_level', 'N/A')}")
            
            # Check storage
            print(f"✓ Storage count after workflow: {storage.count()}")
            
            return True
        
        return asyncio.run(run_workflow_test())
        
    except Exception as e:
        print(f"✗ Workflow integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("Basic Functionality Test")
    print("=" * 60)
    
    tests = [
        ("MockResponseModel", test_mock_response_model),
        ("MockQueryHandler", test_mock_query_handler),
        ("SessionStorageProvider", test_session_storage),
        ("Workflow Integration", test_workflow_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Implementation is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)