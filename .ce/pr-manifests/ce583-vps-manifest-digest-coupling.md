# PR path manifest — VPS manifest digest coupling

This carrier confines the VPS runsc image expectation to the manifest-owned
contract and tests that the launcher resolves an alternative valid manifest.
The manifest lists itself.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=3c501c0e314967671fc28f64cd8974e5fdb72a2e833c62762d3ab456832873be

```text
.ce/changelog/ce583-vps-manifest-digest-coupling.md
.ce/pr-manifests/ce583-vps-manifest-digest-coupling.md
validators/tests/unit/test_vps_runsc_launcher.py
```
