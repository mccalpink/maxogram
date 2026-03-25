# Архитектура maxogram

## Обзор

maxogram — многослойный фреймворк. Каждый слой зависит только от нижестоящих, что обеспечивает разделение ответственности и тестируемость.

```
User Code (handlers, filters, middleware)
         |
    Dispatcher / Router
         |
      Client (Bot)
         |
    Session (HTTP)
         |
    Methods + Types
```

## Слои

### Types (модели данных)

Pydantic v2 модели для всех сущностей Max Bot API: `Message`, `Chat`, `User`, `Update`, `Attachment`, `Keyboard` и др.
96 классов с валидацией, сериализацией и discriminated unions для полиморфных типов (Update, Attachment).

Базовый класс `MaxObject` обеспечивает привязку к `Bot` — модели получают доступ к API через `set_bot()`.

### Methods (API-методы)

`MaxMethod[T]` — generic базовый класс для API-запросов. Каждый метод знает свой HTTP verb, path и тип ответа.
30 методов покрывают все endpoints Max Bot API: messages, chats, members, callbacks, subscriptions, uploads, updates.

### Client (Bot + Session)

- **Bot** — фасад: хранит token, предоставляет 30 shortcut-методов (`send_message`, `get_chat` и т.д.), делегирует HTTP в Session
- **BaseSession** (ABC) — контракт HTTP-транспорта
- **AiohttpSession** — реализация на aiohttp: сериализация `MaxMethod`, HTTP-вызов, десериализация ответа, обработка ошибок

### Dispatcher + Router (маршрутизация)

**Router** содержит 13 `MaxEventObserver` — по одному для каждого типа события Max API:
`message_created`, `message_callback`, `message_edited`, `message_removed`, `bot_started`, `bot_added`, `bot_removed`, `user_added`, `user_removed`, `chat_title_changed`, `message_constructed`, `message_construction_request`, `message_chat_created`.

Роутеры образуют дерево через `include_router()`. Событие проходит по дереву: сначала текущий роутер, затем sub_routers. Первый обработавший хендлер останавливает propagation.

**Dispatcher** наследует Router и добавляет:
- `feed_update()` — точка входа для обновлений
- Встроенные outer middleware (`ErrorsMiddleware`, `MaxContextMiddleware`)
- Polling orchestration (`run_polling`, `start_polling`)
- `workflow_data` — глобальный контекст для хендлеров

### Event System

```
MaxEventObserver
├── outer_middleware chain
│   └── trigger()
│       ├── filter check (Filter chain)
│       ├── inner_middleware chain
│       │   └── handler()
│       └── fallback: UNHANDLED
```

**HandlerObject** оборачивает callback и список фильтров. При trigger:
1. Проход по registered handlers
2. Для каждого — проверка фильтров
3. Если все фильтры пройдены — вызов handler через inner middleware
4. DI: аргументы handler резолвятся из `data` dict (bot, state, event и др.)

### Filters (фильтрация)

Абстрактный `Filter` с методом `__call__(event, **kwargs) -> dict | False`.
При совпадении фильтр возвращает dict с данными (например, `{"command": CommandObject(...)}`), которые мерджатся в kwargs хендлера.

Встроенные фильтры:

| Фильтр | Назначение |
|--------|-----------|
| `Command` | Команды (`/start`, `/help`) с парсингом аргументов |
| `StateFilter` | Фильтрация по FSM-состоянию (одно, несколько, wildcard `"*"`, `None`) |
| `ChatTypeFilter` | Фильтрация по типу чата (dialog, chat, channel) |
| `ContentTypeFilter` | Фильтрация по типу вложения (photo, video, file) |
| `CallbackData` | Типизированные callback-данные (Pydantic модель) |
| `MagicData` | DSL-фильтрация через MagicFilter по данным контекста |
| `ExceptionTypeFilter` | Фильтрация ошибок по типу исключения |

`MagicFilter` (`F`) предоставляет DSL для лаконичных фильтров: `F.message.body.text == "hello"`.

### Middleware

Onion-pattern: каждый middleware получает `handler`, `event`, `data` и решает, вызывать ли handler.

Два уровня:
- **outer_middleware** — выполняется до фильтров (логирование, throttling, контекст)
- **inner_middleware** — выполняется после фильтров, перед хендлером

Встроенные middleware:
- `ErrorsMiddleware` — перехват исключений, вызов error observer
- `MaxContextMiddleware` — наполнение `data` контекстными объектами (event_chat, event_from_user и др.)
- `FSMContextMiddleware` — инъекция `state: FSMContext` и `raw_state` в хендлеры
- `CallbackAnswerMiddleware` — автоматический ответ на callback-запросы

