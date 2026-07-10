# BRIEF — dev-4 — review-analysis of PR #866 (dev-1's ce-ops#478: controller posture banner, P0 of the ratified #471 program)
2026-07-06 ~17:0xZ by CE-DEV-2. Read-only, verdict-only. Mechanics: `git fetch origin pull/866/head:review-866`, throwaway worktree, baseline STRICTLY `git show <merge-base>:<path>`. Head 1fc74896, branch ce-478-posture-banner.

Embedded acceptance bar (you can't read ce-ops; this is ce-ops#478's ratified bar — Operator ratified the parent program as a block today):
- A command prints the controller posture: role, harness, launch mode, Ring-0 confirmed, Ring-1 active, Ring-2/closeout support, credential-scrub status, remote-control status, approval-wall armed state, signing-deputy status, and allowed posture (read-only | foreman | gate-capable).
- The banner must be consumable by the future `ce takeover` evidence packet (ce-ops#477 is the sibling P0 — check the output is structured/JSON-able, not prose-only).

Your bars:
1. TRUTHFULNESS: every banner field must be DERIVED from real state (launch evidence, hook packs, daemon state, config), never hardcoded or asserted. Any field that prints a static value = REQUEST_CHANGES with the line.
2. "gate-capable" must appear ONLY when the underlying capabilities are actually verified present — fail-closed to the weakest posture on any missing/unreadable input.
3. Read-only: the banner command must mutate NOTHING (no state writes, no network beyond local reads — flag any).
4. Tests: failure-direction (missing hook pack / disabled wall → banner degrades correctly, not crashes).
5. New `ce` verb → docs-coupling satisfied; class sane (tiny/story).
Emit exactly: `VERDICT-866: APPROVE` or `VERDICT-866: REQUEST_CHANGES` + numbered evidence.
