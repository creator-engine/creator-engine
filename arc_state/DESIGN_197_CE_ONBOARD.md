# DESIGN — `ce onboard` first-run command + agent-installable CE (ce-ops#197, N1-W5)

**Status:** DESIGN / RESEARCH ONLY — no production code, no PR. This doc is the
sole deliverable.
**Author seat:** CE-DEV-2 controller worker (DGX, `/home/cedev2/creator-engine`).
**Date:** 2026-06-22 · **Revised 2026-06-23** (install-model ratified).
**Scope frame:** Make CE *first-class agent-installable* and wrap the
first-run flow (trust-verify → install → `ce brain init` → first governed launch)
into a guided, quoting-safe, robust, gracefully-degrading experience across **three
install modes**. The install agent is **just another governed CE agent** — not
forbidden.

---

## REVISION 2026-06-23 — install-model ratified

Operator ruling 2026-06-23 ([[ce-agent-pointed-install-model]]) **flips the prior
default**. The original design (below, §3.1) defaulted `--install-mode=print`
(human runs each printed step) and fenced agent-driven install OFF as an escalation
line. That HOLD was a controller-overnight deferral; the Operator has now ruled
agent-driven install **IN SCOPE and FIRST-CLASS — under governance, not forbidden.**

**What changed:**

1. **CE's install novelty is agent-driven install.** A user installs CE by pointing
   THEIR OWN agent at CE; the agent reads CE's signed, machine-readable install spec
   (`docs/llms-install.md`, already signed) and carries out the install under the
   user's authority. This is predicted to become THE norm once machines ship agents
   out-of-the-box (NVIDIA + Microsoft, first machines ~Sept 2026 — aligns with the
   pitch). CE's job: be **cleanly agent-installable** (verifiable, idempotent,
   well-specified steps; a stable machine-readable spec the agent consumes).
2. **Three install modes** replace the single print/exec toggle (§A below):
   agent-pointed (PRIMARY) · guided one-liner (de-facto now) · one-liner-hands-to-agent
   (hybrid). `--install-mode=print` (human runs each printed step) is demoted to the
   **manual fallback**, not the default.
3. **The old escalation line is re-stated, not deleted.** "No onboarding-agent
   autonomous install-EXECUTION" → **"no UNGOVERNED / UNCONSENTED install."** The
   user's invocation (running the one-liner / pointing their agent) IS consent; the
   agent still gates the consequential steps via the governed-install rail (§B).
4. **A governed-install rail** (§B) is now the load-bearing safety model: auto
   trust-verify + confirm-on-consequence/irreversibility + emit an audit record
   ([[ce-visibility-channel-emission-model]]).

**What is preserved unchanged:** the 6 real frictions and their fixes; Decision 4
(profile-PATH default-on managed block + `--no-fix-path`); Decision 5 (`v1`
classification of the new modules); the docs-reconciliation + path-manifest +
version-boundary coupling notes. These carry through the revised unit breakdown (§C)
verbatim in intent.

The original §0–§5 below remain as the detailed substrate (command surface,
friction analysis, file citations). §A/§B/§C/§D are the revised top-of-doc design
and are authoritative where they differ from the original §3/§4/§5.

---

## A. The three install modes — when each applies

CE supports three install modes; they are not exclusive — they form a **fallback
chain** keyed to (a) whether the user has an agent and (b) install complexity. The
machine-readable spec (`docs/llms-install.md`) and the one-liner (`docs/install.sh`)
are the SAME verified substrate underneath all three; the modes differ only in
*who drives* the steps.

### A.1 Agent-pointed (PRIMARY / novel) — the user's own agent installs CE

The user points their own coding agent at `https://creator-engine.dev/llms-install.md`.
The agent:

1. **Verifies the spec** (`docs/llms-install.md:105-149`, §0) with stock `ssh-keygen
   -Y verify` against the pinned `ce-root-v1` trust root bound to an independent
   out-of-band DNS-TXT fingerprint anchor — **before any step**, STOP on anything but
   `Good`. This is the agent-installability contract: no CE tooling required to
   establish trust (it breaks the bootstrap circularity).
2. **Runs the agent loop** the spec already declares (`llms-install.md:185-224`):
   `cev3 onboard --inventory` → prepare `ce-install.answers.yaml` WITH the operator
   (IaC, secrets as SecretRefs only) → `--plan` (terraform-plan analog, fail-closed
   on unknown keys) → apply. Re-runs converge (detected state skipped/reconciled).
3. **Operates under the governed-install rail (§B)** — auto trust-verify, autonomous
   on low-risk reversible user-scoped steps, confirm-on-consequence before
   sudo/system/cloud/irreversible, emit an audit record.

