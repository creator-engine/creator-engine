---
slug: ce315-validator-suite-health
ticket: "#315"
type: fix
scope: validator test-suite health
---

Restores the W4-G10 validator suite health path for the full `validators/tests`
suite while coordinating with #312 / ADR-0010 for first-party app wheel removal.

- Updates the Ring-1 tool guard shim parent to honor `TMPDIR` through
  `tempfile.gettempdir()`.
- Fixes the adoption apply live unit test to use `tmp_path` isolation.
- Leaves the committed first-party validator wheel and its checksum out of this
  PR; #312 owns that artifact removal lane.
