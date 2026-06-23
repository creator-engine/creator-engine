# PR path manifest - ce197-install-robustness

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce197-install-robustness
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`4956994` (`origin/main` at branch handoff).

- **Declared work class:** tiny

Scope:
ce-ops#197 PR-2 install.sh robustness. This slice handles the low-temp
wheelhouse staging fallback and clearer install-lock remediation UX only.

Per-file purpose:
- **`.ce/changelog/ce197-install-robustness.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce197-install-robustness.md`** *(A)* - this closed path-set carrier.
- **`docs/install.sh`** *(M)* - temp free-space probe/fallback and install-lock remediation text.
- **`validators/tests/unit/test_packaging_contract.py`** *(M)* - keep frozen mirror hash checks scoped to frozen mirror artifacts.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - subprocess coverage for low-temp fallback and lock-held UX.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=2d7d37f8175466f462e3f4134b749199d44cb7075f30948fa3a8f14afbc993d5

```text
.ce/changelog/ce197-install-robustness.md
.ce/pr-manifests/ce197-install-robustness.md
docs/install.sh
validators/tests/unit/test_packaging_contract.py
validators/tests/unit/test_v3_installer.py
```
