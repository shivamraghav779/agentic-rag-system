"""API Key Manager with fallback mechanism for Gemini API keys."""
import logging
import time
from typing import List, Optional
from threading import Lock
import google.generativeai as genai

# Try to import google exceptions, but handle if not available
try:
    from google.api_core import exceptions as google_exceptions
except ImportError:
    google_exceptions = None

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manages multiple Gemini API keys with automatic fallback on rate limits."""
    
    def __init__(self, api_keys: List[str]):
        """
        Initialize API key manager.
        
        Args:
            api_keys: List of Gemini API keys (comma-separated string or list)
        """
        # Parse API keys if it's a string
        if isinstance(api_keys, str):
            # Split by comma and clean up
            self.api_keys = [key.strip() for key in api_keys.split(',') if key.strip()]
        else:
            self.api_keys = [key for key in api_keys if key]
        
        if not self.api_keys:
            raise ValueError("At least one API key is required")
        
        self.current_key_index = 0
        self.lock = Lock()
        self.key_blacklist = {}  # key_index -> timestamp when it can be retried
        self.blacklist_duration = 60  # seconds to wait before retrying a rate-limited key
        
        logger.info(f"Initialized API Key Manager with {len(self.api_keys)} keys")
    
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
        
        # Blacklist expired, remove it
        del self.key_blacklist[key_index]
        return False
    
    def _blacklist_key(self, key_index: int):
        """Blacklist a key for a certain duration."""
        self.key_blacklist[key_index] = time.time() + self.blacklist_duration
        logger.warning(f"API key at index {key_index} blacklisted for {self.blacklist_duration} seconds")
    
    def _switch_to_next_key(self) -> bool:
        """
        Switch to the next available API key.
        
        Returns:
            True if switched to a new key, False if no keys available
        """
        with self.lock:
            original_index = self.current_key_index
            
            # Try to find an available key
            for attempt in range(len(self.api_keys)):
                next_index = (self.current_key_index + 1) % len(self.api_keys)
                
                # If we've tried all keys, check if any are no longer blacklisted
                if attempt == len(self.api_keys) - 1:
                    # Check if original key is still blacklisted
                    if not self._is_key_blacklisted(original_index):
                        self.current_key_index = original_index
                        logger.info(f"Switched back to original API key at index {original_index}")
                        return True
                    # All keys are blacklisted, wait a bit and try original
                    time.sleep(1)
                    if not self._is_key_blacklisted(original_index):
                        self.current_key_index = original_index
                        return True
                    raise Exception("All API keys are rate limited. Please try again later.")
                
                if not self._is_key_blacklisted(next_index):
                    self.current_key_index = next_index
                    logger.info(f"Switched to API key at index {next_index} (from {original_index})")
                    return True
            
            return False
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limit error."""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Check for common rate limit indicators
        rate_limit_indicators = [
            'rate limit',
            'rate_limit',
            'quota exceeded',
            'resource exhausted',
            '429',
            'too many requests',
            'quotaexceeded',
            'resourceedexhausted'
        ]
        
        if any(indicator in error_str for indicator in rate_limit_indicators):
            return True
        
        # Check for Google API specific rate limit exceptions
        if hasattr(error, 'status_code') and error.status_code == 429:
            return True
        
        if google_exceptions and isinstance(error, google_exceptions.ResourceExhausted):
            return True
        
        return False
    
    def execute_with_fallback(self, func, *args, **kwargs):
        """
        Execute a function with API key fallback on rate limit errors.
        
        Args:
            func: Function to execute (should accept api_key as first parameter or use genai.configure)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            Exception: If all keys are exhausted or other errors occur
        """
        max_attempts = len(self.api_keys) * 2  # Try each key at least twice
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                current_key = self.get_current_key()
                
                # Configure genai with current key
                genai.configure(api_key=current_key)
                
                # Execute the function
                return func(*args, **kwargs)
                
            except Exception as e:
                last_error = e
                
                # Check if it's a rate limit error
                if self._is_rate_limit_error(e):
                    logger.warning(
                        f"Rate limit error with key at index {self.current_key_index}: {str(e)}"
                    )
                    
                    # Blacklist current key
                    self._blacklist_key(self.current_key_index)
                    
                    # Try to switch to next key
                    if not self._switch_to_next_key():
                        # All keys exhausted
                        raise Exception(
                            "All API keys have been rate limited. Please try again later."
                        ) from e
                    
                    # Continue to next attempt with new key
                    continue
                else:
                    # Not a rate limit error, re-raise immediately
                    logger.error(f"Non-rate-limit error with Gemini API: {str(e)}")
                    raise
        
        # If we get here, all attempts failed
        raise Exception(
            f"Failed after {max_attempts} attempts. Last error: {str(last_error)}"
        ) from last_error
    
    def reset_blacklist(self):
        """Reset the blacklist (useful for testing or manual reset)."""
        with self.lock:
            self.key_blacklist.clear()
            logger.info("API key blacklist reset")

