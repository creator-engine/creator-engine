---
brief_id: BRIEF_dev3_queue2_20260709
ticket: ce-506-daemon-vs-agent-rubric-design-s1
seat: dev-3
seat_kind: contained-commit-only
branch: ce-506-daemon-vs-agent-rubric-design-s1
worktree: /var/tmp/ce-506-daemon-vs-agent-rubric-design-s1
size: S
units: 1
priority: TOP
mandate: daemon-vs-agent-rubric-ratified-20260708
grounded_on: origin/main@e3ab6e6aa2d9878a67df517f80aca9536e171165
composed_at: 2026-07-09
---

# BRIEF: Daemon-vs-agent rubric design doc — slice 1

**Drop/substitute note:** ce-ops#487 (`ce shape --from <path>`) was the original
candidate for this queue slot. It is DROPPED because PR #878 (MERGED 2026-07-07)
already delivered the implementation; a dev-1 in-compose claim exists on the ticket.
Assigning #487 again would produce a duplicate. Substitute: ce-ops#506 — write the
daemon-vs-agent rubric design doc from the ratified memory content embedded in the
ticket.

**DESIGN-PREVIEW HOLD:** This PR contains a design document. Per design-preview
doctrine, the PR must be opened and then HELD (do not self-merge, do not request
auto-merge). The controller will review with the Operator before the merge gate is
opened. Mark the PR description with `[DESIGN-PREVIEW — AWAITING OPERATOR]`.

**Contained seat rules (enforced):**
- Targeted tests only — no full suite. The unit produces a Markdown doc; no
  programmatic tests are required. Validate that the file is well-formed Markdown
  and the carrier matches, then commit.
- No committed READY file.
- No ce-ops issue number references in any committed artifact.

---

## Mandate (2026-07-08)

The planned factory organs (reviewer-assignment, seat-ticket triage, belt) were
defaulted to deterministic daemons without a per-task routing analysis. Steinberger's
factory evidence shows the correct pattern: deterministic skeletons spawn probabilistic
agent-organs that propose; the human (or deterministic disposer) ratifies. The rubric
that distinguishes daemons from agent-organs has been ratified in controller memory
but is not yet a governed repo artifact accessible to contributors or future controllers.

This slice produces the design doc that codifies the rubric and applies it organ-by-organ.

---

## Ticket content (ce-ops#506, embedded)

**Parent mandate:** Operator question ratified as design mandate 2026-07-08. Defaulted
factory organs (c4 reviewer-assignment, c5 triage, belt) to deterministic daemons without
per-task analysis. Prior art: Steinberger autonomy analysis (controller state root,
2026-06-27) — his factory uses NO deciding daemons; deterministic triggers spawn
probabilistic agents that read plain-text policy; human ratifies aggregated evidence.

**Deliverable:** `docs/design/daemon-vs-agent-rubric.md`

The doc must cover four sections:

### Section 1 — Routing rubric

| Axis | Deterministic daemon | Agent-organ |
|---|---|---|
| Primary invariant | Fail-closed; NEVER calls an LLM | Judgment layer; MUST call LLM |
| Function type | Authority enforcement, mechanics, transport, token custody | Proposal-only output into deterministic disposer |
| Error model | Hard fail (no output is safer than wrong output) | Graceful-degrade on miss; never blocks the skeleton |
| Token budget | Zero (token-free) | Token-rationed; Haiku class; bounded per activation |

Agent-organ FOUR invariants (all four must hold or it is not an agent-organ — it is an unbounded agent):
1. **Deterministic trigger** — GH event / belt tick / merge-queue state change (never self-scheduling).
2. **Versioned plain-text policy input** — read from repo at activation time (e.g., `AGENTS.md`, `policy/`); no hardcoded prompts.
3. **Proposal-only output into deterministic disposer** — the organ proposes; the daemon/ledger disposes. Grader-outside applied to the organ layer.
4. **Token-rationed small-model execution** — Haiku class; bounded per activation.

### Section 2 — Organ-by-organ application

| Organ | Classification | Rationale |
|---|---|---|
| Gate daemon | Deterministic daemon | Authority enforcement — fail-closed is non-negotiable |
| Option A materializer | Deterministic daemon | Authority — produces signed carriers; wrong output worse than no output |
| Reviewer assignment | Deterministic matrix + optional agent expertise tie-break | Matrix is authority; tie-break is judgment only when matrix is ambiguous |
| Review execution | Agent-organ (per AutoReview pattern) | Judgment — fresh-context per-commit review |
| Seat-ticket triage | Agent-organ judgment riding the polling belt; advisory disposal into deterministic disposer | c5 triage organ; belt is the skeleton |
| Belt-poller | Deterministic daemon | Transport — token-free; polling is mechanics not judgment |

