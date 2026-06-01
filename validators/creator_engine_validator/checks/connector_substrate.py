"""G2.005.0 connector substrate validator.

Two shape-only record families for the Phase D connector substrate:

* ``connector`` — a connector descriptor (source-host or tracker). Declares an
  opaque provider-class label, a capability scope (read-only or a bounded write
  set), and a credential reference BY NAME ONLY. No secret values anywhere.
* ``mission_brief`` — the bounded task brief a connector carries. Declares an
  opaque assignment/lane ref, permitted mutation classes (which MAY include the
  bounded non-privileged ``tracker_mirror`` class but MUST NOT include any
  privileged class), a capability scope, and references CE-event/PCL artifacts
  only by opaque 64-hex content hashes. Shape-only ``signature``.

Substrate only: no connector runtime, no network/API calls, no credential
injection. Privileged mutation classes remain Operator-only; ``agent_ratifier``
stays reserved-inactive and may not emit; connectors/Mission-Briefs never ratify.
Active writes under legacy ``.hermes/`` paths are refused.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

# --- shared substrate floor --------------------------------------------------
OPERATING_MODES = frozenset({"strict", "auto", "transcendence"})
EMITTING_ROLES = frozenset({"operator", "controller", "architect", "implementer", "reviewer", "verification", "agent_reviewer"})
FORBIDDEN_ACTIVE_ROLES = frozenset({"agent_ratifier", "source"})

CONNECTOR_KINDS = frozenset({"source_host", "tracker"})
TRACKER_MIRROR_VERBS = frozenset({"issue-create", "issue-update", "pr-comment"})
READ_VERBS = frozenset({"issue-read", "pr-read", "repo-read", "status-read"})

NON_PRIVILEGED_BRIEF_CLASSES = frozenset({"docs", "code", "tracker_mirror"})
PRIVILEGED_CLASSES = frozenset({"deploy", "governance", "identity", "security", "attestation", "redaction"})

FORBIDDEN_SECRET_KEYS = frozenset(
    {"token", "secret", "password", "api_key", "apikey", "access_token", "client_secret", "private_key", "installation_id", "app_slug", "account_name"}
)
_SECRET_VALUE_RE = re.compile(r"(gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}|xox[baprs]-[A-Za-z0-9-]{8,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

_SCANNED_YAML_SUFFIXES = {".yml", ".yaml"}
_SCANNED_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_PROTOCOL_DOC = "CONNECTOR_PROTOCOL.md"
_SPEC_FEATURE_DIR = "005-connector-substrate"
_HERMES_ACTIVE_TOKENS = ("connector", "mission", "brief", "tracker")

# --- connector family --------------------------------------------------------
CONN_CHECK_NAME = "connector"
CONN_CONTRACT = "specs/v2/005-connector-substrate/spec.ce.yml#connector"
CONN_SCHEMA_PATH = "schemas/connector.schema.yaml"
CONN_KEY = "connector"
CONN_SCOPE_TOKEN = "connector"

CONN_CODE_SCHEMA = "VAL-CONN-SCHEMA"
CONN_CODE_KIND = "VAL-CONN-KIND"
CONN_CODE_ROLE_FLOOR = "VAL-CONN-ROLE-FLOOR"
CONN_CODE_MODE_ENUM = "VAL-CONN-MODE-ENUM"
CONN_CODE_CREDENTIAL_REF = "VAL-CONN-CREDENTIAL-REF"
CONN_CODE_SECRET = "VAL-CONN-SECRET"
CONN_CODE_CAPABILITY = "VAL-CONN-CAPABILITY"
CONN_CODE_NO_INLINE = "VAL-CONN-NO-INLINE"
CONN_CODE_WRITE_FREEZE = "VAL-CONN-WRITE-FREEZE"

# --- mission-brief family ----------------------------------------------------
MB_CHECK_NAME = "mission_brief"
MB_CONTRACT = "specs/v2/005-connector-substrate/spec.ce.yml#mission_brief"
MB_SCHEMA_PATH = "schemas/mission-brief.schema.yaml"
MB_KEY = "mission_brief"
MB_SCOPE_TOKEN = "mission-brief"

MB_CODE_SCHEMA = "VAL-MB-SCHEMA"
MB_CODE_ROLE_FLOOR = "VAL-MB-ROLE-FLOOR"
MB_CODE_MODE_ENUM = "VAL-MB-MODE-ENUM"
MB_CODE_CLASS = "VAL-MB-CLASS"
MB_CODE_PRIVILEGE_ESCALATION = "VAL-MB-PRIVILEGE-ESCALATION"
MB_CODE_POINTER_SHAPE = "VAL-MB-POINTER-SHAPE"
MB_CODE_SIGNATURE_SHAPE = "VAL-MB-SIGNATURE-SHAPE"
MB_CODE_SECRET = "VAL-MB-SECRET"
MB_CODE_NO_INLINE = "VAL-MB-NO-INLINE"
MB_CODE_WRITE_FREEZE = "VAL-MB-WRITE-FREEZE"


def _normalize_token(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _pointer(parts: tuple[Any, ...]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _contains_secret(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_SECRET_VALUE_RE.search(value))
    if isinstance(value, dict):
        for k, v in value.items():
            if _normalize_token(k) in FORBIDDEN_SECRET_KEYS and isinstance(v, str) and v.strip():
                return True
            if _contains_secret(v):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_secret(v) for v in value)
    return False


def _subtree_contains_hermes_active_write(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        if not text.startswith(".hermes/") and "/.hermes/" not in text:
            return False
        return any(tok in text.lower() for tok in _HERMES_ACTIVE_TOKENS)
    if isinstance(value, dict):
        return any(_subtree_contains_hermes_active_write(k) or _subtree_contains_hermes_active_write(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_subtree_contains_hermes_active_write(v) for v in value)
    return False


def _path_in_scope(path: Path, scope_token: str) -> bool:
    parts = path.parts
    if scope_token in parts:
        return True
    if path.name == _PROTOCOL_DOC:
        return True
    for i in range(len(parts) - 2):
        if parts[i] == "specs" and parts[i + 1] == "v2" and parts[i + 2] == _SPEC_FEATURE_DIR:
            return path.name == "spec.md"
    return False


def _iter_scanned_files(paths: Iterable[Path], scope_token: str) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    suffixes = _SCANNED_YAML_SUFFIXES | _SCANNED_MARKDOWN_SUFFIXES
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(p for p in path.rglob("*") if p.is_file())
        else:
            candidates = []
        for candidate in candidates:
            if _is_tmp_artifact(candidate) or candidate.suffix.lower() not in suffixes or not _path_in_scope(candidate, scope_token):
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


def _validate_markdown(path: Path, single_key: str, code: str, contract: str) -> list[ValidationError]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [make_error(code, path, "", f"failed to read markdown: {exc}", contract)]
    errors: list[ValidationError] = []
    in_fence = False
    fence_is_yaml = False
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if line_no == 1 and stripped == "---":
            in_fence = True
            fence_is_yaml = True
            continue
        if in_fence and fence_is_yaml and stripped in {"---", "..."}:
            in_fence = False
            fence_is_yaml = False
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if not in_fence:
                marker = stripped[3:].strip().lower()
                in_fence = True
                fence_is_yaml = marker in {"yaml", "yml"}
            else:
                in_fence = False
                fence_is_yaml = False
            continue
        if not fence_is_yaml:
            continue
        key = stripped.split(":", 1)[0].strip()
        if key == single_key:
            errors.append(make_error(code, path, _pointer(("line", line_no)), "connector-substrate metadata belongs in sidecars/examples, not Markdown bodies", contract))
    return errors


# --- connector ---------------------------------------------------------------
def validate_connector_file(path: Path) -> list[ValidationError]:
    path = Path(path)
    if path.suffix.lower() in _SCANNED_MARKDOWN_SUFFIXES:
        return _validate_markdown(path, CONN_KEY, CONN_CODE_NO_INLINE, CONN_CONTRACT)
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [make_error(CONN_CODE_SCHEMA, path, "", str(exc), CONN_SCHEMA_PATH)]
    errors: list[ValidationError] = []
    try:
        errors.extend(validate_with_schema(data, CONN_SCHEMA_PATH, path, code=CONN_CODE_SCHEMA, contract=CONN_SCHEMA_PATH))
    except Exception as exc:  # pragma: no cover - environment guard
        errors.append(make_error(CONN_CODE_SCHEMA, path, "", f"schema validation failed: {exc}", CONN_SCHEMA_PATH))
    if not isinstance(data, dict) or CONN_KEY not in data or not isinstance(data[CONN_KEY], dict):
        if not errors:
            errors.append(make_error(CONN_CODE_SCHEMA, path, "", "scoped YAML files must declare a connector mapping", CONN_SCHEMA_PATH))
        return errors
    rec = data[CONN_KEY]
    pre = (CONN_KEY,)

    if _normalize_token(rec.get("connector_kind", "")) not in {_normalize_token(k) for k in CONNECTOR_KINDS}:
        errors.append(make_error(CONN_CODE_KIND, path, _pointer(pre + ("connector_kind",)), "connector_kind must be one of source_host, tracker", CONN_CONTRACT))
    role = _normalize_token(rec.get("emitting_role", ""))
    if role not in EMITTING_ROLES or role in FORBIDDEN_ACTIVE_ROLES:
        errors.append(make_error(CONN_CODE_ROLE_FLOOR, path, _pointer(pre + ("emitting_role",)), "emitting_role must be a canonical non-ratifying role; agent_ratifier/source are reserved-inactive and may not emit", CONN_CONTRACT))
    if _normalize_token(rec.get("operating_mode", "")) not in OPERATING_MODES:
        errors.append(make_error(CONN_CODE_MODE_ENUM, path, _pointer(pre + ("operating_mode",)), "operating_mode must be one of strict, auto, transcendence", CONN_CONTRACT))

    cred = rec.get("credential_ref")
    if not isinstance(cred, dict) or "ref_name" not in cred or "ref_kind" not in cred:
        errors.append(make_error(CONN_CODE_CREDENTIAL_REF, path, _pointer(pre + ("credential_ref",)), "credential_ref must be a {ref_kind, ref_name} reference BY NAME — never a secret value", CONN_CONTRACT))

    if _contains_secret(rec):
        errors.append(make_error(CONN_CODE_SECRET, path, _pointer(pre,), "connector descriptor must not carry secret/credential values; reference credentials by name only", CONN_CONTRACT))

    cap = rec.get("capability")
    if isinstance(cap, dict):
        scope = _normalize_token(cap.get("scope", ""))
        verbs = cap.get("verbs") if isinstance(cap.get("verbs"), list) else []
        allowed = READ_VERBS if scope == "read_only" else TRACKER_MIRROR_VERBS if scope == "write" else frozenset()
        for v in verbs:
            if str(v) not in allowed:
                errors.append(make_error(CONN_CODE_CAPABILITY, path, _pointer(pre + ("capability", "verbs")), f"verb {v!r} is not permitted for scope {scope!r}; write scope is bounded to tracker_mirror verbs (issue-create/issue-update/pr-comment), no privileged verbs", CONN_CONTRACT))

    if _subtree_contains_hermes_active_write(rec):
        errors.append(make_error(CONN_CODE_WRITE_FREEZE, path, _pointer(pre,), "connector substrate must not target legacy .hermes/ paths as active v2 state", CONN_CONTRACT))
    return errors


# --- mission-brief -----------------------------------------------------------
def validate_mission_brief_file(path: Path) -> list[ValidationError]:
    path = Path(path)
    if path.suffix.lower() in _SCANNED_MARKDOWN_SUFFIXES:
        return _validate_markdown(path, MB_KEY, MB_CODE_NO_INLINE, MB_CONTRACT)
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [make_error(MB_CODE_SCHEMA, path, "", str(exc), MB_SCHEMA_PATH)]
    errors: list[ValidationError] = []
    try:
        errors.extend(validate_with_schema(data, MB_SCHEMA_PATH, path, code=MB_CODE_SCHEMA, contract=MB_SCHEMA_PATH))
    except Exception as exc:  # pragma: no cover - environment guard
        errors.append(make_error(MB_CODE_SCHEMA, path, "", f"schema validation failed: {exc}", MB_SCHEMA_PATH))
    if not isinstance(data, dict) or MB_KEY not in data or not isinstance(data[MB_KEY], dict):
        if not errors:
            errors.append(make_error(MB_CODE_SCHEMA, path, "", "scoped YAML files must declare a mission_brief mapping", MB_SCHEMA_PATH))
        return errors
    rec = data[MB_KEY]
    pre = (MB_KEY,)

    role = _normalize_token(rec.get("emitting_role", ""))
    if role not in EMITTING_ROLES or role in FORBIDDEN_ACTIVE_ROLES:
        errors.append(make_error(MB_CODE_ROLE_FLOOR, path, _pointer(pre + ("emitting_role",)), "emitting_role must be a canonical non-ratifying role; agent_ratifier/source are reserved-inactive and Mission-Briefs never ratify", MB_CONTRACT))
    if _normalize_token(rec.get("operating_mode", "")) not in OPERATING_MODES:
        errors.append(make_error(MB_CODE_MODE_ENUM, path, _pointer(pre + ("operating_mode",)), "operating_mode must be one of strict, auto, transcendence", MB_CONTRACT))

    classes = rec.get("declared_mutation_classes")
    if isinstance(classes, list):
        for idx, cls in enumerate(classes):
            c = _normalize_token(cls)
            if c in PRIVILEGED_CLASSES:
                errors.append(make_error(MB_CODE_PRIVILEGE_ESCALATION, path, _pointer(pre + ("declared_mutation_classes", idx)), f"privileged class {cls!r} must not be declared by a Mission-Brief; privileged classes remain Operator-only", MB_CONTRACT))
            elif c not in NON_PRIVILEGED_BRIEF_CLASSES:
                errors.append(make_error(MB_CODE_CLASS, path, _pointer(pre + ("declared_mutation_classes", idx)), f"declared mutation class {cls!r} is not a permitted connector-substrate class (docs, code, tracker_mirror)", MB_CONTRACT))

    refs = rec.get("refs")
    if isinstance(refs, dict):
        for key in ("ce_event_content_hash", "pcl_content_hash", "binding_ref"):
            if key in refs:
                val = refs.get(key)
                if not isinstance(val, str) or not _HASH_RE.match(val):
                    errors.append(make_error(MB_CODE_POINTER_SHAPE, path, _pointer(pre + ("refs", key)), f"{key} must reference the artifact by an opaque 64-hex content hash", MB_CONTRACT))

    sig = rec.get("signature")
    if not isinstance(sig, dict):
        errors.append(make_error(MB_CODE_SIGNATURE_SHAPE, path, _pointer(pre + ("signature",)), "signature must be a shape-only mapping", MB_CONTRACT))
    else:
        if not {"scheme", "key_id", "value"} <= set(sig):
            errors.append(make_error(MB_CODE_SIGNATURE_SHAPE, path, _pointer(pre + ("signature",)), "signature missing required shape fields", MB_CONTRACT))
        if _normalize_token(sig.get("value", "")) != "reserved_inactive":
            errors.append(make_error(MB_CODE_SIGNATURE_SHAPE, path, _pointer(pre + ("signature", "value")), "signature value must remain reserved-inactive in G2.005.0", MB_CONTRACT))

    if _contains_secret(rec):
        errors.append(make_error(MB_CODE_SECRET, path, _pointer(pre,), "Mission-Brief must not carry secret/credential values", MB_CONTRACT))
    if _subtree_contains_hermes_active_write(rec):
        errors.append(make_error(MB_CODE_WRITE_FREEZE, path, _pointer(pre,), "Mission-Brief must not target legacy .hermes/ paths as active v2 state", MB_CONTRACT))
    return errors


@register(
    CONN_CHECK_NAME,
    [CONN_CODE_SCHEMA, CONN_CODE_KIND, CONN_CODE_ROLE_FLOOR, CONN_CODE_MODE_ENUM, CONN_CODE_CREDENTIAL_REF, CONN_CODE_SECRET, CONN_CODE_CAPABILITY, CONN_CODE_NO_INLINE, CONN_CODE_WRITE_FREEZE],
)
def run_connector(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in _iter_scanned_files(paths, CONN_SCOPE_TOKEN):
        errors.extend(validate_connector_file(file_path))
    return CheckResult(name=CONN_CHECK_NAME, errors=tuple(errors))


@register(
    MB_CHECK_NAME,
    [MB_CODE_SCHEMA, MB_CODE_ROLE_FLOOR, MB_CODE_MODE_ENUM, MB_CODE_CLASS, MB_CODE_PRIVILEGE_ESCALATION, MB_CODE_POINTER_SHAPE, MB_CODE_SIGNATURE_SHAPE, MB_CODE_SECRET, MB_CODE_NO_INLINE, MB_CODE_WRITE_FREEZE],
)
def run_mission_brief(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in _iter_scanned_files(paths, MB_SCOPE_TOKEN):
        errors.extend(validate_mission_brief_file(file_path))
    return CheckResult(name=MB_CHECK_NAME, errors=tuple(errors))
