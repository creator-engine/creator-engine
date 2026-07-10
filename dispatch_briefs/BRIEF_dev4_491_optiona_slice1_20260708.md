# BRIEF — dev-4 — 2026-07-08 — 1 unit: CE-491 Option A merge-time brain append intent materializer, Slice 1

This is the first implementation slice for the Option A merge-time brain append intent materialization design (ticket CE-491, merged design at `docs/design/ce-491-optiona-merge-intent.md`; complementary stale-tail backstop at `docs/design/ce-491-ledger-append-serialization-slice1.md`). No prior materializer slice exists. Role: **implementer**. You are a COMMIT-ONLY contained seat: when preflight is green, signal `READY ce-491-optiona-slice1 <commit-sha> .ce/pr-manifests/ce-491-optiona-slice1.md` in the pane. If blocked, signal `BLOCKED ce-491-optiona-slice1 <one-line reason>`. Worktree: `git fetch origin main` first, then create a fresh worktree at `/var/tmp/ce-491-optiona-slice1` off `origin/main`. Branch name is `ce-491-optiona-slice1`. Do NOT activate any venv.

## U1 — branch `ce-491-optiona-slice1` (declare work class honestly; likely story)

CONTEXT (CE-491 — ticket unreachable from seat; design summaries embedded):

The Option A design (`docs/design/ce-491-optiona-merge-intent.md`) replaces direct PR edits to `.ce/brain/assertions.yaml` with data-only append intents placed under `.ce/brain/append-intents/<branch-slug>.yaml`. After a PR lands in the merge queue, the merge-gate queue daemon materializes those intents onto the live ledger tail via a deterministic direct commit to `main`, under a narrow Operator-granted authority. The pre-existing ledger-append-serialization slice-1 design (`docs/design/ce-491-ledger-append-serialization-slice1.md`) shipped a fail-closed PR preflight gate (the stale-tail backstop) for legacy PRs that directly edit `.ce/brain/assertions.yaml`; that slice is complete and its gate remains in place unchanged. Option A is the mediated follow-on path explicitly deferred by that document. The two designs are complementary: the stale-tail gate guards direct-edit PRs; the new XOR gate (`brain_append_intent_xor_direct_ledger`) ensures PRs never carry both paths at once; the materializer handles intent-carrying PRs post-merge. Implementation slice 1 for Option A covers the materializer library in dry-run-only mode, the XOR gate validator check, and unit tests. Read both design documents in full before writing any code.

Existing code this slice builds on (all present on `origin/main`):
- `validators/creator_engine_validator/brain_append_worker.py` — intent loading, validation, and ledger-apply skeleton; materializer imports and extends this rather than duplicating its logic
- `validators/creator_engine_validator/brain_append_intent.schema.yaml` — intent schema (`kind`, `schema_version`, `intent_kind`, four payload blocks); the tracked schema already includes `decision_append` and `lesson_append` from PR #888
- `validators/creator_engine_validator/daemon_lease.py` — filesystem lease facility; materializer uses `daemon_lease.acquire` for the brain-append component lease; do not re-implement leasing
- `validators/creator_engine_validator/forge/automerge_actuator.py` — the merge-gate actuator context; the materializer's closeout flow sits conceptually adjacent to this daemon's accepted-merge stream

The materializer module belongs at `validators/creator_engine_validator/brain_intent_materializer.py` — adjacent to `brain_append_worker.py` (the brain worker skeleton it extends) and `daemon_lease.py` (the lease facility it imports). Do NOT place materializer code under `tools/` or create a new top-level package.

RATIFIED OPERATOR RULINGS (2026-07-08) — the seat cannot read the controller ledger; these rulings are embedded here and are authoritative:

