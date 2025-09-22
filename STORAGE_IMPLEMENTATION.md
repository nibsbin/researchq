# Storage Abstraction Implementation

This document describes the storage abstraction implementation for AutoRA sprayer query results.

## Overview

The storage abstraction allows query results to be stored and retrieved using different backends while maintaining a consistent interface. This addresses the requirement to "Create an abstract class that abstracts storage read and write for these queries" and ensures "All retrievals should go through this database class."

## Architecture

### Abstract Base Class

**`QueryStorage`** (`autora/storage.py`):
- Abstract base class defining the storage interface
- Async methods for storing and retrieving query results
- Support for filtering, counting, and DataFrame conversion
- Thread-safe operations using asyncio locks

### Storage Implementations

#### 1. InMemoryStorage
- **Purpose**: Default in-memory storage (maintains existing behavior)
- **Features**: 
  - Thread-safe using `asyncio.Lock`
  - Simple list-based storage
  - Fast access and filtering
  - Automatic timestamp addition
- **Use case**: Development, testing, small datasets

#### 2. SQLiteStorage  
- **Purpose**: Persistent database storage
- **Features**:
  - Automatic schema creation with proper indexing
  - JSON field support for complex data structures
  - Intelligent filtering (direct columns vs JSON fields)
  - Database persistence across application runs
  - Automatic serialization/deserialization
- **Use case**: Production, large datasets, data persistence

### Factory Function

**`create_storage(storage_type, **kwargs)`**:
- Factory function for easy storage instantiation
- Supports "memory" and "sqlite" types
- Configurable parameters via kwargs

## Integration with Sprayer

### Updated Functions

#### `process_single_query(task_data, storage=None)`
- Added optional `storage` parameter
- Automatically stores results when storage is provided
- Maintains backward compatibility (works without storage)

#### `spray(..., storage=None, storage_config=None)`
- Added `storage` parameter (can be instance, string, or None)
- Added `storage_config` for additional configuration
- All results retrieved from storage for consistency
- Backward compatible (defaults to memory storage)

### Usage Examples

```python
# Default behavior (memory storage)
df = await spray(word_sets=sets, research_questions=questions)

# SQLite storage with default database
df = await spray(word_sets=sets, research_questions=questions, storage="sqlite")

# SQLite storage with custom database path
df = await spray(
    word_sets=sets, 
    research_questions=questions,
    storage="sqlite",
    storage_config={"db_path": "my_results.db"}
)

# Use existing storage instance
storage = SQLiteStorage("persistent.db")
df = await spray(word_sets=sets, research_questions=questions, storage=storage)

# Access stored results later
results = await storage.retrieve_query_results()
filtered_results = await storage.retrieve_query_results({"country": "USA"})
```

## Database Schema

SQLite storage uses the following schema:

```sql
CREATE TABLE query_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT,
    research_question TEXT,
    sonar_response TEXT,
    sonar_response_json TEXT,  -- JSON serialized
    question_template TEXT,
    search_results TEXT,       -- JSON serialized  
    citations TEXT,            -- JSON serialized
    enriched_citations TEXT,   -- JSON serialized
    content TEXT,
    structured_data TEXT,      -- JSON serialized
    parsing_success BOOLEAN,
    parsing_error TEXT,
    retries_used INTEGER,
    timestamp TEXT,
    word_dict TEXT,           -- JSON serialized
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Filtering Support

Both storage backends support filtering by:

### InMemoryStorage
- Direct key-value matching on any field
- Simple equality filtering

### SQLiteStorage  
- Direct column filtering for database fields
- JSON field filtering using `json_extract()` for word_dict parameters
- Example: `{"country": "USA"}` becomes `json_extract(word_dict, '$.country') = 'USA'`

## Testing

Comprehensive test suite includes:

- **Unit Tests** (`tests/test_storage.py`): 18 tests covering all storage operations
- **Integration Tests** (`tests/test_sprayer_storage_integration.py`): 9 tests validating sprayer integration
- **Demo Scripts**: 
  - `demo_storage.py`: Basic storage functionality demonstration  
  - `demo_sprayer_with_storage.py`: Complete integration examples

## Backward Compatibility

- **100% backward compatible**: All existing code continues to work unchanged
- **Default behavior preserved**: Uses memory storage when no storage parameter provided
- **No breaking changes**: All existing function signatures maintained
- **Existing tests pass**: All prior functionality preserved

## Performance Considerations

### InMemoryStorage
- **Pros**: Fast access, no I/O overhead
- **Cons**: Memory usage grows with data, no persistence
- **Best for**: Small datasets, development, testing

### SQLiteStorage  
- **Pros**: Persistent storage, efficient for large datasets, indexed queries
- **Cons**: I/O overhead, database file management
- **Best for**: Production use, large datasets, data persistence requirements

## Error Handling

- Storage operations are wrapped in try-catch blocks
- Graceful degradation when storage operations fail
- Detailed error logging for debugging
- Query processing continues even if storage fails

## Thread Safety

- Both implementations use `asyncio.Lock` for thread safety
- Safe for concurrent access from multiple async tasks
- Database operations are executed in thread pool for SQLite

## Future Extensions

The abstract design allows for easy addition of new storage backends:

- **Redis**: For distributed/cached storage
- **PostgreSQL**: For enterprise-grade relational storage  
- **Cloud Storage**: For cloud-native deployments
- **Custom backends**: Implement `QueryStorage` interface