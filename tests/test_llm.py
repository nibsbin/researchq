from researchq.llm import query_sonar_structured
from pydantic import BaseModel, Field

def test_query():
    class ResponseModel(BaseModel):
        answer: str

    prompt = "What is the capital of France?"
    result = query_sonar_structured(prompt, ResponseModel)
    assert 'raw_response' in result
    assert 'structured_data' in result
    assert isinstance(result['structured_data'], ResponseModel)
    assert result['structured_data'].answer.lower() == "paris"