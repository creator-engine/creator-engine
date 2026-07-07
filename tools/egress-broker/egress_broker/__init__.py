"""ADR-0007 egress gateway / publish broker — deterministic v0.

A **non-agent, deterministic** host-side broker that couriers a contained CE seat's
*signed* commit to the forge under fail-closed policy, attributed to the seat's OWN GitHub
App. It is the incremental, build-now path toward the full ADR-0007 egress gateway: it
replaces the manual uncontained-controller courier with an auditable, policy-gated,
deterministic enforcer — the only thing ADR-0007 trusts to hold forge egress, *because it
cannot be talked into misusing the credential.*

This package is **host-side operational tooling**, NOT validator logic: it is deliberately
NOT part of the installable ``creator-engine-validator`` package and registers no validator
check. It composes the existing, frozen forge primitives (``forge.app_jwt_runner`` mint
seam, ``forge.scoped_token`` least-privilege mint, ``forge.change_push`` never-force push,
``forge.credential_runner`` env-only credential injection) and adds the genuinely new v0
pieces: a pure fail-closed policy core, host-side commit-fact extraction, per-App
installation-id discovery, a per-App config schema, an append-only audit, and the
verify→mint→push→PR orchestration.

Fail-closed is the law: deny on ANY verification doubt. See ``policy.py`` (the TCB heart)
and ``docs/architecture/egress-broker.md`` for the ADR-0007 mapping and what is deferred to
the full gateway (OpenBao JIT PEM custody, OpenShell supervisor integration, the
contained-controller endgame).

Defensive only — couriers our own governed seat's signed, reviewed work through our own
forge under policy; never offensive (no force-push, no history rewrite, no detection
evasion, no credential exfiltration).
"""
from __future__ import annotations

from .host_broker import (
    handle_self_push_json_line,
    handle_self_push_request,
    serve_self_push_unix_socket,
    systemd_activated_unix_socket,
)
from .jit_credential import ModelCredential, SeatCredentialStore
from .orchestrator import ContainedSeatSelfPushRequest, contained_seat_self_push
from .policy import (
    BrokerPolicy,
    CheckResult,
    CommitFacts,
    Decision,
    Precondition,
    RateState,
    evaluate,
)

__all__ = [
    "BrokerPolicy",
    "CheckResult",
    "CommitFacts",
    "ContainedSeatSelfPushRequest",
    "Decision",
    "ModelCredential",
    "Precondition",
    "RateState",
    "SeatCredentialStore",
    "contained_seat_self_push",
    "evaluate",
    "handle_self_push_json_line",
    "handle_self_push_request",
    "serve_self_push_unix_socket",
    "systemd_activated_unix_socket",
]
