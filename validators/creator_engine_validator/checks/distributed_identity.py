"""G2.004.2 distributed-identity substrate validator.

Two shape-only record families extend the feature-004 coordination substrate
without coupling to federated-identity, CE-event, or PCL runtime code:

* ``federated_identity_binding`` — cross-repo identity bindings. A binding
  asserts, as coordination/attestation state only, that a named principal in one
  repository is the same principal as named identities in one or more other
  repositories. Identities and repos are referenced by opaque, stable identifiers
  only — no secret material, no key bytes.
* ``distributed_claim`` — the cross-repo / team-mode coordination claim
  primitive (the distributed analogue of a single-repo PCL lane claim). A claim
  binds to a federated identity binding and may reference CE-event blocks and PCL
  records, but only by opaque 64-hex content hashes carried in the body.

Both families are content-addressed, hash-chained, never ratify, keep
``agent_ratifier`` reserved-inactive, and freeze active writes under the legacy
``.hermes/`` root. Live runtime, ``.ce/`` live writes, signing, and key custody
remain deferred to a later, separately ratified gate.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

# --- federated identity binding family ---------------------------------------
FIB_CHECK_NAME = "federated_identity_binding"
FIB_CONTRACT = "specs/v2/004-pcl-substrate/spec.ce.yml#federated_identity_binding"
FIB_SCHEMA_PATH = "schemas/federated-identity-binding.schema.yaml"
FIB_SINGLE_KEY = "federated_identity_binding"
FIB_CHAIN_KEY = "federated_identity_chain"
FIB_RECORD_KINDS = frozenset({"federated_identity_binding", "binding_revocation"})
FIB_SCOPE_TOKEN = "federated-identity-binding"

FIB_CODE_SCHEMA = "VAL-FIB-SCHEMA"
FIB_CODE_CONTENT_ADDRESS = "VAL-FIB-CONTENT-ADDRESS"
FIB_CODE_CHAIN_LINK = "VAL-FIB-CHAIN-LINK"
FIB_CODE_RECORD_KIND = "VAL-FIB-RECORD-KIND"
FIB_CODE_ROLE_FLOOR = "VAL-FIB-ROLE-FLOOR"
FIB_CODE_MODE_ENUM = "VAL-FIB-MODE-ENUM"
FIB_CODE_BINDING_SHAPE = "VAL-FIB-BINDING-SHAPE"
FIB_CODE_SIGNATURE_SHAPE = "VAL-FIB-SIGNATURE-SHAPE"
FIB_CODE_NO_INLINE = "VAL-FIB-NO-INLINE"
FIB_CODE_WRITE_FREEZE = "VAL-FIB-WRITE-FREEZE"

# --- distributed claim family ------------------------------------------------
DC_CHECK_NAME = "distributed_claim"
DC_CONTRACT = "specs/v2/004-pcl-substrate/spec.ce.yml#distributed_claim"
DC_SCHEMA_PATH = "schemas/distributed-claim.schema.yaml"
DC_SINGLE_KEY = "distributed_claim"
DC_CHAIN_KEY = "distributed_claim_chain"
DC_RECORD_KINDS = frozenset({"claim_open", "claim_renew", "claim_release"})
DC_SCOPE_TOKEN = "distributed-claim"

DC_CODE_SCHEMA = "VAL-DC-SCHEMA"
DC_CODE_CONTENT_ADDRESS = "VAL-DC-CONTENT-ADDRESS"
DC_CODE_CHAIN_LINK = "VAL-DC-CHAIN-LINK"
DC_CODE_RECORD_KIND = "VAL-DC-RECORD-KIND"
DC_CODE_ROLE_FLOOR = "VAL-DC-ROLE-FLOOR"
DC_CODE_MODE_ENUM = "VAL-DC-MODE-ENUM"
DC_CODE_POINTER_SHAPE = "VAL-DC-POINTER-SHAPE"
DC_CODE_SIGNATURE_SHAPE = "VAL-DC-SIGNATURE-SHAPE"
DC_CODE_NO_INLINE = "VAL-DC-NO-INLINE"
DC_CODE_WRITE_FREEZE = "VAL-DC-WRITE-FREEZE"

# --- shared substrate floor --------------------------------------------------
OPERATING_MODES = frozenset({"strict", "auto", "transcendence"})
EMITTING_ROLES = frozenset({"operator", "controller", "architect", "implementer", "reviewer", "verification", "agent_reviewer"})
FORBIDDEN_ACTIVE_ROLES = frozenset({"agent_ratifier", "source"})

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_HERMES_ACTIVE_TOKENS = ("claim", "identit", "binding", "pcl", "ce-event", "ce_event")
_SCANNED_YAML_SUFFIXES = {".yml", ".yaml"}
_SCANNED_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_PROTOCOL_DOC = "DISTRIBUTED_IDENTITY_PROTOCOL.md"
_SPEC_FEATURE_DIR = "004-pcl-substrate"


def _normalize_token(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _pointer(parts: tuple[Any, ...]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _canonical_hash(record: dict[str, Any]) -> str:
    material = {k: v for k, v in record.items() if k not in {"content_hash", "signature"}}
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _subtree_contains_hermes_active_write(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        if not text.startswith(".hermes/") and "/.hermes/" not in text:
            return False
        lowered = text.lower()
        return any(token in lowered for token in _HERMES_ACTIVE_TOKENS)
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


class _Family:
    """Validation configuration for one shape-only record family."""

    def __init__(
        self,
        *,
        contract: str,
        schema_path: str,
        single_key: str,
        chain_key: str,
        record_kinds: frozenset[str],
        scope_token: str,
        codes: dict[str, str],
        body_validator: Callable[["_Family", dict[str, Any], Path, tuple[Any, ...]], list[ValidationError]],
    ) -> None:
        self.contract = contract
        self.schema_path = schema_path
        self.single_key = single_key
        self.chain_key = chain_key
        self.record_kinds = record_kinds
        self.scope_token = scope_token
        self.codes = codes
        self.body_validator = body_validator

    def err(self, code: str, path: Path, parts: tuple[Any, ...], message: str, contract: str | None = None) -> ValidationError:
        return make_error(code, path, _pointer(parts), message, contract or self.contract)

    def records_from_data(self, data: Any, path: Path) -> tuple[list[dict[str, Any]], list[ValidationError]]:
        code = self.codes["schema"]
        if not isinstance(data, dict):
            return [], [self.err(code, path, (), f"{self.single_key} files must be YAML mappings", self.schema_path)]
        if self.single_key in data:
            record = data[self.single_key]
            if isinstance(record, dict):
                return [record], []
            return [], [self.err(code, path, (self.single_key,), f"{self.single_key} must be a mapping", self.schema_path)]
        if self.chain_key in data:
            chain = data[self.chain_key]
            if not isinstance(chain, list):
                return [], [self.err(code, path, (self.chain_key,), f"{self.chain_key} must be a list", self.schema_path)]
            errors: list[ValidationError] = []
            records: list[dict[str, Any]] = []
            for idx, item in enumerate(chain):
                if not isinstance(item, dict):
                    errors.append(self.err(code, path, (self.chain_key, idx), "chain entries must be mappings", self.schema_path))
                else:
                    records.append(item)
            return records, errors
        return [], [self.err(code, path, (), f"scoped YAML files must declare {self.single_key} or {self.chain_key}", self.schema_path)]

    def validate_signature(self, record: dict[str, Any], path: Path, prefix: tuple[Any, ...]) -> list[ValidationError]:
        code = self.codes["signature_shape"]
        sig = record.get("signature")
        if not isinstance(sig, dict):
            return [self.err(code, path, prefix + ("signature",), "signature must be a shape-only mapping")]
        required = {"scheme", "key_id", "value"}
        missing = sorted(required - set(sig))
        errors: list[ValidationError] = []
        if missing:
            errors.append(self.err(code, path, prefix + ("signature",), f"signature missing required shape fields: {', '.join(missing)}"))
        if _normalize_token(sig.get("value", "")) != "reserved_inactive":
            errors.append(self.err(code, path, prefix + ("signature", "value"), "signature value must remain reserved-inactive in G2.004.2"))
        return errors

    def validate_records(self, records: list[dict[str, Any]], path: Path, *, root_key: str) -> list[ValidationError]:
        errors: list[ValidationError] = []
        previous_hash: str | None = None
        for idx, record in enumerate(records):
            prefix = (root_key, idx) if root_key.endswith("_chain") else (root_key,)
            kind = _normalize_token(record.get("record_kind", ""))
            if kind not in self.record_kinds:
                errors.append(self.err(self.codes["record_kind"], path, prefix + ("record_kind",), "record_kind must be one of the canonical record kinds for this family"))
            role = _normalize_token(record.get("emitting_role", ""))
            if role not in EMITTING_ROLES or role in FORBIDDEN_ACTIVE_ROLES:
                errors.append(self.err(self.codes["role_floor"], path, prefix + ("emitting_role",), "emitting_role must be a canonical non-ratifying role; agent_ratifier is reserved-inactive and these records never ratify"))
            mode = _normalize_token(record.get("operating_mode", ""))
            if mode not in OPERATING_MODES:
                errors.append(self.err(self.codes["mode_enum"], path, prefix + ("operating_mode",), "operating_mode must be one of strict, auto, transcendence"))
            expected = _canonical_hash(record)
            if record.get("content_hash") != expected:
                errors.append(self.err(self.codes["content_address"], path, prefix + ("content_hash",), "content_hash must equal SHA256 of canonical record material excluding content_hash and signature"))
            parent = record.get("parent_hash")
            if idx == 0:
                if parent is not None:
                    errors.append(self.err(self.codes["chain_link"], path, prefix + ("parent_hash",), "genesis record parent_hash must be null"))
            elif parent != previous_hash:
                errors.append(self.err(self.codes["chain_link"], path, prefix + ("parent_hash",), "non-genesis parent_hash must match prior record content_hash"))
            previous_hash = str(record.get("content_hash") or "")
            errors.extend(self.validate_signature(record, path, prefix))
            if kind in self.record_kinds:
                errors.extend(self.body_validator(self, record, path, prefix))
            if _subtree_contains_hermes_active_write(record.get("body")):
                errors.append(self.err(self.codes["write_freeze"], path, prefix + ("body",), "G2.004.2 records must not target legacy .hermes/ paths as active v2 coordination/identity state"))
        return errors

    def validate_markdown_file(self, path: Path) -> list[ValidationError]:
        code = self.codes["no_inline"]
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return [self.err(code, path, (), f"failed to read markdown: {exc}")]
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
            if key in {self.single_key, self.chain_key}:
                errors.append(self.err(code, path, ("line", line_no), "record metadata belongs in sidecars/examples, not Markdown bodies"))
        return errors

    def validate_file(self, path: Path) -> list[ValidationError]:
        if path.suffix.lower() in _SCANNED_MARKDOWN_SUFFIXES:
            return self.validate_markdown_file(path)
        code = self.codes["schema"]
        try:
            data = load_yaml(path)
        except LoaderError as exc:
            return [self.err(code, path, (), str(exc), self.schema_path)]
        errors: list[ValidationError] = []
        try:
            errors.extend(validate_with_schema(data, self.schema_path, path, code=code, contract=self.schema_path))
        except Exception as exc:  # pragma: no cover - environment guard
            errors.append(self.err(code, path, (), f"schema validation failed: {exc}", self.schema_path))
        records, record_errors = self.records_from_data(data, path)
        errors.extend(record_errors)
        root_key = self.chain_key if isinstance(data, dict) and self.chain_key in data else self.single_key
        if records:
            errors.extend(self.validate_records(records, path, root_key=root_key))
        return errors

    def run(self, paths: Iterable[Path], name: str) -> CheckResult:
        errors: list[ValidationError] = []
        for file_path in _iter_scanned_files(paths, self.scope_token):
            errors.extend(self.validate_file(file_path))
        return CheckResult(name=name, errors=tuple(errors))


def _validate_fib_body(family: _Family, record: dict[str, Any], path: Path, prefix: tuple[Any, ...]) -> list[ValidationError]:
    code = family.codes["binding_shape"]
    body = record.get("body")
    if not isinstance(body, dict):
        return [family.err(code, path, prefix + ("body",), "federated identity binding records must carry a body mapping")]
    kind = _normalize_token(record.get("record_kind", ""))
    errors: list[ValidationError] = []
    if kind == "binding_revocation":
        ref = body.get("revokes_binding")
        if not isinstance(ref, str) or not _HASH_RE.match(ref):
            errors.append(family.err(code, path, prefix + ("body", "revokes_binding"), "binding_revocation body must reference the revoked binding by an opaque 64-hex revokes_binding hash"))
        return errors
    principal = body.get("principal_id")
    if not isinstance(principal, str) or not principal.strip():
        errors.append(family.err(code, path, prefix + ("body", "principal_id"), "federated_identity_binding body must carry an opaque non-empty principal_id"))
    repo_bindings = body.get("repo_bindings")
    if not isinstance(repo_bindings, list) or len(repo_bindings) < 2:
        errors.append(family.err(code, path, prefix + ("body", "repo_bindings"), "a cross-repo federated_identity_binding must bind the principal across at least two repositories"))
    else:
        for i, rb in enumerate(repo_bindings):
            if not isinstance(rb, dict) or not str(rb.get("repo_id", "")).strip() or not str(rb.get("identity_ref", "")).strip():
                errors.append(family.err(code, path, prefix + ("body", "repo_bindings", i), "each repo binding must carry opaque non-empty repo_id and identity_ref"))
    return errors


def _validate_dc_body(family: _Family, record: dict[str, Any], path: Path, prefix: tuple[Any, ...]) -> list[ValidationError]:
    code = family.codes["pointer_shape"]
    body = record.get("body")
    if not isinstance(body, dict):
        return [family.err(code, path, prefix + ("body",), "distributed claim records must carry a body mapping")]
    errors: list[ValidationError] = []
    subject = body.get("claim_subject")
    if not isinstance(subject, str) or not subject.strip():
        errors.append(family.err(code, path, prefix + ("body", "claim_subject"), "distributed claim body must carry an opaque non-empty claim_subject"))
    ref = body.get("binding_ref")
    if not isinstance(ref, str) or not _HASH_RE.match(ref):
        errors.append(family.err(code, path, prefix + ("body", "binding_ref"), "distributed claim body must bind to a federated identity binding by an opaque 64-hex binding_ref"))
    for opt in ("ce_event_content_hash", "pcl_content_hash"):
        if opt in body:
            value = body.get(opt)
            if not isinstance(value, str) or not _HASH_RE.match(value):
                errors.append(family.err(code, path, prefix + ("body", opt), f"{opt} must reference the artifact by an opaque 64-hex content hash"))
    return errors


_FIB_FAMILY = _Family(
    contract=FIB_CONTRACT,
    schema_path=FIB_SCHEMA_PATH,
    single_key=FIB_SINGLE_KEY,
    chain_key=FIB_CHAIN_KEY,
    record_kinds=FIB_RECORD_KINDS,
    scope_token=FIB_SCOPE_TOKEN,
    codes={
        "schema": FIB_CODE_SCHEMA,
        "content_address": FIB_CODE_CONTENT_ADDRESS,
        "chain_link": FIB_CODE_CHAIN_LINK,
        "record_kind": FIB_CODE_RECORD_KIND,
        "role_floor": FIB_CODE_ROLE_FLOOR,
        "mode_enum": FIB_CODE_MODE_ENUM,
        "binding_shape": FIB_CODE_BINDING_SHAPE,
        "signature_shape": FIB_CODE_SIGNATURE_SHAPE,
        "no_inline": FIB_CODE_NO_INLINE,
        "write_freeze": FIB_CODE_WRITE_FREEZE,
    },
    body_validator=_validate_fib_body,
)

_DC_FAMILY = _Family(
    contract=DC_CONTRACT,
    schema_path=DC_SCHEMA_PATH,
    single_key=DC_SINGLE_KEY,
    chain_key=DC_CHAIN_KEY,
    record_kinds=DC_RECORD_KINDS,
    scope_token=DC_SCOPE_TOKEN,
    codes={
        "schema": DC_CODE_SCHEMA,
        "content_address": DC_CODE_CONTENT_ADDRESS,
        "chain_link": DC_CODE_CHAIN_LINK,
        "record_kind": DC_CODE_RECORD_KIND,
        "role_floor": DC_CODE_ROLE_FLOOR,
        "mode_enum": DC_CODE_MODE_ENUM,
        "pointer_shape": DC_CODE_POINTER_SHAPE,
        "signature_shape": DC_CODE_SIGNATURE_SHAPE,
        "no_inline": DC_CODE_NO_INLINE,
        "write_freeze": DC_CODE_WRITE_FREEZE,
    },
    body_validator=_validate_dc_body,
)


def validate_fib_file(path: Path) -> list[ValidationError]:
    return _FIB_FAMILY.validate_file(Path(path))


def validate_dc_file(path: Path) -> list[ValidationError]:
    return _DC_FAMILY.validate_file(Path(path))


@register(
    FIB_CHECK_NAME,
    [
        FIB_CODE_SCHEMA,
        FIB_CODE_CONTENT_ADDRESS,
        FIB_CODE_CHAIN_LINK,
        FIB_CODE_RECORD_KIND,
        FIB_CODE_ROLE_FLOOR,
        FIB_CODE_MODE_ENUM,
        FIB_CODE_BINDING_SHAPE,
        FIB_CODE_SIGNATURE_SHAPE,
        FIB_CODE_NO_INLINE,
        FIB_CODE_WRITE_FREEZE,
    ],
)
def run_federated_identity_binding(paths: Iterable[Path]) -> CheckResult:
    return _FIB_FAMILY.run(paths, FIB_CHECK_NAME)


@register(
    DC_CHECK_NAME,
    [
        DC_CODE_SCHEMA,
        DC_CODE_CONTENT_ADDRESS,
        DC_CODE_CHAIN_LINK,
        DC_CODE_RECORD_KIND,
        DC_CODE_ROLE_FLOOR,
        DC_CODE_MODE_ENUM,
        DC_CODE_POINTER_SHAPE,
        DC_CODE_SIGNATURE_SHAPE,
        DC_CODE_NO_INLINE,
        DC_CODE_WRITE_FREEZE,
    ],
)
def run_distributed_claim(paths: Iterable[Path]) -> CheckResult:
    return _DC_FAMILY.run(paths, DC_CHECK_NAME)
