"""Тесты RedisStorage и RedisEventIsolation."""

from __future__ import annotations

import json
from typing import Any

import fakeredis
import pytest

from maxogram.fsm.storage.base import StorageKey
from maxogram.fsm.storage.redis import (
    DefaultKeyBuilder,
    RedisEventIsolation,
    RedisStorage,
)


@pytest.fixture
def redis_client() -> fakeredis.FakeAsyncRedis:
    """Фейковый async Redis-клиент."""
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def storage(redis_client: fakeredis.FakeAsyncRedis) -> RedisStorage:
    """RedisStorage с fakeredis."""
    return RedisStorage(redis=redis_client)


def _make_key(
    bot_id: int = 1,
    chat_id: int = 100,
    user_id: int = 42,
    destiny: str = "default",
) -> StorageKey:
    """Создать тестовый StorageKey."""
    return StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id, destiny=destiny)


# ---------------------------------------------------------------------------
# RedisStorage — управление состоянием
# ---------------------------------------------------------------------------


class TestRedisStorageState:
    """RedisStorage — CRUD операции с состоянием."""

    async def test_get_state_default_none(self, storage: RedisStorage) -> None:
        """По умолчанию состояние — None (ключ не существует)."""
        key = _make_key()
        assert await storage.get_state(key) is None

    async def test_set_get_state(self, storage: RedisStorage) -> None:
        """Установка и получение состояния."""
        key = _make_key()
        await storage.set_state(key, "Form:name")
        assert await storage.get_state(key) == "Form:name"

    async def test_set_state_none_deletes_key(
        self,
        storage: RedisStorage,
        redis_client: fakeredis.FakeAsyncRedis,
    ) -> None:
        """Сброс состояния в None удаляет ключ из Redis."""
        key = _make_key()
        await storage.set_state(key, "Form:name")
        await storage.set_state(key, None)

        assert await storage.get_state(key) is None
        # Ключ действительно удалён из Redis
        redis_key = storage._key_builder.build(key, "state")
        assert await redis_client.exists(redis_key) == 0

    async def test_overwrite_state(self, storage: RedisStorage) -> None:
        """Перезапись состояния."""
        key = _make_key()
        await storage.set_state(key, "Form:step1")
        await storage.set_state(key, "Form:step2")
        assert await storage.get_state(key) == "Form:step2"

    async def test_different_keys_isolated(self, storage: RedisStorage) -> None:
        """Разные StorageKey изолированы."""
        key1 = _make_key(user_id=1)
        key2 = _make_key(user_id=2)

        await storage.set_state(key1, "state1")
        await storage.set_state(key2, "state2")

        assert await storage.get_state(key1) == "state1"
        assert await storage.get_state(key2) == "state2"

    async def test_different_chat_ids_isolated(self, storage: RedisStorage) -> None:
        """Разные chat_id изолированы."""
        key1 = _make_key(chat_id=100)
        key2 = _make_key(chat_id=200)

        await storage.set_state(key1, "state_a")
        await storage.set_state(key2, "state_b")

        assert await storage.get_state(key1) == "state_a"
        assert await storage.get_state(key2) == "state_b"

    async def test_different_destiny_isolated(
        self, redis_client: fakeredis.FakeAsyncRedis
    ) -> None:
        """Разные destiny изолированы (при with_destiny=True)."""
        builder = DefaultKeyBuilder(with_destiny=True)
        storage = RedisStorage(redis=redis_client, key_builder=builder)

        key1 = _make_key(destiny="default")
        key2 = _make_key(destiny="quiz")

        await storage.set_state(key1, "main_state")
        await storage.set_state(key2, "quiz_state")

        assert await storage.get_state(key1) == "main_state"
        assert await storage.get_state(key2) == "quiz_state"


# ---------------------------------------------------------------------------
# RedisStorage — управление данными
# ---------------------------------------------------------------------------


