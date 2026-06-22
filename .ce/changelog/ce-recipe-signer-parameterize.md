---
slug: ce-recipe-signer-parameterize
date: 2026-06-22
kind: fixed
scope: release tooling (validators/creator_engine_validator release-stage)
issue: ce-ops#198
---

**`release-stage --signing-key-id` now parameterizes the embedded verify
recipe by the chosen signer, so an installer following the spec's own recipe
verifies against the actual `signature.key_id`.**

- **Fixed: the rendered `docs/llms-install.md` verify recipe hardcoded the
  default principal.** When staging with a non-default `--signing-key-id`
  (e.g. `ce-root-v1`), the staged spec's `signature.key_id` and the operator
  signing command correctly used the chosen signer, but the embedded
  verification recipe prose still named `ce-dev1-root-v1` in three places: the
  out-of-band DNS-anchor `grep` regex principal, the `awk '$3 == ...'`
  fingerprint selector, and the final `ssh-keygen -Y verify -I` principal. An
  installer following that recipe verified against the wrong principal
  (`-I ce-dev1-root-v1` vs a `ce-root-v1` signature) and failed with "Could
  not verify signature". Every recipe principal now equals the selected
  `signing_key_id`.
- **No behavior change for the default.** Omitting `--signing-key-id` (or
  passing `ce-dev1-root-v1`) is byte-identical to prior behavior. The
  signer-independent trust-root key FILE name (`ce-root-v1`) and the
  out-of-band anchor record name (`_ce-root-v1.creator-engine.dev`) are
  unchanged regardless of signer.
