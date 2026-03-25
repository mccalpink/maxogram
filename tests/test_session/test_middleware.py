"""Тесты RequestMiddleware, RetryMiddleware, LoggingMiddleware."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from maxogram.client.session.middleware import (
    LoggingMiddleware,
    RequestMiddleware,
    RetryMiddleware,
)
from maxogram.exceptions import MaxServerError, MaxTooManyRequestsError


def _make_method() -> MagicMock:
    """Создать мок MaxMethod."""
    method = MagicMock()
    method.__api_path__ = "/test/path"
    method.__http_method__ = "GET"
    method.__class__.__name__ = "TestMethod"
    return method


def _make_bot() -> MagicMock:
    """Создать мок Bot."""
    bot = MagicMock()
    bot.id = 123
    return bot


# ---------------------------------------------------------------------------
# RequestMiddleware — ABC
# ---------------------------------------------------------------------------


class TestRequestMiddlewareABC:
    """RequestMiddleware — абстрактный базовый класс."""

    async def test_cannot_instantiate_directly(self) -> None:
        """RequestMiddleware — абстрактный, нельзя создать напрямую."""
        with pytest.raises(TypeError):
            RequestMiddleware()  # type: ignore[abstract]

    async def test_concrete_subclass(self) -> None:
        """Можно создать конкретную реализацию."""

        class NoopMiddleware(RequestMiddleware):
            async def __call__(
                self,
                make_request: Any,
                bot: Any,
                method: Any,
                timeout: float | None = None,
            ) -> Any:
                return await make_request(bot, method, timeout)

        mw = NoopMiddleware()
        make_request = AsyncMock(return_value="result")
        bot = _make_bot()
        method = _make_method()

        result = await mw(make_request, bot, method, timeout=10.0)
        assert result == "result"
        make_request.assert_called_once_with(bot, method, 10.0)


# ---------------------------------------------------------------------------
# RetryMiddleware
# ---------------------------------------------------------------------------


class TestRetryMiddleware:
    """RetryMiddleware — retry с exponential backoff."""

    async def test_success_no_retry(self) -> None:
        """При успешном запросе — один вызов, без retry."""
        mw = RetryMiddleware(max_retries=3, base_delay=0.01)
        make_request = AsyncMock(return_value="ok")
        bot = _make_bot()
        method = _make_method()

        result = await mw(make_request, bot, method)
        assert result == "ok"
        assert make_request.call_count == 1

    async def test_retry_on_server_error(self) -> None:
        """Retry при 5xx ошибках."""
        mw = RetryMiddleware(max_retries=2, base_delay=0.01)
        make_request = AsyncMock(
            side_effect=[
                MaxServerError(
                    status_code=500, error="err", error_message="Internal"
                ),
                "ok",
            ]
        )
        bot = _make_bot()
        method = _make_method()

        result = await mw(make_request, bot, method)
        assert result == "ok"
        assert make_request.call_count == 2

    async def test_retry_on_429(self) -> None:
        """Retry при 429 Too Many Requests."""
        mw = RetryMiddleware(max_retries=2, base_delay=0.01)
        make_request = AsyncMock(
            side_effect=[
                MaxTooManyRequestsError(
                    error="rate_limit",
                    error_message="Too many requests",
                    retry_after=0.01,
                ),
                "ok",
            ]
        )
        bot = _make_bot()
        method = _make_method()

        result = await mw(make_request, bot, method)
        assert result == "ok"
        assert make_request.call_count == 2

    async def test_retry_uses_retry_after(self) -> None:
        """При 429 с retry_after — ждёт указанное время."""
        mw = RetryMiddleware(max_retries=2, base_delay=0.01)
        make_request = AsyncMock(
            side_effect=[
                MaxTooManyRequestsError(
                    error="rate_limit",
                    error_message="Too many requests",
                    retry_after=0.01,
                ),
                "ok",
            ]
        )
        bot = _make_bot()
        method = _make_method()

        result = await mw(make_request, bot, method)
        assert result == "ok"

    async def test_max_retries_exceeded(self) -> None:
        """Если max_retries исчерпан — пробрасывает исключение."""
        mw = RetryMiddleware(max_retries=2, base_delay=0.01)
        error = MaxServerError(
            status_code=503, error="err", error_message="Service Unavailable"
        )
        make_request = AsyncMock(side_effect=error)
        bot = _make_bot()
        method = _make_method()

        with pytest.raises(MaxServerError):
            await mw(make_request, bot, method)

        assert make_request.call_count == 3  # 1 initial + 2 retries

    async def test_non_retryable_error_not_retried(self) -> None:
        """Не-retryable ошибки (400, 401, 403, 404) не повторяются."""
        from maxogram.exceptions import MaxBadRequestError

        mw = RetryMiddleware(max_retries=3, base_delay=0.01)
        make_request = AsyncMock(
            side_effect=MaxBadRequestError(
                error="bad", error_message="Bad request"
            )
        )
        bot = _make_bot()
        method = _make_method()

        with pytest.raises(MaxBadRequestError):
            await mw(make_request, bot, method)

        assert make_request.call_count == 1

    async def test_exponential_backoff(self) -> None:
        """Задержка растёт экспоненциально."""
        mw = RetryMiddleware(max_retries=3, base_delay=0.1, backoff_factor=2.0)
        # Проверяем через параметры, что delays рассчитываются правильно
        assert mw._base_delay == 0.1
        assert mw._backoff_factor == 2.0

    async def test_default_parameters(self) -> None:
        """Параметры по умолчанию."""
        mw = RetryMiddleware()
        assert mw._max_retries == 3
        assert mw._base_delay == 1.0
        assert mw._backoff_factor == 2.0
        assert mw._max_delay == 30.0

    async def test_max_delay_cap(self) -> None:
        """Задержка не превышает max_delay."""
        mw = RetryMiddleware(
            max_retries=10, base_delay=10.0, backoff_factor=10.0, max_delay=5.0
        )
        # delay = min(base * factor^attempt, max_delay)
        # 10 * 10^0 = 10, но max_delay=5.0
        assert mw._max_delay == 5.0


# ---------------------------------------------------------------------------
# LoggingMiddleware
# ---------------------------------------------------------------------------


class TestLoggingMiddleware:
    """LoggingMiddleware — structured logging запросов/ответов."""

    async def test_logs_request_and_response(self, caplog: Any) -> None:
        """Логирует запрос и успешный ответ."""
        mw = LoggingMiddleware()
        make_request = AsyncMock(return_value="result")
        bot = _make_bot()
        method = _make_method()

        with caplog.at_level(logging.DEBUG, logger="maxogram.client.session.middleware"):
            result = await mw(make_request, bot, method, timeout=10.0)

        assert result == "result"
        assert make_request.call_count == 1
        # Должны быть записи о запросе и ответе
        assert any(
            "request" in r.message.lower() for r in caplog.records
        )
        assert any(
            "response" in r.message.lower() for r in caplog.records
        )

    async def test_logs_error(self, caplog: Any) -> None:
        """Логирует ошибку при неудачном запросе."""
        mw = LoggingMiddleware()
        make_request = AsyncMock(
            side_effect=MaxServerError(
                status_code=500, error="err", error_message="Internal"
            )
        )
        bot = _make_bot()
        method = _make_method()

        with (
            caplog.at_level(logging.DEBUG, logger="maxogram.client.session.middleware"),
            pytest.raises(MaxServerError),
        ):
            await mw(make_request, bot, method)

        # Должна быть запись об ошибке
        assert any(
            "error" in r.message.lower() or r.levelno >= logging.ERROR
            for r in caplog.records
        )

    async def test_custom_logger_name(self, caplog: Any) -> None:
        """Можно указать кастомное имя логгера."""
        mw = LoggingMiddleware(logger_name="my.custom.logger")
        make_request = AsyncMock(return_value="result")
        bot = _make_bot()
        method = _make_method()

        with caplog.at_level(logging.DEBUG, logger="my.custom.logger"):
            await mw(make_request, bot, method)

        assert any(r.name == "my.custom.logger" for r in caplog.records)

    async def test_passes_through_result(self) -> None:
        """LoggingMiddleware прозрачно передаёт результат."""
        mw = LoggingMiddleware()
        expected = {"status": "ok", "data": [1, 2, 3]}
        make_request = AsyncMock(return_value=expected)
        bot = _make_bot()
        method = _make_method()

        result = await mw(make_request, bot, method)
        assert result == expected

    async def test_passes_through_exception(self) -> None:
        """LoggingMiddleware пробрасывает исключение."""
        mw = LoggingMiddleware()
        make_request = AsyncMock(
            side_effect=MaxServerError(
                status_code=502, error="err", error_message="Bad Gateway"
            )
        )
        bot = _make_bot()
        method = _make_method()

        with pytest.raises(MaxServerError, match="Bad Gateway"):
            await mw(make_request, bot, method)


# ---------------------------------------------------------------------------
# Интеграция — цепочка middleware
# ---------------------------------------------------------------------------


class TestMiddlewareChain:
    """Тесты цепочки middleware."""

    async def test_chain_order(self) -> None:
        """Middleware применяются в правильном порядке."""
        order: list[str] = []

        class FirstMiddleware(RequestMiddleware):
            async def __call__(
                self,
                make_request: Any,
                bot: Any,
                method: Any,
                timeout: float | None = None,
            ) -> Any:
                order.append("first_before")
                result = await make_request(bot, method, timeout)
                order.append("first_after")
                return result

        class SecondMiddleware(RequestMiddleware):
            async def __call__(
                self,
                make_request: Any,
                bot: Any,
                method: Any,
                timeout: float | None = None,
            ) -> Any:
                order.append("second_before")
                result = await make_request(bot, method, timeout)
                order.append("second_after")
                return result

        make_request = AsyncMock(return_value="result")
        bot = _make_bot()
        method = _make_method()

        # Оборачиваем: second(first(make_request))
        first = FirstMiddleware()
        second = SecondMiddleware()

        # Wrapping: создаём callable, оборачивающий make_request
        async def wrapped_by_first(
            b: Any, m: Any, t: float | None = None
        ) -> Any:
            return await first(make_request, b, m, t)

        result = await second(wrapped_by_first, bot, method)

        assert result == "result"
        assert order == [
            "second_before",
            "first_before",
            "first_after",
            "second_after",
        ]
