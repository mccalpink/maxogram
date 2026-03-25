"""Тесты парсинга OpenAPI YAML и Python AST."""

from __future__ import annotations

from pathlib import Path

import pytest

from maxogram.utils.schema_diff.models import ParsedCode, ParsedSchema
from maxogram.utils.schema_diff.parser import parse_code, parse_schema

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseSchema:
    """Парсинг OpenAPI YAML → ParsedSchema."""

    @pytest.fixture()
    def schema(self) -> ParsedSchema:
        return parse_schema(FIXTURES / "mini_schema.yaml")

    def test_user_fields(self, schema: ParsedSchema) -> None:
        user = schema.types["User"]
        names = {f.name for f in user.fields}
        assert names == {"user_id", "name", "username"}

    def test_user_id_required(self, schema: ParsedSchema) -> None:
        user = schema.types["User"]
        uid = next(f for f in user.fields if f.name == "user_id")
        assert uid.required is True
        assert uid.type_str == "integer"

    def test_username_nullable(self, schema: ParsedSchema) -> None:
        user = schema.types["User"]
        uname = next(f for f in user.fields if f.name == "username")
        assert uname.nullable is True

    def test_message_ref_field(self, schema: ParsedSchema) -> None:
        msg = schema.types["Message"]
        sender = next(f for f in msg.fields if f.name == "sender")
        assert sender.type_str == "User"

    def test_types_count_includes_unions(self, schema: ParsedSchema) -> None:
        assert len(schema.types) >= 5

    def test_update_discriminator(self, schema: ParsedSchema) -> None:
        update = schema.types["Update"]
        assert update.discriminator == "update_type"
        assert "message_created" in update.discriminator_mapping

    def test_parse_from_string(self) -> None:
        yaml_str = (FIXTURES / "mini_schema.yaml").read_text()
        schema = parse_schema(yaml_str=yaml_str)
        assert "User" in schema.types

    def test_methods_count(self, schema: ParsedSchema) -> None:
        assert len(schema.methods) == 2

    def test_send_message_method(self, schema: ParsedSchema) -> None:
        m = schema.methods["sendMessage"]
        assert m.path == "/messages"
        assert m.http_method == "POST"
        assert m.body_type == "NewMessageBody"
        assert m.return_type == "Message"

    def test_get_chat_method(self, schema: ParsedSchema) -> None:
        m = schema.methods["getChat"]
        assert m.path == "/chats/{chatId}"
        assert m.http_method == "GET"
        param_names = [p.name for p in m.params]
        assert "chatId" in param_names


class TestParseCode:
    """Парсинг Python AST → ParsedCode."""

    @pytest.fixture()
    def code(self) -> ParsedCode:
        return parse_code(
            types_dir=FIXTURES / "mini_code" / "types",
            methods_dir=FIXTURES / "mini_code" / "methods",
        )

    def test_types_found(self, code: ParsedCode) -> None:
        assert "User" in code.types
        assert "Message" in code.types
        assert "MaxObject" not in code.types  # base class excluded

    def test_user_fields(self, code: ParsedCode) -> None:
        user = code.types["User"]
        names = {f.name for f in user.fields}
        assert names == {"user_id", "name", "username"}

    def test_field_alias_with_default(self, code: ParsedCode) -> None:
        """Field(default=None, alias='from') — alias extracted from keyword arg."""
        msg = code.types["Message"]
        from_field = next(f for f in msg.fields if f.name == "from_")
        assert from_field.alias == "from"

    def test_union_type_detected(self, code: ParsedCode) -> None:
        """Annotated[Union[...]] recognized as type with union_variants."""
        assert "Update" in code.types
        update = code.types["Update"]
        assert "MessageCreatedUpdate" in update.union_variants
        assert "BotStartedUpdate" in update.union_variants

    def test_methods_found(self, code: ParsedCode) -> None:
        assert "SendMessage" in code.methods

    def test_method_api_path(self, code: ParsedCode) -> None:
        m = code.methods["SendMessage"]
        assert m.api_path == "/messages"
        assert m.http_method == "POST"

    def test_method_return_type(self, code: ParsedCode) -> None:
        m = code.methods["SendMessage"]
        assert m.return_type == "SendMessageResult"

    def test_method_query_params(self, code: ParsedCode) -> None:
        m = code.methods["SendMessage"]
        assert "chat_id" in m.query_params

    def test_method_fields(self, code: ParsedCode) -> None:
        m = code.methods["SendMessage"]
        names = {f.name for f in m.fields}
        assert "chat_id" in names
        assert "text" in names
