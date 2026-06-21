"""F2 work-sizing floor classifier and record check.

This check is deliberately local and deterministic. It validates persisted
``work-sizing-floor-record`` YAML records whose ``change_stats`` are caller-
supplied git ``--numstat``-style line/file stats. Generated, lockfile, and
vendored paths are explicit local exclusions. The classifier stays pure; the
``run_with_base`` adapter is the PR-diff gate that derives live git numstat
input from ``<base>..HEAD``.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath, Path
from typing import Any, Final, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "work_sizing_floor"
CONTRACT = "schemas/work-sizing-floor.schema.yaml"
SCHEMA = "schemas/work-sizing-floor.schema.yaml"
KIND_VALUE = "work-sizing-floor-record"

CODE_SCHEMA = "VAL-WORK-SIZING-FLOOR-SCHEMA"
CODE_INVALID = "VAL-WORK-SIZING-FLOOR-INVALID"

WORK_CLASSES: Final[tuple[str, ...]] = ("tiny", "story", "feature", "epic")
_LOCKFILE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "cargo.lock",
        "composer.lock",
        "go.sum",
        "npm-shrinkwrap.json",
        "package-lock.json",
        "pipfile.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }
)
_VENDORED_PARTS: Final[frozenset[str]] = frozenset(
    {"node_modules", "third_party", "vendor", "vendored", "vendors", "wheelhouse", "wheelhouse-dev"}
)
_GENERATED_PARTS: Final[frozenset[str]] = frozenset({"generated", "gen"})


@dataclass(frozen=True)
class ChangeStat:
    path: str
    additions: int
    deletions: int
    binary: bool = False

    @property
    def changed_lines(self) -> int:
        return self.additions + self.deletions


def _normalize_path(path: str) -> PurePosixPath:
    normalized = path.replace("\\", "/").strip("/")
    return PurePosixPath(normalized or ".")


def excluded_path_category(path: str) -> str | None:
    """Return the local exclusion category for ``path``, if any."""
    pure = _normalize_path(path)
    name = pure.name.lower()
    parts = tuple(part.lower() for part in pure.parts)
    if name in _LOCKFILE_NAMES:
        return "lockfile"
    if any(part in _VENDORED_PARTS for part in parts):
        return "vendored"
    if any(part in _GENERATED_PARTS for part in parts):
        return "generated"
    if ".generated." in name or name.endswith((".generated", ".min.js", ".min.css")):
        return "generated"
    return None


def parse_numstat(text: str) -> list[ChangeStat]:
    """Parse ``git diff --numstat`` text into deterministic change stats."""
    stats: list[ChangeStat] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3:
            raise ValueError("invalid numstat line")
        additions_raw, deletions_raw, path = parts
        binary = additions_raw == "-" and deletions_raw == "-"
        if binary:
            additions = 0
            deletions = 0
        else:
            try:
                additions = int(additions_raw)
                deletions = int(deletions_raw)
            except ValueError as exc:
                raise ValueError("invalid numstat line") from exc
        if additions < 0 or deletions < 0 or not path:
            raise ValueError("invalid numstat line")
        stats.append(ChangeStat(path=path, additions=additions, deletions=deletions, binary=binary))
    return stats


def _run_git(args: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command, returning (returncode, stdout, stderr). Never raises."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout, result.stderr


def _repo_root_for(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / "validators").is_dir():
            return candidate
    return Path.cwd()


def _coerce_change_stat(raw: ChangeStat | dict[str, Any]) -> ChangeStat:
    if isinstance(raw, ChangeStat):
        stat = raw
    elif isinstance(raw, dict):
        try:
            stat = ChangeStat(
                path=str(raw["path"]),
                additions=int(raw["additions"]),
                deletions=int(raw["deletions"]),
                binary=bool(raw.get("binary", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid change_stats entry") from exc
    else:
        raise ValueError("invalid change_stats entry")
    if not stat.path or stat.additions < 0 or stat.deletions < 0:
        raise ValueError("invalid change_stats entry")
    return stat


def _size_band(included_lines: int) -> tuple[str, str]:
    if included_lines <= 200:
        return "target_advisory", "tiny"
    if included_lines < 800:
        return "warn", "story"
    if included_lines <= 1000:
        return "explain_or_split", "feature"
    return "split_required", "epic"


def classify_change_size(change_stats: Iterable[ChangeStat | dict[str, Any]]) -> dict[str, Any]:
    """Classify included change size after local path exclusions."""
    included_files = 0
    included_lines = 0
    excluded_files = 0
    excluded_lines = 0
    excluded_categories: set[str] = set()

    for raw in change_stats:
        stat = _coerce_change_stat(raw)
        category = excluded_path_category(stat.path)
        if category is None:
            included_files += 1
            included_lines += stat.changed_lines
        else:
            excluded_files += 1
            excluded_lines += stat.changed_lines
            excluded_categories.add(category)

    size_band, minimum = _size_band(included_lines)
    return {
        "included_files": included_files,
        "included_lines": included_lines,
        "excluded_files": excluded_files,
        "excluded_lines": excluded_lines,
        "excluded_path_categories": sorted(excluded_categories),
        "size_band": size_band,
        "minimum_work_class": minimum,
    }


def sizing_floor_projection(
    declared_work_class: str,
    change_stats: Iterable[ChangeStat | dict[str, Any]],
) -> dict[str, Any]:
    """Return derived floor fields for the declared work class."""
    if declared_work_class not in WORK_CLASSES:
        raise ValueError("unknown work_class")
    projection = classify_change_size(change_stats)
    projection["floor_met"] = (
        WORK_CLASSES.index(declared_work_class)
        >= WORK_CLASSES.index(str(projection["minimum_work_class"]))
    )
    return projection


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_floor(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_work_sizing_floor_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate work-sizing floor record files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p) and not _is_under_excluded(p) and not _is_tmp_artifact(p)
            ]
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            try:
                data = load_yaml(candidate)
            except LoaderError:
                continue
            if not _record_is_floor(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_work_sizing_floor(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one floor record against schema and deterministic projection."""
    errors = validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)
    if errors:
        return errors
    try:
        expected = sizing_floor_projection(
            str(record["declared_work_class"]),
            record.get("change_stats", ()),
        )
    except (KeyError, ValueError):
        return errors
    if record.get("sizing_floor") != expected:
        errors.append(make_error(
            CODE_INVALID,
            path,
            "sizing_floor",
            "sizing_floor must equal sizing_floor_projection(declared_work_class, change_stats)",
            CONTRACT,
        ))
    if not expected["floor_met"]:
        errors.append(make_error(
            CODE_INVALID,
            path,
            "declared_work_class",
            "declared_work_class must satisfy sizing_floor.minimum_work_class",
            CONTRACT,
        ))
    return errors


