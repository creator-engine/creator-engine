# ce-ops#166 - Knowledge SSOT Slice 1

- Added explicit Knowledge-SSOT assertion fields for statement, assertion type,
  and verification method while preserving structured claim material.
- Projected canonical assertion fields through deterministic brain bootstrap so
  controller launch receives the shared truth payload at startup.
- Hardened drift verification for probe, static, and manual-attested assertion
  methods, including a real `harness_fan_out` probed capability assertion path.
- Carried forward the worker-spawn `TMPDIR` robustness fix needed for the full
  unit suite on this base.
