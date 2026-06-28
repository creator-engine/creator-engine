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
