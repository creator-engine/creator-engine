# PR path manifest - ce97-test-notification-hygiene

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce97-test-notification-hygiene

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified scope:
Controller dispatch for ce-ops#97 on 2026-06-19: suppress resource-bound/OOM
integration-test desktop notification leaks on dogfood GNOME desktops. Do not
touch trust-root, served install, or public download paths.

Base:
`d2d22b0e3a52a551ec8fbc79571ab3e806353b40` (`origin/main` at branch creation).

The changes:
- `test_resource_bound_systemd.py` no longer runs live `systemd-run` OOM tests
  just because user-level cgroup delegation is available. The live tests now
  require `CI=1` or `CE_RUN_RESOURCE_BOUND_SYSTEMD_TESTS=1` on a non-desktop
  host.
- Desktop session variables (`DISPLAY`, `WAYLAND_DISPLAY`,
  `XDG_CURRENT_DESKTOP`, `DESKTOP_SESSION`) force the live OOM tests to skip,
  preventing GNOME application-stopped/OOM notifications during ordinary local
  test runs.
- Regression tests assert the desktop refusal, opt-in requirement, and
  headless CI/explicit opt-in acceptance behavior.

Per-file purpose (the closed path-set - 3 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce97-test-notification-hygiene.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/ce97-test-notification-hygiene.md`** *(A)* - this
  carrier.
- **`validators/tests/integration/test_resource_bound_systemd.py`** *(M)* -
  notification-hygiene gate and regression tests for live systemd/OOM tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=a58da0368b683da3f1190b2851e6246c5c2e0acdcbf7ce049d314fcd8484b920

```text
.ce/changelog/ce97-test-notification-hygiene.md
.ce/pr-manifests/ce97-test-notification-hygiene.md
validators/tests/integration/test_resource_bound_systemd.py
```
