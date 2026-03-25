"""FSMContextMiddleware — инъекция FSMContext в контекст хендлера."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from maxogram.dispatcher.middlewares.base import BaseMiddleware
from maxogram.fsm.context import FSMContext
from maxogram.fsm.storage.base import BaseEventIsolation, BaseStorage, StorageKey
from maxogram.fsm.strategy import FSMStrategy, apply_strategy

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = ["FSMContextMiddleware"]


class FSMContextMiddleware(BaseMiddleware):
    """Middleware для инъекции FSMContext в контекст хендлера.

    Добавляет в data:
    - ``state``: :class:`FSMContext`
    - ``raw_state``: ``str | None`` — текущее состояние как строка
    - ``fsm_storage``: :class:`BaseStorage`
    """

    def __init__(
        self,
        storage: BaseStorage,
        strategy: FSMStrategy = FSMStrategy.USER_IN_CHAT,
        events_isolation: BaseEventIsolation | None = None,
    ) -> None:
        self.storage = storage
        self.strategy = strategy
        self.events_isolation = events_isolation

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        """Обработка события: создать FSMContext и передать в хендлер."""
        # Извлекаем user и chat из данных MaxContextMiddleware
        event_from_user = data.get("event_from_user")
        event_chat = data.get("event_chat")

        # Без user или chat — пропускаем FSM
        if event_from_user is None or event_chat is None:
            return await handler(event, data)

        user_id: int | None = getattr(event_from_user, "user_id", None)
        chat_id: int | None = getattr(event_chat, "chat_id", None)

        if user_id is None or chat_id is None:
            return await handler(event, data)

        # Получаем bot_id
        bot = data.get("bot")
        bot_id = 0
        if bot is not None:
            me = getattr(bot, "_me", None)
            if me is not None:
                bot_id = getattr(me, "user_id", 0)

        # Применяем стратегию
        effective_chat_id, effective_user_id = apply_strategy(self.strategy, chat_id, user_id)

        # Создаём StorageKey и FSMContext
        key = StorageKey(
            bot_id=bot_id,
            chat_id=effective_chat_id,
            user_id=effective_user_id,
        )
        context = FSMContext(storage=self.storage, key=key)

        # Добавляем в data
        data["state"] = context
        data["raw_state"] = await context.get_state()
        data["fsm_storage"] = self.storage

        # Event isolation
        if self.events_isolation:
            async with self.events_isolation.lock(key):
                return await handler(event, data)
        return await handler(event, data)
