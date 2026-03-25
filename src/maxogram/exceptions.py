"""Иерархия исключений maxogram."""

from __future__ import annotations

__all__ = [
    "ClientDecodeError",
    "MaxAPIError",
    "MaxBadRequestError",
    "MaxForbiddenError",
    "MaxNetworkError",
    "MaxNotFoundError",
    "MaxServerError",
    "MaxTooManyRequestsError",
    "MaxUnauthorizedError",
    "MaxogramError",
]


class MaxogramError(Exception):
    """Базовое исключение maxogram."""


class MaxAPIError(MaxogramError):
    """Ошибка Max Bot API (HTTP 4xx/5xx)."""

    def __init__(
        self,
        status_code: int,
        error: str | None,
        error_message: str,
        code: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = error
        self.error_message = error_message
        self.code = code
        super().__init__(f"[{status_code}] {error_message}")


class MaxUnauthorizedError(MaxAPIError):
    """401 Unauthorized — неверный токен."""

    def __init__(self, error: str | None, error_message: str, code: str | None = None) -> None:
        super().__init__(status_code=401, error=error, error_message=error_message, code=code)


class MaxBadRequestError(MaxAPIError):
    """400 Bad Request."""

    def __init__(self, error: str | None, error_message: str, code: str | None = None) -> None:
        super().__init__(status_code=400, error=error, error_message=error_message, code=code)


class MaxForbiddenError(MaxAPIError):
    """403 Forbidden."""

    def __init__(self, error: str | None, error_message: str, code: str | None = None) -> None:
        super().__init__(status_code=403, error=error, error_message=error_message, code=code)


class MaxNotFoundError(MaxAPIError):
    """404 Not Found."""

    def __init__(self, error: str | None, error_message: str, code: str | None = None) -> None:
        super().__init__(status_code=404, error=error, error_message=error_message, code=code)


class MaxTooManyRequestsError(MaxAPIError):
    """429 Too Many Requests — превышен rate limit (30 rps)."""

    def __init__(
        self,
        error: str | None,
        error_message: str,
        retry_after: float | None = None,
        code: str | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(status_code=429, error=error, error_message=error_message, code=code)


class MaxServerError(MaxAPIError):
    """5xx Server Error."""

    def __init__(
        self, status_code: int, error: str | None, error_message: str, code: str | None = None
    ) -> None:
        super().__init__(
            status_code=status_code, error=error, error_message=error_message, code=code
        )


class MaxNetworkError(MaxogramError):
    """Сетевая ошибка (таймаут, connection refused и т.п.)."""

    def __init__(
        self,
        message: str,
        original_error: BaseException | None = None,
    ) -> None:
        self.original_error = original_error
        super().__init__(message)


class ClientDecodeError(MaxogramError):
    """Ошибка парсинга JSON-ответа от API."""

    def __init__(self, message: str, original_error: BaseException | None = None) -> None:
        self.original_error = original_error
        super().__init__(message)
