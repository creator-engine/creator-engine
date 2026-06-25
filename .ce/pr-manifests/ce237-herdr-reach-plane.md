# PR path manifest — ce237-herdr-reach-plane

CI runs verify-path-manifest; base..HEAD must equal the authorized set; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=6284bcc752f8986254f7c18de7db4c62a46266bc638d433de275ccac4acd00ad

```text
.ce/changelog/ce237-herdr-reach-plane.md
.ce/pr-manifests/ce237-herdr-reach-plane.md
docs/operations/HERDR_OPERATOR_REACH_PLANE.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/unit/test_ce_herdr_cli.py
validators/tests/unit/test_herdr_session.py
```
