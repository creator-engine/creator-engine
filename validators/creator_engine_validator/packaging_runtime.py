"""RV1-060 — Option B v1.0 packaging-contract introspection.

This module is the single source of truth for the Source-locked Option B / 1B
packaging contract and the read-only helpers that assert it. ``ce doctor``
reuses :func:`verify_packaging_contract` for the dependency/wheelhouse-drift
guard clause (RED-G-6), and the packaging tests assert the required author-side
contract over the tracked artifacts. The first-party app-wheel/source parity
attestation is exposed separately by :func:`verify_wheel_matches_source` so the
post-merge wheel-bake lane can run it without serializing authored PRs.

The contract (``docs/governance/V1_PRODUCT_CONTRACT.md`` §6):

* Python floor ``>=3.14``; tested/target band is **3.14.x** (3.13 excluded,
  3.15 invalid/unreleased at decision time).
* runtime pins ``PyYAML==6.0.3`` and ``jsonschema==4.26.0``.
    * cp314-only dual-arch Linux offline wheelhouse (no cp311/cp312/cp313 artifacts).
* ``uv.lock`` is primary; ``requirements.txt`` is a lockstep export.
* build backend ``setuptools.build_meta``; distribution stays
  ``creator-engine-validator`` (DP-1 = A); both console scripts retained.

It uses only stdlib (``tomllib`` is read-only TOML; no TOML *writer* dependency
is introduced, per the format split B6/B7).
"""
from __future__ import annotations

import ast
import re
import subprocess
import tomllib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

# --- Locked contract constants ---------------------------------------------

REQUIRES_PYTHON = ">=3.14"
PYTHON_TARGET = (3, 14)
DISTRIBUTION_NAME = "creator-engine-validator"
BUILD_BACKEND = "setuptools.build_meta"
CONSOLE_SCRIPTS = {
    "creator-engine-validator": "creator_engine_validator.cli:main",
    "ce": "creator_engine_validator.ce_cli:main",
}
# Normalized (PEP 503) name -> exact pinned version.
RUNTIME_PINS = {"pyyaml": "6.0.3", "jsonschema": "4.26.0"}
# Every runtime distribution (direct + transitive) that must be offline-installable.
REQUIRED_WHEELHOUSE_DISTRIBUTIONS = frozenset(
    {"pyyaml", "jsonschema", "attrs", "jsonschema-specifications", "referencing", "rpds-py"}
)
REQUIRED_ABI = "cp314"
FORBIDDEN_ABI_TAGS = ("cp311", "cp312", "cp313")


@dataclass(frozen=True)
class PackagingContractResult:
    ok: bool
    violations: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# --- pure helpers -----------------------------------------------------------


def normalize_name(name: str) -> str:
    """PEP 503 normalization (lower-case, runs of ``-_.`` collapse to ``-``)."""
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


def interpreter_in_contract(version_info: Sequence[int]) -> bool:
    """True iff ``version_info`` is in the tested/target band 3.14.x.

    The pyproject floor is ``>=3.14`` (compatibility promise), but the runtime
    interpreter-contract assertion enforces the *target* band, so 3.13 (below)
    and 3.15 (above target / unreleased at decision time) are both refused
    (RED-G-1).
    """
    return tuple(version_info[:2]) == PYTHON_TARGET


# --- wheel filename parsing -------------------------------------------------


def wheelhouse_wheels(wheelhouse_dir: Path | str) -> list[str]:
    """Sorted ``*.whl`` filenames present in the wheelhouse (non-recursive)."""
    d = Path(wheelhouse_dir)
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.glob("*.whl"))


def _wheel_distribution(filename: str) -> str:
    """Distribution name from a wheel filename (the part before the version)."""
    return normalize_name(filename.split("-", 1)[0])


def wheelhouse_distribution_names(wheelhouse_dir: Path | str) -> list[str]:
    return sorted({_wheel_distribution(w) for w in wheelhouse_wheels(wheelhouse_dir)})


def _wheel_filename_parts(filename: str) -> tuple[str, str] | None:
    """Return ``(normalized distribution, version)`` from a wheel filename."""
    if not filename.endswith(".whl"):
        return None
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return None
    return normalize_name(parts[0]), parts[1]


# --- pyproject / lock / requirements parsing --------------------------------


