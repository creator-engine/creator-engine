#!/usr/bin/env python3
"""Generate the lock-derived dependency inventory embedded in ``NOTICE``.

``validators/uv.lock`` is the version source of truth for Creator Engine's
registry-resolved application and optional-feature dependency closure.  License
terms are intentionally *not* inferred here: uv's lock format carries package
identity and artifact hashes, not authoritative license attribution.  The
surrounding NOTICE text therefore retains its curated statement that each
vendored wheel's own metadata and license text govern.

The generator owns only the delimited inventory, not the whole legal notice:

* ``--check`` renders in memory and fails on drift without writing;
* ``--write`` replaces only the delimited block in ``NOTICE``.

Both modes are deterministic (sorted normalized package names; no timestamps),
which makes the committed inventory a checked projection of the lock.
"""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path
from typing import Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_RELATIVE = Path("NOTICE")
LOCK_RELATIVE = Path("validators/uv.lock")
BEGIN_MARKER = "<!-- ce-autogen: notice-inventory begin -->"
END_MARKER = "<!-- ce-autogen: notice-inventory end -->"


def _packages(repo_root: Path) -> list[tuple[str, str]]:
    """Return registry packages from the lock, sorted by normalized name."""
    raw = tomllib.loads((repo_root / LOCK_RELATIVE).read_text(encoding="utf-8"))
    packages: list[tuple[str, str]] = []
    for package in raw.get("package", []):
        if "registry" not in package.get("source", {}):
            continue
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise ValueError("registry package is missing a string name or version")
        packages.append((name, version))
    if not packages:
        raise ValueError("uv.lock contains no registry packages")
    return sorted(packages, key=lambda item: item[0].replace("-", "_").lower())


def render(repo_root: Path = _REPO_ROOT) -> str:
    """Render the exact marker-delimited NOTICE inventory from ``uv.lock``."""
    lines = [
        BEGIN_MARKER,
        "Third-party dependency inventory (generated from `validators/uv.lock`):",
        "",
        "| Package | Version |",
        "| --- | --- |",
    ]
    lines.extend(f"| `{name}` | `{version}` |" for name, version in _packages(repo_root))
    lines.extend(["", END_MARKER, ""])
    return "\n".join(lines)


def _replace_inventory(notice: str, rendered: str) -> str:
    """Replace exactly one well-formed generated region, refusing ambiguity."""
    if notice.count(BEGIN_MARKER) != 1 or notice.count(END_MARKER) != 1:
        raise ValueError("NOTICE must contain exactly one notice-inventory marker pair")
    start = notice.index(BEGIN_MARKER)
    end = notice.index(END_MARKER, start) + len(END_MARKER)
    if end <= start:
        raise ValueError("NOTICE notice-inventory markers are out of order")
    return notice[:start] + rendered.rstrip("\n") + notice[end:]


def check(repo_root: Path = _REPO_ROOT) -> tuple[bool, str]:
    """Return whether NOTICE's generated region is fresh, without writing."""
    notice_path = repo_root / DOC_RELATIVE
    try:
        notice = notice_path.read_text(encoding="utf-8")
        expected = _replace_inventory(notice, render(repo_root))
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        return False, f"NOTICE inventory is unreadable: {exc}"
    if notice != expected:
        return False, (
            "NOTICE dependency inventory is stale relative to validators/uv.lock; "
            "run `python scripts/gen_notice_inventory.py --write` and commit NOTICE"
        )
    return True, "NOTICE dependency inventory is current"


def write(repo_root: Path = _REPO_ROOT) -> None:
    """Refresh only NOTICE's generated region from the lock."""
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
    ok, message = check()
    if not ok:
        print(message)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
