# dispatcher

Маршрутизация событий, middleware pipeline и orchestration. Центральный модуль фреймворка.

## Основные классы

| Класс | Описание |
|-------|----------|
| `Dispatcher` | Корневой координатор: наследует `Router`, добавляет `feed_update()`, polling, startup/shutdown |
| `Router` | Маршрутизатор событий. Содержит observer для каждого из 13 типов событий Max API |
| `MaxEventObserver` | Observer для одного типа события. Хранит хендлеры, фильтры, inner/outer middleware |
| `EventObserver` | Простой observer для lifecycle-событий (startup, shutdown) |
| `HandlerObject` | Обёртка хендлера с фильтрами, DI, флагами |
| `CallableObject` | DI-обёртка callable: интроспекция параметров, автоматическая фильтрация kwargs |
| `BaseMiddleware` | ABC для middleware (onion pattern) |

## Использование

```python
from maxogram.client import Bot
from maxogram.dispatcher import Dispatcher, Router

dp = Dispatcher()
router = Router()

@router.message_created(Command("start"))
async def on_start(update, bot):
    await bot.send_message(chat_id=update.message.recipient.chat_id, text="Привет!")

dp.include_router(router)
bot = Bot(token="your_token")
dp.run_polling(bot)
```

```python
# Middleware (onion pattern):
from maxogram.dispatcher.middlewares.base import BaseMiddleware

class LogMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        print(f"Event: {event.update_type}")
        return await handler(event, data)

router.message_created.middleware.register(LogMiddleware())
```

```python
# Вложенные роутеры:
admin_router = Router(name="admin")
user_router = Router(name="user")
dp.include_routers(admin_router, user_router)
```

## Архитектура

```
Dispatcher (extends Router)
 ├── feed_update(bot, update) — точка входа для всех update
 ├── update observer → outer middleware → _listen_update → propagate_event
 ├── start_polling() / run_polling() — запуск long polling
 ├── workflow_data — глобальный контекст (dict-like доступ)
 └── Router tree
      ├── 13 MaxEventObserver (message_created, message_callback, ...)
      ├── error observer — перехват ошибок из хендлеров
      ├── startup / shutdown EventObserver
      ├── sub_routers — дерево вложенных роутеров
      └── propagate_event() — рекурсивный обход дерева
```

- **Событие проходит:** `feed_update → outer middleware → _listen_update → propagate_event → observer.trigger → inner middleware → handler`
- **DI:** `CallableObject` анализирует сигнатуру callback и передаёт только объявленные параметры из `data`
- **Фильтры:** AND-логика. Фильтр может обогатить kwargs хендлера (вернув `dict`)
- **Встроенные outer middleware:** `ErrorsMiddleware` (перехват ошибок), `MaxContextMiddleware` (извлечение user/chat из update)

## Ссылки

- Связанные модули: `filters/` (фильтры), `handlers/` (class-based handlers), `fsm/` (FSM middleware), `polling/` (polling loop), `webhook/` (webhook handler)
