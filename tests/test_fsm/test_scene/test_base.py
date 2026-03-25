"""Тесты Scene — базовый класс сцены."""

from __future__ import annotations

import pytest

from maxogram.dispatcher.event.bases import UNHANDLED
from maxogram.dispatcher.router import Router
from maxogram.fsm.context import FSMContext
from maxogram.fsm.scene.base import Scene, SceneConfig
from maxogram.fsm.state import State, StatesGroup
from maxogram.fsm.storage.base import StorageKey
from maxogram.fsm.storage.memory import MemoryStorage

# --- Fixtures ---


def _make_context(storage: MemoryStorage | None = None) -> FSMContext:
    """Создать FSMContext для тестов."""
    s = storage or MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=100, user_id=200)
    return FSMContext(storage=s, key=key)


# --- Test StatesGroups ---


class MenuStates(StatesGroup):
    main = State()


class OrderStates(StatesGroup):
    product = State()
    quantity = State()
    confirm = State()


# --- Тесты ---


class TestSceneCreation:
    """Создание Scene из класса."""

    def test_scene_is_router(self) -> None:
        """Scene наследуется от Router."""

        class MenuScene(Scene, state=MenuStates):
            pass

        scene = MenuScene()
        assert isinstance(scene, Router)

    def test_scene_has_state_group(self) -> None:
        """Scene хранит ссылку на StatesGroup."""

        class MenuScene(Scene, state=MenuStates):
            pass

        assert MenuScene.__scene_state__ is MenuStates

    def test_scene_name_from_class(self) -> None:
        """Имя сцены по умолчанию — имя класса."""

        class MenuScene(Scene, state=MenuStates):
            pass

        scene = MenuScene()
        assert scene.scene_name == "MenuScene"

    def test_scene_custom_name(self) -> None:
        """Имя сцены можно задать через SceneConfig."""

        class MenuScene(Scene, state=MenuStates):
            __scene_config__ = SceneConfig(scene_name="custom_menu")

        scene = MenuScene()
        assert scene.scene_name == "custom_menu"

    def test_scene_without_state_cannot_instantiate(self) -> None:
        """Scene без state= можно определить (промежуточный класс),
        но нельзя инстанцировать — __scene_state__ is None."""

        class BadScene(Scene):  # type: ignore[call-arg]
            pass

        assert BadScene.__scene_state__ is None  # type: ignore[union-attr]

        # Попытка инстанцировать — RuntimeError (нет состояний)
        with pytest.raises(TypeError):
            BadScene()

    def test_scene_router_name(self) -> None:
        """Router.name сцены содержит имя сцены."""

        class MenuScene(Scene, state=MenuStates):
            pass

        scene = MenuScene()
        assert "MenuScene" in scene.name


class TestSceneEnterLeave:
    """Вход и выход из сцены через FSMContext."""

    @pytest.mark.asyncio
    async def test_on_enter_sets_state(self) -> None:
        """При входе в сцену устанавливается первое состояние группы."""

        class OrderScene(Scene, state=OrderStates):
            pass

        scene = OrderScene()
        ctx = _make_context()

        await scene.enter(ctx)

        raw = await ctx.get_state()
        # Должно быть первое состояние группы
        assert raw == OrderStates.product.state

    @pytest.mark.asyncio
    async def test_on_enter_custom_state(self) -> None:
        """Можно указать конкретное состояние при входе."""

        class OrderScene(Scene, state=OrderStates):
            pass

        scene = OrderScene()
        ctx = _make_context()

        await scene.enter(ctx, state=OrderStates.quantity)

        raw = await ctx.get_state()
        assert raw == OrderStates.quantity.state

    @pytest.mark.asyncio
    async def test_on_enter_callback_called(self) -> None:
        """on_enter callback вызывается при входе."""
        calls: list[str] = []

        class OrderScene(Scene, state=OrderStates):
            async def on_enter(self, ctx: FSMContext) -> None:
                calls.append("entered")

        scene = OrderScene()
        ctx = _make_context()
        await scene.enter(ctx)

        assert calls == ["entered"]

    @pytest.mark.asyncio
    async def test_on_leave_callback_called(self) -> None:
        """on_leave callback вызывается при выходе."""
        calls: list[str] = []

        class OrderScene(Scene, state=OrderStates):
            async def on_leave(self, ctx: FSMContext) -> None:
                calls.append("left")

        scene = OrderScene()
        ctx = _make_context()
        await scene.enter(ctx)
        await scene.leave(ctx)

        assert calls == ["left"]

    @pytest.mark.asyncio
    async def test_leave_clears_state(self) -> None:
        """При выходе из сцены состояние очищается."""

        class OrderScene(Scene, state=OrderStates):
            pass

        scene = OrderScene()
        ctx = _make_context()
        await scene.enter(ctx)

        # Состояние установлено
        assert await ctx.get_state() is not None

        await scene.leave(ctx)

        # Состояние очищено
        assert await ctx.get_state() is None

    @pytest.mark.asyncio
    async def test_leave_preserves_data_by_default(self) -> None:
        """По умолчанию leave НЕ очищает данные."""

        class OrderScene(Scene, state=OrderStates):
            pass

        scene = OrderScene()
        ctx = _make_context()
        await scene.enter(ctx)
        await ctx.update_data(product="apple")
        await scene.leave(ctx)

        data = await ctx.get_data()
        assert data == {"product": "apple"}

    @pytest.mark.asyncio
    async def test_leave_clear_data_option(self) -> None:
        """SceneConfig.reset_data_on_leave=True очищает данные при выходе."""

        class OrderScene(Scene, state=OrderStates):
            __scene_config__ = SceneConfig(reset_data_on_leave=True)

        scene = OrderScene()
        ctx = _make_context()
        await scene.enter(ctx)
        await ctx.update_data(product="apple")
        await scene.leave(ctx)

        data = await ctx.get_data()
        assert data == {}

    @pytest.mark.asyncio
    async def test_enter_leave_lifecycle_order(self) -> None:
        """Порядок: on_enter при входе, on_leave при выходе."""
        calls: list[str] = []

        class OrderScene(Scene, state=OrderStates):
            async def on_enter(self, ctx: FSMContext) -> None:
                calls.append("enter")

            async def on_leave(self, ctx: FSMContext) -> None:
                calls.append("leave")

        scene = OrderScene()
        ctx = _make_context()

        await scene.enter(ctx)
        await scene.leave(ctx)

        assert calls == ["enter", "leave"]

    @pytest.mark.asyncio
    async def test_on_enter_receives_data(self) -> None:
        """on_enter получает дополнительные kwargs."""
        received: dict[str, object] = {}

        class OrderScene(Scene, state=OrderStates):
            async def on_enter(self, ctx: FSMContext, **kwargs: object) -> None:
                received.update(kwargs)

        scene = OrderScene()
        ctx = _make_context()
        await scene.enter(ctx, product="apple")

        assert received == {"product": "apple"}


