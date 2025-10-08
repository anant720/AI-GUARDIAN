# Guardian Error Handling

class GuardianError(Exception):
    """Base exception for Guardian errors."""
    pass

class ModelLoadError(GuardianError):
    """Raised when ML model fails to load."""
    pass

class AnalysisError(GuardianError):
    """Raised when message analysis fails."""
    pass

class ConfigurationError(GuardianError):
    """Raised when configuration is invalid."""
    pass



