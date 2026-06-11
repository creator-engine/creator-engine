# PR path manifest - v3.5 suite-speed gate

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
`~/ce-launch/v35-suite-speed/v35-suite-speed-gate-RATIFIED-20260611.md`
(sha256 `52a9dffbbe88c418c635d9b94430a8792d84fdc581313cb752304b9dc93e6aff`;
Operator-ratified 2026-06-11, Section 6 fork resolutions binding).

Implementer mandate:
`~/ce-launch/v35-suite-speed/SUITE_SPEED_IMPL_MANDATE.md`
(sha256 `81500d34008eae1d3d73ce051944b22b6948468330c670b9c0629df25b86b43d`).

Per-file purpose (the closed 21-row manifest):
- **`.github/workflows/validate.yml`** *(M)* - add `-n auto --dist loadgroup` to the single
  pytest invocation line.
- **`validators/requirements-dev.txt`** *(M)* - add test-only `pytest-xdist==3.8.0` and
  `execnet==2.1.2`; runtime packaging checks do not read this file.
- **`validators/wheelhouse-dev/pytest_xdist-3.8.0-py3-none-any.whl`** *(NEW)* - vendored xdist
  wheel for offline CI dev installs.
- **`validators/wheelhouse-dev/execnet-2.1.2-py3-none-any.whl`** *(NEW)* - vendored xdist
  transitive dependency for offline CI dev installs.
- **`validators/tests/conftest.py`** *(M)* - register `xdist_group` and add session-scoped
  `check-examples` and version-boundary scan fixtures.
- **`validators/tests/integration/test_lane_launch_tmux.py`** *(M)* - group the real tmux test as
  `real-tmux`.
- **`validators/tests/integration/test_resource_bound_systemd.py`** *(M)* - group the live
  user-systemd file as `user-systemd`.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - consume session-scoped real-package
  scan fixtures.
- **`validators/tests/unit/test_ce_check_cli.py`** *(M)* - retarget the default-dot-path equality
  test to a small temporary governed tree.
- **`validators/tests/unit/test_cli.py`** *(M)* - consume the shared `check_examples_result` fixture
  and group the test as `check-examples-sweep`.
- **`validators/tests/integration/test_architect_evidence_examples.py`** *(M)* - shared
  `check-examples` fixture consumer.
- **`validators/tests/integration/test_ce_runtime_evidence_examples.py`** *(M)* - shared
  `check-examples` fixture consumers.
- **`validators/tests/integration/test_ce_runtime_policy_examples.py`** *(M)* - shared
  `check-examples` fixture consumer.
- **`validators/tests/integration/test_completion_report_examples.py`** *(M)* - shared
  `check-examples` fixture consumer.
- **`validators/tests/integration/test_container_instance_examples.py`** *(M)* - shared
  `check-examples` fixture consumer.
- **`validators/tests/integration/test_handoff_examples.py`** *(M)* - shared `check-examples`
  fixture consumer.
- **`validators/tests/integration/test_implementer_evidence_examples.py`** *(M)* - shared
  `check-examples` fixture consumer.
- **`validators/tests/integration/test_review_evidence_examples.py`** *(M)* - shared
  `check-examples` fixture consumer.
- **`validators/tests/integration/test_worker_container_policy_examples.py`** *(M)* - shared
  `check-examples` fixture consumer.
- **`validators/tests/integration/test_worktree_lease_examples.py`** *(M)* - shared
  `check-examples` fixture consumer.
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier.

- **base:** `7b03d62349d115d42fc1d50fb5b863262d98c46a` (origin/main post-#196, per mandate).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=21

AUTHORIZED_PATHS_SHA256=c2e1c6a9bc72df2630a836b4449f48face2730cc86701aefb6c736f1091c85a7

```text
.ce/pr-path-manifest.md
.github/workflows/validate.yml
validators/requirements-dev.txt
validators/tests/conftest.py
validators/tests/integration/test_architect_evidence_examples.py
validators/tests/integration/test_ce_runtime_evidence_examples.py
validators/tests/integration/test_ce_runtime_policy_examples.py
validators/tests/integration/test_completion_report_examples.py
validators/tests/integration/test_container_instance_examples.py
validators/tests/integration/test_handoff_examples.py
validators/tests/integration/test_implementer_evidence_examples.py
validators/tests/integration/test_lane_launch_tmux.py
validators/tests/integration/test_resource_bound_systemd.py
validators/tests/integration/test_review_evidence_examples.py
validators/tests/integration/test_worker_container_policy_examples.py
validators/tests/integration/test_worktree_lease_examples.py
validators/tests/unit/test_ce_check_cli.py
validators/tests/unit/test_cli.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse-dev/execnet-2.1.2-py3-none-any.whl
validators/wheelhouse-dev/pytest_xdist-3.8.0-py3-none-any.whl
```