class TestRedisStorageData:
    """RedisStorage — CRUD операции с данными."""

    async def test_get_data_default_empty(self, storage: RedisStorage) -> None:
        """По умолчанию данные — пустой dict."""
        key = _make_key()
        assert await storage.get_data(key) == {}

    async def test_set_get_data(self, storage: RedisStorage) -> None:
        """Установка и получение данных."""
        key = _make_key()
        await storage.set_data(key, {"name": "Alice", "age": 30})
        assert await storage.get_data(key) == {"name": "Alice", "age": 30}

    async def test_set_empty_data_deletes_key(
        self,
        storage: RedisStorage,
        redis_client: fakeredis.FakeAsyncRedis,
    ) -> None:
        """Установка пустых данных удаляет ключ из Redis."""
        key = _make_key()
        await storage.set_data(key, {"name": "Alice"})
        await storage.set_data(key, {})

        assert await storage.get_data(key) == {}
        redis_key = storage._key_builder.build(key, "data")
        assert await redis_client.exists(redis_key) == 0

    async def test_set_data_replaces_completely(self, storage: RedisStorage) -> None:
        """set_data полностью заменяет данные."""
        key = _make_key()
        await storage.set_data(key, {"a": 1, "b": 2})
        await storage.set_data(key, {"c": 3})

        assert await storage.get_data(key) == {"c": 3}

    async def test_update_data_merge(self, storage: RedisStorage) -> None:
        """update_data мержит данные."""
        key = _make_key()
        await storage.set_data(key, {"a": 1})
        result = await storage.update_data(key, {"b": 2})
        assert result == {"a": 1, "b": 2}

    async def test_update_data_kwargs(self, storage: RedisStorage) -> None:
        """update_data принимает kwargs."""
        key = _make_key()
        result = await storage.update_data(key, name="Alice", age=30)
        assert result == {"name": "Alice", "age": 30}

    async def test_update_data_overwrites_existing(self, storage: RedisStorage) -> None:
        """update_data перезаписывает существующие ключи."""
        key = _make_key()
        await storage.set_data(key, {"name": "Alice"})
        result = await storage.update_data(key, {"name": "Bob", "age": 25})
        assert result == {"name": "Bob", "age": 25}

    async def test_get_value(self, storage: RedisStorage) -> None:
        """get_value возвращает одно значение."""
        key = _make_key()
        await storage.set_data(key, {"name": "Alice", "age": 30})
        assert await storage.get_value(key, "name") == "Alice"

    async def test_get_value_default(self, storage: RedisStorage) -> None:
        """get_value возвращает default, если ключа нет."""
        key = _make_key()
        assert await storage.get_value(key, "missing", "fallback") == "fallback"

    async def test_get_value_default_none(self, storage: RedisStorage) -> None:
        """get_value без default возвращает None."""
        key = _make_key()
        assert await storage.get_value(key, "missing") is None

    async def test_data_serialization_complex(self, storage: RedisStorage) -> None:
        """Сериализация/десериализация сложных данных (JSON-совместимые)."""
        key = _make_key()
        complex_data: dict[str, Any] = {
            "name": "Alice",
            "items": [1, 2, 3],
            "nested": {"x": True, "y": None},
            "count": 42,
        }
        await storage.set_data(key, complex_data)
        assert await storage.get_data(key) == complex_data

    async def test_different_keys_data_isolated(self, storage: RedisStorage) -> None:
        """Данные разных ключей изолированы."""
        key1 = _make_key(user_id=1)
        key2 = _make_key(user_id=2)

        await storage.set_data(key1, {"user": "Alice"})
        await storage.set_data(key2, {"user": "Bob"})

        assert await storage.get_data(key1) == {"user": "Alice"}
        assert await storage.get_data(key2) == {"user": "Bob"}


# ---------------------------------------------------------------------------
# RedisStorage — close
# ---------------------------------------------------------------------------


class TestRedisStorageClose:
    """RedisStorage — close закрывает Redis-соединение."""

    async def test_close(self, storage: RedisStorage) -> None:
        """close() не вызывает ошибок."""
        await storage.close()


# ---------------------------------------------------------------------------
# RedisStorage — from_url
# ---------------------------------------------------------------------------


