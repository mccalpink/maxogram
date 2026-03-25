"""Тесты AiohttpSession — HTTP-клиент на aiohttp."""

from __future__ import annotations

import json

import aresponses
import pytest

from maxogram.client.session.aiohttp import AiohttpSession
from maxogram.enums import UploadType
from maxogram.exceptions import (
    MaxBadRequestError,
    MaxNetworkError,
    MaxNotFoundError,
    MaxTooManyRequestsError,
)
from maxogram.methods.bot import EditMyInfo, GetMyInfo
from maxogram.methods.chat import GetChat
from maxogram.methods.member import GetMembers
from maxogram.methods.message import DeleteMessage, EditMessage, GetMessages, SendMessage
from maxogram.methods.upload import GetUploadUrl


class MockBot:
    """Мок бота с токеном."""

    token = "test-token-12345"


@pytest.fixture()
def mock_bot() -> MockBot:
    return MockBot()


@pytest.fixture()
def session() -> AiohttpSession:
    return AiohttpSession(max_retries=1)


# --- GET запрос ---


class TestGetRequest:
    """GET /me — GetMyInfo."""

    async def test_get_my_info(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """GET запрос с правильным HTTP-методом и Authorization header."""
        response_data = {
            "user_id": 42,
            "name": "TestBot",
            "is_bot": True,
            "last_activity_time": 1700000000,
        }

        async with aresponses.ResponsesMockServer() as rsps:
            rsps.add(
                "platform-api.max.ru",
                "/me",
                "GET",
                aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                ),
            )

            result = await session.make_request(mock_bot, GetMyInfo())

        assert result.user_id == 42
        assert result.name == "TestBot"
        assert result.is_bot is True
        await session.close()


# --- POST с body ---


class TestPostRequest:
    """POST /messages — SendMessage."""

    async def test_send_message_body_and_query(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """POST: body содержит text, query содержит chat_id."""
        response_data = {
            "message": {
                "sender": {"user_id": 42, "name": "Bot", "is_bot": True, "last_activity_time": 0},
                "recipient": {"chat_id": 123, "chat_type": "chat"},
                "timestamp": 1700000000,
                "body": {"mid": "mid.1", "seq": 1, "text": "Hello"},
            },
        }

        async with aresponses.ResponsesMockServer() as rsps:

            async def handler(request: aresponses.request) -> aresponses.Response:  # type: ignore[name-defined]
                # Проверяем Authorization header
                assert request.headers.get("Authorization") == "test-token-12345"
                # Проверяем query params
                assert "chat_id" in str(request.url.query)
                # Проверяем body содержит text
                body_bytes = await request.read()
                body_data = json.loads(body_bytes)
                assert "text" in body_data
                assert body_data["text"] == "Hello"
                return aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                )

            rsps.add("platform-api.max.ru", "/messages", "POST", handler)

            result = await session.make_request(
                mock_bot,
                SendMessage(chat_id=123, text="Hello"),
            )

        assert result.message.body.text == "Hello"
        await session.close()


# --- Path params ---


class TestPathParams:
    """GET /chats/{chatId} — GetChat."""

    async def test_path_params_substitution(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """Path param chat_id подставляется в URL: /chats/123."""
        response_data = {
            "chat_id": 123,
            "type": "chat",
            "status": "active",
            "last_event_time": 1700000000,
            "participants_count": 5,
            "is_public": False,
        }

        async with aresponses.ResponsesMockServer() as rsps:
            rsps.add(
                "platform-api.max.ru",
                "/chats/123",
                "GET",
                aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                ),
            )

            result = await session.make_request(
                mock_bot,
                GetChat(chat_id=123),
            )

        assert result.chat_id == 123
        await session.close()


# --- Query alias ---


