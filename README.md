# maxogram

[![Python](https://img.shields.io/pypi/pyversions/maxogram)](https://pypi.org/project/maxogram/)
[![PyPI](https://img.shields.io/pypi/v/maxogram)](https://pypi.org/project/maxogram/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1487%20passed-brightgreen)]()
[![mypy](https://img.shields.io/badge/mypy-strict-blue)]()

Асинхронный Python-фреймворк для [Max Bot API](https://dev.max.ru/), вдохновленный [aiogram](https://github.com/aiogram/aiogram).
Предоставляет типизированный, расширяемый интерфейс для создания ботов в мессенджере [Max](https://max.ru).

## Возможности

### Ядро фреймворка

- **Полное покрытие Max Bot API** — 30 методов, 96 типов, все 13 типов событий
- **Router + Dispatcher** — дерево роутеров с propagation событий, вложенность, lifecycle hooks
- **Фильтры** — Command, ChatType, ContentType, CallbackData, MagicFilter (DSL), ExceptionType
- **Middleware** — onion pattern, inner/outer и request-level middleware (RetryMiddleware, LoggingMiddleware)
- **FSM** — конечные автоматы с MemoryStorage, RedisStorage и MongoStorage
- **Scene** — высокоуровневый FSM для сложных диалогов (Scene, WizardScene, SceneRegistry)
- **Multi-bot** — несколько ботов в одном Dispatcher
- **Webhook** — aiohttp handler, WebhookManager с auto-resubscribe, IP whitelist security
- **Polling** — long polling с exponential backoff и graceful shutdown
- **Keyboard builder** — InlineKeyboardBuilder с `adjust()` для раскладки кнопок
- **Class-based handlers** — BaseHandler, MessageHandler, CallbackHandler
- **Flags** — декораторы метаданных на хендлерах для use-case-specific middleware
- **Dependency Injection** — автоматическое внедрение `bot`, `state`, `event` в хендлеры
- **Типизация** — `py.typed`, mypy strict, Pydantic v2 модели

### Уникальные фичи Max

- **Message Constructor** — интерактивное конструирование сообщений (нативная фича Max API)
- **Resumable Upload** — загрузка файлов до 4 GB чанками с возобновлением после сбоя

### Утилиты

- **I18n** — интернационализация через gettext (I18nMiddleware, LazyProxy)
- **Text Formatting** — Bold, Italic, Code, Link, UserMention builders
- **ChatActionSender** — автоматическая отправка typing/recording actions
- **MediaGroupBuilder** — групповая отправка медиа
- **Deep Linking** — create_start_link, encode_payload, decode_payload
- **WebApp Validation** — HMAC-SHA256 валидация initData
- **CallbackAnswerMiddleware** — автоответ на callback если хендлер не ответил

## Установка

```bash
pip install maxogram
```

Дополнительные зависимости:

```bash
pip install maxogram[redis]   # RedisStorage для FSM
pip install maxogram[mongodb]  # MongoStorage для FSM
pip install maxogram[fast]    # uvloop + aiodns
pip install maxogram[proxy]   # SOCKS-прокси
pip install maxogram[i18n]    # интернационализация (gettext)
```

## Быстрый старт

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
    """Повторяет любое текстовое сообщение."""
    text = event.message.body.text
    chat_id = event.message.recipient.chat_id
    if text and chat_id:
        await bot.send_message(chat_id=chat_id, text=text)


bot = Bot(token=os.environ["MAX_BOT_TOKEN"])
dp = Dispatcher()
dp.include_router(router)
dp.run_polling(bot)
```

Больше примеров: [`examples/`](examples/)

## Основные концепции

### Router

Маршрутизатор событий. Содержит observer для каждого из 13 типов событий Max API.
Роутеры вкладываются друг в друга, образуя дерево — событие проходит по дереву до первого обработчика.

```python
main_router = Router(name="main")
admin_router = Router(name="admin")
main_router.include_router(admin_router)
```

### Filters

Фильтры определяют, какой хендлер обработает событие. Встроенные фильтры:
`Command`, `ChatTypeFilter`, `ContentTypeFilter`, `CallbackData`, `MagicData`, `ExceptionTypeFilter`.

```python
from maxogram.filters import Command

@router.message_created(Command("start"))
async def cmd_start(event, bot, command, **kwargs):
    ...
```

### Middleware

Onion-pattern middleware для pre/post обработки. Два уровня: `outer_middleware` (до фильтров) и `inner_middleware` (после фильтров, перед хендлером).

```python
from maxogram.dispatcher.middlewares.base import BaseMiddleware

class LogMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        print(f"Event: {event}")
        return await handler(event, data)

router.message_created.outer_middleware.register(LogMiddleware())
```

### FSM

Конечные автоматы для диалоговых сценариев. `State` + `StatesGroup` описывают состояния, `FSMContext` управляет переходами и данными.

```python
from maxogram.fsm.state import State, StatesGroup
from maxogram.fsm.context import FSMContext

class Form(StatesGroup):
    name = State()
    age = State()

@router.message_created()
async def ask_name(event, bot, state: FSMContext, **kwargs):
    await state.set_state(Form.name)
    ...
```

### Webhook

Production-ready webhook с aiohttp. WebhookManager управляет lifecycle, auto-resubscribe и graceful shutdown.
IPWhitelistMiddleware защищает endpoint от поддельных запросов.

## Инструменты разработчика

### Schema Diff Tool

CLI-инструмент для сравнения OpenAPI-схемы Max Bot API с кодом библиотеки. Помогает отслеживать расхождения при обновлении API.

```bash
poetry run schema-diff                        # сравнить с актуальной схемой
poetry run schema-diff --schema path/to/openapi.json  # указать путь к схеме
```

Выводит: новые методы в API, удалённые методы, изменённые параметры.

## Документация

- [Быстрый старт](docs/quickstart.md)
- [Архитектура](docs/architecture.md)
- [Примеры](examples/)
- [Max Bot API](https://dev.max.ru/)

## Требования

- Python 3.11+
- aiohttp >= 3.9
- pydantic >= 2.4
- magic-filter >= 1.0.12
- aiofiles >= 23.2
- certifi >= 2023.7

## Лицензия

[MIT](LICENSE)
