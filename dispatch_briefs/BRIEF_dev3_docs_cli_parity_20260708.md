# BRIEF — dev-3 — 2026-07-08 — docs/guide CLI parity + welcome.md orientation restructure (ce-ops#508)

Role: **implementer**. Contained COMMIT-ONLY seat. Fresh worktree at `/var/tmp/ce-docs-cli-parity`
off `origin/main` (fetch first). Branch `ce-docs-cli-parity`. No venv activation.
Use `--profile contained-seat` for preflight.
On green preflight signal: `READY ce-docs-cli-parity <commit-sha> .ce/pr-manifests/ce-docs-cli-parity.md`
If blocked: `BLOCKED ce-docs-cli-parity <one-line reason>`

## U1 — branch `ce-docs-cli-parity` (work class: story)

OPERATOR MANDATE (P1, ce-ops#508, gates the Arad send): two-part doc quality pass,
both required before the first external user sees the guide set.

Part (a): every `ce <verb>` reference in `docs/guide/*` must correspond to a
verb actually accessible via the shipped `ce` binary. Fix = align docs to shipped
CLI (conservative: do not invent or port verbs; where a doc journey step depends
on a genuinely missing verb, rewrite the step in honest prose and note the verb
gap in the PR body as a product follow-up item).

Part (b): restructure `docs/guide/welcome.md` per the orientation-only rule:
Welcome = what CE is + how to navigate the docs + where-to-go-next. Move the
install content (the "Day One as a new user: install, launch, use it" block
currently at ~line 63, containing the `curl | bash` block and `ce onboard`
instructions) into the appropriate existing install/quickstart doc. Do not
duplicate it; add a navigation pointer in welcome.md that directs install-seekers
to the right doc.

---

## Part (a): CLI verb parity sweep

### How to build the authoritative verb list

The shipped `ce` binary exposes two verb surfaces that must BOTH be checked:

**Surface 1 — ce_cli.py native verbs** (the v1 kernel CLI):
`validators/creator_engine_validator/ce_cli.py` on `origin/main`.
These are the verbs registered directly via `groups.add_parser(...)` in
`_build_parser()`. Read all `add_parser` call sites.

**Surface 2 — V3_FORWARDING_SHIMS** (the v3 verbs forwarded through `ce`):
`validators/creator_engine_validator/ce_cli.py`, dict `V3_FORWARDING_SHIMS`
(starts around line 247 on main). Every key in this dict IS a valid, accessible
`ce <verb>` — ce_cli.py forwards it to `v3_cli.py` via `_forward_v3_command`.

The union of Surface 1 and Surface 2 is the complete set of accessible `ce` verbs.
A verb found in `v3_cli.py` but NOT in V3_FORWARDING_SHIMS is NOT accessible from
the top-level `ce` binary — document any such gaps found.

### Known accessible verbs (confirmed on origin/main)

From V3_FORWARDING_SHIMS (verified): `ce scope`, `ce shape`, `ce ratify`, `ce drive`,
`ce dispatch`, `ce collect`, `ce pr`, `ce review`, `ce merge`, `ce configure-repo`,
`ce ruleset`, `ce review-submit`, `ce auto-merge`, `ce review-pickup`,
`ce escalation`, `ce notify`, `ce reap`, `ce status`, `ce show`, `ce artifacts`,
`ce report`, `ce install`, `ce carrier`, `ce guide`, `ce cockpit`, `ce session`,
`ce queue-poll`, `ce inbox`, `ce controller-inbox`, `ce queue-daemon`,
`ce emergency-stop`, `ce queue-dequeue`, `ce approval-capability`, `ce seats`,
`ce fleet`.

From ce_cli.py native parsers: `ce dequeue`, `ce verify-install`, `ce update`,
`ce clean-main-install`, `ce surfaces check-updates`, `ce surfaces fleet-rollout`,
`ce onboard`, `ce bootstrap`, `ce lane launch`, `ce lane status`, `ce lane verify`,
`ce lane archive`, `ce ledger record`, `ce ledger verify`, `ce worker allocate`,
`ce worker terminate`, `ce worker gc`, `ce worker status`, `ce worker spawn`,
`ce worker run`, `ce worker worktree-prune`, `ce fanin build`, `ce fanin inspect`,
`ce queue dry-run`, `ce queue inspect`, `ce queue poll`, `ce event append`,
`ce event verify`, `ce event sign`, `ce event replay`, `ce event index`,
`ce pcl append`, `ce pcl verify`, `ce pcl replay`, `ce pcl index`, `ce pcl merge`,
`ce brain init`, `ce brain assert`, `ce brain check`, `ce brain correct`,
`ce brain sync`, `ce brain ingest`, `ce brain recall`, `ce brain verify`,
`ce brain probe`, `ce brain bootstrap`, `ce orchestrator status`,
`ce connector verify`, `ce connector plan`, `ce connector fetch`,
`ce connector write-plan`, `ce connector submit`, `ce init`,
`ce containment-status`, `ce posture`, `ce validate-pr`, `ce automerge-decide`,
`ce automerge-status`, `ce automerge-kill-switch`, `ce takeover`,
`ce continuity-drill`, `ce publish-branch`, `ce herdr remote-attach`,
`ce conveyor sweep`.

### Sweep procedure

Do NOT rely on the list above alone. Do the sweep yourself:

```bash
# From your worktree on origin/main:
git grep -n "ce [a-z]" docs/guide/ | grep -E "\`ce [a-z]" | sort -u
```

For every `ce <verb>` occurrence found:
1. Check whether `<verb>` appears in V3_FORWARDING_SHIMS or in `add_parser` calls
   in `_build_parser()` of `ce_cli.py`.
2. If the verb is a multi-word subcommand (`ce brain init`, `ce lane launch`, etc.),
   check the subparser too.
3. If NOT found in either surface: document it as a mismatch.

### Known pre-enumerated mismatches (confirmed before dispatch)

No genuine mismatches were found during territory check — all verbs referenced in
the docs that were checked (`ce inbox`, `ce show`, `ce artifacts`, `ce scope`,
`ce shape`, `ce ratify`, `ce drive`, `ce merge`, `ce report`, `ce session`,
`ce launch`, `ce onboard`) are accessible via the shipped binary.

However, the systematic sweep MUST still run: there may be additional verbs in
files not spot-checked (e.g., `docs/guide/complete-walkthrough.md`,
`docs/guide/pilot-runbook.md`, `docs/guide/zero-to-governed-seat-quickstart.md`,
`docs/guide/first-value-mythos.md`, `docs/guide/agile-to-ce-sdlc.md`,
`docs/guide/contributing-to-ce.md`). Enumerate all findings in the PR body.

### Fix rules for genuine mismatches

- **Verb exists but under a different name or flag form:** align the doc to the
  real invocation. Do not introduce flags the command does not accept.
- **Verb genuinely does not exist in either surface:** rewrite the journey step
  to use prose or an equivalent verb that does exist. Note the missing verb in the
  PR body as a PRODUCT FOLLOW-UP for the CLI to add.
- **Do NOT port verbs between CLIs** (do not add a v3 verb to ce_cli.py or vice
  versa as part of this unit). Verb additions are a separate engineering task.
- **Vocabulary rules apply throughout:** no "bet", no "appetite"; the Goal/Done-when/
  Change-type trio where relevant; no internal host/topology names; no ce-ops# refs.

---

## Part (b): welcome.md orientation-only restructure

### Current state (ground from `git show origin/main:docs/guide/welcome.md`)

`docs/guide/welcome.md` (268 lines on main) has the following structure:
- Lines 1-52: What CE is, the key idea, navigation pointers — **KEEP (orientation)**
- Lines 63-130 approx: "Day One as a new user: install, launch, use it" — **MOVE**
  This block contains:
  - §0 Prepare: install coding agent CLI; `.hermes/` gitignore instruction
  - §1 Install: `curl | bash` one-liner + "on-brand alternative"
  - "If you arrived through an install handoff" section
  - §2 First run: `ce onboard`
  - §3 Use it exactly like your normal agent
- Lines ~130-175: "Your first real value" — **EVALUATE** (may stay in welcome as
  conceptual orientation, OR move; see decision below)
- Lines ~175-228: "For collaborators: contributing to Creator Engine itself" — **KEEP**
- Lines ~228-268: "Where to go next" table — **KEEP (navigation)**

### Required restructure

**Remove from welcome.md:** the entire "Day One as a new user: install, launch,
use it" block (§0 Prepare through §3 Use it). This is install/quickstart content,
not orientation.

**Important:** the `.hermes/` gitignore instruction in §0 Prepare is REMOVED as
a consequence of moving this block. Do not carry it to the destination doc —
ce-ops#507 (BRIEF_dev1_hermes_retirement_20260708) is retiring that requirement
from `ce_onboard.py` concurrently. The destination install content should NOT
instruct users to gitignore `.hermes/`. If dev-1 has merged before this unit,
`ce init` creates the `.ce/state` layout and no gitignore entry is required.
If dev-1 has NOT yet merged, write the destination content without the `.hermes/`
instruction and add a note in the PR body: "Depends on ce-hermes-retirement for
the gitignore requirement removal; CI will verify compatibility."

**Move destination:** the Day One install content belongs in
`docs/guide/quickstart.md` or `docs/guide/zero-to-governed-seat-quickstart.md`.
Read both on `origin/main` first. Choose the more appropriate destination:
- If `quickstart.md` already covers the quick first-run (it does: it has
  `ce onboard` instructions), do NOT duplicate the content. Instead, replace the
  Day One block in welcome.md with a brief (2-4 sentence) bridging paragraph and
  a clear pointer: "To install and run CE for the first time, follow
  [quickstart.md](./quickstart.md)." If the quickstart is missing the
  `curl | bash` one-liner or the "if you arrived through an install handoff"
  material, ADD those to quickstart.md (additively, not by replacing existing
  content).
- Keep the Day One content ONCE. If it already exists in the destination, the
  welcome.md block simply becomes a pointer.

**"Your first real value" section (~lines 130-175):** KEEP in welcome.md. This
is conceptual orientation (what "first deny" and "first governed change" mean),
not install instructions. It answers "what am I working toward?" — appropriate
for an orientation doc.

### Orientation rule for welcome.md after restructure

The restructured welcome.md must satisfy: a new reader who has never heard of CE
can read it and understand (a) what CE is, (b) how the governed workflow feels in
practice (the first-deny moment), (c) what "first real value" means, (d) where to
go to install and get started, and (e) how to contribute. It must NOT contain
step-by-step install instructions or copy-paste command sequences.

### Vocabulary rules (PUBLIC-FACING content)

- No "bet", "appetite", or internal program names
- No ce-ops# ticket references
- No seat, host, topology, or fleet internal names
- No `.hermes/` mentions in any user-facing instruction context (per retirement mandate)
- Goal/Done-when/Change-type trio where applicable
- Budget appears at most as an opt-in aside ("you can optionally set a cap")

---

## Hard constraints

- Do NOT touch `README.md` — claimed by in-flight `ce-readme-overhaul` (dev-4).
- Do NOT touch `validators/creator_engine_validator/ce_cli.py` or any
  `validators/creator_engine_validator/checks/version_drift.py` path — claimed
  by ce-readme-overhaul (dev-4 version-drift gate extension).
- Do NOT touch `validators/creator_engine_validator/ce_onboard.py` — claimed
  by `ce-hermes-retirement` (dev-1). If the welcome.md Day One block contains a
  `.hermes/` gitignore instruction, simply remove it (do not rewrite it to point
  at ce_onboard.py behavior; that is dev-1's responsibility).
- Do NOT add or modify CLI verbs (this is a docs-only unit).
- Do NOT restructure any other docs/guide file beyond the minimal edits needed to:
  (a) fix verb mismatches found in the sweep, and (b) receive the moved content
  from welcome.md without duplication.
- Maintain all existing inbound links: if any file outside docs/guide/ links to
  a specific heading in welcome.md that is being removed, update the link to point
  to the new location.

---

## Standing preflight directive (ce-ops#303)

FULL `ce validate-pr --profile contained-seat` green before commit-for-harvest.

KNOWN SEAT-ENV FALSE-REDS (proven 2026-07-08, controller has evidence): the
control-plane portability gate and the check-examples/libsodium gate may fail in
this seat's image on paths OUTSIDE your diff. If the ONLY failures are those two
gates on files you did not touch, note them verbatim in the evidence section and
signal READY anyway — the controller re-runs the definitive CI-parity preflight at
harvest. Any failure touching YOUR changed files = fix it or signal BLOCKED.

---

## STOP LINE

No pushes, no PRs, no gate acts, no signing. Only these paths:

```
docs/guide/welcome.md
docs/guide/quickstart.md
docs/guide/solo-ceo-onboarding.md
docs/guide/solo-dev-onboarding.md
docs/guide/complete-walkthrough.md
docs/guide/pilot-runbook.md
docs/guide/zero-to-governed-seat-quickstart.md
docs/guide/agile-to-ce-sdlc.md
docs/guide/first-value-mythos.md
docs/guide/contributing-to-ce.md
docs/guide/understanding-ce.md
.ce/changelog/ce-docs-cli-parity.md
.ce/pr-manifests/ce-docs-cli-parity.md
```

Any docs/guide/* file not in this list that the sweep reveals has verb mismatches:
add it to your carrier manifest (update AUTHORIZED_PATHS_COUNT and
AUTHORIZED_PATHS_SHA256) and include it in the PR body explanation. The stop line
may expand to cover sweep findings, but ONLY within `docs/guide/`.

Carrier: slug == `ce-docs-cli-parity` exactly; every changed path enumerated;
exactly ONE `- **Declared work class:** S` line.

Evidence in the PR body must include:
1. The raw `git grep` verb sweep output: every `ce <verb>` occurrence in
   docs/guide/*, labeled VERIFIED (verb exists) or MISMATCH (verb missing).
2. For each genuine mismatch: the original line, the rewritten line, and the
   product follow-up note.
3. The welcome.md restructure: confirm the "Day One" block line range removed,
   the destination file and line range where content landed (or the pointer text
   added in its place).
4. Confirmation that no heading referenced by external links was removed without
   updating the linker.
