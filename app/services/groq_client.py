"""Groq API client for chat completions."""
import requests
from typing import List, Dict, Optional, Any
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GroqRateLimitError(requests.exceptions.HTTPError):
    """Custom exception for Groq rate limit errors."""
    def __init__(self, message, response=None):
        super().__init__(message)
        self.status_code = 429
        self.response = response


class GroqClient:
    """Client for Groq API chat completions."""
    
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize Groq client.
        
        Args:
            api_key: Groq API key
            model: Model name (default: llama-3.3-70b-versatile)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
    
    def generate_content(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Generate content using Groq API.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response dictionary with 'text' and usage information
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            # Check for rate limit - raise exception that will be caught by provider manager
            if response.status_code == 429:
                error_msg = response.json().get('error', {}).get('message', 'Rate limit exceeded')
                raise GroqRateLimitError(f"429 Rate Limit: {error_msg}", response=response)
            
            response.raise_for_status()
            
            data = response.json()
            
            # Extract response text
            if 'choices' in data and len(data['choices']) > 0:
                text = data['choices'][0]['message']['content']
            else:
                text = "I couldn't generate a response. Please try again."
            
            # Extract usage information
            usage = data.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            
            # Create a response-like object
            class GroqResponse:
                def __init__(self, text, prompt_tokens, completion_tokens):
                    self.text = text
                    self.prompt_tokens = prompt_tokens
                    self.completion_tokens = completion_tokens
                    # For compatibility with Gemini response format
                    self.usage_metadata = type('obj', (object,), {
                        'prompt_token_count': prompt_tokens,
                        'candidates_token_count': completion_tokens
                    })()
            
            return GroqResponse(text, prompt_tokens, completion_tokens)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {str(e)}")
            raise Exception(f"Groq API error: {str(e)}") from e

