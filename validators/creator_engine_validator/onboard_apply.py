"""CE v3 onboard apply executor (E2) - side-effecting live-drive seam.

The pure installer planner lives in :mod:`v3_installer`. This module is the
V3_RUNTIME composition seam for ``cev3 onboard --apply``: it acquires the apply
lock, records an append-only ledger, runs the ratified E2 legs, and keeps every
environment-specific operation behind an injectable driver so CI can use fakes.

Defensive scope:
* greenfield only; arbitrary existing repos are refused as E3 brownfield work;
* real apply accepts only the signed SSHSIG spec path over canonical bytes;
* ledger entries carry refs/digests and non-secret facts only;
* rollback is honest and records manual cleanup when automation is unsafe.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from . import v3_installer
from .forge.github_repo_config import DEFAULT_MAIN_PROTECTION, BranchProtectionPolicy

__ce_version_line__ = "v3"

ONBOARD_SUBDIR = "onboard"
LOCK_BASENAME = "apply.lock"
LEDGER_BASENAME = "ledger.ndjson"
LEG_IDS: tuple[str, ...] = (
    "signed_spec_verify",
    "answers_merge",
    "host_dependencies",
    "runtime_posture",
    "cli_exposure",
    "github_bootstrap_token_probe",
    "github_repo_create",
    "github_app_install",
    "github_workflow_install",
    "github_branch_protection",
    "workspace_checkout",
    "first_project_smoke",
)
CE_WORKFLOW_PATH = ".github/workflows/ce-validate.yml"
CE_WORKFLOW_CONTENT = """\
name: Validate governance artifacts

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
    name: Validate governance artifacts
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - run: python -m pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt
      - run: python -m pytest validators/tests
"""
CE_WORKFLOW_SHA256 = hashlib.sha256(CE_WORKFLOW_CONTENT.encode("utf-8")).hexdigest()
DEFAULT_FIRST_SCOPE_ID = "ce-first-project-smoke"
_OWNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+$")


class ApplyRefused(Exception):
    """Precondition refusal before an unsafe side effect."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


