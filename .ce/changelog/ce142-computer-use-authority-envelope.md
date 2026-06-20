---
slug: ce142-computer-use-authority-envelope
date: 2026-06-20
kind: added
scope: computer-use authority envelope
issue: ce-ops#142
---

Added the Phase 1 computer-use/UI side-effect authority envelope substrate:
schema, prose contracts, examples, and the `ce_computer_use_authority_envelope`
validator check. The envelope is closed to account rename, app rename, and
console setting mechanics, binds to a ratified prompt digest, enforces DoR
completeness, and rejects token/2FA/credential material.

Live Ring-2 hook honoring remains a Phase 2 follow-up.
