"""Router — маршрутизатор событий Max API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

from maxogram.dispatcher.event.bases import UNHANDLED
from maxogram.dispatcher.event.event import EventObserver
from maxogram.dispatcher.event.max import MaxEventObserver

__all__ = [
    "Router",
]


class Router:
    """Маршрутизатор событий Max API.

    Содержит MaxEventObserver для каждого типа события
    и поддерживает вложенность (дерево роутеров).
    """

    def __init__(self, *, name: str | None = None) -> None:
        self.name = name or hex(id(self))

        self._parent_router: Router | None = None
        self.sub_routers: list[Router] = []

        # Lifecycle observers
        self.startup = EventObserver()
        self.shutdown = EventObserver()

        # 13 observers для событий Max API
        self.message_created = MaxEventObserver(router=self, event_name="message_created")
        self.message_callback = MaxEventObserver(router=self, event_name="message_callback")
        self.message_edited = MaxEventObserver(router=self, event_name="message_edited")
        self.message_removed = MaxEventObserver(router=self, event_name="message_removed")
        self.bot_started = MaxEventObserver(router=self, event_name="bot_started")
        self.bot_added = MaxEventObserver(router=self, event_name="bot_added")
        self.bot_removed = MaxEventObserver(router=self, event_name="bot_removed")
        self.user_added = MaxEventObserver(router=self, event_name="user_added")
        self.user_removed = MaxEventObserver(router=self, event_name="user_removed")
        self.chat_title_changed = MaxEventObserver(router=self, event_name="chat_title_changed")
        self.message_constructed = MaxEventObserver(router=self, event_name="message_constructed")
        self.message_construction_request = MaxEventObserver(
            router=self, event_name="message_construction_request"
        )
        self.message_chat_created = MaxEventObserver(
            router=self, event_name="message_chat_created"
        )

        # Error observer — перехват ошибок из хендлеров
        self.error = MaxEventObserver(router=self, event_name="error")
        self.errors = self.error

        # Маппинг name -> observer для propagation
        self.observers: dict[str, MaxEventObserver] = {
            "message_created": self.message_created,
            "message_callback": self.message_callback,
            "message_edited": self.message_edited,
            "message_removed": self.message_removed,
            "bot_started": self.bot_started,
            "bot_added": self.bot_added,
            "bot_removed": self.bot_removed,
            "user_added": self.user_added,
            "user_removed": self.user_removed,
            "chat_title_changed": self.chat_title_changed,
            "message_constructed": self.message_constructed,
            "message_construction_request": self.message_construction_request,
            "message_chat_created": self.message_chat_created,
            "error": self.error,
        }

    @property
    def parent_router(self) -> Router | None:
        """Родительский роутер."""
        return self._parent_router

    @parent_router.setter
    def parent_router(self, router: Router) -> None:
        """Установить родительский роутер с проверками."""
        if not isinstance(router, Router):
            msg = f"Ожидался Router, получен {type(router).__name__}"
            raise TypeError(msg)
        if self._parent_router is not None:
            msg = "Router is already attached to a parent router"
            raise RuntimeError(msg)
        if router is self:
            msg = "Self-referencing routers is not allowed"
            raise RuntimeError(msg)
        # Проверка циклических ссылок — обход вверх по chain_head
        for parent in router.chain_head:
            if parent is self:
                msg = "Circular router reference detected"
                raise RuntimeError(msg)
        self._parent_router = router
        router.sub_routers.append(self)

    def include_router(self, router: Router) -> Router:
        """Подключить дочерний роутер."""
        if not isinstance(router, Router):
            msg = f"Ожидался Router, получен {type(router).__name__}"
            raise TypeError(msg)
        router.parent_router = self
        return router

    def include_routers(self, *routers: Router) -> None:
        """Подключить несколько дочерних роутеров."""
        for router in routers:
            self.include_router(router)

    async def propagate_event(self, update_type: str, event: Any, **kwargs: Any) -> Any:
        """Распространить событие по дереву роутеров.

        Сначала пробует текущий роутер, затем рекурсивно sub_routers.
        Первый обработавший хендлер останавливает распространение.
        """
        kwargs["event_router"] = self
        observer = self.observers.get(update_type)

        if observer:
            response = await observer.trigger(event, **kwargs)
            if response is not UNHANDLED:
                return response

        # Рекурсия по sub_routers
        for sub_router in self.sub_routers:
            response = await sub_router.propagate_event(update_type, event, **kwargs)
            if response is not UNHANDLED:
                return response

        return UNHANDLED

    async def emit_startup(self, *args: Any, **kwargs: Any) -> None:
        """Вызвать startup-хендлеры по всему дереву."""
        kwargs["router"] = self
        await self.startup.trigger(*args, **kwargs)
        for router in self.sub_routers:
            await router.emit_startup(*args, **kwargs)

    async def emit_shutdown(self, *args: Any, **kwargs: Any) -> None:
        """Вызвать shutdown-хендлеры по всему дереву."""
        kwargs["router"] = self
        await self.shutdown.trigger(*args, **kwargs)
        for router in self.sub_routers:
            await router.emit_shutdown(*args, **kwargs)

    @property
    def chain_head(self) -> Generator[Router, None, None]:
        """От текущего роутера вверх к корню."""
        router: Router | None = self
        while router:
            yield router
            router = router.parent_router

    @property
    def chain_tail(self) -> Generator[Router, None, None]:
        """От текущего роутера вниз ко всем потомкам."""
        yield self
        for router in self.sub_routers:
            yield from router.chain_tail

    def resolve_used_update_types(self, skip_events: set[str] | None = None) -> list[str]:
        """Определить типы событий, на которые есть хендлеры."""
        used: set[str] = set()
        for router in self.chain_tail:
            for event_name, observer in router.observers.items():
                if observer.handlers:
                    used.add(event_name)
        if skip_events:
            used -= skip_events
        return sorted(used)
