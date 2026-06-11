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

import base64
import binascii
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
#: The real asymmetric algorithm the served spec is signed with (an OpenSSH
#: detached SSHSIG over the canonical bytes — verifiable with stock ``ssh-keygen``,
#: no CE tooling, which is what breaks the install-time bootstrap circularity).
SSH_ED25519_ALGO = "ssh-ed25519"
#: The fixed SSHSIG namespace the trust root signs/verifies under (``-n`` to
#: ``ssh-keygen -Y``). Pinned in-spec; a wrong namespace fails verification.
SSH_SIG_NAMESPACE = "ce-spec-v1"
#: The repo-served trust root (the OpenSSH ``allowed_signers`` file) — Pages maps it
#: to ``creator-engine.dev/keys/ce-root-v1`` (extension-less). The PURE
#: :func:`parse_allowed_signers` loader turns its bytes into :data:`PINNED_KEYS`;
#: this module never reads it from disk (the CLI/tests inject the text).
PINNED_KEY_FILE = "docs/keys/ce-root-v1"
#: The placeholder token a dynamic signature field carries in the CANONICAL bytes
#: (reused byte-for-byte from E.3: the served spec's content digest covered the
#: file with ``value:`` set to exactly this token). The canonical bytes normalize
#: every dynamic signature field back to this token, so embedding the real
#: ``value:``/``content_sha256:`` never changes what the signature covers.
SIGNATURE_PLACEHOLDER = "<published-with-this-spec>"

