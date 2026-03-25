# webhook

Приём обновлений от Max через HTTP webhook. Включает handler для обработки запросов, менеджер lifecycle и IP-фильтрацию.

## Основные классы

| Класс | Описание |
|-------|----------|
| `WebhookHandler` | Aiohttp web handler: парсит JSON payload в `Update`, передаёт в `Dispatcher` |
| `WebhookManager` | Lifecycle менеджер: запуск сервера, подписка/отписка, auto-reconnect, graceful shutdown |
| `IPWhitelistMiddleware` | Aiohttp middleware для проверки IP-адреса запроса по whitelist |

## Использование

```python
from maxogram.client import Bot
from maxogram.dispatcher import Dispatcher
from maxogram.webhook import WebhookManager

dp = Dispatcher()
bot = Bot(token="your_token")

# Простой запуск:
manager = WebhookManager(dp, bot, host="0.0.0.0", port=8080)
manager.run("https://example.com/webhook")
```

```python
# С IP-фильтрацией:
from maxogram.webhook.security import IPWhitelistMiddleware

ip_mw = IPWhitelistMiddleware.for_max()  # Известные IP Max
# или кастомный whitelist:
ip_mw = IPWhitelistMiddleware(trusted_ips=["10.0.0.0/8"])
```

```python
# Async запуск с настройками:
manager = WebhookManager(
    dp, bot,
    host="0.0.0.0",
    port=8080,
    path="/webhook",
    allowed_updates=["message_created", "message_callback"],
    resubscribe_interval=7.5 * 3600,  # Max отписывает через 8ч
    close_bot_session=True,
)
await manager.start("https://example.com/webhook")
```

## Архитектура

- **`WebhookHandler`** — принимает POST, парсит JSON в discriminated union `Update` через Pydantic `TypeAdapter`, передаёт в `dispatcher.feed_update()`. Неизвестные `update_type` пропускаются с 200 OK (чтобы Max не отписал webhook)
- **`WebhookManager`** — orchestration: создаёт aiohttp app, запускает `AppRunner`, подписывается через `bot.subscribe()`, запускает periodic resubscribe (Max отписывает webhook через 8 часов без 200 OK), graceful shutdown с отпиской
- **`IPWhitelistMiddleware`** — проверка IP по CIDR whitelist. Factory `for_max()` содержит известные IP Max. Поддержка `X-Forwarded-For` для reverse proxy

## Ссылки

- [Max Bot API — webhook](https://dev.max.ru/)
- Связанные модули: `dispatcher/` (feed_update), `client/` (subscribe/unsubscribe), `polling/` (альтернативный transport)
