"""Тесты для types/chat.py."""

from __future__ import annotations

from maxogram.types import Chat, ChatList, ChatMember, ChatMembersList, ChatPatch

CHAT_DATA = {
    "chat_id": 222,
    "type": "dialog",
    "status": "active",
    "title": "Тестовый чат",
    "last_event_time": 1711000000000,
    "participants_count": 2,
    "is_public": False,
}


class TestChat:
    def test_create(self) -> None:
        chat = Chat.model_validate(CHAT_DATA)
        assert chat.chat_id == 222
        assert chat.type == "dialog"
        assert chat.status == "active"
        assert chat.participants_count == 2
        assert chat.is_public is False

    def test_optional_fields(self) -> None:
        chat = Chat.model_validate(CHAT_DATA)
        assert chat.owner_id is None
        assert chat.link is None
        assert chat.description is None
        assert chat.pinned_message is None

    def test_round_trip(self) -> None:
        chat = Chat.model_validate(CHAT_DATA)
        dumped = chat.model_dump()
        chat2 = Chat.model_validate(dumped)
        assert chat2.chat_id == chat.chat_id


class TestChatMember:
    def test_create(self) -> None:
        data = {
            "user_id": 111,
            "name": "Иван",
            "is_bot": False,
            "last_activity_time": 1711000000000,
            "last_access_time": 1711000000000,
            "is_owner": True,
            "is_admin": True,
            "join_time": 1710000000000,
            "permissions": ["read_all_messages", "add_remove_members"],
        }
        member = ChatMember.model_validate(data)
        assert member.is_owner is True
        assert member.is_admin is True
        assert member.permissions is not None
        assert len(member.permissions) == 2


class TestChatPatch:
    def test_all_optional(self) -> None:
        patch = ChatPatch()
        assert patch.title is None
        assert patch.icon is None


class TestChatList:
    def test_create(self) -> None:
        data = {
            "chats": [CHAT_DATA],
            "marker": 123,
        }
        chat_list = ChatList.model_validate(data)
        assert len(chat_list.chats) == 1
        assert chat_list.marker == 123


class TestChatMembersList:
    def test_create(self) -> None:
        data = {
            "members": [
                {
                    "user_id": 111,
                    "name": "Иван",
                    "is_bot": False,
                    "last_activity_time": 1711000000000,
                    "last_access_time": 1711000000000,
                    "is_owner": False,
                    "is_admin": False,
                    "join_time": 1710000000000,
                }
            ],
            "marker": None,
        }
        members = ChatMembersList.model_validate(data)
        assert len(members.members) == 1
        assert members.marker is None
