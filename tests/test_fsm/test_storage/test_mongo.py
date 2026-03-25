"""Тесты MongoStorage и MongoEventIsolation."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from maxogram.fsm.storage.base import StorageKey
from maxogram.fsm.storage.mongo import MongoEventIsolation, MongoStorage


def _make_key(
    bot_id: int = 1,
    chat_id: int = 100,
    user_id: int = 42,
    destiny: str = "default",
) -> StorageKey:
    """Создать тестовый StorageKey."""
    return StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id, destiny=destiny)


def _build_mongo_key(key: StorageKey) -> str:
    """Построить строковый ключ MongoDB-документа (как в MongoStorage)."""
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.destiny}"


def _mock_collection() -> MagicMock:
    """Создать мок коллекции MongoDB с AsyncMock-методами."""
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value=None)
    collection.replace_one = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.find_one_and_update = AsyncMock(return_value=None)
    return collection


def _mock_client(collection: MagicMock | None = None) -> MagicMock:
    """Создать мок AsyncIOMotorClient."""
    client = MagicMock()
    coll = collection or _mock_collection()
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coll)
    client.__getitem__ = MagicMock(return_value=db)
    client.close = MagicMock()  # motor client.close() — sync
    return client


@pytest.fixture
def collection() -> MagicMock:
    """Мок коллекции MongoDB."""
    return _mock_collection()


@pytest.fixture
def storage(collection: MagicMock) -> MongoStorage:
    """MongoStorage с мок-коллекцией."""
    client = _mock_client(collection)
    return MongoStorage(client=client, database="test_db", collection_name="fsm_states")


# ---------------------------------------------------------------------------
# MongoStorage — управление состоянием
# ---------------------------------------------------------------------------


class TestMongoStorageState:
    """MongoStorage — CRUD операции с состоянием."""

    async def test_get_state_default_none(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """По умолчанию состояние — None (документ не существует)."""
        collection.find_one.return_value = None
        key = _make_key()
        assert await storage.get_state(key) is None

    async def test_get_state_returns_value(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """get_state возвращает сохранённое состояние."""
        key = _make_key()
        doc_key = _build_mongo_key(key)
        collection.find_one.return_value = {
            "_id": doc_key,
            "state": "Form:name",
            "data": {},
        }
        assert await storage.get_state(key) == "Form:name"

    async def test_set_state(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """set_state сохраняет состояние через replace_one(upsert=True)."""
        key = _make_key()
        doc_key = _build_mongo_key(key)
        # Сначала возвращаем None (документ не существует)
        collection.find_one.return_value = None
        await storage.set_state(key, "Form:name")
        collection.replace_one.assert_called_once()
        call_args = collection.replace_one.call_args
        assert call_args[0][0] == {"_id": doc_key}
        doc = call_args[0][1]
        assert doc["state"] == "Form:name"
        assert call_args[1]["upsert"] is True

    async def test_set_state_none_clears(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """set_state(None) сбрасывает состояние в документе."""
        key = _make_key()
        doc_key = _build_mongo_key(key)
        collection.find_one.return_value = {
            "_id": doc_key,
            "state": "Form:name",
            "data": {"name": "Alice"},
        }
        await storage.set_state(key, None)
        collection.replace_one.assert_called_once()
        call_args = collection.replace_one.call_args
        doc = call_args[0][1]
        assert doc["state"] is None
        # Данные сохраняются
        assert doc["data"] == {"name": "Alice"}

    async def test_set_state_none_no_existing_doc(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """set_state(None) без существующего документа — upsert с пустыми данными."""
        key = _make_key()
        collection.find_one.return_value = None
        await storage.set_state(key, None)
        collection.replace_one.assert_called_once()
        call_args = collection.replace_one.call_args
        doc = call_args[0][1]
        assert doc["state"] is None
        assert doc["data"] == {}

    async def test_different_keys_produce_different_ids(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """Разные StorageKey порождают разные _id в MongoDB."""
        key1 = _make_key(user_id=1)
        key2 = _make_key(user_id=2)
        id1 = _build_mongo_key(key1)
        id2 = _build_mongo_key(key2)
        assert id1 != id2


# ---------------------------------------------------------------------------
# MongoStorage — управление данными
# ---------------------------------------------------------------------------


class TestMongoStorageData:
    """MongoStorage — CRUD операции с данными."""

    async def test_get_data_default_empty(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """По умолчанию данные — пустой dict."""
        collection.find_one.return_value = None
        key = _make_key()
        assert await storage.get_data(key) == {}

    async def test_get_data_returns_value(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """get_data возвращает сохранённые данные."""
        key = _make_key()
        doc_key = _build_mongo_key(key)
        collection.find_one.return_value = {
            "_id": doc_key,
            "state": None,
            "data": {"name": "Alice", "age": 30},
        }
        assert await storage.get_data(key) == {"name": "Alice", "age": 30}

    async def test_set_data(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """set_data сохраняет данные через replace_one(upsert=True)."""
        key = _make_key()
        doc_key = _build_mongo_key(key)
        collection.find_one.return_value = None
        await storage.set_data(key, {"name": "Alice", "age": 30})
        collection.replace_one.assert_called_once()
        call_args = collection.replace_one.call_args
        assert call_args[0][0] == {"_id": doc_key}
        doc = call_args[0][1]
        assert doc["data"] == {"name": "Alice", "age": 30}

    async def test_set_data_preserves_state(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """set_data сохраняет текущее состояние при замене данных."""
        key = _make_key()
        doc_key = _build_mongo_key(key)
        collection.find_one.return_value = {
            "_id": doc_key,
            "state": "Form:name",
            "data": {"old": True},
        }
        await storage.set_data(key, {"new": True})
        call_args = collection.replace_one.call_args
        doc = call_args[0][1]
        assert doc["state"] == "Form:name"
        assert doc["data"] == {"new": True}

    async def test_set_empty_data(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """set_data с пустыми данными сохраняет пустой dict."""
        key = _make_key()
        collection.find_one.return_value = None
        await storage.set_data(key, {})
        collection.replace_one.assert_called_once()
        call_args = collection.replace_one.call_args
        doc = call_args[0][1]
        assert doc["data"] == {}

    async def test_data_serialization_complex(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """Сложные данные (JSON-совместимые) сохраняются корректно."""
        key = _make_key()
        complex_data: dict[str, Any] = {
            "name": "Alice",
            "items": [1, 2, 3],
            "nested": {"x": True, "y": None},
            "count": 42,
        }
        collection.find_one.return_value = None
        await storage.set_data(key, complex_data)
        call_args = collection.replace_one.call_args
        doc = call_args[0][1]
        assert doc["data"] == complex_data

    async def test_update_data_merge(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """update_data мержит данные (через BaseStorage)."""
        key = _make_key()
        doc_key = _build_mongo_key(key)
        # Первый вызов get_data (внутри update_data)
        collection.find_one.return_value = {
            "_id": doc_key,
            "state": None,
            "data": {"a": 1},
        }
        result = await storage.update_data(key, {"b": 2})
        assert result == {"a": 1, "b": 2}

    async def test_update_data_kwargs(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """update_data принимает kwargs."""
        key = _make_key()
        collection.find_one.return_value = None
        result = await storage.update_data(key, name="Alice", age=30)
        assert result == {"name": "Alice", "age": 30}

    async def test_get_value(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """get_value возвращает одно значение."""
        key = _make_key()
        doc_key = _build_mongo_key(key)
        collection.find_one.return_value = {
            "_id": doc_key,
            "state": None,
            "data": {"name": "Alice", "age": 30},
        }
        assert await storage.get_value(key, "name") == "Alice"

    async def test_get_value_default(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """get_value возвращает default, если ключа нет."""
        key = _make_key()
        collection.find_one.return_value = None
        assert await storage.get_value(key, "missing", "fallback") == "fallback"


# ---------------------------------------------------------------------------
# MongoStorage — close
# ---------------------------------------------------------------------------


class TestMongoStorageClose:
    """MongoStorage — close закрывает motor client."""

    async def test_close(self, storage: MongoStorage) -> None:
        """close() вызывает client.close()."""
        await storage.close()
        storage._client.close.assert_called_once()


# ---------------------------------------------------------------------------
# MongoStorage — from_url
# ---------------------------------------------------------------------------


class TestMongoStorageFromUrl:
    """MongoStorage.from_url — конструктор из URL."""

    async def test_from_url_creates_storage(self) -> None:
        """from_url создаёт MongoStorage с motor client."""
        with patch(
            "motor.motor_asyncio.AsyncIOMotorClient"
        ) as mock_cls:
            mock_client = _mock_client()
            mock_cls.return_value = mock_client
            storage = MongoStorage.from_url("mongodb://localhost:27017/test_db")
            assert isinstance(storage, MongoStorage)
            mock_cls.assert_called_once_with("mongodb://localhost:27017/test_db")
            await storage.close()

    async def test_from_url_with_params(self) -> None:
        """from_url передаёт параметры."""
        with patch(
            "motor.motor_asyncio.AsyncIOMotorClient"
        ) as mock_cls:
            mock_client = _mock_client()
            mock_cls.return_value = mock_client
            storage = MongoStorage.from_url(
                "mongodb://localhost:27017",
                database="my_db",
                collection_name="my_states",
            )
            assert storage._database_name == "my_db"
            assert storage._collection_name == "my_states"
            await storage.close()

    async def test_from_url_default_database(self) -> None:
        """from_url использует 'maxogram' как базу по умолчанию."""
        with patch(
            "motor.motor_asyncio.AsyncIOMotorClient"
        ) as mock_cls:
            mock_cls.return_value = _mock_client()
            storage = MongoStorage.from_url("mongodb://localhost:27017")
            assert storage._database_name == "maxogram"
            await storage.close()


# ---------------------------------------------------------------------------
# MongoStorage — формат документа
# ---------------------------------------------------------------------------


class TestMongoStorageDocumentFormat:
    """Проверка формата документов в MongoDB."""

    async def test_document_has_correct_structure(
        self, storage: MongoStorage, collection: MagicMock
    ) -> None:
        """Документ содержит _id, state, data."""
        key = _make_key()
        doc_key = _build_mongo_key(key)
        collection.find_one.return_value = None

        await storage.set_state(key, "Form:name")

        call_args = collection.replace_one.call_args
        doc = call_args[0][1]
        assert "_id" in doc
        assert "state" in doc
        assert "data" in doc
        assert doc["_id"] == doc_key

    async def test_key_format(self) -> None:
        """Ключ имеет формат bot_id:chat_id:user_id:destiny."""
        key = _make_key(bot_id=5, chat_id=200, user_id=99, destiny="quiz")
        expected = "5:200:99:quiz"
        assert _build_mongo_key(key) == expected


# ---------------------------------------------------------------------------
# MongoEventIsolation
# ---------------------------------------------------------------------------


class TestMongoEventIsolation:
    """MongoEventIsolation — distributed lock через MongoDB."""

    async def test_lock_executes_body(self) -> None:
        """lock() выполняет тело контекстного менеджера."""
        collection = _mock_collection()
        # find_one_and_update для acquire возвращает документ (lock acquired)
        collection.find_one_and_update.return_value = {"_id": "lock_key", "locked": True}
        collection.delete_one = AsyncMock()

        isolation = MongoEventIsolation(collection=collection)
        key = _make_key()
        executed = False

        async with isolation.lock(key):
            executed = True

        assert executed is True

    async def test_lock_acquires_via_find_one_and_update(self) -> None:
        """lock() захватывает блокировку через find_one_and_update."""
        collection = _mock_collection()
        collection.find_one_and_update.return_value = {"_id": "lock_key", "locked": True}
        collection.delete_one = AsyncMock()

        isolation = MongoEventIsolation(collection=collection)
        key = _make_key()

        async with isolation.lock(key):
            collection.find_one_and_update.assert_called_once()

    async def test_lock_releases_via_delete_one(self) -> None:
        """lock() освобождает блокировку через delete_one."""
        collection = _mock_collection()
        collection.find_one_and_update.return_value = {"_id": "lock_key", "locked": True}
        collection.delete_one = AsyncMock()

        isolation = MongoEventIsolation(collection=collection)
        key = _make_key()

        async with isolation.lock(key):
            pass

        collection.delete_one.assert_called_once()

    async def test_close(self) -> None:
        """close() не вызывает ошибок."""
        collection = _mock_collection()
        isolation = MongoEventIsolation(collection=collection)
        await isolation.close()

    async def test_lock_key_format(self) -> None:
        """lock использует правильный формат ключа."""
        collection = _mock_collection()
        collection.find_one_and_update.return_value = {"_id": "lock", "locked": True}
        collection.delete_one = AsyncMock()

        isolation = MongoEventIsolation(collection=collection, lock_collection_name="locks")
        key = _make_key(bot_id=1, chat_id=100, user_id=42)

        async with isolation.lock(key):
            call_args = collection.find_one_and_update.call_args
            filter_arg = call_args[0][0]
            assert "1:100:42:default" in filter_arg["_id"]