#### HTTP-level middleware (Session)

Отдельный слой middleware для HTTP-запросов к Max Bot API (`client/session/middleware.py`):
- `RequestMiddleware` (ABC) — базовый класс для HTTP-level middleware
- `RetryMiddleware` — автоматический retry при 429/5xx с exponential backoff
- `LoggingMiddleware` — логирование HTTP-запросов к API

### FSM (конечные автоматы)

- `State` / `StatesGroup` — декларативное описание состояний
- `FSMContext` — управление текущим состоянием и данными (set_state, get_data, update_data, clear)
- `FSMStrategy` — стратегия формирования ключа: `USER_IN_CHAT` (default), `CHAT`, `GLOBAL_USER`
- `BaseStorage` (ABC) — контракт хранилища
- `MemoryStorage` — in-memory (для разработки и тестов)
- `RedisStorage` — Redis (для production, горизонтальное масштабирование)
- `MongoStorage` — MongoDB (альтернатива Redis)

### Scene (сцены для сложных диалогов)

Абстракция поверх FSM для пошаговых диалогов:
- `Scene` — базовый класс сцены с lifecycle hooks (`on_enter`, `on_leave`)
- `WizardScene` — сцена с навигацией: `next()`, `back()`, `goto(step)`, `leave()`
- `SceneRegistry` — реестр сцен, управление переходами между ними

Шаги определяются порядком State в StatesGroup. `SceneRegistry.add()` подключает сцену как sub-router.

### I18n (интернационализация)

GNU gettext / Babel:
- `I18n` — менеджер переводов: загрузка `.mo` файлов, `gettext()`, `lazy_gettext()`
- `I18nMiddleware` — определение локали из `event.user_locale`, инъекция `gettext`, `i18n_locale`, `i18n` в хендлеры
- `LazyProxy` — ленивые строки, вычисляемые при `str()`

### Webhook

- `WebhookHandler` — aiohttp request handler: парсинг JSON -> `Update` -> `feed_update`
- `WebhookManager` — lifecycle: запуск aiohttp server, подписка/отписка webhook, auto-resubscribe (Max отписывает через 8ч), graceful shutdown
- `IPWhitelistMiddleware` — aiohttp middleware для проверки IP отправителя

### Polling

Long polling с `GetUpdates`. `BackoffConfig` для exponential backoff при ошибках.
Graceful shutdown через signal handler (SIGINT, SIGTERM).

### Утилиты

- `InlineKeyboardBuilder` — построитель inline-клавиатур с `adjust()` для раскладки по рядам
- `ChatActionSender` — периодическая отправка typing/uploading status (async context manager)
- `MediaGroupBuilder` — сборка нескольких медиа-вложений для одного сообщения
- `Text`, `Bold`, `Italic`, `Code` и др. — builder pattern для форматирования текста с markup
- `ResumableUpload` / `ResumableInputFile` — chunked загрузка файлов до 4 GB с resume
- `create_start_link`, `encode_payload`, `decode_payload` — deep linking
- `validate_init_data`, `parse_init_data` — валидация WebApp initData (HMAC-SHA256)

## Data flow

### Polling

```
Bot.get_updates()
    -> [Update, ...]
    -> Dispatcher.feed_update(bot, update)
        -> outer_middleware chain (ErrorsMiddleware, MaxContextMiddleware, ...)
            -> Dispatcher._listen_update()
                -> Router.propagate_event(update_type, event)
                    -> MaxEventObserver.trigger(event)
                        -> filter chain
                            -> inner_middleware chain
                                -> handler(event, bot=bot, state=state, ...)
```

### Webhook

```
HTTP POST /webhook (JSON body)
    -> WebhookHandler (aiohttp)
        -> parse JSON -> Update (Pydantic)
        -> Dispatcher.feed_update(bot, update)
            -> (тот же pipeline, что и polling)
```

## Расширяемость

- **Custom Filters** — наследование от `Filter`, реализация `__call__`
- **Custom Middleware** — наследование от `BaseMiddleware`
- **Custom Storage** — наследование от `BaseStorage` (FSM)
- **Custom Session** — наследование от `BaseSession` (HTTP-транспорт)
- **Custom Request Middleware** — наследование от `RequestMiddleware` для HTTP-level перехвата
- **Class-based handlers** — наследование от `BaseHandler` / `MessageHandler` / `CallbackHandler`
- **Router tree** — произвольная вложенность для модульной организации хендлеров
- **Flags** — `FlagGenerator` для передачи метаданных от хендлеров в middleware
- **Custom Scenes** — наследование от `Scene` / `WizardScene` для сложных диалогов
