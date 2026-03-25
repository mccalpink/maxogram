# fsm

Конечные автоматы (Finite State Machine) для управления диалогами. Позволяют создавать пошаговые сценарии (формы, опросы, воронки).

## Основные классы

| Класс | Описание |
|-------|----------|
| `State` | Одно состояние FSM. Формат: `GroupName:state_name` |
| `StatesGroup` | Группа состояний (metaclass для автоматической регистрации) |
| `FSMContext` | Контекст FSM для конкретного user/chat. Методы: `set_state`, `get_data`, `update_data`, `clear` |
| `FSMContextMiddleware` | Middleware для инъекции `FSMContext` в хендлер как параметр `state` |
| `FSMStrategy` | Стратегия ключа: `USER_IN_CHAT`, `CHAT`, `GLOBAL_USER` |
| `BaseStorage` | ABC хранилища состояний |
| `MemoryStorage` | In-memory хранилище (для разработки) |
| `StorageKey` | Ключ идентификации FSM-контекста: `(bot_id, chat_id, user_id)` |

## Использование

```python
from maxogram.fsm import State, StatesGroup, FSMContext

# Определение состояний:
class OrderForm(StatesGroup):
    waiting_product = State()
    waiting_quantity = State()
    confirm = State()

# В хендлере:
@router.message_created(Command("order"))
async def start_order(update, state: FSMContext):
    await state.set_state(OrderForm.waiting_product)
    await bot.send_message(chat_id=..., text="Какой товар?")

@router.message_created(OrderForm.waiting_product)
async def get_product(update, state: FSMContext):
    await state.update_data(product=update.message.body.text)
    await state.set_state(OrderForm.waiting_quantity)

@router.message_created(OrderForm.confirm)
async def confirm_order(update, state: FSMContext):
    data = await state.get_data()
    await state.clear()  # Сбросить состояние и данные
```

```python
# Подключение FSM middleware:
from maxogram.fsm.middleware import FSMContextMiddleware
from maxogram.fsm.storage.memory import MemoryStorage

storage = MemoryStorage()
dp.update.outer_middleware.register(
    FSMContextMiddleware(storage=storage)
)
```

## Архитектура

- **`FSMContextMiddleware`** извлекает `user_id` и `chat_id` из контекста, формирует `StorageKey` по стратегии, создаёт `FSMContext` и кладёт в `data["state"]`
- **`FSMStrategy`** определяет scope состояния: per user per chat (default), per chat, или per user глобально
- **Storage** — подключаемое хранилище. `MemoryStorage` для разработки, `RedisStorage` для production (опциональная зависимость `maxogram[redis]`)

## Ссылки

- Связанные модули: `dispatcher/` (middleware pipeline), `filters/` (фильтрация по состоянию)
