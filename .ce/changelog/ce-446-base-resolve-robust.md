---
slug: ce-446-base-resolve-robust
date: 2026-07-05
kind: fix
scope: governance
issue: ce-ops#446
---

**robust moved-base comparison-base resolution in governance workflow.**

- Resolve pull-request comparison bases through the GitHub compare API before local diff validation, avoiding shallow checkout parent traversal when the recorded PR base is behind origin/main.
- Fetch only the server-resolved merge-base commit for local validation and report remaining graph/API failures as infrastructure failures.
- Supersession-append the validate workflow brain assertion SHA pin for the edited workflow bytes.
- Ratchet the brain-drift active assertion count because the validate-workflow assertion supersession intentionally adds one active ledger record.
