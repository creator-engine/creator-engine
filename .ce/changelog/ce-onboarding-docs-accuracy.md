---
slug: ce-onboarding-docs-accuracy
date: 2026-07-05
kind: docs
scope: public onboarding docs
issue: no-ticket
---

**Correct public onboarding command guidance.**

- **Declared work class:** story

- Rewrite the solo developer onboarding guide around the real first-run flow: `ce onboard` first, then `ce launch` after onboarding.
- Add day-one prerequisites for a coding-agent CLI and `.hermes/` gitignore coverage.
- Correct stale install-spec examples to use `ce install --spec`.
- Shrink the public-doc confidentiality allowlist for cleaned onboarding contract references.

CE-TEST-COUPLING-EXEMPT: existing public-doc confidentiality ratchet tests cover allowlist shrink behavior; this change only removes stale allowlist entries after cleaning docs.
