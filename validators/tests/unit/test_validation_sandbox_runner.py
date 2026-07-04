from __future__ import annotations

import dataclasses
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from creator_engine_validator import container_launcher
from creator_engine_validator.forge.authority_contexts import ValidationSandboxContext
from creator_engine_validator.validation_sandbox import ValidationSandboxSpec
from creator_engine_validator.validation_sandbox_receipt import (
    ValidationSandboxReceiptIssuer,
    command_sha256,
)
from creator_engine_validator.validation_sandbox_runner import (
    TMPFS_TMPDIR,
    run_validation_sandbox_in_container,
)


TREE_SHA = "1" * 40
POLICY_SHA = "a" * 64
IMAGE_SHA = "sha256:" + "b" * 64


@dataclass
class FakeCommandRunner:
    returncode: int = 0
    stdout: str = "ok\n"
    stderr: str = ""
    timeout: bool = False
    fail: Exception | None = None
    calls: list[tuple[list[str], float | None]] = field(default_factory=list)

    def podman_run_supports_timeout(self, binary: str) -> bool:
        return binary == "podman"

    def run(
        self,
        argv: list[str] | tuple[str, ...],
        *,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(argv), timeout))
        if argv[:3] == ["podman", "rm", "-f"]:
            return subprocess.CompletedProcess(list(argv), 0, "", "")
        if self.fail is not None:
            raise self.fail
        if self.timeout:
            raise subprocess.TimeoutExpired(list(argv), timeout or 0, output="partial", stderr="slow")
        return subprocess.CompletedProcess(list(argv), self.returncode, self.stdout, self.stderr)


@dataclass
class RecordingIssuer:
    inner: ValidationSandboxReceiptIssuer
    minted: int = 0

    def mint(self, **kwargs: Any):
        self.minted += 1
        return self.inner.mint(**kwargs)


def _context(tmp_path: Path) -> ValidationSandboxContext:
    return ValidationSandboxContext.from_sandbox(tmp_path / "validation-context")


def _spec(tmp_path: Path, *, timeout_seconds: float = 11) -> ValidationSandboxSpec:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return ValidationSandboxSpec(
        context=_context(tmp_path),
        command=("ce", "validate-pr", "--offline"),
        cwd=workspace,
        timeout_seconds=timeout_seconds,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path / "validation-context" / "home"),
            "XDG_CONFIG_HOME": str(tmp_path / "validation-context" / "xdg-config"),
            "CE_VALIDATION_ROLE": "verification",
            "CE_EGRESS_ALLOWED": "0",
        },
    )


def _policy_record(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "kind": "worker-container-policy-record",
        "record_type": "worker_container_policy",
        "schema_version": "1",
        "policy_id": "podman-verification-v1",
        "policy_sha": POLICY_SHA,
        "role": "verification",
        "runtime_engine": "podman-rootless",
        "image_ref": {"name": "ghcr.io/example/verification:latest", "sha": IMAGE_SHA},
        "mount_manifest": [{"path": "/worktrees/example", "mode": "ro"}],
        "egress_allowlist": [],
        "secret_allowlist": [],
        "grant_extensible": False,
        "grant_authority": "source",
    }
    record.update(overrides)
    return record


def _write_policy(tmp_path: Path, **overrides: Any) -> Path:
    path = tmp_path / "governance" / "policies" / "worker-container" / "podman-verification-v1.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(_policy_record(**overrides), sort_keys=True), encoding="utf-8")
    return path


def _issuer() -> ValidationSandboxReceiptIssuer:
    return ValidationSandboxReceiptIssuer(secret=b"test-secret", nonce_factory=lambda: "nonce-001")


def test_spec_maps_to_foreground_podman_argv_with_identical_readonly_mount_and_timeouts(tmp_path: Path):
    spec = _spec(tmp_path, timeout_seconds=11)
    runner = FakeCommandRunner()

    run = run_validation_sandbox_in_container(
        spec,
        tree_sha=TREE_SHA,
        policy_path=_write_policy(tmp_path),
        command_runner=runner,
        receipt_issuer=_issuer(),
        instance_id="validation-sandbox-test",
    )

    assert run.result.returncode == 0
    assert run.receipt is not None
    assert len(runner.calls) == 1
    argv, host_timeout = runner.calls[0]
    assert host_timeout == 11
    assert argv[:4] == ["podman", "run", "--rm", "--name"]
    assert "--timeout" in argv
    assert argv[argv.index("--timeout") + 1] == "11"
    assert argv[argv.index("--network") + 1] == "none"
    assert argv[argv.index("--workdir") + 1] == str(spec.cwd)
    assert argv[argv.index("-v") + 1] == f"{spec.cwd}:{spec.cwd}:ro"
    assert argv[argv.index("--tmpfs") + 1] == TMPFS_TMPDIR
    assert "--secret" not in argv
    assert argv[-4:] == ["ghcr.io/example/verification:latest@" + IMAGE_SHA, "ce", "validate-pr", "--offline"]
    assert "--env" in argv
    assert "CE_EGRESS_ALLOWED=0" in argv


