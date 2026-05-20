# Completion Report — Class F example

**Gate class**: F — blocked gate.
**Controller**: `hermes-primary`
**Lane**: `blocked-gate-example`
**Outcome**: `blocked`

## Summary

Gate opened to perform a hypothetical downstream task but was blocked when the
upstream substrate was not present. Closing the gate explicitly per the
protocol: a blocked gate without a closure report is undefined runtime state.

## Recommended immediate next step

- **Description**: Resolve the blocker by ratifying the upstream substrate gate.
- **Rationale**: The downstream gate cannot make progress without the upstream substrate; ratify the upstream gate first.
- **Next-action kind**: `blocker_resolution`

## Exact next Source prompt pointer+SHA256

- **Kind**: `present`
- **Prompt path**: `.hermes/envelopes/source-ratify-upstream-substrate.md`
- **Prompt SHA256**: `7777777777777777777777777777777777777777777777777777777777777777`
- **Canonical ratification line**: Source ratifies the upstream substrate gate before the downstream gate may reopen.

---

**Blocker description**: upstream substrate gate has not been ratified.
**Resumption pointer**: `.hermes/envelopes/source-ratify-example-class-f-resume.md` (SHA256 `8888…8888`).
