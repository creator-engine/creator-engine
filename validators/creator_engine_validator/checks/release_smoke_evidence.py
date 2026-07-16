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

from .. import release_smoke_evidence as producer
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
SIGNING_KEY_ID = "ce-root-v1"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
IMAGE_RE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
PACKAGE_VERSION_RE = re.compile(r"^  package_version: (\S+)$")
EVIDENCE_NAME_RE = re.compile(
    r"^release-v"
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-((?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\.json$"
)
FINALIZE_MANIFEST_FIELDS = {
    "kind",
    "schema_version",
    "package_version",
    "canonical_spec_sha256",
    "signed_spec_sha256",
    "signature_sha256",
    "signing_key_id",
    "signing_namespace",
    "artifacts",
}
FINALIZE_ARTIFACT_FIELDS = {"path", "sha256", "size"}
FINALIZE_MANIFEST_KIND = "ce-release-finalize-manifest"

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
    signature = unsigned.get("signature")
    if isinstance(signature, dict):
        public_descriptor = dict(signature)
        public_descriptor.pop("value", None)
        unsigned["signature"] = public_descriptor
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _string(mapping: dict[str, object], key: str) -> str | None:
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _exact_keys(value: object, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _semver_from_evidence_name(name: str) -> tuple[tuple[int, int, int], tuple[str, ...] | None] | None:
    match = EVIDENCE_NAME_RE.fullmatch(name)
    if match is None:
        return None
    prerelease = tuple(match.group(4).split(".")) if match.group(4) is not None else None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3))), prerelease


def _prerelease_lt(left: tuple[str, ...] | None, right: tuple[str, ...] | None) -> bool:
    if left is None:
        return False
    if right is None:
        return True
    for left_item, right_item in zip(left, right):
        if left_item == right_item:
            continue
        left_numeric = left_item.isdigit()
        right_numeric = right_item.isdigit()
        if left_numeric and right_numeric:
            return int(left_item) < int(right_item)
        if left_numeric != right_numeric:
            return left_numeric
        return left_item < right_item
    return len(left) < len(right)


def _semver_strictly_lower(
    candidate: tuple[tuple[int, int, int], tuple[str, ...] | None],
    current: tuple[tuple[int, int, int], tuple[str, ...] | None],
) -> bool:
    if candidate[0] != current[0]:
        return candidate[0] < current[0]
    return _prerelease_lt(candidate[1], current[1])


def _validate_historical_evidence(evidence_path: Path, filename_version: str) -> list[ValidationError]:
    """Validate historical record authenticity/shape without rebinding old hashes."""

    try:
        raw = evidence_path.read_bytes()
        record = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [_error(evidence_path, "", f"historical evidence must be canonical JSON: {exc}")]
    if not isinstance(record, dict):
        return [_error(evidence_path, "", "historical evidence must be a JSON object")]
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if raw != canonical:
        return [_error(evidence_path, "", "historical evidence must be exactly canonical compact ASCII JSON")]
    signature = record.get("signature")
    if not _exact_keys(signature, {"key_id", "algo", "namespace", "value"}):
        return [_error(evidence_path, "signature", "historical evidence must carry an exact SSHSIG descriptor")]
    assert isinstance(signature, dict)
    if (
        signature.get("key_id") != SIGNING_KEY_ID
        or signature.get("algo") != install_spec_signature_guard.SSH_ED25519_ALGO
        or signature.get("namespace") != SSH_SIG_NAMESPACE
    ):
        return [_error(evidence_path, "signature", "historical evidence must bind ce-root-v1/ce-release-smoke-v1")]
    signature_value = signature.get("value")
    try:
        if not isinstance(signature_value, str):
            raise ValueError("not a string")
        base64.b64decode(signature_value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError):
        return [_error(evidence_path, "signature.value", "historical evidence signature must be valid base64")]
    unsigned = dict(record)
    unsigned["signature"] = {key: signature[key] for key in ("key_id", "algo", "namespace")}
    if set(unsigned) != producer.UNSIGNED_FIELDS:
        return [_error(evidence_path, "", "historical evidence must contain exactly the release smoke schema fields")]
    synthetic_result = {field: unsigned[field] for field in producer.RESULT_FIELDS - {"release_binding"}}
    synthetic_result["release_binding"] = {
        field: unsigned[field] for field in producer.RESULT_BINDING_FIELDS
    }
    try:
        producer._validate_result(synthetic_result)
    except producer.ReleaseSmokeEvidenceError as exc:
        return [_error(evidence_path, "", f"historical evidence shape is invalid: {exc}")]
    if record.get("package_version") != filename_version:
        return [_error(evidence_path, "package_version", "historical evidence filename and record version must match exactly")]
    return []


def _read_manifest(path: Path) -> tuple[dict[str, object] | None, str | None]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, f"could not parse release finalize manifest: {exc}"
    if not isinstance(value, dict):
        return None, "release finalize manifest must be a mapping"
    return value, None


