# PR path manifest — ce-recipe-signer-parameterize · parameterize the llms-install verify recipe by the chosen signer

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-recipe-signer-parameterize
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Scope:
`release-stage --signing-key-id ce-root-v1` (ce-ops#352) correctly set the staged spec's
`signature.key_id` to the chosen signer and the operator signing command, but the embedded
verification RECIPE prose inside the rendered `docs/llms-install.md` still named the default
signer `ce-dev1-root-v1` in three places: the out-of-band DNS-anchor `grep` regex principal,
the `awk '$3 == "ce-dev1-root-v1"'` fingerprint selector, and the final
`ssh-keygen -Y verify -I ce-dev1-root-v1`. An installer following the spec's own recipe
verified against `-I ce-dev1-root-v1` while the signature was `ce-root-v1` → "Could not verify
signature" → install fails. This threads `signing_key_id` into the recipe so every principal
reference equals `signature.key_id`, with **no behavior change when omitted** (default stays
`ce-dev1-root-v1`, byte-identical). This is a source-only edit shipped under
`PYTHONPATH=validators`; no app/dependency wheel is rebuilt and the published
`docs/downloads/0.2.0/` mirror is untouched.

The signer-independent trust-root key FILE name (`ce-root-v1`, used as `curl .../keys/ce-root-v1`
and `ssh-keygen -Y verify -f ce-root-v1`) and the out-of-band anchor record name
(`_ce-root-v1.creator-engine.dev`, which carries per-principal fingerprints for BOTH principals)
are unchanged regardless of signer; only the *principal* the recipe greps-for and verifies-with
changes.

Per-file purpose (the closed path-set — 4 paths):
- **`.ce/pr-manifests/ce-recipe-signer-parameterize.md`** *(A)* — this carrier (self-inclusive).
- **`.ce/changelog/ce-recipe-signer-parameterize.md`** *(A)* — per-PR changelog fragment
  (kind: fixed).
- **`validators/creator_engine_validator/release_publish.py`** *(M)* — adds
  `_replace_recipe_principal(text, signing_key_id)` and calls it from
  `_render_placeholder_spec` (right after the `signature.key_id` field rewrite). It rewrites the
  default principal `SIGNING_KEY_ID` to the chosen `signing_key_id` in exactly the three recipe
  positions (DNS-anchor `grep` regex, `awk '$3 == ...'` selector, `ssh-keygen -Y verify -I`),
  each match-count-asserted to exactly one. When `signing_key_id == SIGNING_KEY_ID` (the default)
  it early-returns, so default output is byte-identical to prior behavior. The trust-root key
  file name and anchor record name are not touched.
- **`validators/tests/unit/test_release_publish.py`** *(M)* — extends the fixture
  `docs/llms-install.md` to include the verify recipe block (so the recipe rewrite is exercised),
  and adds `test_stage_signed_release_parameterizes_verify_recipe_principal`: staging with
  `signing_key_id="ce-root-v1"` makes all three recipe principals `ce-root-v1` with no leftover
  `ce-dev1-root-v1`, while the key file name and `_ce-root-v1.creator-engine.dev` anchor record
  are preserved; the default (omitted) still yields `ce-dev1-root-v1` in all three positions.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=097214929b250250e8725aab72561f5caf275a9ef26fdfde1816900a0bca6352

```text
.ce/changelog/ce-recipe-signer-parameterize.md
.ce/pr-manifests/ce-recipe-signer-parameterize.md
validators/creator_engine_validator/release_publish.py
validators/tests/unit/test_release_publish.py
```
