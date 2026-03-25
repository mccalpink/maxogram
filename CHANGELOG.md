# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

## [1.1.0] - 2026-03-25

### Fixed

- **FilterObject awaitable для async callable-классов** — callable-экземпляры с `async def __call__` без наследования от `Filter` теперь корректно определяются как awaitable (#1)
- **outer_middleware на event observers** — `propagate_event()` теперь вызывает `wrap_outer_middleware`, outer middleware на `message_created`, `message_callback` и др. работают корректно (#3)
- **Типы event в документации** — исправлены все примеры: `MessageCreatedUpdate` → `Message`, `MessageCallbackUpdate` → `Callback` (#2)
- Отправка пустого `{}` тела для POST вместо `None` — исправлен 400 Empty request body при `answer_on_callback`
- Извлечение event-объектов из Update перед передачей в handlers
- 5 багов, найденных при тестировании MaxShop: утечка kwargs, парсинг ошибок API и др.
- 56 предупреждений ruff: неиспользуемые импорты, сортировка импортов, type-checking блоки

### Changed

- **BREAKING:** `Bot.send_message` и 12 других shortcut-методов — аргументы после первого позиционного стали keyword-only (`*`). Вызов `bot.send_message(chat_id, "текст")` теперь даёт `TypeError`, используйте `bot.send_message(chat_id, text="текст")` (#4)

### Added

- `drop_pending_updates` в polling, исправлен deep linking `startapp` → `start`

## [1.0.0] - 2026-03-22

### Added — Уникальные фичи Max

- **Message Constructor** — интерактивное конструирование сообщений (уникальная фича Max API)
- **Resumable Upload** — загрузка файлов до 4 GB чанками с возобновлением после сбоя

### Added — Расширения фреймворка

- **Scene** — высокоуровневый FSM для сложных диалогов (Scene, WizardScene, SceneRegistry)
- **I18n** — интернационализация через gettext (I18nMiddleware, LazyProxy)
- **Multi-bot** — поддержка нескольких ботов в одном Dispatcher
- **CallbackAnswerMiddleware** — автоответ на callback если хендлер не ответил
- **Request Middleware** — middleware на уровне HTTP-запросов (RetryMiddleware, LoggingMiddleware)

### Added — Утилиты

- **ChatActionSender** — автоматическая отправка typing/recording actions
- **MediaGroupBuilder** — групповая отправка медиа
- **Text Formatting** — Bold, Italic, Code, Link, Mention builders
- **Deep Linking** — create_start_link, encode_payload, decode_payload
- **WebApp Validation** — HMAC-SHA256 валидация initData

### Added — Storage

- **MongoStorage** — MongoDB-бэкенд для FSM (optional dependency: motor)

### Added — Инструменты

- **Schema Diff Tool** — CLI-инструмент сравнения OpenAPI schema с кодом (`poetry run schema-diff`)

## [0.1.0] - 2026-03-22

### Added

- **Webhook** — `WebhookHandler` (aiohttp), `WebhookManager` с auto-resubscribe (Max отписывает через 8ч)
- **Webhook Security** — `IPWhitelistMiddleware` с whitelist IP-подсетей Max
- **RedisStorage** — FSM storage на Redis для production-окружений
- **Расширенные фильтры** — `ChatTypeFilter`, `ContentTypeFilter`, `CallbackData`, `ExceptionTypeFilter`, `MagicData`
- **Class-based handlers** — `BaseHandler`, `MessageHandler`, `CallbackHandler`
- **Flags** — `FlagGenerator`, `get_flag`, `check_flag` для метаданных хендлеров
- **Media utils** — утилиты для работы с медиа-вложениями
- **Backoff** — `BackoffConfig` с exponential backoff для polling

### Fixed

- Исправлена утечка kwargs между хендлерами при `SkipHandler`
- Парсинг и хранение поля `code` в ошибках API
- Очистка мёртвого кода в session, исправлена сортировка импортов

## [0.0.1] - 2026-03-21

### Added

- **Types** — 96 Pydantic v2 моделей для всех сущностей Max Bot API (Message, Chat, User, Update, Attachment, Keyboard и др.)
- **Methods** — `MaxMethod[T]` и 30 типизированных методов API (messages, chats, members, callbacks, subscriptions, uploads, updates)
- **Client** — `Bot` с 30 shortcut-методами, `BaseSession` (ABC), `AiohttpSession`, `MaxAPIServer`
- **Exceptions** — иерархия исключений: `MaxError`, `MaxAPIError`, `NetworkError`, `TokenError`
- **Enums** — `ChatType`, `SenderAction`, `TextFormat`, `UploadType`, `AttachmentType` и др.
- **Dispatcher** — центральный координатор с feed_update, polling orchestration, workflow_data
- **Router** — дерево роутеров, 13 `MaxEventObserver` для всех типов событий Max API, propagation
- **Event system** — `EventObserver`, `MaxEventObserver` с фильтрами и middleware chain
- **Middleware** — `BaseMiddleware` (onion pattern), `MiddlewareManager`, `MaxContextMiddleware`, `ErrorsMiddleware`
- **Filters** — `Filter` (ABC), `Command` с `CommandObject`, `MagicFilter` (DSL)
- **FSM** — `State`, `StatesGroup`, `FSMContext`, `MemoryStorage`, `FSMContextMiddleware`
- **Polling** — long polling с exponential backoff, graceful shutdown, signal handling
- **DI** — `CallableObject`, `FilterObject`, `HandlerObject` для dependency injection
- **Keyboard** — `InlineKeyboardBuilder` с `button()`, `adjust()`, `as_attachment()`
- **Shortcuts** — `MessageCreatedUpdate.answer()`, `MessageCallbackUpdate.answer()`
- Интеграционные тесты, echo bot example
- Конфигурация: Poetry + PEP 621, ruff, mypy strict, pytest-asyncio, py.typed
