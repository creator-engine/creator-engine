# CE WELCOME PACK T5 — structure rationale + honesty ledger (2026-07-08)

Deliverable: `tmp/ce-welcome-pack-t5/` — 17 rendered sections, 188KB offline
`index.html`, 19 md sources, `build.py` + `template.html` (regenerable: edit md,
re-run `python3 build.py`). Supersedes T4 (`tmp/arad-pack-0.3.4/`).

## Structure chosen (and why)

Seven journey parts: **Orient → First Hour → Concepts → First Day → First Week
→ Reference → Your Pilot.** The pack is built as pack-original *wrapper* pages
(Welcome, How To Install CE, Your First Hour, READMEs) that orient and route,
plus **canon docs from origin/main included verbatim** as the substance. This
is deliberate: the canon Quickstart's own anti-drift rule says welcome packs
must link (not duplicate) the journey docs — verbatim inclusion with a visible
"CE canon reference" bar is linking-by-inclusion; the wrappers add zero
divergent journey text. Every wrapper section opens with "You are here" and
closes with "What you just achieved / Next step" (guided-journey doctrine: the
pack is the human-side harness for onboarding).

Operator's a–f, each resolved:
- (a) Welcome rewritten: one-line thesis, day-one feel, the two modes, how to
  use the pack, where-to-go-next table. All install content moved out.
- (b/d) "How To Install CE" is its own sidebar section, second in the journey,
  before anything that assumes an install; Quickstart no longer reachable
  without passing it in the nav order.
- (c) CEO-first everywhere: Welcome introduces CEO as default; Your First Hour
  presents the CEO path first with the Dev track as a routed subsection; First
  Day lists CEO Mode before Dev Mode; Quickstart is explicitly relabeled
  "Quickstart (Dev track)" with a track badge.
- (e) getting-started-step-by-step.md (spec-kit era) DROPPED entirely —
  superseded by solo-ceo/solo-dev + complete-walkthrough. The one spec-kit
  reference in the pilot constitution draft patched to governed-change
  vocabulary (Scope/Goal/Done-when/Change-type).
- (f) .hermes: see honesty ledger below.

## DEV-mode placement decision

