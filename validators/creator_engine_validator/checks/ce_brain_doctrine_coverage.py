"""Knowledge-SSOT doctrine coverage ratchet.

This check keeps doctrine prose under governed trees tied either to an active
static brain assertion or to an explicit seeded exception. New unaccounted
doctrine files fail closed, while stale exceptions force the debt list to
shrink as assertions are added or files are removed.

The ratchet verifies linkage only: an active static assertion whose
``evidence_ref`` resolves to the doctrine file. It does not prove topical
relevance; semantic validity remains layered on ``ce_brain_assertions`` and
``ce_brain_drift``.

The registered check intentionally anchors to one repo root from the first
input path. Live validator invocations operate on a single checkout root; if
this check needs batch multi-root semantics later, mirror
``surfaces_manifest._repo_roots`` instead of widening the doctrine tree scan.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .. import brain_runtime
from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "ce_brain_doctrine_coverage"
MANIFEST_RELATIVE_PATH = Path(".ce") / "brain" / "doctrine-coverage.yaml"
CONTRACT = str(MANIFEST_RELATIVE_PATH)

CODE_MANIFEST_INVALID = "brain_doctrine_manifest_invalid"
CODE_UNCOVERED = "brain_doctrine_uncovered"
CODE_STALE_EXCEPTION = "brain_doctrine_stale_exception"


@dataclass(frozen=True)
class DoctrineCoverageManifest:
    path: Path
    governed_trees: tuple[str, ...]
    exceptions: tuple[str, ...]


def _pointer(parts: tuple[Any, ...]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _repo_root_for(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (
            (candidate / MANIFEST_RELATIVE_PATH).is_file()
            or (candidate / brain_runtime.AUTHORITATIVE_LEDGER_RELATIVE_PATH).is_file()
            or (candidate / "docs" / "contracts").is_dir()
            or (candidate / ".git").exists()
            or (candidate / "validators").is_dir()
        ):
            return candidate
    return Path.cwd()


def _clean_repo_relative(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    without_fragment = stripped.split("#", 1)[0].replace("\\", "/")
    path = PurePosixPath(without_fragment)
    if path.is_absolute() or path.as_posix() in {"", "."} or ".." in path.parts:
        return None
    return path.as_posix()


def _manifest_error(path: Path, pointer: tuple[Any, ...], message: str) -> ValidationError:
    return make_error(CODE_MANIFEST_INVALID, path, _pointer(pointer), message, CONTRACT)


def _load_manifest(repo_root: Path) -> tuple[DoctrineCoverageManifest | None, list[ValidationError]]:
    path = repo_root / MANIFEST_RELATIVE_PATH
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return None, [_manifest_error(path, (), f"doctrine coverage manifest is unreadable: {exc}")]
    if not isinstance(data, dict):
        return None, [_manifest_error(path, (), "doctrine coverage manifest must be a YAML mapping")]

    errors: list[ValidationError] = []
    if data.get("kind") != "brain-doctrine-coverage-manifest":
        errors.append(
            _manifest_error(
                path,
                ("kind",),
                "doctrine coverage manifest kind must be brain-doctrine-coverage-manifest",
            )
        )
    if data.get("schema_version") != "1":
        errors.append(
            _manifest_error(path, ("schema_version",), 'doctrine coverage manifest schema_version must be "1"')
        )

    governed_trees_raw = data.get("governed_trees")
    if not isinstance(governed_trees_raw, list) or not governed_trees_raw:
        errors.append(
            _manifest_error(
                path,
                ("governed_trees",),
                "doctrine coverage manifest governed_trees must be a non-empty list",
            )
        )
        governed_trees: tuple[str, ...] = ()
    else:
        trees: list[str] = []
        for idx, value in enumerate(governed_trees_raw):
            clean = _clean_repo_relative(value)
            if clean is None:
                errors.append(
                    _manifest_error(
                        path,
                        ("governed_trees", idx),
                        "governed_trees entries must be non-empty repo-relative paths",
                    )
                )
                continue
            trees.append(clean)
        governed_trees = tuple(sorted(set(trees)))

    exceptions_raw = data.get("exceptions")
    if exceptions_raw is None:
        exceptions = ()
    elif not isinstance(exceptions_raw, list):
        errors.append(
            _manifest_error(path, ("exceptions",), "doctrine coverage manifest exceptions must be a list")
        )
        exceptions = ()
    else:
        clean_exceptions: list[str] = []
        seen: set[str] = set()
        for idx, value in enumerate(exceptions_raw):
            clean = _clean_repo_relative(value)
            if clean is None:
                errors.append(
                    _manifest_error(
                        path,
                        ("exceptions", idx),
                        "exceptions entries must be non-empty repo-relative paths",
                    )
                )
                continue
            if clean in seen:
                errors.append(
                    _manifest_error(path, ("exceptions", idx), f"duplicate doctrine exception {clean!r}")
                )
                continue
            seen.add(clean)
            clean_exceptions.append(clean)
        exceptions = tuple(clean_exceptions)

    if errors:
        return None, errors
    return DoctrineCoverageManifest(path=path, governed_trees=governed_trees, exceptions=exceptions), []


def _is_under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def _covered_paths(records: Iterable[dict[str, Any]]) -> set[str]:
    covered: set[str] = set()
    for record in records:
        if record.get("status") != "active":
            continue
        method = record.get("verification_method")
        if not isinstance(method, dict) or method.get("type") != "static":
            continue
        clean = _clean_repo_relative(method.get("evidence_ref"))
        if clean is not None:
            covered.add(clean)
    return covered


def _governed_markdown_files(repo_root: Path, manifest: DoctrineCoverageManifest) -> tuple[set[str], list[ValidationError]]:
    files: set[str] = set()
    errors: list[ValidationError] = []
    for idx, tree in enumerate(manifest.governed_trees):
        root = repo_root / tree
        if not root.is_dir():
            errors.append(
                _manifest_error(
                    manifest.path,
                    ("governed_trees", idx),
                    f"governed doctrine tree {tree!r} does not exist",
                )
            )
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name == "README.md":
                continue
            files.add(path.relative_to(repo_root).as_posix())
    return files, errors


def validate_repo(repo_root: Path) -> list[ValidationError]:
    manifest, errors = _load_manifest(repo_root)
    if manifest is None:
        return errors

    doctrine_files, tree_errors = _governed_markdown_files(repo_root, manifest)
    if tree_errors:
        return tree_errors

    if brain_runtime.authoritative_ledger_exists(repo_root):
        try:
            records = brain_runtime.load_authoritative_records(repo_root)
        except brain_runtime.BrainLedgerInvalid as exc:
            return [
                _manifest_error(
                    repo_root / brain_runtime.AUTHORITATIVE_LEDGER_RELATIVE_PATH,
                    (),
                    f"authoritative brain assertion ledger is unreadable: {exc}",
                )
            ]
    else:
        records = []

    covered = _covered_paths(records)
    exceptions = set(manifest.exceptions)
    findings: list[ValidationError] = []

    for idx, exception in enumerate(manifest.exceptions):
        path = repo_root / exception
        if not any(_is_under(exception, tree) for tree in manifest.governed_trees):
            findings.append(
                make_error(
                    CODE_STALE_EXCEPTION,
                    manifest.path,
                    _pointer(("exceptions", idx)),
                    f"doctrine exception {exception!r} is outside governed_trees",
                    CONTRACT,
                )
            )
            continue
        if not path.is_file():
            findings.append(
                make_error(
                    CODE_STALE_EXCEPTION,
                    manifest.path,
                    _pointer(("exceptions", idx)),
                    f"doctrine exception {exception!r} no longer points at an existing file",
                    CONTRACT,
                )
            )
            continue
        if exception in covered:
            findings.append(
                make_error(
                    CODE_STALE_EXCEPTION,
                    manifest.path,
                    _pointer(("exceptions", idx)),
                    f"doctrine exception {exception!r} is now covered by an active static brain assertion; remove it",
                    CONTRACT,
                )
            )

    for path in sorted(doctrine_files):
        if path in covered or path in exceptions:
            continue
        findings.append(
            make_error(
                CODE_UNCOVERED,
                repo_root / path,
                "",
                (
                    f"doctrine file {path!r} is not covered by an active static brain assertion; "
                    f"run `ce brain assert --evidence-ref {path} --type convention ...` "
                    f"or add {path!r} to {MANIFEST_RELATIVE_PATH.as_posix()} exceptions"
                ),
                CONTRACT,
            )
        )

    return findings


@register(
    CHECK_NAME,
    [
        CODE_MANIFEST_INVALID,
        CODE_UNCOVERED,
        CODE_STALE_EXCEPTION,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    raw_paths = [Path(path) for path in paths] or [Path(".")]
    repo_root = _repo_root_for(raw_paths[0])
    return CheckResult(name=CHECK_NAME, errors=tuple(validate_repo(repo_root)))
