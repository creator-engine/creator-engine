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

## 6. DGX JOB-1: validation receipt tree-identity refusal

### 6.1 Recognize the refusal

Before Podman starts,
`validators/creator_engine_validator/validation_sandbox_runner.py::_derive_mounted_tree_sha()`
runs:

```text
git status --porcelain=v1 --untracked-files=all
```

Any output causes the runner to refuse receipt minting with:

```text
validation sandbox mounted tree must be clean before receipt minting
```

Treat this as a receipt tree-identity control, not as lint. The runner verifies
the mounted tree is clean before execution and includes the resulting `tree_sha`
in the signed receipt. A receipt is valid only when it names the exact tree that
was validated.

### 6.2 Refuse apparent bypasses

- Do not use `--allow-dirty` to work around this refusal. That option applies
  only to `pr_preflight._assert_clean_tree()`; it neither bypasses nor weakens
  the validation sandbox's L2 clean-tree requirement.
- Do not treat generated carriers as justification for weakening the control.
  Armed conveyor policy sets `allow_dirty_validation=False` and commits
  generated carriers before container validation. Carrier generation therefore
  cannot explain away a dirty mounted tree at receipt-minting time.

Do not blindly stash, reset, delete, or clean the worktree. Such actions can
erase an intended or safety-significant change and break the receipt chain they
are supposed to repair.

### 6.3 Resolve with seat-local evidence

This refusal remains unresolved when the diagnosing seats cannot reach the
allocated DGX worktree, its exact porcelain status, daemon and seat logs, or the
Podman/runsc/gvproxy substrate. Without that evidence, a dirty path cannot be
classified as stale generated output versus an intended or safety-significant
change.

Resolution requires DGX seat-local read and execute authority. The authorized
operator must:

1. Identify the exact allocated worktree and container mount.
2. Capture `git status --porcelain=v1 --untracked-files=all`, `HEAD`, and
   `HEAD^{tree}` before changing anything.
3. Capture the relevant daemon and seat logs and the Podman/runsc/gvproxy
   runtime state.
4. Classify every dirty path. Preserve and commit intended changes; remove only
   stale output supported by the captured evidence.
5. Rerun validation from the clean, classified tree and retain the resulting
   receipt evidence.

Under the ratified no-single-point-of-failure operating consequence, an
unexercised fallback is not a fallback. Until this procedure is completed and
the lane is exercised, DGX reduces nothing in host-loss risk despite eight
repair units.

That consequence does not make the lane needless. Current CI, static checks,
and dry runs do not prove live DGX arm64/runsc/gvproxy behavior. A narrowly
scoped, Operator-authorized DGX canary may therefore remain a genuine standing
need rather than sunk cost.
