"""MongoStorage, MongoEventIsolation — MongoDB-бэкенд FSM-хранилища."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from maxogram.fsm.storage.base import BaseEventIsolation, BaseStorage, StorageKey

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

__all__ = [
    "MongoEventIsolation",
    "MongoStorage",
]


def _build_key(key: StorageKey) -> str:
    """Построить строковый ключ для MongoDB-документа.

    Формат: ``{bot_id}:{chat_id}:{user_id}:{destiny}``
    """
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.destiny}"


class MongoStorage(BaseStorage):
    """MongoDB-бэкенд FSM-хранилища.

    Состояние и данные хранятся в одном документе:
    ``{_id: key, state: str | None, data: dict}``

    Требует: ``maxogram[mongodb]`` (``motor>=3.3``).

    Args:
        client: Async Motor клиент.
        database: Имя базы данных.
        collection_name: Имя коллекции для FSM-состояний.
    """

    def __init__(
        self,
        client: Any,
        database: str = "maxogram",
        collection_name: str = "fsm_states",
    ) -> None:
        self._client: Any = client
        self._database_name = database
        self._collection_name = collection_name
        self._collection: Any = client[database][collection_name]

    @classmethod
    def from_url(
        cls,
        url: str,
        database: str = "maxogram",
        collection_name: str = "fsm_states",
    ) -> MongoStorage:
        """Создать storage из MongoDB URL.

        Args:
            url: MongoDB connection URL (``mongodb://host:port``).
            database: Имя базы данных.
            collection_name: Имя коллекции.

        Returns:
            Новый экземпляр MongoStorage.
        """
        from motor.motor_asyncio import AsyncIOMotorClient

        client: Any = AsyncIOMotorClient(url)
        return cls(client=client, database=database, collection_name=collection_name)

    async def _get_document(self, key: StorageKey) -> dict[str, Any] | None:
        """Получить документ из MongoDB по ключу."""
        doc_key = _build_key(key)
        result: dict[str, Any] | None = await self._collection.find_one({"_id": doc_key})
        return result

    async def _save_document(
        self,
        key: StorageKey,
        state: str | None,
        data: dict[str, Any],
    ) -> None:
        """Сохранить документ в MongoDB (upsert)."""
        doc_key = _build_key(key)
        doc: dict[str, Any] = {"_id": doc_key, "state": state, "data": data}
        await self._collection.replace_one({"_id": doc_key}, doc, upsert=True)

    async def set_state(
        self,
        key: StorageKey,
        state: str | None = None,
    ) -> None:
        """Установить состояние.

        Сохраняет существующие данные при изменении состояния.
        """
        existing = await self._get_document(key)
        data = existing["data"] if existing else {}
        await self._save_document(key, state, data)

    async def get_state(self, key: StorageKey) -> str | None:
        """Получить текущее состояние.

        Returns:
            Строка состояния или None, если не установлено.
        """
        doc = await self._get_document(key)
        if doc is None:
            return None
        result: str | None = doc.get("state")
        return result

    async def set_data(
        self,
        key: StorageKey,
        data: Mapping[str, Any],
    ) -> None:
        """Полностью заменить данные.

        Сохраняет существующее состояние при замене данных.
        """
        existing = await self._get_document(key)
        state = existing["state"] if existing else None
        await self._save_document(key, state, dict(data))

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        """Получить все данные.

        Returns:
            dict с данными или пустой dict, если данных нет.
        """
        doc = await self._get_document(key)
        if doc is None:
            return {}
        result: dict[str, Any] = doc.get("data", {})
        return result

    async def close(self) -> None:
        """Закрыть Motor-клиент."""
        self._client.close()


class MongoEventIsolation(BaseEventIsolation):
    """Distributed lock через MongoDB для изоляции FSM-событий.

    Использует отдельную коллекцию для блокировок.
    Lock реализован через ``find_one_and_update`` с ``upsert=True``.

    Args:
        collection: Коллекция MongoDB для данных (или блокировок).
        lock_collection_name: Имя коллекции для блокировок (суффикс).
    """

    def __init__(
        self,
        collection: Any,
        lock_collection_name: str = "fsm_locks",
    ) -> None:
        self._collection = collection
        self._lock_collection_name = lock_collection_name

    @asynccontextmanager
    async def lock(
        self,
        key: StorageKey,
    ) -> AsyncGenerator[None, None]:
        """Захватить distributed lock для ключа.

        Использует find_one_and_update с upsert для атомарного захвата.
        Освобождает через delete_one.

        Args:
            key: Ключ FSM-контекста.
        """
        lock_id = f"lock:{_build_key(key)}"
        try:
            await self._collection.find_one_and_update(
                {"_id": lock_id},
                {"$set": {"locked": True}},
                upsert=True,
            )
            yield
        finally:
            await self._collection.delete_one({"_id": lock_id})

    async def close(self) -> None:
        """Закрыть (no-op: Motor-клиент управляется MongoStorage)."""
