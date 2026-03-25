"""Тесты Router — маршрутизатор событий Max API."""

from __future__ import annotations

from typing import Any

import pytest

from maxogram.dispatcher.event.bases import UNHANDLED
from maxogram.dispatcher.event.event import EventObserver
from maxogram.dispatcher.event.max import MaxEventObserver
from maxogram.dispatcher.router import Router

# Список всех 14 observers (13 Max API + error)
MAX_EVENT_NAMES = [
    "message_created",
    "message_callback",
    "message_edited",
    "message_removed",
    "bot_started",
    "bot_added",
    "bot_removed",
    "user_added",
    "user_removed",
    "chat_title_changed",
    "message_constructed",
    "message_construction_request",
    "message_chat_created",
    "error",
]


class TestRouterInit:
    """Тесты инициализации Router."""

    def test_custom_name(self) -> None:
        router = Router(name="main")
        assert router.name == "main"

    def test_default_name_hex_id(self) -> None:
        router = Router()
        assert router.name == hex(id(router))

    def test_has_14_observers(self) -> None:
        router = Router()
        assert len(router.observers) == 14
        for name in MAX_EVENT_NAMES:
            assert name in router.observers

    def test_observers_are_max_event_observer(self) -> None:
        router = Router()
        for name, observer in router.observers.items():
            assert isinstance(observer, MaxEventObserver), f"{name} is not MaxEventObserver"

    def test_observers_have_correct_event_name(self) -> None:
        router = Router()
        for name, observer in router.observers.items():
            assert observer.event_name == name

    def test_observers_reference_router(self) -> None:
        router = Router()
        for name, observer in router.observers.items():
            assert observer.router is router, f"{name} observer does not reference router"

    def test_observer_attributes_match_dict(self) -> None:
        router = Router()
        assert router.observers["message_created"] is router.message_created
        assert router.observers["message_callback"] is router.message_callback
        assert router.observers["bot_started"] is router.bot_started
        assert router.observers["message_chat_created"] is router.message_chat_created

    def test_has_startup_shutdown_observers(self) -> None:
        router = Router()
        assert isinstance(router.startup, EventObserver)
        assert isinstance(router.shutdown, EventObserver)

    def test_no_parent_by_default(self) -> None:
        router = Router()
        assert router.parent_router is None

    def test_empty_sub_routers(self) -> None:
        router = Router()
        assert router.sub_routers == []


