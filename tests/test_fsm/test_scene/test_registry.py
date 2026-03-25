"""Тесты SceneRegistry — реестр и маршрутизация сцен."""

from __future__ import annotations

import pytest

from maxogram.dispatcher.router import Router
from maxogram.fsm.context import FSMContext
from maxogram.fsm.scene.base import Scene, SceneConfig
from maxogram.fsm.scene.registry import SceneRegistry
from maxogram.fsm.state import State, StatesGroup
from maxogram.fsm.storage.base import StorageKey
from maxogram.fsm.storage.memory import MemoryStorage

# --- Helpers ---


def _make_storage() -> MemoryStorage:
    return MemoryStorage()


def _make_context(storage: MemoryStorage | None = None) -> FSMContext:
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


class ProfileStates(StatesGroup):
    name = State()
    email = State()


# --- Test Scenes ---


class MenuScene(Scene, state=MenuStates):
    """Главное меню."""


class OrderScene(Scene, state=OrderStates):
    """Заказ товара."""


class ProfileScene(Scene, state=ProfileStates):
    """Профиль пользователя."""


# --- Тесты ---


class TestSceneRegistryCreation:
    """Создание и регистрация SceneRegistry."""

    def test_create_registry(self) -> None:
        """SceneRegistry создаётся с Router."""
        router = Router()
        registry = SceneRegistry(router)
        assert registry.router is router

    def test_register_scene(self) -> None:
        """Регистрация сцены по имени."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene)

        assert "MenuScene" in registry

    def test_register_multiple_scenes(self) -> None:
        """Регистрация нескольких сцен."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene, OrderScene, ProfileScene)

        assert "MenuScene" in registry
        assert "OrderScene" in registry
        assert "ProfileScene" in registry

    def test_duplicate_scene_raises(self) -> None:
        """Повторная регистрация сцены — ошибка."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene)

        with pytest.raises(ValueError, match="already registered"):
            registry.add(MenuScene)

    def test_get_scene_by_name(self) -> None:
        """Получение сцены по имени."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene)

        scene = registry.get("MenuScene")
        assert isinstance(scene, MenuScene)

    def test_get_unknown_scene_raises(self) -> None:
        """Получение несуществующей сцены — KeyError."""
        router = Router()
        registry = SceneRegistry(router)

        with pytest.raises(KeyError, match="UnknownScene"):
            registry.get("UnknownScene")

    def test_scene_custom_name_registration(self) -> None:
        """Сцена с custom name регистрируется под этим именем."""

        class CustomScene(Scene, state=MenuStates):
            __scene_config__ = SceneConfig(scene_name="my_menu")

        router = Router()
        registry = SceneRegistry(router)
        registry.add(CustomScene)

        assert "my_menu" in registry
        assert "CustomScene" not in registry


