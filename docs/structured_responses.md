# Structured Responses with Pydantic Models

AutoRA now supports structured responses using Pydantic models through Perplexity's native JSON schema structured outputs feature. This provides reliable, validated responses that conform to your specified data structure.

## How It Works

The `spray()` function now accepts an optional `response_model` parameter that takes a Pydantic BaseModel class. When provided, AutoRA uses Perplexity's native `response_format` parameter to enforce the JSON schema structure, eliminating the need for manual text parsing.

## Basic Usage

```python
import asyncio
from autora.sprayer import spray
from examples.pydantic_models import SimpleYesNoResponse

async def example():
    # Define your word sets and questions
    word_sets = {
        "ministry_domain": ["Energy", "Transport"],
        "country": ["USA", "Azerbaijan"]
    }
    
    questions = [
        "Does the department/ministry of {ministry_domain} in {country} have cybersecurity responsibilities?"
    ]
    
    # Run with structured responses
    df = await spray(
        word_sets_param=word_sets,
        research_questions_param=questions,
        delay_seconds=1.0,
        response_model=SimpleYesNoResponse  # Add this for structured responses
    )
    
    # Access structured data
    for _, row in df.iterrows():
        if row['parsing_success']:
            structured = row['structured_data']
            print(f"Answer: {structured['answer']}")
            print(f"Confidence: {structured['confidence']}")
            print(f"Explanation: {structured['explanation']}")
        else:
            print(f"Parsing failed: {row['parsing_error']}")

asyncio.run(example())
```

## Available Pydantic Models

The `examples/pydantic_models.py` file contains several pre-built models:

### SimpleYesNoResponse
Simple yes/no answers with explanation:
- `answer`: bool
- `confidence`: ConfidenceLevel (high/medium/low)
- `explanation`: str
- `sources`: List[str]

### CybersecurityAssessment
Comprehensive cybersecurity assessments:
- `has_cybersecurity_responsibilities`: bool
- `confidence`: ConfidenceLevel
- `scope`: CybersecurityScope (internal/external/both/none/unclear)
- `key_responsibilities`: List[str]
- `handles_cyber_terrorism`: Optional[bool]
- `focus_orientation`: Optional[str]
- `evidence_sources`: List[str]
- `additional_notes`: Optional[str]

### DepartmentInfo
Detailed department information including cybersecurity assessment:
- `department_name`: str
- `country`: str
- `primary_mandate`: str
- `key_functions`: List[str]
- `cybersecurity_involvement`: CybersecurityAssessment
- `website_url`: Optional[str]
- `last_updated`: Optional[str]

## Creating Custom Models

You can create your own Pydantic models:

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class MyCustomResponse(BaseModel):
    title: str = Field(description="The main title or heading")
    summary: str = Field(description="Brief summary of key points")
    key_points: List[str] = Field(description="List of important points")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence from 0 to 1")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")

# Use it with spray()
df = await spray(
    word_sets_param=my_word_sets,
    research_questions_param=my_questions,
    response_model=MyCustomResponse
)
```

## Key Benefits

1. **Reliability**: Uses Perplexity's native structured output feature - no manual JSON parsing
2. **Validation**: Automatic validation using Pydantic ensures data integrity
3. **Type Safety**: Full type hints and IDE support
4. **Consistent Format**: Guaranteed consistent response structure across all queries
5. **Error Handling**: Clear error reporting when schema validation fails

## DataFrame Structure

When using structured responses, the resulting DataFrame includes additional columns:

- `structured_data`: The parsed Pydantic model as a dictionary
- `parsing_success`: Boolean indicating if parsing succeeded
- `parsing_error`: Error message if parsing failed
- `retries_used`: Number of retries used for the API call

## Testing

Run the demo to see structured responses in action:

```bash
cd /path/to/AutoRA
uv run python -m autora.sprayer
# Choose option 2 for structured demo
```

Or run the test script:

```bash
uv run python tests/test_structured_spray.py
```

## Important Notes

- The first request with a new JSON schema may take 10-30 seconds as Perplexity prepares the schema
- Subsequent requests with the same schema are much faster
- Complex recursive schemas are not supported by Perplexity
- Always include helpful field descriptions in your Pydantic models to improve response quality