"""Install-spec signature guard.

The public agent-native install spec is executable guidance. This guard keeps the
served spec and any versioned mirrors from carrying placeholder or malformed
SSHSIG values, and can verify the detached SSHSIG through the existing installer
primitive when a verifier is supplied.
"""

from __future__ import annotations

import base64
import binascii
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from ..v3_installer import PINNED_KEYS, canonical_spec_bytes, content_digest
from ..reporting import CheckResult, ValidationError, make_error
from . import register


CHECK_NAME = "install_spec_signature_guard"
CODE_MISSING = "install_spec_signature_missing"
CODE_PLACEHOLDER = "install_spec_signature_placeholder"
CODE_BASE64 = "install_spec_signature_invalid_base64"
CODE_CONTENT = "install_spec_signature_content_sha"
CODE_VERIFY = "install_spec_signature_unverified"
CONTRACT = "docs/llms-install.md"
INSTALL_SPEC = "llms-install.md"
SSH_ED25519_ALGO = "ssh-ed25519"
SSH_SIG_NAMESPACE = "ce-spec-v1"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

Verifier = Callable[[str, bytes, Any, Any], bool]


def _repo_root_for(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / "docs" / INSTALL_SPEC).is_file():
            return candidate
    return None


def install_spec_paths(repo_root: Path) -> list[Path]:
    """Return served install specs under the repo root.

    The root served spec is always checked. Versioned download mirrors are
    checked when present; no mirror is required by this guard.
    """
    docs = repo_root / "docs"
    paths = [docs / INSTALL_SPEC]
    downloads = docs / "downloads"
    if downloads.is_dir():
        paths.extend(sorted(downloads.glob(f"*/{INSTALL_SPEC}")))
    return paths


def _err(code: str, path: Path, field: str, message: str) -> ValidationError:
    return make_error(code, path, field, message, CONTRACT)


def _signature_value_is_placeholder(value: str) -> bool:
    stripped = value.strip()
    return len(stripped) >= 2 and stripped.startswith("<") and stripped.endswith(">")


def parse_embedded_signature_block(spec_bytes: bytes | str) -> dict[str, str]:
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

    required = {"key_id", "algo", "namespace", "value", "content_sha256"}
    missing = sorted(required - fields.keys())
    if missing:
        raise ValueError("signature block missing " + ", ".join(missing))
    if fields["namespace"] != SSH_SIG_NAMESPACE:
        raise ValueError(f"namespace {fields['namespace']!r} is not {SSH_SIG_NAMESPACE!r}")
    if fields["algo"] != SSH_ED25519_ALGO:
        raise ValueError(f"algo {fields['algo']!r} is not {SSH_ED25519_ALGO!r}")
    if not HEX64_RE.match(fields["content_sha256"]):
        raise ValueError("content_sha256 is not a 64-hex digest")
    return fields


def _verify_spec(canonical: bytes, signature: dict[str, str], *, pinned_keys: dict[str, Any], verifier: Verifier) -> str | None:
    key_id = signature.get("key_id")
    if key_id not in pinned_keys:
        return f"unknown/unpinned signing key {key_id!r}"
    algo = signature.get("algo", "")
    if verifier(algo, canonical, signature.get("value"), pinned_keys[key_id]):
        return None
    return f"signature did not verify (algo {algo!r})"


