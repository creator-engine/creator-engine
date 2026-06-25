---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0007
title: "Egress gateway / publish broker — the push path when every agent is contained"
status: proposed
date: 2026-06-20
decision_makers: ["ce-gate-architect"]
consulted: []
informed: []
review_by: 2026-12-20
mutation_class: governance
evidence_refs:
  - kind: issue
    ref: "ce-ops#128 — every-agent-contained program (controllers under governed substrate)"
    tag: containment-program
  - kind: issue
    ref: "ce-ops#135 — OpenBao dedicated secret-store micro-unit (physical segregation fast-follow); the secret-zero broker (W3) landed against it as PR #281. The secret-side twin."
    tag: secret-broker
  - kind: adr
    ref: "docs/decisions/0005-openbao-secret-identity-backend.md (SecretIdentityBackend)"
    tag: openbao-backend
  - kind: doc
    ref: "Session 2026-06-20: commit-and-signal via uncontained dev-2 courier; PR #280; dev-3 ce-ops credential-scope finding (#137)"
    tag: session-evidence
---

# Egress gateway / publish broker — the push path when every agent is contained

## Context and Problem Statement

A CE controller executing a ticket runs a chain whose links carry *different*
identities: **author** (who wrote/signed the commit) ≠ **push transport** (the
credential that uploads) ≠ **merge** (the gated act). Today a contained agent
(e.g. dev-4) authors + commits + signs locally but cannot push (no credential,
no egress, governance hook denies it), so an **uncontained controller** (today
dev-2) acts as courier: it takes the signed commit and pushes/opens the PR
("commit-and-signal"). The every-agent-contained endgame (#128, a roadmap milestone
critical path) contains **every** agent including controllers — which removes
the last uncontained courier. So: when no agent may push, *what* pushes?

## Decision Drivers

- Containment doctrine: no probabilistic, prompt-injectable LLM agent may hold
  forge egress (`ce-mandatory-containment-decision`, `ce-governed-seat-cannot-push`).
- The conserved CE separation: author ≠ transport ≠ merge.
- Minimize the trusted computing base (TCB) to a small, auditable surface.
- Must compose with the OpenBao broker (#135) and OpenShell supervisor/gateway.

## Considered Options

1. **Keep an uncontained "publisher" controller** (status quo stopgap) — leaves
   one prompt-injectable agent holding egress; contradicts #128.
2. **Give each contained agent its own push credential under tight policy** —
   policy enforced *inside* a probabilistic agent is unsound; an LLM with a
   credential is exactly what containment forbids.
3. **Egress gateway / publish broker (chosen)** — a **non-agent, deterministic
   policy enforcer** is the sole holder of forge egress and the push credential.

## Decision Outcome

Chosen option: **3 — the egress gateway / publish broker.** Push/PR/merge egress
leaves the agent layer entirely and moves to a deterministic gateway (the
OpenShell **supervisor/gateway** layer). Flow when all agents are contained:

1. Contained agent authors + commits + **signs** locally; its signing key is
   delivered just-in-time from **OpenBao** (#135) — nothing standing on disk.
2. It **signals** the signed artifact (branch + SHA / commit object) to the
   gateway over a controlled channel — a handoff, not a push.
3. The gateway **verifies before transmitting**: signature valid + author is an
   authorized identity; target is an allowed branch namespace (never
   direct-to-main); ratification/CI preconditions present; within rate/scope.
4. On pass, the gateway **pushes + opens the PR** with *its own* credential
   (also OpenBao-custodied, never seen by any agent). Authorship travels with
   the signed commit ("`ce-dev-N` authored, Verified · gateway pushed").
5. **Merge** is the same shape, actuated only when the ratification record +
   peer review + green CI are all present.

This is the **network-egress twin of the OpenBao secret broker**: the broker
stops agents *holding* secrets; the gateway stops agents *reaching* the forge.
Both anchor in OpenBao. The human (Operator) remains the **ratifier, never the
courier** — "automate the push, human-gate the ratify" taken to its limit.

The key safety claim: a deterministic gateway is trustable with the credential
*because it cannot be talked into misusing it*, where an LLM agent cannot. So
"every agent contained" shrinks the TCB from N reasoning agents to one auditable
enforcer — which *is* the point of the program.

## Consequences

- Good: unblocks every-agent-contained incl. controllers (#128); shrinks the TCB
  to one deterministic component; clean author/transport separation with a
  signed-authorship audit anchor; aligns with the OpenShell supervisor/gateway.
- Good: justifies per-dev **own Apps even for never-pushing contained agents**
  (e.g. `ce-forge-dev-4`) — identity/sign is the App's job, push is the
  gateway's; PEMs custodied in OpenBao.
- Trade-off: the gateway must be **built/adopted** (designed-not-built today);
  until then the dev-2-uncontained courier is the honest stopgap.
- Trade-off: the gateway becomes a **high-assurance component** — its compromise
  equals forge compromise → demands hardening, minimal surface, strong audit.
- Trade-off: adds a hop (agent → gateway → forge) and a signed-artifact handoff
  protocol to design and specify.
- Note: the UI / computer-use side (today's renames) is the analog — a mediated
  **browser** gateway (e.g. `ce-browser`) + human-in-loop for auth challenges —
  same "mediated egress through a controlled channel" pattern.
