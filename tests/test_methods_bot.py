"""Тесты для methods/bot.py."""

from __future__ import annotations

from maxogram.methods.bot import EditMyInfo, GetMyInfo
from maxogram.types.user import BotCommand, BotInfo


class TestGetMyInfo:
    """Тесты GET /me — получение информации о боте."""

    def test_metadata(self) -> None:
        assert GetMyInfo.__api_path__ == "/me"
        assert GetMyInfo.__http_method__ == "GET"
        assert GetMyInfo.__returning__ is BotInfo
        assert GetMyInfo.__query_params__ == set()
        assert GetMyInfo.__path_params__ == {}

    def test_create(self) -> None:
        m = GetMyInfo()
        assert isinstance(m, GetMyInfo)

    def test_body_empty(self) -> None:
        """GET без параметров — body пуст."""
        m = GetMyInfo()
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}


class TestEditMyInfo:
    """Тесты PATCH /me — редактирование информации о боте."""

    def test_metadata(self) -> None:
        assert EditMyInfo.__api_path__ == "/me"
        assert EditMyInfo.__http_method__ == "PATCH"
        assert EditMyInfo.__returning__ is BotInfo
        assert EditMyInfo.__query_params__ == set()
        assert EditMyInfo.__path_params__ == {}

    def test_create_empty(self) -> None:
        """Все поля опциональны — можно создать без аргументов."""
        m = EditMyInfo()
        assert m.name is None
        assert m.description is None
        assert m.commands is None
        assert m.photo is None

    def test_create_with_name(self) -> None:
        m = EditMyInfo(name="MyBot")
        assert m.name == "MyBot"

    def test_create_with_commands(self) -> None:
        cmds = [
            BotCommand(name="start", description="Начать"),
            BotCommand(name="help"),
        ]
        m = EditMyInfo(commands=cmds)
        assert m.commands is not None
        assert len(m.commands) == 2
        assert m.commands[0].name == "start"

    def test_create_with_all_fields(self) -> None:
        m = EditMyInfo(
            name="Bot",
            description="Описание",
            commands=[BotCommand(name="start")],
            photo={"url": "https://example.com/photo.jpg"},  # type: ignore[arg-type]
        )
        assert m.name == "Bot"
        assert m.description == "Описание"
        assert m.commands is not None
        assert m.photo is not None

    def test_body_excludes_none(self) -> None:
        """Только заполненные поля попадают в body."""
        m = EditMyInfo(name="Bot")
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {"name": "Bot"}

    def test_body_all_none(self) -> None:
        """Если ничего не задано — body пуст."""
        m = EditMyInfo()
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}

    def test_body_with_commands(self) -> None:
        """Команды сериализуются корректно."""
        m = EditMyInfo(
            commands=[BotCommand(name="start", description="Начать")],
        )
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert "commands" in body
        assert len(body["commands"]) == 1
        assert body["commands"][0]["name"] == "start"
        assert body["commands"][0]["description"] == "Начать"
