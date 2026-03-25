"""Абстрактный базовый класс HTTP-сессии для Max Bot API."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from maxogram.client.server import MaxAPIServer
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

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from maxogram.methods.base import MaxMethod

__all__ = ["BaseSession"]


class BaseSession(ABC):
    """Абстракция HTTP-сессии для Max Bot API.

    Реализации: AiohttpSession (default).
    Пользователи могут написать свою (httpx, curl и т.д.).

    Отличия от aiogram BaseSession:
    1. Поддержка разных HTTP-методов (GET/POST/PUT/PATCH/DELETE)
    2. Authorization через header, не URL
    3. Разделение параметров на path/query/body
    4. JSON body вместо form-data
    """

    def __init__(
        self,
        api: MaxAPIServer | None = None,
        json_loads: Callable[..., Any] = json.loads,
        json_dumps: Callable[..., str] = json.dumps,
        timeout: float = 60.0,
    ) -> None:
        self.api = api or MaxAPIServer()
        self._json_loads = json_loads
        self._json_dumps = json_dumps
        self.timeout = timeout

    @abstractmethod
    async def make_request(
        self,
        bot: Any,
        method: MaxMethod[Any],
        timeout: float | None = None,
    ) -> Any:
        """Выполнить HTTP-запрос к Max Bot API.

        Реализация должна:
        1. Определить HTTP-метод из method.__http_method__
        2. Сформировать URL из method.__api_path__ + path params
        3. Разделить параметры на query и body
        4. Добавить Authorization header
        5. Выполнить запрос
        6. Вернуть десериализованный результат через check_response
        """
        ...

    @abstractmethod
    async def stream_content(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        chunk_size: int = 65536,
    ) -> AsyncGenerator[bytes, None]:
        """Потоковое чтение содержимого (для скачивания файлов)."""
        ...
        yield b""  # pragma: no cover — нужен для AsyncGenerator типизации

    @abstractmethod
    async def close(self) -> None:
        """Закрыть сессию и освободить ресурсы."""
        ...

    def check_response(
        self,
        method: MaxMethod[Any],
        status_code: int,
        content: str,
    ) -> Any:
        """Проверить ответ API, вернуть результат или бросить исключение.

        Max API формат:
        - 200: прямой JSON результат (НЕ обёрнут как в Telegram)
        - 4xx/5xx: {"error": "...", "code": "...", "message": "..."}
        """
        # 1. Parse JSON
        try:
            json_data = self._json_loads(content)
        except Exception as e:
            raise ClientDecodeError(
                f"Failed to parse JSON: {content[:200]}",
                original_error=e,
            ) from e

        # 2. Error mapping
        if status_code >= 400:
            self._raise_for_status(status_code, json_data)

        # 3. Success — deserialize через Pydantic
        returning: type = method.__returning__
        return returning.model_validate(json_data)  # type: ignore[attr-defined]

    def _raise_for_status(
        self,
        status_code: int,
        json_data: Any,
    ) -> None:
        """Преобразовать HTTP-ошибку в соответствующее исключение."""
        error_str: str | None = None
        code: str | None = None
        message = "Unknown error"
        retry_after: float | None = None

        if isinstance(json_data, dict):
            error_str = json_data.get("error")
            code = json_data.get("code")
            message = json_data.get("message", "Unknown error")
            raw_retry = json_data.get("retry_after")
            if raw_retry is not None:
                retry_after = float(raw_retry)

        error_map: dict[int, type[MaxAPIError]] = {
            400: MaxBadRequestError,
            401: MaxUnauthorizedError,
            403: MaxForbiddenError,
            404: MaxNotFoundError,
        }

        if status_code in error_map:
            exc_cls = error_map[status_code]
            raise exc_cls(error=error_str, error_message=message, code=code)  # type: ignore[call-arg]

        if status_code == 429:
            raise MaxTooManyRequestsError(
                error=error_str,
                error_message=message,
                retry_after=retry_after,
                code=code,
            )

        if status_code >= 500:
            raise MaxServerError(
                status_code=status_code,
                error=error_str,
                error_message=message,
                code=code,
            )

        # Неизвестный 4xx
        raise MaxAPIError(
            status_code=status_code,
            error=error_str,
            error_message=message,
            code=code,
        )

    async def __call__(
        self,
        bot: Any,
        method: MaxMethod[Any],
        timeout: float | None = None,
    ) -> Any:
        """Делегирует в make_request. В будущем — точка для middleware."""
        return await self.make_request(bot, method, timeout)
