---
slug: ce-release-signing-key-id
date: 2026-06-22
kind: added
scope: release tooling (validators/creator_engine_validator release-stage)
issue: ce-ops
---

**`release-stage` can now select which valid root trust anchor signs a release
via `--signing-key-id`, with no behavior change when omitted.**

- **New `--signing-key-id` option on `ce ... release-stage`.** Default is the
  prior hardcoded `ce-dev1-root-v1` (omitting it is byte-identical to today).
  Allowed values are exactly the two ratified trust anchors
  `{ce-root-v1, ce-dev1-root-v1}` (argparse `choices`); anything else is
  rejected fail-closed before any build runs. The library entrypoint
  `stage_signed_release(signing_key_id=...)` re-validates the anchor against
  `ALLOWED_SIGNING_KEY_IDS` for direct/non-CLI callers.
- **The chosen anchor becomes part of the signed bytes.** It is threaded into
  the staged spec's `signature.key_id`, the `llms-install.canonical` mirror the
  Operator signs, the `release-stage-manifest.yml` `signing_key_id:`, the
  emitted operator `signing_command`, and the `SIGNING-INSTRUCTIONS.md`
  `ssh-keygen -Y sign -I` identity — so the canonical-spec hash reflects the
  selected signer.
