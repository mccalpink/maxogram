"""FSM storage — хранилища состояний.

Redis-классы доступны через ``maxogram.fsm.storage.redis``
(требуется extra ``maxogram[redis]``).
"""

from maxogram.fsm.storage.base import BaseEventIsolation, BaseStorage, StorageKey
from maxogram.fsm.storage.memory import DisabledEventIsolation, MemoryStorage

__all__ = [
    "BaseEventIsolation",
    "BaseStorage",
    "DisabledEventIsolation",
    "MemoryStorage",
    "StorageKey",
]
