# scene

Высокоуровневый FSM — сцены для сложных диалогов. Сцена = изолированный Router, привязанный к StatesGroup, с lifecycle-хуками (`on_enter`, `on_leave`) и автоматическими переходами между сценами.

## Когда Scene vs обычный FSM

| Критерий | FSM (`State` / `StatesGroup`) | Scene |
|----------|-------------------------------|-------|
| Простые формы (2-5 шагов) | Подходит | Избыточно |
| Сложный диалог с ветвлениями | Много ручного кода | Подходит |
| Несколько независимых диалогов | Один `StatesGroup`, конфликты | Каждый диалог — отдельная Scene |
| Lifecycle hooks (вход/выход) | Вручную | `on_enter()` / `on_leave()` |
| Пошаговый wizard (next/back) | Вручную | `WizardScene` из коробки |

## Основные классы

| Класс | Описание |
|-------|----------|
| `Scene` | Базовый класс сцены — изолированный Router + FSM lifecycle. Хуки: `on_enter()`, `on_leave()` |
| `SceneConfig` | Конфигурация: `scene_name`, `reset_data_on_leave` |
| `SceneRegistry` | Реестр сцен: `add()`, `enter()`, `leave()`, `find_by_state()`. Управляет переходами |
| `WizardScene` | Сцена с пошаговой навигацией: `next()`, `back()`, `goto()`, `retake()` |

## Использование

```python
from maxogram.fsm import State, StatesGroup, FSMContext
from maxogram.fsm.scene import Scene, SceneRegistry, WizardScene

# --- Определение сцены ---

class OrderStates(StatesGroup):
    product = State()
    quantity = State()
    confirm = State()

class OrderScene(Scene, state=OrderStates):
    async def on_enter(self, ctx: FSMContext, **kwargs):
        # Вызывается при входе в сцену
        ...

    async def on_leave(self, ctx: FSMContext):
        # Вызывается при выходе из сцены
        ...

# --- Регистрация ---

registry = SceneRegistry(router=dp)
registry.add(OrderScene)

# --- Переход между сценами ---

@router.message_created(Command("order"))
async def start_order(update, state: FSMContext):
    await registry.enter(state, "OrderScene")
```

```python
# --- WizardScene: пошаговая навигация ---

class RegStates(StatesGroup):
    name = State()
    email = State()
    confirm = State()

class RegWizard(WizardScene, state=RegStates):
    async def on_enter(self, ctx: FSMContext, **kwargs):
        ...

# В хендлере:
@wizard.message_created(RegStates.name)
async def on_name(update, state: FSMContext):
    await state.update_data(name=update.message.body.text)
    await wizard_instance.next(state)   # → email
    # await wizard_instance.back(state)  # ← назад
    # await wizard_instance.goto(state, step=2)  # → confirm
```

## Ссылки

- Связанные модули: `fsm/` (State, StatesGroup, FSMContext), `dispatcher/` (Router)
