class ContextOSError(Exception):
    """Base exception for all ContextOS errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class DatabaseError(ContextOSError):
    """Raised when database operations fail."""
    pass

class VectorStoreError(ContextOSError):
    """Raised when vector store operations fail."""
    pass

class LLMError(ContextOSError):
    """Raised when LLM providers fail."""
    pass

class EngineError(ContextOSError):
    """Raised when optimization engines encounter a fatal error."""
    pass

class IngestionError(ContextOSError):
    """Raised when file ingestion or parsing fails."""
    pass

class AuthError(ContextOSError):
    """Raised on authentication failures."""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)

class RateLimitError(ContextOSError):
    """Raised when rate limits are exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)
