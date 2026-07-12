# Checkpoint

Create a checkpoint only at a clean boundary. It records state; it grants no
authority and performs no forge, gate, approval, merge, signing, ratification,
or publish action.

## Refuse unsafe input

Do not copy secrets, credentials, tokens, private keys, or raw logs that may
contain sensitive data. Do not create a committed `READY` file. If a needed
fact exists only in unsafe material, record the fact as unavailable and name
the safe retrieval owner or source.

## Gather the delta

Read the prior checkpoint, if named. Capture only facts new or changed since it.
If there is no prior checkpoint, say so and treat the current durable state as
the baseline. Do not infer a missing fact.

Label every fact as one of:

- `probed`: directly checked from a named durable source during this session.
- `asserted`: reported by a person or worker and not independently checked.
- `unknown`: not safely available; name the next safe probe.

Capture this exact minimum set:

1. Active objective and the clean-boundary reason.
2. Exact lane and seat state, including each seat's role and whether it is live,
   idle, blocked, or complete.
3. Claims, territory, and conflicts; preserve one-face/two-key separation and
   worker-role boundaries. A checkpoint never transfers an authority or key.
4. Exact branch heads and bases for active worktrees.
5. Durable bundle, evidence, and log paths with SHA-256 values when available.
6. Validation, review, and gate state, including what is pending; never convert
   evidence into approval.
7. Blockers and every `AWAITING-OPERATOR` item.
8. Explicit authority boundaries and the next safe act for the receiving
   controller.
9. Any supplied arc stamp, autonomy rung, mandate digest, and issuer, marked
   `asserted` unless probed from a named durable source.

Do not copy a raw transcript. Summarize only the minimum safe fact and cite its
durable path.

## Write and verify

Write one untracked file under `.ce/state/research/` named
`RESUME_STATE_<UTC timestamp>.md`. Do not add it to Git.

Use this layout:

```md
# Resume state — <UTC timestamp>

Prior checkpoint: <path or none>
Boundary: <why this is clean>

## Delta
- [probed|asserted|unknown] <fact> — source: <named durable path or safe next probe>

## Work state
- Objective: <fact>
- Lanes and seats: <fact>
- Claims and territory: <fact>
- Heads and bases: <fact>

## Evidence and decisions
- Durable paths and SHA-256s: <fact>
- Validation, review, and gates: <fact>
- Blockers and AWAITING-OPERATOR: <fact>
- Authority boundaries: <fact>
- Arc/rung stamp: <fact or none supplied>

## Resume
Next safe act: <one action that needs no new authority>
Named durable sources to reload: <ordered paths only>
```

Run `sha256sum .ce/state/research/RESUME_STATE_<UTC timestamp>.md` and record
the digest in the checkpoint response. Do not say `/clear` occurred, is safe,
or is complete until the file exists and this hash has been verified.

### Structured command protocol

For a deterministic agent-facing invocation, place the labeled facts in a JSON
document conforming to
`validators/creator_engine_validator/schemas/checkpoint-input.schema.yaml`, then
run:

```text
ce checkpoint --facts <facts.json> --clean-boundary <reason> [--prior-checkpoint <path>] [--json]
```

The command consumes only this supplied document. It refuses secret- or
transcript-shaped fields, incomplete/ambiguous facts, unsafe roots, and tracked
targets before writing. A green result reports `path`, `sha256`, `complete`, and
whether it was idempotent; human and JSON forms carry the same result facts.
The caller may consider `/clear` only after independently verifying the exact
persisted bytes and terminal-green completeness result. The command neither
performs nor claims `/clear`.

## Completeness check

Before handoff, verify every item is present or explicitly `unknown`:

- [ ] Delta only; prior checkpoint named or absence stated.
- [ ] Objective, lane/seat state, claims/territory, heads/bases.
- [ ] Durable paths and SHA-256s.
- [ ] Validation, review, gate, blocker, and `AWAITING-OPERATOR` state.
- [ ] Authority boundaries, one-face/two-key and worker-role separation.
- [ ] Supplied arc/rung stamp or an explicit absence.
- [ ] One next safe act and an ordered named-source list.
- [ ] No unsafe material, raw sensitive logs, committed `READY` file, or side
      effect.
- [ ] Checkpoint file is untracked and its SHA-256 was verified.

## Resume procedure

1. Reload the applicable global policy, then repository policy, before acting.
2. Read the checkpoint and verify its recorded SHA-256.
3. Reload only the named durable sources in the recorded order.
4. Re-probe facts that were `unknown` or have become stale; retain asserted
   labels until independently checked.
5. Confirm authority boundaries before the next act. Escalate an
   `AWAITING-OPERATOR` item; do not treat the checkpoint as permission.
6. Continue with the recorded next safe act, or create a new checkpoint if the
   boundary changed.
