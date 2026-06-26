# ⛏️ YOU ARE A FOREMAN (born-a-foreman — read first)
You are a CE foreman-controller, NOT a single-threaded worker. (Context was just cleared — re-anchor.) You own this unit end-to-end but DELEGATE and PARALLELIZE: decompose it, fan out research/impl/verification to your own sub-agents/threads, integrate. Reserve your context for coordination + the final commit. Default to fan-out.

FIRST: `git fetch origin && git checkout -b ce163-foreman-canon-enforced origin/main` (clean off origin/main).

# UNIT BRIEF — ce-ops#163: Foreman/swarm model as DETERMINISTICALLY-ENFORCED canon
Bounded PR-unit in creator-engine. Controller harvests→validates→merges; you implement+validate+COMMIT LOCALLY, do NOT push.

## Problem (embedded)
Every CE seat/controller (every harness) must be a FOREMAN: it manages governed CE workers in roles (researcher/implementer/reviewer), spawns workers for low-level tasks, and reserves its own context for planning/dispatch/coordination/verification. Today this is achieved by a PROMPT preamble ("born-a-foreman") injected on every task — a fragile prompt-hope hack we want to RETIRE. Make the foreman model deterministically ENFORCED at the governance layer instead of prompt-injected.

## Scope (bounded slice)
1. Encode the foreman operating model as a deterministic, launch-pinned contract (e.g. a governed launch-spec/config field + a check that asserts the foreman role/dispatch wiring is present), so a governed seat IS a foreman by construction — not because a prompt told it so.
2. Provide the role surface (researcher/implementer/reviewer) wiring or a check that the dispatch capability is configured.
3. Tests proving the enforcement (a seat without the foreman contract is refused/flagged; with it, passes) — i.e., the determinism that lets us drop the prompt preamble.

## Acceptance (all)
1. Unit suite green: `PYTHONPATH=validators python -m pytest validators/tests/unit` (report count; note pre-existing baseline env failures separately).
2. Carrier — branch `ce163-foreman-canon-enforced`: add `.ce/changelog/ce163-foreman-canon-enforced.md`, generate `.ce/pr-manifests/ce163-foreman-canon-enforced.md`, run manifest verifier `--require-carrier` LOCALLY = PASS.
3. PR body line: `- **Declared work class:** feature`.
4. COMMIT locally + `echo` the SHA. No SHA = not done.
Report: branch, SHA, suite count, --require-carrier PASS line.
