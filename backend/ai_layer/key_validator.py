"""API Key validation service for BYOK (Bring Your Own Key) feature."""

import asyncio
import logging
from typing import Tuple
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

VALIDATION_TIMEOUT = 10  # seconds


async def validate_deepseek_key(api_key: str) -> Tuple[bool, str | None]:
    """Test a DeepSeek API key with a minimal API call.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid, otherwise contains user-friendly error:
        - "Invalid API key" (401)
        - "Rate limit exceeded" (429)
        - "Service unavailable" (5xx)
        - "Validation timeout" (timeout after 10s)
    """
    try:
        client = AsyncOpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=api_key
        )

        # Make a minimal API call (list models)
        # Timeout after 10 seconds
        await asyncio.wait_for(
            client.models.list(),
            timeout=VALIDATION_TIMEOUT
        )

        return True, None

    except asyncio.TimeoutError:
        return False, "Validation timeout"
    except Exception as e:
        error_str = str(e).lower()
        if "401" in error_str or "unauthorized" in error_str:
            return False, "Invalid API key"
        elif "429" in error_str or "rate limit" in error_str:
            return False, "Rate limit exceeded"
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            return False, "Service unavailable"
        else:
            logger.error(f"Unexpected error validating DeepSeek key: {e}")
            return False, "Validation failed"


async def validate_gemini_key(api_key: str) -> Tuple[bool, str | None]:
    """Test a Gemini API key with a minimal API call.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid, otherwise contains user-friendly error.
    """
    try:
        client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key=api_key
        )

        # Make a minimal API call (list models)
        await asyncio.wait_for(
            client.models.list(),
            timeout=VALIDATION_TIMEOUT
        )

        return True, None

    except asyncio.TimeoutError:
        return False, "Validation timeout"
    except Exception as e:
        error_str = str(e).lower()
        if "401" in error_str or "unauthorized" in error_str:
            return False, "Invalid API key"
        elif "429" in error_str or "rate limit" in error_str:
            return False, "Rate limit exceeded"
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            return False, "Service unavailable"
        else:
            logger.error(f"Unexpected error validating Gemini key: {e}")
            return False, "Validation failed"
