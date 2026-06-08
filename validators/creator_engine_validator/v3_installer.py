"""CE v3 — two-mode installer logic + the cost opt-out profile (G-7.4). PURE.

The operator-typeless install (``docs/architecture/pilot-deployment-transport.md``):
two modes — a served **one-liner** (`curl … | bash` → onboard) and an
**agent-native** mode (the agent fetches a SIGNED install spec and **verifies it
against a pinned CE public key BEFORE executing**). Both provision the runtime
backend + the GitHub App + PEM-on-tmpfs custody + the policy bundle. **Human
contract:** the operator types nothing; approves only **sudo** (privileged
installs) + the **GitHub-App authorization click**.

This module is the **CI-pure decision substrate** — the verify-before-execute
gate, the detect-don't-assume dependency planner, the Default-vs-Custom installer
profile (with the cost opt-out), and the ``ce`` CLI-exposure plan. **The live
drive is the deferred seam:** the actual ``curl|bash`` execution, the runtime
backend provisioning (gVisor / egress proxy), the interactive GitHub-App click,
and the live transport probe are NOT here — exactly the G-4/G-5/G-6 cut. The
read-only dependency *detection* (which/probe) is injected (the CLI does it live;
the planner stays pure).

Signing model: this repo ships no asymmetric-crypto dependency, so the in-tree
floor is a **content-address integrity** binding (sha256), with the real
asymmetric verify supplied through an **injectable verifier** seam (the pinned CE
public key + the algorithm backend) — mirroring CE's existing "content-hash +
injected signer" pattern (forge App-JWT; the v1 shape-only event signatures). The
LOAD-BEARING logic — *verify before execute, refuse on tamper / unknown key* — is
CI-pure here; only the cryptographic primitive is the injected/deferred backend.

PURE: no disk / subprocess / socket / clock / rng. Defensive only — it governs how
CE installs ITSELF (the grader-outside-the-agent principle applied at install
time: the human ratifies the privileged step; the rest runs under a verifiable
spec); never an offensive capability.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Callable

#: The user-facing command the pilot install exposes (Operator-ratified directive).
CE_CMD = "ce"
#: The internal monorepo console_script the pilot aliases ``ce`` onto.
INTERNAL_ENTRY = "cev3"

#: The dependencies the installer detects (detect-don't-assume). ``uv`` is
#: user-space (no sudo); the rest are system installs (batched sudo ask).
REQUIRED_DEPENDENCIES = ("git", "python", "runsc", "proxy", "uv")
_SUDO_TOOLS = frozenset({"git", "python", "runsc", "proxy"})

#: The educate-at-opt-out copy — VERBATIM from ``docs/contracts/spend-envelope.md``.
EDUCATE_AT_OPTOUT = (
    "Turning this off won't speed up your runs; it only removes per-run / "
    "per-fleet budget friction. The runaway-detection net (global ceiling + "
    "anomaly → escalate) stays on."
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
#: The in-tree integrity-floor algorithm (a content address; not asymmetric crypto).
CONTENT_ALGO = "sha256-content"

#: The PINNED CE signing keys (key_id → published public-key material). The agent
#: verifies a served install spec against these BEFORE executing. The in-tree floor
#: verifies content-address integrity + key_id pinning; the real asymmetric verify
#: against the published material is the injected verifier (deferred live). The
#: material here is an out-of-band-published placeholder marker, not a secret.
PINNED_KEYS: dict[str, str] = {
    "ce-root-v1": "ed25519:published-out-of-band-at-creator-engine.dev/keys/ce-root-v1",
}


class InstallRefused(Exception):
    """A fail-closed refusal — verification failed or the opt-out is unratified."""


# ---------------------------------------------------------------------------
# Verify-before-execute (sign / verify) — PURE
# ---------------------------------------------------------------------------
def content_digest(spec_bytes: bytes | str) -> str:
    """The sha256 content address of an install spec (the integrity floor)."""
    if isinstance(spec_bytes, str):
        spec_bytes = spec_bytes.encode("utf-8")
    return hashlib.sha256(spec_bytes).hexdigest()


def sign_spec(spec_bytes: bytes | str, *, key_id: str, signer: Callable[[bytes], str] | None = None) -> dict[str, Any]:
    """Produce a signature block ``{key_id, algo, value}`` for an install spec.

    The default (no ``signer``) emits the content-address floor (sha256). A real
    asymmetric ``signer`` (injected) produces an ``algo``-tagged value — deferred.
    """
    raw = spec_bytes.encode("utf-8") if isinstance(spec_bytes, str) else spec_bytes
    if signer is None:
        return {"key_id": key_id, "algo": CONTENT_ALGO, "value": content_digest(raw)}
    return {"key_id": key_id, "algo": "asymmetric", "value": signer(raw)}


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    reason: str
    key_id: str | None = None


def _default_verifier(algo: str, raw: bytes, value: Any, key_material: Any) -> bool:
    """The in-tree integrity floor: a content-address match. Asymmetric → injected."""
    if algo == CONTENT_ALGO:
        return isinstance(value, str) and value == content_digest(raw)
    return False  # a real asymmetric algo needs an injected verifier


def verify_spec(
    spec_bytes: bytes | str,
    signature: Any,
    *,
    pinned_keys: dict[str, Any],
    verifier: Callable[[str, bytes, Any, Any], bool] | None = None,
) -> VerifyResult:
    """Verify an install spec's signature against the PINNED CE keys (PURE).

    Refuses unless (1) the signature names a ``key_id`` present in ``pinned_keys``
    AND (2) the (injected, else floor) ``verifier`` accepts the value. Returns a
    :class:`VerifyResult`; never raises (the gate :func:`require_verified` raises).
    """
    raw = spec_bytes.encode("utf-8") if isinstance(spec_bytes, str) else spec_bytes
    if not isinstance(signature, dict):
        return VerifyResult(False, "no signature block")
    key_id = signature.get("key_id")
    if key_id not in pinned_keys:
        return VerifyResult(False, f"unknown/unpinned signing key {key_id!r}", key_id)
    algo = signature.get("algo", "")
    verify = verifier or _default_verifier
    if verify(algo, raw, signature.get("value"), pinned_keys[key_id]):
        return VerifyResult(True, "verified against pinned key", key_id)
    return VerifyResult(False, f"signature did not verify (algo {algo!r})", key_id)


def require_verified(
    spec_bytes: bytes | str,
    signature: Any,
    *,
    pinned_keys: dict[str, Any],
    verifier: Callable[[str, bytes, Any, Any], bool] | None = None,
) -> VerifyResult:
    """The verify-BEFORE-execute gate — raise :class:`InstallRefused` on failure."""
    result = verify_spec(spec_bytes, signature, pinned_keys=pinned_keys, verifier=verifier)
    if not result.ok:
        raise InstallRefused(f"install spec refused before execution: {result.reason}")
    return result


# ---------------------------------------------------------------------------
# Dependency detection — detect-don't-assume, fix-with-permission (PURE)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DepStep:
    name: str
    present: bool
    action: str        # "skip" | "install"
    requires_sudo: bool


@dataclass(frozen=True)
class InstallPlan:
    steps: tuple[DepStep, ...]

    @property
    def to_install(self) -> tuple[str, ...]:
        return tuple(s.name for s in self.steps if s.action == "install")

    @property
    def needs_sudo(self) -> bool:
        # batched: a single sudo ask covers every privileged install
        return any(s.action == "install" and s.requires_sudo for s in self.steps)


def plan_dependencies(required: Any = REQUIRED_DEPENDENCIES, probe: dict[str, bool] | None = None) -> InstallPlan:
    """Plan dependency resolution from an injected presence probe (PURE).

    ``probe`` maps a tool → present? (the live read-only ``which`` detection is
    done by the CLI and injected here). Present → skip; missing → a
    permission-gated install step (idempotent; ``_SUDO_TOOLS`` need sudo, batched).
    Never fail-on-missing — it plans, the human approves.
    """
    probe = probe or {}
    steps: list[DepStep] = []
    for tool in required:
        present = bool(probe.get(tool, False))
        steps.append(DepStep(
            name=tool,
            present=present,
            action="skip" if present else "install",
            requires_sudo=(tool in _SUDO_TOOLS),
        ))
    return InstallPlan(tuple(steps))


# ---------------------------------------------------------------------------
# The Default-vs-Custom installer profile + the cost opt-out (PURE)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class InstallerProfile:
    mode: str                    # "default" | "custom"
    runtime_policy: dict[str, Any]   # the spend_cap_* fragment ce_spend_envelope accepts
    educate: str | None          # the educate-at-opt-out copy (present iff opting out)


def _valid_optout(ratification: Any) -> bool:
    return (
        isinstance(ratification, dict)
        and isinstance(ratification.get("ratified_prompt_sha"), str)
        and bool(_HEX64_RE.match(ratification["ratified_prompt_sha"]))
        and isinstance(ratification.get("approver_ref"), str)
        and bool(_HEX64_RE.match(ratification["approver_ref"]))
    )


def build_profile(*, opt_out: bool = False, optout_ratification: Any = None) -> InstallerProfile:
    """Assemble the installer profile (PURE).

    **Default** → ``spend_cap_enforcement: enforce`` (the cost-runaway protection
    on). **Custom opt-out** → ``off`` + a REQUIRED ``spend_cap_optout`` ratification
    binding (ratified-HUMAN-only; an agent can never opt out) + the educate copy.
    The opt-out disables only the budget CAPS — the runaway-DETECTION net (the
    global ceiling + anomaly→escalate) stays on (cap/detection split, G-5). The
    emitted fragment is exactly what ``ce_spend_envelope`` accepts.
    """
    if not opt_out:
        return InstallerProfile("default", {"spend_cap_enforcement": "enforce"}, None)
    if not _valid_optout(optout_ratification):
        raise InstallRefused(
            "cost opt-out is a ratified-HUMAN-only choice — it REQUIRES a "
            "spend_cap_optout binding with a 64-hex ratified_prompt_sha + "
            "approver_ref (an agent can never opt out of cost enforcement)"
        )
    return InstallerProfile(
        "custom",
        {"spend_cap_enforcement": "off", "spend_cap_optout": dict(optout_ratification)},
        EDUCATE_AT_OPTOUT,
    )


# ---------------------------------------------------------------------------
# The ``ce`` CLI-exposure step (PURE)
# ---------------------------------------------------------------------------
def ce_exposure_plan(*, command: str = CE_CMD, via: str = INTERNAL_ENTRY) -> dict[str, str]:
    """The plan step exposing the v3 CLI as ``ce`` on the v3-only pilot install.

    The pilot installs v3 ONLY (no v1 ``ce`` to collide with), so the installer
    exposes this CLI AS ``ce`` (an alias/symlink onto the ``cev3`` console_script,
    or a v3-only distribution whose script is named ``ce``). The live symlink is
    the deferred drive. Per the Operator-ratified user-facing-name directive.
    """
    return {
        "step": "expose_cli",
        "command": command,
        "via": via,
        "rationale": "pilot installs v3-only; the user types `ce` (never the internal `cev3`)",
    }


# ---------------------------------------------------------------------------
# Assemble the full (dry-run) install plan (PURE)
# ---------------------------------------------------------------------------
def build_install_plan(
    spec_bytes: bytes | str,
    signature: Any,
    *,
    pinned_keys: dict[str, Any],
    probe: dict[str, bool] | None = None,
    mode: str = "agent-native",
    opt_out: bool = False,
    optout_ratification: Any = None,
    verifier: Callable[[str, bytes, Any, Any], bool] | None = None,
) -> dict[str, Any]:
    """Verify-then-plan: the CI-pure install plan a live drive would execute.

    Order is load-bearing: **verify the spec FIRST** (raises
    :class:`InstallRefused` on tamper / unknown key — nothing is planned for an
    unverified spec), then the dependency plan, the profile, and the ``ce``
    exposure. Records the **human-approval contract** (sudo + the GitHub-App click
    are the only human steps). Pure — no execution.
    """
    verified = require_verified(spec_bytes, signature, pinned_keys=pinned_keys, verifier=verifier)
    deps = plan_dependencies(REQUIRED_DEPENDENCIES, probe)
    profile = build_profile(opt_out=opt_out, optout_ratification=optout_ratification)
    return {
        "mode": mode,
        "verified": {"ok": verified.ok, "key_id": verified.key_id},
        "dependencies": {
            "install": list(deps.to_install),
            "skip": [s.name for s in deps.steps if s.action == "skip"],
            "needs_sudo": deps.needs_sudo,
        },
        "profile": {"mode": profile.mode, "runtime_policy": profile.runtime_policy},
        "educate": profile.educate,
        "expose_cli": ce_exposure_plan(),
        # the ONLY human-approved steps — the operator types nothing else:
        "human_approves": (
            (["sudo (privileged dependency installs)"] if deps.needs_sudo else [])
            + ["the GitHub-App authorization click"]
        ),
        "deferred_live_seams": [
            "the curl|bash / privileged execution",
            "the runtime backend provisioning (gVisor runsc + egress proxy)",
            "the interactive GitHub-App authorization",
            "the live transport probe",
        ],
    }
