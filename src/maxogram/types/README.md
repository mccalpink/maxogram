# types

Pydantic v2 модели данных Max Bot API. Полное покрытие всех типов, которые возвращает и принимает API.

## Основные классы

| Класс | Описание |
|-------|----------|
| `MaxObject` | Базовый класс всех типов. Хранит ссылку на `Bot` для shortcuts |
| `Message`, `MessageBody` | Сообщение и его тело (текст, вложения, разметка) |
| `Chat`, `ChatMember` | Чат и участник чата |
| `User`, `BotInfo` | Пользователь и информация о боте |
| `Callback`, `CallbackAnswer` | Callback-запрос и ответ на него |
| `Update` (discriminated union) | Входящее обновление от API. 13 подтипов по `update_type` |
| `Attachment` (union) | Вложение: фото, видео, аудио, файл, стикер, контакт, геолокация |
| `Button` (union) | Кнопка inline-клавиатуры: callback, link, contact, geo, chat |
| `Keyboard` | Inline-клавиатура (ряды кнопок) |
| `MarkupElement` (union) | Разметка текста: bold, italic, code, ссылка, упоминание |
| `Subscription` | Webhook-подписка |
| `UploadEndpoint` | URL для загрузки файлов |

## Использование

```python
from maxogram.types import Message, CallbackButton, Keyboard

# Типы создаются автоматически при получении update от API.
# Ручное создание — для отправки:

button = CallbackButton(text="Нажми", payload="action:1")
keyboard = Keyboard(buttons=[[button]])
```

```python
from maxogram.types import Update, MessageCreatedUpdate

# Discriminated union — Pydantic автоматически выбирает подтип:
data = {"update_type": "message_created", "timestamp": 123, "message": {...}}
update = Update.model_validate(data)  # -> MessageCreatedUpdate
```

## Архитектура

- **`MaxObject`** — базовый класс с `extra="allow"` (forward-compatibility с новыми полями API) и рекурсивным `set_bot()` для shortcuts (`message.answer()`)
- **Discriminated unions** — `Update` и `Attachment` используют Pydantic discriminator для автоматического выбора подтипа
- **Alias-маппинг** — Python snake_case поля маппятся на camelCase API через `alias`
- Модели разделены по файлам: `message.py`, `chat.py`, `user.py`, `update.py`, `attachment.py`, `button.py`, `keyboard.py`, `markup.py`, `callback.py`, `misc.py`

## Ссылки

- [Max Bot API — типы данных](https://dev.max.ru/)
- Связанные модули: `methods/` (используют типы как `__returning__`), `client/` (Bot propagates `set_bot`)
