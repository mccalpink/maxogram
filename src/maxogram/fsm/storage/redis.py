"""RedisStorage, RedisEventIsolation — Redis-бэкенд FSM-хранилища."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from maxogram.fsm.storage.base import BaseEventIsolation, BaseStorage, StorageKey

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

    from redis.asyncio import Redis

__all__ = [
    "DefaultKeyBuilder",
    "KeyBuilder",
    "RedisEventIsolation",
    "RedisStorage",
]


class KeyBuilder:
    """Абстрактный построитель Redis-ключей.

    Переопределяйте :meth:`build` для кастомной схемы ключей.
    """

    def build(self, key: StorageKey, part: str) -> str:
        """Построить Redis-ключ из StorageKey и части (state/data/lock).

        Args:
            key: Ключ FSM-контекста.
            part: Суффикс ключа (``"state"``, ``"data"``, ``"lock"``).

        Returns:
            Строка Redis-ключа.
        """
        raise NotImplementedError


class DefaultKeyBuilder(KeyBuilder):
    """Построитель ключей по умолчанию.

    Формат: ``{prefix}:{part}:{bot_id}:{chat_id}:{user_id}[:{destiny}]``

    Args:
        prefix: Префикс ключа.
        separator: Разделитель компонентов.
        with_bot_id: Включать ли bot_id (по умолчанию True).
        with_destiny: Включать ли destiny (по умолчанию False).
    """

    def __init__(
        self,
        *,
        prefix: str = "maxogram",
        separator: str = ":",
        with_bot_id: bool = True,
        with_destiny: bool = False,
    ) -> None:
        self._prefix = prefix
        self._separator = separator
        self._with_bot_id = with_bot_id
        self._with_destiny = with_destiny

    def build(self, key: StorageKey, part: str) -> str:
        """Построить Redis-ключ.

        Формат: ``{prefix}{sep}{part}{sep}[{bot_id}{sep}]{chat_id}{sep}{user_id}[{sep}{destiny}]``
        """
        sep = self._separator
        parts: list[str] = [self._prefix, part]

        if self._with_bot_id:
            parts.append(str(key.bot_id))

        parts.append(str(key.chat_id))
        parts.append(str(key.user_id))

        if self._with_destiny:
            parts.append(key.destiny)

        return sep.join(parts)


class RedisStorage(BaseStorage):
    """Redis-бэкенд FSM-хранилища.

    Состояние хранится как строка, данные — как JSON.
    Требует: ``maxogram[redis]`` (``redis>=5.0``).

    Args:
        redis: Async Redis-клиент.
        key_builder: Построитель ключей (по умолчанию :class:`DefaultKeyBuilder`).
        state_ttl: TTL для ключей состояния (секунды), None — без TTL.
        data_ttl: TTL для ключей данных (секунды), None — без TTL.
    """

    def __init__(
        self,
        redis: Redis,
        key_builder: KeyBuilder | None = None,
        state_ttl: int | None = None,
        data_ttl: int | None = None,
    ) -> None:
        self._redis = redis
        self._key_builder = key_builder or DefaultKeyBuilder()
        self._state_ttl = state_ttl
        self._data_ttl = data_ttl

    @classmethod
    def from_url(
        cls,
        url: str,
        key_builder: KeyBuilder | None = None,
        state_ttl: int | None = None,
        data_ttl: int | None = None,
        **redis_kwargs: Any,
    ) -> RedisStorage:
        """Создать storage из Redis URL.

        Args:
            url: Redis connection URL (``redis://host:port/db``).
            key_builder: Построитель ключей.
            state_ttl: TTL для состояний.
            data_ttl: TTL для данных.
            **redis_kwargs: Дополнительные параметры для ``Redis.from_url()``.

        Returns:
            Новый экземпляр RedisStorage.
        """
        from redis.asyncio import Redis as AsyncRedis

        redis = AsyncRedis.from_url(url, decode_responses=True, **redis_kwargs)
        return cls(
            redis=redis,
            key_builder=key_builder,
            state_ttl=state_ttl,
            data_ttl=data_ttl,
        )

    async def set_state(
        self,
        key: StorageKey,
        state: str | None = None,
    ) -> None:
        """Установить состояние.

        При ``state=None`` ключ удаляется из Redis.
        """
        redis_key = self._key_builder.build(key, "state")
        if state is None:
            await self._redis.delete(redis_key)
        else:
            await self._redis.set(redis_key, state, ex=self._state_ttl)

    async def get_state(self, key: StorageKey) -> str | None:
        """Получить текущее состояние.

        Returns:
            Строка состояния или None, если не установлено.
        """
        redis_key = self._key_builder.build(key, "state")
        value = await self._redis.get(redis_key)
        if value is None:
            return None
        return str(value)

    async def set_data(
        self,
        key: StorageKey,
        data: Mapping[str, Any],
    ) -> None:
        """Полностью заменить данные.

        При пустом ``data`` ключ удаляется из Redis.
        Данные сериализуются в JSON.
        """
        redis_key = self._key_builder.build(key, "data")
        if not data:
            await self._redis.delete(redis_key)
        else:
            await self._redis.set(redis_key, json.dumps(data), ex=self._data_ttl)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        """Получить все данные.

        Returns:
            dict с данными или пустой dict, если данных нет.
        """
        redis_key = self._key_builder.build(key, "data")
        value = await self._redis.get(redis_key)
        if value is None:
            return {}
        result: dict[str, Any] = json.loads(value)
        return result

    async def close(self) -> None:
        """Закрыть Redis-соединение."""
        await self._redis.aclose()


class RedisEventIsolation(BaseEventIsolation):
    """Distributed lock через Redis для изоляции FSM-событий.

    Гарантирует, что для одного StorageKey одновременно обрабатывается
    только одно событие. Использует Redis distributed lock.

    Args:
        redis: Async Redis-клиент.
        key_builder: Построитель ключей.
        lock_timeout: Таймаут блокировки в секундах.
    """

    def __init__(
        self,
        redis: Redis,
        key_builder: KeyBuilder | None = None,
        lock_timeout: float = 30.0,
    ) -> None:
        self._redis = redis
        self._key_builder = key_builder or DefaultKeyBuilder()
        self._lock_timeout = lock_timeout

    @asynccontextmanager
    async def lock(
        self,
        key: StorageKey,
    ) -> AsyncGenerator[None, None]:
        """Захватить distributed lock для ключа.

        Args:
            key: Ключ FSM-контекста.
        """
        redis_key = self._key_builder.build(key, "lock")
        redis_lock = self._redis.lock(redis_key, timeout=self._lock_timeout)
        try:
            await redis_lock.acquire()
            yield
        finally:
            await redis_lock.release()

    async def close(self) -> None:
        """Закрыть (no-op: Redis-соединение управляется RedisStorage)."""
