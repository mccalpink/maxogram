"""Интеграционный тест — полный pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from maxogram.utils.schema_diff.analyzer import compare
from maxogram.utils.schema_diff.parser import parse_code, parse_schema
from maxogram.utils.schema_diff.reporter import to_markdown, to_terminal

FIXTURES = Path(__file__).parent / "fixtures"


class TestFullPipeline:
    def test_parse_compare_report(self) -> None:
        """Full cycle: schema + code → diff → report."""
        schema = parse_schema(FIXTURES / "mini_schema.yaml")
        code = parse_code(
            types_dir=FIXTURES / "mini_code" / "types",
            methods_dir=FIXTURES / "mini_code" / "methods",
        )
        diff = compare(schema, code)

        terminal_output = to_terminal(diff)
        assert isinstance(terminal_output, str)
        assert len(terminal_output) > 0

        markdown_output = to_markdown(diff)
        assert markdown_output.startswith("#")

    def test_write_markdown_to_file(self, tmp_path: Path) -> None:
        """Markdown report written to file."""
        schema = parse_schema(FIXTURES / "mini_schema.yaml")
        code = parse_code(
            types_dir=FIXTURES / "mini_code" / "types",
            methods_dir=FIXTURES / "mini_code" / "methods",
        )
        diff = compare(schema, code)
        report = to_markdown(diff)

        out_file = tmp_path / "SCHEMA_DIFF.md"
        out_file.write_text(report)
        assert out_file.exists()
        assert len(out_file.read_text()) > 0

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML → exception."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{{invalid yaml::")
        with pytest.raises(yaml.YAMLError):
            parse_schema(bad_yaml)

    def test_empty_dirs(self, tmp_path: Path) -> None:
        """Empty directories → all schema types in diff."""
        schema = parse_schema(FIXTURES / "mini_schema.yaml")
        types_dir = tmp_path / "types"
        methods_dir = tmp_path / "methods"
        types_dir.mkdir()
        methods_dir.mkdir()
        code = parse_code(types_dir, methods_dir)
        diff = compare(schema, code)
        # With empty code, all schema types should appear as new or unmatched
        assert diff.has_changes is True

    def test_generator_integration(self, tmp_path: Path) -> None:
        """Full pipeline including generator."""
        from maxogram.utils.schema_diff.generator import generate

        schema = parse_schema(FIXTURES / "mini_schema.yaml")
        code = parse_code(
            types_dir=FIXTURES / "mini_code" / "types",
            methods_dir=FIXTURES / "mini_code" / "methods",
        )
        diff = compare(schema, code)

        # Only generate if there are new items
        generate(
            diff,
            schema_types=schema.types,
            schema_methods=schema.methods,
            output_dir=tmp_path,
        )
        # At minimum, the function should run without errors
        # Whether it generates files depends on the fixture diff
