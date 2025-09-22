"""Simple in-memory storage provider implementation."""

from typing import Dict, Any
from classes import StorageProvider, Question


class SessionStorageProvider(StorageProvider):
    """Simple in-memory implementation of StorageProvider for demonstration purposes."""
    
    def __init__(self):
        # In-memory storage using question string as key
        self._storage: Dict[str, Dict[str, Any]] = {}
    
    async def save_response(self, question: Question, full_response: Dict[str, Any]) -> None:
        """Save a response to in-memory storage."""
        question_key = self._get_question_key(question)
        self._storage[question_key] = full_response
    
    async def get_response(self, question: Question) -> str:
        """Retrieve a response from in-memory storage."""
        question_key = self._get_question_key(question)
        response = self._storage.get(question_key)
        
        if response is None:
            return "No response found for this question"
        
        # Return a string representation of the stored response
        return str(response)
    
    def _get_question_key(self, question: Question) -> str:
        """Generate a unique key for a question based on its content."""
        return question.get_string
    
    def get_all_responses(self) -> Dict[str, Dict[str, Any]]:
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