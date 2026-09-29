# Why: Custom exception hierarchies allow upper layers (like FastAPI exception handlers) 
# to catch specific domain errors and return appropriate HTTP status codes, 
# while keeping business logic clean.

class MandiSenseError(Exception):
    """Base exception for all MandiSense AI errors."""
    pass

class DataIngestionError(MandiSenseError):
    """Raised when data cannot be fetched or parsed (e.g., Agmarknet timeouts)."""
    pass

class ConfigurationError(MandiSenseError):
    """Raised when there is an issue with application configuration."""
    pass

class AgentError(MandiSenseError):
    """Raised when an individual forecasting agent fails to compute a prediction."""
    pass

class EnsembleError(MandiSenseError):
    """Raised when the meta-ensemble layer fails to aggregate agent predictions."""
    pass

class StoreLockTimeoutError(MandiSenseError):
    """Raised when a write lock could not be acquired and the holder is not
    stale enough to be presumed abandoned. Raised rather than proceeding
    unprotected, because a read-modify-write that runs without the lock it
    was supposed to wait for can silently overwrite a concurrent run's
    inserts."""
    pass
