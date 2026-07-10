# Dispatch brief — ce-ops#292 (AutoReview self-trigger via AGENTS.md, Wave 1.2)

**Seat:** dev-3 (`ce-vps-codex`)
**Role:** implementer
**Ticket:** creator-engine/ce-ops#292 — "AutoReview self-trigger via AGENTS.md (Wave 1.2)"
**Arc-ref:** Day-shift arc 2026-06-27, item 1.2. Authority: G5 (build + arm).

## Pre-work (mandatory — your old branch is dead)

Your current branch `ce-302-broker-namespace` is STALE: that work already merged as #567. Do NOT build on it.

```
cd /workspace/creator-engine
git fetch origin
git worktree add ~/ce-workspaces/wt-ce292-autoreview -b ce-292-autoreview origin/main
cd ~/ce-workspaces/wt-ce292-autoreview
```

Do ALL work in that fresh worktree branched off `origin/main`.

## Goal

Auto-fire a fresh-context reviewer worker pre-PR-open / pre-merge, encoded as ONE line in
`AGENTS.md` — not controller-dispatched. Reuse the EXISTING `reviewer` role
(`.claude/agents/reviewer.md`) + the `/code-review` skill. Steal Peter Steinberger's
self-trigger pattern.

## Scope / allowed surfaces

- `AGENTS.md` — add the trigger line that fires the reviewer role automatically pre-PR / pre-merge.
- A THIN self-fire hook/wrapper around the existing reviewer worker (no new reviewer logic, reuse `reviewer.md` + `/code-review`).
- Reviewer evidence is posted as a PR COMMENT (or REQUEST_CHANGES). `APPROVE` stays HARD-REFUSED per wall policy — the self-fire path must NEVER approve.
- Tests for the new trigger/hook wiring.

## OUT OF SCOPE — do not touch (in-flight PR territory)

- The egress broker: `tools/egress-broker/**`, `deploy/systemd/**`, INCLUDING the egress
  *self-review* broker (`ce_egress_self_review_broker.py`, `ce-egress-self-review.*`). That is PR #584's territory. Your reviewer self-trigger is the AGENTS.md/charter mechanism, NOT the egress broker.
- Doc-autogen generators: `scripts/gen_schema_reference.py`, `.ce/reference/**`,
  `validators/.../checks/schema_reference_autogen_sync.py`. That is PR #585's territory.

## Expected evidence (DoD)

1. A PR self-triggers a fresh-context reviewer run without controller dispatch; review
   evidence is posted to the PR (COMMENT/REQUEST_CHANGES, never APPROVE) before the controller sees it.
2. Full LOCAL CI-parity preflight green (run `ce validate-pr` / the full gate set on a CLEAN tree —
   your validator venv was just fixed, so self-preflight works now).
3. A pushed PR (self-push as your own identity, ce-dev-3) carrying:
   - the canonical carrier (`.ce/pr-manifests/` + `.ce/changelog/` entries),
   - the PR body line: `- **Declared work class:** <tier>`.

## Stop line

Push the PR and STOP. Do NOT self-approve and do NOT merge — the controller holds the
merge gate. Report the PR number back.
