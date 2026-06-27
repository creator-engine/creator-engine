# PR path manifest - fix-ce315-b1-anchor-footgun

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref fix/ce315-b1-anchor-footgun --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** story

Scope:
ce-ops#324 (B1 anchor footgun, found in the 0.3.0 release rehearsal). Inverts the
Phase A release-stage signing-anchor parameterization so the public trust root
`ce-root-v1` — the principal the `docs/llms-install.md` self-verify recipe is
authored for — is the canonical, no-recipe-rewrite default, and a recipe rewrite
fires only for the dev/test anchor `ce-dev1-root-v1`. Adds a fail-closed guard
asserting the staged `signature.key_id` equals both the requested anchor and the
recipe's parsed verify principal. The Operator-held root-signing hard refusal is
untouched (no auto-signing).

Per-file purpose:
- **`.ce/changelog/fix-ce315-b1-anchor-footgun.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/fix-ce315-b1-anchor-footgun.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/cli.py`** *(M)* - `--signing-key-id` default flipped to `ce-root-v1` (release-stage + release).
- **`validators/creator_engine_validator/release_publish.py`** *(M)* - inverted anchor default + recipe rewrite, added `_assert_anchor_recipe_match` fail-closed guard and anchor-aware signing instructions.
- **`validators/tests/unit/test_release_phase_a.py`** *(M)* - fixture recipe authored for `ce-root-v1`.
- **`validators/tests/unit/test_release_publish.py`** *(M)* - inverted default/dev anchor coverage + new guard tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=4b1a2459a779ec46b0fee67984b4b35a7a895de075fdc5eb7231b583b5b4601c

```text
.ce/changelog/fix-ce315-b1-anchor-footgun.md
.ce/pr-manifests/fix-ce315-b1-anchor-footgun.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/release_publish.py
validators/tests/unit/test_release_phase_a.py
validators/tests/unit/test_release_publish.py
```