class TestSceneRegistryRouting:
    """SceneRegistry подключает сцены как sub_routers."""

    def test_scenes_become_subrouters(self) -> None:
        """Зарегистрированные сцены подключаются к Router."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene, OrderScene)

        # Scene instances are sub_routers of the main router
        assert len(router.sub_routers) == 2

    @pytest.mark.asyncio
    async def test_route_to_active_scene(self) -> None:
        """Событие маршрутизируется в активную сцену."""
        results: list[str] = []
        storage = _make_storage()

        class TestOrderScene(Scene, state=OrderStates):
            pass

        router = Router()
        registry = SceneRegistry(router)
        registry.add(TestOrderScene)

        # Регистрируем хендлер на сцене
        scene = registry.get("TestOrderScene")

        @scene.message_created()
        async def handle_product(event: object, **kwargs: object) -> str:
            results.append("product_handler")
            return "ok"

        # Входим в сцену
        ctx = _make_context(storage)
        await scene.enter(ctx)

        # Проверяем что хендлер сцены работает
        result = await scene.propagate_event(
            "message_created", "test", handler=None
        )
        assert result == "ok"
        assert results == ["product_handler"]


class TestSceneRegistryTransitions:
    """Переходы между сценами."""

    @pytest.mark.asyncio
    async def test_enter_scene_via_registry(self) -> None:
        """Вход в сцену через registry."""
        storage = _make_storage()
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene, OrderScene)

        ctx = _make_context(storage)
        await registry.enter(ctx, "OrderScene")

        raw = await ctx.get_state()
        assert raw == OrderStates.product.state

    @pytest.mark.asyncio
    async def test_transition_between_scenes(self) -> None:
        """Переход из одной сцены в другую."""
        calls: list[str] = []
        storage = _make_storage()

        class TrackedMenuScene(Scene, state=MenuStates):
            async def on_enter(self, ctx: FSMContext) -> None:
                calls.append("menu_enter")

            async def on_leave(self, ctx: FSMContext) -> None:
                calls.append("menu_leave")

        class TrackedOrderScene(Scene, state=OrderStates):
            async def on_enter(self, ctx: FSMContext) -> None:
                calls.append("order_enter")

            async def on_leave(self, ctx: FSMContext) -> None:
                calls.append("order_leave")

        router = Router()
        registry = SceneRegistry(router)
        registry.add(TrackedMenuScene, TrackedOrderScene)

        ctx = _make_context(storage)

        # Входим в меню
        await registry.enter(ctx, "TrackedMenuScene")
        assert calls == ["menu_enter"]

        # Переход в заказ — сначала leave, потом enter
        await registry.enter(ctx, "TrackedOrderScene")
        assert calls == ["menu_enter", "menu_leave", "order_enter"]

    @pytest.mark.asyncio
    async def test_leave_current_scene(self) -> None:
        """Выход из текущей сцены через registry."""
        storage = _make_storage()
        calls: list[str] = []

        class TrackedMenuScene(Scene, state=MenuStates):
            async def on_leave(self, ctx: FSMContext) -> None:
                calls.append("menu_leave")

        router = Router()
        registry = SceneRegistry(router)
        registry.add(TrackedMenuScene)

        ctx = _make_context(storage)
        await registry.enter(ctx, "TrackedMenuScene")

        await registry.leave(ctx)

        assert calls == ["menu_leave"]
        assert await ctx.get_state() is None

    @pytest.mark.asyncio
    async def test_leave_when_not_in_scene(self) -> None:
        """Выход из сцены, когда ни в одной не находимся — no-op."""
        storage = _make_storage()
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene)

        ctx = _make_context(storage)
        # Не вызывает ошибку
        await registry.leave(ctx)
        assert await ctx.get_state() is None

    @pytest.mark.asyncio
    async def test_enter_unknown_scene_raises(self) -> None:
        """Вход в несуществующую сцену — ошибка."""
        storage = _make_storage()
        router = Router()
        registry = SceneRegistry(router)

        ctx = _make_context(storage)
        with pytest.raises(KeyError, match="UnknownScene"):
            await registry.enter(ctx, "UnknownScene")


class TestSceneRegistryFindByState:
    """Поиск сцены по текущему состоянию."""

    def test_find_scene_by_state(self) -> None:
        """Найти сцену по строке состояния."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene, OrderScene)

        scene = registry.find_by_state(OrderStates.product.state)
        assert isinstance(scene, OrderScene)

    def test_find_scene_any_state_in_group(self) -> None:
        """Любое состояние группы находит правильную сцену."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(OrderScene)

        s1 = registry.find_by_state(OrderStates.product.state)
        s2 = registry.find_by_state(OrderStates.quantity.state)
        s3 = registry.find_by_state(OrderStates.confirm.state)

        assert s1 is s2 is s3

    def test_find_scene_unknown_state_returns_none(self) -> None:
        """Неизвестное состояние — None."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene)

        result = registry.find_by_state("Unknown:state")
        assert result is None

    def test_find_scene_none_state_returns_none(self) -> None:
        """None — нет активной сцены."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene)

        result = registry.find_by_state(None)
        assert result is None


class TestSceneRegistryContains:
    """Проверка наличия сцены в реестре."""

    def test_contains_registered(self) -> None:
        """Зарегистрированная сцена — True."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene)
        assert "MenuScene" in registry

    def test_not_contains_unregistered(self) -> None:
        """Незарегистрированная сцена — False."""
        router = Router()
        registry = SceneRegistry(router)
        assert "MenuScene" not in registry

    def test_len(self) -> None:
        """len() возвращает количество сцен."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add(MenuScene, OrderScene)
        assert len(registry) == 2


class TestSceneRegistryAddInstance:
    """add_instance() — регистрация готовых экземпляров сцен."""

    def test_add_instance_basic(self) -> None:
        """add_instance() регистрирует готовый экземпляр."""
        router = Router()
        registry = SceneRegistry(router)
        scene = OrderScene()
        registry.add_instance(scene)

        assert "OrderScene" in registry
        assert registry.get("OrderScene") is scene

    def test_add_instance_preserves_handlers(self) -> None:
        """add_instance() сохраняет хендлеры, зарегистрированные на инстансе."""
        scene = OrderScene()

        @scene.message_created()
        async def handle_msg(event: object, **kwargs: object) -> str:
            return "ok"

        router = Router()
        registry = SceneRegistry(router)
        registry.add_instance(scene)

        # Хендлер должен быть на зарегистрированном инстансе
        registered = registry.get("OrderScene")
        assert registered is scene
        assert len(registered.message_created.handlers) > 0

    def test_add_instance_becomes_subrouter(self) -> None:
        """add_instance() подключает сцену как sub_router."""
        router = Router()
        registry = SceneRegistry(router)
        scene = MenuScene()
        registry.add_instance(scene)

        assert scene in router.sub_routers

    def test_add_instance_duplicate_raises(self) -> None:
        """Повторная регистрация через add_instance() — ошибка."""
        router = Router()
        registry = SceneRegistry(router)
        scene = OrderScene()
        registry.add_instance(scene)

        with pytest.raises(ValueError, match="already registered"):
            registry.add_instance(OrderScene())

    def test_add_instance_multiple(self) -> None:
        """add_instance() с несколькими сценами."""
        router = Router()
        registry = SceneRegistry(router)
        registry.add_instance(MenuScene(), OrderScene(), ProfileScene())

        assert len(registry) == 3
        assert "MenuScene" in registry
        assert "OrderScene" in registry
        assert "ProfileScene" in registry
