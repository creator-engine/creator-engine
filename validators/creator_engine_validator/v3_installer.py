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
drive is the E2 composition seam in ``onboard_apply``:** the actual ``curl|bash``
execution, runtime backend provisioning (gVisor / egress proxy), interactive
GitHub-App click, and live transport probe are NOT here. The read-only dependency
*detection* (which/probe) is injected (the CLI does it live; the planner stays
pure).

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
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Mapping
from urllib.parse import urlparse

from . import v3_greenfield

#: The user-facing command the pilot install exposes (Operator-ratified directive).
CE_CMD = "ce"
#: The internal monorepo console_script the pilot aliases ``ce`` onto.
INTERNAL_ENTRY = "cev3"

#: Tier-scoped dependency sets — the planner selects one by isolation tier
#: (ce-ops#71 §A.1; the gVisor→opt-in demotion). The flat Tier-2 set *was* the
#: only set; Tier 0/1 are subsets that exclude the privileged ``runsc``/``proxy``
#: pairing. ``git``/``python``/``uv`` are user-level in every tier.
#:   Tier 0 — governance-only, no sandbox (zero root).
#:   Tier 1 — governance + unprivileged OS-native sandbox (bwrap/seccomp/Landlock
#:     on Linux, Seatbelt on macOS). The sandbox primitives are PROBE-ONLY (never
#:     auto-sudo-installed — that is what keeps Tier 1 "zero root"); they are NOT
#:     planned as dep steps here, only surfaced as documented prerequisites.
#:   Tier 2 — governance + gVisor ``runsc`` + egress proxy (the heavy, privileged
#:     opt-in; the only tier that drags sudo tools into the plan).
TIER_DEPS: dict[int, tuple[str, ...]] = {
    0: ("git", "python", "uv"),
    1: ("git", "python", "uv"),                       # + sandbox primitives via the probe-only path
    2: ("git", "python", "uv", "runsc", "proxy"),
}
#: The default tier preserves TODAY's behavior (the heavy gVisor pairing). The
#: default-flip to Tier 1, the ``--sandbox`` selector, and ``solo-pilot→tier1``
#: are G71.3 (deferred — they touch the CLI/onboard/schema seams).
DEFAULT_ISOLATION_TIER = 2
#: The dependencies the installer detects (detect-don't-assume) at the default
#: tier — kept as a flat name for back-compatible callers; equals the Tier-2 set.
REQUIRED_DEPENDENCIES = TIER_DEPS[DEFAULT_ISOLATION_TIER]
#: Only the gVisor pairing is privileged. ``git``/``python``/``uv`` become
#: user-level ALWAYS (ce-ops#71 §A.1) — so a plan needs sudo iff a Tier-2 plan is
#: selected and its ``runsc``/``proxy`` are not already present.
_SUDO_TOOLS = frozenset({"runsc", "proxy"})

#: Backend-KEYED dependency sets — the #71-CORE re-frame of the numeric
#: :data:`TIER_DEPS` so deps follow the SELECTED RunnerBackend (the neutral
#: ``isolation_backend`` keys of ``schemas/runtime-policy.schema.yaml``) rather
#: than a tier number. The mapping is the same fail-closed shape as the tiers:
#:   ``os-native``    — the unprivileged default DIRECTION; **no sudo** (its
#:     sandbox primitives are PROBE-ONLY documented prerequisites, never planned
#:     as auto-sudo dep steps — what keeps it zero-root). == TIER_DEPS[0/1].
#:   ``gvisor-proxy`` — the heavy single-host opt-in; the only key that drags the
#:     privileged ``runsc``/``proxy`` pairing into the plan. == TIER_DEPS[2].
#:   ``openshell``    — the gateway tier delegates ENFORCEMENT to a container
#:     engine (Docker/Podman/VM), provisioned out-of-band by the gateway, not by
#:     this installer; the installer's own dep floor is the core no-sudo set.
#: ``git``/``python``/``uv`` are user-level in every backend.
BACKEND_DEPS: dict[str, tuple[str, ...]] = {
    "os-native": ("git", "python", "uv"),
    "gvisor-proxy": ("git", "python", "uv", "runsc", "proxy"),
    "openshell": ("git", "python", "uv"),
}
#: The schema-level default backend (``schemas/runtime-policy.schema.yaml``
#: ``isolation_backend.default``). It STAYS ``gvisor-proxy`` so records authored
#: before #71 (omitting the field) keep today's backend — the GATE on the
#: default-flip migration (ce-ops#71 req-4): the no-sudo default reaches a record
#: only by an explicit ``isolation_backend`` or a profile that maps to it, never
#: by a silent global flip that would break gVisor-pinned fixtures/answer-files.
DEFAULT_ISOLATION_BACKEND = "gvisor-proxy"
#: Per-profile default backend (the install-answers ``profile`` field →
#: ``isolation_backend``). ``solo-pilot`` (governance-only) maps to the
#: unprivileged ``os-native`` so it stops dragging the gVisor runtime (ce-ops#71
#: Edit C / OQ-4 "solo-pilot → os-native is clear"). ``team`` stays at the
#: conservative :data:`DEFAULT_ISOLATION_BACKEND` because the shared-host
#: threat-model default is an OPEN Operator call (research §9 OQ-4) — NOT
#: hardcoded to os-native here; ESCALATED.
PROFILE_DEFAULT_BACKEND: dict[str, str] = {
    "solo-pilot": "os-native",
    "team": DEFAULT_ISOLATION_BACKEND,
}


#: Backend → numeric isolation tier (the G71.2 :data:`TIER_DEPS` attestation
#: seam). Keeps the numeric ``isolation_tier`` carried on the profile in agreement
#: with the SELECTED backend, so the emitted plan never advertises a heavier tier
#: than the backend ``--apply`` actually materializes (ce-ops#71 MINOR-C):
#:   ``os-native``    → Tier 1 (governance + the unprivileged OS-native sandbox).
#:   ``openshell``    → Tier 0 (the installer provisions no LOCAL sandbox; the
#:     gateway delegates enforcement to a container engine out-of-band).
#:   ``gvisor-proxy`` → Tier 2 (the only tier that drags the privileged runtime).
#: Tiers 0/1 share the same no-sudo dep floor, so the number is attestation
#: metadata + the ``tier == 2`` gVisor-seam gate — never a privilege change.
BACKEND_TIER: dict[str, int] = {
    "os-native": 1,
    "gvisor-proxy": 2,
    "openshell": 0,
}


def tier_for_backend(backend: Any) -> int:
    """Map a resolved ``isolation_backend`` key to its numeric tier (PURE, fail-closed).

    An unknown key is REFUSED (never a silent fall-through to the heavy default) so
    the tier the plan attests always matches a known backend.
    """
    if backend not in BACKEND_TIER:
        raise InstallRefused(
            f"unknown isolation backend {backend!r}: expected one of "
            f"{sorted(BACKEND_TIER)}"
        )
    return BACKEND_TIER[backend]


def resolve_isolation_backend(*, profile: Any = None, explicit: Any = None) -> str:
    """Resolve the selected ``isolation_backend`` (PURE, fail-closed).

    Precedence: an **explicit** ``isolation_backend`` (from a record / answers /
    a future ``--sandbox`` flag) wins; else the **profile** default
    (:data:`PROFILE_DEFAULT_BACKEND`); else the schema-level
    :data:`DEFAULT_ISOLATION_BACKEND` (``gvisor-proxy`` — the back-compat gate for
    pre-#71 records). An explicit backend that is not a known
    :data:`BACKEND_DEPS` key is REFUSED (fail-closed; never a silent fall-through).
    """
    if explicit is not None and explicit != "":
        if explicit not in BACKEND_DEPS:
            raise InstallRefused(
                f"unknown isolation backend {explicit!r}: expected one of "
                f"{sorted(BACKEND_DEPS)}"
            )
        return str(explicit)
    if isinstance(profile, str) and profile in PROFILE_DEFAULT_BACKEND:
        return PROFILE_DEFAULT_BACKEND[profile]
    return DEFAULT_ISOLATION_BACKEND