@register(CHECK_NAME, [CODE_SCHEMA, CODE_INVALID])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_work_sizing_floor_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            continue
        errors.extend(validate_work_sizing_floor(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))


def run_with_base(
    paths: Iterable[Path],
    base: str,
    *,
    declared_work_class: str,
) -> CheckResult:
    """PR-diff gate for ``git diff --numstat --no-renames <base>..HEAD``."""
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = _repo_root_for(raw_paths[0])
    errors: list[ValidationError] = []

    returncode, stdout, _stderr = _run_git(
        ["diff", "--numstat", "--no-renames", f"{base}..HEAD"],
        repo_root,
    )
    if returncode != 0:
        errors.append(make_error(
            CODE_INVALID,
            "PR_DIFF",
            "",
            "git diff numstat failed",
            CONTRACT,
        ))
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    try:
        projection = sizing_floor_projection(declared_work_class, parse_numstat(stdout))
    except ValueError:
        errors.append(make_error(
            CODE_INVALID,
            "PR_DIFF",
            "declared_work_class",
            "declared_work_class must satisfy PR diff work-sizing floor",
            CONTRACT,
        ))
        return CheckResult(name=CHECK_NAME, errors=tuple(errors))

    if not projection["floor_met"]:
        errors.append(make_error(
            CODE_INVALID,
            "PR_DIFF",
            "declared_work_class",
            "declared_work_class must satisfy PR diff work-sizing floor",
            CONTRACT,
        ))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
