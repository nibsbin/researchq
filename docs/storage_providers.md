# Storage Providers

ResearchQ supports multiple storage providers for caching question/response pairs. This allows you to choose the storage solution that best fits your needs.

## Available Storage Providers

### SessionStorageProvider
- **Type**: In-memory storage
- **Persistence**: Data lost when process ends
- **Use case**: Temporary caching during a single session
- **Performance**: Fastest
- **Location**: `researchq.session_storage.SessionStorageProvider`

```python
from researchq import SessionStorageProvider

storage = SessionStorageProvider()
```

### SQLiteStorageProvider ⭐ NEW
- **Type**: SQLite database storage
- **Persistence**: Data persists across sessions
- **Use case**: Long-term research data storage
- **Performance**: Fast with disk persistence
- **Location**: `researchq.sqlite_storage.SQLiteStorageProvider`

```python
from researchq import SQLiteStorageProvider

# Use default database file
storage = SQLiteStorageProvider()

# Or specify custom database path
storage = SQLiteStorageProvider("my_research.db")
```

## Choosing a Storage Provider

| Scenario | Recommended Provider | Reason |
|----------|---------------------|---------|
| Quick experiments | SessionStorageProvider | Fastest, no setup |
| Research projects | SQLiteStorageProvider | Persistent, reliable |
| Large datasets | SQLiteStorageProvider | Memory efficient |
| Multi-session work | SQLiteStorageProvider | Data persists |
| CI/CD testing | SessionStorageProvider | Clean state each run |

## Usage with Workflow

Both storage providers implement the same interface and can be used interchangeably:

```python
from researchq import Workflow, SQLiteStorageProvider
from researchq.mock_query import MockQueryHandler, MockResponseModel

# Set up workflow with persistent storage
query_handler = MockQueryHandler(MockResponseModel)
storage = SQLiteStorageProvider("research.db")
workflow = Workflow(query_handler=query_handler, storage=storage)

# Use workflow normally - responses will be cached to SQLite
answer = await workflow.ask(question)
```

## Storage Provider Interface

All storage providers implement the `StorageProvider` abstract base class:

```python
from abc import ABC, abstractmethod
from typing import AsyncIterable
from researchq.classes import Question, QueryResponse

class StorageProvider(ABC):
    @abstractmethod
    async def save_response(self, question: Question, response: QueryResponse) -> None:
        """Save a question/response pair."""
        
    @abstractmethod
    async def get_response(self, question: Question) -> QueryResponse | None:
        """Retrieve a response for a question."""
        
    @abstractmethod
    async def delete_response(self, question: Question) -> None:
        """Delete a stored response."""
        
    @abstractmethod
    async def get_stored_questions(self) -> AsyncIterable[Question]:
        """Iterate over all stored questions."""
```

## Creating Custom Storage Providers

You can create custom storage providers by implementing the `StorageProvider` interface:

```python
from researchq.classes import StorageProvider, Question, QueryResponse

class MyCustomStorageProvider(StorageProvider):
    async def save_response(self, question: Question, response: QueryResponse) -> None:
        # Your implementation here
        pass
        
    async def get_response(self, question: Question) -> QueryResponse | None:
        # Your implementation here
        pass
        
    # ... implement other required methods
```

## See Also

- [SQLite Storage Provider Documentation](sqlite_storage.md) - Detailed guide for SQLite storage
- [Examples](../examples/) - Working examples with different storage providers