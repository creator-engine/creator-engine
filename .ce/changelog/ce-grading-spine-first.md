---
slug: ce-grading-spine-first
date: 2026-06-26
kind: changed
scope: validator grading spine
issue: ce-ops#20
---

**Add spine-first grading safety foundations.**

- Adds deterministic spine verdict primitives that make semantic grades
  non-counting unless the deterministic spine is green.
- Adds mode/tier independence policy selection and review-evidence
  attestation checks for reviewer model, authorship obfuscation, and
  adversarial prompts.
- Binds approval-capability policy digests to active run mode and risk tier to
  reject replay across stricter policies.
- Extends review-evidence schema, template, examples, and focused unit tests.
