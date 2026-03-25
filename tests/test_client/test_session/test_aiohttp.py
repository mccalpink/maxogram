"""Тесты AiohttpSession — HTTP-запросы к Max API."""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from maxogram.client.session.aiohttp import AiohttpSession
from maxogram.methods.base import MaxMethod
from maxogram.types.misc import SimpleQueryResult

# --- Тестовые методы ---


class PostEmptyMethod(MaxMethod["SimpleQueryResult"]):
    """POST-метод, у которого все поля — query params → body пустой."""

    __api_path__: ClassVar[str] = "/answers"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SimpleQueryResult
    __query_params__: ClassVar[frozenset[str]] = frozenset({"callback_id"})

    callback_id: str


class GetEmptyMethod(MaxMethod["SimpleQueryResult"]):
    """GET-метод с пустым body."""

    __api_path__: ClassVar[str] = "/chats"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = SimpleQueryResult
    __query_params__: ClassVar[frozenset[str]] = frozenset()


# --- Тесты ---


class TestAiohttpSessionEmptyBody:
    """POST с пустым body отправляет json={}, GET — json=None."""

    @pytest.mark.asyncio
    async def test_post_empty_body_sends_empty_dict(self) -> None:
        """POST с пустым body (все поля в query) → json={}."""
        session = AiohttpSession()
        bot = MagicMock()
        bot.token = "test_token"
        method = PostEmptyMethod(callback_id="cb_123")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"success": true}')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.request = MagicMock(return_value=mock_response)

        with patch.object(session, "_get_session", return_value=mock_session):
            await session._do_request(bot, method)

        # Проверяем что json={} а не None
        call_kwargs = mock_session.request.call_args
        assert call_kwargs.kwargs["json"] == {}

    @pytest.mark.asyncio
    async def test_get_empty_body_sends_none(self) -> None:
        """GET с пустым body → json=None."""
        session = AiohttpSession()
        bot = MagicMock()
        bot.token = "test_token"
        method = GetEmptyMethod()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"success": true}')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.request = MagicMock(return_value=mock_response)

        with patch.object(session, "_get_session", return_value=mock_session):
            await session._do_request(bot, method)

        call_kwargs = mock_session.request.call_args
        assert call_kwargs.kwargs["json"] is None
