"""Custom exception hierarchy for the Logopaedie Report Agent backend."""


class AppError(Exception):
    """Base exception for all application errors."""


# ── AI Service Errors ────────────────────────────────────────────────────────
class AIServiceError(AppError):
    """Base exception for AI/LLM service errors."""


class RateLimitError(AIServiceError):
    """Raised when the AI service rate limit is exceeded."""


class ModelExhaustedError(AIServiceError):
    """Raised when all model fallback options are exhausted."""


class TranscriptionError(AIServiceError):
    """Raised when audio transcription fails."""


# ── Session Errors ───────────────────────────────────────────────────────────
class SessionError(AppError):
    """Base exception for session-related errors."""


class SessionNotFoundError(SessionError):
    """Raised when a session cannot be found."""


class SessionExpiredError(SessionError):
    """Raised when a session has expired."""


# ── Validation Errors ────────────────────────────────────────────────────────
class ValidationError(AppError):
    """Base exception for input validation errors."""


class FileTooLargeError(ValidationError):
    """Raised when an uploaded file exceeds the size limit."""


class UnsupportedFileTypeError(ValidationError):
    """Raised when the file type is not supported."""


# ── Report Errors ────────────────────────────────────────────────────────────
class ReportError(AppError):
    """Base exception for report-related errors."""


class ReportNotFoundError(ReportError):
    """Raised when a report cannot be found."""


class ReportGenerationError(ReportError):
    """Raised when report generation fails."""
