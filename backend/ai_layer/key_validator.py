"""API Key validation service for BYOK (Bring Your Own Key) feature."""

import asyncio
import logging
from typing import Tuple
import aiohttp
from openai import AsyncOpenAI, APIStatusError

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
    except APIStatusError as e:
        logger.info(f"DeepSeek validation HTTP {e.status_code}: {e.message}")
        if e.status_code == 401:
            return False, "Invalid API key"
        elif e.status_code == 429:
            return False, "Rate limit exceeded"
        elif e.status_code >= 500:
            return False, "Service unavailable"
        else:
            return False, "Validation failed"
    except Exception as e:
        logger.error(f"Unexpected error validating DeepSeek key: {e}")
        return False, "Validation failed"


async def validate_gemini_key(api_key: str) -> Tuple[bool, str | None]:
    """Test a Gemini API key with a lightweight models.list GET request.

    Uses the native Gemini REST API (not OpenAI-compat) to avoid
    triggering generation rate limits on free-tier keys.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid, otherwise contains user-friendly error.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=VALIDATION_TIMEOUT)) as resp:
                status = resp.status
                if status == 200:
                    return True, None
                logger.info(f"Gemini validation HTTP {status}")
                if status == 400 or status == 401 or status == 403:
                    return False, "Invalid API key"
                elif status == 429:
                    return False, "Rate limit exceeded"
                elif status >= 500:
                    return False, "Service unavailable"
                else:
                    return False, "Validation failed"
    except asyncio.TimeoutError:
        return False, "Validation timeout"
    except Exception as e:
        logger.error(f"Unexpected error validating Gemini key: {e}")
        return False, "Validation failed"
