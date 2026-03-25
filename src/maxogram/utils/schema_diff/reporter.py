"""Форматирование DiffResult в текст для терминала и Markdown."""

from __future__ import annotations

from maxogram.utils.schema_diff.models import DiffResult, FieldDiff

# --- Вспомогательные метки ---

_KIND_LABEL: dict[str, str] = {
    "new": "NEW",
    "removed": "REMOVED",
    "changed": "CHANGED",
}

_FIELD_KIND_LABEL: dict[str, str] = {
    "added": "+",
    "removed": "-",
    "changed": "~",
}


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------


def to_terminal(diff: DiffResult) -> str:
    """Вернуть человекочитаемый отчёт для вывода в терминал.

    Иконки: NEW / REMOVED / CHANGED для типов и методов.
    Пустой DiffResult → сообщение «No changes detected».
    """
    if not diff.has_changes and not diff.unmatched_code:
        return "No changes detected."

    lines: list[str] = ["Max API Schema Diff", ""]

    # --- Types ---
    if diff.type_diffs:
        lines.append(f"Types ({len(diff.type_diffs)} change(s)):")
        for td in diff.type_diffs:
            label = _KIND_LABEL.get(td.kind, td.kind.upper())
            lines.append(f"  {label:<9} {td.name}")
            for fd in td.field_diffs:
                lines.append(_format_field_diff_terminal(fd))
        lines.append("")

    # --- Methods ---
    if diff.method_diffs:
        lines.append(f"Methods ({len(diff.method_diffs)} change(s)):")
        for md in diff.method_diffs:
            label = _KIND_LABEL.get(md.kind, md.kind.upper())
            detail = f"  {md.details}" if md.details else ""
            lines.append(f"  {label:<9} {md.name}{detail}")
        lines.append("")

    # --- Unmatched schema ---
    if diff.unmatched_schema:
        lines.append("Unmatched in schema (not in code):")
        for name in diff.unmatched_schema:
            lines.append(f"  {name}")
        lines.append("")

    # --- Unmatched code ---
    if diff.unmatched_code:
        lines.append("Unmatched in code (not in schema):")
        for name in diff.unmatched_code:
            lines.append(f"  {name}")
        lines.append("")

    # --- Summary ---
    lines.append(_build_summary(diff))

    return "\n".join(lines)


def _format_field_diff_terminal(fd: FieldDiff) -> str:
    """Строка терминала для одного FieldDiff."""
    sign = _FIELD_KIND_LABEL.get(fd.kind, "?")
    type_info = fd.schema_type or fd.code_type or ""
    type_str = f": {type_info}" if type_info else ""
    details = f"  ({fd.details})" if fd.details else ""
    kind_note = f"({fd.kind} field)" if not fd.details else f"({fd.kind} field, {fd.details})"
    return f"    {sign} {fd.name}{type_str:<30} {kind_note}{details}"


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------


def to_markdown(diff: DiffResult) -> str:
    """Вернуть отчёт в формате Markdown.

    Использует заголовки #/## и списки.
    Пустой DiffResult → «No changes detected».
    """
    if not diff.has_changes and not diff.unmatched_code:
        return "# Max API Schema Diff\n\nNo changes detected."

    lines: list[str] = ["# Max API Schema Diff", ""]

    # --- Types ---
    if diff.type_diffs:
        lines.append(f"## Types ({len(diff.type_diffs)} change(s))")
        lines.append("")
        for td in diff.type_diffs:
            label = _KIND_LABEL.get(td.kind, td.kind.upper())
            lines.append(f"### `{td.name}` — {label}")
            if td.field_diffs:
                lines.append("")
                lines.append("| Field | Change | Schema type | Code type |")
                lines.append("|-------|--------|-------------|-----------|")
                for fd in td.field_diffs:
                    schema_t = fd.schema_type or ""
                    code_t = fd.code_type or ""
                    details = fd.details or ""
                    kind_col = fd.kind if not details else f"{fd.kind} ({details})"
                    lines.append(f"| `{fd.name}` | {kind_col} | {schema_t} | {code_t} |")
            lines.append("")

    # --- Methods ---
    if diff.method_diffs:
        lines.append(f"## Methods ({len(diff.method_diffs)} change(s))")
        lines.append("")
        lines.append("| Method | Change | Details |")
        lines.append("|--------|--------|---------|")
        for md in diff.method_diffs:
            label = _KIND_LABEL.get(md.kind, md.kind.upper())
            details = md.details or ""
            lines.append(f"| `{md.name}` | {label} | {details} |")
        lines.append("")

    # --- Unmatched schema ---
    if diff.unmatched_schema:
        lines.append("## Unmatched in schema (not in code)")
        lines.append("")
        for name in diff.unmatched_schema:
            lines.append(f"- `{name}`")
        lines.append("")

    # --- Unmatched code ---
    if diff.unmatched_code:
        lines.append("## Unmatched in code (not in schema)")
        lines.append("")
        for name in diff.unmatched_code:
            lines.append(f"- `{name}`")
        lines.append("")

    # --- Summary ---
    lines.append("## Summary")
    lines.append("")
    lines.append(_build_summary(diff))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Общие утилиты
# ---------------------------------------------------------------------------


def _build_summary(diff: DiffResult) -> str:
    """Строка Summary с подсчётом изменений по категориям."""
    parts: list[str] = []

    new_types = sum(1 for td in diff.type_diffs if td.kind == "new")
    removed_types = sum(1 for td in diff.type_diffs if td.kind == "removed")
    changed_types = sum(1 for td in diff.type_diffs if td.kind == "changed")
    new_methods = sum(1 for md in diff.method_diffs if md.kind == "new")
    removed_methods = sum(1 for md in diff.method_diffs if md.kind == "removed")
    changed_methods = sum(1 for md in diff.method_diffs if md.kind == "changed")

    if new_types:
        parts.append(f"{new_types} new type(s)")
    if removed_types:
        parts.append(f"{removed_types} removed type(s)")
    if changed_types:
        parts.append(f"{changed_types} changed type(s)")
    if new_methods:
        parts.append(f"{new_methods} new method(s)")
    if removed_methods:
        parts.append(f"{removed_methods} removed method(s)")
    if changed_methods:
        parts.append(f"{changed_methods} changed method(s)")
    if diff.unmatched_schema:
        parts.append(f"{len(diff.unmatched_schema)} unmatched in schema")
    if diff.unmatched_code:
        parts.append(f"{len(diff.unmatched_code)} unmatched in code")

    summary_body = ", ".join(parts) if parts else "no significant changes"
    return f"Summary: {summary_body}"
