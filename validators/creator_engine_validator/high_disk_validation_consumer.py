"""Fixed-purpose atomic-file-drop consumer for high-disk validation.

The connector intentionally has no network or credential surface.  It drops a
canonical request directory for the ratified ``ce-validation-lane.service`` and
accepts only a typed, receipt-bound success for that exact submission.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import stat
import time
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol

from .high_disk_validation_lane import (
    HighDiskValidationSubmission,
    HighDiskValidationSuccess,
)
from .validation_sandbox_receipt import ValidationSandboxReceipt, command_sha256


DGX_VALIDATION_LANE_SERVICE = "ce-validation-lane.service"
DEFAULT_DROP_ROOT = Path("/var/lib/creator-engine/ce-validation-lane")
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_POLL_INTERVAL_SECONDS = 0.1
_REQUEST_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_FORBIDDEN_COMMAND_TERMS = ("authorization", "credential", "secret", "token")


class HighDiskValidationConsumerError(RuntimeError):
    """The fixed-purpose high-disk consumer could not prove a matching success."""


class HighDiskValidationConsumer(Protocol):
    """Only capability exposed to the local preflight caller."""

    def submit(self, submission: HighDiskValidationSubmission) -> HighDiskValidationSuccess: ...


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _submission_record(submission: HighDiskValidationSubmission) -> dict[str, object]:
    return {
        "repository": submission.repository,
        "base_sha": submission.base_sha,
        "head_sha": submission.head_sha,
        "expected_tree_sha": submission.expected_tree_sha,
        "sorted_carrier_digest": submission.sorted_carrier_digest,
        "validator_command": list(submission.validator_command),
        "validator_profile": submission.validator_profile,
        "policy_digest": submission.policy_digest,
        "image_digest": submission.image_digest,
        "minimum_headroom_gib": submission.minimum_headroom_gib,
        "venue_id": submission.venue_id,
    }


def canonical_submission_bytes(submission: HighDiskValidationSubmission) -> bytes:
    """Return the one canonical, credential-free submission representation."""

    _assert_submission_is_credential_free(submission)
    return _canonical_json(
        {
            "kind": "high-disk-validation-submission",
            "schema_version": "1",
            "submission": _submission_record(submission),
        }
    )


def _assert_submission_is_credential_free(submission: HighDiskValidationSubmission) -> None:
    for argument in submission.validator_command:
        if any(term in argument.lower() for term in _FORBIDDEN_COMMAND_TERMS):
            raise HighDiskValidationConsumerError(
                "high-disk validation command must not carry credential-like arguments"
            )


def _write_new_file(path: Path, content: bytes) -> None:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as exc:
        raise HighDiskValidationConsumerError(f"cannot create high-disk request file {path}: {exc}") from exc
    with os.fdopen(fd, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _require_directory(path: Path, *, description: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise HighDiskValidationConsumerError(f"{description} is unavailable at {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise HighDiskValidationConsumerError(f"{description} must be a non-symlink directory: {path}")


def _read_result(path: Path) -> bytes | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise HighDiskValidationConsumerError(f"cannot inspect high-disk result {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise HighDiskValidationConsumerError(f"high-disk result must be a regular non-symlink file: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise HighDiskValidationConsumerError(f"cannot read high-disk result {path}: {exc}") from exc


def _require_mapping(value: object, *, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise HighDiskValidationConsumerError(f"high-disk result {field_name} must be an object")
    return value


def _require_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise HighDiskValidationConsumerError(f"high-disk result {field_name} must be a string")
    return value


def _result_success(value: Mapping[str, object]) -> HighDiskValidationSuccess:
    required = {
        "repository",
        "base_sha",
        "head_sha",
        "tree_sha",
        "sorted_carrier_digest",
        "validator_command",
        "validator_profile",
        "policy_digest",
        "image_digest",
        "minimum_headroom_gib",
        "venue_id",
        "allocation_id",
        "receipt_bytes_b64",
        "receipt_sha256",
    }
    if set(value) != required:
        raise HighDiskValidationConsumerError("high-disk result success fields are malformed")
    command = value["validator_command"]
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise HighDiskValidationConsumerError("high-disk result validator_command must be a string list")
    minimum = value["minimum_headroom_gib"]
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
        raise HighDiskValidationConsumerError("high-disk result minimum_headroom_gib must be numeric")
    try:
        receipt_bytes = base64.b64decode(
            _require_string(value["receipt_bytes_b64"], field_name="success.receipt_bytes_b64"),
            validate=True,
        )
    except (ValueError, binascii.Error) as exc:
        raise HighDiskValidationConsumerError("high-disk result receipt_bytes_b64 is invalid") from exc
    receipt_sha256 = _require_string(value["receipt_sha256"], field_name="success.receipt_sha256")
    if hashlib.sha256(receipt_bytes).hexdigest() != receipt_sha256:
        raise HighDiskValidationConsumerError("high-disk result receipt digest does not match receipt bytes")
    try:
        return HighDiskValidationSuccess(
            repository=_require_string(value["repository"], field_name="success.repository"),
            base_sha=_require_string(value["base_sha"], field_name="success.base_sha"),
            head_sha=_require_string(value["head_sha"], field_name="success.head_sha"),
            tree_sha=_require_string(value["tree_sha"], field_name="success.tree_sha"),
            sorted_carrier_digest=_require_string(
                value["sorted_carrier_digest"], field_name="success.sorted_carrier_digest"
            ),
            validator_command=tuple(command),
            validator_profile=_require_string(value["validator_profile"], field_name="success.validator_profile"),
            policy_digest=_require_string(value["policy_digest"], field_name="success.policy_digest"),
            image_digest=_require_string(value["image_digest"], field_name="success.image_digest"),
            minimum_headroom_gib=float(minimum),
            venue_id=_require_string(value["venue_id"], field_name="success.venue_id"),
            allocation_id=_require_string(value["allocation_id"], field_name="success.allocation_id"),
            receipt_bytes=receipt_bytes,
            receipt_sha256=receipt_sha256,
        )
    except (TypeError, ValueError) as exc:
        raise HighDiskValidationConsumerError("high-disk result success is invalid") from exc


def _require_receipt_binding(
    receipt_bytes: bytes,
    submission: HighDiskValidationSubmission,
) -> None:
    try:
        payload = json.loads(receipt_bytes.decode("utf-8"))
        receipt = ValidationSandboxReceipt(**_require_mapping(payload, field_name="receipt"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HighDiskValidationConsumerError("high-disk result receipt is malformed") from exc
    expected = {
        "tree_sha": submission.expected_tree_sha,
        "command_sha256": command_sha256(submission.validator_command),
        "policy_sha": submission.policy_digest,
        "image_sha": submission.image_digest,
    }
    for field_name, expected_value in expected.items():
        if getattr(receipt, field_name) != expected_value:
            raise HighDiskValidationConsumerError(f"high-disk receipt {field_name} does not match submission")
    if receipt.returncode != 0:
        raise HighDiskValidationConsumerError("high-disk receipt records a nonzero return code")
    if receipt.egress_allowlist_applied or receipt.secret_allowlist_applied:
        raise HighDiskValidationConsumerError("high-disk receipt records egress or secret access")


def _require_matching_success(
    success: HighDiskValidationSuccess,
    submission: HighDiskValidationSubmission,
) -> None:
    expected = {
        "repository": submission.repository,
        "base_sha": submission.base_sha,
        "head_sha": submission.head_sha,
        "tree_sha": submission.expected_tree_sha,
        "sorted_carrier_digest": submission.sorted_carrier_digest,
        "validator_command": submission.validator_command,
        "validator_profile": submission.validator_profile,
        "policy_digest": submission.policy_digest,
        "image_digest": submission.image_digest,
        "minimum_headroom_gib": submission.minimum_headroom_gib,
        "venue_id": submission.venue_id,
    }
    for field_name, expected_value in expected.items():
        if getattr(success, field_name) != expected_value:
            raise HighDiskValidationConsumerError(f"high-disk success {field_name} does not match submission")
    if not success.allocation_id:
        raise HighDiskValidationConsumerError("high-disk success has no allocation identity")
    _require_receipt_binding(success.receipt_bytes, submission)


class AtomicFileDropHighDiskValidationConsumer:
    """Submit one canonical request to the DGX validation-lane file drop.

    The service watches ``incoming`` directories and publishes a same-ID JSON
    result under ``results``.  Directory rename makes the two request files
    visible together; no command, socket, SSH, or ambient environment is used.
    """

    def __init__(
        self,
        drop_root: Path = DEFAULT_DROP_ROOT,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        request_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        if timeout_seconds <= 0 or poll_interval_seconds <= 0:
            raise ValueError("high-disk validation timeout and polling interval must be positive")
        self._drop_root = Path(drop_root)
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._request_id_factory = request_id_factory

    def submit(self, submission: HighDiskValidationSubmission) -> HighDiskValidationSuccess:
        request_id = self._request_id_factory()
        if not _REQUEST_ID_RE.fullmatch(request_id):
            raise HighDiskValidationConsumerError("high-disk request identifier is malformed")
        incoming = self._drop_root / "incoming"
        results = self._drop_root / "results"
        _require_directory(incoming, description="high-disk incoming drop directory")
        _require_directory(results, description="high-disk result directory")
        request_path = incoming / request_id
        staging_path = incoming / f".{request_id}.tmp"
        if request_path.exists() or staging_path.exists():
            raise HighDiskValidationConsumerError("high-disk request identifier already exists")

        submission_bytes = canonical_submission_bytes(submission)
        bundle_bytes = _canonical_json(
            {
                "kind": "high-disk-validation-bundle",
                "schema_version": "1",
                "request_id": request_id,
                "submission_sha256": hashlib.sha256(submission_bytes).hexdigest(),
            }
        )
        try:
            staging_path.mkdir(mode=0o700)
            _write_new_file(staging_path / "submission.json", submission_bytes)
            _write_new_file(staging_path / "bundle.json", bundle_bytes)
            os.replace(staging_path, request_path)
        except HighDiskValidationConsumerError:
            shutil.rmtree(staging_path, ignore_errors=True)
            raise
        except OSError as exc:
            shutil.rmtree(staging_path, ignore_errors=True)
            raise HighDiskValidationConsumerError(f"cannot atomically publish high-disk request: {exc}") from exc

        result_path = results / f"{request_id}.json"
        deadline = self._clock() + self._timeout_seconds
        while True:
            result_bytes = _read_result(result_path)
            if result_bytes is not None:
                return self._parse_result(result_bytes, request_id, submission)
            if self._clock() >= deadline:
                raise HighDiskValidationConsumerError(
                    f"{DGX_VALIDATION_LANE_SERVICE} did not return a result before timeout"
                )
            self._sleeper(self._poll_interval_seconds)

    @staticmethod
    def _parse_result(
        result_bytes: bytes,
        request_id: str,
        submission: HighDiskValidationSubmission,
    ) -> HighDiskValidationSuccess:
        try:
            result = _require_mapping(json.loads(result_bytes.decode("utf-8")), field_name="root")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HighDiskValidationConsumerError("high-disk result is not valid JSON") from exc
        if set(result) != {"kind", "schema_version", "request_id", "status", "success"}:
            raise HighDiskValidationConsumerError("high-disk result fields are malformed")
        if result["kind"] != "high-disk-validation-result" or result["schema_version"] != "1":
            raise HighDiskValidationConsumerError("high-disk result kind or schema is unsupported")
        if result["request_id"] != request_id:
            raise HighDiskValidationConsumerError("high-disk result request identifier does not match")
        if result["status"] != "verified-success":
            raise HighDiskValidationConsumerError("high-disk validation did not report verified success")
        success = _result_success(_require_mapping(result["success"], field_name="success"))
        _require_matching_success(success, submission)
        return success


__all__ = [
    "AtomicFileDropHighDiskValidationConsumer",
    "DEFAULT_DROP_ROOT",
    "DGX_VALIDATION_LANE_SERVICE",
    "HighDiskValidationConsumer",
    "HighDiskValidationConsumerError",
    "canonical_submission_bytes",
]