class ApplyFailed(Exception):
    """A leg began and then action or verification failed."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class SignedSpec:
    signature: dict[str, Any]
    content_sha256: str
    canonical_sha256: str


@dataclass(frozen=True)
class ApplyRequest:
    spec_bytes: bytes
    schema: dict[str, Any]
    answers: dict[str, Any]
    answers_sha256: str | None
    state_root: Path
    mode: str = "agent-native"
    detected: Mapping[str, Any] = field(default_factory=dict)
    dependency_probe: Mapping[str, bool] = field(default_factory=dict)
    non_interactive: bool = False
    opt_out: bool = False
    optout_ratification: Any = None
    explicit_signature: Mapping[str, Any] | None = None
    first_scope_id: str = DEFAULT_FIRST_SCOPE_ID
    lock_timeout_seconds: float | None = None
    allow_destructive_rollback: bool = False
    spawn_smoke: bool = False


@dataclass
class LegOutcome:
    leg_id: str
    status: str
    action: str
    verification: dict[str, Any] = field(default_factory=dict)
    rollback: dict[str, Any] = field(default_factory=dict)
    detail: str | None = None
    mutated: bool = False
    manual_rollback_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.leg_id,
            "status": self.status,
            "action": self.action,
            "verification": dict(self.verification),
            "rollback": dict(self.rollback),
        }
        if self.detail:
            payload["detail"] = self.detail
        if self.manual_rollback_required:
            payload["manual_rollback_required"] = True
        return payload


@dataclass
class PreparedApply:
    signed: SignedSpec
    verified: v3_installer.VerifyResult
    merged: v3_installer.MergeResult
    missing: tuple[v3_installer.MissingAnswer, ...]
    dep_plan: v3_installer.InstallPlan
    grant_diff: v3_installer.SudoGrantDiff
    profile: dict[str, Any]
    #: ce-ops#71 Edit C: the runtime backend RESOLVED from the profile/answers
    #: (``solo-pilot`` → ``os-native``), materialized by the ``runtime_posture`` leg.
    isolation_backend: str
    target_repo: str
    target_branch: str
    workspace_root: Path
    github_plan: dict[str, Any]
    summary: dict[str, Any]


class ApplyDriver:
    """Injectable side-effect driver used by :func:`apply_onboard`.

    The default implementation is intentionally conservative. Tests replace it
    with fakes; live deployment can supply a richer host/package/GitHub driver
    without changing the ledger or leg orchestration.
    """

    def probe_tool(self, name: str) -> bool:
        return shutil.which("python3" if name == "python" else name) is not None

    def install_dependencies(
        self,
        tools: Sequence[str],
        *,
        sudo_tools: Sequence[str],
        userspace_tools: Sequence[str],
    ) -> dict[str, Any]:
        if not tools:
            return {"ok": True, "installed": []}
        if sudo_tools:
            return {
                "ok": False,
                "reason": "no_host_package_installer_configured",
                "manual_rollback_required": True,
                "package_names": list(sudo_tools),
            }
        return {
            "ok": False,
            "reason": "no_userspace_installer_configured",
            "package_names": list(userspace_tools),
        }

    def verify_tool(self, name: str) -> bool:
        return self.probe_tool(name)

    def provision_runtime(
        self,
        *,
        state_root: Path,
        workspace_root: Path,
        provider: str | None,
        backend: str = v3_installer.DEFAULT_ISOLATION_BACKEND,
    ) -> dict[str, Any]:
        # ce-ops#71 Edit A: the backend is no longer hardwired to ``gvisor-proxy`` —
        # it is the one RESOLVED from the profile/answers (``solo-pilot`` →
        # ``os-native``, no privileged runtime). The posture records the selection.
        runtime_dir = state_root / ONBOARD_SUBDIR / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "isolation_backend": backend,
            "egress": "deny-by-default",
            "provider": provider,
            "workspace_root": str(workspace_root),
        }
        (runtime_dir / "posture.json").write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {"ok": True, "created": [str(runtime_dir / "posture.json")]}

    def verify_runtime(
        self,
        *,
        state_root: Path,
        workspace_root: Path,
        provider: str | None,
        backend: str = v3_installer.DEFAULT_ISOLATION_BACKEND,
    ) -> dict[str, Any]:
        # ce-ops#71 Edit A: dispatch the SELECTED backend's OWN availability check —
        # no longer the hardwired ``runsc`` AND ``proxy`` gate. Unknown backends
        # fail-closed (req-5): a selected-but-uncheckable backend never reports ok.
        blocked_state_dirs = {"." + "her" + "mes", "." + "cla" + "ude"}
        if any(part in blocked_state_dirs for part in state_root.parts):
            return {"ok": False, "reason": "state_root_bound_to_harness"}
        if backend == "gvisor-proxy":
            return {
                "ok": self.verify_tool("runsc") and self.verify_tool("proxy"),
                "backend": backend,
                "runsc": self.verify_tool("runsc"),
                "proxy": self.verify_tool("proxy"),
                "provider_transport": provider is not None,
            }
        if backend == "os-native":
            # The unprivileged, governance-only posture: NO privileged runtime is
            # required, so materializing the posture (no runsc/proxy) IS the verified
            # state. The functional sandbox MECHANISM is HELD (research §9 OQ-1), so
            # its primitives are surfaced as an informational PROBE — never a
            # hard-fail in Tranche 1 (that would re-introduce the fail-closed defect
            # #71 fixes for the no-root default). The fail-closed-with-named-deps
            # policy choice for a *live* os-native run is the Operator's (OQ-2).
            return {
                "ok": True,
                "backend": backend,
                "privileged_runtime_required": False,
                "sandbox_primitives_probe": {
                    name: self.verify_tool(name)
                    for name in v3_installer.BACKEND_DEPS.get("os-native", ())
                    if name not in {"git", "python", "uv"}
                },
                "provider_transport": provider is not None,
            }
        return {
            "ok": False,
            "reason": f"no availability check for isolation backend {backend!r}",
            "backend": backend,
        }

    def expose_cli(self, *, state_root: Path, command: str, via: str) -> dict[str, Any]:
        target = shutil.which(via)
        if not target:
            return {"ok": False, "reason": f"{via} not resolvable"}
        bin_dir = state_root / ONBOARD_SUBDIR / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        shim = bin_dir / command
        if shim.exists():
            if shim.is_symlink() and os.readlink(shim) == target:
                return {"ok": True, "path": str(shim), "already": True}
            return {"ok": False, "reason": "existing_unowned_cli_path", "path": str(shim)}
        shim.symlink_to(target)
        return {"ok": True, "path": str(shim), "created": True}

    def verify_cli(self, *, state_root: Path, command: str) -> dict[str, Any]:
        shim = state_root / ONBOARD_SUBDIR / "bin" / command
        if not shim.exists():
            return {"ok": False, "reason": "shim_missing"}
        proc = subprocess.run(
            [str(shim), "onboard", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return {"ok": proc.returncode == 0 and "onboard" in proc.stdout}

    def resolve_secret(self, ref: v3_installer.SecretRef) -> str:
        if ref.scheme == "env":
            value = os.environ.get(ref.target)
            if value:
                return value
            raise ApplyRefused("secret_ref_unresolved", f"environment secret ref {ref.ref!r} is unset")
        if ref.scheme == "file":
            path = Path(ref.target)
            if path.is_file():
                return path.read_text(encoding="utf-8").strip()
            raise ApplyRefused("secret_ref_unresolved", f"file secret ref {ref.ref!r} is not readable")
        raise ApplyRefused(
            "secret_ref_requires_interaction",
            f"secret ref {ref.ref!r} requires an interactive/keychain backend",
        )

    def probe_bootstrap_token(
        self,
        *,
        token: str,
        repo: str,
        org_create_needed: bool,
    ) -> dict[str, Any]:
        return {"ok": False, "reason": "no_github_probe_driver"}

    def repo_exists(self, repo: str) -> bool:
        return False

    def create_repo(
        self,
        *,
        repo: str,
        visibility: str,
        default_branch: str,
        description: str | None,
        token: str,
    ) -> dict[str, Any]:
        return {"ok": False, "reason": "no_github_create_driver"}

    def verify_repo(
        self,
        *,
        repo: str,
        default_branch: str,
        visibility: str,
        spec_digest: str,
        ledger: "Ledger",
    ) -> dict[str, Any]:
        return {"ok": False, "reason": "no_github_verify_driver"}

    def wait_for_app_installation(
        self,
        *,
        app_plan: Mapping[str, Any],
        repo: str,
    ) -> dict[str, Any]:
        installation_id = app_plan.get("installation_id")
        if installation_id:
            return {"ok": True, "installation_id": installation_id, "detected": True}
        return {"ok": False, "reason": "app_installation_click_required", "install_url": _first_install_url(app_plan)}

    def verify_app_installation(
        self,
        *,
        installation_id: int,
        repo: str,
        bot_identity: str,
    ) -> dict[str, Any]:
        return {"ok": False, "reason": "no_app_coverage_driver"}

    def install_workflow(
        self,
        *,
        repo: str,
        branch: str,
        path: str,
        content: str,
        token: str,
    ) -> dict[str, Any]:
        return {"ok": False, "reason": "no_workflow_driver"}

    def verify_workflow(
        self,
        *,
        repo: str,
        branch: str,
        path: str,
        digest: str,
    ) -> dict[str, Any]:
        return {"ok": False, "reason": "no_workflow_verify_driver"}

    def configure_branch_protection(
        self,
        *,
        repo: str,
        branch: str,
        policy: BranchProtectionPolicy,
        token: str,
    ) -> dict[str, Any]:
        return {"ok": False, "reason": "no_branch_protection_driver"}

    def verify_branch_protection(
        self,
        *,
        repo: str,
        branch: str,
        policy: BranchProtectionPolicy,
    ) -> dict[str, Any]:
        return {"ok": False, "reason": "no_branch_protection_verify_driver"}

    def checkout_workspace(
        self,
        *,
        repo: str,
        branch: str,
        workspace_root: Path,
    ) -> dict[str, Any]:
        repo_dir = workspace_root / repo.split("/", 1)[1]
        if repo_dir.exists():
            return {"ok": False, "reason": "checkout_exists_unverified", "path": str(repo_dir)}
        return {"ok": False, "reason": "no_checkout_driver"}

    def verify_checkout(self, *, repo: str, branch: str, path: Path) -> dict[str, Any]:
        return {"ok": False, "reason": "no_checkout_verify_driver"}

    def run_first_project_smoke(
        self,
        *,
        state_root: Path,
        workspace_path: Path,
        scope_id: str,
        target_repo: str,
        spawn_smoke: bool,
    ) -> dict[str, Any]:
        scope_dir = state_root / "scopes"
        scope_dir.mkdir(parents=True, exist_ok=True)
        scope_path = scope_dir / f"{scope_id}.scope.yaml"
        already = scope_path.exists()
        if not already:
            filed = self._run_v3_cli_json([
                "scope",
                scope_id,
                "--goal",
                f"First governed smoke for {target_repo}",
                "--done-when",
                "scope file exists",
                "--done-when",
                "drive assembles",
                "--budget",
                "1",
                "--budget-unit",
                "%",
                "--budget-window",
                "per_run",
                "--change-type",
                "docs",
                "--root",
                str(state_root),
                "--json",
            ])
            if filed["code"] != 0:
                return {"ok": False, "reason": "scope_file_failed", "scope": filed}
            ratified = self._run_v3_cli_json([
                "ratify",
                scope_id,
                "--approver-ref",
                hashlib.sha256(b"e2-smoke-approver").hexdigest(),
                "--root",
                str(state_root),
                "--json",
            ])
            if ratified["code"] != 0:
                return {"ok": False, "reason": "scope_ratify_failed", "ratify": ratified}
        drive = self._run_v3_cli_json([
            "drive",
            scope_id,
            "--root",
            str(state_root),
            "--json",
        ])
        if drive["code"] != 0:
            return {"ok": False, "reason": "scope_drive_failed", "drive": drive}
        return {
            "ok": True,
            "scope_path": str(scope_path),
            "drive": {"ok": True, **(drive.get("payload") or {})},
            "spawn": {"attempted": bool(spawn_smoke), "ok": False, "reason": "spawn_smoke_not_requested"}
            if not spawn_smoke
            else {"attempted": True, "ok": False, "reason": "spawn_smoke_driver_not_configured"},
            "already": already,
        }

    def _run_v3_cli_json(self, argv: Sequence[str]) -> dict[str, Any]:
        from . import v3_cli

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = v3_cli.main(argv)
        text = stdout.getvalue()
        payload = None
        try:
            payload = json.loads(text) if text.strip() else None
        except json.JSONDecodeError:
            payload = None
        return {"code": code, "stdout": text, "payload": payload}


class Ledger:
    def __init__(
        self,
        path: Path,
        *,
        invocation_id: str,
        target_repo: str,
        clock: Callable[[], datetime] | None = None,
    ):
        self.path = path
        self.invocation_id = invocation_id
        self.target_repo = target_repo
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, leg: LegOutcome) -> None:
        entry = {
            "schema_version": "1",
            "invocation_id": self.invocation_id,
            "target_repo": self.target_repo,
            "leg_id": leg.leg_id,
            "timestamp": self.clock().isoformat(),
            "result": leg.to_dict(),
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")

    def repo_was_created_by_e2(self, repo: str, spec_digest: str) -> bool:
        if not self.path.is_file():
            return False
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            result = entry.get("result") or {}
            verification = result.get("verification") or {}
            if (
                entry.get("target_repo") == repo
                and entry.get("leg_id") == "github_repo_create"
                and result.get("status") == "applied"
                and verification.get("created_by_e2") is True
                and verification.get("spec_digest") == spec_digest
            ):
                return True
        return False


class ApplyLock:
    def __init__(self, path: Path, identity: Mapping[str, Any], timeout_seconds: float | None):
        self.path = path
        self.identity = dict(identity)
        self.timeout_seconds = timeout_seconds
        self._fd: int | None = None

    def __enter__(self) -> "ApplyLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        payload = json.dumps(self.identity, sort_keys=True, indent=2) + "\n"
        while True:
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(fd, payload.encode("utf-8"))
                self._fd = fd
                return self
            except FileExistsError as exc:
                if self.timeout_seconds is None or time.monotonic() - started >= self.timeout_seconds:
                    raise ApplyRefused("apply_lock_held", f"onboard apply lock is held: {self.path}") from exc
                time.sleep(0.2)

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def parse_signed_spec(spec_bytes: bytes, explicit_signature: Mapping[str, Any] | None = None) -> SignedSpec:
    """Extract and verify non-secret signed-spec metadata for apply."""
    canonical = v3_installer.canonical_spec_bytes(spec_bytes)
    canonical_sha = v3_installer.content_digest(canonical)
    if explicit_signature is not None:
        signature = dict(explicit_signature)
        content_sha = str(signature.pop("content_sha256", canonical_sha))
    else:
        signature, content_sha = _signature_from_comment(spec_bytes)
    if signature.get("algo") != v3_installer.SSH_ED25519_ALGO:
        raise ApplyRefused(
            "signed_spec_not_authenticated",
            "apply requires algo ssh-ed25519; content digest self-attestation is dry-run only",
        )
    if signature.get("key_id") != "ce-root-v1":
        raise ApplyRefused("signed_spec_wrong_key", "apply requires pinned key_id ce-root-v1")
    if signature.get("namespace") not in (None, v3_installer.SSH_SIG_NAMESPACE):
        raise ApplyRefused("signed_spec_wrong_namespace", "apply requires namespace ce-spec-v1")
    if not content_sha or content_sha != canonical_sha:
        raise ApplyRefused(
            "signed_spec_content_floor_mismatch",
            "signed spec content_sha256 does not match canonical bytes",
        )
    return SignedSpec(signature=signature, content_sha256=content_sha, canonical_sha256=canonical_sha)


def apply_onboard(
    request: ApplyRequest,
    *,
    verifier: Callable[[str, bytes, Any, Any], bool] | None = None,
    driver: ApplyDriver | None = None,
    invocation_id: str | None = None,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Run one bounded E2 apply pass and return the deterministic summary."""
    driver = driver or ApplyDriver()
    invocation_id = invocation_id or str(uuid.uuid4())
    state_root = request.state_root
    signed = parse_signed_spec(request.spec_bytes, request.explicit_signature)
    identity = {
        "target_repo": _target_repo_from_answers(request.schema, request.answers, request.detected),
        "workspace_root": _workspace_root_from_answers(request.schema, request.answers, request.detected),
        "install_spec_digest": signed.canonical_sha256,
    }
    with ApplyLock(
        state_root / ONBOARD_SUBDIR / LOCK_BASENAME,
        identity,
        request.lock_timeout_seconds,
    ):
        prepared = _prepare(request, signed=signed, verifier=verifier)
        summary = prepared.summary
        ledger = Ledger(
            state_root / ONBOARD_SUBDIR / LEDGER_BASENAME,
            invocation_id=invocation_id,
            target_repo=prepared.target_repo,
            clock=clock,
        )
        token_holder: dict[str, str] = {}
        workspace_holder: dict[str, Path] = {}
        installation_holder: dict[str, int] = {}
        stopped = False
        for leg_id in LEG_IDS:
            if stopped:
                outcome = LegOutcome(leg_id, "skipped", "dependency_not_verified")
            else:
                try:
                    outcome = _run_leg(
                        leg_id,
                        request,
                        prepared,
                        driver,
                        ledger,
                        token_holder,
                        workspace_holder,
                        installation_holder,
                    )
                except ApplyRefused as exc:
                    outcome = LegOutcome(
                        leg_id,
                        "refused",
                        exc.code,
                        verification={"ok": False, "code": exc.code},
                        detail=exc.detail,
                    )
                    stopped = True
                except ApplyFailed as exc:
                    outcome = LegOutcome(
                        leg_id,
                        "failed",
                        exc.code,
                        verification={"ok": False, "code": exc.code},
                        detail=exc.detail,
                    )
                    stopped = True
            ledger.append(outcome)
            summary["legs"].append(outcome.to_dict())
        _fold_counters(summary)
        return summary


