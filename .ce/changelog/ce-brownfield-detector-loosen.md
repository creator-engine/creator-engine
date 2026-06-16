---
slug: ce-brownfield-detector-loosen
date: 2026-06-16
kind: fixed
scope: install / onboard --apply
issue: ce-ops#90
---

**Loosen the already-CE workflow detector so a repo whose CE validate workflow
uses a known legacy filename (the flagship's `validate.yml`) is recognised as
already-CE — without weakening the byte-level anti-tamper pin.**

The plain-join already-CE detector (`repo_is_already_ce_governed` and its
`github_workflow_install` verify leg) hard-pinned a SINGLE workflow
filename+digest: `.github/workflows/ce-validate.yml` at one fixed
`CE_WORKFLOW_SHA256`. An already-CE repo whose CE validate workflow lives at a
different filename — e.g. the flagship `creator-engine/creator-engine`'s legacy
`.github/workflows/validate.yml` — got a 404, so detection returned `False` and
`onboard --apply` dead-ended at the `e2_brownfield_seam_unavailable` refusal even
though the repo IS CE-governed.

The fix replaces the single cosmetic filename+digest coupling with
**governance-signal detection** (`detect_ce_workflow` over a `KNOWN_CE_WORKFLOWS`
set of `CeWorkflowIdentity` byte-pins). A repo is workflow-CE iff ANY known
identity is present at its EXACT pinned digest — the canonical `ce-validate.yml`
OR the flagship's legacy `validate.yml`.

- The validator-artifact byte-pin is PRESERVED per identity (the same read the
  install leg verifies with): a tampered, byte-drifted, non-CE, or absent
  workflow matches NO identity and detection fails closed to the brownfield/E3
  refuse — the anti-tamper guarantee is unchanged, only the filename coupling is
  dropped (loosen ≠ weaken).
- Net effect: `repo_is_already_ce_governed` returns `True` for the flagship
  (`validate.yml`) AND the canonical `ce-validate.yml`, while still rejecting
  tampered/non-CE/absent workflows. The plain-join `onboard --apply` now COMPLETES
  for the legacy-filename repo (verify-only; the live workflow file is never
  overwritten).

Out of scope (deferred Option B): renaming the flagship's `validate.yml` →
`ce-validate.yml`. Greenfield onboarding is unchanged — it still installs and
verifies the canonical `ce-validate.yml` at its pinned digest.
