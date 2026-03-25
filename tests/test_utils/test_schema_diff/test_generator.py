"""Тесты generator — генерация заготовок."""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxogram.utils.schema_diff.generator import generate
from maxogram.utils.schema_diff.models import (
    DiffResult,
    MethodDiff,
    SchemaField,
    SchemaMethod,
    SchemaType,
    TypeDiff,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestGenerateTypes:
    def test_creates_type_file(self, tmp_path: Path) -> None:
        diff = DiffResult(type_diffs=[TypeDiff(name="Chat", kind="new")])
        schema_types = {
            "Chat": SchemaType(
                name="Chat",
                fields=[
                    SchemaField(name="chat_id", type_str="integer", required=True, nullable=False),
                    SchemaField(name="title", type_str="string", required=True, nullable=False),
                ],
            )
        }
        generate(diff, schema_types=schema_types, schema_methods={}, output_dir=tmp_path)
        generated = tmp_path / "types" / "chat.py"
        assert generated.exists()

    def test_type_file_content(self, tmp_path: Path) -> None:
        diff = DiffResult(type_diffs=[TypeDiff(name="Chat", kind="new")])
        schema_types = {
            "Chat": SchemaType(
                name="Chat",
                fields=[
                    SchemaField(name="chat_id", type_str="integer", required=True, nullable=False),
                    SchemaField(name="title", type_str="string", required=True, nullable=False),
                ],
            )
        }
        generate(diff, schema_types=schema_types, schema_methods={}, output_dir=tmp_path)
        content = (tmp_path / "types" / "chat.py").read_text()
        assert "class Chat" in content
        assert "chat_id: int" in content
        assert "title: str" in content
        assert "MaxObject" in content

    def test_skips_non_new_types(self, tmp_path: Path) -> None:
        diff = DiffResult(type_diffs=[TypeDiff(name="User", kind="changed")])
        generate(diff, schema_types={}, schema_methods={}, output_dir=tmp_path)
        assert not (tmp_path / "types").exists()

    def test_nullable_field(self, tmp_path: Path) -> None:
        diff = DiffResult(type_diffs=[TypeDiff(name="Foo", kind="new")])
        schema_types = {
            "Foo": SchemaType(
                name="Foo",
                fields=[
                    SchemaField(name="bar", type_str="string", required=False, nullable=True),
                ],
            )
        }
        generate(diff, schema_types=schema_types, schema_methods={}, output_dir=tmp_path)
        content = (tmp_path / "types" / "foo.py").read_text()
        assert "None" in content  # bar should be optional


class TestGenerateMethods:
    def test_creates_method_file(self, tmp_path: Path) -> None:
        diff = DiffResult(method_diffs=[MethodDiff(name="pinMessage", kind="new")])
        schema_methods = {
            "pinMessage": SchemaMethod(
                name="pinMessage",
                path="/chats/{chatId}/pin",
                http_method="PUT",
                return_type="SimpleQueryResult",
            )
        }
        generate(diff, schema_types={}, schema_methods=schema_methods, output_dir=tmp_path)
        generated = tmp_path / "methods" / "pin_message.py"
        assert generated.exists()

    def test_method_file_content(self, tmp_path: Path) -> None:
        diff = DiffResult(method_diffs=[MethodDiff(name="pinMessage", kind="new")])
        schema_methods = {
            "pinMessage": SchemaMethod(
                name="pinMessage",
                path="/chats/{chatId}/pin",
                http_method="PUT",
                return_type="SimpleQueryResult",
            )
        }
        generate(diff, schema_types={}, schema_methods=schema_methods, output_dir=tmp_path)
        content = (tmp_path / "methods" / "pin_message.py").read_text()
        assert "class PinMessage" in content
        assert '"/chats/{chatId}/pin"' in content
        assert '"PUT"' in content
        assert "MaxMethod" in content

    def test_skips_non_new_methods(self, tmp_path: Path) -> None:
        diff = DiffResult(method_diffs=[MethodDiff(name="sendMessage", kind="changed")])
        generate(diff, schema_types={}, schema_methods={}, output_dir=tmp_path)
        assert not (tmp_path / "methods").exists()
