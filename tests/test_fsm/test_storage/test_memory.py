"""Тесты MemoryStorage и DisabledEventIsolation."""

from __future__ import annotations

import pytest

from maxogram.fsm.storage.base import StorageKey
from maxogram.fsm.storage.memory import DisabledEventIsolation, MemoryStorage


def _make_key(
    bot_id: int = 1,
    chat_id: int = 100,
    user_id: int = 42,
) -> StorageKey:
    """Создать тестовый StorageKey."""
    return StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)


class TestMemoryStorageState:
    """MemoryStorage — управление состоянием."""

    @pytest.mark.asyncio
    async def test_get_state_default_none(self) -> None:
        """По умолчанию состояние — None."""
        storage = MemoryStorage()
        key = _make_key()
        assert await storage.get_state(key) is None

    @pytest.mark.asyncio
    async def test_set_get_state(self) -> None:
        """Установка и получение состояния."""
        storage = MemoryStorage()
        key = _make_key()
        await storage.set_state(key, "Form:name")
        assert await storage.get_state(key) == "Form:name"

    @pytest.mark.asyncio
    async def test_set_state_none(self) -> None:
        """Сброс состояния в None."""
        storage = MemoryStorage()
        key = _make_key()
        await storage.set_state(key, "Form:name")
        await storage.set_state(key, None)
        assert await storage.get_state(key) is None

    @pytest.mark.asyncio
    async def test_different_keys_isolated(self) -> None:
        """Разные ключи изолированы друг от друга."""
        storage = MemoryStorage()
        key1 = _make_key(user_id=1)
        key2 = _make_key(user_id=2)

        await storage.set_state(key1, "state1")
        await storage.set_state(key2, "state2")

        assert await storage.get_state(key1) == "state1"
        assert await storage.get_state(key2) == "state2"


class TestMemoryStorageData:
    """MemoryStorage — управление данными."""

    @pytest.mark.asyncio
    async def test_get_data_default_empty(self) -> None:
        """По умолчанию данные — пустой dict."""
        storage = MemoryStorage()
        key = _make_key()
        assert await storage.get_data(key) == {}

    @pytest.mark.asyncio
    async def test_set_get_data(self) -> None:
        """Установка и получение данных."""
        storage = MemoryStorage()
        key = _make_key()
        await storage.set_data(key, {"name": "Alice"})
        assert await storage.get_data(key) == {"name": "Alice"}

    @pytest.mark.asyncio
    async def test_get_data_returns_copy(self) -> None:
        """get_data возвращает копию — мутация не влияет на хранилище."""
        storage = MemoryStorage()
        key = _make_key()
        await storage.set_data(key, {"name": "Alice"})

        data = await storage.get_data(key)
        data["name"] = "Bob"

        assert await storage.get_data(key) == {"name": "Alice"}

    @pytest.mark.asyncio
    async def test_update_data_merge(self) -> None:
        """update_data мержит данные."""
        storage = MemoryStorage()
        key = _make_key()
        await storage.set_data(key, {"a": 1})
        result = await storage.update_data(key, {"b": 2})
        assert result == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_update_data_kwargs(self) -> None:
        """update_data принимает kwargs."""
        storage = MemoryStorage()
        key = _make_key()
        result = await storage.update_data(key, name="Alice", age=30)
        assert result == {"name": "Alice", "age": 30}

    @pytest.mark.asyncio
    async def test_get_value(self) -> None:
        """get_value возвращает одно значение."""
        storage = MemoryStorage()
        key = _make_key()
        await storage.set_data(key, {"name": "Alice", "age": 30})
        assert await storage.get_value(key, "name") == "Alice"

    @pytest.mark.asyncio
    async def test_get_value_default(self) -> None:
        """get_value возвращает default, если ключа нет."""
        storage = MemoryStorage()
        key = _make_key()
        assert await storage.get_value(key, "missing", "fallback") == "fallback"

    @pytest.mark.asyncio
    async def test_get_value_default_none(self) -> None:
        """get_value без default возвращает None."""
        storage = MemoryStorage()
        key = _make_key()
        assert await storage.get_value(key, "missing") is None


class TestMemoryStorageClose:
    """MemoryStorage — close очищает хранилище."""

    @pytest.mark.asyncio
    async def test_close_clears_data(self) -> None:
        """close() очищает все данные и состояния."""
        storage = MemoryStorage()
        key = _make_key()
        await storage.set_state(key, "test")
        await storage.set_data(key, {"x": 1})

        await storage.close()

        assert await storage.get_state(key) is None
        assert await storage.get_data(key) == {}


class TestDisabledEventIsolation:
    """DisabledEventIsolation — no-op lock."""

    @pytest.mark.asyncio
    async def test_lock_noop(self) -> None:
        """lock() выполняется без блокировки."""
        isolation = DisabledEventIsolation()
        key = _make_key()
        executed = False

        async with isolation.lock(key):
            executed = True

        assert executed is True

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """close() не вызывает ошибок."""
        isolation = DisabledEventIsolation()
        await isolation.close()


class TestStorageKey:
    """StorageKey — frozen dataclass."""

    def test_create(self) -> None:
        key = StorageKey(bot_id=1, chat_id=100, user_id=42)
        assert key.bot_id == 1
        assert key.chat_id == 100
        assert key.user_id == 42
        assert key.destiny == "default"

    def test_custom_destiny(self) -> None:
        key = StorageKey(bot_id=1, chat_id=100, user_id=42, destiny="quiz")
        assert key.destiny == "quiz"

    def test_frozen(self) -> None:
        key = StorageKey(bot_id=1, chat_id=100, user_id=42)
        with pytest.raises(AttributeError):
            key.bot_id = 2  # type: ignore[misc]

    def test_equality(self) -> None:
        key1 = StorageKey(bot_id=1, chat_id=100, user_id=42)
        key2 = StorageKey(bot_id=1, chat_id=100, user_id=42)
        assert key1 == key2

    def test_hash(self) -> None:
        key1 = StorageKey(bot_id=1, chat_id=100, user_id=42)
        key2 = StorageKey(bot_id=1, chat_id=100, user_id=42)
        assert hash(key1) == hash(key2)

    def test_different_destiny_not_equal(self) -> None:
        key1 = StorageKey(bot_id=1, chat_id=100, user_id=42, destiny="a")
        key2 = StorageKey(bot_id=1, chat_id=100, user_id=42, destiny="b")
        assert key1 != key2
