"""``version_boundary`` — guard the CE v1 ↔ v3 coexistence boundary (G-3.9).

A self/structural check (it inspects this package's own import graph, not
sidecar artifacts; cf. ``completion_report_required_for_envelope``). It reads
the version-line taxonomy from ``creator_engine_validator._versions`` and
asserts, against the *actual* intra-package import graph:

  * HARD — no ``v1`` module imports a ``v3`` module, or vice-versa. The two
    execution runtimes stay mutually isolated. No exceptions.
  * RATCHET — every ``shared``→version edge must be a baselined entry in
    ``BASELINE_SHARED_TO_VERSION_ALLOWLIST``. New shared→version couplings fail.
  * COMPLETENESS — every module named in a runtime surface must still exist
    (catches renames/removals that would silently drop a module to ``shared``).
  * Stale allowlist entries (edges that no longer exist) are reported as
    warnings so the ratchet floor can be tightened.

Contract: ``docs/architecture/VERSION_BOUNDARY.md``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from .. import _versions as ver
from . import register

CHECK_NAME = "version_boundary"
CONTRACT = "docs/architecture/VERSION_BOUNDARY.md"
PKG = "creator_engine_validator"

CODE_CROSS = "VAL-VERBND-CROSS"          # v1<->v3 hard violation
CODE_UNALLOWED = "VAL-VERBND-SHARED-EDGE"  # shared->version not on the allowlist
CODE_MISSING = "VAL-VERBND-MISSING"        # declared runtime module no longer exists
CODE_OVERLAP = "VAL-VERBND-OVERLAP"        # module declared in BOTH runtime surfaces
CODE_STALE = "VAL-VERBND-STALE-ALLOW"      # allowlist entry whose edge is gone (warning)


def _package_dir() -> Path:
    # .../creator_engine_validator/checks/version_boundary.py -> .../creator_engine_validator
    return Path(__file__).resolve().parent.parent


def _rel(dotted_abs: str) -> str:
    """Strip the package prefix, returning the package-relative dotted name."""
    if dotted_abs == PKG:
        return ""
    prefix = PKG + "."
    return dotted_abs[len(prefix):] if dotted_abs.startswith(prefix) else dotted_abs


def discover_modules(pkg_dir: Path) -> dict[str, Path]:
    """Map every shipped module's *absolute* dotted name to its file path."""
    mods: dict[str, Path] = {}
    for p in sorted(pkg_dir.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        parts = list(p.relative_to(pkg_dir.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        mods[".".join(parts)] = p
    return mods


def _resolve_from(dotted_self: str, is_package: bool, level: int, module: str | None) -> str:
    """Resolve a relative ``from`` import to its absolute target prefix.

    ``dotted_self`` is the importing module's dotted name; ``is_package`` is True
    when it is a package ``__init__`` — whose discovered dotted name IS the package,
    so its relative-import anchor is the package itself, not its parent. (A regular
    module ``pkg.sub.mod`` anchors relative imports at ``pkg.sub``; a package
    ``pkg.sub``'s own ``__init__`` anchors at ``pkg.sub``.)
    """
    if level == 0:
        return module or ""
    parts = dotted_self.split(".")
    pkg_parts = parts if is_package else parts[:-1]  # anchor package for relatives
    up = level - 1
    if up:
        pkg_parts = pkg_parts[:-up] if up <= len(pkg_parts) else []
    tail = [module] if module else []
    return ".".join(pkg_parts + tail)


def _best_known(target: str, known: set[str]) -> str | None:
    """Longest known-module prefix of ``target`` (so ``a.b.Cls`` -> module ``a.b``)."""
    parts = target.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in known:
            return cand
    return None


def build_edges(mods: dict[str, Path]) -> set[tuple[str, str]]:
    """Extract intra-package import edges as (src_rel, dst_rel) pairs."""
    known = set(mods)
    edges: set[tuple[str, str]] = set()
    for dotted, path in mods.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names if a.name.startswith(PKG)]
            elif isinstance(node, ast.ImportFrom):
                base = _resolve_from(dotted, path.name == "__init__.py", node.level, node.module)
                if base.startswith(PKG) or node.level > 0:
                    targets = [base] + [
                        (base + "." + a.name) if base else a.name for a in node.names
                    ]
                    targets = [t for t in targets if t.startswith(PKG)]
            for t in targets:
                k = _best_known(t, known)
                if k and k != dotted:
                    edges.add((_rel(dotted), _rel(k)))
    return edges


def evaluate(mods: dict[str, Path]) -> tuple[list[ValidationError], list[ValidationError]]:
    """Return (errors, warnings) for the version-boundary invariant."""
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    rel_known = {_rel(m) for m in mods}

    # INTEGRITY — a module must not be declared in both runtime surfaces
    # (classify() would silently resolve it to v1, masking the boundary).
    for dup in sorted(ver.V1_RUNTIME & ver.V3_RUNTIME):
        errors.append(
            make_error(
                CODE_OVERLAP,
                "creator_engine_validator/_versions.py",
                dup,
                f"module '{dup}' is declared in BOTH V1_RUNTIME and V3_RUNTIME; "
                "a module belongs to exactly one version line",
                CONTRACT,
            )
        )

    # COMPLETENESS — every declared runtime module must still exist.
    for declared in sorted(ver.V1_RUNTIME | ver.V3_RUNTIME):
        if declared not in rel_known:
            errors.append(
                make_error(
                    CODE_MISSING,
                    "creator_engine_validator/_versions.py",
                    declared,
                    f"declared runtime module '{declared}' no longer exists; "
                    "update the taxonomy (rename/remove)",
                    CONTRACT,
                )
            )

    edges = build_edges(mods)
    used_allow: set[tuple[str, str]] = set()
    for src, dst in sorted(edges):
        cs, cd = ver.classify(src), ver.classify(dst)
        if {cs, cd} == {ver.V1, ver.V3}:
            errors.append(
                make_error(
                    CODE_CROSS,
                    f"creator_engine_validator/{src.replace('.', '/')}.py",
                    f"imports:{dst}",
                    f"HARD boundary violation: {cs} module '{src}' imports "
                    f"{cd} module '{dst}'. v1 and v3 runtimes must stay isolated.",
                    CONTRACT,
                )
            )
        elif cs == ver.SHARED and cd in (ver.V1, ver.V3):
            if (src, dst) in ver.BASELINE_SHARED_TO_VERSION_ALLOWLIST:
                used_allow.add((src, dst))
            else:
                errors.append(
                    make_error(
                        CODE_UNALLOWED,
                        f"creator_engine_validator/{src.replace('.', '/')}.py",
                        f"imports:{dst}",
                        f"new shared->{cd} coupling: '{src}' imports '{dst}'. "
                        "Decouple it, or (if justified) add a baselined allowlist "
                        "entry in _versions.py.",
                        CONTRACT,
                    )
                )

    # Stale allowlist entries (edge no longer present) -> warning to tighten the floor.
    for entry in sorted(ver.BASELINE_SHARED_TO_VERSION_ALLOWLIST - used_allow):
        warnings.append(
            make_error(
                CODE_STALE,
                "creator_engine_validator/_versions.py",
                f"{entry[0]}->{entry[1]}",
                "allowlisted shared->version edge no longer exists; "
                "remove it from BASELINE_SHARED_TO_VERSION_ALLOWLIST to tighten the ratchet.",
                CONTRACT,
            )
        )
    return errors, warnings


@register(CHECK_NAME, [CODE_CROSS, CODE_UNALLOWED])
def run(paths: Iterable[Path]) -> CheckResult:  # noqa: ARG001 - self/structural check
    mods = discover_modules(_package_dir())
    errors, warnings = evaluate(mods)
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))
