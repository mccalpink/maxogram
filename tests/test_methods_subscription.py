"""Тесты для methods/subscription.py."""

from __future__ import annotations

from maxogram.methods.subscription import GetSubscriptions, Subscribe, Unsubscribe
from maxogram.types.misc import GetSubscriptionsResult, SimpleQueryResult


class TestGetSubscriptions:
    """Тесты GET /subscriptions — Список подписок."""

    def test_metadata(self) -> None:
        assert GetSubscriptions.__api_path__ == "/subscriptions"
        assert GetSubscriptions.__http_method__ == "GET"
        assert GetSubscriptions.__returning__ is GetSubscriptionsResult
        assert GetSubscriptions.__query_params__ == set()
        assert GetSubscriptions.__path_params__ == {}

    def test_create(self) -> None:
        m = GetSubscriptions()
        assert isinstance(m, GetSubscriptions)

    def test_body_empty(self) -> None:
        """GET без параметров — body пуст."""
        m = GetSubscriptions()
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}


class TestSubscribe:
    """Тесты POST /subscriptions — Создать webhook-подписку."""

    def test_metadata(self) -> None:
        assert Subscribe.__api_path__ == "/subscriptions"
        assert Subscribe.__http_method__ == "POST"
        assert Subscribe.__returning__ is SimpleQueryResult
        assert Subscribe.__query_params__ == set()
        assert Subscribe.__path_params__ == {}

    def test_create(self) -> None:
        m = Subscribe(
            url="https://example.com/webhook",
            update_types=["message_created", "bot_started"],
        )
        assert m.url == "https://example.com/webhook"
        assert m.update_types == ["message_created", "bot_started"]
        assert m.version is None

    def test_create_with_version(self) -> None:
        """Опциональный параметр version."""
        m = Subscribe(
            url="https://example.com/webhook",
            update_types=["message_created"],
            version="0.3.0",
        )
        assert m.version == "0.3.0"

    def test_body_contains_url_and_update_types(self) -> None:
        """Body содержит url, update_types, version."""
        m = Subscribe(
            url="https://example.com/webhook",
            update_types=["message_created"],
            version="0.3.0",
        )
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {
            "url": "https://example.com/webhook",
            "update_types": ["message_created"],
            "version": "0.3.0",
        }

    def test_body_excludes_none_version(self) -> None:
        """Если version=None — не попадает в body."""
        m = Subscribe(
            url="https://example.com/webhook",
            update_types=["message_created"],
        )
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert "version" not in body
        assert body == {
            "url": "https://example.com/webhook",
            "update_types": ["message_created"],
        }


class TestUnsubscribe:
    """Тесты DELETE /subscriptions — Удалить webhook-подписку."""

    def test_metadata(self) -> None:
        assert Unsubscribe.__api_path__ == "/subscriptions"
        assert Unsubscribe.__http_method__ == "DELETE"
        assert Unsubscribe.__returning__ is SimpleQueryResult
        assert Unsubscribe.__query_params__ == {"url"}
        assert Unsubscribe.__path_params__ == {}

    def test_create(self) -> None:
        m = Unsubscribe(url="https://example.com/webhook")
        assert m.url == "https://example.com/webhook"

    def test_query_params_contains_url(self) -> None:
        """url передаётся как query parameter, не в body."""
        assert Unsubscribe.__query_params__ == {"url"}

    def test_body_empty(self) -> None:
        """Body пуст — url уходит в query params."""
        m = Unsubscribe(url="https://example.com/webhook")
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}
