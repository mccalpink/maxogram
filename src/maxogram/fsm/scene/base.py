"""Scene — базовый класс сцены (изолированный Router + FSM lifecycle)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from maxogram.dispatcher.router import Router
from maxogram.fsm.state import StatesGroup

if TYPE_CHECKING:
    from maxogram.fsm.context import FSMContext
    from maxogram.fsm.state import State

__all__ = [
    "Scene",
    "SceneConfig",
]


@dataclass(frozen=True)
class SceneConfig:
    """Конфигурация сцены.

    - ``scene_name`` — имя сцены (по умолчанию — имя класса)
    - ``reset_data_on_leave`` — очищать данные при выходе из сцены
    """

    scene_name: str | None = None
    reset_data_on_leave: bool = False


class SceneMeta(type):
    """Метакласс для Scene.

    Обрабатывает ``state=`` параметр при определении класса:
    ``class MyScene(Scene, state=MyStates): ...``

    Промежуточные базовые классы (например WizardScene) могут
    не указывать ``state=`` — они станут абстрактными.
    """

    # Имена классов, которые являются промежуточными базовыми
    _abstract_scene_classes: set[str] = set()

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        state: type[StatesGroup] | None = None,
        **kwargs: Any,
    ) -> SceneMeta:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Пропускаем базовый класс Scene
        if name == "Scene" and not any(hasattr(b, "__scene_state__") for b in bases):
            return cls

        # Наследуем state от родительского класса если не указан явно
        if state is None:
            for base in bases:
                if hasattr(base, "__scene_state__"):
                    state = base.__scene_state__
                    break

        if state is None:
            # Проверяем: это промежуточный класс (абстрактный)?
            # Промежуточный = наследует Scene напрямую и не имеет state
            is_intermediate = any(
                hasattr(b, "__scene_state__") or b.__name__ == "Scene" for b in bases
            ) and not any(
                hasattr(b, "__scene_state__") and b.__scene_state__ is not None for b in bases
            )
            if is_intermediate:
                cls.__scene_state__ = None  # type: ignore[attr-defined]
                mcs._abstract_scene_classes.add(name)
                return cls

            msg = (
                f"Scene '{name}' requires a 'state' parameter: "
                f"class {name}(Scene, state=MyStatesGroup)"
            )
            raise TypeError(msg)

        cls.__scene_state__ = state  # type: ignore[attr-defined]
        return cls


class Scene(Router, metaclass=SceneMeta, state=None):
    """Базовый класс сцены — изолированный Router с FSM lifecycle.

    Сцена привязана к StatesGroup и предоставляет:
    - ``enter()`` / ``leave()`` — вход/выход с hooks
    - ``on_enter()`` / ``on_leave()`` — переопределяемые callbacks
    - Все возможности Router (хендлеры, фильтры, middleware)

    Пример::

        class OrderScene(Scene, state=OrderStates):
            async def on_enter(self, ctx: FSMContext) -> None:
                ...

            async def on_leave(self, ctx: FSMContext) -> None:
                ...
    """

    __scene_state__: type[StatesGroup]
    __scene_config__: SceneConfig

    def __init_subclass__(cls, state: type[StatesGroup] | None = None, **kwargs: Any) -> None:
        """Устанавливает дефолтный SceneConfig если не указан."""
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "__scene_config__"):
            cls.__scene_config__ = SceneConfig()

    def __init__(self) -> None:
        if self.__scene_state__ is None:
            msg = (
                f"Cannot instantiate abstract scene '{type(self).__name__}'. "
                f"Define it with state=: class {type(self).__name__}(Scene, state=MyStatesGroup)"
            )
            raise TypeError(msg)
        super().__init__(name=f"Scene:{self.scene_name}")
        self.config = self.__scene_config__

    @property
    def scene_name(self) -> str:
        """Имя сцены (для регистрации в SceneRegistry)."""
        if self.__scene_config__.scene_name:
            return self.__scene_config__.scene_name
        return type(self).__name__

    def owns_state(self, state: str | None) -> bool:
        """Проверить, принадлежит ли состояние этой сцене."""
        if state is None:
            return False
        return state in self.__scene_state__.__all_states_names__

    async def enter(
        self,
        ctx: FSMContext,
        state: State | None = None,
        **kwargs: Any,
    ) -> None:
        """Войти в сцену.

        Устанавливает первое состояние группы (или указанное) и вызывает on_enter.
        """
        if state is None:
            # Первое состояние группы
            states = self.__scene_state__.__states__
            target = states[0] if states else None
        else:
            target = state

        await ctx.set_state(target)
        await self.on_enter(ctx, **kwargs)

    async def leave(self, ctx: FSMContext) -> None:
        """Выйти из сцены.

        Вызывает on_leave, очищает состояние (и данные если настроено).
        """
        await self.on_leave(ctx)
        await ctx.set_state(None)
        if self.config.reset_data_on_leave:
            await ctx.set_data({})

    async def on_enter(self, ctx: FSMContext, **kwargs: Any) -> None:
        """Hook при входе в сцену. Переопределяется в подклассах."""

    async def on_leave(self, ctx: FSMContext) -> None:
        """Hook при выходе из сцены. Переопределяется в подклассах."""
