# Contributing

Руководство по участию в разработке maxogram.

## Требования

- Python 3.11+
- [Poetry](https://python-poetry.org/) 2.x

## Настройка окружения

```bash
git clone https://github.com/mccalpink/maxogram.git
cd maxogram
poetry install --with dev
```

Poetry создаст виртуальное окружение в `.venv/` внутри проекта.

## Запуск тестов

```bash
poetry run pytest                # все тесты
poetry run pytest -k "not integration"  # только unit-тесты
poetry run pytest -x             # остановиться на первой ошибке
poetry run pytest --cov          # с coverage
```

## Линтеры и типы

```bash
poetry run ruff check src/ tests/          # линтер
poetry run ruff format --check src/ tests/ # проверка форматирования
poetry run ruff format src/ tests/         # автоформатирование
poetry run mypy src/                       # проверка типов (strict)
```

Перед отправкой PR убедитесь, что все три проверки проходят без ошибок.

## Стиль кода

- **Форматирование** — ruff (line-length 99)
- **Типизация** — mypy strict, аннотации на все публичные функции
- **Docstrings** — на русском, для всех публичных классов и методов
- **Импорты** — isort через ruff, `from __future__ import annotations` в каждом модуле

## Процесс разработки

1. Создайте ветку от `main`
2. Напишите тесты (TDD: тесты до реализации)
3. Реализуйте фичу
4. Убедитесь, что `pytest`, `ruff check`, `mypy` проходят
5. Создайте Pull Request

## Структура проекта

```
src/maxogram/       # исходный код
tests/              # тесты (зеркалят структуру src/)
  integration/      # интеграционные тесты
examples/           # примеры ботов
docs/               # документация
```

## Коммиты

Формат: `тип: описание`

Типы: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Примеры:
```
feat: add ChatTypeFilter for filtering by chat type
fix: prevent kwargs leaking between handlers on SkipHandler
docs: update quickstart with webhook example
```

## Зависимости

Добавление зависимостей — только через Poetry:

```bash
poetry add some-package           # основная зависимость
poetry add --group dev some-tool  # dev-зависимость
```

Не редактируйте `pyproject.toml` вручную для добавления зависимостей.

## Лицензия

Участвуя в проекте, вы соглашаетесь с тем, что ваши вклады будут распространяться
под лицензией [MIT](LICENSE).
