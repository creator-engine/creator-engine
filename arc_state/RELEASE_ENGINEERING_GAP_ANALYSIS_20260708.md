# Release-Engineering Gap Analysis — why CE can't yet ship a workable build to a user
**CE-DEV-2 controller fork · 2026-07-08 · commissioned by Operator after two failed Arad ships**

## Executive summary — verdict on the hypothesis

The hypothesis ("CE lacks a release-acceptance layer") is **confirmed, with a precision**: CE is
missing not one layer but **two distinct standard disciplines**, plus a third minor one:

1. **Release acceptance / launch readiness (the big one).** Every CE gate — and they are
   genuinely strong — fires at **merge time, on source**. Nothing in the pipeline ever exercises
   **the product as a user experiences it**: install the signed artifact in a clean environment,
   onboard a fresh repo, follow the documented first-hour journey. Industry solved this with
   release-candidate promotion pipelines, production readiness reviews, launch checklists, UAT,
   and release smoke tests on the shipped artifact. Both Arad failures pass through this hole and
   would have been caught by its most basic form.
2. **Definition-of-Done enforcement on closure (the process one).** Tickets close without
   acceptance evidence — worst case mechanically: the cross-repo autoclose bot closed the
   3-part #467 when a PR explicitly titled "slice 1" merged. "Closed" in our tracker does not
   mean "real". This is the same evidence-gated principle our merge gate already embodies,
   simply never applied to the tracker or the release boundary.
3. **Environment hermeticity (minor but real).** Seat-preflight false-REDs (portability,
   libsodium) are the classic non-hermetic-build symptom; Google-class release engineering makes
   build/verify environments identical by construction (SRE "hermetic builds").

The deepest formulation: **CE has a world-class *merge* gate and no *ship* gate.** Our own
release-to-traction doctrine already states the DoD ("live install + users") — it was ratified
as doctrine but never mechanized as a gate, which by our own bake-gaps-into-CE rule means it
does not exist.

---

## Part 1 — Case reconstruction (grounded)