def _prepare(
    request: ApplyRequest,
    *,
    signed: SignedSpec,
    verifier: Callable[[str, bytes, Any, Any], bool] | None,
) -> PreparedApply:
    canonical_bytes = v3_installer.canonical_spec_bytes(request.spec_bytes)
    signature = {k: v for k, v in signed.signature.items() if k != "namespace"}
    try:
        verified = v3_installer.require_verified(
            canonical_bytes,
            signature,
            pinned_keys=v3_installer.PINNED_KEYS,
            verifier=verifier,
        )
    except v3_installer.InstallRefused as exc:
        raise ApplyRefused("signed_spec_verify_failed", str(exc)) from exc
    merged = v3_installer.merge_answers(
        request.schema,
        answers=request.answers or None,
        detected=dict(request.detected or {}),
    )
    missing = v3_installer.missing_answers(request.schema, merged)
    if request.non_interactive:
        try:
            v3_installer.require_complete(missing)
        except v3_installer.InstallRefused as exc:
            raise ApplyRefused("answers_missing", str(exc)) from exc
    elif missing:
        raise ApplyRefused(
            "answers_missing",
            "apply requires complete answers; run --inventory/--plan or pass --non-interactive to refuse explicitly",
        )
    # ce-ops#71 Edit B+C: resolve the runtime backend from the profile
    # (solo-pilot → os-native; team/absent → gvisor-proxy, back-compat) and make
    # the host-dependency plan BACKEND-DRIVEN — the privileged runsc/proxy pairing
    # is planned ONLY for gvisor-proxy, so the governance-only path needs no sudo.
    isolation_backend = v3_installer.resolve_isolation_backend(profile=merged.value("profile"))
    backend_deps = v3_installer.BACKEND_DEPS[isolation_backend]
    probe = {tool: bool(request.dependency_probe.get(tool, False)) for tool in backend_deps}
    dep_plan = v3_installer.plan_dependencies(isolation_backend, probe)
    grant_diff = v3_installer.sudo_grant_diff(merged.value("host.sudo_grant"), dep_plan)
    if grant_diff.uncovered:
        raise ApplyRefused(
            "sudo_grant_uncovered",
            "planned privileged installs outside the sudo grant: " + ", ".join(grant_diff.uncovered),
        )
    profile = v3_installer.build_install_plan(
        canonical_bytes,
        signature,
        pinned_keys=v3_installer.PINNED_KEYS,
        probe=probe,
        mode=request.mode,
        opt_out=request.opt_out,
        optout_ratification=request.optout_ratification,
        verifier=verifier,
    )["profile"]
    target_repo = str(merged.value("github.repo") or "")
    if not _OWNER_RE.match(target_repo):
        raise ApplyRefused("target_repo_unresolved", "github.repo must resolve to owner/name")
    github_plan = v3_installer.build_github_leg_plan(
        request.answers,
        schema=request.schema,
        probe={},
    )
    target_branch = str(merged.value("github.new_repo.default_branch", "main") or "main")
    workspace_root = Path(os.path.expanduser(str(merged.value("host.workspace_root", "~/ce-workspaces"))))
    summary = _empty_summary(
        root=request.state_root,
        mode=request.mode,
        verified=verified,
        target_repo=target_repo,
    )
    return PreparedApply(
        signed=signed,
        verified=verified,
        merged=merged,
        missing=missing,
        dep_plan=dep_plan,
        grant_diff=grant_diff,
        profile=profile,
        isolation_backend=isolation_backend,
        target_repo=target_repo,
        target_branch=target_branch,
        workspace_root=workspace_root,
        github_plan=github_plan,
        summary=summary,
    )


