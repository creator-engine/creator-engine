"""Single source of truth for the control-plane portability boundary."""

from __future__ import annotations

import ast
import io
import re
import stat
import subprocess
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from ..reporting import CheckResult, ValidationError, make_error

CHECK_NAME = "portability_plane"
CONTRACT = "surfaces/portability-plane-manifest.yaml"
MANIFEST = Path("surfaces/portability-plane-manifest.yaml")
CONTROL_ROOT = Path("validators/creator_engine_validator")
BINARY_SENTINEL = b"\0"
_SELF = Path(__file__).resolve()
_SELF_REL = "validators/creator_engine_validator/checks/portability_plane.py"

CODE_MISSING_MANIFEST = "CE-PORTABILITY-MANIFEST"
CODE_MALFORMED_MANIFEST = "CE-PORTABILITY-MANIFEST"
CODE_STALE_ENTRY = "CE-PORTABILITY-STALE"
CODE_VIOLATION = "CE-PORTABILITY"

SYSTEMD_RE = re.compile(r"\b(?:systemd|sdnotify)\b", re.IGNORECASE)
RUN_PATH_RE = re.compile(r"^/run(?:/|$)|/run/")
DEV_SHM_RE = re.compile(r"^/dev/shm(?:/|$)|/dev/shm/")
SUBPROCESS_COMMAND_RE = re.compile(r"^(?:systemctl|setfacl|journalctl)(?:\s|$)")


@dataclass(frozen=True)
class PortabilityOffense:
    path: str
    line: int
    pattern: str
    label: str
    text: str

    def key(self) -> tuple[str, str, str]:
        return self.path, self.pattern, self.text

    def format(self) -> str:
        return f"{self.path}:{self.line} [{self.label}] {self.text}"


@dataclass(frozen=True)
class PlaneManifest:
    runtime_plane_paths: frozenset[str]
    baseline_exemptions: tuple[dict[str, str], ...]


