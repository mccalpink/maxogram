# maxogram — документация

Async Python framework для [Max Bot API](https://dev.max.ru/).

## Содержание

| Документ | Описание |
|----------|----------|
| [Быстрый старт](quickstart.md) | Установка, echo bot, команды, клавиатуры, FSM, webhook, middleware, i18n, утилиты |
| [Архитектура](architecture.md) | Слои фреймворка, data flow, расширяемость |

## Примеры

Готовые примеры ботов в директории [`examples/`](../examples/):

| Файл | Описание |
|------|----------|
| `echo_bot.py` | Минимальный echo bot (polling) |
| `error_handling.py` | Перехват ошибок через error handlers |
| `scene_bot.py` | WizardScene для пошаговых диалогов |
| `i18n_bot.py` | Мультиязычный бот (GNU gettext) |
| `multibot.py` | Несколько ботов на одном Dispatcher |
| `webhook_bot.py` | Webhook-режим для production |

## Ссылки

- [Max Bot API](https://dev.max.ru/) — официальная документация API
- [PyPI](https://pypi.org/project/maxogram/) — установка через pip
