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


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Missing or invalid ingest token.") -> None:
        super().__init__(code="unauthorized", message=message, status_code=401)
