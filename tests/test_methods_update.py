"""Тесты для methods/update.py."""

from __future__ import annotations

from maxogram.methods.update import GetUpdates
from maxogram.types.update import GetUpdatesResult


class TestGetUpdates:
    """Тесты GET /updates — Long polling для получения обновлений."""

    def test_metadata(self) -> None:
        assert GetUpdates.__api_path__ == "/updates"
        assert GetUpdates.__http_method__ == "GET"
        assert GetUpdates.__returning__ is GetUpdatesResult
        assert GetUpdates.__query_params__ == {"limit", "timeout", "marker", "types"}
        assert GetUpdates.__path_params__ == {}

    def test_create_empty(self) -> None:
        """Все поля опциональны — можно создать без аргументов."""
        m = GetUpdates()
        assert m.limit is None
        assert m.timeout is None
        assert m.marker is None
        assert m.types is None

    def test_create_with_all_params(self) -> None:
        m = GetUpdates(
            limit=100,
            timeout=30,
            marker=12345,
            types=["message_created", "bot_started"],
        )
        assert m.limit == 100
        assert m.timeout == 30
        assert m.marker == 12345
        assert m.types == ["message_created", "bot_started"]

    def test_create_partial_params(self) -> None:
        """Частичное заполнение — остальные None."""
        m = GetUpdates(limit=50, timeout=10)
        assert m.limit == 50
        assert m.timeout == 10
        assert m.marker is None
        assert m.types is None

    def test_query_params_complete(self) -> None:
        """Все 4 поля — query parameters."""
        assert GetUpdates.__query_params__ == {"limit", "timeout", "marker", "types"}

    def test_body_empty_no_params(self) -> None:
        """Body пуст — все поля в query params (без параметров)."""
        m = GetUpdates()
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}

    def test_body_empty_with_params(self) -> None:
        """Body пуст даже с заполненными полями — всё уходит в query."""
        m = GetUpdates(
            limit=100,
            timeout=30,
            marker=12345,
            types=["message_created"],
        )
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}
