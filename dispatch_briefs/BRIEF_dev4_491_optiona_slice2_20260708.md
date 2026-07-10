# BRIEF — dev-4 — 2026-07-08 — 1 unit: CE-491 Option A merge-time brain append intent materializer, Slice 2

This is the second implementation slice for the Option A merge-time brain append intent materialization design (ticket CE-491, merged design at `docs/design/ce-491-optiona-merge-intent.md`; complementary stale-tail backstop at `docs/design/ce-491-ledger-append-serialization-slice1.md`). Slice 1 (PR #902) delivers the dry-run materializer library, the XOR gate module, and 7 unit test modules. Slice 2 builds on top of the merged slice-1 module. Role: **implementer**. You are a COMMIT-ONLY contained seat: when preflight is green, signal `READY ce-491-optiona-slice2 <commit-sha> .ce/pr-manifests/ce-491-optiona-slice2.md` in the pane. If blocked, signal `BLOCKED ce-491-optiona-slice2 <one-line reason>`. Worktree: `git fetch origin main` first, then **verify the prerequisite** (see below), then create a fresh worktree at `/var/tmp/ce-491-optiona-slice2` off `origin/main`. Branch name is `ce-491-optiona-slice2`. Do NOT activate any venv.

**PREREQUISITE CHECK (BLOCKING):** Before creating the worktree or writing any code, confirm that both `validators/creator_engine_validator/brain_intent_materializer.py` and `validators/creator_engine_validator/brain_intent_xor_gate.py` exist on the fetched `origin/main`. If either is absent, PR #902 (slice 1) has not yet merged; signal `BLOCKED ce-491-optiona-slice2 slice-1 modules not present on origin/main` and stop.

## U1 — branch `ce-491-optiona-slice2` (declare work class honestly; likely story)

CONTEXT (CE-491 — ticket unreachable from seat; design summaries embedded):

The Option A design (`docs/design/ce-491-optiona-merge-intent.md`) replaces direct PR edits to `.ce/brain/assertions.yaml` with data-only append intents placed under `.ce/brain/append-intents/<branch-slug>.yaml`. After a PR lands in the merge queue, the merge-gate queue daemon materializes those intents onto the live ledger tail via a deterministic direct commit to `main`, under a narrow Operator-granted authority. The pre-existing ledger-append-serialization slice-1 design (`docs/design/ce-491-ledger-append-serialization-slice1.md`) shipped a fail-closed PR preflight gate (the stale-tail backstop) for legacy PRs that directly edit `.ce/brain/assertions.yaml`; that slice is complete and its gate remains in place unchanged. Option A is the mediated follow-on path explicitly deferred by that document. The two designs are complementary: the stale-tail gate guards direct-edit PRs; the XOR gate (`brain_append_intent_xor_direct_ledger`) ensures PRs never carry both paths at once; the materializer handles intent-carrying PRs post-merge. Implementation slice 1 for Option A covers the materializer library in dry-run-only mode, the XOR gate validator check, and 7 unit test modules. Slice 2 remediates review findings from slice 1, adds the history scan loop, the HELD-state closeout window timer, and the service wrapper skeleton. Read both design documents in full before writing any code.

Existing code this slice builds on (all present on `origin/main` after slice-1 merge — verify):
- `validators/creator_engine_validator/brain_intent_materializer.py` — the slice-1 materializer library; slice 2 extends and remediates it directly
- `validators/creator_engine_validator/brain_intent_xor_gate.py` — the slice-1 XOR gate module; slice 2 wires its `check_xor` function into the validate-pr dispatch; the module itself is NOT modified
- `validators/creator_engine_validator/brain_append_worker.py` — intent loading, validation, and ledger-apply skeleton imported by the materializer
- `validators/creator_engine_validator/brain_append_intent.schema.yaml` — intent schema (`kind`, `schema_version`, `intent_kind`, four payload blocks)
- `validators/creator_engine_validator/daemon_lease.py` — filesystem lease facility used by the materializer
- `validators/creator_engine_validator/forge/automerge_actuator.py` — merge-gate actuator context; the materializer's closeout flow sits conceptually adjacent to this daemon's accepted-merge stream
- `validators/creator_engine_validator/pr_preflight.py` — the local PR preflight runner; slice 2 wires the XOR gate into the `run_preflight` function here; the function `_changed_paths` in this module supplies the path list that the XOR gate checks

RATIFIED OPERATOR RULINGS (2026-07-08) — the seat cannot read the controller ledger; these rulings are embedded here and are authoritative:

- Q1 (authority scope): The queue daemon gets the narrow direct-commit-to-main materialization authority AS DESIGNED: arming separate; fail-closed holds; only `assertions.yaml` + consumed intent files; deterministic commits.
- Q2 (credential surface): Authority is carried by a DEDICATED NARROW GitHub App `ce-materializer` (App ID 4244593, installation 145152358, `contents:write` only, single-repo, ruleset always-bypass — ALREADY PROVISIONED). The implementation MUST read App credentials from config/env pointers, NEVER hardcode paths or embed key material. Arming (enabling live writes) is explicitly OUT of slice 1 and slice 2 scope.
- Q3 (quarantine placement): Quarantine artifacts go OUT-OF-BAND in the daemon state root, referenced from the PR comment — NEVER in-band on `main`.
- Q4 (topology): STRICT SINGLETON by deployment policy (efficient singleton + one-click IaC redeploy precondition — redeploy tooling already landed as `deploy/singleton-redeploy/`, PR #895).

GOAL: Implement Slice 2 as defined below. The design at `docs/design/ce-491-optiona-merge-intent.md` is the authoritative source. Where any brief text and the design conflict, the design wins; signal BLOCKED rather than resolve a conflict silently.

**SLICE 2 — IN SCOPE:**

**A. Pre-arming remediations from the slice-1 review (all implemented in or adjacent to `validators/creator_engine_validator/brain_intent_materializer.py` and the files listed in the authorized path list):**

A1. Wire `brain_intent_xor_gate.check_xor` into the actual validate-pr dispatch path so the XOR gate fires during real PR validation. The registration point is in `validators/creator_engine_validator/pr_preflight.py`, function `run_preflight`. The existing brain-ledger hard gates are wired directly in `run_preflight` as `_run_check()` calls — for example, `"Creator Engine validator - brain ledger current-tail PR-diff gate"` is registered there by passing a lambda that calls `_assert_brain_ledger_delta_uses_current_tail(...)`. The XOR gate must be wired the same way: add a `_run_check()` entry in `run_preflight` that calls `brain_intent_xor_gate.check_xor(_changed_paths(config.repo_root, comparison_base["value"], runner))` and converts any returned `ValidationError` list into a gate failure (hard failure — non-empty list means FAIL). Place this check adjacent to the existing brain-ledger gate, after `comparison_base` is resolved. The wiring must import `brain_intent_xor_gate` at the top of `pr_preflight.py`. Do not register the XOR gate through the `checks/__init__.py` decorator-based registry — wire it directly in `run_preflight` following the same pattern as the stale-tail gate.

A2. Add a dedicated negative/escape-path unit test for `_require_state_subtree` in `validators/tests/unit/test_brain_intent_materializer_hold.py`. The test must assert that passing a path outside the `.ce/state/` subtree (e.g. `/tmp/evil/key.json`, or a path under `/home/`, or any path not descending from the state root) causes `_require_state_subtree` to raise. `_require_state_subtree` is the sole guard keeping all four state-write sites (dry-run, held-state, quarantine, JSONL event log) inside `.ce/state/`. This test must be in `test_brain_intent_materializer_hold.py` (not a new file), since that module already tests write-site behavior.

A3. `AUTHORIZED_WRITE_PATHS` frozenset is currently dead code (defined as documentation of armed-write authority bounds but never enforced at runtime). Make it a live constraint: add an assertion at the armed-write guard site (or in a dedicated `_assert_armed_write_target(path)` function called by any future armed write site) that the target path is within `AUTHORIZED_WRITE_PATHS`. Since `ARMING_ENABLED = False` in this slice, this assertion guards a currently-unreachable code path; its purpose is to make the authority bound mechanically unbypassable if arming is later enabled without a review of the enforcement site. Add a test in `test_brain_intent_materializer_hold.py` that reads `AUTHORIZED_WRITE_PATHS` from the module and asserts it is a non-empty frozenset whose members are the expected bounded paths (`.ce/brain/assertions.yaml` and `.ce/brain/append-intents/`), confirming the frozenset is not empty metadata.

A4. Three targeted cleanup items, all in `brain_intent_materializer.py` and `test_brain_intent_materializer_hold.py`:
- Add a code comment in `Materializer.run_dry` at the HELD-path code block that documents the HeldError-vs-BrainAppendRefusal artifact asymmetry: HELD paths (via `HeldError`) produce a `HeldStateStore` record and one JSONL event but NO dry-run artifact JSON; `BrainAppendRefusal` (refused path) writes the quarantine artifact and emits a `refused` event but does NOT write a held-state record. Document this asymmetry clearly so future arming code handles both branches correctly.
- Replace `__import__("hashlib")` in `validators/tests/unit/test_brain_intent_materializer_hold.py` with a standard top-level `import hashlib` at the head of the file. The `__import__()` form is needlessly opaque.
- Remove the dead `index + 1 < len(parts)` condition from `_require_state_subtree` in `brain_intent_materializer.py`. If this condition is unreachable by construction (as the review identified), removing it simplifies the guard and eliminates a false-coverage path. Add a brief inline comment explaining why the condition was removed (e.g., "removed: always-True by loop structure; path parts are never exhausted mid-iteration when the subtree root has fewer parts than the candidate").

**B. History scan loop (deferred from slice 1 per its OUT-OF-SCOPE list):**

Implement in `brain_intent_materializer.py` a `HistoryScanner` class (or equivalent module-level function) that walks `main` first-parent history in reverse chronological order to discover all unprocessed pending intents per the design (lifecycle step 3: "Landed pending materialization"). Specification:

- Takes an injectable `GitRunner` callable (same signature as `brain_append_worker.GitRunner`) so tests can provide a fake git runner without spawning a subprocess.
- Calls the runner with `["log", "--first-parent", "--format=%H", "origin/main"]` (or equivalent) to enumerate first-parent SHAs in reverse chronological order (newest first).
- For each commit SHA, checks whether the tree at that commit contains any files under `.ce/brain/append-intents/` using the runner (`["ls-tree", "-r", "--name-only", sha, ".ce/brain/append-intents/"]`). Intent files present in a commit's tree that are also present in the current `origin/main` tree (i.e., not yet consumed) are pending.
- Yields discovered `(merge_commit_sha, intent_path)` pairs in first-parent merge order (oldest first, since materialization must proceed oldest-first to preserve hash-chain order) — i.e., reverse the reverse-chronological list before yielding.
- Deterministic ordering: for a given commit, if multiple intent files are present (future extension), yield them in path-sorted order.
- Dry-run only: the scanner discovers; it does not call `Materializer.run_dry` itself. The caller is responsible for feeding discovered intents to the materializer.
- Note on design alignment: the design's lifecycle step 3 states that pending intents are discovered by walking `main` first-parent history. This scan naturally surfaces ALL unconsumed intent files on `main`, including those from merged PRs earlier than the most recently scanned batch — this is the backfill mechanism per the design. There is no separate "backfill" concept in the design distinct from the history scan; "Backfill of historical intent files already present on main from earlier merged PRs" in the slice-1 OUT-OF-SCOPE list referred to running this scan at all, which slice 2 now covers. The brief therefore removes that item from OUT-OF-SCOPE. The scan is bounded to first-parent `origin/main` history and does not traverse merge parents.
- Unit tests in `validators/tests/unit/test_brain_intent_materializer_scan.py` with a fake git runner. Required test cases: empty history returns no intents; one pending intent found in newest commit is yielded oldest-first (i.e., yielded since it is the only commit); two commits each with one distinct intent are yielded in first-parent oldest-first order; an intent absent from the current `origin/main` tree (already consumed) is NOT yielded; multiple intents in one commit (for future-extension resilience) are yielded in path-sorted order; fake runner simulating a `git log` subprocess failure raises (fail-closed).

**C. HELD-state closeout window timer (deferred from slice 1):**

Implement in `brain_intent_materializer.py` a `CloseoutWindowPolicy` class (or equivalent) that evaluates the design's 30-minute advisory-to-hard-failure conversion. Specification:

- The closeout window is 30 minutes from `held_at_utc` in the `HeldStateStore` record (the time the merge commit first appeared on `main` first-parent history, which corresponds to when the intent entered HELD state).
- An injectable clock (`now: Callable[[], datetime] | None = None`) is required for deterministic testing. Default: `datetime.utcnow` (naive UTC). All comparisons must use naive UTC consistently — do not mix aware and naive datetimes.
- `CloseoutWindowPolicy.evaluate(held_record: dict, now_fn: Callable[[], datetime] | None = None) -> CloseoutStatus` where `CloseoutStatus` is a dataclass or namedtuple with fields: `is_advisory` (bool, True if within the 30-minute window), `is_hard_failure` (bool, True if past the window), `deadline_utc` (ISO-8601 string with trailing `Z`), `held_reason` (str, passed through from the record), `materialization_key` (str).
- During the 30-minute window: advisory status only; this slice does NOT register a gate check for it (the `brain_append_intent_closeout` validator gate registration is explicitly deferred to a later slice, as the design requires the gate to be wired only after arming is in place or specifically authorized). If the design mandates gate registration in this slice (i.e., the design says the advisory/hard-failure status MUST be visible during PR validation before arming), record that reading in a docstring comment at `CloseoutWindowPolicy` and signal `BLOCKED ce-491-optiona-slice2 design-mandates-closeout-gate-registration-before-arming-needs-Operator-ruling` rather than improvise. The conservative fail-closed reading is: no gate registration in this slice; the timer logic is implemented and testable but only produces `CloseoutStatus` output, which callers inspect. Gate registration is slice 3 / arming scope.
- The `HeldStateStore` (from slice 1) must be extended to persist `held_at_utc` if not already present in the slice-1 schema. If the slice-1 implementation already persists `held_at_utc`, no schema change is needed; confirm in code.
- Unit tests in `validators/tests/unit/test_brain_intent_materializer_closeout.py`. Required test cases: a held record with `held_at_utc` 10 minutes in the past returns `is_advisory=True, is_hard_failure=False`; a held record with `held_at_utc` 31 minutes in the past returns `is_advisory=False, is_hard_failure=True`; a held record with `held_at_utc` exactly 30 minutes in the past is hard failure (boundary is exclusive, consistent with fail-closed interpretation); injectable clock accepted and used; `deadline_utc` is exactly 30 minutes after `held_at_utc` in ISO-8601 UTC format with trailing `Z`; malformed `held_at_utc` field raises rather than silently returning advisory.

**D. Service wrapper skeleton (deferred from slice 1):**

Implement in `brain_intent_materializer.py` a `MaterializerRunLoop` class (or module-level `run_loop` function) that is the supervised entry point for later systemd integration. Specification:

- Library-level only: this is an importable, unit-testable function/class. Do NOT add systemd unit files, do NOT touch `deploy/` in this slice.
- Accepts an injectable poll source (`poll_source: Callable[[], list[tuple[str, str]]] | None = None`) that returns a list of `(merge_commit_sha, intent_path)` pairs to process. The default poll source calls `HistoryScanner` on the current repo root. The injectable form exists so tests can provide deterministic input without git subprocess calls.
- For each `(merge_commit_sha, intent_path)` pair from the poll source: derive `branch_slug` from `Path(intent_path).stem`; derive `pr_number` from the merge commit metadata if available (or accept it as a parameter); call `Materializer.run_dry(merge_commit_sha, intent_path, branch_slug, pr_number, config)`. Collect `DryRunOutput` results and return them.
- Does not manage a process lifecycle, signals, or restart logic in this slice — that is systemd/supervisor scope. The run-loop function executes one poll-and-process cycle and returns.
- Documents the Q4 singleton lease caveat at the class or function docstring level: "Under multi-instance topology, multiple run-loop invocations against the same repo state would produce competing leases; correctness requires an external linearizable lock with the same brain-append exclusion scope (Q4 ratified ruling)."
- Unit tests in `validators/tests/unit/test_brain_intent_materializer_runloop.py`. Required test cases: empty poll source returns empty result list; single-item poll source calls `Materializer.run_dry` once and returns one `DryRunOutput`; two-item poll source calls `Materializer.run_dry` twice in order; injectable poll source is used (not the default `HistoryScanner`); run-loop function is importable from `brain_intent_materializer` without triggering git subprocess calls (importability test); class or function docstring contains the Q4 singleton-caveat sentence (test reads the docstring).

**SLICE 2 — OUT OF SCOPE (carry forward; items removed from this list if now covered by slice 2):**

- Arming: no live git commit construction, no `git commit-tree`, no `git push`, no GitHub API write call of any kind. `ARMING_ENABLED = False` is hard-coded and must not be made overridable in this or any future slice without a new Operator ruling.
- GitHub App credential loading or use: App ID 4244593, installation 145152358 are provisioned. No code in this slice loads, validates, or exercises actual App credentials.
- PR comment posting: advisory comment format is defined in the design and the dry-run advisory string constants may exist in the module, but no forge API call is made.
- Compare-and-swap push and post-push verification (design steps 9–10): not reachable without arming.
- Backfill of historical intent files already present on `main`: this item is REMOVED from the deferred list — B's history scan naturally serves as the backfill mechanism per the design's step 3 (the daemon discovers all pending intents by walking `main` first-parent history; no separate backfill is defined in the design).
- Multi-intent batch envelope for a single branch: deferred.
- `brain_append_intent_closeout` validator check (gate registration for the closeout window): deferred to slice 3 / arming scope, unless the design mandates it before arming (see C above for the BLOCKED signal path).
- `deploy/` directory and systemd unit files: not touched in this slice.
- Systemd service lifecycle, signal handling, restart logic: not in scope.
- CAS push, App credential loading, backfill, multi-intent batch envelope remain deferred.

Unit tests: one new module per new concern (test_brain_intent_materializer_scan.py for B, test_brain_intent_materializer_closeout.py for C, test_brain_intent_materializer_runloop.py for D). Extensions to existing test modules are authorized ONLY for A2, A3, and A4 targets in `test_brain_intent_materializer_hold.py` (targeted additions as described above — do not restructure or rename existing tests). All other slice-1 test modules (`test_brain_intent_materializer_key.py`, `test_brain_intent_materializer_validation.py`, `test_brain_intent_materializer_core.py`, `test_brain_intent_materializer_lease.py`, `test_brain_intent_materializer_dryrun.py`, `test_brain_intent_xor_gate.py`) must NOT be modified. If a slice-1 test breaks due to a slice-2 change (e.g., `_require_state_subtree` cleanup), fix the code, not the test, unless the test itself was demonstrably testing dead code — in that case, signal BLOCKED for controller resolution.

Carrier and changelog:
- `.ce/changelog/ce-491-optiona-slice2.md`
- `.ce/pr-manifests/ce-491-optiona-slice2.md` — carrier slug MUST equal branch name exactly (`ce-491-optiona-slice2`); list every changed file path individually; include exactly one line `- **Declared work class:** <honest assessment>`.

**HARD INVARIANTS (from the design's failure-mode sections and ratified Operator rulings above):**

1. Fail-closed on malformed intent: if intent validation fails after PR CI, the materializer MUST write a quarantine artifact at `.ce/state/brain-intent-quarantine/<materialization-key>.json` and enter HELD state with reason `brain_intent_materialization_failed`. The intent MUST NOT be silently dropped, modified on `main`, or removed. This invariant is unaffected by slice-2 additions; all new code paths must preserve it.

2. Quarantine is OUT-OF-BAND in the daemon state root, NEVER in-band on `main` (Q3 ratified ruling). No quarantine artifact, held-state file, dry-run JSON, scan result, closeout status, or run-loop output is ever written to any path that would be committed to the repository. If any output path escapes the `.ce/state/` subtree, it is a hard failure. `_require_state_subtree` remains the enforcement point; A2 adds a test proving it fails closed.

3. Deterministic / reproducible commit content: given the same live tail `content_hash`, `merge_commit_sha`, `intent_path`, canonical intent SHA-256, and PR metadata, every execution MUST produce identical record bytes and therefore the same `content_hash`. Record body MUST NOT contain wall-clock timestamps, PID, hostname, credential identifiers, retry counters, local filesystem paths, or lease-holder identity. Slice-2 additions (scan, closeout, run-loop) must not inject non-deterministic data into record bytes.

4. Chain integrity verified before any append: `LedgerTailProof` MUST prove the current tail before `RecordBuilder` assigns `prev_hash`. If the tail cannot be proven, the materializer MUST raise `HeldError(reason="brain_ledger_tail_unprovable")` and write no ledger bytes and no dry-run patch. Slice-2 code must not short-circuit or bypass this check.

5. ARMING IS OFF in this slice: `ARMING_ENABLED = False` is a module-level constant. No code path may write to `.ce/brain/assertions.yaml` or remove any `.ce/brain/append-intents/` file. Any method that would construct a git tree or push ref MUST raise `RuntimeError("materializer arming is disabled: slice 1 ships dry-run only")` unconditionally. This constant MUST NOT be made overridable by any config or env variable in this slice.

6. No force-push: the design explicitly forbids force-push. Slice 2 introduces no push code. Any code structure introduced in slice 2 that would allow a non-compare-and-swap push in a future slice is a design defect; surface it as a BLOCKED signal.

7. Authorized write-path bounds for armed writes are now LIVE (A3 remediation): `AUTHORIZED_WRITE_PATHS` is no longer dead code — a `_assert_armed_write_target(path)` assertion (or equivalent central guard) is active at the armed-write code path. When `ARMING_ENABLED` is True in a future slice, any write to a path not in `AUTHORIZED_WRITE_PATHS` (`.ce/brain/assertions.yaml` and consumed intent files under `.ce/brain/append-intents/`) must raise before the write is attempted. The enforcement code must be present and reachable (not guarded by `ARMING_ENABLED`) so that the constraint is visible to reviewers even when arming is off. Document this at the enforcement site.

8. App credentials from config/env pointers only (Q2 ratified ruling): `MaterializerConfig.private_key_env` is a string naming an env variable — never a key value. Slice 2 must not load or dereference `private_key_env`. Scan, closeout, and run-loop code must not add credential-handling of any kind.

9. Singleton lease is diagnostic-only under multi-instance topology (Q4 ratified ruling): `MaterializerLease`'s docstring retains the caveat from slice 1. The new `MaterializerRunLoop`'s docstring MUST ALSO state the Q4 singleton caveat (as required by item D above). Two docstring locations; both must be present.

10. XOR-gate wiring is additive (new in slice 2): the `brain_intent_xor_gate.check_xor` wiring in `run_preflight` MUST NOT weaken, replace, suppress, or bypass any existing validator gate, including the `"Creator Engine validator - brain ledger current-tail PR-diff gate"` and any other gates already registered in `run_preflight`. The wiring is purely additive: a new `_run_check()` entry is inserted alongside the existing entries. If the XOR gate errors return a non-empty list, the preflight must fail hard (return non-zero) for that check entry — not warn and continue.

TERRITORY NOTE: The existing pattern for hard gates in `pr_preflight.py::run_preflight` is `checks.append(_run_check("gate name", lambda: ..., out, err))` followed by `if not checks[-1].ok: return 1`. The XOR gate wiring must follow this exact pattern. The `_changed_paths(config.repo_root, comparison_base["value"], runner)` helper already provides the list of changed paths needed by `check_xor`. The XOR gate must be called after `comparison_base` is resolved (it depends on that value) and must fail hard if the check fails (i.e., include the early-return guard). The closest structural prior art for the history scan is the `daemon_lease.py` lease facility — injectable, minimal subprocess surface. The `tools/egress-broker/egress_broker/audit.py` append-only JSONL pattern continues to apply to the event log; do not import from `tools/`. Where the design is silent on an implementation detail, choose the conservative fail-closed reading, record the choice in a docstring, and do not improvise governance policy.

EVIDENCE: Carrier slug must equal branch name exactly (`ce-491-optiona-slice2`); self-inclusive; honest `- **Declared work class:**` line. Changelog fragment at `.ce/changelog/ce-491-optiona-slice2.md`. Evidence summary must include: total test count and count per test module (all modules, not just new ones), confirmation that `ARMING_ENABLED = False` is still enforced and the existing test assertion still passes, confirmation that `_require_state_subtree` negative test passes with an out-of-subtree path, confirmation that `AUTHORIZED_WRITE_PATHS` enforcement code is in place and the frozenset is non-empty, confirmation that `CloseoutWindowPolicy.evaluate` boundary case (exactly 30 minutes) is hard failure with injectable clock, confirmation that `HistoryScanner` with fake runner yields intents in oldest-first order, confirmation that `MaterializerRunLoop` docstring contains the Q4 singleton-caveat sentence, any design gaps encountered with the conservative resolution chosen, and any Operator question from the design or this brief that affected a slice-2 decision.

Standing preflight directive (ce-ops#303): run the FULL local validator preflight (`ce validate-pr --profile contained-seat`, CI-parity) before commit-for-harvest. Do not discover gates via CI.

STOP LINE: no pushes, no PRs, no gate acts, no signing, no approval or merge actions, no files outside the authorized scope below. If the design under-specifies a governance semantic (not merely an implementation detail resolvable by a conservative default), stop and signal `BLOCKED ce-491-optiona-slice2 <one-line reason>` — do not improvise governance semantics.

Authorized paths for this slice (carrier must enumerate every changed file path individually; these are the only files this brief authorizes):

```
validators/creator_engine_validator/brain_intent_materializer.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_brain_intent_materializer_hold.py
validators/tests/unit/test_brain_intent_materializer_scan.py
validators/tests/unit/test_brain_intent_materializer_closeout.py
validators/tests/unit/test_brain_intent_materializer_runloop.py
.ce/changelog/ce-491-optiona-slice2.md
.ce/pr-manifests/ce-491-optiona-slice2.md
```

No other paths. On green preflight emit exactly:

```
READY ce-491-optiona-slice2 <commit-sha> .ce/pr-manifests/ce-491-optiona-slice2.md
```

If blocked emit:

```
BLOCKED ce-491-optiona-slice2 <one-line reason>
```
