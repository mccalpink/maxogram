"""Анализатор различий: сравнение ParsedSchema vs ParsedCode → DiffResult."""

from __future__ import annotations

from maxogram.utils.schema_diff.models import (
    CodeField,
    CodeType,
    DiffResult,
    FieldDiff,
    MethodDiff,
    ParsedCode,
    ParsedSchema,
    SchemaType,
    TypeDiff,
)

# Соответствие типов OpenAPI → Python
_TYPE_MAP: dict[str, str] = {
    "integer": "int",
    "string": "str",
    "boolean": "bool",
    "number": "float",
}


def compare(schema: ParsedSchema, code: ParsedCode) -> DiffResult:
    """Сравнить ParsedSchema и ParsedCode, вернуть DiffResult.

    Логика:
    - Типы сопоставляются по имени.
    - Поля сопоставляются по имени или по alias (alias имеет приоритет).
    - Методы сопоставляются по паре (path, http_method), не по имени.
    - Типы в schema, но не в code → TypeDiff(kind="new").
    - Типы в code, но не в schema → unmatched_code.
    """
    result = DiffResult()

    _compare_types(schema, code, result)
    _compare_methods(schema, code, result)

    return result


# --- Типы ---

def _compare_types(schema: ParsedSchema, code: ParsedCode, result: DiffResult) -> None:
    """Сравнить типы schema vs code."""
    matched_code_names: set[str] = set()

    for schema_name, schema_type in schema.types.items():
        code_type = code.types.get(schema_name)

        if schema_type.discriminator:
            # Union-тип: сравниваем по discriminator_mapping
            matched_code_names.add(schema_name)
            type_diff = _compare_union(schema_name, schema_type, code_type)
            if type_diff is not None:
                result.type_diffs.append(type_diff)
        elif code_type is None:
            # Тип есть в schema, нет в code
            result.type_diffs.append(TypeDiff(name=schema_name, kind="new"))
        else:
            matched_code_names.add(schema_name)
            field_diffs = _compare_fields(schema_type, code_type)
            if field_diffs:
                result.type_diffs.append(TypeDiff(
                    name=schema_name, kind="changed", field_diffs=field_diffs,
                ))

    # Типы в code, которых нет в schema
    for code_name in code.types:
        if code_name not in matched_code_names:
            result.unmatched_code.append(code_name)


def _compare_union(
    name: str,
    schema_type: SchemaType,
    code_type: CodeType | None,
) -> TypeDiff | None:
    """Сравнить union-тип по discriminator_mapping vs union_variants."""
    schema_variants = set(schema_type.discriminator_mapping.values())
    code_variants = set(code_type.union_variants) if code_type else set()

    new_variants = schema_variants - code_variants
    if new_variants:
        field_diffs = [
            FieldDiff(name=v, kind="added", details="новый вариант union")
            for v in sorted(new_variants)
        ]
        return TypeDiff(name=name, kind="changed", field_diffs=field_diffs)
    return None


# --- Поля ---

def _compare_fields(schema_type: SchemaType, code_type: CodeType) -> list[FieldDiff]:
    """Сравнить поля типа. Возвращает список различий."""
    diffs: list[FieldDiff] = []

    # Строим lookup: имя → CodeField и alias → CodeField
    code_by_name: dict[str, CodeField] = {f.name: f for f in code_type.fields}
    code_by_alias: dict[str, CodeField] = {
        f.alias: f for f in code_type.fields if f.alias is not None
    }

    matched_code_fields: set[str] = set()

    for sf in schema_type.fields:
        # Поиск по alias сначала, затем по имени
        cf = code_by_alias.get(sf.name) or code_by_name.get(sf.name)

        if cf is None:
            diffs.append(FieldDiff(
                name=sf.name, kind="added",
                schema_type=sf.type_str, code_type=None,
            ))
        else:
            matched_code_fields.add(cf.name)
            expected_code_type = _TYPE_MAP.get(sf.type_str, sf.type_str)
            if cf.type_str != expected_code_type:
                diffs.append(FieldDiff(
                    name=sf.name, kind="changed",
                    schema_type=sf.type_str, code_type=cf.type_str,
                ))

    return diffs


# --- Методы ---

def _compare_methods(schema: ParsedSchema, code: ParsedCode, result: DiffResult) -> None:
    """Сравнить методы schema vs code по паре (path, http_method)."""
    # Строим lookup кода: (api_path, http_method) → CodeMethod
    code_by_endpoint: dict[tuple[str, str], object] = {
        (m.api_path, m.http_method): m
        for m in code.methods.values()
    }

    for schema_name, sm in schema.methods.items():
        key = (sm.path, sm.http_method)
        if key not in code_by_endpoint:
            result.method_diffs.append(MethodDiff(name=schema_name, kind="new"))
