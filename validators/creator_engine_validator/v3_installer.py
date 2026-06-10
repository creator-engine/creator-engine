"""CE v3 — two-mode installer logic + the cost opt-out profile (G-7.4). PURE.

The operator-typeless install (``docs/architecture/pilot-deployment-transport.md``):
two modes — a served **one-liner** (`curl … | bash` → onboard) and an
**agent-native** mode (the agent fetches a SIGNED install spec and **verifies it
against a pinned CE public key BEFORE executing**). Both provision the runtime
backend + the GitHub App + PEM-on-tmpfs custody + the policy bundle. **Human
contract:** the operator types nothing; approves only **sudo** (privileged
installs) + the **GitHub-App authorization click**.

v3.5-E.3 unifies the two modes into ONE ENGINE (the design of record's §2):
the installer is a single pipeline of journey steps, each declaring its inputs
against one inventory derived from ``schemas/install-answers.schema.yaml`` (the
single source of truth — its ``x-ce-*`` annotations carry step / sensitivity /
modes / applicability). Mode is just *where answers come from*:
``interactive > answers-file > detected > default``, with ``--non-interactive``
turning the final ask into a fail-closed refusal that enumerates exactly what
is missing (the terraform ``-input=false`` analog). Secrets enter ONLY by
reference (:class:`SecretRef`); governance-WEAKENING answers (cost opt-out,
protections below the CE reference floor) require the ONE ratified-HUMAN-only
binding shape (:func:`valid_ratification`) — an agent preparing an answers
file can configure anything except a weaker grader. Nothing in an answers file
can bypass :func:`require_verified` — the pipeline order stays
verify → answers → probe → plan → apply.

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

PURE: no disk / subprocess / socket / clock / rng; imports stdlib plus (lazily,
answers-validation only) the pinned ``jsonschema`` — the answers SCHEMA document
is INJECTED as a dict (the CLI loads it; this module never reads disk).
Defensive only — it governs how
CE installs ITSELF (the grader-outside-the-agent principle applied at install
time: the human ratifies the privileged step; the rest runs under a verifiable
spec); never an offensive capability.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator

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


def valid_ratification(binding: Any, *, require_ack: bool = False) -> bool:
    """The ONE governance-weakening attestation validator (generalizes the G-5
    cost opt-out into an installer-wide invariant, v3.5-E.3 §2.2).

    A valid binding is ``{ratified_prompt_sha, approver_ref}`` — both 64-hex
    opaque digests, ratified-HUMAN-only. With ``require_ack=True`` (the
    answers-file form) the binding must ALSO carry
    ``educate_acknowledged: True`` — the file cannot skip the educate-first
    step. Every governance-WEAKENING answer (cost opt-out; branch protections
    below the CE reference floor) takes this same shape: an agent can
    configure anything except a weaker grader.
    """
    if not (
        isinstance(binding, dict)
        and isinstance(binding.get("ratified_prompt_sha"), str)
        and bool(_HEX64_RE.match(binding["ratified_prompt_sha"]))
        and isinstance(binding.get("approver_ref"), str)
        and bool(_HEX64_RE.match(binding["approver_ref"]))
    ):
        return False
    if require_ack and binding.get("educate_acknowledged") is not True:
        return False
    return True


def _valid_optout(ratification: Any) -> bool:
    return valid_ratification(ratification)


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


# ---------------------------------------------------------------------------
# v3.5-E.3 — the answers file + the operator-input inventory (PURE)
#
# One engine, two modes. The schema (`schemas/install-answers.schema.yaml`) is
# the single source of truth: its `x-ce-*` annotations carry each input's
# journey step / sensitivity / supply modes / applicability, and EVERYTHING
# below derives from it (the `--inventory` emission, the precedence merge, the
# fail-closed missing list). The schema document is INJECTED as a dict — this
# module never touches disk; the CLI loads it live.
# ---------------------------------------------------------------------------

#: Repo-root-relative path of the answers schema (the CLI's load target).
ANSWERS_SCHEMA_PATH = "schemas/install-answers.schema.yaml"
#: The canonical answers-file basename (committable; lands via governed PR).
ANSWERS_BASENAME = "ce-install.answers.yaml"
#: The answers-file format version this engine speaks.
ANSWERS_VERSION = 1

#: SecretRef schemes — a secret enters the answers file ONLY by reference.
SECRET_REF_SCHEMES = ("env", "file", "prompt", "keychain")
_SECRET_REF_RE = re.compile(r"^(env|file|prompt|keychain)://(\S+)$")

#: Precedence (one rule, no exceptions): interactive > answers > detected > default.
PROVENANCE_ORDER = ("interactive", "answers", "detected", "default")


@dataclass(frozen=True)
class SecretRef:
    """A parsed secret-by-reference. Inert until apply time: refs resolve at
    the moment of use, in memory; evidence records the REF, never the value."""
    scheme: str
    target: str

    @property
    def ref(self) -> str:
        return f"{self.scheme}://{self.target}"


def parse_secret_ref(value: Any) -> SecretRef | None:
    """Parse a SecretRef string (``env://VAR`` · ``file:///path`` ·
    ``prompt://label`` · ``keychain://label``). Returns ``None`` for anything
    else — including a raw secret value (pattern-only; never resolves)."""
    if not isinstance(value, str):
        return None
    match = _SECRET_REF_RE.match(value)
    if match is None:
        return None
    return SecretRef(match.group(1), match.group(2))


def require_secret_ref(value: Any, *, field_key: str) -> SecretRef:
    """Belt-and-braces raw-value refusal (design §2.3 property 3): even if the
    schema pattern drifted, a secret-typed answers value that does not parse
    as a SecretRef is REFUSED — secrets never enter the file by value."""
    ref = parse_secret_ref(value)
    if ref is None:
        raise InstallRefused(
            f"answers field {field_key!r} is secret-typed and MUST be a SecretRef "
            f"({' / '.join(s + '://…' for s in SECRET_REF_SCHEMES)}); a raw secret "
            "value is refused — secrets never enter the answers file by value"
        )
    return ref


# --- the inventory (derived from the schema's x-ce annotations) -------------
@dataclass(frozen=True)
class InventoryInput:
    """One operator input, as declared by the schema (never hand-maintained)."""
    key: str                      # dotted answers path, e.g. "github.repo"
    step: int                     # journey step that consumes it
    sensitivity: str              # plain | consent | ratification | secret
    modes: tuple[str, ...]        # F file-by-value · R by-reference · I interactive · D detected
    default: Any = None
    has_default: bool = False
    default_from: str | None = None        # dotted key seeding this one's default
    when: tuple[str, Any] | None = None    # (dotted key, required value) applicability
    optional: bool = False                 # absence is accepted; never blocks
    description: str = ""


def _iter_annotated(node: Any, prefix: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    """Walk a schema's ``properties`` tree yielding (dotted key, subschema)
    for every ``x-ce-step``-annotated input. An annotated node is ONE input
    (even when it is an object, e.g. a ratification binding); only
    UN-annotated objects are descended into."""
    if not isinstance(node, dict):
        return
    properties = node.get("properties")
    if not isinstance(properties, dict):
        return
    for name, sub in properties.items():
        if not isinstance(sub, dict):
            continue
        key = f"{prefix}{name}"
        if "x-ce-step" in sub:
            yield key, sub
        elif isinstance(sub.get("properties"), dict):
            yield from _iter_annotated(sub, prefix=f"{key}.")


def schema_inventory(schema: dict[str, Any]) -> tuple[InventoryInput, ...]:
    """The full operator-input inventory, derived from the injected schema
    (the awareness artifact's backbone — design §2.0 clause 1)."""
    items: list[InventoryInput] = []
    for key, sub in _iter_annotated(schema):
        when: tuple[str, Any] | None = None
        condition = sub.get("x-ce-when")
        if isinstance(condition, dict) and "key" in condition:
            when = (str(condition["key"]), condition.get("equals"))
        items.append(
            InventoryInput(
                key=key,
                step=int(sub["x-ce-step"]),
                sensitivity=str(sub.get("x-ce-sensitivity", "plain")),
                modes=tuple(str(m) for m in sub.get("x-ce-modes", ())),
                default=sub.get("default"),
                has_default="default" in sub,
                default_from=sub.get("x-ce-default-from"),
                when=when,
                optional=bool(sub.get("x-ce-optional", False)),
                description=str(sub.get("description", "")).strip(),
            )
        )
    return tuple(sorted(items, key=lambda item: (item.step, item.key)))


def _lookup_key(mapping: Any, dotted: str) -> tuple[bool, Any]:
    """Resolve a dotted key in a nested mapping → (present?, value)."""
    node = mapping
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


# --- the reference governance floor (as data, from the schema) --------------
def reference_protections(schema: dict[str, Any]) -> dict[str, Any]:
    """The CE branch-protection reference posture — THE floor as data, read
    from the schema's ``x-ce-reference-posture`` (single source of truth;
    planners and checks derive from here, never a hand-maintained copy)."""
    present, node = _lookup_key(
        schema.get("properties", {}),
        "github.properties.protections",
    )
    posture = node.get("x-ce-reference-posture") if present and isinstance(node, dict) else None
    if not isinstance(posture, dict):
        raise InstallRefused(
            "the injected answers schema carries no x-ce-reference-posture under "
            "github.protections — the governance floor must be data, not a guess"
        )
    return dict(posture)


def protection_weakenings(desired: dict[str, Any], *, floor: dict[str, Any]) -> tuple[str, ...]:
    """Name every way ``desired`` WEAKENS the reference floor (empty = only
    strengthens / restates). Absent keys inherit the floor — only an explicit
    answer can weaken."""
    weakenings: list[str] = []
    floor_checks = floor.get("required_checks", [])
    if "required_checks" in desired:
        desired_checks = desired["required_checks"] if isinstance(desired["required_checks"], list) else []
        dropped = [c for c in floor_checks if c not in desired_checks]
        if dropped:
            weakenings.append(f"required_checks drops the CE gate {dropped!r}")
    for flag in ("strict", "dismiss_stale", "enforce_admins", "squash_only"):
        if floor.get(flag) is True and desired.get(flag) is False:
            weakenings.append(f"{flag} disabled below the reference floor")
    floor_reviews = floor.get("required_reviews", 1)
    if isinstance(desired.get("required_reviews"), int) and desired["required_reviews"] < floor_reviews:
        weakenings.append(
            f"required_reviews {desired['required_reviews']} below the floor {floor_reviews}"
        )
    return tuple(weakenings)


def governance_weakening_problems(answers: dict[str, Any], *, schema: dict[str, Any]) -> list[str]:
    """The installer-wide governance-weakening ratification check (generalizes
    the G-5 cost opt-out, design §2.2): every answer that weakens the grader
    REQUIRES the one ratified-HUMAN-only binding shape, educate-acknowledged
    in-band. An agent can configure anything except a weaker grader."""
    problems: list[str] = []
    cost = answers.get("cost")
    if isinstance(cost, dict) and cost.get("profile") == "custom":
        if not valid_ratification(cost.get("optout"), require_ack=True):
            problems.append(
                "governance: cost.profile 'custom' (the cap opt-out) REQUIRES "
                "cost.optout {ratified_prompt_sha, approver_ref, "
                "educate_acknowledged: true} — ratified-HUMAN-only, educate-first"
            )
    github = answers.get("github")
    protections = github.get("protections") if isinstance(github, dict) else None
    if isinstance(protections, dict):
        weakenings = protection_weakenings(protections, floor=reference_protections(schema))
        if weakenings and not valid_ratification(protections.get("ratification"), require_ack=True):
            problems.append(
                "governance: github.protections weakens the CE reference floor ("
                + "; ".join(weakenings)
                + ") and REQUIRES a ratification binding {ratified_prompt_sha, "
                "approver_ref, educate_acknowledged: true} — an agent can configure "
                "anything except a weaker grader"
            )
    return problems


# --- answers validation (fail-closed) ----------------------------------------
def validate_answers(answers: Any, *, schema: dict[str, Any]) -> tuple[str, ...]:
    """Validate an answers document against the injected schema + the
    cross-field governance invariants. Returns ALL problems (fail-closed
    callers refuse on any): schema violations — including UNKNOWN KEYS, which
    must ERROR, never silently fall through to an interactive ask (the classic
    IaC footgun) — raw secret values (belt-and-braces beyond the schema
    pattern), and unratified governance weakenings."""
    if not isinstance(answers, dict):
        return (f"answers file must be a mapping, got {type(answers).__name__}",)
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("jsonschema is required; install validators/requirements.txt") from exc
    problems: list[str] = []
    for err in sorted(Draft202012Validator(schema).iter_errors(answers), key=lambda e: list(e.path)):
        pointer = "/" + "/".join(str(part) for part in err.path)
        problems.append(f"schema: {pointer}: {err.message}")
    for item in schema_inventory(schema):
        if item.sensitivity != "secret":
            continue
        present, value = _lookup_key(answers, item.key)
        if present and parse_secret_ref(value) is None:
            problems.append(
                f"secret: {item.key} must be a SecretRef "
                f"({' / '.join(s + '://…' for s in SECRET_REF_SCHEMES)}); "
                "raw secret values are refused"
            )
    problems.extend(governance_weakening_problems(answers, schema=schema))
    return tuple(problems)


def require_valid_answers(answers: Any, *, schema: dict[str, Any]) -> dict[str, Any]:
    """The fail-closed answers gate — raise :class:`InstallRefused` listing
    every problem (a typo'd key must ERROR, never look consumed)."""
    problems = validate_answers(answers, schema=schema)
    if problems:
        raise InstallRefused(
            "answers file refused (fail-closed): " + " · ".join(problems)
        )
    return answers


def optout_binding_from_answers(answers: dict[str, Any]) -> dict[str, str] | None:
    """The answers→profile bridge. A ``custom`` cost profile yields the
    validated opt-out binding STRIPPED to the two digest keys — the
    runtime-policy ``spend_cap_optout`` fragment is
    ``unevaluatedProperties: false``, so ``educate_acknowledged`` (an
    answers-file-only attestation) must not ride through. ``None`` for the
    default profile."""
    cost = answers.get("cost")
    if not isinstance(cost, dict) or cost.get("profile") != "custom":
        return None
    binding = cost.get("optout")
    if not valid_ratification(binding, require_ack=True):
        raise InstallRefused(
            "cost.profile 'custom' REQUIRES a cost.optout binding with 64-hex "
            "ratified_prompt_sha + approver_ref AND educate_acknowledged: true "
            "(ratified-HUMAN-only; the file cannot skip the educate step)"
        )
    return {
        "ratified_prompt_sha": binding["ratified_prompt_sha"],
        "approver_ref": binding["approver_ref"],
    }


# --- the precedence merge (one rule, no exceptions) --------------------------
@dataclass(frozen=True)
class ResolvedInput:
    """One merged input value + where it came from (the evidence-spine
    provenance: which inputs came from file vs interactive vs detected)."""
    key: str
    value: Any
    source: str   # one of PROVENANCE_ORDER


@dataclass(frozen=True)
class AnswerConflict:
    """A file value CONTRADICTING a detected fact (e.g. github.repo ≠ the cwd
    origin) — surfaced, never a silent override of reality. Resolution is an
    interactive answer (or a non-interactive refusal)."""
    key: str
    file_value: Any
    detected_value: Any


@dataclass(frozen=True)
class MergeResult:
    resolved: dict[str, ResolvedInput] = field(default_factory=dict)
    conflicts: tuple[AnswerConflict, ...] = ()

    def value(self, key: str, fallback: Any = None) -> Any:
        entry = self.resolved.get(key)
        return entry.value if entry is not None else fallback


def merge_answers(
    schema: dict[str, Any],
    *,
    answers: dict[str, Any] | None = None,
    detected: dict[str, Any] | None = None,
    interactive: dict[str, Any] | None = None,
) -> MergeResult:
    """The precedence merge: ``interactive > answers > detected > default``
    over the schema-derived inventory. ``detected`` and ``interactive`` are
    flat dotted-key mappings (the CLI's live read-only probes / collected
    asks); ``answers`` is the nested answers document. A file value that
    contradicts a detected fact is recorded as an :class:`AnswerConflict`
    (file precedence holds for the provisional value, but the conflict joins
    the ask/missing list until an interactive answer settles it)."""
    answers = answers or {}
    detected = detected or {}
    interactive = interactive or {}
    resolved: dict[str, ResolvedInput] = {}
    conflicts: list[AnswerConflict] = []
    deferred_defaults: list[InventoryInput] = []
    for item in schema_inventory(schema):
        file_present, file_value = _lookup_key(answers, item.key)
        detected_present = item.key in detected and detected[item.key] is not None
        detected_value = detected.get(item.key)
        if file_present and detected_present and file_value != detected_value and "D" in item.modes:
            conflicts.append(AnswerConflict(item.key, file_value, detected_value))
        if item.key in interactive and interactive[item.key] is not None:
            resolved[item.key] = ResolvedInput(item.key, interactive[item.key], "interactive")
        elif file_present:
            resolved[item.key] = ResolvedInput(item.key, file_value, "answers")
        elif detected_present:
            resolved[item.key] = ResolvedInput(item.key, detected_value, "detected")
        elif item.has_default:
            resolved[item.key] = ResolvedInput(item.key, item.default, "default")
        elif item.default_from:
            deferred_defaults.append(item)
    for item in deferred_defaults:  # cross-key defaults resolve after the pass
        seed = resolved.get(item.default_from or "")
        if seed is not None:
            resolved[item.key] = ResolvedInput(item.key, seed.value, "default")
    return MergeResult(resolved=resolved, conflicts=tuple(conflicts))


def _applicable(item: InventoryInput, merged: MergeResult) -> bool:
    """An input applies unless its x-ce-when condition resolves false."""
    if item.when is None:
        return True
    condition_key, required = item.when
    return merged.value(condition_key) == required


# --- the missing list (the batched ask / the fail-closed refusal) ------------
@dataclass(frozen=True)
class MissingAnswer:
    key: str
    step: int
    reason: str   # "needed" | "secret_ref_required" | "conflict"


def missing_answers(schema: dict[str, Any], merged: MergeResult) -> tuple[MissingAnswer, ...]:
    """Every APPLICABLE input still unresolved after the merge — in
    interactive mode each becomes one batched ask at its journey step; in
    ``--non-interactive`` mode the list IS the refusal (exactly what is
    missing, the terraform ``-input=false`` analog). Unsettled
    detected-vs-file conflicts join the list until an interactive answer
    resolves them."""
    conflicted = {c.key for c in merged.conflicts}
    missing: list[MissingAnswer] = []
    for item in schema_inventory(schema):
        if not _applicable(item, merged):
            continue
        entry = merged.resolved.get(item.key)
        if item.key in conflicted and (entry is None or entry.source != "interactive"):
            missing.append(MissingAnswer(item.key, item.step, "conflict"))
            continue
        if entry is not None:
            continue
        if item.optional:
            continue
        reason = "secret_ref_required" if item.sensitivity == "secret" else "needed"
        missing.append(MissingAnswer(item.key, item.step, reason))
    return tuple(missing)


def require_complete(missing: Iterable[MissingAnswer]) -> None:
    """The ``--non-interactive`` fail-closed gate: refuse with the EXACT
    missing list (never proceed on a guess, never ask)."""
    missing = tuple(missing)
    if not missing:
        return
    rendered = "; ".join(f"{m.key} (step {m.step}: {m.reason})" for m in missing)
    raise InstallRefused(
        f"non-interactive mode is fail-closed — unresolved inputs: {rendered}. "
        "Prepare them in the answers file (`ce onboard --inventory` lists every "
        "input) or run interactively."
    )


# --- the scoped sudo pre-grant diff (fork F4) --------------------------------
@dataclass(frozen=True)
class SudoGrantDiff:
    grant: tuple[str, ...]
    covered: tuple[str, ...]
    uncovered: tuple[str, ...]

    @property
    def converged(self) -> bool:
        return not self.uncovered


def sudo_grant_diff(grant: Iterable[str] | None, plan: InstallPlan) -> SudoGrantDiff:
    """Diff the planner's computed PRIVILEGED install set against the scoped
    sudo pre-grant (``host.sudo_grant`` — an explicit package allowlist; a
    bare ``sudo: true`` is schema-invalid by construction). Any package
    OUTSIDE the grant → stop and ask (refuse in ``--non-interactive``): the
    answers file is the operator's written upfront approval, but an unscoped
    grant would let plan drift silently widen a privileged action — which
    would violate verify-before-execute in spirit."""
    granted = tuple(grant) if grant is not None else ()
    sudo_installs = tuple(
        s.name for s in plan.steps if s.action == "install" and s.requires_sudo
    )
    covered = tuple(name for name in sudo_installs if name in granted)
    uncovered = tuple(name for name in sudo_installs if name not in granted)
    return SudoGrantDiff(grant=granted, covered=covered, uncovered=uncovered)


# --- the --inventory emission (the awareness artifact) ------------------------
def inventory_emission(
    schema: dict[str, Any],
    *,
    detected: dict[str, Any] | None = None,
    answers: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    """``ce onboard --inventory``: the full input inventory with live status
    per key — the artifact an agent reads to PREPARE the answers file
    (design §2.0 clause 1). Generated from the schema + the injected probes,
    never hand-maintained."""
    merged = merge_answers(schema, answers=answers, detected=detected)
    conflicted = {c.key: c for c in merged.conflicts}
    rows: list[dict[str, Any]] = []
    for item in schema_inventory(schema):
        entry = merged.resolved.get(item.key)
        if item.key in conflicted:
            conflict = conflicted[item.key]
            status = (
                f"conflict (file {conflict.file_value!r} contradicts "
                f"detected {conflict.detected_value!r})"
            )
        elif not _applicable(item, merged):
            status = "not-applicable"
        elif entry is not None and entry.source == "answers":
            status = f"answered:{entry.value}"
        elif entry is not None and entry.source == "detected":
            status = f"detected:{entry.value}"
        elif entry is not None and entry.source == "default":
            status = f"default:{entry.value}"
        elif item.sensitivity == "secret":
            status = "secret (ref required)"
        else:
            status = f"needed (would ask at step {item.step})"
        rows.append(
            {
                "key": item.key,
                "step": item.step,
                "sensitivity": item.sensitivity,
                "modes": list(item.modes),
                "optional": item.optional,
                "status": status,
            }
        )
    return tuple(rows)
