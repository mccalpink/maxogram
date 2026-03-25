"""HTTP-сессия на aiohttp для Max Bot API."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiohttp

from maxogram.client.session.base import BaseSession
from maxogram.exceptions import MaxNetworkError, MaxTooManyRequestsError

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from maxogram.methods.base import MaxMethod

__all__ = ["AiohttpSession"]


class AiohttpSession(BaseSession):
    """Default HTTP-сессия на aiohttp.

    Поддержка:
    - Lazy создание ClientSession
    - Retry при 429 (Too Many Requests)
    - Proxy
    - Потоковое скачивание (stream_content)
    """

    def __init__(
        self,
        proxy: str | None = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._proxy = proxy
        self._max_retries = max_retries
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать aiohttp ClientSession (lazy)."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                json_serialize=self._json_dumps,
            )
        return self._session

    async def make_request(
        self,
        bot: Any,
        method: MaxMethod[Any],
        timeout: float | None = None,
    ) -> Any:
        """Выполнить HTTP-запрос с retry при 429."""
        for attempt in range(self._max_retries + 1):
            try:
                return await self._do_request(bot, method, timeout)
            except MaxTooManyRequestsError as e:
                if attempt == self._max_retries:
                    raise
                wait = e.retry_after or 1.0
                await asyncio.sleep(wait)
        # Unreachable, но для mypy
        msg = "Unreachable"  # pragma: no cover
        raise RuntimeError(msg)  # pragma: no cover

    async def _do_request(
        self,
        bot: Any,
        method: MaxMethod[Any],
        timeout: float | None = None,
    ) -> Any:
        """Основная логика HTTP-запроса."""
        session = await self._get_session()

        # 1. URL с path params
        path = method.__api_path__
        for field_name, api_name in method.__path_params__.items():
            value = getattr(method, field_name)
            path = path.replace(f"{{{api_name}}}", str(value))
        url = self.api.api_url(path)

        # 2. HTTP-метод
        http_method = method.__http_method__

        # 3. Headers
        headers = {"Authorization": bot.token}

        # 4. Query params с alias resolution
        query: dict[str, str | int | float] = {}
        for param in method.__query_params__:
            value = getattr(method, param, None)
            if value is not None:
                # Alias resolution: from_ → "from", type_ → "type"
                field_info = type(method).model_fields.get(param)
                api_key = (
                    field_info.alias
                    if field_info and field_info.alias
                    else param
                )
                # Конвертация значений в типы, поддерживаемые yarl/aiohttp
                if isinstance(value, list):
                    # Списочные параметры — comma-separated
                    query[api_key] = ",".join(str(v) for v in value)
                elif isinstance(value, bool):
                    # bool → строка (до int проверки, т.к. bool наследует int)
                    query[api_key] = str(value).lower()
                elif isinstance(value, (int, float)):
                    query[api_key] = value
                else:
                    query[api_key] = str(value)

        # 5. Body (JSON) — исключаем query и path params
        exclude_fields: set[str] = set(method.__query_params__) | set(method.__path_params__)
        body = method.model_dump(exclude=exclude_fields, exclude_none=True)

        # Пустое body для GET/DELETE — не отправляем json
        # Для POST/PUT/PATCH — отправляем даже пустой dict (иначе 400 Empty request body)
        if body:
            json_body = body
        elif http_method in ("GET", "DELETE", "HEAD"):
            json_body = None
        else:
            json_body = {}

        # 6. Timeout
        request_timeout = aiohttp.ClientTimeout(total=timeout or self.timeout)

        # 7. HTTP-запрос
        try:
            async with session.request(
                method=http_method,
                url=url,
                headers=headers,
                params=query,
                json=json_body,
                proxy=self._proxy,
                timeout=request_timeout,
            ) as response:
                content = await response.text()
                return self.check_response(method, response.status, content)
        except (TimeoutError, aiohttp.ClientError) as e:
            raise MaxNetworkError(
                message=f"Network error: {e}",
                original_error=e,
            ) from e

    async def stream_content(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        chunk_size: int = 65536,
    ) -> AsyncGenerator[bytes, None]:
        """Потоковое скачивание содержимого (для файлов)."""
        session = await self._get_session()
        request_timeout = aiohttp.ClientTimeout(total=timeout)
        try:
            async with session.get(
                url,
                headers=headers,
                timeout=request_timeout,
                proxy=self._proxy,
            ) as response:
                async for chunk in response.content.iter_chunked(chunk_size):
                    yield chunk
        except (TimeoutError, aiohttp.ClientError) as e:
            raise MaxNetworkError(
                message=f"Stream error: {e}",
                original_error=e,
            ) from e

    async def close(self) -> None:
        """Закрыть aiohttp сессию."""
        if self._session and not self._session.closed:
            await self._session.close()
