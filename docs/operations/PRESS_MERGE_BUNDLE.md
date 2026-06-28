# Press-Merge Bundle

**Status**: proposed runtime and proposed schema, not frozen.
**Implementation**: `validators/creator_engine_validator/press_merge_bundle.py`.
**Schema**: `schemas/press-merge-bundle.schema.yaml`.

## Purpose

The press-merge bundle is a deterministic, content-hashed evidence surface for
one pull request head ref. It collapses the inputs an Operator normally reads
before pressing merge into one structured object and one Markdown rendering:
diff summary, test/CI roll-up, review evidence, and computer-use evidence where
present.

The bundle is evidence only. It carries no merge authority, does not ratify,
approve, enqueue, merge, deploy, mutate branch protection, or modify live
repository settings. `has_authority` is always `false`.

## Schema Decision

This change proposes a new `press-merge-bundle` schema instead of extending the
existing `evidence-fan-in-packet` schema.

Rationale: the fan-in packet is a generic local evidence index keyed by packet
id and evidence manifests. The press-merge surface is PR-keyed and needs
first-class sections for `diff_summary`, `test_results`, `review_evidence`, and
`computer_use_evidence`. Encoding those fields into the generic `evidence[]`
shape would hide the exact structure the Operator and downstream W1/W2 surfaces
need to inspect. The new schema mirrors fan-in's invariants instead: source
ratification reference, `has_authority: false`, deterministic `content_hash`,
and ref+sha evidence references.

The schema is proposed for Orchestrator sign-off; it is not a frozen governance
contract.

## Runtime Contract

`build_bundle(...)` is CLI-agnostic. It accepts PR/head-ref metadata, source
ratification, diff summary, test results, review-evidence refs, optional
computer-use refs, and an optional path-manifest carrier ref.

Before constructing output, the runtime verifies every evidence ref by `ref` and
`sha256` using the fan-in runtime's SHA helper. A missing ref or SHA drift is
refused fail-closed. Review evidence records are loaded only after their bytes
match the pinned SHA and must provide a verdict plus non-ratification statement.

The runtime reuses the fan-in runtime's canonical JSON serialization,
content-hash helper, SHA256 helper, schema version, and shared refusal classes
for equivalent authority, stale evidence, SHA mismatch, and missing
source-ratification failures.

`render_bundle(...)` is pure over the bundle object. It emits deterministic
Markdown with sections for PR/content hash, diff summary, test/CI roll-up,
review evidence, optional computer-use evidence, and a footer restating that the
bundle carries no merge authority.
