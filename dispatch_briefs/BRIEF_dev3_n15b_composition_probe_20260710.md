# DISPATCH — dev-3 — 2026-07-10 — unit: post-merge composition probe (detection-only) — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-n15b-composition-probe <full-40-hex-sha>`
or `BLOCKED ce-n15b-composition-probe <one-line-reason>`.
Branch `ce-n15b-composition-probe` off freshly fetched origin/main OR LATER. Worktree
/var/tmp/wt-ce-n15b-composition-probe. Standing preflight directive: run
`ce validate-pr --profile contained-seat` if your environment can; else focused tests +
BLOCKED(env) per protocol. PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (embedded)

A green check is a perishable fact about a PAIRING (PR head × main-at-a-moment), never a durable
property of a branch. A merged PR's newly-landed gates made every already-open PR's merge-ref red
UNIFORMLY, undetected for hours. The plain main-tip validation already exists in CI and stayed
green throughout. What was missing: the COMPOSITION probe — a detector that runs after merge,
simulating the composition of a given PR with the fresh main-tip, to catch landing-time
invalidations before they poison all dependent PRs. This unit is DETECTION-ONLY: build the probe
module, wire it to run on representative PRs after merge, classify outcomes, and record incidents.
No auto-close wiring, no paging integration in this slice — the record is the seam.

## Unit

NEW module `validators/creator_engine_validator/composition_probe.py` — pure orchestration over
injectable seams (no gh calls in this slice; runner-injectable like `ticket_reconcile_feed`):

1. **Function contract:** `probe_composition(main_tip_sha: str, representative_pr: dict) → CompositionProbeResult`:
   - Input: `main_tip_sha` (current main tip at probe time), `representative_pr` (dict with
     `number`, `head_sha` at minimum).
   - Process: (1) build a throwaway worktree, fetch refs; (2) merge the PR head into main tip
     (git merge-base + merge-tree simulation or actual checkout+merge); (3) classify merge
     conflict outcome separately from validation outcome; (4) run an injectable validation
     command from the merged tree (e.g. `pytest validators/tests/preflight/` or a wrapped
     `ce validate-pr`); (5) if validation fails, retry once; (6) classify final outcome as one
     of: `GREEN`, `RED_FIRST_TRY_THEN_RETRY_ALSO_RED` (deterministic), `RED_FIRST_TRY_THEN_GREEN`
     (flake), `MERGE_CONFLICT`, `MERGE_ABORT` (can't auto-merge).

2. **Retry-once contract:** on RED from step 4, run the validation once more with fresh state
   (clean build, etc.). If it passes, classify as flake. If it fails again, classify as
   deterministic.

3. **Incident record emission:** on `RED_FIRST_TRY_THEN_RETRY_ALSO_RED`, emit a structured
   incident record (same durable-event JSONL path as alarm records) with class
   `composition_probe_red_deterministic`, naming `main_tip_sha` as the suspect breaking landing,
   the PR number being composed, the failing validation output tail (last 500 chars), and the
   merge base that was used.

4. **Injection points:**
   - `validator_fn`: callable `(repo_path: str, tree_ref: str) → bool` (True=green, False=red);
     default implementation wraps `ce validate-pr` or equivalent; tests inject a stub.
   - `merge_strategy`: callable for git merge simulation; default is `git merge-tree`; tests can
     stub.
   - `tmp_dir`: optional path for throwaway worktree; defaults to `/tmp/ce-composition-probe-<uuid>`.

5. **__main__ for CLI:** accept a small JSON input (stdin or file) with keys `main_tip_sha`,
   `representative_pr` (object with `number`, `head_sha`), emit the result and the incident
   record (if any) to stdout as JSONL.

6. **Tests — NEW `validators/tests/unit/test_composition_probe.py`:**
   - Fixture-driven via injectable validator and merge strategy.
   - **Green path:** merges cleanly, validates green → result is GREEN.
   - **Merge conflict path:** merge-tree reports conflict → result is MERGE_CONFLICT, no retry.
   - **Deterministic red path:** merge clean, validation red on first try, red on second try →
     result is RED_FIRST_TRY_THEN_RETRY_ALSO_RED, incident record emitted, output tail captured.
   - **Flake path:** merge clean, validation red on first try, green on second try → result is
     RED_FIRST_TRY_THEN_GREEN, no incident record.
   - **Record shape:** incident records are well-formed JSONL, include all required fields,
     match the durable-event schema used elsewhere.
   - All existing tests in `validators/tests/unit/` must remain green and untouched.

## Files (allowed writes)

- `validators/creator_engine_validator/composition_probe.py` — NEW module, pure probe logic +
  CLI __main__
- `validators/tests/unit/test_composition_probe.py` — NEW test module, fixture-driven tests
- `.ce/changelog/ce-n15b-composition-probe.md` — changelog fragment
- `.ce/pr-manifests/ce-n15b-composition-probe.md` — carrier (slug=branch) with exactly
  `- **Declared work class:** S`

Product lens throughout. Synthetic fixtures for tests. No internal ticket references in
committed content.

## Stop lines

`.github/**`, `deploy/**`, `forge/**`, `checks/**`, `pr_preflight.py`, `ce_cli.py`, `v3_cli.py`,
`secret_identity.py`, all other in-flight modules, `.ce/brain/assertions.yaml`, brain ledger.

## Signal

After focused tests pass and the confidentiality check is green:

1. Commit all changes on branch `ce-n15b-composition-probe`.
2. Signal: `READY-FOR-HARVEST ce-n15b-composition-probe <full-40-hex-sha>`

**In-seat validation note:** when running full `ce validate-pr` from the seat post-relaunch,
ensure you use the absolute path `/workspace/creator-engine/.venv/bin/ce` — bare `ce` does not
resolve correctly in the contained seat after a relaunch and will fail silently or use the wrong
binary. This applies to any invocation of the ce CLI during or after your development work.
