"""Signed in-place CE update runtime.

The update path mirrors ``docs/install.sh``: fetch the signed install spec and
trust root, bind the root to an out-of-band ``_ce-root-v1`` fingerprint anchor,
verify the SSHSIG, verify ``SHA256SUMS`` and selected wheel artifacts, then
atomically promote a verified venv target. Tests inject the fetch/signature/swap
seams; the production defaults are the live mirror and stock ``ssh-keygen``.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urljoin
from urllib.request import urlopen as _stdlib_urlopen

from . import _version, ce_provenance, install_prereqs
from .bootstrap_manifest import (
    BootstrapManifest,
    BootstrapManifestError,
    BootstrapWheel,
    parse_bootstrap_manifest,
    parse_sha256s,
)

DEFAULT_SITE = "https://creator-engine.dev"
DEFAULT_TRUST_ANCHOR_URL = (
    "https://dns.google/resolve?name=_ce-root-v1.creator-engine.dev&type=TXT"
)
DEFAULT_TRUST_ANCHOR_SOURCE = "dns-txt:_ce-root-v1.creator-engine.dev"
SSH_SIG_NAMESPACE = "ce-spec-v1"
SSH_ED25519_ALGO = "ssh-ed25519"
SIGNATURE_PLACEHOLDER = "<published-with-this-spec>"
PUBLISHED_INSTALL_SPEC_URL = "https://creator-engine.dev/llms-install.md"
STARTUP_UPDATE_CACHE_TTL_SECONDS = 6 * 60 * 60
STARTUP_UPDATE_FETCH_TIMEOUT_SECONDS = 0.75
STARTUP_UPDATE_CACHE_ENV = "CE_UPDATE_CHECK_CACHE"
STARTUP_UPDATE_DISABLE_ENV = "CE_UPDATE_CHECK"
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_OPENSSH_SHA256_FINGERPRINT_RE = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")

UrlFetcher = Callable[[str], bytes]
SshsigRunner = Callable[..., bool]


class UpdateRefused(Exception):
    """Fail-closed update refusal."""


@dataclass(frozen=True)
class SignedInstallSpec:
    signature: dict[str, Any]
    content_sha256: str
    canonical_sha256: str


@dataclass(frozen=True)
class TrustAnchorRecord:
    source: str
    key_id: str
    fingerprint: str


@dataclass(frozen=True)
class TrustAnchorEvidence:
    ok: bool
    status: str
    reason: str
    agreed: tuple[str, ...] = ()
    mismatched: tuple[str, ...] = ()

    def to_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "reason": self.reason,
            "agreed": list(self.agreed),
            "mismatched": list(self.mismatched),
        }


@dataclass(frozen=True)
class InstalledIdentity:
    semver: str
    build_git_sha: str

    @property
    def token(self) -> str:
        return f"{self.semver}+{self.build_git_sha[:12]}"


@dataclass(frozen=True)
class ReleaseIdentity:
    semver: str
    build_git_sha: str
    app_wheel: str
    app_wheel_sha256: str

    @property
    def token(self) -> str:
        return f"{self.semver}+{self.build_git_sha[:12]}"


@dataclass(frozen=True)
class VerifiedRelease:
    identity: ReleaseIdentity
    manifest: BootstrapManifest
    spec_bytes: bytes
    canonical_spec_sha256: str
    trust_root_sha256: str
    trust_anchor_sha256: str
    sha256s_text: str
    sha256s_sha256: str
    platform_tag: str
    wheelhouse: Mapping[str, bytes]
    trust_anchor: Mapping[str, Any]
    artifact_verification: Mapping[str, Any]


@dataclass(frozen=True)
class UpdateResult:
    ok: bool
    status: str
    reason: str
    installed: InstalledIdentity
    available: ReleaseIdentity | None = None
    update_available: bool = False
    read_only: bool = False
    install_root: str | None = None
    actions: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()
    release: Mapping[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "status": self.status,
            "reason": self.reason,
            "read_only": self.read_only,
            "update_available": self.update_available,
            "installed": {
                "semver": self.installed.semver,
                "build_git_sha": self.installed.build_git_sha,
                "token": self.installed.token,
            },
            "available": None,
            "install_root": self.install_root,
            "actions": list(self.actions),
            "problems": list(self.problems),
            "release": dict(self.release),
        }
        if self.available is not None:
            payload["available"] = {
                "semver": self.available.semver,
                "build_git_sha": self.available.build_git_sha,
                "token": self.available.token,
                "app_wheel": self.available.app_wheel,
                "app_wheel_sha256": self.available.app_wheel_sha256,
            }
        return payload


@dataclass(frozen=True)
class SpecOnlyRelease:
    semver: str
    app_wheel: str
    app_wheel_sha256: str
    canonical_spec_sha256: str
    trust_root_sha256: str
    trust_anchor_sha256: str
    trust_anchor: Mapping[str, Any]


@dataclass(frozen=True)
class StartupUpdateCheck:
    update_available: bool
    available_semver: str | None = None
    reason: str = "no update"
    from_cache: bool = False
    notice_due: bool = False
    cache_path: Path | None = None


def installed_identity() -> InstalledIdentity:
    return InstalledIdentity(
        semver=str(_version.SEMVER),
        build_git_sha=str(_version.BUILD_GIT_SHA),
    )


def default_fetcher(url: str, *, timeout: float | None = None) -> bytes:
    with _stdlib_urlopen(url, timeout=timeout) as response:
        return response.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_spec_bytes(spec_bytes: bytes | str) -> bytes:
    raw = spec_bytes.encode("utf-8") if isinstance(spec_bytes, str) else spec_bytes
    text = raw.decode("utf-8")
    for field_name in ("value", "content_sha256"):
        text = re.sub(
            rf"(?m)^(  {field_name}: ).*$",
            rf"\g<1>{SIGNATURE_PLACEHOLDER}",
            text,
        )
    return text.encode("utf-8")


def _parse_allowed_signers(text: str) -> dict[str, str]:
    pinned: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) >= 3:
            pinned[fields[0].split(",")[0]] = line
    return pinned


def _public_key_fingerprint(key_material: str) -> str:
    fields = key_material.split()
    if len(fields) < 3:
        raise UpdateRefused("trust_anchor_refused: key material is not OpenSSH public key material")
    try:
        raw_key = base64.b64decode(fields[2].encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise UpdateRefused(f"trust_anchor_refused: malformed OpenSSH public key: {exc}") from exc
    return "SHA256:" + base64.b64encode(hashlib.sha256(raw_key).digest()).decode("ascii").rstrip("=")


def _parse_embedded_signature_block(spec_bytes: bytes | str) -> dict[str, str]:
    text = spec_bytes.decode("utf-8") if isinstance(spec_bytes, bytes) else spec_bytes
    fields: dict[str, str] = {}
    in_signature = False
    for raw_line in text.splitlines():
        if raw_line.strip() == "signature:":
            in_signature = True
            continue
        if not in_signature:
            continue
        if raw_line.startswith("  "):
            key, sep, value = raw_line.strip().partition(":")
            if sep:
                fields[key] = value.strip()
            continue
        if raw_line.strip():
            break
    missing = sorted({"key_id", "algo", "namespace", "value", "content_sha256"} - fields.keys())
    if missing:
        raise UpdateRefused("signature_refused: missing " + ", ".join(missing))
    if fields["algo"] != SSH_ED25519_ALGO:
        raise UpdateRefused(f"signature_refused: unsupported algo {fields['algo']!r}")
    if fields["namespace"] != SSH_SIG_NAMESPACE:
        raise UpdateRefused(f"signature_refused: unsupported namespace {fields['namespace']!r}")
    if not _HEX64_RE.fullmatch(fields["content_sha256"]):
        raise UpdateRefused("signature_refused: content_sha256 is not 64-hex")
    return fields


def _parse_signed_install_spec(spec_bytes: bytes | str) -> SignedInstallSpec:
    fields = _parse_embedded_signature_block(spec_bytes)
    canonical = _canonical_spec_bytes(spec_bytes)
    canonical_sha = _sha256(canonical)
    if fields["content_sha256"] != canonical_sha:
        raise UpdateRefused("signature_refused: signed spec content_sha256 does not match canonical bytes")
    return SignedInstallSpec(
        signature={
            "key_id": fields["key_id"],
            "algo": fields["algo"],
            "value": fields["value"],
        },
        content_sha256=fields["content_sha256"],
        canonical_sha256=canonical_sha,
    )


def _verify_signed_spec(
    *,
    canonical: bytes,
    signature: Mapping[str, Any],
    trust_root: Mapping[str, str],
    sshsig_runner: SshsigRunner,
) -> str:
    key_id = signature.get("key_id")
    if not isinstance(key_id, str) or key_id not in trust_root:
        raise UpdateRefused(f"signature_refused: key_id {key_id!r} is not present in trust root")
    if signature.get("algo") != SSH_ED25519_ALGO:
        raise UpdateRefused("signature_refused: unsupported signature algorithm")
    value = signature.get("value")
    if not isinstance(value, str):
        raise UpdateRefused("signature_refused: missing signature value")
    try:
        sig_bytes = base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise UpdateRefused(f"signature_refused: signature value is not valid base64: {exc}") from exc
    ok = bool(
        sshsig_runner(
            message=canonical,
            signature=sig_bytes,
            allowed_signers=trust_root[key_id],
            identity=key_id,
            namespace=SSH_SIG_NAMESPACE,
        )
    )
    if not ok:
        raise UpdateRefused("signature_refused: stock SSHSIG verification refused the install spec")
    return key_id


def _origin(value: str | None) -> tuple[str, str, int] | None:
    from urllib.parse import urlparse

    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return (parsed.scheme, parsed.hostname.rstrip(".").lower(), port)


def _verify_trust_anchors(
    key_id: str,
    key_material: str,
    anchors: tuple[TrustAnchorRecord, ...],
    *,
    install_spec_source: str,
) -> TrustAnchorEvidence:
    relevant = tuple(anchor for anchor in anchors if anchor.key_id == key_id)
    if not relevant:
        return TrustAnchorEvidence(False, "same_origin_only", "no out-of-band trust anchor matched the fetched trust root")
    spec_origin = _origin(install_spec_source)
    same_origin = tuple(
        anchor.source for anchor in relevant if _origin(anchor.source) is not None and _origin(anchor.source) == spec_origin
    )
    if same_origin:
        return TrustAnchorEvidence(False, "same_origin_anchor", "trust anchor source shares origin with the install spec")
    fingerprint = _public_key_fingerprint(key_material)
    agreed = tuple(dict.fromkeys(anchor.source for anchor in relevant if anchor.fingerprint == fingerprint))
    mismatched = tuple(dict.fromkeys(anchor.source for anchor in relevant if anchor.fingerprint != fingerprint))
    if mismatched:
        return TrustAnchorEvidence(False, "mismatch", "out-of-band trust anchor fingerprint does not match the fetched trust root", agreed, mismatched)
    if agreed:
        return TrustAnchorEvidence(True, "verified", "out-of-band trust anchor fingerprint matches the fetched trust root", agreed)
    return TrustAnchorEvidence(False, "same_origin_only", "no out-of-band trust anchor agreed with the fetched trust root")


def _normalize_site(site: str) -> str:
    return site.rstrip("/") + "/"


def _release_summary(release: VerifiedRelease) -> dict[str, Any]:
    return {
        "package_version": release.manifest.package_version,
        "canonical_spec_sha256": release.canonical_spec_sha256,
        "sha256s_sha256": release.sha256s_sha256,
        "platform": release.platform_tag,
        "trust_anchor": dict(release.trust_anchor),
        "artifact_rows": list(release.artifact_verification.get("rows", ())),
    }


def _current_or_newer(installed: InstalledIdentity, available: ReleaseIdentity) -> bool:
    current_key = _semver_key(installed.semver)
    available_key = _semver_key(available.semver)
    if current_key != available_key:
        return current_key > available_key
    return installed.build_git_sha == available.build_git_sha


def _update_available(installed: InstalledIdentity, available: ReleaseIdentity) -> bool:
    current_key = _semver_key(installed.semver)
    available_key = _semver_key(available.semver)
    if available_key > current_key:
        return True
    if available_key < current_key:
        return False
    return installed.build_git_sha != available.build_git_sha


def _semver_key(value: str) -> tuple[int, int, int, str]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(.*)", value.strip())
    if match is None:
        return (0, 0, 0, value)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)), match.group(4))


def _platform_facts(
    os_name: str | None = None,
    machine: str | None = None,
) -> tuple[str, str]:
    return os_name or platform.system(), machine or platform.machine()


def _verify_ssh_signature(
    *,
    spec_bytes: bytes,
    trust_root_text: str,
    trust_anchor_raw: bytes,
    trust_anchor_source: str,
    install_spec_source: str,
    sshsig_runner: SshsigRunner | None,
) -> tuple[SignedInstallSpec, str, TrustAnchorEvidence]:
    trust_root = _parse_allowed_signers(trust_root_text)
    signed = _parse_signed_install_spec(spec_bytes)
    canonical = _canonical_spec_bytes(spec_bytes)
    key_id = _verify_signed_spec(
        canonical=canonical,
        signature=signed.signature,
        trust_root=trust_root,
        sshsig_runner=sshsig_runner or _ssh_keygen_verify_runner,
    )
    anchors = _parse_anchor_records(trust_anchor_raw, source=trust_anchor_source)
    evidence = _verify_trust_anchors(
        key_id,
        trust_root[key_id],
        anchors,
        install_spec_source=install_spec_source,
    )
    if not evidence.ok:
        raise UpdateRefused(f"trust_anchor_refused: {evidence.status}: {evidence.reason}")
    return signed, key_id, evidence


def _parse_anchor_records(raw: bytes, *, source: str) -> tuple[TrustAnchorRecord, ...]:
    text = raw.decode("utf-8", errors="replace")
    records: list[TrustAnchorRecord] = []
    for raw_line in text.splitlines():
        line = raw_line.strip().strip('"').strip("'").strip()
        if not line or line.startswith("#"):
            continue
        key_id = ""
        fingerprint = ""
        if "=" in line:
            left, right = line.split("=", 1)
            key_id = left.strip()
            fingerprint = (right.strip().split() or [""])[0]
        else:
            fields = line.split()
            if len(fields) >= 2:
                key_id = fields[0].rstrip(":")
                fingerprint = next((field for field in fields[1:] if field.startswith("SHA256:")), "")
        if key_id and _OPENSSH_SHA256_FINGERPRINT_RE.fullmatch(fingerprint):
            records.append(TrustAnchorRecord(source=source, key_id=key_id, fingerprint=fingerprint))
    # DNS-over-HTTPS JSON can present TXT records inside a single JSON line.
    flattened = re.sub(r"[\{\}\[\]\",\\]", " ", text)
    for key_id, fingerprint in re.findall(
        r"\b([A-Za-z0-9_.-]+)\s*[= ]\s*(SHA256:[A-Za-z0-9+/]{43})\b",
        flattened,
    ):
        records.append(
            TrustAnchorRecord(
                source=source,
                key_id=key_id,
                fingerprint=fingerprint,
            )
        )
    unique: dict[tuple[str, str, str], TrustAnchorRecord] = {}
    for record in records:
        unique[(record.source, record.key_id, record.fingerprint)] = record
    return tuple(unique.values())


def _ssh_keygen_verify_runner(
    *,
    message: bytes,
    signature: bytes,
    allowed_signers: str,
    identity: str,
    namespace: str,
) -> bool:
    if not shutil.which("ssh-keygen"):
        raise UpdateRefused(install_prereqs.ssh_keygen_missing_detail())
    with tempfile.TemporaryDirectory(prefix="ce-update-sshsig-") as tmp:
        root = Path(tmp)
        allowed_path = root / "allowed_signers"
        sig_path = root / "spec.sig"
        allowed_path.write_text(allowed_signers + "\n", encoding="utf-8")
        sig_path.write_bytes(signature)
        try:
            proc = subprocess.run(
                [
                    "ssh-keygen",
                    "-Y",
                    "verify",
                    "-f",
                    str(allowed_path),
                    "-I",
                    identity,
                    "-n",
                    namespace,
                    "-s",
                    str(sig_path),
                ],
                input=message,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except FileNotFoundError as exc:
            raise UpdateRefused(install_prereqs.ssh_keygen_missing_detail()) from exc
        return proc.returncode == 0


def _fetch_release_artifacts(
    *,
    manifest: BootstrapManifest,
    fetcher: UrlFetcher,
    os_name: str,
    machine: str,
) -> tuple[str, str, dict[str, bytes], dict[str, str], dict[str, Any]]:
    sha256s_bytes = fetcher(manifest.sha256s_url)
    sha256s_text = sha256s_bytes.decode("utf-8")
    sha256s_sha = _sha256(sha256s_bytes)
    sums = parse_sha256s(sha256s_text)
    fetched: dict[str, bytes] = {
        "SHA256SUMS": sha256s_bytes,
        manifest.install_sh_sha256s_entry: fetcher(manifest.install_sh_url),
    }
    schema_name = _filename_from_url(manifest.answers_schema_url)
    fetched[schema_name] = fetcher(manifest.answers_schema_url)

    platform_tag = _platform_tag_for(os_name, machine)
    wheelhouse: dict[str, bytes] = {}
    for wheel in manifest.wheels_for_platform(platform_tag):
        wheel_bytes = fetcher(wheel.url)
        wheelhouse[wheel.filename] = wheel_bytes
        fetched[wheel.filename] = wheel_bytes

    fetched_digests = {name: _sha256(data) for name, data in fetched.items()}
    for wheel in manifest.wheels_for_platform(platform_tag):
        fetched_digests[wheel.url] = fetched_digests[wheel.filename]
    fetched_digests[manifest.install_sh_url] = fetched_digests[manifest.install_sh_sha256s_entry]
    fetched_digests[manifest.answers_schema_url] = fetched_digests[schema_name]

    if sha256s_sha != manifest.sha256s_sha256:
        raise UpdateRefused("artifact_hash_mismatch: SHA256SUMS digest does not match signed manifest")
    artifact_verification = _verify_bootstrap_artifacts(
        manifest=manifest,
        sha256s_text=sha256s_text,
        fetched_digests=fetched_digests,
        platform_tag=platform_tag,
    )
    return sha256s_text, sha256s_sha, wheelhouse, sums, artifact_verification


def _filename_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def _platform_tag_for(os_name: str, machine: str) -> str:
    normalized_os = os_name.lower()
    normalized_machine = machine.lower()
    if normalized_os != "linux":
        raise UpdateRefused(
            f"unsupported_platform: no signed wheelhouse for {os_name}/{machine}; "
            "E1 supports Linux x86_64/amd64 and Linux aarch64/arm64 with CPython 3.14 wheels"
        )
    if normalized_machine in {"x86_64", "amd64"}:
        return "linux-x86_64-cp314"
    if normalized_machine in {"aarch64", "arm64"}:
        return "linux-aarch64-cp314"
    raise UpdateRefused(
        f"unsupported_platform: no signed wheelhouse for {os_name}/{machine}; "
        "E1 supports Linux x86_64/amd64 and Linux aarch64/arm64 with CPython 3.14 wheels"
    )


def _artifact_row(name: str, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "artifact": name,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "ok": bool(expected and actual == expected),
    }


def _verify_bootstrap_artifacts(
    *,
    manifest: BootstrapManifest,
    sha256s_text: str,
    fetched_digests: Mapping[str, Any],
    platform_tag: str,
) -> dict[str, Any]:
    sums_digest = _sha256(sha256s_text.encode("utf-8"))
    sums = parse_sha256s(sha256s_text)
    rows = [_artifact_row("SHA256SUMS", manifest.sha256s_sha256, sums_digest)]
    problems: list[str] = []
    if rows[-1]["ok"] is not True:
        problems.append("SHA256SUMS digest does not match the signed manifest")

    install_name = manifest.install_sh_sha256s_entry
    install_expected = sums.get(install_name)
    install_actual = fetched_digests.get(install_name) or fetched_digests.get(manifest.install_sh_url)
    rows.append(_artifact_row(install_name, install_expected, install_actual))
    if install_expected is None:
        problems.append(f"SHA256SUMS is missing {install_name}")
    if rows[-1]["ok"] is not True:
        problems.append(f"{install_name} digest mismatch")

    schema_name = _filename_from_url(manifest.answers_schema_url)
    schema_actual = fetched_digests.get(schema_name) or fetched_digests.get(manifest.answers_schema_url)
    rows.append(_artifact_row(schema_name, manifest.answers_schema_sha256, schema_actual))
    if rows[-1]["ok"] is not True:
        problems.append(f"{schema_name} digest mismatch")
    if schema_name in sums and sums[schema_name] != manifest.answers_schema_sha256:
        problems.append(f"SHA256SUMS entry for {schema_name} disagrees with the signed manifest")

    for wheel in manifest.wheels_for_platform(platform_tag):
        sum_value = sums.get(wheel.filename)
        if sum_value is None:
            problems.append(f"SHA256SUMS is missing {wheel.filename}")
        elif sum_value != wheel.sha256:
            problems.append(f"SHA256SUMS entry for {wheel.filename} disagrees with the signed manifest")
        actual = fetched_digests.get(wheel.filename) or fetched_digests.get(wheel.url)
        rows.append(_artifact_row(wheel.filename, wheel.sha256, actual))
        if rows[-1]["ok"] is not True:
            problems.append(f"{wheel.filename} digest mismatch")
    if problems:
        raise UpdateRefused("artifact_hash_mismatch: " + "; ".join(problems))
    return {"ok": True, "platform": platform_tag, "rows": rows}


def _release_identity_from_app_wheel(
    *,
    manifest: BootstrapManifest,
    app_wheel: BootstrapWheel,
    wheel_bytes: bytes,
) -> ReleaseIdentity:
    try:
        with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
            version_text = archive.read("creator_engine_validator/_version.py").decode("utf-8")
    except (KeyError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise UpdateRefused("wheel_source_parity_refused: app wheel lacks readable _version.py") from exc
    semver = _python_scalar(version_text, "SEMVER")
    build_sha = _python_scalar(version_text, "BUILD_GIT_SHA")
    if semver != manifest.package_version:
        raise UpdateRefused(
            "wheel_source_parity_refused: app wheel SEMVER does not match signed manifest"
        )
    if not re.fullmatch(r"[0-9a-f]{40}", build_sha):
        raise UpdateRefused("wheel_source_parity_refused: app wheel BUILD_GIT_SHA is not 40-hex")
    return ReleaseIdentity(
        semver=semver,
        build_git_sha=build_sha,
        app_wheel=app_wheel.filename,
        app_wheel_sha256=app_wheel.sha256,
    )


def _python_scalar(source: str, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']\s*$", source)
    if match is None:
        raise UpdateRefused(f"wheel_source_parity_refused: missing {name}")
    return match.group(1)


def resolve_latest_signed_release(
    *,
    site: str = DEFAULT_SITE,
    trust_anchor_url: str = DEFAULT_TRUST_ANCHOR_URL,
    trust_anchor_source: str = DEFAULT_TRUST_ANCHOR_SOURCE,
    fetcher: UrlFetcher | None = None,
    sshsig_runner: SshsigRunner | None = None,
    os_name: str | None = None,
    machine: str | None = None,
) -> VerifiedRelease:
    fetch = fetcher or default_fetcher
    base = _normalize_site(site)
    spec_url = urljoin(base, "llms-install.md")
    trust_root_url = urljoin(base, "keys/ce-root-v1")
    spec_bytes = fetch(spec_url)
    trust_root_bytes = fetch(trust_root_url)
    trust_anchor_raw = fetch(trust_anchor_url)
    trust_root_text = trust_root_bytes.decode("utf-8")
    signed, _verified, trust_anchor = _verify_ssh_signature(
        spec_bytes=spec_bytes,
        trust_root_text=trust_root_text,
        trust_anchor_raw=trust_anchor_raw,
        trust_anchor_source=trust_anchor_source,
        install_spec_source=spec_url,
        sshsig_runner=sshsig_runner,
    )
    try:
        manifest = parse_bootstrap_manifest(spec_bytes, error_cls=UpdateRefused)
    except BootstrapManifestError as exc:
        raise UpdateRefused(str(exc)) from exc
    os_fact, machine_fact = _platform_facts(os_name, machine)
    sha256s_text, sha256s_sha, wheelhouse, _sums, artifact_verification = _fetch_release_artifacts(
        manifest=manifest,
        fetcher=fetch,
        os_name=os_fact,
        machine=machine_fact,
    )
    platform_tag = artifact_verification["platform"]
    app_wheel = manifest.wheel_by_filename().get(manifest.app_wheel)
    if app_wheel is None or app_wheel.filename not in wheelhouse:
        raise UpdateRefused("wheel_source_parity_refused: signed app wheel missing from wheelhouse")
    available_identity = _release_identity_from_app_wheel(
        manifest=manifest,
        app_wheel=app_wheel,
        wheel_bytes=wheelhouse[app_wheel.filename],
    )
    return VerifiedRelease(
        identity=available_identity,
        manifest=manifest,
        spec_bytes=spec_bytes,
        canonical_spec_sha256=signed.canonical_sha256,
        trust_root_sha256=_sha256(trust_root_bytes),
        trust_anchor_sha256=_sha256(trust_anchor_raw),
        sha256s_text=sha256s_text,
        sha256s_sha256=sha256s_sha,
        platform_tag=platform_tag,
        wheelhouse=wheelhouse,
        trust_anchor=trust_anchor.to_record(),
        artifact_verification=artifact_verification,
    )


def resolve_latest_signed_release_spec_only(
    *,
    site: str = DEFAULT_SITE,
    trust_anchor_url: str = DEFAULT_TRUST_ANCHOR_URL,
    trust_anchor_source: str = DEFAULT_TRUST_ANCHOR_SOURCE,
    fetcher: UrlFetcher | None = None,
    sshsig_runner: SshsigRunner | None = None,
) -> SpecOnlyRelease:
    fetch = fetcher or default_fetcher
    base = _normalize_site(site)
    spec_url = urljoin(base, "llms-install.md")
    trust_root_url = urljoin(base, "keys/ce-root-v1")
    spec_bytes = fetch(spec_url)
    trust_root_bytes = fetch(trust_root_url)
    trust_anchor_raw = fetch(trust_anchor_url)
    trust_root_text = trust_root_bytes.decode("utf-8")
    signed, _verified, trust_anchor = _verify_ssh_signature(
        spec_bytes=spec_bytes,
        trust_root_text=trust_root_text,
        trust_anchor_raw=trust_anchor_raw,
        trust_anchor_source=trust_anchor_source,
        install_spec_source=spec_url,
        sshsig_runner=sshsig_runner,
    )
    try:
        manifest = parse_bootstrap_manifest(spec_bytes, error_cls=UpdateRefused)
    except BootstrapManifestError as exc:
        raise UpdateRefused(str(exc)) from exc
    app_wheel = manifest.wheel_by_filename().get(manifest.app_wheel)
    if app_wheel is None:
        raise UpdateRefused("startup_update_refused: signed app wheel row missing from manifest")
    return SpecOnlyRelease(
        semver=manifest.package_version,
        app_wheel=app_wheel.filename,
        app_wheel_sha256=app_wheel.sha256,
        canonical_spec_sha256=signed.canonical_sha256,
        trust_root_sha256=_sha256(trust_root_bytes),
        trust_anchor_sha256=_sha256(trust_anchor_raw),
        trust_anchor=trust_anchor.to_record(),
    )


def _startup_cache_path() -> Path:
    override = os.environ.get(STARTUP_UPDATE_CACHE_ENV)
    if override:
        return Path(override).expanduser()
    cache_home = os.environ.get("XDG_CACHE_HOME")
    if cache_home:
        return Path(cache_home).expanduser() / "creator-engine" / "update-check.json"
    home = os.environ.get("HOME")
    if home:
        return Path(home).expanduser() / ".cache" / "creator-engine" / "update-check.json"
    return Path(tempfile.gettempdir()) / "creator-engine-update-check.json"


def startup_update_check_disabled(env: Mapping[str, str] | None = None) -> bool:
    source = env if env is not None else os.environ
    value = str(source.get(STARTUP_UPDATE_DISABLE_ENV, "")).strip().lower()
    return value in {"0", "false", "no", "off", "disable", "disabled"}


def _is_stable_release_identity(identity: InstalledIdentity) -> bool:
    return re.fullmatch(r"\d+\.\d+\.\d+", identity.semver.strip()) is not None


def _fetch_with_timeout(fetcher: UrlFetcher, url: str, timeout_seconds: float) -> bytes:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fetcher, url)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeout as exc:
        future.cancel()
        raise TimeoutError(f"timed out fetching {url}") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _read_startup_update_cache(path: Path, *, now: float, ttl_seconds: int) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    checked_at = payload.get("checked_at")
    if not isinstance(checked_at, (int, float)) or now - float(checked_at) >= ttl_seconds:
        return None
    return payload


def _write_startup_update_cache(path: Path, payload: Mapping[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(dict(payload), sort_keys=True), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        return


def mark_startup_update_notice_shown(cache_path: Path | None = None) -> None:
    path = cache_path or _startup_cache_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict):
        return
    payload["notice_shown"] = True
    _write_startup_update_cache(path, payload)


def check_startup_update_notice(
    *,
    site: str = DEFAULT_SITE,
    trust_anchor_url: str = DEFAULT_TRUST_ANCHOR_URL,
    trust_anchor_source: str = DEFAULT_TRUST_ANCHOR_SOURCE,
    fetcher: UrlFetcher | None = None,
    sshsig_runner: SshsigRunner | None = None,
    installed: InstalledIdentity | None = None,
    cache_path: Path | None = None,
    cache_ttl_seconds: int = STARTUP_UPDATE_CACHE_TTL_SECONDS,
    fetch_timeout_seconds: float = STARTUP_UPDATE_FETCH_TIMEOUT_SECONDS,
    now: float | None = None,
    env: Mapping[str, str] | None = None,
) -> StartupUpdateCheck:
    current = installed or installed_identity()
    path = cache_path or _startup_cache_path()
    if startup_update_check_disabled(env):
        return StartupUpdateCheck(False, reason="disabled", cache_path=path)
    if not _is_stable_release_identity(current):
        return StartupUpdateCheck(False, reason="not stable release", cache_path=path)

    now_value = time.time() if now is None else now
    cached = _read_startup_update_cache(path, now=now_value, ttl_seconds=cache_ttl_seconds)
    if cached is not None:
        update_available = bool(cached.get("update_available"))
        available_semver = cached.get("available_semver")
        semver = available_semver if isinstance(available_semver, str) else None
        notice_due = update_available and cached.get("notice_shown") is not True
        return StartupUpdateCheck(
            update_available=update_available,
            available_semver=semver,
            reason="cached",
            from_cache=True,
            notice_due=notice_due,
            cache_path=path,
        )

    base_fetcher = fetcher or (lambda url: default_fetcher(url, timeout=fetch_timeout_seconds))

    def timed_fetcher(url: str) -> bytes:
        return _fetch_with_timeout(base_fetcher, url, fetch_timeout_seconds)

    try:
        release = resolve_latest_signed_release_spec_only(
            site=site,
            trust_anchor_url=trust_anchor_url,
            trust_anchor_source=trust_anchor_source,
            fetcher=timed_fetcher,
            sshsig_runner=sshsig_runner,
        )
        available = _semver_key(release.semver) > _semver_key(current.semver)
        payload = {
            "checked_at": now_value,
            "installed_semver": current.semver,
            "available_semver": release.semver,
            "update_available": available,
            "notice_shown": False,
            "canonical_spec_sha256": release.canonical_spec_sha256,
        }
        _write_startup_update_cache(path, payload)
        return StartupUpdateCheck(
            update_available=available,
            available_semver=release.semver,
            reason="update available" if available else "installed CE is current",
            notice_due=available,
            cache_path=path,
        )
    except Exception:
        return StartupUpdateCheck(False, reason="fail open", cache_path=path)


def check_for_update(
    *,
    site: str = DEFAULT_SITE,
    trust_anchor_url: str = DEFAULT_TRUST_ANCHOR_URL,
    trust_anchor_source: str = DEFAULT_TRUST_ANCHOR_SOURCE,
    fetcher: UrlFetcher | None = None,
    sshsig_runner: SshsigRunner | None = None,
    installed: InstalledIdentity | None = None,
    os_name: str | None = None,
    machine: str | None = None,
) -> UpdateResult:
    current = installed or installed_identity()
    release = resolve_latest_signed_release(
        site=site,
        trust_anchor_url=trust_anchor_url,
        trust_anchor_source=trust_anchor_source,
        fetcher=fetcher,
        sshsig_runner=sshsig_runner,
        os_name=os_name,
        machine=machine,
    )
    available = _update_available(current, release.identity)
    status = "available" if available else "current"
    reason = "update available" if available else "installed CE is current"
    if _current_or_newer(current, release.identity) and not available:
        reason = "installed CE is current or newer than the signed mirror"
    return UpdateResult(
        ok=True,
        status=status,
        reason=reason,
        installed=current,
        available=release.identity,
        update_available=available,
        read_only=True,
        release=_release_summary(release),
    )


class VenvSwapper:
    """Build a verified venv target and atomically promote ``install_root/venv``."""

    def __init__(self, *, python_executable: str | None = None):
        self.python_executable = python_executable or sys.executable

    def apply(self, install_root: Path, release: VerifiedRelease) -> tuple[str, ...]:
        root = install_root
        root.mkdir(parents=True, exist_ok=True)
        lock = _InstallLock(root)
        with lock:
            target = root / f"venv-{release.manifest.package_version}-{release.sha256s_sha256}"
            actions: list[str] = []
            if not self._venv_target_ok(target):
                self._build_target(target, release)
                actions.append("build_verified_venv")
            else:
                actions.append("reuse_verified_venv_target")
            self._promote_and_write_state(root, target, release)
            actions.append("promote_verified_venv")
            actions.append("write_install_state")
            return tuple(actions)

    def _venv_target_ok(self, target: Path) -> bool:
        ce = target / "bin" / "ce"
        cev3 = target / "bin" / "cev3"
        return ce.is_file() and os.access(ce, os.X_OK) and cev3.is_file() and os.access(cev3, os.X_OK)

    def _build_target(self, target: Path, release: VerifiedRelease) -> None:
        wheelhouse = target.parent / f".{target.name}.wheelhouse.{os.getpid()}"
        if target.exists():
            shutil.rmtree(target)
        if wheelhouse.exists():
            shutil.rmtree(wheelhouse)
        try:
            wheelhouse.mkdir(parents=True)
            for filename, data in release.wheelhouse.items():
                (wheelhouse / filename).write_bytes(data)
            subprocess.run([self.python_executable, "-m", "venv", str(target)], check=True)
            subprocess.run(
                [
                    str(target / "bin" / "python"),
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--find-links",
                    str(wheelhouse),
                    f"{release.manifest.package_name}=={release.manifest.package_version}",
                ],
                check=True,
            )
            subprocess.run([str(target / "bin" / "ce"), "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            subprocess.run([str(target / "bin" / "cev3"), "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(wheelhouse, ignore_errors=True)

    def _promote_and_write_state(self, root: Path, target: Path, release: VerifiedRelease) -> None:
        live = root / "venv"
        link_tmp = root / f"venv.link.{os.getpid()}"
        backup = root / f"venv.previous.{os.getpid()}"
        if link_tmp.exists() or link_tmp.is_symlink():
            link_tmp.unlink()
        if backup.exists() or backup.is_symlink():
            if backup.is_dir() and not backup.is_symlink():
                shutil.rmtree(backup)
            else:
                backup.unlink()
        previous_symlink_target = os.readlink(live) if live.is_symlink() else None
        link_tmp.symlink_to(target.name)
        moved_dir = False
        promoted = False
        try:
            if live.exists() and not live.is_symlink():
                os.replace(live, backup)
                moved_dir = True
            os.replace(link_tmp, live)
            promoted = True
            self._write_state(root, target, release)
        except Exception:
            if link_tmp.exists() or link_tmp.is_symlink():
                link_tmp.unlink()
            if promoted:
                if live.exists() or live.is_symlink():
                    if live.is_dir() and not live.is_symlink():
                        shutil.rmtree(live)
                    else:
                        live.unlink()
                if previous_symlink_target is not None:
                    live.symlink_to(previous_symlink_target)
            if moved_dir and backup.exists() and not live.exists():
                os.replace(backup, live)
            raise
        if backup.exists():
            if backup.is_dir() and not backup.is_symlink():
                shutil.rmtree(backup)
            else:
                backup.unlink()

    def _write_state(self, root: Path, target: Path, release: VerifiedRelease) -> None:
        state_path = root / "install-state"
        tmp = state_path.with_name(f"{state_path.name}.tmp.{os.getpid()}")
        lines = [
            f"spec_canonical_sha256={release.canonical_spec_sha256}",
            f"trust_root_sha256={release.trust_root_sha256}",
            f"trust_anchor_source={DEFAULT_TRUST_ANCHOR_SOURCE}",
            f"trust_anchor_sha256={release.trust_anchor_sha256}",
            f"sha256s_sha256={release.sha256s_sha256}",
            f"package_version={release.manifest.package_version}",
            f"python_executable={self.python_executable}",
            f"platform={release.platform_tag}",
            f"venv_path={root / 'venv'}",
            f"venv_target={target}",
            f"timestamp={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        ]
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, state_path)


class _InstallLock:
    def __init__(self, root: Path):
        self.path = root / "install.lock"

    def __enter__(self) -> "_InstallLock":
        try:
            self.path.mkdir()
        except FileExistsError as exc:
            raise UpdateRefused(f"install_lock_held: lock already exists at {self.path}") from exc
        (self.path / "pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            (self.path / "pid").unlink()
        except FileNotFoundError:
            pass
        try:
            self.path.rmdir()
        except OSError:
            pass


def apply_update(
    *,
    install_root: str | Path | None = None,
    site: str = DEFAULT_SITE,
    trust_anchor_url: str = DEFAULT_TRUST_ANCHOR_URL,
    trust_anchor_source: str = DEFAULT_TRUST_ANCHOR_SOURCE,
    fetcher: UrlFetcher | None = None,
    sshsig_runner: SshsigRunner | None = None,
    installed: InstalledIdentity | None = None,
    os_name: str | None = None,
    machine: str | None = None,
    swapper: VenvSwapper | None = None,
) -> UpdateResult:
    current = installed or installed_identity()
    release = resolve_latest_signed_release(
        site=site,
        trust_anchor_url=trust_anchor_url,
        trust_anchor_source=trust_anchor_source,
        fetcher=fetcher,
        sshsig_runner=sshsig_runner,
        os_name=os_name,
        machine=machine,
    )
    root = Path(install_root) if install_root is not None else ce_provenance.default_install_root()
    if not _update_available(current, release.identity):
        return UpdateResult(
            ok=True,
            status="current",
            reason="installed CE is current",
            installed=current,
            available=release.identity,
            update_available=False,
            read_only=False,
            install_root=str(root),
            actions=("noop_current",),
            release=_release_summary(release),
        )
    runner = swapper or VenvSwapper()
    try:
        actions = runner.apply(root, release)
    except Exception as exc:
        return UpdateResult(
            ok=False,
            status="refuse",
            reason="update refused before convergence completed",
            installed=current,
            available=release.identity,
            update_available=True,
            read_only=False,
            install_root=str(root),
            problems=(f"swap_failed:{exc.__class__.__name__}",),
            release=_release_summary(release),
        )
    return UpdateResult(
        ok=True,
        status="updated",
        reason="updated CE in place",
        installed=current,
        available=release.identity,
        update_available=True,
        read_only=False,
        install_root=str(root),
        actions=actions,
        release=_release_summary(release),
    )


def run_cli(args: Any) -> int:
    try:
        if getattr(args, "check", False):
            result = check_for_update(
                site=args.site,
                trust_anchor_url=args.trust_anchor_url,
            )
        else:
            result = apply_update(
                install_root=getattr(args, "install_root", None),
                site=args.site,
                trust_anchor_url=args.trust_anchor_url,
            )
    except UpdateRefused as exc:
        current = installed_identity()
        result = UpdateResult(
            ok=False,
            status="refuse",
            reason=str(exc),
            installed=current,
            read_only=bool(getattr(args, "check", False)),
            install_root=getattr(args, "install_root", None),
            problems=(str(exc),),
        )
    if getattr(args, "json_output", False):
        import json

        print(json.dumps(result.to_json(), indent=2, sort_keys=True))
    elif result.ok and result.status == "current":
        print(f"ce update: current ({result.installed.token})")
    elif result.ok and result.status == "available":
        available = result.available.token if result.available else "unknown"
        print(f"ce update: available {available} (installed {result.installed.token})")
    elif result.ok:
        available = result.available.token if result.available else "unknown"
        print(f"ce update: {result.status} to {available}")
    else:
        print(f"ERROR: ce update refused: {result.reason}", file=sys.stderr)
    return 0 if result.ok else 1
