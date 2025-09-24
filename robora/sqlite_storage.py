"""SQLite-based storage provider implementation."""

import sqlite3
import json
import asyncio
from typing import Dict, Any, AsyncIterable, Optional
from pathlib import Path
from robora.classes import StorageProvider, Question, QueryResponse


class SQLiteStorageProvider(StorageProvider):
    """SQLite-based implementation of StorageProvider for persistent storage."""
    
    def __init__(self, db_path: str = "robora.db"):
        """
        Initialize SQLite storage provider.
        
        Args:
            db_path: Path to SQLite database file. Defaults to "robora.db"
        """
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the SQLite database and create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS question_responses (
                    question_hash INTEGER PRIMARY KEY,
                    question_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def _serialize_question(self, question: Question) -> str:
        """Serialize a Question object to JSON string."""
        return json.dumps({
            "word_set": question.word_set,
            "template": question.template,
            "response_model": question.response_model.__name__ if question.response_model else None
        })
    
    def _deserialize_question(self, question_json: str, response_model_name: Optional[str] = None) -> Question:
        """Deserialize a Question object from JSON string."""
        data = json.loads(question_json)
        # Note: We can't fully reconstruct the response_model from just the name
        # For now, we'll set it to None and let the calling code handle it
        return Question(
            word_set=data["word_set"],
            template=data["template"],
            response_model=None  # This will need to be handled by the caller
        )
    
    def _serialize_response(self, response: QueryResponse) -> str:
        """Serialize a QueryResponse object to JSON string."""
        return json.dumps({
            "full_response": response.full_response,
            "error": response.error
        })
    
    def _deserialize_response(self, response_json: str) -> QueryResponse:
        """Deserialize a QueryResponse object from JSON string."""
        data = json.loads(response_json)
        return QueryResponse(
            full_response=data["full_response"],
            error=data["error"]
        )
    
    async def save_response(self, question: Question, response: QueryResponse) -> None:
        """Save a response to SQLite storage."""
        # Run database operations in a thread to avoid blocking the event loop
        def _save():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO question_responses 
                    (question_hash, question_json, response_json)
                    VALUES (?, ?, ?)
                """, (
                    hash(question),
                    self._serialize_question(question),
                    self._serialize_response(response)
                ))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _save)
    
    async def get_response(self, question: Question) -> QueryResponse | None:
        """Retrieve a response from SQLite storage."""
        def _get():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT response_json FROM question_responses 
                    WHERE question_hash = ?
                """, (hash(question),))
                row = cursor.fetchone()
                return row[0] if row else None
        
        response_json = await asyncio.get_event_loop().run_in_executor(None, _get)
        
        if response_json is None:
            return None
        
        return self._deserialize_response(response_json)
    
    async def delete_response(self, question: Question) -> None:
        """Delete a response from SQLite storage."""
        def _delete():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    DELETE FROM question_responses 
                    WHERE question_hash = ?
                """, (hash(question),))
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, _delete)
    
    async def get_stored_questions(self) -> AsyncIterable[Question]:
        """Retrieve all stored questions from SQLite storage."""
        def _get_all():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT question_json FROM question_responses
                    ORDER BY created_at
                """)
                return cursor.fetchall()
        
        rows = await asyncio.get_event_loop().run_in_executor(None, _get_all)
        
        for row in rows:
            question_json = row[0]
            question = self._deserialize_question(question_json)
            yield question
    
    def clear(self) -> None:
        """Clear all stored responses."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM question_responses")
            conn.commit()
    
    def count(self) -> int:
        """Return the number of stored responses."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM question_responses")
            return cursor.fetchone()[0]
    
    def __repr__(self) -> str:
        return f"SQLiteStorageProvider(db_path='{self.db_path}', stored_responses={self.count()})"
    
    def __str__(self) -> str:
        return f"SQLiteStorageProvider with {self.count()} stored responses at {self.db_path}"