**One journey spine, CEO default, Dev as a labeled track — not a forked pack.**
Mechanics: a persistent CEO/DEV toggle in the sidebar (CEO preselected =
encode-the-rec-as-default; persisted via localStorage); nav entries carry
CEO/Dev-track badges; the non-selected track's nav entries dim to 45% opacity
but never hide (a reference you can't find is worse than one you can ignore).
Canon mode docs (solo-ceo/solo-dev) stay separate sections, CEO first, because
they are canon and self-contained. Research basis: progressive-disclosure
pattern (show the default path, reveal advanced on request — GitLab Pajamas,
IxDF) and the low-code-platform lesson that fully forked persona docs blur
product focus; Stripe-style persona routing keeps one narrative with explicit
track markers. Sources consulted:
[IxDF progressive disclosure](https://ixdf.org/literature/topics/progressive-disclosure),
[GitLab Pajamas](https://design.gitlab.com/patterns/progressive-disclosure/),
[GitBook documentation personas](https://gitbook.com/docs/guides/docs-workflow-optimization/documentation-personas),
[UXPin](https://www.uxpin.com/studio/blog/what-is-progressive-disclosure/).

## Honesty ledger — claims I could NOT purge/ground, and why

1. **.hermes is NOT retired on main 0.3.4.** `ce_onboard.py` hard-refuses
   without a `.hermes/` gitignore (STATE_PATH_GUIDANCE); `ce_cli.py` ledger
   paths live under `.hermes/`. Purging the reference would break every real
   install. Compromise shipped: ONE functional mention in Install prerequisites
   (de-branded — no "Hermes" proper noun, no legacy narrative), plus the
   references inside verbatim canon docs (solo-dev, zero-to-governed, macOS).
   → NEEDS PRODUCT TICKET: finish .hermes→.ce/state rename; the pack inherits
   the cleanup automatically at the next regen.
2. **Canon upstream has the same structural flaws the Operator flagged.**
   docs/guide/welcome.md on main mixes install into welcome and carries the
   .hermes prep in its front section. The pack fixes presentation; upstream
   canon should be restructured to match (candidate PR, not done here — canon
   edits are a governed unit, not a pack task).
3. **CEO-mode "decision inbox" (`ce inbox --repo <owner/repo>`)** is asserted
   by canon solo-ceo-onboarding.md; I did not independently verify the verb
   exists in the CLI surface. Trusted canon; flag for the next docs-vs-CLI
   parity sweep.
4. Dropped `day-to-day-with-ce.md` (pack-only, not canon): its daily-rhythm and
   collaborator content is covered by solo-ceo-onboarding §"daily rhythm" and
   §"collaborator". Its "What you're not doing anymore" framing is nice copy —
   candidate to upstream into canon someday, noted here so it isn't lost.

## Purged-rot inventory

- getting-started-step-by-step.md: DROPPED (spec-kit walkthrough, deprecated
  header, budget-as-required framing, "being retired" language).
- day-to-day-with-ce.md: DROPPED (superseded; had Budget-in-trio line).
- Old welcome.md: REPLACED (install content inside welcome; .hermes prep as
  the pack's opening act; Hermes branding).
- mythos-constitution.draft.md: spec-kit amendment-procedure line rewritten to
  governed-change vocabulary; moved under pilot/ with a swappability README.
- T4's 13 vocab edits are inherited by construction (T5 uses canon sources,
  which are clean; the edited file was pack-only and is dropped).

## Check battery (all PASS)

HTML parses with balanced tags (html.parser walk); zero external resources
(no script/link/img src, no url(http), no CDN strings, no fetch/XHR); vocab
clean (bet/appetite: 0); product lens clean (ce-ops#/seat names/host topology:
0 in rendered HTML; "Arad" appears only in pilot addendum by design); version
0.3.4 (no 0.3.3); copy-clean code blocks (no `$ ` prompts); prefers-color-scheme
light+dark; sticky nav; per-block copy buttons; CEO/DEV toggle present,
CEO default. 25 tables, 56 code blocks, 17 sections.

## T5.1 delta (2026-07-08 evening — Operator findings a/b/c + verdict-C truth)

Operator findings on T5, all applied:
- (a) **First Hour split like First Day**: your-first-hour.md replaced by
  your-first-hour-ceo.md (ceo track) + your-first-hour-dev.md (dev track); the
  CEO/DEV toggle now governs both First Hour and First Day uniformly.
- (b) **CEO track: zero command blocks.** first-day-ceo.md is now PACK-AUTHORED
  (replaces verbatim canon solo-ceo-onboarding.md, which still instructs
  `ce ratify --approver-ref …`, `ce merge --apply`, and the unshipped `ce inbox`
  — upstream canon fix is ticketed territory, out of pack scope). CEO sections
  teach the intent-and-authorization dialogue: the user says "Yes — build this"
  / "Ship it"; the agent invokes the verbs; CE records. Commands appear only as
  inline-code "under the hood" asides (verdict C: agent-mediated ratify/merge
  work mechanically today, so this is the honest current flow). Grounds: the
  ce-users-never-type-commands doctrine — comprehension (non-technical users
  can't parse flags/jargon) and reliability (humans blunder raw commands more
  than governed agents, and recover worse).
- (c) **"How CEO mode differs" Ship row fixed**: CEO column no longer shows the
  merge command; CEO Ship = review-with-recommendation → natural-language
  approval, agent executes the gated merge.
- Install: agent-driven install path promoted to Path A (recommended);
  one-liner demoted to hands-on Path B; `ce onboard` gains the delegation note.
- Canon refresh: quickstart.md + zero-to-governed-seat-quickstart.md re-pulled
  from post-#906 origin/main (the two canon files #906 changed).
- .hermes verdict re-verified on current main: STILL required by `ce onboard`
  (ce_onboard.py:81,540 — the retirement unit is parked, unpushed). The single
  functional Install mention stays; canon functional mentions allowlisted.
- build.py gains a fail-closed check battery (build exits 1): CEO-track
  sections contain no fenced code blocks; no ce-ops# refs; spec-kit +
  "being retired" purge-list; .hermes outside the functional allowlist; and no
  `ce inbox` documentation anywhere. All checks PASS on this build.
