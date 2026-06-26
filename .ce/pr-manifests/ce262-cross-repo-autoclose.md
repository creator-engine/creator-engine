# PR path manifest - ce262-cross-repo-autoclose

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce262-cross-repo-autoclose --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** story

Scope:
ce-ops#262 proves that GitHub does NOT auto-close issues across repositories via
`Closes` keywords in PR descriptions (cross-repo PRs only produce a
CrossReferencedEvent, never a ConnectedEvent/close), so 59 ce-ops issues were
found stale-open after merged creator-engine PRs.

This PR enhances the merge-triggered autoclose bot (originally ce-ops#154) with
title-scan: every ``ce-ops#N`` token in a merged PR title is now auto-closed via
the API, covering the dominant CE PR title convention (``feat(ce-ops#NNN): ...``).
Body ``Closes/Fixes/Resolves ce-ops#N`` refs continue to be honoured.

Parsing logic is extracted into a standalone stdlib-only module
(``tools/ce-ops-autoclose/parse_issue_refs.py``) so it can be unit-tested in
isolation. The workflow driver and token name are updated to ``CE_CROSS_REPO_TOKEN``.

Base:
`d5cf03d12e3fe307d178ac4820159ee014a4d7db` (`origin/main` at branch creation).

Per-file purpose:
- **`.ce/changelog/ce262-cross-repo-autoclose.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce262-cross-repo-autoclose.md`** *(A)* - this closed
  path-set carrier.
- **`.github/scripts/ceops_autoclose.py`** *(M)* - updated driver: imports
  shared parser, adds ``CE_CROSS_REPO_TOKEN`` primary with ``CE_OPS_TOKEN``
  legacy fallback, back-compat ``parse_closing_ceops_refs`` shim preserved.
- **`.github/workflows/ce-ops-autoclose.yml`** *(M)* - passes
  ``CE_CROSS_REPO_TOKEN`` to driver; adds clearer trigger/secret documentation.
- **`tools/ce-ops-autoclose/parse_issue_refs.py`** *(A)* - standalone
  stdlib-only parser with ``parse_title_refs``, ``parse_body_closing_refs``,
  and ``parse_all_refs`` (title-first, deduplicated).
- **`validators/tests/unit/test_ce262_parse_issue_refs.py`** *(A)* - 27 unit
  tests covering title-only, body-keyword, combined, dedup, cross-repo form,
  case-insensitivity, and none-found cases.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=c7b14c1ee4923c9ec65add5514034e4de427edc26295cfc74bc6e772085cecba

```text
.ce/changelog/ce262-cross-repo-autoclose.md
.ce/pr-manifests/ce262-cross-repo-autoclose.md
.github/scripts/ceops_autoclose.py
.github/workflows/ce-ops-autoclose.yml
tools/ce-ops-autoclose/parse_issue_refs.py
validators/tests/unit/test_ce262_parse_issue_refs.py
```

## Operator action required before bot is live

The `CE_CROSS_REPO_TOKEN` Actions secret must be provisioned in
`creator-engine/creator-engine` repository settings before the workflow can
close ce-ops issues.

**Token requirements:**
- Fine-grained PAT **or** GitHub App installation token
- Scope: `issues:write` on `creator-engine/ce-ops` **only**
- The built-in `GITHUB_TOKEN` cannot substitute (it is scoped to
  `creator-engine/creator-engine` and cannot close cross-repo issues)

Existing `CE_OPS_TOKEN` (if already provisioned) continues to work as a
legacy fallback — the driver accepts either name.
