"""Парсер OpenAPI YAML → ParsedSchema и Python AST → ParsedCode."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

import yaml

from maxogram.utils.schema_diff.models import (
    CodeField,
    CodeMethod,
    CodeType,
    ParsedCode,
    ParsedSchema,
    SchemaField,
    SchemaMethod,
    SchemaType,
)


def parse_schema(
    path: Path | None = None,
    *,
    yaml_str: str | None = None,
) -> ParsedSchema:
    """Парсинг OpenAPI YAML-файла или строки → ParsedSchema.

    Принимает либо путь к файлу, либо YAML-строку (для CLI с загрузкой по URL).

    Args:
        path: Путь к YAML-файлу.
        yaml_str: YAML-содержимое в виде строки.

    Returns:
        ParsedSchema с types и methods.

    Raises:
        ValueError: Если не передан ни path, ни yaml_str.
    """
    if yaml_str is not None:
        raw = yaml.safe_load(yaml_str)
    elif path is not None:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    else:
        raise ValueError("Необходимо передать path или yaml_str")

    schema = ParsedSchema()
    _parse_components(raw, schema)
    _parse_paths(raw, schema)
    return schema


# --- Вспомогательные функции ---


def _resolve_ref(ref_str: str) -> str:
    """Извлекает имя типа из $ref вида '#/components/schemas/Foo' → 'Foo'."""
    return ref_str.rsplit("/", 1)[-1]


def _parse_type(prop_dict: dict[str, Any]) -> str:
    """Определяет строку типа из словаря свойства OpenAPI.

    Примеры:
        {"$ref": "#/components/schemas/User"} → "User"
        {"type": "array", "items": {"$ref": "..."}} → "array[Foo]"
        {"type": "integer"} → "integer"
    """
    if "$ref" in prop_dict:
        return _resolve_ref(prop_dict["$ref"])
    type_val = prop_dict.get("type", "object")
    if type_val == "array":
        items = prop_dict.get("items", {})
        item_type = _parse_type(items) if items else "any"
        return f"array[{item_type}]"
    return str(type_val)


def _parse_components(raw: dict[str, Any], schema: ParsedSchema) -> None:
    """Парсит секцию components/schemas → заполняет schema.types."""
    schemas = raw.get("components", {}).get("schemas", {})
    for type_name, type_def in schemas.items():
        schema_type = _parse_schema_type(type_name, type_def, schemas)
        schema.types[type_name] = schema_type


def _parse_schema_type(
    name: str,
    type_def: dict[str, Any],
    all_schemas: dict[str, Any],
) -> SchemaType:
    """Создаёт SchemaType из определения в OpenAPI.

    Обрабатывает три случая:
    - Обычный объект с properties
    - discriminator (Update-подобные типы)
    - allOf (наследование, MessageCreatedUpdate)
    """
    schema_type = SchemaType(name=name)

    # allOf: объединяем поля из всех частей
    if "allOf" in type_def:
        _merge_all_of(schema_type, type_def["allOf"], all_schemas)
        return schema_type

    # discriminator
    discriminator_def = type_def.get("discriminator")
    if discriminator_def:
        schema_type.discriminator = discriminator_def.get("propertyName")
        raw_mapping = discriminator_def.get("mapping", {})
        # Нормализуем значения маппинга: убираем $ref-путь, оставляем имя типа
        schema_type.discriminator_mapping = {
            key: _resolve_ref(val) for key, val in raw_mapping.items()
        }

    # Обычные properties
    properties = type_def.get("properties", {})
    required_fields = set(type_def.get("required", []))
    for field_name, field_def in properties.items():
        schema_type.fields.append(_make_field(field_name, field_def, required_fields))

    return schema_type


def _merge_all_of(
    schema_type: SchemaType,
    all_of: list[dict[str, Any]],
    all_schemas: dict[str, Any],
) -> None:
    """Объединяет поля из allOf-списка в schema_type.

    Первый элемент — как правило $ref на родителя (поля помечаются inherited).
    Второй элемент — собственные properties типа.
    """
    for part in all_of:
        if "$ref" in part:
            # Родительский тип: рекурсивно берём его поля
            parent_name = _resolve_ref(part["$ref"])
            parent_def = all_schemas.get(parent_name, {})
            parent_required = set(parent_def.get("required", []))
            # Если у родителя тоже allOf — рекурсия
            if "allOf" in parent_def:
                parent_type = SchemaType(name=parent_name)
                _merge_all_of(parent_type, parent_def["allOf"], all_schemas)
                schema_type.fields.extend(parent_type.fields)
            else:
                for field_name, field_def in parent_def.get("properties", {}).items():
                    schema_type.fields.append(_make_field(field_name, field_def, parent_required))
        else:
            # Собственная часть: properties + required
            own_required = set(part.get("required", []))
            for field_name, field_def in part.get("properties", {}).items():
                schema_type.fields.append(_make_field(field_name, field_def, own_required))


def _make_field(
    name: str,
    field_def: dict[str, Any],
    required_set: set[str],
) -> SchemaField:
    """Создаёт SchemaField из имени, определения и множества required-полей."""
    return SchemaField(
        name=name,
        type_str=_parse_type(field_def),
        required=name in required_set,
        nullable=bool(field_def.get("nullable", False)),
        description=field_def.get("description"),
    )


def _parse_paths(raw: dict[str, Any], schema: ParsedSchema) -> None:
    """Парсит секцию paths → заполняет schema.methods."""
    paths = raw.get("paths", {})
    for path, path_item in paths.items():
        for http_verb, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if not operation_id:
                continue
            method = _parse_operation(operation_id, path, http_verb, operation)
            schema.methods[operation_id] = method


def _parse_operation(
    operation_id: str,
    path: str,
    http_verb: str,
    operation: dict[str, Any],
) -> SchemaMethod:
    """Создаёт SchemaMethod из одной операции OpenAPI."""
    method = SchemaMethod(
        name=operation_id,
        path=path,
        http_method=http_verb.upper(),
    )

    # Параметры (query + path)
    for param in operation.get("parameters", []):
        param_schema = param.get("schema", {})
        method.params.append(
            SchemaField(
                name=param["name"],
                type_str=_parse_type(param_schema) if param_schema else "string",
                required=bool(param.get("required", False)),
                nullable=False,
                description=param.get("description"),
            )
        )

    # requestBody → body_type
    request_body = operation.get("requestBody", {})
    body_schema = request_body.get("content", {}).get("application/json", {}).get("schema", {})
    if "$ref" in body_schema:
        method.body_type = _resolve_ref(body_schema["$ref"])
    elif body_schema.get("type"):
        method.body_type = body_schema["type"]

    # response 200 → return_type
    response_200 = operation.get("responses", {}).get("200", {})
    resp_schema = response_200.get("content", {}).get("application/json", {}).get("schema", {})
    if "$ref" in resp_schema:
        method.return_type = _resolve_ref(resp_schema["$ref"])
    elif resp_schema.get("type"):
        method.return_type = resp_schema["type"]

    return method


# =====================================================================
# Python AST → ParsedCode
# =====================================================================

# Базовые классы, которые не включаются в результат парсинга
_BASE_CLASSES = frozenset({"MaxObject", "MaxMethod", "BaseModel"})


def parse_code(
    types_dir: Path,
    methods_dir: Path,
) -> ParsedCode:
    """Парсинг Python-файлов с типами и методами → ParsedCode.

    Сканирует .py файлы в types_dir и methods_dir, извлекает классы
    через AST-анализ.

    Args:
        types_dir: Директория с файлами типов.
        methods_dir: Директория с файлами методов.

    Returns:
        ParsedCode с types и methods.
    """
    result = ParsedCode()
    _parse_code_dir(types_dir, result)
    _parse_code_dir(methods_dir, result)
    return result


def _parse_code_dir(directory: Path, result: ParsedCode) -> None:
    """Парсит все .py файлы в директории."""
    for py_file in sorted(directory.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            print(
                f"WARNING: Syntax error in {py_file}, skipping",
                file=sys.stderr,
            )
            continue
        _process_module(tree, str(py_file), result)


def _process_module(
    tree: ast.Module,
    file_path: str,
    result: ParsedCode,
) -> None:
    """Обрабатывает AST модуля: извлекает классы и union-типы."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            _process_class(node, file_path, result)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            _process_union_assign(node, file_path, result)


