# DISPATCH — dev-3 — 2026-07-10 — unit: ce-505 guided-journey UX research (S, research/design doc)
Role: implementer foreman (research deliverable). Signal per standing format when done:
`READY-FOR-HARVEST ce-505-guided-journey-research <full-40-hex-sha>` or `BLOCKED ... <reason>`.

## Preconditions
`git fetch origin main`; branch `ce-505-guided-journey-research` off fetched origin/main;
worktree /var/tmp/wt-ce-505-guided-journey-research. Do NOT touch .ce/brain/assertions.yaml.
Venv caveat stands: focused checks green + BLOCKED(env) if validate-pr cannot run.

## Unit (embedded ticket ce-ops#505)
Research + design doc for the guided-journey UI/UX — the HUMAN-side harness of the factory.
Deliverable: `docs/design/guided-journey-ux.md`. Ratified doctrine to build on (do not
relitigate): the UI is a read-model/emission surface of the ONE face, never a second authority;
AWAITING-OPERATOR queue is the core primitive; in fleet mode the Operator ratifies arcs in
batch and reviews no per-artifact work. Cover: (1) the journey read-model — what the human
sees per stage (Frame→Shape→Build→Review→Ship vocabulary is canon); (2) the awaiting-operator
inbox as THE interaction point — batch ratification ergonomics, full-absolute-path refs,
zero internal ticket refs (product lens); (3) the vacation test — a human returns after N days
and resumes command from the surface alone: what state must it replay; (4) per-turn completion
reports as the emission feed; (5) explicit non-goals (no second brain, no chat-with-the-factory
control plane). Decisions with rationale + rejected alternatives, not a survey. Quality bar:
top-tier authorship, CEO-first reading order.

## Files (allowed writes)
docs/design/guided-journey-ux.md (NEW), .ce/changelog/ce-505-guided-journey-research.md,
carrier .ce/pr-manifests/ce-505-guided-journey-research.md (slug=branch) containing exactly:
`- **Declared work class:** S`

## Stop lines
Everything else — especially ce_cli.py, forge/**, deploy/**, .github/**, docs/llms-install.md,
existing docs/design/* files (additive only), .ce/brain/assertions.yaml.
