# CE-DEV-2 relay envelope for main Claude controller — Arad package review — 2026-07-06T12:22Z

Scope: local Arad handoff package at `tmp/arad-pack-0.3.3/`. No external send,
approval, merge, signing, or gate action performed.

Use this as the pointer artifact for the returning Claude controller. It folds
the Operator's review questions, my findings, the package decisions, and the
edits already made.

## Current package path

- Primary package: `tmp/arad-pack-0.3.3/index.html`
- Source/reference docs:
  - `tmp/arad-pack-0.3.3/03-cover-note-to-arad.md`
  - `tmp/arad-pack-0.3.3/01-upgrade-note-0.3.3.md`
  - `tmp/arad-pack-0.3.3/02-upgrade-procedure.md`
  - `tmp/arad-pack-0.3.3/WELCOME_YOUR_CE_JOURNEY.md`
  - `tmp/arad-pack-0.3.3/INDEX.md`
  - `tmp/arad-pack-0.3.3/PACK_MANIFEST.md`

## Decisions captured

1. **HTML is the primary package format.** Operator judged the HTML package
   better for humans and likely agents: easier to view, navigate, search, and
   review in a browser. `tmp/arad-pack-0.3.3/index.html` is now the primary
   deliverable. Markdown files remain source/reference material unless the
   Operator later decides to include or hide them.
2. **The user journey guide is included.** `WELCOME_YOUR_CE_JOURNEY.md` is a
   first-class section in the HTML package and should be delivered as part of
   the package.

## Operator questions/issues raised and responses

### 1. Package format

**Operator issue:** after comparing the Markdown and HTML versions, Operator
concluded HTML is better for humans and likely agents because it is easier to
view, navigate, and review.

**Response/finding:** agreed and recorded as package decision 1. `index.html`
is now the primary deliverable. Markdown remains source/reference material
unless Operator later decides to include or hide it in the delivered bundle.

### 2. Cover-note bullets looked incomplete

**Operator issue:** in the cover note, the sentences beginning "The full
repo-adoption step now works. If you ever tried running the" and "Your App
credentials are recognized correctly. The 0.3.2 planner had a" appeared
incomplete.

**Finding:** the Markdown list items were normally wrapped, but the simple
local HTML renderer treated continuation lines as separate text, causing the
bullets to appear truncated in the browser view.

**Response:** flattened those two cover-note bullets in
`03-cover-note-to-arad.md` and fixed the HTML renderer to fold indented
continuation lines into the preceding bullet/numbered item. This should also
prevent the same rendering defect in other package sections.

### 3. Smoke-check confusion

**Operator issue:** package said "resolve or waive the launch smoke check";
Operator asked whether a smoke check had already been performed.

**Finding:** yes, some smoke evidence exists, but not the specific remaining
check. C3 evidence covers:

- 0.3.3 install succeeded.
- signed spec verified.
- planner converged.
- apply path reached the join-PR step.
- GitHub Free protection limitation was recorded as reference mode.

The remaining check is narrower: a post-upgrade `ce launch` session on a
tenant-configured host was **not** performed.

Additional accuracy finding: `/var/tmp/ce-canary-c3/stage2_apply.json` ends
`ok:false` because `brownfield_verify_preserved_checks` refused with
`protection_floor_unenforceable` on GitHub Free private repo. Therefore earlier
"apply chain green" wording was too strong.

**Response:** corrected package language from "two OPERATOR-CHECK items" to
one optional remaining check; wheel digests are resolved. Replaced "apply chain
green" with "apply path reached join PR; protection floor recorded as reference
mode."

### 4. Include user journey guide

**Operator decision:** the user journey guide will be included in the package.

**Response:** recorded as decision 2 in `INDEX.md`, `PACK_MANIFEST.md`, and
the HTML overview. The HTML package presents CE Journey as a first-class
navigable section.

### 5. CE Journey overpromised natural-language workflow entry

**Operator issue:** the CE Journey said: "Start by describing what you want in
plain language to your coding agent in a CE session (`ce launch` opens the
session in your terminal). You are in the Frame stage..." Operator questioned
whether this would really invoke CE workflow, suspecting Arad would need an
explicit CE verb such as `frame`, `ce frame`, or similar.

**Finding:** Operator's instinct was correct. I verified the 0.3.3 canary venv:

- `/var/tmp/ce-canary-c3/ce-install/venv/bin/ce --help` exposes `session`,
  `launch`, `shape`, `scope`, `ratify`, `drive`, `report`, etc.
- `ce session` opens the CE session frame/status line.
- `ce launch` opens/attaches the visible governed coding-agent pane.
- `ce shape` is the Frame->Shape "grill me" helper.
- `ce scope` files a Scope.
- `ce ratify` places the human front-gate bet.
- `ce drive --spawn` drives the ratified Scope.
- `ce report` renders the completion report.

Natural language is useful inside the governed session to explore and draft,
but it is not itself the guaranteed workflow trigger. Governed work begins
when the user files/ratifies a Scope with explicit CE verbs.

**Response:** rewrote the CE Journey daily flow to say:

- open `ce session` and/or `ce launch`;
- use plain language to explore, but do not assume natural-language text
  automatically starts workflow;
