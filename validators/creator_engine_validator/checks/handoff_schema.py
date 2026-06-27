"""Handoff and recommended-prompt front-matter schema check.

Validates YAML front matter at the top of handoff and
recommended-prompt documents against the schemas in
``schemas/handoff.schema.yaml`` and
``schemas/recommended-prompt.schema.yaml``.

Documents are identified by the ``kind:`` field in their front
matter:

- ``hermes-handoff`` → handoff schema.
- ``hermes-recommended-prompt`` → recommended-prompt schema.

Other Markdown documents (delivery docs, operations docs, READMEs)
are ignored. Documents without YAML front matter are ignored.

Where the front matter declares both ``allowed_paths_count`` and a
fenced manifest in the body, the check additionally requires the
declared count to match the front-matter value. The
``path_manifest_fidelity`` check enforces the body-level
``*_PATHS_COUNT=`` / ``*_PATHS_SHA256=`` rules; this check enforces
the front-matter <-> body coherence.

See:
  - ``docs/operations/CONTROLLER_BOUNDARY_POLICY.md``
  - ``schemas/handoff.schema.yaml``
  - ``schemas/recommended-prompt.schema.yaml``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "handoff_schema"
CONTRACT = "schemas/handoff.schema.yaml"

DOCUMENT_SUFFIXES: frozenset[str] = frozenset({".md"})

SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        "__pycache__",
        "wheelhouse",
        "wheelhouse-dev",
        ".egg-info",
        ".mypy_cache",
        ".pytest_cache",
        ".git",
        "node_modules",
    }
)

FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

SCHEMA_PATHS = {
    "hermes-handoff": "schemas/handoff.schema.yaml",
    "hermes-recommended-prompt": "schemas/recommended-prompt.schema.yaml",
}


def _extract_front_matter(text: str) -> str | None:
    match = FRONT_MATTER_PATTERN.match(text)
    if match is None:
        return None
    return match.group(1)


def _load_yaml_text(yaml_text: str) -> Any:
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise LoaderError("PyYAML is required") from exc
    return yaml.safe_load(yaml_text)


def _load_schema(schema_path: Path) -> dict[str, Any] | None:
    try:
        import yaml
    except ModuleNotFoundError:  # pragma: no cover
        return None
    try:
        with schema_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, Exception):
        return None
    return data if isinstance(data, dict) else None


def _validate_with_jsonschema(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Validate `instance` against `schema`. Returns a list of error messages, empty on success."""
    try:
        import jsonschema
    except ModuleNotFoundError:  # pragma: no cover
        return []
    errors: list[str] = []
    validator_cls = jsonschema.Draft202012Validator
    validator = validator_cls(schema)
    for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path)):
        field = ".".join(str(p) for p in error.absolute_path) or "<root>"
        errors.append(f"{field}: {error.message}")
    return errors


def _repo_root_for(path: Path) -> Path:
    def _walk(start: Path) -> Path | None:
        for candidate in (start, *start.parents):
            if (candidate / ".git").exists() or (candidate / "validators").is_dir():
                return candidate
        return None

    primary = path if path.is_dir() else path.parent
    # Tmp paths and inputs outside the repo never hit a repo marker, so fall back
    # to cwd's ancestors (which finds the root when pytest is run from validators/)
    # and finally to this module's source location for fully out-of-tree contexts.
    for start in (primary, Path.cwd(), Path(__file__).resolve().parent):
        found = _walk(start)
        if found is not None:
            return found
    return Path.cwd()


def _iter_documents(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for root in paths:
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = []
            for candidate in sorted(root.rglob("*")):
                if any(part in SKIP_DIR_NAMES for part in candidate.parts):
                    continue
                if candidate.is_file():
                    candidates.append(candidate)
        for candidate in candidates:
            if candidate.suffix.lower() not in DOCUMENT_SUFFIXES:
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _count_manifest_lines(text: str) -> int | None:
    """Return the unique-line count of the first fenced ```text manifest block, or None if absent."""
    fence_open = "```text\n"
    idx = text.find(fence_open)
    if idx == -1:
        return None
    start = idx + len(fence_open)
    end = text.find("```", start)
    if end == -1:
        return None
    body = text[start:end].rstrip("\n")
    lines = [line for line in body.split("\n") if line]
    return len({line for line in lines})


def scan_document(doc_path: Path, text: str, repo_root: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    fm_text = _extract_front_matter(text)
    if fm_text is None:
        return errors

    try:
        data = _load_yaml_text(fm_text)
    except (LoaderError, Exception) as exc:
        errors.append(
            make_error(
                "handoff_schema_invalid_yaml",
                doc_path,
                "frontmatter",
                f"front matter is not valid YAML: {exc}",
                CONTRACT,
            )
        )
        return errors

    if not isinstance(data, dict):
        errors.append(
            make_error(
                "handoff_schema_invalid_yaml",
                doc_path,
                "frontmatter",
                "front matter MUST be a YAML mapping",
                CONTRACT,
            )
        )
        return errors

    kind = data.get("kind")
    if kind not in SCHEMA_PATHS:
        return errors

    # ce-ops#331: anchor the packaged schema via the shared resolver (robust to an
    # installed wheel and any working directory), falling back to the repo-root
    # path only if the resolver does not find a packaged file.
    from ..schema import _resolve_schema_path

    schema_path = _resolve_schema_path(SCHEMA_PATHS[kind])
    if not schema_path.is_file():
        schema_path = repo_root / SCHEMA_PATHS[kind]
    schema = _load_schema(schema_path)
    if schema is None:
        errors.append(
            make_error(
                "handoff_schema_unavailable",
                doc_path,
                "frontmatter",
                f"schema not loadable from {SCHEMA_PATHS[kind]}",
                CONTRACT,
            )
        )
        return errors

    for issue in _validate_with_jsonschema(data, schema):
        errors.append(
            make_error(
                "handoff_schema_violation",
                doc_path,
                "frontmatter",
                f"{kind}: {issue}",
                CONTRACT,
            )
        )

    # Coherence: front-matter allowed_paths_count vs fenced manifest unique-line count.
    declared_count = data.get("allowed_paths_count")
    if isinstance(declared_count, int):
        manifest_lines = _count_manifest_lines(text)
        if manifest_lines is not None and manifest_lines != declared_count:
            errors.append(
                make_error(
                    "handoff_schema_count_incoherent",
                    doc_path,
                    "frontmatter.allowed_paths_count",
                    (
                        f"front matter declares allowed_paths_count={declared_count} "
                        f"but fenced manifest normalizes to {manifest_lines} unique lines"
                    ),
                    CONTRACT,
                )
            )

    return errors


@register(CHECK_NAME, ["WH-002"])
def run(paths: Iterable[Path]) -> CheckResult:
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = _repo_root_for(raw_paths[0])
    errors: list[ValidationError] = []
    for doc in _iter_documents(raw_paths):
        try:
            text = doc.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        errors.extend(scan_document(doc, text, repo_root))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
