"""CLI entry point для Schema Diff Tool.

Запуск:
    poetry run schema-diff
    python -m maxogram.utils.schema_diff
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.request import urlopen

DEFAULT_SCHEMA_URL = (
    "https://raw.githubusercontent.com/tamtam-chat/tamtam-bot-api-schema/master/schema.yaml"
)


def _download_schema(url: str) -> str:
    """Скачать OpenAPI schema по URL."""
    try:
        with urlopen(url, timeout=30) as resp:  # noqa: S310
            result: str = resp.read().decode("utf-8")
            return result
    except Exception as exc:
        print(f"Cannot download schema: {url}\n{exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Точка входа CLI."""
    parser = argparse.ArgumentParser(
        prog="schema-diff",
        description="Compare Max Bot API OpenAPI schema with maxogram code",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Path to local OpenAPI YAML (default: download from GitHub)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write markdown report to file",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate skeleton files for new types/methods",
    )
    parser.add_argument(
        "--types-dir",
        type=Path,
        default=Path("src/maxogram/types"),
        help="Path to types/ directory (default: src/maxogram/types)",
    )
    parser.add_argument(
        "--methods-dir",
        type=Path,
        default=Path("src/maxogram/methods"),
        help="Path to methods/ directory (default: src/maxogram/methods)",
    )
    args = parser.parse_args()

    try:
        import yaml  # noqa: F401
    except ImportError:
        print("pyyaml is required: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    from maxogram.utils.schema_diff.analyzer import compare
    from maxogram.utils.schema_diff.parser import parse_code, parse_schema
    from maxogram.utils.schema_diff.reporter import to_markdown, to_terminal

    # 1. Parse schema
    if args.schema:
        schema = parse_schema(args.schema)
    else:
        yaml_str = _download_schema(DEFAULT_SCHEMA_URL)
        schema = parse_schema(yaml_str=yaml_str)

    # 2. Parse code
    code = parse_code(args.types_dir, args.methods_dir)

    # 3. Compare
    diff = compare(schema, code)

    # 4. Report
    if args.output:
        report = to_markdown(diff)
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(to_terminal(diff))

    # 5. Generate
    if args.generate:
        try:
            from maxogram.utils.schema_diff.generator import generate
        except ImportError:
            print("Generator module not available yet.", file=sys.stderr)
            sys.exit(1)

        output_dir = Path("generated")
        generate(
            diff,
            schema_types=schema.types,
            schema_methods=schema.methods,
            output_dir=output_dir,
        )
        print(f"Skeletons generated in {output_dir}/")

    sys.exit(1 if diff.has_changes else 0)


if __name__ == "__main__":
    main()
