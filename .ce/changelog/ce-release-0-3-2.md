---
slug: ce-release-0-3-2
date: 2026-07-05
kind: chore
scope: release
issue: creator-engine/ce-ops#447
---

**bump 0.3.1 -> 0.3.2 + CHANGELOG + release staging.**

Bump version 0.3.1 -> 0.3.2, merge the parked `ce-415-followup-tinies` branch (brownfield-enabled-default schema clarification, synced into both the validators and docs schema copies so the re-sign carries the new `answers_schema_sha256`), fold forward the ce-release-0.3.1-rc2 fixes (nested-git-worktree skip in `surfaces_manifest._iter_dockerfiles`, version-agnostic URL-prefix assertions in `test_onboard_apply_live.py`), fix a stale `ce onboard --spec` step in the install-spec template to `ce install --spec` (refused by the CLI since #812), assemble the 0.3.2 CHANGELOG from 146 changelog fragments since the release/v0.3.1 tag (scrubbed of ce-ops# ticket references per the public-docs product-lens doctrine), publish the placeholder-signed 0.3.2 install spec to docs/llms-install.md (matching the ratified 0.3.1 release pattern), refresh the drifted brain-assertion evidence pin for validators/pyproject.toml, and stage placeholder-signed 0.3.2 release artifacts under `.ce/release-staging/0.3.2/`. Emits bytes-to-sign for the controller at `.ce/release-staging/0.3.2/INSTALL_SPEC_TO_SIGN`.
