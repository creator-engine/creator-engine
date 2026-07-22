#!/usr/bin/env python3
"""Generate the distributed-dependency inventory embedded in ``NOTICE``.

The generated inventory is intentionally narrower than legal attribution:

* runtime names and versions are the ordinary (non-extra) dependency closure
  rooted at ``creator-engine-validator`` in ``validators/uv.lock``;
* development names and versions are the pinned ``requirements-dev.txt`` set,
  verified against actual ``wheelhouse-dev`` filenames.

The lock does not carry authoritative licensing data, so the per-package
license-attribution section outside the generated markers remains curated by
hand from the distributed wheel metadata. ``--check`` is read-only and fails
on a stale NOTICE or any displayed version that lacks a matching wheel.
``--write`` replaces only the marker-delimited inventory.
"""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path
from typing import Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_RELATIVE = Path("NOTICE")
LOCK_RELATIVE = Path("validators/uv.lock")
DEV_REQUIREMENTS_RELATIVE = Path("validators/requirements-dev.txt")
RUNTIME_WHEELHOUSE_RELATIVE = Path("validators/wheelhouse")
DEV_WHEELHOUSE_RELATIVE = Path("validators/wheelhouse-dev")
PROJECT_NAME = "creator-engine-validator"
BEGIN_MARKER = "<!-- ce-autogen: notice-inventory begin -->"
END_MARKER = "<!-- ce-autogen: notice-inventory end -->"


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


def _wheel_versions(directory: Path) -> dict[str, set[str]]:
    """Map normalized distribution names to versions from shipped wheel names."""
    if not directory.is_dir():
        raise ValueError(f"missing wheelhouse: {directory}")
    versions: dict[str, set[str]] = {}
    for wheel in directory.glob("*.whl"):
        parts = wheel.name[:-4].split("-")
        if len(parts) < 5:
            raise ValueError(f"invalid wheel filename: {wheel.name}")
        versions.setdefault(_normalize_name(parts[0]), set()).add(parts[1])
    if not versions:
        raise ValueError(f"wheelhouse contains no wheels: {directory}")
    return versions


def _runtime_packages(repo_root: Path) -> dict[str, str]:
    """Return only the project's ordinary lock dependency closure, not extras."""
    raw = tomllib.loads((repo_root / LOCK_RELATIVE).read_text(encoding="utf-8"))
    entries = {
        _normalize_name(str(package["name"])): package
        for package in raw.get("package", [])
        if isinstance(package.get("name"), str) and isinstance(package.get("version"), str)
    }
    project = entries.get(PROJECT_NAME)
    if project is None:
        raise ValueError(f"uv.lock has no {PROJECT_NAME} package")

    packages: dict[str, str] = {}
    pending = [
        _normalize_name(str(dependency["name"]))
        for dependency in project.get("dependencies", [])
        if isinstance(dependency.get("name"), str)
    ]
    while pending:
        name = pending.pop()
        if name in packages:
            continue
        package = entries.get(name)
        if package is None:
            raise ValueError(f"uv.lock closure references missing package: {name}")
        packages[name] = str(package["version"])
        pending.extend(
            _normalize_name(str(dependency["name"]))
            for dependency in package.get("dependencies", [])
            if isinstance(dependency.get("name"), str)
        )
    if not packages:
        raise ValueError("uv.lock runtime closure is empty")
    return packages


def _dev_packages(repo_root: Path) -> dict[str, str]:
    """Return exact pins from the dev requirements source."""
    packages: dict[str, str] = {}
    for raw in (repo_root / DEV_REQUIREMENTS_RELATIVE).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or "==" not in line:
            continue
        name, version = line.split("==", 1)
        name, version = _normalize_name(name), version.strip()
        if not name or not version:
            raise ValueError(f"invalid development requirement: {raw!r}")
        packages[name] = version
    if not packages:
        raise ValueError("requirements-dev.txt has no pinned packages")
    return packages


def _require_vendored_versions(
    packages: dict[str, str], wheelhouse: Path, *, label: str
) -> None:
    """Fail closed unless every displayed name/version is actually distributed."""
    wheel_versions = _wheel_versions(wheelhouse)
    missing = [
        f"{name}=={version}"
        for name, version in sorted(packages.items())
        if version not in wheel_versions.get(name, set())
    ]
    if missing:
        raise ValueError(f"{label} inventory has no matching vendored wheel: {', '.join(missing)}")


def _render_table(title: str, packages: dict[str, str]) -> list[str]:
    lines = [title, "", "| Package | Version |", "| --- | --- |"]
    lines.extend(f"| `{name}` | `{version}` |" for name, version in sorted(packages.items()))
    return lines


def render(repo_root: Path = _REPO_ROOT) -> str:
    """Render the marker-delimited runtime and development inventories."""
    runtime = _runtime_packages(repo_root)
    development = _dev_packages(repo_root)
    _require_vendored_versions(
        runtime, repo_root / RUNTIME_WHEELHOUSE_RELATIVE, label="runtime"
    )
    _require_vendored_versions(
        development, repo_root / DEV_WHEELHOUSE_RELATIVE, label="development"
    )
    lines = [BEGIN_MARKER]
    lines.extend(_render_table("Runtime wheelhouse inventory (from `validators/uv.lock` runtime closure):", runtime))
    lines.append("")
    lines.extend(
        _render_table(
            "Development wheelhouse inventory (from `validators/requirements-dev.txt`, verified against `validators/wheelhouse-dev/`):",
            development,
        )
    )
    lines.extend(["", END_MARKER, ""])
    return "\n".join(lines)


def _replace_inventory(notice: str, rendered: str) -> str:
    """Replace exactly one well-formed generated region, refusing ambiguity."""
    if notice.count(BEGIN_MARKER) != 1 or notice.count(END_MARKER) != 1:
        raise ValueError("NOTICE must contain exactly one notice-inventory marker pair")
    start = notice.index(BEGIN_MARKER)
    end = notice.index(END_MARKER, start) + len(END_MARKER)
    return notice[:start] + rendered.rstrip("\n") + notice[end:]


def check(repo_root: Path = _REPO_ROOT) -> tuple[bool, str]:
    """Return whether NOTICE is fresh and every displayed pin is distributed."""
    notice_path = repo_root / DOC_RELATIVE
    try:
        notice = notice_path.read_text(encoding="utf-8")
        expected = _replace_inventory(notice, render(repo_root))
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        return False, f"NOTICE inventory is unreadable: {exc}"
    if notice != expected:
        return False, (
            "NOTICE dependency inventory is stale; run "
            "`python scripts/gen_notice_inventory.py --write` and commit NOTICE"
        )
    return True, "NOTICE dependency inventory and vendored-wheel versions are current"


def write(repo_root: Path = _REPO_ROOT) -> None:
    """Refresh only NOTICE's generated region."""
    notice_path = repo_root / DOC_RELATIVE
    notice = notice_path.read_text(encoding="utf-8")
    notice_path.write_text(_replace_inventory(notice, render(repo_root)), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify NOTICE without writing")
    mode.add_argument("--write", action="store_true", help="refresh NOTICE's generated inventory")
    args = parser.parse_args(argv)
    if args.write:
        try:
            write()
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            parser.error(str(exc))
        return 0
    current, message = check()
    if not current:
        print(message)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
