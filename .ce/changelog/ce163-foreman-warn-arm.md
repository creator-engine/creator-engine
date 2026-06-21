# ce-ops#163 G6 — Foreman WARN-Only Hook Observation

- Armed `hook_check.py` to observe foreman implementation work in
  delegation-required mutation classes as advisory allow decisions with
  `wouldHaveDenied: true`.
- Forwarded the launch-pinned brain-bootstrap `seat_class` into `hook-check`:
  a verified worker payload suppresses the foreman warning, while invalid
  payload evidence fails closed to foreman.
- Preserved existing hard-denies for restricted mechanics and credential-like
  paths; those decisions still win before foreman observation and still write
  refusal-chain records.
- Added focused unit and CLI coverage for foreman warnings, worker and
  coordination no-warning paths, policy-ref resolution, and governed `git push`
  hard-deny precedence.
- Refreshed the generated build identity for the current base; ADR-0010 keeps
  first-party app-wheel parity out of this author-side source PR.