class TestQueryAlias:
    """Тесты alias resolution для query params."""

    async def test_from_alias(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """GetMessages(from_=1000) → query key 'from' (не 'from_')."""
        response_data = {"messages": []}

        async with aresponses.ResponsesMockServer() as rsps:

            def handler(request: aresponses.request) -> aresponses.Response:  # type: ignore[name-defined]
                query_string = str(request.url.query_string)
                # Должен быть "from", не "from_"
                assert "from=1000" in query_string
                assert "from_" not in query_string
                return aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                )

            rsps.add("platform-api.max.ru", "/messages", "GET", handler)

            await session.make_request(
                mock_bot,
                GetMessages(from_=1000),
            )

        await session.close()

    async def test_type_alias(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """GetUploadUrl(type_=UploadType.IMAGE) → query key 'type' (не 'type_')."""
        response_data = {"url": "https://upload.max.ru/file123"}

        async with aresponses.ResponsesMockServer() as rsps:

            def handler(request: aresponses.request) -> aresponses.Response:  # type: ignore[name-defined]
                query_string = str(request.url.query_string)
                # Должен быть "type", не "type_"
                assert "type=image" in query_string
                assert "type_" not in query_string
                return aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                )

            rsps.add("platform-api.max.ru", "/uploads", "POST", handler)

            result = await session.make_request(
                mock_bot,
                GetUploadUrl(type_=UploadType.IMAGE),
            )

        assert result.url == "https://upload.max.ru/file123"
        await session.close()


# --- HTTP methods ---


class TestHttpMethods:
    """Тесты для разных HTTP-методов (DELETE, PUT, PATCH)."""

    async def test_delete_method(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """DELETE /messages — правильный HTTP метод."""
        response_data = {"success": True}

        async with aresponses.ResponsesMockServer() as rsps:
            rsps.add(
                "platform-api.max.ru",
                "/messages",
                "DELETE",
                aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                ),
            )

            result = await session.make_request(
                mock_bot,
                DeleteMessage(message_id="mid.999"),
            )

        assert result.success is True
        await session.close()

    async def test_put_method(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """PUT /messages — EditMessage."""
        response_data = {"success": True}

        async with aresponses.ResponsesMockServer() as rsps:
            rsps.add(
                "platform-api.max.ru",
                "/messages",
                "PUT",
                aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                ),
            )

            result = await session.make_request(
                mock_bot,
                EditMessage(message_id="mid.1", text="Updated"),
            )

        assert result.success is True
        await session.close()

    async def test_patch_method(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """PATCH /me — EditMyInfo."""
        response_data = {
            "user_id": 1,
            "name": "NewName",
            "is_bot": True,
            "last_activity_time": 1700000000,
        }

        async with aresponses.ResponsesMockServer() as rsps:
            rsps.add(
                "platform-api.max.ru",
                "/me",
                "PATCH",
                aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                ),
            )

            result = await session.make_request(
                mock_bot,
                EditMyInfo(name="NewName"),
            )

        assert result.name == "NewName"
        await session.close()


# --- Error handling ---


