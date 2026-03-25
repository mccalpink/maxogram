"""Тесты reporter — форматирование DiffResult."""

from __future__ import annotations

from maxogram.utils.schema_diff.models import DiffResult, FieldDiff, MethodDiff, TypeDiff
from maxogram.utils.schema_diff.reporter import to_markdown, to_terminal


def _sample_diff() -> DiffResult:
    return DiffResult(
        type_diffs=[
            TypeDiff(name="Chat", kind="new", field_diffs=[]),
            TypeDiff(name="User", kind="changed", field_diffs=[
                FieldDiff(name="email", kind="added", schema_type="string", code_type=None),
            ]),
        ],
        method_diffs=[
            MethodDiff(name="pinMessage", kind="new", details="PUT /chats/{chatId}/pin"),
        ],
        unmatched_schema=[],
        unmatched_code=["InlineKeyboardBuilder"],
    )


class TestToTerminal:

    def test_contains_new_type(self) -> None:
        output = to_terminal(_sample_diff())
        assert "Chat" in output
        assert "NEW" in output or "new" in output.lower()

    def test_contains_changed_type(self) -> None:
        output = to_terminal(_sample_diff())
        assert "User" in output
        assert "email" in output

    def test_contains_new_method(self) -> None:
        output = to_terminal(_sample_diff())
        assert "pinMessage" in output

    def test_contains_summary(self) -> None:
        output = to_terminal(_sample_diff())
        assert "Summary" in output or "summary" in output.lower()

    def test_empty_diff(self) -> None:
        output = to_terminal(DiffResult())
        assert "no changes" in output.lower() or "No changes" in output

    def test_unmatched_code_shown(self) -> None:
        output = to_terminal(_sample_diff())
        assert "InlineKeyboardBuilder" in output


class TestToMarkdown:

    def test_is_valid_markdown(self) -> None:
        output = to_markdown(_sample_diff())
        assert output.startswith("#")

    def test_contains_types_section(self) -> None:
        output = to_markdown(_sample_diff())
        assert "Chat" in output
        assert "User" in output

    def test_contains_methods_section(self) -> None:
        output = to_markdown(_sample_diff())
        assert "pinMessage" in output

    def test_empty_diff(self) -> None:
        output = to_markdown(DiffResult())
        assert "no changes" in output.lower() or "No changes" in output

    def test_unmatched_code_shown(self) -> None:
        output = to_markdown(_sample_diff())
        assert "InlineKeyboardBuilder" in output
