# schema_diff

CLI-инструмент для сравнения OpenAPI schema Max Bot API с кодом maxogram. Находит расхождения в типах, полях, методах и union-вариантах. Генерирует заготовки файлов для новых элементов.

## Модули

| Модуль | Описание |
|--------|----------|
| `models.py` | Внутренние dataclass-модели: `SchemaType`, `CodeType`, `DiffResult`, `FieldDiff` и др. |
| `parser.py` | Парсер OpenAPI YAML (`parse_schema`) и Python AST (`parse_code`) |
| `analyzer.py` | Сравнение `ParsedSchema` vs `ParsedCode` → `DiffResult` |
| `reporter.py` | Форматирование отчёта: `to_terminal()` и `to_markdown()` |
| `generator.py` | Генерация файлов-заготовок для новых типов и методов |
| `__main__.py` | CLI entry point |

## CLI команды

```bash
# Скачать schema с GitHub и сравнить с кодом:
poetry run schema-diff

# Использовать локальный файл schema:
poetry run schema-diff --schema path/to/schema.yaml

# Сохранить отчёт в Markdown:
poetry run schema-diff --output report.md

# Сгенерировать заготовки для новых типов/методов:
poetry run schema-diff --generate

# Указать директории с кодом:
poetry run schema-diff --types-dir src/maxogram/types --methods-dir src/maxogram/methods
```

## Что показывает

- **Типы**: новые (в schema, но не в коде), изменённые поля (тип, nullable, required)
- **Методы**: новые endpoints (по паре path + HTTP method)
- **Union-варианты**: новые варианты в discriminator mapping
- **Unmatched**: типы в коде, которых нет в schema

## Генерация заготовок

Флаг `--generate` создаёт файлы-заготовки в `generated/`:

```
generated/
├── types/
│   └── new_type.py      # class NewType(MaxObject) с полями из schema
└── methods/
    └── new_method.py    # class NewMethod(MaxMethod) с __api_path__ и __http_method__
```

Генерируются только элементы с `kind="new"`. Изменённые и удалённые требуют ручной доработки.

## Ссылки

- Schema URL по умолчанию: `https://raw.githubusercontent.com/tamtam-chat/tamtam-bot-api-schema/master/schema.yaml`
- Связанные модули: `types/` (модели API), `methods/` (методы API)
