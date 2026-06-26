# ce-ops#244 - Worker Tier Contract

- Added a machine-readable governed Worker tier contract for in-process
  researcher, implementer, and reviewer workers.
- Worker spawn records now carry inherited Ring-1/refusal/envelope governance,
  no ambient credentials, prohibited capabilities, role-surface references, and
  structured-result return requirements.
- Added a registered worker-tier contract check and wired foreman-routed
  implementation delegation through it so old or over-broad worker records fail
  closed.
- Added regression coverage for conforming records, missing contracts,
  prohibited capabilities, depth bounds, role-surface presence, and hook-check
  delegation enforcement.
