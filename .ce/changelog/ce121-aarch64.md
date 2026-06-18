---
slug: ce121-aarch64
date: 2026-06-18
kind: fixed
scope: public installer / signed wheelhouse
issue: ce-ops#121
base: 5302520250c1510df9f8fac1d0b7268087228b4f
---

Adds Linux/aarch64 support to the public CE v3 installer and 0.2.0 wheelhouse.

- Accepts `Linux/aarch64` and `Linux/arm64` in the Python and shell bootstrap
  platform gates while keeping non-Linux and other architectures fail-closed.
- Adds platform-aware `required_wheels` and `python_acquisition` selection so
  Linux x86_64 keeps the existing native wheels and Linux aarch64 pulls the
  aarch64 PyYAML, rpds-py, and uv artifacts.
- Adds aarch64 wheels to both `validators/wheelhouse/` and the Pages mirror at
  `docs/downloads/0.2.0/`; pure-Python wheels remain shared.
- Rebuilds `creator_engine_validator-0.2.0-py3-none-any.whl` from current source
  and re-pins both `SHA256SUMS` files.
- Updates `docs/llms-install.md` with `content_sha256`
  `2d2d4ef30da2371e3a5f78cbe23a401386658cc28dd9247e5c932b57bc6d59df`,
  mirror `sha256s_sha256`
  `e6460c09e925576bfe39ae9465fea1e589df182e318b520d6867be0cb145f86c`,
  and the literal unsigned placeholder `value: <RESIGN-REQUIRED-ce-root-v1>`.
  Operator re-sign and Pages publish remain separate gated steps.
