"""Generate-then-verify guard for the auto-generated schema reference.

This is the verify half of the schema doc-autogen loop: import
``scripts/gen_schema_reference.py`` from the repo being validated, render
``schemas/*.yaml`` in memory, and assert byte-parity against the committed
``.ce/reference/schemas.generated.md``.

The check is read-only. Remediation for stale output is:
``python scripts/gen_schema_reference.py --write`` and commit the regenerated
artifact.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "schema_reference_autogen_sync"

CODE_STALE = "VAL-AUTOGEN-STALE-SCHEMA"
CODE_UNREADABLE = "VAL-AUTOGEN-SCHEMA-UNREADABLE"

DOC_RELATIVE = Path(".ce/reference/schemas.generated.md")
GENERATOR_RELATIVE = Path("scripts/gen_schema_reference.py")
CONTRACT = str(GENERATOR_RELATIVE)


def _repo_root_for(path: Path) -> Path | None:
    """Find the repo root by walking up to a checkout carrying the generator."""
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / GENERATOR_RELATIVE).is_file():
            return candidate
    return None


def _load_generator(repo_root: Path):
    """Import the generator module from this repo root by file path."""
    gen_path = repo_root / GENERATOR_RELATIVE
    spec = importlib.util.spec_from_file_location(
        "creator_engine_validator._gen_schema_reference", gen_path
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load generator at {gen_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_repo(repo_root: Path) -> list[ValidationError]:
    try:
        generator = _load_generator(repo_root)
        rendered = generator.render(repo_root)
    except Exception as exc:  # noqa: BLE001 - fail closed on any render failure
        return [
            make_error(
                CODE_UNREADABLE,
                repo_root / GENERATOR_RELATIVE,
                "",
                f"schema-reference generator is unrenderable: {exc}",
                CONTRACT,
            )
        ]

    doc = repo_root / Path(getattr(generator, "DOC_RELATIVE", DOC_RELATIVE))
    if not doc.is_file():
        return [
            make_error(
                CODE_STALE,
                doc,
                "",
                "generated schema reference is missing; run "
                "`python scripts/gen_schema_reference.py --write` and commit it",
                CONTRACT,
            )
        ]

    try:
        committed = doc.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            make_error(
                CODE_UNREADABLE,
                doc,
                "",
                f"generated schema reference is unreadable: {exc}",
                CONTRACT,
            )
        ]

    if committed != rendered:
        return [
            make_error(
                CODE_STALE,
                doc,
                "",
                "generated schema reference is stale relative to schemas/*.yaml; "
                "run `python scripts/gen_schema_reference.py --write` and commit "
                "the regenerated .ce/reference/schemas.generated.md",
                CONTRACT,
            )
        ]
    return []


@register(CHECK_NAME, [CODE_STALE, CODE_UNREADABLE])
def run(paths: Iterable[Path]) -> CheckResult:
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        root = _repo_root_for(Path(raw))
        if root is None:
            continue
        resolved = root.resolve()
        if resolved not in seen:
            seen.add(resolved)
            roots.append(root)

    errors: list[ValidationError] = []
    for root in roots:
        errors.extend(validate_repo(root))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
