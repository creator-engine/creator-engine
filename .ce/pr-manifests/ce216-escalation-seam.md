# PR path manifest - ce216-escalation-seam

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce216-escalation-seam
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/ce216-deterministic-resolvers` at branch handoff.

- **Declared work class:** story

Scope:
ce-ops#216 Unit 4. Add a data-only escalation seam for unresolved deterministic
resolver outputs so semantic conflicts route to controller action instead of
being silently parked. No executor, push, merge, credential, network, or write
authority is introduced.

Per-file purpose:
- **`.ce/changelog/ce216-escalation-seam.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce216-escalation-seam.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify the escalation seam as v3 forge code.
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* - expose escalation context, event, refusal, and fold helpers through the forge package surface.
- **`validators/creator_engine_validator/forge/integrator_escalation.py`** *(A)* - pure data-only unresolved-result to controller-event implementation.
- **`validators/tests/unit/test_integrator_escalation.py`** *(A)* - TDD coverage for event shape, no-op mechanical outputs, fold behavior, and fail-closed malformed inputs.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - update the v3 module count and classification assertion.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=65a81a39ad2ceb9bc7b7d1cb2c6835dfa7ef2d1fe362a456ee86b31a8a98ae27

```text
.ce/changelog/ce216-escalation-seam.md
.ce/pr-manifests/ce216-escalation-seam.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/integrator_escalation.py
validators/tests/unit/test_integrator_escalation.py
validators/tests/unit/test_version_boundary.py
```
