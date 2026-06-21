# PR path manifest — ce-ops#163 (foreman seat-class Slice 1)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce163-foreman-seat-class
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below (the carrier lists itself); the fidelity scan requires the declared count
and SHA256 to match the fenced block.

Ratified scope:
Foreman-Delegation Slice 1 from `tmp/163-foreman-build-brief.md` (sha256
`4445cc878d7cae46a30d3bdf1573c3389e6df81431f553e94157e7410132bed4`).

Scope: build only the born-a-foreman deterministic spine: pure `seat_class.py`,
`schemas/seat-class-policy.schema.yaml`, a `seat_class_policy` check, examples,
tests, changelog, and rebuilt app wheel. Explicitly excluded: `hook_check.py`,
launcher/runtime wiring, worker spawning, Gate C/Gate D, action-count triggers,
line-count triggers, UX, and cockpit rendering.

Per-file purpose:
- **`.ce/changelog/ce163-foreman-seat-class.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce163-foreman-seat-class.md`** *(A)* — this carrier
  (self-inclusive).
- **`docs/contracts/seat-class-policy.md`** *(A)* — short policy contract stub.
- **`examples/malformed/seat-class-policy/bad-depth.yaml`** *(A)* — malformed
  recursion-depth fixture.
- **`examples/malformed/seat-class-policy/bad-mutation-class.yaml`** *(A)* —
  malformed baseline-mutation-class fixture.
- **`examples/malformed/seat-class-policy/default-not-foreman.yaml`** *(A)* —
  malformed born-a-foreman default fixture.
- **`examples/malformed/seat-class-policy/secret-value.yaml`** *(A)* —
  malformed secret-value fixture.
- **`examples/well-formed/seat-class-policy/foreman.yaml`** *(A)* — valid
  foreman policy fixture.
- **`examples/well-formed/seat-class-policy/minimal.yaml`** *(A)* — minimal
  valid policy fixture.
- **`examples/well-formed/seat-class-policy/worker.yaml`** *(A)* — valid worker
  policy fixture.
- **`schemas/seat-class-policy.schema.yaml`** *(A)* — policy schema.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* —
  registers the `seat_class_policy` check.
- **`validators/creator_engine_validator/checks/seat_class_policy.py`** *(A)* —
  schema and semantic policy check.
- **`validators/creator_engine_validator/seat_class.py`** *(A)* — pure
  classifier/resolver/verdict helpers.
- **`validators/tests/integration/test_seat_class_policy_examples.py`** *(A)* —
  example integration tests.
- **`validators/tests/unit/test_app_jwt_runner.py`** *(M)* — registered-check
  count drift guard updated.
- **`validators/tests/unit/test_change_status.py`** *(M)* — registered-check
  count drift guard updated.
- **`validators/tests/unit/test_credential_runner.py`** *(M)* —
  registered-check count drift guard updated.
- **`validators/tests/unit/test_evidence_sink.py`** *(M)* — registered-check
  count drift guard updated.
- **`validators/tests/unit/test_merge.py`** *(M)* — registered-check count drift
  guard updated.
- **`validators/tests/unit/test_open_change.py`** *(M)* — registered-check count
  drift guard updated.
- **`validators/tests/unit/test_redact.py`** *(M)* — registered-check count drift
  guard updated.
- **`validators/tests/unit/test_seat_class.py`** *(A)* — pure classifier tests.
- **`validators/tests/unit/test_seat_class_policy.py`** *(A)* — policy check
  tests.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* —
  registered-check count drift guard updated.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned app-wheel checksum
  after rebuild.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**
  *(M)* — rebuilt app wheel matching this branch's validator source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=27

AUTHORIZED_PATHS_SHA256=de5ea58dcfc59d51ffba83c0d32078ae9c7b0b28cee44d155d5648474f314ef3

```text
.ce/changelog/ce163-foreman-seat-class.md
.ce/pr-manifests/ce163-foreman-seat-class.md
docs/contracts/seat-class-policy.md
examples/malformed/seat-class-policy/bad-depth.yaml
examples/malformed/seat-class-policy/bad-mutation-class.yaml
examples/malformed/seat-class-policy/default-not-foreman.yaml
examples/malformed/seat-class-policy/secret-value.yaml
examples/well-formed/seat-class-policy/foreman.yaml
examples/well-formed/seat-class-policy/minimal.yaml
examples/well-formed/seat-class-policy/worker.yaml
schemas/seat-class-policy.schema.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/seat_class_policy.py
validators/creator_engine_validator/seat_class.py
validators/tests/integration/test_seat_class_policy_examples.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_seat_class.py
validators/tests/unit/test_seat_class_policy.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
