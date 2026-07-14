"""Fail-closed PR-diff gate for release smoke evidence.

Release finalization is deliberately out of band.  This guard only decides
whether a release-class change carries a complete, signed *record* of its
hermetic smoke.  It never runs Docker, signs, fetches, or publishes anything.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import yaml

from .. import v3_installer
from ..reporting import CheckResult, ValidationError, make_error
from . import install_spec_signature_guard
from .git_helpers import repo_root_for, run_git


CHECK_NAME = "release_smoke_evidence"
CONTRACT = "docs/llms-install.md release smoke evidence policy"
CODE_INVALID = "VAL-RELEASE-SMOKE-EVIDENCE-INVALID"

INSTALL_SPEC = Path("docs/llms-install.md")
FINALIZE_MANIFEST = Path("docs/release-finalize-manifest.yml")
EVIDENCE_DIR = Path(".ce/release-evidence")
SCHEMA_VERSION = "1"
SSH_SIG_NAMESPACE = "ce-release-smoke-v1"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
IMAGE_RE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")

Verifier = Callable[[str, bytes, Any, Any], bool]


def _error(path: Path | str, field: str, message: str) -> ValidationError:
    return make_error(CODE_INVALID, path, field, message, CONTRACT)


def _changed_paths(repo_root: Path, base: str) -> tuple[set[str] | None, ValidationError | None]:
    code, stdout, _stderr = run_git(["diff", "--name-only", f"{base}..HEAD"], repo_root)
    if code != 0:
        return None, _error("PR_DIFF", "", "git diff name-only failed")
    return {line.strip() for line in stdout.splitlines() if line.strip()}, None


def _canonical_record_bytes(record: dict[str, object]) -> bytes:
    unsigned = dict(record)
    unsigned.pop("signature", None)
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _string(mapping: dict[str, object], key: str) -> str | None:
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _exact_keys(value: object, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _read_manifest(path: Path) -> tuple[dict[str, object] | None, str | None]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, f"could not parse release finalize manifest: {exc}"
    if not isinstance(value, dict):
        return None, "release finalize manifest must be a mapping"
    return value, None


def _default_verifier() -> Verifier:
    return v3_installer.ssh_ed25519_verifier(
        install_spec_signature_guard._ssh_keygen_verify_runner,
        namespace=SSH_SIG_NAMESPACE,
    )


def _validate_evidence(
    repo_root: Path,
    evidence_path: Path,
    *,
    verifier: Verifier | None,
) -> list[ValidationError]:
    try:
        raw = evidence_path.read_bytes()
        record = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [_error(evidence_path, "", f"evidence must be canonical JSON: {exc}")]
    if not isinstance(record, dict):
        return [_error(evidence_path, "", "evidence must be a JSON object")]
    canonical_json = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if raw != canonical_json:
        return [_error(evidence_path, "", "evidence must be exactly canonical JSON (sorted keys, compact ASCII)")]

    errors: list[ValidationError] = []
    if set(record) != {
        "schema_version",
        "canonical_spec_sha256",
        "signed_spec_sha256",
        "summary",
        "stages",
        "containment",
        "container_image",
        "signature",
    }:
        errors.append(_error(evidence_path, "", "evidence must contain exactly the release smoke schema fields"))
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(_error(evidence_path, "schema_version", f"must be {SCHEMA_VERSION!r}"))

    spec_path = repo_root / INSTALL_SPEC
    try:
        spec = spec_path.read_bytes()
    except OSError as exc:
        return [_error(spec_path, "", f"could not read checked-out signed install spec: {exc}")]
    actual_canonical = hashlib.sha256(v3_installer.canonical_spec_bytes(spec)).hexdigest()
    actual_signed = hashlib.sha256(spec).hexdigest()
    for field, expected in (("canonical_spec_sha256", actual_canonical), ("signed_spec_sha256", actual_signed)):
        value = _string(record, field)
        if value is None or not HEX64_RE.fullmatch(value) or value != expected:
            errors.append(_error(evidence_path, field, f"must match the checked-out signed install spec ({expected})"))

    manifest, manifest_error = _read_manifest(repo_root / FINALIZE_MANIFEST)
    if manifest_error:
        errors.append(_error(FINALIZE_MANIFEST, "", manifest_error))
    else:
        assert manifest is not None
        for field, expected in (("canonical_spec_sha256", actual_canonical), ("signed_spec_sha256", actual_signed)):
            if _string(manifest, field) != expected:
                errors.append(_error(FINALIZE_MANIFEST, field, f"must match the checked-out signed install spec ({expected})"))

    summary = record.get("summary")
    if not _exact_keys(summary, {"failed", "stubbed"}) or summary.get("failed") != 0 or summary.get("stubbed") != 0:
        errors.append(_error(evidence_path, "summary", "must report exactly zero failed and zero stubbed"))
    stages = record.get("stages")
    if not _exact_keys(stages, {"install", "install_verify"}) or stages.get("install") != "passed" or stages.get("install_verify") != "passed":
        errors.append(_error(evidence_path, "stages", "install and install_verify must both be passed"))
    containment = record.get("containment")
    if not _exact_keys(containment, {"host_checkout_mount"}) or containment.get("host_checkout_mount") is not False:
        errors.append(_error(evidence_path, "containment.host_checkout_mount", "must be false"))
    image = _string(record, "container_image")
    if image is None or not IMAGE_RE.fullmatch(image):
        errors.append(_error(evidence_path, "container_image", "must be a digest-pinned image reference"))

    signature = record.get("signature")
    if not _exact_keys(signature, {"key_id", "algo", "namespace", "value"}):
        return errors + [_error(evidence_path, "signature", "must be an SSHSIG object")]
    key_id = _string(signature, "key_id")
    algo = _string(signature, "algo")
    namespace = _string(signature, "namespace")
    value = _string(signature, "value")
    if key_id not in v3_installer.PINNED_KEYS:
        errors.append(_error(evidence_path, "signature.key_id", "must name an existing pinned trust-root key"))
    if algo != v3_installer.SSH_ED25519_ALGO:
        errors.append(_error(evidence_path, "signature.algo", "must be ssh-ed25519"))
    if namespace != SSH_SIG_NAMESPACE:
        errors.append(_error(evidence_path, "signature.namespace", f"must be {SSH_SIG_NAMESPACE!r}"))
    if value is None:
        errors.append(_error(evidence_path, "signature.value", "must be a base64 detached SSHSIG"))
    else:
        try:
            base64.b64decode(value.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error, ValueError):
            errors.append(_error(evidence_path, "signature.value", "must be valid base64"))
    if not errors:
        verify = verifier or _default_verifier()
        if not verify(algo, _canonical_record_bytes(record), value, v3_installer.PINNED_KEYS[key_id]):
            errors.append(_error(evidence_path, "signature", "detached SSHSIG did not verify in ce-release-smoke-v1 namespace"))
    return errors


def run_with_base(paths: Iterable[Path], base: str, *, verifier: Verifier | None = None) -> CheckResult:
    raw_paths = [Path(path) for path in paths] or [Path(".")]
    repo_root = repo_root_for(raw_paths[0])
    changed, error = _changed_paths(repo_root, base)
    if error is not None:
        return CheckResult(name=CHECK_NAME, errors=(error,))
    assert changed is not None
    if not {INSTALL_SPEC.as_posix(), FINALIZE_MANIFEST.as_posix()}.issubset(changed):
        return CheckResult(name=CHECK_NAME)

    evidence_paths = sorted((repo_root / EVIDENCE_DIR).glob("*.json")) if (repo_root / EVIDENCE_DIR).is_dir() else []
    if len(evidence_paths) != 1:
        return CheckResult(
            name=CHECK_NAME,
            errors=(_error(EVIDENCE_DIR, "", "release-class PR requires exactly one canonical JSON smoke-evidence record"),),
        )
    return CheckResult(name=CHECK_NAME, errors=tuple(_validate_evidence(repo_root, evidence_paths[0], verifier=verifier)))
