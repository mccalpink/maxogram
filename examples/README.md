# Примеры maxogram

Рабочие примеры для быстрого старта. Каждый пример -- самостоятельный бот, который можно запустить.

## Подготовка

1. Получите токен бота на [dev.max.ru](https://dev.max.ru)
2. Установите переменную окружения:
   ```bash
   export MAX_BOT_TOKEN="your-token-here"
   ```

## Примеры

### echo_bot.py -- Базовый бот

Демонстрирует основные возможности:
- Команды (`/start`, `/keyboard`, `/form`)
- Echo сообщений (повтор любого текста)
- Inline-клавиатура с обработкой callback
- FSM (форма с состояниями: имя и возраст)

```bash
poetry run python examples/echo_bot.py
```

### webhook_bot.py -- Webhook для production

Демонстрирует:
- Настройку WebhookManager с aiohttp-сервером
- Auto-reconnect (переподписка каждые 7.5 часов)
- Graceful shutdown по SIGINT/SIGTERM

```bash
WEBHOOK_URL=https://mybot.example.com/webhook poetry run python examples/webhook_bot.py
```

### scene_bot.py -- WizardScene (пошаговая анкета)

Демонстрирует:
- WizardScene с навигацией (next/back/goto)
- SceneRegistry для управления сценами
- Пошаговый сбор данных: имя -> возраст -> подтверждение

```bash
poetry run python examples/scene_bot.py
```

### i18n_bot.py -- Мультиязычный бот

Демонстрирует:
- I18n с двумя локалями (ru, en)
- I18nMiddleware для автоматического определения локали
- gettext и lazy_gettext в хендлерах
- Переключение языка по команде `/lang`

```bash
poetry run python examples/i18n_bot.py
```

### multibot.py -- Два бота в одном приложении

Демонстрирует:
- Два экземпляра Bot с разными токенами
- Общий Dispatcher, `dp.run_polling(bot1, bot2)`
- DI: хендлер получает правильный bot автоматически

```bash
MAX_BOT_TOKEN_1=xxx MAX_BOT_TOKEN_2=yyy poetry run python examples/multibot.py
```

### error_handling.py -- Обработка ошибок

Демонстрирует:
- Error observer через `router.error()`
- ExceptionTypeFilter для фильтрации по типу исключения
- ErrorEvent с доступом к исключению и оригинальному update
- Намеренные ошибки для демонстрации (`/error`, `/crash`)

```bash
poetry run python examples/error_handling.py
```
