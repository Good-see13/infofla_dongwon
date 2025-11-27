"""
Custom exceptions for AI model management and inference services.
"""

from typing import Optional


class ModelLoadError(RuntimeError):
    """Raised when a model fails to load."""


class ModelNotAvailableError(RuntimeError):
    """Raised when a requested model is not loaded or unavailable."""


class DetectionError(RuntimeError):
    """Raised when the detection pipeline fails."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class VLMProcessingError(RuntimeError):
    """Raised when the VLM pipeline fails."""


def build_error_message(prefix: str, detail: Optional[str] = None) -> str:
    """
    Compose a normalized error message.

    Args:
        prefix: Contextual prefix for the error.
        detail: Optional detailed message.
    """
    if detail:
        return f"{prefix}: {detail}"
    return prefix
