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
import inspect
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from . import onboard_apply, v3_installer
from .forge.app_jwt_runner import Signer, app_jwt_gh_runner, build_app_jwt
from .forge.change import open_change
from .forge.change_push import PushRefused, push_change
from .forge.credential_runner import authenticated_gh_runner
from .forge.github_repo_config import (
    BranchProtectionPolicy,
    ForgeConfigError,
    ForgeConfigRefused,
    GhRunner,
)
from .forge.protection_diagnostics import (
    PROTECTION_FLOOR_UNENFORCEABLE_CODE,
    protection_floor_unenforceable,
    protection_floor_unenforceable_diagnostic,
)
from .forge.ruleset import (
    CE_PROTECTION_RULESET_NAME,
    RulesetPolicy,
    ruleset_satisfies_policy,
)
from .forge.scoped_token import (
    ScopedToken,
    TokenRequest,
    mint_scoped_token,
    revoke_scoped_token,
)

__ce_version_line__ = "v3"

#: ce-ops#157 — the token-minting seam. A ``token_minter`` maps a validated
#: :class:`~creator_engine_validator.forge.scoped_token.TokenRequest` to a minted
#: :class:`~creator_engine_validator.forge.scoped_token.ScopedToken`. When set on
#: :class:`LiveForgeConfig` it REPLACES the in-process local-signer mint path
#: (``app_jwt_gh_runner`` → ``mint_scoped_token``): the standing shared-App mint broker holds
#: the key and mints server-side, so a user can join WITHOUT a PEM on their disk. The driver
#: builds the SAME request either way, so the least-privilege ceiling is identical regardless
#: of who mints. ``None`` (the default) keeps today's local-signer path byte-for-byte.
TokenMinter = Callable[[TokenRequest], ScopedToken]

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
#: ce-ops#157 — the shared-App mint-broker URL. When set on a ``github.app.kind: shared`` run,
#: the driver mints its scoped token via the standing broker (``POST <url>/v1/token``) instead
#: of a local PEM signer, so the user needs NO App private key on disk. Absent → the shared run
#: falls through to the local-signer path (and is ``None`` if no PEM resolves — fail-closed).
ENV_MINT_BROKER_URL = "CE_FORGE_MINT_BROKER_URL"
#: ce-ops#157 — the caller's ``ghu_`` user token (from the S1 device flow) the broker uses for
#: its user->installation binding check. Carried host-side, never in the portable answers file.
ENV_MINT_BROKER_USER_TOKEN = "CE_FORGE_MINT_BROKER_USER_TOKEN"
NETWORK_SUBPROCESS_TIMEOUT_ENV = "CE_NETWORK_SUBPROCESS_TIMEOUT_SECONDS"
DEFAULT_NETWORK_SUBPROCESS_TIMEOUT_SECONDS = 60.0

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
    """A sha256-pinned secrets scanner for the brownfield scrub gate (§3.3, OQ-5).

    Gitleaks + TruffleHog (the client-zero runbook pair). ``sha256`` pins the EXACT fetched
    artifact bytes; an EMPTY ``sha256`` means UNPINNED -> the live scan fail-closes
    (``ran=False``) so an unverified artifact is NEVER executed. ``archive_member`` names the
    regular file to extract when the pinned URL is a release tarball.
    """

    tool: str
    version: str
    url: str
    sha256: str
    platform: str = ""
    archive_member: str = ""


#: The two-scanner set the scrub gate requires (mirrors ``onboard_apply.REQUIRED_SCRUB_SCANNERS``).
REQUIRED_SCRUB_SCANNERS: tuple[str, ...] = ("gitleaks", "trufflehog")
GITLEAKS_RELEASE_BASE_URL = "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1"
TRUFFLEHOG_RELEASE_BASE_URL = "https://github.com/trufflesecurity/trufflehog/releases/download/v3.95.6"

#: ce-ops#159 commissioned scanner release pins. Hashes are reproduced from the upstream
#: GitHub release archives and checked against the publishers' checksum files. The live path
#: verifies the archive bytes before extracting the expected scanner binary; any fetch/hash/
#: extraction drift fail-closes before execution.
BROWNFIELD_SCANNER_MIRROR: tuple[BrownfieldScanner, ...] = (
    BrownfieldScanner(
        tool="gitleaks",
        version="8.30.1",
        url=f"{GITLEAKS_RELEASE_BASE_URL}/gitleaks_8.30.1_linux_x64.tar.gz",
        sha256="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
        platform="linux/x86_64",
        archive_member="gitleaks",
    ),
    BrownfieldScanner(
        tool="gitleaks",
        version="8.30.1",
        url=f"{GITLEAKS_RELEASE_BASE_URL}/gitleaks_8.30.1_linux_arm64.tar.gz",
        sha256="e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080",
        platform="linux/arm64",
        archive_member="gitleaks",
    ),
    BrownfieldScanner(
        tool="trufflehog",
        version="3.95.6",
        url=f"{TRUFFLEHOG_RELEASE_BASE_URL}/trufflehog_3.95.6_linux_amd64.tar.gz",
        sha256="1b62ea3cbc672ed5fd36e0eebb00b1fb50bbb7ee35090f42437a5852a299e16b",
        platform="linux/x86_64",
        archive_member="trufflehog",
    ),
    BrownfieldScanner(
        tool="trufflehog",
        version="3.95.6",
        url=f"{TRUFFLEHOG_RELEASE_BASE_URL}/trufflehog_3.95.6_linux_arm64.tar.gz",
        sha256="e0d8722485bf592f9ef9a72009fb5184656cfab4864fed453bbbf694d5b9350b",
        platform="linux/arm64",
        archive_member="trufflehog",
    ),
)


def _host_scanner_platform() -> str | None:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system != "linux":
        return None
    if machine in {"x86_64", "amd64"}:
        return "linux/x86_64"
    if machine in {"aarch64", "arm64"}:
        return "linux/arm64"
    return None


def _scanner_pins_for_platform(platform: str | None) -> dict[str, BrownfieldScanner]:
    """Return the commissioned scanner pins for a supported platform, else fail-closed empty."""
    if not platform:
        return {}
    return {pin.tool: pin for pin in BROWNFIELD_SCANNER_MIRROR if pin.platform == platform}


#: The live default scanner pins for this host. Unsupported hosts get an empty mapping, which
#: keeps the scrub gate fail-closed with ``brownfield_secret_scanner_unavailable``.
BROWNFIELD_SCANNERS: dict[str, BrownfieldScanner] = _scanner_pins_for_platform(
    _host_scanner_platform()
)
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
#: OPTIONAL offline FALLBACK for the apply-time userspace-dep install. Design A's DEFAULT path
#: fetches the pinned ``uv`` wheel from CE's mirror; if this env points at a directory that
#: already holds the pinned wheel (sha256-verified), the driver uses it instead of fetching —
#: a no-egress fallback for air-gapped / pre-seeded hosts. Absent → mirror-fetch (the default).
ENV_WHEELHOUSE = "CE_FORGE_WHEELHOUSE"
ENV_RUNTIME_BIN_DIR = "CE_FORGE_RUNTIME_BIN_DIR"
_GITHUB_API_ROOT = "https://api.github.com"
_GITHUB_API_VERSION = "2022-11-28"
_GITHUB_ACCEPT = "application/vnd.github+json"


