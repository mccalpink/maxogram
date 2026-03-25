"""Тесты MaxAPIServer."""

import dataclasses

import pytest

from maxogram.client.server import MaxAPIServer


class TestMaxAPIServer:
    def test_default_base_url(self) -> None:
        server = MaxAPIServer()
        assert server.base_url == "https://platform-api.max.ru"

    def test_api_url(self) -> None:
        server = MaxAPIServer()
        assert server.api_url("/me") == "https://platform-api.max.ru/me"

    def test_api_url_with_path(self) -> None:
        server = MaxAPIServer()
        url = server.api_url("/chats/12345/members")
        assert url == "https://platform-api.max.ru/chats/12345/members"

    def test_custom_base_url(self) -> None:
        server = MaxAPIServer(base_url="http://localhost:8080")
        assert server.api_url("/me") == "http://localhost:8080/me"

    def test_frozen(self) -> None:
        server = MaxAPIServer()
        assert dataclasses.is_dataclass(server)
        with pytest.raises(dataclasses.FrozenInstanceError):
            server.base_url = "http://other"  # type: ignore[misc]

    def test_is_dataclass(self) -> None:
        assert dataclasses.is_dataclass(MaxAPIServer)
