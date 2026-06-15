"""CE v3 production live-forge ``ApplyDriver`` (ce-ops#88, Phase 1) — the #85 plain-join keystone.

Published 0.2.0's existing-repo ``onboard --apply`` is inert: ``_onboard_apply_driver``
hands back the base :class:`onboard_apply.ApplyDriver`, whose every forge method is a noop
stub, so :func:`onboard_apply.repo_is_already_ce_governed` can never see the three live
read-only signals it needs (``repo_exists`` → ``verify_workflow`` at the pinned digest →
``verify_branch_protection`` against the floor) and a real already-CE repo dead-ends at
``e2_brownfield_seam_unavailable``. This module supplies the live driver that closes that gap.

Phase 1 (this gate) wires ONLY:

* the forge **read-only** detection legs (``repo_exists`` / ``verify_repo`` / ``verify_workflow``
  / ``verify_branch_protection`` / ``existing_branch_protection_contexts`` / ``probe_bootstrap_token``), and
* the idempotent **plain-join** apply legs for an already-CE repo — a verify-first,
  defer-not-mutate ``configure_branch_protection`` (OQ-F: **zero forge writes on the happy
  path**) and a local ``git clone`` ``checkout_workspace`` (+ its ``verify_checkout``).

Greenfield mutate legs (``create_repo`` / ``install_workflow`` / app-install) are **Phase 2**,
a strictly larger blast radius behind explicit per-install escalation authority — NOT here.
All **host** legs (``probe_tool`` / ``install_dependencies`` / ``provision_runtime`` /
``expose_cli`` / ``resolve_secret`` / ``run_first_project_smoke``) are inherited unchanged.

Auth (composed, never invented). Every forge read routes through the shipped ``GhRunner``
credential toolchain authenticated by a JIT, least-privilege, time-boxed installation token:
``mint_scoped_token`` (G-2.2, at the Phase-1 read ceiling ``{metadata:read, contents:read,
administration:read}`` and binding NO escalation authority — so it can never widen to a write)
minted via the ``app_jwt_gh_runner`` Bearer adapter (G-3.7.1, because ``gh`` cannot App-JWT
auth) → ``authenticated_gh_runner`` (G-3.4, ``GH_TOKEN`` in the child env ONLY) for the reads →
``revoke_scoped_token`` the instant the legs finish (``close()``). The App private key (PEM)
never enters the driver — RS256 signing is an injected host-side :data:`Signer` over a PEM held
on tmpfs. The token value never touches argv / a log / ``print`` / an exception / the evidence
spine / disk; only the non-secret scope / expiry / correlation ref are attestable. The
credential authenticates CE's OWN forge subprocess only, never an agent/sandbox container.

Defensive only — read-mostly, least-privilege detection of our own pilot repos; never offensive.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import onboard_apply, v3_installer
from .forge.app_jwt_runner import Signer, app_jwt_gh_runner
from .forge.credential_runner import authenticated_gh_runner
from .forge.github_repo_config import BranchProtectionPolicy, ForgeConfigError, GhRunner
from .forge.scoped_token import (
    ScopedToken,
    TokenRequest,
    mint_scoped_token,
    revoke_scoped_token,
)

__ce_version_line__ = "v3"

#: Phase-1 least-privilege READ ceiling. ``administration:read`` is required because GitHub
#: gates branch-protection reads behind the Administration permission; it is the read-mostly
#: baseline tier of the ceiling-driven minter, so it mints without any escalation authority.
PHASE1_PERMISSIONS: dict[str, str] = {
    "metadata": "read",
    "contents": "read",
    "administration": "read",
}
#: Phase-1 binds NO escalation authority — every write/admin grant therefore refuses at the
#: minter (default-deny). Phase-2 greenfield authors its own escalated policy; zero edits here.
PHASE1_ESCALATION_AUTHORITY: tuple[tuple[str, str], ...] = ()
#: The forge-read credential is seconds of work; well under the 1h ceiling.
FORGE_READ_TTL_SECONDS = 600
#: The logical secret name the per-onboard read credential satisfies (non-secret metadata).
FORGE_READ_SECRET_NAME = "onboard_forge_read"

#: Host env vars that carry the live-forge authorization + App credentials (config, NOT
#: answers — the PEM path lives here so the secret content never travels through the answers
#: file, and the authorization flag is co-located with the creds it gates).
#:
#: ``CE_FORGE_LIVE_FORGE`` is the explicit, default-OFF authorization flag (OQ-D: gate-spec §6
#: "a posture/answers flag" / §8 OQ-D "explicit answers/env flag"). It is an ENV flag rather
#: than an install-answers key because the answers schema's sha256 is pinned inside the
#: ce-root-v1-signed ``docs/llms-install.md`` — adding a field there would force a trust-root
#: re-sign. Co-locating the flag with the (already host-side) App credentials keeps the entire
#: live-forge config host-side and out of the portable, signed answers surface. Autodetect is
#: still REJECTED: the flag must be explicitly set AND the credentials must resolve.
ENV_LIVE_FORGE = "CE_FORGE_LIVE_FORGE"
ENV_APP_CLIENT_ID = "CE_FORGE_APP_CLIENT_ID"
ENV_INSTALLATION_ID = "CE_FORGE_INSTALLATION_ID"
ENV_APP_PEM = "CE_FORGE_APP_PEM"


@dataclass(frozen=True)
class LiveForgeConfig:
    """Everything the live driver needs to mint + use + revoke its own forge-read token.

    ``signer`` is the host-side RS256 :data:`Signer` over the App PEM — the PEM content never
    enters the driver. ``transport`` / ``spawn`` / ``git_spawn`` are injectable network seams
    (live by default); tests inject fakes and perform ZERO live network / subprocess.
    """

    repo: str
    installation_id: int
    app_client_id: str
    signer: Signer
    #: 64-hex digest binding issuance to the verified install spec in force (its canonical sha).
    policy_sha: str
    run_id: str
    transport: Any = None  # app-JWT HTTPS transport seam
    spawn: Any = None  # authenticated-gh subprocess seam
    git_spawn: Any = None  # workspace-clone subprocess seam


def _gh_get(runner: GhRunner, path: str) -> tuple[int, object, str]:
    """``gh api <path>`` through an authenticated runner; never raises. ``(code, json|None, stderr)``."""
    proc = runner(["gh", "api", path], None)
    out = (proc.stdout or "").strip()
    parsed: object = None
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return proc.returncode, parsed, proc.stderr or ""


def _protection_contexts(protection: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not isinstance(protection, Mapping):
        return ()
    checks = protection.get("required_status_checks") or {}
    contexts = checks.get("contexts") if isinstance(checks, Mapping) else None
    return tuple(str(c) for c in (contexts or ()))


def _parse_oauth_scopes_header(raw_response: str) -> set[str]:
    """Extract the classic OAuth scopes from a ``gh api -i`` (header-including) response."""
    scopes: set[str] = set()
    for line in raw_response.splitlines():
        if not line.strip():
            break  # headers end at the first blank line; the body follows
        if line.lower().startswith("x-oauth-scopes:"):
            _, _, value = line.partition(":")
            scopes = {s.strip() for s in value.split(",") if s.strip()}
    return scopes


def _bootstrap_scopes_from_oauth(oauth_scopes: set[str], *, org_create_needed: bool) -> list[str]:
    """Map a bootstrap PAT's classic OAuth scopes to CE's bootstrap-permission names.

    Grounded in GitHub's documented classic-scope semantics, NOT invented: the ``repo`` scope
    grants full control of repositories (administration / contents / actions write), and the
    ``workflow`` scope grants updating ``.github/workflows`` files. Org repo-create rides on
    ``repo`` (the actor must additionally be able to create in the org).
    """
    granted: set[str] = set()
    if "repo" in oauth_scopes:
        granted.update({"administration:write", "contents:write", "actions:write"})
    if "workflow" in oauth_scopes:
        granted.add("workflows:write")
    if org_create_needed and "repo" in oauth_scopes:
        granted.add(v3_installer.ORG_CREATE_SCOPE)
    return sorted(granted)


class LiveForgeApplyDriver(onboard_apply.ApplyDriver):
    """Production live-forge driver (Phase 1): forge reads + idempotent plain-join apply.

    Overrides ONLY the forge legs; inherits every host leg from
    :class:`onboard_apply.ApplyDriver`. Lazily mints ONE read-scoped installation token on the
    first forge read, reuses it across detection + the plain-join legs, and revokes it on
    :meth:`close` — the instant the legs finish.
    """

    def __init__(self, config: LiveForgeConfig):
        self._cfg = config
        self._token: ScopedToken | None = None
        self._read_runner: GhRunner | None = None

    # -- credential lifecycle (mint -> use -> revoke) ----------------------------------------
    def _reader(self) -> GhRunner:
        """Lazily mint the Phase-1 read token and return the authenticated ``GhRunner`` (cached)."""
        if self._read_runner is None:
            mint_runner = app_jwt_gh_runner(
                self._cfg.app_client_id,
                signer=self._cfg.signer,
                transport=self._cfg.transport,
            )
            request = TokenRequest(
                repo=self._cfg.repo,
                installation_id=self._cfg.installation_id,
                run_id=self._cfg.run_id,
                policy_sha=self._cfg.policy_sha,
                permissions=PHASE1_PERMISSIONS,
                secret_name=FORGE_READ_SECRET_NAME,
                requested_ttl_seconds=FORGE_READ_TTL_SECONDS,
                escalation_authority=PHASE1_ESCALATION_AUTHORITY,
            )
            self._token = mint_scoped_token(request, gh_runner=mint_runner)
            self._read_runner = authenticated_gh_runner(self._token, spawn=self._cfg.spawn)
        return self._read_runner

    def close(self) -> None:
        """Revoke the minted read token (best-effort, authenticated AS the token); never raises.

        Called the instant the legs finish (defense-in-depth beyond the <=10m ceiling). A revoke
        transport failure is swallowed — the token expires on its own — and never leaks the value.
        """
        if self._token is not None and self._read_runner is not None:
            with contextlib.suppress(ForgeConfigError, OSError):
                revoke_scoped_token(self._token, gh_runner=self._read_runner)
        self._token = None
        self._read_runner = None

    def __enter__(self) -> "LiveForgeApplyDriver":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.close()

    # -- forge READ legs (Phase 1) -----------------------------------------------------------
    def repo_exists(self, repo: str) -> bool:
        try:
            code, parsed, _ = _gh_get(self._reader(), f"repos/{repo}")
        except Exception:  # noqa: BLE001 — detection is fail-closed: any error → not reachable
            return False
        return code == 0 and isinstance(parsed, dict) and bool(parsed.get("full_name"))

    def verify_repo(
        self,
        *,
        repo: str,
        default_branch: str,
        visibility: str,
        spec_digest: str,
        ledger: "onboard_apply.Ledger",
    ) -> dict[str, Any]:
        try:
            code, parsed, _ = _gh_get(self._reader(), f"repos/{repo}")
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "repo_read_failed"}
        if code != 0 or not isinstance(parsed, dict):
            return {"ok": False, "reason": "repo_read_failed"}
        live_branch = str(parsed.get("default_branch") or "")
        live_visibility = "private" if bool(parsed.get("private")) else "public"
        # Plain-join verifies the repo is reachable and CE governance lives on the branch we
        # check (default branch). Visibility is the existing owner's choice — the joining dev
        # does not control it — so it is reported, NOT gated (gating it would fail-close a
        # legitimately-public already-CE repo against the new-repo ``private`` default).
        ok = live_branch == default_branch
        return {
            "ok": ok,
            "default_branch": live_branch,
            "visibility": live_visibility,
            "requested_visibility": visibility,
        }

    def verify_workflow(self, *, repo: str, branch: str, path: str, digest: str) -> dict[str, Any]:
        """GET the workflow contents and pin the EXACT byte digest (OQ-C, fail-closed).

        A present-but-byte-drifted workflow returns a DISTINCT ``workflow_digest_mismatch`` reason
        (so a joining dev learns *why* detection failed) — never a blanket brownfield refuse.
        """
        try:
            code, parsed, _ = _gh_get(self._reader(), f"repos/{repo}/contents/{path}?ref={branch}")
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "workflow_read_failed"}
        if code != 0 or not isinstance(parsed, dict) or "content" not in parsed:
            return {"ok": False, "reason": "workflow_absent"}
        try:
            raw = base64.b64decode(parsed["content"])  # GitHub returns base64 (newline-wrapped)
        except (ValueError, TypeError):
            return {"ok": False, "reason": "workflow_decode_failed"}
        actual = hashlib.sha256(raw).hexdigest()
        if actual == digest:
            return {"ok": True, "sha256": actual}
        return {
            "ok": False,
            "reason": "workflow_digest_mismatch",
            "expected": digest,
            "actual": actual,
        }

    def verify_branch_protection(
        self, *, repo: str, branch: str, policy: BranchProtectionPolicy
    ) -> dict[str, Any]:
        try:
            code, parsed, _ = _gh_get(
                self._reader(), f"repos/{repo}/branches/{branch}/protection"
            )
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "protection_read_failed"}
        if code != 0 or not isinstance(parsed, dict):
            return {"ok": False, "reason": "protection_read_failed"}
        live = set(_protection_contexts(parsed))
        floor = set(policy.required_status_check_contexts)
        # The floor's required checks must ALL be present (a repo with MORE checks still
        # satisfies the floor); a missing CE check fails detection → brownfield defer upstream.
        return {"ok": floor.issubset(live), "contexts": sorted(live)}

    def existing_branch_protection_contexts(
        self, *, repo: str, branch: str
    ) -> tuple[str, ...]:
        try:
            code, parsed, _ = _gh_get(
                self._reader(), f"repos/{repo}/branches/{branch}/protection"
            )
        except Exception:  # noqa: BLE001 — fail-closed: report no live contexts known
            return ()
        if code != 0 or not isinstance(parsed, dict):
            return ()
        return _protection_contexts(parsed)

    def probe_bootstrap_token(
        self, *, token: str, repo: str, org_create_needed: bool
    ) -> dict[str, Any]:
        """Validity probe of the human BOOTSTRAP PAT (``GET /user``) — distinct auth from the App.

        Authenticates AS the bootstrap token (value in the child ``GH_TOKEN`` env only, never argv)
        and reports its login + the CE bootstrap permissions implied by its classic OAuth scopes.
        """
        try:
            holder = ScopedToken(
                run_id=self._cfg.run_id,
                repo=repo,
                policy_sha=self._cfg.policy_sha,
                secret_name="github.bootstrap_token",
                permissions=(),
                expires_at="",
                token_ref="bootstrap",
                value=token,
            )
            runner = authenticated_gh_runner(holder, spawn=self._cfg.spawn)
            proc = runner(["gh", "api", "-i", "user"], None)
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "bootstrap_probe_failed"}
        if proc.returncode != 0:
            return {"ok": False, "reason": "bootstrap_probe_failed"}
        oauth_scopes = _parse_oauth_scopes_header(proc.stdout or "")
        body = (proc.stdout or "").split("\n\n", 1)[-1].strip()
        login = None
        try:
            login = (json.loads(body) or {}).get("login")
        except (json.JSONDecodeError, ValueError):
            login = None
        if not login:
            return {"ok": False, "reason": "bootstrap_probe_no_identity"}
        return {
            "ok": True,
            "login": login,
            "scopes": _bootstrap_scopes_from_oauth(oauth_scopes, org_create_needed=org_create_needed),
        }

    def verify_app_installation(
        self, *, installation_id: int, repo: str, bot_identity: str
    ) -> dict[str, Any]:
        """Phase-1 read-only App-installation COVERAGE GET (ce-ops#88 amendment, Operator-ratified).

        Confirms the ALREADY-installed App covers ``repo`` — NO install click, NO mutation. Lists
        the installation's repositories via the minted installation token (``Metadata:read``,
        within the Phase-1 ceiling) and checks the target repo is covered. The bot identity is the
        App the installation token was minted under (implicit in the credential), reported back.
        The install *click* / greenfield ``wait_for_app_installation`` stay Phase-2 (inherited).
        Pagination: checks the first ``per_page=100`` page — sufficient for the plain-join target;
        the live Mode-A VPS rehearsal is the full-coverage proof.
        """
        try:
            code, parsed, _ = _gh_get(self._reader(), "installation/repositories?per_page=100")
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "app_installation_read_failed"}
        if code != 0 or not isinstance(parsed, dict):
            return {"ok": False, "reason": "app_installation_read_failed"}
        repos = parsed.get("repositories") or []
        covered = any(
            isinstance(r, Mapping) and r.get("full_name") == repo for r in repos
        )
        if not covered:
            return {
                "ok": False,
                "reason": "app_installation_repo_not_covered",
                "installation_id": installation_id,
            }
        return {
            "ok": True,
            "installation_id": installation_id,
            "bot_identity": bot_identity,
            "covered": True,
        }

    # -- plain-join APPLY legs (Phase 1) -----------------------------------------------------
    def configure_branch_protection(
        self, *, repo: str, branch: str, policy: BranchProtectionPolicy, token: str
    ) -> dict[str, Any]:
        """VERIFY-FIRST, defer-not-mutate (OQ-F) — NEVER issues a protection write.

        On an already-CE repo (detection confirmed the floor present) the desired union is
        identical to the live state → a no-op (``already: True``, ``mutated: False``). If a CE
        required check is genuinely MISSING the repo is NOT fully already-CE → fail closed (no
        PUT). So Phase-1's forge-write blast radius on the happy path is **zero**.
        """
        try:
            code, parsed, _ = _gh_get(
                self._reader(), f"repos/{repo}/branches/{branch}/protection"
            )
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "protection_read_failed_no_write"}
        if code != 0 or not isinstance(parsed, dict):
            return {"ok": False, "reason": "protection_read_failed_no_write"}
        live = set(_protection_contexts(parsed))
        would_add = set(policy.required_status_check_contexts) - live
        if would_add:
            # A real protection mutation would be required → defer, do NOT write.
            return {
                "ok": False,
                "reason": "branch_protection_mutation_deferred",
                "would_add": sorted(would_add),
            }
        return {"ok": True, "already": True, "mutated": False, "contexts": sorted(live)}

    def checkout_workspace(
        self, *, repo: str, branch: str, workspace_root: Path
    ) -> dict[str, Any]:
        """Local ``git clone`` (remote read + local write only) via ``gh repo clone`` (GH_TOKEN env)."""
        repo_dir = workspace_root / repo.split("/", 1)[1]
        if repo_dir.exists():
            return {"ok": True, "already": True, "path": str(repo_dir)}
        try:
            workspace_root.mkdir(parents=True, exist_ok=True)
            runner = self._clone_runner()
            # gh repo clone reads GH_TOKEN from the child env → no token in argv.
            proc = runner(
                ["gh", "repo", "clone", repo, str(repo_dir), "--", "--branch", branch, "--depth", "1"],
                None,
            )
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "checkout_failed"}
        if proc.returncode != 0:
            return {"ok": False, "reason": "checkout_failed"}
        return {"ok": True, "path": str(repo_dir), "created": True}

    def _clone_runner(self) -> GhRunner:
        """Authenticated runner for the clone (uses ``git_spawn`` if injected, else the read spawn)."""
        self._reader()  # ensure the read token is minted
        assert self._token is not None
        spawn = self._cfg.git_spawn if self._cfg.git_spawn is not None else self._cfg.spawn
        return authenticated_gh_runner(self._token, spawn=spawn)

    def verify_checkout(self, *, repo: str, branch: str, path: Path) -> dict[str, Any]:
        """Local-filesystem verification of the clone the live ``checkout_workspace`` just made.

        DEVIATION (flagged): the base ``verify_checkout`` is a noop stub returning ``ok: False``,
        which would fail the ``workspace_checkout`` leg after a successful live clone. Completing
        the plain-join checkout therefore REQUIRES overriding it. It remains a local read (the
        clone target is a git working tree) — no forge call, no write.
        """
        repo_dir = Path(path)
        if not (repo_dir / ".git").exists():
            return {"ok": False, "reason": "checkout_missing"}
        return {"ok": True, "branch": branch}


# ---------------------------------------------------------------------------------------------
# Host-side PEM signer (Mode-A live path; the PEM CONTENT never enters the driver)
# ---------------------------------------------------------------------------------------------
def pem_signer(pem_path: str) -> Signer:
    """An RS256 :data:`Signer` over the App PEM at ``pem_path`` (host-side, via ``openssl``).

    The PEM path (config) is passed to ``openssl``; the PEM CONTENT is never read into Python and
    never enters the driver. The driver calls the returned closure with the JWT signing input only.
    Errors carry no key material / token. ``openssl`` avoids a new crypto dependency in the wheel.
    """

    def sign(signing_input: bytes) -> bytes:
        proc = subprocess.run(  # noqa: S603 — fixed argv; pem_path is config, content stays on tmpfs
            ["openssl", "dgst", "-sha256", "-sign", pem_path],
            input=signing_input,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if proc.returncode != 0 or not proc.stdout:
            raise ForgeConfigError("App JWT RS256 signing failed (host-side signer)")
        return proc.stdout

    return sign


# ---------------------------------------------------------------------------------------------
# Selection factory (OQ-D) — default OFF, fail-closed to the base noop driver
# ---------------------------------------------------------------------------------------------
def _flag_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.strip().lower() in ("1", "true", "yes", "on")


def resolve_live_config(
    merged: "v3_installer.MergeResult",
    *,
    policy_sha: str,
    env: Mapping[str, str] | None = None,
) -> LiveForgeConfig | None:
    """Resolve the live-forge App credentials (host env + answers); ``None`` if anything is absent.

    Fail-closed: a missing client-id / installation-id / PEM (or an unreadable PEM path) returns
    ``None`` so the caller keeps the base noop driver — never a silent half-live driver.
    """
    env = os.environ if env is None else env
    repo = str(merged.value("github.repo") or "")
    if not repo:
        return None
    installation_raw = merged.value("github.app.installation_id") or env.get(ENV_INSTALLATION_ID)
    client_id = env.get(ENV_APP_CLIENT_ID)
    pem_path = env.get(ENV_APP_PEM)
    if not (installation_raw and client_id and pem_path):
        return None
    try:
        installation_id = int(installation_raw)
    except (TypeError, ValueError):
        return None
    if installation_id <= 0:
        return None
    if not Path(pem_path).is_file():  # host-side presence check; content never read here
        return None
    return LiveForgeConfig(
        repo=repo,
        installation_id=installation_id,
        app_client_id=str(client_id),
        signer=pem_signer(pem_path),
        policy_sha=policy_sha,
        run_id=f"onboard-live-forge:{repo}",
    )


def live_forge_select(
    base: onboard_apply.ApplyDriver,
    *,
    merged: "v3_installer.MergeResult",
    policy_sha: str,
    env: Mapping[str, str] | None = None,
) -> onboard_apply.ApplyDriver:
    """Return the live driver ONLY when explicitly authorized AND credentials resolve; else ``base``.

    OQ-D fail-closed selection: default **OFF**. Returns :class:`LiveForgeApplyDriver` iff the
    explicit env flag ``CE_FORGE_LIVE_FORGE`` is set true AND :func:`resolve_live_config` resolves
    the App credentials; otherwise returns ``base`` unchanged (the noop driver, or — in tests —
    whatever the zero-arg ``_onboard_apply_driver`` monkeypatch injected). Autodetect is REJECTED:
    the explicit flag is required (credentials present without the flag → ``base``). ``base`` is
    passed through untouched when OFF, so this is invisible to the existing ``FakeDriver``
    monkeypatch.
    """
    env = os.environ if env is None else env
    if not _flag_true(env.get(ENV_LIVE_FORGE)):
        return base
    config = resolve_live_config(merged, policy_sha=policy_sha, env=env)
    if config is None:
        return base  # authorized but unconfigured → fail-closed to the base noop driver
    return LiveForgeApplyDriver(config)
