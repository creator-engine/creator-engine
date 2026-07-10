# BRIEF — dev-4 — 2026-07-09 — P2: Acceptance-Evidence closure rule (STRANGELOOP-1 pool)

Role: **implementer** (story unit — parser extension + warn-mode enforcement + tests +
docs section; NO product code changes unrelated to the close-bot). Contained COMMIT-ONLY
seat. Fresh worktree /var/tmp/wt-p2-acceptance off origin/main (fetch first).
Branch `ce-p2-acceptance-evidence`.
Signal: `READY ce-p2-acceptance-evidence <sha> .ce/pr-manifests/ce-p2-acceptance-evidence.md`
or `BLOCKED ce-p2-acceptance-evidence <reason>`. Declared work class: **story**.
NO .ce/brain/assertions.yaml edits. Standing preflight directive: FULL `ce validate-pr` before READY.

---

## Context — what the close-bot is and where it lives

The cross-repo autoclose bot closes issues in a separate tracker when a PR
merges to main. It is implemented across two files:

- **`tools/ce-ops-autoclose/parse_issue_refs.py`** (125 lines) — stdlib-only
  parser; two public functions: `parse_title_refs(title)` and
  `parse_body_closing_refs(body)`, composed by `parse_all_refs(title, body)`.
  No closing-keyword requirement on title refs; body refs require
  `Closes`/`Fixes`/`Resolves` (and inflections).

- **`.github/scripts/ceops_autoclose.py`** (261 lines) — workflow driver;
  dynamically imports the parser module, loads PR context from
  `GITHUB_EVENT_PATH`, resolves the cross-repo token, then calls
  `close_issue_if_open()` for each extracted issue number.

Triggered by `.github/workflows/ce-ops-autoclose.yml` on `pull_request` type
`closed`, job condition `merged == true && base.ref == 'main'`, both steps
carry `continue-on-error: true`.

Existing tests live in:
- `validators/tests/unit/test_ceops_autoclose.py`
- `validators/tests/unit/test_ce262_parse_issue_refs.py`

**Two confirmed defects in `.github/scripts/ceops_autoclose.py` that this
slice must fix:**

1. **Fail-open on missing token** — lines 240–247: if
   `CE_CROSS_REPO_TOKEN` and legacy `CE_OPS_TOKEN` are both absent, the
   function prints a `::warning::` and returns `0`. During token rotation
   this silently skips all closures; directive-class tickets can be
   auto-closed before the new token is in place. Fix: return nonzero (exit 1)
   when the token is absent.

2. **No evidence check** — `close_issue_if_open` (lines 200–214) closes any
   referenced issue unconditionally. There is no check for an
   `Acceptance-Evidence:` field on the PR body, and no label-based gate.

---

## Ratified rule (Decision 14 pool P2)

Directive-class issues may be closed by the autoclose bot only when the
closing PR body contains an `Acceptance-Evidence:` field that names a
check, test, or validator that fails if the outcome is absent from main.

When evidence is missing the bot must **warn** (post a comment) rather than
close. The bot must **fail closed** (exit nonzero) when the cross-repo token
is absent — no silent skips.

---

## U1 — Acceptance-Evidence enforcement, slice 1

### Scope (exactly this, nothing more)

1. **Parser extension** — add `parse_acceptance_evidence(body: str) -> str | None`
   to `tools/ce-ops-autoclose/parse_issue_refs.py`. The function extracts the
   value of an `Acceptance-Evidence:` line in the PR body (leading whitespace
   and optional colon-space separator tolerated; returns `None` when absent).
   Line form: `Acceptance-Evidence: <value>` anywhere in the body (not
   keyword-gated). Export it from the module alongside the existing public
   functions.

2. **Directive-label detection** — in `.github/scripts/ceops_autoclose.py`,
   after fetching the issue via `_api_json("GET", issue_path, token)` (the
   call that already exists inside `close_issue_if_open`, lines 201–203),
   inspect `issue.get("labels", [])` for a label whose `name` field equals
   `"directive"` (case-sensitive; the label is on the tracked issue, not
   the PR). Slice 1 defaults unlabeled issues to **exempt** — only issues
   carrying the `directive` label are subject to the evidence check.

