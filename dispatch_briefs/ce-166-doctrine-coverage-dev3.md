# SEED BRIEF — ce-ops#166 Slice 4: doctrine-coverage ratchet check (dev-3)

- **Ticket**: ce-ops#166 (Knowledge SSOT) — Slice 4. This brief is SELF-CONTAINED;
  do not attempt to read the ticket (you have no egress). Everything you need is here.
- **Role**: implementer (governed seat). You build, test, commit. You do NOT push,
  approve, merge, or touch any gate. Controller harvests.
- **Branch**: `ce-166-doctrine-coverage` off `origin/main` (fetch first if you can;
  if fetch fails, branch off your local origin/main and SAY SO in the done-report).
- **Worktree**: create under `/var/tmp` (NOT /workspace). venv has no activate —
  use `.venv/bin/python -m pytest`.
- **Declared work class**: S.

## Problem (why this slice exists)

CE's brain (Knowledge-SSOT) machinery is shipped and strong: hash-chained
append-only assertion ledger at `.ce/brain/assertions.yaml`, fail-closed drift
verification (`checks/ce_brain_drift.py`), schema+chain integrity
(`checks/ce_brain_assertions.py`), all wired into the standard check registry.
But COVERAGE is thin: `docs/contracts/` holds 37 doctrine files and only 2 are
coupled to an active brain assertion. Nothing today notices when a new
doctrine file lands uncoupled — doctrine stays prose that agents must
*remember*, which is exactly the drift failure class this epic exists to kill.
Convert "someone must remember to `ce brain assert` this doc" into "CI refuses
an unaccounted-for net-new doctrine file."

## Design (deterministic, no NLP — follow this shape)

1. **New data manifest** `.ce/brain/doctrine-coverage.yaml`:
   ```yaml
   kind: brain-doctrine-coverage-manifest
   schema_version: "1"
   governed_trees:
     - docs/contracts
   exceptions:
     # seed with EVERY currently-uncoupled docs/contracts/*.md file
     # (i.e., all except the ones covered by an active static assertion
     #  whose evidence_ref resolves to them — today that is
     #  docs/contracts/authoring-a-governed-pr.md; verify the exact covered
     #  set yourself from .ce/brain/assertions.yaml before seeding)
     - docs/contracts/<...>.md
   ```
   Seeding the exception list with today's uncovered files means the slice
   lands GREEN with zero forced content authoring, while arming forward
   pressure (ratchet may only shrink).

2. **New check module**
   `validators/creator_engine_validator/checks/ce_brain_doctrine_coverage.py`:
   - Load the manifest; fail-closed on malformed/missing shape
     (error code `brain_doctrine_manifest_invalid`).
   - Load the authoritative ledger via
     `brain_runtime.load_authoritative_records(repo_root)` (REUSE — do not
     duplicate ledger parsing).
   - Coverage set = for every ACTIVE record with
     `verification_method.type == "static"`, resolve `evidence_ref` (strip any
     `#fragment`) to a repo-relative path → that file is "covered". (Check
     whether any existing assertion uses a `#fragment` suffix before assuming
     it's optional-but-supported; today none appear to.)
   - For every `*.md` under each `governed_trees` prefix (exclude `README.md`):
     - covered → OK; if ALSO listed in `exceptions` → FAIL
       `brain_doctrine_stale_exception` (ratchet only shrinks).
     - not covered, in `exceptions` → OK (acknowledged debt).
     - not covered, not in `exceptions` → FAIL `brain_doctrine_uncovered`,
       actionable message telling the author to either
       `ce brain assert --evidence-ref <path> --type convention ...` or add the
       path to `.ce/brain/doctrine-coverage.yaml` exceptions.
     - exception entry pointing at a file that no longer exists → FAIL (stale).
   - Register via `@register(CHECK_NAME, [...])` exactly like
     `ce_brain_assertions` / `ce_brain_drift`.

3. **One-line wiring**: add the import line for the new module to
   `validators/creator_engine_validator/checks/__init__.py` (mirrors existing
   entries). This alone puts it under the existing `run_registered(paths)`
   seam. **NO edits** to `pr_preflight.py`, `ce_cli.py`, `brain_runtime.py`,
   `ce_brain_drift.py`, `public_docs_confidentiality.py` (pattern reference
   only — you may READ it to mirror the KNOWN_PENDING/ratchet discipline).

4. **Tests** `validators/tests/unit/test_ce_brain_doctrine_coverage.py` —
   fixture repo trees exercising at minimum:
   (i) net-new uncovered file under `docs/contracts/` + empty exceptions →
   FAIL `brain_doctrine_uncovered`;
   (ii) same file in `exceptions` → PASS;
   (iii) file with a genuine active `static` assertion resolving to it → PASS
   with no exception entry;
   (iv) exception entry for a file that IS covered → FAIL
   `brain_doctrine_stale_exception`;
   (v) exception entry for a nonexistent file → FAIL;
   (vi) malformed manifest (missing `governed_trees`) → FAIL
   `brain_doctrine_manifest_invalid`.
   Each behavior needs a clean fail-without/pass-with shape.

## Allowed paths (EXACTLY these; if a fix seems to need another file, STOP and report)

- `validators/creator_engine_validator/checks/ce_brain_doctrine_coverage.py` (new)
- `validators/creator_engine_validator/checks/__init__.py` (one import line)
- `.ce/brain/doctrine-coverage.yaml` (new)
- `validators/tests/unit/test_ce_brain_doctrine_coverage.py` (new)
- `.ce/changelog/ce-166-doctrine-coverage.md` (new — REQUIRED changelog fragment)
- `.ce/pr-manifests/ce-166-doctrine-coverage.md` (new — REQUIRED carrier; regen
  via the `carrier_gen` API `write_carriers(base="origin/main")`, never hand-list)

## Standing preflight directive (ce-ops#303)

Run the FULL local validator preflight (`ce validate-pr`, CI-parity,
TMPDIR=/var/tmp) GREEN in ONE pass before commit-for-harvest; do not discover
gates via CI. `pytest -m "not slow"` is iteration-only; the full suite is the bar.

## Expected evidence (done-report)

1. Verbatim GREEN tail of full `ce validate-pr`.
2. Test run output showing all new tests pass AND at least one demonstrated
   fail-without case (temporarily revert the guard or use the fixture to show
   the check actually fires).
3. The exact covered-set you derived from `assertions.yaml` and the count of
   seeded exceptions (should be ~35-36).
4. `git add -A && git commit && echo COMMIT_SHA=$(git rev-parse HEAD)` — a
   done-report WITHOUT a verifiable commit SHA is NOT done.
5. Emit `READY-FOR-HARVEST ce-166-doctrine-coverage <sha>` as the final line.

## Stop line

Do NOT push, open a PR, approve, or merge — controller harvests. Do NOT touch
any file outside the allowed list. Do NOT edit gate-sensitive modules
(`brain_runtime.py`, `ce_brain_drift.py`, `pr_preflight.py`, `ce_cli.py`,
`public_docs_confidentiality.py`, `.github/**`). If blocked, report the
blocker and stop — do not improvise scope.