- Q1 (authority scope): The queue daemon gets the narrow direct-commit-to-main materialization authority AS DESIGNED: arming separate; fail-closed holds; only `assertions.yaml` + consumed intent files; deterministic commits.
- Q2 (credential surface): Authority is carried by a DEDICATED NARROW GitHub App `ce-materializer` (App ID 4244593, installation 145152358, `contents:write` only, single-repo, ruleset always-bypass — ALREADY PROVISIONED). The implementation MUST read App credentials from config/env pointers, NEVER hardcode paths or embed key material. Arming (enabling live writes) is explicitly OUT of slice 1 scope.
- Q3 (quarantine placement): Quarantine artifacts go OUT-OF-BAND in the daemon state root, referenced from the PR comment — NEVER in-band on `main`.
- Q4 (topology): STRICT SINGLETON by deployment policy (efficient singleton + one-click IaC redeploy precondition — redeploy tooling already landed as `deploy/singleton-redeploy/`, PR #895).

GOAL: Implement Slice 1 as defined below. The design at `docs/design/ce-491-optiona-merge-intent.md` is the authoritative source. Where any brief text and the design conflict, the design wins; signal BLOCKED rather than resolve a conflict silently.

**SLICE 1 — IN SCOPE:**

New module `validators/creator_engine_validator/brain_intent_materializer.py` (pure stdlib only; `yaml` is available via the existing package; do not add third-party dependencies without recording the gap in the evidence file; do not import from `tools/`). Required internal structure:

- `ARMING_ENABLED = False` — module-level constant, hard-coded to `False`. Any code path that would construct a git commit object, push a ref, or write to `.ce/brain/assertions.yaml` or `.ce/brain/append-intents/` MUST raise `RuntimeError("materializer arming is disabled: slice 1 ships dry-run only")` when this constant is `False`. This constant MUST NOT be overridable by any config or env variable in this slice.
- `AUTHORIZED_WRITE_PATHS` — module-level frozenset or tuple naming the two path classes that future armed writes are bounded to: `.ce/brain/assertions.yaml` and paths under `.ce/brain/append-intents/`. Document this as a module-level constant so future slices have an explicit reference.
- `MaterializationKey` — dataclass or namedtuple holding `merge_commit_sha`, `intent_path`, `intent_sha256`, and `key_hex` (the 64-char hex digest). Compute as `sha256(merge_commit_sha + "\n" + intent_path + "\n" + intent_sha256 + "\n")` — exact byte sequence per the design. Provide a `compute(merge_commit_sha, intent_path, intent_sha256) -> MaterializationKey` constructor.
- `IntentDiscovery` — loads and validates an intent file at a given path; calls `brain_append_worker.load_intent` and re-validates the data-only contract (no `prev_hash`, `content_hash`, or any field in `brain_append_worker.POSITION_OR_HOST_FIELDS` present in the intent body); enforces path binding (the file stem, i.e. `Path(intent_path).stem`, must equal the `branch_slug`); computes `intent_sha256` as the SHA-256 of the canonical UTF-8 bytes of the file; produces a `MaterializationKey`. Raises `BrainAppendRefusal` on any violation.
- `LedgerTailProof` — given a repo root and git ref, loads `.ce/brain/assertions.yaml` from the live git tip (using a `GitRunner` callable identical to the one in `brain_append_worker.py`), parses it via `brain_runtime.load_ledger_text`, and returns the live tail record and its `content_hash`. On parse failure, chain break, or unreadable ledger raises `HeldError(reason="brain_ledger_tail_unprovable")`.
- `HeldError` — exception class with a `reason` string field. Valid reasons per the design: `brain_intent_materialization_failed`, `brain_ledger_tail_unprovable`, `brain_intent_partial_materialization`.
- `RecordBuilder` — accepts the validated intent data dict, the live tail `content_hash` (as `prev_hash`), and merge metadata (`merge_commit_sha`, `pr_number`, `branch_slug`, `materialization_key`). Calls `brain_append_worker._apply_intent` (or the equivalent internal `brain_runtime` functions) to produce the new ledger YAML bytes with `prev_hash` set from the live tail. Populates the `mediation` block on each appended record in the exact YAML field order specified in the design: `mode`, `intent_path`, `intent_sha256`, `intent_kind`, `merge_commit_sha`, `pr_number`, `branch_slug`, `materialization_key`, `materialization_record_index`, `materialization_record_count`. Record body MUST NOT contain: wall-clock timestamps, daemon PID, hostname, credential identifiers, retry counters, local filesystem paths, lease-holder identity, or `materialization_commit_sha`. Those may appear only in the commit trailer, PR comment, and daemon log — not in the record body. Verifies that re-running with the same inputs produces identical record bytes (determinism assertion in docstring).
- `DryRunOutput` — dataclass for the dry-run JSON artifact. Fields: `mode` (always `"dry_run"`), `status` (`"would_materialize"` | `"held"` | `"refused"`), `intent_path`, `intent_sha256`, `merge_commit_sha`, `would_append_records` (list of record dicts as `RecordBuilder` would produce), `would_remove_intent_path`, `materialization_key`, `ledger_tail_before`, `ledger_tail_after`, `refusal_reason`, `generated_patch_sha256`. Writes to `.ce/state/brain-intent-materializer/dry-run/<materialization-key>.json`. Creates parent dirs. Never writes to `main`.
- `QuarantineWriter` — writes out-of-band quarantine artifact to `.ce/state/brain-intent-quarantine/<materialization-key>.json`. Fields: `intent_path`, `intent_sha256`, `merge_commit_sha`, `validation_error`, `actor_version`, `timestamp`. Creates parent dirs. Never writes to any path that would be committed to the repository. Called whenever intent validation fails post-CI (malformed intent on main).
- `HeldStateStore` — persists held records at `.ce/state/brain-intent-materializer/held/<materialization-key>.json`; loads on restart. Fields per the design: `held_reason`, `materialization_key`, `intent_path`, `intent_sha256`, `merge_commit_sha`, `held_at_utc`. Creates parent dirs.
- `MaterializerLease` — thin wrapper around `daemon_lease.acquire` for the component named `brain-append`. The daemon state root for the lease is `.ce/state/brain-intent-materializer/leases/`. Module-level docstring MUST state: "Under multi-instance topology this local lease is not a correctness guard; correctness then requires an external linearizable lock with the same brain-append exclusion scope (Q4 ratified ruling)." In dry-run mode, the lease is acquired for the duration of the run and released on completion or error; no main mutation ever occurs while held.
- `MaterializerConfig` — dataclass for configuration. Required fields: `state_root` (path to `.ce/state/brain-intent-materializer/`), `quarantine_root` (path to `.ce/state/brain-intent-quarantine/`), `repo_root`, `app_id` (int, for future use, default `4244593`), `installation_id` (int, for future use, default `145152358`), `private_key_env` (str, env var name pointing to the App private key — never the key itself). The slice 1 implementation MUST NOT load or use `private_key_env` for any operation. Config must load fail-closed: missing required field raises `MaterializerConfigError`.
- `Materializer.run_dry(merge_commit_sha, intent_path, branch_slug, pr_number, config)` — the single public entry point for slice 1. Orchestrates in order: (1) acquire `MaterializerLease`; (2) call `IntentDiscovery` to load and validate the intent; (3) call `LedgerTailProof` to prove the live tail; (4) call `RecordBuilder` to produce deterministic record bytes; (5) write `DryRunOutput` JSON; (6) emit one event to the append-only JSONL daemon event log; (7) release the lease. On any `HeldError`: write `HeldStateStore` record, write `QuarantineWriter` artifact if reason is `brain_intent_materialization_failed`, emit a `held` event to the daemon log, release the lease, return `DryRunOutput` with `status="held"`. On `BrainAppendRefusal`: write quarantine artifact, emit `refused` event, release the lease, return `DryRunOutput` with `status="refused"`. The method MUST NOT construct a git tree, a git commit object, or call any push function.
- Append-only JSONL daemon event log at `<config.state_root>/materializer.jsonl`. One event per run, per hold, per quarantine. Required fields per event: `materialization_key`, `intent_sha256`, `merge_commit_sha`, `main_parent_sha` (the live tip resolved by `LedgerTailProof`; `null` if tail proof failed before resolution), `result_status`, `event_sha256` (SHA-256 of the JSON line bytes before the trailing newline). Clock must be injectable (`now: Callable[[], datetime] | None = None`) so tests are deterministic. Timestamps MUST be RFC 3339 UTC with trailing `Z`. Append-only: the file is opened with mode `"a"`; never truncated.

New module `validators/creator_engine_validator/brain_intent_xor_gate.py`:
- Implements the `brain_append_intent_xor_direct_ledger` hard gate.
- Public function: `check_xor(changed_paths: list[str]) -> list[ValidationError]`.
- Returns a hard error if `changed_paths` includes both at least one path matching `.ce/brain/append-intents/*.yaml` (or `.yml`) AND the path `.ce/brain/assertions.yaml`.
- Error code: `brain_append_intent_xor_direct_ledger`.
- Error message: `"PR carries both an append intent file and a direct .ce/brain/assertions.yaml edit; hybrid PRs are refused regardless of stale-tail status"`.
- Accepts only the list of changed path strings; requires no filesystem access and no git subprocess in the gate logic itself.
- Returns an empty list when only intent files are present, only assertions.yaml is present, or neither is present.

Unit tests in `validators/tests/unit/` (one module per concern; injectable adapters for all external I/O; no live git subprocess or live filesystem required beyond `tmp_path`):

- `test_brain_intent_materializer_key.py` — `MaterializationKey.compute` is stable: same inputs always produce the same 64-char lowercase hex key; different `merge_commit_sha`, `intent_path`, or `intent_sha256` each produce a different key; key is exactly 64 lowercase hex characters; the exact byte sequence fed to SHA-256 matches the design's formula.
- `test_brain_intent_materializer_validation.py` — `IntentDiscovery`: valid intent accepted and `intent_sha256` computed; branch slug mismatch between path stem and `branch_slug` arg refused with `brain_append_intent_schema` or a dedicated code; intent carrying `prev_hash` or `content_hash` refused; intent carrying any `POSITION_OR_HOST_FIELDS` field refused; unknown `intent_kind` refused; malformed YAML refused; all four valid `intent_kind` values accepted; data-only contract confirmed.
- `test_brain_intent_materializer_core.py` — `RecordBuilder`: same inputs produce byte-identical record YAML on every call (determinism); `mediation` block present with all required fields in the exact order specified in the design; record body absent of wall-clock timestamps, PID, hostname; `materialization_record_index` / `materialization_record_count` correct for single-record (`active_assertion_append`) and two-record (`ce411_supersede_pair`) cases; `content_hash` in each produced record matches the expected chaining rule; `prev_hash` on the first appended record equals the live tail `content_hash`.
- `test_brain_intent_materializer_hold.py` — `HeldStateStore.write` and `HeldStateStore.load` round-trip for all three hold reasons; malformed intent produces `QuarantineWriter` artifact at `.ce/state/brain-intent-quarantine/<key>.json` and NOT at any path under `.ce/brain/`; quarantine artifact fields match the design; HELD with `brain_ledger_tail_unprovable` produces no dry-run output and no ledger bytes; `HeldError` reason surfaces in `DryRunOutput.refusal_reason`.
- `test_brain_intent_materializer_lease.py` — `MaterializerLease` calls `daemon_lease.acquire` for component `brain-append`; a second acquisition attempt while the first lease is held raises `DaemonLeaseHeld`; lease releases on context exit or explicit release; module docstring text includes the Q4 singleton-caveat sentence (test reads the docstring).
- `test_brain_intent_materializer_dryrun.py` — `Materializer.run_dry` produces dry-run JSON at the correct path; `mode` field is `"dry_run"`; `status` is `"would_materialize"` for a valid intent; `generated_patch_sha256` is present; `ARMING_ENABLED = False` is enforced: monkeypatch any hypothetical push call and confirm it is never reached; `would_append_records` matches what `RecordBuilder` produces for the same inputs; a malformed intent produces `status="refused"` with quarantine artifact; a tail-unprovable condition produces `status="held"` with held state written; one event is appended to the JSONL log for every call; event `event_sha256` is the SHA-256 of the JSON line bytes; clock is injectable (pass a fixed `datetime` and assert `started_at` matches); the JSONL file is never truncated between calls.
- `test_brain_intent_xor_gate.py` — a path set containing both `.ce/brain/append-intents/ce-foo.yaml` and `.ce/brain/assertions.yaml` returns one error with code `brain_append_intent_xor_direct_ledger`; a path set with only the intent file returns no errors; a path set with only `assertions.yaml` returns no errors; an empty path set returns no errors; error is hard regardless of other path content.

Carrier and changelog:
- `.ce/changelog/ce-491-optiona-slice1.md`
- `.ce/pr-manifests/ce-491-optiona-slice1.md` — carrier slug MUST equal branch name exactly (`ce-491-optiona-slice1`); list every changed file path individually; include exactly one line `- **Declared work class:** <honest assessment>`.

**SLICE 1 — OUT OF SCOPE (defer to later slices):**

- Arming: no live git commit construction, no `git commit-tree`, no `git push`, no GitHub API write call of any kind. `ARMING_ENABLED = False` is hard-coded and must not be made overridable in this slice.
- GitHub App credential loading or use: App ID 4244593, installation 145152358 are provisioned. No code in this slice loads, validates, or exercises actual App credentials. Config dataclass fields for `app_id`, `installation_id`, and `private_key_env` may be defined but must remain unused.
- PR comment posting: advisory comment format is defined in the design and may appear as a string constant in the module, but no forge API call is made in this slice. The dry-run JSON is the only evidence output in scope.
- Service wrapper, systemd unit, supervised process entry-point, and the `deploy/singleton-redeploy/` integration hook. Slice 1 ships the library; the service wrapper comes in a later slice.
- History scan loop: the design's step of walking `main` first-parent history in reverse chronological order to discover all unprocessed pending intents is deferred. `Materializer.run_dry` accepts a single `(merge_commit_sha, intent_path, branch_slug, pr_number)` tuple, not a scan over all merged PRs.
- Compare-and-swap push and post-push verification (steps 9–10 of the design's materialization algorithm): not reachable without arming.
- HELD-state closeout window enforcement (30-minute advisory → hard failure timer): the HELD state data structure is implemented; the wall-clock timer that converts advisory to hard gate failure is deferred.
- Backfill of historical intent files already present on `main` from earlier merged PRs.
- Multi-intent batch envelope for a single branch (the design explicitly defers this).
- Conversion of existing direct-ledger-authorship PRs to the intent file path.
- The `brain_append_intent_closeout` validator check (whether a merged PR's intent is still present on `main` past closeout window): deferred to a later slice once arming and the closeout window timer land.

HARD INVARIANTS (from the design's failure-mode sections and ratified Operator rulings above):

1. Fail-closed on malformed intent: if intent validation fails after PR CI, the materializer MUST write a quarantine artifact at `.ce/state/brain-intent-quarantine/<materialization-key>.json` and enter HELD state with reason `brain_intent_materialization_failed`. The intent MUST NOT be silently dropped, modified on `main`, or removed. Test this path.

2. Quarantine is OUT-OF-BAND in the daemon state root, NEVER in-band on `main` (Q3 ratified ruling). No quarantine artifact, held-state file, or dry-run JSON is ever written to any path that would be committed to the repository. If any output path escapes the `.ce/state/` subtree, it is a hard failure.

3. Deterministic / reproducible commit content: given the same live tail `content_hash`, `merge_commit_sha`, `intent_path`, canonical intent SHA-256, and PR metadata, every execution MUST produce identical record bytes and therefore the same `content_hash`. Record body MUST NOT contain wall-clock timestamps, PID, hostname, credential identifiers, retry counters, local filesystem paths, or lease-holder identity. This invariant must be tested in `test_brain_intent_materializer_core.py`.

4. Chain integrity verified before any append: `LedgerTailProof` MUST prove the current tail before `RecordBuilder` assigns `prev_hash`. If the tail cannot be proven, the materializer MUST raise `HeldError(reason="brain_ledger_tail_unprovable")` and write no ledger bytes and no dry-run patch.

5. ARMING IS OFF in this slice: `ARMING_ENABLED = False` is a module-level constant. No code path may write to `.ce/brain/assertions.yaml` or remove any `.ce/brain/append-intents/` file. Any method that would construct a git tree or push ref MUST raise `RuntimeError("materializer arming is disabled: slice 1 ships dry-run only")` unconditionally. This must be tested.

6. No force-push: the design explicitly forbids force-push. Although slice 1 does not push, any code structure that would allow a non-compare-and-swap push in a future slice is a design defect; surface it as a BLOCKED signal rather than implementing it.

7. Authorized write-path bounds for future arming: document as a module-level constant or docstring: when live mode arms, the only paths the materializer may write are `.ce/brain/assertions.yaml` and consumed intent files under `.ce/brain/append-intents/`. This annotation is reviewable evidence of the authority boundary (Q1 ratified ruling).

8. App credentials from config/env pointers only (Q2 ratified ruling): `MaterializerConfig.private_key_env` is a string naming an env variable — never a key value. Slice 1 must not load or dereference `private_key_env`. Document that any future arming code must read credentials by name from env or a secrets backend; hardcoding a path or key material is a security boundary violation.

9. Singleton lease is diagnostic-only under multi-instance topology (Q4 ratified ruling): `MaterializerLease`'s module-level or class-level docstring MUST state that this local lease is correct for a single-instance deployment and that a second instance invalidates it unless an external linearizable lock governs the `brain-append` exclusion scope.

TERRITORY NOTE: The closest structural prior art is `validators/creator_engine_validator/brain_append_worker.py` — the materializer imports and extends this module; do not duplicate its validation or `_apply_intent` logic. The `daemon_lease.py` in the same package provides the lease facility — import it. `tools/egress-broker/egress_broker/audit.py` shows the JSONL append pattern (append-only, injectable clock, RFC 3339 UTC timestamps) — follow the same pattern for the materializer event log but do NOT import from `tools/`; copy the relevant pattern into `brain_intent_materializer.py` as its own implementation. Where the design is silent on an implementation detail (e.g., exact JSONL field ordering, exact tmp-path naming for dry-run collision avoidance, exact failure message wording beyond the design's vocabulary), choose the conservative fail-closed reading, record the choice in a docstring or in the evidence file, and do not improvise governance policy. Do not modify `validators/creator_engine_validator/brain_append_worker.py`, `validators/creator_engine_validator/brain_append_intent.schema.yaml`, `validators/creator_engine_validator/daemon_lease.py`, or any existing test module.

EVIDENCE: Carrier slug must equal branch name exactly (`ce-491-optiona-slice1`); self-inclusive; honest `- **Declared work class:**` line. Changelog fragment at `.ce/changelog/ce-491-optiona-slice1.md`. Evidence summary must include: total test count and count per test module, confirmation that `ARMING_ENABLED = False` is enforced and covered by a dedicated test assertion, confirmation that quarantine artifacts write to `.ce/state/brain-intent-quarantine/` and not to any in-repo committed path, confirmation that record bytes are deterministic for all four `intent_kind` values with a same-inputs-same-output assertion in the test, any design gaps encountered with the conservative resolution chosen, and any Open Operator Question from the design that affected a Slice 1 decision (so the controller can route it).

Standing preflight directive (ce-ops#303): run the FULL local validator preflight (`ce validate-pr --profile contained-seat`, CI-parity) before commit-for-harvest. Do not discover gates via CI.

STOP LINE: no pushes, no PRs, no gate acts, no signing, no approval or merge actions, no files outside the authorized scope below. If the design under-specifies a governance semantic (not merely an implementation detail resolvable by a conservative default), stop and signal `BLOCKED ce-491-optiona-slice1 <one-line reason>` — do not improvise governance semantics.

Authorized paths for this slice (carrier must enumerate every changed file path individually; these are the only files this brief authorizes):

```
validators/creator_engine_validator/brain_intent_materializer.py
validators/creator_engine_validator/brain_intent_xor_gate.py
validators/tests/unit/test_brain_intent_materializer_key.py
validators/tests/unit/test_brain_intent_materializer_validation.py
validators/tests/unit/test_brain_intent_materializer_core.py
validators/tests/unit/test_brain_intent_materializer_hold.py
validators/tests/unit/test_brain_intent_materializer_lease.py
validators/tests/unit/test_brain_intent_materializer_dryrun.py
validators/tests/unit/test_brain_intent_xor_gate.py
.ce/changelog/ce-491-optiona-slice1.md
.ce/pr-manifests/ce-491-optiona-slice1.md
```

No other paths. On green preflight emit exactly:

```
READY ce-491-optiona-slice1 <commit-sha> .ce/pr-manifests/ce-491-optiona-slice1.md
```

If blocked emit:

```
BLOCKED ce-491-optiona-slice1 <one-line reason>
```
