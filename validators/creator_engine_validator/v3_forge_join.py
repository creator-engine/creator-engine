"""v3.1-G2a/G2c — the forge-leg composition root joining the G1 dispatch to the forge.

G1 stops at a governed seat that AUTHORS a branch locally and is push-denied. The forge legs
(``forge.change_push`` / ``forge.open_change`` / ``forge.merge`` / ``forge.mint_scoped_token`` /
``run_assembly.make_merge_driver``) all EXIST and are all v3, but nothing reaches them from the
``cev3`` spine. This module is that single composition root — the place where the seat's dispatch
state meets the forge:

* :func:`load_app_config` reads the host GitHub-App config AS DATA (instance-local, outside the
  repo; the verified ``~/.ce-keys/ce-forge-app.json`` convention) — fail-closed on
  missing/malformed/missing fields. NOTHING from it except shape-safe facts (the repo) ever reaches
  a record; the App ids / pem path never do.
* :func:`openssl_signer` is the FIRST production RS256 signer for ``forge.app_jwt_gh_runner`` — an
  ``openssl dgst -sha256 -sign`` subprocess with the signing input on STDIN, so the App private key
  NEVER enters the v3 process. Injected runner seam; CI fakes it.
* :func:`open_change_for_run` is the G2a ship leg — preconditions (the dispatch exists, was actually
  spawned, is not spawn-failure-stamped, carries no prior ``change`` block) BEFORE any forge call,
  then mint→push→open under a JIT, least-privilege, time-boxed token revoked in a ``finally`` (the
  ``run_assembly`` discipline). It stamps a value-free ``change`` block onto ``dispatch.yaml``.
* :func:`merge_for_run` (G2c) is the gated-merge leg — it mirrors
  ``run_assembly.make_merge_driver``'s composition (reconstruct the ChangeRef from the
  ``pr_opened`` change_set → gated ``forge.merge`` under a DISTINCT identity →
  ``orchestrator.merge_change`` persist) while ALSO surfacing the ``MergeResult`` gate snapshot the
  plan-mode CLI needs (the driver returns only ``CollectedEvidence``).

**The v1⊥v3 boundary.** This module imports ``forge.*`` / ``run_assembly`` / ``orchestrator`` —
all v3 — and imports **NO v1 module** (``test_v3_forge_join`` asserts this off the AST). The join
is a pure v3→v3 composition; no boundary is crossed.

Secret hygiene (load-bearing): the JIT token VALUE lives only in the child ``gh``/``git`` env (the
``credential_runner`` / ``change_push`` pattern); the App PRIVATE KEY lives only behind the
``openssl`` subprocess (the ``app_jwt_runner`` ``Signer`` seam). Neither ever enters the argv, a
log, the returned objects, disk, or any record. Network/subprocess/crypto only behind injectable
seams; CI drives fakes with zero live git/gh/openssl/HTTPS. Importing this module performs no I/O
and registers no validator check.

Defensive only — it ships our own governed seat's reviewed work through our own forge; never
offensive.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .checks import path_manifest_fidelity
from .evidence_sink import file_evidence_sink
from .forge.app_jwt_runner import Signer, app_jwt_gh_runner
from .forge.change import ChangeRef, open_change
from .forge.change_push import push_change
from .forge.change_status import pr_state
from .forge.credential_runner import authenticated_gh_runner
from .forge.github_repo_config import ForgeConfigError, GhRunner
from .forge.auto_merge import AutoMergeResult, enable_auto_merge
from .forge.merge import MergeResult, merge
from .forge import re_review
from .forge.review_submit import ReviewResult, submit_review
from .forge.review_submission_receipt import ReviewSubmissionReceipt, ReviewSubmissionReceiptAuthority
from .forge.reviewer_terminal import ReviewerTerminal, ReviewerTerminalRefused, require_reviewed_terminal
from .forge.scoped_token import (
    ScopedToken,
    TokenRequest,
    mint_scoped_token,
    revoke_scoped_token,
)
from .runner.backend import CollectedEvidence
from .runtime_evidence_spine import RUN_OUTCOME_RECORD_TYPE, append as _spine_append
from .sec7_forge_guard import sec7_forge_refusal

#: The verified live host App-config convention (instance-local, outside the repo). The
#: ``--app-config`` flag is REQUIRED on ``cev3 pr`` (host filenames differ); this is documentation
#: of the shape, not a silent default the CLI applies.
DEFAULT_APP_CONFIG_PATH = "~/.ce-keys/ce-forge-app.json"
#: Documentation-only reviewer config convention. The CLI requires an explicit path so host-local
#: reviewer credentials cannot be silently confused with the author App.
DEFAULT_REVIEWER_APP_CONFIG_PATH = "~/.ce-keys/agent-reviewer-app.json"

#: The CE repo the PR is opened against — constant across the org's hosts (the host-bound facts are
#: the App credential + reviewer identity, NOT the repo). A config may override it via a ``repo`` key.
DEFAULT_REPO = "creator-engine/creator-engine"

#: The dispatch-state subdir under the v3 local-state ``root`` (mirrors ``v3_seat_bridge`` /
#: ``v3_cli``; replicated locally to avoid coupling to either module).
DISPATCHES_SUBDIR = "dispatches"
#: The run-evidence subdir under the v3 local-state ``root`` (the persisted chains).
RUNS_SUBDIR = "runs"

#: The EXACT least-privilege permission set a PR-open per-run credential requests — never broader.
PR_TOKEN_PERMISSIONS: dict[str, str] = {"contents": "write", "pull_requests": "write"}
#: ce-ops#88 — under the ceiling-driven three-tier minter, ``contents:write`` is an
#: escalation-gated grant (default-DENY). The PR-open flow's authority to push a branch is
#: NOT new: it is the already-ratified, orchestrator-gated per-run deploy authority
#: ([[ce-push-deploy-authority-model]]) the run is provisioned under. We make that authority
#: EXPLICIT here so the mint passes the new single enforcement point WITHOUT widening it —
#: ``pull_requests:write`` stays a Tier-3 baseline grant and needs no escalation entry.
PR_TOKEN_ESCALATION_AUTHORITY: tuple[tuple[str, str], ...] = (("contents", "write"),)
#: The PR-open credential time-box (<= the 1h ceiling, well under it — a PR-open is seconds of work).
PR_TOKEN_TTL_SECONDS = 900
#: The logical secret name the per-run PR credential satisfies.
PR_SECRET_NAME = "forge_pr_open"

#: D1/P1 — a merge token, when a caller explicitly chooses to mint one, must carry only
#: ``contents:write``. The default merge path still uses the injected/ambient runner and
#: mints no token in P1.
MERGE_TOKEN_PERMISSIONS: dict[str, str] = {"contents": "write"}
MERGE_TOKEN_ESCALATION_AUTHORITY: tuple[tuple[str, str], ...] = (("contents", "write"),)
MERGE_TOKEN_TTL_SECONDS = 900
MERGE_SECRET_NAME = "forge_merge"

#: D3/P1 — the independent reviewer App may only approve PRs. It must never carry
#: ``contents:write`` or any escalation authority.
REVIEWER_TOKEN_PERMISSIONS: dict[str, str] = {"pull_requests": "write"}
REVIEWER_TOKEN_ESCALATION_AUTHORITY: tuple[tuple[str, str], ...] = ()
REVIEWER_TOKEN_TTL_SECONDS = 900
REVIEWER_SECRET_NAME = "forge_review_submit"

#: D4/P1 — per-PR auto-merge needs PR write plus Contents write; only Contents is Tier-2.
AUTO_MERGE_TOKEN_PERMISSIONS: dict[str, str] = {
    "contents": "write",
    "pull_requests": "write",
}
AUTO_MERGE_TOKEN_ESCALATION_AUTHORITY: tuple[tuple[str, str], ...] = (("contents", "write"),)
AUTO_MERGE_TOKEN_TTL_SECONDS = 900
AUTO_MERGE_SECRET_NAME = "forge_auto_merge"

#: D2/D4 repo configuration writes are repo-administration writes, bound per operation.
REPO_ADMIN_TOKEN_PERMISSIONS: dict[str, str] = {"administration": "write"}
REPO_ADMIN_TOKEN_ESCALATION_AUTHORITY: tuple[tuple[str, str], ...] = (
    ("administration", "write"),
)
REPO_ADMIN_TOKEN_TTL_SECONDS = 900
REPO_ADMIN_SECRET_NAME = "forge_repo_admin"

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

# ---------------------------------------------------------------------------
# F6 Phase-0 two-tier change-block re-stamp — record kinds/types + carrier dir
# ---------------------------------------------------------------------------
#: The F6 base-only re-stamp record (the ONLY machine authority for base-only
#: merge-head movement) and the F6 squash tree-equivalence merge-audit record.
#: Defined HERE (not in the record-agnostic spine — the closed manifest excludes
#: the spine): the schema validates the shape and ``verify_chain`` is record-type
#: agnostic (content-address + chain-link + sequence + policy-binding apply
#: uniformly), so no spine/check logic changes.
CHANGE_RESTAMP_RECORD_KIND = "runtime-change-restamp"
CHANGE_RESTAMP_RECORD_TYPE = "runtime_change_restamp"
MERGE_AUDIT_RECORD_KIND = "runtime-merge-audit"
MERGE_AUDIT_RECORD_TYPE = "runtime_merge_audit"

#: The per-PR carrier directory (mirror of ``path_manifest_fidelity.MANIFEST_DIR``).
#: A carrier path is MECHANICAL metadata (it records base/head/restamp prose), so
#: it is EXCLUDED from the content-diff identity; its PATH-SET is proved unchanged
#: structurally via ``path_manifest_fidelity.parse_carrier`` instead.
CARRIER_DIR = path_manifest_fidelity.MANIFEST_DIR

#: The F6 ``head_status`` vocabulary surfaced by ``merge_for_run`` (plan + apply).
HEAD_UNCHANGED = "unchanged"
HEAD_BASE_ONLY_RESTAMP = "base_only_restamp_available"
HEAD_BASE_ONLY_RESTAMPED = "base_only_restamped"
HEAD_CONTENT_DRIFT = "content_drift_refused"
HEAD_LEGACY_UNPROVABLE = "legacy_unprovable"

#: The F6 refusal-reason codes (the value-free refusal taxonomy; never an override).
RESTAMP_CONTENT_DRIFT_CODE = "content_drift_requires_reratification"
RESTAMP_LEGACY_UNPROVABLE_CODE = "restamp_legacy_unprovable"


class ForgeJoinRefused(Exception):
    """Fail-closed refusal in the forge-leg composition (value-free; never a half-open)."""


# ---------------------------------------------------------------------------
# Host App config — read AS DATA (instance-local; ids never reach a record)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AppConfig:
    """The host GitHub-App config, read AS DATA from instance-local state.

    ``client_id`` / ``installation_id`` / ``pem_path`` are host-bound App identity used ONLY to
    mint+sign — they NEVER reach a record. ``repo`` is the shape-safe fact (owner/name) that may.
    ``permissions`` documents the App's installed grant (informational; the mint requests the fixed
    least-privilege subset, never this whole set).
    """

    client_id: str
    installation_id: int
    pem_path: str
    repo: str
    permissions: tuple[tuple[str, str], ...]

    def __repr__(self) -> str:  # keep host App ids out of incidental log/repr surfaces
        return (
            f"AppConfig(repo={self.repo!r}, pem_path=<host-local>, "
            f"client_id=<redacted>, installation_id=<redacted>)"
        )

    __str__ = __repr__


def load_app_config(path: str | Path = DEFAULT_APP_CONFIG_PATH) -> AppConfig:
    """Read the host App config JSON AS DATA; fail-closed on missing/malformed/missing fields.

    Required fields: ``client_id`` (non-empty), ``installation_id`` (a positive int), ``pem_path``
    (non-empty; ``~`` expanded), ``permissions`` (a mapping). ``repo`` is optional (defaults to the
    canonical CE repo). The file is instance-local host state; this never copies the App ids into a
    record.
    """
    cfg_path = Path(path).expanduser()
    if not cfg_path.is_file():
        raise ForgeJoinRefused(
            f"App config not found at {cfg_path} (pass --app-config; host filenames differ — "
            f"laptop ce-forge-app.json, CE-DEV-1 ce-forge-dev1.json)"
        )
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ForgeJoinRefused(f"App config at {cfg_path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ForgeJoinRefused(f"App config at {cfg_path} must be a JSON object")

    client_id = str(data.get("client_id") or "").strip()
    if not client_id:
        raise ForgeJoinRefused(f"App config at {cfg_path} is missing 'client_id'")
    raw_inst = data.get("installation_id")
    try:
        installation_id = int(raw_inst)
    except (TypeError, ValueError):
        raise ForgeJoinRefused(
            f"App config at {cfg_path} 'installation_id' must be an integer (got {raw_inst!r})"
        ) from None
    if installation_id <= 0:
        raise ForgeJoinRefused(f"App config at {cfg_path} 'installation_id' must be positive")
    pem_path = str(data.get("pem_path") or "").strip()
    if not pem_path:
        raise ForgeJoinRefused(f"App config at {cfg_path} is missing 'pem_path'")
    pem_path = str(Path(pem_path).expanduser())
    repo = str(data.get("repo") or DEFAULT_REPO).strip()
    if not _REPO_RE.match(repo):
        raise ForgeJoinRefused(f"App config at {cfg_path} 'repo' {repo!r} is not in owner/name form")
    perms_raw = data.get("permissions") or {}
    if not isinstance(perms_raw, Mapping):
        raise ForgeJoinRefused(f"App config at {cfg_path} 'permissions' must be a mapping")
    permissions = tuple(sorted((str(k), str(v)) for k, v in perms_raw.items()))
    return AppConfig(
        client_id=client_id,
        installation_id=installation_id,
        pem_path=pem_path,
        repo=repo,
        permissions=permissions,
    )


def load_reviewer_app_config(path: str | Path = DEFAULT_REVIEWER_APP_CONFIG_PATH) -> AppConfig:
    """Read the separate reviewer App config.

    This intentionally reuses :func:`load_app_config`'s shape checks while keeping a distinct
    call site/flag in the CLI. The reviewer App must be a separate identity and its token
    requests are constrained by :data:`REVIEWER_TOKEN_PERMISSIONS`.
    """
    return load_app_config(path)


# ---------------------------------------------------------------------------
# The production RS256 signer — the App private key stays behind openssl
# ---------------------------------------------------------------------------
def openssl_signer(
    pem_path: str | Path, *, runner: Callable[..., Any] = subprocess.run
) -> Signer:
    """Return the FIRST production RS256 :data:`~.forge.app_jwt_runner.Signer` for App-JWT minting.

    Signs the JWT signing input by execing ``openssl dgst -sha256 -sign <pem_path>`` with the input
    on STDIN and capturing the raw signature bytes from STDOUT — the **PEM never enters the v3
    process** (openssl reads the file itself). A non-zero exit is a fail-closed
    :class:`ForgeJoinRefused` (value-free). ``runner`` is the injectable subprocess seam (CI fakes
    it → zero live openssl).
    """
    pem = str(pem_path)

    def sign(signing_input: bytes) -> bytes:
        proc = runner(
            ["openssl", "dgst", "-sha256", "-sign", pem],
            input=signing_input,
            capture_output=True,
        )
        if getattr(proc, "returncode", 1) != 0:
            raise ForgeJoinRefused(
                "openssl RS256 signing failed (the App private key is unreadable or invalid); "
                "refusing to mint"
            )
        signature = getattr(proc, "stdout", b"") or b""
        if not signature:
            raise ForgeJoinRefused("openssl produced an empty RS256 signature; refusing to mint")
        return signature

    return sign


# ---------------------------------------------------------------------------
# Policy SHA — the canonical derivation (reused by v3_cli; never duplicated)
# ---------------------------------------------------------------------------
def policy_sha(policy: dict[str, Any]) -> str:
    """The 64-hex policy binding for a run's records (the canonical derivation).

    Uses the policy's own ``policy_sha`` when it is a valid 64-hex digest, else derives a
    deterministic SHA256 over the canonical policy body. ``v3_cli._policy_sha`` delegates here so
    the derivation lives in exactly one place.
    """
    existing = policy.get("policy_sha")
    if isinstance(existing, str) and _HEX64_RE.match(existing):
        return existing
    body = {k: v for k, v in policy.items() if k != "policy_sha"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Dispatch-state seam (read AS DATA; the change block stamped value-free)
# ---------------------------------------------------------------------------
def _dispatch_path(root: Path, run_id: str) -> Path:
    return root / DISPATCHES_SUBDIR / run_id / "dispatch.yaml"


def _load_dispatch(root: Path, run_id: str) -> dict[str, Any]:
    path = _dispatch_path(root, run_id)
    if not path.is_file():
        raise ForgeJoinRefused(f"no dispatch record for run {run_id!r} under {root / DISPATCHES_SUBDIR}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ForgeJoinRefused(f"malformed dispatch record at {path}")
    return data


def _write_dispatch(root: Path, run_id: str, data: dict[str, Any]) -> None:
    _dispatch_path(root, run_id).write_text(
        yaml.safe_dump(data, sort_keys=True, default_flow_style=False), encoding="utf-8"
    )


def _read_policy(dispatch: dict[str, Any]) -> dict[str, Any]:
    """Read the run's ``runtime-policy.yaml`` AS DATA (for the policy_sha binding)."""
    ref = dispatch.get("runtime_policy_ref")
    if ref and Path(ref).is_file():
        loaded = yaml.safe_load(Path(ref).read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
    return {}


def _assert_openable(dispatch: dict[str, Any], run_id: str) -> None:
    """Refuse BEFORE any forge call unless the dispatch is a clean, spawned, un-stamped run."""
    if dispatch.get("spawn_failed_at"):
        raise ForgeJoinRefused(
            f"run {run_id!r} is spawn-failure-stamped; refusing to open a PR for a run that never "
            "became a live seat"
        )
    if not (dispatch.get("spawned_at") or dispatch.get("terminal")):
        raise ForgeJoinRefused(
            f"run {run_id!r} was never spawned (no spawned_at/terminal); refusing to open a PR "
            "for a run that did not happen"
        )
    if dispatch.get("change"):
        raise ForgeJoinRefused(
            f"run {run_id!r} already carries a stamped change block; refusing to re-open "
            "(a PR is claimed once per run)"
        )


def _utcstamp_iso(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_mint_runner(app_config: AppConfig) -> GhRunner:  # pragma: no cover - the live App-JWT path
    """The production App-JWT mint runner: Bearer-JWT over HTTPS, signed by openssl (PEM off-process)."""
    return app_jwt_gh_runner(
        app_config.client_id, signer=openssl_signer(app_config.pem_path)
    )


def _default_reviewer_mint_runner(app_config: AppConfig) -> GhRunner:  # pragma: no cover
    """Production App-JWT mint runner for the separate reviewer App identity."""
    return _default_mint_runner(app_config)


def mint_operation_token(
    app_config: AppConfig,
    *,
    run_id: str,
    policy_sha_value: str,
    permissions: Mapping[str, str],
    secret_name: str,
    requested_ttl_seconds: int,
    escalation_authority: tuple[tuple[str, str], ...] = (),
    mint_gh_runner: GhRunner | None = None,
) -> ScopedToken:
    """Mint one operation-scoped App token using an explicit minimal permission set."""
    request = TokenRequest(
        repo=app_config.repo,
        installation_id=app_config.installation_id,
        run_id=run_id,
        policy_sha=policy_sha_value,
        permissions=permissions,
        secret_name=secret_name,
        requested_ttl_seconds=requested_ttl_seconds,
        escalation_authority=escalation_authority,
    )
    mint_runner = mint_gh_runner if mint_gh_runner is not None else _default_mint_runner(app_config)
    return mint_scoped_token(request, gh_runner=mint_runner)


def _change_from_dispatch(root: Path, run_id: str, repo: str) -> tuple[ChangeRef, str]:
    dispatch = _load_dispatch(root, run_id)
    change = dispatch.get("change") or {}
    pr_number = change.get("pr_number")
    head_sha = str(change.get("head_sha") or "").strip()
    if not pr_number or not head_sha:
        raise ForgeJoinRefused(
            f"run {run_id!r} has no opened PR change block with pr_number/head_sha"
        )
    branch = str(change.get("branch") or run_id)
    base = str(change.get("base") or "main")
    manifest_paths = tuple(str(p) for p in (change.get("manifest_paths") or ()))
    plan_ref = policy_sha(_read_policy(dispatch))
    return (
        ChangeRef(
            repo=repo, branch=branch, base=base, pr_number=int(pr_number),
            head_sha=head_sha, manifest_paths=manifest_paths, plan_ref=plan_ref,
            changed=True, applied=True, verified=True,
        ),
        plan_ref,
    )


def _revoke_best_effort(token: ScopedToken, *, token_spawn: Any = None) -> None:
    try:
        revoke_scoped_token(token, gh_runner=authenticated_gh_runner(token, spawn=token_spawn))
    except ForgeConfigError:
        logging.getLogger(__name__).warning(
            "scoped-token revoke failed for run %s (token_ref %s); it will expire on its ttl",
            token.run_id,
            token.token_ref,
        )


def submit_review_for_run(
    root: Path | str,
    run_id: str,
    *,
    reviewer_app_config: AppConfig,
    apply: bool = False,
    body: str = "",
    terminal: ReviewerTerminal | dict | str | None = None,
    receipt: ReviewSubmissionReceipt | dict | None = None,
    receipt_authority: ReviewSubmissionReceiptAuthority | None = None,
    mint_gh_runner: GhRunner | None = None,
    token_spawn: Any = None,
    sec7_context: object | None = None,
) -> ReviewResult:
    """Mint reviewer-App token -> submit independent APPROVE for the run's opened PR."""
    refusal = sec7_forge_refusal("review-submit", sec7_context)
    if refusal is not None:
        raise ForgeJoinRefused(refusal)
    root = Path(root)
    change, plan_ref = _change_from_dispatch(root, run_id, reviewer_app_config.repo)
    # Admission precedes operation-token minting.  A v1/prose result must never
    # cause a reviewer credential to be minted merely to discover it is invalid.
    try:
        require_reviewed_terminal(
            terminal if terminal is not None else body, repository=change.repo,
            pr_number=change.pr_number, head_sha=change.head_sha, event="APPROVE",
        )
    except ReviewerTerminalRefused as exc:
        raise ForgeJoinRefused(f"review terminal admission refused: {exc}") from exc
    if apply and (receipt is None or receipt_authority is None):
        raise ForgeJoinRefused("review submission requires parser-issued receipt authority and receipt")
    token = mint_operation_token(
        reviewer_app_config,
        run_id=run_id,
        policy_sha_value=plan_ref,
        permissions=REVIEWER_TOKEN_PERMISSIONS,
        secret_name=REVIEWER_SECRET_NAME,
        requested_ttl_seconds=REVIEWER_TOKEN_TTL_SECONDS,
        escalation_authority=REVIEWER_TOKEN_ESCALATION_AUTHORITY,
        mint_gh_runner=(
            mint_gh_runner
            if mint_gh_runner is not None
            else _default_reviewer_mint_runner(reviewer_app_config)
        ),
    )
    try:
        return submit_review(
            change,
            body=body,
            terminal=terminal,
            receipt=receipt,
            receipt_authority=receipt_authority,
            apply=apply,
            gh_runner=authenticated_gh_runner(token, spawn=token_spawn),
        )
    finally:
        _revoke_best_effort(token, token_spawn=token_spawn)


def enable_auto_merge_for_run(
    root: Path | str,
    run_id: str,
    *,
    app_config: AppConfig,
    method: str = "squash",
    apply: bool = False,
    mint_gh_runner: GhRunner | None = None,
    token_spawn: Any = None,
    sec7_context: object | None = None,
) -> AutoMergeResult:
    """Mint author-App token -> enable GraphQL auto-merge for the run's opened PR."""
    refusal = sec7_forge_refusal("auto-merge", sec7_context)
    if refusal is not None:
        raise ForgeJoinRefused(refusal)
    root = Path(root)
    change, plan_ref = _change_from_dispatch(root, run_id, app_config.repo)
    token = mint_operation_token(
        app_config,
        run_id=run_id,
        policy_sha_value=plan_ref,
        permissions=AUTO_MERGE_TOKEN_PERMISSIONS,
        secret_name=AUTO_MERGE_SECRET_NAME,
        requested_ttl_seconds=AUTO_MERGE_TOKEN_TTL_SECONDS,
        escalation_authority=AUTO_MERGE_TOKEN_ESCALATION_AUTHORITY,
        mint_gh_runner=mint_gh_runner,
    )
    try:
        return enable_auto_merge(
            change,
            method=method,
            apply=apply,
            gh_runner=authenticated_gh_runner(token, spawn=token_spawn),
        )
    finally:
        _revoke_best_effort(token, token_spawn=token_spawn)


def open_change_for_run(
    root: Path | str,
    run_id: str,
    *,
    app_config: AppConfig,
    branch: str,
    manifest_paths: Sequence[str],
    base: str = "main",
    source_dir: str | Path = ".",
    apply: bool = False,
    mint_gh_runner: GhRunner | None = None,
    git_spawn: Any = None,
    token_spawn: Any = None,
    git_identity_runner: GitRunner | None = None,
    now: datetime | None = None,
) -> ChangeRef:
    """Mint→push→open one PR for a governed seat's authored branch (plan-by-default).

    Fail-closed preconditions FIRST (dispatch exists, was spawned, not spawn-failure-stamped, no
    prior ``change`` block). Then, under a JIT, least-privilege (``contents:write`` +
    ``pull_requests:write``), <=900s token minted via the App-JWT runner and REVOKED in a
    ``finally`` (best-effort, authenticated AS the token): :func:`~.forge.change_push.push_change`
    pushes the branch (apply-gated, never force) and :func:`~.forge.change.open_change` claims its
    PR. With ``apply=True`` the value-free ``change`` block
    (``branch``/``base``/``pr_number``/``head_sha``/``manifest_paths``/``opened_at`` — shape refs
    only) is stamped onto ``dispatch.yaml``; plan mode (``apply=False``) reads state and mutates
    nothing. Every network/crypto seam is injectable; CI drives fakes with zero live I/O.

    F6 Phase-0: when a ``git_identity_runner`` is supplied (production wires the local-checkout git
    seam), the stamped change block ALSO carries the value-free re-stamp anchor — ``base_sha`` plus
    the change identity (``head_tree_sha`` / ``content_diff_id`` / ``patch_id_stable`` /
    ``manifest_paths_sha256`` / ``proof_inputs_sha256``) — so a later base-only motion can be
    machine-proved instead of re-adopted. Without the seam the block conserves its pre-F6 shape (a
    chain that lacks ``base_sha`` is treated as legacy-unprovable at merge, NEVER overridden).
    """
    root = Path(root)
    dispatch = _load_dispatch(root, run_id)
    _assert_openable(dispatch, run_id)
    paths = tuple(manifest_paths or ())
    if not paths:
        raise ForgeJoinRefused(f"run {run_id!r} PR-open requires a non-empty manifest path-set")

    policy = _read_policy(dispatch)
    plan_ref = policy_sha(policy)
    repo = app_config.repo

    request = TokenRequest(
        repo=repo,
        installation_id=app_config.installation_id,
        run_id=run_id,
        policy_sha=plan_ref,
        permissions=PR_TOKEN_PERMISSIONS,
        secret_name=PR_SECRET_NAME,
        requested_ttl_seconds=PR_TOKEN_TTL_SECONDS,
        escalation_authority=PR_TOKEN_ESCALATION_AUTHORITY,
    )
    mint_runner = mint_gh_runner if mint_gh_runner is not None else _default_mint_runner(app_config)
    token = mint_scoped_token(request, gh_runner=mint_runner)
    try:
        # 1) push the authored branch to the CONSTRUCTED HTTPS remote (apply-gated, never force).
        push_change(
            repo, branch, source_dir=source_dir, token=token, apply=apply, spawn=git_spawn,
        )
        # 2) claim exactly one PR for it (authenticated AS the minted token; value in env only).
        authed = authenticated_gh_runner(token, spawn=token_spawn)
        ref = open_change(repo, branch, base, paths, plan_ref, apply=apply, gh_runner=authed)
        # 3) on a REAL apply (a PR exists), stamp the value-free change block; plan mode mutates nothing.
        if apply and getattr(ref, "pr_number", None) is not None:
            change_block: dict[str, Any] = {
                "branch": branch,
                "base": base,
                "pr_number": ref.pr_number,
                "head_sha": ref.head_sha,
                "manifest_paths": list(paths),
                "opened_at": _utcstamp_iso(now),
            }
            # F6: stamp the value-free re-stamp anchor (base_sha + change identity) when the git
            # seam is available. Best-effort — an unresolved ref leaves the pre-F6 shape intact.
            if git_identity_runner is not None:
                change_block.update(_open_identity_fields(git_identity_runner, base, ref.head_sha, paths))
            dispatch["change"] = change_block
            _write_dispatch(root, run_id, dispatch)
        return ref
    finally:
        # Defense-in-depth: release the credential the instant the open ends — success OR failure —
        # rather than waiting out its ttl. DELETE /installation/token authenticates AS the token, so
        # route the revoke through an authenticated runner bound to it (best-effort; a revoke
        # failure neither masks the open exception nor manufactures one — the token expires on ttl).
        try:
            revoke_scoped_token(token, gh_runner=authenticated_gh_runner(token, spawn=token_spawn))
        except ForgeConfigError:
            logging.getLogger(__name__).warning(
                "scoped-token revoke failed for run %s (token_ref %s); it will expire on its ttl",
                run_id,
                token.token_ref,
            )


# ---------------------------------------------------------------------------
# G2c — the gated-merge leg (the DISTINCT merge identity; never the per-run token)
# ---------------------------------------------------------------------------
def ambient_gh_runner(*, spawn: Any = subprocess.run) -> GhRunner:
    """A :data:`GhRunner` authenticating AS the Operator's ambient ``gh`` login — the DISTINCT
    merge identity (fork §6.4).

    The per-run token AUTHORED the PR, so it must NEVER merge it (self-merge collision; the merge
    gate + branch protection assume an independent merger). The merge therefore rides the Operator's
    ambient ``gh auth`` login — no token is injected into the child env, and this module mints NO
    per-run token on the merge path. CI injects a fake ``spawn``.
    """
    def runner(argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        return spawn(
            list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
        )

    return runner


def _pr_opened_change_set(records: list[dict[str, Any]]) -> tuple[dict[str, Any], str] | None:
    """Return the (change_set pointer, policy_sha) from the chain's ``pr_opened`` outcome, or None."""
    for r in records:
        if (isinstance(r, dict) and r.get("record_type") == RUN_OUTCOME_RECORD_TYPE
                and r.get("outcome") == "pr_opened"):
            cs = r.get("change_set") or {}
            if cs.get("pr_number"):
                return cs, str(r.get("policy_sha") or "")
    return None


# ---------------------------------------------------------------------------
# F6 Phase-0 — change-block identity (git seam) + the base-only re-stamp proof
# ---------------------------------------------------------------------------
#: An injectable git seam: ``(argv, input_text=None) -> CompletedProcess`` (the
#: ``subprocess.run`` shape). CI injects a fake → zero live git.
GitRunner = Callable[..., Any]


class _GitUnavailable(Exception):
    """A required git ref/object is unavailable — the chain cannot be proven (legacy)."""


def default_git_runner(source_dir: str | Path = ".") -> GitRunner:  # pragma: no cover - live git
    """The production git seam: runs ``git`` in ``source_dir``, captured, never raising itself."""

    def run(argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            list(argv), cwd=str(source_dir), check=False, capture_output=True,
            text=True, input=input_text, timeout=60,
        )

    return run


def _git_out(git_runner: GitRunner, argv: Sequence[str], input_text: str | None = None) -> str:
    """Run a git command through the seam; raise :class:`_GitUnavailable` on a non-zero exit."""
    proc = git_runner(list(argv), input_text)
    if getattr(proc, "returncode", 1) != 0:
        raise _GitUnavailable(f"git {' '.join(str(a) for a in argv[1:3])} unavailable")
    return getattr(proc, "stdout", "") or ""


def _is_carrier_path(path: str) -> bool:
    """True when ``path`` is a per-PR carrier (mechanical base/head/restamp metadata)."""
    return path.startswith(CARRIER_DIR.rstrip("/") + "/")


def _normalized_pathset_sha256(paths: Sequence[str]) -> str:
    """The carrier canonicalization: ``sha256("\\n".join(sorted(unique)) + "\\n")``."""
    uniq = sorted({p.strip() for p in paths if p and p.strip()})
    return hashlib.sha256(("\n".join(uniq) + "\n").encode("utf-8")).hexdigest()


def _change_identity(
    git_runner: GitRunner, base_ref: str, head_ref: str, paths: Sequence[str]
) -> dict[str, str]:
    """Compute the value-free change-block identity over the authorized NON-mechanical paths.

    ``content_diff_id`` = SHA256 of the normalized ``git diff base..head -- <non-carrier paths>``;
    ``patch_id_stable`` = git stable patch-id over that same diff (invariant under base-only
    motion — the pre-image of our files is unchanged when base did not touch them). Raises
    :class:`_GitUnavailable` if any ref/object is missing (→ legacy-unprovable).
    """
    non_mech = sorted({p for p in paths if p and not _is_carrier_path(p)})
    head_tree = _git_out(git_runner, ["git", "rev-parse", f"{head_ref}^{{tree}}"]).strip()
    diff = _git_out(
        git_runner, ["git", "diff", "--no-color", f"{base_ref}..{head_ref}", "--", *non_mech]
    )
    content_diff_id = hashlib.sha256(diff.encode("utf-8")).hexdigest()
    pid_out = _git_out(git_runner, ["git", "patch-id", "--stable"], diff).split()
    patch_id = pid_out[0] if pid_out else content_diff_id
    return {
        "head_tree_sha": head_tree,
        "content_diff_id": content_diff_id,
        "patch_id_stable": patch_id,
        "manifest_paths_sha256": _normalized_pathset_sha256(paths),
    }


def _carrier_path(paths: Sequence[str]) -> str | None:
    """The single per-PR carrier in the authorized path-set (or None)."""
    carriers = [p for p in paths if _is_carrier_path(p)]
    return carriers[0] if len(carriers) == 1 else None


def _carrier_pathset_sha256(git_runner: GitRunner, ref: str, carrier: str | None) -> str | None:
    """The carrier's STRUCTURED path-set hash at ``ref`` (mechanical base/head prose ignored)."""
    if not carrier:
        return None
    text = _git_out(git_runner, ["git", "show", f"{ref}:{carrier}"])
    ident = path_manifest_fidelity.parse_carrier(text)
    return ident.normalized_sha256 if ident else None


def _open_identity_fields(
    git_runner: GitRunner, base_ref: str, head_sha: str | None, paths: Sequence[str]
) -> dict[str, str]:
    """The F6 re-stamp anchor fields stamped at open (base_sha + change identity). Best-effort.

    Returns ``{}`` (the pre-F6 change-block shape) when any required ref is unresolvable — a chain
    without ``base_sha`` is later treated as legacy-unprovable, never overridden.
    """
    try:
        base_sha = _git_out(git_runner, ["git", "rev-parse", base_ref]).strip()
        ident = _change_identity(git_runner, base_ref, head_sha or "HEAD", paths)
    except _GitUnavailable:
        return {}
    if not base_sha:
        return {}
    proof_inputs = hashlib.sha256(json.dumps({
        "base_sha": base_sha, "head_sha": head_sha,
        "content_diff_id": ident["content_diff_id"], "patch_id": ident["patch_id_stable"],
        "manifest_paths_sha256": ident["manifest_paths_sha256"],
    }, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "base_sha": base_sha,
        "head_tree_sha": ident["head_tree_sha"],
        "content_diff_id": ident["content_diff_id"],
        "patch_id_stable": ident["patch_id_stable"],
        "manifest_paths_sha256": ident["manifest_paths_sha256"],
        "proof_inputs_sha256": proof_inputs,
    }


@dataclass(frozen=True)
class RestampMergeResult:
    """The F6 plan/apply result: the merge gate snapshot + the head-status disposition.

    Exposes every :class:`~.forge.merge.MergeResult` field the CLI / G2c tests read
    (``pr_number`` / ``eligible`` / ``would_merge`` / ``merged`` / ``merge_commit_sha`` /
    review / checks / mergeable) PLUS the F6 ``head_status`` (``unchanged`` /
    ``base_only_restamp_available`` / ``base_only_restamped``), the old/new base+head SHAs,
    whether a ``runtime_change_restamp`` was recorded, and the squash tree-equivalence audit
    verdict. Value-free. NEVER carries a token (the merge path mints none).
    """

    pr_number: int
    head_status: str
    old_head_sha: str | None
    new_head_sha: str | None
    old_base_sha: str | None
    new_base_sha: str | None
    eligible: bool
    would_merge: bool
    merged: bool
    merge_commit_sha: str | None
    review_decision: str | None
    rollup_state: str
    merge_state_status: str
    mergeable: str | None
    applied: bool
    restamp_recorded: bool
    audit_tree_equivalence: bool | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pr_number": self.pr_number,
            "head_status": self.head_status,
            "old_head_sha": self.old_head_sha,
            "new_head_sha": self.new_head_sha,
            "old_base_sha": self.old_base_sha,
            "new_base_sha": self.new_base_sha,
            "eligible": self.eligible,
            "would_merge": self.would_merge,
            "merged": self.merged,
            "merge_commit_sha": self.merge_commit_sha,
            "review_decision": self.review_decision,
            "rollup_state": self.rollup_state,
            "merge_state_status": self.merge_state_status,
            "mergeable": self.mergeable,
            "applied": self.applied,
            "restamp_recorded": self.restamp_recorded,
            "audit_tree_equivalence": self.audit_tree_equivalence,
        }


def merge_for_run(
    root: Path | str,
    run_id: str,
    *,
    merge_gh_runner: GhRunner,
    apply: bool = False,
    repo: str = DEFAULT_REPO,
    git_runner: GitRunner | None = None,
) -> RestampMergeResult:
    """Gate-read (or apply) a squash-merge of the run's opened PR under the F6 two-tier re-stamp.

    Preconditions: the dispatch is collected (``collected_at`` set), the persisted chain exists, and
    its ``pr_opened`` record carries a ``change_set`` with a ``pr_number``. The ACTIVE merge head is
    the LATEST attested change-block head — the original ``pr_opened`` head if no later re-stamp, or a
    ``runtime_change_restamp`` head. CE reads the LIVE PR state (one combined read through the
    DISTINCT ``merge_gh_runner`` — NEVER the per-run token; this leg mints none) and compares the live
    head to the attested head:

    * **unchanged** — merge with the attested head, exactly as before.
    * **base-only motion** — when the live head moved but CE machine-proves rebase-equivalence
      (unchanged branch/base/PR identity + unchanged carrier path-set + unchanged normalized content
      diff identity + unchanged stable patch-id), re-stamp the change block to the new head: append
      a ``runtime_change_restamp`` (``authority: machine_rebase_equivalence``), then merge with the
      NEW head.
    * **content drift** — any changed content/path/pin identity REFUSES
      (``content_drift_requires_reratification``) before any merge PUT; a fresh ratification, never an
      override, is the path forward.
    * **legacy unprovable** — a chain lacking ``base_sha`` (or whose old refs cannot be resolved)
      REFUSES (``restamp_legacy_unprovable``) before any merge PUT; a raw head SHA is NEVER accepted.

    Plan mode (``apply=False``) reports ``head_status`` + the old/new SHAs and mutates nothing. Apply
    mode issues exactly one head-pinned squash on the active head, then appends ``runtime_change_restamp``
    (if re-stamped) + ``pr_merged`` + a ``runtime_merge_audit`` (the squash tree-equivalence proof:
    what-was-TESTED == what-MERGES) onto the SAME chain and re-persists — only on an ACTUAL merge.
    """
    root = Path(root)
    dispatch = _load_dispatch(root, run_id)
    if not dispatch.get("collected_at"):
        raise ForgeJoinRefused(
            f"run {run_id!r} is not collected (no collected_at); refusing to merge before its "
            "evidence chain is folded"
        )
    chain_path = root / RUNS_SUBDIR / f"{run_id}.runtime-evidence.yaml"
    if not chain_path.is_file():
        raise ForgeJoinRefused(f"run {run_id!r} has no persisted evidence chain at {chain_path}")
    doc = yaml.safe_load(chain_path.read_text(encoding="utf-8"))
    records = list((doc or {}).get("records") or [])
    found = _pr_opened_change_set(records)
    if found is None:
        raise ForgeJoinRefused(
            f"run {run_id!r} chain carries no pr_opened change_set with a pr_number; nothing to merge"
        )
    cs, plan_ref = found
    pr_number = int(cs["pr_number"])
    git = git_runner if git_runner is not None else default_git_runner(".")

    # The latest ATTESTED change-block head (a prior runtime_change_restamp wins over pr_opened).
    attested_head, attested_base = _latest_attested_head(records, cs)
    branch = str(cs.get("branch") or "")
    base = str(cs.get("base") or "main")
    manifest_paths = tuple(cs.get("manifest_paths") or [])
    carrier = _carrier_path(manifest_paths)

    # 1) Read live PR state once (combined). Refuse on PR-identity drift BEFORE any side effect.
    read_change = ChangeRef(
        repo=repo, branch=branch, base=base, pr_number=pr_number, head_sha=attested_head,
        manifest_paths=manifest_paths, plan_ref=plan_ref, changed=True, applied=True, verified=True,
    )
    live = pr_state(read_change, gh_runner=merge_gh_runner)
    if (live.branch and live.branch != branch) or (live.base and live.base != base):
        raise ForgeJoinRefused(
            f"run {run_id!r} PR #{pr_number} identity drifted "
            f"(branch {live.branch!r}!={branch!r} or base {live.base!r}!={base!r}); refusing — "
            "a re-targeted PR is content drift requiring full re-ratification, never a re-stamp"
        )
    new_head = live.head_sha or attested_head
    new_base = live.base_sha or attested_base or ""

    # 2) Classify the head motion.
    restamp_record_body: dict[str, Any] | None = None
    if new_head == attested_head:
        head_status = HEAD_UNCHANGED
        active_head = attested_head
    else:
        head_status, restamp_record_body = _classify_head_motion(
            git, run_id, pr_number, branch, base, carrier, manifest_paths, plan_ref,
            old_base_sha=attested_base, old_head_sha=attested_head,
            new_base_sha=new_base, new_head_sha=new_head,
        )
        active_head = new_head

    proven_restamp = head_status == HEAD_BASE_ONLY_RESTAMP

    # 3) PLAN mode mutates nothing — surface the disposition + the live gate.
    if not apply:
        would = live.eligible if head_status in (HEAD_UNCHANGED, HEAD_BASE_ONLY_RESTAMP) else False
        return RestampMergeResult(
            pr_number=pr_number, head_status=head_status,
            old_head_sha=attested_head, new_head_sha=(new_head if new_head != attested_head else None),
            old_base_sha=attested_base, new_base_sha=(new_base if new_head != attested_head else None),
            eligible=live.eligible, would_merge=would, merged=False, merge_commit_sha=None,
            review_decision=live.review_decision, rollup_state=live.rollup_state,
            merge_state_status=live.merge_state_status, mergeable=live.mergeable, applied=False,
            restamp_recorded=False, audit_tree_equivalence=None,
        )

    # 4) APPLY mode — refuse drift/legacy BEFORE any merge PUT (no override, ever).
    if head_status == HEAD_LEGACY_UNPROVABLE:
        raise ForgeJoinRefused(
            f"{RESTAMP_LEGACY_UNPROVABLE_CODE}: run {run_id!r} PR #{pr_number} head moved to "
            f"{new_head} but the chain cannot prove base-only equivalence (no base_sha or old "
            "refs unavailable); re-adopt a fresh chain — a raw head SHA is never accepted"
        )
    if head_status == HEAD_CONTENT_DRIFT:
        raise ForgeJoinRefused(
            f"{RESTAMP_CONTENT_DRIFT_CODE}: run {run_id!r} PR #{pr_number} head {new_head} changed "
            "content/path-set/pins vs the attested change block; refusing — content movement "
            "requires full re-ratification, never a machine re-stamp"
        )

    # 5) If GitHub reset reviewDecision after a proven base-only rebase, restore
    # the prior approval only through the same authenticated reviewer identity.
    if proven_restamp and live.review_decision == "REVIEW_REQUIRED":
        _restore_same_reviewer_base_only_approval(
            repo=repo,
            pr_number=pr_number,
            branch=branch,
            base=base,
            manifest_paths=manifest_paths,
            approved_head=attested_head,
            active_head=active_head,
            gh_runner=merge_gh_runner,
        )

    # 6) Gated head-pinned squash on the ACTIVE head (the attested or the proven-restamp head).
    merge_change_ref = ChangeRef(
        repo=repo, branch=branch, base=base, pr_number=pr_number, head_sha=active_head,
        manifest_paths=manifest_paths, plan_ref=plan_ref, changed=True, applied=True, verified=True,
    )
    result = merge(merge_change_ref, apply=True, gh_runner=merge_gh_runner)

    restamp_recorded = False
    audit_equiv: bool | None = None
    if result.merged:
        chain = list(records)
        if proven_restamp and restamp_record_body is not None:
            chain = chain + [_spine_append(chain, restamp_record_body)]
            restamp_recorded = True
        # pr_merged onto the SAME chain (value-free change_set pointer, carrying the active head).
        chain = chain + [_spine_append(chain, _pr_merged_body(
            run_id, plan_ref, branch, base, manifest_paths, active_head, pr_number,
            base_sha=new_base if proven_restamp else attested_base,
        ))]
        # The squash tree-equivalence audit (what-was-TESTED == what-MERGES). Best-effort: a git
        # ref we cannot resolve skips the audit (the merge already happened) with a warning.
        audit_body, audit_equiv = _merge_audit_body(
            git, run_id, plan_ref, pr_number, active_head, result.merge_commit_sha,
        )
        if audit_body is not None:
            chain = chain + [_spine_append(chain, audit_body)]
        sink = file_evidence_sink(chain_path.parent)
        sink(CollectedEvidence(
            handle_ref=run_id, records=tuple(chain),
            note=(str((doc or {}).get("note") or "") + "; run-outcome: pr_merged").lstrip("; "),
        ))

    return RestampMergeResult(
        pr_number=pr_number,
        head_status=(HEAD_BASE_ONLY_RESTAMPED if (proven_restamp and result.merged) else head_status),
        old_head_sha=attested_head, new_head_sha=(new_head if new_head != attested_head else None),
        old_base_sha=attested_base, new_base_sha=(new_base if new_head != attested_head else None),
        eligible=result.eligible, would_merge=result.would_merge, merged=result.merged,
        merge_commit_sha=result.merge_commit_sha, review_decision=result.review_decision,
        rollup_state=result.rollup_state, merge_state_status=result.merge_state_status,
        mergeable=result.mergeable, applied=True,
        restamp_recorded=restamp_recorded, audit_tree_equivalence=audit_equiv,
    )


def _latest_attested_head(records: list[dict[str, Any]], cs: dict[str, Any]) -> tuple[str, str | None]:
    """Return the (head_sha, base_sha) of the LATEST attested change block.

    A later ``runtime_change_restamp`` re-stamp wins over the original ``pr_opened`` head (the F6
    authority rule); otherwise the ``pr_opened`` change_set's head + optional ``base_sha``.
    """
    head = str(cs.get("head_sha") or "")
    base = cs.get("base_sha")
    for r in records:
        if isinstance(r, dict) and r.get("record_type") == CHANGE_RESTAMP_RECORD_TYPE:
            head = str(r.get("new_head_sha") or head)
            base = r.get("new_base_sha") or base
    return head, (str(base) if base else None)


def _restore_same_reviewer_base_only_approval(
    *,
    repo: str,
    pr_number: int,
    branch: str,
    base: str,
    manifest_paths: Sequence[str],
    approved_head: str,
    active_head: str,
    gh_runner: GhRunner,
) -> ReviewResult | None:
    """Submit APPROVE on ``active_head`` only as the stale approving reviewer.

    The base-only proof is established by the caller before this helper is
    invoked. This helper only proves same-reviewer semantics from complete
    review history plus the runner's authenticated login. If the current
    credential is not the prior approver, it returns ``None`` and the normal
    merge gate remains closed.
    """
    reviewer = re_review._authenticated_login(gh_runner)
    reviews = re_review.list_reviews(repo, pr_number, gh_runner=gh_runner)
    prior = re_review.stale_base_only_approval_by_reviewer(
        reviews,
        active_head,
        approved_head,
        reviewer,
        base_only_proven=True,
    )
    if prior is None:
        return None
    # A prior GitHub approval proves only a historical decision.  It is not a
    # v2 REVIEWED terminal for this active head and must never be re-emitted as
    # arbitrary approval prose.  Preserve the fail-closed boundary: obtain a
    # fresh inspected terminal + receipt through the review-submission path.
    raise ForgeJoinRefused(
        "base-only approval restoration requires a fresh v2 reviewer terminal and "
        "single-use submission receipt; automatic prose restoration is refused"
    )


def _classify_head_motion(
    git: GitRunner, run_id: str, pr_number: int, branch: str, base: str,
    carrier: str | None, manifest_paths: Sequence[str], plan_ref: str, *,
    old_base_sha: str | None, old_head_sha: str, new_base_sha: str, new_head_sha: str,
) -> tuple[str, dict[str, Any] | None]:
    """Classify a moved head as base-only-provable, content-drift, or legacy-unprovable.

    Returns ``(head_status, restamp_record_body|None)``. The body is built only when base-only
    equivalence is machine-proven (it is the ``runtime_change_restamp`` to append on apply).
    """
    if not old_base_sha or not new_base_sha:
        return HEAD_LEGACY_UNPROVABLE, None
    try:
        old_id = _change_identity(git, old_base_sha, old_head_sha, manifest_paths)
        new_id = _change_identity(git, new_base_sha, new_head_sha, manifest_paths)
        old_carrier = _carrier_pathset_sha256(git, old_head_sha, carrier)
        new_carrier = _carrier_pathset_sha256(git, new_head_sha, carrier)
    except _GitUnavailable:
        return HEAD_LEGACY_UNPROVABLE, None

    pathset_unchanged = (carrier is None) or (
        old_carrier is not None and old_carrier == new_carrier
    )
    content_unchanged = (
        old_id["content_diff_id"] == new_id["content_diff_id"]
        and old_id["patch_id_stable"] == new_id["patch_id_stable"]
    )
    if not (pathset_unchanged and content_unchanged):
        return HEAD_CONTENT_DRIFT, None

    proof_inputs = hashlib.sha256(json.dumps({
        "pr_number": pr_number, "branch": branch, "base": base,
        "old_base": old_base_sha, "old_head": old_head_sha,
        "new_base": new_base_sha, "new_head": new_head_sha,
        "manifest_paths_sha256": new_id["manifest_paths_sha256"],
        "content_diff_id": new_id["content_diff_id"], "patch_id": new_id["patch_id_stable"],
        "carrier": new_carrier,
    }, sort_keys=True).encode("utf-8")).hexdigest()
    body = {
        "kind": CHANGE_RESTAMP_RECORD_KIND, "record_type": CHANGE_RESTAMP_RECORD_TYPE,
        "schema_version": "1", "policy_sha": plan_ref, "run_id": run_id,
        "recorded_at": _utcstamp_iso(None), "restamp_type": "base_only",
        "authority": "machine_rebase_equivalence", "pr_number": pr_number,
        "branch": branch, "base": base,
        "old_base_sha": old_base_sha, "old_head_sha": old_head_sha,
        "new_base_sha": new_base_sha, "new_head_sha": new_head_sha,
        "manifest_paths_sha256": new_id["manifest_paths_sha256"],
        "old_content_diff_id": old_id["content_diff_id"],
        "new_content_diff_id": new_id["content_diff_id"],
        "old_patch_id": old_id["patch_id_stable"], "new_patch_id": new_id["patch_id_stable"],
        "proof_inputs_sha256": proof_inputs,
    }
    return HEAD_BASE_ONLY_RESTAMP, body


def _pr_merged_body(
    run_id: str, plan_ref: str, branch: str, base: str, manifest_paths: Sequence[str],
    head_sha: str, pr_number: int, *, base_sha: str | None,
) -> dict[str, Any]:
    """The value-free ``pr_merged`` run-outcome body pointing at the merged (active) head."""
    change_set: dict[str, Any] = {
        "branch": branch, "base": base, "manifest_paths": list(manifest_paths),
        "head_sha": head_sha, "pr_number": pr_number,
    }
    if base_sha:
        change_set["base_sha"] = base_sha
    return {
        "kind": "runtime-run-outcome", "record_type": RUN_OUTCOME_RECORD_TYPE,
        "schema_version": "1", "policy_sha": plan_ref, "run_id": run_id,
        "recorded_at": _utcstamp_iso(None), "outcome": "pr_merged", "change_set": change_set,
    }


def _merge_audit_body(
    git: GitRunner, run_id: str, plan_ref: str, pr_number: int,
    tested_head: str, merge_commit_sha: str | None,
) -> tuple[dict[str, Any] | None, bool | None]:
    """Build the squash tree-equivalence audit body (best-effort), returning (body, tree_equivalence).

    The conserved invariant: the TESTED head tree must equal the MERGED tree. A git ref we cannot
    resolve (e.g. the squash commit not yet fetched) skips the audit — the merge already happened —
    returning ``(None, None)`` with a warning rather than failing post-merge.
    """
    if not (merge_commit_sha or "").strip():
        return None, None
    try:
        tested_tree = _git_out(git, ["git", "rev-parse", f"{tested_head}^{{tree}}"]).strip()
        merged_tree = _git_out(git, ["git", "rev-parse", f"{merge_commit_sha}^{{tree}}"]).strip()
    except _GitUnavailable:
        logging.getLogger(__name__).warning(
            "run %s merge-audit skipped: merged-commit tree unresolved (the merge stands)", run_id
        )
        return None, None
    equiv = bool(tested_tree) and tested_tree == merged_tree
    body = {
        "kind": MERGE_AUDIT_RECORD_KIND, "record_type": MERGE_AUDIT_RECORD_TYPE,
        "schema_version": "1", "policy_sha": plan_ref, "run_id": run_id,
        "recorded_at": _utcstamp_iso(None), "pr_number": pr_number,
        "tested_head_sha": tested_head, "tested_tree_sha": tested_tree,
        "merge_method": "squash", "merge_commit_sha": merge_commit_sha,
        "merged_tree_sha": merged_tree, "tree_equivalence": equiv,
    }
    if not equiv:
        logging.getLogger(__name__).error(
            "run %s MERGE-AUDIT TREE MISMATCH: tested %s != merged %s (operator alert)",
            run_id, tested_tree, merged_tree,
        )
    return body, equiv
