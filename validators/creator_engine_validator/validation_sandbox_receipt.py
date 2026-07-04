"""Signed receipts for containerized validation-sandbox runs."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


_HEX_RE = re.compile(r"^[0-9a-f]+$")


class ValidationSandboxReceiptError(ValueError):
    """A validation-sandbox receipt is malformed or fails verification."""


def command_sha256(command: Sequence[str]) -> str:
    """Return the canonical SHA256 binding for a trailing sandbox argv."""

    canonical = json.dumps(list(command), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _normalize_mounts(mounts: Sequence[Mapping[str, Any]]) -> tuple[tuple[str, str], ...]:
    return tuple((str(entry["path"]), str(entry["mode"])) for entry in mounts)


def _coerce_mounts(mounts: Sequence[Any]) -> tuple[tuple[str, str], ...]:
    normalized: list[tuple[str, str]] = []
    for entry in mounts:
        if isinstance(entry, Mapping):
            normalized.append((str(entry["path"]), str(entry["mode"])))
        else:
            path, mode = entry
            normalized.append((str(path), str(mode)))
    return tuple(normalized)


@dataclass(frozen=True)
class ValidationSandboxReceipt:
    """Opaque bearer receipt bound to one observed containerized validation run."""

    nonce: str
    tree_sha: str
    command_sha256: str
    policy_sha: str
    image_sha: str
    mount_manifest_applied: tuple[tuple[str, str], ...]
    egress_allowlist_applied: tuple[str, ...]
    secret_allowlist_applied: tuple[str, ...]
    returncode: int
    signature: str
    kind: str = "validation-sandbox-receipt"
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if not self.nonce:
            raise ValidationSandboxReceiptError("nonce is required")
        for field_name in ("command_sha256", "policy_sha", "signature"):
            value = str(getattr(self, field_name))
            if not _HEX_RE.fullmatch(value) or len(value) != 64:
                raise ValidationSandboxReceiptError(f"{field_name} must be lowercase 64-hex")
        if not self.tree_sha:
            raise ValidationSandboxReceiptError("tree_sha is required")
        if not str(self.image_sha).startswith("sha256:"):
            raise ValidationSandboxReceiptError("image_sha must be a sha256 image digest")
        object.__setattr__(self, "mount_manifest_applied", _coerce_mounts(self.mount_manifest_applied))
        object.__setattr__(self, "egress_allowlist_applied", tuple(self.egress_allowlist_applied))
        object.__setattr__(self, "secret_allowlist_applied", tuple(self.secret_allowlist_applied))

    def signing_payload(self) -> dict[str, Any]:
        """Return the deterministic payload covered by the HMAC signature."""

        return {
            "kind": self.kind,
            "schema_version": self.schema_version,
            "nonce": self.nonce,
            "tree_sha": self.tree_sha,
            "command_sha256": self.command_sha256,
            "policy_sha": self.policy_sha,
            "image_sha": self.image_sha,
            "mount_manifest_applied": [
                {"path": path, "mode": mode}
                for path, mode in self.mount_manifest_applied
            ],
            "egress_allowlist_applied": list(self.egress_allowlist_applied),
            "secret_allowlist_applied": list(self.secret_allowlist_applied),
            "returncode": self.returncode,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.signing_payload()
        payload["signature"] = self.signature
        return payload


class ValidationSandboxReceiptIssuer:
    """Mint and verify HMAC receipts for observed validation-sandbox exits."""

    def __init__(
        self,
        *,
        secret: bytes | None = None,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self._secret = secret if secret is not None else secrets.token_bytes(32)
        self._nonce_factory = nonce_factory or (lambda: secrets.token_urlsafe(32))

    def mint(
        self,
        *,
        tree_sha: str,
        command: Sequence[str],
        policy_sha: str,
        image_sha: str,
        mount_manifest_applied: Sequence[Mapping[str, Any]],
        egress_allowlist_applied: Sequence[str],
        secret_allowlist_applied: Sequence[str],
        returncode: int,
    ) -> ValidationSandboxReceipt:
        nonce = self._nonce_factory()
        unsigned = ValidationSandboxReceipt(
            nonce=nonce,
            tree_sha=tree_sha,
            command_sha256=command_sha256(command),
            policy_sha=policy_sha,
            image_sha=image_sha,
            mount_manifest_applied=_normalize_mounts(mount_manifest_applied),
            egress_allowlist_applied=tuple(str(item) for item in egress_allowlist_applied),
            secret_allowlist_applied=tuple(str(item) for item in secret_allowlist_applied),
            returncode=int(returncode),
            signature="0" * 64,
        )
        return ValidationSandboxReceipt(
            nonce=unsigned.nonce,
            tree_sha=unsigned.tree_sha,
            command_sha256=unsigned.command_sha256,
            policy_sha=unsigned.policy_sha,
            image_sha=unsigned.image_sha,
            mount_manifest_applied=unsigned.mount_manifest_applied,
            egress_allowlist_applied=unsigned.egress_allowlist_applied,
            secret_allowlist_applied=unsigned.secret_allowlist_applied,
            returncode=unsigned.returncode,
            signature=self._signature(unsigned),
        )

    def verify(self, receipt: ValidationSandboxReceipt) -> bool:
        expected = self._signature(receipt)
        return hmac.compare_digest(receipt.signature, expected)

    def _signature(self, receipt: ValidationSandboxReceipt) -> str:
        message = json.dumps(
            receipt.signing_payload(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(hmac.new(self._secret, message, hashlib.sha256).digest()).hexdigest()


__all__ = [
    "ValidationSandboxReceipt",
    "ValidationSandboxReceiptError",
    "ValidationSandboxReceiptIssuer",
    "command_sha256",
]
