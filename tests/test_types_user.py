"""Тесты для types/user.py."""

from __future__ import annotations

from maxogram.types.user import BotCommand, BotInfo, BotPatch, User, UserWithPhoto

USER_DATA = {
    "user_id": 111,
    "name": "Иван",
    "username": "ivan",
    "is_bot": False,
    "last_activity_time": 1711000000000,
}


class TestUser:
    def test_create(self) -> None:
        user = User.model_validate(USER_DATA)
        assert user.user_id == 111
        assert user.name == "Иван"
        assert user.username == "ivan"
        assert user.is_bot is False
        assert user.last_activity_time == 1711000000000

    def test_username_optional(self) -> None:
        data = {**USER_DATA, "username": None}
        user = User.model_validate(data)
        assert user.username is None

    def test_round_trip(self) -> None:
        user = User.model_validate(USER_DATA)
        dumped = user.model_dump()
        user2 = User.model_validate(dumped)
        assert user2.user_id == user.user_id
        assert user2.name == user.name


class TestUserWithPhoto:
    def test_extends_user(self) -> None:
        data = {
            **USER_DATA,
            "description": "Описание",
            "avatar_url": "https://example.com/avatar.jpg",
            "full_avatar_url": "https://example.com/full.jpg",
        }
        user = UserWithPhoto.model_validate(data)
        assert user.user_id == 111
        assert user.description == "Описание"
        assert user.avatar_url is not None


class TestBotCommand:
    def test_create(self) -> None:
        cmd = BotCommand(name="start", description="Начать")
        assert cmd.name == "start"
        assert cmd.description == "Начать"

    def test_description_optional(self) -> None:
        cmd = BotCommand(name="help")
        assert cmd.description is None


class TestBotInfo:
    def test_with_commands(self) -> None:
        data = {
            **USER_DATA,
            "is_bot": True,
            "commands": [
                {"name": "start", "description": "Начать"},
                {"name": "help"},
            ],
        }
        bot = BotInfo.model_validate(data)
        assert bot.is_bot is True
        assert bot.commands is not None
        assert len(bot.commands) == 2
        assert bot.commands[0].name == "start"


class TestBotPatch:
    def test_all_optional(self) -> None:
        patch = BotPatch()
        assert patch.name is None
        assert patch.description is None
        assert patch.commands is None
        assert patch.photo is None

    def test_with_values(self) -> None:
        patch = BotPatch(name="NewBot", description="Desc")
        assert patch.name == "NewBot"