#: The educate-at-opt-out copy — VERBATIM from ``docs/contracts/spend-envelope.md``.
EDUCATE_AT_OPTOUT = (
    "Turning this off won't speed up your runs; it only removes per-run / "
    "per-fleet budget friction. The runaway-detection net (global ceiling + "
    "anomaly → escalate) stays on."
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_OPENSSH_SHA256_FINGERPRINT_RE = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
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
#: The public signed agent-native install spec origin. The CLI reads a local
#: path, but authentic onboarding is verifying this served artifact.
PUBLISHED_INSTALL_SPEC_URL = "https://creator-engine.dev/llms-install.md"
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
    "ce-dev1-root-v1": (
        "ce-dev1-root-v1 ssh-ed25519 "
        "AAAAC3NzaC1lZDI1NTE5AAAAIMjl3sHqj5cutQvwHrFL6qfyQyOgz+2fssoJH29nSvTf"
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


def public_key_fingerprint(key_material: str) -> str:
    """Return the OpenSSH-style SHA256 fingerprint for an ``allowed_signers`` key.

    The out-of-band trust anchor publishes this fingerprint, not the key line
    itself, so DNS TXT / GitHub profile / Sigstore evidence can be compared
    without trusting the same-origin served ``allowed_signers`` file.
    """
    fields = key_material.split()
    if len(fields) < 3:
        raise InstallRefused("trust anchor refused: key material is not an OpenSSH public key")
    try:
        raw_key = base64.b64decode(fields[2].encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise InstallRefused(f"trust anchor refused: malformed OpenSSH key material: {exc}") from exc
    return "SHA256:" + base64.b64encode(hashlib.sha256(raw_key).digest()).decode("ascii").rstrip("=")


@dataclass(frozen=True)
class TrustAnchorRecord:
    source: str
    key_id: str
    fingerprint: str


@dataclass(frozen=True)
class TrustAnchorEvidence:
    ok: bool
    status: str
    reason: str
    agreed: tuple[str, ...] = ()
    mismatched: tuple[str, ...] = ()

    def to_record(self) -> dict[str, Any]:
        """JSON-serializable evidence for CLI inventory / plan output."""
        record: dict[str, Any] = {
            "ok": self.ok,
            "status": self.status,
            "reason": self.reason,
            "agreed": list(self.agreed),
            "mismatched": list(self.mismatched),
        }
        return record


def parse_trust_anchor_records(text: str, *, source: str) -> tuple[TrustAnchorRecord, ...]:
    """Parse out-of-band ce-root fingerprint assertions (PURE).

    Supported publish forms are intentionally line-oriented so they work for DNS
    TXT records, a GitHub org/profile field, or a Sigstore bundle annotation:
    ``ce-root-v1=SHA256:...`` and ``ce-root-v1 SHA256:...``. Invalid or unrelated
    lines are ignored; an empty parse later fails closed as ``same_origin_only``.
    """
    records: list[TrustAnchorRecord] = []
    for raw_line in text.splitlines():
        line = raw_line.strip().strip('"').strip("'").strip()
        if not line or line.startswith("#"):
            continue
        key_id = ""
        fingerprint = ""
        if "=" in line:
            left, right = line.split("=", 1)
            key_id = left.strip()
            fingerprint = (right.strip().split() or [""])[0]
        else:
            fields = line.split()
            if len(fields) >= 2:
                key_id = fields[0].rstrip(":")
                fingerprint = next((field for field in fields[1:] if field.startswith("SHA256:")), "")
        if key_id and _OPENSSH_SHA256_FINGERPRINT_RE.fullmatch(fingerprint):
            records.append(TrustAnchorRecord(source=source, key_id=key_id, fingerprint=fingerprint))
    return tuple(records)


def _unique_ordered(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)


def _url_origin(value: str | None) -> tuple[str, str, int | None] | None:
    """Return the semantic web origin for a URL-like source, else ``None``."""
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    scheme = parsed.scheme.lower()
    host = parsed.hostname.rstrip(".").lower()
    try:
        port = parsed.port
    except ValueError:
        return None
    if port is None and scheme == "https":
        port = 443
    elif port is None and scheme == "http":
        port = 80
    return (scheme, host, port)


def trust_anchor_shares_origin(anchor_source: str, install_spec_source: str | None) -> bool:
    """Whether an anchor source is same-origin with the install spec source."""
    anchor_origin = _url_origin(anchor_source)
    spec_origin = _url_origin(install_spec_source)
    return anchor_origin is not None and spec_origin is not None and anchor_origin == spec_origin


def verify_trust_anchors(
    key_id: str,
    key_material: str,
    anchors: Iterable[TrustAnchorRecord],
    *,
    install_spec_source: str | None = PUBLISHED_INSTALL_SPEC_URL,
) -> TrustAnchorEvidence:
    """Compare the verified trust-root key to out-of-band fingerprint anchors.

    Authentic install mode is VERIFIED only when at least one independently
    supplied anchor agrees with the fetched trust root and no supplied anchor for
    the key disagrees. With no matching anchor, the status is intentionally
    degraded to ``same_origin_only``. A URL anchor from the same origin as the
    install spec is not out-of-band and is refused before fingerprint equality is
    considered.
    """
    fingerprint = public_key_fingerprint(key_material)
    relevant = tuple(anchor for anchor in anchors if anchor.key_id == key_id)
    if not relevant:
        return TrustAnchorEvidence(
            ok=False,
            status="same_origin_only",
            reason=(
                "no out-of-band trust anchor matched the fetched trust root; "
                "authentic verification would rely only on same-origin repo-served material"
            ),
        )
    same_origin = _unique_ordered(
        anchor.source
        for anchor in relevant
        if trust_anchor_shares_origin(anchor.source, install_spec_source)
    )
    if same_origin:
        return TrustAnchorEvidence(
            ok=False,
            status="same_origin_anchor",
            reason=(
                "trust anchor source shares origin with the install spec; "
                "authentic verification requires an out-of-band source"
            ),
        )
    agreed = _unique_ordered(anchor.source for anchor in relevant if anchor.fingerprint == fingerprint)
    mismatched = _unique_ordered(anchor.source for anchor in relevant if anchor.fingerprint != fingerprint)
    if mismatched:
        return TrustAnchorEvidence(
            ok=False,
            status="mismatch",
            reason="out-of-band trust anchor fingerprint does not match the fetched trust root",
            agreed=agreed,
            mismatched=mismatched,
        )
    if agreed:
        return TrustAnchorEvidence(
            ok=True,
            status="verified",
            reason="out-of-band trust anchor fingerprint matches the fetched trust root",
            agreed=agreed,
        )
    return TrustAnchorEvidence(
        ok=False,
        status="same_origin_only",
        reason="no out-of-band trust anchor agreed with the fetched trust root",
    )


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


@dataclass(frozen=True)
class SignedInstallSpec:
    """The embedded SSHSIG block plus the canonical content floor."""

    signature: dict[str, Any]
    content_sha256: str
    canonical_sha256: str


@dataclass(frozen=True)
class BootstrapWheel:
    filename: str
    url: str
    sha256: str
    platforms: tuple[str, ...] = ("all",)


@dataclass(frozen=True)
class PythonAcquisition:
    platform: str
    tool: str
    version: str
    url: str
    sha256: str
    command: str


@dataclass(frozen=True)
class BootstrapManifest:
    artifact_manifest_version: int
    package_name: str
    package_version: str
    python_requires: str
    artifact_base_url: str
    sha256s_url: str
    sha256s_sha256: str
    install_sh_url: str
    install_sh_sha256s_entry: str
    answers_schema_url: str
    answers_schema_sha256: str
    app_wheel: str
    required_wheels: tuple[BootstrapWheel, ...]
    python_acquisitions: tuple[PythonAcquisition, ...]

    def wheel_by_filename(self) -> dict[str, BootstrapWheel]:
        return {wheel.filename: wheel for wheel in self.required_wheels}

    @property
    def python_acquisition(self) -> PythonAcquisition:
        return self.python_acquisition_for_platform("linux-x86_64-cp314")

    def python_acquisition_for_platform(self, platform: str) -> PythonAcquisition:
        for acquisition in self.python_acquisitions:
            if acquisition.platform == platform:
                return acquisition
        raise InstallRefused(f"bad_bootstrap_manifest: python_acquisition missing for {platform}")

    def wheels_for_platform(self, platform: str) -> tuple[BootstrapWheel, ...]:
        selected = tuple(
            wheel
            for wheel in self.required_wheels
            if "all" in wheel.platforms or platform in wheel.platforms
        )
        if self.app_wheel not in {wheel.filename for wheel in selected}:
            raise InstallRefused(
                f"bad_bootstrap_manifest: app_wheel is not listed for {platform}"
            )
        return selected


INSTALL_FAILURE_CLASSES = frozenset({
    "network_fetch_failed",
    "pages_mirror_not_ready",
    "trust_root_unreadable",
    "signature_refused",
    "artifact_hash_mismatch",
    "missing_bootstrap_dependency",
    "python_acquisition_failed",
    "python_venv_unavailable",
    "unsupported_platform",
    "venv_install_failed",
    "entrypoint_missing",
    "onboard_inventory_failed",
})


def parse_embedded_signature_block(spec_bytes: bytes | str) -> dict[str, str]:
    """Extract the served spec's embedded ``signature:`` block (PURE).

    The block is intentionally a tiny line-oriented subset so shell can parse it
    before Python exists. Required fields are returned as strings; malformed or
    incomplete blocks refuse before any caller can proceed.
    """
    text = spec_bytes.decode("utf-8") if isinstance(spec_bytes, bytes) else spec_bytes
    fields: dict[str, str] = {}
    in_signature = False
    for raw_line in text.splitlines():
        if raw_line.strip() == "signature:":
            in_signature = True
            continue
        if not in_signature:
            continue
        if raw_line.startswith("  "):
            key, sep, value = raw_line.strip().partition(":")
            if sep:
                fields[key] = value.strip()
            continue
        if raw_line.strip():
            break
    required = {"key_id", "algo", "namespace", "value", "content_sha256"}
    missing = sorted(required - fields.keys())
    if missing:
        raise InstallRefused(
            "signature_refused: install spec signature block missing "
            + ", ".join(missing)
        )
    if fields["namespace"] != SSH_SIG_NAMESPACE:
        raise InstallRefused(
            f"signature_refused: namespace {fields['namespace']!r} is not {SSH_SIG_NAMESPACE!r}"
        )
    if fields["algo"] != SSH_ED25519_ALGO:
        raise InstallRefused(
            f"signature_refused: algo {fields['algo']!r} is not {SSH_ED25519_ALGO!r}"
        )
    if not _HEX64_RE.match(fields["content_sha256"]):
        raise InstallRefused("signature_refused: content_sha256 is not a 64-hex digest")
    return fields


def parse_signed_install_spec(spec_bytes: bytes | str) -> SignedInstallSpec:
    """Parse and content-floor-check the embedded SSHSIG install spec.

    This does not run an asymmetric primitive; it prepares the exact canonical
    bytes and signature dict that ``require_verified(..., ssh_ed25519_verifier)``
    consumes at the CLI/shell I/O edge.
    """
    fields = parse_embedded_signature_block(spec_bytes)
    canonical = canonical_spec_bytes(spec_bytes)
    canonical_sha = content_digest(canonical)
    if fields["content_sha256"] != canonical_sha:
        raise InstallRefused(
            "signature_refused: signed spec content_sha256 does not match canonical bytes"
        )
    signature = {
        "key_id": fields["key_id"],
        "algo": fields["algo"],
        "value": fields["value"],
    }
    return SignedInstallSpec(
        signature=signature,
        content_sha256=fields["content_sha256"],
        canonical_sha256=canonical_sha,
    )


def _strip_inline_comment(value: str) -> str:
    return value.split(" #", 1)[0].strip()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX64_RE.match(value))


def _parse_platforms(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ("all",)
    normalized = _strip_inline_comment(value).strip()
    if normalized in {"", "*", "all"}:
        return ("all",)
    platforms = tuple(part for part in re.split(r"[,\s]+", normalized) if part)
    return platforms or ("all",)


def _platform_tag_for(os_name: str, machine: str) -> str:
    normalized_os = os_name.lower()
    normalized_machine = machine.lower()
    if normalized_os != "linux":
        raise InstallRefused(
            f"unsupported_platform: no signed wheelhouse for {os_name}/{machine}; "
            "E1 supports Linux x86_64/amd64 and Linux aarch64/arm64 with CPython 3.14 wheels"
        )
    if normalized_machine in {"x86_64", "amd64"}:
        return "linux-x86_64-cp314"
    if normalized_machine in {"aarch64", "arm64"}:
        return "linux-aarch64-cp314"
    raise InstallRefused(
        f"unsupported_platform: no signed wheelhouse for {os_name}/{machine}; "
        "E1 supports Linux x86_64/amd64 and Linux aarch64/arm64 with CPython 3.14 wheels"
    )


def parse_bootstrap_manifest(spec_bytes: bytes | str) -> BootstrapManifest:
    """Parse the line-oriented ``artifact_manifest:`` block from llms-install.md.

    The format deliberately avoids YAML-only features: two-space scalar keys,
    ``required_wheels`` list items with ``filename/url/sha256/platforms``, and a
    platform-qualified ``python_acquisition`` list. That keeps shell and this
    pure parser in parity.
    """
    text = spec_bytes.decode("utf-8") if isinstance(spec_bytes, bytes) else spec_bytes
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "artifact_manifest:")
    except StopIteration as exc:
        raise InstallRefused("missing_bootstrap_manifest: artifact_manifest block missing") from exc

    scalars: dict[str, str] = {}
    wheels: list[dict[str, str]] = []
    python_acquisitions: list[dict[str, str]] = []
    legacy_python_acquisition: dict[str, str] = {}
    section: str | None = None
    current_wheel: dict[str, str] | None = None
    current_python_acquisition: dict[str, str] | None = None

    for raw_line in lines[start + 1:]:
        if raw_line and not raw_line.startswith("  "):
            break
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line == "  required_wheels:":
            section = "required_wheels"
            continue
        if line == "  python_acquisition:":
            if current_wheel is not None:
                wheels.append(current_wheel)
                current_wheel = None
            section = "python_acquisition"
            continue
        if section == "required_wheels":
            if line.startswith("    - filename: "):
                if current_wheel is not None:
                    wheels.append(current_wheel)
                current_wheel = {"filename": _strip_inline_comment(line.split(": ", 1)[1])}
                continue
            if line.startswith("      ") and current_wheel is not None:
                key, sep, value = line.strip().partition(":")
                if sep:
                    current_wheel[key] = _strip_inline_comment(value)
                continue
        if section == "python_acquisition":
            if line.startswith("    - platform: "):
                if current_python_acquisition is not None:
                    python_acquisitions.append(current_python_acquisition)
                current_python_acquisition = {
                    "platform": _strip_inline_comment(line.split(": ", 1)[1])
                }
                continue
            if line.startswith("      ") and current_python_acquisition is not None:
                key, sep, value = line.strip().partition(":")
                if sep:
                    current_python_acquisition[key] = _strip_inline_comment(value)
                continue
            if line.startswith("    ") and current_python_acquisition is None:
                key, sep, value = line.strip().partition(":")
                if sep:
                    legacy_python_acquisition[key] = _strip_inline_comment(value)
                continue
            continue
        if line.startswith("  "):
            key, sep, value = line.strip().partition(":")
            if sep:
                scalars[key] = _strip_inline_comment(value)
    if current_wheel is not None:
        wheels.append(current_wheel)
    if current_python_acquisition is not None:
        python_acquisitions.append(current_python_acquisition)

    required_scalars = {
        "artifact_manifest_version",
        "package_name",
        "package_version",
        "python_requires",
        "artifact_base_url",
        "sha256s_url",
        "sha256s_sha256",
        "install_sh_url",
        "install_sh_sha256s_entry",
        "answers_schema_url",
        "answers_schema_sha256",
        "app_wheel",
    }
    missing = sorted(required_scalars - scalars.keys())
    if missing:
        raise InstallRefused("bad_bootstrap_manifest: missing " + ", ".join(missing))
    try:
        version = int(scalars["artifact_manifest_version"])
    except ValueError as exc:
        raise InstallRefused("bad_bootstrap_manifest: artifact_manifest_version must be an integer") from exc
    if version != 1:
        raise InstallRefused(f"bad_bootstrap_manifest: unsupported version {version}")
    for key in ("sha256s_sha256", "answers_schema_sha256"):
        if not _valid_sha256(scalars[key]):
            raise InstallRefused(f"bad_bootstrap_manifest: {key} is not a 64-hex digest")
    parsed_wheels: list[BootstrapWheel] = []
    for wheel in wheels:
        wheel_missing = sorted({"filename", "url", "sha256"} - wheel.keys())
        if wheel_missing:
            raise InstallRefused(
                "bad_bootstrap_manifest: wheel entry missing " + ", ".join(wheel_missing)
            )
        if not _valid_sha256(wheel["sha256"]):
            raise InstallRefused(
                f"bad_bootstrap_manifest: wheel {wheel['filename']} sha256 is not 64-hex"
            )
        parsed_wheels.append(
            BootstrapWheel(
                wheel["filename"],
                wheel["url"],
                wheel["sha256"],
                _parse_platforms(wheel.get("platforms")),
            )
        )
    if not parsed_wheels:
        raise InstallRefused("bad_bootstrap_manifest: required_wheels is empty")
    if scalars["app_wheel"] not in {wheel.filename for wheel in parsed_wheels}:
        raise InstallRefused("bad_bootstrap_manifest: app_wheel is not in required_wheels")

    required_python = {"tool", "version", "url", "sha256", "command"}
    if legacy_python_acquisition and not python_acquisitions:
        legacy_python_acquisition.setdefault("platform", "linux-x86_64-cp314")
        python_acquisitions.append(legacy_python_acquisition)
    parsed_python_acquisitions: list[PythonAcquisition] = []
    for acquisition in python_acquisitions:
        missing_python = sorted((required_python | {"platform"}) - acquisition.keys())
        if missing_python:
            raise InstallRefused(
                "bad_bootstrap_manifest: python_acquisition missing "
                + ", ".join(missing_python)
            )
        if not _valid_sha256(acquisition["sha256"]):
            raise InstallRefused("bad_bootstrap_manifest: python_acquisition sha256 is not 64-hex")
        parsed_python_acquisitions.append(
            PythonAcquisition(
                platform=acquisition["platform"],
                tool=acquisition["tool"],
                version=acquisition["version"],
                url=acquisition["url"],
                sha256=acquisition["sha256"],
                command=acquisition["command"],
            )
        )
    if not parsed_python_acquisitions:
        raise InstallRefused("bad_bootstrap_manifest: python_acquisition is empty")
    return BootstrapManifest(
        artifact_manifest_version=version,
        package_name=scalars["package_name"],
        package_version=scalars["package_version"],
        python_requires=scalars["python_requires"],
        artifact_base_url=scalars["artifact_base_url"],
        sha256s_url=scalars["sha256s_url"],
        sha256s_sha256=scalars["sha256s_sha256"],
        install_sh_url=scalars["install_sh_url"],
        install_sh_sha256s_entry=scalars["install_sh_sha256s_entry"],
        answers_schema_url=scalars["answers_schema_url"],
        answers_schema_sha256=scalars["answers_schema_sha256"],
        app_wheel=scalars["app_wheel"],
        required_wheels=tuple(parsed_wheels),
        python_acquisitions=tuple(parsed_python_acquisitions),
    )


def parse_sha256s(text: str) -> dict[str, str]:
    """Parse a SHA256SUMS file into ``{filename: digest}`` for shell parity tests."""
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 2:
            continue
        digest, filename = fields[0], fields[-1].lstrip("*")
        if _valid_sha256(digest):
            parsed[filename] = digest
    return parsed


def build_bootstrap_artifact_plan(
    manifest: BootstrapManifest,
    *,
    os_name: str,
    machine: str,
) -> dict[str, Any]:
    """Select the signed E1 artifact set for injected platform facts."""
    platform = _platform_tag_for(os_name, machine)
    wheels = manifest.wheels_for_platform(platform)
    python_acquisition = manifest.python_acquisition_for_platform(platform)
    return {
        "platform": platform,
        "package": f"{manifest.package_name}=={manifest.package_version}",
        "python_requires": manifest.python_requires,
        "app_wheel": manifest.app_wheel,
        "wheels": [wheel.__dict__ for wheel in wheels],
        "python_acquisition": python_acquisition.__dict__,
    }


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


def plan_dependencies(
    tier: Any = DEFAULT_ISOLATION_TIER,
    probe: dict[str, bool] | None = None,
) -> InstallPlan:
    """Plan dependency resolution from an injected presence probe (PURE).

    ``tier`` selects the dependency set, polymorphically:
      * a **backend key** (``str`` — ``os-native`` / ``gvisor-proxy`` /
        ``openshell``) resolves to :data:`BACKEND_DEPS`. This is the #71-CORE
        surface: deps follow the SELECTED backend (unknown key ⇒ fail-closed).
      * an **isolation tier** (``int`` ``0|1|2``) resolves to :data:`TIER_DEPS`
        (the G71.2 numeric surface; Tier 0/1 exclude the privileged
        ``runsc``/``proxy`` pairing).
      * an explicit **iterable** of dependency names (the pre-tier flat call) —
        for back-compatible callers.
    Default is the heavy Tier 2, preserving today's behavior.

    ``probe`` maps a tool → present? (the live read-only ``which`` detection is
    done by the CLI and injected here). Present → skip; missing → a
    permission-gated install step (idempotent; ``_SUDO_TOOLS`` need sudo, batched
    — and only ``runsc``/``proxy`` are in that set, so a plan needs sudo iff a
    Tier-2 plan is selected). Never fail-on-missing — it plans, the human approves.
    """
    if isinstance(tier, str):
        if tier not in BACKEND_DEPS:
            raise InstallRefused(
                f"unknown isolation backend {tier!r}: expected one of "
                f"{sorted(BACKEND_DEPS)}"
            )
        required: Iterable[str] = BACKEND_DEPS[tier]
    elif isinstance(tier, int) and not isinstance(tier, bool):
        if tier not in TIER_DEPS:
            raise InstallRefused(
                f"unknown isolation tier {tier!r}: expected one of {sorted(TIER_DEPS)}"
            )
        required = TIER_DEPS[tier]
    else:
        required = tier  # explicit dependency-name iterable (back-compat)
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
    #: The selected isolation tier (0|1|2; ce-ops#71 §A.1). Carried on the profile
    #: so the plan stays attestable. The selector that SETS it from the answers
    #: file / ``--sandbox`` flag (and the solo-pilot→tier1 default) is G71.3; here
    #: it defaults to the heavy Tier 2 to preserve today's behavior.
    isolation_tier: int = DEFAULT_ISOLATION_TIER


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


def build_profile(
    *,
    opt_out: bool = False,
    optout_ratification: Any = None,
    isolation_tier: int = DEFAULT_ISOLATION_TIER,
) -> InstallerProfile:
    """Assemble the installer profile (PURE).

    **Default** → ``spend_cap_enforcement: enforce`` (the cost-runaway protection
    on). **Custom opt-out** → ``off`` + a REQUIRED ``spend_cap_optout`` ratification
    binding (ratified-HUMAN-only; an agent can never opt out) + the educate copy.
    The opt-out disables only the budget CAPS — the runaway-DETECTION net (the
    global ceiling + anomaly→escalate) stays on (cap/detection split, G-5). The
    emitted fragment is exactly what ``ce_spend_envelope`` accepts.

    ``isolation_tier`` (ce-ops#71 §A.1) is carried through onto the profile,
    orthogonal to the cost dial; it defaults to the heavy Tier 2 (today's
    behavior). The selector that derives it from answers/CLI is G71.3.
    """
    if isolation_tier not in TIER_DEPS:
        raise InstallRefused(
            f"unknown isolation tier {isolation_tier!r}: expected one of {sorted(TIER_DEPS)}"
        )
    if not opt_out:
        return InstallerProfile(
            "default", {"spend_cap_enforcement": "enforce"}, None, isolation_tier
        )
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
        isolation_tier,
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
    tier: int = DEFAULT_ISOLATION_TIER,
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

    ``tier`` (ce-ops#71 §A.1) selects the isolation tier (default Tier 2 = today's
    heavy behavior). The plan stays attestable via ``profile.isolation_tier``, and
    the gVisor runtime-backend deferred seam is emitted **only for Tier 2** — Tier
    0/1 are zero-root and do not provision ``runsc``/``proxy``.
    """
    verified = require_verified(spec_bytes, signature, pinned_keys=pinned_keys, verifier=verifier)
    deps = plan_dependencies(tier, probe)
    profile = build_profile(
        opt_out=opt_out, optout_ratification=optout_ratification, isolation_tier=tier
    )
    deferred_live_seams = ["the curl|bash / privileged execution"]
    if tier == 2:
        deferred_live_seams.append(
            "the runtime backend provisioning (gVisor runsc + egress proxy)"
        )
    deferred_live_seams += [
        "the interactive GitHub-App authorization",
        "the live transport probe",
    ]
    return {
        "mode": mode,
        "verified": {"ok": verified.ok, "key_id": verified.key_id},
        "dependencies": {
            "install": list(deps.to_install),
            "skip": [s.name for s in deps.steps if s.action == "skip"],
            "needs_sudo": deps.needs_sudo,
            "isolation_tier": profile.isolation_tier,
        },
        "profile": {
            "mode": profile.mode,
            "runtime_policy": profile.runtime_policy,
            "isolation_tier": profile.isolation_tier,
        },
        "educate": profile.educate,
        "expose_cli": ce_exposure_plan(),
        # the ONLY human-approved steps — the operator types nothing else:
        "human_approves": (
            (["sudo (privileged dependency installs)"] if deps.needs_sudo else [])
            + ["the GitHub-App authorization click"]
        ),
        "deferred_live_seams": deferred_live_seams,
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
BROWNFIELD_SKILL_ARTIFACT_PATHS = (
    ".ce/skills/project-conventions.md",
    ".ce/skills/project-validation.md",
)
BROWNFIELD_SCOPE_SEED_PATH = ".ce/state/scopes/ce-brownfield-adoption.scope.yaml"
BROWNFIELD_REQUIRED_CHECK = "Validate governance artifacts"
BROWNFIELD_ADOPTION_BRANCH = "ce/adopt-governance"
#: ce-ops#85 E3 adoption-APPLY (the join-PR layer) — the CANONICAL executor leg ids.
#: This names the actual ``onboard_apply`` adoption legs (the join-PR flow), so the
#: projection (this constant + the ``--plan`` ``apply_steps`` below) and the executor
#: AGREE (verify-verdict MINOR). ``github_branch_protection`` is DROPPED: the join PR is
#: PR-mediated and never mutates branch protection (``administration:write`` is excluded
#: from the §6 ceiling — OQ-1), so the projection must not promise a step the executor
#: never performs. ``onboard_apply.ADOPTION_LEG_IDS`` aliases this exact tuple.
BROWNFIELD_APPLY_STEP_IDS = (
    "brownfield_inventory_drift_check",
    "brownfield_secret_preflight",
    "brownfield_build_scaffold",
    "brownfield_push_branch",
    "brownfield_open_join_pr",
    "brownfield_verify_preserved_checks",
    "brownfield_record_apply_evidence",
)


def _resolved_values(merged: MergeResult) -> dict[str, Any]:
    return {key: entry.value for key, entry in merged.resolved.items()}


def build_greenfield_first_project_plan(
    schema: dict[str, Any],
    merged: MergeResult,
    missing: Iterable[MissingAnswer],
    *,
    e2_apply_result: Mapping[str, Any] | None = None,
    e2_apply_result_ref: str | None = None,
) -> dict[str, Any] | None:
    """Compose the E4 greenfield first-project read model.

    This is an onboard projection only. It does not restate E2's GitHub/scaffold
    plan, compute E2 convergence counters, or mutate anything.
    """
    missing_items = tuple(missing)
    payload = v3_greenfield.build_first_project_plan(
        _resolved_values(merged),
        missing_keys=(item.key for item in missing_items),
        e2_plan_ref="onboard.github_leg",
        e2_apply_result=e2_apply_result,
        e2_apply_result_ref=e2_apply_result_ref,
    )
    if payload is None:
        return None
    payload["counters"] = {
        "inventory_inputs": len(schema_inventory(schema)),
        "missing_answers": len(missing_items),
    }
    return payload


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


def bootstrap_required_scopes(*, mode: str, org_create_needed: bool = False) -> tuple[str, ...]:
    """Right-size the bootstrap-PAT capability requirement to the actual operation (ce-ops#94).

    A *plain-join* (``mode != "new"`` — a new dev joining an already-CE repo) performs ZERO forge
    writes with the bootstrap PAT: every forge op rides the App installation token and branch
    protection is verify-first/defer-not-mutate (never written), so the requirement is
    IDENTITY-ONLY (empty). Greenfield (``mode == "new"``) genuinely creates the repo, installs the
    workflow, and writes protection WITH the PAT — so the full write set (+ org repo-create when
    creating in an org) is required.
    """
    if mode != "new":
        return ()
    required = list(REQUIRED_BOOTSTRAP_SCOPES)
    if org_create_needed:
        required.append(ORG_CREATE_SCOPE)
    return tuple(required)


def bootstrap_scope_table(
    granted: Any,
    *,
    org_create_needed: bool = False,
    required: Iterable[str] | None = None,
) -> dict[str, Any]:
    """The bootstrap-token scope VERIFICATION table (a check, not an input).

    ``granted`` is the injected probe result (an iterable of granted scopes);
    ``None`` = unprobed → fail-closed (every row unverified, ok False). ``required`` overrides the
    verified set (ce-ops#94 right-sizing — e.g. ``bootstrap_required_scopes``); when omitted it
    defaults to ``REQUIRED_BOOTSTRAP_SCOPES`` (+ org repo-create when needed), preserving the prior
    behavior. An empty ``required`` (plain-join, identity-only) yields no rows → trivially ``ok``."""
    if required is None:
        required = list(REQUIRED_BOOTSTRAP_SCOPES)
        if org_create_needed:
            required.append(ORG_CREATE_SCOPE)
    else:
        required = list(required)
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
    enforcement: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The branch-protection desired-state DIFF (declarative reconciliation,
    the terraform model): read current state (injected probe; None =
    unprotected/unprobed), diff against desired, plan ONLY the drift, report
    the diff before any mutation. Same answers, second run → empty plan.

    `required_checks` compares as a SUBSET (the live apply unions contexts —
    mirroring `forge.github_repo_config.BranchProtectionPolicy.with_contexts`
    — so configuring never silently drops a check someone else registered)."""
    effective = effective_protections(desired, floor=floor)
    current_was_unprobed = current is None
    current = current or {}
    enforcement_state = dict(enforcement or {})
    if not enforcement_state:
        enforcement_state = {
            "state": "unprobed" if current_was_unprobed else "verified_classic",
        }
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
        "enforcement": enforcement_state,
        "converged": not drift and enforcement_state.get("state") != "unenforceable",
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
      protection_enforcement structured enforcement state | None
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
        enforcement=probe.get("protection_enforcement"),
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


# ---------------------------------------------------------------------------
# ce-ops#53 E3 — brownfield adoption inventory + pure plan payloads
# ---------------------------------------------------------------------------
def _string_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    out: list[str] = []
    seen: set[str] = set()
    try:
        iterator = iter(values)
    except TypeError:
        return []
    for value in iterator:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _commands_from_probe(probe: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    for item in (probe.get("tests") or {}).get("commands", ()):
        if isinstance(item, dict):
            commands.extend(_string_list(item.get("command")))
        else:
            commands.extend(_string_list(item))
    return _string_list(commands)


def _candidate_value(candidates: Any) -> str | None:
    if not isinstance(candidates, list) or not candidates:
        return None
    sorted_candidates = sorted(
        [c for c in candidates if isinstance(c, dict) and c.get("value")],
        key=lambda c: (-float(c.get("confidence", 0)), str(c.get("value"))),
    )
    if not sorted_candidates:
        return None
    return str(sorted_candidates[0]["value"])


def _history_mode_from_probe(probe: dict[str, Any]) -> str:
    history = probe.get("history") or {}
    if history.get("mode") in {"git_history_present", "absent", "unknown"}:
        return str(history["mode"])
    if history.get("present") is False or history.get("head_sha") is None and history.get("present") is False:
        return "absent"
    if history.get("head_sha"):
        return "git_history_present"
    return "unknown"


def brownfield_detected_facts(probe: dict[str, Any] | None) -> dict[str, Any]:
    """Project a read-only project probe into dotted answers facts.

    The same precedence rule handles these facts as every other installer
    input: an operator file can override them, and contradictions are surfaced
    as merge conflicts.
    """
    probe = probe or {}
    conventions = probe.get("conventions") or {}
    detected: dict[str, Any] = {
        "brownfield.enabled": bool(probe.get("enabled", True)),
        "brownfield.project_root": str(probe.get("project_root") or "."),
        "brownfield.history.mode": _history_mode_from_probe(probe),
        "brownfield.secrets.preflight": str(
            (probe.get("secrets") or {}).get("preflight", "required")
        ),
    }
    commands = _commands_from_probe(probe)
    if commands:
        detected["brownfield.tests.required_commands"] = commands
    branch_pattern = _candidate_value(conventions.get("branch_patterns"))
    if branch_pattern:
        detected["brownfield.conventions.branch_pattern"] = branch_pattern
    commit_style = _candidate_value(conventions.get("commit_styles"))
    if commit_style:
        detected["brownfield.conventions.commit_style"] = commit_style
    origin = (probe.get("github") or {}).get("origin_remote")
    if origin:
        detected.update(github_detected_facts({"origin_remote": origin}))
    return detected


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


_BROWNFIELD_ATTESTOR_REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}:[A-Za-z][A-Za-z0-9_-]{0,63}$")


def _valid_brownfield_attestor_ref(value: Any) -> bool:
    return isinstance(value, str) and bool(_BROWNFIELD_ATTESTOR_REF_RE.fullmatch(value))


def brownfield_baseline_attestation_record(
    *,
    baseline_commit_sha: str,
    snapshot_content_digest: str,
    scrub_result: Mapping[str, Any],
    attestor_ref: str,
    attested_at: str,
) -> dict[str, Any]:
    """Build the value-free v0 brownfield baseline attestation record.

    Slice 1 is deliberately CI-pure: no SSHSIG, no filesystem read, no scanner
    execution, and no client values. Callers pass only already-computed digests
    and value-free scrub metadata; the returned record self-attests via
    ``content_digest`` over canonical JSON excluding that field.
    """
    if not _valid_brownfield_attestor_ref(attestor_ref):
        raise ValueError(
            "attestor_ref must be a value-free actor label pair like 'operator:peer-operator'"
        )
    scanners = scrub_result.get("scanners") if isinstance(scrub_result, Mapping) else ()
    scanner_rows: list[dict[str, str]] = []
    if isinstance(scanners, Iterable) and not isinstance(scanners, (str, bytes, Mapping)):
        for scanner in scanners:
            if not isinstance(scanner, Mapping):
                continue
            scanner_rows.append(
                {
                    "name": str(scanner.get("name", "")),
                    "version": str(scanner.get("version", "")),
                    "result": str(scanner.get("result", "")),
                }
            )
    scanner_rows.sort(key=lambda row: (row["name"], row["version"], row["result"]))
    record: dict[str, Any] = {
        "kind": "brownfield-baseline-attestation",
        "record_type": "brownfield_baseline_attestation",
        "schema_version": "1",
        "baseline_commit_sha": str(baseline_commit_sha),
        "snapshot": {"content_digest": str(snapshot_content_digest)},
        "scrub": {
            "status": str(scrub_result.get("status", "")) if isinstance(scrub_result, Mapping) else "",
            "scanners": scanner_rows,
        },
        "attestor_ref": str(attestor_ref),
        "attested_at": str(attested_at),
    }
    record["content_digest"] = content_digest(_canonical_json_bytes(record))
    return record


def canonical_brownfield_inventory_sha256(payload: dict[str, Any]) -> str:
    """Hash the value-free brownfield inventory payload with stable JSON."""
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def brownfield_inventory_sha256(
    schema: dict[str, Any],
    answers: dict[str, Any] | None,
    probe: dict[str, Any] | None,
) -> str:
    """Recompute the brownfield inventory digest from (schema, answers, probe).

    ce-ops#85 E3 adoption-APPLY: the ``brownfield_inventory_drift_check`` leg recomputes
    this over a FRESH read-only inventory at apply time and compares it to the ratified
    plan's ``inventory_sha256``; a mismatch means the repo drifted since ``--plan`` and the
    adoption refuses (``brownfield_inventory_drift``) before any scrub/build/push. It is the
    SAME canonical payload + hash :func:`build_brownfield_adoption_plan` emits, so a
    no-drift re-run reproduces the plan's digest exactly.
    """
    merged = merge_answers(
        schema, answers=answers or None, detected=brownfield_detected_facts(probe or {})
    )
    payload = _brownfield_inventory_payload(schema, merged, probe or {})
    return canonical_brownfield_inventory_sha256(payload)


def _normalized_workflows(probe: dict[str, Any]) -> list[dict[str, Any]]:
    workflows: list[dict[str, Any]] = []
    for wf in (probe.get("ci") or {}).get("workflows", ()):
        if not isinstance(wf, dict):
            continue
        check_names = _string_list(wf.get("check_names"))
        workflows.append({
            "path": str(wf.get("path") or ""),
            "name": str(wf.get("name") or ""),
            "triggers": _string_list(wf.get("triggers")),
            "jobs": _string_list(wf.get("jobs")),
            "check_names": check_names,
            "ce_validate": bool(wf.get("ce_validate", False)),
        })
    return sorted(workflows, key=lambda item: item["path"])


def _checks_to_preserve(probe: dict[str, Any], workflows: list[dict[str, Any]]) -> list[str]:
    checks = _string_list((probe.get("ci") or {}).get("current_required_checks"))
    for workflow in workflows:
        checks.extend(_string_list(workflow.get("check_names")))
    return _string_list(checks)


def _waivers_by_id(values: Any) -> dict[str, dict[str, Any]]:
    waivers: dict[str, dict[str, Any]] = {}
    if not isinstance(values, list):
        return waivers
    for item in values:
        if isinstance(item, dict) and item.get("finding_id"):
            waivers[str(item["finding_id"])] = item
    return waivers


def _finding_ids(values: Any) -> list[str]:
    ids: list[str] = []
    if not isinstance(values, list):
        return ids
    for item in values:
        if isinstance(item, dict):
            ids.extend(_string_list(item.get("id") or item.get("finding_id")))
        else:
            ids.extend(_string_list(item))
    return _string_list(ids)


def _brownfield_inventory_payload(
    schema: dict[str, Any],
    merged: MergeResult,
    probe: dict[str, Any],
) -> dict[str, Any]:
    workflows = _normalized_workflows(probe)
    floor = reference_protections(schema)
    ce_check = str((floor.get("required_checks") or [BROWNFIELD_REQUIRED_CHECK])[0])
    checks_preserved = _checks_to_preserve(probe, workflows)
    strategy = str(merged.value("brownfield.ci.required_checks_strategy", "preserve-and-add"))
    checks_to_add = [] if ce_check in checks_preserved or strategy != "preserve-and-add" else [ce_check]
    history_probe = probe.get("history") or {}
    tests = _string_list(merged.value("brownfield.tests.required_commands", _commands_from_probe(probe)))
    secrets = probe.get("secrets") or {}
    return {
        "enabled": bool(merged.value("brownfield.enabled", True)),
        "project_root": str(merged.value("brownfield.project_root", ".")),
        "ci": {
            "existing_workflows": workflows,
            "checks_to_preserve": checks_preserved,
            "checks_to_add": checks_to_add,
        },
        "tests": {
            "required_commands": tests,
            "detected_commands": _commands_from_probe(probe),
        },
        "history": {
            "mode": str(merged.value("brownfield.history.mode", _history_mode_from_probe(probe))),
            "head_sha": history_probe.get("head_sha"),
            "default_branch": history_probe.get("default_branch"),
            "commit_count": int(history_probe.get("commit_count") or 0),
            "last_commit_time": history_probe.get("last_commit_time"),
            "tags_present": bool(history_probe.get("tags_present", False)),
            "merge_commits": int(history_probe.get("merge_commits") or 0),
            "top_changed_dirs": _string_list(history_probe.get("top_changed_dirs")),
            "dirty": bool(history_probe.get("dirty", False)),
        },
        "conventions": {
            "branch_pattern": merged.value("brownfield.conventions.branch_pattern"),
            "commit_style": merged.value("brownfield.conventions.commit_style"),
            "branch_candidates": conventions_list((probe.get("conventions") or {}).get("branch_patterns")),
            "commit_candidates": conventions_list((probe.get("conventions") or {}).get("commit_styles")),
        },
        "secrets_preflight": {
            "required": merged.value("brownfield.secrets.preflight", "required") == "required",
            "status": str(secrets.get("status") or "not_run"),
            "scanner_available": secrets.get("scanner_available"),
            "planned_report": "onboard/secrets-preflight.json",
            "findings": _finding_ids(secrets.get("findings")),
        },
    }


def conventions_list(values: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(values, list):
        return out
    for item in values:
        if isinstance(item, dict) and item.get("value"):
            out.append({
                "value": str(item["value"]),
                "confidence": float(item.get("confidence", 0)),
                "source": str(item.get("source", "detected")),
            })
    return sorted(out, key=lambda item: (-item["confidence"], item["value"]))


def _scope_seed(inventory: dict[str, Any], inventory_sha256: str) -> dict[str, Any]:
    tests = inventory["tests"]["required_commands"]
    checks = inventory["ci"]["checks_to_preserve"] + inventory["ci"]["checks_to_add"]
    criteria = [
        "existing CI remains green",
        "CE validate check is added without dropping existing checks",
        "project history is preserved",
    ]
    criteria.extend(f"local validation passes: {command}" for command in tests)
    criteria.extend(f"required check remains represented: {check}" for check in checks)
    return {
        "scope_id": "ce-brownfield-adoption",
        "intent": "Adopt the existing project into CE governance",
        "mutation_class": "code",
        "acceptance_criteria": _string_list(criteria),
        "appetite": {"amount": 25.0, "unit": "%", "window": "per_run"},
        "skill_refs": list(BROWNFIELD_SKILL_ARTIFACT_PATHS),
        "binding": {"brownfield_inventory_sha256": inventory_sha256},
        "risk_notes": [
            f"history mode: {inventory['history']['mode']}",
            "do not rewrite history, delete branches, or drop existing checks",
        ],
    }


def _project_conventions_content(inventory: dict[str, Any]) -> str:
    conventions = inventory["conventions"]
    branch = conventions.get("branch_pattern") or "No branch pattern was detected."
    commit = conventions.get("commit_style") or "No commit style was detected."
    return (
        "# Project Conventions\n\n"
        f"- Branch pattern: {branch}\n"
        f"- Commit style: {commit}\n"
        "- Preserve existing branch, tag, and release history.\n"
        "- Do not change branch naming, commit style, CODEOWNERS, workflows, or protections unless the Scope says so.\n"
    )


def _project_validation_content(inventory: dict[str, Any]) -> str:
    checks = inventory["ci"]["checks_to_preserve"] + inventory["ci"]["checks_to_add"]
    commands = inventory["tests"]["required_commands"]
    lines = ["# Project Validation", ""]
    if commands:
        lines.append("## Local Commands")
        lines.extend(f"- `{command}`" for command in commands)
        lines.append("")
    else:
        lines.extend(["## Local Commands", "- No source-controlled test command was detected.", ""])
    if checks:
        lines.append("## CI Checks")
        lines.extend(f"- {check}" for check in _string_list(checks))
        lines.append("")
    lines.append("Run the listed commands and preserve the listed checks for governed changes.")
    return "\n".join(lines) + "\n"


def _artifact_plan(inventory: dict[str, Any], inventory_sha256: str) -> dict[str, Any]:
    convention_content = _project_conventions_content(inventory)
    validation_content = _project_validation_content(inventory)
    scope_seed = _scope_seed(inventory, inventory_sha256)
    skill_artifacts = [
        {
            "path": BROWNFIELD_SKILL_ARTIFACT_PATHS[0],
            "sha256": content_digest(convention_content),
            "content": convention_content,
        },
        {
            "path": BROWNFIELD_SKILL_ARTIFACT_PATHS[1],
            "sha256": content_digest(validation_content),
            "content": validation_content,
        },
    ]
    return {
        "install_answers_updates": [
            {"key": "brownfield.tests.required_commands", "value": inventory["tests"]["required_commands"]},
            {"key": "brownfield.ci.required_checks_strategy", "value": "preserve-and-add"},
        ],
        "scope_seed": scope_seed,
        "scope_seed_path": BROWNFIELD_SCOPE_SEED_PATH,
        "skill_artifacts": skill_artifacts,
    }


def _brownfield_blockers(
    inventory: dict[str, Any],
    merged: MergeResult,
    probe: dict[str, Any],
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for conflict in merged.conflicts:
        if conflict.key.startswith("brownfield.") or conflict.key == "github.repo":
            blockers.append({
                "code": "needs_operator_answers",
                "detail": f"{conflict.key} conflicts with detected reality",
            })
    if inventory["history"]["mode"] == "absent":
        blockers.append({
            "code": "needs_baseline_capture",
            "detail": "project has no Git history; synthetic history is not permitted",
        })
    if inventory["history"]["dirty"]:
        blockers.append({
            "code": "blocked_dirty_tree",
            "detail": "tracked working-tree changes make the inventory stale",
        })
    secrets = probe.get("secrets") or {}
    scanner_available = secrets.get("scanner_available")
    secrets_status = str(secrets.get("status") or "not_run")
    if inventory["secrets_preflight"]["required"]:
        # ce-ops#85 verify-verdict MAJOR-2 (plan-side fail-open fix): the old guard only
        # blocked on an EXPLICIT ``scanner_available is False`` — a ``None``/absent value
        # (a probe that simply did not RUN the scanner yet) slipped through. That is
        # benign for the pre-apply ``not_run`` projection (the apply leg runs + fail-closes
        # the scrub for real, see ``onboard_apply.brownfield_secret_preflight``), so it
        # stays ``adoptable_after_scrub``. The fail-OPEN we close: a probe that CLAIMS the
        # scrub is ``clean`` WITHOUT an affirmative ``scanner_available is True`` — absence
        # of an affirmed scanner must never read as "clean" (a green ``adoptable`` verdict
        # that lets a consumer treat apply as already-scrubbed). Treat anything other than
        # an affirmative ``True`` behind a ``clean`` claim as a STOP.
        if scanner_available is False:
            blockers.append({
                "code": "scanner_unavailable",
                "detail": "secrets preflight is required but no supported scanner is available",
            })
        elif secrets_status == "clean" and scanner_available is not True:
            blockers.append({
                "code": "scanner_unavailable",
                "detail": (
                    "secrets preflight reports 'clean' without an affirmative available "
                    "scanner; absence of a parsed/affirmed scanner is NOT clean (fail-closed)"
                ),
            })
    finding_ids = _finding_ids(secrets.get("findings"))
    answers_waivers = _waivers_by_id(merged.value("brownfield.secrets.waivers", []))
    unwaived = [fid for fid in finding_ids if fid not in answers_waivers]
    if unwaived:
        blockers.append({
            "code": "blocked_secret_findings",
            "detail": "unwaived secrets-scrub findings: " + ", ".join(unwaived),
        })
    for waiver in answers_waivers.values():
        if not valid_ratification(waiver.get("ratification"), require_ack=True):
            blockers.append({
                "code": "waiver_missing_ratification",
                "detail": f"waiver {waiver.get('finding_id')} lacks the required ratification binding",
            })
    return blockers


def _classification(blockers: list[dict[str, str]], inventory: dict[str, Any]) -> str:
    codes = {b["code"] for b in blockers}
    for code in (
        "needs_baseline_capture",
        "blocked_dirty_tree",
        "blocked_secret_findings",
        "needs_operator_answers",
        "scanner_unavailable",
        "waiver_missing_ratification",
    ):
        if code in codes:
            return code
    if inventory["secrets_preflight"]["required"] and inventory["secrets_preflight"]["status"] != "clean":
        return "adoptable_after_scrub"
    return "adoptable"


def _apply_steps(inventory: dict[str, Any], artifact_plan: dict[str, Any], inventory_sha256: str) -> list[dict[str, Any]]:
    scaffold_paths = [
        *[a["path"] for a in artifact_plan["skill_artifacts"]],
        artifact_plan["scope_seed_path"],
        ".github/workflows/ce-validate.yml",
    ]
    return [
        {
            "id": "brownfield_inventory_drift_check",
            "e2_leg": "brownfield_probe",
            "verify": {"inventory_sha256": inventory_sha256},
        },
        {
            "id": "brownfield_secret_preflight",
            "e2_leg": "brownfield_scrub_preflight",
            "scan_paths": [".", *scaffold_paths],
            "writes": [],
        },
        {
            "id": "brownfield_build_scaffold",
            "e2_leg": "brownfield_build_scaffold",
            "paths": scaffold_paths,
            "requires": ["secrets_preflight_clean_or_waived"],
        },
        {
            "id": "brownfield_push_branch",
            "e2_leg": "brownfield_push_branch",
            "branch": BROWNFIELD_ADOPTION_BRANCH,
            "requires": ["brownfield_build_scaffold"],
        },
        {
            "id": "brownfield_open_join_pr",
            "e2_leg": "brownfield_open_join_pr",
            "base": inventory["history"]["default_branch"],
            "branch": BROWNFIELD_ADOPTION_BRANCH,
            "manifest_paths": scaffold_paths,
            "plan_ref": inventory_sha256,
            "requires": ["brownfield_push_branch"],
        },
        # ce-ops#85 verify-verdict MINOR: NO ``github_branch_protection`` step. The
        # adoption join PR is PR-mediated and never mutates branch protection
        # (``administration:write`` excluded, §6 OQ-1); the union is only *recommended*
        # in the PR body. The projection must not promise a write the executor never
        # issues, so this step is dropped (projection ↔ executor agree).
        {
            "id": "brownfield_verify_preserved_checks",
            "e2_leg": "brownfield_verify_preserved_checks",
            "checks": inventory["ci"]["checks_to_preserve"] + inventory["ci"]["checks_to_add"],
        },
        {
            "id": "brownfield_record_apply_evidence",
            "e2_leg": "brownfield_record_apply_evidence",
            "value_free": True,
        },
    ]


def _brownfield_counters(
    inventory: dict[str, Any],
    artifact_plan: dict[str, Any],
    apply_steps: list[dict[str, Any]],
    merged: MergeResult,
    probe: dict[str, Any],
) -> dict[str, int]:
    detected_commands = _commands_from_probe(probe)
    command_source = merged.resolved.get("brownfield.tests.required_commands")
    operator_supplied = (
        len(_string_list(command_source.value))
        if command_source is not None and command_source.source in {"answers", "interactive"}
        else 0
    )
    findings = inventory["secrets_preflight"]["findings"]
    waivers = _waivers_by_id(merged.value("brownfield.secrets.waivers", []))
    blocking = [fid for fid in findings if fid not in waivers]
    return {
        "ci_workflows_observed": len(inventory["ci"]["existing_workflows"]),
        "ci_checks_preserved": len(inventory["ci"]["checks_to_preserve"]),
        "ci_checks_added": len(inventory["ci"]["checks_to_add"]),
        "test_commands_detected": len(detected_commands),
        "test_commands_operator_supplied": operator_supplied,
        "history_commits_sampled": int(inventory["history"]["commit_count"]),
        "convention_candidates_detected": (
            len(inventory["conventions"]["branch_candidates"])
            + len(inventory["conventions"]["commit_candidates"])
        ),
        "skill_artifacts_planned": len(artifact_plan["skill_artifacts"]),
        "scope_seed_planned": 1 if artifact_plan.get("scope_seed") else 0,
        "scrub_findings": len(findings),
        "scrub_findings_waived": len([fid for fid in findings if fid in waivers]),
        "scrub_findings_blocking": len(blocking),
        "apply_steps_planned": len(apply_steps),
    }


def brownfield_inventory_summary(
    schema: dict[str, Any],
    *,
    answers: dict[str, Any] | None = None,
    probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Value-free brownfield block for ``ce onboard --inventory``."""
    probe = probe or {}
    merged = merge_answers(schema, answers=answers or None, detected=brownfield_detected_facts(probe))
    inventory = _brownfield_inventory_payload(schema, merged, probe)
    blockers = _brownfield_blockers(inventory, merged, probe)
    return {
        "enabled": inventory["enabled"],
        "project_root": inventory["project_root"],
        "ci": inventory["ci"]["existing_workflows"],
        "tests": inventory["tests"]["required_commands"],
        "history": inventory["history"],
        "conventions": inventory["conventions"],
        "secrets_preflight": {
            "required": inventory["secrets_preflight"]["required"],
            "status": inventory["secrets_preflight"]["status"],
        },
        "blockers": blockers,
    }


def build_brownfield_adoption_plan(
    answers: dict[str, Any] | None,
    *,
    schema: dict[str, Any],
    probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose the E3 brownfield adoption payload without mutating anything."""
    answers = answers or {"answers_version": 1}
    require_valid_answers(answers, schema=schema)
    probe = probe or {}
    detected = brownfield_detected_facts(probe)
    merged = merge_answers(schema, answers=answers or None, detected=detected)
    inventory = _brownfield_inventory_payload(schema, merged, probe)
    inventory_sha256 = canonical_brownfield_inventory_sha256(inventory)
    artifact_plan = _artifact_plan(inventory, inventory_sha256)
    blockers = _brownfield_blockers(inventory, merged, probe)
    blocked = bool(blockers)
    apply_steps = [] if blocked or not inventory["enabled"] else _apply_steps(inventory, artifact_plan, inventory_sha256)
    counters = _brownfield_counters(inventory, artifact_plan, apply_steps, merged, probe)
    classification = _classification(blockers, inventory)
    return {
        "enabled": inventory["enabled"],
        "classification": classification,
        "inventory_sha256": inventory_sha256,
        "project_root": inventory["project_root"],
        "ci": inventory["ci"],
        "tests": {"required_commands": inventory["tests"]["required_commands"]},
        "history": {
            "mode": inventory["history"]["mode"],
            "head_sha": inventory["history"]["head_sha"],
            "default_branch": inventory["history"]["default_branch"],
            "blockers": [b for b in blockers if b["code"] in {"needs_baseline_capture", "blocked_dirty_tree"}],
        },
        "conventions": {
            "branch_pattern": inventory["conventions"]["branch_pattern"],
            "commit_style": inventory["conventions"]["commit_style"],
        },
        "secrets_preflight": {
            "required": inventory["secrets_preflight"]["required"],
            "planned": True,
            "status": inventory["secrets_preflight"]["status"],
            "waivers": list(_waivers_by_id(merged.value("brownfield.secrets.waivers", [])).keys()),
        },
        "artifact_plan": artifact_plan,
        "apply_steps": apply_steps,
        "blocked": blocked,
        "blockers": blockers,
        "counters": counters,
    }
