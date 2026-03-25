# client

HTTP-клиент для Max Bot API. Содержит `Bot` (фасад) и систему сессий (transport layer).

## Основные классы

| Класс | Описание |
|-------|----------|
| `Bot` | Главный фасад: хранит token, 30 shortcut-методов для всех API endpoints |
| `BaseSession` | ABC для HTTP-сессий. Определяет контракт `make_request`, `check_response`, `stream_content` |
| `AiohttpSession` | Реализация сессии на aiohttp. Используется по умолчанию |
| `MaxAPIServer` | Конфигурация API-сервера (base URL: `https://platform-api.max.ru`) |

## Использование

```python
from maxogram.client import Bot

bot = Bot(token="your_token")

# Shortcut-методы:
info = await bot.get_my_info()
await bot.send_message(chat_id=123, text="Привет!")
chat = await bot.get_chat(chat_id=456)

# Или через MaxMethod напрямую:
from maxogram.methods import SendMessage
result = await bot(SendMessage(chat_id=123, text="Привет!"))

# Async context manager:
async with Bot(token="your_token") as bot:
    await bot.send_message(chat_id=123, text="Привет!")
```

```python
# Кастомная сессия:
from maxogram.client.session.base import BaseSession
from maxogram.client.server import MaxAPIServer

bot = Bot(
    token="your_token",
    session=AiohttpSession(
        api=MaxAPIServer(base_url="https://custom-api.example.com"),
        timeout=30.0,
    ),
)
```

## Архитектура

```
Bot
 ├── token
 ├── session: BaseSession (default: AiohttpSession)
 │    ├── api: MaxAPIServer (base URL)
 │    ├── make_request() — выполнение HTTP-запроса
 │    ├── check_response() — парсинг ответа, маппинг ошибок
 │    └── stream_content() — потоковое скачивание файлов
 └── __call__(method) — Bot(method) → session(bot, method) → result.set_bot(bot)
```

- **Bot** — фасад. Создаёт `MaxMethod`, передаёт в `Session`, ставит `set_bot()` на результат для shortcuts
- **BaseSession** — абстракция transport layer. Позволяет заменить aiohttp на httpx, curl и т.д.
- **AiohttpSession** — реализация с lazy-init `ClientSession`, Authorization header, JSON body
- **check_response** — маппинг HTTP-ошибок в типизированные исключения (`MaxAPIError` и подклассы)

## Ссылки

- [Max Bot API — авторизация](https://dev.max.ru/)
- Связанные модули: `methods/` (API-методы), `types/` (результаты), `exceptions.py` (ошибки)