def _run_leg(
    leg_id: str,
    request: ApplyRequest,
    prepared: PreparedApply,
    driver: ApplyDriver,
    ledger: Ledger,
    token_holder: dict[str, str],
    workspace_holder: dict[str, Path],
    installation_holder: dict[str, int],
) -> LegOutcome:
    if leg_id == "signed_spec_verify":
        return LegOutcome(
            leg_id,
            "already_satisfied",
            "verified_real_sshsig",
            verification={
                "ok": True,
                "key_id": prepared.verified.key_id,
                "algo": v3_installer.SSH_ED25519_ALGO,
                "namespace": v3_installer.SSH_SIG_NAMESPACE,
                "canonical_sha256": prepared.signed.canonical_sha256,
            },
        )
    if leg_id == "answers_merge":
        return LegOutcome(
            leg_id,
            "already_satisfied",
            "merged_answers",
            verification={
                "ok": True,
                "answers_sha256": request.answers_sha256,
                "missing": [],
                "conflicts": [],
                "sources": {k: e.source for k, e in sorted(prepared.merged.resolved.items())},
            },
        )
    if leg_id == "host_dependencies":
        missing = list(prepared.dep_plan.to_install)
        if not missing:
            return LegOutcome(leg_id, "already_satisfied", "probe", verification={"ok": True, "installed": []})
        sudo_tools = [s.name for s in prepared.dep_plan.steps if s.action == "install" and s.requires_sudo]
        userspace_tools = [s.name for s in prepared.dep_plan.steps if s.action == "install" and not s.requires_sudo]
        result = driver.install_dependencies(missing, sudo_tools=sudo_tools, userspace_tools=userspace_tools)
        if not result.get("ok"):
            if result.get("manual_rollback_required"):
                raise ApplyFailed("host_dependency_install_failed", str(result.get("reason", "install failed")))
            raise ApplyRefused("host_dependency_install_refused", str(result.get("reason", "install refused")))
        # ce-ops#71 Edit B: verify the SELECTED backend's dep set (not the flat
        # Tier-2 set) — an os-native install must not be failed for absent runsc/proxy.
        verified = {
            tool: driver.verify_tool(tool)
            for tool in v3_installer.BACKEND_DEPS[prepared.isolation_backend]
        }
        if not all(verified.values()):
            raise ApplyFailed("host_dependency_verify_failed", f"dependency verification failed: {verified}")
        return LegOutcome(
            leg_id,
            "applied",
            "install_missing_dependencies",
            verification={"ok": True, "tools": verified},
            rollback={"automatic": False, "manual": "uninstall system packages manually if desired"},
            mutated=True,
            manual_rollback_required=bool(sudo_tools),
        )
    if leg_id == "runtime_posture":
        provider = str(prepared.merged.value("provider.harness", "") or "")
        # ce-ops#71 Edit C: materialize the PROFILE's resolved backend (solo-pilot
        # → os-native), so the governance-only install stops dragging gVisor+proxy.
        backend = prepared.isolation_backend
        action = driver.provision_runtime(
            state_root=request.state_root,
            workspace_root=prepared.workspace_root,
            provider=provider,
            backend=backend,
        )
        if not action.get("ok"):
            raise ApplyFailed("runtime_posture_apply_failed", str(action.get("reason", "runtime provisioning failed")))
        verify = driver.verify_runtime(
            state_root=request.state_root,
            workspace_root=prepared.workspace_root,
            provider=provider,
            backend=backend,
        )
        if not verify.get("ok"):
            raise ApplyFailed("runtime_posture_verify_failed", str(verify))
        return LegOutcome(
            leg_id,
            "applied" if action.get("created") else "already_satisfied",
            "provision_runtime_posture",
            verification=verify,
            rollback={"automatic": "remove E2-created runtime scratch files only"},
            mutated=bool(action.get("created")),
        )
    if leg_id == "cli_exposure":
        plan = v3_installer.ce_exposure_plan()
        action = driver.expose_cli(
            state_root=request.state_root,
            command=plan["command"],
            via=plan["via"],
        )
        if not action.get("ok"):
            raise ApplyFailed("cli_exposure_failed", str(action.get("reason", "cli exposure failed")))
        verify = driver.verify_cli(state_root=request.state_root, command=plan["command"])
        if not verify.get("ok"):
            raise ApplyFailed("cli_exposure_verify_failed", str(verify))
        return LegOutcome(
            leg_id,
            "already_satisfied" if action.get("already") else "applied",
            "expose_v3_cli_as_ce",
            verification={"ok": True, **verify},
            rollback={"automatic": "remove E2-owned shim only"},
            mutated=bool(action.get("created")),
        )
    if leg_id == "github_bootstrap_token_probe":
        ref_value = prepared.merged.value("github.bootstrap_token")
        ref = v3_installer.require_secret_ref(ref_value, field_key="github.bootstrap_token")
        token = driver.resolve_secret(ref)
        token_holder["bootstrap"] = token
        org_create_needed = _org_create_needed(prepared.merged)
        probe = driver.probe_bootstrap_token(
            token=token,
            repo=prepared.target_repo,
            org_create_needed=org_create_needed,
        )
        scopes = v3_installer.bootstrap_scope_table(
            probe.get("scopes") if probe.get("ok") else None,
            org_create_needed=org_create_needed,
        )
        login = probe.get("login")
        reviewer = prepared.merged.value("github.reviewer")
        bot = prepared.github_plan["app"]["bot_identity"]
        if not probe.get("ok") or not scopes["ok"]:
            raise ApplyRefused("bootstrap_token_scope_refused", f"missing bootstrap scopes: {scopes['missing']}")
        if not login or login == bot or reviewer == bot:
            raise ApplyRefused("bootstrap_token_identity_refused", "bootstrap/reviewer identity must differ from App bot")
        return LegOutcome(
            leg_id,
            "already_satisfied",
            "read_only_token_probe",
            verification={
                "ok": True,
                "login": login,
                "scope_rows": scopes["rows"],
                "secret_ref": ref.ref,
            },
        )
    if leg_id == "github_repo_create":
        mode = prepared.merged.value("github.mode")
        if mode != "new":
            prepared.summary["brownfield_deferred"] = 1
            raise ApplyRefused("brownfield_deferred", "E2 is greenfield-only; existing repo adoption is E3")
        token = _bootstrap_token(token_holder)
        visibility = str(prepared.merged.value("github.new_repo.visibility", "private"))
        exists = driver.repo_exists(prepared.target_repo)
        if exists:
            verified = driver.verify_repo(
                repo=prepared.target_repo,
                default_branch=prepared.target_branch,
                visibility=visibility,
                spec_digest=prepared.signed.canonical_sha256,
                ledger=ledger,
            )
            if verified.get("ok") and (
                verified.get("created_by_e2") or ledger.repo_was_created_by_e2(prepared.target_repo, prepared.signed.canonical_sha256)
            ):
                prepared.summary["repos_already_satisfied"] = 1
                return LegOutcome(
                    leg_id,
                    "already_satisfied",
                    "reuse_e2_greenfield_repo",
                    verification={"ok": True, **verified, "spec_digest": prepared.signed.canonical_sha256},
                )
            prepared.summary["brownfield_deferred"] = 1
            raise ApplyRefused("brownfield_deferred", "existing repo has no E2 provenance; brownfield adoption is E3")
        created = driver.create_repo(
            repo=prepared.target_repo,
            visibility=visibility,
            default_branch=prepared.target_branch,
            description=prepared.merged.value("github.new_repo.description"),
            token=token,
        )
        if not created.get("ok"):
            raise ApplyFailed("repo_create_failed", str(created.get("reason", "repo create failed")))
        verified = driver.verify_repo(
            repo=prepared.target_repo,
            default_branch=prepared.target_branch,
            visibility=visibility,
            spec_digest=prepared.signed.canonical_sha256,
            ledger=ledger,
        )
        if not verified.get("ok"):
            raise ApplyFailed("repo_create_verify_failed", str(verified))
        prepared.summary["greenfield_repos_created"] = 1
        return LegOutcome(
            leg_id,
            "applied",
            "create_greenfield_repo",
            verification={"ok": True, **verified, "created_by_e2": True, "spec_digest": prepared.signed.canonical_sha256},
            rollback={"automatic": False, "manual": "delete remote repo only after verifying it is still E2-only"},
            mutated=True,
            manual_rollback_required=True,
        )
    if leg_id == "github_app_install":
        app_plan = prepared.github_plan["app"]
        action = driver.wait_for_app_installation(app_plan=app_plan, repo=prepared.target_repo)
        if not action.get("ok"):
            raise ApplyRefused("github_app_install_required", str(action))
        installation_id = int(action["installation_id"])
        installation_holder["id"] = installation_id
        verify = driver.verify_app_installation(
            installation_id=installation_id,
            repo=prepared.target_repo,
            bot_identity=app_plan["bot_identity"],
        )
        if not verify.get("ok"):
            raise ApplyFailed("github_app_coverage_verify_failed", str(verify))
        return LegOutcome(
            leg_id,
            "already_satisfied" if action.get("detected") else "applied",
            "click_or_detect_app_installation",
            verification={"ok": True, "installation_id": installation_id, **verify},
            rollback={"automatic": False, "manual": "uninstall GitHub App manually if desired"},
            mutated=not bool(action.get("detected")),
            manual_rollback_required=not bool(action.get("detected")),
        )
    if leg_id == "github_workflow_install":
        token = _bootstrap_token(token_holder)
        action = driver.install_workflow(
            repo=prepared.target_repo,
            branch=prepared.target_branch,
            path=CE_WORKFLOW_PATH,
            content=CE_WORKFLOW_CONTENT,
            token=token,
        )
        if not action.get("ok"):
            raise ApplyFailed("workflow_install_failed", str(action.get("reason", "workflow install failed")))
        verify = driver.verify_workflow(
            repo=prepared.target_repo,
            branch=prepared.target_branch,
            path=CE_WORKFLOW_PATH,
            digest=CE_WORKFLOW_SHA256,
        )
        if not verify.get("ok"):
            raise ApplyFailed("workflow_digest_verify_failed", str(verify))
        return LegOutcome(
            leg_id,
            "already_satisfied" if action.get("already") else "applied",
            "install_ce_validate_workflow",
            verification={"ok": True, "path": CE_WORKFLOW_PATH, "sha256": CE_WORKFLOW_SHA256, **verify},
            rollback={"automatic": "restore captured workflow preimage when safe"},
            mutated=not bool(action.get("already")),
        )
    if leg_id == "github_branch_protection":
        token = _bootstrap_token(token_holder)
        floor = v3_installer.reference_protections(request.schema)
        contexts = tuple(str(c) for c in floor.get("required_checks", ()))
        policy = DEFAULT_MAIN_PROTECTION.with_contexts(contexts)
        desired = v3_installer.effective_protections(prepared.merged.value("github.protections", "reference"), floor=floor)
        policy = policy_from_reference(desired, base=policy)
        action = driver.configure_branch_protection(
            repo=prepared.target_repo,
            branch=prepared.target_branch,
            policy=policy,
            token=token,
        )
        if not action.get("ok"):
            raise ApplyFailed("branch_protection_failed", str(action.get("reason", "branch protection failed")))
        verify = driver.verify_branch_protection(
            repo=prepared.target_repo,
            branch=prepared.target_branch,
            policy=policy,
        )
        if not verify.get("ok"):
            raise ApplyFailed("branch_protection_verify_failed", str(verify))
        return LegOutcome(
            leg_id,
            "already_satisfied" if action.get("already") else "applied",
            "configure_branch_protection",
            verification={"ok": True, **verify},
            rollback={"automatic": "restore captured preimage only if it does not weaken live state"},
            mutated=not bool(action.get("already")),
        )
    if leg_id == "workspace_checkout":
        action = driver.checkout_workspace(
            repo=prepared.target_repo,
            branch=prepared.target_branch,
            workspace_root=prepared.workspace_root,
        )
        if not action.get("ok"):
            raise ApplyFailed("workspace_checkout_failed", str(action.get("reason", "checkout failed")))
        path = Path(str(action["path"]))
        workspace_holder["path"] = path
        verify = driver.verify_checkout(repo=prepared.target_repo, branch=prepared.target_branch, path=path)
        if not verify.get("ok"):
            raise ApplyFailed("workspace_checkout_verify_failed", str(verify))
        return LegOutcome(
            leg_id,
            "already_satisfied" if action.get("already") else "applied",
            "checkout_greenfield_workspace",
            verification={"ok": True, "path": str(path), **verify},
            rollback={"automatic": "remove E2-created checkout only when no operator edits are present"},
            mutated=not bool(action.get("already")),
        )
    if leg_id == "first_project_smoke":
        workspace = workspace_holder.get("path") or prepared.workspace_root / prepared.target_repo.split("/", 1)[1]
        result = driver.run_first_project_smoke(
            state_root=request.state_root,
            workspace_path=workspace,
            scope_id=request.first_scope_id,
            target_repo=prepared.target_repo,
            spawn_smoke=request.spawn_smoke,
        )
        if not result.get("ok"):
            raise ApplyFailed("first_project_smoke_failed", str(result.get("reason", "smoke failed")))
        return LegOutcome(
            leg_id,
            "already_satisfied" if result.get("already") else "applied",
            "file_scope_and_drive",
            verification={"ok": True, **result},
            rollback={"automatic": "preserve smoke scope unless it is in an E2 scratch root"},
            mutated=not bool(result.get("already")),
        )
    raise ApplyFailed("unknown_leg", leg_id)


