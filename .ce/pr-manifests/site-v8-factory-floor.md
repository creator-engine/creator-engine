# PR path manifest - site-v8-factory-floor

Closed manifest for the v8 "The Factory Floor" website redesign (ce-ops#51).
Replaces the live `docs/index.html` (v7 → v8), snapshots the outgoing v7 bytes
to `site-archive/index-v7-the-choice.html` + promotes v8 in the archive ledger
(site-versioning policy), adds the transparent nav-logo asset, and re-pins the
cockpit theme to the v8 palette (`v3_cockpit.py` THEME + the serve test) to keep
the site↔cockpit single-source-of-truth invariant. Rebuilds the validator app
wheel from branch source and re-pins the wheelhouse checksum so packaged cockpit
theme bytes match source.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=abb3b68f5beaa12037fe07c8da568e2e9adc6b8e6a7269098e0c8b79245a62a8

```text
.ce/changelog/site-v8-factory-floor.md
.ce/pr-manifests/site-v8-factory-floor.md
docs/assets/ce-logo-v2-weldarm-transparent.svg
docs/index.html
site-archive/README.md
site-archive/index-v7-the-choice.html
validators/creator_engine_validator/v3_cockpit.py
validators/tests/unit/test_v3_cockpit_serve.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
