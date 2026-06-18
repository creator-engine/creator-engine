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
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import onboard_apply, v3_installer
from .forge.app_jwt_runner import Signer, app_jwt_gh_runner
from .forge.change import open_change
from .forge.change_push import PushRefused, push_change
from .forge.credential_runner import authenticated_gh_runner
from .forge.github_repo_config import (
    BranchProtectionPolicy,
    ForgeConfigError,
    ForgeConfigRefused,
    GhRunner,
)
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
#: ce-ops#85 E3 adoption-APPLY (the join-PR WRITE escalation, §6.3 / OQ-3). A SECOND,
#: default-OFF authorization flag, co-located with the App creds and mirroring
#: ``CE_FORGE_LIVE_FORGE`` (ENV not answers-schema, so no ce-root-v1 re-sign cascade). The
#: adoption WRITE path requires BOTH ``CE_FORGE_LIVE_FORGE=1`` AND ``CE_FORGE_ADOPTION_WRITE=1``
#: — the one-time, human-ratified per-install escalation gate beyond #233's zero-write posture.
ENV_ADOPTION_WRITE = "CE_FORGE_ADOPTION_WRITE"

#: ce-ops#85 §6.1 — the least-privilege join-PR WRITE ceiling. GitHub installation-token
#: permissions are a ``scope -> level`` map, so ``contents:write`` SUBSUMES ``contents:read``
#: (a scope cannot carry two levels): the §6.1 conceptual ceiling
#: ``{metadata:read, contents:read, contents:write, workflows:write, pull_requests:write}``
#: collapses to this 4-entry minted map. ``contents:write`` (push the branch) and
#: ``workflows:write`` (the branch adds ``.github/workflows/ce-validate.yml``) are Tier-2
#: escalation-gated; ``pull_requests:write`` (open the join PR) is Tier-3 baseline (admitted
#: with no escalation). ``administration:write`` is DELIBERATELY ABSENT (OQ-1): the join PR
#: never mutates branch protection.
ADOPTION_WRITE_PERMISSIONS: dict[str, str] = {
    "metadata": "read",
    "contents": "write",
    "workflows": "write",
    "pull_requests": "write",
}
#: The EXACT escalation authority the adoption write token binds (§6.3) — only the two Tier-2
#: grants the join PR needs. ``pull_requests:write`` is Tier-3 (no authority required) and
#: ``administration:write`` is NOT here (never minted). A request that includes a Tier-2 write
#: WITHOUT binding this refuses at the minter (default-deny) — defence-in-depth.
ADOPTION_ESCALATION_AUTHORITY: tuple[tuple[str, str], ...] = (
    ("contents", "write"),
    ("workflows", "write"),
)
#: The adoption write credential is minted for legs 4-5 ONLY and revoked immediately after.
FORGE_WRITE_TTL_SECONDS = 600
FORGE_WRITE_SECRET_NAME = "onboard_forge_adoption_write"


@dataclass(frozen=True)
class BrownfieldScanner:
    """A sha256-pinned, mirror-served secrets scanner for the scrub gate (§3.3, OQ-5).

    Gitleaks + TruffleHog (the client-zero runbook pair). ``sha256`` pins the EXACT mirror-
    served binary bytes; an EMPTY ``sha256`` means UNPINNED → the live scan fail-closes
    (``ran=False``) so an unverified binary is NEVER executed. The concrete release pins are
    COMMISSIONED at the live Mode-A VPS rehearsal (the only venue the scanners run — CI uses
    the injected ``scrub_scan`` seam and performs ZERO scanner). Mirrors ``MirrorUserspaceWheel``.
    """

    tool: str
    version: str
    url: str
    sha256: str


#: The KNOWN secrets-scrub scanners (§3.3 hard gate). ``sha256`` is intentionally EMPTY here:
#: the live binary pins are commissioned at the VPS Mode-A rehearsal (the DoD live venue). Until
#: pinned, the live ``_default_scrub_scan`` reports each scanner ``ran=False`` → the
#: ``brownfield_secret_preflight`` leg fail-closes (``brownfield_secret_scanner_unavailable``),
#: so NO adoption branch is built/pushed/PR'd without an affirmed, pinned two-scanner clean.
BROWNFIELD_SCANNERS: dict[str, BrownfieldScanner] = {
    "gitleaks": BrownfieldScanner(tool="gitleaks", version="", url="", sha256=""),
    "trufflehog": BrownfieldScanner(tool="trufflehog", version="", url="", sha256=""),
}
#: The two-scanner set the scrub gate requires (mirrors ``onboard_apply.REQUIRED_SCRUB_SCANNERS``).
REQUIRED_SCRUB_SCANNERS: tuple[str, ...] = ("gitleaks", "trufflehog")
ENV_GITLEAKS_URL = "CE_FORGE_GITLEAKS_URL"
ENV_GITLEAKS_SHA256 = "CE_FORGE_GITLEAKS_SHA256"
ENV_GITLEAKS_VERSION = "CE_FORGE_GITLEAKS_VERSION"
ENV_TRUFFLEHOG_URL = "CE_FORGE_TRUFFLEHOG_URL"
ENV_TRUFFLEHOG_SHA256 = "CE_FORGE_TRUFFLEHOG_SHA256"
ENV_TRUFFLEHOG_VERSION = "CE_FORGE_TRUFFLEHOG_VERSION"
SCANNER_ENV_KEYS: dict[str, tuple[str, str, str]] = {
    "gitleaks": (ENV_GITLEAKS_URL, ENV_GITLEAKS_SHA256, ENV_GITLEAKS_VERSION),
    "trufflehog": (ENV_TRUFFLEHOG_URL, ENV_TRUFFLEHOG_SHA256, ENV_TRUFFLEHOG_VERSION),
}
FINE_GRAINED_PERMISSION_PROBE_PATH = ".github/workflows/ce-fine-grained-permission-probe.yml"
#: OPTIONAL offline FALLBACK for the apply-time userspace-dep install. Design A's DEFAULT path
#: fetches the pinned ``uv`` wheel from CE's mirror; if this env points at a directory that
#: already holds the pinned wheel (sha256-verified), the driver uses it instead of fetching —
#: a no-egress fallback for air-gapped / pre-seeded hosts. Absent → mirror-fetch (the default).
ENV_WHEELHOUSE = "CE_FORGE_WHEELHOUSE"


