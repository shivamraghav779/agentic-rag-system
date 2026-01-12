"""Multi-provider LLM manager with fallback mechanism for Gemini and Groq."""
import logging
import time
import requests
from typing import List, Optional, Dict, Any
from threading import Lock
from enum import Enum
import google.generativeai as genai

# Try to import google exceptions, but handle if not available
try:
    from google.api_core import exceptions as google_exceptions
except ImportError:
    google_exceptions = None

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    GROQ = "groq"


class ProviderKeyManager:
    """Manages API keys for a single provider with fallback."""
    
    def __init__(self, provider: LLMProvider, api_keys: List[str], blacklist_duration: int = 60):
        """
        Initialize provider key manager.
        
        Args:
            provider: The LLM provider (GEMINI or GROQ)
            api_keys: List of API keys for this provider
            blacklist_duration: Seconds to blacklist a key after rate limit
        """
        if isinstance(api_keys, str):
            self.api_keys = [key.strip() for key in api_keys.split(',') if key.strip()]
        else:
            self.api_keys = [key for key in api_keys if key]
        
        if not self.api_keys:
            raise ValueError(f"At least one {provider.value} API key is required")
        
        self.provider = provider
        self.current_key_index = 0
        self.lock = Lock()
        self.key_blacklist = {}
        self.blacklist_duration = blacklist_duration
        
        logger.info(f"Initialized {provider.value.upper()} Key Manager with {len(self.api_keys)} keys")
    
    def get_current_key(self) -> str:
        """Get the current active API key."""
        return self.api_keys[self.current_key_index]
    
    def _is_key_blacklisted(self, key_index: int) -> bool:
        """Check if a key is currently blacklisted."""
        if key_index not in self.key_blacklist:
            return False
        
        blacklist_until = self.key_blacklist[key_index]
        if time.time() < blacklist_until:
            return True
        
        del self.key_blacklist[key_index]
        return False
    
    def _blacklist_key(self, key_index: int):
        """Blacklist a key for a certain duration."""
        self.key_blacklist[key_index] = time.time() + self.blacklist_duration
        logger.warning(f"{self.provider.value.upper()} API key at index {key_index} blacklisted for {self.blacklist_duration} seconds")
    
    def _switch_to_next_key(self) -> bool:
        """Switch to the next available API key."""
        with self.lock:
            original_index = self.current_key_index
            
            for attempt in range(len(self.api_keys)):
                next_index = (self.current_key_index + 1) % len(self.api_keys)
                
                if attempt == len(self.api_keys) - 1:
                    if not self._is_key_blacklisted(original_index):
                        self.current_key_index = original_index
                        logger.info(f"Switched back to original {self.provider.value.upper()} API key at index {original_index}")
                        return True
                    time.sleep(1)
                    if not self._is_key_blacklisted(original_index):
                        self.current_key_index = original_index
                        return True
                    return False
                
                if not self._is_key_blacklisted(next_index):
                    self.current_key_index = next_index
                    logger.info(f"Switched to {self.provider.value.upper()} API key at index {next_index} (from {original_index})")
                    return True
            
            return False
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limit error."""
        error_str = str(error).lower()
        
        rate_limit_indicators = [
            'rate limit', 'rate_limit', 'quota exceeded', 'resource exhausted',
            '429', 'too many requests', 'quotaexceeded', 'resourceedexhausted'
        ]
        
        if any(indicator in error_str for indicator in rate_limit_indicators):
            return True
        
        if hasattr(error, 'status_code') and error.status_code == 429:
            return True
        
        if google_exceptions and isinstance(error, google_exceptions.ResourceExhausted):
            return True
        
        # Check for HTTP response errors
        if hasattr(error, 'response'):
            if hasattr(error.response, 'status_code') and error.response.status_code == 429:
                return True
        
        return False
    
    def _is_api_key_error(self, error: Exception) -> bool:
        """Check if the error is an API key expiration/invalid error."""
        error_str = str(error).lower()
        
        # Check for API key related errors
        api_key_indicators = [
            'api key expired',
            'api key invalid',
            'api_key_expired',
            'api_key_invalid',
            'invalid api key',
            'invalid_api_key',
            'api key not found',
            'authentication failed',
            'unauthorized',
            'invalid_argument',
            'api_key_invalid'
        ]
        
        if any(indicator in error_str for indicator in api_key_indicators):
            return True
        
        # Check error details if available (for Google API errors)
        if hasattr(error, 'status_code') and error.status_code == 400:
            # Check if it's an INVALID_ARGUMENT with API key error
            if 'api key' in error_str or 'api_key' in error_str:
                return True
        
        # Check for Google API specific invalid argument exceptions related to API keys
        if google_exceptions and isinstance(error, google_exceptions.InvalidArgument):
            if 'api key' in error_str or 'api_key' in error_str:
                return True
        
        return False
    
    def has_available_key(self) -> bool:
        """Check if there's at least one available (non-blacklisted) key."""
        for i in range(len(self.api_keys)):
            if not self._is_key_blacklisted(i):
                return True
        return False
    
    def reset_blacklist(self):
        """Reset the blacklist."""
        with self.lock:
            self.key_blacklist.clear()
            logger.info(f"{self.provider.value.upper()} API key blacklist reset")