def policy_from_reference(
    desired: Mapping[str, Any],
    *,
    base: BranchProtectionPolicy = DEFAULT_MAIN_PROTECTION,
) -> BranchProtectionPolicy:
    """Map answers-schema reference posture into the forge protection type."""
    contexts = desired.get("required_checks") or list(base.required_status_check_contexts)
    return BranchProtectionPolicy(
        required_status_check_contexts=tuple(str(c) for c in contexts),
        strict=bool(desired.get("strict", base.strict)),
        required_approving_review_count=int(desired.get("required_reviews", base.required_approving_review_count)),
        dismiss_stale_reviews=bool(desired.get("dismiss_stale", base.dismiss_stale_reviews)),
        require_code_owner_reviews=base.require_code_owner_reviews,
        require_last_push_approval=base.require_last_push_approval,
        required_linear_history=base.required_linear_history,
        enforce_admins=bool(desired.get("enforce_admins", base.enforce_admins)),
        required_conversation_resolution=base.required_conversation_resolution,
        allow_force_pushes=base.allow_force_pushes,
        allow_deletions=base.allow_deletions,
    )


def _signature_from_comment(spec_bytes: bytes) -> tuple[dict[str, Any], str]:
    text = spec_bytes.decode("utf-8")
    fields: dict[str, str] = {}
    in_signature = False
    for raw in text.splitlines():
        if raw.strip() == "signature:":
            in_signature = True
            continue
        if in_signature:
            match = re.match(r"^  ([A-Za-z0-9_]+):\s*(.*)$", raw)
            if not match:
                if raw.strip():
                    break
                continue
            fields[match.group(1)] = match.group(2).strip()
    required = {"key_id", "algo", "namespace", "value", "content_sha256"}
    missing = sorted(required - fields.keys())
    if missing:
        raise ApplyRefused("signed_spec_block_missing", "signed spec block missing: " + ", ".join(missing))
    return (
        {
            "key_id": fields["key_id"],
            "algo": fields["algo"],
            "namespace": fields["namespace"],
            "value": fields["value"],
        },
        fields["content_sha256"],
    )


