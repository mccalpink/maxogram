"""WizardScene — сцена с пошаговой навигацией (next/back/goto)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxogram.fsm.scene.base import Scene

if TYPE_CHECKING:
    from maxogram.fsm.context import FSMContext
    from maxogram.fsm.state import State

__all__ = [
    "WizardScene",
]


class WizardScene(Scene):
    """Сцена с пошаговой навигацией.

    Шаги определяются состояниями StatesGroup в порядке объявления.
    Предоставляет методы навигации: ``next()``, ``back()``, ``goto()``, ``retake()``.

    Пример::

        class RegStates(StatesGroup):
            name = State()
            email = State()
            confirm = State()

        class RegWizard(WizardScene, state=RegStates):
            async def on_enter(self, ctx: FSMContext) -> None:
                ...
    """

    @property
    def steps(self) -> tuple[State, ...]:
        """Шаги wizard-а — состояния StatesGroup в порядке объявления."""
        return self.__scene_state__.__states__

    @property
    def total_steps(self) -> int:
        """Общее количество шагов."""
        return len(self.steps)

    async def current_step_index(self, ctx: FSMContext) -> int | None:
        """Индекс текущего шага (0-based) или None если не в wizard."""
        raw = await ctx.get_state()
        if raw is None:
            return None
        for i, step in enumerate(self.steps):
            if step.state == raw:
                return i
        return None

    async def is_first_step(self, ctx: FSMContext) -> bool:
        """Проверить, находимся ли на первом шаге."""
        return await self.current_step_index(ctx) == 0

    async def is_last_step(self, ctx: FSMContext) -> bool:
        """Проверить, находимся ли на последнем шаге."""
        idx = await self.current_step_index(ctx)
        return idx == self.total_steps - 1

    async def next(self, ctx: FSMContext) -> None:
        """Перейти к следующему шагу. На последнем — остаёмся."""
        idx = await self.current_step_index(ctx)
        if idx is None:
            return
        next_idx = min(idx + 1, self.total_steps - 1)
        await ctx.set_state(self.steps[next_idx])

    async def back(self, ctx: FSMContext) -> None:
        """Вернуться к предыдущему шагу. На первом — остаёмся."""
        idx = await self.current_step_index(ctx)
        if idx is None:
            return
        prev_idx = max(idx - 1, 0)
        await ctx.set_state(self.steps[prev_idx])

    async def retake(self, ctx: FSMContext) -> None:
        """Повторно установить текущий шаг (для повторной обработки)."""
        idx = await self.current_step_index(ctx)
        if idx is None:
            return
        await ctx.set_state(self.steps[idx])

    async def goto(
        self,
        ctx: FSMContext,
        step: int | None = None,
        state: State | None = None,
    ) -> None:
        """Перейти к шагу по индексу или State-объекту.

        Укажите ``step`` (индекс) или ``state`` (State-объект).
        """
        if state is not None:
            # Найти индекс по State
            for i, s in enumerate(self.steps):
                if s is state or s.state == state.state:
                    await ctx.set_state(self.steps[i])
                    return
            msg = f"State {state!r} not found in wizard steps"
            raise ValueError(msg)

        if step is not None:
            if step < 0 or step >= self.total_steps:
                msg = f"Step index {step} out of range [0, {self.total_steps})"
                raise IndexError(msg)
            await ctx.set_state(self.steps[step])
            return

        msg = "Either 'step' or 'state' must be provided"
        raise ValueError(msg)