class PortabilityScanError(Exception):
    """A scan-surface or manifest failure that must fail the check."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _tracked_repo_paths(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PortabilityScanError(f"could not enumerate tracked files: {exc}") from exc
    return [rel for rel in proc.stdout.decode("utf-8", errors="replace").split("\0") if rel]


def _is_regular_file(path: Path) -> bool:
    return stat.S_ISREG(path.stat().st_mode)


def _control_plane_source_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for rel in sorted(_tracked_repo_paths(root)):
        path = root / rel
        if rel == _SELF_REL or path.resolve() == _SELF:
            continue
        if not rel.startswith(f"{CONTROL_ROOT.as_posix()}/") or not rel.endswith(".py"):
            continue
        try:
            if not _is_regular_file(path):
                continue
            if BINARY_SENTINEL in path.read_bytes():
                continue
        except OSError as exc:
            raise PortabilityScanError(f"{rel}: unreadable file: {exc}") from exc
        paths.append(rel)
    return paths


def _load_manifest(root: Path) -> tuple[PlaneManifest | None, list[ValidationError]]:
    path = root / MANIFEST
    if not path.is_file():
        return None, [make_error(CODE_MISSING_MANIFEST, MANIFEST, "", "missing portability plane manifest", CONTRACT)]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, [make_error(CODE_MALFORMED_MANIFEST, MANIFEST, "", f"could not parse YAML: {exc}", CONTRACT)]

    if not isinstance(data, dict) or not isinstance(data.get("portability_plane"), dict):
        return None, [
            make_error(
                CODE_MALFORMED_MANIFEST,
                MANIFEST,
                "portability_plane",
                "expected a portability_plane mapping",
                CONTRACT,
            )
        ]
    section = data["portability_plane"]
    runtime_paths = section.get("runtime_plane_paths", [])
    baseline = section.get("baseline_exemptions", [])
    errors: list[ValidationError] = []
    if not isinstance(runtime_paths, list) or not all(isinstance(item, str) for item in runtime_paths):
        errors.append(
            make_error(
                CODE_MALFORMED_MANIFEST,
                MANIFEST,
                "runtime_plane_paths",
                "expected a list of repo-relative paths",
                CONTRACT,
            )
        )
        runtime_paths = []
    if not isinstance(baseline, list) or not all(isinstance(item, dict) for item in baseline):
        errors.append(
            make_error(
                CODE_MALFORMED_MANIFEST,
                MANIFEST,
                "baseline_exemptions",
                "expected a list of exemption mappings",
                CONTRACT,
            )
        )
        baseline = []

    normalized_runtime: set[str] = set()
    for rel in runtime_paths:
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            errors.append(
                make_error(
                    CODE_MALFORMED_MANIFEST,
                    MANIFEST,
                    "runtime_plane_paths",
                    f"invalid runtime-plane path {rel!r}",
                    CONTRACT,
                )
            )
            continue
        normalized_runtime.add(rel_path.as_posix())

    normalized_baseline: list[dict[str, str]] = []
    for index, entry in enumerate(baseline):
        normalized: dict[str, str] = {}
        for field in ("path", "pattern", "match", "date", "reason"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    make_error(
                        CODE_MALFORMED_MANIFEST,
                        MANIFEST,
                        f"baseline_exemptions[{index}].{field}",
                        "required non-empty string",
                        CONTRACT,
                    )
                )
                continue
            normalized[field] = value
        if len(normalized) == 5:
            normalized_baseline.append(normalized)

    return PlaneManifest(
        runtime_plane_paths=frozenset(normalized_runtime),
        baseline_exemptions=tuple(normalized_baseline),
    ), errors


def _docstring_lines(text: str) -> frozenset[int]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return frozenset()

    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body
        if not body:
            continue
        first = body[0]
        if not (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            continue
        start = getattr(first, "lineno", None)
        end = getattr(first, "end_lineno", start)
        if start is None or end is None:
            continue
        lines.update(range(start, end + 1))
    return frozenset(lines)


def _literal_value(token_text: str) -> str:
    try:
        value = ast.literal_eval(token_text)
    except (SyntaxError, ValueError):
        return token_text
    return value if isinstance(value, str) else token_text


def _line_offenses(rel: str, text: str) -> list[PortabilityOffense]:
    source_lines = text.splitlines()
    docstrings = _docstring_lines(text)
    offenses: list[PortabilityOffense] = []
    per_line_tokens: dict[int, list[str]] = {}
    seen: set[tuple[int, str]] = set()

    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for token in tokens:
            line = token.start[0]
            token_text = token.string
            if token.type in {tokenize.COMMENT, tokenize.ENCODING, tokenize.ENDMARKER}:
                continue
            if line in docstrings:
                continue
            if token.type == tokenize.STRING:
                value = _literal_value(token_text)
                for pattern, label, regex in (
                    ("systemd-reference", "systemd or sdnotify reference", SYSTEMD_RE),
                    ("run-path-literal", "literal /run path", RUN_PATH_RE),
                    ("dev-shm-path-literal", "literal /dev/shm path", DEV_SHM_RE),
                    ("subprocess-command", "runtime-only subprocess command", SUBPROCESS_COMMAND_RE),
                ):
                    if regex.search(value):
                        key = (line, pattern)
                        if key not in seen:
                            offenses.append(
                                PortabilityOffense(
                                    path=rel,
                                    line=line,
                                    pattern=pattern,
                                    label=label,
                                    text=source_lines[line - 1].strip(),
                                )
                            )
                            seen.add(key)
                continue
            if token.type == tokenize.NAME and SYSTEMD_RE.fullmatch(token_text):
                key = (line, "systemd-reference")
                if key not in seen:
                    offenses.append(
                        PortabilityOffense(
                            path=rel,
                            line=line,
                            pattern="systemd-reference",
                            label="systemd or sdnotify reference",
                            text=source_lines[line - 1].strip(),
                        )
                    )
                    seen.add(key)
            if token.type not in {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}:
                per_line_tokens.setdefault(line, []).append(token_text)
    except tokenize.TokenError as exc:
        raise PortabilityScanError(f"{rel}: could not tokenize Python source: {exc}") from exc

    for line, parts in per_line_tokens.items():
        compact = "".join(parts)
        if "socket.AF_UNIX" not in compact:
            continue
        key = (line, "af-unix-socket")
        if key in seen:
            continue
        offenses.append(
            PortabilityOffense(
                path=rel,
                line=line,
                pattern="af-unix-socket",
                label="socket.AF_UNIX usage",
                text=source_lines[line - 1].strip(),
            )
        )
        seen.add(key)

    return sorted(offenses, key=lambda offense: (offense.path, offense.line, offense.pattern))


def scan_offenses(*, repo_root: Path | None = None, manifest: PlaneManifest | None = None) -> list[PortabilityOffense]:
    root = (repo_root or globals()["repo_root"]()).resolve()
    if manifest is None:
        manifest, errors = _load_manifest(root)
        if errors:
            raise PortabilityScanError("; ".join(error.format() for error in errors))
        if manifest is None:
            raise PortabilityScanError("missing portability plane manifest")

    offenses: list[PortabilityOffense] = []
    for rel in _control_plane_source_paths(root):
        if rel in manifest.runtime_plane_paths:
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise PortabilityScanError(f"{rel}: unreadable file: {exc}") from exc
        offenses.extend(_line_offenses(rel, text))
    return offenses


def _validate_manifest_references(manifest: PlaneManifest, source_paths: Iterable[str]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    tracked = set(source_paths)
    for rel in sorted(manifest.runtime_plane_paths):
        if rel not in tracked:
            errors.append(
                make_error(
                    CODE_STALE_ENTRY,
                    MANIFEST,
                    rel,
                    "runtime-plane manifest path is absent or not a tracked control-plane Python module",
                    CONTRACT,
                )
            )
    for index, entry in enumerate(manifest.baseline_exemptions):
        rel = entry["path"]
        if rel not in tracked:
            errors.append(
                make_error(
                    CODE_STALE_ENTRY,
                    MANIFEST,
                    f"baseline_exemptions[{index}].path",
                    f"baseline path {rel!r} is absent or not tracked",
                    CONTRACT,
                )
            )
        if rel in manifest.runtime_plane_paths:
            errors.append(
                make_error(
                    CODE_MALFORMED_MANIFEST,
                    MANIFEST,
                    f"baseline_exemptions[{index}].path",
                    f"baseline path {rel!r} is also declared runtime-plane",
                    CONTRACT,
                )
            )
    return errors


def validate_repo(root: Path) -> tuple[list[ValidationError], int]:
    root = root.resolve()
    manifest, errors = _load_manifest(root)
    if manifest is None:
        return errors, 0
    source_paths = _control_plane_source_paths(root)
    errors.extend(_validate_manifest_references(manifest, source_paths))
    offenses = scan_offenses(repo_root=root, manifest=manifest)
    baseline_keys = {(entry["path"], entry["pattern"], entry["match"]) for entry in manifest.baseline_exemptions}
    actual_keys = {offense.key() for offense in offenses}

    for entry in manifest.baseline_exemptions:
        key = (entry["path"], entry["pattern"], entry["match"])
        if key not in actual_keys:
            errors.append(
                make_error(
                    CODE_STALE_ENTRY,
                    MANIFEST,
                    entry["path"],
                    f"baseline exemption for {entry['pattern']!r} is stale and must be removed",
                    CONTRACT,
                )
            )

    for offense in offenses:
        if offense.key() in baseline_keys:
            continue
        errors.append(
            make_error(
                CODE_VIOLATION,
                offense.path,
                str(offense.line),
                (
                    f"{offense.label} is only allowed in declared runtime-plane modules "
                    f"or exact dated baseline exemptions: {offense.text}"
                ),
                CONTRACT,
            )
        )

    return errors, len(manifest.baseline_exemptions)


def run(paths: Iterable[Path]) -> CheckResult:
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        root = path if path.is_dir() else path.parent
        for candidate in (root.resolve(), *root.resolve().parents):
            if (candidate / CONTROL_ROOT).is_dir():
                resolved = candidate.resolve()
                if resolved not in seen:
                    roots.append(resolved)
                    seen.add(resolved)
                break

    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    for root in roots or [repo_root()]:
        try:
            root_errors, baseline_count = validate_repo(root)
        except PortabilityScanError as exc:
            errors.append(make_error(CODE_MALFORMED_MANIFEST, root, "", str(exc), CONTRACT))
            continue
        errors.extend(root_errors)
        warnings.append(
            make_error(
                "CE-PORTABILITY-BASELINE",
                MANIFEST,
                "",
                f"portability baseline exemptions: {baseline_count}",
                CONTRACT,
            )
        )
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))
