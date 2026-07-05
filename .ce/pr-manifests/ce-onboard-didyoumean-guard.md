# PR path manifest - ce-onboard-didyoumean-guard - native onboard installer-flag hint

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-onboard-didyoumean-guard

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

- **Declared work class:** tiny

The changes:
- Add a pre-parse native `ce onboard` guard for stale installer-only flags
  (`--spec`, `--answers`, `--answers-schema`, `--plan`, `--apply`,
  `--inventory`) that exits 2 and points users to `ce install <same args>`.
- Cover the guard and the unaffected native dispatch path in onboard CLI tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=7647d8eddce08e75f9b3a350ec8191e7871e1fb438c6a065ddf3785e1cc4576e

```text
.ce/changelog/ce-onboard-didyoumean-guard.md
.ce/pr-manifests/ce-onboard-didyoumean-guard.md
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_ce_onboard_cli.py
```