class TestSceneAsRouter:
    """Scene работает как Router — хендлеры, фильтры, propagation."""

    @pytest.mark.asyncio
    async def test_register_handler(self) -> None:
        """Можно регистрировать хендлеры на Scene."""
        results: list[str] = []

        class MenuScene(Scene, state=MenuStates):
            pass

        scene = MenuScene()

        @scene.message_created()
        async def handle_msg(event: object, **kwargs: object) -> str:
            results.append("handled")
            return "ok"

        assert len(scene.message_created.handlers) == 1

    @pytest.mark.asyncio
    async def test_scene_propagate_event(self) -> None:
        """Scene propagate_event работает как Router."""
        results: list[str] = []

        class MenuScene(Scene, state=MenuStates):
            pass

        scene = MenuScene()

        @scene.message_created()
        async def handle_msg(event: object, **kwargs: object) -> str:
            results.append("handled")
            return "ok"

        result = await scene.propagate_event("message_created", "test_event", handler=None)
        assert result == "ok"
        assert results == ["handled"]

    @pytest.mark.asyncio
    async def test_scene_include_subrouter(self) -> None:
        """Scene может содержать sub_routers."""

        class MenuScene(Scene, state=MenuStates):
            pass

        scene = MenuScene()
        child = Router(name="child")
        scene.include_router(child)

        assert child in scene.sub_routers

    @pytest.mark.asyncio
    async def test_scene_unhandled_event(self) -> None:
        """Без хендлеров — UNHANDLED."""

        class MenuScene(Scene, state=MenuStates):
            pass

        scene = MenuScene()
        result = await scene.propagate_event("message_created", "test_event", handler=None)
        assert result is UNHANDLED


class TestSceneConfig:
    """SceneConfig — конфигурация сцены."""

    def test_default_config(self) -> None:
        """SceneConfig по умолчанию."""
        config = SceneConfig()
        assert config.scene_name is None
        assert config.reset_data_on_leave is False

    def test_custom_config(self) -> None:
        """SceneConfig с кастомными значениями."""
        config = SceneConfig(scene_name="my_scene", reset_data_on_leave=True)
        assert config.scene_name == "my_scene"
        assert config.reset_data_on_leave is True

    def test_scene_inherits_config(self) -> None:
        """Scene использует __scene_config__."""

        class OrderScene(Scene, state=OrderStates):
            __scene_config__ = SceneConfig(reset_data_on_leave=True)

        scene = OrderScene()
        assert scene.config.reset_data_on_leave is True


class TestSceneStatesOwnership:
    """Scene владеет состояниями своего StatesGroup."""

    def test_owns_state(self) -> None:
        """Scene knows which states belong to it."""

        class OrderScene(Scene, state=OrderStates):
            pass

        scene = OrderScene()
        assert scene.owns_state(OrderStates.product.state)
        assert scene.owns_state(OrderStates.quantity.state)
        assert not scene.owns_state(MenuStates.main.state)

    def test_owns_state_none(self) -> None:
        """None state не принадлежит ни одной сцене."""

        class OrderScene(Scene, state=OrderStates):
            pass

        scene = OrderScene()
        assert not scene.owns_state(None)
