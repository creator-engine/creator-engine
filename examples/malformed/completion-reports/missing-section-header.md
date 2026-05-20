# Completion Report — malformed (missing terminal section header)

This Markdown body intentionally omits the
`Exact next Source prompt pointer+SHA256` terminal section header.
The CR-003 (warn-only) terminal-section check fails against this
body even though the adjacent YAML sidecar self-declares all three
sections present.

## Summary

Demonstrates the CR-003 failure mode.

## Recommended immediate next step

- **Description**: Re-author the Markdown body to embed all three section headers in canonical order.
- **Rationale**: CR-003 must see the headers in the rendered body, not just in the YAML self-declaration.
- **Next-action kind**: `blocker_resolution`

---

(Notice: there is no `## Exact next Source prompt pointer+SHA256` header below.)
