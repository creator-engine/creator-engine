"""``v3_naming_hygiene`` — keep the v3 surface free of bootstrapping-harness residue (G-4.1).

A self/structural fitness-function check (it inspects this package's own v3
surface, not sidecar artifacts; sibling to ``version_boundary``). CE terminology
must stay DECOUPLED from implementation in the v3/v3.1 surface: v1 retains the
``.hermes/`` local-state root (frozen, coexistence) but v3/v3.1 must NOT inherit
it, and the v3 surface must not embed the CE bootstrapping-harness names. This
check enforces that **by machine, not by chance** — green on day one (the v3
surface is clean) and ratcheting (a new residue fails).

It reads the version-line taxonomy from ``creator_engine_validator._versions`` and
asserts, against the v3 CODE surface (``classify(...) == "v3"``) and the declared
v3 SCHEMA surface (``_versions.V3_SCHEMAS``):

  * RESIDUE — no v3-classified CODE module or v3 SCHEMA file may contain a CE
    bootstrapping-harness residue token (``.hermes`` / ``Hermes`` / ``Nefarious``,
    case-insensitive), unless the exact ``(file, token)`` is a baselined entry in
    ``_versions.BASELINE_V3_NAMING_ALLOWLIST`` (ratchet floor; expected EMPTY).
  * COMPLETENESS — every declared ``V3_SCHEMAS`` file must still exist (catches a
    rename that would silently drop schema coverage).
  * Stale allowlist entries (no longer present) are reported as warnings.

Deliberately NOT forbidden: legitimate transport/runtime ADAPTER names
(``Claude``/``Codex``/``gVisor``/``ACP``/``OpenShell``) — impl-named adapters are
correct (e.g. ``runner.cc_hook_adapter``, ``runner.gvisor_proxy_backend``). The
residue token-set is precisely the CE bootstrapping harness, nothing else.

Scope EXCLUDES: v3 DOCS (they legitimately point to the current ``.hermes/``
research root), the v1/shared surface (v1 checks validate v1's ``.hermes/``
layout), and the grandfathered legacy corpus. Those — plus the v1
``.hermes/``→``.ce/`` rename — migrate in a separate, post-pilot, ratifiable
terminology/naming gate; they are NOT this check's concern.

Exception to that exclusion: the load-bearing ``ce launch`` surface is now the
live v3 governed-seat spawn path. It is still version-classified as v1 for
coexistence, but its state-emitting launch defaults must not point at the
reserved ``.hermes/`` root.

Contract: ``docs/contracts/v3-naming-hygiene.md``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from .. import _versions as ver
from . import register
from .version_boundary import PKG, _package_dir, _rel, discover_modules

CHECK_NAME = "v3_naming_hygiene"
CONTRACT = "docs/contracts/v3-naming-hygiene.md"

CODE_RESIDUE = "VAL-V3NAME-RESIDUE"          # harness-name residue in a v3 CODE/SCHEMA file
CODE_MISSING_SCHEMA = "VAL-V3NAME-MISSING-SCHEMA"  # declared v3 schema no longer exists
CODE_STALE = "VAL-V3NAME-STALE-ALLOW"        # allowlist entry whose residue is gone (warning)

#: The CE bootstrapping-harness residue tokens (case-insensitive). ``.hermes`` is a
#: subset of the ``hermes`` substring, so ``hermes`` covers the path token too.
_RESIDUE_RE = re.compile(r"hermes|nefarious", re.IGNORECASE)
_HERMES_PATH_RE = re.compile(r"\.hermes", re.IGNORECASE)
_LAUNCH_SURFACE_REL_PATHS = (
    "validators/creator_engine_validator/launch_runtime.py",
    "validators/creator_engine_validator/ce_cli.py",
)


def _repo_root() -> Path:
    # .../validators/creator_engine_validator -> .../validators -> repo root
    return _package_dir().parent.parent


def _relpath(path: Path, repo_root: Path) -> str:
    """Repo-root-relative path string, robust to a path outside the tree (tests)."""
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _scan(text: str) -> dict[str, list[int]]:
    """Map each distinct (lowercased) residue token to the 1-based lines it occurs on."""
    found: dict[str, list[int]] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _RESIDUE_RE.finditer(line):
            token = match.group(0).lower()
            found.setdefault(token, [])
            if lineno not in found[token]:
                found[token].append(lineno)
    return found


def _scan_hermes_path(text: str) -> dict[str, list[int]]:
    """Map launch-surface ``.hermes`` path residue to 1-based line numbers."""
    found: dict[str, list[int]] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _HERMES_PATH_RE.search(line):
            found.setdefault(".hermes", []).append(lineno)
    return found


def _between_markers(text: str, start: str, end: str) -> str:
    start_idx = text.find(start)
    if start_idx == -1:
        return ""
    end_idx = text.find(end, start_idx)
    if end_idx == -1:
        return text[start_idx:]
    return text[start_idx:end_idx]


def _launch_surface_text(rel_path: str, text: str) -> str:
    if rel_path.endswith("launch_runtime.py"):
        return text
    if rel_path.endswith("ce_cli.py"):
        return "\n".join(
            part
            for part in (
                _between_markers(text, "# ce launch / ce hud", "def _lane_launch"),
                _between_markers(text, "def _launch(", "def _acquire_launch_claim"),
            )
            if part
        )
    return ""


def evaluate() -> tuple[list[ValidationError], list[ValidationError]]:
    """Return (errors, warnings) for the v3 naming-hygiene invariant."""
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    used_allow: set[tuple[str, str]] = set()
    repo_root = _repo_root()

    def _check_file(rel_path: str, text: str) -> None:
        for token, lines in sorted(_scan(text).items()):
            entry = (rel_path, token)
            if entry in ver.BASELINE_V3_NAMING_ALLOWLIST:
                used_allow.add(entry)
                continue
            line_list = ", ".join(str(n) for n in lines)
            errors.append(
                make_error(
                    CODE_RESIDUE,
                    rel_path,
                    f"token:{token}@L{line_list}",
                    f"v3 surface must not embed the CE bootstrapping-harness residue "
                    f"{token!r} (line(s) {line_list}); v3/v3.1 stay decoupled from "
                    f".hermes/Hermes/Nefarious (v1 keeps .hermes frozen). Decouple it, or "
                    f"(if a justified external citation) add a baselined allowlist entry in "
                    f"_versions.py BASELINE_V3_NAMING_ALLOWLIST.",
                    CONTRACT,
                )
            )

    def _check_launch_file(rel_path: str, text: str) -> None:
        for token, lines in sorted(_scan_hermes_path(_launch_surface_text(rel_path, text)).items()):
            line_list = ", ".join(str(n) for n in lines)
            errors.append(
                make_error(
                    CODE_RESIDUE,
                    rel_path,
                    f"token:{token}@L{line_list}",
                    f"ce launch emits v3 governed-seat state and must not point at "
                    f"{token!r} (line(s) {line_list}); use _versions.V3_LOCAL_STATE_ROOT "
                    "and .ce/state launch paths instead.",
                    CONTRACT,
                )
            )

    # v3 CODE surface (modules classified v3 by the _versions taxonomy).
    for dotted, path in sorted(discover_modules(_package_dir()).items()):
        if ver.classify(_rel(dotted)) != ver.V3:
            continue
        _check_file(_relpath(path, repo_root), path.read_text(encoding="utf-8"))

    # Load-bearing ce launch surface: v1-classified, but emits v3 governed-seat state.
    for rel_path in _LAUNCH_SURFACE_REL_PATHS:
        launch_path = repo_root / rel_path
        if launch_path.is_file():
            _check_launch_file(rel_path, launch_path.read_text(encoding="utf-8"))

    # v3 SCHEMA surface (declared list).
    for schema_rel in sorted(ver.V3_SCHEMAS):
        schema_path = repo_root / schema_rel
        if not schema_path.is_file():
            errors.append(
                make_error(
                    CODE_MISSING_SCHEMA,
                    schema_rel,
                    "",
                    f"declared v3 schema {schema_rel!r} no longer exists; update "
                    "_versions.V3_SCHEMAS (rename/remove).",
                    CONTRACT,
                )
            )
            continue
        _check_file(schema_rel, schema_path.read_text(encoding="utf-8"))

    # Stale allowlist entries (residue no longer present) -> warning to tighten the floor.
    for entry in sorted(ver.BASELINE_V3_NAMING_ALLOWLIST - used_allow):
        warnings.append(
            make_error(
                CODE_STALE,
                entry[0],
                f"token:{entry[1]}",
                "baselined v3 naming-hygiene exception no longer present; remove it from "
                "_versions.BASELINE_V3_NAMING_ALLOWLIST to tighten the ratchet.",
                CONTRACT,
            )
        )
    return errors, warnings


@register(CHECK_NAME, [CODE_RESIDUE, CODE_MISSING_SCHEMA])
def run(paths: Iterable[Path]) -> CheckResult:  # noqa: ARG001 - self/structural check
    errors, warnings = evaluate()
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))
