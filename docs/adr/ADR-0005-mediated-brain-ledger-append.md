# ADR-0005 — Mediated brain ledger append

- **Status:** Ratified (Operator, 2026-07-06, day-arc D3 batch ratification).
- **Date:** 2026-07-05
- **Gate:** Brain ledger append serialization design.
- **Mutation class:** docs/governance documentation only. This ADR changes no
  ledger schema, no validator behavior, no merge-gate behavior, no broker
  behavior, and no `.ce/brain/**` content.
- **Authority basis:** mediated brain-append ADR task brief,
  SHA256 `131de51703af7695d1e0949f3db4f870715d3d99d2a07bdeb2d9e435dc7159d6`.

> This ADR proposes the design direction for serializing writes to
> `.ce/brain/assertions.yaml`. It does not implement a daemon, lock, rebase bot,
> schema change, or ledger mutation.

---

## 1. Context

`.ce/brain/assertions.yaml` is the tracked Knowledge-SSOT assertion ledger. It
is append-only and hash-chained: each appended record occupies the next
`sequence`, names the previous record's `content_hash` as `prev_hash`, and
contributes its own `content_hash` to the next record. Two concurrent writers
that both append from the same ledger head collide on chain position even when
their semantic assertions are unrelated. The loser must rebase, recompute
`sequence`, `prev_hash`, and downstream `content_hash` values, and rerun ledger
validation before the branch can land.

The current mitigation is out-of-band coordination. Seats use territory claims
or explicit completion-worker serialization to avoid two branches editing the
ledger at once. That is workable for rare writes, but it stops scaling as the
memory-to-brain migration and Knowledge SSOT work increase the
number of controllers and contained seats producing brain assertions.

Recent evidence shows the scaling limit:

- On 2026-07-02, one seat's ledger write was scoped out of a PR because another
  branch held the ledger. The resolution was manual loser-rebases-and-recomputes
  chain handling.
- On 2026-07-05, ce-411 needed an `assertions.yaml` supersede appended
  controller-side and was manually serialized by a single completion worker to
  avoid a chain-position collision.
- On 2026-07-05, ce-452 needed the same controller-side manual serialization.
  Together with the 2026-07-02 incident, this was the third manual
  serialization event that week. Later on 2026-07-05, PRs #838, #835, and #836
  produced a three-way chain-position collision — the 0.3.1 release branch and
  two completion PRs each re-chained in locked order — while PR #843 required a
  further branch recompute; counting the day's earlier incidents, 2026-07-05
  alone required five serialized ledger interventions.

The Phase B multi-coordinator ADR is separately designing write-authority
partitioning. This ADR does not preempt that partitioning decision; it defines
the smallest mediated append direction that can reduce chain collisions while
remaining compatible with later authority partitioning.

## 2. Invariants any mediated path must preserve

The ledger remains append-only. A mediated path must never mutate existing
records, reorder existing records, drop records, or weaken validation into a
warning. The old ledger must remain an exact prefix of the new ledger.

Each append must preserve chain mechanics:

- appended `sequence` values are contiguous from the current ledger length;
- the first appended record's `prev_hash` equals the current head
  `content_hash`, or the genesis hash for an empty ledger;
- each following appended record's `prev_hash` equals the previous appended
  record's `content_hash`;
- all content hashes are recomputed over the final canonical bytes.

The duplicate-ID and tombstone invariants introduced by ce-411 must also hold
through mediation. A new active assertion must not duplicate an existing active
assertion ID. A supersede must append the required tombstone-plus-active pair:
the tombstone preserves the prior record content except for chain and supersede
fields, marks the prior assertion `superseded`, points `superseded_by` at the
replacement active ID, and is followed by an active replacement whose
`superseded_by` is empty. The supersede chain must not cycle, must not point at
missing IDs, and must not leave active-count accounting inconsistent.

These invariants are authority boundaries, not implementation details. Any
daemon, bot, or lock that cannot prove them fail-closed is not eligible to write
the tracked ledger.

## 3. Option A — queue-daemon-mediated append

In this model, writers submit proposed append records as data. A
brain-append daemon serializes accepted submissions against the current ledger
head, assigns final `sequence` and `prev_hash` values, recomputes
`content_hash`, validates the whole ledger, and emits the tracked
`.ce/brain/assertions.yaml` change plus the associated carrier evidence.

Against gate-singleton doctrine, this should not be merged into the existing
merge-gate queue daemon by default. The merge gate is already the policy
singleton for harvest, validation, push, PR, and merge-adjacent authority.
Brain append serialization is a narrower state-mutation service over one
append-only ledger. Reusing the merge gate's process would overload its mandate
and couple ledger availability to merge-gate health. The recommended topology
is a separate brain-append daemon with an explicit contract to the merge gate:
the merge gate may require its evidence before accepting ledger-touching PRs,
but it is not itself the append allocator.

Containment fits this option if contained seats submit append intent through a
brokered channel rather than host filesystem access. The submission can travel
as PR data, a carrier artifact, or an existing egress-broker-style seam; the
seat supplies untrusted assertion content and metadata, while the daemon owns
the tracked checkout, ledger head, chain position, and final write.

Crash behavior can be fail-closed. The daemon should stage intent durably,
write the ledger only after validating the fully materialized result, and leave
no partial tracked ledger mutation on crash. A submitted intent that was not
committed to a validated ledger head remains pending or rejected with evidence;
it must not be half-applied.

