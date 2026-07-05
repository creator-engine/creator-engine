---
slug: ce-s1a-docker-runner-backend
date: 2026-07-05
kind: added
scope: runtime/runner
issue: ce-s1a-docker-runner-backend
---

**Add plain Docker contained runner backend.**

- Added a `docker` runner backend that uses the runtime policy's digest-pinned
  image, adds no Docker `--runtime=` flag, and bind-mounts only the policy mount
  manifest.
- Registered `docker` through runtime policy resolution and the visible runtime
  bridge while preserving raw-fallback refusals for unsupported backends.
- Extended the runtime-policy contract with `docker` and the ratified
  `controller` role enum addition, with hermetic unit coverage for translation,
  refusal, and bridge composition.
- Push-readiness follow-up: baselined the `runner.docker_backend` v3 taxonomy
  classification in `_versions.py` and regenerated the CLI/schema autogen
  reference docs so the version-boundary and autogen-sync gates pass clean.
- Review-pickup follow-up: locked the latent `network=='proxy'` docker-argv
  branch to fail closed (docker-side egress mediation is not implemented) with
  a regression test, and added an Operator-ratified (2026-07-05 day-arc)
  decision citation next to the `controller` role-enum addition in the schema
  and contract doc (see those files for the ticket reference).
