"""v2 terminology-canon enforcement (G2.001.1).

Realizes three required-validation entries from the ``G2.001.0`` foundation
substrate ``required_validation`` map (see
``specs/v2/001-v2-foundation-substrate/spec.ce.yml``):

* ``VAL-TERMINOLOGY`` (RV2-001-011 / RV2-001-012) — new v2 artifacts MUST emit
  ``operator`` as the human-authority machine role and the canonical
  ``Operator ratifies prompt:`` ratification line; the legacy ``source`` role
  value and ``Source ratifies prompt:`` line are accepted on import only and
  MUST NOT be emitted by new v2 artifacts.
* ``VAL-WRITE-FREEZE`` (RV2-001-007) — new v2 artifacts MUST NOT declare
  ``.hermes/`` as an active/canonical state or write root; ``.ce/`` is the only
  canonical active-state root in emitted v2 artifacts.
* ``VAL-NO-DESTRUCTIVE-REMOVAL`` (RV2-001-023, alias-accept half) — the same
  legacy forms remain readable when they appear in clearly-marked
  import/crosswalk/archive/historical context, so the check ACCEPTS them there
  (no destructive removal of v1 aliases — Q-O5).

Scope and boundaries (kept deliberately narrow and low-false-positive):

* The check fires only on artifacts under ``specs/v2/`` (and on the bundled
  ``ce-terminology-v2`` fixtures); it never inspects v1 ``specs/NNN``,
  ``docs/``, or other roots, so it cannot regress existing v1 checks.
* Role / active-root emission is enforced on the *values* of structured YAML
  fields (``*.ce.yml`` sidecars and v2 YAML governance), not on prose, because
  that is where new v2 artifacts actually emit roles and state roots.
* Ratification-line emission is enforced on Markdown: a line that, after
  stripping list/quote/heading/backtick markers, *begins* an actual
  ``Source ratifies prompt:<target>`` statement. A mid-sentence mention of the
  legacy phrase (e.g. describing the import-alias rule) is descriptive, not an
  emission, and is accepted.
* Markdown ``.hermes/`` mentions are descriptive (citing the legacy/read-only
  root, the write-freeze rule, or a permitted ``.hermes/`` research/historical
  read context) and are not treated as active-state emission; active-state
  declaration is a structured-field concern handled on YAML.

A file is treated as clearly-marked legacy/import context — and therefore fully
accepted — when it is the canonical crosswalk register (``_crosswalk.yml``),
lives under an ``archive``/``legacy``/``historical``/``imported`` path segment,
or carries an explicit context marker (``ce_terminology_context:`` in YAML or
``<!-- ce-terminology-context: ... -->`` in Markdown) naming a legacy context.

The check is read-only; it only loads and inspects files under the given paths.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "ce_terminology_v2"
CONTRACT = "specs/v2/001-v2-foundation-substrate/spec.ce.yml#terminology_canon"

# Failure codes (substrings tie back to the spec.ce.yml required_validation IDs).
CODE_SOURCE_ROLE = "VAL-TERMINOLOGY-SOURCE-ROLE"          # RV2-001-011
CODE_SOURCE_RATIFIES = "VAL-TERMINOLOGY-SOURCE-RATIFIES"  # RV2-001-012
CODE_HERMES_ACTIVE = "VAL-WRITE-FREEZE-HERMES-ACTIVE"     # RV2-001-007
CODE_SIDECAR_ALIAS = "VAL-TERMINOLOGY-SIDECAR-ALIAS"      # RV2-001-016
CODE_INVALID = "ce_terminology_v2_invalid_record"

# Legacy sidecar filename alias: new v2 artifacts emit ``*.ce.yml``; the legacy
# ``*.creator-engine.yml`` filename is accepted on import only (FR-016 / RV2-001-016).
LEGACY_SIDECAR_SUFFIX = ".creator-engine.yml"

# Legacy forms that v2 artifacts accept on import but never emit.
LEGACY_ROLE_VALUE = "source"
CANONICAL_ROLE_VALUE = "operator"
LEGACY_ACTIVE_ROOT = ".hermes/"
CANONICAL_ACTIVE_ROOT = ".ce/"

# Explicit context values that mark a region/file as clearly-marked legacy
# import/crosswalk/archive/historical context (accept-on-import, no removal).
LEGACY_CONTEXT_VALUES = frozenset(
    {
        "import",
        "import-alias",
        "import_alias",
        "crosswalk",
        "archive",
        "archival",
        "historical",
        "history",
        "legacy",
        "legacy-import",
        "legacy_import",
    }
)
# Path segments whose presence marks a file as legacy/import context.
LEGACY_PATH_SEGMENTS = frozenset({"archive", "legacy", "historical", "imported"})
# The canonical crosswalk register is, by definition, legacy<->canonical context.
CROSSWALK_FILENAMES = frozenset({"_crosswalk.yml", "_crosswalk.yaml"})

# YAML keys that *bind* a human-authority machine role. A value of ``source``
# under one of these keys is an emitted legacy role.
EXPLICIT_ROLE_KEYS = frozenset(
    {
        "role",
        "ratifier",
        "ratified_by",
        "required_ratifier_role",
        "human_authority_role",
        "human_authority_machine_role",
        "machine_role",
        "authority_role",
        "emitted_role",
        "canonical_role",
        # plural ratifier role fields (round 8)
        "ratifiers",
        "required_ratifiers",
        "allowed_ratifiers",
    }
)
# Keys *inside* a role-bearing subtree whose value DOCUMENTS the legacy alias
# rather than EMITTING it (e.g. a terminology canon's ``legacy_alias: source``,
# paired with ``canonical_emit: operator``). Tokens under these keys are descriptive,
# not emissions, so the recursive role check skips them to avoid false positives on
# the canon's own self-description. (The forbidden emission shapes use ordinary
# keys like ``primary``/``machine``/``name`` or encode ``source`` as a key, none of
# which are descriptors, so blocker coverage is preserved.)
ROLE_LEGACY_DESCRIPTOR_KEYS = frozenset(
    {
        # EXACT descriptor keys only. Broad `legacy`/`alias`/`aliases` were removed
        # (round 6): they let emissions like `roles: {legacy: source}` slip through.
        # The canon documents the alias with the precise key `legacy_alias`.
        "legacy_alias",
        "legacy_aliases",
        "legacy_value",
        "import_alias",
        "import_aliases",
    }
)

# YAML keys that declare an active / write state root. A value of ``.hermes/``
# under one of these keys violates the write-freeze.
ACTIVE_ROOT_KEYS = frozenset(
    {
        "canonical_active_root",
        "canonical_active_state_root",
        "active_state_root",
        "active_root",
        "active_state",
        "write_root",
        "write_roots",
        "allowed_write_root",
        "allowed_write_roots",
        "active_write_root",
        "active_write_roots",
        "canonical_write_root",
        "canonical_write_roots",
        "canonical_state_root",
        "canonical_state_roots",
        "state_root",
        "state_write_root",
        "emit_root",
        "output_root",
    }
)

# Markdown line that begins an actual emitted ratification statement using the
# legacy ``Source`` authority (canonical is ``Operator ratifies prompt:``). The
# trailing ``\S`` requires a real target, so a bare descriptive mention of the
# phrase does not match.
_RATIFIES_LINE = re.compile(r"^source ratifies prompt:\s*\S", re.IGNORECASE)
# Leading markers stripped before testing a Markdown line for emission.
_LEADING_MARKERS = re.compile(r"^[\s>#*+\-`\"']+")
# Ordered-list item marker (``1.`` / ``1)``) stripped after the leading markers so an
# ordered-list ratification line (``1. Source ratifies prompt:<target>``) is still
# recognised as an emission.
_ORDERED_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s+")
# Task-list checkbox marker (``[ ]`` / ``[x]``) stripped so a task-list ratification
# line (``- [ ] Source ratifies prompt:<target>``) is still recognised as an emission.
_TASK_LIST_MARKER = re.compile(r"^\[[ xX]\]\s+")
_MD_CONTEXT_MARKER = re.compile(
    r"<!--\s*ce[-_]terminology[-_]context:\s*([A-Za-z0-9_-]+)\s*-->", re.IGNORECASE
)

_SCANNED_SUFFIXES = {".md", ".yml", ".yaml"}


def _normalize_key(key: Any) -> str:
    return str(key).strip().lower()


def _is_role_key(key: str) -> bool:
    # Fail closed across structured role-emission shapes the review flagged:
    # `role`/`*_role` (allowlist), plural `roles`/`*_roles`, and authority-bearing
    # fields `authority`/`human_authority`/`*_authority`.
    if key in EXPLICIT_ROLE_KEYS:
        return True
    return (
        key.endswith("_role")
        or key.endswith("_roles")
        or key == "roles"
        or key == "authority"
        or key.endswith("_authority")
    )


def _is_active_root_key(key: str) -> bool:
    # Cautious broadening: accept a known active/write/state-root key OR its simple
    # plural (e.g. ``active_state_roots`` / ``state_roots`` / ``active_roots``).
    # Stripping a single trailing ``s`` and re-checking the allowlist deliberately
    # does NOT match unrelated ``*_root``/``*_roots`` keys such as ``legacy_root``,
    # keeping false positives low (only leaves starting with ``.hermes/`` are flagged).
    if key in ACTIVE_ROOT_KEYS:
        return True
    return key.endswith("s") and key[:-1] in ACTIVE_ROOT_KEYS


def _path_in_scope(path: Path) -> bool:
    """True for artifacts under a contiguous ``specs/v2`` path or the bundled v2 fixtures."""
    parts = path.parts
    for i in range(len(parts) - 1):
        if parts[i] == "specs" and parts[i + 1] == "v2":
            return True
    return "ce-terminology-v2" in parts


def _is_legacy_context_path(path: Path) -> bool:
    if path.name in CROSSWALK_FILENAMES:
        return True
    return any(part in LEGACY_PATH_SEGMENTS for part in path.parts)


def _yaml_declares_legacy_context(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    marker = data.get("ce_terminology_context")
    return isinstance(marker, str) and marker.strip().lower() in LEGACY_CONTEXT_VALUES


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def iter_scanned_files(paths: Iterable[Path]) -> list[Path]:
    """Return in-scope v2 Markdown/YAML artifacts under ``paths``."""
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(
                p for p in path.rglob("*") if p.is_file() and p.suffix in _SCANNED_SUFFIXES
            )
        else:
            candidates = []
        for candidate in candidates:
            if candidate.suffix not in _SCANNED_SUFFIXES:
                continue
            if _is_tmp_artifact(candidate):
                continue
            if not _path_in_scope(candidate):
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


def _pointer(parts: tuple[str, ...]) -> str:
    rendered = [part.replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _yaml_value_errors(value: Any, path: Path, parts: tuple[str, ...]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, str):
        # Ratification-line emission may appear in any structured YAML string value
        # (``ratification_line: "Source ratifies prompt:/x"``, nested, or in a list),
        # not only in Markdown. Begins-with semantics (``_RATIFIES_LINE``) means a
        # string that merely *mentions* the phrase is descriptive, not an emission.
        if _text_has_ratifies_emission(value):
            errors.append(
                make_error(
                    CODE_SOURCE_RATIFIES,
                    path,
                    _pointer(parts),
                    "new v2 artifacts MUST emit the canonical ratification line "
                    "'Operator ratifies prompt:'; legacy 'Source ratifies prompt:' is accepted on "
                    "import only (FR-012 / RV2-001-012)",
                    CONTRACT,
                )
            )
    elif isinstance(value, dict):
        for key, child in value.items():
            key_norm = _normalize_key(key)
            # Descriptor keys document a legacy alias (e.g. the canon's
            # ``legacy_alias: "Source ratifies prompt:"``); their subtree is
            # self-description, not emission — skip it entirely.
            if key_norm in ROLE_LEGACY_DESCRIPTOR_KEYS:
                continue
            child_parts = (*parts, str(key))
            if _is_role_key(key_norm):
                errors.extend(_role_value_errors(child, path, child_parts))
            if _is_active_root_key(key_norm):
                errors.extend(_active_root_value_errors(child, path, child_parts))
            errors.extend(_yaml_value_errors(child, path, child_parts))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_yaml_value_errors(child, path, (*parts, str(index))))
    return errors


def _iter_role_tokens(
    value: Any, parts: tuple[str, ...]
) -> Iterable[tuple[str, tuple[str, ...]]]:
    """Yield candidate role tokens under a role-bearing field.

    Walks the whole subtree so the legacy role is caught however it is encoded:
    a direct/nested string *value* (``role: {name: source}``, ``roles: [{name: source}]``)
    OR a map *key* (``roles: {source: {active: true}}``). Both string leaves and
    dict keys are yielded with their JSON-pointer parts.
    """
    if isinstance(value, str):
        yield value, parts
    elif isinstance(value, dict):
        for key, child in value.items():
            if _normalize_key(key) in ROLE_LEGACY_DESCRIPTOR_KEYS:
                continue  # documents the legacy alias; not an emission — skip subtree
            yield str(key), (*parts, str(key))  # key may itself encode the role
            yield from _iter_role_tokens(child, (*parts, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_role_tokens(child, (*parts, str(index)))


def _role_value_errors(value: Any, path: Path, parts: tuple[str, ...]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for token, token_parts in _iter_role_tokens(value, parts):
        if token.strip().lower() == LEGACY_ROLE_VALUE:
            errors.append(
                make_error(
                    CODE_SOURCE_ROLE,
                    path,
                    _pointer(token_parts),
                    "new v2 artifacts MUST emit the canonical human-authority role "
                    f"{CANONICAL_ROLE_VALUE!r}; legacy {LEGACY_ROLE_VALUE!r} is accepted on "
                    "import only (FR-011 / RV2-001-011)",
                    CONTRACT,
                )
            )
    return errors


def _iter_active_root_tokens(
    value: Any, parts: tuple[str, ...]
) -> Iterable[tuple[str, tuple[str, ...]]]:
    """Yield candidate active-root tokens (string leaves AND dict keys) under ``value``.

    Walks scalars, dicts, and lists so a ``.hermes`` root is caught however it is
    encoded under a recognized active/write-root field: a direct/nested/plural
    *value* (``write_roots: {primary: .hermes/}``, ``active_state_roots: [.hermes]``)
    OR a map *key* (``write_roots: {.hermes/: active}``).
    """
    if isinstance(value, str):
        yield value, parts
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key), (*parts, str(key))  # key may itself encode the root
            yield from _iter_active_root_tokens(child, (*parts, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_active_root_tokens(child, (*parts, str(index)))


def _is_hermes_active_root(text: str) -> bool:
    """True when ``text`` denotes the legacy ``.hermes`` active/write root.

    Normalizes a single leading ``./`` then matches the bare ``.hermes`` directory
    or ``.hermes/...``. Exact-prefix matching avoids flagging distinct
    ``.hermes``-prefixed names such as ``.hermesphere`` / ``./.hermesphere``. This is
    deliberately NOT general path canonicalization.
    """
    s = text.strip()
    if s.startswith("./"):
        s = s[2:]  # normalize one leading ./ only
    return s == ".hermes" or s.startswith(LEGACY_ACTIVE_ROOT)


def _active_root_value_errors(value: Any, path: Path, parts: tuple[str, ...]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for token, token_parts in _iter_active_root_tokens(value, parts):
        if _is_hermes_active_root(token):
            errors.append(
                make_error(
                    CODE_HERMES_ACTIVE,
                    path,
                    _pointer(token_parts),
                    f"new v2 artifacts MUST NOT declare {LEGACY_ACTIVE_ROOT!r} as an active/write "
                    f"state root; {CANONICAL_ACTIVE_ROOT!r} is the only canonical active-state root "
                    "(write-freeze, FR-007 / RV2-001-007)",
                    CONTRACT,
                )
            )
    return errors


def _line_is_ratifies_emission(raw_line: str) -> bool:
    """True when a single line *begins* a legacy ``Source ratifies prompt:<target>``
    statement after stripping list/quote/heading/ordered-list/task-list markers."""
    stripped = _LEADING_MARKERS.sub("", raw_line)
    stripped = _ORDERED_LIST_MARKER.sub("", stripped)
    stripped = _TASK_LIST_MARKER.sub("", stripped).strip()
    return bool(_RATIFIES_LINE.match(stripped))


def _text_has_ratifies_emission(text: str) -> bool:
    """True when any line of ``text`` is a legacy ratification emission. Used for YAML
    string values (incl. multiline block scalars), line-wise."""
    return any(_line_is_ratifies_emission(line) for line in text.splitlines())


def _markdown_errors(text: str, path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        if _line_is_ratifies_emission(raw_line):
            errors.append(
                make_error(
                    CODE_SOURCE_RATIFIES,
                    path,
                    f"L{lineno}",
                    "new v2 artifacts MUST emit the canonical ratification line "
                    "'Operator ratifies prompt:'; legacy 'Source ratifies prompt:' is accepted on "
                    "import only (FR-012 / RV2-001-012)",
                    CONTRACT,
                )
            )
    return errors


def _markdown_declares_legacy_context(text: str) -> bool:
    match = _MD_CONTEXT_MARKER.search(text)
    return bool(match and match.group(1).strip().lower() in LEGACY_CONTEXT_VALUES)


def validate_file(path: Path) -> list[ValidationError]:
    """Validate one in-scope v2 artifact. Legacy-context files are accepted."""
    if _is_legacy_context_path(path):
        return []
    if path.suffix in {".yml", ".yaml"}:
        try:
            data = load_yaml(path)
        except LoaderError as exc:
            return [make_error(CODE_INVALID, path, "", str(exc), CONTRACT)]
        if _yaml_declares_legacy_context(data):
            return []
        errors = _yaml_value_errors(data, path, ())
        if path.name.endswith(LEGACY_SIDECAR_SUFFIX):
            errors.append(
                make_error(
                    CODE_SIDECAR_ALIAS,
                    path,
                    "",
                    "new v2 artifacts MUST use the canonical '*.ce.yml' sidecar filename; "
                    "legacy '*.creator-engine.yml' is accepted on import only (FR-016 / RV2-001-016)",
                    CONTRACT,
                )
            )
        return errors
    # Markdown
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [make_error(CODE_INVALID, path, "", str(exc), CONTRACT)]
    if _markdown_declares_legacy_context(text):
        return []
    return _markdown_errors(text, path)


@register(CHECK_NAME, [CODE_SOURCE_ROLE, CODE_SOURCE_RATIFIES, CODE_HERMES_ACTIVE, CODE_SIDECAR_ALIAS, CODE_INVALID])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in iter_scanned_files(paths):
        errors.extend(validate_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