def _process_class(
    node: ast.ClassDef,
    file_path: str,
    result: ParsedCode,
) -> None:
    """Обрабатывает определение класса.

    Пропускает базовые классы. Классы с __api_path__ → CodeMethod,
    остальные → CodeType.
    """
    name = node.name
    if name in _BASE_CLASSES:
        return

    # Проверяем наличие model_config (признак базового класса)
    if _has_model_config(node):
        return

    # Извлекаем поля и ClassVar-атрибуты
    fields: list[CodeField] = []
    classvars: dict[str, Any] = {}

    for stmt in node.body:
        if not isinstance(stmt, ast.AnnAssign) or stmt.target is None:
            continue
        if not isinstance(stmt.target, ast.Name):
            continue

        attr_name = stmt.target.id

        # ClassVar — метаданные метода
        if _is_classvar(stmt.annotation):
            classvars[attr_name] = _extract_classvar_value(attr_name, stmt)
            continue

        # Обычное аннотированное поле
        type_str = _annotation_to_str(stmt.annotation)
        alias = _extract_field_alias(stmt.value) if stmt.value else None
        fields.append(CodeField(name=attr_name, type_str=type_str, alias=alias))

    # Классифицируем: method или type
    if "__api_path__" in classvars:
        method = CodeMethod(
            name=name,
            api_path=classvars.get("__api_path__", ""),
            http_method=classvars.get("__http_method__", ""),
            return_type=classvars.get("__returning__", ""),
            query_params=classvars.get("__query_params__", frozenset()),
            path_params=classvars.get("__path_params__", {}),
            fields=fields,
            file_path=file_path,
        )
        result.methods[name] = method
    else:
        code_type = CodeType(
            name=name,
            fields=fields,
            file_path=file_path,
        )
        result.types[name] = code_type