This option best preserves append-only invariants because one writer owns final
chain assignment. It also gives ce-411 duplicate-ID and tombstone checks one
mandatory enforcement point before bytes enter the tracked ledger.

## 4. Option B — merge-queue-native resolution

In this model, normal PRs continue to edit `.ce/brain/assertions.yaml`.
When the merge queue detects a chain collision, a bot rebases the loser,
recomputes `sequence`, `prev_hash`, and `content_hash`, and updates the branch.

Against gate-singleton doctrine, this keeps all authority in the merge gate and
avoids introducing a new daemon. That is attractive, but it turns the merge
gate into an editor of authored ledger bytes. The gate must understand every
valid append and supersede shape, decide which branch loses, rewrite commits,
and prove that it did not change semantic assertion content. That is broader
than queueing and validation.

Containment is simple for seats because their proposed append already exits as
PR data. The downside is that conflict resolution happens late, after a branch
exists and CI/review may already have reasoned about pre-rebase bytes.

Crash behavior is mixed. A failed rebase bot can fail closed by leaving the PR
unmerged, but it can also strand branches in partially updated states unless
branch updates are atomic and audited. Reviewers must be able to distinguish
semantic assertion changes from mechanical chain rewrites.

This option can preserve append-only and ce-411 invariants, but only if the
merge bot becomes a full ledger-aware rewriter. That is a larger Phase-1
surface than necessary and keeps the current friction until the queue collision
actually occurs.

## 5. Option C — claim/lock primitive on the ledger file

In this model, writers acquire a ledger-file claim or lock, reusing the
standup-lock A5 machinery. Only the lock holder appends
to `.ce/brain/assertions.yaml`; other writers wait or skip their append.

Against gate-singleton doctrine, this avoids adding write authority to the
merge gate. It also avoids a new append daemon. However, it does not mediate
the append itself; it merely serializes humans or seats before they perform the
same fragile manual operation.

Containment is weak unless the lock service is exposed through a brokered seam.
Contained seats have no host filesystem access, so a host-local lock file is
not sufficient. A lock acquired through PR comments or a broker still leaves
the contained writer responsible for producing correct final chain bytes
against a head that may change before merge.

Crash behavior is the main risk. Locks need leases, expiry, owner identity, and
clear stale-lock recovery. A crash while holding the lock must fail closed
without granting a second writer permission to append over uncertain state, but
overly conservative stale-lock handling recreates the current manual bottleneck.

This option reduces simultaneous edits but does not enforce duplicate-ID,
tombstone, or hash-chain correctness. It is useful as an interim coordination
aid, not as the mediated append primitive.

## 6. Decision proposal

Recommend Option A: a separate queue-daemon-mediated brain append service, not
a merge-gate extension and not a lock-only protocol.

The brain-append daemon should be a narrow singleton for final ledger writes.
It receives append intent as data, derives the current ledger head from a
daemon-owned checkout, assigns chain position, validates append-only and
ce-411 invariants, and emits a reviewable change. The merge gate remains the
policy singleton for merge admission and must require evidence that a
ledger-touching branch was produced by, or reconciled through, the append
daemon.

## 7. Minimal Phase-1 slice

The smallest shippable mediation is:

1. Define a data-only append-intent envelope for one active assertion append or
   one ce-411-style supersede pair. The envelope does not change the ledger
   record schema.
2. Add a controller/host-side brain-append worker or daemon that consumes one
   intent at a time from a durable queue, materializes the current
   `origin/main` ledger, assigns `sequence` and `prev_hash`, recomputes hashes,
   and runs existing ledger validation.
3. Emit only two kinds of outcomes: a committed carrier branch/patch with
   evidence, or a fail-closed refusal naming the violated invariant.
4. Require ledger-touching PRs in this class to carry mediation evidence, while
   leaving non-ledger PRs unchanged.

Phase 1 may use an existing egress-broker-style transfer or PR-data transfer to
carry the seat's intent out of containment. The important boundary is that the
contained seat never chooses host paths, final chain position, or final ledger
bytes.

## 8. Deferrals

This ADR defers:

- implementation of the daemon, queue storage, CLI, broker integration, and CI
  checks;
- the Phase B multi-coordinator authority partitioning decision;
- fleet-wide remote append APIs and multi-repository brain ledgers;
- merge-bot semantic rewrite support for arbitrary historical branches;
- a general lock-service design beyond any short-lived compatibility guard;
- changes to reviewer assignment, auto-merge, or merge-queue policy outside
  the evidence requirement for ledger-touching PRs.

Once the daemon ships, out-of-band ledger appends that bypass it are refused at
the merge gate for lack of mediation evidence.

## 9. Non-goals

- No implementation is authorized by this ADR.
- No ledger record schema change is proposed.
- No `.ce/brain/**` content is changed.
- No docs/contracts page is added or changed.
- No existing manual ledger append is declared invalid retroactively.

## 10. Consequences

- Brain ledger write authority becomes explicit and auditable instead of being
  hidden in manual completion-worker serialization.
- Contained seats can still propose assertions, but final chain assignment and
  validation move to a trusted mediator.
- Merge conflicts on chain position should fall sharply once ledger-touching
  work routes through the daemon.
- The system gains a small new singleton, so its availability, audit log, and
  fail-closed recovery path must be designed carefully before arming.
