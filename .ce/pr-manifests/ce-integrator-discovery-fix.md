# PR path manifest — ce-ops#218 · Integrator daemon live discovery fixes

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-integrator-discovery-fix` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=b48e8543d23c9728eb14dce89a9a520fd40cb3988d2b1019dadd8def298b3c0a

```text
.ce/changelog/ce-integrator-discovery-fix.md
.ce/pr-manifests/ce-integrator-discovery-fix.md
validators/creator_engine_validator/forge/integrator_belt.py
validators/tests/unit/test_integrator_belt.py
```