3. **Warn-mode enforcement** — when the issue is directive-class AND the PR
   body contains no `Acceptance-Evidence:` value, do NOT close the issue.
   Instead, post a single structured bot comment (via the existing
   `_api_json("POST", .../comments, ...)` pattern) and return without
   patching the state. Comment template (keep it short and machine-readable):

   ```
   **Autoclose blocked — Acceptance-Evidence required.**

   This issue carries the `directive` label. The closing PR did not supply
   an `Acceptance-Evidence:` field in its body. Add a line of the form:

       Acceptance-Evidence: <check-name or test path>

   to the PR body and the bot will close this issue on the next merge.

   Closing PR: <PR URL>
   ```

   The comment must include the PR URL from the context dict (key `"url"`).

4. **Fail-closed on token absence** — change the early-return in `main()`
   (currently at line 247, `return 0`) to `return 1`. Update the surrounding
   `::warning::` to `::error::`. The `continue-on-error: true` on the workflow
   step is intentional (keeps existing merge-unblocking contract); the step
   now sets a failed exit code so the failure is visible in the check log
   rather than silently swallowed.

5. **Tests** — add a new test file
   `validators/tests/unit/test_p2_acceptance_evidence.py` covering:
   - `parse_acceptance_evidence` returns the value when the field is present
   - `parse_acceptance_evidence` returns `None` when absent
   - `parse_acceptance_evidence` is whitespace-tolerant (leading spaces,
     trailing whitespace on the value)
   - directive-labeled issue + no evidence → warn comment posted, issue NOT
     closed (mock `_api_json`; verify PATCH never called, POST called once
     with "Acceptance-Evidence required" in the body)
   - directive-labeled issue + evidence present → issue closed normally
     (existing `close_issue_if_open` path; verify PATCH called)
   - non-directive issue + no evidence → issue closed normally (exempt path)
   - token absent → `main()` returns 1 (existing test
     `test_non_main_base_ref_is_noop` is a model — do NOT modify it;
     add a new parametrized test for the token-absent case)

6. **Docs section** — add a new section to the comment block at the top of
   `.github/scripts/ceops_autoclose.py` (between the existing module docstring
   and the imports, after line 22 / before `from __future__ import annotations`
   at line 23). Title the section `# Acceptance-Evidence enforcement (P2)`.
   Cover: the `directive` label convention, the `Acceptance-Evidence:` field
   format, warn-mode behavior, and fail-closed semantics. Keep it under
   25 lines; no internal references, no issue-tracker numbers.

### What NOT to touch

- Do not edit `.ce/brain/assertions.yaml`.
- Do not change `.github/workflows/ce-ops-autoclose.yml` (the `continue-on-error`
  flag is intentional; the fail-closed fix is a Python exit-code change only).
- Do not modify `test_ceops_autoclose.py` or `test_ce262_parse_issue_refs.py`
  (extend, never break existing test coverage).
- Do not add the `directive` label to any repository — label creation is
  out of scope for this slice; the bot merely reads labels that already exist.
- No changes to `surfaces/manifest.yaml`, `validators/`, or any file outside
  the six targets listed above:
  `tools/ce-ops-autoclose/parse_issue_refs.py`,
  `.github/scripts/ceops_autoclose.py`,
  `validators/tests/unit/test_p2_acceptance_evidence.py`,
  plus the carrier manifest and changelog fragment.

### Acceptance evidence for THIS slice

The closing PR body must carry:

```
Acceptance-Evidence: validators/tests/unit/test_p2_acceptance_evidence.py
```

This file must exist in the PR and must contain at minimum the seven test
cases enumerated above. `pytest validators/tests/unit/test_p2_acceptance_evidence.py`
must pass in the worktree before READY is signaled.

### Preflight sequence (mandatory before READY)

```
git fetch origin
git checkout -b ce-p2-acceptance-evidence origin/main
# ... implement ...
pytest validators/tests/unit/test_p2_acceptance_evidence.py -v
pytest validators/tests/unit/test_ceops_autoclose.py -v
pytest validators/tests/unit/test_ce262_parse_issue_refs.py -v
ce validate-pr   # must be fully GREEN
```

Produce the carrier manifest at
`.ce/pr-manifests/ce-p2-acceptance-evidence.md` (declared paths: the three
Python files + the test file + the docs fragment in `ceops_autoclose.py`,
work class `story`). Include a CHANGELOG entry under `## Unreleased` in
`CHANGELOG.md` noting the Acceptance-Evidence warn-mode enforcement and
fail-closed token behavior.