def read_pyproject(path: Path | str) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def _pyproject_version(path: Path | str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    version = read_pyproject(p).get("project", {}).get("version")
    return version if isinstance(version, str) else None


def _source_declared_version(path: Path | str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    return None


def _split_pin(spec: str) -> tuple[str, str] | None:
    spec = spec.strip()
    if "==" not in spec:
        return None
    name, _, version = spec.partition("==")
    return normalize_name(name), version.strip()


def parse_requirements(path: Path | str) -> dict[str, str]:
    """Map normalized name -> pinned version from a ``==``-pinned requirements file."""
    out: dict[str, str] = {}
    p = Path(path)
    if not p.is_file():
        return out
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].split(";", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        # drop environment markers / extras hash suffixes
        line = line.split(" ", 1)[0]
        pin = _split_pin(line)
        if pin:
            out[pin[0]] = pin[1]
    return out


def parse_uv_lock(path: Path | str) -> dict[str, str]:
    """Map normalized name -> version from a ``uv.lock`` (read-only tomllib)."""
    p = Path(path)
    if not p.is_file():
        return {}
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for entry in data.get("package", []):
        name = entry.get("name")
        version = entry.get("version")
        if name and version:
            out[normalize_name(name)] = version
    return out


# --- violation collectors ---------------------------------------------------


def pyproject_violations(path: Path | str) -> list[str]:
    v: list[str] = []
    p = Path(path)
    if not p.is_file():
        return [f"missing pyproject.toml at {p}"]
    data = read_pyproject(p)
    project = data.get("project", {})
    if project.get("requires-python") != REQUIRES_PYTHON:
        v.append(
            f"requires-python must be {REQUIRES_PYTHON!r}, got {project.get('requires-python')!r}"
        )
    if project.get("name") != DISTRIBUTION_NAME:
        v.append(f"distribution must stay {DISTRIBUTION_NAME!r} (DP-1=A), got {project.get('name')!r}")
    if data.get("build-system", {}).get("build-backend") != BUILD_BACKEND:
        v.append(f"build backend must be {BUILD_BACKEND!r}")
    deps = {}
    for spec in project.get("dependencies", []):
        pin = _split_pin(spec)
        if pin:
            deps[pin[0]] = pin[1]
    for name, version in RUNTIME_PINS.items():
        if deps.get(name) != version:
            v.append(f"dependency {name} must be pinned =={version}, got {deps.get(name)!r}")
    scripts = project.get("scripts", {})
    for name, target in CONSOLE_SCRIPTS.items():
        if scripts.get(name) != target:
            v.append(f"console script {name!r} must map to {target!r}, got {scripts.get(name)!r}")
    return v


def wheelhouse_violations(wheelhouse_dir: Path | str) -> list[str]:
    v: list[str] = []
    d = Path(wheelhouse_dir)
    if not d.is_dir():
        return [f"missing wheelhouse directory at {d}"]
    wheels = wheelhouse_wheels(d)
    offenders = [w for w in wheels if any(tag in w for tag in FORBIDDEN_ABI_TAGS)]
    if offenders:
        v.append(f"non-cp314 ABI wheels present (must be removed): {offenders}")
    if not any("cp314" in w for w in wheels):
        v.append("wheelhouse contains no cp314 ABI wheel; cp314 build not present")
    present = {normalize_name(n) for n in wheelhouse_distribution_names(d)}
    missing = sorted(REQUIRED_WHEELHOUSE_DISTRIBUTIONS - present)
    if missing:
        v.append(f"wheelhouse missing offline wheels for: {missing}")
    return v


def lockstep_violations(requirements_path: Path | str, uv_lock_path: Path | str) -> list[str]:
    v: list[str] = []
    reqs = parse_requirements(requirements_path)
    lock = parse_uv_lock(uv_lock_path)
    if not lock:
        return [f"uv.lock missing or empty at {uv_lock_path}"]
    if not reqs:
        return [f"requirements.txt missing or empty at {requirements_path}"]
    # Every locked runtime distribution must appear in the export at the same version.
    for name, version in lock.items():
        if name == DISTRIBUTION_NAME:
            continue  # the project itself is not exported into requirements
        if name not in reqs:
            v.append(f"requirements.txt missing {name} (locked {version})")
        elif reqs[name] != version:
            v.append(f"requirements.txt {name}=={reqs[name]} drifted from uv.lock {version}")
    return v


def verify_wheel_matches_source(repo_root: Path | str) -> list[str]:
    """Report app-wheel/source drift when both the repo source and wheel exist.

    Installed end-user contexts may have only the wheel (or only a checkout
    without the shipped wheelhouse), so this guard is intentionally a no-op
    unless both sides of the fidelity comparison are present.
    """
    root = Path(repo_root)
    validators = root / "validators"
    source_root = validators / "creator_engine_validator"
    wheelhouse = validators / "wheelhouse"
    if not source_root.is_dir() or not wheelhouse.is_dir():
        return []
    app_wheels = sorted(wheelhouse.glob("creator_engine_validator-*.whl"))
    if not app_wheels:
        return []

    v: list[str] = []
    pyproject_version = _pyproject_version(validators / "pyproject.toml")
    source_version = _source_declared_version(source_root / "version.py")
    if pyproject_version is None:
        v.append(f"missing project version in {validators / 'pyproject.toml'}")
    if source_version is None:
        v.append(f"missing __version__ in {source_root / 'version.py'}")
    if pyproject_version and source_version and pyproject_version != source_version:
        v.append(
            f"pyproject version {pyproject_version!r} differs from "
            f"creator_engine_validator.version.__version__ {source_version!r}"
        )

    source_files = {
        path.relative_to(source_root).as_posix(): path
        for path in source_root.rglob("*.py")
        if path.is_file()
    }

    for wheel in app_wheels:
        parsed = _wheel_filename_parts(wheel.name)
        if parsed is None:
            v.append(f"invalid app wheel filename: {wheel.name}")
            continue
        wheel_dist, wheel_version = parsed
        if wheel_dist != DISTRIBUTION_NAME:
            v.append(
                f"app wheel {wheel.name} distribution must be {DISTRIBUTION_NAME!r}, "
                f"got {wheel_dist!r}"
            )
        if pyproject_version and wheel_version != pyproject_version:
            v.append(
                f"app wheel {wheel.name} version {wheel_version!r} differs from "
                f"pyproject version {pyproject_version!r}"
            )
        if source_version and wheel_version != source_version:
            v.append(
                f"app wheel {wheel.name} version {wheel_version!r} differs from "
                f"creator_engine_validator.version.__version__ {source_version!r}"
            )

        try:
            with zipfile.ZipFile(wheel) as zf:
                wheel_files = {
                    name.removeprefix("creator_engine_validator/")
                    for name in zf.namelist()
                    if name.startswith("creator_engine_validator/") and name.endswith(".py")
                }
                for rel in sorted(wheel_files - source_files.keys()):
                    v.append(f"app wheel {wheel.name} has no source file for {rel}")
                for rel in sorted(source_files.keys() - wheel_files):
                    v.append(f"app wheel {wheel.name} missing source file {rel}")
                for rel in sorted(source_files.keys() & wheel_files):
                    wheel_bytes = zf.read(f"creator_engine_validator/{rel}")
                    source_bytes = source_files[rel].read_bytes()
                    if wheel_bytes != source_bytes:
                        v.append(f"app wheel {wheel.name} differs from source file {rel}")
        except zipfile.BadZipFile:
            v.append(f"invalid app wheel zip archive: {wheel}")
    return v


def _module_str_constant(path: Path | str, name: str) -> str | None:
    """Read a top-level ``<name> = "<literal>"`` string constant via AST (read-only)."""
    p = Path(path)
    if not p.is_file():
        return None
    tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    return None


def _is_full_sha(value: str | None) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdefABCDEF" for c in value)


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess | None:
    """Run ``git -C <repo_root> <args>`` (read-only); ``None`` if git is absent.

    The single git seam for the freshness probe — monkeypatchable in tests so a
    shallow-clone shape can be exercised without a real shallow checkout.
    """
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False, capture_output=True, text=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None


def _is_shallow_repo(repo_root: Path) -> bool:
    proc = _git(repo_root, "rev-parse", "--is-shallow-repository")
    return proc is not None and proc.returncode == 0 and proc.stdout.strip() == "true"


def _baked_sha_git_problem(repo_root: Path, baked: str) -> str | None:
    """Freshness check for the baked SHA, lenient when git can't prove drift.

    When ``repo_root`` is a live git checkout, the baked ``BUILD_GIT_SHA`` must
    be a real commit that is an ancestor of (or equal to) HEAD — this catches a
    placeholder/garbage/foreign SHA without rotting as history grows past the
    gate (exact merge-parent equality is the gate's one-time step-6 check, not a
    perpetual CI assertion). Two contexts are skipped because git cannot prove
    drift there: (1) git absent / not a checkout (a no-git/wheel-install context);
    (2) the baked object is ABSENT on a **shallow** clone — ``actions/checkout``
    is depth-1, so the merge-parent base commit is legitimately not an object in
    the repo during the pytest step. Only a FULL clone can distinguish a genuine
    missing/foreign sha from a shallow-truncated history, so the absent-object
    violation fires only there.
    """
    head = _git(repo_root, "rev-parse", "--verify", "HEAD")
    if head is None or head.returncode != 0:
        return None  # not a checkout / git unavailable -> skip, do not fabricate drift
    exists = _git(repo_root, "cat-file", "-e", f"{baked}^{{commit}}")
    if exists is None:
        return None
    if exists.returncode != 0:
        if _is_shallow_repo(repo_root):
            return None  # shallow clone: the base commit is truncated away, not missing
        return f"generated _version.py BUILD_GIT_SHA {baked} is not a commit in this repository"
    ancestor = _git(repo_root, "merge-base", "--is-ancestor", baked, "HEAD")
    if ancestor is None:
        return None
    if ancestor.returncode != 0:
        return f"generated _version.py BUILD_GIT_SHA {baked} is not an ancestor of HEAD (stale baked sha)"
    return None


def verify_generated_version(repo_root: Path | str) -> list[str]:
    """Assert the generated ``_version.py`` parity (ce-ops#25 packaging extension).

    No-op unless the source tree is present (mirrors :func:`verify_wheel_matches_source`
    — an installed wheel-only context has no source checkout to compare). When
    present, asserts: ``_version.py`` exists; ``SEMVER`` equals the pyproject
    version; ``BUILD_GIT_SHA`` is a 40-hex commit sha; and (in a git checkout)
    the baked SHA is a real ancestor of HEAD.
    """
    root = Path(repo_root)
    validators = root / "validators"
    source_root = validators / "creator_engine_validator"
    if not source_root.is_dir():
        return []
    v: list[str] = []
    version_file = source_root / "_version.py"
    if not version_file.is_file():
        return [f"missing generated build-identity file {version_file}"]
    semver = _module_str_constant(version_file, "SEMVER")
    baked = _module_str_constant(version_file, "BUILD_GIT_SHA")
    pyproject_version = _pyproject_version(validators / "pyproject.toml")
    if semver is None:
        v.append(f"generated _version.py is missing a SEMVER string constant")
    elif pyproject_version and semver != pyproject_version:
        v.append(
            f"generated _version.py SEMVER {semver!r} differs from pyproject "
            f"version {pyproject_version!r}"
        )
    if not _is_full_sha(baked):
        v.append(f"generated _version.py BUILD_GIT_SHA {baked!r} is not a 40-hex commit sha")
    else:
        problem = _baked_sha_git_problem(root, baked)
        if problem:
            v.append(problem)
    return v


def verify_packaging_contract(repo_root: Path | str) -> PackagingContractResult:
    """Aggregate the author-side Option B packaging contract (RED-G-6).

    ADR-0010 moves first-party app-wheel/source parity to the post-merge bake
    gate. This aggregate therefore keeps pyproject, runtime wheelhouse,
    lockstep, and generated-version checks required, but intentionally excludes
    :func:`verify_wheel_matches_source`.
    """
    root = Path(repo_root)
    validators = root / "validators"
    violations: list[str] = []
    violations += pyproject_violations(validators / "pyproject.toml")
    violations += wheelhouse_violations(validators / "wheelhouse")
    violations += lockstep_violations(validators / "requirements.txt", validators / "uv.lock")
    violations += verify_generated_version(root)
    details = {
        "requires_python": REQUIRES_PYTHON,
        "runtime_pins": dict(RUNTIME_PINS),
        "wheelhouse_wheels": wheelhouse_wheels(validators / "wheelhouse"),
        "uv_lock": parse_uv_lock(validators / "uv.lock"),
    }
    return PackagingContractResult(ok=not violations, violations=violations, details=details)


def interpreter_violation(version_info: Sequence[int] | None = None) -> str | None:
    """Return a refusal message if the active interpreter is out-of-contract."""
    import sys

    vi = version_info if version_info is not None else sys.version_info[:3]
    if not interpreter_in_contract(vi):
        got = ".".join(str(x) for x in vi)
        return (
            f"active interpreter {got} is out-of-contract; "
            f"contract is floor {REQUIRES_PYTHON} / target band 3.14.x"
        )
    return None