@dataclass(frozen=True)
class MirrorUserspaceWheel:
    """A sha256-pinned, no-sudo userspace tool wheel SERVED FROM CE's own 0.2.0 mirror.

    Design A (Operator-ratified, ce-ops#90): the apply-time ``install_dependencies`` leg
    fetches ``url`` from CE's mirror (``docs/downloads/0.2.0/``, NOT astral.sh / PyPI), verifies
    the downloaded bytes against ``sha256`` BEFORE install (anti-tamper), then installs OFFLINE
    via ``pip install --no-index --find-links <downloaded-dir> <tool>``. The pin is bound to the
    SIGNED ``required_wheels`` entry in ``docs/llms-install.md`` and the served wheel by a parity
    test, so the in-code pin can never silently drift from the signed manifest.
    """

    tool: str
    filename: str
    url: str
    sha256: str
    #: The expected ``<tool> --version`` substring — confirms the installed binary RUNS and is
    #: the pinned version (ce-ops#90 verify-fix: the post-install verify probes the install
    #: location and runs the version check there, not bare ``shutil.which`` on ``os.environ`` PATH).
    version: str = ""


#: The KNOWN SET of mirror-served userspace-tool wheels (design A). ``uv`` 0.11.21 matches the
#: ``python_acquisition`` version pinned in the signed ``docs/llms-install.md`` manifest and is
#: also listed under that manifest's ``required_wheels`` (so its integrity is rooted in the
#: ce-root-v1 signature). uv has NO Python dependencies → a single wheel installs offline clean.
MIRROR_USERSPACE_WHEELS: dict[str, MirrorUserspaceWheel] = {
    "uv": MirrorUserspaceWheel(
        tool="uv",
        filename="uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
        url=(
            "https://creator-engine.dev/downloads/0.2.0/"
            "uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
        ),
        sha256="b9ecdefa81db7e966d1655988cad6f840316228381dd69131ebc4ae9362bbccd",
        version="0.11.21",
    ),
}


def _default_pip_spawn(argv: Sequence[str]) -> subprocess.CompletedProcess:
    """Run an offline ``pip`` install in this interpreter; injectable so tests do ZERO pip."""
    return subprocess.run(  # noqa: S603 — fixed argv built from a pinned tool name + local dir
        list(argv), check=False, capture_output=True, text=True, timeout=300
    )


def _default_mirror_fetch(url: str) -> bytes:
    """GET ``url`` from CE's public mirror and return the bytes; injectable so tests do ZERO net.

    A plain HTTPS GET of a single pinned artifact from CE's OWN mirror — NOT a package index
    resolve (no PyPI/astral). The caller sha256-verifies the bytes against the in-code pin before
    use, so a tampered transport is caught at the verify gate, never trusted.
    """
    import urllib.request  # local import: keep the module import-light; only the live path needs it

    with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310 — fixed https CE mirror URL
        return resp.read()


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
    #: Injectable mirror-fetch seam (url -> bytes) for the apply-time userspace-dep install;
    #: tests inject a fake → ZERO network. None → live HTTPS GET of CE's mirror.
    mirror_fetch: Any = None
    #: Injectable ``pip`` spawn seam (argv -> CompletedProcess); tests inject a fake → ZERO pip.
    pip_spawn: Any = None
    #: Override for the venv scripts dir the userspace-tool verify probes (ce-ops#90 verify-fix).
    #: None → the running interpreter's scripts dir (where ``pip install`` placed the console
    #: script); tests inject a temp dir holding a fake binary. NOT a PATH search.
    scripts_dir: str | None = None
    #: ce-ops#85 adoption-apply — injectable secrets-scrub seam ``(scan_root, scaffold) -> dict``
    #: returning per-scanner reports. CI injects a fake → ZERO scanner. None → the live default
    #: (sha256-pinned mirror-served Gitleaks + TruffleHog; fail-closed when unpinned).
    scrub_scan: Any = None
    #: Optional runtime-supplied Gitleaks + TruffleHog mirror pins. ``resolve_live_config`` reads
    #: them from host env; absent or incomplete pins leave the scrub default fail-closed.
    brownfield_scanners: Mapping[str, BrownfieldScanner] | None = None


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


def _looks_like_branch_not_protected(parsed: object, stderr: str) -> bool:
    """True only for GitHub's branch-protection-absent signal, not generic API failure."""
    message = ""
    if isinstance(parsed, Mapping):
        message = str(parsed.get("message") or "")
    text = f"{message}\n{stderr or ''}".lower()
    return "branch not protected" in text


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


def _scanner_pins_from_env(env: Mapping[str, str]) -> Mapping[str, BrownfieldScanner] | None:
    """Runtime scanner-pin supply path for VPS Mode-A; absent/partial pins fail closed."""
    supplied = False
    pins: dict[str, BrownfieldScanner] = {}
    for tool, (url_key, sha_key, version_key) in SCANNER_ENV_KEYS.items():
        url = str(env.get(url_key) or "")
        sha256 = str(env.get(sha_key) or "")
        version = str(env.get(version_key) or "")
        if url or sha256 or version:
            supplied = True
        pins[tool] = BrownfieldScanner(
            tool=tool,
            version=version,
            url=url,
            sha256=sha256 if url and _valid_sha256(sha256) else "",
        )
    return pins if supplied else None


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


