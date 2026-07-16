"""Pure/local producer for signed release smoke-evidence records.

The smoke run and Operator signature are deliberately out of band.  This
module validates their public outputs, renders the exact bytes to sign, verifies
the returned detached SSHSIG against the pinned public trust root, and writes
only the explicitly requested evidence/carrier files.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import shlex
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from . import carrier_gen
from .checks import install_spec_signature_guard
from .checks.path_manifest_fidelity import _normalize_manifest


SCHEMA_VERSION = "1"
SSH_SIG_NAMESPACE = "ce-release-smoke-v1"
SIGNING_KEY_ID = "ce-root-v1"
SSH_ALGO = "ssh-ed25519"
FINALIZE_MANIFEST = Path("docs/release-finalize-manifest.yml")
INSTALL_SPEC = Path("docs/llms-install.md")
IMAGE_RE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
PACKAGE_VERSION_RE = re.compile(r"^  package_version: (\S+)$")
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
RESULT_FIELDS = {
    "schema_version",
    "container_image",
    "containment",
    "installation",
    "release_binding",
    "summary",
    "stages",
}
RESULT_BINDING_ORDER = (
    "package_version",
    "canonical_spec_sha256",
    "signed_spec_sha256",
    "finalize_manifest_sha256",
    "artifacts_sha256",
)
RESULT_BINDING_FIELDS = set(RESULT_BINDING_ORDER)
INSTALLATION_FIELDS = {
    "ce_version",
    "cev3_version",
    "verified_spec_sha256",
    "pre_signed_spec_sha256",
    "post_signed_spec_sha256",
    "pre_finalize_manifest_sha256",
    "post_finalize_manifest_sha256",
}
UNSIGNED_FIELDS = {
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
}
ROOT_ARTIFACT_PATHS = {
    "SIGNING-INSTRUCTIONS.md",
    "install.sh",
    "llms-install.canonical",
    "llms-install.md",
    "release-stage-manifest.yml",
    "keys/ce-root-v1",
    "schemas/install-answers.schema.yaml",
}

Verifier = Callable[[str, bytes, Any, Any], bool]


class ReleaseSmokeEvidenceError(ValueError):
    """A producer input failed a fail-closed release-smoke contract."""


@dataclass(frozen=True)
class ReleaseTreeBinding:
    package_version: str
    canonical_spec_sha256: str
    signed_spec_sha256: str
    finalize_manifest_sha256: str
    artifacts_sha256: str


@dataclass(frozen=True)
class PreparedEvidence:
    record: dict[str, object]
    canonical_bytes: bytes
    signing_command: str
    package_version: str
    manifest_sha256: str


@dataclass(frozen=True)
class FinalizedEvidence:
    record: dict[str, object]
    evidence_path: Path
    carrier_path: Path


def _canonical_json(value: Mapping[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _exact_mapping(value: object, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _signed_spec_package_version(spec: bytes) -> str:
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
    raise ReleaseSmokeEvidenceError("signed install spec artifact_manifest is missing package_version")


def _load_json_canonical(path: Path, *, label: str) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseSmokeEvidenceError(f"{label} is not readable JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseSmokeEvidenceError(f"{label} must be a JSON object")
    if raw != _canonical_json(value):
        raise ReleaseSmokeEvidenceError(f"{label} must be exact canonical compact ASCII JSON")
    return value


def _validate_result(value: dict[str, object]) -> None:
    if set(value) != RESULT_FIELDS:
        raise ReleaseSmokeEvidenceError(
            "smoke result must contain exactly the endpoint-observed result fields, including installation"
        )
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseSmokeEvidenceError("smoke result schema_version must be '1'")
    image = value.get("container_image")
    if not isinstance(image, str) or not IMAGE_RE.fullmatch(image):
        raise ReleaseSmokeEvidenceError("smoke result container_image must be digest-pinned")
    containment = value.get("containment")
    if not _exact_mapping(containment, {"host_checkout_mount"}) or containment.get("host_checkout_mount") is not False:
        raise ReleaseSmokeEvidenceError("smoke result host_checkout_mount must be false")
    summary = value.get("summary")
    if not _exact_mapping(summary, {"failed", "stubbed"}) or summary != {"failed": 0, "stubbed": 0}:
        raise ReleaseSmokeEvidenceError("smoke result failed and stubbed counts must both be zero")
    stages = value.get("stages")
    expected_stages = {"install": "passed", "install_verify": "passed"}
    if not _exact_mapping(stages, set(expected_stages)) or stages != expected_stages:
        raise ReleaseSmokeEvidenceError("smoke result install and install_verify must both be passed")
    release_binding = value.get("release_binding")
    if not _exact_mapping(release_binding, RESULT_BINDING_FIELDS):
        raise ReleaseSmokeEvidenceError("smoke result release_binding must contain exactly the observed release fields")
    assert isinstance(release_binding, dict)
    package_version = release_binding.get("package_version")
    if not isinstance(package_version, str) or not package_version or any(character.isspace() for character in package_version):
        raise ReleaseSmokeEvidenceError("smoke result release_binding.package_version is invalid")
    for field in RESULT_BINDING_FIELDS - {"package_version"}:
        digest = release_binding.get(field)
        if not isinstance(digest, str) or not HEX64_RE.fullmatch(digest):
            raise ReleaseSmokeEvidenceError(f"smoke result release_binding.{field} must be a lowercase SHA-256 digest")
    installation = value.get("installation")
    if not _exact_mapping(installation, INSTALLATION_FIELDS):
        raise ReleaseSmokeEvidenceError("smoke result installation must contain exactly the installed/pre/post observation fields")
    assert isinstance(installation, dict)
    version_pattern = re.compile(rf"^{re.escape(package_version)}\+[0-9a-f]{{8}}$")
    for field in ("ce_version", "cev3_version"):
        installed_version = installation.get(field)
        if not isinstance(installed_version, str) or not version_pattern.fullmatch(installed_version):
            raise ReleaseSmokeEvidenceError(
                f"smoke result installation.{field} must identify finalized package version {package_version}"
            )
    expected_observations = {
        "verified_spec_sha256": ("signed_spec_sha256", release_binding["signed_spec_sha256"]),
        "pre_signed_spec_sha256": ("signed_spec_sha256", release_binding["signed_spec_sha256"]),
        "post_signed_spec_sha256": ("signed_spec_sha256", release_binding["signed_spec_sha256"]),
        "pre_finalize_manifest_sha256": ("finalize_manifest_sha256", release_binding["finalize_manifest_sha256"]),
        "post_finalize_manifest_sha256": ("finalize_manifest_sha256", release_binding["finalize_manifest_sha256"]),
    }
    for field, (binding_field, expected) in expected_observations.items():
        observed = installation.get(field)
        if not isinstance(observed, str) or not HEX64_RE.fullmatch(observed) or observed != expected:
            raise ReleaseSmokeEvidenceError(
                f"smoke result installation.{field} must match release_binding.{binding_field}"
            )


def _validate_observed_binding(result: dict[str, object], binding: ReleaseTreeBinding) -> None:
    observed = result["release_binding"]
    assert isinstance(observed, dict)
    for field in RESULT_BINDING_ORDER:
        expected = getattr(binding, field)
        if observed.get(field) != expected:
            raise ReleaseSmokeEvidenceError(
                f"smoke result release_binding.{field} does not match the exact finalized release tree"
            )


def _manifest_artifact_path(docs: Path, relative: str, package_version: str) -> Path:
    rel = Path(relative)
    if not relative or rel.is_absolute() or ".." in rel.parts or rel.as_posix() != relative:
        raise ReleaseSmokeEvidenceError(f"manifest artifact path must be a normalized relative path; escape refused: {relative!r}")
    allowed_download = relative.startswith(f"downloads/{package_version}/")
    if relative not in ROOT_ARTIFACT_PATHS and not allowed_download:
        raise ReleaseSmokeEvidenceError(f"manifest artifact path is outside finalized release content: {relative!r}")
    path = docs / rel
    try:
        path.resolve(strict=False).relative_to(docs.resolve())
    except ValueError as exc:
        raise ReleaseSmokeEvidenceError(f"manifest artifact path escapes docs: {relative!r}") from exc
    return path


def validate_release_tree(repo_root: Path | str) -> ReleaseTreeBinding:
    """Validate the finalized manifest, signed spec, and every owned artifact."""

    root = Path(repo_root).resolve()
    docs = root / "docs"
    manifest_path = root / FINALIZE_MANIFEST
    spec_path = root / INSTALL_SPEC
    try:
        manifest_raw = manifest_path.read_bytes()
        manifest = yaml.safe_load(manifest_raw.decode("utf-8"))
        spec = spec_path.read_bytes()
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ReleaseSmokeEvidenceError(f"could not read finalized release tree: {exc}") from exc
    if not isinstance(manifest, dict) or set(manifest) != FINALIZE_MANIFEST_FIELDS:
        raise ReleaseSmokeEvidenceError("release finalize manifest must contain exactly the finalized contract fields")
    if manifest.get("kind") != "ce-release-finalize-manifest" or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseSmokeEvidenceError("release finalize manifest kind/schema_version is invalid")

    package_version = _signed_spec_package_version(spec)
    if manifest.get("package_version") != package_version:
        raise ReleaseSmokeEvidenceError("release finalize manifest package_version does not match signed install spec")
    canonical_sha = hashlib.sha256(install_spec_signature_guard.canonical_spec_bytes(spec)).hexdigest()
    signed_sha = hashlib.sha256(spec).hexdigest()
    if manifest.get("canonical_spec_sha256") != canonical_sha:
        raise ReleaseSmokeEvidenceError("release finalize manifest canonical_spec_sha256 does not match signed install spec")
    if manifest.get("signed_spec_sha256") != signed_sha:
        raise ReleaseSmokeEvidenceError("release finalize manifest signed_spec_sha256 does not match signed install spec")

    try:
        spec_signature = install_spec_signature_guard.parse_embedded_signature_block(spec)
    except ValueError as exc:
        raise ReleaseSmokeEvidenceError(f"signed install spec signature is invalid: {exc}") from exc
    expected_signature_sha = hashlib.sha256(spec_signature["value"].encode("ascii")).hexdigest()
    for field, expected in (
        ("signature_sha256", expected_signature_sha),
        ("signing_key_id", spec_signature["key_id"]),
        ("signing_namespace", spec_signature["namespace"]),
    ):
        if manifest.get(field) != expected:
            raise ReleaseSmokeEvidenceError(f"release finalize manifest {field} does not match signed install spec")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ReleaseSmokeEvidenceError("release finalize manifest artifacts must be non-empty")
    declared_paths: set[str] = set()
    for index, item in enumerate(artifacts):
        if not _exact_mapping(item, FINALIZE_ARTIFACT_FIELDS):
            raise ReleaseSmokeEvidenceError(f"manifest artifacts[{index}] must contain exactly path, sha256, and size")
        assert isinstance(item, dict)
        relative = item.get("path")
        digest = item.get("sha256")
        size = item.get("size")
        if not isinstance(relative, str):
            raise ReleaseSmokeEvidenceError(f"manifest artifacts[{index}].path must be a string")
        if relative in declared_paths:
            raise ReleaseSmokeEvidenceError(f"manifest artifact path is duplicated: {relative}")
        declared_paths.add(relative)
        if not isinstance(digest, str) or not HEX64_RE.fullmatch(digest):
            raise ReleaseSmokeEvidenceError(f"manifest artifact {relative!r} sha256 is invalid")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ReleaseSmokeEvidenceError(f"manifest artifact {relative!r} size is invalid")
        artifact_path = _manifest_artifact_path(docs, relative, package_version)
        if not artifact_path.is_file() or artifact_path.is_symlink():
            raise ReleaseSmokeEvidenceError(f"manifest artifact is missing or not a regular file: {relative}")
        raw = artifact_path.read_bytes()
        if len(raw) != size:
            raise ReleaseSmokeEvidenceError(f"manifest artifact size drifted: {relative}")
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ReleaseSmokeEvidenceError(f"manifest artifact sha256 drifted: {relative}")

    managed_actual = {relative for relative in ROOT_ARTIFACT_PATHS if (docs / relative).is_file()}
    downloads = docs / "downloads" / package_version
    if downloads.is_dir():
        managed_actual.update(
            path.relative_to(docs).as_posix()
            for path in downloads.rglob("*")
            if path.is_file()
        )
    extras = sorted(managed_actual - declared_paths)
    missing_declarations = sorted(declared_paths - managed_actual)
    if extras:
        raise ReleaseSmokeEvidenceError("finalized release tree contains extra artifact(s): " + ", ".join(extras))
    if missing_declarations:
        raise ReleaseSmokeEvidenceError("release finalize manifest names missing artifact(s): " + ", ".join(missing_declarations))

    return ReleaseTreeBinding(
        package_version=package_version,
        canonical_spec_sha256=canonical_sha,
        signed_spec_sha256=signed_sha,
        finalize_manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
        artifacts_sha256=_artifact_section_sha256(manifest_raw),
    )


def _artifact_section_sha256(manifest_raw: bytes) -> str:
    marker = b"artifacts:\n"
    position = manifest_raw.find(marker)
    if position < 0:
        raise ReleaseSmokeEvidenceError("release finalize manifest is missing its canonical artifacts section")
    return hashlib.sha256(manifest_raw[position:]).hexdigest()


def _unsigned_record(binding: ReleaseTreeBinding, result: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "package_version": binding.package_version,
        "canonical_spec_sha256": binding.canonical_spec_sha256,
        "signed_spec_sha256": binding.signed_spec_sha256,
        "finalize_manifest_sha256": binding.finalize_manifest_sha256,
        "artifacts_sha256": binding.artifacts_sha256,
        "summary": result["summary"],
        "stages": result["stages"],
        "containment": result["containment"],
        "container_image": result["container_image"],
        "installation": result["installation"],
        "signature": {"key_id": SIGNING_KEY_ID, "algo": SSH_ALGO, "namespace": SSH_SIG_NAMESPACE},
    }


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def prepare_evidence(
    repo_root: Path | str,
    result_path: Path | str,
    unsigned_out: Path | str,
) -> PreparedEvidence:
    """Validate public worker output and atomically emit the exact bytes to sign."""

    binding = validate_release_tree(repo_root)
    result = _load_json_canonical(Path(result_path), label="release smoke result")
    _validate_result(result)
    _validate_observed_binding(result, binding)
    record = _unsigned_record(binding, result)
    canonical = _canonical_json(record)
    output = Path(unsigned_out)
    _atomic_write(output, canonical)
    signing_command = (
        "ssh-keygen -Y sign -f /path/to/ce-root-v1-private "
        f"-n {SSH_SIG_NAMESPACE} {shlex.quote(str(output))}"
    )
    return PreparedEvidence(
        record=record,
        canonical_bytes=canonical,
        signing_command=signing_command,
        package_version=binding.package_version,
        manifest_sha256=binding.finalize_manifest_sha256,
    )


def _validate_unsigned(repo_root: Path, unsigned_path: Path) -> tuple[dict[str, object], bytes, ReleaseTreeBinding]:
    record = _load_json_canonical(unsigned_path, label="unsigned release smoke evidence")
    if set(record) != UNSIGNED_FIELDS:
        raise ReleaseSmokeEvidenceError("unsigned release smoke evidence has unexpected fields")
    synthetic_result = {
        field: record[field]
        for field in RESULT_FIELDS - {"release_binding"}
    }
    synthetic_result["release_binding"] = {field: record[field] for field in RESULT_BINDING_FIELDS}
    _validate_result(synthetic_result)
    signature = record.get("signature")
    expected_signature = {"key_id": SIGNING_KEY_ID, "algo": SSH_ALGO, "namespace": SSH_SIG_NAMESPACE}
    if signature != expected_signature:
        raise ReleaseSmokeEvidenceError("unsigned signature descriptor must bind ce-root-v1 and ce-release-smoke-v1")
    binding = validate_release_tree(repo_root)
    _validate_observed_binding(synthetic_result, binding)
    for field, expected in (
        ("package_version", binding.package_version),
        ("canonical_spec_sha256", binding.canonical_spec_sha256),
        ("signed_spec_sha256", binding.signed_spec_sha256),
        ("finalize_manifest_sha256", binding.finalize_manifest_sha256),
        ("artifacts_sha256", binding.artifacts_sha256),
    ):
        if record.get(field) != expected:
            raise ReleaseSmokeEvidenceError(f"unsigned release smoke evidence {field} does not match finalized tree")
    return record, _canonical_json(record), binding


def _default_verifier(algo: str, message: bytes, value: Any, key_material: Any) -> bool:
    if algo != SSH_ALGO or not isinstance(value, str) or not isinstance(key_material, str):
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
                message=message,
                signature=signature,
                allowed_signers=key_material,
                identity=fields[0].split(",")[0],
                namespace=SSH_SIG_NAMESPACE,
            )
        )
    except Exception:
        return False


def _render_refreshed_carrier(
    repo_root: Path,
    carrier_path: Path,
    evidence_path: Path,
    *,
    base: str,
) -> bytes:
    try:
        current = carrier_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseSmokeEvidenceError(f"could not read requested carrier: {exc}") from exc
    header = re.match(r"^# PR path manifest — (.+?) · (.+)$", current.splitlines()[0])
    if header is None:
        raise ReleaseSmokeEvidenceError("requested carrier header is invalid")
    work_class = re.search(r"Declared work class:\*\*\s*:?\s*`?([A-Za-z][A-Za-z0-9_-]*)`?", current)
    if work_class is None:
        raise ReleaseSmokeEvidenceError("requested carrier is missing declared work class")
    slug = carrier_path.stem
    try:
        paths, _count, _digest = carrier_gen.compute_path_set(repo_root, slug, base)
    except RuntimeError as exc:
        raise ReleaseSmokeEvidenceError(str(exc)) from exc
    evidence_relative = evidence_path.relative_to(repo_root).as_posix()
    canonical_paths = [*paths, evidence_relative]
    count, digest, _errors = _normalize_manifest(canonical_paths)
    rendered = carrier_gen.render_manifest(
        slug,
        header.group(1),
        header.group(2),
        canonical_paths,
        count,
        digest,
        declared_work_class=work_class.group(1),
    )
    return rendered.encode("utf-8")


def finalize_evidence(
    repo_root: Path | str,
    unsigned_path: Path | str,
    signature_base64: str,
    evidence_out: Path | str,
    carrier_path: Path | str,
    base: str,
    *,
    verifier: Verifier | None = None,
    pinned_keys: Mapping[str, str] | None = None,
) -> FinalizedEvidence:
    """Verify a public detached SSHSIG and atomically write evidence/carrier."""

    root = Path(repo_root).resolve()
    unsigned = Path(unsigned_path)
    record, canonical, binding = _validate_unsigned(root, unsigned)
    signature = signature_base64.strip()
    try:
        base64.b64decode(signature.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise ReleaseSmokeEvidenceError("public detached signature must be valid base64") from exc
    keys = dict(pinned_keys or install_spec_signature_guard.PINNED_KEYS)
    if SIGNING_KEY_ID not in keys:
        raise ReleaseSmokeEvidenceError("pinned ce-root-v1 public key is unavailable")
    verify = verifier or _default_verifier
    if not verify(SSH_ALGO, canonical, signature, keys[SIGNING_KEY_ID]):
        raise ReleaseSmokeEvidenceError("public detached SSHSIG did not verify in ce-release-smoke-v1 namespace")

    evidence_path = Path(evidence_out).resolve()
    expected_evidence = (root / ".ce/release-evidence" / f"release-v{binding.package_version}.json").resolve()
    if evidence_path != expected_evidence:
        raise ReleaseSmokeEvidenceError(f"evidence output must be {expected_evidence}")
    carrier = Path(carrier_path).resolve()
    try:
        carrier.relative_to(root / ".ce/pr-manifests")
    except ValueError as exc:
        raise ReleaseSmokeEvidenceError("carrier output must be under .ce/pr-manifests") from exc

    final_record = dict(record)
    final_signature = dict(record["signature"])
    final_signature["value"] = signature
    final_record["signature"] = final_signature
    evidence_raw = _canonical_json(final_record)
    carrier_raw = _render_refreshed_carrier(root, carrier, evidence_path, base=base)
    _atomic_write(evidence_path, evidence_raw)
    _atomic_write(carrier, carrier_raw)
    return FinalizedEvidence(record=final_record, evidence_path=evidence_path, carrier_path=carrier)


__all__ = [
    "FinalizedEvidence",
    "PreparedEvidence",
    "ReleaseSmokeEvidenceError",
    "finalize_evidence",
    "prepare_evidence",
    "validate_release_tree",
]
