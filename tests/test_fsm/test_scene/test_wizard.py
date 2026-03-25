"""Тесты WizardScene — пошаговый FSM-сценарий."""

from __future__ import annotations

import pytest

from maxogram.fsm.context import FSMContext
from maxogram.fsm.scene.base import Scene
from maxogram.fsm.scene.wizard import WizardScene
from maxogram.fsm.state import State, StatesGroup
from maxogram.fsm.storage.base import StorageKey
from maxogram.fsm.storage.memory import MemoryStorage

# --- Helpers ---


def _make_context(storage: MemoryStorage | None = None) -> FSMContext:
    s = storage or MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=100, user_id=200)
    return FSMContext(storage=s, key=key)


# --- States ---


class RegistrationStates(StatesGroup):
    name = State()
    email = State()
    phone = State()
    confirm = State()


class TwoStepStates(StatesGroup):
    step1 = State()
    step2 = State()


# --- Тесты ---


class TestWizardSceneCreation:
    """Создание WizardScene."""

    def test_wizard_is_scene(self) -> None:
        """WizardScene наследует Scene."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        assert isinstance(wizard, Scene)

    def test_wizard_steps_from_states(self) -> None:
        """Шаги wizard-а определяются состояниями StatesGroup."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        assert len(wizard.steps) == 4
        assert wizard.steps[0] is RegistrationStates.name
        assert wizard.steps[1] is RegistrationStates.email
        assert wizard.steps[2] is RegistrationStates.phone
        assert wizard.steps[3] is RegistrationStates.confirm


class TestWizardNavigation:
    """Навигация wizard: next, back, goto."""

    @pytest.mark.asyncio
    async def test_enter_starts_at_first_step(self) -> None:
        """Вход в wizard начинается с первого шага."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        raw = await ctx.get_state()
        assert raw == RegistrationStates.name.state

    @pytest.mark.asyncio
    async def test_next_step(self) -> None:
        """next() переходит к следующему шагу."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        await wizard.next(ctx)
        assert await ctx.get_state() == RegistrationStates.email.state

        await wizard.next(ctx)
        assert await ctx.get_state() == RegistrationStates.phone.state

    @pytest.mark.asyncio
    async def test_back_step(self) -> None:
        """back() возвращается к предыдущему шагу."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        await wizard.next(ctx)  # email
        await wizard.next(ctx)  # phone
        await wizard.back(ctx)  # email

        assert await ctx.get_state() == RegistrationStates.email.state

    @pytest.mark.asyncio
    async def test_back_at_first_step_stays(self) -> None:
        """back() на первом шаге — остаёмся на месте."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        await wizard.back(ctx)
        assert await ctx.get_state() == RegistrationStates.name.state

    @pytest.mark.asyncio
    async def test_next_at_last_step_stays(self) -> None:
        """next() на последнем шаге — остаёмся на месте."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        # Прокручиваем до конца
        await wizard.next(ctx)  # email
        await wizard.next(ctx)  # phone
        await wizard.next(ctx)  # confirm

        # Ещё раз next — остаёмся
        await wizard.next(ctx)
        assert await ctx.get_state() == RegistrationStates.confirm.state

    @pytest.mark.asyncio
    async def test_goto_step_by_index(self) -> None:
        """goto() переходит к шагу по индексу."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        await wizard.goto(ctx, step=2)
        assert await ctx.get_state() == RegistrationStates.phone.state

    @pytest.mark.asyncio
    async def test_goto_step_by_state(self) -> None:
        """goto() переходит к шагу по State-объекту."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        await wizard.goto(ctx, state=RegistrationStates.confirm)
        assert await ctx.get_state() == RegistrationStates.confirm.state

    @pytest.mark.asyncio
    async def test_goto_invalid_index_raises(self) -> None:
        """goto() с невалидным индексом — ошибка."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        with pytest.raises(IndexError):
            await wizard.goto(ctx, step=99)

    @pytest.mark.asyncio
    async def test_goto_invalid_state_raises(self) -> None:
        """goto() с состоянием не из этой группы — ошибка."""

        class OtherStates(StatesGroup):
            other = State()

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        with pytest.raises(ValueError, match="not found"):
            await wizard.goto(ctx, state=OtherStates.other)

    @pytest.mark.asyncio
    async def test_retake_stays_on_current_step(self) -> None:
        """retake() повторно устанавливает текущее состояние (для повторной обработки)."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)
        await wizard.next(ctx)  # email

        await wizard.retake(ctx)
        assert await ctx.get_state() == RegistrationStates.email.state


class TestWizardCurrentStep:
    """Получение информации о текущем шаге."""

    @pytest.mark.asyncio
    async def test_current_step_index(self) -> None:
        """current_step_index() возвращает индекс текущего шага."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        assert await wizard.current_step_index(ctx) == 0

        await wizard.next(ctx)
        assert await wizard.current_step_index(ctx) == 1

    @pytest.mark.asyncio
    async def test_current_step_index_none_when_not_in_wizard(self) -> None:
        """current_step_index() возвращает None, если не в wizard."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()

        assert await wizard.current_step_index(ctx) is None

    @pytest.mark.asyncio
    async def test_is_first_step(self) -> None:
        """is_first_step() проверяет первый шаг."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        assert await wizard.is_first_step(ctx) is True
        await wizard.next(ctx)
        assert await wizard.is_first_step(ctx) is False

    @pytest.mark.asyncio
    async def test_is_last_step(self) -> None:
        """is_last_step() проверяет последний шаг."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        assert await wizard.is_last_step(ctx) is False

        # Прокрутим до конца
        await wizard.next(ctx)
        await wizard.next(ctx)
        await wizard.next(ctx)

        assert await wizard.is_last_step(ctx) is True

    @pytest.mark.asyncio
    async def test_total_steps(self) -> None:
        """total_steps — общее количество шагов."""

        class RegWizard(WizardScene, state=RegistrationStates):
            pass

        wizard = RegWizard()
        assert wizard.total_steps == 4

    @pytest.mark.asyncio
    async def test_two_step_wizard(self) -> None:
        """Wizard с двумя шагами — минимальный случай."""

        class TwoStepWizard(WizardScene, state=TwoStepStates):
            pass

        wizard = TwoStepWizard()
        ctx = _make_context()
        await wizard.enter(ctx)

        assert await wizard.is_first_step(ctx) is True
        assert await wizard.is_last_step(ctx) is False

        await wizard.next(ctx)
        assert await wizard.is_first_step(ctx) is False
        assert await wizard.is_last_step(ctx) is True
