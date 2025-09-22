"""Interfaces with LLMs"""

from typing import Any, Dict, List, Optional, Type, Union
import httpx
import json
import asyncio
from pydantic import BaseModel, ValidationError

from researchq.CONFIG import PERPLEXITY_API_KEY

from collections import namedtuple

class QueryResponse:
    raw_response: Optional[Dict[str, Any]] = None
    structured_data: Optional[BaseModel] = None

    def __init__(self):
        self.raw_response = None
        self.structured_data = None
    def __init__(self, raw_response=str, structured_output=Dict[str, Any]):
        self.raw_response = raw_response
        self.structured_output = structured_output

async def query_sonar_structured(
    prompt: str, 
    response_model: Type[BaseModel], 
    model: str = "sonar",
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Query the Perplexity Sonar API with native structured output support using response_format.
    
    Args:
        prompt: The user prompt to send
        response_model: Pydantic model class to structure the response
        model: The model to use (default: "sonar")
    
    Returns:
        dict: Contains 'raw_response' (original API response), 'structured_data' (parsed model),
              'parsing_success' (bool), and 'parsing_error' (if any)
    """
    # Generate JSON schema from Pydantic model with descriptions
    schema = response_model.model_json_schema()
    
    # Enhance the prompt to improve schema adherence and mention field descriptions
    enhanced_prompt = f"""
{prompt}

Please provide comprehensive information and format your response according to the specified JSON schema structure. Pay attention to the field descriptions in the schema to understand what information is expected for each field.

JSON Schema:
{json.dumps(schema, indent=2)}
"""
    
    result = QueryResponse()
    for attempt in range(max_retries):
        try:
            # Use Perplexity's native structured output with response_format
            async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for first schema use
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        'model': model,
                        'messages': [
                            {
                                'role': 'user',
                                'content': enhanced_prompt
                            }
                        ],
                        'response_format': {
                            'type': 'json_schema',
                            'json_schema': {
                                'schema': schema
                            }
                        }
                    }
                )
                
                # Check if the response is successful
                response.raise_for_status()
                
                # Check if response has content before trying to parse JSON
                if not response.content:
                    raise ValueError("Empty response from API")
                
                raw_response = response.json()
                result['raw_response'] = raw_response
                
                # Extract the structured content from the response
                content = raw_response.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                if not content:
                    raise ValueError("Empty content in API response")
                
                # Handle reasoning models that include <think> tags
                if content.startswith('<think>') and '</think>' in content:
                    # Extract JSON after the closing </think> tag
                    json_start = content.find('</think>') + 8
                    json_content = content[json_start:].strip()
                else:
                    json_content = content.strip()
                
                # Parse the JSON content directly (should be valid JSON from structured output)
                try:
                    json_data = json.loads(json_content)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse structured JSON response: {str(e)}")
                
                # Validate against the Pydantic model
                structured_data = response_model.model_validate(json_data)
                break
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            if e.response.status_code == 400:
                # Bad request likely means schema issue, don't retry
                break
            elif attempt == max_retries - 1:
                break
            else:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            if attempt == max_retries - 1:
                break
            else:
                await asyncio.sleep(1)  # Brief delay before retry
                
        except Exception as e:
            result['parsing_error'] = f"Unexpected error: {str(e)}"
            break
    
    return result