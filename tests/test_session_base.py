"""Тесты BaseSession ABC — check_response, __init__, __call__."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import AsyncMock

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

import pytest

from maxogram.client.server import MaxAPIServer
from maxogram.client.session.base import BaseSession
from maxogram.exceptions import (
    ClientDecodeError,
    MaxAPIError,
    MaxBadRequestError,
    MaxForbiddenError,
    MaxNotFoundError,
    MaxServerError,
    MaxTooManyRequestsError,
    MaxUnauthorizedError,
)
from maxogram.methods.base import MaxMethod
from maxogram.types.misc import SimpleQueryResult
from maxogram.types.user import BotInfo

# --- Concrete реализация для тестирования ABC ---


class ConcreteSession(BaseSession):
    """Минимальный наследник BaseSession для тестирования."""

    async def make_request(
        self,
        bot: Any,
        method: MaxMethod[Any],
        timeout: float | None = None,
    ) -> Any:
        raise NotImplementedError

    async def stream_content(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        chunk_size: int = 65536,
    ) -> AsyncGenerator[bytes, None]:
        yield b""

    async def close(self) -> None:
        pass


# --- Фиктивный метод для тестов ---


class FakeMethodSimple(MaxMethod["SimpleQueryResult"]):
    """Фиктивный метод, возвращающий SimpleQueryResult."""

    __api_path__: ClassVar[str] = "/test"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SimpleQueryResult


class FakeMethodBotInfo(MaxMethod["BotInfo"]):
    """Фиктивный метод, возвращающий BotInfo."""

    __api_path__: ClassVar[str] = "/me"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = BotInfo


# --- Тесты __init__ ---


class TestBaseSessionInit:
    """Тесты инициализации BaseSession."""

    def test_defaults(self) -> None:
        """API по умолчанию, timeout 60, стандартные json_loads/dumps."""
        session = ConcreteSession()
        assert isinstance(session.api, MaxAPIServer)
        assert session.api.base_url == "https://platform-api.max.ru"
        assert session.timeout == 60.0
        assert session._json_loads is json.loads
        assert session._json_dumps is json.dumps

    def test_custom_api(self) -> None:
        """Можно передать кастомный MaxAPIServer."""
        api = MaxAPIServer(base_url="http://localhost:9999")
        session = ConcreteSession(api=api)
        assert session.api.base_url == "http://localhost:9999"

    def test_custom_timeout(self) -> None:
        """Кастомный timeout."""
        session = ConcreteSession(timeout=30.0)
        assert session.timeout == 30.0

    def test_custom_json_loads_dumps(self) -> None:
        """Кастомные json_loads/json_dumps."""

        def custom_loads(s: str) -> Any:
            return json.loads(s)

        def custom_dumps(obj: Any) -> str:
            return json.dumps(obj, indent=2)

        session = ConcreteSession(
            json_loads=custom_loads,
            json_dumps=custom_dumps,
        )
        assert session._json_loads is custom_loads
        assert session._json_dumps is custom_dumps


# --- Тесты check_response: success ---


class TestCheckResponseSuccess:
    """Тесты check_response при успешном ответе (200)."""

    def test_simple_query_result(self) -> None:
        """200 + {"success": true} → SimpleQueryResult(success=True)."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = json.dumps({"success": True})

        result = session.check_response(method, 200, content)

        assert isinstance(result, SimpleQueryResult)
        assert result.success is True

    def test_simple_query_result_with_message(self) -> None:
        """200 + {"success": true, "message": "ok"} → SimpleQueryResult."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = json.dumps({"success": True, "message": "ok"})

        result = session.check_response(method, 200, content)

        assert isinstance(result, SimpleQueryResult)
        assert result.success is True
        assert result.message == "ok"

    def test_bot_info(self) -> None:
        """200 + BotInfo JSON → BotInfo с правильными полями."""
        session = ConcreteSession()
        method = FakeMethodBotInfo()
        content = json.dumps(
            {
                "user_id": 1,
                "name": "TestBot",
                "is_bot": True,
                "last_activity_time": 1700000000,
            }
        )

        result = session.check_response(method, 200, content)

        assert isinstance(result, BotInfo)
        assert result.user_id == 1
        assert result.name == "TestBot"
        assert result.is_bot is True


# --- Тесты check_response: ошибки ---


class TestCheckResponseErrors:
    """Тесты check_response при ошибках (4xx/5xx)."""

    def _error_json(
        self,
        error: str = "error.code",
        message: str = "Something went wrong",
        **extra: Any,
    ) -> str:
        data: dict[str, Any] = {"error": error, "message": message}
        data.update(extra)
        return json.dumps(data)

    def test_400_bad_request(self) -> None:
        """400 → MaxBadRequestError."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = self._error_json(error="validation.error", message="Invalid param")

        with pytest.raises(MaxBadRequestError) as exc_info:
            session.check_response(method, 400, content)

        assert exc_info.value.status_code == 400
        assert exc_info.value.error == "validation.error"
        assert exc_info.value.error_message == "Invalid param"

    def test_401_unauthorized(self) -> None:
        """401 → MaxUnauthorizedError."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = self._error_json(error="auth.error", message="Invalid token")

        with pytest.raises(MaxUnauthorizedError) as exc_info:
            session.check_response(method, 401, content)

        assert exc_info.value.status_code == 401

    def test_403_forbidden(self) -> None:
        """403 → MaxForbiddenError."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = self._error_json(error="access.denied", message="Forbidden")

        with pytest.raises(MaxForbiddenError) as exc_info:
            session.check_response(method, 403, content)

        assert exc_info.value.status_code == 403

    def test_404_not_found(self) -> None:
        """404 → MaxNotFoundError."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = self._error_json(error="not.found", message="Chat not found")

        with pytest.raises(MaxNotFoundError) as exc_info:
            session.check_response(method, 404, content)

        assert exc_info.value.status_code == 404
        assert exc_info.value.error_message == "Chat not found"

    def test_429_too_many_requests_with_retry_after(self) -> None:
        """429 → MaxTooManyRequestsError с retry_after."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = self._error_json(
            error="rate.limit",
            message="Too many requests",
            retry_after=2.5,
        )

        with pytest.raises(MaxTooManyRequestsError) as exc_info:
            session.check_response(method, 429, content)

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 2.5

    def test_429_without_retry_after(self) -> None:
        """429 без retry_after → retry_after=None."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = self._error_json(error="rate.limit", message="Too many requests")

        with pytest.raises(MaxTooManyRequestsError) as exc_info:
            session.check_response(method, 429, content)

        assert exc_info.value.retry_after is None

    def test_500_server_error(self) -> None:
        """500 → MaxServerError."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = self._error_json(error="internal", message="Internal Server Error")

        with pytest.raises(MaxServerError) as exc_info:
            session.check_response(method, 500, content)

        assert exc_info.value.status_code == 500

    def test_502_server_error(self) -> None:
        """502 → MaxServerError(status_code=502)."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = self._error_json(error="gateway", message="Bad Gateway")

        with pytest.raises(MaxServerError) as exc_info:
            session.check_response(method, 502, content)

        assert exc_info.value.status_code == 502

    def test_418_unknown_4xx(self) -> None:
        """418 (неизвестный 4xx) → MaxAPIError."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = self._error_json(error="teapot", message="I'm a teapot")

        with pytest.raises(MaxAPIError) as exc_info:
            session.check_response(method, 418, content)

        # Должен быть именно MaxAPIError, не подклассы
        assert type(exc_info.value) is MaxAPIError
        assert exc_info.value.status_code == 418

    def test_invalid_json(self) -> None:
        """Невалидный JSON → ClientDecodeError."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = "not valid json {{"

        with pytest.raises(ClientDecodeError) as exc_info:
            session.check_response(method, 200, content)

        assert exc_info.value.original_error is not None
        assert "not valid json" in str(exc_info.value)

    def test_error_with_no_error_field(self) -> None:
        """Ответ ошибки без поля error → error=None."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = json.dumps({"message": "Bad request"})

        with pytest.raises(MaxBadRequestError) as exc_info:
            session.check_response(method, 400, content)

        assert exc_info.value.error is None
        assert exc_info.value.error_message == "Bad request"

    def test_error_with_no_message_field(self) -> None:
        """Ответ ошибки без поля message → 'Unknown error'."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = json.dumps({"error": "some.error"})

        with pytest.raises(MaxBadRequestError) as exc_info:
            session.check_response(method, 400, content)

        assert exc_info.value.error_message == "Unknown error"

    def test_error_code_parsed(self) -> None:
        """Поле code из ответа API сохраняется в исключении."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = json.dumps(
            {
                "error": "validation.error",
                "code": "invalid.param",
                "message": "Bad param",
            }
        )

        with pytest.raises(MaxBadRequestError) as exc_info:
            session.check_response(method, 400, content)

        assert exc_info.value.code == "invalid.param"

    def test_error_code_none_when_missing(self) -> None:
        """Если code отсутствует в ответе → None."""
        session = ConcreteSession()
        method = FakeMethodSimple()
        content = json.dumps({"error": "err", "message": "msg"})

        with pytest.raises(MaxBadRequestError) as exc_info:
            session.check_response(method, 400, content)

        assert exc_info.value.code is None


# --- Тест __call__ ---


class TestBaseSessionCall:
    """Тест __call__ — делегирует в make_request."""

    async def test_call_delegates_to_make_request(self) -> None:
        """__call__ вызывает make_request с теми же аргументами."""
        session = ConcreteSession()
        session.make_request = AsyncMock(return_value="result")  # type: ignore[method-assign]

        bot = object()
        method = FakeMethodSimple()

        result = await session(bot, method, timeout=10.0)

        assert result == "result"
        session.make_request.assert_awaited_once_with(bot, method, 10.0)
