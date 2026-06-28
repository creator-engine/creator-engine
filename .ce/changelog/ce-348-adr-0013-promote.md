---
slug: ce-348-adr-0013-promote
date: 2026-06-28
kind: governance
scope: docs/decisions (ADR governance record), validators (confidentiality gate hardening)
issue: ce-ops#348
---

**ratify + promote ADR-0013 (substrate-independent authority) and harden the public-docs confidentiality gate.**

- Promotes draft ADR-0013 to accepted status in docs/decisions/
- Adds ratification block (ratified by chmod735 on 2026-06-28)
- Abstracts all internal ce-ops private-repo URL references (19 removed) into descriptive
  phrases; adds a traceability note directing readers to the internal companion record
- Hardens `public_docs_confidentiality.py`: adds `github.com/creator-engine/ce-ops` pattern
  to FORBIDDEN_PATTERNS so the URL form of a private-repo link is caught in addition to the
  existing `ce-ops#NNN` shorthand pattern
- Adds test `test_offenses_reports_planted_private_repo_url` asserting the URL form is flagged
- Removes two residual confidentiality leaks from ADR-0013 found in independent review:
  - Replaces both occurrences of the confidential internal codename `skynet` (frontmatter
    `evidence_refs` line and body prose) with "CEO-Mode governed-autonomy ratification
    discussion"
  - Abstracts six `ce-ops-NNN` hyphen-form tag values in the YAML frontmatter
    (ce-ops-341, ce-ops-6, ce-ops-291, ce-ops-289, ce-ops-adr-0003, ce-ops-adr-0004)
    to descriptive slugs (run-mode-parameterization, strangeloop-lane, ceo-mode-automerge,
    socket-attestation, adr-0003, adr-0004)
- Further hardens `public_docs_confidentiality.py`: adds two new FORBIDDEN_PATTERNS:
  - `("confidential internal codename skynet", re.compile(r"(?i)skynet"))` — case-insensitive
  - `("confidential ce-ops hyphen ticket ref", re.compile(r"ce-ops-\d+"))` — catches
    hyphen-form issue refs that bypass the existing `ce-ops#\d+` pattern
- Extends `test_public_docs_confidentiality.py` with three new tests:
  `test_offenses_reports_planted_skynet_codename`,
  `test_offenses_reports_planted_ce_ops_hyphen_ticket_ref`, and
  `test_ce_ops_adr_hyphen_form_not_flagged_by_numeric_pattern` (verifies no false positive
  on `ce-ops-adr-0003` since the pattern requires digits, not letters, after `ce-ops-`)
