# PR path manifest — `ce-support-agent-p0`

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`). The path-manifest fidelity
gate requires this PR's `base..HEAD` diff (computed `--no-renames`) to equal
exactly the authorized path-set below; the repo-wide fidelity scan requires the
declared count and SHA256 to match the fenced block.

- **Declared work class:** feature

Ticket: ce-ops#317 — `ce ask` support-agent P0 foundations (corpus allowlist +
read-only profile + honest scaffold + system-prompt contract). Design:
`.ce/state/research/CE_SUPPORT_AGENT_PLAN_20260627.md`. Model wiring + eval are
later tickets.

Scope adjudication (IN):
- P0.1 corpus allowlist: `support_corpus_allowlist.yaml` (manifest) +
  `support_corpus.py` (product-lens ∩ confidentiality-clean intersection,
  reusing `public_docs_confidentiality`).
- P0.3 read-only profile: `support_profile.py` (deny writes/exec/network/`ce`
  subcommands; corpus-root read allowlist; secret-path deny; reuses
  `hook_check`).
- P0.4 `ce ask` / `ce support` dev-gated scaffold: `ce_cli.py` registration +
  `support_runtime.py` honest scaffold; `cli.py` + `pr_preflight.py` wire the
  new `scan-support-corpus` fail-closed check.
- P0.5 system-prompt contract: `support_system_prompt.md`.
- Version-boundary classification for the two new v1 subcommand runtimes
  (`_versions.py`) + count/inventory guard updates
  (`test_version_boundary.py`, `test_v1_docs_reconciliation.py`).
- Tests: `test_support_agent_p0.py`. Changelog: `ce317-support-agent-p0.md`.
  This carrier (lists itself).

Authorized path-set:

CE317_PATHS_COUNT=14
CE317_PATHS_SHA256=f627e0c16adc58efb9170c8375caaf0441389d2922df6e2e7bc6bf0e487e33d2

```text
.ce/changelog/ce-support-agent-p0.md
.ce/pr-manifests/ce-support-agent-p0.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/pr_preflight.py
validators/creator_engine_validator/support_corpus.py
validators/creator_engine_validator/support_corpus_allowlist.yaml
validators/creator_engine_validator/support_profile.py
validators/creator_engine_validator/support_runtime.py
validators/creator_engine_validator/support_system_prompt.md
validators/tests/unit/test_support_agent_p0.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_boundary.py
```
