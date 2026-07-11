# PR path manifest — ce-terra-default-flip · Canonicalize contained-seat launcher defaults to Terra

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-terra-default-flip` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=1a7aa1eda1d711994ad6a666c333b95be67972684d1ce08935672f473655411c

```text
.ce/changelog/ce-terra-default-flip.md
.ce/pr-manifests/ce-terra-default-flip.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/README.md
deploy/vps-runsc/run-vps-runsc.sh
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_launcher.py
```
