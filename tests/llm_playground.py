"""
LLM Playground - A tool to test and experiment with the LLM module
"""

import asyncio
import sys
import os
import json

# Add the parent directory to the path so we can import from researchq
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from researchq.llm import query_sonar


def print_separator():
    print("=" * 60)


def print_response(response):
    """Pretty print the LLM response"""
    print("\n📤 Response:")
    print_separator()
    
    if isinstance(response, dict):
        # Pretty print JSON response
        print(json.dumps(response, indent=2))
    else:
        print(response)
    
    print_separator()


async def test_default_query():
    """Test the default query from the llm.py file"""
    print("\n🧪 Testing default query (AI developments today)...")
    try:
        response = await query_sonar()
        print_response(response)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def custom_query(prompt: str):
    """Test with a custom prompt"""
    print(f"\n🧪 Testing custom query: '{prompt}'...")
    
    try:
        # Use the updated query_sonar function that accepts custom prompts
        response = await query_sonar(prompt)
        print_response(response)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def interactive_mode():
    """Interactive mode for testing custom prompts"""
    print("\n🎮 Interactive Mode - Enter your prompts (type 'quit' to exit)")
    print("Type 'default' to test the original query")
    print_separator()
    
    while True:
        prompt = input("\n💬 Enter your prompt: ").strip()
        
        if prompt.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        elif prompt.lower() == 'default':
            await test_default_query()
        elif prompt:
            await custom_query(prompt)
        else:
            print("⚠️  Please enter a valid prompt")


async def run_tests():
    """Run a series of predefined tests"""
    print("🚀 Running LLM Playground Tests")
    print_separator()
    
    # Check if API key is configured
    from researchq.CONFIG import PERPLEXITY_API_KEY
    if not PERPLEXITY_API_KEY:
        print("❌ PERPLEXITY_API_KEY is not configured!")
        print("Make sure you have a .env file with PERPLEXITY_API_KEY set")
        return
    
    print("✅ API key found")
    
    # Test 1: Default query
    success1 = await test_default_query()
    
    # Test 2: Custom query
    test_prompts = [
        "What is the weather like today?",
        "Explain quantum computing in simple terms",
        "What are the latest developments in AI research?"
    ]
    
    successes = [success1]
    
    for prompt in test_prompts:
        success = await custom_query(prompt)
        successes.append(success)
    
    # Summary
    print(f"\n📊 Test Results: {sum(successes)}/{len(successes)} tests passed")
    
    return all(successes)


def show_help():
    """Show help information"""
    print("""
🔧 LLM Playground Help
======================

Available commands:
  python llm_playground.py test       - Run predefined tests
  python llm_playground.py interactive - Enter interactive mode
  python llm_playground.py help       - Show this help message

Interactive mode commands:
  - Enter any text to send as a prompt
  - 'default' - Test the original hardcoded query
  - 'quit' or 'q' - Exit interactive mode

Example usage:
  python llm_playground.py test
  python llm_playground.py interactive
    """)


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        command = "interactive"
    else:
        command = sys.argv[1].lower()
    
    if command == "test":
        await run_tests()
    elif command == "interactive":
        await interactive_mode()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    asyncio.run(main())