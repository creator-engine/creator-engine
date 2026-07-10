# BRIEF — dev-1 docs tinies batch 3 (foreman mode, 2 file-disjoint units)

Role: implementer-foreman (dev-1, non-contained). Same mechanics as batch 2: per unit — own
worktree off FRESH origin/main, own branch/PR/changelog/carrier, work class tiny, semantic
novelty check FIRST (name the seam, verify vs fresh main; already-resolved is a valid outcome).

## U1 — branch `ce-docs-pilot-welcome` — pilot welcome/handoff page
Seam: "the page a new PILOT TENANT reads first after receiving their install handoff" — a
product-lens welcome covering: what you received (the signed one-liner install + the
llms-install.md agent-playbook alternative, as two equivalent paths), what CE governs in your
repo once onboarded (gates, PR-only flow, contained agent launch), your first governed session
(pointer to the quickstart + pilot-runbook pages, do NOT duplicate their content), and where to
report issues. GENERIC product content only — no tenant names, no org names, no internal
references of any kind.
Novelty check: docs/guide/welcome.md EXISTS — read it first. If pilot-handoff content belongs
there, EXTEND welcome.md instead of creating a new page (your call after reading; one file
either way). ⛔ Do NOT touch docs/guide/pilot-runbook.md or docs/contracts/installer.md — both
have OPEN PRs in flight (#818, #816).

## U2 — branch `ce-docs-stale-wheel-envvar` — CE_ALLOW_STALE_WHEEL docs mention
Seam: "user-facing documentation of the CE_ALLOW_STALE_WHEEL escape hatch" — currently
documented NOWHERE user-facing (#816's env enumeration is gate-daemon-scoped and deliberately
excluded it). Content to document (verified from source, ce_cli.py — re-verify on your branch):
the stale-wheel version-skew guard refuses gate commands (validate-pr, brain verify/correct/sync)
when the installed wheel is older than the source checkout; setting CE_ALLOW_STALE_WHEEL=1
(literal '1' only) overrides the refusal and the override is logged; the durable fix is
reinstalling/updating the wheel. Pick the ONE right existing page (a troubleshooting or CLI
reference page — NOT installer.md, NOT pilot-runbook.md); if genuinely no page fits, a short new
docs/guide/troubleshooting.md is acceptable.

## STOP lines (both units)
⛔ docs/install.sh, docs/downloads/**, docs/llms-install.md = SIGNED artifacts — never edit.
⛔ Product lens: zero ce-ops#/internal-fleet/tenant-org references.
⛔ No code, no schema edits. Never sign. No review/approve/merge/enqueue.

## Evidence bar
Full `ce validate-pr` GREEN one pass before push. Changelog + carrier (stem == branch slug).
Exactly one `- **Declared work class:** tiny` line per PR body.
Signal per unit: `READY <branch> <40-hex sha> PR=<url>` (or `READY <branch> already-resolved`).
