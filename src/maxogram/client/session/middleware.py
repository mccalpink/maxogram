"""HTTP-level middleware для запросов к Max Bot API."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from maxogram.exceptions import MaxServerError, MaxTooManyRequestsError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from maxogram.methods.base import MaxMethod

    MakeRequestFunc = Callable[
        [Any, MaxMethod[Any], float | None],
        Coroutine[Any, Any, Any],
    ]

__all__ = [
    "LoggingMiddleware",
    "RequestMiddleware",
    "RetryMiddleware",
]


class RequestMiddleware(ABC):
    """Абстрактный базовый класс HTTP-level middleware.

    Middleware оборачивает вызов ``make_request`` и может добавлять
    логику до/после запроса (retry, logging, metrics и т.д.).

    Реализации вызываются по wrapping-паттерну::

        result = await middleware(make_request, bot, method, timeout)
    """

    @abstractmethod
    async def __call__(
        self,
        make_request: MakeRequestFunc,
        bot: Any,
        method: MaxMethod[Any],
        timeout: float | None = None,
    ) -> Any:
        """Выполнить middleware-логику.

        Args:
            make_request: Функция выполнения HTTP-запроса.
            bot: Экземпляр бота.
            method: API-метод.
            timeout: Таймаут запроса.

        Returns:
            Результат выполнения запроса.
        """
        ...


class RetryMiddleware(RequestMiddleware):
    """Retry с exponential backoff при 429/5xx ошибках.

    Args:
        max_retries: Максимальное количество повторных попыток.
        base_delay: Начальная задержка (секунды).
        backoff_factor: Множитель задержки.
        max_delay: Максимальная задержка (секунды).
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 30.0,
    ) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._backoff_factor = backoff_factor
        self._max_delay = max_delay

    async def __call__(
        self,
        make_request: MakeRequestFunc,
        bot: Any,
        method: MaxMethod[Any],
        timeout: float | None = None,
    ) -> Any:
        """Выполнить запрос с retry при retryable-ошибках."""
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return await make_request(bot, method, timeout)
            except MaxTooManyRequestsError as e:
                last_error = e
                if attempt == self._max_retries:
                    raise
                delay = e.retry_after or self._calculate_delay(attempt)
                await asyncio.sleep(delay)
            except MaxServerError as e:
                last_error = e
                if attempt == self._max_retries:
                    raise
                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)

        raise last_error  # type: ignore[misc]  # pragma: no cover

    def _calculate_delay(self, attempt: int) -> float:
        """Рассчитать задержку с exponential backoff."""
        delay = self._base_delay * (self._backoff_factor ** attempt)
        return min(delay, self._max_delay)


class LoggingMiddleware(RequestMiddleware):
    """Structured logging HTTP-запросов и ответов.

    Args:
        logger_name: Имя логгера.
        log_level: Уровень логирования для запросов/ответов.
        error_level: Уровень логирования для ошибок.
    """

    def __init__(
        self,
        logger_name: str = "maxogram.client.session.middleware",
        log_level: int = logging.DEBUG,
        error_level: int = logging.ERROR,
    ) -> None:
        self._logger = logging.getLogger(logger_name)
        self._log_level = log_level
        self._error_level = error_level

    async def __call__(
        self,
        make_request: MakeRequestFunc,
        bot: Any,
        method: MaxMethod[Any],
        timeout: float | None = None,
    ) -> Any:
        """Логировать запрос, ответ и ошибки."""
        method_name = type(method).__name__
        api_path = getattr(method, "__api_path__", "unknown")
        http_method = getattr(method, "__http_method__", "unknown")

        self._logger.log(
            self._log_level,
            "Request %s %s (%s) timeout=%s",
            http_method,
            api_path,
            method_name,
            timeout,
        )

        start = time.monotonic()
        try:
            result = await make_request(bot, method, timeout)
        except Exception as e:
            elapsed = time.monotonic() - start
            self._logger.log(
                self._error_level,
                "Request error %s %s (%s) after %.3fs: %s",
                http_method,
                api_path,
                method_name,
                elapsed,
                e,
            )
            raise

        elapsed = time.monotonic() - start
        self._logger.log(
            self._log_level,
            "Response %s %s (%s) in %.3fs",
            http_method,
            api_path,
            method_name,
            elapsed,
        )
        return result
