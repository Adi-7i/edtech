"""
AI Client

Provider-agnostic AI client wrapper for OpenAI and Azure OpenAI.
"""

import asyncio
import os
import time
from typing import Dict, List, Optional

try:
    from openai import AsyncOpenAI, AsyncAzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    # OpenAI package not installed - use mock for development
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None
    AsyncAzureOpenAI = None


class AIClient:
    """
    Provider-agnostic AI client.
    
    Supports:
    - OpenAI (GPT-4, GPT-3.5-turbo)
    - Azure OpenAI
    
    Configuration via environment variables:
    - AI_PROVIDER: "openai" or "azure_openai"
    - OPENAI_API_KEY: OpenAI API key
    - OPENAI_MODEL: Model name (e.g., "gpt-4-turbo-preview")
    - AZURE_OPENAI_ENDPOINT: Azure endpoint URL
    - AZURE_OPENAI_API_KEY: Azure API key
    - AZURE_OPENAI_DEPLOYMENT: Azure deployment name
    """
    
    def __init__(self):
        """Initialize AI client based on provider."""
        # If OpenAI package not available, use mock mode
        if not OPENAI_AVAILABLE:
            self.provider = "mock"
            self.client = None
            self.model = "mock-gpt-4"
            print("⚠️  OpenAI package not installed - using mock AI responses")
            return
        
        self.provider = os.getenv("AI_PROVIDER", "openai")
        
        # Azure OpenAI provider
        if self.provider == "azure_openai":
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
            
            if not all([api_key, endpoint, deployment]):
                # Use mock mode if Azure config incomplete
                self.provider = "mock"
                self.client = None
                self.model = "mock-gpt-4"
                print("⚠️  Azure OpenAI config incomplete - using mock AI responses")
                return
            
            try:
                self.client = AsyncAzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=endpoint
                )
                self.model = deployment
                print(f"✅ Azure OpenAI initialized: {deployment}")
            except Exception as e:
                self.provider = "mock"
                self.client = None
                self.model = "mock-gpt-4"
                print(f"⚠️  Azure OpenAI initialization failed: {e}")
        
        # Standard OpenAI provider
        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # Use mock mode if no API key
                self.provider = "mock"
                self.client = None
                self.model = "mock-gpt-4"
                print("⚠️  OPENAI_API_KEY not set - using mock AI responses")
                return
            
            self.client = AsyncOpenAI(api_key=api_key)
            self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
            print(f"✅ OpenAI initialized: {self.model}")
        
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> tuple[str, int]:
        """
        Generate AI response.
        
        Args:
            messages: Chat messages [{"role": "system/user/assistant", "content": "..."}]
            temperature: Creativity level (0.0-1.0)
                - 0.0: Deterministic, focused
                - 0.7: Balanced (default)
                - 1.0: Creative, diverse
            max_tokens: Maximum response length
        
        Returns:
            Tuple of (response_text, tokens_used)
        
        Raises:
            Exception: If API call fails
        """
        # Mock mode (for development without API key)
        if self.provider == "mock":
            await asyncio.sleep(0.5)  # Simulate API delay
            
            # Generate mock response based on query
            user_message = next((m["content"] for m in messages if m["role"] == "user"), "")
            
            mock_response = f"""Based on your study profile, here's my guidance:

{user_message[:100]}...

This is a mock response since OpenAI API is not configured. In production, this would be replaced with actual AI-generated content tailored to your specific question, exam timeline, and weak subjects.

To enable real AI responses:
1. Install openai package: pip install openai
2. Set OPENAI_API_KEY environment variable
3. Restart the server

For now, continue testing other features of the AI assistant (usage tracking, access control, etc.)."""
            
            return mock_response, 150  # Mock token count
        
        # Real AI call
        try:
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract response
            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            return response_text, tokens_used
        
        except Exception as e:
            # Log error (in production, use proper logging)
            print(f"AI API Error: {str(e)}")
            raise
    
    def get_provider_info(self) -> dict:
        """
        Get current provider information.
        
        Returns:
            Dictionary with provider and model info
        """
        return {
            "provider": self.provider,
            "model": self.model
        }


# Singleton instance
_ai_client: Optional[AIClient] = None


def get_ai_client() -> AIClient:
    """
    Get AI client singleton.
    
    Creates instance on first call, reuses thereafter.
    
    Returns:
        AIClient instance
    """
    global _ai_client
    
    if _ai_client is None:
        _ai_client = AIClient()
    
    return _ai_client
