"""SceneRegistry — реестр сцен и маршрутизация по текущему состоянию."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from maxogram.fsm.context import FSMContext
    from maxogram.fsm.state import State

from maxogram.dispatcher.router import Router
from maxogram.fsm.scene.base import Scene

__all__ = [
    "SceneRegistry",
]


class SceneRegistry:
    """Реестр сцен — хранит экземпляры Scene, управляет переходами.

    - ``add()`` — регистрация сцен (создаёт экземпляры, подключает как sub_routers)
    - ``enter()`` — вход в сцену по имени (с автоматическим leave из текущей)
    - ``leave()`` — выход из текущей сцены
    - ``find_by_state()`` — поиск сцены по строке состояния
    """

    def __init__(self, router: Router) -> None:
        self.router = router
        self._scenes: dict[str, Scene] = {}

    def add(self, *scene_classes: type[Scene]) -> None:
        """Зарегистрировать классы сцен.

        Создаёт экземпляры и подключает их как sub_routers к основному Router.
        """
        for scene_cls in scene_classes:
            scene = scene_cls()
            name = scene.scene_name

            if name in self._scenes:
                msg = f"Scene '{name}' is already registered"
                raise ValueError(msg)

            self._scenes[name] = scene
            self.router.include_router(scene)

    def add_instance(self, *scenes: Scene) -> None:
        """Зарегистрировать готовые экземпляры сцен (с хендлерами).

        Используйте вместо ``add()`` когда хендлеры зарегистрированы
        декораторами на существующем инстансе сцены.
        """
        for scene in scenes:
            name = scene.scene_name

            if name in self._scenes:
                msg = f"Scene '{name}' is already registered"
                raise ValueError(msg)

            self._scenes[name] = scene
            self.router.include_router(scene)

    def get(self, name: str) -> Scene:
        """Получить экземпляр сцены по имени."""
        if name not in self._scenes:
            msg = f"Scene '{name}' is not registered"
            raise KeyError(msg)
        return self._scenes[name]

    def find_by_state(self, state: str | None) -> Scene | None:
        """Найти сцену, владеющую данным состоянием."""
        if state is None:
            return None
        for scene in self._scenes.values():
            if scene.owns_state(state):
                return scene
        return None

    async def enter(
        self,
        ctx: FSMContext,
        name: str,
        state: State | None = None,
        **kwargs: Any,
    ) -> None:
        """Войти в сцену по имени.

        Если пользователь уже в другой сцене — сначала leave из неё.
        """
        target = self.get(name)

        # Выйти из текущей сцены если есть
        current_state = await ctx.get_state()
        if current_state is not None:
            current_scene = self.find_by_state(current_state)
            if current_scene is not None:
                await current_scene.leave(ctx)

        await target.enter(ctx, state=state, **kwargs)

    async def leave(self, ctx: FSMContext) -> None:
        """Выйти из текущей сцены."""
        current_state = await ctx.get_state()
        if current_state is None:
            return

        current_scene = self.find_by_state(current_state)
        if current_scene is not None:
            await current_scene.leave(ctx)

    def __contains__(self, name: str) -> bool:
        return name in self._scenes

    def __len__(self) -> int:
        return len(self._scenes)
