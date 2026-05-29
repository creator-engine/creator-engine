# Worker-Host Readiness

**Status**: Operational guardrail (additive). Describes when a host is ready to
run governed worker containers, and the preflight that MUST precede any
authorization of containerized worker lanes.
**Companions**:
`docs/operations/WORKER_CONTAINER_PROTOCOL.md` (substrate contracts),
`docs/operations/AGENT_NATIVE_BOOTSTRAP.md` (preflight),
`docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md` (`ce doctor` guard).

---

## 1. Why this document exists

CE ships a worker **substrate and runtime surface** (record schemas, refusal
predicates, the `ce worker` CLI, guarded rootless-Podman invocation construction,
and fail-closed behavior). That is not the same as a **host that can actually run
a worker container**. Conflating the two leads to authorizing containerized
worker work on a host where it cannot run — which CE then correctly refuses at
runtime (`G5-PODMAN-UNAVAILABLE`), but only after a plan has been built around a
false readiness assumption.

This document defines readiness levels and a hard preflight so that "ready" always
answers the question **ready for what?**

## 2. Operational Readiness Levels (ORL)

```text
ORL-0  Schema/docs only — record shapes, contracts, protocol prose exist.
ORL-1  Runtime/CLI substrate present; behavior proven against FAKE seams
       (PodmanCommandRunner / NullCredentialBroker); fails closed without Podman.
ORL-2  Host preflight passes: `ce doctor --require-worker` PASS (rootless Podman
       present and rootless; uid/gid subordinate mapping works).
ORL-3  Minimal LOCAL worker smoke test passes: no egress, no secrets, a benign
       pinned image; container starts and exits; instance record written.
ORL-4  A worker policy with a REAL pinned image digest is ratified and enforced
       (PCO-044 image_sha binding holds); no placeholder digests.
ORL-5  Networked/secret-bearing worker proven: an egress-enforcement primitive is
       proven (no G5-EGRESS-UNENFORCEABLE bypass) AND secret delivery is proven
       without leaking model-provider values or any controller key into
       argv / records / transcripts.
ORL-6  True multi-lane concurrency under CE governance (per-lane worktree, lease,
       and claim; a containerized worker lane runs concurrently).
```

A capability claim MUST cite its ORL and the evidence for it. "CE has workers" is
not a claim; "CE worker substrate is at ORL-1; this host is below ORL-2" is.

## 3. Hard preflight rule (the guardrail)

Before any prompt, handoff, envelope, or Controller action **authorizes**
`ce worker allocate`, `ce lane launch` for a containerized worker role, or a
containerized-worker concurrency test, the authorizing party MUST have observed,
in the target environment:

```bash
ce doctor --require-worker      # MUST exit non-zero-free: RED-G-3 = [ok], not [skip]/[FAIL]
```

Notes:

- Plain `ce doctor` is **not** sufficient evidence of worker readiness. It only
  `[skip]`s `RED-G-3` (`rootless-podman-worker`); the skip is **not** a pass.
  Only `--require-worker` evaluates `RED-G-3` as a hard clause.
- A containerized-worker authorization issued without this preflight is a
  governance defect, even if CE later refuses the allocation at runtime.
- If `ce doctor --require-worker` fails `RED-G-3`, the correct next step is host
  provisioning (see the host remediation runbook), **not** weakening isolation,
  and **not** an unisolated fallback launch.

## 4. What each readiness gap blocks

| Observed | Blocks | Correct response |
|---|---|---|
| `RED-G-3` FAIL (no rootless Podman) | ORL-2+; all containerized worker allocation | Provision rootless Podman (package + uidmap + subuid/subgid); re-run `--require-worker`. |
| Policy declares non-empty egress, no enforcement primitive | allocation (`G5-EGRESS-UNENFORCEABLE`) | Design + ratify an egress-enforcement primitive, or use a no-egress policy for ORL-3. |
| Policy image digest is a placeholder | ORL-4 ratification | Build/pin a real image digest (`sha256:<hex64>`); PCO-044 binds the instance to it. |
| No proven secret-delivery path | ORL-5 | Design + prove broker secret delivery with no leakage; never inject a controller key. |

## 5. Non-goals

This document does not install Podman, does not allocate workers, does not change
`ce worker allocate` behavior (which already fails closed correctly), and does not
ratify any policy. It is a readiness vocabulary and a preflight rule. Provisioning
and live-worker proofs are separate, Operator-ratified gates.
