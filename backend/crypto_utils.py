"""Encryption utilities for BYOK API keys using Fernet symmetric encryption."""

import logging
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

logger = logging.getLogger(__name__)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key using Fernet symmetric encryption.
    
    Args:
        plaintext: The raw API key to encrypt.
        
    Returns:
        Base64-encoded ciphertext string.
        
    Raises:
        RuntimeError: If ENCRYPTION_KEY is not configured.
    """
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str | None:
    """Decrypt an API key.
    
    Args:
        ciphertext: The encrypted API key.
        
    Returns:
        The decrypted plaintext key, or None if decryption fails.
        Never raises an exception - logs errors and returns None.
    """
    if not ciphertext:
        return None
    
    try:
        key = current_app.config.get('ENCRYPTION_KEY')
        if not key:
            logger.error("ENCRYPTION_KEY is not configured")
            return None
        
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        logger.error(f"Failed to decrypt API key - invalid token (wrong key?): {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        return None
