# PR path manifest — ce-release-signing-key-id · make the release signer identity selectable

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-release-signing-key-id
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Scope:
The signed-release staging tool hardcoded the signer identity
(`release_publish.py` `SIGNING_KEY_ID = "ce-dev1-root-v1"`). Both `ce-root-v1` and
`ce-dev1-root-v1` are valid trust anchors (`docs/keys/ce-root-v1` allowed_signers). This
adds a `--signing-key-id` option so the Operator can choose which valid anchor signs a
release, with **no behavior change when omitted** (default stays `ce-dev1-root-v1`).

The chosen `signing_key_id` is fail-closed to exactly `{ce-root-v1, ce-dev1-root-v1}`
(argparse `choices` at the CLI; `ALLOWED_SIGNING_KEY_IDS` re-validated inside
`stage_signed_release` for direct/library callers — rejected before any build/mutation).
It is threaded into the staged spec's `signature.key_id` (so it is part of the signed
canonical bytes), the `llms-install.canonical` mirror, the `release-stage-manifest.yml`
`signing_key_id:`, the operator `signing_command`, and the `SIGNING-INSTRUCTIONS.md`
`ssh-keygen -Y sign -I` identity. No app/dependency wheel is rebuilt: this is a
source-only edit shipped under `PYTHONPATH=validators`; the wheelhouse and the published
`docs/downloads/0.2.0/` release artifact are untouched (source/wheel parity verifies
build-from-source, not the published mirror).

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/pr-manifests/ce-release-signing-key-id.md`** *(A)* — this carrier (self-inclusive).
- **`.ce/changelog/ce-release-signing-key-id.md`** *(A)* — per-PR changelog fragment
  (type: feature).
- **`validators/creator_engine_validator/cli.py`** *(M)* — adds the `--signing-key-id`
  argument to the `release-stage` subparser (default `ce-dev1-root-v1`, choices
  `{ce-root-v1, ce-dev1-root-v1}`) and threads `args.signing_key_id` into
  `stage_signed_release(...)`.
- **`validators/creator_engine_validator/release_publish.py`** *(M)* — adds
  `ALLOWED_SIGNING_KEY_IDS`; adds `signing_key_id: str = SIGNING_KEY_ID` to
  `stage_signed_release`, `_render_placeholder_spec`, `_render_signing_instructions`, and
  `_stage_manifest`; validates the anchor fail-closed in `_validate_inputs`; replaces the
  three internal uses of the module-level `SIGNING_KEY_ID` (signing instructions, manifest
  `signing_key_id:`, signing command) and sets the spec `signature.key_id` (in the signed
  canonical bytes) from the passed value. The module constant remains the default so
  existing callers/tests are unaffected.
- **`validators/tests/unit/test_release_publish.py`** *(M)* — new/extended tests: default
  (omitted) still yields `ce-dev1-root-v1` across spec/canonical/manifest; staging with
  `signing_key_id="ce-root-v1"` carries `ce-root-v1` in spec + canonical + manifest +
  signing command and the canonical sha reflects it; an invalid id is rejected before the
  builder runs; the CLI rejects an out-of-choices id (exit 2) and threads the selected and
  default id into the pipeline.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=5e2097e216d7b8f5eedaad30f02173fb99babf6231106fb7e09fd60338759307

```text
.ce/changelog/ce-release-signing-key-id.md
.ce/pr-manifests/ce-release-signing-key-id.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/release_publish.py
validators/tests/unit/test_release_publish.py
```