### Section 3 — Organ hydration contract

Agent-organs access the memory layer via the hydrate contract (from the acceptance-evidence program, slice 2):
- **Authoritative source:** deterministic ledger (always consulted; authoritative).
- **Advisory source:** vector/graph recall (graceful-degrade on miss; never blocks).
- **Policy injection:** organ receives versioned plain-text policy file path at spawn time; no hardcoded prompts.
- **Dual-store note:** SSOT ledger write + advisory recall index write happen in the same commit; neither is optional.

### Section 4 — Two Steinberger steals as first implementations

**S1 — AutoReview analog (self-triggering):**
GH Actions webhook → agent-organ reviews PR with fresh context per commit; proposes
verdict to deterministic approval gate; never self-approves. Token budget: Haiku, 1
activation per commit. Policy: `AGENTS.md` reviewer rubric at HEAD of the PR branch.

**S2 — Triage analog (belt-driven):**
Belt tick (polling, configurable interval) → agent-organ reads open issue list + triage
policy → proposes label + lane assignment → deterministic disposer writes labels via
GH API only when confidence ≥ threshold. Policy: `policy/triage-rules.md` at HEAD.
Token budget: Haiku, 1 activation per batch of ≤ 20 issues.

**Canon framing (both steals):**
- Trigger is deterministic; the agent is ephemeral per activation.
- Output is advisory: a structured proposal artifact, not a direct system action.
- Disposer is deterministic: evaluates the proposal against policy, applies or discards.
- Human can override the disposer by modifying policy.md; the rubric then shifts automatically.

---

## Standing obligations — copy verbatim into PR body + checklist

- [ ] Changelog fragment: `.ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md`
- [ ] Carrier: `.ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md`
      slug field MUST be exactly `ce-506-daemon-vs-agent-rubric-design-s1`
- [ ] Work class line in PR body: `**Declared work class: story**`
      (LEGACY vocab: tiny|story|feature|epic; this is story = S)