class MultiProviderLLMManager:
    """Manages multiple LLM providers (Gemini and Groq) with automatic fallback."""
    
    def __init__(
        self,
        gemini_keys: Optional[List[str]] = None,
        groq_keys: Optional[List[str]] = None,
        blacklist_duration: int = 60,
        preferred_provider: LLMProvider = LLMProvider.GEMINI
    ):
        """
        Initialize multi-provider LLM manager.
        
        Args:
            gemini_keys: List of Gemini API keys
            groq_keys: List of Groq API keys
            blacklist_duration: Seconds to blacklist a key after rate limit
            preferred_provider: Preferred provider to use first
        """
        self.providers = {}
        self.current_provider = preferred_provider
        self.lock = Lock()
        self.blacklist_duration = blacklist_duration
        
        # Initialize Gemini provider
        if gemini_keys:
            try:
                self.providers[LLMProvider.GEMINI] = ProviderKeyManager(
                    LLMProvider.GEMINI, gemini_keys, blacklist_duration
                )
                logger.info("Gemini provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}")
        
        # Initialize Groq provider
        if groq_keys:
            try:
                self.providers[LLMProvider.GROQ] = ProviderKeyManager(
                    LLMProvider.GROQ, groq_keys, blacklist_duration
                )
                logger.info("Groq provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq provider: {e}")
        
        if not self.providers:
            raise ValueError("At least one provider (Gemini or Groq) must be configured")
        
        # Set current provider to first available
        if preferred_provider not in self.providers or not self.providers[preferred_provider].has_available_key():
            # Switch to first available provider
            for provider in self.providers:
                if self.providers[provider].has_available_key():
                    self.current_provider = provider
                    break
    
    def get_current_provider(self) -> LLMProvider:
        """Get the current active provider."""
        return self.current_provider
    
    def get_current_key_manager(self) -> ProviderKeyManager:
        """Get the key manager for the current provider."""
        return self.providers[self.current_provider]
    
    def _switch_to_next_provider(self) -> bool:
        """Switch to the next available provider."""
        with self.lock:
            original_provider = self.current_provider
            
            # Try all providers
            for provider in self.providers:
                if provider != self.current_provider:
                    if self.providers[provider].has_available_key():
                        self.current_provider = provider
                        logger.info(f"Switched from {original_provider.value.upper()} to {provider.value.upper()}")
                        return True
            
            # If original provider has available keys now, switch back
            if self.providers[original_provider].has_available_key():
                self.current_provider = original_provider
                logger.info(f"Switched back to {original_provider.value.upper()}")
                return True
            
            return False
    
    def execute_with_fallback(self, gemini_func, groq_func, *args, **kwargs):
        """
        Execute a function with provider and key fallback.
        
        Args:
            gemini_func: Function to execute for Gemini (should configure genai internally)
            groq_func: Function to execute for Groq
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of function execution
        """
        max_provider_attempts = len(self.providers) * 2
        last_error = None
        
        for provider_attempt in range(max_provider_attempts):
            provider_manager = self.get_current_key_manager()
            max_key_attempts = len(provider_manager.api_keys) * 2
            
            for key_attempt in range(max_key_attempts):
                try:
                    if self.current_provider == LLMProvider.GEMINI:
                        return gemini_func(*args, **kwargs)
                    elif self.current_provider == LLMProvider.GROQ:
                        return groq_func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    if provider_manager._is_rate_limit_error(e):
                        logger.warning(
                            f"Rate limit error with {self.current_provider.value.upper()} "
                            f"key at index {provider_manager.current_key_index}: {str(e)}"
                        )
                        
                        provider_manager._blacklist_key(provider_manager.current_key_index)
                        
                        if provider_manager._switch_to_next_key():
                            continue
                        else:
                            # All keys exhausted for this provider, try next provider
                            logger.warning(f"All {self.current_provider.value.upper()} keys exhausted, trying next provider")
                            break
                    elif provider_manager._is_api_key_error(e):
                        # API key expired or invalid - try next key
                        logger.warning(
                            f"API key error (expired/invalid) with {self.current_provider.value.upper()} "
                            f"key at index {provider_manager.current_key_index}: {str(e)}"
                        )
                        
                        # Try to switch to next key
                        if provider_manager._switch_to_next_key():
                            continue
                        else:
                            # All keys exhausted or invalid for this provider, try next provider
                            logger.warning(
                                f"All {self.current_provider.value.upper()} keys expired/invalid, trying next provider"
                            )
                            break
                    else:
                        # Not a rate limit or API key error, re-raise
                        logger.error(f"Non-rate-limit error with {self.current_provider.value.upper()} API: {str(e)}")
                        raise
            
            # Try next provider
            if self._switch_to_next_provider():
                continue
            else:
                # All providers exhausted
                raise Exception(
                    f"All providers and keys have been rate limited. Please try again later. Last error: {str(last_error)}"
                ) from last_error
        
        raise Exception(
            f"Failed after {max_provider_attempts} provider attempts. Last error: {str(last_error)}"
        ) from last_error
    
    def reset_all_blacklists(self):
        """Reset all provider blacklists."""
        for provider_manager in self.providers.values():
            provider_manager.reset_blacklist()

