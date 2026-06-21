# ce-ops#176 — Brain Capability Probes

- Added the `brain_probe` registry for fresh Knowledge-SSOT capability probes
  with deterministic `present` / `absent` / `unknown` verdicts.
- Added `ce brain probe <name>` and `ce brain probe --all` CLI surfaces.
- Extended the brain assertion validator so active `probe:<name>` assertions
  are re-probed and fail closed when the stored verdict disagrees with reality.
