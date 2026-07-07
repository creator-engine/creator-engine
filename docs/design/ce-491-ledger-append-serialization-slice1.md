# Ledger Append Serialization Slice 1

## Decision

Slice 1 ships the validator backstop, not merge-time materialization.

The mediated append direction remains the target: PRs should eventually carry
data-only append intents under a staging path such as
`.ce/brain/append-intents/<branch-slug>.yaml`, and a merge-closeout append
worker should materialize those intents onto the live `.ce/brain/assertions.yaml`
tail after merge admission. The repository already has a ratified mediated
append ADR and a worker skeleton for data-only intent validation, but wiring
that path through closeout policy, queue ownership, and merge evidence is larger
than a one-unit change.

This slice therefore adds a fail-closed PR preflight gate for the tracked
authoritative ledger. When a PR changes `.ce/brain/assertions.yaml`, local
preflight compares the ledger tail at the PR merge base with the ledger tail at
the freshly fetched live base. If the live base tail moved, the PR is refused
before expensive gates run. The refusal explains that the branch would re-chain
from a non-current tail and tells the author to rebase and re-run the brain
chain-producing commands on the current base.

## Evidence Driving the Cut

Two recent failure modes show why a warning is insufficient:

- append-vs-append: two branches append from the same ledger tail and produce a
  semantic fork even when Git can merge other files cleanly;
- stale mid-chain re-pin: evidence hash corrections can cascade new
  `content_hash` and `prev_hash` values from the edited record to the tail, so a
  branch computed on an old ledger becomes invalid after main advances.

Both are tail freshness problems from the PR author's view. The slice 1 guard
does not serialize writes, but it makes the failure impossible to miss and
prevents stale ledger bytes from continuing through PR validation.

## Deferred

- merge-closeout materialization from append intent files;
- mandatory mediation evidence for ledger-touching PRs;
- durable queue policy, daemon ownership, crash recovery, and closeout audit
  artifacts;
- conversion of existing direct ledger authorship workflows to intent files.
