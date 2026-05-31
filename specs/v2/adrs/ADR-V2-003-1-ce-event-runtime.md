# ADR-V2-003-1: CE-event runtime

Status: Accepted for G2.003.1 draft (CE-event runtime; predecessor ADR-V2-003)

## Context

G2.003.0 (ADR-V2-003, PR #91, merged) landed the CE-event signed-block
substrate: the content-addressed, hash-chained block shape, the
`ce-event-block.schema.yaml` schema, the `ce_event_block` validator, the
well-formed/malformed examples, and the spec/sidecar text. That substrate is
deliberately write-free — it validates shape but emits nothing.

G2.003.1 must turn that substrate into an executable runtime: a local,
daemonless, network-free `ce event {sign,verify,append,replay,index}` surface
that produces and reads append-only event chains. It must do so without
weakening the Operator-only privileged floor, without introducing any
cryptography or key custody, and without writing live event state into the
frozen `.hermes/ce-events/` path.

A precursor problem also has to be solved in-slice: the canonical home for v2
event state is the instance-local `.ce/` zone, but the full G2.001.0 `.ce/`
namespace runtime (the `.gitignore` posture plus `ce init` creation) has not
landed. The runtime therefore needs the minimal additive ignore posture it
depends on.

## Decision

1. **Runtime, not a new validator.** G2.003.1 adds the
   `creator_engine_validator.ce_event_runtime` module and the `ce event` CLI
   group only. It registers no new check and changes no schema. Shape decisions
   are delegated to the already-landed `ce_event_block` validator: the runtime
   reuses the validator's canonical-hash function, role/mode enums, signature
   and write-freeze predicates, and per-chain block predicates verbatim, so a
   runtime-produced block is byte-for-byte the artifact the validator already
   accepts. A backward-compatibility canary asserts this on every test run.

2. **Append-only local chains under an ignored zone.** `append` writes one block
   per file plus a head manifest under `.ce/ce-events/spool/<stream>/`. The
   genesis block uses sequence 0 and a null parent hash; each later block takes
   the next monotonic sequence and links its parent hash to the current head
   content hash. Records are authored as deterministic stdlib JSON, mirroring
   the v1 Side-Effect Ledger and fan-in runtimes.

3. **Minimal, additive `.ce/` ignore posture.** A single additive `.gitignore`
   line ignores `.ce/ce-events/spool/`. The runtime refuses to write when that
   spool root is not git-ignored inside a repository, reusing the read-only
   `git check-ignore` guard pattern from the fan-in runtime. The change is
   deliberately minimal: it does not wholesale-ignore `.ce/` (governance
   subtrees must remain trackable) and does not pre-empt the full G2.001.0
   namespace gate.

4. **The privileged floor and signature reservation are preserved.** `ce event`
   may emit only canonical non-ratifying roles; `agent_ratifier` and `source`
   are refused. The signature mapping stays shape-only with value
   reserved-inactive, and a non-reserved value is refused. The runtime performs
   no signing, key custody, key rotation, distributed identity, or credential
   handling. Operating mode is recorded as context only; an unknown mode is
   refused and no mode is activated. Every refusal is raised before any write,
   so a refused call leaves the spool byte-identical. New refusal codes use the
   `G2-EVENT-*` family.

5. **A transport seam keeps the path testable and network-free.** The
   append/read path runs through an injectable transport whose default is the
   local filesystem ("git" = synced by ordinary git, not a CE network call), so
   the runtime is unit-testable with a fake and the default makes no network
   call. Network transports, distributed identity, PCL, the Integration Queue,
   connectors, and CI/deploy hooks are explicitly deferred.

## Consequences

- The Operator-only privileged floor is preserved in every mode; this ADR
  ratifies no floor relaxation, activates no elevated mode, binds no
  `agent_ratifier`, and introduces no cryptography or key custody.
- Runtime event state never reaches the tracked tree: all writes land under the
  ignored spool, so the canonical-branch diff carries no runtime state.
- Editing the `ce_cli.py` command surface makes the tracked offline wheelhouse
  wheel stale relative to source; the wheel is rebuilt and its checksum manifest
  refreshed as part of this slice's packaging contract.
- Future gates (G2.004.1 PCL runtime; distributed/signed emission) can build on
  a stable runtime surface without retrofitting block or chain semantics.

## Non-ratification statement

This ADR records a design decision for the PR candidate. It ratifies no future
runtime authority, no privileged-floor relaxation, no agent ratification, and no
cryptographic signing or key custody. The scoped authority is the
Operator-ratified G2.003.1 execution prompt recorded in the feature 003
`spec.ce.yml` `authority_basis`.
