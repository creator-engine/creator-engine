"""Offline guard for the generated identity denylist artifact.

This per-PR check verifies what the public PR gate can verify without private
registry access: the committed artifact is structurally valid, contains only
hashed identity entries, the fleet manifest guard loads the artifact rather
than a hardcoded plaintext fallback, and the loaded ruleset is non-empty.

Freshness against the live ce-ops identity registry is enforced by the separate
scheduled freshness workflow, which runs the generator with access to the
private registry and fails loudly on drift.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..identity_denylist import ARTIFACT_RELATIVE, IdentityDenylistError, load_identity_denylist
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "identity_denylist_autogen_sync"
CODE_UNREADABLE = "VAL-AUTOGEN-IDENTITY-DENYLIST-UNREADABLE"
CODE_STALE_WIRING = "VAL-AUTOGEN-IDENTITY-DENYLIST-WIRING"

ARTIFACT_REPO_RELATIVE = Path("validators/creator_engine_validator") / ARTIFACT_RELATIVE
GUARD_RELATIVE = Path("validators/creator_engine_validator/checks/fleet_manifest_guard.py")
CONTRACT = "scripts/gen_identity_denylist.py"


def _repo_root_for(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ARTIFACT_REPO_RELATIVE).is_file() and (candidate / GUARD_RELATIVE).is_file():
            return candidate
    return None


def _error(code: str, path: Path, message: str) -> ValidationError:
    return make_error(code, path, "", message, CONTRACT)


def validate_repo(repo_root: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    artifact = repo_root / ARTIFACT_REPO_RELATIVE
    try:
        denylist = load_identity_denylist(artifact)
    except (OSError, IdentityDenylistError, ValueError) as exc:
        errors.append(_error(CODE_UNREADABLE, artifact, f"identity denylist artifact is invalid: {exc}"))
        denylist = None

    if denylist is not None and not denylist.entries:
        errors.append(_error(CODE_UNREADABLE, artifact, "identity denylist artifact is empty"))

    guard = repo_root / GUARD_RELATIVE
    try:
        source = guard.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(_error(CODE_STALE_WIRING, guard, f"fleet manifest guard is unreadable: {exc}"))
        return errors

    if "load_identity_denylist" not in source or "find_identity_matches" not in source:
        errors.append(
            _error(
                CODE_STALE_WIRING,
                guard,
                "fleet_manifest_guard.py must load and match the generated identity denylist artifact",
            )
        )
    if "INTERNAL_LITERAL_TOKENS" in source:
        errors.append(
            _error(
                CODE_STALE_WIRING,
                guard,
                "fleet_manifest_guard.py must not retain a hardcoded plaintext identity fallback",
            )
        )
    return errors


@register(CHECK_NAME, [CODE_UNREADABLE, CODE_STALE_WIRING])
def run(paths: Iterable[Path]) -> CheckResult:
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        root = _repo_root_for(Path(raw))
        if root is None:
            continue
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(root)

    errors: list[ValidationError] = []
    for root in roots:
        errors.extend(validate_repo(root))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
