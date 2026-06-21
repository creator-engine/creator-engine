# ce-ops#177 — Brain Drift CI

- Added the `ce_brain_drift` governance check for active Knowledge-SSOT brain assertions.
- Added `ce brain verify --drift` for on-demand drift verification.
- Wired CI to run the drift check over `.ce/state` on every validation run.
- Added offline probe and local-evidence tests for pass, drift, fail-closed, and deterministic output paths.
