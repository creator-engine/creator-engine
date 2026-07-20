---
slug: ce636-brain-correct-statement-preservation
date: 2026-07-20
kind: fixed
scope: brain correction runtime
issue: ce-ops#636
---

**Preserve doctrine statements through omitted-statement brain corrections.**

- `ce brain correct` now carries the active predecessor's statement into its
  successor when `--statement` is omitted, instead of replacing doctrine
  wording with a generic rendering of the corrected structured claim.
- Explicit `--statement` values still replace the wording. Existing callers
  that omit the option remain compatible and no longer silently hollow active
  SSOT doctrine.
- CLI coverage proves the active successor retains a deliberately non-template
  predecessor statement and fails when the preservation guard is removed.
- Regenerated the canonical internal CLI reference from the supported generator
  so the changed `ce brain correct --statement` help remains byte-synchronized.
