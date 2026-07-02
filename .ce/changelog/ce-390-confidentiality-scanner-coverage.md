---
slug: ce-390-confidentiality-scanner-coverage
date: 2026-07-02
kind: fixed
scope: public-repo confidentiality scanner
issue: ce-ops#390
---

**Widen public-repo confidentiality scan to all tracked text files.**

Widened the public-repo confidentiality scanner from a docs-only extension allowlist to full coverage of all git-tracked text files, closing a gap where confidential ce-ops#N ticket references or other forbidden patterns could leak through non-doc file types.

- Full-coverage widening: scan now walks all tracked text files (binary-sentinel skipped) instead of a fixed docs-suffix allowlist.
- Structural carrier exemption accepts both the bare `ce-ops#N` and the repo-qualified `creator-engine/ce-ops#N` forms in generated changelog frontmatter (`issue:` line) and PR-manifest headers only; the same ticket ref appearing in body prose still fails closed.
- Scan errors (unreadable file, forbidden-pattern match failure) fail closed rather than being silently skipped.
- Pre-existing tracked-text baseline hits are allowlisted via the existing debt-ratchet mechanism; remediation is tracked internally, not via a new external program.
- Adds 3 new tests proving qualified-form frontmatter/header refs pass with an empty allowlist, plus 3 companion tests for the existing bare-form + qualified-body-prose-fails coverage.
