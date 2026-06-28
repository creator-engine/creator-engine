# PR path manifest - ce-295-w5-g5-body-emit

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).

- **Declared work class:** story
- **story:** ce-ops#295 W5 slice 1 - G5 body-line auto-emit (ce-ops#340)

Scope:
Add `--declared-work-class` to the egress broker CLI and thread it into
`render_pr_body` so broker-pushed PRs carry the required G5 work-class line.
Auto-discover from the carrier file when the CLI arg is omitted; fail closed if
neither resolves.

Per-file purpose:
- **`.ce/changelog/ce-295-w5-g5-body-emit.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-295-w5-g5-body-emit.md`** *(A)* - this closed path-set carrier.
- **`tools/egress-broker/ce_egress_broker.py`** *(M)* - add the optional CLI argument and pass it to the courier.
- **`tools/egress-broker/egress_broker/orchestrator.py`** *(M)* - discover, validate, pass, and emit the broker PR work class.
- **`validators/tests/unit/test_egress_cli.py`** *(M)* - cover CLI argument threading.
- **`validators/tests/unit/test_egress_host_broker.py`** *(M)* - pass the trusted courier option through self-push host-broker seams.
- **`validators/tests/unit/test_egress_orchestrator.py`** *(M)* - cover body emission, carrier discovery, and fail-closed behavior.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=ae0a414b6cbf7789f6b25c989a00ec64d879835da34ac7e4ff8c3d172aedb896

```text
.ce/changelog/ce-295-w5-g5-body-emit.md
.ce/pr-manifests/ce-295-w5-g5-body-emit.md
tools/egress-broker/ce_egress_broker.py
tools/egress-broker/egress_broker/orchestrator.py
validators/tests/unit/test_egress_cli.py
validators/tests/unit/test_egress_host_broker.py
validators/tests/unit/test_egress_orchestrator.py
```
