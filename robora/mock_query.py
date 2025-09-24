"""Mock implementations for testing and demonstration purposes."""

from typing import Any, Dict, Type
from pydantic import BaseModel, Field
from robora.classes import QueryHandler, QueryResponse


class MockResponseModel(BaseModel):
    """Mock response model for demonstration with relevance and explanation fields."""
    
    relevance: int = Field(
        description="Relevance score of 0 (none), 1 (low), 2 (medium), 3 (high)", ge=0, le=3
    )
    
    explanation: str = Field(
        description="Detailed explanation of the cybersecurity assessment and reasoning"
    )


class MockQueryHandler(QueryHandler):
    """Mock implementation of QueryHandler that returns predefined responses."""
    
    def __init__(self, response_model: Type[BaseModel] = None):
        self.response_model = response_model or MockResponseModel
    
    async def query(self, prompt: str) -> QueryResponse:
        """Return a mock response that is structurally similar to SonarQueryHandler."""
        
        # Create mock response that mimics the structure of Perplexity API response
        mock_full_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"relevance": 7, "explanation": "This is a mock response demonstrating a moderate cybersecurity level with detailed explanation about security practices and recommendations."}'
                    },
                    "finish_reason": "stop"
                }
            ],
            "citations": [
                "https://mock-security-source1.com",
                "https://mock-security-source2.com"
            ],
            "search_results": [
                {
                    "url": "https://mock-security-source1.com",
                    "title": "Mock Cybersecurity Guidelines",
                    "snippet": "Essential cybersecurity practices and recommendations...",
                    "date": "2024-01-15",
                    "last_updated": "2024-01-15"
                },
                {
                    "url": "https://mock-security-source2.com", 
                    "title": "Security Assessment Framework",
                    "snippet": "Framework for evaluating cybersecurity posture...",
                    "date": "2024-01-10",
                    "last_updated": "2024-01-12"
                }
            ],
            "model": "mock-model",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        return QueryResponse(full_response=mock_full_response, error=None)
    
    def extract_fields(self, full_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and enrich fields from the mock response, similar to SonarQueryHandler."""
        
        if not full_response:
            return {}
        
        # Extract content from mock response structure
        content_raw = full_response.get('choices', [{}])[0].get('message', {}).get('content', '')
        if not content_raw:
            return {}
        
        try:
            import json
            content_dict = json.loads(content_raw)
            content = self.response_model.model_validate(content_dict)
        except (json.JSONDecodeError, Exception):
            # Fallback to default values if parsing fails
            content = self.response_model(
                relevance=2,
                explanation="Default mock response - unable to parse structured content"
            )
            content_dict = content.model_dump()
        
        # Enrich with citations similar to SonarQueryHandler
        enriched_citations = []
        citations = full_response.get('citations', [])
        search_results = full_response.get('search_results', [])
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
        
        content_dict['enriched_citations'] = enriched_citations
        return content_dict
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(response_model={self.response_model.__name__})"
        )
    
    def __str__(self) -> str:
        return f"MockQueryHandler with response model {self.response_model.__name__}"