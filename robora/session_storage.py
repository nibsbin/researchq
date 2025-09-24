"""Simple in-memory storage provider implementation."""

from typing import Dict, Any, AsyncIterable
from robora.classes import StorageProvider, Question, QueryResponse


class SessionStorageProvider(StorageProvider):
    """Simple in-memory implementation of StorageProvider for demonstration purposes."""
    
    def __init__(self):
        # In-memory storage using question string as key
        self._storage: Dict[Question, QueryResponse] = {}
    
    async def save_response(self, question: Question, response:QueryResponse) -> None:
        """Save a response to in-memory storage."""
        self._storage[question] = response
    
    async def get_response(self, question: Question) -> QueryResponse|None:
        """Retrieve a response from in-memory storage."""
        response = self._storage.get(question)
        
        if response is None:
            return None
        
        # Return a string representation of the stored response
        return response
    
    async def delete_response(self, question: Question) -> None:
        """Delete a response from in-memory storage."""
        if question in self._storage:
            del self._storage[question]

    async def get_stored_questions(self) -> AsyncIterable[Question]:
        for question in self._storage.keys():
            yield question
    
    def clear(self) -> None:
        """Clear all stored responses."""
        self._storage.clear()
    
    def count(self) -> int:
        """Return the number of stored responses."""
        return len(self._storage)
    
    def __repr__(self) -> str:
        return f"SessionStorageProvider(stored_responses={len(self._storage)})"
    
    def __str__(self) -> str:
        return f"SessionStorageProvider with {len(self._storage)} stored responses"