# PR path manifest - ce-ops#322 schema reference doc-autogen

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21
convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir
.ce/pr-manifests --head-ref ce322-doc-autogen-schema-reference` and requires
this PR's diff to equal exactly the authorized path-set below. This carrier
lists itself.

- **Declared work class:** story

Scope:
ce-ops#322 adds doc-autogen Tier-1 generator #2 for `schemas/*.yaml` into the
internal reference tree, plus the matching generate-then-verify validator guard.
The change is limited to the schema-reference generator, generated internal
reference artifact, validator registration/check, focused tests, changelog, and
this manifest.

Excluded:
No changes to `tools/egress-broker/**`, systemd units, `.claude/skills/**`,
README, `docs/guide/**`, `.github/**`, `ce_cli.py`,
`scripts/gen_cli_reference.py`, or the CLI-reference check/tests.

Per-file purpose:
- **`.ce/changelog/ce322-doc-autogen-schema-reference.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce322-doc-autogen-schema-reference.md`** *(A)* - this carrier.
- **`.ce/reference/schemas.generated.md`** *(A)* - generated internal schema reference artifact.
- **`scripts/gen_schema_reference.py`** *(A)* - deterministic schema-reference generator with `--write`/`--check`.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - register the schema-reference autogen sync check near the existing CLI-reference autogen guard.
- **`validators/creator_engine_validator/checks/schema_reference_autogen_sync.py`** *(A)* - read-only generate-then-verify validator check.
- **`validators/tests/unit/test_schema_reference_autogen_sync.py`** *(A)* - focused unit coverage for the generator/check contract.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=2ee446e16b3155a1e495dda48c88df926c7d2bb364a612cadc62155228054592

```text
.ce/changelog/ce322-doc-autogen-schema-reference.md
.ce/pr-manifests/ce322-doc-autogen-schema-reference.md
.ce/reference/schemas.generated.md
scripts/gen_schema_reference.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/schema_reference_autogen_sync.py
validators/tests/unit/test_schema_reference_autogen_sync.py
```
