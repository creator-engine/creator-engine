# BRIEF — dev-4 — 2026-07-07 ~20:3xZ — 1 unit: ce-ops#491 slice 2 = Option A merge-time intent materialization (hard unit)

You built slice 1 (the fail-closed stale-tail gate, merged as PR #882) — this is the
documented next slice. Ticket substance embedded (you cannot read ce-ops). COMMIT-ONLY
(ledger/gate-adjacent): when done signal `READY <branch> <sha> <evidence-path>`; the
controller harvests. Worktree: fresh /var/tmp checkout off origin/main.

## U1 — branch `ce-491-optiona-merge-intent` (declare work class honestly; likely M/feature)

CONTEXT (on main already): #882 added the tail-freshness gate — a PR whose
assertions.yaml delta chains from a stale tail is REFUSED fail-closed, which serializes
concurrent brain-append PRs behind zero drift. That conservatism is disclosed slice-1
intent. Your own design doc for slice 1 (docs/design/ce-491-ledger-append-serialization-slice1.md
on main) documents Option A as the follow-on: materialize the append INTENT at merge
time instead of refusing.

GOAL: implement Option A — a PR carries its brain-ledger append as a declarative
INTENT (not a pre-chained record); at merge/integration time the gate-side machinery
re-chains the intent onto the LIVE tail deterministically, so concurrent brain-append
PRs no longer serialize behind zero drift, while every invariant slice 1 protects
(chain linkage integrity, fail-closed on unprovable tail, no silent pass) is preserved.
Follow your slice-1 design doc's Option A section as the spec; where it is silent,
choose the conservative fail-closed reading and note the choice in the evidence file.

HARD INVARIANTS (from the ratified slice-1 review):
- The #882 gate stays intact for non-intent (legacy pre-chained) deltas — no loosening.
- Intent materialization must be deterministic and idempotent (re-running the merge
  step on the same intent + same live tail yields byte-identical records).
- Unprovable live tail at materialization time = fail-closed refusal, never a guess.
- Teaching-quality refusal messages, consistent with the `ce brain assert`/`ce brain
  correct` vocabulary slice 1 established.

TERRITORY NOTE: your #488 memory-layer branch is mid-harvest and may merge while you
build; it touches brain runtime/append modules. Base on the FRESHEST origin/main when
you start, and re-fetch + rebase onto freshest main before your final validation pass.
dev-3 is concurrently adding append-only TESTS in #882's test module — expect at most
trivial test-file rebases at harvest.

EVIDENCE: carrier slug==branch, self-inclusive, honest `- **Declared work class:**`
line; changelog fragment `.ce/changelog/ce-491-optiona-merge-intent.md`; evidence
summary with test counts including NEW tests proving: concurrent-intent PRs both land
without manual re-chain; determinism/idempotency; fail-closed unprovable-tail path.

Standing preflight directive (ce-ops#303): run the FULL local validator preflight
(`ce validate-pr`, CI-parity) before commit-for-harvest; do not discover gates via CI.

STOP LINE: no pushes, no PRs, no gate acts, no signing, no files outside the brain/
ledger/gate seam + its tests + changelog/carrier. If the design doc's Option A section
is too thin to implement without inventing policy, STOP and signal BLOCKED-DESIGN with
the specific open question — do not improvise governance semantics.
