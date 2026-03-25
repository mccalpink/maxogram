# polling

Long polling клиент для получения обновлений от Max Bot API.

## Основные классы

| Класс | Описание |
|-------|----------|
| `Polling` | Long polling loop: цикл `GetUpdates` с marker tracking, backoff при ошибках, graceful stop |

## Использование

```python
from maxogram.client import Bot
from maxogram.dispatcher import Dispatcher

dp = Dispatcher()
bot = Bot(token="your_token")

# Рекомендуемый способ — через Dispatcher:
dp.run_polling(bot)

# Или async:
await dp.start_polling(
    bot,
    polling_timeout=30,
    allowed_updates=["message_created", "message_callback"],
)
```

```python
# Настройка backoff:
from maxogram.utils.backoff import BackoffConfig

await dp.start_polling(
    bot,
    backoff_config=BackoffConfig(
        min_delay=1.0,
        max_delay=60.0,
        factor=2.0,
        jitter=True,
    ),
)
```

## Архитектура

- `Polling` создаётся внутри `Dispatcher.start_polling()` и не предназначен для прямого использования
- Цикл: `GetUpdates(timeout, marker, types)` → обработка каждого update через `dispatcher.feed_update()` → обновление marker
- При ошибке — exponential backoff с jitter (через `Backoff`). При успехе — сброс backoff
- `stop()` устанавливает `asyncio.Event`, цикл завершается после текущего запроса
- `allowed_updates` автоматически определяется из зарегистрированных хендлеров (`resolve_used_update_types`)

## Ссылки

- [Max Bot API — получение обновлений](https://dev.max.ru/)
- Связанные модули: `dispatcher/` (orchestration и feed_update), `webhook/` (альтернативный transport), `utils/backoff.py` (retry-логика)
