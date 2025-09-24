# SQLite Storage Provider

The `SQLiteStorageProvider` provides persistent storage for question/response pairs using an SQLite database. This allows research data to be stored and retrieved across different sessions.

## Basic Usage

```python
import asyncio
from researchq import Question, QueryResponse, SQLiteStorageProvider

async def example():
    # Initialize with default database name
    storage = SQLiteStorageProvider()  # Creates "researchq.db"
    
    # Or specify a custom database path
    storage = SQLiteStorageProvider("my_research.db")
    
    # Create a question
    question = Question(
        word_set={"org": "Department of Defense", "country": "USA"},
        template="What is the cybersecurity posture of {org} in {country}?",
        response_model=MyResponseModel
    )
    
    # Create a response
    response = QueryResponse(
        full_response={"cybersecurity_level": 8, "assessment": "High"},
        error=None
    )
    
    # Save the response
    await storage.save_response(question, response)
    
    # Retrieve the response later
    retrieved = await storage.get_response(question)
    print(retrieved.full_response)  # {"cybersecurity_level": 8, "assessment": "High"}

asyncio.run(example())
```

## Integration with Workflow

The SQLite storage provider can be used directly with the `Workflow` class for automatic caching:

```python
import asyncio
from researchq import Workflow, SQLiteStorageProvider
from researchq.mock_query import MockQueryHandler, MockResponseModel

async def workflow_example():
    # Set up components
    query_handler = MockQueryHandler(MockResponseModel)
    storage = SQLiteStorageProvider("research_cache.db")
    workflow = Workflow(query_handler=query_handler, storage=storage)
    
    # Create question
    question = Question(
        word_set={"org": "NASA", "country": "USA"},
        template="Assess {org} cybersecurity in {country}",
        response_model=MockResponseModel
    )
    
    # First request - will query and cache
    answer1 = await workflow.ask(question)
    print("First request:", answer1.fields)
    
    # Second request - will use cached result
    answer2 = await workflow.ask(question)
    print("Second request (cached):", answer2.fields)
    
    # Results should be identical
    assert answer1.full_response == answer2.full_response

asyncio.run(workflow_example())
```

## Features

### Persistence
Data persists across different instances and sessions:

```python
# Save data with one instance
storage1 = SQLiteStorageProvider("data.db")
await storage1.save_response(question, response)

# Access same data with new instance
storage2 = SQLiteStorageProvider("data.db")
retrieved = await storage2.get_response(question)  # Works!
```

### Automatic Database Management
- Database and tables are created automatically on first use
- No need to manually initialize schema
- Uses efficient SQLite indexes for fast lookups

### Thread-Safe Async Operations
All database operations are run in a thread pool to avoid blocking the event loop:

```python
# These operations won't block other async code
await storage.save_response(question1, response1)
await storage.save_response(question2, response2)
await storage.save_response(question3, response3)
```

## API Reference

### Constructor
```python
SQLiteStorageProvider(db_path: str = "researchq.db")
```

**Parameters:**
- `db_path`: Path to SQLite database file. Defaults to "researchq.db"

### Methods

#### `save_response(question, response)`
Save a question/response pair to the database.

```python
await storage.save_response(question, response)
```

- Uses `INSERT OR REPLACE` to handle duplicate questions
- Serializes objects as JSON for storage

#### `get_response(question)`
Retrieve a response for a given question.

```python
response = await storage.get_response(question)
if response:
    print("Found cached response")
else:
    print("No cached response found")
```

Returns `None` if no response is found.

#### `delete_response(question)`
Delete a stored response.

```python
await storage.delete_response(question)
```

#### `get_stored_questions()`
Iterate over all stored questions.

```python
async for question in storage.get_stored_questions():
    print(f"Stored: {question.value}")
```

#### `clear()`
Delete all stored responses.

```python
storage.clear()  # Synchronous operation
```

#### `count()`
Get the number of stored responses.

```python
count = storage.count()  # Synchronous operation
print(f"Database contains {count} responses")
```

## Database Schema

The SQLite database uses a simple schema:

```sql
CREATE TABLE question_responses (
    question_hash INTEGER PRIMARY KEY,
    question_json TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- `question_hash`: Hash of the question (from `Question.__hash__()`)
- `question_json`: Serialized Question object
- `response_json`: Serialized QueryResponse object
- `created_at`: Timestamp when the record was created

## Question Hashing

Questions are identified by their hash, which is computed from:
- Template string
- Word set (as frozen set of key-value pairs)

This means questions with identical templates and word sets will be treated as the same question, regardless of the `response_model`.

## Error Handling

The SQLite provider handles common scenarios gracefully:

- **Database creation**: Automatically creates database and tables if they don't exist
- **Concurrent access**: SQLite handles concurrent reads/writes automatically
- **Missing responses**: Returns `None` instead of raising exceptions
- **Serialization errors**: Will raise appropriate exceptions if objects can't be serialized

## Performance Considerations

- **Indexing**: Uses the question hash as a primary key for fast lookups
- **Async operations**: Database operations run in thread pool to avoid blocking
- **Connection management**: Uses connection-per-operation for thread safety
- **JSON serialization**: Efficient for typical question/response data sizes

## Comparison with SessionStorageProvider

| Feature | SessionStorageProvider | SQLiteStorageProvider |
|---------|----------------------|----------------------|
| Persistence | In-memory only | Persistent to disk |
| Performance | Fastest | Fast (disk I/O) |
| Memory usage | High for large datasets | Low |
| Concurrency | Single process | Multi-process safe |
| Setup | None required | Automatic |

Choose `SessionStorageProvider` for temporary caching and `SQLiteStorageProvider` for persistent research data storage.