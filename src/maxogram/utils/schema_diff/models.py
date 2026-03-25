"""Внутренние модели Schema Diff Tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal  # noqa: TCH003

# --- Schema-side (из OpenAPI YAML) ---

@dataclass
class SchemaField:
    """Поле типа из OpenAPI schema."""

    name: str
    type_str: str
    required: bool
    nullable: bool
    description: str | None = None


@dataclass
class SchemaType:
    """Тип из OpenAPI schema."""

    name: str
    fields: list[SchemaField] = field(default_factory=list)
    discriminator: str | None = None
    discriminator_mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class SchemaMethod:
    """Endpoint из OpenAPI schema."""

    name: str
    path: str
    http_method: str
    params: list[SchemaField] = field(default_factory=list)
    body_type: str | None = None
    return_type: str = ""


@dataclass
class ParsedSchema:
    """Результат парсинга OpenAPI schema."""

    types: dict[str, SchemaType] = field(default_factory=dict)
    methods: dict[str, SchemaMethod] = field(default_factory=dict)


# --- Code-side (из Python AST) ---

@dataclass
class CodeField:
    """Поле класса из Python-кода."""

    name: str
    type_str: str
    alias: str | None = None


@dataclass
class CodeType:
    """Тип (класс) из Python-кода."""

    name: str
    fields: list[CodeField] = field(default_factory=list)
    file_path: str = ""
    union_variants: list[str] = field(default_factory=list)


@dataclass
class CodeMethod:
    """Метод API (класс) из Python-кода."""

    name: str
    api_path: str = ""
    http_method: str = ""
    return_type: str = ""
    query_params: frozenset[str] = field(default_factory=frozenset)
    path_params: dict[str, str] = field(default_factory=dict)
    fields: list[CodeField] = field(default_factory=list)
    file_path: str = ""


@dataclass
class ParsedCode:
    """Результат парсинга Python-кода."""

    types: dict[str, CodeType] = field(default_factory=dict)
    methods: dict[str, CodeMethod] = field(default_factory=dict)


# --- Diff ---

@dataclass
class FieldDiff:
    """Различие в одном поле."""

    name: str
    kind: Literal["added", "removed", "changed"]
    schema_type: str | None = None
    code_type: str | None = None
    details: str | None = None


@dataclass
class TypeDiff:
    """Различие в типе."""

    name: str
    kind: Literal["new", "removed", "changed"]
    field_diffs: list[FieldDiff] = field(default_factory=list)


@dataclass
class MethodDiff:
    """Различие в методе API."""

    name: str
    kind: Literal["new", "removed", "changed"]
    details: str | None = None


@dataclass
class DiffResult:
    """Полный результат сравнения."""

    type_diffs: list[TypeDiff] = field(default_factory=list)
    method_diffs: list[MethodDiff] = field(default_factory=list)
    unmatched_schema: list[str] = field(default_factory=list)
    unmatched_code: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Есть ли изменения."""
        return bool(self.type_diffs or self.method_diffs or self.unmatched_schema)
