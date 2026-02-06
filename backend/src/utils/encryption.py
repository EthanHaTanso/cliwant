"""
Encryption utilities for sensitive data.

Uses AES-256 encryption for storing API keys and account numbers.
"""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.config import get_settings

# Cache for Fernet instance
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or create Fernet encryption instance."""
    global _fernet

    if _fernet is None:
        settings = get_settings()
        key = settings.encryption_key

        if not key:
            # Generate a default key for development (not secure for production)
            key = "development-key-do-not-use-in-production"

        # Derive a proper key from the provided key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"ai-tax-assistant-salt",  # Fixed salt for consistency
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        _fernet = Fernet(derived_key)

    return _fernet


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value.

    Args:
        value: Plain text value to encrypt

    Returns:
        Base64-encoded encrypted string
    """
    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt an encrypted string value.

    Args:
        encrypted_value: Base64-encoded encrypted string

    Returns:
        Decrypted plain text value
    """
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_value.encode())
    return decrypted.decode()