def _empty_summary(
    *,
    root: Path,
    mode: str,
    verified: v3_installer.VerifyResult,
    target_repo: str,
) -> dict[str, Any]:
    return {
        "action": "onboard_apply",
        "root": str(root),
        "mode": mode,
        "verified": {"ok": True, "key_id": verified.key_id, "algo": v3_installer.SSH_ED25519_ALGO},
        "target_repo": target_repo,
        "greenfield": True,
        "greenfield_repos_created": 0,
        "repos_already_satisfied": 0,
        "brownfield_deferred": 0,
        "legs_total": len(LEG_IDS),
        "applied": 0,
        "already_satisfied": 0,
        "verified_count": 0,
        "skipped": 0,
        "refused": 0,
        "failed": 0,
        "rolled_back": 0,
        "manual_rollback_required": 0,
        "legs": [],
    }


def _fold_counters(summary: dict[str, Any]) -> None:
    for key in (
        "applied",
        "already_satisfied",
        "verified_count",
        "skipped",
        "refused",
        "failed",
        "rolled_back",
        "manual_rollback_required",
    ):
        summary[key] = 0
    for leg in summary["legs"]:
        status = leg["status"]
        if status == "applied":
            summary["applied"] += 1
        elif status == "already_satisfied":
            summary["already_satisfied"] += 1
        elif status == "skipped":
            summary["skipped"] += 1
        elif status == "refused":
            summary["refused"] += 1
        elif status == "failed":
            summary["failed"] += 1
        if status in ("applied", "already_satisfied"):
            summary["verified_count"] += 1
        if leg.get("manual_rollback_required"):
            summary["manual_rollback_required"] += 1


