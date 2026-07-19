# PR path manifest — ce-ops#624 · class-policy registry

This per-PR carrier lists the closed authorized path set for the ticket-class
policy registry (`S` slice, CE624).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=abe0840b3ae14eb29f677eafd8acd821352a9b7418089746ab9cbce02694d8cc

```text
.ce/changelog/ce-624-class-policy-registry.md
.ce/pr-manifests/ce-624-class-policy-registry.md
docs/decisions/ADR-0018-ticket-class-registry.md
validators/creator_engine_validator/forge/ticket_class_registry.py
validators/creator_engine_validator/forge/ticket_class_registry.yaml
validators/tests/unit/test_ticket_class_registry.py
```