@dataclass(frozen=True)
class MirrorUserspaceWheel:
    """A sha256-pinned, no-sudo userspace tool wheel SERVED FROM CE's own versioned mirror.

    Design A (Operator-ratified, ce-ops#90): the apply-time ``install_dependencies`` leg
    fetches ``url`` from CE's mirror (``docs/downloads/<version>/``, NOT astral.sh / PyPI), verifies
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
            "https://creator-engine.dev/downloads/0.3.6/"
            "uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
        ),
        sha256="b9ecdefa81db7e966d1655988cad6f840316228381dd69131ebc4ae9362bbccd",
        version="0.11.21",
    ),
}


@dataclass(frozen=True)
class PinnedSystemTool:
    """A sha-pinned host runtime binary installed during gVisor runtime provisioning."""

    tool: str
    version: str
    filename: str
    url: str
    digest: str
    digest_algo: str
    version_args: tuple[str, ...] = ("--version",)


GVISOR_RUNSC_VERSION = "20260608.0"
GVISOR_GVPROXY_VERSION = "v0.8.9"
GVISOR_RUNTIME_TOOLS: tuple[str, ...] = ("runsc", "gvproxy")
PINNED_SYSTEM_TOOLS: dict[str, dict[str, PinnedSystemTool]] = {
    "runsc": {
        "x86_64": PinnedSystemTool(
            tool="runsc",
            version=GVISOR_RUNSC_VERSION,
            filename="runsc",
            url=(
                "https://storage.googleapis.com/gvisor/releases/release/"
                f"{GVISOR_RUNSC_VERSION}/x86_64/runsc"
            ),
            digest=(
                "8ecbf845e50880ab65573153756aea01da2823d05a61bce23c6c24f4446d064a"
                "b5a253e7ee6a8b619c5934c373ea74487c7c2ab2754dfb1e0b27860c6e0d2014"
            ),
            digest_algo="sha512",
        ),
        "aarch64": PinnedSystemTool(
            tool="runsc",
            version=GVISOR_RUNSC_VERSION,
            filename="runsc",
            url=(
                "https://storage.googleapis.com/gvisor/releases/release/"
                f"{GVISOR_RUNSC_VERSION}/aarch64/runsc"
            ),
            digest=(
                "9c7c74453b3a08c6663d72680355edb56a86e9b1ef6637b0ab5942b576d47"
                "eaf2ab6b448a0f8e9408757c6ffed116ff95d2885e6ed8cc0bd3b27036af5b27450"
            ),
            digest_algo="sha512",
        ),
    },
    "gvproxy": {
        "x86_64": PinnedSystemTool(
            tool="gvproxy",
            version=GVISOR_GVPROXY_VERSION,
            filename="gvproxy-linux-amd64",
            url=(
                "https://github.com/containers/gvisor-tap-vsock/releases/download/"
                f"{GVISOR_GVPROXY_VERSION}/gvproxy-linux-amd64"
            ),
            digest="3011c5629c9138d2050fb23c510e09ae53e30ec52e6a9ab85632bc1550e8ef63",
            digest_algo="sha256",
        ),
        "aarch64": PinnedSystemTool(
            tool="gvproxy",
            version=GVISOR_GVPROXY_VERSION,
            filename="gvproxy-linux-arm64",
            url=(
                "https://github.com/containers/gvisor-tap-vsock/releases/download/"
                f"{GVISOR_GVPROXY_VERSION}/gvproxy-linux-arm64"
            ),
            digest="6ecca02839254c9a0cc184bba7aac63755a22d7ed10d455b852528a99d7f7d4b",
            digest_algo="sha256",
        ),
    },
}


def _default_pip_spawn(argv: Sequence[str]) -> subprocess.CompletedProcess:
    """Run an offline ``pip`` install in this interpreter; injectable so tests do ZERO pip."""
    return subprocess.run(  # noqa: S603 — fixed argv built from a pinned tool name + local dir
        list(argv), check=False, capture_output=True, text=True, timeout=300
    )


def _default_system_spawn(argv: Sequence[str]) -> subprocess.CompletedProcess:
    """Run a host install/version helper command; injectable so tests do ZERO sudo."""
    return subprocess.run(  # noqa: S603 — fixed argv from pinned artifacts and install paths
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


def _network_subprocess_timeout_seconds() -> float:
    raw = os.environ.get(NETWORK_SUBPROCESS_TIMEOUT_ENV)
    if raw is None or raw.strip() == "":
        return DEFAULT_NETWORK_SUBPROCESS_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError:
        raise ForgeConfigRefused(
            f"{NETWORK_SUBPROCESS_TIMEOUT_ENV} must be a positive number of seconds"
        ) from None
    if timeout <= 0:
        raise ForgeConfigRefused(f"{NETWORK_SUBPROCESS_TIMEOUT_ENV} must be a positive number of seconds")
    return timeout


def _network_timeout_detail(*, context: str, argv: Sequence[str], timeout: float | None) -> str:
    rendered = " ".join(str(part) for part in argv)
    suffix = f" after {timeout:g}s" if timeout else ""
    return (
        f"{context} timed out{suffix}: {rendered}. "
        "Check network connectivity, GitHub availability, and gh authentication."
    )


def _spawn_accepts_timeout(spawn: Any) -> bool:
    try:
        sig = inspect.signature(spawn)
    except (TypeError, ValueError):
        return True
    return "timeout" in sig.parameters or any(
        param.kind is inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values()
    )


def _network_spawn(spawn: Any, *, context: str):
    """Wrap a live/injected gh spawn with the CE network subprocess timeout."""

    def run(argv: Sequence[str], input_text: str | None, env: dict[str, str]) -> subprocess.CompletedProcess:
        argv_list = list(argv)
        timeout = _network_subprocess_timeout_seconds()
        try:
            if spawn is None:
                return subprocess.run(  # noqa: S603 — fixed gh argv assembled by CE forge callers
                    argv_list,
                    check=False,
                    capture_output=True,
                    text=True,
                    input=input_text,
                    env=env,
                    timeout=timeout,
                )
            if _spawn_accepts_timeout(spawn):
                return spawn(argv_list, input_text, env, timeout=timeout)
            return spawn(argv_list, input_text, env)
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                argv_list,
                124,
                stdout="",
                stderr=_network_timeout_detail(
                    context=context,
                    argv=argv_list,
                    timeout=exc.timeout or timeout,
                ),
            )

    return run


@dataclass(frozen=True)
class LiveForgeConfig:
    """Everything the live driver needs to mint + use + revoke its own forge-read token.

    ``signer`` is the host-side RS256 :data:`Signer` over the App PEM — the PEM content never
    enters the driver. It is REQUIRED for the local-signer mint path and OPTIONAL (``None``)
    when a ``token_minter`` is supplied — the mint broker (ce-ops#157) then holds the key and
    mints the scoped token server-side, so the user never needs a PEM. ``transport`` / ``spawn``
    / ``git_spawn`` are injectable network seams (live by default); tests inject fakes and
    perform ZERO live network / subprocess.
    """

    repo: str
    installation_id: int
    app_client_id: str
    #: RS256 signer over the App PEM. REQUIRED for the local-signer mint path; ``None`` is
    #: permitted ONLY when ``token_minter`` is set (the broker holds the key — ce-ops#157).
    signer: Signer | None
    #: 64-hex digest binding issuance to the verified install spec in force (its canonical sha).
    policy_sha: str
    run_id: str
    #: ce-ops#157 — when set, mint the scoped token THROUGH this seam (the shared-App broker)
    #: instead of the in-process local-signer path; the driver builds the same request either
    #: way. ``None`` → today's local-signer mint (``app_jwt_gh_runner`` → ``mint_scoped_token``).
    token_minter: TokenMinter | None = None
    transport: Any = None  # app-JWT HTTPS transport seam
    spawn: Any = None  # authenticated-gh subprocess seam
    git_spawn: Any = None  # workspace-clone subprocess seam
    #: Injectable mirror-fetch seam (url -> bytes) for the apply-time userspace-dep install;
    #: tests inject a fake → ZERO network. None → live HTTPS GET of CE's mirror.
    mirror_fetch: Any = None
    #: Injectable ``pip`` spawn seam (argv -> CompletedProcess); tests inject a fake → ZERO pip.
    pip_spawn: Any = None
    #: Injectable host-system spawn seam for pinned runtime binary install commands. Tests inject
    #: fakes; live defaults to ``subprocess.run`` and fails closed on any non-zero return.
    system_spawn: Any = None
    #: Override for the runtime binary install dir. None -> ``CE_FORGE_RUNTIME_BIN_DIR`` or
    #: ``/usr/local/bin``. Tests use this to avoid host mutation.
    runtime_bin_dir: str | None = None
    #: Override for the venv scripts dir the userspace-tool verify probes (ce-ops#90 verify-fix).
    #: None → the running interpreter's scripts dir (where ``pip install`` placed the console
    #: script); tests inject a temp dir holding a fake binary. NOT a PATH search.
    scripts_dir: str | None = None
    #: ce-ops#85 adoption-apply — injectable secrets-scrub seam ``(scan_root, scaffold) -> dict``
    #: returning per-scanner reports. CI injects a fake → ZERO scanner. None → the live default
    #: (sha256-pinned mirror-served Gitleaks + TruffleHog; fail-closed when unpinned).
    scrub_scan: Any = None
    #: Optional runtime-supplied Gitleaks + TruffleHog mirror pins. ``resolve_live_config`` reads
    #: them from host env; absent pins use the commissioned mirror defaults, while incomplete pins
    #: still fail closed before any unverified scanner binary can execute.
    brownfield_scanners: Mapping[str, BrownfieldScanner] | None = None

def _gh_get(runner: GhRunner, path: str) -> tuple[int, object, str]:
    """``gh api <path>`` through an authenticated runner; never raises. ``(code, json|None, stderr)``."""
    argv = ["gh", "api", path]
    try:
        proc = runner(argv, None)
    except subprocess.TimeoutExpired as exc:
        return 124, None, _network_timeout_detail(context="gh api", argv=argv, timeout=exc.timeout)
    out = (proc.stdout or "").strip()
    parsed: object = None
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return proc.returncode, parsed, proc.stderr or ""


def _app_jwt_get(config: LiveForgeConfig, path: str) -> tuple[int, object, str]:
    """GET a GitHub App endpoint with App-JWT auth through the injected HTTPS transport.

    Fail-closed on the broker path: when ``signer`` is ``None`` (ce-ops#157, the shared-App key
    lives only in the broker) this driver cannot author an App-JWT itself, so the App-level read
    returns an error tuple rather than raising — the caller treats it as an unavailable read.
    """
    if config.signer is None:
        return 1, None, "app-level read unavailable: no local signer (shared-App broker path)"
    jwt = build_app_jwt(config.app_client_id, signer=config.signer)
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Accept": _GITHUB_ACCEPT,
        "X-GitHub-Api-Version": _GITHUB_API_VERSION,
    }
    try:
        status, body = config.transport("GET", f"{_GITHUB_API_ROOT}/{path}", headers, None)
    except Exception as exc:  # noqa: BLE001 — fail closed; never expose bearer/JWT details.
        return 1, None, f"app installation read failed: {exc.__class__.__name__}"
    parsed: object = None
    text = (body or "").strip()
    if text:
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return (0 if 200 <= status < 300 else 1), parsed, "" if 200 <= status < 300 else text


def _protection_contexts(protection: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not isinstance(protection, Mapping):
        return ()
    checks = protection.get("required_status_checks") or {}
    contexts = checks.get("contexts") if isinstance(checks, Mapping) else None
    return tuple(str(c) for c in (contexts or ()))


def _ruleset_policy_for_branch(policy: BranchProtectionPolicy, *, branch: str) -> RulesetPolicy:
    return RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        branch=branch,
        required_status_check_contexts=policy.required_status_check_contexts,
        strict_required_status_checks_policy=policy.strict,
        required_approving_review_count=max(1, policy.required_approving_review_count),
        # Do NOT propagate the branch-protection ``dismiss_stale_reviews`` floor
        # into GitHub's blunt ruleset flag: it would wipe approvals on every push
        # including pure rebases (creator-engine#368). Re-review-on-content-change
        # is a CE-owned, diff-aware concern (forge.re_review / ce-ops#151), so the
        # ruleset leaves ``dismiss_stale_reviews_on_push`` at its diff-aware-safe
        # default (False). The classic-protection PUT still carries the floor flag.
        require_last_push_approval=policy.require_last_push_approval,
        required_review_thread_resolution=policy.required_conversation_resolution,
        bypass_actors=(),
    )


def _ruleset_required_contexts(ruleset: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not isinstance(ruleset, Mapping):
        return ()
    for rule in ruleset.get("rules") or []:
        if not isinstance(rule, Mapping) or rule.get("type") != "required_status_checks":
            continue
        params = rule.get("parameters") if isinstance(rule.get("parameters"), Mapping) else {}
        checks = params.get("required_status_checks") if isinstance(params, Mapping) else []
        return tuple(
            str(item.get("context"))
            for item in checks
            if isinstance(item, Mapping) and item.get("context")
        )
    return ()


def _merge_settings(parsed: Mapping[str, Any] | None) -> dict[str, bool]:
    parsed = parsed or {}
    return {
        "allow_squash_merge": bool(parsed.get("allow_squash_merge", False)),
        "allow_merge_commit": bool(parsed.get("allow_merge_commit", False)),
        "allow_rebase_merge": bool(parsed.get("allow_rebase_merge", False)),
    }


def _looks_like_branch_not_protected(parsed: object, stderr: str) -> bool:
    """True only for GitHub's branch-protection-absent signal, not generic API failure."""
    message = ""
    if isinstance(parsed, Mapping):
        message = str(parsed.get("message") or "")
    text = f"{message}\n{stderr or ''}".lower()
    return "branch not protected" in text


def _rulesets_from_payload(parsed: object) -> list[dict[str, Any]]:
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, Mapping):
        for key in ("rulesets", "items"):
            value = parsed.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _find_ce_ruleset(
    runner: GhRunner, repo: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    code, parsed, stderr = _gh_get(runner, f"repos/{repo}/rulesets")
    if code != 0:
        if code == 124:
            return None, {
                "ok": False,
                "reason": "protection_read_failed",
                "surface": "rulesets",
                "detail": stderr,
            }
        if protection_floor_unenforceable(parsed, stderr):
            return None, protection_floor_unenforceable_diagnostic(
                surface="rulesets", parsed=parsed, stderr=stderr
            )
        result = {"ok": False, "reason": "protection_read_failed", "surface": "rulesets"}
        if stderr:
            result["detail"] = stderr
        return None, result
    for ruleset in _rulesets_from_payload(parsed):
        if ruleset.get("name") == CE_PROTECTION_RULESET_NAME:
            return ruleset, None
    return None, None


def _combined_floor_unenforceable(
    classic: Mapping[str, Any] | None, rulesets: Mapping[str, Any]
) -> dict[str, Any]:
    messages = [
        str(diag.get("message") or "").strip()
        for diag in (classic, rulesets)
        if isinstance(diag, Mapping) and str(diag.get("message") or "").strip()
    ]
    return {
        "ok": False,
        "code": PROTECTION_FLOOR_UNENFORCEABLE_CODE,
        "reason": PROTECTION_FLOOR_UNENFORCEABLE_CODE,
        "surface": "classic_and_rulesets" if classic else "rulesets",
        "message": "; ".join(messages),
        "remediation": rulesets.get("remediation"),
        "classic": dict(classic) if isinstance(classic, Mapping) else None,
        "rulesets": dict(rulesets),
    }


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


def _host_machine() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    if machine in {"aarch64", "arm64"}:
        return "aarch64"
    return machine


def _digest_bytes(data: bytes, algo: str) -> str:
    if algo == "sha256":
        return hashlib.sha256(data).hexdigest()
    if algo == "sha512":
        return hashlib.sha512(data).hexdigest()
    raise ValueError(f"unsupported digest algorithm: {algo}")


def _pinned_system_tool(name: str, *, machine: str | None = None) -> PinnedSystemTool | None:
    pins = PINNED_SYSTEM_TOOLS.get(name)
    if not pins:
        return None
    return pins.get(machine or _host_machine())


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
            platform=_host_scanner_platform() or "",
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
    """Classify the bootstrap PAT by prefix (ce-ops#94).

    Grounded in GitHub's documented PAT prefixes: ``github_pat_`` = fine-grained PAT (emits
    NO ``X-OAuth-Scopes`` and exposes no permission introspection); ``ghp_`` = classic PAT.
    Unknown prefixes refuse fail-closed even if a response happens to carry classic-scope headers.
    """
    t = (token or "").strip()
    if t.startswith("github_pat_"):
        return "fine_grained"
    if t.startswith("ghp_"):
        return "classic"
    return "unknown"


def _app_installation_zero_repos_error(*, installation_id: int, repo: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": "app_installation_zero_accessible_repos",
        "installation_id": installation_id,
        "repo": repo,
        "message": (
            f"GitHub App installation {installation_id} reports zero accessible repositories; "
            f"it cannot cover target repo {repo}."
        ),
        "action": (
            "install or reconfigure the GitHub App installation so it has access to "
            f"{repo}. If repo_selection=all is enabled on an account with no target repo, "
            "install the App on the account that owns the target repo or select the target "
            "repo explicitly."
        ),
    }


def _forge_noreply_email(login: str) -> str:
    return f"{login}@users.noreply.github.com"


def _resolved_forge_identity(login: Any) -> dict[str, str]:
    """Resolve the local git author identity from the bootstrap token's ``GET /user`` login.

    Empty/invalid input refuses; callers must never fall back to ambient git or ``gh`` config
    because that can bind a dev install to a shared controller identity.
    """
    resolved_login = str(login or "").strip()
    if not resolved_login or any(ch.isspace() for ch in resolved_login):
        raise onboard_apply.ApplyRefused(
            "forge_identity_unresolved",
            "forge actor identity is unresolved; refusing ambient git author fallback",
        )
    resolved_email = _forge_noreply_email(resolved_login)
    return {
        "login": resolved_login,
        "name": resolved_login,
        "email": resolved_email,
        "source": "bootstrap_token_get_user",
    }


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
        self._bootstrap_forge_identity: dict[str, str] | None = None

    # -- credential lifecycle (mint -> use -> revoke) ----------------------------------------
    def _mint(self, request: TokenRequest) -> ScopedToken:
        """Mint a scoped token via the ``token_minter`` seam (broker) or the local-signer path.

        ce-ops#157: when ``LiveForgeConfig.token_minter`` is set, the standing shared-App mint
        broker mints server-side (the App key never enters this process — the user needs no
        PEM); the driver still builds the request, so the least-privilege ceiling is identical.
        Otherwise the in-process local-signer path is used UNCHANGED
        (``app_jwt_gh_runner`` → ``mint_scoped_token``), which requires a ``signer``.
        """
        if self._cfg.token_minter is not None:
            return self._cfg.token_minter(request)
        if self._cfg.signer is None:
            raise ForgeConfigRefused(
                "LiveForgeConfig.signer is required for the local mint path "
                "(set a token_minter to mint via the shared-App broker instead)"
            )
        mint_runner = app_jwt_gh_runner(
            self._cfg.app_client_id,
            signer=self._cfg.signer,
            transport=self._cfg.transport,
        )
        return mint_scoped_token(request, gh_runner=mint_runner)

    def _reader(self) -> GhRunner:
        """Lazily mint the Phase-1 read token and return the authenticated ``GhRunner`` (cached)."""
        if self._read_runner is None:
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
            self._token = self._mint(request)
            self._read_runner = authenticated_gh_runner(
                self._token,
                spawn=_network_spawn(self._cfg.spawn, context="forge read gh api"),
            )
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
            code, parsed, stderr = _gh_get(self._reader(), f"repos/{repo}")
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "repo_read_failed"}
        if code != 0 or not isinstance(parsed, dict):
            result = {"ok": False, "reason": "repo_read_failed"}
            if stderr:
                result["detail"] = stderr
            return result
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

    def read_workflow(self, *, repo: str, branch: str, path: str) -> dict[str, Any]:
        """GET workflow contents from GitHub and return decoded bytes plus blob metadata."""
        try:
            code, parsed, stderr = _gh_get(self._reader(), f"repos/{repo}/contents/{path}?ref={branch}")
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "workflow_read_failed"}
        if code == 124:
            return {"ok": False, "reason": "workflow_read_failed", "detail": stderr}
        if code != 0 or not isinstance(parsed, dict) or "content" not in parsed:
            return {"ok": False, "reason": "workflow_absent"}
        try:
            raw = base64.b64decode(parsed["content"])  # GitHub returns base64 (newline-wrapped)
        except (ValueError, TypeError):
            return {"ok": False, "reason": "workflow_decode_failed"}
        return {
            "ok": True,
            "content": raw,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "blob_sha": str(parsed.get("sha") or ""),
            "path": str(parsed.get("path") or path),
        }

    def verify_workflow(self, *, repo: str, branch: str, path: str, digest: str) -> dict[str, Any]:
        """GET the workflow contents and pin the EXACT byte digest (OQ-C, fail-closed).

        A present-but-byte-drifted workflow returns a DISTINCT ``workflow_digest_mismatch`` reason
        (so a joining dev learns *why* detection failed) — never a blanket brownfield refuse.
        """
        current = self.read_workflow(repo=repo, branch=branch, path=path)
        if not current.get("ok"):
            return {k: v for k, v in current.items() if k != "content"}
        actual = str(current.get("sha256") or "")
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
        classic_diag: dict[str, Any] | None = None
        try:
            code, parsed, stderr = _gh_get(
                self._reader(), f"repos/{repo}/branches/{branch}/protection"
            )
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "protection_read_failed"}
        if code == 0 and isinstance(parsed, dict):
            live = set(_protection_contexts(parsed))
            floor = set(policy.required_status_check_contexts)
            # The floor's required checks must ALL be present (a repo with MORE checks still
            # satisfies the floor); a missing CE check fails detection → brownfield defer upstream.
            return {"ok": floor.issubset(live), "contexts": sorted(live), "source": "classic"}
        if protection_floor_unenforceable(parsed, stderr):
            classic_diag = protection_floor_unenforceable_diagnostic(
                surface="classic", parsed=parsed, stderr=stderr
            )
        ruleset, ruleset_diag = _find_ce_ruleset(self._reader(), repo)
        if ruleset_diag:
            if ruleset_diag.get("reason") == PROTECTION_FLOOR_UNENFORCEABLE_CODE:
                return _combined_floor_unenforceable(classic_diag, ruleset_diag)
            return ruleset_diag
        ruleset_policy = _ruleset_policy_for_branch(policy, branch=branch)
        live = set(_ruleset_required_contexts(ruleset))
        floor = set(policy.required_status_check_contexts)
        return {
            "ok": ruleset_satisfies_policy(ruleset, ruleset_policy) and floor.issubset(live),
            "contexts": sorted(live),
            "source": "ruleset",
            "classic_unavailable": classic_diag is not None,
        }

    def existing_branch_protection_contexts(
        self, *, repo: str, branch: str
    ) -> tuple[str, ...]:
        try:
            code, parsed, _ = _gh_get(
                self._reader(), f"repos/{repo}/branches/{branch}/protection"
            )
        except Exception:  # noqa: BLE001 — fail-closed: report no live contexts known
            return ()
        if code == 0 and isinstance(parsed, dict):
            return _protection_contexts(parsed)
        with contextlib.suppress(Exception):
            ruleset, ruleset_diag = _find_ce_ruleset(self._reader(), repo)
            if ruleset_diag:
                return ()
            return _ruleset_required_contexts(ruleset)
        return ()

    def verify_merge_settings(self, *, repo: str, squash_only: bool) -> dict[str, Any]:
        try:
            code, parsed, _ = _gh_get(self._reader(), f"repos/{repo}")
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "repo_merge_settings_read_failed"}
        if code != 0 or not isinstance(parsed, Mapping):
            return {"ok": False, "reason": "repo_merge_settings_read_failed"}
        observed = _merge_settings(parsed)
        desired = {
            "allow_squash_merge": bool(squash_only),
            "allow_merge_commit": not bool(squash_only),
            "allow_rebase_merge": not bool(squash_only),
        }
        return {"ok": observed == desired, "settings": observed}

    def probe_bootstrap_token(
        self, *, token: str, repo: str, org_create_needed: bool
    ) -> dict[str, Any]:
        """Validity probe of the human BOOTSTRAP PAT (``GET /user``) — distinct auth from the App.

        Authenticates AS the bootstrap token (value in the child ``GH_TOKEN`` env only, never argv)
        and reports its login + ``token_type`` (ce-ops#94). For a CLASSIC token it also reports the
        CE bootstrap permissions implied by its ``X-OAuth-Scopes``. A FINE-GRAINED PAT emits no
        ``X-OAuth-Scopes`` and exposes no non-mutating permission introspection, so the probe is
        identity-only and greenfield write legs remain the fail-closed capability check.
        """
        self._bootstrap_forge_identity = None
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
            runner = authenticated_gh_runner(
                holder,
                spawn=_network_spawn(self._cfg.spawn, context="bootstrap gh api user"),
            )
            proc = runner(["gh", "api", "-i", "user"], None)
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "reason": "bootstrap_probe_failed",
                "detail": _network_timeout_detail(
                    context="bootstrap gh api user",
                    argv=["gh", "api", "-i", "user"],
                    timeout=exc.timeout,
                ),
            }
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "bootstrap_probe_failed"}
        if proc.returncode != 0:
            detail = (proc.stderr or "").strip()
            result = {"ok": False, "reason": "bootstrap_probe_failed"}
            if detail:
                result["detail"] = detail
            return result
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
        if token_type in {"classic", "fine_grained"}:
            self._bootstrap_forge_identity = _resolved_forge_identity(login)
        result: dict[str, Any] = {"ok": True, "login": login, "token_type": token_type}
        if token_type == "classic":
            # Only classic PATs expose capability via X-OAuth-Scopes (ce-ops#94). Fine-grained
            # PATs emit none, so classic scopes are never fabricated for them.
            result["scopes"] = _bootstrap_scopes_from_oauth(
                _parse_oauth_scopes_header(raw), org_create_needed=org_create_needed
            )
        return result

    def verify_app_installation(
        self, *, installation_id: int, repo: str, bot_identity: str
    ) -> dict[str, Any]:
        """Phase-1 read-only App-installation COVERAGE GET (ce-ops#88/#126).

        Confirms the ALREADY-installed App covers ``repo`` — NO install click, NO mutation.
        The primary check is scoped to the configured target repo via App-JWT auth, before
        any installation token is minted. If the target lookup fails, a bounded installation
        repository-count read distinguishes "zero accessible repositories" from a normal
        not-covered result so the operator gets an actionable remediation.
        The install *click* / greenfield ``wait_for_app_installation`` stay Phase-2 (inherited).
        """
        coverage = self._installation_repo_coverage(repo, installation_id=installation_id)
        if not coverage.get("ok"):
            result = dict(coverage)
            result.setdefault("installation_id", installation_id)
            return result
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
        userspace tool's wheel is fetched from CE's own versioned mirror (``docs/downloads/<version>/``,
        NOT astral.sh / a live index), its bytes sha256-verified against the in-code pin
        (``MIRROR_USERSPACE_WHEELS``, bound to the SIGNED ``required_wheels`` entry) BEFORE
        install, then installed OFFLINE via ``pip install --no-index --find-links <dir> <tool>``;
        ``verify_tool`` must pass after. A pre-seeded ``CE_FORGE_WHEELHOUSE`` dir is honored as an
        offline FALLBACK (no fetch) when it already holds the pinned wheel. ``sudo_tools`` keep
        the base refusal (a §7 governed seat has no host package installer); the concrete
        ``runsc``/``gvproxy`` runtime binaries are installed by ``provision_runtime``. Fail CLOSED
        on every fetch / hash-mismatch / install / verify failure; the staged temp dir is always
        cleaned.
        """
        if not tools:
            return {"ok": True, "installed": []}
        if sudo_tools:
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
        coverage = self._installation_repo_coverage(repo)
        if not coverage.get("ok"):
            result = dict(coverage)
            result["installation_id"] = installation_id
            return result
        return {"ok": True, "installation_id": installation_id, "detected": True}

    def provision_runtime(
        self,
        *,
        state_root: Path,
        workspace_root: Path,
        provider: str | None,
        backend: str = v3_installer.DEFAULT_ISOLATION_BACKEND,
    ) -> dict[str, Any]:
        """Provision the runtime posture and, for gVisor, the concrete pinned host binaries."""
        runtime_tools: dict[str, str] = {}
        if backend == "gvisor-proxy":
            ensured = self._ensure_pinned_system_tools(GVISOR_RUNTIME_TOOLS)
            if not ensured.get("ok"):
                return ensured
            runtime_tools = dict(ensured.get("runtime_tools") or {})
        result = super().provision_runtime(
            state_root=state_root,
            workspace_root=workspace_root,
            provider=provider,
            backend=backend,
        )
        if runtime_tools:
            result = dict(result)
            result["runtime_tools"] = runtime_tools
        return result

    def verify_tool(self, name: str) -> bool:
        """Verify a dep is installed — BRANCHED by tool class (ce-ops#90 verify-fix, dev-3).

        A userspace tool (``uv``) installs into the venv SCRIPTS dir, which is NOT on
        ``os.environ['PATH']``; the inherited base ``verify_tool`` → ``probe_tool`` →
        ``shutil.which`` therefore returned ``None`` and the leg refused
        ``userspace_tool_verify_failed`` even though the install succeeded (the #244 defect dev-3
        hit on a live ``--apply``). For a userspace tool we probe the ACTUAL install location
        (the absolute ``<scripts>/<tool>``) and run its ``--version`` there — NOT a PATH search.
        The gVisor runtime tools (``runsc``/``gvproxy``) are also version-pinned and verified by
        running their version command. Other system tools (``git``/``python``) keep the inherited
        base PATH probe. Fail-closed (missing / non-runnable / wrong version → ``False``), so a
        broken install still refuses.
        """
        if name in MIRROR_USERSPACE_WHEELS:
            return self._verify_userspace_tool(name)
        pin = _pinned_system_tool(name)
        if pin is not None:
            return self._verify_pinned_system_tool(pin)
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

    def _ensure_pinned_system_tools(self, tools: Sequence[str]) -> dict[str, Any]:
        """Ensure every requested pinned host binary is installed at the expected version."""
        installed: list[str] = []
        versions: dict[str, str] = {}
        for tool in tools:
            pin = _pinned_system_tool(tool)
            if pin is None:
                return {
                    "ok": False,
                    "reason": "no_pinned_system_tool",
                    "tool": tool,
                    "machine": _host_machine(),
                    "manual_rollback_required": True,
                }
            if not self.verify_tool(pin.tool):
                result = self._install_pinned_system_tool(pin)
                if not result.get("ok"):
                    return result
                if not self.verify_tool(pin.tool):
                    return {
                        "ok": False,
                        "reason": "system_tool_verify_failed",
                        "tool": pin.tool,
                        "expected_version": pin.version,
                        "manual_rollback_required": True,
                    }
                installed.append(pin.tool)
            versions[pin.tool] = pin.version
        return {"ok": True, "installed": installed, "runtime_tools": versions}

    def _verify_pinned_system_tool(self, pin: PinnedSystemTool) -> bool:
        output = self._pinned_system_tool_version_output(pin)
        return bool(output and pin.version in output)

    def _pinned_system_tool_version_output(self, pin: PinnedSystemTool) -> str | None:
        candidates: list[Path] = []
        resolved = shutil.which(pin.tool)
        if resolved:
            candidates.append(Path(resolved))
        candidates.append(self._runtime_bin_dir() / pin.tool)
        seen: set[str] = set()
        first_output: str | None = None
        for candidate in candidates:
            key = str(candidate)
            if key in seen:
                continue
            seen.add(key)
            if not candidate.is_file():
                continue
            try:
                proc = subprocess.run(  # noqa: S603 — candidate is a resolved local binary path
                    [str(candidate), *pin.version_args],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except Exception:  # noqa: BLE001 — not runnable means not verified
                continue
            if proc.returncode == 0:
                output = (proc.stdout or "") + (proc.stderr or "")
                if pin.version in output:
                    return output
                first_output = first_output or output
        return first_output

    def _install_pinned_system_tool(self, pin: PinnedSystemTool) -> dict[str, Any]:
        tmpdir = Path(tempfile.mkdtemp(prefix="ce-runtime-tool-"))
        staged = tmpdir / pin.filename
        try:
            try:
                data = self._mirror_fetch(pin.url)
            except Exception:  # noqa: BLE001
                return {"ok": False, "reason": "system_tool_fetch_failed", "tool": pin.tool, "url": pin.url}
            actual = _digest_bytes(data, pin.digest_algo)
            if actual != pin.digest:
                return {
                    "ok": False,
                    "reason": "system_tool_digest_mismatch",
                    "tool": pin.tool,
                    "algo": pin.digest_algo,
                    "expected": pin.digest,
                    "actual": actual,
                }
            staged.write_bytes(data)
            staged.chmod(0o755)
            dest_dir = self._runtime_bin_dir()
            dest = dest_dir / pin.tool
            if self._copy_system_tool_without_sudo(staged, dest):
                return {"ok": True, "tool": pin.tool, "version": pin.version, "path": str(dest)}
            proc = self._system_spawn(["sudo", "install", "-m", "0755", str(staged), str(dest)])
            if getattr(proc, "returncode", 1) != 0:
                return {
                    "ok": False,
                    "reason": "system_tool_install_failed",
                    "tool": pin.tool,
                    "path": str(dest),
                    "manual_rollback_required": True,
                }
            return {"ok": True, "tool": pin.tool, "version": pin.version, "path": str(dest)}
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _copy_system_tool_without_sudo(self, staged: Path, dest: Path) -> bool:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not os.access(dest.parent, os.W_OK):
                return False
            shutil.copy2(staged, dest)
            dest.chmod(0o755)
            return True
        except OSError:
            return False

    def _runtime_bin_dir(self) -> Path:
        override = self._cfg.runtime_bin_dir or os.environ.get(ENV_RUNTIME_BIN_DIR)
        return Path(override or "/usr/local/bin")

    def _system_spawn(self, argv: Sequence[str]) -> subprocess.CompletedProcess:
        spawn = self._cfg.system_spawn or _default_system_spawn
        try:
            return spawn(argv)
        except Exception:  # noqa: BLE001 — fail-closed; caller maps non-zero to refusal
            return subprocess.CompletedProcess(list(argv), 1)

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
        return bool(self._installation_repo_coverage(repo).get("ok"))

    def _installation_repo_coverage(
        self, repo: str, *, installation_id: int | None = None
    ) -> dict[str, Any]:
        """Confirm the configured installation is attached to the target repo."""
        expected_installation_id = installation_id or self._cfg.installation_id
        code, parsed, _ = _app_jwt_get(self._cfg, f"repos/{repo}/installation")
        if code == 0 and isinstance(parsed, Mapping):
            target_installation_id = parsed.get("id")
            if int(target_installation_id or 0) == int(expected_installation_id):
                return {"ok": True, "covered": True, "installation_id": expected_installation_id}
            return {
                "ok": False,
                "reason": "app_installation_repo_not_covered",
                "installation_id": expected_installation_id,
                "repo": repo,
                "target_installation_id": target_installation_id,
            }

        count_code, count_parsed, _ = _app_jwt_get(
            self._cfg,
            f"app/installations/{expected_installation_id}/repositories?per_page=1",
        )
        if count_code != 0 or not isinstance(count_parsed, Mapping):
            return {"ok": False, "reason": "app_installation_read_failed", "repo": repo}
        repos = count_parsed.get("repositories") or []
        if not repos and count_parsed.get("total_count") == 0:
            return _app_installation_zero_repos_error(
                installation_id=expected_installation_id,
                repo=repo,
            )
        if any(isinstance(r, Mapping) and r.get("full_name") == repo for r in repos):
            return {"ok": True, "covered": True, "installation_id": expected_installation_id}
        return {
            "ok": False,
            "reason": "app_installation_repo_not_covered",
            "installation_id": expected_installation_id,
            "repo": repo,
        }

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
        classic_diag: dict[str, Any] | None = None
        try:
            code, parsed, stderr = _gh_get(
                self._reader(), f"repos/{repo}/branches/{branch}/protection"
            )
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "protection_read_failed_no_write"}
        source = "classic"
        if code == 0 and isinstance(parsed, dict):
            live = set(_protection_contexts(parsed))
        else:
            if protection_floor_unenforceable(parsed, stderr):
                classic_diag = protection_floor_unenforceable_diagnostic(
                    surface="classic", parsed=parsed, stderr=stderr
                )
            ruleset, ruleset_diag = _find_ce_ruleset(self._reader(), repo)
            if ruleset_diag:
                if ruleset_diag.get("reason") == PROTECTION_FLOOR_UNENFORCEABLE_CODE:
                    return _combined_floor_unenforceable(classic_diag, ruleset_diag)
                return {"ok": False, "reason": "protection_read_failed_no_write", **ruleset_diag}
            ruleset_policy = _ruleset_policy_for_branch(policy, branch=branch)
            if not ruleset_satisfies_policy(ruleset, ruleset_policy):
                return {"ok": False, "reason": "branch_protection_ruleset_missing_no_write"}
            live = set(_ruleset_required_contexts(ruleset))
            source = "ruleset"
        would_add = set(policy.required_status_check_contexts) - live
        if would_add:
            # A real protection mutation would be required → defer, do NOT write.
            return {
                "ok": False,
                "reason": "branch_protection_mutation_deferred",
                "would_add": sorted(would_add),
            }
        return {
            "ok": True,
            "already": True,
            "mutated": False,
            "contexts": sorted(live),
            "source": source,
            "classic_unavailable": classic_diag is not None,
        }

    def configure_merge_settings(self, *, repo: str, squash_only: bool, token: str) -> dict[str, Any]:
        """VERIFY-FIRST, defer-not-mutate for Phase 1 repo merge settings."""
        result = self.verify_merge_settings(repo=repo, squash_only=squash_only)
        if result.get("ok"):
            return {"ok": True, "already": True, "mutated": False, **result}
        return {
            "ok": False,
            "reason": "merge_settings_mutation_deferred",
            "desired_squash_only": squash_only,
            **result,
        }

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
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "reason": "checkout_failed",
                "detail": _network_timeout_detail(
                    context="gh repo clone",
                    argv=["gh", "repo", "clone", repo, str(repo_dir), "--", "--branch", branch, "--depth", "1"],
                    timeout=exc.timeout,
                ),
            }
        except Exception:  # noqa: BLE001
            return {"ok": False, "reason": "checkout_failed"}
        if proc.returncode != 0:
            detail = (proc.stderr or "").strip()
            result = {"ok": False, "reason": "checkout_failed"}
            if detail:
                result["detail"] = detail
            return result
        return {"ok": True, "path": str(repo_dir), "created": True}

    def _clone_runner(self) -> GhRunner:
        """Authenticated runner for the clone (uses ``git_spawn`` if injected, else the read spawn)."""
        self._reader()  # ensure the read token is minted
        assert self._token is not None
        spawn = self._cfg.git_spawn if self._cfg.git_spawn is not None else self._cfg.spawn
        return authenticated_gh_runner(
            self._token,
            spawn=_network_spawn(spawn, context="gh repo clone"),
        )

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
    affirmative fail-closed authority. The live default selects only commissioned Linux scanner
    pins and fail-closes on unsupported platforms or incomplete runtime overrides.

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
            # minter raises TokenMintRefused BEFORE any forge call (defence-in-depth, §6.3). The
            # broker path (ce-ops#157) mints the write token server-side at the SAME ceiling.
            self._write_token = self._mint(request)
            self._write_runner = authenticated_gh_runner(
                self._write_token,
                spawn=_network_spawn(self._cfg.spawn, context="adoption write gh api"),
            )
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

    def refresh_workflow(
        self,
        *,
        repo: str,
        branch: str,
        path: str,
        content: str,
        current_sha: str | None = None,
    ) -> dict[str, Any]:
        """Replace exactly one workflow file through GitHub's contents API."""
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        argv = [
            "gh",
            "api",
            "-X",
            "PUT",
            f"repos/{repo}/contents/{path}",
            "-f",
            "message=ce: refresh CE validation workflow",
            "-f",
            f"content={encoded}",
            "-f",
            f"branch={branch}",
        ]
        if current_sha:
            argv.extend(["-f", f"sha={current_sha}"])
        runner = self._writer()
        try:
            proc = runner(argv, None)
        finally:
            self._revoke_write()
        if proc.returncode != 0:
            return {"ok": False, "reason": "workflow_refresh_write_failed", "detail": (proc.stderr or "").strip()}
        parsed: object = None
        if (proc.stdout or "").strip():
            with contextlib.suppress(json.JSONDecodeError, ValueError):
                parsed = json.loads(proc.stdout or "")
        commit_sha = ""
        if isinstance(parsed, Mapping):
            commit = parsed.get("commit")
            if isinstance(commit, Mapping):
                commit_sha = str(commit.get("sha") or "")
        return {"ok": True, "path": path, "commit_sha": commit_sha}

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
        """Live scrub: per-scanner sha-pinned run; fail-closed (``ran=False``) when unpinned.

        Each scanner's report is ``{ran, exit_code, findings, error}``. With an EMPTY pin (an
        unsupported host platform or incomplete runtime override) the report is ``ran=False`` so
        the leg refuses ``brownfield_secret_scanner_unavailable`` — NO unverified binary is ever
        executed and absence is never read as clean.

        When scanner pins are supplied, scan a temporary materialized tree containing BOTH the
        pre-existing project bytes and every scaffold artifact leg 3 would commit, matching the
        plan-side ``scan_paths`` contract: ``[".", *scaffold_paths]``.
        """
        reports: dict[str, Any] = {}
        scanner_pins = (
            self._cfg.brownfield_scanners
            if self._cfg.brownfield_scanners is not None
            else BROWNFIELD_SCANNERS
        )
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

        Reuses the wheel-staging anti-tamper pattern: fetch ``pin.url``, verify the artifact
        bytes against ``pin.sha256`` BEFORE extracting/making any binary executable, then run the
        tool over ``scan_root``. Returns ``{ran, exit_code, findings, error}`` — fail-closed on
        any fetch/hash/extract/spawn error.
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
            try:
                binary_bytes = _scanner_binary_bytes(pin, data)
            except ValueError as exc:
                return {
                    "ran": False,
                    "exit_code": None,
                    "findings": [],
                    "error": f"{pin.tool}: extract failed: {exc}",
                }
            binary = staged_dir / pin.tool
            binary.write_bytes(binary_bytes)
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
        identity = self._bootstrap_forge_identity
        if identity is None:
            raise onboard_apply.ApplyRefused(
                "forge_identity_unresolved",
                "forge actor identity was not resolved from bootstrap token GET /user; refusing ambient git author fallback",
            )
        self._bind_git_commit_identity(repo_dir, identity)
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
        self._verify_git_commit_identity(repo_dir, identity)
        return {
            "ok": True,
            "source_dir": str(repo_dir),
            "head_sha": (head.stdout or "").strip(),
            "scaffold_paths": written,
            "workflow_sha256": workflow_sha,
            "already": already,
            "forge_identity": identity,
        }

    def _bind_git_commit_identity(self, repo_dir: Path, identity: Mapping[str, str]) -> None:
        """Bind local git author config to install-time identity and verify no ambient fallback."""
        expected = {
            "user.name": identity["name"],
            "user.email": identity["email"],
            "user.useConfigOnly": "true",
        }
        for key, value in expected.items():
            proc = self._git(["config", "--local", key, value], cwd=repo_dir)
            if proc.returncode != 0:
                raise onboard_apply.ApplyFailed(
                    "brownfield_scaffold_identity_failed",
                    f"failed to bind local git identity {key}",
                )
        for key, value in expected.items():
            proc = self._git(["config", "--local", "--get", key], cwd=repo_dir)
            actual = (proc.stdout or "").strip()
            if proc.returncode != 0 or actual != value:
                raise onboard_apply.ApplyFailed(
                    "brownfield_scaffold_identity_failed",
                    f"local git identity {key} resolved to {actual!r}, expected {value!r}",
                )

    def _verify_git_commit_identity(self, repo_dir: Path, identity: Mapping[str, str]) -> None:
        proc = self._git(["log", "-1", "--format=%an%x00%ae", "HEAD"], cwd=repo_dir)
        if proc.returncode != 0:
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_identity_failed",
                "cannot verify adoption commit author identity",
            )
        raw = proc.stdout or ""
        if "\0" not in raw:
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_identity_failed",
                "adoption commit author identity was not parseable",
            )
        name, email = raw.rstrip("\n").split("\0", 1)
        if name != identity["name"] or email != identity["email"]:
            raise onboard_apply.ApplyFailed(
                "brownfield_scaffold_identity_failed",
                "adoption commit author identity did not match install-time forge identity",
            )

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
        self,
        *,
        repo: str,
        base: str,
        expected_checks: Sequence[str],
        declared_protections: str | None = None,
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
            if protection_floor_unenforceable(parsed, stderr):
                if declared_protections == "reference":
                    return {
                        "ok": True,
                        "existing_checks": [],
                        "expected_checks": list(expected_checks),
                        "dropped": [],
                        "protection_floor": "documented-not-enforced",
                        "repo": repo,
                        "branch": base,
                        "declared_protections": declared_protections,
                    }
                diagnostic = protection_floor_unenforceable_diagnostic(
                    surface="classic", parsed=parsed, stderr=stderr
                )
                raise onboard_apply.ApplyRefused(
                    PROTECTION_FLOOR_UNENFORCEABLE_CODE,
                    onboard_apply.protection_floor_unenforceable_detail(
                        repo=repo, branch=base, diagnostic=diagnostic
                    ),
                )
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