**CE's design obligation here:** keep `llms-install.md` a *stable, signed,
machine-readable contract* and make every install step **verifiable + idempotent +
well-specified**. `ce verify-install` (friction #4, PR-1) is the agent's
post-condition self-check ("am I the genuine published release"). The new
**`ce onboard --emit-manifest` / structured onboard manifest** (PR-5b) gives the
agent a machine-readable description of the first-run phases (what onboard would do,
each phase's blast-radius + reversibility class) so the agent can plan + gate them.

### A.2 Guided one-liner (de-facto NOW) — the human runs one copy-paste line

`curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash`
(`llms-install.md:155`). `install.sh` does **everything**, guided; the human runs NO
complex commands and types nothing but `sudo`/the GitHub-App click. This is the
existing, working path; the one-liner already owns §0 trust-verify
(`install.sh:485-524`), wheelhouse hash-check, venv build, and authenticated
inventory. For users WITHOUT an agent, this is the entry point. `ce onboard` wraps
the post-install legs (`ce brain init` + first governed launch) the one-liner
stops short of (`install.sh:716-740`).

### A.3 One-liner-hands-to-agent (hybrid) — detect complexity, hand off to the user's agent

When the guided one-liner hits **real complexity that bash handles poorly**
(infra/env/variable resolution, multi-step cloud setup, ambiguous host topology),
it DETECTS this and HANDS OFF to the user's agent to finish — the user already has
one, and complex installs need agent reasoning, not more bash.

- **Detection heuristic (when to hand off):** `install.sh` already produces a
  machine-readable *inventory* of unmet facts (`cev3 onboard --inventory`:
  `needed (would ask at step N)` · `secret (ref required)` · missing `runsc`/`proxy`/
  creds/GitHub-App — `llms-install.md:168-175`, `install.sh:716-740`). Hand-off
  triggers when the inventory contains items that are (i) **interactive/ambiguous**
  (a key needs operator judgement, not a default), (ii) **multi-variable/infra**
  (gVisor + egress-proxy provisioning, cloud creds, branch-protection reconcile),
  or (iii) **secret-resolution** that bash cannot safely orchestrate (SecretRef
  prompts at moment-of-use). Pure missing-package installs with a scoped
  `host.sudo_grant` stay in bash (mode A.2). The count/severity of unmet inventory
  items crossing a threshold = the heuristic; it is *derived from existing inventory
  output*, not a new classifier.
- **Handoff mechanism (how install.sh discovers + invokes the user's agent):**
  1. **Discover** the user's agent: probe a small ordered list — `$CE_INSTALL_AGENT`
     (explicit override, an argv command template) → known harness binaries on PATH
     (`claude`, `codex`, …) → `$EDITOR`-adjacent / a config hint. If none found,
     fall through to mode A.4 (print the exact `llms-install.md`-pointer for the
     human to paste into whatever agent they have).
  2. **Hand off** by invoking the discovered agent with a **self-contained brief**:
     the verified-spec path, the verified trust-root + anchor, the answers file (if
     any), and the *remaining inventory* (the exact unmet items). install.sh passes
     the **already-verified** spec + trust artifacts so the agent does not re-fetch
     over a fresh trust boundary — provenance is carried, not re-bootstrapped. The
     brief embeds content (no private ticket refs — [[ce-no-egress-seat-self-contained-briefs]]).
  3. The agent then runs A.1's governed loop from the handoff point forward.

### A.4 Manual print (FALLBACK) — `--install-mode=print`

`--install-mode=print` prints each step for a human to run by hand. This is the
**manual fallback** for the no-agent / locked-down / debug case — NOT the default.
It is the old escalation-era default, demoted.

### A.5 Mode selection (default + override)

`ce onboard` / `install.sh` selects automatically: **agent present + reachable →
hybrid hand-off when complexity is detected (A.3), else guided (A.2); no agent →
guided one-liner (A.2); explicit `--install-mode=print` → manual (A.4).** Pointing
an external agent at `llms-install.md` (A.1) is outside `install.sh` entirely — it
is the agent's own entry. The default is NEVER "print every step for the human."

---

## B. The governed-install rail (the safety model)

The install agent — whether the user's external agent (A.1), the handed-off agent
(A.3), or `install.sh` acting on the user's behalf (A.2) — is **just another
governed CE agent**. The rail has three non-negotiable legs. It binds to
[[ce-autonomous-authority-doctrine]] (authority GRANTED ≠ EXERCISED; bar =
consequence × novelty × irreversibility) and [[ce-visibility-channel-emission-model]].

### B.1 Auto trust-verify — BEFORE installing anything

Automatic, non-negotiable, first. Signature (SSHSIG over canonical bytes) +
**DNS-anchor binding** (same-origin-only trust roots are REFUSED —
`llms-install.md:120-149`, `install.sh:485-524`). On anything but a `Good` result:
**STOP before any persistent mutation.** No mode skips this — it is the grader
living outside the agent, applied to CE's own install. `ce verify-install` (PR-1) is
the agent-consumable re-check of the *installed* artifact's provenance after the
fact (friction #4).

### B.2 Confirm-on-consequence / irreversibility

The agent proceeds **autonomously** for low-risk, reversible, **user-scoped** steps
and **CONFIRMS** before high-consequence / irreversible / out-of-scope steps. The
classifier is `consequence × novelty × irreversibility`:

| Step | Class | Default behavior |
| --- | --- | --- |
| Download artifacts, fetch spec/trust-root/anchor | low / reversible / user-scoped | **autonomous** |
| Verify signatures + hashes | read-only | **autonomous** |
| Build venv in `~/.local` (user-local, removable) | low / reversible / user-scoped | **autonomous** |
| Managed `.bashrc`/`.profile` PATH block (CE-marked, reversible) | low / reversible / user-scoped | **autonomous** (Decision 4 default-on; `--no-fix-path` opt-out) |
| `ce init` / `ce brain init` (local ledger, idempotent) | low / reversible / user-scoped | **autonomous** |
| `sudo` / system packages (`runsc`, `proxy`, `git`, `python`) | high / system-scoped | **CONFIRM** (a scoped `host.sudo_grant: [runsc,proxy]` = the operator's written upfront consent; anything OUTSIDE the grant still asks) |
| Cloud / infra provisioning, branch-protection mutation | high / consequential / partly irreversible | **CONFIRM**, show desired-state diff first (`llms-install.md:320-333`) |
| GitHub-App authorization click | irreversible-ish, operator-only | **HUMAN ACTION** (the one click; first-run only) |
| Anything OUTSIDE the user's CE scope | high / novel | **CONFIRM** (refuse non-interactive with the exact missing list) |
| Weakening the grader / cost opt-out / protections below floor | binding | **RATIFIED-HUMAN-ONLY** binding; the agent may NEVER set it (`llms-install.md:204-209, 244-250`) |

This is the precise sharpening of the old escalation line: agent-autonomy is GRANTED
for the reversible user-scoped majority and WITHHELD (confirm/ratify) for the
consequential minority. The user's invocation is consent **to the install**, not a
blank check for every consequential sub-step.

### B.3 Emit an audit record

The install emits a **structured, retrospectively-auditable record** of what it did
— each phase, its consequence-class, the autonomous-vs-confirmed decision, the
verify results, and the final converged state — into CE's canonical read-model so it
is auditable after the fact ([[ce-visibility-channel-emission-model]]: ratify +
retrospective-audit is the default; watching is opt-in). Concretely: `ce onboard
--json` already emits a per-phase machine record (§1.1); the rail extends each phase
record with `{consequence_class, decision: auto|confirmed|ratified, verify: {...}}`
and writes the run as one audit envelope. This is the same emission seam as
contact-on-need: when the agent hits a CONFIRM/RATIFY gate it emits an "I need your
input" event to the user's chosen channel (it does not silently block in a dark
pane).

---

## C. Revised ordered PR-sized unit breakdown (~200-400 ln each, strict-TDD)

Supersedes §4. Same repo invariants per PR: **tests first**; `.ce/pr-manifests/<slug>.md`
matching `base..HEAD`; `.ce/changelog/<slug>.md`; `_versions.py` classification for
any NEW module. Adding `ce onboard` / `ce verify-install` command groups **trips
`validators/tests/unit/test_v1_docs_reconciliation.py`** (exact `ce` group-set ==
README.md, `:52-65`) → those PRs MUST update `README.md:68-73` AND name both
`README.md` and the test in the manifest ([[ce-new-ce-group-docs-coupling]]).
Decision 5: classify the new modules **`v1`** in `_versions.py` (they are driven by
the v1 `ce` kernel; AST-guard the cross-plane imports; a `BASELINE_SHARED_TO_VERSION_ALLOWLIST`
edge may be needed for the v3-installer-parsing reuse — `_versions.py:195,249`).

**Ordering rationale:** leaf utilities + the agent-installability surface first
(PR-1..4), so the orchestrator (PR-5) and the hybrid hand-off (PR-7) compose
already-tested pieces; the launcher refuse-fix (PR-6) is parallelizable, sequenced
to avoid churn on the shared launch path.

| PR | Title | Friction(s) | Coupling |
| --- | --- | --- | --- |
| PR-1 | `ce verify-install` provenance self-check | **#4** | new group → docs-reconciliation + README; `_versions.py` v1 |
| PR-2 | install.sh robustness: low-TMPDIR fallback + clearer lock UX | **#3, #5** | docs-tree; no `_versions.py` |
| PR-3 | profile-PATH standardization writer (default-on, `--no-fix-path`) | **#2 onboard-side** | `_versions.py` v1 |
| PR-4 | programmatic `ce init`/`ce brain init` + doctor probes | — | — |
| PR-5 | `ce onboard` orchestrator (6 phases) + `--emit-manifest` | **#6** | new group → docs-reconciliation + README; `_versions.py` v1 |
| PR-6 | launcher resolve-harness + refuse-before-spawn + lifecycle reconcile | **#2 root, #6** | shared launch path; no new group |
| PR-7 | install.sh hybrid hand-off: complexity-detect + agent-discover/invoke | (enables A.3) | docs-tree + brief contract |

### PR-1 — `ce verify-install` (friction #4) · the agent-installability post-check
NEW `ce_provenance.py` + `ce verify-install` subparser; reuse `v3_installer.py`
digest parsing (`:820-928`). Reads `install-state` `sha256s_sha256` + `package_version`,
recomputes vs the pinned venv dir, online compares to live `SHA256SUMS`, `--offline`
= local only. **Reproduces hashes, never transcribes** ([[ce-verifier-hash-false-positive]]).
Tests: genuine-match PASS; tampered REFUSE; offline degrade; missing-state refuse.
~250-350 ln. (This is what an A.1 agent calls to confirm "genuine release".)

### PR-2 — install.sh robustness (frictions #3, #5)
`docs/install.sh`: probe free space before `mktemp -d` (`:472`), fall back to a home
staging dir below threshold; improve `install_lock_held`/`stale_install_lock`
(`:402-415`) to name the holder pid + copy-paste remediation (optional
`CE_INSTALL_WAIT`/`--force`). Shell tests via the `test_v3_installer.py` subprocess
pattern. ~150-250 ln.

### PR-3 — profile-PATH standardization writer (friction #2 onboard-side)
NEW `ce_profile_path.py`: idempotent CE-marked block (`# >>> creator-engine PATH >>>`)
adding `~/.local/bin` + npm global bin; safe re-run; never clobber non-CE lines.
**Default-on with `--no-fix-path` opt-out (Decision 4).** Under the rail (§B.2) this
is a low/reversible/user-scoped step → autonomous. Tests: add-once / re-run no-op /
preserve non-CE lines / marker detection. ~200-300 ln. `_versions.py` v1.

### PR-4 — programmatic init/brain-init + doctor probes
Confirm `ce init` (`ce_cli.py:800`) + `ce brain init` (`:1972`) are callable as
library functions for orchestration; add the doctor low-TMPDIR + PATH-gap probes
onboard phase-1 consumes. ~150-250 ln. (May merge into PR-5.)

### PR-5 — `ce onboard` orchestrator + `--emit-manifest` (friction #6)
NEW `ce_onboard.py` + `ce onboard` subparser; sequences the 6 phases (§1.1);
`--json`, `--install-mode {agent,guided,hybrid,print,skip}` (NB: enum revised from
the old `{auto,print,skip}` — default selection per §A.5, **not** `print`),
`--no-launch`, `--no-fix-path`, `--yes`, `--harness`; idempotent + resumable;
degradation branches (offline / no-tmux / already-onboarded). First-launch drives
**exactly ONE** `ce launch` + verifies single live controller via `seat_lifecycle`
(friction #6). **`--emit-manifest`** (the A.1 agent-installability surface): emit a
machine-readable description of the onboard phases — each phase's id, action,
blast-radius, **consequence-class + reversibility** (the §B.2 classification) — so
the user's agent can plan + gate them. Each `--json` phase record carries the §B.3
audit fields. Tests: happy-path (mocked legs); each degradation branch; idempotent
re-run; refuse-on-unverified-install; single-controller assertion; manifest schema +
consequence-class correctness. ~350-400 ln (split orchestrator vs CLI-surface if
over budget). `_versions.py` v1; new group → docs-reconciliation + README.

### PR-6 — launcher resolve-harness + refuse-before-spawn (friction #2 root, #6)
`codex_launch_spec.build_governed_codex_command` (`:229-236`) +
`launch_runtime.py:219`: resolve harness via `shutil.which` against a composed
known-good PATH (or a configured absolute path) and **refuse with a clear message
before any side effect** if unresolved. Add lifecycle reconcile so an exec-127 seat
does not stay `state: alive` (#212 finding 2); investigate double-`launched` event
(finding 3). Tests: unresolved → refusal (no spawn, no stale alive record); resolved
→ unchanged; reconcile on exec-fail. No new group. ~250-350 ln. Parallelizable;
sequence late.

### PR-7 — install.sh hybrid hand-off (enables mode A.3)
`docs/install.sh`: after the authenticated `cev3 onboard --inventory`
(`:716-740`), evaluate the **complexity heuristic** (§A.3: count/severity of
interactive/infra/secret-resolution inventory items vs threshold). When it trips:
**discover** the user's agent (`$CE_INSTALL_AGENT` → known harness binaries on PATH →
fallthrough to A.4 print) and **invoke** it with a self-contained brief (verified
spec + trust-root + anchor + answers + remaining inventory; provenance carried, not
re-bootstrapped). Tests (subprocess pattern): heuristic trips on infra-heavy
inventory + stays in-bash on simple; discovery order; brief contains the verified
artifacts + embeds content (no external refs). Bash, docs-tree; brief contract is the
testable seam. ~250-350 ln.

### Friction → unit map (all 6 preserved)

| # | Friction | Unit |
| --- | --- | --- |
| 1 | Hand-typed §0 trust-verify quoting-hostile | covered by modes A.1–A.3 wrapping `install.sh` / spec §0 (never re-typed); rail §B.1 |
| 2 | Launcher bare-`codex` PATH gap + `.bashrc` drift | **PR-3** (profile block) + **PR-6** (refuse-before-spawn) |
| 3 | `/tmp` tmpfs exhaustion mid-wheelhouse | **PR-2** |
| 4 | `+buildsha` ambiguity, no provenance self-check | **PR-1** (`ce verify-install`) |
| 5 | install-lock collision confusing UX | **PR-2** |
| 6 | stale lifecycle / double-spawn on relaunch | **PR-5** (single-controller assertion) + **PR-6** (lifecycle reconcile) |

---

## D. Risks / open questions for the Operator

1. **`--install-mode` enum + default.** Revised to `{agent, guided, hybrid, print,
   skip}` with auto-selection per §A.5 (default is NEVER `print`). Confirm the enum
   names + that `hybrid` is the right default when an agent is present and complexity
   is detected (vs always-guided-bash).
2. **Hybrid hand-off discovery surface (PR-7).** The agent-discovery order
   (`$CE_INSTALL_AGENT` → PATH harness binaries → print-fallback) is a new trust
   surface: install.sh invoking a local binary. Recommend it pass only the
   **already-verified** artifacts + a content-embedded brief, never re-mint trust,
   and require explicit user confirm before first invoking a discovered agent
   (consequence × novelty bar — invoking an external program is novel). Confirm the
   discovery list + the confirm-before-invoke default.
3. **Consequence-class table (§B.2) is the policy ground-truth.** It encodes which
   steps are autonomous vs confirm vs ratified. Recommend it live as a *data table*
   the orchestrator + `--emit-manifest` both read (single source), not scattered
   conditionals. Operator to confirm the autonomous/confirm boundary — esp. the
   managed `.bashrc` block being autonomous (Decision 4 default-on).
4. **Audit-record schema (§B.3) reuse.** Recommend the install audit envelope reuse
   the existing read-model/runtime-evidence emission seam rather than a bespoke
   format, so it renders through the same channel layer
   ([[ce-visibility-channel-emission-model]]). Confirm the envelope shape / whether a
   new evidence kind is warranted.
5. **`_versions.py` classification.** Decision 5 = `v1` for `ce_onboard`,
   `ce_provenance`, `ce_profile_path`. They reuse `v3_installer` parsing → may need a
   `BASELINE_SHARED_TO_VERSION_ALLOWLIST` edge with an AST cross-plane guard. Confirm
   `v1` (vs `shared`) at PR time.
6. **Docs-reconciliation is a guaranteed CI trip** for PR-1 + PR-5 (new `ce` groups)
   — README + the test must be in the manifest or CI blocks ([[ce-new-ce-group-docs-coupling]]).
7. **install.sh is shell, not Python** → harder TDD for PR-2/PR-7; lean on the
   `test_v3_installer.py` subprocess pattern; keep shell changes minimal + testable.
8. **#212 double-spawn (finding 3)** may be non-deterministic; PR-6 should at minimum
   make single-controller the asserted post-condition even if the root needs a
   follow-up.

---

## 0. Two distinct "onboard" things — name the collision up front

There is already a `cev3 onboard` / `ce onboard`-adjacent surface, and it is **not**
the first-run one-shot this work-unit builds. Disambiguate before designing:

| Name | What it is | File |
| --- | --- | --- |
| **`cev3 onboard` (existing)** | Spec-driven *infra-adoption applier*: forge selection, trust-root/anchor verify, `--inventory` / `--plan` / `--apply` of a signed install spec into a GitHub forge. The E2 live-drive seam. | `validators/creator_engine_validator/v3_cli.py:2764` (`_cmd_onboard`), parser at `:3968`; drivers `onboard_apply.py`, `onboard_apply_live.py` |
| **`ce onboard` (NEW — this work)** | First-run **one-shot orchestrator**: verify-install provenance, ensure venv+PATH+brain ledger, drive exactly one governed controller launch. A *kernel* (`ce`) command that composes existing pieces; it does **not** re-implement adoption. | NEW module under the `ce` kernel CLI (`ce_cli.py`) |

The N1-W5 ticket (#197) is framed as the big self-driving DevOps-agent vision; the
**night-arc work-unit** is the concrete, in-scope subset: wrap the brittle
hand-typed §0 trust-verify + install + brain-init + first launch into one robust
guided command. This doc designs that subset and explicitly fences off the agent
autonomy leg.

---

## 1. Scope + UX

### 1.1 The guided flow (happy path)

`ce onboard` runs as a single guided, idempotent, resumable sequence. Each step is
a **named phase** with its own preflight, action, and verification, emitting a
status line (and `--json` machine record). Phases:

1. **Preflight / environment doctor.** Reuse `ce doctor` (`ce_cli.py:778`) logic:
   detect OS/arch, Python floor (>=3.14), required bootstrap tools, governed-host
   posture. Detect low-`/tmp` (NEW — friction #3) and per-profile PATH gaps
   (NEW — friction #2). Plain-language summary of what onboard will do + blast
   radius; single approval gate (T0 dialogue from #197, minimal form).
2. **Install / acquire** (if `ce`/`cev3` not already a genuine published release).
   Delegate to the published `install.sh` one-liner (the quoting-safe path) rather
   than re-typing §0. `ce onboard` either (a) detects a present, verified install
   and skips, or (b) prints/executes the canonical `curl … | bash` install with the
   correct trust-anchor + answers, never asking the user to hand-build the
   fingerprint bind. (Execution-vs-print is a user choice; default = print the
   exact command unless the user opts into local exec — see §5 escalation.)
3. **Provenance self-check** — `ce verify-install` (NEW). Confirm "am I the genuine
   published release" by comparing the recorded install-state `sha256s_sha256`
   against the live `SHA256SUMS` (real provenance, friction #4). Resolves the
   `0.2.0+<buildsha>` ambiguity.
4. **PATH standardization** (NEW — friction #2 / #212). Idempotently ensure the
   user profile exports both `~/.local/bin` (CE shims) and the npm global bin
   (`~/.npm-global/bin`, harness binaries) so the governed launcher resolves the
   harness on the seat's *actual* (non-login) launch env. Print a re-source hint.
5. **Workspace bootstrap** — `ce init` (`ce_cli.py:800`, local kernel state) +
   `ce brain init` (`ce_cli.py:1972`, idempotent genesis ledger, #206). Makes the
   workspace launch-capable with no manual `ce brain assert`.
6. **First governed launch** — drive exactly ONE `ce launch` (`ce_cli.py:990`),
   verify the controller registered exactly once in `seat_lifecycle`
   (friction #6 / #212), and surface the live seat.

### 1.2 Automate vs prompt

- **Automate (no prompt):** doctor, low-`/tmp` detection + TMPDIR fallback,
  provenance self-check, PATH idempotent profile edit, `ce init`, `ce brain init`,
  lifecycle verification.
- **Prompt once (T0 approval):** the upfront plain-language plan + blast-radius
  approval; any credential entry (answers file / forge creds) the underlying
  install needs; whether to *execute* the install locally vs *print* the one-liner.
- **Never hand-typed:** no `sed`/`awk`/`grep` fingerprint bind, no manual
  `ssh-keygen -Y verify`. The install.sh one-liner owns all of that
  (`docs/install.sh:485-524`).

### 1.3 Graceful degradation

- **Offline / no network:** skip install + provenance-against-live-SHA256SUMS;
  fall to provenance-against-recorded-state only; still run init/brain-init/launch
  if a venv exists. Emit a clear "offline: verified against local state only" note.
- **Missing deps (uv/python/ssh-keygen):** doctor refuses with the exact remedial
  command, never a cryptic mid-install failure.
- **No tmux / not a governed host:** stop before launch with the `ce doctor
  --require-visible-launch` refusal message; everything up to launch already done.
- **Already onboarded:** every phase is idempotent → re-running is a safe no-op
  that reports current state (mirrors `ce brain init` already-initialized path,
  `ce_cli.py:1983-1987`).

---

## 2. Current state — what exists, and which friction each phase fixes

### 2.1 `install.sh` (`docs/install.sh`, 26 KB, the published one-liner)

- Trust chain: fetch signed spec + trust root, key-id presence check, canonical
  hash bind, `ssh-keygen -Y verify` (`:485-524`). **All quoting-hostile hand-typing
  lives here today when done manually — friction #1.** The one-liner already
  encapsulates it; `ce onboard` should *point at / wrap* it, not reproduce it.
- Wheelhouse hash-check vs `SHA256SUMS` (`:615-635`); venv build pinned to
  `venv-<version>-<sha256s_sha>` (`:589`), atomic promote (`:700-708`).
- CLI shims: `install_cli_shims` creates `~/.local/bin/{ce,cev3}` symlinks but
  **only warns** if `~/.local/bin` is off PATH (`:457-469`) — it never writes the
  profile. **Friction #2 (PATH drift) is unfixed here.**
- TMPDIR: `TMPDIR_CE="$(mktemp -d)"` (`:472`) with **no free-space check**.
  Cleanup trap at `:37-38`. **Friction #3 (tmpfs exhaustion) unfixed.**
- Install-lock: `acquire_lock` via `mkdir "$BOOTSTRAP_ROOT/install.lock"` with
  stale-PID detection (`:402-415`); messages `install_lock_held` /
  `stale_install_lock`. **Friction #5: functional but terse UX** ("remove it after
  confirming no installer is running").
- Provenance anchor: `write_state` records `sha256s_sha256`, `package_version`,
  `venv_path` to `$BOOTSTRAP_ROOT/install-state` (`:417-433`). Default root
  `$HOME/.local/share/creator-engine/bootstrap` (`:582-590`). **This is the data a
  `ce verify-install` needs — friction #4; the command itself does not exist.**
- Final step: runs `cev3 onboard --inventory` (`:716-740`) then prints a "next:"
  hint to hand-run `cev3 onboard … --plan`. **It stops here — it does NOT run
  `ce brain init` or any first governed launch. That gap is exactly what `ce
  onboard` closes** (and is the #206 / N1-W5 seam).

### 2.2 `v3_installer.py` (`validators/creator_engine_validator/v3_installer.py`, 3585 ln)

- Parses the bootstrap manifest, validates `sha256s_sha256` + per-wheel digests
  (`:820-928`); raises `InstallRefused` on mismatch. The Python side of the trust /
  hash contract install.sh shells out around. `ce verify-install` should reuse this
  module's digest parsing rather than re-implement hashing (avoids the
  verifier-hash-transcription footgun, MEMORY `ce-verifier-hash-false-positive`).

### 2.3 `cev3 onboard` (`v3_cli.py`)

- Full signed-spec adoption applier (see §0). `ce onboard` composes/points at this
  for the *adoption* leg but is a separate, kernel-level orchestrator.

### 2.4 `ce` kernel CLI (`ce_cli.py`, 3010 ln)

- argparse, top-level `groups` subparsers. As-built groups: `lane, ledger, worker,
  fanin, queue, event, pcl, brain, connector, reviewer-triage, claim, pickup,
  check, doctor, init, launch, hud` (registered `:126-994`; dispatch map `:2820+`).
  `--version` → `version.add_version_flag` (`:123`).
- `ce brain init` at `:1972` (`_brain_init`), idempotent + fail-closed on corrupt
  ledger (#206) — the bootstrap leg `ce onboard` will call.
- `ce doctor` (`:778`) + `ce init` (`:800`) already exist — reuse, don't rebuild.
- `version.py`: `ce --version` derives `<semver>+<short-sha>` =
  `0.2.0+<buildsha>` (the legit-but-ambiguous token, friction #4). No
  `ce verify-install` exists (grep-confirmed empty).
- `ce brain init` subcommand registered at `ce_cli.py:683-688` (under the `brain`
  group `:563`), handler `_brain_init` `:1972`, dispatched via `_BRAIN_DISPATCH`
  `:2877`. `brain_runtime.py` owns the ledger (`LEDGER_RELATIVE_PATH =
  brain/assertions.yaml`); `brain_bootstrap.py` is pure read-only.
- **`v3_installer.py` is a PURE library** ("no disk / subprocess / socket /
  clock / rng") — it owns trust-verify + manifest/digest parsing + venv-reconcile
  *planning* (`plan_verified_venv_reconcile:1188`) but performs **no I/O**. So
  `ce verify-install` reuses its digest parsing but must own its own state-file
  read + hashing (or shell to install.sh's recorded `install-state`).

### 2.5 Governed launcher PATH root cause (friction #2 / #212)

- `codex_launch_spec.build_governed_codex_command` (`codex_launch_spec.py:229-236`)
  emits a **bare `codex` token** inside `env -u <creds> codex …` — relies entirely
  on the launching shell's PATH; `codex` is at `~/.npm-global/bin/codex`, only on
  the interactive PATH → exit 127 when launched from a non-login shell.
- Same pattern in `launch_runtime.py:219`: `command = [harness, *extra_args]` —
  bare harness token for ALL harnesses (codex caller at `launch_runtime.py:426`).
- The **sentinel wrapper** (`seat_sentinel.py`, `build_wrapper_script:139`, runs
  the inner command at `:184`) that actually execs the harness in the tmux pane
  **injects NO PATH** — it writes only an optional `{export_block}` from `exports`
  (`:128-137`), never PATH. So `codex` resolves against whatever PATH the pane
  inherits. This is the precise #212 root cause; a PATH-seed could also be added
  to the `exports` mapping as a defense-in-depth.
- **Fix surface for #212 (paired with this work):** (a) `ce onboard` standardizes
  the profile PATH so any launch shell resolves the harness; AND (b) the launcher
  should `shutil.which` the harness against a known-good PATH and **refuse with a
  clear message before any side effect** if unresolved (a small companion fix; can
  be its own PR — see §4 PR-6). This doc designs the onboard-side standardization;
  the launcher refuse-before-spawn is co-filed under #212.

### Friction → fix matrix

| # | Friction | Fixed by phase / PR |
| --- | --- | --- |
| 1 | Hand-typed §0 trust-verify quoting-hostile | Phase 2 wraps `install.sh` one-liner; never re-types sed/awk/ssh-keygen |
| 2 | Launcher bare-`codex` PATH gap + `.bashrc` drift | Phase 4 PATH standardization (PR-3) + launcher refuse-before-spawn (PR-6) |
| 3 | `/tmp` tmpfs exhaustion mid-wheelhouse | Phase 1 low-TMPDIR detection + home-staging fallback (PR-2) |
| 4 | `+buildsha` ambiguity, no provenance self-check | Phase 3 `ce verify-install` (PR-1) |
| 5 | install-lock collision confusing UX | PR-2 clearer "install in progress" message + (optional) wait/--force |
| 6 | stale lifecycle / double-spawn on relaunch | Phase 6 single-controller verification (PR-5) + #212 lifecycle reconcile |

---

## 3. Design — command surface + composition

### 3.1 Command surface

New top-level kernel group `ce onboard` (argparse subparser under `groups` in
`ce_cli.py`), plus a sibling utility `ce verify-install`:

```
ce onboard [--repo-root PATH] [--json] [--emit-manifest]
           [--install-mode {agent,guided,hybrid,print,skip}]  # REVISED: auto-select per §A.5; default NEVER print
           [--answers FILE]                      # passed through to install
           [--no-launch]                         # do everything up to first launch
           [--no-fix-path]                       # opt out of the managed PATH block (Decision 4)
           [--yes]                               # non-interactive (refuse w/ missing list, never silently proceed)
           [--harness {claude,codex,...}]        # first-launch harness (default per config)

ce verify-install [--json] [--install-root PATH] [--offline]
```

- **Wiring (3 touchpoints in `ce_cli.py`):** (a) `groups.add_parser("onboard", …)`
  near `brain` (`:563`); (b) handler `_cmd_onboard(args)`; (c) an `if args.group ==
  "onboard":` branch in `main()` (`:2908`) — dispatch is an `if`-chain plus
  per-group sub-dispatch dicts (e.g. `_BRAIN_DISPATCH`), not a single tail map.
- `ce onboard` is the orchestrator; it does the minimum itself and **delegates each
  leg to an existing surface**: `ce doctor`, `install.sh` (or detected install),
  `ce verify-install`, profile-PATH writer, `ce init`, `ce brain init`,
  `ce launch`. Keep onboard thin — it is a *composition + UX* layer.
- `ce verify-install` is independently useful (provenance self-check; ties to #46,
  #190 `ce update`) and is the friction-#4 deliverable. Reads
  `$CE_BASE/bootstrap/install-state`, recomputes/compares `sha256s_sha256` against
  the venv-pinned dir and (online) the live `SHA256SUMS`. Reuses
  `v3_installer.py` digest parsing; **reproduces hashes, never transcribes**
  (MEMORY footgun).

### 3.2 Composition order (what onboard calls, in sequence)

```
ce onboard
  ├─ 1. ce doctor (+ low-TMPDIR probe, + PATH-gap probe)   → refuse early w/ remedy
  ├─ 2. detect install → if absent: print/exec install.sh one-liner (quoting-safe)
  ├─ 3. ce verify-install                                  → genuine-release gate
  ├─ 4. standardize profile PATH (~/.local/bin + npm bin)  → idempotent, re-source hint
  ├─ 5. ce init  &&  ce brain init                         → launch-capable workspace
  └─ 6. ce launch (exactly once) + verify single live controller
```

### 3.3 PATH standardization (friction #2/#212) — design detail

- Idempotent edit of the user's login profile (`~/.profile` and/or `~/.bashrc`,
  guarded by a CE-marked block `# >>> creator-engine PATH >>>`/`# <<<`) adding both
  `~/.local/bin` and the npm global prefix bin to PATH. Idempotency: detect the
  marker block; never duplicate; never clobber non-CE lines (mirror the
  refuse-on-non-symlink caution at `install.sh:443`).
- Because profile edits only help *future* login shells, the launcher-side fix
  (PR-6, #212) is the belt to the onboard suspenders: resolve harness via
  `shutil.which` against a composed known-good PATH and **refuse before spawn** if
  absent — no more silent exit-127 wrapper death.

### 3.4 Where provenance self-check fits

`ce verify-install` is phase 3 of onboard AND a standalone command. Onboard treats
a verify-install failure as a **hard gate** (refuse to proceed to launch on an
unverified install), with `--install-mode skip` allowing an explicit override for
dev workspaces. It also surfaces in `ce doctor` output for at-a-glance provenance.

---

## 4. Work breakdown — ordered, PR-sized units (~200-400 ln each)

Strict-TDD repo. Each PR carries: tests first; `.ce/pr-manifests/<slug>.md`
matching `base..HEAD`; `.ce/changelog/<slug>.md`; and for any NEW module a
`_versions.py` classification entry. Adding the `ce onboard` / `ce verify-install`
command groups **trips `validators/tests/unit/test_v1_docs_reconciliation.py`**
(it asserts the exact `ce` command-group set == README.md, `:52-65`), so the PR
that adds each group MUST update `README.md` (the v1 inventory list at lines 68-73)
AND name both `README.md` and `test_v1_docs_reconciliation.py` in the manifest
(MEMORY `ce-new-ce-group-docs-coupling`).

**Ordering rationale:** build the leaf utilities first (verify-install, install
robustness, PATH), so the orchestrator (PR-5) composes already-tested pieces; the
launcher refuse-fix (PR-6) is parallelizable but sequenced last as it touches the
shared launch path.

### PR-1 — `ce verify-install` provenance self-check (friction #4)
- NEW `ce_provenance.py` (or fold into existing) + `ce verify-install` subparser in
  `ce_cli.py`; reuse `v3_installer.py` digest parsing.
- Reads `install-state` `sha256s_sha256` + `package_version`; recomputes vs the
  pinned venv dir; online compares to live `SHA256SUMS`; `--offline` = local only.
- **Tests:** genuine-match PASS; tampered/mismatch REFUSE; offline degradation;
  missing-state refusal. **`_versions.py`:** classify (likely `shared` — it reads
  install-state + reuses v3 installer parsing but is invoked by the v1 `ce` kernel;
  decide at PR time, AST-guard no cross-plane import). **Docs-reconciliation:** new
  group → update README + name the test. ~250-350 ln.

### PR-2 — install.sh robustness: low-TMPDIR fallback + clearer lock UX (frictions #3, #5)
- `docs/install.sh`: before `mktemp -d`, probe free space on `$TMPDIR`; if below a
  threshold (e.g. wheelhouse size + margin), fall back to a home staging dir
  (`$CE_BASE/tmp`) with a clear note. Improve `install_lock_held` /
  `stale_install_lock` messages (name the holder pid + a copy-paste remediation;
  optional `CE_INSTALL_WAIT`/`--force`).
- **Tests:** install.sh is shell — add a focused shell/bats-style or
  python-subprocess test (repo pattern: `test_v3_installer.py` already exercises
  installer paths) asserting low-space triggers fallback + lock message format.
  No new Python module → no `_versions.py` change; install.sh is docs-tree (confirm
  manifest path coverage). ~150-250 ln.

### PR-3 — profile PATH standardization writer (frictions #2, #212-onboard-side)
- NEW small module `ce_profile_path.py`: idempotent CE-marked block adding
  `~/.local/bin` + npm global bin; safe re-run; never clobber.
- **Tests:** fresh profile adds block once; re-run no-op; existing non-CE PATH
  lines preserved; marker-block detection. **`_versions.py`:** classify (`shared`
  or `v1`). ~200-300 ln. (Not yet wired into a command — pure unit + a `ce onboard`
  caller in PR-5.)

### PR-4 — `ce brain init` / `ce init` wiring confirmation + onboard helpers
- Thin: confirm `ce init` + `ce brain init` are callable as library functions (not
  only argv) for orchestration; add any missing programmatic entry + the
  doctor low-TMPDIR / PATH-gap probes used by onboard phase 1.
- **Tests:** programmatic init/brain-init idempotency; doctor probes. ~150-250 ln.
  (May merge into PR-5 if small.)

### PR-5 — `ce onboard` orchestrator (the one-shot; composes PR-1..4)
- NEW `ce_onboard.py` + `ce onboard` subparser; sequences the 6 phases; `--json`,
  `--install-mode`, `--no-launch`, `--yes`, `--harness`; idempotent + resumable;
  graceful-degradation branches (offline / no-tmux / already-onboarded).
- First-launch step drives exactly ONE `ce launch` and verifies single live
  controller via `seat_lifecycle` (friction #6).
- **Tests:** full happy-path (mocked legs); each degradation branch; idempotent
  re-run; refuse-on-unverified-install; single-controller assertion. **`_versions.py`:**
  classify `ce_onboard` (it drives the v1 `ce` kernel + reads install-state →
  decide `v1` vs `shared`; AST-guard imports). **Docs-reconciliation:** new
  `ce onboard` group → README + test named in manifest. ~350-400 ln (may split
  orchestrator vs CLI-surface into two PRs if it exceeds budget).

### PR-6 — launcher: resolve harness binary + refuse-before-spawn (friction #2 root, #212)
- `codex_launch_spec.build_governed_codex_command` (`:229`) and
  `launch_runtime.py:219`: resolve harness via `shutil.which` against a composed
  known-good PATH (or accept a configured absolute path) and **refuse with a clear
  message before any side effect** if unresolved. Add lifecycle reconcile so a
  dead-on-spawn (exit-127) seat doesn't stay `state: alive` (#212 finding 2), and
  investigate the double-`launched`-event (finding 3).
- **Tests:** unresolved harness → refusal (no spawn, no stale alive record);
  resolved → unchanged command; lifecycle reconcile on exec-failure. Touches shared
  launch path → careful classification; no new group (no docs-reconciliation hit).
  ~250-350 ln. Can land in parallel with PR-1..5; sequence last to avoid churn.

---

## 5. Risks / escalations

> **SUPERSEDED 2026-06-23 by §B/§D.** The hard escalation line below ("no
> autonomous install-EXECUTION") was the controller-overnight HOLD; the Operator
> has since ruled agent-driven install IN-SCOPE under the governed-install rail
> (§B). The re-stated line is **"no UNGOVERNED / UNCONSENTED install"** — the
> user's invocation is consent; the rail's confirm-on-consequence gates the
> consequential sub-steps. Read §B/§D as authoritative; the text below is retained
> for the friction/footgun risks, which remain valid.

### (HISTORICAL) ESCALATION LINE — now folded into the §B rail
- Building `ce onboard` / `ce verify-install` is in scope. The original framing
  fenced agent-driven *autonomous execution* OFF; that is now governed-in-scope per
  §A/§B (binds to `ce-autonomous-authority-doctrine`: authority GRANTED ≠ EXERCISED
  — withheld for the consequential minority, granted for the reversible majority).
  Still flag to the Operator any PR that grants autonomy for a step the §B.2 table
  classifies CONFIRM/RATIFIED.

### Decisions needing the Operator
1. **`--install-mode` default** — REVISED: enum `{agent, guided, hybrid, print,
   skip}`, auto-selected per §A.5; default is NEVER `print` (see §D.1). The old
   recommendation of `print` is superseded.
2. **Profile edit scope** — editing `~/.bashrc`/`~/.profile` is a host-config side
   effect. Recommend an idempotent, CE-marked, reversible block + explicit note;
   confirm acceptable as a default-on behavior (vs opt-in `--fix-path`).
3. **`_versions.py` classification of new modules** (`ce_onboard`, `ce_provenance`,
   `ce_profile_path`) — `v1` vs `shared`. They are driven by the v1 `ce` kernel but
   read install-state and reuse v3-installer parsing; decide per-PR with the
   AST-cross-plane guard, may need a `BASELINE_SHARED_TO_VERSION_ALLOWLIST` edge.

### Other risks
- **install.sh is shell, not Python** → harder TDD; lean on the existing
  `test_v3_installer.py` subprocess pattern; keep shell changes minimal + testable.
- **Verifier hash transcription footgun** (MEMORY) — `ce verify-install` must
  reproduce digests programmatically, never echo a transcribed hash.
- **Docs-reconciliation coupling is a guaranteed CI trip** for each new `ce` group
  — easy to forget README + the test in the manifest → CI block (MEMORY).
- **#212 lifecycle/double-spawn** finding 3 (two `launched` events) may be
  non-deterministic; PR-6 should at minimum make single-controller the asserted
  post-condition of onboard's first launch even if the root double-spawn needs a
  follow-up.

---

## Appendix — key cited files

- `docs/install.sh` — one-liner: lock `:402-415`, shims/PATH `:457-469`, TMPDIR
  `:472`, trust-verify `:485-524`, state/provenance `:417-433` + `:582-590`,
  wheelhouse hash `:615-635`, final `cev3 onboard --inventory` `:716-740`.
- `validators/creator_engine_validator/ce_cli.py` — groups `:126-994`, `ce doctor`
  `:778`, `ce init` `:800`, `ce launch` `:990`, `ce brain init` `:1972`, dispatch
  `:2820+`, `main` `:2908`.
- `validators/creator_engine_validator/v3_cli.py` — existing `cev3 onboard`:
  `_cmd_onboard` `:2764`, parser `:3968`.
- `validators/creator_engine_validator/v3_installer.py` — manifest/digest parsing
  `:820-928` (`sha256s_sha256` validation).
- `validators/creator_engine_validator/codex_launch_spec.py:229-236` — bare-`codex`
  token (friction #2 root).
- `validators/creator_engine_validator/launch_runtime.py:219` — bare-harness token.
- `validators/creator_engine_validator/version.py` — `<semver>+<short-sha>` token.
- `validators/creator_engine_validator/_versions.py` — `V1_RUNTIME`/`V3_RUNTIME`/
  `classify()` `:249`, allowlist `:195`.
- `validators/tests/unit/test_v1_docs_reconciliation.py:52-65` — exact `ce`
  command-group inventory guard (README coupling).
- `README.md:68-73` — as-built v1 `ce` command-group list to update.
- No `ce verify-install` exists today (grep-confirmed).
