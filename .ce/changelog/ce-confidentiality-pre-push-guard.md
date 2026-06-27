# ce-ops#306 — public-docs confidentiality: catch leaks before push

Root-fix the recurring public-docs confidentiality leak (worker-authored doc PRs
dropping `ce-ops#NNN` ticket refs / internal host identifiers into `docs/**`,
caught only at CI by the fail-closed guard and blocking the merge queue).

- **Single-sourced the rule.** Extracted the confidentiality rule (public-doc
  file set, forbidden patterns, `KNOWN_PENDING` debt-ratchet allowlist, offense
  formatter, standing reminder) into one module,
  `creator_engine_validator.public_docs_confidentiality`. The existing CI guard
  test is now a thin caller of that module, so there is exactly one source of
  truth and no drift risk.
- **Fast standalone CLI check.** Added `scan-public-docs-confidentiality`
  (sub-second, no network, no token) backed by the same module.
- **Pre-push enforcement.** Wired that check into `ce validate-pr` (local PR
  preflight), so a leak is caught BEFORE push even when the author skips the
  full pytest suite.
- **Standing reminder, folded in.** The check's failure remediation surfaces
  verbatim: "If you touch docs/**, run the confidentiality guard before push;
  ZERO ce-ops# refs in public docs."