#: The PINNED CE signing key (key_id → the published ``allowed_signers``-format
#: line: ``<principal> <keytype> <base64-key>``). The agent verifies a served
#: install spec against this BEFORE executing. Mirrors the repo-served trust root
#: :data:`PINNED_KEY_FILE`; the public key is published material, never a secret.
PINNED_KEYS: dict[str, str] = {
    "ce-root-v1": (
        "ce-root-v1 ssh-ed25519 "
        "AAAAC3NzaC1lZDI1NTE5AAAAIG/El7UgQWNbfCv0so+P8eERg8oGkQqr6HjumrcnMLpJ"
    ),
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


def sign_spec(
    spec_bytes: bytes | str,
    *,
    key_id: str,
    signer: Callable[[bytes], str] | None = None,
    algo: str | None = None,
) -> dict[str, Any]:
    """Produce a signature block ``{key_id, algo, value}`` for an install spec.

    The default (no ``signer``) emits the content-address floor (sha256). A real
    asymmetric ``signer`` (injected) produces an ``algo``-tagged value — the
    Operator's offline ``ssh-keygen -Y sign`` flow passes ``algo="ssh-ed25519"``
    and a ``signer`` that returns the base64 of the detached ``.sig`` (see
    :func:`operator_sign_recipe`). The private key never touches this module.
    """
    raw = spec_bytes.encode("utf-8") if isinstance(spec_bytes, str) else spec_bytes
    if signer is None:
        return {"key_id": key_id, "algo": CONTENT_ALGO, "value": content_digest(raw)}
    return {"key_id": key_id, "algo": algo or "asymmetric", "value": signer(raw)}


def operator_sign_recipe(
    canonical_bytes_path: str = "ce-spec.canonical",
    *,
    key_path: str = "~/.ce-keys/ce-root-v1",
) -> str:
    """The Operator's offline detached-signing act (DOCUMENTED, never automated;
    the private key never reaches the repo or any seat). Signs the canonical
    bytes under the fixed namespace, then base64-encodes the ``.sig`` for the
    ``value:`` field. Returned as a shell template for the runbook — pure."""
    return (
        f"ssh-keygen -Y sign -f {key_path} -n {SSH_SIG_NAMESPACE} {canonical_bytes_path} "
        f"&& base64 -w0 {canonical_bytes_path}.sig"
    )


def parse_allowed_signers(text: str) -> dict[str, str]:
    """Parse an OpenSSH ``allowed_signers`` file into ``{principal: line}`` (PURE).

    Each non-comment line is ``<principal> <keytype> <base64-key> [comment]``;
    the principal is the pinned ``key_id``. The whole line is retained as the
    pinned material (the verifier hands it back to ``ssh-keygen -Y verify -f``).
    Lines that do not parse as at least ``principal keytype key`` are skipped —
    the loader never raises; an empty result simply pins nothing (fail-closed)."""
    pinned: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 3:
            continue
        principal = fields[0].split(",")[0]
        pinned[principal] = line
    return pinned


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


def ssh_ed25519_verifier(
    runner: Callable[..., bool] | None,
    *,
    namespace: str = SSH_SIG_NAMESPACE,
) -> Callable[[str, bytes, Any, Any], bool]:
    """Build the ``ssh-ed25519`` SSHSIG verifier on an INJECTED runner (PURE here;
    fail-closed). The asymmetric primitive — ``ssh-keygen -Y verify`` — has no
    place in this CI-pure module (no subprocess), so the CLI/tests inject a
    ``runner`` that performs it; this returns the verifier
    :func:`verify_spec` plugs in.

    The verifier:
      * accepts ONLY ``algo == "ssh-ed25519"`` (any other ⇒ ``False``);
      * base64-decodes the block's ``value`` into the detached ``.sig`` bytes
        (malformed base64 ⇒ ``False``);
      * derives the ``-I`` identity (principal) from the pinned
        ``allowed_signers`` line (``key_material``);
      * hands ``(message=raw, signature, allowed_signers, identity, namespace)``
        to ``runner`` and returns its boolean.

    A missing runner (no ``ssh-keygen`` wired), a missing-binary failure, or ANY
    runner exception ⇒ ``False`` — verification fails CLOSED, never half-open."""
    def _verify(algo: str, raw: bytes, value: Any, key_material: Any) -> bool:
        if algo != SSH_ED25519_ALGO or runner is None:
            return False
        if not isinstance(value, str) or not isinstance(key_material, str):
            return False
        try:
            signature = base64.b64decode(value.encode("ascii"), validate=True)
        except (binascii.Error, ValueError):
            return False
        fields = key_material.split()
        if len(fields) < 3:
            return False
        identity = fields[0].split(",")[0]
        try:
            return bool(runner(
                message=raw,
                signature=signature,
                allowed_signers=key_material,
                identity=identity,
                namespace=namespace,
            ))
        except Exception:
            return False

    return _verify


def canonical_spec_bytes(spec_bytes: bytes | str) -> bytes:
    """Normalize a served spec to the CANONICAL bytes the signature covers (PURE).

    Reuses the E.3 canonicalization byte-for-byte and extends it to every dynamic
    signature field: this is the spec with the signature block's ``value:`` and
    ``content_sha256:`` lines reset to exactly ``  <field>: <placeholder>`` (full
    line, no trailing comment), everything else byte-for-byte UTF-8. Embedding the
    real values therefore never changes what the detached SSHSIG / the
    ``content_sha256`` floor cover — and an agent reproduces these bytes with one
    stock ``sed`` (the §0 recipe). Lines are matched anywhere a signature field
    appears; the indentation (two spaces) matches the in-comment YAML block."""
    raw = spec_bytes.encode("utf-8") if isinstance(spec_bytes, str) else spec_bytes
    text = raw.decode("utf-8")
    for field_name in ("value", "content_sha256"):
        text = re.sub(
            rf"(?m)^(  {field_name}: ).*$",
            rf"\g<1>{SIGNATURE_PLACEHOLDER}",
            text,
        )
    return text.encode("utf-8")


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


# ---------------------------------------------------------------------------
# v3.5-E.3 E3-G2 — the GitHub leg, decomposed (PURE planners, injected probes)
#
# The contract's "the operator approves the GitHub-App authorization click"
# step, decomposed into plannable parts (design §2.2 step 4): repo plan ·
# bootstrap-token scope VERIFICATION · App plan (shared vs own,
# click-or-detect) · branch-protection desired-state diff (the reference
# posture as data, from the answers schema) · Actions workflow plan · the
# reviewer-identity floor. All pure, mirroring `plan_dependencies`: the live
# read-only probes are injected by the CLI; the live API MUTATIONS stay the
# deferred seam (the forge HTTPS-Bearer App-JWT adapter is the mint leg —
# `forge.app_jwt_runner` / `forge.github_repo_config` — when the drive goes
# live; gh cannot App-JWT auth).
# ---------------------------------------------------------------------------

#: Minimal fine-grained bootstrap-token permissions on the target repo —
#: VERIFIED by probe (a check, not an input; design §2.2).
REQUIRED_BOOTSTRAP_SCOPES = (
    "administration:write",
    "contents:write",
    "actions:write",
    "workflows:write",
)
#: Needed additionally ONLY when creating a new repo inside an org.
ORG_CREATE_SCOPE = "org:repo_create"
#: The CE-published shared GitHub App (fork F5: the solo-pilot default).
SHARED_APP_SLUG = "creator-engine"


def app_bot_identity(slug: str = SHARED_APP_SLUG) -> str:
    """The App's bot login — the AUTHOR identity CE opens/merges PRs under
    (≠ the human), which is what makes solo no-self-approval hold."""
    return f"{slug}[bot]"


def github_detected_facts(probe: dict[str, Any] | None) -> dict[str, Any]:
    """Project an injected read-only GitHub probe into detected merge facts
    (the dotted keys `merge_answers` consumes). Probe keys (all optional —
    detection is read-only; absence = unprobed):

      origin_remote        cwd origin `owner/name` → detect-and-offer existing
      token_login          the bootstrap token's authenticated login
      app_installation_id  an existing App installation (re-run convergence)
    """
    probe = probe or {}
    detected: dict[str, Any] = {}
    if probe.get("origin_remote"):
        detected["github.mode"] = "existing"
        detected["github.repo"] = probe["origin_remote"]
    if probe.get("token_login"):
        detected["github.reviewer"] = probe["token_login"]
    if probe.get("app_installation_id"):
        detected["github.app.installation_id"] = probe["app_installation_id"]
    return detected


def plan_repo(
    *,
    mode: str,
    repo: Any = None,
    new_repo: dict[str, Any] | None = None,
    repo_exists: bool | None = None,
) -> dict[str, Any]:
    """The existing-vs-new repo plan (pure; `repo_exists` is the injected
    read-only probe result, None = unprobed)."""
    problems: list[str] = []
    steps: list[dict[str, Any]] = []
    if mode not in ("existing", "new"):
        problems.append(f"github.mode must be 'existing' or 'new', got {mode!r}")
    if not repo:
        problems.append("github.repo is unresolved (owner/name)")
    if mode == "existing":
        action = "use_existing"
        if repo_exists is False:
            problems.append(f"github.repo {repo!r} was probed and does not exist")
    else:
        new_repo = new_repo or {}
        if repo_exists is True:
            action = "use_existing"  # idempotent re-run: create converges to use
        else:
            action = "create"
            steps.append({
                "step": "create_repo",
                "repo": repo,
                "visibility": new_repo.get("visibility", "private"),
                "default_branch": new_repo.get("default_branch", "main"),
                "description": new_repo.get("description"),
            })
    return {
        "action": action if not problems else "refuse",
        "repo": repo,
        "steps": steps if not problems else [],
        "problems": problems,
        "converged": not steps and not problems,
    }


def bootstrap_scope_table(
    granted: Any,
    *,
    org_create_needed: bool = False,
) -> dict[str, Any]:
    """The bootstrap-token scope VERIFICATION table (a check, not an input).

    ``granted`` is the injected probe result (an iterable of granted scopes);
    ``None`` = unprobed → fail-closed (every row unverified, ok False)."""
    required = list(REQUIRED_BOOTSTRAP_SCOPES)
    if org_create_needed:
        required.append(ORG_CREATE_SCOPE)
    probed = granted is not None
    granted_set = set(granted) if probed else set()
    rows = [
        {"scope": scope, "granted": (scope in granted_set) if probed else None}
        for scope in required
    ]
    missing = [r["scope"] for r in rows if r["granted"] is not True]
    return {"rows": rows, "probed": probed, "missing": missing, "ok": not missing}


def plan_github_app(
    *,
    kind: str = "shared",
    app_id: Any = None,
    client_id: Any = None,
    pem_ref: Any = None,
    installation_id: Any = None,
) -> dict[str, Any]:
    """The GitHub-App plan: shared vs own; click-or-detect-installation.

    The click cannot be put in a file — it is the contract's second
    human-approval step. In answers-file mode the installer (a) emits the
    App-install URL and polls (bounded) for the installation, and (b) on
    RE-RUN detects an existing installation (or a declared installation_id)
    and SKIPS the click entirely — converged state is fully declarative;
    only the FIRST run has the one irreducible interactive step."""
    problems: list[str] = []
    if kind not in ("shared", "own"):
        problems.append(f"github.app.kind must be 'shared' or 'own', got {kind!r}")
    slug = SHARED_APP_SLUG
    if kind == "own":
        if not app_id:
            problems.append("github.app.app_id is required for an own App")
        if not client_id:
            problems.append("github.app.client_id is required for an own App")
        if pem_ref is None or parse_secret_ref(pem_ref) is None:
            problems.append(
                "github.app.pem must be a SecretRef (tmpfs custody, e.g. "
                "file:///dev/shm/ce-app.pem) — never a raw key"
            )
        slug = str(app_id) if app_id else slug
    click_required = installation_id is None
    steps: list[dict[str, Any]] = []
    if click_required:
        steps.append({
            "step": "app_install_click",
            "human": True,
            "install_url": f"https://github.com/apps/{slug}/installations/new",
            "then": "poll for the installation (bounded wait)",
        })
    return {
        "kind": kind,
        "bot_identity": app_bot_identity(slug if kind == "own" else SHARED_APP_SLUG),
        "click_required": click_required,
        "installation_id": installation_id,
        "steps": steps,
        "problems": problems,
        "converged": not click_required and not problems,
        "custody": "PEM on tmpfs → JIT scoped token at open/merge, then revoke (never in the box)",
    }


def effective_protections(desired: Any, *, floor: dict[str, Any]) -> dict[str, Any]:
    """Overlay an answers-file protections value on the reference floor.
    `"reference"` (or absence) = the floor verbatim; an object's keys override
    field-by-field (weakening already required its ratification binding at
    answers validation — `governance_weakening_problems`)."""
    effective = dict(floor)
    if isinstance(desired, dict):
        for key, value in desired.items():
            if key != "ratification":
                effective[key] = value
    return effective


def plan_branch_protection(
    current: dict[str, Any] | None,
    desired: Any,
    *,
    floor: dict[str, Any],
) -> dict[str, Any]:
    """The branch-protection desired-state DIFF (declarative reconciliation,
    the terraform model): read current state (injected probe; None =
    unprotected/unprobed), diff against desired, plan ONLY the drift, report
    the diff before any mutation. Same answers, second run → empty plan.

    `required_checks` compares as a SUBSET (the live apply unions contexts —
    mirroring `forge.github_repo_config.BranchProtectionPolicy.with_contexts`
    — so configuring never silently drops a check someone else registered)."""
    effective = effective_protections(desired, floor=floor)
    current = current or {}
    drift: list[dict[str, Any]] = []
    for key, want in effective.items():
        have = current.get(key)
        if key == "required_checks":
            want_set = set(want if isinstance(want, list) else [])
            have_set = set(have if isinstance(have, list) else [])
            if not want_set <= have_set:
                drift.append({
                    "key": key,
                    "current": sorted(have_set),
                    "desired": sorted(want_set | have_set),
                    "note": "applied as a union — never drops an existing check",
                })
        elif have != want:
            drift.append({"key": key, "current": have, "desired": want})
    return {
        "effective_desired": effective,
        "drift": drift,
        "converged": not drift,
        "apply": "only the drift (the live PUT is the deferred forge seam)",
    }


def plan_actions_workflow(
    *,
    install_validate_workflow: bool = True,
    actions_enabled: bool | None = None,
    workflow_present: bool | None = None,
    required_check: str,
) -> dict[str, Any]:
    """The Actions plan: enable Actions (org/repo probe) + install CE's
    validate workflow so the required check exists and runs on every PR."""
    steps: list[dict[str, Any]] = []
    if actions_enabled is False:
        steps.append({"step": "enable_actions"})
    if install_validate_workflow and workflow_present is not True:
        steps.append({
            "step": "install_validate_workflow",
            "provides_required_check": required_check,
        })
    return {
        "install_validate_workflow": install_validate_workflow,
        "steps": steps,
        "converged": not steps,
    }


def reviewer_identity_floor(
    *,
    reviewer: Any = None,
    token_login: Any = None,
    bot_identity: str | None = None,
) -> dict[str, Any]:
    """The no-self-approval floor: a reviewer identity must exist and differ
    from the AUTHOR identity of CE's PRs — the App bot (solo: the human IS
    the reviewer; the detected default is the token's authenticated login)."""
    resolved = reviewer or token_login
    problems: list[str] = []
    if not resolved:
        problems.append("no reviewer identity (github.reviewer unresolved and no token login probed)")
    elif bot_identity and resolved == bot_identity:
        problems.append(
            f"reviewer {resolved!r} IS the PR author identity {bot_identity!r} — "
            "no-self-approval requires a distinct reviewer"
        )
    return {"reviewer": resolved, "author_identity": bot_identity, "ok": not problems, "problems": problems}


def build_github_leg_plan(
    answers: dict[str, Any],
    *,
    schema: dict[str, Any],
    probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose the full (dry-run) GitHub leg from a VALIDATED answers document
    plus the injected read-only probe. Pure — nothing is mutated; the live
    API drive (repo create, App install, protection PUT, workflow commit) is
    the deferred seam behind the forge mint leg.

    Probe keys consumed here beyond `github_detected_facts`:
      repo_exists           bool | None
      token_scopes          iterable of granted scopes | None
      current_protections   the read current protection state | None
      actions_enabled       bool | None
      workflow_present      bool | None
    """
    require_valid_answers(answers, schema=schema)
    probe = probe or {}
    merged = merge_answers(schema, answers=answers, detected=github_detected_facts(probe))
    floor = reference_protections(schema)
    mode = merged.value("github.mode", "existing")
    repo_plan = plan_repo(
        mode=mode,
        repo=merged.value("github.repo"),
        new_repo={
            "visibility": merged.value("github.new_repo.visibility", "private"),
            "default_branch": merged.value("github.new_repo.default_branch", "main"),
            "description": merged.value("github.new_repo.description"),
        },
        repo_exists=probe.get("repo_exists"),
    )
    org_create_needed = mode == "new" and "/" in str(merged.value("github.repo") or "") and bool(probe.get("owner_is_org"))
    scopes = bootstrap_scope_table(probe.get("token_scopes"), org_create_needed=org_create_needed)
    app_plan = plan_github_app(
        kind=merged.value("github.app.kind", "shared"),
        app_id=merged.value("github.app.app_id"),
        client_id=merged.value("github.app.client_id"),
        pem_ref=merged.value("github.app.pem"),
        installation_id=merged.value("github.app.installation_id"),
    )
    protection_plan = plan_branch_protection(
        probe.get("current_protections"),
        merged.value("github.protections", "reference"),
        floor=floor,
    )
    actions_plan = plan_actions_workflow(
        install_validate_workflow=bool(merged.value("github.actions.install_validate_workflow", True)),
        actions_enabled=probe.get("actions_enabled"),
        workflow_present=probe.get("workflow_present"),
        required_check=(floor.get("required_checks") or ["Validate governance artifacts"])[0],
    )
    reviewer_floor = reviewer_identity_floor(
        reviewer=merged.value("github.reviewer"),
        token_login=probe.get("token_login"),
        bot_identity=app_plan["bot_identity"],
    )
    converged = all([
        repo_plan["converged"], app_plan["converged"], protection_plan["converged"],
        actions_plan["converged"], scopes["ok"], reviewer_floor["ok"],
    ])
    return {
        "repo": repo_plan,
        "bootstrap_token_scopes": scopes,
        "app": app_plan,
        "branch_protection": protection_plan,
        "actions": actions_plan,
        "reviewer": reviewer_floor,
        "conflicts": [
            {"key": c.key, "file": c.file_value, "detected": c.detected_value}
            for c in merged.conflicts
        ],
        "converged": converged,
        "human_approves": (["the GitHub-App authorization click"] if app_plan["click_required"] else []),
        "deferred_live_seams": [
            "the live forge API mutations (repo create · App install · protection PUT · workflow commit)",
            "the HTTPS-Bearer App-JWT mint leg (forge.app_jwt_runner; gh cannot App-JWT auth)",
        ],
    }
