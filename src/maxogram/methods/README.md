# methods

Декларативные объекты API-методов Max Bot API. Каждый метод — Pydantic-модель с метаданными для HTTP-запроса.

## Основные классы

| Класс | API endpoint | HTTP |
|-------|-------------|------|
| `MaxMethod[T]` | — | Базовый класс всех методов |
| `GetMyInfo` | `GET /me` | Информация о боте |
| `EditMyInfo` | `PATCH /me` | Редактирование бота |
| `SendMessage` | `POST /messages` | Отправка сообщения |
| `EditMessage` | `PUT /messages` | Редактирование сообщения |
| `DeleteMessage` | `DELETE /messages` | Удаление сообщения |
| `GetMessages` | `GET /messages` | Список сообщений |
| `GetChat` | `GET /chats/{chatId}` | Информация о чате |
| `GetChats` | `GET /chats` | Список чатов |
| `GetMembers` | `GET /chats/{chatId}/members` | Участники чата |
| `AnswerOnCallback` | `POST /answers` | Ответ на callback |
| `GetUpdates` | `GET /updates` | Long polling |
| `Subscribe` / `Unsubscribe` | `POST/DELETE /subscriptions` | Webhook |
| `GetUploadUrl` | `POST /uploads` | URL для загрузки файлов |

## Использование

```python
from maxogram.methods import SendMessage, GetChat

# Методы — чистые data-объекты. Выполняются через Bot:
method = SendMessage(chat_id=123, text="Привет!")
result = await bot(method)

# Или через shortcut:
result = await bot.send_message(chat_id=123, text="Привет!")
```

```python
from maxogram.methods.base import MaxMethod

# Каждый метод определяет:
# __api_path__    — URL path ("/messages", "/chats/{chatId}")
# __http_method__ — GET, POST, PUT, PATCH, DELETE
# __returning__   — тип результата (Pydantic-модель)
# __query_params__ — поля для URL query string
# __path_params__  — поля для подстановки в URL path
```

## Архитектура

`MaxMethod[T]` наследует `MaxObject` и `Generic[T]`. Это чистый data-объект без логики выполнения HTTP-запроса. Вся логика разбора параметров (path, query, body) и выполнения запроса — в `BaseSession`.

Методы разделены по файлам: `bot.py`, `chat.py`, `message.py`, `member.py`, `pin.py`, `callback.py`, `subscription.py`, `update.py`, `upload.py`.

## Ссылки

- [Max Bot API — методы](https://dev.max.ru/)
- Связанные модули: `types/` (возвращаемые типы), `client/session/` (выполнение запросов), `client/bot.py` (shortcut-методы)
