# PR path manifest - site-v8-factory-floor

Closed manifest for the v8 "The Factory Floor" website redesign (ce-ops#51).
Replaces the live `docs/index.html` (v7 → v8), snapshots the outgoing v7 bytes
to `site-archive/index-v7-the-choice.html` + promotes v8 in the archive ledger
(site-versioning policy), adds the transparent nav-logo asset, and re-pins the
cockpit theme to the v8 palette (`v3_cockpit.py` THEME + the serve test) to keep
the site↔cockpit single-source-of-truth invariant. No wheel rebuild (theme
constants only; ships from source).

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=1ba3491bb8bcee4ca98b8271ac01cee7c05461f6a68f59a0748d6f8b76f71b06

```text
.ce/changelog/site-v8-factory-floor.md
.ce/pr-manifests/site-v8-factory-floor.md
docs/assets/ce-logo-v2-weldarm-transparent.svg
docs/index.html
site-archive/README.md
site-archive/index-v7-the-choice.html
validators/creator_engine_validator/v3_cockpit.py
validators/tests/unit/test_v3_cockpit_serve.py
```
