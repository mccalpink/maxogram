# Быстрый старт

## Установка

```bash
pip install maxogram
```

Или через Poetry:

```bash
poetry add maxogram
```

## Получение токена

1. Откройте [dev.max.ru](https://dev.max.ru/)
2. Создайте бота
3. Скопируйте токен

Установите токен в переменную окружения:

```bash
export MAX_BOT_TOKEN="your-token-here"
```

## Echo bot (polling)

Минимальный бот, который повторяет текстовые сообщения:

```python
import os

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.router import Router
from maxogram.types.update import MessageCreatedUpdate

router = Router()


@router.message_created()
async def echo(
    event: MessageCreatedUpdate,
    bot: Bot,
    **kwargs: object,
) -> None:
    text = event.message.body.text
    chat_id = event.message.recipient.chat_id
    if text and chat_id:
        await bot.send_message(chat_id=chat_id, text=text)


bot = Bot(token=os.environ["MAX_BOT_TOKEN"])
dp = Dispatcher()
dp.include_router(router)
dp.run_polling(bot)
```

`run_polling` запускает event loop, long polling и graceful shutdown по Ctrl+C.

## Обработка команд

Фильтр `Command` парсит команды из текста сообщения:

```python
from maxogram.filters import Command
from maxogram.filters.command import CommandObject


@router.message_created(Command("start"))
async def cmd_start(
    event: MessageCreatedUpdate,
    bot: Bot,
    command: CommandObject,
    **kwargs: object,
) -> None:
    chat_id = event.message.recipient.chat_id
    if chat_id:
        await bot.send_message(chat_id=chat_id, text="Привет! Я бот на maxogram.")


@router.message_created(Command("help"))
async def cmd_help(
    event: MessageCreatedUpdate,
    bot: Bot,
    command: CommandObject,
    **kwargs: object,
) -> None:
    chat_id = event.message.recipient.chat_id
    if chat_id:
        await bot.send_message(chat_id=chat_id, text="Доступные команды: /start, /help")
```

`CommandObject` содержит `prefix`, `command`, `args` — аргументы после команды.

## Inline-клавиатура и callback

Создание клавиатуры через `InlineKeyboardBuilder` и обработка нажатий:

```python
from maxogram.types.update import MessageCallbackUpdate
from maxogram.utils.keyboard import InlineKeyboardBuilder


@router.message_created(Command("menu"))
async def cmd_menu(
    event: MessageCreatedUpdate,
    bot: Bot,
    **kwargs: object,
) -> None:
    chat_id = event.message.recipient.chat_id
    if not chat_id:
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Option A", payload="a")
    builder.button(text="Option B", payload="b")
    builder.adjust(2)  # 2 кнопки в ряд

    await bot.send_message(
        chat_id=chat_id,
        text="Выберите:",
        attachments=[builder.as_attachment()],
    )


@router.message_callback()
async def on_callback(
    event: MessageCallbackUpdate,
    bot: Bot,
    **kwargs: object,
) -> None:
    callback = event.callback
    await bot.answer_on_callback(
        callback_id=callback.callback_id,
        notification=f"Вы выбрали: {callback.payload}",
    )
```

## FSM (конечные автоматы)

Диалоговые сценарии с сохранением состояния. `StateFilter` автоматически фильтрует хендлеры по текущему состоянию:

```python
from maxogram.filters import StateFilter
from maxogram.fsm.context import FSMContext
from maxogram.fsm.middleware import FSMContextMiddleware
from maxogram.fsm.state import State, StatesGroup
from maxogram.fsm.storage.memory import MemoryStorage


class OrderForm(StatesGroup):
    product = State()
    quantity = State()


@router.message_created(Command("order"))
async def cmd_order(
    event: MessageCreatedUpdate,
    bot: Bot,
    state: FSMContext,
    **kwargs: object,
) -> None:
    chat_id = event.message.recipient.chat_id
    if chat_id:
        await state.set_state(OrderForm.product)
        await bot.send_message(chat_id=chat_id, text="Какой товар?")


@router.message_created(StateFilter(OrderForm.product))
async def process_product(
    event: MessageCreatedUpdate,
    bot: Bot,
    state: FSMContext,
    **kwargs: object,
) -> None:
    text = event.message.body.text
    chat_id = event.message.recipient.chat_id
    if not chat_id:
        return
    await state.update_data(product=text)
    await state.set_state(OrderForm.quantity)
    await bot.send_message(chat_id=chat_id, text="Сколько штук?")


@router.message_created(StateFilter(OrderForm.quantity))
async def process_quantity(
    event: MessageCreatedUpdate,
    bot: Bot,
    state: FSMContext,
    **kwargs: object,
) -> None:
    text = event.message.body.text
    chat_id = event.message.recipient.chat_id
    if not chat_id:
        return
    await state.update_data(quantity=text)
    data = await state.get_data()
    await state.clear()
    await bot.send_message(
        chat_id=chat_id,
        text=f"Заказ: {data['product']} x {data['quantity']}",
    )
```

`StateFilter` поддерживает:
- Одно состояние: `StateFilter(OrderForm.product)`
- Несколько: `StateFilter(OrderForm.product, OrderForm.quantity)`
- Любое активное: `StateFilter("*")`
- Отсутствие состояния: `StateFilter(None)`

Подключение FSM middleware к Dispatcher:

```python
storage = MemoryStorage()  # или RedisStorage(redis=redis_client)
dp.update.outer_middleware.register(FSMContextMiddleware(storage=storage))
```

`MemoryStorage` подходит для разработки. В production используйте `RedisStorage`:

```python
from maxogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

redis = Redis(host="localhost", port=6379)
storage = RedisStorage(redis=redis)
```

## Webhook (production)

Для production-окружений вместо polling используйте webhook:

```python
import os

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.router import Router
from maxogram.webhook.manager import WebhookManager

router = Router()
# ... регистрация хендлеров ...

bot = Bot(token=os.environ["MAX_BOT_TOKEN"])
dp = Dispatcher()
dp.include_router(router)

manager = WebhookManager(
    dispatcher=dp,
    bot=bot,
    host="0.0.0.0",
    port=8080,
    path="/webhook",
)

import asyncio
asyncio.run(manager.start())
```

`WebhookManager` автоматически:
- Подписывает webhook при старте
- Переподписывается каждые 7.5 часов (Max отписывает через 8ч)
- Отписывается и останавливает сервер при shutdown

Для защиты от поддельных запросов используйте `IPWhitelistMiddleware`:

```python
from maxogram.webhook.security import IPWhitelistMiddleware

ip_mw = IPWhitelistMiddleware.for_max()
# Передайте в WebhookManager или добавьте в aiohttp app middleware
```

## Middleware

Создание собственного middleware:

```python
from maxogram.dispatcher.middlewares.base import BaseMiddleware


class LogMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        print(f"Получено событие: {type(event).__name__}")
        result = await handler(event, data)
        print(f"Обработано: {result}")
        return result


# outer — до фильтров
router.message_created.outer_middleware.register(LogMiddleware())

# inner — после фильтров, перед хендлером
router.message_created.inner_middleware.register(LogMiddleware())
```

## Вложенные роутеры

Модульная организация хендлеров:

```python
from maxogram.dispatcher.router import Router

# Отдельные модули
admin_router = Router(name="admin")
user_router = Router(name="user")

# Главный роутер
main_router = Router(name="main")
main_router.include_router(admin_router)
main_router.include_router(user_router)

# Dispatcher подключает главный роутер
dp = Dispatcher()
dp.include_router(main_router)
```

## Обработка ошибок (Error Handling)

Регистрация error handlers через `router.error()` — перехват исключений из хендлеров:

```python
from maxogram.dispatcher.middlewares.error import ErrorEvent
from maxogram.filters.exception import ExceptionTypeFilter


@router.error(ExceptionTypeFilter(ValueError))
async def handle_value_error(
    event: ErrorEvent,
    bot: Bot,
    **kwargs: object,
) -> bool:
    """Перехват ValueError."""
    print(f"ValueError: {event.exception}")
    return True  # ошибка обработана


@router.error()
async def handle_any_error(
    event: ErrorEvent,
    bot: Bot,
    **kwargs: object,
) -> bool:
    """Fallback — все остальные исключения."""
    print(f"Ошибка: {type(event.exception).__name__}: {event.exception}")
    return True
```

`ErrorEvent` содержит `.exception` (перехваченное исключение) и `.update` (оригинальное событие). `ExceptionTypeFilter` фильтрует по типу: `ExceptionTypeFilter(ValueError, TypeError)` — несколько типов. Хендлеры проверяются в порядке регистрации. Если вернуть `True` — ошибка считается обработанной.

Полный пример: `examples/error_handling.py`

## Scene — сложные диалоги

Когда FSM-диалог имеет много шагов и навигацию (вперёд/назад/перейти к шагу), удобнее использовать `WizardScene` вместо ручной проверки `raw_state`:

```python
from maxogram.fsm.scene.wizard import WizardScene
from maxogram.fsm.scene.registry import SceneRegistry
from maxogram.fsm.state import State, StatesGroup


class SurveyStates(StatesGroup):
    name = State()
    age = State()
    confirm = State()


class SurveyWizard(WizardScene, state=SurveyStates):
    """Wizard-сцена: имя -> возраст -> подтверждение."""

    async def on_enter(self, ctx, **kwargs):
        pass  # hook при входе


# Регистрация — подключает сцену как sub-router
registry = SceneRegistry(router=router)
registry.add(SurveyWizard)


@router.message_created()
async def cmd_start(event, bot, state, **kwargs):
    if (event.message.body.text or "").startswith("/start"):
        chat_id = event.message.recipient.chat_id
        await registry.enter(ctx=state, name="SurveyWizard")
        await bot.send_message(chat_id=chat_id, text="Как вас зовут?")
```

`WizardScene` предоставляет навигацию: `scene.next(state)`, `scene.back(state)`, `scene.goto(state, step=0)`, `scene.leave(state)`. Шаги определяются порядком State в StatesGroup.

`SceneRegistry` управляет переходами между сценами: при `registry.enter()` автоматически выходит из текущей сцены (если была) и входит в новую.

Для работы Scene необходим FSM middleware (см. секцию FSM).

Полный пример: `examples/scene_bot.py`

## Интернационализация (I18n)

Мультиязычность через GNU gettext — `.mo` файлы в директории `locales/`:

```python
from pathlib import Path
from maxogram.i18n.core import I18n
from maxogram.i18n.middleware import I18nMiddleware

i18n = I18n(path=Path("locales"), default_locale="ru", domain="messages")

# lazy_gettext — перевод вычисляется при str(), а не при определении
__ = i18n.lazy_gettext
WELCOME = __("Welcome to the bot!")


@router.message_created()
async def cmd_start(event, bot, gettext, **kwargs):
    """gettext инжектируется I18nMiddleware, привязан к текущей локали."""
    _ = gettext
    await bot.send_message(
        chat_id=event.message.recipient.chat_id,
        text=_("Hello! I'm a multilingual bot."),
    )
```

Подключение middleware:

```python
dp.update.outer_middleware.register(I18nMiddleware(i18n=i18n))
```

`I18nMiddleware` определяет локаль из `event.user_locale` (webhook payload) и инжектирует в хендлер: `gettext` (функция перевода), `i18n_locale` (текущая локаль), `i18n` (экземпляр I18n). Для кастомной логики определения языка передайте `locale_resolver`.

Полный пример: `examples/i18n_bot.py`

## Несколько ботов (Multi-bot)

Один Dispatcher может обслуживать несколько ботов — каждый получает свой polling loop:

```python
import os
from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher

bot1 = Bot(token=os.environ["MAX_BOT_TOKEN_1"])
bot2 = Bot(token=os.environ["MAX_BOT_TOKEN_2"])

dp = Dispatcher()
dp.include_router(router)

# Параллельный polling через asyncio.gather
dp.run_polling(bot1, bot2)
```

Хендлер автоматически получает тот экземпляр `Bot`, от которого пришёл update — через DI. Один и тот же хендлер обслуживает оба бота.

Полный пример: `examples/multibot.py`

## Загрузка больших файлов

`ResumableUpload` — chunked загрузка до 4 GB с поддержкой resume и progress callback:

```python
from maxogram.utils.resumable import ResumableInputFile

# Автоматический выбор: < 10 MB — обычная загрузка, >= 10 MB — chunked
file = ResumableInputFile(
    path="video.mp4",
    chunk_size=5 * 1024 * 1024,  # 5 MB чанки
    on_progress=lambda sent, total: print(f"{sent}/{total} bytes"),
)
token = await file.upload(bot)
```

`ResumableInputFile` наследует `MaxInputFile` и автоматически выбирает стратегию по `threshold` (по умолчанию 10 MB). При сетевом сбое `ResumableUpload.upload()` можно вызвать повторно — продолжит с позиции `bytes_sent`.

## Утилиты

### ChatActionSender

Периодическая отправка typing/uploading status, пока выполняется долгая операция:

```python
from maxogram.utils.chat_action import ChatActionSender

async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
    result = await heavy_computation()
    await bot.send_message(chat_id=chat_id, text=result)
```

Также доступны: `upload_photo()`, `upload_video()`, `upload_audio()`, `upload_file()`.

### MediaGroupBuilder

Отправка нескольких медиа-файлов в одном сообщении:

```python
from maxogram.utils.media_group import MediaGroupBuilder

builder = MediaGroupBuilder()
builder.add_photo(token="upload_token_1")
builder.add_video(token="upload_token_2")
await bot.send_message(chat_id=chat_id, attachments=builder.build())
```

### Text Formatting

Форматирование текста с markup-элементами Max API:

```python
from maxogram.utils.formatting import Bold, Italic, Code, Text

node = Text("Привет, ") + Bold("мир") + Text("! Это ") + Code("код")
text, markup = node.render()
await bot.send_message(chat_id=chat_id, text=text, markup=markup)
```

Доступны: `Bold`, `Italic`, `Code`, `Pre`, `Underline`, `Strikethrough`, `Heading`, `Highlight`, `Link`, `UserMention`. Конвертеры: `as_html(node)`, `as_markdown(node)`.

### Deep Linking

Генерация ссылок для запуска бота с параметрами:

```python
from maxogram.utils.deep_linking import create_start_link, encode_payload, decode_payload

link = create_start_link(username="mybot", payload=encode_payload("ref=promo"))
# https://max.ru/mybot?start=cmVmPXByb21v

original = decode_payload("cmVmPXByb21v")  # "ref=promo"
```
