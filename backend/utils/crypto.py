"""AES-256 encryption for user API keys via Fernet (symmetric)."""
import base64
from cryptography.fernet import Fernet
from core.config import settings


def _get_fernet() -> Fernet:
    raw = settings.ENCRYPTION_KEY
    # Accept a 64-hex-char key and convert to 32 bytes, then base64-url-encode for Fernet
    if len(raw) == 64:
        key_bytes = bytes.fromhex(raw)
    else:
        key_bytes = raw.encode()[:32].ljust(32, b"0")
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_api_key(raw_key: str) -> str:
    """Encrypt a plaintext API key for storage in the database."""
    return _get_fernet().encrypt(raw_key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    """Decrypt a stored API key back to plaintext for use in requests."""
    return _get_fernet().decrypt(encrypted.encode()).decode()
