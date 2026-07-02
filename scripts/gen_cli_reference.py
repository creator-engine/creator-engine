#!/usr/bin/env python3
"""Deterministic ``ce`` CLI-reference generator (doc-autogen Tier-1 pilot).

This is the first slice of the CE doc-autogen program
(``.ce/state/research/CE_DOC_AUTOGEN_DESIGN_20260627.md``, §2.2.1 + Phase 0).

It introspects the ``ce`` argparse tree
(:func:`creator_engine_validator.ce_cli._build_parser`) **read-only** and
projects it into a Markdown CLI reference. The projection is a pure
``project(parser) -> text`` function — deterministic, no timestamps, no
environment-dependent content — so a CI ``--check`` run can re-render and assert
byte-parity against the committed ``.ce/reference/cli.generated.md``. A stale committed
doc fails closed.

Two run modes (mirroring ``gen-controller-bootstrap.py`` and the design's
``--check``/``--write`` contract):

- ``--check`` (CI / read-only): render in memory, compare to the committed doc,
  exit non-zero on any diff. **Never writes.**
- ``--write`` (developer / local): render and write the committed doc in place,
  so the dev workflow is "run generator -> commit", not hand-edit.

Internal-only command groups (``ce_cli.INTERNAL_COMMAND_GROUPS``) and any
``argparse.SUPPRESS``-helped command are projected exactly as ``ce --help``
presents them: omitted from the public reference. This keeps the generated doc
product-lens-safe — it is nothing more than the public ``ce --help`` surface.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VALIDATORS = _REPO_ROOT / "validators"
if str(_VALIDATORS) not in sys.path:
    sys.path.insert(0, str(_VALIDATORS))

from creator_engine_validator.ce_cli import (  # noqa: E402
    INTERNAL_COMMAND_GROUPS,
    _build_parser,
)

# The committed artifact this generator owns (whole-file byte-parity).
#
# INTERNAL location (``.ce/reference/`` — NOT the served public ``docs/`` tree):
# the reference is a faithful projection of every ``ce`` ``help=`` string, some
# of which legitimately carry internal references (ce-ops# tickets, seat ids).
# Since the generator introspects ``ce_cli.py`` READ-ONLY it must not rewrite
# those strings, so the artifact is kept OFF the public-docs surface and out of
# the public-docs confidentiality guard's scan set (design §3.3: the public and
# internal generator sets are disjoint). A later phase can add a public,
# product-lens-scrubbed projection as a separate generated artifact.
DOC_RELATIVE = Path(".ce/reference/cli.generated.md")

# A machine-readable provenance header so downstream consumers (e.g. the
# support-agent corpus, §3.2 of the design) can trust the doc as
# fresh-by-construction and distinguish generated from hand-authored content.
_AUTOGEN_HEADER = (
    "<!-- ce-autogen: generator=scripts/gen_cli_reference.py "
    "source=validators/creator_engine_validator/ce_cli.py:_build_parser -->"
)


def _sha256_text(text: str) -> str:
    """sha256 of UTF-8 text (mirrors the parity guard's byte-hash stance)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_environment(text: str) -> str:
    """Strip environment-dependent content so the projection is host-stable.

    The generate-then-verify invariant requires byte-identical output on every
    machine and CI runner. A few ``ce`` ``help=``/``default=`` strings embed the
    *running interpreter path* (``sys.executable`` — e.g. the ``validate-pr
    --test-command`` default), which differs per venv/host. Normalize that one
    interpreter token to a stable placeholder so a dev's local render and CI's
    render agree byte-for-byte. Anything else stays verbatim.
    """
    if not text:
        return text
    return text.replace(sys.executable, "<python>")


def _is_public(name: str, help_text: object) -> bool:
    """A command/group is public iff ``ce --help`` would list it.

    Mirrors the kernel's own visibility rules: internal command groups
    (``INTERNAL_COMMAND_GROUPS``) and ``argparse.SUPPRESS``-helped commands are
    hidden from ``ce --help`` and so are omitted from the public reference.
    """
    if name in INTERNAL_COMMAND_GROUPS:
        return False
    if help_text is argparse.SUPPRESS:
        return False
    return True


def _option_actions(parser: argparse.ArgumentParser) -> list[argparse.Action]:
    """Optional/flag actions (excluding the auto -h/--help), in declared order."""
    out: list[argparse.Action] = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            continue
        if isinstance(action, argparse._HelpAction):
            continue
        if not action.option_strings:
            continue
        if action.help is argparse.SUPPRESS:
            continue
        out.append(action)
    return out


def _positional_actions(parser: argparse.ArgumentParser) -> list[argparse.Action]:
    """Positional actions (no option strings, not a subparser), declared order."""
    out: list[argparse.Action] = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            continue
        if action.option_strings:
            continue
        if action.help is argparse.SUPPRESS:
            continue
        out.append(action)
    return out


def _subparsers_action(
    parser: argparse.ArgumentParser,
) -> argparse._SubParsersAction | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _md_escape(text: str) -> str:
    """Normalize host-dependent content, escape the cell delimiter, collapse NLs."""
    text = _normalize_environment(text)
    return text.replace("\n", " ").replace("|", "\\|").strip()


def _choices_str(action: argparse.Action) -> str:
    if action.choices is None:
        return ""
    try:
        rendered = sorted(str(c) for c in action.choices)
    except TypeError:
        rendered = [str(c) for c in action.choices]
    return ", ".join(rendered)


def _option_row(action: argparse.Action) -> str:
    flags = ", ".join(f"`{f}`" for f in action.option_strings)
    required = "yes" if getattr(action, "required", False) else "no"
    choices = _choices_str(action)
    choices_cell = f"`{_md_escape(choices)}`" if choices else ""
    help_text = _md_escape(action.help or "")
    return f"| {flags} | {required} | {choices_cell} | {help_text} |"


def _positional_row(action: argparse.Action) -> str:
    name = action.metavar or action.dest
    choices = _choices_str(action)
    choices_cell = f"`{_md_escape(choices)}`" if choices else ""
    help_text = _md_escape(action.help or "")
    return f"| `{_md_escape(str(name))}` | {choices_cell} | {help_text} |"


def _render_leaf(lines: list[str], path: str, parser: argparse.ArgumentParser) -> None:
    """Render one leaf command (no further subcommands) as a section."""
    lines.append(f"### `{path}`")
    lines.append("")
    if parser.description:
        lines.append(_md_escape(parser.description))
        lines.append("")

    positionals = _positional_actions(parser)
    if positionals:
        lines.append("Positional arguments:")
        lines.append("")
        lines.append("| Argument | Choices | Description |")
        lines.append("| --- | --- | --- |")
        for action in positionals:
            lines.append(_positional_row(action))
        lines.append("")

    options = _option_actions(parser)
    if options:
        lines.append("Options:")
        lines.append("")
        lines.append("| Option | Required | Choices | Description |")
        lines.append("| --- | --- | --- | --- |")
        for action in options:
            lines.append(_option_row(action))
        lines.append("")

    if not positionals and not options:
        lines.append("_No arguments._")
        lines.append("")


def _render_command(
    lines: list[str], path: str, help_text: str, parser: argparse.ArgumentParser
) -> None:
    """Recursively render a command, descending into public subcommands."""
    sub = _subparsers_action(parser)
    if sub is None or not sub.choices:
        _render_leaf(lines, path, parser)
        return

    # A command group with subcommands: header + the public subcommands sorted.
    lines.append(f"### `{path}`")
    lines.append("")
    if help_text:
        lines.append(_md_escape(help_text))
        lines.append("")

    # Map each subparser to its help string (from the _ChoicesPseudoAction list).
    sub_help: dict[str, str] = {}
    for pseudo in sub._choices_actions:
        sub_help[pseudo.dest] = pseudo.help or ""

    for name in sorted(sub.choices):
        child = sub.choices[name]
        child_help = sub_help.get(name, "")
        if not _is_public(name, child_help):
            continue
        _render_command(lines, f"{path} {name}", child_help, child)


def project(parser: argparse.ArgumentParser) -> str:
    """Pure projection: argparse tree -> deterministic Markdown CLI reference.

    No timestamps, no environment-dependent content. Stable ordering (groups and
    subcommands sorted), so re-rendering the same parser yields byte-identical
    output — the invariant the generate-then-verify guard depends on.
    """
    lines: list[str] = []
    lines.append(_AUTOGEN_HEADER)
    lines.append("")
    lines.append(f"# `{parser.prog}` CLI reference")
    lines.append("")
    lines.append(
        "GENERATED FILE — do not edit by hand. This is a deterministic projection "
        "of the `ce` argparse command tree. To refresh it, run "
        "`python scripts/gen_cli_reference.py --write` and commit the result; a "
        "stale committed copy fails the validator gate "
        "(`VAL-AUTOGEN-STALE-CLI`)."
    )
    lines.append("")
    if parser.description:
        lines.append(_md_escape(parser.description))
        lines.append("")

    top_options = _option_actions(parser)
    if top_options:
        lines.append("## Top-level options")
        lines.append("")
        lines.append("| Option | Required | Choices | Description |")
        lines.append("| --- | --- | --- | --- |")
        for action in top_options:
            lines.append(_option_row(action))
        lines.append("")

    sub = _subparsers_action(parser)
    lines.append("## Commands")
    lines.append("")
    if sub is None or not sub.choices:
        lines.append("_No commands._")
        body = "\n".join(lines).rstrip("\n") + "\n"
        return body

    sub_help: dict[str, str] = {}
    for pseudo in sub._choices_actions:
        sub_help[pseudo.dest] = pseudo.help or ""

    for name in sorted(sub.choices):
        if not _is_public(name, sub_help.get(name, "")):
            continue
        child = sub.choices[name]
        _render_command(lines, name, sub_help.get(name, ""), child)

    body = "\n".join(lines).rstrip("\n") + "\n"
    return body


def render() -> str:
    """Render the CLI reference from the live ``ce`` parser."""
    return project(_build_parser())


def _doc_path(repo_root: Path) -> Path:
    return repo_root / DOC_RELATIVE


def check(repo_root: Path) -> tuple[bool, str]:
    """Return (ok, message). ok=False when the committed doc is stale/missing."""
    rendered = render()
    doc = _doc_path(repo_root)
    if not doc.is_file():
        return (
            False,
            f"{DOC_RELATIVE} is missing; run "
            f"`python scripts/gen_cli_reference.py --write` and commit it.",
        )
    committed = doc.read_text(encoding="utf-8")
    if _sha256_text(committed) == _sha256_text(rendered):
        return True, f"{DOC_RELATIVE} is current with the ce CLI argparse tree."
    return (
        False,
        f"{DOC_RELATIVE} is stale "
        f"(committed sha256={_sha256_text(committed)}, "
        f"generated sha256={_sha256_text(rendered)}); run "
        f"`python scripts/gen_cli_reference.py --write` and commit it.",
    )


def write(repo_root: Path) -> Path:
    """Render and write the committed doc in place. Returns the written path."""
    rendered = render()
    doc = _doc_path(repo_root)
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(rendered, encoding="utf-8")
    return doc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gen_cli_reference",
        description="Generate or verify the ce CLI reference (.ce/reference/cli.generated.md).",
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
        help="repo root containing .ce/reference/cli.generated.md (default: this checkout)",
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