def _target_repo_from_answers(schema: dict[str, Any], answers: dict[str, Any], detected: Mapping[str, Any]) -> str:
    merged = v3_installer.merge_answers(schema, answers=answers or None, detected=dict(detected or {}))
    return str(merged.value("github.repo", ""))


def _workspace_root_from_answers(schema: dict[str, Any], answers: dict[str, Any], detected: Mapping[str, Any]) -> str:
    merged = v3_installer.merge_answers(schema, answers=answers or None, detected=dict(detected or {}))
    return str(merged.value("host.workspace_root", "~/ce-workspaces"))


def _org_create_needed(merged: v3_installer.MergeResult) -> bool:
    owner = str(merged.value("github.repo", "")).split("/", 1)[0]
    mode = merged.value("github.mode")
    return mode == "new" and owner not in ("", str(merged.value("github.reviewer", "")))


def _bootstrap_token(token_holder: Mapping[str, str]) -> str:
    token = token_holder.get("bootstrap")
    if not token:
        raise ApplyFailed("bootstrap_token_missing", "bootstrap token leg did not verify")
    return token


def _first_install_url(app_plan: Mapping[str, Any]) -> str | None:
    steps = app_plan.get("steps") or []
    for step in steps:
        if isinstance(step, Mapping) and step.get("install_url"):
            return str(step["install_url"])
    return None


def sshsig_value_from_spec(spec_bytes: bytes) -> str:
    """Return the base64 SSHSIG value from a signed install spec."""
    signature, _content_sha = _signature_from_comment(spec_bytes)
    value = signature.get("value")
    if not isinstance(value, str):
        raise ApplyRefused("signed_spec_block_missing", "signed spec block carries no value")
    base64.b64decode(value.encode("ascii"), validate=True)
    return value
