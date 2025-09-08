"""Interfaces with LLMs"""

from typing import Any, Dict, List, Optional
import httpx

import httpx
import asyncio

from autora.CONFIG import PERPLEXITY_API_KEY

async def query_sonar(prompt: Optional[str] = None, model: str = "sonar"):
    """
    Query the Perplexity Sonar API with a custom prompt
    
    Args:
        prompt: The user prompt to send. If None, uses default AI developments query
        model: The model to use (default: "sonar")
    
    Returns:
        dict: The API response as a dictionary
    """
    if prompt is None:
        prompt = "What are the major AI developments and announcements from today across the tech industry?"
    
    async with httpx.AsyncClient(timeout=50.0) as client:
        response = await client.post(  # Changed from GET to POST
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
                        'content': prompt
                    }
                ]
            }
        )
        return response.json()


async def query_sonar_with_context(prompt: str, context_messages: List[Dict[str, str]], model: str = "sonar"):
    """
    Query the Perplexity Sonar API with conversation context
    
    Args:
        prompt: The current user prompt
        context_messages: List of previous messages in the conversation
        model: The model to use (default: "sonar")
    
    Returns:
        dict: The API response as a dictionary
    """
    messages = context_messages + [{"role": "user", "content": prompt}]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                'model': model,
                'messages': messages
            }
        )
        return response.json()