### Case 1: broken tenant workflow shipped to Arad (ce-ops#494)
- **Defect:** `_render_ce_workflow_content()` in `onboard_apply.py` used `rb"\1<…>"` in a
  non-raw string context → `\1` compiled to `chr(1)`; every `ce onboard --apply` since
  2026-06-19 (PR #265) emitted a tenant workflow whose spec-verify step fail-closes with
  `content_sha256 mismatch`. Arad onboarded 2026-07-03; root-caused 2026-07-07; fixed #859/#899;
  her repo remediated 2026-07-08.
- **Why no gate caught it:** the signer (`release_publish.py`, correct raw string) and the
  verifier template (broken) are **different code paths**; unit tests validated each in
  isolation and never executed the **round trip on the emitted artifact** (render workflow →
  run its verify step against a signed spec). All merge gates passed because the source was
  "fine" — the *generated product* was broken.
- **Earliest standard catch-point:** an acceptance test that onboards a scratch repo and
  executes the emitted workflow's verify step (merge-time, cheap); failing that, a fresh-tenant
  rehearsal before any tenant send (release-time) — 18 days of broken onboards would have been
  zero.

### Case 2: default-mode docs instruct a nonexistent verb (ce-ops#508)
- **Defect:** `docs/guide/solo-ceo-onboarding.md` (the DEFAULT-mode journey) instructs
  `ce inbox`; the verb exists only in `v3_cli.py`, not the shipped `ce_cli.py`. Two prior
  parity sweeps (#449, #485) missed the CEO path; `test_v1_docs_reconciliation` guards
  CLI↔README inventory but **does not cover docs/guide/** (verified on main).
- **Why no gate caught it:** docs merged through gates that check *format* (YAML, vocabulary,
  confidentiality) but never *execute* what the docs tell a user to type. Docs are prose to our
  pipeline; industry docs-as-code practice treats documented commands as **executable test
  cases** that fail the build when they break.
- **Earliest standard catch-point:** docs-verb parity gate (static, merge-time) or executable
  docs testing; the journey rehearsal catches it at release-time by definition (a rehearsal
  follows the docs verbatim).

### Adjacent evidence — same disease, different organs
- **README rot through 4 releases (#467/#140):** #467's part 2 (version-drift gate) shipped in
  PR #867 and works (version strings current); parts 1 and 3 (release-triggered sync,
  significant-change refresh) never shipped because the **autoclose bot closed the whole issue
  on the "slice 1" PR title**. The stale "As of June 25" line is dated *prose*, outside the
  version-claim gate's pattern. → DoD-on-closure defect, mechanically induced.
- **.hermes half-retirement (#149→#507):** retirement executed piecemeal; closure carried no
  acceptance criterion ("fresh onboard = zero .hermes"). → DoD-on-closure defect.
- **Seat preflight false-REDs:** seat images diverge from CI env (libsodium absent; portability
  scan invocation differs). → hermeticity defect. Distinct layer, same discipline family.

**Claim test — "one missing layer"?** Rejected as stated. Cases 1+2 share the release-acceptance
hole; #467/#149 are closure-integrity; false-REDs are hermeticity. But all three reduce to one
principle CE already believes: **no claim without evidence** — applied today only at merge, not
at ship, close, or build-env.

---

## Part 2 — What industry standards actually prescribe (cited)

- **Release engineering as a discipline** ([Google SRE, Release Engineering](https://sre.google/sre-book/release-engineering/);
  [USENIX LISA15](https://www.usenix.org/sites/default/files/conference/protected-files/lisa15_slides_mcnutt.pdf)):
  four principles — self-service, high velocity, **hermetic builds** ("insensitive to the
  libraries and other software installed on the build machine"), **enforcement of policies and
  procedures**. Releases are a *product function* with owned tooling (Rapid), not a ceremony
  bolted onto merges.
- **Launch readiness as a gate** ([SRE Launch Checklist](https://sre.google/sre-book/launch-checklist/);
  [Reliable Product Launches](https://sre.google/sre-book/reliable-product-launches/);
  [PRR / engagement model](https://sre.google/sre-book/evolving-sre-engagement-model/)):
  Google requires a Launch Coordination Engineer to **sign off** launches against a checklist;
  Production Readiness Review is a *prerequisite* for a service carrying users. Go/no-go is an
  explicit decision with evidence ([go/no-go frameworks](https://instituteprojectmanagement.com/blog/go-no-go-production-readiness-checklist/)),
  including **UAT complete** as a standard line item.
- **RC → staged promotion → GA with real users in rings**
  ([Windows Insider channels](https://en.wikipedia.org/wiki/Windows_Insider);
  [Microsoft flighting](https://learn.microsoft.com/en-us/windows-insider/flighting)):
  builds graduate Canary→Dev→Beta→Release-Preview with **dogfood users at every ring** and
  controlled/staged rollout to bound blast radius. The universal pattern: *someone who is not
  the author uses the shipped artifact before a customer does.*
- **Docs are part of the product and are tested**
  ([GitLab documentation testing](https://docs.gitlab.com/development/documentation/testing/);
  [docs-as-code CI](https://pronovix.com/blog/cicd-and-docs-code-workflow);
  [executable examples](https://oneuptime.com/blog/post/2026-01-25-documentation-as-code/view)):
  mature orgs run docs through the same CI as code, including **extracting and executing
  documented commands** so a tutorial that lies fails the build. Case 2 is the textbook failure
  this practice exists to prevent.
- **DORA capabilities** ([DORA metrics](https://dora.dev/guides/dora-metrics/);
  [2024/25 findings](https://octopus.com/devops/metrics/dora-metrics/);
  [2025 report takeaways](https://www.faros.ai/blog/key-takeaways-from-the-dora-report-2025)):
  change-failure-rate and the 2024 **rework rate** metric measure exactly our failure class
  (unplanned fixes for user-visible issues — Arad remediation was rework). 2025 finding directly
  on point for us: **AI-accelerated throughput increases delivery instability unless
  foundational practices (CI, test automation, small batches, platform quality gates) are in
  place first.** CE has the throughput (10 merges/day); the report says exactly this profile
  must invest in stability capabilities or instability compounds.
- **Adversarial check on the hypothesis:** could the missing standard instead be "acceptance
  criteria in tickets" or "a QA function"? Partially — closure-integrity (#467/#149) is an
  acceptance-criteria problem, and we adopt that below. But acceptance criteria alone would NOT
  have caught case 1 or 2 (both units met their stated criteria; the criteria never included
  "works when a user installs and follows the docs"). The user-journey rehearsal is the
  irreplaceable piece. Hypothesis stands with the two-discipline split.

---

## Part 3 — Gap matrix and CE-native adoption

| Standard practice | CE today (evidence) | Would have caught C1/C2? | Severity | CE-native shape |
|---|---|---|---|---|
| Merge gates (CI, review, evidence) | ✅ strong (validators, containerized gate, 280+ passes) | — | — | keep |
| Hermetic build/verify envs | ⚠️ partial: CI parity on host; seat images drift (libsodium, portability) | no | M | image-parity gate: seat-ready profile must prove env == CI manifest (ledgered unit exists) |
| **Release smoke on shipped artifact (fresh install)** | ❌ none — install.sh signed but never executed post-release in clean env | **C1 yes** | **P0** | **fresh-tenant rehearsal gate (below)** |
| **UAT / journey acceptance (docs followed verbatim)** | ❌ none | **C1+C2 yes** | **P0** | rehearsal executes documented first-hour verbatim |
| Executable/parity-tested docs | ⚠️ `test_v1_docs_reconciliation` covers README↔CLI only, not docs/guide | **C2 yes** | H | extend reconciliation gate to docs/guide verb inventory (#508 stretch) |
| RC→GA promotion; version not "released" until acceptance passes | ❌ tag+sign = released | C1 yes (Arad would've gotten a passed RC) | H | releases born RC; `ce release promote` requires rehearsal evidence bundle |
| Go/no-go with named gatekeeper | ⚠️ implicit (Operator send decision, no checklist) | partial | M | tenant-send checklist rendered into awaiting-operator queue item — decision WITH evidence attached |
| Dogfood the INSTALLED artifact | ❌ we dogfood source checkouts, never the shipped release | C1 yes | H | ring 0 = one CE seat runs on the installed release, not repo checkout |
| Staged rings / canary users | ⚠️ implicit (Arad IS the canary — with no ring before her) | — | M | ring order: rehearsal bot → internal installed-CE seat → pilot tenant → public |
| DoD/acceptance evidence at closure | ❌ autoclose on title-ref; slice-1 closed 3-part #467 | (#467 class) | H | closure gate: directive-class issues need acceptance-evidence link; bot must NOT autoclose multi-part issues on "slice N" PRs |
| Rework-rate tracking (DORA) | ❌ unmeasured | — | L | count remediation units per release in the release evidence bundle |

### THIS ARC — the minimal release-acceptance stage (stress-tested seed, adopted)

**Fresh-Tenant Rehearsal gate** — a codified, automatable pipeline stage; a release or tenant-send
is NOT eligible until it passes:

1. Clean container (pinned image = hermetic env), **no repo checkout** — install exactly as the
   docs instruct (`install.sh` from the signed release).
2. Onboard a scratch repo (`ce onboard --apply`) and **execute the emitted workflow's verify
   steps** (kills case 1 forever).
3. Execute the documented first-hour journey **verbatim from the welcome pack / quickstart**,
   CEO-mode path first (kills case 2: a doc that lies fails the rehearsal). Static docs-verb
   parity gate as the cheap merge-time companion.
4. Emit an evidence bundle (transcript, exit codes, artifact hashes) → attached to the release
   record; the Arad-send checklist in the awaiting-operator queue links it. Go/no-go = Operator
   reads evidence, not vibes.
5. Failures file conveyor units automatically (belt-feed class), not ad-hoc fixes.

Fits existing primitives: it is a **verification daemon + seat-shaped runner** (same containerized
template as the gate), the evidence bundle rides the existing carrier/evidence conventions, and
the human decision stays exactly where doctrine puts it — the gate/queue. Estimated size: the
rehearsal harness is one story-class unit (steps 1-2 automatable today); the journey executor
(step 3) is a second unit; RC-status plumbing a third.

### FOLLOWING ARCS
- RC→promote release states; ring 0 installed-CE dogfood seat; closure-integrity gate on the
  autoclose bot + acceptance-evidence convention; image-parity gate for seats; rework-rate in
  release evidence; docs/guide executable-examples extraction.

**One-line root cause for the Operator:** we applied "no claim without evidence" to merges and
stopped there; industry applies it to the artifact, the journey, the ticket, and the release —
and now we will too.