class TestErrorHandling:
    """Тесты обработки ошибок."""

    async def test_error_400(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """400 → MaxBadRequestError."""
        error_data = {"error": "validation", "message": "Bad param"}

        async with aresponses.ResponsesMockServer() as rsps:
            rsps.add(
                "platform-api.max.ru",
                "/me",
                "GET",
                aresponses.Response(
                    body=json.dumps(error_data),
                    content_type="application/json",
                    status=400,
                ),
            )

            with pytest.raises(MaxBadRequestError):
                await session.make_request(mock_bot, GetMyInfo())

        await session.close()

    async def test_error_404(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """404 → MaxNotFoundError."""
        error_data = {"error": "not.found", "message": "Chat not found"}

        async with aresponses.ResponsesMockServer() as rsps:
            rsps.add(
                "platform-api.max.ru",
                "/chats/999",
                "GET",
                aresponses.Response(
                    body=json.dumps(error_data),
                    content_type="application/json",
                    status=404,
                ),
            )

            with pytest.raises(MaxNotFoundError):
                await session.make_request(mock_bot, GetChat(chat_id=999))

        await session.close()


# --- Retry 429 ---


class TestRetry429:
    """Тесты retry при 429 Too Many Requests."""

    async def test_retry_429_success(
        self,
        mock_bot: MockBot,
    ) -> None:
        """Первый запрос 429 с retry_after, второй 200 → успех."""
        session = AiohttpSession(max_retries=2)
        error_data = {
            "error": "rate.limit",
            "message": "Too many requests",
            "retry_after": 0.01,
        }
        success_data = {"success": True}

        async with aresponses.ResponsesMockServer() as rsps:
            # Первый запрос — 429
            rsps.add(
                "platform-api.max.ru",
                "/messages",
                "DELETE",
                aresponses.Response(
                    body=json.dumps(error_data),
                    content_type="application/json",
                    status=429,
                ),
            )
            # Второй запрос — 200
            rsps.add(
                "platform-api.max.ru",
                "/messages",
                "DELETE",
                aresponses.Response(
                    body=json.dumps(success_data),
                    content_type="application/json",
                ),
            )

            result = await session.make_request(
                mock_bot,
                DeleteMessage(message_id="mid.1"),
            )

        assert result.success is True
        await session.close()

    async def test_retry_429_exhausted(
        self,
        mock_bot: MockBot,
    ) -> None:
        """Все попытки 429 → MaxTooManyRequestsError."""
        session = AiohttpSession(max_retries=1)
        error_data = {
            "error": "rate.limit",
            "message": "Too many requests",
            "retry_after": 0.01,
        }

        async with aresponses.ResponsesMockServer() as rsps:
            # Первый запрос — 429
            rsps.add(
                "platform-api.max.ru",
                "/messages",
                "DELETE",
                aresponses.Response(
                    body=json.dumps(error_data),
                    content_type="application/json",
                    status=429,
                ),
            )
            # Второй запрос — тоже 429
            rsps.add(
                "platform-api.max.ru",
                "/messages",
                "DELETE",
                aresponses.Response(
                    body=json.dumps(error_data),
                    content_type="application/json",
                    status=429,
                ),
            )

            with pytest.raises(MaxTooManyRequestsError):
                await session.make_request(
                    mock_bot,
                    DeleteMessage(message_id="mid.1"),
                )

        await session.close()


# --- Session close ---


class TestSessionClose:
    """Тесты закрытия сессии."""

    async def test_close(self) -> None:
        """close() закрывает внутреннюю aiohttp сессию."""
        session = AiohttpSession()
        # Создаём внутреннюю сессию
        internal = await session._get_session()
        assert not internal.closed
        await session.close()
        assert internal.closed

    async def test_close_without_session(self) -> None:
        """close() без созданной сессии — не падает."""
        session = AiohttpSession()
        await session.close()  # Не должно бросить исключение


# --- GET пустое body ---


class TestEmptyBody:
    """GET не должен отправлять json body."""

    async def test_get_no_body(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """GET /me — json body не отправляется."""
        response_data = {
            "user_id": 1,
            "name": "Bot",
            "is_bot": True,
            "last_activity_time": 0,
        }

        async with aresponses.ResponsesMockServer() as rsps:

            async def handler(request: aresponses.request) -> aresponses.Response:  # type: ignore[name-defined]
                # body должен быть пустым для GET
                body_bytes = await request.read()
                assert body_bytes in (b"", b"null")
                return aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                )

            rsps.add("platform-api.max.ru", "/me", "GET", handler)

            await session.make_request(mock_bot, GetMyInfo())

        await session.close()


# --- List query params ---


class TestListQueryParams:
    """Списочные query params — comma-separated."""

    async def test_user_ids_list(
        self,
        mock_bot: MockBot,
        session: AiohttpSession,
    ) -> None:
        """user_ids=[1,2,3] → 'user_ids=1,2,3' comma-separated."""
        response_data = {"members": [], "marker": None}

        async with aresponses.ResponsesMockServer() as rsps:

            def handler(request: aresponses.request) -> aresponses.Response:  # type: ignore[name-defined]
                query_string = str(request.url.query_string)
                # Проверяем comma-separated
                assert "user_ids=1%2C2%2C3" in query_string or "user_ids=1,2,3" in query_string
                return aresponses.Response(
                    body=json.dumps(response_data),
                    content_type="application/json",
                )

            rsps.add(
                "platform-api.max.ru",
                "/chats/100/members",
                "GET",
                handler,
            )

            await session.make_request(
                mock_bot,
                GetMembers(chat_id=100, user_ids=[1, 2, 3]),
            )

        await session.close()


# --- Network errors ---


class TestNetworkErrors:
    """Тесты сетевых ошибок — timeout, connection refused."""

    async def test_timeout_raises_network_error(
        self,
        mock_bot: MockBot,
    ) -> None:
        """Timeout при запросе → MaxNetworkError."""
        session = AiohttpSession(max_retries=0)

        async with aresponses.ResponsesMockServer() as rsps:

            async def slow_handler(request: aresponses.request) -> aresponses.Response:  # type: ignore[name-defined]
                import asyncio

                await asyncio.sleep(10)
                return aresponses.Response(body="{}", content_type="application/json")

            rsps.add("platform-api.max.ru", "/me", "GET", slow_handler)

            with pytest.raises(MaxNetworkError) as exc_info:
                await session.make_request(mock_bot, GetMyInfo(), timeout=0.01)

            assert exc_info.value.original_error is not None

        await session.close()

    async def test_network_error_preserves_original(
        self,
        mock_bot: MockBot,
    ) -> None:
        """MaxNetworkError хранит original_error для диагностики."""
        session = AiohttpSession(max_retries=0)

        async with aresponses.ResponsesMockServer() as rsps:

            async def slow(request: aresponses.request) -> aresponses.Response:  # type: ignore[name-defined]
                import asyncio

                await asyncio.sleep(10)
                return aresponses.Response(body="{}", content_type="application/json")

            rsps.add("platform-api.max.ru", "/me", "GET", slow)

            with pytest.raises(MaxNetworkError) as exc_info:
                await session.make_request(mock_bot, GetMyInfo(), timeout=0.01)

            err = exc_info.value
            assert err.original_error is not None
            assert "Network error" in str(err)

        await session.close()


# --- Stream content ---


class TestStreamContent:
    """Тесты потокового скачивания stream_content."""

    async def test_stream_content_returns_chunks(self) -> None:
        """stream_content возвращает chunks данных."""
        session = AiohttpSession()
        test_data = b"Hello, this is file content!" * 100

        async with aresponses.ResponsesMockServer() as rsps:
            rsps.add(
                "example.com",
                "/file.bin",
                "GET",
                aresponses.Response(body=test_data, content_type="application/octet-stream"),
            )

            chunks: list[bytes] = []
            async for chunk in session.stream_content(
                "http://example.com/file.bin",
                chunk_size=256,
            ):
                chunks.append(chunk)

        result = b"".join(chunks)
        assert result == test_data
        await session.close()

    async def test_stream_content_timeout_raises_network_error(self) -> None:
        """Timeout при stream_content → MaxNetworkError."""
        session = AiohttpSession()

        async with aresponses.ResponsesMockServer() as rsps:

            async def slow_handler(request: aresponses.request) -> aresponses.Response:  # type: ignore[name-defined]
                import asyncio

                await asyncio.sleep(10)
                return aresponses.Response(body=b"data", content_type="application/octet-stream")

            rsps.add("example.com", "/file.bin", "GET", slow_handler)

            with pytest.raises(MaxNetworkError):
                async for _ in session.stream_content(
                    "http://example.com/file.bin",
                    timeout=0.01,
                ):
                    pass

        await session.close()

    async def test_stream_content_with_headers(self) -> None:
        """stream_content передаёт custom headers."""
        session = AiohttpSession()

        async with aresponses.ResponsesMockServer() as rsps:

            async def handler(request: aresponses.request) -> aresponses.Response:  # type: ignore[name-defined]
                assert request.headers.get("X-Custom") == "test-value"
                return aresponses.Response(body=b"ok", content_type="application/octet-stream")

            rsps.add("example.com", "/file.bin", "GET", handler)

            chunks: list[bytes] = []
            async for chunk in session.stream_content(
                "http://example.com/file.bin",
                headers={"X-Custom": "test-value"},
            ):
                chunks.append(chunk)

        assert b"".join(chunks) == b"ok"
        await session.close()