def _parse_http_status(raw_response: str) -> int | None:
    for line in raw_response.splitlines():
        if line.startswith("HTTP/"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None


def _parse_accepted_github_permissions(raw_response: str) -> dict[str, set[str]]:
    """Parse GitHub's fine-grained ``X-Accepted-GitHub-Permissions`` header."""
    permissions: dict[str, set[str]] = {}
    for line in raw_response.splitlines():
        if not line.strip():
            break
        if not line.lower().startswith("x-accepted-github-permissions:"):
            continue
        _, _, value = line.partition(":")
        for entry in value.replace(",", ";").split(";"):
            name, sep, level = entry.strip().partition("=")
            if sep and name and level:
                permissions.setdefault(name.strip().lower(), set()).add(level.strip().lower())
    return permissions


def _accepted_permissions_include(raw_response: str, permission: str) -> bool:
    name, sep, level = permission.partition(":")
    if not sep:
        return False
    accepted = _parse_accepted_github_permissions(raw_response)
    return level.lower() in accepted.get(name.lower(), set())


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


def _has_oauth_scopes_header(raw_response: str) -> bool:
    """True iff a ``gh api -i`` response carries an ``X-OAuth-Scopes`` header (classic/OAuth actor)."""
    for line in raw_response.splitlines():
        if not line.strip():
            break  # headers end at the first blank line; the body follows
        if line.lower().startswith("x-oauth-scopes:"):
            return True
    return False


def _detect_token_type(token: str, *, oauth_header_present: bool) -> str:
    """Classify the bootstrap PAT by prefix (ce-ops#94); header-presence as a fallback.

    Grounded in GitHub's documented token-format scheme: ``github_pat_`` = fine-grained PAT (emits
    NO ``X-OAuth-Scopes`` and exposes no permission introspection); ``ghp_`` = classic PAT,
    ``gho_`` = OAuth, ``ghu_`` = App user-to-server — all coarse-grained actors that DO emit
    ``X-OAuth-Scopes``. An unrecognized prefix that nonetheless carries the classic header is
    treated as ``classic``; anything else is ``unknown`` so the caller can fail closed.
    """
    t = (token or "").strip()
    if t.startswith("github_pat_"):
        return "fine_grained"
    if t.startswith(("ghp_", "gho_", "ghu_")):
        return "classic"
    if oauth_header_present:
        return "classic"
    return "unknown"


def _fine_grained_permission_probe_argv(repo: str, permission: str) -> list[str]:
    """Invalid-body probes: authorization must pass, but the request must not mutate."""
    if permission == "administration:write":
        return ["gh", "api", "-i", "-X", "PUT", f"repos/{repo}/actions/permissions"]
    if permission == "contents:write":
        return ["gh", "api", "-i", "-X", "POST", f"repos/{repo}/dispatches"]
    if permission == "actions:write":
        return ["gh", "api", "-i", "-X", "PUT", f"repos/{repo}/actions/oidc/customization/sub"]
    if permission == "workflows:write":
        return [
            "gh",
            "api",
            "-i",
            "-X",
            "PUT",
            f"repos/{repo}/contents/{FINE_GRAINED_PERMISSION_PROBE_PATH}",
        ]
    if permission == v3_installer.ORG_CREATE_SCOPE:
        owner = repo.split("/", 1)[0]
        return ["gh", "api", "-i", "-X", "POST", f"orgs/{owner}/repos"]
    return ["gh", "api", "-i", "user"]


def _fine_grained_permission_header(permission: str) -> str:
    if permission == v3_installer.ORG_CREATE_SCOPE:
        return "administration:write"
    return permission


def _fine_grained_permission_granted(proc: subprocess.CompletedProcess, permission: str) -> bool:
    raw = "\n".join(part for part in (proc.stdout or "", proc.stderr or "") if part)
    status = _parse_http_status(raw)
    # The probe requests intentionally omit required bodies. A 400/422 with the expected
    # fine-grained permission header means GitHub reached request validation after accepting
    # the token's permission. Any 2xx is refused: the probe must never mutate.
    return (
        status in {400, 422}
        and _accepted_permissions_include(raw, _fine_grained_permission_header(permission))
    )


def _probe_fine_grained_bootstrap_permissions(
    runner: GhRunner, *, repo: str, org_create_needed: bool
) -> list[str]:
    required = list(v3_installer.REQUIRED_BOOTSTRAP_SCOPES)
    if org_create_needed:
        required.append(v3_installer.ORG_CREATE_SCOPE)
    granted: list[str] = []
    for permission in required:
        try:
            proc = runner(_fine_grained_permission_probe_argv(repo, permission), None)
        except Exception:  # noqa: BLE001 — fail closed by omitting the permission
            continue
        if _fine_grained_permission_granted(proc, permission):
            granted.append(permission)
    return sorted(set(granted))


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
        and reports its login + ``token_type`` (ce-ops#94). For a CLASSIC token it also reports the
        CE bootstrap permissions implied by its ``X-OAuth-Scopes``. A FINE-GRAINED PAT emits no
        ``X-OAuth-Scopes``, so the driver probes GitHub's fine-grained permission endpoints and
        reports CE permission names in ``permissions``; no classic ``scopes`` set is fabricated.
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
        raw = proc.stdout or ""
        body = raw.split("\n\n", 1)[-1].strip()
        login = None
        try:
            login = (json.loads(body) or {}).get("login")
        except (json.JSONDecodeError, ValueError):
            login = None
        if not login:
            return {"ok": False, "reason": "bootstrap_probe_no_identity"}
        token_type = _detect_token_type(token, oauth_header_present=_has_oauth_scopes_header(raw))
        result: dict[str, Any] = {"ok": True, "login": login, "token_type": token_type}
        if token_type == "classic":
            # Only classic/OAuth actors expose capability via X-OAuth-Scopes (ce-ops#94). Fine-grained
            # PATs emit none, so classic scopes are never fabricated for them.
            result["scopes"] = _bootstrap_scopes_from_oauth(
                _parse_oauth_scopes_header(raw), org_create_needed=org_create_needed
            )
        elif token_type == "fine_grained":
            result["permissions"] = _probe_fine_grained_bootstrap_permissions(
                runner,
                repo=repo,
                org_create_needed=org_create_needed,
            )
        return result

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

    # -- plain-join HOST/APP legs (ce-ops#90 — 2nd live-driver gap, dev-3 dogfood; design A) --
    def install_dependencies(
        self,
        tools: Sequence[str],
        *,
        sudo_tools: Sequence[str],
        userspace_tools: Sequence[str],
    ) -> dict[str, Any]:
        """Install MISSING deps for an already-CE plain-join — OFFLINE, no-sudo, sha256-pinned.

        The base :class:`onboard_apply.ApplyDriver` refuses every userspace install
        (``no_userspace_installer_configured``); the dev-3 brownfield dogfood hit exactly that
        on the os-native ``uv`` dep (the 2nd live-forge driver leg left on the conservative base
        — the 1st was the detector, ce-ops#90 #241). **Design A (Operator-ratified):** each
        userspace tool's wheel is fetched from CE's own 0.2.0 mirror (``docs/downloads/0.2.0/``,
        NOT astral.sh / a live index), its bytes sha256-verified against the in-code pin
        (``MIRROR_USERSPACE_WHEELS``, bound to the SIGNED ``required_wheels`` entry) BEFORE
        install, then installed OFFLINE via ``pip install --no-index --find-links <dir> <tool>``;
        ``verify_tool`` must pass after. A pre-seeded ``CE_FORGE_WHEELHOUSE`` dir is honored as an
        offline FALLBACK (no fetch) when it already holds the pinned wheel. ``sudo_tools`` keep
        the base refusal (a §7 governed seat has no host package installer). Fail CLOSED on every
        fetch / hash-mismatch / install / verify failure; the staged temp dir is always cleaned.
        """
        if not tools:
            return {"ok": True, "installed": []}
        if sudo_tools:
            # governed seat: no host package installer, no sudo (base posture, unchanged).
            return {
                "ok": False,
                "reason": "no_host_package_installer_configured",
                "manual_rollback_required": True,
                "package_names": list(sudo_tools),
            }
        installed: list[str] = []
        staged_tmpdirs: list[Path] = []
        try:
            for tool in userspace_tools:
                pin = MIRROR_USERSPACE_WHEELS.get(tool)
                if pin is None:
                    return {"ok": False, "reason": "no_pinned_userspace_wheel", "tool": tool}
                staged = self._stage_userspace_wheel(pin)
                if not staged.get("ok"):
                    return staged
                if staged.get("tmpdir"):
                    staged_tmpdirs.append(Path(staged["dir"]))
                if not self._pip_install_offline(tool, Path(staged["dir"])):
                    return {"ok": False, "reason": "userspace_install_failed", "tool": tool}
                if not self.verify_tool(tool):
                    return {"ok": False, "reason": "userspace_tool_verify_failed", "tool": tool}
                installed.append(tool)
            return {"ok": True, "installed": installed}
        finally:
            for d in staged_tmpdirs:
                shutil.rmtree(d, ignore_errors=True)

    def wait_for_app_installation(
        self, *, app_plan: Mapping[str, Any], repo: str
    ) -> dict[str, Any]:
        """Read-only already-installed-App DETECT — the companion to ``verify_app_installation``.

        The base refuses ``app_installation_click_required`` unless the answers carry an
        ``installation_id``; a plain-join onto an already-CE repo has the App ALREADY installed,
        and the live driver holds the ``installation_id`` in its config. This confirms
        (read-only) the configured installation covers ``repo``, then returns ``detected=True`` —
        NO interactive click, NO mutation. Fail CLOSED if the id is unconfigured or coverage
        cannot be confirmed. (The leg then calls ``verify_app_installation`` for the authoritative
        coverage gate.)
        """
        installation_id = self._cfg.installation_id
        if not installation_id:
            return {"ok": False, "reason": "app_installation_id_unconfigured"}
        if not self._installation_covers_repo(repo):
            return {
                "ok": False,
                "reason": "app_installation_repo_not_covered",
                "installation_id": installation_id,
            }
        return {"ok": True, "installation_id": installation_id, "detected": True}

    def verify_tool(self, name: str) -> bool:
        """Verify a dep is installed — BRANCHED by tool class (ce-ops#90 verify-fix, dev-3).

        A userspace tool (``uv``) installs into the venv SCRIPTS dir, which is NOT on
        ``os.environ['PATH']``; the inherited base ``verify_tool`` → ``probe_tool`` →
        ``shutil.which`` therefore returned ``None`` and the leg refused
        ``userspace_tool_verify_failed`` even though the install succeeded (the #244 defect dev-3
        hit on a live ``--apply``). For a userspace tool we probe the ACTUAL install location
        (the absolute ``<scripts>/<tool>``) and run its ``--version`` there — NOT a PATH search.
        System tools (``git``/``python``/``runsc``/``proxy``) are correctly on PATH, so they keep
        the inherited base probe UNCHANGED. Fail-closed (missing / non-runnable / wrong version →
        ``False``), so a broken install still refuses.
        """
        if name in MIRROR_USERSPACE_WHEELS:
            return self._verify_userspace_tool(name)
        return super().verify_tool(name)

    def expose_cli(self, *, state_root: Path, command: str, via: str) -> dict[str, Any]:
        """Expose the v3 CLI as ``ce`` — resolving ``via`` at its INSTALL location, not just PATH.

        ce-ops#90 verify-fix AUDIT (whack-a-mole break): ``via`` is ``cev3``, a venv console
        script that — exactly like the ``uv`` verify defect dev-3 hit — may NOT be on
        ``os.environ['PATH']`` on a fresh userspace install, so the inherited base
        ``shutil.which('cev3')`` returns ``None`` → ``cli_exposure_failed`` at the NEXT leg. We
        resolve ``via`` to its absolute install path (the venv scripts dir) first; the base then
        accepts it (``shutil.which`` on an absolute executable returns it) and symlinks the shim
        onto it. Falls back to the bare name (PATH search, the base behavior) when the
        install-location resolution finds nothing — preserving non-venv layouts. The shim itself
        is invoked by absolute path in ``verify_cli``, so no PATH dependency remains downstream.
        """
        resolved = self._resolve_console_script(via)
        return super().expose_cli(state_root=state_root, command=command, via=resolved or via)

    # -- helpers for the host/app legs -------------------------------------------------------
    def _resolve_console_script(self, name: str) -> str | None:
        """Absolute path to a venv-installed console script at its INSTALL location, else ``None``."""
        for scripts in self._userspace_scripts_dirs():
            candidate = scripts / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return None

    def _verify_userspace_tool(self, tool: str) -> bool:
        """Probe a venv-installed userspace tool at its INSTALL LOCATION (not ``os.environ`` PATH).

        Resolves the interpreter's scripts dir(s) — where ``pip install`` placed the console
        script — and verifies the absolute ``<scripts>/<tool>`` exists AND ``<tool> --version``
        runs and reports the pinned version. Fail-closed on every miss (ce-ops#90 verify-fix).
        """
        pin = MIRROR_USERSPACE_WHEELS.get(tool)
        if pin is None:
            return False
        for scripts in self._userspace_scripts_dirs():
            candidate = scripts / tool
            if not candidate.is_file():
                continue
            try:
                proc = subprocess.run(  # noqa: S603 — fixed argv; candidate is an absolute install path
                    [str(candidate), "--version"],
                    check=False, capture_output=True, text=True, timeout=30,
                )
            except Exception:  # noqa: BLE001 — not runnable (perms/arch/...) → fail-closed
                continue
            if proc.returncode != 0:
                continue
            output = (proc.stdout or "") + (proc.stderr or "")
            if not pin.version or pin.version in output:
                return True
        return False

    def _userspace_scripts_dirs(self) -> list[Path]:
        """The candidate scripts dirs the userspace verify probes (NOT a PATH search).

        Config override (tests) → the running interpreter's ``sysconfig`` scripts path AND
        ``dirname(sys.executable)`` (a venv puts both at ``<venv>/bin`` and pip installs console
        scripts there). De-duplicated, order-preserving; fail-closed callers tolerate an empty list.
        """
        if self._cfg.scripts_dir:
            return [Path(self._cfg.scripts_dir)]
        candidates: list[Path] = []
        try:
            scripts = sysconfig.get_path("scripts")
            if scripts:
                candidates.append(Path(scripts))
        except Exception:  # noqa: BLE001 — defensive: sysconfig scheme edge cases never crash verify
            pass
        candidates.append(Path(sys.executable).resolve().parent)
        seen: set[str] = set()
        unique: list[Path] = []
        for c in candidates:
            if str(c) not in seen:
                seen.add(str(c))
                unique.append(c)
        return unique

    def _installation_covers_repo(self, repo: str) -> bool:
        """True iff the configured App installation's repositories include ``repo`` (read-only GET)."""
        try:
            code, parsed, _ = _gh_get(self._reader(), "installation/repositories?per_page=100")
        except Exception:  # noqa: BLE001 — fail-closed: any read error → not confirmable
            return False
        if code != 0 or not isinstance(parsed, dict):
            return False
        repos = parsed.get("repositories") or []
        return any(isinstance(r, Mapping) and r.get("full_name") == repo for r in repos)

    def _stage_userspace_wheel(self, pin: "MirrorUserspaceWheel") -> dict[str, Any]:
        """Make a ``--find-links`` dir holding the sha256-verified pinned wheel.

        DEFAULT = fetch ``pin.url`` from CE's mirror into a fresh temp dir (caller cleans it).
        FALLBACK = if ``CE_FORGE_WHEELHOUSE`` points at a dir already holding the pinned wheel,
        verify + use it in place (no fetch, no temp dir). Either way the wheel's bytes are
        sha256-verified against the pin BEFORE it is returned; fail-closed on mismatch / fetch
        error. Returns ``{ok, dir, tmpdir?}`` or ``{ok: False, reason, ...}``.
        """
        env_dir = os.environ.get(ENV_WHEELHOUSE)
        if env_dir:
            d = Path(env_dir)
            wheel = d / pin.filename
            if d.is_dir() and wheel.is_file():
                actual = hashlib.sha256(wheel.read_bytes()).hexdigest()
                if actual != pin.sha256:
                    return {
                        "ok": False,
                        "reason": "userspace_wheel_sha256_mismatch",
                        "tool": pin.tool,
                        "source": "wheelhouse_fallback",
                        "expected": pin.sha256,
                        "actual": actual,
                    }
                return {"ok": True, "dir": str(d), "tmpdir": False, "source": "wheelhouse_fallback"}
            # env set but the pinned wheel is absent there → fall through to the mirror default.
        tmpdir = Path(tempfile.mkdtemp(prefix="ce-userspace-dep-"))
        try:
            data = self._mirror_fetch(pin.url)
        except Exception:  # noqa: BLE001 — fail-closed: any fetch/transport error → refuse
            shutil.rmtree(tmpdir, ignore_errors=True)
            return {"ok": False, "reason": "userspace_wheel_fetch_failed", "tool": pin.tool, "url": pin.url}
        actual = hashlib.sha256(data).hexdigest()
        if actual != pin.sha256:
            # ANTI-TAMPER: a fetched wheel whose bytes drift from the signed pin is REFUSED.
            shutil.rmtree(tmpdir, ignore_errors=True)
            return {
                "ok": False,
                "reason": "userspace_wheel_sha256_mismatch",
                "tool": pin.tool,
                "source": "mirror_fetch",
                "expected": pin.sha256,
                "actual": actual,
            }
        (tmpdir / pin.filename).write_bytes(data)
        return {"ok": True, "dir": str(tmpdir), "tmpdir": True, "source": "mirror_fetch"}

    def _mirror_fetch(self, url: str) -> bytes:
        """Fetch ``url`` via the injected seam, else the default live HTTPS GET of CE's mirror."""
        fetch = self._cfg.mirror_fetch if self._cfg.mirror_fetch is not None else _default_mirror_fetch
        return fetch(url)

    def _pip_install_offline(self, tool: str, find_links: Path) -> bool:
        """``pip install --no-index --find-links <dir> <tool>`` — OFFLINE; never raises.

        ``--no-index`` guarantees no PyPI/astral resolve; the tool installs only from the
        sha256-verified local ``find_links`` dir. The spawn seam is injectable (tests → ZERO pip).
        """
        argv = [
            sys.executable, "-m", "pip", "install",
            "--no-index", "--find-links", str(find_links), tool,
        ]
        spawn = self._cfg.pip_spawn or _default_pip_spawn
        try:
            proc = spawn(argv)
        except Exception:  # noqa: BLE001 — fail-closed: any spawn error → install failed
            return False
        return getattr(proc, "returncode", 1) == 0

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


class LiveForgeAdoptionDriver(LiveForgeApplyDriver):
    """ce-ops#85 E3 adoption driver — the join-PR layer (two-token model + hard scrub gate).

    Subclasses :class:`LiveForgeApplyDriver`, so the read-only detection legs AND the
    inherited Phase-1 READ token (``PHASE1_PERMISSIONS`` incl ``administration:read``, which
    leg-6 rides) are REUSED unchanged. It ADDS the adoption legs' bodies and the SECOND token:

    Two-token model (verify-verdict MAJOR-1):
      * READ legs (1 drift-check, 2 secret-preflight, 6 preserved-checks) ride the INHERITED
        Phase-1 read token via ``_reader()`` — incl ``administration:read`` for the protection
        read. NO write scope.
      * WRITE legs (4 push, 5 open-PR) ride a SEPARATE token minted lazily by ``_writer()`` at
        the §6.1 ceiling (``ADOPTION_WRITE_PERMISSIONS`` + ``ADOPTION_ESCALATION_AUTHORITY``),
        and REVOKED the instant leg 5 finishes (``_revoke_write``). The write token never
        carries ``administration:*``. ``close()`` revokes BOTH tokens as a backstop.

    Hard scrub gate (verify-verdict MAJOR-2): ``secret_preflight_scan`` runs the sha-pinned
    two-scanner scrub; the ``brownfield_secret_preflight`` leg (in ``onboard_apply``) is the
    affirmative fail-closed authority. The live default fail-closes until the binary pins are
    commissioned at the VPS Mode-A rehearsal.

    Defensive only — PR-mediated, never force-pushes, never mutates branch protection, never
    direct-pushes the default branch; idempotent (stable branch + plan-by-default forge primitives).
    """

    def __init__(self, config: LiveForgeConfig):
        super().__init__(config)
        self._write_token: ScopedToken | None = None
        self._write_runner: GhRunner | None = None
        self._write_revoked: bool = False

    # -- WRITE-token lifecycle (legs 4-5 ONLY; minted late, revoked immediately after) ------
    def _writer(self) -> GhRunner:
        """Lazily mint the §6.1 WRITE token (Tier-2 escalation bound) and return its runner."""
        if self._write_runner is None:
            mint_runner = app_jwt_gh_runner(
                self._cfg.app_client_id, signer=self._cfg.signer, transport=self._cfg.transport
            )
            request = TokenRequest(
                repo=self._cfg.repo,
                installation_id=self._cfg.installation_id,
                run_id=self._cfg.run_id,
                policy_sha=self._cfg.policy_sha,
                permissions=ADOPTION_WRITE_PERMISSIONS,
                secret_name=FORGE_WRITE_SECRET_NAME,
                requested_ttl_seconds=FORGE_WRITE_TTL_SECONDS,
                escalation_authority=ADOPTION_ESCALATION_AUTHORITY,
            )
            # Tier-2 default-deny: if a future edit dropped ADOPTION_ESCALATION_AUTHORITY, the
            # minter raises TokenMintRefused BEFORE any forge call (defence-in-depth, §6.3).
            self._write_token = mint_scoped_token(request, gh_runner=mint_runner)
            self._write_runner = authenticated_gh_runner(self._write_token, spawn=self._cfg.spawn)
        return self._write_runner

    def _revoke_write(self) -> None:
        """Revoke the WRITE token the instant legs 4-5 are done (never raises; never leaks)."""
        if (
            self._write_token is not None
            and self._write_runner is not None
            and not self._write_revoked
        ):
            with contextlib.suppress(ForgeConfigError, OSError):
                revoke_scoped_token(self._write_token, gh_runner=self._write_runner)
        self._write_revoked = True
        self._write_token = None
        self._write_runner = None

    def close(self) -> None:
        """Revoke BOTH the WRITE token (backstop) and the inherited READ token."""
        self._revoke_write()
        super().close()

    # -- leg 2: the sha-pinned two-scanner secrets scrub --------------------------------------
    def secret_preflight_scan(
        self, *, scan_root: str, scaffold: Sequence[Mapping[str, Any]]
    ) -> dict[str, Any]:
        scan = self._cfg.scrub_scan if self._cfg.scrub_scan is not None else self._default_scrub_scan
        try:
            return scan(scan_root, list(scaffold))
        except Exception as exc:  # noqa: BLE001 — fail-closed: a seam error is NOT clean
            return {
                "scanners": {
                    name: {"ran": False, "exit_code": None, "findings": [], "error": f"scrub seam error: {exc}"}
                    for name in REQUIRED_SCRUB_SCANNERS
                }
            }

    def _default_scrub_scan(self, scan_root: str, scaffold: list) -> dict[str, Any]:
        """Live scrub: per-scanner sha-pinned run; fail-closed (``ran=False``) until pinned.

        Each scanner's report is ``{ran, exit_code, findings, error}``. With an EMPTY pin (the
        as-shipped state — concrete binary pins are commissioned at the VPS Mode-A rehearsal)
        the report is ``ran=False`` so the leg refuses ``brownfield_secret_scanner_unavailable``
        — NO unverified binary is ever executed and absence is never read as clean.

        When scanner pins are supplied, scan a temporary materialized tree containing BOTH the
        pre-existing project bytes and every scaffold artifact leg 3 would commit, matching the
        plan-side ``scan_paths`` contract: ``[".", *scaffold_paths]``.
        """
        reports: dict[str, Any] = {}
        scanner_pins = self._cfg.brownfield_scanners or BROWNFIELD_SCANNERS
        active_pins: dict[str, BrownfieldScanner] = {}
        for name in REQUIRED_SCRUB_SCANNERS:
            pin = scanner_pins.get(name)
            if pin is None or not pin.sha256:
                reports[name] = {
                    "ran": False,
                    "exit_code": None,
                    "findings": [],
                    "error": (
                        f"{name}: scanner binary not sha256-pinned — commission the mirror pin "
                        "at the VPS Mode-A rehearsal (fail-closed until then)"
                    ),
                }
            else:
                active_pins[name] = pin
        if not active_pins:
            return {"scanners": reports}
        materialized_root, cleanup_root, scan_paths = self._materialize_scrub_scan_tree(scan_root, scaffold)
        try:
            for name, pin in active_pins.items():
                reports[name] = self._run_pinned_scanner(pin, materialized_root)
            return {"scanners": reports, "scan_paths": scan_paths}
        finally:
            shutil.rmtree(cleanup_root, ignore_errors=True)

    def _materialize_scrub_scan_tree(
        self, scan_root: str, scaffold: Sequence[Mapping[str, Any]]
    ) -> tuple[str, str, list[str]]:
        """Copy ``scan_root`` and overlay scaffold artifacts so scanners cover the full mutation surface."""
        source = Path(scan_root).expanduser()
        if not source.is_dir():
            raise FileNotFoundError(f"scrub scan root is not a directory: {scan_root}")
        cleanup_root = Path(tempfile.mkdtemp(prefix="ce-scrub-tree-"))
        materialized = cleanup_root / "tree"
        try:
            shutil.copytree(source, materialized, symlinks=True)
            scaffold_paths: list[str] = []
            for artifact in scaffold:
                rel = Path(str(artifact["path"]))
                if rel.is_absolute() or ".." in rel.parts:
                    raise ValueError(f"scaffold path escapes scrub tree: {rel}")
                target = materialized / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(artifact["content"]), encoding="utf-8")
                scaffold_paths.append(rel.as_posix())
            return str(materialized), str(cleanup_root), [".", *scaffold_paths]
        except Exception:
            shutil.rmtree(cleanup_root, ignore_errors=True)
            raise

    def _run_pinned_scanner(self, pin: "BrownfieldScanner", scan_root: str) -> dict[str, Any]:
        """Stage the sha256-pinned scanner binary (fetch+verify) and run it; never raises.

        Reuses the wheel-staging anti-tamper pattern: fetch ``pin.url`` from CE's mirror, verify
        the bytes against ``pin.sha256`` BEFORE making it executable, then run the tool over
        ``scan_root``. Returns ``{ran, exit_code, findings, error}`` — fail-closed on any
        fetch/hash/spawn error. (Commission-gated; exercised at the VPS Mode-A rehearsal.)
        """
        staged_dir = Path(tempfile.mkdtemp(prefix=f"ce-scanner-{pin.tool}-"))
        try:
            try:
                data = self._mirror_fetch(pin.url)
            except Exception as exc:  # noqa: BLE001
                return {"ran": False, "exit_code": None, "findings": [], "error": f"{pin.tool}: fetch failed: {exc}"}
            actual = hashlib.sha256(data).hexdigest()
            if actual != pin.sha256:
                return {
                    "ran": False, "exit_code": None, "findings": [],
                    "error": f"{pin.tool}: sha256 mismatch (expected {pin.sha256}, got {actual})",
                }
            binary = staged_dir / pin.tool
            binary.write_bytes(data)
            binary.chmod(0o700)
            argv = _scanner_argv(pin.tool, str(binary), scan_root)
            spawn = self._cfg.pip_spawn or _default_pip_spawn  # reuse the injectable spawn shape
            try:
                proc = spawn(argv)
            except Exception as exc:  # noqa: BLE001
                return {"ran": False, "exit_code": None, "findings": [], "error": f"{pin.tool}: spawn failed: {exc}"}
            try:
                findings = _parse_scanner_findings(pin.tool, getattr(proc, "stdout", "") or "")
            except ValueError as exc:
                return {
                    "ran": True,
                    "exit_code": getattr(proc, "returncode", 1),
                    "findings": [],
                    "error": str(exc),
                }
            return {"ran": True, "exit_code": getattr(proc, "returncode", 1), "findings": findings}
        finally:
            shutil.rmtree(staged_dir, ignore_errors=True)

    # -- leg 3: build the value-free scaffold on the adoption branch (local git only) ---------
    def build_adoption_scaffold(
        self,
        *,
        repo: str,
        base: str,
        branch: str,
        workspace_root: Path,
        artifacts: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        checkout = self.checkout_workspace(repo=repo, branch=base, workspace_root=workspace_root)
        if not checkout.get("ok"):
            return {"ok": False, "reason": checkout.get("reason", "checkout_failed")}
        repo_dir = Path(checkout["path"])
        # stable adoption branch from base (``-B`` resets to base head → idempotent re-run).
        if self._git(["checkout", "-B", branch], cwd=repo_dir).returncode != 0:
            return {"ok": False, "reason": "adoption_branch_checkout_failed"}
        written: list[str] = []
        for artifact in artifacts:
            target = repo_dir / str(artifact["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(artifact["content"]), encoding="utf-8")
            written.append(str(artifact["path"]))
        add = self._git(["add", *written], cwd=repo_dir)
        if add.returncode != 0:
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_commit_failed",
                "git add failed while staging the adoption scaffold",
            )
        commit = self._git(
            ["commit", "-m", "ce: adopt project into CE governance (join PR)"], cwd=repo_dir
        )
        combined = ((commit.stdout or "") + (commit.stderr or "")).lower()
        already = commit.returncode != 0 and "nothing to commit" in combined
        if commit.returncode != 0 and not already:
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_commit_failed",
                "git commit failed while committing the adoption scaffold",
            )
        head = self._git(["rev-parse", "HEAD"], cwd=repo_dir)
        if head.returncode != 0 or not (head.stdout or "").strip():
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_commit_verify_failed",
                "cannot resolve adoption commit HEAD",
            )
        tree = self._git(["ls-tree", "-r", "--name-only", "HEAD", "--", *written], cwd=repo_dir)
        if tree.returncode != 0:
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_commit_verify_failed",
                "cannot inspect committed adoption scaffold tree",
            )
        committed_paths = {line.strip() for line in (tree.stdout or "").splitlines() if line.strip()}
        missing = sorted(set(written) - committed_paths)
        if missing:
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_commit_verify_failed",
                "adoption commit does not contain scaffold path(s): " + ", ".join(missing),
            )
        workflow = self._git(["show", f"HEAD:{onboard_apply.CE_WORKFLOW_PATH}"], cwd=repo_dir)
        if workflow.returncode != 0:
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_commit_verify_failed",
                "adoption commit does not contain the CE validate workflow",
            )
        workflow_sha = hashlib.sha256((workflow.stdout or "").encode("utf-8")).hexdigest()
        if workflow_sha != onboard_apply.CE_WORKFLOW_SHA256:
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_commit_verify_failed",
                "committed CE validate workflow digest does not match the pinned workflow",
            )
        return {
            "ok": True,
            "source_dir": str(repo_dir),
            "head_sha": (head.stdout or "").strip(),
            "scaffold_paths": written,
            "workflow_sha256": workflow_sha,
            "already": already,
        }

    def _git(self, args: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess:
        """Run a LOCAL git command (no credential needed) through the git spawn seam."""
        argv = ["git", "-C", str(cwd), *args]
        env = dict(os.environ)
        if self._cfg.git_spawn is not None:
            return self._cfg.git_spawn(argv, None, env)
        return subprocess.run(  # noqa: S603 — fixed git argv; local working-tree ops only
            argv, check=False, capture_output=True, text=True, env=env, timeout=120
        )

    # -- leg 4: push the adoption branch (WRITE token; never force) ---------------------------
    def push_adoption_branch(self, *, repo: str, branch: str, source_dir: str) -> dict[str, Any]:
        self._writer()  # ensure the WRITE token is minted
        assert self._write_token is not None
        try:
            result = push_change(
                repo, branch, source_dir=source_dir, token=self._write_token,
                apply=True, spawn=self._cfg.git_spawn,
            )
        except PushRefused as exc:
            self._revoke_write()
            return {"ok": False, "reason": "push_refused", "detail": str(exc)}
        except ForgeConfigError as exc:
            self._revoke_write()
            return {"ok": False, "reason": "push_failed", "detail": str(exc)}
        return {
            "ok": True,
            "pushed": result.pushed,
            "up_to_date": result.up_to_date,
            "local_head": result.local_head,
            "remote_head": result.remote_head,
        }

    # -- leg 5: open exactly one join PR (WRITE token; revoke immediately after) ---------------
    def open_adoption_pr(
        self,
        *,
        repo: str,
        branch: str,
        base: str,
        manifest_paths: Sequence[str],
        plan_ref: str,
    ) -> dict[str, Any]:
        runner = self._writer()
        try:
            ref = open_change(
                repo, branch, base, list(manifest_paths), plan_ref, apply=True, gh_runner=runner
            )
        except (ForgeConfigError, ForgeConfigRefused) as exc:
            return {"ok": False, "reason": "open_pr_failed", "detail": str(exc)}
        finally:
            # the WRITE token has done its job (legs 4-5) — revoke it now, not at close().
            self._revoke_write()
        return {
            "ok": True,
            "pr_number": ref.pr_number,
            "head_sha": ref.head_sha,
            "verified": ref.verified,
            "claimed": not ref.changed,
        }

    # -- leg 6: confirm no existing check/workflow dropped (READ token) ------------------------
    def read_preserved_checks(
        self, *, repo: str, base: str, expected_checks: Sequence[str]
    ) -> dict[str, Any]:
        # Rides the INHERITED READ token (administration:read) — the WRITE token is already
        # revoked after leg 5. The join PR is additive (leg 3 only WRITES new files and never
        # issues a protection PUT), so by construction nothing is dropped; this CONFIRMS the
        # live state is readable and reports the preserved contexts. A read failure is
        # fail-closed (cannot affirm preservation → the leg fails).
        try:
            code, parsed, stderr = _gh_get(
                self._reader(), f"repos/{repo}/branches/{base}/protection"
            )
        except Exception:  # noqa: BLE001
            raise onboard_apply.ApplyRefused(
                "brownfield_protection_read_failed",
                "branch-protection read raised before preservation could be affirmed",
            ) from None
        if code != 0:
            if _looks_like_branch_not_protected(parsed, stderr):
                # Affirmative 404/not-protected signal → no required checks exist to drop.
                return {"ok": True, "existing_checks": [], "dropped": []}
            raise onboard_apply.ApplyRefused(
                "brownfield_protection_read_failed",
                f"branch-protection read returned non-404 error (gh rc={code}); refusing to infer clean",
            )
        if not isinstance(parsed, dict):
            return {"ok": False, "reason": "preserved_checks_read_failed"}
        live = list(_protection_contexts(parsed))
        # Additive PR drops nothing; ``dropped`` is empty by construction (a defensive seam a
        # future protection-mutating phase would populate). ``expected_checks`` is reported.
        return {"ok": True, "existing_checks": live, "expected_checks": list(expected_checks), "dropped": []}


def _scanner_argv(tool: str, binary: str, scan_root: str) -> list[str]:
    """The documented detect command per scanner (commission-gated; VPS Mode-A)."""
    if tool == "gitleaks":
        return [binary, "detect", "--source", scan_root, "--no-banner", "--report-format", "json", "--report-path", "-"]
    if tool == "trufflehog":
        return [binary, "filesystem", scan_root, "--json", "--no-update"]
    return [binary, "--version"]


def _parse_scanner_findings(tool: str, stdout: str) -> list[str]:
    """Parse a scanner's JSON output into value-FREE finding ids (never raw secret values)."""
    findings: list[str] = []
    text = (stdout or "").strip()
    if not text:
        return findings
    # Both tools emit JSON (gitleaks an array; trufflehog newline-delimited objects). We extract
    # ONLY a stable, value-free locator (file:line / source) as the finding id — never the secret.
    candidates: list[Any] = []
    try:
        parsed = json.loads(text)
        candidates = parsed if isinstance(parsed, list) else [parsed]
    except (json.JSONDecodeError, ValueError):
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                candidates.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                raise ValueError(f"{tool}: unparseable scanner JSON output") from None
    for index, item in enumerate(candidates):
        if not isinstance(item, Mapping):
            raise ValueError(f"{tool}: unparseable scanner finding record")
        source_meta = item.get("SourceMetadata")
        locator = item.get("File") or item.get("file")
        if not locator and isinstance(source_meta, Mapping):
            locator = source_meta.get("Data")
        line_no = item.get("StartLine") or item.get("line") or ""
        findings.append(f"{tool}:{locator or 'finding'}:{line_no or index}")
    return findings


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
        brownfield_scanners=_scanner_pins_from_env(env),
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


def adoption_forge_select(
    base: onboard_apply.ApplyDriver,
    *,
    merged: "v3_installer.MergeResult",
    policy_sha: str,
    env: Mapping[str, str] | None = None,
) -> onboard_apply.ApplyDriver:
    """Select the E3 adoption driver ONLY under the DUAL escalation (§6.3); else delegate.

    ce-ops#85 fail-closed selection: returns :class:`LiveForgeAdoptionDriver` iff BOTH
    ``CE_FORGE_LIVE_FORGE`` AND ``CE_FORGE_ADOPTION_WRITE`` are set true AND the App credentials
    resolve. Otherwise it delegates to :func:`live_forge_select` (the READ-only live driver when
    only ``CE_FORGE_LIVE_FORGE`` is set, or ``base`` when OFF) — so an unauthorized run keeps the
    unchanged ``brownfield_deferred`` status quo. The adoption driver IS-A
    :class:`LiveForgeApplyDriver`, so detection reads still work on it; the CLI uses
    ``isinstance(..., LiveForgeAdoptionDriver)`` to know the WRITE escalation is authorized.
    """
    env = os.environ if env is None else env
    if not (_flag_true(env.get(ENV_LIVE_FORGE)) and _flag_true(env.get(ENV_ADOPTION_WRITE))):
        return live_forge_select(base, merged=merged, policy_sha=policy_sha, env=env)
    config = resolve_live_config(merged, policy_sha=policy_sha, env=env)
    if config is None:
        return base  # authorized but unconfigured → fail-closed to the base noop driver
    return LiveForgeAdoptionDriver(config)
