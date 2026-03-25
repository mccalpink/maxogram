"""Тесты dataclass-ов schema_diff."""

from __future__ import annotations

from maxogram.utils.schema_diff.models import (
    CodeField,
    CodeMethod,
    CodeType,
    DiffResult,
    FieldDiff,
    ParsedSchema,
    SchemaField,
    SchemaMethod,
    SchemaType,
    TypeDiff,
)


class TestSchemaModels:
    """Schema-side dataclass-ы."""

    def test_schema_field_creation(self) -> None:
        f = SchemaField(
            name="user_id",
            type_str="integer",
            required=True,
            nullable=False,
            description="User ID",
        )
        assert f.name == "user_id"
        assert f.type_str == "integer"
        assert f.required is True

    def test_schema_type_with_discriminator(self) -> None:
        t = SchemaType(name="Update", fields=[], discriminator="update_type")
        assert t.discriminator == "update_type"

    def test_schema_method(self) -> None:
        m = SchemaMethod(
            name="sendMessage",
            path="/messages",
            http_method="POST",
            params=[],
            body_type="NewMessageBody",
            return_type="SendMessageResult",
        )
        assert m.path == "/messages"

    def test_parsed_schema(self) -> None:
        ps = ParsedSchema(types={}, methods={})
        assert isinstance(ps.types, dict)


class TestCodeModels:
    """Code-side dataclass-ы."""

    def test_code_field(self) -> None:
        f = CodeField(name="user_id", type_str="int", alias=None)
        assert f.alias is None

    def test_code_field_with_alias(self) -> None:
        f = CodeField(name="from_", type_str="int", alias="from")
        assert f.alias == "from"

    def test_code_type(self) -> None:
        t = CodeType(name="User", fields=[], file_path="types/user.py")
        assert t.file_path == "types/user.py"

    def test_code_type_union(self) -> None:
        t = CodeType(
            name="Update", fields=[], union_variants=["MessageCreatedUpdate", "BotStartedUpdate"]
        )
        assert len(t.union_variants) == 2

    def test_code_method(self) -> None:
        m = CodeMethod(
            name="SendMessage",
            api_path="/messages",
            http_method="POST",
            return_type="SendMessageResult",
            query_params=frozenset({"chat_id"}),
            path_params={},
            fields=[],
            file_path="methods/message.py",
        )
        assert m.api_path == "/messages"
        assert m.return_type == "SendMessageResult"


class TestDiffModels:
    """Diff dataclass-ы."""

    def test_field_diff(self) -> None:
        d = FieldDiff(
            name="text",
            kind="changed",
            schema_type="string",
            code_type="str",
            details="was required",
        )
        assert d.kind == "changed"

    def test_type_diff(self) -> None:
        d = TypeDiff(name="User", kind="changed", field_diffs=[])
        assert d.kind == "changed"

    def test_diff_result_empty(self) -> None:
        r = DiffResult(type_diffs=[], method_diffs=[], unmatched_schema=[], unmatched_code=[])
        assert r.has_changes is False

    def test_diff_result_with_type_changes(self) -> None:
        td = TypeDiff(name="User", kind="new", field_diffs=[])
        r = DiffResult(type_diffs=[td], method_diffs=[], unmatched_schema=[], unmatched_code=[])
        assert r.has_changes is True

    def test_diff_result_with_unmatched_schema(self) -> None:
        r = DiffResult(
            type_diffs=[], method_diffs=[], unmatched_schema=["NewType"], unmatched_code=[]
        )
        assert r.has_changes is True