class TestRedisStorageFromUrl:
    """RedisStorage.from_url — конструктор из URL."""

    async def test_from_url_creates_storage(self) -> None:
        """from_url создаёт RedisStorage с Redis-клиентом."""
        storage = RedisStorage.from_url("redis://localhost:6379/0")
        assert isinstance(storage, RedisStorage)
        assert storage._redis is not None
        # Закрываем без реального подключения
        await storage.close()

    async def test_from_url_with_kwargs(self) -> None:
        """from_url передаёт kwargs (state_ttl, data_ttl, key_builder)."""
        builder = DefaultKeyBuilder(prefix="test")
        storage = RedisStorage.from_url(
            "redis://localhost:6379/0",
            key_builder=builder,
            state_ttl=60,
            data_ttl=120,
        )
        assert storage._state_ttl == 60
        assert storage._data_ttl == 120
        assert storage._key_builder is builder
        await storage.close()


# ---------------------------------------------------------------------------
# RedisStorage — TTL
# ---------------------------------------------------------------------------


class TestRedisStorageTTL:
    """RedisStorage — TTL для state и data."""

    async def test_state_ttl(self, redis_client: fakeredis.FakeAsyncRedis) -> None:
        """state_ttl устанавливает TTL для ключей состояния."""
        storage = RedisStorage(redis=redis_client, state_ttl=300)
        key = _make_key()
        await storage.set_state(key, "Form:name")

        redis_key = storage._key_builder.build(key, "state")
        ttl = await redis_client.ttl(redis_key)
        assert ttl > 0
        assert ttl <= 300

    async def test_data_ttl(self, redis_client: fakeredis.FakeAsyncRedis) -> None:
        """data_ttl устанавливает TTL для ключей данных."""
        storage = RedisStorage(redis=redis_client, data_ttl=600)
        key = _make_key()
        await storage.set_data(key, {"name": "Alice"})

        redis_key = storage._key_builder.build(key, "data")
        ttl = await redis_client.ttl(redis_key)
        assert ttl > 0
        assert ttl <= 600

    async def test_no_ttl_by_default(
        self,
        storage: RedisStorage,
        redis_client: fakeredis.FakeAsyncRedis,
    ) -> None:
        """Без TTL ключи не истекают (TTL = -1)."""
        key = _make_key()
        await storage.set_state(key, "Form:name")

        redis_key = storage._key_builder.build(key, "state")
        ttl = await redis_client.ttl(redis_key)
        assert ttl == -1  # no expiration


# ---------------------------------------------------------------------------
# DefaultKeyBuilder
# ---------------------------------------------------------------------------


class TestDefaultKeyBuilder:
    """DefaultKeyBuilder — построение Redis-ключей."""

    def test_default_build(self) -> None:
        """Формат по умолчанию: maxogram:state:{bot_id}:{chat_id}:{user_id}."""
        builder = DefaultKeyBuilder()
        key = _make_key(bot_id=1, chat_id=100, user_id=42)
        result = builder.build(key, "state")
        assert result == "maxogram:state:1:100:42"

    def test_build_data_part(self) -> None:
        """Часть 'data' в ключе."""
        builder = DefaultKeyBuilder()
        key = _make_key()
        result = builder.build(key, "data")
        assert result == "maxogram:data:1:100:42"

    def test_build_lock_part(self) -> None:
        """Часть 'lock' в ключе."""
        builder = DefaultKeyBuilder()
        key = _make_key()
        result = builder.build(key, "lock")
        assert result == "maxogram:lock:1:100:42"

    def test_custom_prefix(self) -> None:
        """Кастомный prefix."""
        builder = DefaultKeyBuilder(prefix="mybot")
        key = _make_key()
        result = builder.build(key, "state")
        assert result == "mybot:state:1:100:42"

    def test_custom_separator(self) -> None:
        """Кастомный separator."""
        builder = DefaultKeyBuilder(separator=".")
        key = _make_key()
        result = builder.build(key, "state")
        assert result == "maxogram.state.1.100.42"

    def test_with_bot_id_false(self) -> None:
        """with_bot_id=False — без bot_id в ключе."""
        builder = DefaultKeyBuilder(with_bot_id=False)
        key = _make_key(bot_id=1, chat_id=100, user_id=42)
        result = builder.build(key, "state")
        assert result == "maxogram:state:100:42"

    def test_with_destiny(self) -> None:
        """with_destiny=True — destiny добавляется в ключ."""
        builder = DefaultKeyBuilder(with_destiny=True)
        key = _make_key(destiny="quiz")
        result = builder.build(key, "state")
        assert result == "maxogram:state:1:100:42:quiz"

    def test_with_destiny_default_not_included(self) -> None:
        """По умолчанию destiny не включается."""
        builder = DefaultKeyBuilder()
        key = _make_key(destiny="quiz")
        result = builder.build(key, "state")
        assert result == "maxogram:state:1:100:42"

    def test_no_part(self) -> None:
        """Без part — ключ без суффикса."""
        builder = DefaultKeyBuilder()
        key = _make_key()
        result = builder.build(key, "")
        assert result == "maxogram::1:100:42"


