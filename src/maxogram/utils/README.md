# utils

Утилиты библиотеки: построитель клавиатур, загрузка файлов, форматирование текста, chat actions, медиа-группы, deep linking, WebApp validation, backoff, расширение MagicFilter.

## Основные классы

| Класс / Функция | Модуль | Описание |
|-----------------|--------|----------|
| `InlineKeyboardBuilder` | `keyboard.py` | Fluent API для построения inline-клавиатур с `adjust()` |
| `MaxInputFile` | `media.py` | ABC загрузки файлов в Max API (двухэтапная: get URL → POST file) |
| `BufferedInputFile` | `media.py` | Загрузка из `bytes` в памяти |
| `FSInputFile` | `media.py` | Загрузка файла с диска |
| `URLInputFile` | `media.py` | Скачивание по URL и загрузка |
| `TokenInputFile` | `media.py` | Переиспользование ранее загруженного файла по token |
| `BackoffConfig` / `Backoff` | `backoff.py` | Exponential backoff с jitter для retry-логики |
| `MagicFilter` | `magic_filter.py` | Расширение magic-filter с методом `.as_()` для сохранения результата в kwargs |
| `Text`, `Bold`, `Italic`, `Code`, `Link`, ... | `formatting.py` | Builder pattern для форматирования текста с markup Max API |
| `ChatActionSender` | `chat_action.py` | Async context manager для периодической отправки chat actions |
| `MediaGroupBuilder` | `media_group.py` | Fluent API для сборки нескольких вложений в одном сообщении |
| `create_start_link`, `encode_payload`, `decode_payload` | `deep_linking.py` | Deep linking: генерация URL и кодирование/декодирование payload |
| `validate_init_data`, `parse_init_data` | `webapp.py` | WebApp Validation: HMAC-SHA256 проверка initData |
| `ResumableUpload`, `ResumableInputFile` | `resumable.py` | Chunked upload больших файлов (до 4 GB) с Content-Range |
| `schema_diff/` | `schema_diff/` | CLI-инструмент для сравнения OpenAPI schema с кодом ([README](schema_diff/README.md)) |

## Использование

```python
from maxogram.utils.keyboard import InlineKeyboardBuilder

builder = InlineKeyboardBuilder()
builder.button(text="Да", payload="yes")
builder.button(text="Нет", payload="no")
builder.button(text="Сайт", url="https://example.com")
builder.adjust(2, 1)  # первый ряд — 2 кнопки, второй — 1

attachment = builder.as_attachment()
await bot.send_message(chat_id=123, text="Выберите:", attachments=[attachment])
```

```python
from maxogram.utils.media import BufferedInputFile, FSInputFile

# Из памяти:
file = BufferedInputFile(data=b"...", filename="report.pdf")
token = await file.upload(bot)

# С диска:
file = FSInputFile("/path/to/photo.jpg")
token = await file.upload(bot)
```

```python
from maxogram.utils.formatting import Bold, Italic, Text, Link, as_html

# Builder pattern: Text + Bold + Link → text + markup[]
node = Text("Привет ") + Bold("мир") + Text("! ") + Link("Ссылка", url="https://max.ru")
text, markup = node.render()
# text = "Привет мир! Ссылка"
# markup = [StrongMarkup(from_=7, length=3), LinkMarkup(from_=12, length=6, ...)]

# Конвертация в HTML/Markdown:
html = as_html(Bold("жирный") + Italic(" курсив"))
# → "<b>жирный</b><i> курсив</i>"
```

```python
from maxogram.utils.chat_action import ChatActionSender

# Показать "typing..." пока идёт обработка:
async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
    result = await heavy_computation()
    await bot.send_message(chat_id=chat_id, text=result)
```

```python
from maxogram.utils.media_group import MediaGroupBuilder

builder = MediaGroupBuilder()
builder.add_photo(token="upload_token_1")
builder.add_video(token="upload_token_2")
attachments = builder.build()
await bot.send_message(chat_id=123, attachments=attachments)
```

```python
from maxogram.utils.deep_linking import create_start_link, encode_payload, decode_payload

url = create_start_link(username="mybot", payload=encode_payload("ref=campaign1"))
# → "https://max.ru/mybot?start=cmVmPWNhbXBhaWduMQ"

original = decode_payload("cmVmPWNhbXBhaWduMQ")
# → "ref=campaign1"
```

```python
from maxogram.utils.webapp import validate_init_data, parse_init_data

# Проверка подписи WebApp initData:
is_valid = validate_init_data(init_data_string, bot_token, lifetime=86400)

# Проверка + парсинг в модель:
data = parse_init_data(init_data_string, bot_token)
print(data.user.first_name)
```

```python
from maxogram.utils.resumable import ResumableInputFile

# Загрузка большого файла (автовыбор: обычная < 10 MB, chunked >= 10 MB):
file = ResumableInputFile("video_4gb.mp4", on_progress=lambda sent, total: print(f"{sent}/{total}"))
token = await file.upload(bot)
```

```python
from maxogram.filters import F

# MagicFilter с .as_():
F.message.body.text.regexp(r"(\d+)").as_("match")
# handler получит match=<re.Match object>
```

## Ссылки

- [Max Bot API — загрузка файлов](https://dev.max.ru/)
- Связанные модули: `types/button.py` (типы кнопок), `types/keyboard.py` (Keyboard), `types/markup.py` (MarkupElement), `client/` (Bot для upload), `filters/` (MagicFilter), `dispatcher/` (middleware)
