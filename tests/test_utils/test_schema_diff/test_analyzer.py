"""Тесты analyzer — сравнение schema vs code."""

from __future__ import annotations

from maxogram.utils.schema_diff.analyzer import compare
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


def _user_schema() -> SchemaType:
    return SchemaType(name="User", fields=[
        SchemaField(name="user_id", type_str="integer", required=True, nullable=False),
        SchemaField(name="name", type_str="string", required=True, nullable=False),
    ])


def _user_code() -> CodeType:
    return CodeType(name="User", fields=[
        CodeField(name="user_id", type_str="int"),
        CodeField(name="name", type_str="str"),
    ])


class TestCompareTypes:
    """Сравнение типов."""

    def test_identical_types_no_diff(self) -> None:
        schema = ParsedSchema(types={"User": _user_schema()})
        code = ParsedCode(types={"User": _user_code()})
        result = compare(schema, code)
        assert result.has_changes is False

    def test_new_type_in_schema(self) -> None:
        schema = ParsedSchema(types={"User": _user_schema(), "Chat": SchemaType(name="Chat")})
        code = ParsedCode(types={"User": _user_code()})
        result = compare(schema, code)
        assert any(d.name == "Chat" and d.kind == "new" for d in result.type_diffs)

    def test_removed_type_from_schema(self) -> None:
        schema = ParsedSchema(types={})
        code = ParsedCode(types={"User": _user_code()})
        result = compare(schema, code)
        assert "User" in result.unmatched_code

    def test_added_field(self) -> None:
        user_s = _user_schema()
        user_s.fields.append(
            SchemaField(name="email", type_str="string", required=False, nullable=True),
        )
        schema = ParsedSchema(types={"User": user_s})
        code = ParsedCode(types={"User": _user_code()})
        result = compare(schema, code)
        td = next(d for d in result.type_diffs if d.name == "User")
        assert any(f.name == "email" and f.kind == "added" for f in td.field_diffs)

    def test_changed_field_type(self) -> None:
        user_s = SchemaType(name="User", fields=[
            SchemaField(name="user_id", type_str="string", required=True, nullable=False),
        ])
        user_c = CodeType(name="User", fields=[
            CodeField(name="user_id", type_str="int"),
        ])
        schema = ParsedSchema(types={"User": user_s})
        code = ParsedCode(types={"User": user_c})
        result = compare(schema, code)
        td = next(d for d in result.type_diffs if d.name == "User")
        assert any(f.name == "user_id" and f.kind == "changed" for f in td.field_diffs)

    def test_alias_matching(self) -> None:
        """Field 'from' in schema == 'from_' with alias='from' in code."""
        schema = ParsedSchema(types={"Msg": SchemaType(name="Msg", fields=[
            SchemaField(name="from", type_str="integer", required=True, nullable=False),
        ])})
        code = ParsedCode(types={"Msg": CodeType(name="Msg", fields=[
            CodeField(name="from_", type_str="int", alias="from"),
        ])})
        result = compare(schema, code)
        assert result.has_changes is False

    def test_union_new_variant(self) -> None:
        """New variant in discriminator mapping → diff."""
        schema = ParsedSchema(types={"Update": SchemaType(
            name="Update", discriminator="update_type",
            discriminator_mapping={
                "message_created": "MessageCreatedUpdate",
                "bot_started": "BotStartedUpdate",
                "new_event": "NewEventUpdate",
            },
        )})
        code = ParsedCode(types={"Update": CodeType(
            name="Update",
            union_variants=["MessageCreatedUpdate", "BotStartedUpdate"],
        )})
        result = compare(schema, code)
        assert result.has_changes is True


class TestCompareMethods:
    """Сравнение методов."""

    def test_method_matched_by_path_and_verb(self) -> None:
        schema = ParsedSchema(methods={"sendMessage": SchemaMethod(
            name="sendMessage", path="/messages", http_method="POST",
        )})
        code = ParsedCode(methods={"SendMessage": CodeMethod(
            name="SendMessage", api_path="/messages", http_method="POST",
        )})
        result = compare(schema, code)
        assert result.has_changes is False

    def test_new_method(self) -> None:
        schema = ParsedSchema(methods={"pinMessage": SchemaMethod(
            name="pinMessage", path="/chats/{chatId}/pin", http_method="PUT",
        )})
        code = ParsedCode(methods={})
        result = compare(schema, code)
        assert any(d.name == "pinMessage" and d.kind == "new" for d in result.method_diffs)
