# PR path manifest — F-1.2+F-1.3 suite disk-headroom admission + scratch reaper slice 1

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-f1-storage-admission
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Design ref: `VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710.md §C/F-1.2+F-1.3`

- **Declared work class:** S

Per-file purpose (closed path-set — 9 paths; carrier is self-inclusive):

- **`.ce/changelog/ce-f1-storage-admission.md`** *(A)* — per-PR changelog entry.
- **`.ce/pr-manifests/ce-f1-storage-admission.md`** *(A)* — this carrier (self-inclusive).
- **`deploy/storage-reaper/ce-storage-reaper.service`** *(A)* — systemd oneshot service template for the reaper (F-1.3).
- **`deploy/storage-reaper/ce-storage-reaper.timer`** *(A)* — daily systemd timer template (Persistent=true, RandomizedDelaySec=1800).
- **`deploy/storage-reaper/reap-scratch.sh`** *(A)* — deterministic scratch reaper script: sweeps /var/tmp/wt-* (48h), /var/tmp/pt-* (24h), docker dangling images; --dry-run flag; shellcheck-clean (F-1.3 slice 1).
- **`validators/creator_engine_validator/disk_headroom.py`** *(A)* — shared headroom module: check_headroom(), free_gb(), DiskHeadroomError, effective_min_free_gb(); CE_SUITE_MIN_FREE_GB env override (F-1.2).
- **`validators/creator_engine_validator/pr_preflight.py`** *(M)* — minimal integration: imports disk_headroom, adds DISK_HEADROOM_CHECK_NAME constant, disk_headroom_gate() closure, and a fast-fail check just before the baseline-diff test command stage (F-1.2).
- **`validators/tests/unit/test_disk_headroom.py`** *(A)* — 18 unit tests: statvfs mock seam, threshold pass/fail, env override, DiskHeadroomError attributes, preflight integration (block before pytest, pass with adequate disk).
- **`validators/tests/unit/test_reap_scratch.py`** *(A)* — 8 subprocess tests: --dry-run exit 0, aged-fixture detection (wt-* 50h, pt-* 30h), fresh-dir exclusion, no-delete guarantee, unknown-flag exit.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=a87efa6cc029b9350c30ed52cb51e0361fe950a25bae6c3c1a456fc703e2fea2

```text
.ce/changelog/ce-f1-storage-admission.md
.ce/pr-manifests/ce-f1-storage-admission.md
deploy/storage-reaper/ce-storage-reaper.service
deploy/storage-reaper/ce-storage-reaper.timer
deploy/storage-reaper/reap-scratch.sh
validators/creator_engine_validator/disk_headroom.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_disk_headroom.py
validators/tests/unit/test_reap_scratch.py
```
