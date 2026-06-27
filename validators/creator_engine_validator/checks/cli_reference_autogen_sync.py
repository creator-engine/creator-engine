"""Generate-then-verify guard for the auto-generated ``ce`` CLI reference.

Doc-autogen Tier-1 pilot (``.ce/state/research/CE_DOC_AUTOGEN_DESIGN_20260627.md``
§2.2.1 + Phase 0). This is the *verify* half of the generate-then-verify loop:
it imports the generator's pure ``project()`` projection of the ``ce`` argparse
tree, renders it in memory, and asserts byte-parity against the committed
``.ce/reference/cli.generated.md``. A stale committed doc fails closed.

Because this check is ``@register``'d it rides the existing validator gate that
runs on ``pull_request`` (``.github/workflows/validate.yml``) with zero new CI
plumbing — so a PR that edits a ``help=`` string in ``ce_cli.py`` without
regenerating the reference cannot go green (cannot merge / cannot auto-merge).
Remediation: ``python scripts/gen_cli_reference.py --write`` and commit.

The check is read-only: it never writes the artifact (only the generator's
``--write`` mode mutates), keeping the gate non-mutating.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "cli_reference_autogen_sync"

CODE_STALE = "VAL-AUTOGEN-STALE-CLI"
CODE_UNREADABLE = "VAL-AUTOGEN-CLI-UNREADABLE"

# The internal (NOT public-docs) committed artifact; kept in sync with the
# generator's own ``DOC_RELATIVE`` (the check asserts they agree per-repo-root).
DOC_RELATIVE = Path(".ce/reference/cli.generated.md")
GENERATOR_RELATIVE = Path("scripts/gen_cli_reference.py")
CONTRACT = str(GENERATOR_RELATIVE)


def _repo_root_for(path: Path) -> Path | None:
    """Find the repo root by walking up to a checkout carrying the generator."""
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / GENERATOR_RELATIVE).is_file():
            return candidate
    return None


def _load_generator(repo_root: Path):
    """Import the generator module from this repo root by file path.

    The generator lives under ``scripts/`` (not an importable package), so load
    it directly from the resolved repo root rather than the package namespace —
    this keeps the check correct inside isolated worktrees and the merge-queue
    checkout, not just the dev box.
    """
    gen_path = repo_root / GENERATOR_RELATIVE
    spec = importlib.util.spec_from_file_location(
        "creator_engine_validator._gen_cli_reference", gen_path
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load generator at {gen_path}")
    module = importlib.util.module_from_spec(spec)
    # Register before exec so the generator's own relative imports resolve.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_repo(repo_root: Path) -> list[ValidationError]:
    try:
        generator = _load_generator(repo_root)
        rendered = generator.render()
    except Exception as exc:  # noqa: BLE001 - fail closed on any render failure
        return [
            make_error(
                CODE_UNREADABLE,
                repo_root / GENERATOR_RELATIVE,
                "",
                f"CLI-reference generator is unrenderable: {exc}",
                CONTRACT,
            )
        ]

    # Resolve the artifact path from the generator itself so the check and the
    # generator can never disagree about where the committed doc lives.
    doc = repo_root / Path(getattr(generator, "DOC_RELATIVE", DOC_RELATIVE))
    if not doc.is_file():
        return [
            make_error(
                CODE_STALE,
                doc,
                "",
                "generated CLI reference is missing; run "
                "`python scripts/gen_cli_reference.py --write` and commit it",
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
                f"generated CLI reference is unreadable: {exc}",
                CONTRACT,
            )
        ]

    if committed != rendered:
        return [
            make_error(
                CODE_STALE,
                doc,
                "",
                "generated CLI reference is stale relative to the ce argparse "
                "tree; run `python scripts/gen_cli_reference.py --write` and "
                "commit the regenerated .ce/reference/cli.generated.md",
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
