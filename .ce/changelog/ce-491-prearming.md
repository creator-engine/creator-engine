---
slug: ce-491-prearming
date: 2026-07-08
kind: fixed
scope: materializer pre-arming checklist
issue: CE-491
---

**Close materializer pre-arming review findings.**

- Bumps the materializer audit actor version to `ce-491-prearming`.
- Normalizes materializer evidence paths before enforcing `.ce/state` bounds.
- Documents the HeldError artifact asymmetry beside the handler.
- Adds run-preflight coverage proving the brain append intent/direct ledger XOR gate fires in the real check sequence.