- use explicit verbs: `ce shape`, `ce scope`, `ce ratify`, `ce drive --spawn`,
  `ce report`;
- the governing contract is the Scope record, not the chat transcript.

### 6. PRD creation/use was missing

**Operator issue:** journey section needed more detail on PRDs: what a PRD is,
how to create one with CE, and how to use an existing one.

**Finding:** CE does not need a separate magic PRD mode for this package. The
correct tenant explanation is:

- A PRD is a product requirements document, useful when a product/feature is
  larger than one Scope.
- A PRD does not authorize implementation by itself.
- Create a PRD as a docs-only Scope, then ratify/drive it.
- Use an existing PRD by putting it in the repo (example:
  `docs/prd/trading-terminal.md`) and creating smaller Scopes that cite it via
  `--note "Source PRD: docs/prd/trading-terminal.md"`.
- Rule of thumb: the PRD explains the product; each Scope authorizes one
  bounded piece of work.

**Response:** added a full PRD section to `WELCOME_YOUR_CE_JOURNEY.md` and
the embedded HTML copy, including create-new and use-existing command examples.

### 7. Trading terminal example and risk framing

**Operator issue/example:** asked how Claude Code would know what to do with a
natural-language request such as building an autonomous deterministic trading
terminal connected to Interactive Brokers, trading selected NASDAQ/NYSE
tickers under gates.

**Finding/response:** this is high-risk and should not jump straight to Build.
The updated Journey uses this as the example: first shape it into a PRD, then
split into small Scopes such as simulation mode, read-only broker connection,
risk-policy design, paper-trading gate, manual approval gate, audit log, and
only later any live trading capability. The examples explicitly mark PRD as
`--change-type docs` and a read-only broker connection as `--change-type code`
with done-when criteria proving no order placement path exists.

## Corrections made during review

- Cover-note bullets were visually incomplete in HTML because the local
  renderer mishandled wrapped Markdown list continuations. Fixed both by
  flattening the two cover-note bullets and by teaching the HTML renderer to
  fold continuation lines into list items.
- CE Journey originally implied that plain natural-language intent inside
  `ce launch` would automatically start a CE workflow. Operator flagged this
  as likely wrong. Verified 0.3.3 CLI surface: `ce` exposes explicit
  `session`, `launch`, `shape`, `scope`, `ratify`, `drive`, and `report`.
  Updated journey text to say natural language is for exploration/shaping, but
  governed work starts via explicit CE verbs and a ratified Scope.
- Added a PRD section to the CE Journey: what a PRD is, how to create one as a
  docs-only Scope, how to use an existing PRD, and the rule that a PRD informs
  Scopes but does not itself authorize implementation.
- Package wording was corrected from "two OPERATOR-CHECK items" to one
  remaining optional check. Wheel digests are already resolved; only the
  post-upgrade `ce launch` smoke remains.
- Clarified smoke evidence: C3 performed install/spec/planner/apply-path
  evidence and reached the join-PR step, with GitHub Free protection recorded
  as reference mode. It did **not** perform a post-upgrade `ce launch` on a
  tenant-configured host.
- Tightened "apply chain green" wording to "apply path reached join PR;
  protection floor recorded as reference mode" to avoid overclaiming, since
  `stage2_apply.json` ends `ok:false` due to `protection_floor_unenforceable`.

## Exact command-surface facts verified

Checked the 0.3.3 canary install at
`/var/tmp/ce-canary-c3/ce-install/venv/bin/ce`.

Relevant help facts:

- `ce session`: launch the governed session frame + status line.
- `ce launch`: open/attach the visible Controller-seat tmux launcher.
- `ce shape`: run the Frame->Shape grill-me on a partial draft.
- `ce scope`: file a Scope (Goal/Done-when/Budget/Change-type).
- `ce ratify`: place the bet on a Ready Scope (human-only front gate).
- `ce drive`: assemble the governed dispatch; `--spawn` launches the seat.
- `ce report`: render the per-run completion report.

Note: `cev3` also exposes these verbs but prints a deprecation warning; the
tenant-facing package should use `ce`, not `cev3`.

## Files updated

- `tmp/arad-pack-0.3.3/index.html`
- `tmp/arad-pack-0.3.3/INDEX.md`
- `tmp/arad-pack-0.3.3/PACK_MANIFEST.md`
- `tmp/arad-pack-0.3.3/03-cover-note-to-arad.md`
- `tmp/arad-pack-0.3.3/01-upgrade-note-0.3.3.md`
- `tmp/arad-pack-0.3.3/02-upgrade-procedure.md`
- `tmp/arad-pack-0.3.3/WELCOME_YOUR_CE_JOURNEY.md`

## Current open items for main controller / Operator

1. Decide whether to run or waive the optional post-upgrade `ce launch` smoke
   on a tenant-configured host before sending.
2. Fill `[Operator name]` in the cover note.
3. Decide whether Markdown source files should be bundled with the delivered
   HTML package or retained as Operator-only source/reference material.
4. Continue section-by-section package review from the updated HTML package.

## Non-actions / bounds honored

- Did not send anything to Arad.
- Did not approve, merge, sign, arm, or perform external comms.
- Edits were local package/research relay edits only.
