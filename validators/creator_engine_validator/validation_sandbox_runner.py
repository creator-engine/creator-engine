"""Containerized production runner for the frozen validation_sandbox seam."""

from __future__ import annotations

import hashlib
import importlib
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import container_launcher
from .checks.worker_container_policy import validate_worker_container_policy
from .forge.authority_contexts import require_no_credential_env
from .loader import LoaderError, load_yaml
from .validation_sandbox import ValidationSandboxResult, ValidationSandboxSpec
from .validation_sandbox_receipt import (
    ValidationSandboxReceipt,
    ValidationSandboxReceiptIssuer,
)


DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "governance"
    / "policies"
    / "worker-container"
    / "podman-verification-v1.yaml"
)
TMPFS_TMPDIR = "/tmp:rw,nosuid,nodev,noexec"


class ValidationSandboxRunnerError(RuntimeError):
    """Containerized validation-sandbox runner failed before a receipt was minted."""


class ValidationSandboxPolicyError(ValidationSandboxRunnerError):
    """The selected worker-container policy is not the ratified verification policy."""


@dataclass(frozen=True)
class ValidationSandboxContainerRun:
    """Container run result plus optional receipt and side-effect ledger evidence."""

    result: ValidationSandboxResult
    receipt: ValidationSandboxReceipt | None
    side_effect_path: Path | None = None
    side_effect_record: dict[str, Any] | None = None


LedgerRecorder = Callable[..., Any]


