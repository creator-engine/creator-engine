"""RV1-060 — Option B v1.0 packaging-contract introspection.

This module is the single source of truth for the Source-locked Option B / 1B
packaging contract and the read-only helpers that assert it. ``ce doctor``
reuses :func:`verify_packaging_contract` for the dependency/wheelhouse-drift
guard clause (RED-G-6), and the packaging tests assert the contract over the
tracked artifacts.

The contract (``docs/governance/V1_PRODUCT_CONTRACT.md`` §6):

* Python floor ``>=3.14``; tested/target band is **3.14.x** (3.13 excluded,
  3.15 invalid/unreleased at decision time).
* runtime pins ``PyYAML==6.0.3`` and ``jsonschema==4.26.0``.
* cp314-only x86-64 offline wheelhouse (no cp311/cp312/cp313 artifacts).
* ``uv.lock`` is primary; ``requirements.txt`` is a lockstep export.
* build backend ``setuptools.build_meta``; distribution stays
  ``creator-engine-validator`` (DP-1 = A); both console scripts retained.

It uses only stdlib (``tomllib`` is read-only TOML; no TOML *writer* dependency
is introduced, per the format split B6/B7).
"""
from __future__ import annotations

import re
import tomllib
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


# --- pyproject / lock / requirements parsing --------------------------------


def read_pyproject(path: Path | str) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


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


def verify_packaging_contract(repo_root: Path | str) -> PackagingContractResult:
    """Aggregate the Option B packaging contract for the guard (RED-G-6)."""
    root = Path(repo_root)
    validators = root / "validators"
    violations: list[str] = []
    violations += pyproject_violations(validators / "pyproject.toml")
    violations += wheelhouse_violations(validators / "wheelhouse")
    violations += lockstep_violations(validators / "requirements.txt", validators / "uv.lock")
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