- [ ] PR description MUST include: `[DESIGN-PREVIEW — AWAITING OPERATOR]`
- [ ] NEVER commit a file named READY (gate signal, not a commit artifact)
- [ ] No ce-ops issue number references in PR body, commit messages, or code comments
      (use plain English descriptions of the ticket's intent)

---

## Files to produce — COMPLETE territory

All three files are new. No existing file is modified by this PR.

```
docs/design/daemon-vs-agent-rubric.md                              (new)
.ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md           (new)
.ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md        (new)
```

**Brain-pin precompute (byte-change rule):** All targets are new files.
Prior sha256: N/A for each. The PR diff must show only additions on these
three paths — no deletions from any existing file.

---

## Frozen / in-flight paths — DO NOT TOUCH

| Path | Owned by |
|---|---|
| `.ce/brain/assertions.yaml` | PR #929 (ABSOLUTE STOP) |
| `validators/creator_engine_validator/ce_cli.py` | PR #929 (open) |
| `docs/reference/cli.md` | PR #929 (open) |
| `docs/design/ratification-authorization-binding.md` | PR #912 (open) |
| `validators/creator_engine_validator/launch_runtime.py` | dev-4 in-flight (ce-490) |
| `tools/controller/state_sync.py` | dev-3 prior unit (ce-497) |
| `docs/operations/CONTROLLER_BOOTSTRAP.md` | dev-1 prior unit (ce-496) |
| `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` | PR #925 (open) |
| `docs/governance/identity-registry.example.yaml` | PR #925 (open) |

No `surfaces/manifest.yaml` edit. No new `AGENTS.md` or `CLAUDE.md` changes.

---

## Design doc specification: `docs/design/daemon-vs-agent-rubric.md`

The document should follow this structure:

```
# Daemon vs. Agent-organ: routing rubric for CE factory organs

## 1. Why the distinction matters
## 2. Routing rubric
### 2.1 Deterministic daemons
### 2.2 Agent-organs
### 2.3 The four invariants (agent-organs only)
## 3. Applied: organ-by-organ classification
## 4. Organ hydration contract
## 5. Two Steinberger steals — first implementations
### 5.1 S1 — AutoReview analog
### 5.2 S2 — Triage analog
## 6. Governance note
```

**Section 6 — Governance note** must include:

> This document is a DESIGN-PREVIEW artifact. It has been HELD for Operator
> review before the merge gate is opened. The rubric is ratified as of
> 2026-07-08; the doc is the governed repo form of the ratification. Do not
> implement organ classication changes without first updating this doc and
> obtaining Operator sign-off.

Keep the doc factual and terse. Avoid marketing language. Tables are preferred over
prose for the rubric and organ-classification sections. The target audience is a future
contributor or replacement controller reading the repo cold.

---

## Changelog fragment (`.ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md`)

```markdown
## ce-506-daemon-vs-agent-rubric-design-s1

- docs(design): add daemon-vs-agent routing rubric design doc

  Adds docs/design/daemon-vs-agent-rubric.md: governed form of the 2026-07-08
  ratified rubric for deciding whether a factory organ should be implemented as
  a deterministic daemon (fail-closed, token-free) or as an agent-organ (judgment
  layer satisfying four invariants: deterministic trigger, versioned plain-text
  policy input, proposal-only output into deterministic disposer, token-rationed
  Haiku-class execution).

  Applies the rubric organ-by-organ (gate daemon, materializer, reviewer
  assignment, review execution, triage, belt-poller) and specifies two Steinberger
  steal implementations (AutoReview analog and belt-driven triage analog).

  DESIGN-PREVIEW: this PR is held for Operator review before merge.

  - **Declared work class:** story
```

---

## PR carrier (`.ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md`)

```markdown
# PR path manifest — ce-506-daemon-vs-agent-rubric-design-s1

slug: ce-506-daemon-vs-agent-rubric-design-s1

- **Declared work class: story**

[DESIGN-PREVIEW — AWAITING OPERATOR]

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=d62b64c5939dec4aa2cc80daa4276d1dcd4af546167039c28127f44c461be31d

\`\`\`text
.ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md
.ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md
docs/design/daemon-vs-agent-rubric.md
\`\`\`
```

Compute verification:
```python
import hashlib
paths = sorted([
    ".ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md",
    ".ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md",
    "docs/design/daemon-vs-agent-rubric.md",
])
print(hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest())
# → d62b64c5939dec4aa2cc80daa4276d1dcd4af546167039c28127f44c461be31d
```

---

## PR body template (use this verbatim, fill in validation output)

```markdown
## Summary

[DESIGN-PREVIEW — AWAITING OPERATOR]

- Add docs/design/daemon-vs-agent-rubric.md: governed form of the 2026-07-08 ratified
  routing rubric for CE factory organs.
- Codifies daemon vs. agent-organ decision criteria, four agent-organ invariants,
  organ-by-organ classification table, hydration contract, and two Steinberger steal
  implementations (AutoReview analog, belt-driven triage analog).
- PR is HELD pending Operator design review — do not merge without explicit Operator
  sign-off.

**Declared work class: story**

## Validation

- Confirm docs/design/daemon-vs-agent-rubric.md is present and well-formed Markdown
- `PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli validate-pr --repo-root . --declared-work-class S`

## Gate noise (pre-fill after running validate-pr)

<paste validate-pr output here>

## Closes

Governed repo form of the daemon-vs-agent routing rubric ratified 2026-07-08.
Applied organ-by-organ; two Steinberger steals specified as first implementations.
```

---

## Preflight gate (contained seat — targeted only)

```bash
# From worktree root (contained commit-only seat)

# Confirm doc is present
ls docs/design/daemon-vs-agent-rubric.md

# Validate carrier
PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli \
  validate-pr --repo-root . --declared-work-class S
```

Do NOT run the full test suite (contained seat rule: targeted tests only).
If validate-pr reports path-manifest mismatch, recompute AUTHORIZED_PATHS_SHA256
and update the carrier before committing.

---

## Stop-lines (enforced)

1. No code changes — this unit is documentation only.
2. No `assertions.yaml` modifications.
3. No gate surfaces (`ce_cli.py` is in PR #929 territory).
4. No READY file committed.
5. PR must be opened with `[DESIGN-PREVIEW — AWAITING OPERATOR]` in the title or
   description. The seat signals done by pushing the branch; the controller opens
   the PR with the design-preview flag and holds for Operator review.
6. Do not request auto-merge. Design preview PRs are Operator-gated.
