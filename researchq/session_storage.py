"""Simple in-memory storage provider implementation."""

from typing import Dict, Any
from researchq.classes import StorageProvider, Question, QueryResponse


class SessionStorageProvider(StorageProvider):
    """Simple in-memory implementation of StorageProvider for demonstration purposes."""
    
    def __init__(self):
        # In-memory storage using question string as key
        self._storage: Dict[str, QueryResponse] = {}
    
    async def save_response(self, question: Question, response:QueryResponse) -> None:
        """Save a response to in-memory storage."""
        question_key = self._get_question_key(question)
        self._storage[question_key] = response
    
    async def get_response(self, question: Question) -> QueryResponse|None:
        """Retrieve a response from in-memory storage."""
        question_key = self._get_question_key(question)
        response = self._storage.get(question_key)
        
        if response is None:
            return None
        
        # Return a string representation of the stored response
        return response
    
    async def get_response_valid(self, question: Question) -> bool:
        return self._get_question_key(question) in self._storage
    
    async def delete_response(self, question: Question) -> None:
        """Delete a response from in-memory storage."""
        question_key = self._get_question_key(question)
        if question_key in self._storage:
            del self._storage[question_key]
    
    def _get_question_key(self, question: Question) -> str:
        """Generate a unique key for a question based on its content."""
        return question.value
    
    def get_all_responses(self) -> Dict[str, QueryResponse]:
        """Get all stored responses (utility method for debugging/inspection)."""
        return self._storage.copy()
    
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