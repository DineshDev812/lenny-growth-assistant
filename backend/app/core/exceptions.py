class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class DatabaseUnavailableError(AppError):
    def __init__(self, message: str = "Database is unavailable.") -> None:
        super().__init__(code="db_down", message=message, status_code=503)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(code="not_found", message=message, status_code=404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access forbidden.") -> None:
        super().__init__(code="forbidden", message=message, status_code=403)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Missing or invalid ingest token.") -> None:
        super().__init__(code="unauthorized", message=message, status_code=401)


class IngestInProgressError(AppError):
    def __init__(self, message: str = "Ingestion is already running.") -> None:
        super().__init__(code="ingest_in_progress", message=message, status_code=409)


class ProviderUnconfiguredError(AppError):
    def __init__(self, message: str = "LLM provider is not configured.") -> None:
        super().__init__(code="provider_unconfigured", message=message, status_code=503)


class ProviderUnavailableError(AppError):
    def __init__(self, message: str = "LLM provider is currently unavailable.") -> None:
        super().__init__(code="provider_unavailable", message=message, status_code=503)


class ProviderTimeoutError(AppError):
    def __init__(self, message: str = "LLM provider request timed out.") -> None:
        super().__init__(code="provider_timeout", message=message, status_code=504)


class RateLimitedError(AppError):
    def __init__(self, message: str = "Too many requests. Please wait before trying again.") -> None:
        super().__init__(code="rate_limited", message=message, status_code=429)


class MessageTooLongError(AppError):
    def __init__(self, message: str = "Message exceeds maximum allowed length.") -> None:
        super().__init__(code="message_too_long", message=message, status_code=400)


class ModelUnavailableError(AppError):
    def __init__(self, message: str = "Model provider is currently unavailable.") -> None:
        super().__init__(code="model_unavailable", message=message, status_code=503)


class ModelTimeoutError(AppError):
    def __init__(self, message: str = "Model request timed out.") -> None:
        super().__init__(code="model_timeout", message=message, status_code=504)
