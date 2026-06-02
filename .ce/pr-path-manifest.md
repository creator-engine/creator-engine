# PR path manifest — v3 G-iii (GitHub-native coordination)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below — the first end-to-end exercise of the carrier convention
(the G-iii dogfood: the diff-gate runs *active*, not neutral).

AUTHORIZED_PATHS_COUNT=7
AUTHORIZED_PATHS_SHA256=12897328d3b49763fa8ce8e099891bad6b87d42d0efe88d047b28399ccacbcf7

```text
.ce/pr-path-manifest.md
.github/CODEOWNERS
docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md
docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/github_repo_config.py
validators/tests/unit/test_github_repo_config.py
```
