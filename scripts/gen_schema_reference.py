#!/usr/bin/env python3
"""Deterministic schema-reference generator for ``schemas/*.yaml``.

This is the schemas companion to ``scripts/gen_cli_reference.py``: it projects
the committed JSON-schema YAML files into a generated Markdown reference and
supports the same non-mutating ``--check`` and mutating ``--write`` modes.

The projection is intentionally pure and dependency-free. It reads only tracked
schema files under ``schemas/*.yaml``, orders them by repo-relative path, and
emits no timestamps, usernames, host paths, or environment-derived content.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent

DOC_RELATIVE = Path(".ce/reference/schemas.generated.md")
SCHEMAS_GLOB = "schemas/*.yaml"

_AUTOGEN_HEADER = (
    "<!-- ce-autogen: generator=scripts/gen_schema_reference.py "
    "source=schemas/*.yaml -->"
)


@dataclass(frozen=True)
class Field:
    name: str
    shape: str
    constraints: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class SchemaReference:
    path: Path
    schema_id: str
    title: str
    description: str
    root_type: str
    required: tuple[str, ...]
    fields: tuple[Field, ...]
    item_required: tuple[str, ...]
    item_fields: tuple[Field, ...]
    defs: tuple[Field, ...]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _key_and_value(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith("- "):
        return None
    if ":" not in stripped:
        return None
    key, value = stripped.split(":", 1)
    return _unquote(key.strip()), value.strip()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _inline_list(value: str) -> tuple[str, ...]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return ()
    inner = value[1:-1].strip()
    if not inner:
        return ()
    return tuple(_unquote(part.strip()) for part in inner.split(","))


def _md_escape(text: str) -> str:
    return " ".join(text.replace("|", "\\|").split())


def _truncate(text: str, *, limit: int = 220) -> str:
    text = _md_escape(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _scalar_at(lines: Sequence[str], key: str, indent: int) -> str:
    prefix = f"{key}:"
    for line in lines:
        if _indent(line) != indent:
            continue
        stripped = line.strip()
        if not stripped.startswith(prefix):
            continue
        value = stripped[len(prefix) :].strip()
        if value in {"|", "|-", "|+", ">", ">-", ">+"}:
            return ""
        return _unquote(value)
    return ""


def _section_bounds(
    lines: Sequence[str], key: str, indent: int, *, start: int = 0, end: int | None = None
) -> tuple[int, int] | None:
    end = len(lines) if end is None else end
    prefix = f"{key}:"
    for idx in range(start, end):
        line = lines[idx]
        if _indent(line) == indent and line.strip().startswith(prefix):
            stop = idx + 1
            while stop < end:
                if lines[stop].strip() and _indent(lines[stop]) <= indent:
                    break
                stop += 1
            return idx + 1, stop
    return None


def _list_at(
    lines: Sequence[str], key: str, indent: int, *, start: int = 0, end: int | None = None
) -> tuple[str, ...]:
    end = len(lines) if end is None else end
    prefix = f"{key}:"
    for idx in range(start, end):
        line = lines[idx]
        if _indent(line) != indent:
            continue
        stripped = line.strip()
        if not stripped.startswith(prefix):
            continue
        value = stripped[len(prefix) :].strip()
        inline = _inline_list(value)
        if inline:
            return inline
        out: list[str] = []
        item_indent = indent + 2
        cursor = idx + 1
        while cursor < end:
            candidate = lines[cursor]
            if candidate.strip() and _indent(candidate) <= indent:
                break
            stripped_candidate = candidate.strip()
            if _indent(candidate) == item_indent and stripped_candidate.startswith("- "):
                out.append(_unquote(stripped_candidate[2:].strip()))
            cursor += 1
        return tuple(out)
    return ()


def _block_scalar_at(lines: Sequence[str], key: str, indent: int) -> str:
    prefix = f"{key}:"
    for idx, line in enumerate(lines):
        if _indent(line) != indent or not line.strip().startswith(prefix):
            continue
        value = line.strip()[len(prefix) :].strip()
        if value not in {"|", "|-", "|+", ">", ">-", ">+"}:
            return _unquote(value)
        body: list[str] = []
        cursor = idx + 1
        while cursor < len(lines):
            candidate = lines[cursor]
            if candidate.strip() and _indent(candidate) <= indent:
                break
            body.append(candidate.strip())
            cursor += 1
        paragraphs = "\n".join(body).strip().split("\n\n")
        return paragraphs[0].strip() if paragraphs else ""
    return ""


def _named_blocks(
    lines: Sequence[str], section: str, section_indent: int, name_indent: int
) -> list[tuple[str, list[str]]]:
    bounds = _section_bounds(lines, section, section_indent)
    if bounds is None:
        return []
    start, end = bounds
    blocks: list[tuple[str, list[str]]] = []
    cursor = start
    while cursor < end:
        line = lines[cursor]
        parsed = _key_and_value(line)
        if _indent(line) == name_indent and parsed is not None:
            name, _ = parsed
            stop = cursor + 1
            while stop < end:
                if lines[stop].strip() and _indent(lines[stop]) <= name_indent:
                    break
                stop += 1
            blocks.append((name, list(lines[cursor:stop])))
            cursor = stop
            continue
        cursor += 1
    return blocks


def _named_blocks_in_range(
    lines: Sequence[str],
    start: int,
    end: int,
    section: str,
    section_indent: int,
    name_indent: int,
) -> list[tuple[str, list[str]]]:
    bounds = _section_bounds(lines, section, section_indent, start=start, end=end)
    if bounds is None:
        return []
    sub_start, sub_end = bounds
    blocks: list[tuple[str, list[str]]] = []
    cursor = sub_start
    while cursor < sub_end:
        line = lines[cursor]
        parsed = _key_and_value(line)
        if _indent(line) == name_indent and parsed is not None:
            name, _ = parsed
            stop = cursor + 1
            while stop < sub_end:
                if lines[stop].strip() and _indent(lines[stop]) <= name_indent:
                    break
                stop += 1
            blocks.append((name, list(lines[cursor:stop])))
            cursor = stop
            continue
        cursor += 1
    return blocks


def _has_direct_section(block: Sequence[str], key: str, indent: int) -> bool:
    prefix = f"{key}:"
    return any(_indent(line) == indent and line.strip().startswith(prefix) for line in block)


def _field_from_block(name: str, block: Sequence[str]) -> Field:
    header_indent = _indent(block[0])
    direct = header_indent + 2
    field_type = _scalar_at(block, "type", direct)
    type_list = _list_at(block, "type", direct)
    ref = _scalar_at(block, "$ref", direct)
    const = _scalar_at(block, "const", direct)
    enum = _list_at(block, "enum", direct)

    shape_parts: list[str] = []
    if field_type:
        shape_parts.append(field_type)
    elif type_list:
        shape_parts.append(" | ".join(type_list))
    if ref:
        shape_parts.append(f"$ref {ref}")
    if _has_direct_section(block, "oneOf", direct):
        shape_parts.append("oneOf")
    if _has_direct_section(block, "anyOf", direct):
        shape_parts.append("anyOf")
    if _has_direct_section(block, "allOf", direct):
        shape_parts.append("allOf")
    if not shape_parts and const:
        shape_parts.append("const")
    if not shape_parts and enum:
        shape_parts.append("enum")
    if not shape_parts:
        shape_parts.append("unspecified")

    constraints: list[str] = []
    if const:
        constraints.append(f"const `{_md_escape(const)}`")
    if enum:
        constraints.append("enum " + ", ".join(f"`{_md_escape(item)}`" for item in enum))
    for key in (
        "pattern",
        "format",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
        "uniqueItems",
        "additionalProperties",
        "unevaluatedProperties",
    ):
        value = _scalar_at(block, key, direct)
        if value:
            constraints.append(f"{key} `{_md_escape(value)}`")

    description = _block_scalar_at(block, "description", direct)
    return Field(
        name=name,
        shape="; ".join(shape_parts),
        constraints=tuple(constraints),
        description=_truncate(description),
    )


def _schema_reference(path: Path, repo_root: Path) -> SchemaReference:
    lines = path.read_text(encoding="utf-8").splitlines()
    schema_id = _scalar_at(lines, "$id", 0)
    title = _scalar_at(lines, "title", 0)
    description = _truncate(_block_scalar_at(lines, "description", 0))
    root_type = _scalar_at(lines, "type", 0) or "unspecified"
    required = _list_at(lines, "required", 0)
    fields = tuple(
        _field_from_block(name, block)
        for name, block in _named_blocks(lines, "properties", 0, 2)
    )

    item_required: tuple[str, ...] = ()
    item_fields: tuple[Field, ...] = ()
    item_bounds = _section_bounds(lines, "items", 0)
    if item_bounds is not None:
        start, end = item_bounds
        item_required = _list_at(lines, "required", 2, start=start, end=end)
        item_fields = tuple(
            _field_from_block(name, block)
            for name, block in _named_blocks_in_range(lines, start, end, "properties", 2, 4)
        )

    defs = tuple(
        _field_from_block(name, block)
        for name, block in _named_blocks(lines, "$defs", 0, 2)
    )
    return SchemaReference(
        path=path.relative_to(repo_root),
        schema_id=schema_id,
        title=title,
        description=description,
        root_type=root_type,
        required=required,
        fields=fields,
        item_required=item_required,
        item_fields=item_fields,
        defs=defs,
    )


def _schema_paths(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "schemas").glob("*.yaml"), key=lambda path: path.name)


def _required_cell(values: Sequence[str]) -> str:
    if not values:
        return "_None declared._"
    return ", ".join(f"`{_md_escape(value)}`" for value in values)


def _render_field_table(lines: list[str], fields: Sequence[Field], required: Sequence[str]) -> None:
    if not fields:
        lines.append("_No properties declared._")
        lines.append("")
        return

    required_set = set(required)
    lines.append("| Property | Shape | Required | Constraints | Description |")
    lines.append("| --- | --- | --- | --- | --- |")
    for field in fields:
        constraints = "<br>".join(field.constraints)
        required_cell = "yes" if field.name in required_set else "no"
        lines.append(
            "| "
            f"`{_md_escape(field.name)}` | "
            f"{_md_escape(field.shape)} | "
            f"{required_cell} | "
            f"{constraints} | "
            f"{field.description} |"
        )
    lines.append("")


def project(references: Sequence[SchemaReference]) -> str:
    lines: list[str] = []
    lines.append(_AUTOGEN_HEADER)
    lines.append("")
    lines.append("# Schema reference")
    lines.append("")
    lines.append(
        "GENERATED FILE -- do not edit by hand. This is a deterministic "
        "projection of `schemas/*.yaml`. To refresh it, run "
        "`python scripts/gen_schema_reference.py --write` and commit the result; "
        "a stale committed copy fails the validator gate "
        "(`VAL-AUTOGEN-STALE-SCHEMA`)."
    )
    lines.append("")
    lines.append(f"Schema files: {len(references)}")
    lines.append("")
    lines.append("## Index")
    lines.append("")
    lines.append("| Schema | Title | Root type |")
    lines.append("| --- | --- | --- |")
    for ref in references:
        lines.append(
            f"| `{ref.path.as_posix()}` | {_md_escape(ref.title)} | "
            f"`{_md_escape(ref.root_type)}` |"
        )
    lines.append("")

    lines.append("## Schemas")
    lines.append("")
    for ref in references:
        lines.append(f"### `{ref.path.as_posix()}`")
        lines.append("")
        lines.append("| Metadata | Value |")
        lines.append("| --- | --- |")
        lines.append(f"| Title | {_md_escape(ref.title)} |")
        lines.append(f"| `$id` | `{_md_escape(ref.schema_id)}` |")
        lines.append(f"| Root type | `{_md_escape(ref.root_type)}` |")
        lines.append("")
        if ref.description:
            lines.append(ref.description)
            lines.append("")

        lines.append("Required fields:")
        lines.append("")
        lines.append(_required_cell(ref.required))
        lines.append("")
        lines.append("Properties:")
        lines.append("")
        _render_field_table(lines, ref.fields, ref.required)

        if ref.item_fields or ref.item_required:
            lines.append("Array item required fields:")
            lines.append("")
            lines.append(_required_cell(ref.item_required))
            lines.append("")
            lines.append("Array item properties:")
            lines.append("")
            _render_field_table(lines, ref.item_fields, ref.item_required)

        if ref.defs:
            lines.append("Definitions:")
            lines.append("")
            _render_field_table(lines, ref.defs, ())

    return "\n".join(lines).rstrip("\n") + "\n"


def render(repo_root: Path | None = None) -> str:
    """Render the schema reference from ``schemas/*.yaml`` under ``repo_root``."""
    root = _REPO_ROOT if repo_root is None else repo_root
    refs = tuple(_schema_reference(path, root) for path in _schema_paths(root))
    return project(refs)


def _doc_path(repo_root: Path) -> Path:
    return repo_root / DOC_RELATIVE


def check(repo_root: Path) -> tuple[bool, str]:
    rendered = render(repo_root)
    doc = _doc_path(repo_root)
    if not doc.is_file():
        return (
            False,
            f"{DOC_RELATIVE} is missing; run "
            f"`python scripts/gen_schema_reference.py --write` and commit it.",
        )
    committed = doc.read_text(encoding="utf-8")
    if _sha256_text(committed) == _sha256_text(rendered):
        return True, f"{DOC_RELATIVE} is current with schemas/*.yaml."
    return (
        False,
        f"{DOC_RELATIVE} is stale "
        f"(committed sha256={_sha256_text(committed)}, "
        f"generated sha256={_sha256_text(rendered)}); run "
        f"`python scripts/gen_schema_reference.py --write` and commit it.",
    )


def write(repo_root: Path) -> Path:
    rendered = render(repo_root)
    doc = _doc_path(repo_root)
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(rendered, encoding="utf-8")
    return doc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gen_schema_reference",
        description="Generate or verify the schema reference (.ce/reference/schemas.generated.md).",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="read-only: render and diff against the committed doc; exit non-zero if stale",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="render and write the committed doc in place",
    )
    parser.add_argument(
        "--repo-root",
        default=str(_REPO_ROOT),
        help="repo root containing .ce/reference/schemas.generated.md (default: this checkout)",
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    if args.write:
        written = write(repo_root)
        print(f"wrote {written.relative_to(repo_root)}")
        return 0

    ok, message = check(repo_root)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