def _scanner_binary_bytes(pin: BrownfieldScanner, payload: bytes) -> bytes:
    """Return executable scanner bytes from a pinned payload.

    Env overrides may still point at raw binaries. The built-in #159 defaults point at upstream
    ``.tar.gz`` release archives; for those, read exactly one regular file named by
    ``archive_member``/``tool`` without extracting archive paths to disk.
    """

    if not (pin.archive_member or pin.url.endswith((".tar.gz", ".tgz"))):
        return payload

    target = pin.archive_member or pin.tool
    matches: list[tarfile.TarInfo] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tf:
            for member in tf.getmembers():
                member_path = PurePosixPath(member.name)
                if member_path.is_absolute() or ".." in member_path.parts:
                    continue
                if member.isfile() and member_path.name == target:
                    matches.append(member)
            if len(matches) != 1:
                raise ValueError(
                    f"expected exactly one regular archive member named {target!r}, found {len(matches)}"
                )
            extracted = tf.extractfile(matches[0])
            if extracted is None:
                raise ValueError(f"archive member {matches[0].name!r} could not be read")
            return extracted.read()
    except tarfile.TarError as exc:
        raise ValueError(f"invalid tar.gz payload: {exc}") from exc


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


def _post_mint_broker(url: str, payload: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover - live HTTPS
    """POST a mint request to the broker's ``/v1/token`` and return the parsed JSON response.

    The lone live network shell for the broker mint path; tests monkeypatch this. Never logs the
    request/response bodies (they carry credentials).
    """
    import urllib.error
    import urllib.request

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:  # noqa: S310 — fixed https broker URL
            body = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        status = exc.code
    try:
        parsed = json.loads(body) if body else {}
    except (json.JSONDecodeError, ValueError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    parsed.setdefault("status", status)
    return parsed


def broker_minter(
    broker_url: str, *, caller_user_token: str = ""
) -> "TokenMinter":
    """Return a :data:`TokenMinter` that mints THROUGH the standing shared-App broker (ce-ops#157).

    The returned closure maps a :class:`TokenRequest` to the broker's ``POST /v1/token`` call and
    wraps the response token in a :class:`ScopedToken`. The shared-App private key never enters
    this process — the broker holds it. A non-200 broker response (binding/ceiling/transport
    refusal) raises :class:`ForgeConfigError` so the driver fails closed exactly as a local mint
    refusal would. The user's ``ghu_`` token rides in the request body the broker uses for its
    binding check and never appears in a log or exception here.
    """
    endpoint = broker_url.rstrip("/") + "/v1/token"

    def mint(request: TokenRequest) -> ScopedToken:
        payload = {
            "installation_id": request.installation_id,
            "repo": request.repo,
            "permissions": dict(request.permissions),
            "caller_user_token": caller_user_token,
        }
        resp = _post_mint_broker(endpoint, payload)
        if int(resp.get("status") or 0) != 200 or not resp.get("token"):
            raise ForgeConfigError(
                f"mint broker refused the request for {request.repo} "
                f"(status {resp.get('status')}, reason {resp.get('reason')!r})"
            )
        perms = tuple(
            (str(p[0]), str(p[1])) for p in (resp.get("permissions") or ()) if len(p) == 2
        ) or tuple(sorted((str(k), str(v)) for k, v in request.permissions.items()))
        expires_at = str(resp.get("expires_at") or "")
        return ScopedToken(
            run_id=request.run_id,
            repo=request.repo,
            policy_sha=request.policy_sha,
            secret_name=request.secret_name,
            permissions=perms,
            expires_at=expires_at,
            token_ref=f"{request.repo}@broker@{expires_at}",
            value=str(resp["token"]),
        )

    return mint


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

    # ce-ops#157 — shared-App mint-broker branch. On a ``github.app.kind: shared`` run with a
    # broker URL configured, mint via the standing broker (the user needs NO App PEM); the
    # signer is None and a ``broker_minter`` closure becomes the driver's token_minter. Requires
    # a resolvable installation id + client id; missing broker URL or install → fall through /
    # fail-closed. ``kind: own`` NEVER takes this path (it always uses its local PEM signer).
    kind = str(merged.value("github.app.kind", "shared") or "shared")
    broker_url = env.get(ENV_MINT_BROKER_URL)
    if kind == "shared" and broker_url:
        if not (installation_raw and client_id):
            return None
        try:
            installation_id = int(installation_raw)
        except (TypeError, ValueError):
            return None
        if installation_id <= 0:
            return None
        return LiveForgeConfig(
            repo=repo,
            installation_id=installation_id,
            app_client_id=str(client_id),
            signer=None,  # the broker holds the key — no PEM on the user's disk
            policy_sha=policy_sha,
            run_id=f"onboard-live-forge:{repo}",
            token_minter=broker_minter(
                broker_url, caller_user_token=env.get(ENV_MINT_BROKER_USER_TOKEN, "")
            ),
            brownfield_scanners=_scanner_pins_from_env(env),
        )

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
