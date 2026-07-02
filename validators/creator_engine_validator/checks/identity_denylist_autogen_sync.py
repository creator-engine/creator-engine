"""Offline guard for the runtime identity denylist wiring.

This per-PR check verifies what the public PR gate can verify without private
registry access: the generated runtime artifact is not required in the public
checkout, any locally generated artifact is structurally valid runtime data,
and the fleet manifest guard fails open with an explicit advisory instead of
falling back to hardcoded plaintext identities.

Freshness against the live ce-ops identity registry is enforced by the separate
scheduled freshness workflow, which generates and checks the runtime artifact
with access to the private registry. The artifact is gitignored and must not be
committed or packaged.
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
CODE_RUNTIME_ABSENT = "VAL-AUTOGEN-IDENTITY-DENYLIST-RUNTIME-ABSENT"

ARTIFACT_REPO_RELATIVE = Path("validators/creator_engine_validator") / ARTIFACT_RELATIVE
GUARD_RELATIVE = Path("validators/creator_engine_validator/checks/fleet_manifest_guard.py")
CONTRACT = "scripts/gen_identity_denylist.py"


def _repo_root_for(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / GUARD_RELATIVE).is_file() and (candidate / CONTRACT).is_file():
            return candidate
    return None


def _error(code: str, path: Path, message: str) -> ValidationError:
    return make_error(code, path, "", message, CONTRACT)


def validate_repo(repo_root: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    artifact = repo_root / ARTIFACT_REPO_RELATIVE
    if artifact.exists():
        try:
            denylist = load_identity_denylist(artifact)
        except (OSError, IdentityDenylistError, ValueError) as exc:
            errors.append(_error(CODE_UNREADABLE, artifact, f"runtime identity denylist artifact is invalid: {exc}"))
            denylist = None

        if denylist is not None and not denylist.entries:
            errors.append(_error(CODE_UNREADABLE, artifact, "runtime identity denylist artifact is empty"))

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
                "fleet_manifest_guard.py must load and match the generated runtime identity denylist artifact",
            )
        )
    if "CODE_IDENTITY_DENYLIST_UNAVAILABLE" not in source or "warnings" not in source:
        errors.append(
            _error(
                CODE_STALE_WIRING,
                guard,
                "fleet_manifest_guard.py must fail open with an explicit advisory when the runtime identity denylist is absent",
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


def validate_repo_with_warnings(repo_root: Path) -> tuple[list[ValidationError], list[ValidationError]]:
    errors = validate_repo(repo_root)
    warnings: list[ValidationError] = []
    artifact = repo_root / ARTIFACT_REPO_RELATIVE
    if not artifact.exists():
        warnings.append(
            _error(
                CODE_RUNTIME_ABSENT,
                artifact,
                "runtime identity denylist artifact is absent in this checkout; public PR validation skips registry-derived identity tokens and the scheduled ce-ops-backed workflow generates it for freshness checks",
            )
        )
    return errors, warnings


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
    warnings: list[ValidationError] = []
    for root in roots:
        root_errors, root_warnings = validate_repo_with_warnings(root)
        errors.extend(root_errors)
        warnings.extend(root_warnings)
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))
