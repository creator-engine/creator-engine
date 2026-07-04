---
slug: ce-445-g8-dockerfile-offline-setuptools
date: 2026-07-04
kind: fix
scope: deploy
issue: ce-ops#445
---

**Install offline setuptools before canonical wheel builds.**

- Copy `validators/wheelhouse-dev` into both canonical-image wheel-builder stages and install `setuptools` with `--no-index` before building the validator wheel with unchanged `--no-deps --no-build-isolation` flags.
- Fix `build-image.sh` staging: `stage_context()` and `print_stage_context_commands()` now include `wheelhouse-dev` in the staged context dir so `COPY validators/wheelhouse-dev` in the Dockerfile resolves correctly.
