# i18n

Интернационализация через GNU gettext. Переводы из `.mo` файлов, ленивые строки через `LazyProxy`, автоматическое определение локали через middleware.

## Основные классы

| Класс | Описание |
|-------|----------|
| `I18n` | Менеджер переводов: `gettext()`, `ngettext()`, `lazy_gettext()`. Кэширует загруженные `.mo` файлы |
| `LazyProxy` | Прокси-строка, вычисляемая при обращении к `str()`. Для определений на уровне модуля |
| `I18nMiddleware` | Middleware: определяет локаль, устанавливает `current_locale` в contextvars, добавляет `gettext` в DI |

## Структура переводов

```
locales/
├── ru/
│   └── LC_MESSAGES/
│       └── messages.mo
└── en/
    └── LC_MESSAGES/
        └── messages.mo
```

## Использование

```python
from maxogram.i18n import I18n, I18nMiddleware

# 1. Создать менеджер переводов
i18n = I18n(path="locales", default_locale="ru", domain="messages")

# 2. Подключить middleware
dp.update.outer_middleware(I18nMiddleware(i18n=i18n))

# 3. В хендлере — gettext приходит через DI
@router.message_created()
async def handler(update, gettext, **kwargs):
    _ = gettext
    await bot.send_message(chat_id=..., text=_("Hello!"))
```

```python
# Ленивые строки (определяются до того, как известна локаль):
_ = i18n.lazy_gettext
WELCOME = _("Welcome!")  # LazyProxy, не строка

# При str(WELCOME) — вычисляется с текущей локалью
print(WELCOME)  # → "Добро пожаловать!" (если локаль ru)
```

```python
# Множественное число:
text = i18n.ngettext("{n} message", "{n} messages", count, locale="ru")

# Пользовательский locale_resolver:
async def my_resolver(event, data):
    user = data.get("event_user")
    return user.language if user else "ru"

I18nMiddleware(i18n=i18n, locale_resolver=my_resolver)
```

## Приоритет определения локали

1. Пользовательский `locale_resolver` (если задан)
2. `event.user_locale` (из webhook payload)
3. `default_locale` из I18n

## Ссылки

- Связанные модули: `dispatcher/` (middleware pipeline, DI)
