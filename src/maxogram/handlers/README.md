# handlers

Class-based handlers — альтернатива функциональным хендлерам. Организация логики обработки событий в классах с типизированным доступом к event и data.

## Основные классы

| Класс | Описание |
|-------|----------|
| `BaseHandler[T]` | ABC class-based handler. Generic по типу события |
| `MessageHandler` | Handler для `message_created`. `self.event` типизирован как `Message` |
| `CallbackHandler` | Handler для `message_callback`. `self.event` типизирован как `Callback` |

## Использование

```python
from maxogram.handlers import MessageHandler, CallbackHandler

class GreetHandler(MessageHandler):
    async def handle(self):
        # self.event — Message
        # self.data — dict с bot, state и т.д.
        # self.bot — shortcut для self.data["bot"]
        await self.bot.send_message(
            chat_id=self.event.recipient.chat_id,
            text="Привет!",
        )

class ButtonHandler(CallbackHandler):
    async def handle(self):
        # self.event — Callback
        callback_id = self.event.callback_id
        await self.bot.answer_on_callback(callback_id, notification="OK")
```

```python
# Регистрация в роутере:
from maxogram.filters import Command

router.message_created.register(GreetHandler, Command("start"))
router.message_callback.register(ButtonHandler)
```

## Архитектура

- `BaseHandler` реализует `__await__`, поэтому совместим с `CallableObject` (DI dispatcher)
- `__init__` принимает `event` (позиционный) + `**kwargs` (data из middleware pipeline)
- Подклассы реализуют `handle()` — единственный обязательный метод

## Ссылки

- Связанные модули: `dispatcher/` (регистрация и вызов), `filters/` (фильтрация событий)
