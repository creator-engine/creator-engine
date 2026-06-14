"""CE v3 plane-C audit overlay: classifier + AuditOverlayBackend (G-1.3b).

The backend-agnostic audit layer that makes the rented runtime *accountable*.
Two pieces, both behind the G-1.1 ``RunnerBackend`` adapter:

* a PURE **classifier** — the policy decision point: ``classify(event,
  runtime_policy)`` evaluates an observed runtime/lifecycle event against the
  G-1.0 runtime-policy record and returns ``allowed`` / ``denied`` / ``escalate``;
* a **decorator** — ``AuditOverlayBackend`` wraps any ``RunnerBackend`` so every
  ``provision -> run -> collect -> teardown`` step (and every observed runtime
  event) emits a tamper-evident, hash-chained evidence record via the merged
  G-1.3a ``runtime_evidence_spine``, bound to the ``policy_sha`` it attests.

Per the secure-runtime architect report this is the "logical-governance" layer
the rented runtime does not provide, and the audit trail that turns each runtime
decision into cryptographic evidence on top of kernel enforcement.

Design invariants (deliberate, load-bearing):

* **PURE classifier.** ``classify`` is a pure function — no live tap, no
  subprocess, no socket, no disk, no wall-clock read. It mirrors the G-1.2
  translate-vs-execute split: the live event *source* is a later seam; this
  module only decides + attests.
* **DECORATOR overlay.** ``AuditOverlayBackend`` wraps an inner backend; it does
  NOT edit the concrete backends and registers NO ``isolation_backend``. The
  inner backend does the real work; the overlay observes + attests. So
  ``gvisor-proxy`` (and the future ``openshell``) get audit for free.
* **REUSE, don't reinvent.** The hash chain is the merged G-1.3a
  ``runtime_evidence_spine`` (``append`` / ``verify_chain``); a record the
  overlay emits is exactly what the ``ce_runtime_evidence`` check accepts.
* **Not a check, not a registered backend.** Importing this module registers no
  validator check and no backend; it leaves ``--list-checks`` (43) and
  ``available_backends()`` byte-identical, and performs no I/O.
* **Pure clock seam.** Timestamps are inputs, never read from the wall clock
  here; the default ``clock`` is a deterministic counter (a real-clock
  implementation is an injected seam, a later concern).

Defensive only — accountability for our own agent runtime; never offensive.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable

from ..runtime_evidence_spine import (
    AGENT_ACTION_OPS,
    CLASSIFICATIONS,
    DECISION_MODES,
    RECORD_KIND,
    RUNTIME_AGENT_ACTION_RECORD_KIND,
    RUNTIME_AGENT_ACTION_RECORD_TYPE,
    append,
    verify_chain,
)
from .backend import (
    CollectedEvidence,
    ProvisionedHandle,
    ProvisionRequest,
    RunnerBackend,
    RunRequest,
    RunResult,
    TeardownResult,
)

#: The three classifier verdicts (reuse the spine's source of truth).
ALLOWED, DENIED, ESCALATE = CLASSIFICATIONS  # ("allowed", "denied", "escalate")


# ---------------------------------------------------------------------------
# Event model — frozen, pure inputs to the classifier. The live event *source*
# (a tap on the running container) is a deferred seam; here events are values.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LifecycleEvent:
    """A RunnerBackend lifecycle transition (provision/run/collect/teardown)."""

    phase: str


@dataclass(frozen=True)
class EgressEvent:
    """An outbound connection attempt observed inside the runtime."""

    host: str
    port: int | None = None
    phase: str = "run"


@dataclass(frozen=True)
class MountEvent:
    """A filesystem mount/access observed inside the runtime."""

    path: str
    mode: str = "ro"  # "ro" | "rw"
    phase: str = "run"


@dataclass(frozen=True)
class SecretEvent:
    """A secret-injection request observed inside the runtime."""

    name: str
    phase: str = "run"


@dataclass(frozen=True)
class AgentActionEvent:
    """A single agent action observed over a run (the v3 G-4 per-action axis).

    Two ORTHOGONAL axes carry the gate decision (design: agent-interaction
    contract):

    * ``op`` — the capability/operation axis (``read``/``write``/``exec``/
      ``egress``/``secret``/``vcs``): the *"do we gate?"* axis. Reads are
      observe-only; the rest are gateable.
    * ``mutation_class`` — the blast-radius/severity axis, drawn from the shared
      planning-layer taxonomy (``checks.mutation_class``: ``docs``/``code``/
      ``schema``/``deploy``/``governance``/``identity``/``security``/
      ``attestation``/``redaction``, plus ``none``). It is an INPUT here — the
      classifier does not derive it (the adapter that observes the action does,
      e.g. :mod:`creator_engine_validator.runner.cc_hook_adapter`), exactly as
      ``EgressEvent.host`` is an input.

    ``op`` decides *whether* to block; ``op × mutation_class × fidelity`` decides
    *how hard*. ``fidelity`` is the provenance marker (stamped by the adapter,
    never the agent; lower fidelity → stricter policy); ``timing`` is ``pre``
    (gateable before execution → preventive) or ``post`` (observed after →
    detective). ``target`` and ``tool`` are value-free provenance fields.
    """

    op: str
    mutation_class: str = "none"
    target: str = ""
    tool: str = ""
    fidelity: str = "faithful"
    timing: str = "pre"


@dataclass(frozen=True)
class Decision:
    """The deterministic verdict of :func:`decide` for one agent action.

    ``verdict`` is the enforced outcome (``allowed``/``denied``/``escalate``);
    ``mode`` is the gate-mode the verdict was produced under (provenance);
    ``reason`` is a deterministic explanation string; ``remember`` carries the
    ACP "always" persistence lever (set by a human resolving an escalation, not
    by :func:`decide`); ``escalation_id`` is a deterministic, value-free digest
    present only when ``verdict == escalate``.
    """

    verdict: str
    mode: str
    reason: str
    remember: str = "none"
    escalation_id: str | None = None


# ---------------------------------------------------------------------------
# The classifier — the pure policy decision point
# ---------------------------------------------------------------------------
def classify(event: Any, runtime_policy: dict[str, Any]) -> str:
    """Classify ``event`` against a runtime-policy record (PURE).

    Returns one of ``allowed`` / ``denied`` / ``escalate`` (the
    :data:`CLASSIFICATIONS` set), evaluated against the G-1.0 ``ce_runtime_policy``
    record's ``egress_allowlist`` / ``mount_manifest`` / ``secret_allowlist``:

    * a lifecycle transition is ``allowed`` (the policy validated clean at
      provision, else the inner backend would have refused);
    * an egress to an allowlisted host is ``allowed``, otherwise ``denied``
      (deny-by-default — an empty allowlist denies all egress);
    * a mount whose path is in the manifest is ``allowed``, unless it requests
      ``rw`` on a path granted ``ro`` (that needs a grant → ``escalate``); a path
      not in the manifest is ``denied`` (default-deny);
    * a secret whose name is in the allowlist is ``allowed``, otherwise
      ``denied``;
    * any unrecognized event type fails safe to ``escalate`` (human review).

    No I/O, no subprocess, no clock read.
    """
    if not isinstance(runtime_policy, dict):
        return ESCALATE
    if isinstance(event, LifecycleEvent):
        return ALLOWED
    if isinstance(event, EgressEvent):
        hosts = {
            rule.get("host")
            for rule in (runtime_policy.get("egress_allowlist") or [])
            if isinstance(rule, dict)
        }
        return ALLOWED if event.host in hosts else DENIED
    if isinstance(event, MountEvent):
        for entry in runtime_policy.get("mount_manifest") or []:
            if isinstance(entry, dict) and entry.get("path") == event.path:
                if event.mode == "rw" and entry.get("mode") != "rw":
                    return ESCALATE  # rw on a ro-granted mount — needs a grant
                return ALLOWED
        return DENIED  # default-deny: path not in the manifest
    if isinstance(event, SecretEvent):
        names = set(runtime_policy.get("secret_allowlist") or [])
        return ALLOWED if event.name in names else DENIED
    if isinstance(event, AgentActionEvent):
        return _classify_agent_action(event, runtime_policy)
    return ESCALATE  # unknown event type — fail safe to human review


def _action_allowlisted(op: str, mutation_class: str, runtime_policy: dict[str, Any]) -> bool:
    """True when the ``(op, mutation_class)`` cell is granted by the policy's action allowlist.

    Reads ``runtime_policy['action_class_allowlist']`` — a list of ``{op,
    mutation_class}`` grants (the additive G-4 policy field). PURE.
    """
    for cell in runtime_policy.get("action_class_allowlist") or []:
        if (
            isinstance(cell, dict)
            and cell.get("op") == op
            and cell.get("mutation_class") == mutation_class
        ):
            return True
    return False


def _classify_agent_action(event: AgentActionEvent, runtime_policy: dict[str, Any]) -> str:
    """Classify an :class:`AgentActionEvent` (PURE) — the ``op × mutation_class × fidelity`` rule.

    * an unknown ``op`` fails safe to ``escalate``;
    * ``op == read`` is ``allowed`` (observe-only — reads are never gated);
    * a mutating op observed at NON-``faithful`` fidelity ``escalate``s by default
      (Fork-1: lower observation fidelity earns stricter policy — an allowlist
      grant alone does not clear a non-faithfully-observed mutation; the
      gate-mode ladder in :func:`decide` may still resolve it, e.g. ``auto``);
    * a mutating op at ``faithful`` fidelity is ``allowed`` iff its
      ``(op, mutation_class)`` cell is on the action allowlist, else ``denied``
      (deny-by-default).
    """
    if event.op not in AGENT_ACTION_OPS:
        return ESCALATE
    if event.op == "read":
        return ALLOWED
    if event.fidelity != "faithful":
        return ESCALATE
    if _action_allowlisted(event.op, event.mutation_class, runtime_policy):
        return ALLOWED
    return DENIED


# ---------------------------------------------------------------------------
# The control-point — a deterministic, in-process, zero-token wrapper over classify
# ---------------------------------------------------------------------------
#: Cells that are DENIED unconditionally — they survive even ``full`` (YOLO) mode
#: and any ``always_allow`` rule (the Zed "built-in deny" tier). Minting or
#: altering identity/security secrets is never auto-authorized at the substrate.
BUILTIN_DENY_CELLS: frozenset[tuple[str, str]] = frozenset(
    {
        ("secret", "identity"),
        ("secret", "security"),
    }
)


def _escalation_id(event: AgentActionEvent) -> str:
    """A deterministic, value-free escalation digest for an action (PURE; no clock/rng)."""
    material = "|".join(
        (event.op, event.mutation_class, event.target, event.tool, event.fidelity, event.timing)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _rule_matches(rule: Any, event: AgentActionEvent) -> bool:
    """True when an ``always_*`` ladder rule applies to ``event`` (PURE).

    A rule may scope by ``op`` and/or ``mutation_class`` (absent = wildcard) and
    by an optional ``target_pattern`` (substring match on ``target``).
    """
    if not isinstance(rule, dict):
        return False
    if rule.get("op") not in (None, event.op):
        return False
    if rule.get("mutation_class") not in (None, event.mutation_class):
        return False
    pattern = rule.get("target_pattern")
    if pattern is not None and str(pattern) not in event.target:
        return False
    return True


def _resolve_mode(event: AgentActionEvent, ladder: dict[str, Any]) -> str:
    """Resolve the gate-mode for the ``(op, mutation_class)`` cell (PURE).

    A per-cell override wins over ``default_mode``; an absent/invalid mode falls
    back to the safe ``ask``.
    """
    for cell in ladder.get("cells") or []:
        if (
            isinstance(cell, dict)
            and cell.get("op") == event.op
            and cell.get("mutation_class") == event.mutation_class
            and cell.get("mode") in DECISION_MODES
        ):
            return str(cell["mode"])
    default_mode = ladder.get("default_mode")
    return str(default_mode) if default_mode in DECISION_MODES else "ask"


def _apply_mode(mode: str, base: str, event: AgentActionEvent) -> tuple[str, str]:
    """Compose a gate-mode with the :func:`classify` base verdict (PURE)."""
    if mode == "deny":
        return DENIED, "mode=deny"
    if mode == "full":
        # YOLO — allow; built-in denies and always_deny rules were already applied.
        return ALLOWED, "mode=full (built-in denies still apply)"
    if mode == "allowlist":
        return base, f"mode=allowlist:{base}"
    if mode == "ask":
        if base == ALLOWED:
            return ALLOWED, "mode=ask:allowed"
        return ESCALATE, "mode=ask:confirm"
    if mode == "auto":
        # Advisory-only (a deterministic stand-in for the advisory classifier):
        # it may downgrade an escalate->allow, but NEVER authorizes a deny-class
        # action — a denied base stays denied. Human review is the fallback.
        if base == DENIED:
            return DENIED, "mode=auto:deny-class-not-authorized"
        if base == ESCALATE:
            return ALLOWED, "mode=auto:advisory-allow"
        return ALLOWED, "mode=auto:allowed"
    return ESCALATE, f"mode={mode}:unknown-fail-safe"


def decide(event: Any, runtime_policy: Any) -> Decision:
    """Return a deterministic :class:`Decision` for an agent action (PURE; in-process; µs; zero-token).

    Order (all deterministic, no I/O / subprocess / socket / clock / rng):

    1. ``classify(event, policy)`` → the base verdict.
    2. **built-in deny** — a :data:`BUILTIN_DENY_CELLS` cell denies, surviving
       even ``full`` and any ``always_allow`` rule.
    3. **Zed precedence** over the ladder's ``always_*`` rules:
       ``always_deny`` > ``always_confirm`` > ``always_allow`` (deny precedes).
    4. **gate-mode ladder** — resolve the cell's mode
       (``deny``/``allowlist``/``ask``/``auto``/``full``) and compose it with the
       base verdict.

    For a non-:class:`AgentActionEvent`, :func:`decide` is a thin wrapper that
    reports the :func:`classify` verdict (no ladder applies).
    """
    base = classify(event, runtime_policy)
    if not isinstance(event, AgentActionEvent):
        return Decision(verdict=base, mode="allowlist", reason=f"classify:{base}")

    policy = runtime_policy if isinstance(runtime_policy, dict) else {}
    ladder_raw = policy.get("gate_mode_ladder")
    ladder = ladder_raw if isinstance(ladder_raw, dict) else {}
    cell = (event.op, event.mutation_class)

    # 2. built-in deny — survives full + always_allow.
    if cell in BUILTIN_DENY_CELLS:
        return Decision(DENIED, "deny", f"built-in deny for {event.op}/{event.mutation_class}")

    # 3. Zed precedence over always_* rules (deny > confirm > allow).
    effects = {
        rule.get("effect")
        for rule in (ladder.get("rules") or [])
        if isinstance(rule, dict) and _rule_matches(rule, event)
    }
    if "always_deny" in effects:
        return Decision(DENIED, "deny", "always_deny rule")
    if "always_confirm" in effects:
        return Decision(ESCALATE, "ask", "always_confirm rule", escalation_id=_escalation_id(event))
    if "always_allow" in effects:
        return Decision(ALLOWED, "allowlist", "always_allow rule")

    # 4. gate-mode ladder, composed with the base verdict.
    mode = _resolve_mode(event, ladder)
    verdict, reason = _apply_mode(mode, base, event)
    escalation_id = _escalation_id(event) if verdict == ESCALATE else None
    return Decision(verdict, mode, reason, escalation_id=escalation_id)


# ---------------------------------------------------------------------------
# The pure clock seam (deterministic default; real-clock impl is injected later)
# ---------------------------------------------------------------------------
Clock = Callable[[], str]


class CounterClock:
    """A deterministic, pure default clock — never reads the wall clock."""

    def __init__(self) -> None:
        self._n = 0

    def __call__(self) -> str:
        self._n += 1
        return f"t{self._n}"


# ---------------------------------------------------------------------------
# The overlay — a decorator over any RunnerBackend
# ---------------------------------------------------------------------------
class AuditOverlayBackend(RunnerBackend):
    """Wrap an inner :class:`RunnerBackend`; attest each step to a hash-chained spine.

    The inner backend does the real provision/run/collect/teardown work; this
    overlay classifies each step and ``append``s an evidence record (bound to the
    handle's ``policy_sha``) to a per-handle in-memory chain via the merged G-1.3a
    substrate. ``collect`` folds the spine chain into the returned
    :class:`CollectedEvidence`. A clean run satisfies ``verify_chain(chain) == []``.

    Registers no ``isolation_backend`` and no validator check; it is composed
    around an existing backend (e.g. ``AuditOverlayBackend(GvisorProxyBackend())``).
    """

    def __init__(self, inner: RunnerBackend, clock: Clock | None = None) -> None:
        self._inner = inner
        self._clock: Clock = clock if clock is not None else CounterClock()
        self._chains: dict[str, list[dict[str, Any]]] = {}
        self._policies: dict[str, dict[str, Any]] = {}
        #: A composed key; the overlay itself is not registered under it.
        self.backend_key = f"audit-overlay[{getattr(inner, 'backend_key', '?')}]"

    # -- attestation helpers -------------------------------------------------
    def _emit(self, handle: ProvisionedHandle, phase: str, classification: str) -> dict[str, Any]:
        chain = self._chains.setdefault(handle.ref, [])
        body: dict[str, Any] = {
            "kind": RECORD_KIND,
            "record_type": "runtime_evidence",
            "schema_version": "1",
            "policy_sha": handle.policy_sha,
            "run_id": handle.run_id,
            "lifecycle_phase": phase,
            "classification": classification,
            "recorded_at": self._clock(),
        }
        inner_key = getattr(self._inner, "backend_key", "")
        if isinstance(inner_key, str) and inner_key:
            body["backend_key"] = inner_key
        record = append(chain, body)
        chain.append(record)
        return record

    def chain(self, handle: ProvisionedHandle) -> tuple[dict[str, Any], ...]:
        """Return the (ordered) evidence chain attested for ``handle``."""
        return tuple(self._chains.get(handle.ref, ()))

    def observe(self, handle: ProvisionedHandle, event: Any) -> dict[str, Any]:
        """Classify a concrete runtime ``event`` against the attested policy + record it.

        This is how a (future, deferred) live event tap feeds the overlay: the
        event is classified against the exact policy provisioned for ``handle``,
        and the verdict is attested into the hash chain.
        """
        policy = self._policies.get(handle.ref, {})
        classification = classify(event, policy)
        phase = getattr(event, "phase", "run")
        return self._emit(handle, str(phase), classification)

    def _emit_action(
        self, handle: ProvisionedHandle, event: AgentActionEvent, decision: Decision
    ) -> dict[str, Any]:
        """Append a ``runtime_agent_action`` record (the event + the verdict) to the chain."""
        chain = self._chains.setdefault(handle.ref, [])
        body: dict[str, Any] = {
            "kind": RUNTIME_AGENT_ACTION_RECORD_KIND,
            "record_type": RUNTIME_AGENT_ACTION_RECORD_TYPE,
            "schema_version": "1",
            "policy_sha": handle.policy_sha,
            "run_id": handle.run_id,
            "recorded_at": self._clock(),
            "op": event.op,
            "mutation_class": event.mutation_class,
            "target": event.target,
            "tool": event.tool,
            "fidelity": event.fidelity,
            "timing": event.timing,
            "classification": decision.verdict,
            "decision_mode": decision.mode,
            "decision_reason": decision.reason,
        }
        if decision.escalation_id is not None:
            body["escalation_id"] = decision.escalation_id
        record = append(chain, body)
        chain.append(record)
        return record

    def observe_action(self, handle: ProvisionedHandle, event: AgentActionEvent) -> dict[str, Any]:
        """Decide on a concrete agent action against the attested policy + attest the verdict.

        The per-action analogue of :meth:`observe`: it runs the deterministic
        :func:`decide` control-point against the exact policy provisioned for
        ``handle`` and appends the fidelity-tagged ``runtime_agent_action`` record
        (allow/deny/escalate alike) to the same tamper-evident hash chain. The
        live action *source* (an ACP / CC-hook / transcript tap) is the adapter
        seam; here the event is a value (cf. :mod:`..cc_hook_adapter`).
        """
        policy = self._policies.get(handle.ref, {})
        decision = decide(event, policy)
        return self._emit_action(handle, event, decision)

    # -- the wrapped RunnerBackend lifecycle ---------------------------------
    def _provision(self, request: ProvisionRequest) -> ProvisionedHandle:
        # The RunnerBackend.provision template method already validated the record
        # (deny surface) before delegating here; the inner backend's provision()
        # re-applies the same guard, so a returned handle means the policy
        # validated clean → the provision is allowed.
        handle = self._inner.provision(request)
        if isinstance(request.runtime_policy, dict):
            self._policies[handle.ref] = request.runtime_policy
        self._emit(handle, "provision", ALLOWED)
        return handle

    def run(self, handle: ProvisionedHandle, request: RunRequest) -> RunResult:
        result = self._inner.run(handle, request)
        self._emit(handle, "run", ALLOWED)
        return result

    def collect(self, handle: ProvisionedHandle) -> CollectedEvidence:
        inner_evidence = self._inner.collect(handle)
        self._emit(handle, "collect", ALLOWED)
        spine = self.chain(handle)
        return CollectedEvidence(
            handle_ref=inner_evidence.handle_ref,
            records=tuple(inner_evidence.records) + spine,
            note=f"audit-overlay attested {len(spine)} spine record(s); inner: {inner_evidence.note}",
        )

    def teardown(self, handle: ProvisionedHandle) -> TeardownResult:
        self._emit(handle, "teardown", ALLOWED)
        result = self._inner.teardown(handle)
        self._policies.pop(handle.ref, None)
        return result