def _process_union_assign(
    node: ast.Assign | ast.AnnAssign,
    file_path: str,
    result: ParsedCode,
) -> None:
    """Обрабатывает Annotated[Union[...], ...] присвоение → CodeType с union_variants."""
    # Определяем имя и значение
    if isinstance(node, ast.AnnAssign):
        if not isinstance(node.target, ast.Name):
            return
        name = node.target.id
        value = node.value
    elif isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return
        name = target.id
        value = node.value
    else:
        return

    if value is None:
        return

    variants = _extract_union_variants(value)
    if variants:
        result.types[name] = CodeType(
            name=name,
            union_variants=variants,
            file_path=file_path,
        )


# --- AST-хелперы ---


def _has_model_config(node: ast.ClassDef) -> bool:
    """Проверяет, есть ли model_config в теле класса (признак базового)."""
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "model_config":
                    return True
    return False


def _is_classvar(annotation: ast.expr) -> bool:
    """Проверяет, является ли аннотация ClassVar[...].

    ClassVar выглядит как ast.Subscript(value=ast.Name(id='ClassVar'), ...).
    """
    return (
        isinstance(annotation, ast.Subscript)
        and isinstance(annotation.value, ast.Name)
        and annotation.value.id == "ClassVar"
    )


def _extract_classvar_value(
    attr_name: str,
    stmt: ast.AnnAssign,
) -> Any:
    """Извлекает значение ClassVar-атрибута по имени.

    Поддерживает:
    - __api_path__, __http_method__ → строка
    - __returning__ → строка (имя типа или строковый литерал)
    - __query_params__ → frozenset[str]
    - __path_params__ → dict[str, str]
    """
    if stmt.value is None:
        return None

    if attr_name in ("__api_path__", "__http_method__"):
        return _extract_classvar_str(stmt.value)
    if attr_name == "__returning__":
        return _extract_classvar_name(stmt.value)
    if attr_name == "__query_params__":
        return _extract_frozenset_items(stmt.value)
    if attr_name == "__path_params__":
        return _extract_dict_items(stmt.value)

    return None