def _signed_spec_package_version(spec: bytes) -> str:
    """Read the producer's one artifact-manifest package version scalar."""
    in_artifact_manifest = False
    for line in spec.decode("utf-8").splitlines():
        if line.strip() == "artifact_manifest:":
            in_artifact_manifest = True
            continue
        if not in_artifact_manifest:
            continue
        match = PACKAGE_VERSION_RE.fullmatch(line)
        if match is not None:
            return match.group(1)
        if line.strip() and not line.startswith("  "):
            break
    raise ValueError("signed install spec artifact_manifest is missing package_version")


def _validate_finalize_manifest(
    manifest: dict[str, object],
    spec: bytes,
    *,
    canonical_spec_sha256: str,
    signed_spec_sha256: str,
) -> list[ValidationError]:
    """Validate every value emitted by the release-finalize producer.

    The manifest is part of the release binding, not merely a convenient place
    to repeat the two spec digests.  Require its complete, typed contract so a
    truncated mapping cannot turn a release-class diff into an accept.
    """
    errors: list[ValidationError] = []
    if set(manifest) != FINALIZE_MANIFEST_FIELDS:
        errors.append(_error(FINALIZE_MANIFEST, "", "must contain exactly the release finalize contract fields"))

    if manifest.get("kind") != FINALIZE_MANIFEST_KIND:
        errors.append(_error(FINALIZE_MANIFEST, "kind", f"must be {FINALIZE_MANIFEST_KIND!r}"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(_error(FINALIZE_MANIFEST, "schema_version", f"must be {SCHEMA_VERSION!r}"))
    for field, expected in (
        ("canonical_spec_sha256", canonical_spec_sha256),
        ("signed_spec_sha256", signed_spec_sha256),
    ):
        if _string(manifest, field) != expected:
            errors.append(_error(FINALIZE_MANIFEST, field, f"must match the checked-out signed install spec ({expected})"))

    try:
        signature = install_spec_signature_guard.parse_embedded_signature_block(spec)
        package_version = _signed_spec_package_version(spec)
        signature_sha256 = hashlib.sha256(signature["value"].encode("ascii")).hexdigest()
    except (UnicodeDecodeError, UnicodeEncodeError, ValueError) as exc:
        return errors + [_error(FINALIZE_MANIFEST, "", f"could not derive finalize bindings from signed install spec: {exc}")]

    for field, expected in (
        ("package_version", package_version),
        ("signature_sha256", signature_sha256),
        ("signing_key_id", signature["key_id"]),
        ("signing_namespace", signature["namespace"]),
    ):
        if _string(manifest, field) != expected:
            errors.append(_error(FINALIZE_MANIFEST, field, f"must match the checked-out signed install spec ({expected})"))

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append(_error(FINALIZE_MANIFEST, "artifacts", "must be a non-empty artifact set"))
    else:
        paths: set[str] = set()
        for index, artifact in enumerate(artifacts):
            field = f"artifacts[{index}]"
            if not _exact_keys(artifact, FINALIZE_ARTIFACT_FIELDS):
                errors.append(_error(FINALIZE_MANIFEST, field, "must contain exactly path, sha256, and size"))
                continue
            assert isinstance(artifact, dict)
            path = _string(artifact, "path")
            sha256 = _string(artifact, "sha256")
            size = artifact.get("size")
            if path is None or not path or path.startswith("/") or ".." in Path(path).parts:
                errors.append(_error(FINALIZE_MANIFEST, f"{field}.path", "must be a non-empty relative artifact path"))
            elif path in paths:
                errors.append(_error(FINALIZE_MANIFEST, f"{field}.path", "must not duplicate another artifact path"))
            else:
                paths.add(path)
            if sha256 is None or not HEX64_RE.fullmatch(sha256):
                errors.append(_error(FINALIZE_MANIFEST, f"{field}.sha256", "must be a lowercase SHA-256 digest"))
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                errors.append(_error(FINALIZE_MANIFEST, f"{field}.size", "must be a non-negative integer"))
    return errors


def _default_verifier() -> Verifier:
    def _verify(algo: str, raw: bytes, value: Any, key_material: Any) -> bool:
        if algo != install_spec_signature_guard.SSH_ED25519_ALGO:
            return False
        if not isinstance(value, str) or not isinstance(key_material, str):
            return False
        try:
            signature = base64.b64decode(value.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error, ValueError):
            return False
        fields = key_material.split()
        if len(fields) < 3:
            return False
        try:
            return bool(
                install_spec_signature_guard._ssh_keygen_verify_runner(
                    message=raw,
                    signature=signature,
                    allowed_signers=key_material,
                    identity=fields[0].split(",")[0],
                    namespace=SSH_SIG_NAMESPACE,
                )
            )
        except Exception:
            return False

    return _verify


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
        "package_version",
        "canonical_spec_sha256",
        "signed_spec_sha256",
        "finalize_manifest_sha256",
        "artifacts_sha256",
        "summary",
        "stages",
        "containment",
        "container_image",
        "installation",
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
    actual_canonical = hashlib.sha256(install_spec_signature_guard.canonical_spec_bytes(spec)).hexdigest()
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
        errors.extend(
            _validate_finalize_manifest(
                manifest,
                spec,
                canonical_spec_sha256=actual_canonical,
                signed_spec_sha256=actual_signed,
            )
        )
    try:
        tree_binding = producer.validate_release_tree(repo_root)
    except producer.ReleaseSmokeEvidenceError as exc:
        errors.append(_error(FINALIZE_MANIFEST, "artifacts", str(exc)))
    else:
        for field, expected in (
            ("package_version", tree_binding.package_version),
            ("artifacts_sha256", tree_binding.artifacts_sha256),
        ):
            value = _string(record, field)
            if value != expected:
                errors.append(_error(evidence_path, field, f"must match the exact checked-out finalized release tree ({expected})"))
        manifest_digest = _string(record, "finalize_manifest_sha256")
        if manifest_digest != tree_binding.finalize_manifest_sha256:
            errors.append(
                _error(
                    evidence_path,
                    "finalize_manifest_sha256",
                    "must match the exact checked-out release finalize manifest "
                    f"({tree_binding.finalize_manifest_sha256})",
                )
            )

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
    installation = record.get("installation")
    synthetic_result = {
        "schema_version": record.get("schema_version"),
        "container_image": record.get("container_image"),
        "containment": record.get("containment"),
        "installation": installation,
        "release_binding": {field: record.get(field) for field in producer.RESULT_BINDING_FIELDS},
        "summary": record.get("summary"),
        "stages": record.get("stages"),
    }
    try:
        producer._validate_result(synthetic_result)
    except producer.ReleaseSmokeEvidenceError as exc:
        errors.append(_error(evidence_path, "installation", str(exc)))

    signature = record.get("signature")
    if not _exact_keys(signature, {"key_id", "algo", "namespace", "value"}):
        return errors + [_error(evidence_path, "signature", "must be an SSHSIG object")]
    key_id = _string(signature, "key_id")
    algo = _string(signature, "algo")
    namespace = _string(signature, "namespace")
    value = _string(signature, "value")
    if key_id != SIGNING_KEY_ID:
        errors.append(_error(evidence_path, "signature.key_id", f"must be {SIGNING_KEY_ID!r}"))
    if algo != install_spec_signature_guard.SSH_ED25519_ALGO:
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
        if not verify(algo, _canonical_record_bytes(record), value, install_spec_signature_guard.PINNED_KEYS[SIGNING_KEY_ID]):
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

    try:
        binding = producer.validate_release_tree(repo_root)
    except producer.ReleaseSmokeEvidenceError as exc:
        return CheckResult(name=CHECK_NAME, errors=(_error(FINALIZE_MANIFEST, "", str(exc)),))
    expected_relative = (EVIDENCE_DIR / f"release-v{binding.package_version}.json").as_posix()
    changed_evidence = sorted(path for path in changed if path.startswith(f"{EVIDENCE_DIR.as_posix()}/"))
    if changed_evidence != [expected_relative]:
        return CheckResult(
            name=CHECK_NAME,
            errors=(
                _error(
                    EVIDENCE_DIR,
                    "",
                    "release-class PR must newly change exactly its version-derived canonical smoke-evidence record "
                    f"({expected_relative}); changed evidence: {changed_evidence}",
                ),
            ),
        )
    evidence_path = repo_root / expected_relative
    if not evidence_path.is_file():
        return CheckResult(name=CHECK_NAME, errors=(_error(evidence_path, "", "expected smoke-evidence record is missing"),))
    current_name = f"release-v{binding.package_version}.json"
    current_semver = _semver_from_evidence_name(current_name)
    if current_semver is None:
        return CheckResult(
            name=CHECK_NAME,
            errors=(_error(FINALIZE_MANIFEST, "package_version", "package version is not canonical semantic version"),),
        )
    evidence_dir = repo_root / EVIDENCE_DIR
    try:
        entries = sorted(evidence_dir.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        return CheckResult(name=CHECK_NAME, errors=(_error(EVIDENCE_DIR, "", f"could not enumerate evidence: {exc}"),))
    historical_errors: list[ValidationError] = []
    for entry in entries:
        if entry.name == current_name:
            continue
        candidate_semver = _semver_from_evidence_name(entry.name)
        if entry.is_symlink() or not entry.is_file() or candidate_semver is None:
            historical_errors.append(
                _error(entry, "", "unchanged evidence entries must be canonical release-v<semantic-version>.json regular files")
            )
            continue
        if not _semver_strictly_lower(candidate_semver, current_semver):
            historical_errors.append(
                _error(entry, "", "unchanged evidence version must be strictly lower than the current finalized version")
            )
            continue
        filename_version = entry.name[len("release-v") : -len(".json")]
        historical_errors.extend(_validate_historical_evidence(entry, filename_version))
    if historical_errors:
        return CheckResult(name=CHECK_NAME, errors=tuple(historical_errors))
    return CheckResult(name=CHECK_NAME, errors=tuple(_validate_evidence(repo_root, evidence_path, verifier=verifier)))
