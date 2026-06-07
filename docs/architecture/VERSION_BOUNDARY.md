# CE v1 ↔ v3 Version Boundary

**Status:** active contract (G-3.9). **Enforced by:** the `version_boundary` check
(`creator_engine_validator/checks/version_boundary.py`) against the taxonomy in
`creator_engine_validator/_versions.py`. **Directive:** CE v1.0 is **retained**; v1
and v3 **coexist** on a shared base — we operate on v1.0 to build v3.x, and v1.0 is a
shipped, working system. This replaces the spec §6 "deletion plan" with version
*coexistence/separation* (additive, not subtractive).

## Why this exists

CE ships, in one package (`creator_engine_validator`), **two coexisting product
versions** plus the shared governance engine they both rest on:

- **CE v1.0** — the `ce` launcher and its coordination/launch runtime (lane, PCO,
  tmux, hook pack, launch specs, the `ce` subcommand runtimes).
- **CE v3.x** — the agent-native execution runtime (orchestrator, run-assembly,
  forge adapters, runner backends, the evidence sink).
- **Shared governance engine / durable base** — the validator: its CLI, the check
  registry, every check, plus `loader`/`reporting`/`schema`/`environment_guard`/
  `version` and the pure `runtime_evidence_spine` substrate.

The two **execution runtimes** must stay independently-operable (so v1 can be used to
build v3, and so either can later be operated or extracted on its own). The boundary
that guarantees this already held on `main @ ab482ee`; this contract **declares and
guards** it so it cannot silently regress as v3 grows.

## The taxonomy (`_versions.py`)

Every shipped module is classified into exactly one **version line**: `v1`, `v3`, or
`shared`. The two runtime surfaces are enumerated explicitly (`V1_RUNTIME`,
`V3_RUNTIME`); everything else — the validator engine and durable infra — is `shared`.
Counts on `main`: **v1 = 21, v3 = 18, shared = 51** (90 shipped modules).

### Deliberate boundary calls
A few modules straddle and were classified deliberately:

| module | line | rationale |
|---|---|---|
| `runtime_evidence_spine` | **shared** | a pure, dependency-free cryptographic chain substrate, already reused by a shared check (`ce_runtime_evidence`) *and* by v3 — it belongs in the durable base |
| `evidence_sink` | **v3** | imports `runner.backend` (v3) and is consumed only by the v3 `orchestrator`/`run_assembly`; part of the v3 execution path, not version-neutral |
| `environment_guard` | **shared** | the env/packaging-contract guard is durable infra (design §2 infra-spine); its single edge into v1 is allowlisted (below), not reclassified |

## The invariant

The `version_boundary` check enforces, against the **actual** intra-package import graph:

1. **HARD — runtime ⊥ runtime.** No `v1` module imports a `v3` module, or vice-versa.
   No allowlist, no exceptions. (`VAL-VERBND-CROSS`)
2. **RATCHET — `shared` → version is allowlisted only.** A `shared` module may import a
   version-specific module **only** via a baselined, justified entry in
   `BASELINE_SHARED_TO_VERSION_ALLOWLIST`. New `shared`→version edges fail; the
   allowlist only ever shrinks. (`VAL-VERBND-SHARED-EDGE`)
3. **INTEGRITY / COMPLETENESS.** A module may not be declared in both runtime surfaces
   (`VAL-VERBND-OVERLAP`); a declared runtime module must still exist
   (`VAL-VERBND-MISSING`); an allowlisted edge that no longer exists is reported as a
   warning so the floor can be tightened (`VAL-VERBND-STALE-ALLOW`).

`shared` may always be imported by anyone — it is the base both versions sit on.

## The baselined allowlist (ratchet floor)

Derived from the full import graph on `main @ ab482ee`. These are the **only** permitted
`shared`→version couplings; the ratchet prevents new ones.

| edge | line | justification |
|---|---|---|
| `cli → hook_check` | shared → v1 | the unified validator CLI hosts v1 launcher subcommands (lazy import). The v3 CLI arrives at **G-7** as a *distinct* entry point — never by mutating this one. |
| `cli → pco_allocator` | shared → v1 | as above: the validator CLI hosts v1 PCO subcommands (lazy import) |
| `environment_guard → packaging_runtime` | shared → v1 | the shared env/packaging-contract guard reuses the v1 packaging-contract types; a candidate for extraction into a shared packaging-contract module |

There are **zero `shared`→`v3`** entries — the deliberate calls above keep the durable
substrate out of the allowlist.

## What this is *not*

- **Not a deletion.** Nothing in the v1 surface is removed. The modules the spec §6
  "deletion plan" once marked for excision are simply **labeled `v1` and retained**.
- **Not physical sub-packaging.** Logical separation now (registry + marker + guard +
  docs, zero code moves); physical sub-packaging (`v1/`, `v3/`, `common/`) is deferred
  to **G-7** and only if the logical boundary proves it worth the churn.
- **Cleanup = orphaned-only.** Any future removal is restricted to code proven dead to
  **both** versions — a separate, separately-justified pass, never the version-bearing
  machinery.

## Adding code

- Put new code in the version line it belongs to. If it is genuinely shared, leave it
  `shared` (the default for anything not in a runtime surface).
- **Do not** import across the v1⊥v3 boundary. If you find you need to, the design is
  wrong — raise it.
- **Do not** add a `shared`→version import. If one is truly unavoidable, decouple first;
  only if justified, add a baselined allowlist entry **with a rationale** and expect it
  to be challenged in review. The allowlist is a floor that shrinks, not a parking lot.