def _extract_classvar_str(node: ast.expr) -> str | None:
    """Извлекает строковое значение из ast.Constant."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_classvar_name(node: ast.expr) -> str | None:
    """Извлекает имя типа: ast.Name → id, ast.Constant(str) → value."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_frozenset_items(node: ast.expr) -> frozenset[str]:
    """Извлекает элементы frozenset({...}).

    AST: ast.Call(func=ast.Name(id='frozenset'),
                  args=[ast.Set(elts=[ast.Constant(...)])])
    """
    if not isinstance(node, ast.Call):
        return frozenset()
    if not (isinstance(node.func, ast.Name) and node.func.id == "frozenset"):
        return frozenset()
    if not node.args:
        return frozenset()
    arg = node.args[0]
    if not isinstance(arg, ast.Set):
        return frozenset()
    items: list[str] = []
    for elt in arg.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            items.append(elt.value)
    return frozenset(items)


def _extract_dict_items(node: ast.expr) -> dict[str, str]:
    """Извлекает элементы словаря {...}.

    AST: ast.Dict(keys=[ast.Constant(...)], values=[ast.Constant(...)])
    """
    if isinstance(node, ast.Dict):
        result: dict[str, str] = {}
        for key, val in zip(node.keys, node.values, strict=True):
            if (
                isinstance(key, ast.Constant)
                and isinstance(val, ast.Constant)
                and isinstance(key.value, str)
                and isinstance(val.value, str)
            ):
                result[key.value] = val.value
        return result
    # Пустой dict через вызов: dict()
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "dict"
        and not node.args
    ):
        return {}
    return {}


def _extract_field_alias(node: ast.expr) -> str | None:
    """Извлекает alias из Field(alias='...') или Field(default=..., alias='...').

    AST: ast.Call(func=ast.Name(id='Field'),
                  keywords=[ast.keyword(arg='alias', value=ast.Constant(...))])
    """
    if not isinstance(node, ast.Call):
        return None
    # Проверяем, что это вызов Field
    if isinstance(node.func, ast.Name) and node.func.id == "Field":
        for kw in node.keywords:
            if kw.arg == "alias" and isinstance(kw.value, ast.Constant):
                return str(kw.value.value)
    return None


def _annotation_to_str(node: ast.expr) -> str:
    """Конвертирует AST-аннотацию типа в строку.

    Примеры:
        ast.Name("int") → "int"
        ast.BinOp(X | Y) → "X | Y"
        ast.Subscript("list", "Foo") → "list[Foo]"
        ast.Constant("User") → "User" (строковая аннотация)
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Attribute):
        return f"{_annotation_to_str(node.value)}.{node.attr}"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _annotation_to_str(node.left)
        right = _annotation_to_str(node.right)
        return f"{left} | {right}"
    if isinstance(node, ast.Subscript):
        base = _annotation_to_str(node.value)
        slice_str = _annotation_to_str(node.slice)
        return f"{base}[{slice_str}]"
    if isinstance(node, ast.Tuple):
        parts = [_annotation_to_str(elt) for elt in node.elts]
        return ", ".join(parts)
    # Fallback: используем ast.dump для неизвестных узлов
    return ast.dump(node)


def _extract_union_variants(node: ast.expr) -> list[str] | None:
    """Извлекает варианты из Annotated[Union[A, B, ...], ...].

    AST: ast.Subscript(
        value=ast.Name(id='Annotated'),
        slice=ast.Tuple(elts=[
            ast.Subscript(value=ast.Name(id='Union'), slice=ast.Tuple(elts=[...])),
            ...
        ])
    )
    """
    if not isinstance(node, ast.Subscript):
        return None
    if not (isinstance(node.value, ast.Name) and node.value.id == "Annotated"):
        return None

    # slice должен быть Tuple с ≥1 элементом
    if not isinstance(node.slice, ast.Tuple) or not node.slice.elts:
        return None

    first_arg = node.slice.elts[0]

    # Первый аргумент должен быть Union[...]
    if not isinstance(first_arg, ast.Subscript):
        return None
    if not (isinstance(first_arg.value, ast.Name) and first_arg.value.id == "Union"):
        return None

    # Извлекаем имена вариантов из Union
    union_slice = first_arg.slice
    if isinstance(union_slice, ast.Tuple):
        variants = []
        for elt in union_slice.elts:
            if isinstance(elt, ast.Name):
                variants.append(elt.id)
        return variants if variants else None

    # Единственный вариант (Union[A] — маловероятно, но обработаем)
    if isinstance(union_slice, ast.Name):
        return [union_slice.id]

    return None
