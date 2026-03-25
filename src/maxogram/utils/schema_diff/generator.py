"""Генератор заготовок файлов для новых типов и методов из OpenAPI schema."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from maxogram.utils.schema_diff.models import DiffResult, SchemaMethod, SchemaType

# Соответствие типов OpenAPI → Python
_OPENAPI_TO_PYTHON: dict[str, str] = {
    "integer": "int",
    "number": "float",
    "string": "str",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}

_TYPE_FILE_TEMPLATE = '''\
"""Автоматически сгенерировано из OpenAPI schema. Требует доработки."""

from maxogram.types.base import MaxObject


class {class_name}(MaxObject):
    """TODO: добавить docstring."""

{fields}
'''

_METHOD_FILE_TEMPLATE = '''\
"""Автоматически сгенерировано из OpenAPI schema. Требует доработки."""

from typing import ClassVar

from maxogram.methods.base import MaxMethod


class {class_name}(MaxMethod["{return_type}"]):
    """TODO: добавить docstring."""

    __api_path__: ClassVar[str] = "{path}"
    __http_method__: ClassVar[str] = "{http_method}"
'''


def _to_snake_case(name: str) -> str:
    """Конвертирует CamelCase или camelCase в snake_case.

    Примеры:
        PinMessage → pin_message
        getChat → get_chat
    """
    # Вставляем _ перед переходом строчная → заглавная
    result = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    # Вставляем _ перед переходом заглавная+заглавная → строчная (аббревиатуры)
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)
    return result.lower()


def _camel_to_pascal(name: str) -> str:
    """Конвертирует camelCase в PascalCase.

    Примеры:
        pinMessage → PinMessage
        Chat → Chat (без изменений)
    """
    if not name:
        return name
    return name[0].upper() + name[1:]


def _schema_type_to_python(type_str: str) -> str:
    """Конвертирует тип OpenAPI schema в тип Python.

    Примеры:
        integer → int
        string → str
        unknown → Any
    """
    return _OPENAPI_TO_PYTHON.get(type_str, "Any")


def _render_type_fields(schema_type: SchemaType) -> str:
    """Генерирует строки полей для класса типа."""
    if not schema_type.fields:
        return "    pass"

    lines: list[str] = []
    for f in schema_type.fields:
        py_type = _schema_type_to_python(f.type_str)
        if f.nullable or not f.required:
            annotation = f"    {f.name}: {py_type} | None = None"
        else:
            annotation = f"    {f.name}: {py_type}"
        lines.append(annotation)
    return "\n".join(lines)


def _generate_type_file(schema_type: SchemaType, output_dir: Path) -> None:
    """Генерирует файл-заготовку для нового типа."""
    class_name = _camel_to_pascal(schema_type.name)
    file_name = _to_snake_case(schema_type.name) + ".py"
    types_dir = output_dir / "types"
    types_dir.mkdir(parents=True, exist_ok=True)

    fields_block = _render_type_fields(schema_type)
    content = _TYPE_FILE_TEMPLATE.format(class_name=class_name, fields=fields_block)
    (types_dir / file_name).write_text(content, encoding="utf-8")


def _generate_method_file(schema_method: SchemaMethod, output_dir: Path) -> None:
    """Генерирует файл-заготовку для нового метода API."""
    class_name = _camel_to_pascal(schema_method.name)
    file_name = _to_snake_case(schema_method.name) + ".py"
    methods_dir = output_dir / "methods"
    methods_dir.mkdir(parents=True, exist_ok=True)

    content = _METHOD_FILE_TEMPLATE.format(
        class_name=class_name,
        return_type=schema_method.return_type,
        path=schema_method.path,
        http_method=schema_method.http_method,
    )
    (methods_dir / file_name).write_text(content, encoding="utf-8")


def generate(
    diff: DiffResult,
    schema_types: dict[str, SchemaType],
    schema_methods: dict[str, SchemaMethod],
    output_dir: Path,
) -> None:
    """Генерирует файлы-заготовки для новых типов и методов.

    Обрабатывает только элементы с kind="new". Изменённые и удалённые
    элементы пропускаются — они требуют ручной доработки.

    Args:
        diff: Результат сравнения schema vs code.
        schema_types: Словарь типов из OpenAPI schema (имя → SchemaType).
        schema_methods: Словарь методов из OpenAPI schema (имя → SchemaMethod).
        output_dir: Корневая директория для генерируемых файлов.
    """
    for type_diff in diff.type_diffs:
        if type_diff.kind != "new":
            continue
        schema_type = schema_types.get(type_diff.name)
        if schema_type is None:
            continue
        _generate_type_file(schema_type, output_dir)

    for method_diff in diff.method_diffs:
        if method_diff.kind != "new":
            continue
        schema_method = schema_methods.get(method_diff.name)
        if schema_method is None:
            continue
        _generate_method_file(schema_method, output_dir)
