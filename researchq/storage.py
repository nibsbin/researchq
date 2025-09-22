"""Abstract storage classes for query results in AutoRA sprayer"""

import sqlite3
import json
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import asyncio
from datetime import datetime


class QueryStorage(ABC):
    """Abstract base class for query result storage"""
    
    @abstractmethod
    async def store_query_result(self, query_result: Dict[str, Any]) -> None:
        """Store a single query result"""
        pass
    
    @abstractmethod
    async def retrieve_query_results(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieve query results, optionally filtered"""
        pass
    
    @abstractmethod
    async def retrieve_as_dataframe(self, filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Retrieve query results as a pandas DataFrame"""
        pass
    
    @abstractmethod
    async def clear_all_results(self) -> None:
        """Clear all stored query results"""
        pass
    
    @abstractmethod
    async def get_result_count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get count of stored query results"""
        pass


class InMemoryStorage(QueryStorage):
    """In-memory storage implementation for query results"""
    
    def __init__(self):
        self._results: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
    
    async def store_query_result(self, query_result: Dict[str, Any]) -> None:
        """Store a single query result in memory"""
        async with self._lock:
            # Add timestamp if not present
            if 'timestamp' not in query_result:
                query_result['timestamp'] = datetime.now().isoformat()
            self._results.append(query_result.copy())
    
    async def retrieve_query_results(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieve query results from memory, optionally filtered"""
        async with self._lock:
            if not filters:
                return self._results.copy()
            
            # Simple filtering implementation
            filtered_results = []
            for result in self._results:
                match = True
                for key, value in filters.items():
                    if key not in result or result[key] != value:
                        match = False
                        break
                if match:
                    filtered_results.append(result)
            
            return filtered_results
    
    async def retrieve_as_dataframe(self, filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Retrieve query results as a pandas DataFrame"""
        results = await self.retrieve_query_results(filters)
        return pd.DataFrame(results)
    
    async def clear_all_results(self) -> None:
        """Clear all stored query results from memory"""
        async with self._lock:
            self._results.clear()
    
    async def get_result_count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get count of stored query results"""
        results = await self.retrieve_query_results(filters)
        return len(results)


class SQLiteStorage(QueryStorage):
    """SQLite database storage implementation for query results"""
    
    def __init__(self, db_path: Union[str, Path] = "autora_queries.db"):
        self.db_path = Path(db_path)
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def _initialize_db(self) -> None:
        """Initialize the SQLite database with the required schema"""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            # Run database initialization in a thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(None, self._create_schema)
            self._initialized = True
    
    def _create_schema(self) -> None:
        """Create the database schema (synchronous helper)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS query_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id TEXT,
                    research_question TEXT,
                    sonar_response TEXT,
                    sonar_response_json TEXT,
                    question_template TEXT,
                    search_results TEXT,
                    citations TEXT,
                    enriched_citations TEXT,
                    content TEXT,
                    structured_data TEXT,
                    parsing_success BOOLEAN,
                    parsing_error TEXT,
                    retries_used INTEGER,
                    timestamp TEXT,
                    word_dict TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indices for common query patterns
            conn.execute('CREATE INDEX IF NOT EXISTS idx_research_question ON query_results(research_question)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_parsing_success ON query_results(parsing_success)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON query_results(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON query_results(created_at)')
            
            conn.commit()
    
    async def store_query_result(self, query_result: Dict[str, Any]) -> None:
        """Store a single query result in SQLite database"""
        await self._initialize_db()
        
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(None, self._store_result_sync, query_result)
    
    def _store_result_sync(self, query_result: Dict[str, Any]) -> None:
        """Synchronous helper to store result in database"""
        # Prepare data for insertion
        data = query_result.copy()
        
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        # Convert complex objects to JSON strings
        json_fields = ['sonar_response_json', 'search_results', 'citations', 'enriched_citations', 
                      'structured_data', 'word_dict']
        
        for field in json_fields:
            if field in data and data[field] is not None:
                if not isinstance(data[field], str):
                    data[field] = json.dumps(data[field])
        
        # Extract word_dict fields for separate columns
        word_dict = data.get('word_dict', {})
        if isinstance(word_dict, str):
            try:
                word_dict = json.loads(word_dict)
            except (json.JSONDecodeError, TypeError):
                word_dict = {}
        
        with sqlite3.connect(self.db_path) as conn:
            # Insert the main record
            conn.execute('''
                INSERT INTO query_results (
                    query_id, research_question, sonar_response, sonar_response_json,
                    question_template, search_results, citations, enriched_citations,
                    content, structured_data, parsing_success, parsing_error,
                    retries_used, timestamp, word_dict
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('query_id'),
                data.get('research_question'),
                data.get('sonar_response'),
                data.get('sonar_response_json'),
                data.get('question_template'),
                data.get('search_results'),
                data.get('citations'),
                data.get('enriched_citations'),
                data.get('content'),
                data.get('structured_data'),
                data.get('parsing_success'),
                data.get('parsing_error'),
                data.get('retries_used'),
                data.get('timestamp'),
                data.get('word_dict')
            ))
            conn.commit()
    
    async def retrieve_query_results(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Retrieve query results from SQLite database, optionally filtered"""
        await self._initialize_db()
        
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(None, self._retrieve_results_sync, filters)
    
    def _retrieve_results_sync(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Synchronous helper to retrieve results from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable column access by name
            
            query = "SELECT * FROM query_results"
            params = []
            
            if filters:
                where_clauses = []
                for key, value in filters.items():
                    # Check if it's a direct column
                    if key in ['query_id', 'research_question', 'parsing_success', 'timestamp', 'created_at']:
                        where_clauses.append(f"{key} = ?")
                        params.append(value)
                    else:
                        # For other fields, search in the JSON word_dict
                        where_clauses.append(f"json_extract(word_dict, '$.{key}') = ?")
                        params.append(value)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY created_at DESC"
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert rows to dictionaries and parse JSON fields
            results = []
            json_fields = ['sonar_response_json', 'search_results', 'citations', 'enriched_citations', 
                          'structured_data', 'word_dict']
            
            for row in rows:
                result = dict(row)
                
                # Parse JSON fields back to objects
                for field in json_fields:
                    if result[field] is not None:
                        try:
                            result[field] = json.loads(result[field])
                        except (json.JSONDecodeError, TypeError):
                            # Keep as string if parsing fails
                            pass
                
                # Expand word_dict fields back to top level
                word_dict = result.get('word_dict', {})
                if isinstance(word_dict, dict):
                    result.update(word_dict)
                
                results.append(result)
            
            return results
    
    async def retrieve_as_dataframe(self, filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Retrieve query results as a pandas DataFrame"""
        results = await self.retrieve_query_results(filters)
        return pd.DataFrame(results)
    
    async def clear_all_results(self) -> None:
        """Clear all stored query results from database"""
        await self._initialize_db()
        
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(None, self._clear_results_sync)
    
    def _clear_results_sync(self) -> None:
        """Synchronous helper to clear all results"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM query_results")
            conn.commit()
    
    async def get_result_count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get count of stored query results"""
        await self._initialize_db()
        
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(None, self._get_count_sync, filters)
    
    def _get_count_sync(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Synchronous helper to get result count"""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT COUNT(*) FROM query_results"
            params = []
            
            if filters:
                where_clauses = []
                for key, value in filters.items():
                    # Check if it's a direct column
                    if key in ['query_id', 'research_question', 'parsing_success', 'timestamp', 'created_at']:
                        where_clauses.append(f"{key} = ?")
                        params.append(value)
                    else:
                        # For other fields, search in the JSON word_dict
                        where_clauses.append(f"json_extract(word_dict, '$.{key}') = ?")
                        params.append(value)
                
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
            
            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]


def create_storage(storage_type: str = "memory", **kwargs) -> QueryStorage:
    """Factory function to create storage instances
    
    Args:
        storage_type: Either "memory" or "sqlite"
        **kwargs: Additional arguments for storage initialization
        
    Returns:
        QueryStorage instance
    """
    if storage_type.lower() == "memory":
        return InMemoryStorage()
    elif storage_type.lower() == "sqlite":
        db_path = kwargs.get("db_path", "autora_queries.db")
        return SQLiteStorage(db_path)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}. Use 'memory' or 'sqlite'")