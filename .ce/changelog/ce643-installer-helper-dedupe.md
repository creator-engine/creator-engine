---
slug: ce643-installer-helper-dedupe
date: 2026-07-25
kind: fixed
scope: signed-release and main-HEAD venv installers
issue: ce-ops#643
---

**Share installer venv promotion mechanics and verify the live link.**

- Moved the duplicate venv target build, install lock, atomic promotion, and
  atomic state-write mechanics into one helper while retaining each route's
  existing artifact payload and state contents.
- Both installer routes now execute `cev3 --help` through the promoted `venv`
  symlink before state is written; a failed live-link check rolls promotion
  back and refuses the install.
- Added direct rollback coverage plus signed-release and main-HEAD route tests
  that bind the check to the live symlink path and retain their action tuples.
