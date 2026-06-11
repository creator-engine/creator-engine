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

from .evidence_sink import file_evidence_sink
from .forge.app_jwt_runner import Signer, app_jwt_gh_runner
from .forge.change import ChangeRef, open_change
from .forge.change_push import push_change
from .forge.credential_runner import authenticated_gh_runner
from .forge.github_repo_config import ForgeConfigError, GhRunner
from .forge.merge import MergeResult, merge
from .forge.scoped_token import (
    ScopedToken,
    TokenRequest,
    mint_scoped_token,
    revoke_scoped_token,
)
from .orchestrator import merge_change
from .runner.backend import CollectedEvidence, RunChangeSet
from .runtime_evidence_spine import RUN_OUTCOME_RECORD_TYPE

#: The verified live host App-config convention (instance-local, outside the repo). The
#: ``--app-config`` flag is REQUIRED on ``cev3 pr`` (host filenames differ); this is documentation
#: of the shape, not a silent default the CLI applies.
DEFAULT_APP_CONFIG_PATH = "~/.ce-keys/ce-forge-app.json"

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
#: The PR-open credential time-box (<= the 1h ceiling, well under it — a PR-open is seconds of work).
PR_TOKEN_TTL_SECONDS = 900
#: The logical secret name the per-run PR credential satisfies.
PR_SECRET_NAME = "forge_pr_open"

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


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
            dispatch["change"] = {
                "branch": branch,
                "base": base,
                "pr_number": ref.pr_number,
                "head_sha": ref.head_sha,
                "manifest_paths": list(paths),
                "opened_at": _utcstamp_iso(now),
            }
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


def merge_for_run(
    root: Path | str,
    run_id: str,
    *,
    merge_gh_runner: GhRunner,
    apply: bool = False,
    repo: str = DEFAULT_REPO,
) -> MergeResult:
    """Gate-read (or apply) a squash-merge of the run's opened PR; attest ``pr_merged`` on a real merge.

    Preconditions: the dispatch is collected (``collected_at`` set), the persisted chain exists, and
    its ``pr_opened`` record carries a ``change_set`` with a ``pr_number``. Reconstructs the
    value-free :class:`~.runner.backend.CollectedEvidence` + the merge-target :class:`ChangeRef` from
    that pointer, then drives the gated merge under the DISTINCT ``merge_gh_runner`` (NEVER the
    per-run token — this leg mints none).

    This mirrors ``run_assembly.make_merge_driver``'s composition (reconstruct → gated merge →
    :func:`~.orchestrator.merge_change` persist) but ALSO returns the :class:`MergeResult` gate
    snapshot the plan-mode CLI surfaces (the driver returns only ``CollectedEvidence``). Exactly ONE
    ``forge.merge`` call runs: with ``apply=False`` it is a non-mutating gate read (``would_merge`` +
    the snapshot); with ``apply=True`` it refuses an ineligible PR (``MergeRefused``) and otherwise
    issues one head-pinned squash, and ``pr_merged`` is appended onto the SAME chain + re-persisted
    only on an ACTUAL merge. A plan-mode / ineligible result attests NOTHING.
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
    head_sha = cs.get("head_sha")

    change = ChangeRef(
        repo=repo,
        branch=str(cs.get("branch") or ""),
        base=str(cs.get("base") or "main"),
        pr_number=pr_number,
        head_sha=head_sha,
        manifest_paths=tuple(cs.get("manifest_paths") or []),
        plan_ref=plan_ref,
        changed=True,
        applied=True,
        verified=True,
    )
    # ONE gated merge under the distinct identity (read in plan mode, head-pinned squash on apply).
    result = merge(change, apply=apply, gh_runner=merge_gh_runner)
    if result.merged:
        # Attest pr_merged onto the SAME chain via the conserved merge_change primitive (the sink
        # re-verifies the whole chain + re-persists <run_id>.runtime-evidence.yaml). change_merger
        # returns the already-computed result so NO second merge call is made.
        prior = CollectedEvidence(
            handle_ref=run_id,
            records=tuple(records),
            note=str((doc or {}).get("note") or ""),
            change_set=RunChangeSet(
                branch=change.branch, base=change.base,
                manifest_paths=tuple(cs.get("manifest_paths") or []),
                head_sha=str(head_sha or ""),
            ),
        )
        sink = file_evidence_sink(chain_path.parent)
        merge_change(
            prior, run_id=run_id, policy_sha=plan_ref,
            change_merger=lambda: result, evidence_sink=sink,
        )
    return result
