# PR path manifest - ce-readme-review-minors - README review minors

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-readme-review-minors` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Slug: `ce-readme-review-minors`

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

## Goal / Done-when / Change-type

Goal: close the README-review follow-up by preventing false current-version drift matches and documenting the shipped conveyor command.

Done-when: README CE-version drift tests distinguish CE release claims from runtime version prose, `docs/reference/cli.md` documents `ce conveyor`, and CLI reconciliation checks public pre-argparse dispatch groups.

Change-type: code and docs.

## Probe Result

- `git log origin/main --oneline | grep -i "readme\|cli.md\|version.drift" | head -3` showed `cb968452 docs: overhaul public README, add CLI reference, extend version-drift gate (#907)`.
- `git show origin/main:docs/reference/cli.md 2>/dev/null | head -5` returned the CLI reference header, so the prerequisite document exists.
- Finding 1 before: `README_CE_VERSION_TEXT` included a standalone `version` alternative:
  `(?i)\b(?:current\s+release|version|(?:ce|creator\s+engine)(?:\s+(?:v(?:ersion)?|release|current\s+release))?)...`
- Finding 1 after: bare `version` is removed; the pattern now requires `current release` or explicit `ce` / `creator engine` context:
  `(?i)\b(?:current\s+release|(?:ce|creator[\s-]+engine)(?:\s+(?:v(?:ersion)?|release|current\s+release))?)...`
- Finding 2 before: `git show origin/main:docs/reference/cli.md | grep -i "conveyor"` returned no output.
- Finding 2 before: `git show origin/main:validators/creator_engine_validator/ce_cli.py | grep -n "PRE_ARGPARSE_DISPATCH_GROUPS"` returned no output.

## Preflight Evidence

- Targeted README version-drift tests: `PYTHONPATH=validators python -m pytest validators/tests/unit/test_version_drift.py -q` -> `17 passed`.
- Targeted CLI docs reconciliation tests: `PYTHONPATH=validators python -m pytest validators/tests/unit/test_v1_docs_reconciliation.py -q` -> `13 passed`.
- Final seat-ready preflight was run by the commit-only worker after writing this carrier; see the worker signal for the terminal result.

## Changed Paths

- `.ce/changelog/ce-readme-review-minors.md` - changelog fragment.
- `.ce/pr-manifests/ce-readme-review-minors.md` - this carrier.
- `docs/reference/cli.md` - public `ce conveyor` reference.
- `validators/creator_engine_validator/ce_cli.py` - declarative pre-argparse dispatch group constants.
- `validators/creator_engine_validator/checks/version_drift.py` - README CE-version regex context guard.
- `validators/tests/unit/test_v1_docs_reconciliation.py` - pre-argparse public dispatch docs coverage.
- `validators/tests/unit/test_version_drift.py` - CE and non-CE README version drift coverage.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=b1a8c806b771273b65a63672354f2c53cf96283f847fa6ab435cfa1dc93c86e6

```text
.ce/changelog/ce-readme-review-minors.md
.ce/pr-manifests/ce-readme-review-minors.md
docs/reference/cli.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/version_drift.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_drift.py
```
