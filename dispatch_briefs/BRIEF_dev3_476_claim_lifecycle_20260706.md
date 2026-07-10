# BRIEF — dev-3 — ce-ops#476: work_claims lifecycle seed slice (story, file-disjoint)
2026-07-06 ~12:3xZ by CE-DEV-2. Role: implementer (foreman — fan out as you see fit), contained, COMMIT-ONLY → harvest. Branch `ce-476-claim-lifecycle` off FRESH origin/main. Your #461 unit stays gated (self-poll main for the #859 template fix as before). This is your next primary unit.

You cannot read ce-ops, so the FULL ticket body is embedded below — it is the spec. Honor its "File-disjoint constraint (hard)" section exactly: NEW files only (validators/claim_lifecycle.py, new tests, docs/claims-lifecycle.md, .github/workflows/ce-claim-closeout.yml); do NOT modify validators/work_claims.py, belt_pickup.py, conveyor.py, readiness_blockers, or any existing dispatch path. If implementing forces a touch on any existing file beyond additive wiring the ticket names, STOP and report the file + why.

Note: `ce claim` is a NEW CLI verb group — the repo's docs-coupling test requires docs for new groups; the ticket's docs/claims-lifecycle.md covers this, make sure the docs test actually passes. The new workflow must be least-privilege (read-only default perms + the narrowest write it needs) and must NOT weaken any existing workflow.

Bar: FULL `ce validate-pr --declared-work-class story` GREEN one pass (if env-only suite failures block you again, same protocol as #467: verify they reproduce on clean origin/main, capture evidence to /var/tmp/ce-476-evidence/, signal BLOCKED-ENV); carrier via write_carriers (stem == branch slug); changelog fragment .ce/changelog/ce-476-claim-lifecycle.md; COMMIT-ONLY, signal `READY-476 <sha>`. STOP lines standard: no push, no approve, no merge, no sign, no sha-pinned files (docs/downloads/*, llms-install.md, install.sh, .ce/release-staging/*).

---- EMBEDDED TICKET ce-ops#476 (verbatim) ----
Title: work_claims lifecycle: define state machine + YAML schema + ce verb surface + PR-merge closeout automation
## Symptom

The controller repo tracks work claims as freeform one-line files at
\`.ce/claims/<slug>.md\` with no schema and no lifecycle. Claims are written at
dispatch time and never transition. There are no machine-readable states, no
timestamps, no seat-attribution fields, and no automatic closeout when the
corresponding PR merges.

## Evidence

- \`.ce/claims/\` files today are plain prose (e.g., \`\"CE-DEV-2 2026-07-05
  dispatched ce-453-foo to dev-4\"`). No YAML frontmatter, no status field.
