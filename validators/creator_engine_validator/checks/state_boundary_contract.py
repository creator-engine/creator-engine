"""State Boundary Contract validation (RV1-021, PCO v1 Gate 2).

Validates State Boundary Contract records against
``schemas/state-boundary-contract.schema.yaml`` plus the write-root,
redaction-safe, and `.hermes/`-ignored predicates that the schema alone
cannot express.

Gate 2 scope is substrate/validator-only. This check:

* enforces that the only governed runtime write root is the ignored
  ``.hermes/`` state root and refuses tracked governance/doc/spec/schema/
  template/validator/source/package write targets;
* refuses secret VALUES in config (only secret names/references allowed);
* verifies ``.hermes/`` is ignored by Git from the worktree context and
  refuses records that declare governed state would be tracked.

The check is read-only: it does not create ``.hermes/`` runtime files, does
not modify ``.gitignore``, and only runs ``git check-ignore`` (a read-only
query) against the worktree it discovers from the record path.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "state_boundary_contract"
CONTRACT = "docs/operations/STATE_BOUNDARY_PROTOCOL.md"
SCHEMA = "schemas/state-boundary-contract.schema.yaml"
KIND_VALUE = "state-boundary-contract"

CODE_SCHEMA = "RV1-021"
CODE_WRITE = "RV1-021-WRITE"
CODE_SECRET = "RV1-021-SECRET"
CODE_IGNORE = "RV1-021-IGNORE"
CODE_INVALID = "state_boundary_contract_invalid_record"

# The only governed runtime write root for the v1.0 kernel.
GOVERNED_STATE_ROOT = ".hermes/"
# Tracked surfaces that governed runtime writes must never target. The
# forbidden_write_roots field must enumerate at least these.
PROTECTED_SURFACE_ROOTS = ("docs/", "specs/", "schemas/", "templates/", "validators/")

SECRET_KEY_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "access_token",
        "account_name",
        "browser_session_cookie",
        "credential",
        "host_gh_token",
        "installation_id",
        "model_api_key",
        "oauth_token",
        "password",
        "private_key",
        "refresh_token",
        "secret_value",
        "session_cookie",
        "token",
    }
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
)


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_contract(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_state_boundary_contract_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate State Boundary Contract files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p)
                and not _is_under_excluded(p)
                and not _is_tmp_artifact(p)
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
            if not _record_is_contract(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def _pointer(parts: Iterable[str]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _secret_errors(value: Any, path: Path, parts: tuple[str, ...] = ()) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_parts = (*parts, key_text)
            if key_text.lower() in SECRET_KEY_NAMES:
                errors.append(
                    make_error(
                        CODE_SECRET,
                        path,
                        _pointer(child_parts),
                        "State Boundary config must record secret names/references only, not secret-bearing fields",
                        CONTRACT,
                    )
                )
            errors.extend(_secret_errors(child, path, child_parts))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_secret_errors(child, path, (*parts, str(index))))
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                errors.append(
                    make_error(
                        CODE_SECRET,
                        path,
                        _pointer(parts),
                        "State Boundary config must not store secret values, only secret names/references",
                        CONTRACT,
                    )
                )
                break
    return errors


def _write_root_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    allowed = record.get("allowed_write_roots")
    if isinstance(allowed, list):
        non_governed = [r for r in allowed if r != GOVERNED_STATE_ROOT]
        if non_governed:
            errors.append(
                make_error(
                    CODE_WRITE,
                    path,
                    "/allowed_write_roots",
                    f"the only governed runtime write root is {GOVERNED_STATE_ROOT!r}; "
                    f"refused non-governed write roots: {non_governed}",
                    CONTRACT,
                )
            )
    forbidden = record.get("forbidden_write_roots")
    if isinstance(forbidden, list):
        forbidden_set = {r for r in forbidden if isinstance(r, str)}
        missing = [root for root in PROTECTED_SURFACE_ROOTS if root not in forbidden_set]
        if missing:
            errors.append(
                make_error(
                    CODE_WRITE,
                    path,
                    "/forbidden_write_roots",
                    f"forbidden_write_roots must enumerate protected tracked surfaces; missing: {missing}",
                    CONTRACT,
                )
            )
    return errors


def _declared_ignore_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    if record.get("state_root_gitignored") is False:
        return [
            make_error(
                CODE_IGNORE,
                path,
                "/state_root_gitignored",
                "record declares the governed state root is not Git-ignored; governed runtime state would be tracked",
                CONTRACT,
            )
        ]
    return []


def validate_state_boundary_contract_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one State Boundary Contract record against RV1-021 (no subprocess)."""
    errors = list(
        validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)
    )
    errors.extend(_secret_errors(record, path))
    errors.extend(_write_root_errors(record, path))
    errors.extend(_declared_ignore_errors(record, path))
    return errors


def _repo_root_for(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / "validators").is_dir():
            return candidate
    return None


def _run_git(args: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    """Run a read-only git query, returning (returncode, stdout, stderr). Never raises."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30, check=False
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return 128, "", str(exc)
    return result.returncode, result.stdout, result.stderr


def _live_ignore_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Verify `.hermes/` is ignored by Git from the record's worktree context."""
    state_root = record.get("state_root")
    if not isinstance(state_root, str) or not state_root:
        return []
    repo_root = _repo_root_for(path)
    if repo_root is None:
        return []  # no worktree context discoverable; do not invent a failure
    returncode, _out, _err = _run_git(["check-ignore", state_root], repo_root)
    # git check-ignore: 0 = path is ignored, 1 = path is NOT ignored,
    # 128 = error / not a git repo. Only a definitive "not ignored" is a failure.
    if returncode == 1:
        return [
            make_error(
                CODE_IGNORE,
                path,
                "/state_root",
                f"Git reports state_root {state_root!r} is not ignored from {repo_root}; "
                "governed runtime state would be tracked",
                CONTRACT,
            )
        ]
    return []


@register(CHECK_NAME, [CODE_SCHEMA, CODE_WRITE, CODE_SECRET, CODE_IGNORE])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_state_boundary_contract_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(
                make_error(
                    CODE_INVALID,
                    record_path,
                    "/",
                    "state-boundary-contract record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_state_boundary_contract_record(record, record_path))
        errors.extend(_live_ignore_errors(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
