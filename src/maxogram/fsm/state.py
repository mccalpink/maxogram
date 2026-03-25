"""State, StatesGroup, StatesGroupMeta — определение и группировка состояний FSM."""

from __future__ import annotations

from typing import Any

__all__ = [
    "State",
    "StatesGroup",
    "StatesGroupMeta",
]


class State:
    """Описание одного состояния FSM.

    Формат строки состояния: ``GroupName:state_name``.
    Специальные значения:
    - ``None`` — нет состояния (дефолт)
    - ``"*"`` — wildcard (любое состояние)
    """

    def __init__(
        self,
        state: str | None = None,
        group_name: str | None = None,
    ) -> None:
        self._state = state
        self._group_name = group_name
        self._group: type[StatesGroup] | None = None

    def set_parent(self, group: type[StatesGroup]) -> None:
        """Установить группу-родителя."""
        self._group = group
        self._group_name = group.__full_group_name__

    @property
    def state(self) -> str | None:
        """Полное имя состояния: ``GroupName:state_name`` или None / ``*``."""
        if self._state is None or self._state == "*":
            return self._state
        group = self._group_name or "@"
        return f"{group}:{self._state}"

    @property
    def group(self) -> type[StatesGroup] | None:
        """Группа-родитель."""
        return self._group

    def __eq__(self, other: object) -> bool:
        if isinstance(other, State):
            return self.state == other.state
        if isinstance(other, str):
            return self.state == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.state)

    def __repr__(self) -> str:
        return f"State({self.state!r})"

    def __str__(self) -> str:
        return self.state or ""


class StatesGroupMeta(type):
    """Метакласс для StatesGroup.

    При создании класса:
    1. Собирает все ``State`` из namespace
    2. Собирает вложенные ``StatesGroup``
    3. Вычисляет ``__states__``, ``__state_names__``,
       ``__all_states__``, ``__all_states_names__``
    4. Вызывает ``set_parent()`` для каждого State
    """

    __full_group_name__: str
    __states__: tuple[State, ...]
    __state_names__: tuple[str, ...]
    __all_states__: tuple[State, ...]
    __all_states_names__: tuple[str, ...]
    __all_children__: tuple[type[StatesGroup], ...]

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> StatesGroupMeta:
        cls = super().__new__(mcs, name, bases, namespace)

        # Пропуск базового класса StatesGroup
        if not bases:
            return cls

        # Определяем полное имя группы (с учётом вложенности)
        parent_group_name = namespace.get("__full_group_name__")
        if parent_group_name:
            cls.__full_group_name__ = parent_group_name
        else:
            cls.__full_group_name__ = name

        # Собираем State и вложенные StatesGroup
        states: list[State] = []
        childs: list[type[StatesGroup]] = []

        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, State):
                attr_value._state = attr_name
                attr_value.set_parent(cls)  # type: ignore[arg-type]
                states.append(attr_value)
            elif isinstance(attr_value, StatesGroupMeta) and attr_value is not cls:
                # Вложенная StatesGroup — обновляем её full_group_name
                attr_value.__full_group_name__ = f"{cls.__full_group_name__}.{attr_value.__name__}"
                # Обновляем состояния вложенной группы с новым полным именем
                _update_nested_states(attr_value)  # type: ignore[arg-type]
                childs.append(attr_value)  # type: ignore[arg-type]

        cls.__states__ = tuple(states)
        cls.__state_names__ = tuple(s.state for s in states if s.state is not None)
        cls.__all_children__ = tuple(childs)

        # all_states включает состояния из вложенных групп
        all_states: list[State] = list(states)
        for child in childs:
            all_states.extend(child.__all_states__)

        cls.__all_states__ = tuple(all_states)
        cls.__all_states_names__ = tuple(s.state for s in all_states if s.state is not None)

        return cls

    def __contains__(cls, item: object) -> bool:
        if isinstance(item, str):
            return item in cls.__all_states_names__
        if isinstance(item, State):
            return item in cls.__all_states__
        return False

    def __repr__(cls) -> str:
        return f"<StatesGroup '{cls.__full_group_name__}'>"


def _update_nested_states(group: type[StatesGroup]) -> None:
    """Обновить state-ы вложенной группы после смены full_group_name."""
    for state in group.__states__:
        state._group_name = group.__full_group_name__

    for child in group.__all_children__:
        child.__full_group_name__ = f"{group.__full_group_name__}.{child.__name__}"
        _update_nested_states(child)


class StatesGroup(metaclass=StatesGroupMeta):
    """Базовый класс для группы состояний FSM.

    Пример::

        class OrderForm(StatesGroup):
            waiting_for_product = State()
            waiting_for_quantity = State()
    """
