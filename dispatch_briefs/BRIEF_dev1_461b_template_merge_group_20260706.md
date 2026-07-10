# BRIEF — dev-1 — adoption workflow template lacks merge_group trigger (#461 blocker; ticket being filed, will be linked on your PR)
2026-07-06 ~09:0xZ. Role: implementer, self-push. Branch `ce-461b-adoption-template-merge-group` off FRESH origin/main.

Finding (dev-3, verified): the client workflow template in validators/creator_engine_validator/onboard_apply.py emits only `pull_request` + `push` triggers; .github/workflows/validate.yml (our own) also has `merge_group: types: [checks_requested]`. Adopted client repos therefore can't satisfy required checks in a merge queue — merge-group parity broken at adoption.

Scope: add the merge_group trigger to the emitted template (mirror validate.yml's stanza); unit test asserting the emitted template contains it (failure-direction: test fails on old template); check whether any doc states the template's trigger set and update it. NOTHING else — this template lives in the shipped wheel, so the fix rides 0.3.4 (do NOT touch 0.3.3 release paths/staging/downloads, do NOT touch llms-install.md or any sha-pinned file → STOP if needed).

Bar: FULL ce validate-pr GREEN one pass; carrier via write_carriers (stem == branch slug); changelog fragment; PR body `- **Declared work class:** tiny`. Self-push + PR; report PR# + head. Stop lines standard (no sign, no merge, no settings).
