# BRIEF — dev-4 — 2026-07-08 — P0: public README overhaul (Operator mandate, due END OF DAY-ARC)

Role: **implementer**. Contained COMMIT-ONLY seat. Fresh worktree at `/var/tmp/ce-readme-overhaul`
off `origin/main` (fetch first). Branch `ce-readme-overhaul`. No venv activation.
On green preflight signal: `READY ce-readme-overhaul <commit-sha> .ce/pr-manifests/ce-readme-overhaul.md`
If blocked: `BLOCKED ce-readme-overhaul <one-line reason>`

## U1 — branch `ce-readme-overhaul` (work class: story)

OPERATOR MANDATE (P0, verbatim intent): the public repo README is stale ("Current Status: As of
June 25, 2026") and must reach spec-kit / BMAD-METHOD quality "and even better" by end of day-arc.
This is a PUBLIC-FACING AUTHORSHIP task: you are writing the front door of the product.

### The bar (embedded — do not fetch the web; these are the reference patterns)
github/spec-kit README: crisp hero (logo + one-line tagline), badges row, TOC, a conceptual
"What is Spec-Driven Development?" section, get-running-in-minutes quickstart (single command),
process phase table, prerequisites, learn-more fan-out, support/maintainers/license footer.
BMAD-METHOD README: bold positioning statement, badges + community links, "What is BMAD" with a
clear two-phase mental model, one-liner quick start, module/ecosystem table, docs fan-out.
Common DNA to replicate: (1) a reader understands WHAT this is and WHY it matters in <30 seconds;
(2) one copy-paste path to first value; (3) conceptual model with a diagram; (4) structured
navigation to deeper docs; (5) NOTHING hand-dated that can rot.

### Required README architecture (adapt headings freely; keep this order-of-information)
1. Hero: project name + one-sentence value proposition (honest, product lens; CE = turn an idea
   into governed, working software through a guided journey with autonomous AI development that
   is EVIDENCE-GATED — quality enforced by the harness, not by trusting the model). Badges:
   latest release, CI status, license (use real badge URLs for this repo; shields.io style).
2. "What is Creator Engine" — 4-6 sentences, plain language. The two audiences framing: you
   describe the guided journey (user states Goal / Done-when / Change-type; CE runs the loop;
   evidence-gated merge). NO internal vocabulary (no "bet"/"appetite"; Budget only as opt-in aside).
3. How CE builds software — the stage canon Frame → Shape → Build → Review → Ship as a Mermaid
   diagram (GitHub renders mermaid in READMEs) + one paragraph. Link docs/guide/how-ce-builds-software.md.
4. Quickstart — install then first session. GROUND IN MAIN: read the real install path from the
   repo (git show origin/main:install.sh header comments + any docs/guide install/onboarding doc —
   locate via `git ls-tree -r origin/main --name-only | grep -iE 'install|quickstart|onboard'`) and
   the real first-session verbs from docs/guide/quickstart.md. CEO-mode/default journey FIRST;
   developer-mode notes second (one subsection, not interleaved). Never invent a command: every
   command line must exist in main docs or the CLI's own help surface.
5. Modes — short table: default guided/CEO experience vs developer mode; link deeper docs.
6. Project status — NO hand-dated "As of" prose. Structural: state current version by pointing at
   the release badge + CHANGELOG.md + GitHub Releases. One sentence on maturity (public pilot phase)
   that stays true without weekly edits.
7. Documentation fan-out table (docs/guide/*, CONTRIBUTING.md, GOVERNANCE.md, SECURITY.md, CODE_OF_CONDUCT.md).
8. License footer.

### Anti-rot gate (the reason this brief exists — the bug behind the stale README)
Extend the EXISTING "version-drift current surface gate" in the validators so README.md is a
covered surface: if README contains a semver-looking CE version string that does not match the
current release version source-of-truth the gate already uses, preflight/CI FAILS. Find the gate:
`grep -rn "version-drift" validators/creator_engine_validator/` and follow its surface list; add
README.md minimally and additively (do NOT weaken or restructure the gate). Add/extend a unit test
proving: matching version passes, stale version fails, version-free README passes. If the gate's
design makes README coverage genuinely infeasible additively, signal BLOCKED with the specific
reason rather than improvising.

### Hard constraints
- PRODUCT LENS ABSOLUTE (public repo): zero ce-ops#/issue refs, zero seat/host/topology/internal
  program names, zero mentions of specific tenants or people. Spec-kit and .hermes are RETIRED
  systems — they must not appear (they don't in the current README's visible sections, but verify).
- Vocabulary rules: no "bet"/"appetite"; Goal/Done-when/Change-type trio; Budget opt-in aside only.
- Do not delete CHANGELOG/GOVERNANCE/etc. or restructure other root docs; README.md is the canvas.
- Keep every claim honest to what main actually ships TODAY (0.3.x). Aspirations belong in a
  clearly-labeled short roadmap pointer, not the present tense.

Standing preflight directive (ce-ops#303): FULL `ce validate-pr --profile contained-seat` green
before commit-for-harvest. KNOWN SEAT-ENV FALSE-REDS (proven 2026-07-08, controller has evidence):
control-plane portability gate and check-examples/libsodium may fail in this seat's image on paths
OUTSIDE your diff — if the ONLY failures are those two gates on files you did not touch, note them
verbatim in the evidence and signal READY anyway; the controller re-runs the definitive CI-parity
preflight at harvest. Any failure touching YOUR changed files = fix or BLOCKED.

STOP LINE: no pushes, no PRs, no gate acts, no signing. Only these paths:
```
README.md
validators/creator_engine_validator/<the version-drift gate module you locate>
validators/tests/unit/<its test module (extend) or one new test module>
.ce/changelog/ce-readme-overhaul.md
.ce/pr-manifests/ce-readme-overhaul.md
```
Carrier: slug == branch exactly; every changed path enumerated; exactly ONE
`- **Declared work class:** S` line. Evidence must include: the 30-second-comprehension self-test
(paste your hero+what-is section), every command's source-of-truth path in main, and the gate
test matrix result.