def test_receipt_minted_only_after_observed_exit_and_binds_fields(tmp_path: Path):
    spec = _spec(tmp_path)
    runner = FakeCommandRunner(returncode=17, stdout="", stderr="failed\n")
    issuer = _issuer()

    run = run_validation_sandbox_in_container(
        spec,
        tree_sha=TREE_SHA,
        policy_path=_write_policy(tmp_path),
        command_runner=runner,
        receipt_issuer=issuer,
    )

    assert run.result.returncode == 17
    assert run.receipt is not None
    assert issuer.verify(run.receipt)
    assert run.receipt.tree_sha == TREE_SHA
    assert run.receipt.command_sha256 == command_sha256(spec.command)
    assert run.receipt.policy_sha == POLICY_SHA
    assert run.receipt.image_sha == IMAGE_SHA
    assert run.receipt.mount_manifest_applied == ((str(spec.cwd), "ro"),)
    assert run.receipt.egress_allowlist_applied == ()
    assert run.receipt.secret_allowlist_applied == ()
    assert run.receipt.returncode == 17


def test_receipt_hmac_verification_fails_after_any_field_tamper(tmp_path: Path):
    spec = _spec(tmp_path)
    issuer = _issuer()
    run = run_validation_sandbox_in_container(
        spec,
        tree_sha=TREE_SHA,
        policy_path=_write_policy(tmp_path),
        command_runner=FakeCommandRunner(),
        receipt_issuer=issuer,
    )

    assert run.receipt is not None
    assert issuer.verify(run.receipt)
    tampered = dataclasses.replace(run.receipt, returncode=99)
    assert not issuer.verify(tampered)


def test_no_receipt_is_minted_on_launcher_failure(tmp_path: Path):
    spec = _spec(tmp_path)
    issuer = RecordingIssuer(_issuer())

    with pytest.raises(OSError, match="podman unavailable"):
        run_validation_sandbox_in_container(
            spec,
            tree_sha=TREE_SHA,
            policy_path=_write_policy(tmp_path),
            command_runner=FakeCommandRunner(fail=OSError("podman unavailable")),
            receipt_issuer=issuer,  # type: ignore[arg-type]
        )

    assert issuer.minted == 0


def test_no_receipt_is_minted_on_timeout_and_host_timeout_is_propagated(tmp_path: Path):
    spec = _spec(tmp_path, timeout_seconds=7)
    issuer = RecordingIssuer(_issuer())
    runner = FakeCommandRunner(timeout=True)

    run = run_validation_sandbox_in_container(
        spec,
        tree_sha=TREE_SHA,
        policy_path=_write_policy(tmp_path),
        command_runner=runner,
        receipt_issuer=issuer,  # type: ignore[arg-type]
        instance_id="validation-timeout-test",
    )

    assert run.receipt is None
    assert run.result.returncode == container_launcher.PODMAN_TIMEOUT_RETURNCODE
    assert "timed out after 7s" in run.result.stderr
    assert runner.calls[0][1] == 7
    assert "--timeout" in runner.calls[0][0]
    assert runner.calls[0][0][runner.calls[0][0].index("--timeout") + 1] == "7"
    assert runner.calls[1][0] == ["podman", "rm", "-f", "validation-timeout-test"]
    assert issuer.minted == 0


def test_side_effect_ledger_record_is_appended_with_validation_sandbox_kind(tmp_path: Path):
    spec = _spec(tmp_path)
    calls: list[dict[str, Any]] = []

    def fake_record(**kwargs: Any) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(record_path=tmp_path / "ledger.json", record=kwargs)

    run = run_validation_sandbox_in_container(
        spec,
        tree_sha=TREE_SHA,
        policy_path=_write_policy(tmp_path),
        command_runner=FakeCommandRunner(),
        receipt_issuer=_issuer(),
        ledger_recorder=fake_record,
        controller_id="hermes-primary",
        lane_id="pco-slice8b",
        claim_ref="claims/hermes-primary/pco-slice8b.yaml",
        repo_root=tmp_path,
        side_effect_ledger_root=tmp_path / "side-effect-ledger",
        active_work_ledger_root=tmp_path / ".hermes" / "active-work-ledger",
        now=datetime(2026, 7, 4, 12, 0, 0, tzinfo=UTC),
    )

    assert run.side_effect_path == tmp_path / "ledger.json"
    assert len(calls) == 1
    call = calls[0]
    assert call["effect_kind"] == "validation_sandbox_run"
    assert call["effect_status"] == "succeeded"
    assert call["actor_role"] == "verification"
    assert call["subject_git_sha"] == TREE_SHA
    assert call["details"] == {
        "returncode": 0,
        "mount_count": 1,
        "egress_count": 0,
        "grant_count": 0,
    }