# ---------------------------------------------------------------------------
# RedisEventIsolation
# ---------------------------------------------------------------------------


class TestRedisEventIsolation:
    """RedisEventIsolation — distributed lock через Redis."""

    async def test_lock_executes_body(self, redis_client: fakeredis.FakeAsyncRedis) -> None:
        """lock() выполняет тело контекстного менеджера."""
        isolation = RedisEventIsolation(redis=redis_client)
        key = _make_key()
        executed = False

        async with isolation.lock(key):
            executed = True

        assert executed is True

    async def test_lock_acquires_and_releases(
        self, redis_client: fakeredis.FakeAsyncRedis
    ) -> None:
        """lock() захватывает и освобождает Redis lock."""
        isolation = RedisEventIsolation(redis=redis_client)
        key = _make_key()
        redis_key = isolation._key_builder.build(key, "lock")

        async with isolation.lock(key):
            # Lock должен быть захвачен
            assert await redis_client.exists(redis_key) == 1

        # Lock освобождён
        assert await redis_client.exists(redis_key) == 0

    async def test_close(self, redis_client: fakeredis.FakeAsyncRedis) -> None:
        """close() не вызывает ошибок."""
        isolation = RedisEventIsolation(redis=redis_client)
        await isolation.close()

    async def test_custom_key_builder(self, redis_client: fakeredis.FakeAsyncRedis) -> None:
        """RedisEventIsolation принимает кастомный key_builder."""
        builder = DefaultKeyBuilder(prefix="custom")
        isolation = RedisEventIsolation(redis=redis_client, key_builder=builder)
        key = _make_key()

        async with isolation.lock(key):
            redis_key = builder.build(key, "lock")
            assert await redis_client.exists(redis_key) == 1


# ---------------------------------------------------------------------------
# Интеграция RedisStorage + Redis key format
# ---------------------------------------------------------------------------


class TestRedisStorageKeyFormat:
    """Проверка, что данные реально сохраняются в Redis с правильными ключами."""

    async def test_state_stored_as_string(
        self,
        storage: RedisStorage,
        redis_client: fakeredis.FakeAsyncRedis,
    ) -> None:
        """Состояние хранится как строка в Redis."""
        key = _make_key()
        await storage.set_state(key, "Form:name")

        redis_key = storage._key_builder.build(key, "state")
        raw = await redis_client.get(redis_key)
        assert raw == "Form:name"

    async def test_data_stored_as_json(
        self,
        storage: RedisStorage,
        redis_client: fakeredis.FakeAsyncRedis,
    ) -> None:
        """Данные хранятся как JSON в Redis."""
        key = _make_key()
        await storage.set_data(key, {"name": "Alice", "age": 30})

        redis_key = storage._key_builder.build(key, "data")
        raw = await redis_client.get(redis_key)
        assert raw is not None
        parsed = json.loads(raw)
        assert parsed == {"name": "Alice", "age": 30}
