# PR path manifest - ce316-doc-autogen-cli-reference

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce316-doc-autogen-cli-reference --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#316 adds the Tier-1 slice of the CE doc-autogen program: a deterministic
`ce --help` -> CLI-reference generator (`scripts/gen_cli_reference.py`) with a
`@register`'d generate-then-verify guard (`cli_reference_autogen_sync`,
`VAL-AUTOGEN-STALE-CLI`) that rides the existing `pull_request` validator gate,
plus the generated committed reference `.ce/reference/cli.md` and its unit
coverage. Design: `.ce/state/research/CE_DOC_AUTOGEN_DESIGN_20260627.md`.

Note:
The generator introspects the `ce` argparse tree read-only; `ce_cli.py` is not
edited. The projection omits internal command groups and `argparse.SUPPRESS`
commands exactly as `ce --help` does, and normalizes the one host-dependent
default (`validate-pr --test-command`'s `sys.executable`) to a stable
`<python>` placeholder for cross-host byte-parity. The artifact is committed to
the INTERNAL `.ce/reference/` tree (NOT the served public `docs/` tree): a
faithful projection of every `help=` string carries internal references
(ce-ops# tickets, seat ids) the read-only generator must not rewrite, so it is
kept off the public-docs confidentiality surface (design §3.3).

Per-file purpose:
- **`.ce/changelog/ce316-doc-autogen-cli-reference.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce316-doc-autogen-cli-reference.md`** *(A)* - this closed path-set carrier.
- **`.ce/reference/cli.generated.md`** *(A)* - the generated, committed `ce` CLI reference (whole-file byte-parity; `<!-- ce-autogen -->` provenance header; internal-only `.generated.` artifact excluded from work-sizing).
- **`scripts/gen_cli_reference.py`** *(A)* - deterministic `project(parser)->markdown` generator with `--check`/`--write`.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - registers the new check in the offline gate.
- **`validators/creator_engine_validator/checks/cli_reference_autogen_sync.py`** *(A)* - the generate-then-verify guard (`VAL-AUTOGEN-STALE-CLI`).
- **`validators/tests/unit/test_cli_reference_autogen_sync.py`** *(A)* - focused unit coverage proving generate-then-verify (fails-on-stale, passes-on-fresh).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=de8b4b46d28ff9697d63e3dba7e7e0996f703e52149d73cdd951ca0b23f67577

```text
.ce/changelog/ce316-doc-autogen-cli-reference.md
.ce/pr-manifests/ce316-doc-autogen-cli-reference.md
.ce/reference/cli.generated.md
scripts/gen_cli_reference.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/cli_reference_autogen_sync.py
validators/tests/unit/test_cli_reference_autogen_sync.py
```