- The dep-unlock executor (ce-ops#463, now in shadow soak) calls
  \`readiness_blockers()\` to decide what to unlock next. It cannot distinguish
  a ticket whose seat is actively building from one that is merely staged for
  dispatch — both look identical in the claim file.
- The territory-map dispatch check (belt pickup path) guards against
  file-path overlap. That check operates on branch slugs inferred from the
  claim filename, not on a declared in-flight state — a claim that survived a
  failed or abandoned dispatch is indistinguishable from an active one.
- Two seat-side start-condition polls on 2026-07-05 hand-rolled \`git log
  --grep\` to infer in-flight status (branch-slug vs merge-title mismatch
  surfaced as bugs the same day) — direct evidence that downstream consumers
  are already working around the missing state signal.
- Operator manually couriered a seat's blocked-status to the controller on
  the same day: further evidence of the gap.

## Root cause

\`.ce/claims/<slug>.md\` was introduced as a lightweight coordination
primitive and intentionally left schemaless. The conveyor has since grown
automation layers (dep-unlock, territory-map, triage-queue) that need
machine-readable claim state. The schema gap was not re-visited.

## Impact

1. **dep-unlock (ce-ops#463)** cannot reason about what is genuinely
   in-flight vs. merely claimed; it may unlock a dependency whose blocking
   seat is already halfway through a build.
2. **Territory-map dispatch** cannot expire or invalidate stale claims,
   creating phantom blocks on ticket work that was abandoned or failed.
3. **Triage-queue / belt** cannot surface a real-time seat-status feed
   without scraping pane output — the forge-native seat status piece (ce-ops#454
   piece 4) depends on having a canonical state to emit.
4. **Controller resume** after context-clear or host restart requires
   re-deriving in-flight state from git log and pane output, a fragile and
   error-prone path.

## Proposed fix — seed scope (story, file-disjoint from current conveyor work)

### 1. Lifecycle state set

Ordered states with entry conditions:

| State | Meaning | Entry condition |
|---|---|---|
| \`claimed\` | Work dispatched to a seat | \`ce\` dispatch path writes claim |
| \`in-build\` | Seat has confirmed first commit | Seat or watcher transitions |
| \`ready\` | Seat has pushed a PR | PR-open event or \`ce\` verb |
| \`harvested\` | PR approved, in merge queue | Approval event or \`ce\` verb |
| \`landed\` | PR merged to main | Merge event (auto-closeout) |
| \`released\` | SHA in a versioned release tag | Release-publish event or \`ce\` verb |

Terminal states: \`landed\`, \`released\`, \`abandoned\` (explicit or timeout).

### 2. Claim file schema (YAML frontmatter)

\`\`\`yaml
# .ce/claims/<slug>.md
---
slug: ce-NNN-short-title
issue: NNN
repo: creator-engine/creator-engine
state: claimed          # one of the states above
seat: ce-dgx-codex      # seat identity (from infra/identity-registry.yaml)
controller: CE-DEV-2    # dispatching controller
claimed_at: 2026-07-06T14:00:00Z
transitioned_at: 2026-07-06T14:00:00Z
pr: null                # filled when state >= ready
merge_sha: null         # filled when state = landed
refs:
  - ce-ops#NNN
---
\`\`\`

The body below the frontmatter remains free-form (human notes / brief pointer).

### 3. \`ce\` verb surface

\`ce claim transition <slug> <new-state> [--pr <url>] [--sha <sha>]\`

- Validates the transition is legal (no backward jumps without \`--force\`).
- Updates \`transitioned_at\` and the relevant nullable fields.
- Emits a structured log line (for watcher / belt consumption).
- Reads identity from the ambient seat/controller environment; no interactive
  input required (safe for automation).

\`ce claim list [--state <state>] [--seat <seat>]\` — tabular output for
  pane-read or forge-emission.

### 4. PR-merge closeout automation

Extend \`ce-ops-autoclose.yml\` (or add a peer \`.github/workflows/ce-claim-closeout.yml\`)
to react on \`pull_request.closed` (merged=true) events in the main
\`creator-engine\` repo:

- Parse the merge commit for a \`Closes-Claim:\` trailer or derive the slug
  from the branch name.
- Call \`ce claim transition <slug> landed --sha <merge_sha>\` (or directly
  update the YAML via a small Python helper).
- Commit the updated claim file on main via the CE App identity.

### 5. Consumer integration (out of scope for this seed)

- dep-unlock executor: gate unlock on \`state not in {claimed, in-build}\`.
- Territory-map: expire claims whose \`state = claimed\` and
  \`claimed_at < now - 24h\` (configurable).
- Belt pickup: emit \`ce claim list --state claimed\` as the in-flight feed.

## Implementation notes

- **File-disjoint constraint (hard):** the seed slice touches only
  \`validators/claim_lifecycle.py\` (new module), \`validators/tests/\` (new
  unit + integration tests), \`docs/claims-lifecycle.md\` (new doc), and
  \`.github/workflows/ce-claim-closeout.yml\` (new workflow). It must NOT
  modify existing dispatch paths (\`work_claims.py\`, \`belt_pickup.py\`,
  \`conveyor.py\`, \`readiness_blockers()\`) in the first slice — those
  integrations are a follow-on story.
- \`ce claim transition\` can be a thin CLI wrapper around
  \`validators/claim_lifecycle.py\`; keep it side-effect-free (file write +
  log) for easy testing.
- Schema validation should use the existing YAML-frontmatter parse path
  already present in the validators module (avoid adding a new dependency).
- Suggested work class: **story** (greenfield module + schema + CLI verb +
  one workflow; no touch to existing paths; should complete in a single
  contained-seat pass).

## References

- ce-ops#454 — dark-factory dispatch layer (CLOSED; parent program; this is
  the work_claims substrate that pieces 1–4 of that program depend on)
- ce-ops#463 — dep-unlock executor in shadow soak (direct consumer of claim
  states; integration is out-of-scope here but must not be broken)
- ce-ops#38 — forge-level work-claim locks (OPEN; complementary: #38 governs
  who may hold a claim at the forge level; this ticket governs the file-schema
  lifecycle once a claim is held)
- ce-ops#471 — controller power-shaping research (2026-07-06; repair-loop
  recursion bottom-out depends on knowing real in-flight state)
- \`.ce/claims/\` — current freeform claim files (repo: creator-engine)
- \`validators/work_claims.py\` — existing claim write path (do not modify in
  seed slice)