class TestIncludeRouter:
    """Тесты подключения sub_router."""

    def test_include_sets_parent(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        assert child.parent_router is root

    def test_include_adds_to_sub_routers(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        assert child in root.sub_routers

    def test_include_returns_child(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        result = root.include_router(child)
        assert result is child

    def test_include_routers_multiple(self) -> None:
        root = Router(name="root")
        c1 = Router(name="c1")
        c2 = Router(name="c2")
        c3 = Router(name="c3")
        root.include_routers(c1, c2, c3)
        assert root.sub_routers == [c1, c2, c3]
        assert c1.parent_router is root
        assert c2.parent_router is root
        assert c3.parent_router is root

    def test_double_attach_raises(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        other = Router(name="other")
        with pytest.raises(RuntimeError, match="already attached"):
            other.include_router(child)

    def test_self_reference_raises(self) -> None:
        router = Router(name="self")
        with pytest.raises(RuntimeError, match="Self-referencing"):
            router.include_router(router)

    def test_circular_reference_raises(self) -> None:
        a = Router(name="A")
        b = Router(name="B")
        a.include_router(b)
        with pytest.raises(RuntimeError, match="[Cc]ircular"):
            b.include_router(a)

    def test_circular_reference_deep_raises(self) -> None:
        a = Router(name="A")
        b = Router(name="B")
        c = Router(name="C")
        a.include_router(b)
        b.include_router(c)
        with pytest.raises(RuntimeError, match="[Cc]ircular"):
            c.include_router(a)

    def test_wrong_type_raises(self) -> None:
        router = Router(name="root")
        with pytest.raises(TypeError):
            router.include_router("not a router")  # type: ignore[arg-type]


class TestPropagateEvent:
    """Тесты propagate_event — распространение событий по дереву роутеров."""

    @pytest.mark.asyncio
    async def test_handler_in_current_router(self) -> None:
        router = Router(name="root")

        async def handler(event: object) -> str:
            return "handled"

        router.message_created.register(handler)
        result = await router.propagate_event("message_created", object())
        assert result == "handled"

    @pytest.mark.asyncio
    async def test_unknown_event_returns_unhandled(self) -> None:
        router = Router(name="root")
        result = await router.propagate_event("unknown_event", object())
        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_no_handlers_returns_unhandled(self) -> None:
        router = Router(name="root")
        result = await router.propagate_event("message_created", object())
        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_sub_router_handles_event(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)

        async def handler(event: object) -> str:
            return "child_handled"

        child.message_created.register(handler)
        result = await root.propagate_event("message_created", object())
        assert result == "child_handled"

    @pytest.mark.asyncio
    async def test_first_sub_router_wins(self) -> None:
        root = Router(name="root")
        c1 = Router(name="c1")
        c2 = Router(name="c2")
        root.include_routers(c1, c2)

        async def h1(event: object) -> str:
            return "first"

        async def h2(event: object) -> str:
            return "second"

        c1.message_created.register(h1)
        c2.message_created.register(h2)

        result = await root.propagate_event("message_created", object())
        assert result == "first"

    @pytest.mark.asyncio
    async def test_root_handler_before_sub_router(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)

        async def root_handler(event: object) -> str:
            return "root"

        async def child_handler(event: object) -> str:
            return "child"

        root.message_created.register(root_handler)
        child.message_created.register(child_handler)

        result = await root.propagate_event("message_created", object())
        assert result == "root"

    @pytest.mark.asyncio
    async def test_event_router_in_kwargs(self) -> None:
        router = Router(name="root")
        received_kwargs: dict[str, Any] = {}

        async def handler(event: object, event_router: Any = None) -> str:
            received_kwargs["event_router"] = event_router
            return "ok"

        router.message_created.register(handler)
        await router.propagate_event("message_created", object())
        assert received_kwargs["event_router"] is router

    @pytest.mark.asyncio
    async def test_sub_router_gets_own_event_router(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        received_kwargs: dict[str, Any] = {}

        async def handler(event: object, event_router: Any = None) -> str:
            received_kwargs["event_router"] = event_router
            return "ok"

        child.message_created.register(handler)
        await root.propagate_event("message_created", object())
        assert received_kwargs["event_router"] is child

    @pytest.mark.asyncio
    async def test_unhandled_in_root_falls_to_sub(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)

        async def reject_filter(event: object) -> bool:
            return False

        async def root_handler(event: object) -> str:
            return "root"

        async def child_handler(event: object) -> str:
            return "child"

        root.message_created.register(root_handler, reject_filter)
        child.message_created.register(child_handler)

        result = await root.propagate_event("message_created", object())
        assert result == "child"

    @pytest.mark.asyncio
    async def test_deep_nesting(self) -> None:
        r1 = Router(name="r1")
        r2 = Router(name="r2")
        r3 = Router(name="r3")
        r1.include_router(r2)
        r2.include_router(r3)

        async def handler(event: object) -> str:
            return "deep"

        r3.bot_started.register(handler)
        result = await r1.propagate_event("bot_started", object())
        assert result == "deep"


class TestEmitStartupShutdown:
    """Тесты emit_startup / emit_shutdown."""

    @pytest.mark.asyncio
    async def test_emit_startup_calls_handlers(self) -> None:
        router = Router(name="root")
        called = False

        async def on_startup() -> None:
            nonlocal called
            called = True

        router.startup.register(on_startup)
        await router.emit_startup()
        assert called is True

    @pytest.mark.asyncio
    async def test_emit_shutdown_calls_handlers(self) -> None:
        router = Router(name="root")
        called = False

        async def on_shutdown() -> None:
            nonlocal called
            called = True

        router.shutdown.register(on_shutdown)
        await router.emit_shutdown()
        assert called is True

    @pytest.mark.asyncio
    async def test_emit_startup_propagates_to_sub_routers(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        order: list[str] = []

        async def root_startup(router: Any = None) -> None:
            order.append("root")

        async def child_startup(router: Any = None) -> None:
            order.append("child")

        root.startup.register(root_startup)
        child.startup.register(child_startup)
        await root.emit_startup()
        assert order == ["root", "child"]

    @pytest.mark.asyncio
    async def test_emit_shutdown_propagates_to_sub_routers(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        order: list[str] = []

        async def root_shutdown(router: Any = None) -> None:
            order.append("root")

        async def child_shutdown(router: Any = None) -> None:
            order.append("child")

        root.shutdown.register(root_shutdown)
        child.shutdown.register(child_shutdown)
        await root.emit_shutdown()
        assert order == ["root", "child"]

    @pytest.mark.asyncio
    async def test_emit_startup_passes_router_kwarg(self) -> None:
        router = Router(name="root")
        received: dict[str, Any] = {}

        async def on_startup(router: Any = None) -> None:
            received["router"] = router

        router.startup.register(on_startup)
        await router.emit_startup()
        assert received["router"] is router

    @pytest.mark.asyncio
    async def test_emit_startup_sub_router_gets_own_router(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        received: list[Any] = []

        async def on_startup(router: Any = None) -> None:
            received.append(router)

        root.startup.register(on_startup)
        child.startup.register(on_startup)
        await root.emit_startup()
        assert received[0] is root
        assert received[1] is child

    @pytest.mark.asyncio
    async def test_emit_startup_deep_tree(self) -> None:
        r1 = Router(name="r1")
        r2 = Router(name="r2")
        r3 = Router(name="r3")
        r1.include_router(r2)
        r2.include_router(r3)
        order: list[str] = []

        async def on_startup(router: Any = None) -> None:
            order.append(router.name)

        r1.startup.register(on_startup)
        r2.startup.register(on_startup)
        r3.startup.register(on_startup)
        await r1.emit_startup()
        assert order == ["r1", "r2", "r3"]


class TestChainHead:
    """Тесты chain_head — от текущего вверх к корню."""

    def test_single_router(self) -> None:
        router = Router(name="single")
        chain = list(router.chain_head)
        assert chain == [router]

    def test_two_levels(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        chain = list(child.chain_head)
        assert chain == [child, root]

    def test_three_levels(self) -> None:
        r1 = Router(name="r1")
        r2 = Router(name="r2")
        r3 = Router(name="r3")
        r1.include_router(r2)
        r2.include_router(r3)
        chain = list(r3.chain_head)
        assert chain == [r3, r2, r1]


class TestChainTail:
    """Тесты chain_tail — от текущего ко всем потомкам."""

    def test_single_router(self) -> None:
        router = Router(name="single")
        chain = list(router.chain_tail)
        assert chain == [router]

    def test_two_levels(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        chain = list(root.chain_tail)
        assert chain == [root, child]

    def test_tree_structure(self) -> None:
        root = Router(name="root")
        c1 = Router(name="c1")
        c2 = Router(name="c2")
        c1_1 = Router(name="c1_1")
        root.include_routers(c1, c2)
        c1.include_router(c1_1)
        chain = list(root.chain_tail)
        assert chain == [root, c1, c1_1, c2]


class TestResolveUsedUpdateTypes:
    """Тесты resolve_used_update_types."""

    def test_no_handlers_empty(self) -> None:
        router = Router(name="root")
        result = router.resolve_used_update_types()
        assert result == []

    def test_single_handler(self) -> None:
        router = Router(name="root")

        async def handler(event: object) -> None: ...

        router.message_created.register(handler)
        result = router.resolve_used_update_types()
        assert result == ["message_created"]

    def test_multiple_handlers(self) -> None:
        router = Router(name="root")

        async def handler(event: object) -> None: ...

        router.message_created.register(handler)
        router.bot_started.register(handler)
        result = router.resolve_used_update_types()
        assert sorted(result) == ["bot_started", "message_created"]

    def test_skip_events(self) -> None:
        router = Router(name="root")

        async def handler(event: object) -> None: ...

        router.message_created.register(handler)
        router.bot_started.register(handler)
        result = router.resolve_used_update_types(skip_events={"bot_started"})
        assert result == ["message_created"]

    def test_includes_sub_router_handlers(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)

        async def handler(event: object) -> None: ...

        root.message_created.register(handler)
        child.bot_started.register(handler)
        result = root.resolve_used_update_types()
        assert sorted(result) == ["bot_started", "message_created"]

    def test_result_is_sorted(self) -> None:
        router = Router(name="root")

        async def handler(event: object) -> None: ...

        router.user_removed.register(handler)
        router.bot_added.register(handler)
        router.message_created.register(handler)
        result = router.resolve_used_update_types()
        assert result == sorted(result)

    def test_no_duplicates_across_tree(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)

        async def handler(event: object) -> None: ...

        root.message_created.register(handler)
        child.message_created.register(handler)
        result = root.resolve_used_update_types()
        assert result == ["message_created"]


class TestPropagateEventOuterMiddleware:
    """Тесты outer_middleware на event observers через propagate_event."""

    @pytest.mark.asyncio
    async def test_outer_middleware_called_on_event_observer(self) -> None:
        """outer_middleware на event observer вызывается через propagate_event."""
        router = Router(name="root")
        mw_called = False

        async def outer_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            nonlocal mw_called
            mw_called = True
            return await handler(event, data)

        async def handler(event: object) -> str:
            return "handled"

        router.message_created.outer_middleware.register(outer_mw)
        router.message_created.register(handler)

        result = await router.propagate_event("message_created", object())
        assert mw_called is True
        assert result == "handled"

    @pytest.mark.asyncio
    async def test_inner_middleware_still_works(self) -> None:
        """Inner middleware продолжает работать (регрессия)."""
        router = Router(name="root")
        inner_called = False

        async def inner_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            nonlocal inner_called
            inner_called = True
            return await handler(event, data)

        async def handler(event: object) -> str:
            return "ok"

        router.message_created.middleware.register(inner_mw)
        router.message_created.register(handler)

        result = await router.propagate_event("message_created", object())
        assert inner_called is True
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_outer_before_inner_before_handler(self) -> None:
        """Порядок вызова: outer → inner → handler."""
        router = Router(name="root")
        order: list[str] = []

        async def outer_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            order.append("outer")
            return await handler(event, data)

        async def inner_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            order.append("inner")
            return await handler(event, data)

        async def handler(event: object) -> str:
            order.append("handler")
            return "ok"

        router.message_created.outer_middleware.register(outer_mw)
        router.message_created.middleware.register(inner_mw)
        router.message_created.register(handler)

        await router.propagate_event("message_created", object())
        assert order == ["outer", "inner", "handler"]

    @pytest.mark.asyncio
    async def test_outer_middleware_can_short_circuit(self) -> None:
        """outer_middleware может прервать цепочку, не вызывая handler."""
        router = Router(name="root")
        handler_called = False

        async def blocking_mw(handler: Any, event: Any, data: dict[str, Any]) -> str:
            return "blocked"

        async def handler(event: object) -> str:
            nonlocal handler_called
            handler_called = True
            return "handled"

        router.message_created.outer_middleware.register(blocking_mw)
        router.message_created.register(handler)

        result = await router.propagate_event("message_created", object())
        assert result == "blocked"
        assert handler_called is False

    @pytest.mark.asyncio
    async def test_outer_middleware_on_sub_router(self) -> None:
        """outer_middleware на sub_router event observer вызывается."""
        root = Router(name="root")
        child = Router(name="child")
        root.include_router(child)
        mw_called = False

        async def outer_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            nonlocal mw_called
            mw_called = True
            return await handler(event, data)

        async def handler(event: object) -> str:
            return "child_handled"

        child.message_created.outer_middleware.register(outer_mw)
        child.message_created.register(handler)

        result = await root.propagate_event("message_created", object())
        assert mw_called is True
        assert result == "child_handled"

    @pytest.mark.asyncio
    async def test_outer_middleware_receives_data_dict(self) -> None:
        """outer_middleware получает data dict с kwargs из propagate_event."""
        router = Router(name="root")
        received_data: dict[str, Any] = {}

        async def outer_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            received_data.update(data)
            return await handler(event, data)

        async def handler(event: object, custom: str = "") -> str:
            return custom

        router.message_created.outer_middleware.register(outer_mw)
        router.message_created.register(handler)

        await router.propagate_event("message_created", object(), custom="value")
        assert received_data["custom"] == "value"
        assert "event_router" in received_data

    @pytest.mark.asyncio
    async def test_multiple_outer_middlewares_order(self) -> None:
        """Несколько outer middleware вызываются в порядке регистрации (onion)."""
        router = Router(name="root")
        order: list[str] = []

        async def mw1(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            order.append("mw1_before")
            result = await handler(event, data)
            order.append("mw1_after")
            return result

        async def mw2(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            order.append("mw2_before")
            result = await handler(event, data)
            order.append("mw2_after")
            return result

        async def handler(event: object) -> str:
            order.append("handler")
            return "ok"

        router.message_created.outer_middleware.register(mw1)
        router.message_created.outer_middleware.register(mw2)
        router.message_created.register(handler)

        await router.propagate_event("message_created", object())
        assert order == ["mw1_before", "mw2_before", "handler", "mw2_after", "mw1_after"]

    @pytest.mark.asyncio
    async def test_no_outer_middleware_still_works(self) -> None:
        """Без outer middleware propagate_event работает как раньше."""
        router = Router(name="root")

        async def handler(event: object) -> str:
            return "no_mw"

        router.message_created.register(handler)
        result = await router.propagate_event("message_created", object())
        assert result == "no_mw"