def validate_file(
    path: Path,
    *,
    verifier: Verifier | None,
    pinned_keys: dict[str, Any] | None = None,
) -> list[ValidationError]:
    """Fail-closed validation for one served install-spec file."""
    if not path.is_file():
        return [_err(CODE_MISSING, path, "", "missing served install spec")]

    try:
        spec_bytes = path.read_bytes()
    except OSError as exc:
        return [_err(CODE_MISSING, path, "", f"could not read install spec: {exc}")]

    try:
        fields = parse_embedded_signature_block(spec_bytes)
    except ValueError as exc:
        return [_err(CODE_MISSING, path, "signature", str(exc))]

    value = fields["value"]
    errors: list[ValidationError] = []
    if _signature_value_is_placeholder(value):
        errors.append(
            _err(
                CODE_PLACEHOLDER,
                path,
                "signature.value",
                "signature value is a placeholder; publish a real detached SSHSIG base64 value",
            )
        )
    else:
        try:
            base64.b64decode(value.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error, ValueError):
            errors.append(
                _err(
                    CODE_BASE64,
                    path,
                    "signature.value",
                    "signature value is not valid base64",
                )
            )

    try:
        canonical = canonical_spec_bytes(spec_bytes)
        canonical_sha = content_digest(canonical)
        if fields["content_sha256"] != canonical_sha:
            raise ValueError("signed spec content_sha256 does not match canonical bytes")
    except ValueError as exc:
        errors.append(_err(CODE_CONTENT, path, "signature.content_sha256", str(exc)))
        return errors

    if errors:
        return errors

    verify = verifier
    if verify is None:
        verify = ssh_keygen_verifier()
    if verify is None:
        return [_err(CODE_VERIFY, path, "signature.value", "ssh-keygen is not available to verify SSHSIG")]

    verify_error = _verify_spec(
        canonical,
        {"key_id": fields["key_id"], "algo": fields["algo"], "value": fields["value"]},
        pinned_keys=pinned_keys or PINNED_KEYS,
        verifier=verify,
    )
    if verify_error is not None:
        return [_err(CODE_VERIFY, path, "signature.value", verify_error)]
    return []


def validate_repo(
    repo_root: Path,
    *,
    verifier: Verifier | None = None,
    pinned_keys: dict[str, Any] | None = None,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for path in install_spec_paths(repo_root):
        errors.extend(validate_file(path, verifier=verifier, pinned_keys=pinned_keys))
    return errors


def _ssh_keygen_verify_runner(
    *,
    message: bytes,
    signature: bytes,
    allowed_signers: str,
    identity: str,
    namespace: str,
) -> bool:
    with tempfile.TemporaryDirectory(prefix="ce-install-spec-sig-") as tmp:
        tmpdir = Path(tmp)
        allowed_path = tmpdir / "allowed_signers"
        sig_path = tmpdir / "spec.sig"
        allowed_path.write_text(allowed_signers + "\n", encoding="utf-8")
        sig_path.write_bytes(signature)
        completed = subprocess.run(
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
            capture_output=True,
            check=False,
        )
    return completed.returncode == 0


def ssh_keygen_verifier() -> Verifier | None:
    if not shutil.which("ssh-keygen"):
        return None

    def _verify(algo: str, raw: bytes, value: Any, key_material: Any) -> bool:
        if algo != SSH_ED25519_ALGO:
            return False
        if not isinstance(value, str) or not isinstance(key_material, str):
            return False
        try:
            signature = base64.b64decode(value.encode("ascii"), validate=True)
        except (binascii.Error, ValueError):
            return False
        fields = key_material.split()
        if len(fields) < 3:
            return False
        identity = fields[0].split(",")[0]
        try:
            return bool(
                _ssh_keygen_verify_runner(
                    message=raw,
                    signature=signature,
                    allowed_signers=key_material,
                    identity=identity,
                    namespace=SSH_SIG_NAMESPACE,
                )
            )
        except Exception:
            return False

    return _verify


@register(CHECK_NAME, [CODE_MISSING, CODE_PLACEHOLDER, CODE_BASE64, CODE_CONTENT, CODE_VERIFY])
def run(paths: Iterable[Path]) -> CheckResult:
    """Temporarily advisory registry adapter.

    ``validate_repo`` is fail-closed and the CLI can return non-zero. The generic
    registry emits warnings until the controller re-signs the spec and flips this
    guard to a blocking required gate.
    """
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        root = _repo_root_for(Path(raw))
        if root is None:
            continue
        resolved = root.resolve()
        if resolved not in seen:
            seen.add(resolved)
            roots.append(root)

    warnings: list[ValidationError] = []
    for root in roots:
        warnings.extend(validate_repo(root))
    return CheckResult(name=CHECK_NAME, warnings=tuple(warnings))
