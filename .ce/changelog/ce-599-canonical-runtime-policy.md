---
slug: ce-599-canonical-runtime-policy
date: 2026-07-18
kind: security
scope: canonical runtime-policy artifact and launch binding
issue: ce-ops#599
work_class: epic
---

**security(runtime): byte-pin the canonical controller-seat policy**

Adds the canonical controller runtime-policy source with independent semantic
and exact-byte digests, deterministic onboarding render and provenance receipt,
and fail-closed one-shot launch enforcement before runner side effects. Live
launches bind an immutable per-dispatch policy copy and recheck source, render,
receipt, registry, ownership, mode, and descriptor identity at the final
boundary. The slice does not provision seats, handle subscription credentials,
enable the deferred DGX venue, or perform any provider login or deployment act.

The production onboarding closure forwards the explicit canonical checkout
through both the console and live-driver paths, refuses held-backend reruns
while launchable gVisor evidence exists, and stages policy/receipt replacements
with recoverable last-known-good semantics across write and verification
failures.

Canonical launcher-registry bytes, runtime-policy source bytes, and semantic
identity are now preflighted and captured before the apply lock or live-driver
selection. Runtime provisioning reuses that immutable binding, so a missing,
malformed, stale, or mismatched explicit checkout refuses without state writes
or host-tool mutation and is never retrusted from a later checkout read.
Direct base and live production-driver calls enforce the same admission for
gVisor at their first instruction, before runtime-directory creation or
pinned-tool ensure. Held os-native and OpenShell provisioning never reads or
emits canonical policy material, including from an installed console outside a
source checkout, while still refusing stale gVisor evidence before posture
mutation. Focused coverage includes the complete live-driver module and proves
invalid direct gVisor checkout roots leave both runtime state and host tools
untouched.

Reconciles the canonical brain ledger through the governed accepted-plan
mechanism after the docs-reconciliation evidence changed, superseding the stale
static-evidence record with its newly hashed replacement. The append-only
supersede pair raises the intentional flat active-assertion ratchet from 120 to
121.
