"""
Test AI Assistant Feature

Tests the AI assistant with Azure OpenAI integration.
"""

import asyncio
import sys
import os

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.ai.ai_client import get_ai_client


async def test_ai_client():
    """Test AI client initialization and basic functionality."""
    print("=" * 70)
    print("Testing AI Assistant Feature")
    print("=" * 70)
    print()
    
    # Test 1: Initialize client
    print("1. Testing AI Client Initialization...")
    try:
        client = get_ai_client()
        provider_info = client.get_provider_info()
        print(f"   ✅ AI Client initialized successfully")
        print(f"   Provider: {provider_info['provider']}")
        print(f"   Model: {provider_info['model']}")
        print()
    except Exception as e:
        print(f"   ❌ Failed to initialize AI client: {e}")
        return
    
    # Test 2: Generate a simple response
    print("2. Testing AI Response Generation...")
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a helpful study coach."
            },
            {
                "role": "user",
                "content": "Explain Newton's First Law of Motion in simple terms."
            }
        ]
        
        print("   Sending test query to Azure OpenAI...")
        response_text, tokens_used = await client.generate_response(
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        
        print(f"   ✅ AI Response received successfully")
        print(f"   Tokens used: {tokens_used}")
        print(f"   Response preview:")
        print("   " + "-" * 66)
        # Show first 300 characters
        preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
        for line in preview.split('\n'):
            print(f"   {line}")
        print("   " + "-" * 66)
        print()
    except Exception as e:
        print(f"   ❌ Failed to generate response: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 3: Context-aware prompt
    print("3. Testing Context-Aware Prompting...")
    try:
        context_messages = [
            {
                "role": "system",
                "content": """You are an AI study coach.

Student Context:
- Exam: JEE Advanced (in 45 days)
- Subjects: Physics, Chemistry, Mathematics
- Weak areas: Thermodynamics, Organic Chemistry
- Study consistency: 85%"""
            },
            {
                "role": "user",
                "content": "How should I prioritize my subjects in the next 2 weeks?"
            }
        ]
        
        print("   Sending context-aware query...")
        response_text, tokens_used = await client.generate_response(
            messages=context_messages,
            temperature=0.7,
            max_tokens=250
        )
        
        print(f"   ✅ Context-aware response received")
        print(f"   Tokens used: {tokens_used}")
        print(f"   Response preview:")
        print("   " + "-" * 66)
        preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
        for line in preview.split('\n'):
            print(f"   {line}")
        print("   " + "-" * 66)
        print()
    except Exception as e:
        print(f"   ❌ Failed with context-aware prompt: {e}")
        return
    
    # Summary
    print("=" * 70)
    print("✅ All AI Assistant Tests Passed!")
    print("=" * 70)
    print()
    print("Azure OpenAI Integration Status:")
    print(f"  • Provider: {provider_info['provider']}")
    print(f"  • Model: {provider_info['model']}")
    print(f"  • Endpoint: Connected ✅")
    print(f"  • API Key: Valid ✅")
    print()
    print("The AI assistant is ready to use with Smart Pack users!")
    print()


if __name__ == "__main__":
    asyncio.run(test_ai_client())