def _utc_now_str(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_ledger_recorder() -> LedgerRecorder:
    module = importlib.import_module("creator_engine_validator.side_effect_ledger_runtime")
    return module.record


def _load_verification_policy(policy_path: Path | str) -> dict[str, Any]:
    path = Path(policy_path)
    try:
        policy = load_yaml(path)
    except LoaderError as exc:
        raise ValidationSandboxPolicyError(f"policy at {path} is unreadable: {exc}") from exc
    if not isinstance(policy, dict):
        raise ValidationSandboxPolicyError(f"policy at {path} is not a mapping")
    errors = validate_worker_container_policy(policy, path)
    if errors:
        raise ValidationSandboxPolicyError(
            f"policy at {path} fails validation: " + "; ".join(error.format() for error in errors)
        )
    if policy.get("policy_id") != "podman-verification-v1":
        raise ValidationSandboxPolicyError("validation sandbox requires podman-verification-v1 policy")
    if policy.get("role") != "verification":
        raise ValidationSandboxPolicyError("validation sandbox policy must be role=verification")
    if policy.get("runtime_engine") != "podman-rootless":
        raise ValidationSandboxPolicyError("validation sandbox policy must use podman-rootless")
    if policy.get("egress_allowlist") not in ([], None):
        raise ValidationSandboxPolicyError("validation sandbox policy must declare empty egress")
    if policy.get("secret_allowlist") not in ([], None):
        raise ValidationSandboxPolicyError("validation sandbox policy must declare empty secrets")
    return policy


def _workspace_mount(cwd: Path) -> dict[str, str]:
    if not cwd.is_absolute():
        raise ValidationSandboxRunnerError(f"validation sandbox cwd must be absolute: {cwd}")
    return {"path": str(cwd), "mode": "ro"}


def _effect_id(receipt: ValidationSandboxReceipt) -> str:
    digest = hashlib.sha256(receipt.nonce.encode("utf-8")).hexdigest()[:16]
    return f"validation-sandbox-run-{digest}"


def _record_validation_sandbox_run(
    *,
    receipt: ValidationSandboxReceipt,
    result: ValidationSandboxResult,
    controller_id: str,
    lane_id: str,
    claim_ref: str,
    repo_root: Path | str,
    side_effect_ledger_root: Path | str,
    active_work_ledger_root: Path | str,
    recorder: LedgerRecorder,
    now: datetime | None,
) -> Any:
    return recorder(
        controller_id=controller_id,
        lane_id=lane_id,
        claim_ref=claim_ref,
        effect_id=_effect_id(receipt),
        effect_kind="validation_sandbox_run",
        effect_status="succeeded" if result.returncode == 0 else "failed",
        summary=f"validation sandbox exited with returncode {result.returncode}",
        occurred_at=_utc_now_str(now),
        repo_root=repo_root,
        side_effect_ledger_root=side_effect_ledger_root,
        active_work_ledger_root=active_work_ledger_root,
        actor_role="verification",
        subject_git_sha=receipt.tree_sha,
        details={
            "returncode": result.returncode,
            "mount_count": len(receipt.mount_manifest_applied),
            "egress_count": len(receipt.egress_allowlist_applied),
            "grant_count": len(receipt.secret_allowlist_applied),
        },
        now=now,
    )


def _maybe_record_ledger(
    *,
    receipt: ValidationSandboxReceipt,
    result: ValidationSandboxResult,
    controller_id: str | None,
    lane_id: str | None,
    claim_ref: str | None,
    repo_root: Path | str | None,
    side_effect_ledger_root: Path | str | None,
    active_work_ledger_root: Path | str | None,
    ledger_recorder: LedgerRecorder,
    now: datetime | None,
) -> tuple[Path | None, dict[str, Any] | None]:
    ledger_args = (
        controller_id,
        lane_id,
        claim_ref,
        repo_root,
        side_effect_ledger_root,
        active_work_ledger_root,
    )
    if all(value is None for value in ledger_args):
        return None, None
    if any(value is None for value in ledger_args):
        raise ValidationSandboxRunnerError("side-effect ledger recording requires all ledger binding arguments")
    ledger_result = _record_validation_sandbox_run(
        receipt=receipt,
        result=result,
        controller_id=str(controller_id),
        lane_id=str(lane_id),
        claim_ref=str(claim_ref),
        repo_root=repo_root or "",
        side_effect_ledger_root=side_effect_ledger_root or "",
        active_work_ledger_root=active_work_ledger_root or "",
        recorder=ledger_recorder,
        now=now,
    )
    return getattr(ledger_result, "record_path", None), getattr(ledger_result, "record", None)


def run_validation_sandbox_in_container(
    spec: ValidationSandboxSpec,
    *,
    tree_sha: str,
    policy_path: Path | str = DEFAULT_POLICY_PATH,
    command_runner: container_launcher.CommandRunner | None = None,
    receipt_issuer: ValidationSandboxReceiptIssuer | None = None,
    ledger_recorder: LedgerRecorder | None = None,
    controller_id: str | None = None,
    lane_id: str | None = None,
    claim_ref: str | None = None,
    repo_root: Path | str | None = None,
    side_effect_ledger_root: Path | str | None = None,
    active_work_ledger_root: Path | str | None = None,
    instance_id: str | None = None,
    now: datetime | None = None,
) -> ValidationSandboxContainerRun:
    """Run ``ValidationSandboxSpec`` in the verification Podman policy container."""

    if not isinstance(spec, ValidationSandboxSpec):
        raise TypeError("run_validation_sandbox_in_container requires ValidationSandboxSpec")
    require_no_credential_env(spec.env, context_name="ValidationSandboxSpec")
    policy = _load_verification_policy(policy_path)
    image_ref = policy["image_ref"]
    timeout_seconds = int(math.ceil(spec.timeout_seconds))
    mount = _workspace_mount(spec.cwd)
    env_items = tuple(sorted((str(key), str(value)) for key, value in spec.env.items()))

    start = time.monotonic()
    run_result = container_launcher.run_foreground_podman(
        image_name=image_ref["name"],
        image_sha=image_ref["sha"],
        command=tuple(spec.command),
        timeout_seconds=timeout_seconds,
        network_mode="none",
        mounts=(mount,),
        workdir=str(spec.cwd),
        env=env_items,
        tmpfs=(TMPFS_TMPDIR,),
        secret_grants=(),
        instance_id=instance_id,
        runner=command_runner,
    )
    result = ValidationSandboxResult(
        run_result.returncode,
        run_result.stdout,
        run_result.stderr,
        time.monotonic() - start,
        spec,
    )
    if run_result.timed_out:
        return ValidationSandboxContainerRun(result=result, receipt=None)

    issuer = receipt_issuer or ValidationSandboxReceiptIssuer()
    receipt = issuer.mint(
        tree_sha=tree_sha,
        command=spec.command,
        policy_sha=policy["policy_sha"],
        image_sha=image_ref["sha"],
        mount_manifest_applied=(mount,),
        egress_allowlist_applied=(),
        secret_allowlist_applied=(),
        returncode=run_result.returncode,
    )
    side_effect_path, side_effect_record = _maybe_record_ledger(
        receipt=receipt,
        result=result,
        controller_id=controller_id,
        lane_id=lane_id,
        claim_ref=claim_ref,
        repo_root=repo_root,
        side_effect_ledger_root=side_effect_ledger_root,
        active_work_ledger_root=active_work_ledger_root,
        ledger_recorder=ledger_recorder or _default_ledger_recorder(),
        now=now,
    )
    return ValidationSandboxContainerRun(
        result=result,
        receipt=receipt,
        side_effect_path=side_effect_path,
        side_effect_record=side_effect_record,
    )


__all__ = [
    "DEFAULT_POLICY_PATH",
    "TMPFS_TMPDIR",
    "ValidationSandboxContainerRun",
    "ValidationSandboxPolicyError",
    "ValidationSandboxRunnerError",
    "run_validation_sandbox_in_container",
]
