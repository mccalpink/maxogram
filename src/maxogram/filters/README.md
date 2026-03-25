# filters

Система фильтров для маршрутизации событий. Определяют, какой хендлер обработает конкретное событие.

## Основные классы

| Класс | Описание |
|-------|----------|
| `Filter` | ABC фильтра. Возвращает `False`, `True` или `dict` (обогащение kwargs) |
| `Command` | Фильтр команд (`/start`, `/help`). Парсит текст в `CommandObject` |
| `CommandObject` | Результат парсинга: prefix, command, args |
| `CallbackData` | Типизированные callback_data с `pack()`/`unpack()` и `filter()` |
| `ContentTypeFilter` | Фильтр по типу контента: image, video, audio, file, text и др. |
| `ContentType` | Enum типов контента (StrEnum) |
| `ChatTypeFilter` | Фильтр по типу чата: dialog, chat, channel |
| `ExceptionTypeFilter` | Фильтр по типу исключения для error handlers |
| `MagicData` | Фильтр по данным контекста через MagicFilter DSL |
| `F` | Глобальный экземпляр `MagicFilter` для DSL-фильтрации |

## Использование

```python
from maxogram.filters import Command, ContentTypeFilter, ContentType, ChatTypeFilter
from maxogram.enums import ChatType

# Команды:
@router.message_created(Command("start"))
async def on_start(update, command: CommandObject): ...

@router.message_created(Command("help", "info", ignore_case=True))
async def on_help(update, command: CommandObject): ...

# Тип контента:
@router.message_created(ContentTypeFilter(ContentType.IMAGE))
async def on_photo(update): ...

# Тип чата:
@router.message_created(ChatTypeFilter(ChatType.DIALOG))
async def on_private(update): ...
```

```python
from maxogram.filters import CallbackData

# Типизированные callback:
class ItemAction(CallbackData, prefix="item"):
    id: int
    action: str

cb = ItemAction(id=42, action="delete")
cb.pack()  # "item:42:delete"

@router.message_callback(ItemAction.filter())
async def on_item(update, callback_data: ItemAction): ...
```

```python
from maxogram.filters import F, MagicData

# MagicFilter DSL:
@router.message_created(F.message.body.text.startswith("!"))
async def on_excl(update): ...

# MagicData — фильтр по контексту:
@router.message_created(MagicData(F.event_chat.chat_type == "dialog"))
async def on_dialog(update): ...
```

## Ссылки

- Связанные модули: `dispatcher/` (регистрация фильтров), `handlers/` (class-based handlers), `utils/magic_filter.py` (расширение MagicFilter с `.as_()`)
