# DAY-ARC MANDATE — CE-DEV-2 — 2026-07-05 — ✅ RATIFIED (Operator, ~07:05Z, form: "Ratify as drafted" selected; Q1=Linux+Docker only, Q2=Arad only, Q3=ghcr publish → GRANT-C live)
> Operator directive (~06:55Z): "deliver our test users with a functional contained version of CE
> today, fully installable either via the one-liner or a playbook fed to their already installed
> coding agent." Supersedes the night mandate's park on tenant-facing work FOR THIS SCOPE once
> ratified. Night-arc residue (C5 soak/retry) continues as background lane D6.

## Theme: first tenant-shippable CONTAINED CE — two install paths, e2e-proven, DoD-gated
Per release-to-traction doctrine: quality-where-it-counts, DoD miss → slip, no MVP shortcuts.

## Definition of Done (all four, evidenced)
1. **Path A (one-liner)**: on a clean Linux host with Docker and NO prior CE, the signed one-liner
   installs CE; `ce launch` starts the user's coding agent CONTAINED in the canonical runtime
   image; a real task round-trips (file edit + gate pass). Evidence: transcript, image digest,
   gate logs.
2. **Path B (agent playbook)**: a fresh already-installed coding agent, fed ONLY
   docs/llms-install.md, completes the same install unaided to the same contained-launch DoD.
3. Docs a tenant touches are accurate (#414 egress allowlist, #417 brownfield/apply prereqs,
   welcome package) — merged, product-lens clean.
4. If any fix required a new signed release: 0.3.2 cut off CURRENT main, wheel-verified, signed,
   published, and BOTH canaries re-run green against the live artifacts.

## Known seams the canaries must close (pre-identified)
- S1: pilot profile resolves to os-native backend; "contained version" requires the container
  backend as the tenant default (two-plane ADR #437 direction). Product fix, seat-sized.
- S2: canonical runtime image exists LOCALLY only; tenants need either (a) ghcr publish via the
  existing publish-runtime-image.yml workflow (recommended; consumer path is designed for digest
  pins) or (b) build-locally-on-install. Operator decision Q3.
- S3: #415 brownfield.enabled false-positive (in flight, dev-3 unit 3).
- S4: llms-install.md vintage vs 0.3.1+ reality — verify, refresh, RE-SIGN (controller-only act).
- S5: #431 launch-gate diagnostic mode — only if a canary shows tenants need it to self-diagnose.

## Execution log (running)
- 07:00Z GRANT-C executed: ce-runtime published to ghcr multi-arch from main@da89bf2f, tags 0.3.1 +
  git-sha, manifest-list digest sha256:7618dbe8811d467c71ae2a8fec231e38fc837532a1dd09b7fe4e7f0dd575353c
  (THE pin for S1b/S1c and the C5 containerized daemon).
- ✅ RESOLVED ~09:58Z 2026-07-05: Operator performed the ghcr visibility click — ce-runtime now
  PUBLIC. Verified: anonymous token pull of :0.3.1 manifest returns 200, digest matches the pin
  sha256:7618dbe8811d467c71ae2a8fec231e38fc837532a1dd09b7fe4e7f0dd575353c. Same click still
  needed for ce-seat after its first publish (re-ask at 0.3.2 ceremony).
- S1 recon complete → 3-unit program dispatched: s1a docker backend (dev-3 unit 4) · s1b seat
  image (dev-1 parallel) · s1c fail-closed launch default (dev-4, gated on s1a merge). Design
  decisions taken under this mandate: fail-closed launch default w/ explicit opt-out; agents baked
  into seat image. 0.3.2 CONFIRMED required for tenants (recon evidence: signed-mirror install
  flow, wheel carries launch code).

- ~08:10Z BOTH D1 canaries complete. Path A (one-liner): install PASS (0.3.1+91d20efc, signed
  ceremony sound), onboard PASS w/ 2 undocumented recoveries, containment FAIL (bare tmux,
  containment-probe NOT CONTAINED — S1 confirmed as THE fix), stopped legitimately at Anthropic
  login. Path B (playbook): §0 ceremony + E1 bootstrap PASS; CRITICAL Gap-1 = public docs
  document ce install/onboard--spec/session which exist only on cev3 (parity recon running).
- New units from canary gaps: ce-npm-path-fix (dev-1 parallel tiny; npm>=9 PATH corruption) ·
  ce-onboarding-docs-accuracy (dev-1 after #417; fantasy-CLI page + first-command contradiction +
  preconditions) · ce-onboard-relaunch-ux (dev-4 after s1c; sentinel idempotency + exit-127
  surfacing + doctor harness check). Tickets being filed by 3 triage workers. S1 program =
  ce-ops#447.
- ✅ ~10:20Z 2026-07-05: Operator approved the chmod735-dor sandbox. chmod735-dor/ce-canary-sandbox
  created (private, id 1289875522) via mythos-overwatch fine-grained PAT; Operator set mythos-ce
  App to ALL-REPOS (API add was 403 org-owner-only) — App token verified reading the sandbox.
  NOTE: all-repos is broader than needed (App has administration:write; now also covers
  infra-docs/infra-code/mythos-ops) — offer narrowing back to selected {mythos, sandbox} after
  the canary. Brownfield Model-C canary (canary C) dispatched against LIVE 0.3.1: adoption via
  mythos-ce App creds → expected containment FAIL (pre-0.3.2, known S1) → gap list; full re-run
  at the 0.3.2 ceremony.

- ~08:20Z Gap-1 RESOLVED-BY-RECON: `ce install`/`ce session` already on main (ce-440-s1 forwarding
  shims); the canary hit the released 0.3.1 wheel which predates them. No CLI-parity unit needed —
  0.3.2 delivers it. Residue: 6 stale `ce onboard --spec` doc lines — 5 added to dev-1's
  ce-onboarding-docs-accuracy unit (plain-join.md, brownfield-adoption.md); llms-install.md:239 is
  the SIGNED live artifact → rides the 0.3.2 re-sign ceremony. Pool tinies: "did you mean ce
  install" guard on native onboard (ce_cli.py, serialize vs ce-434) · ce_cli docstring queue-poll
  nit. Tickets: ce-ops#447 (S1) · #448 (npm PATH). **0.3.2 scope is now crisp: S1a/b/c + npm fix +
  relaunch-UX + forwarding shims (already on main) + docs units + re-signed llms-install.md.**

- ⚠️ 0.3.2 RELEASE CHECKLIST ADDITIONS (from #806 review): (1) regenerate/hand-sync docs/install.sh's
  embedded fix_shell_profile_path heredoc (lines ~842-919) from the FIXED ce_profile_path
  build_path_block before signing — it is a hand-duplicated copy of the broken npm block that runs
  before onboarding's self-heal; (2) llms-install.md line 239 `ce onboard --spec`→`ce install --spec`;
  (3) single-source the profile block (post-release hardening ticket candidate);
  (4b) ~12:15Z from #819 review: the ceremony MUST sequence the seat image — publish ce-seat to
  ghcr, set surfaces/manifest.yaml commit_or_digest (currently UNSET → onboarding emits the
  all-zeros placeholder sha that passes the pin regex but can't be pulled), Operator visibility
  click — BEFORE the canary re-runs, else day-one tenant `ce launch` pulls a nonexistent image.
  (4) ~11:20Z: MERGE THE PARKED ce-415-followup-tinies branch AS PART OF THE CEREMONY —
  .ce/wt-ce415-followup-harvest, rebased HEAD 6a7dd5dc; its install-answers.schema.yaml edit
  invalidates llms-install.md's answers_schema_sha256 pin (harvest host-preflight RED, 4 real
  test_install_bootstrap failures) → the same ceremony re-sign must carry the NEW schema hash.
  Seat false-green cause: @requires_ssh_keygen tests silently skip in-container. Canary-C addendum:
  ~10:50Z apply confirmed PEM/broker-only (pre-minted token structurally rejected) — controller
  runs the PEM-bearing apply inline to finish stages 3-4; 2 new gaps folded into dev-1 batch 2,
  refusal-message product gap POOLED (collides with parked test_v3_cli.py until it merges).
  POOL add ~11:50Z: CE_ALLOW_STALE_WHEEL docs mention still homeless — #816's enumeration is
  gate-daemon-scoped (reviewer-confirmed out of scope) and it was excluded from dev-3's batch;
  needs a one-line tiny on a CLI/troubleshooting page later.

## Lanes
- **D1 Canary spine (controller-driven, verification/architect workers)**: build the two clean-env
  canaries FIRST — they generate the day's real worklist. A: fresh Linux env + docker, live
  one-liner. B: fresh codex/claude session fed llms-install.md. Re-run after every landed fix.
- **D2 Contained-launch productization (seats)**: S1 profile→container backend + image reference
  plumbing (consume published digest or local build), S3, S5-if-needed. Hardest work → dev-4.
- **D3 Playbook path (seat + controller)**: S4 refresh; artifact bytes from seat, signature ONLY
  by controller (ce-root-v1; explicit STOP line in every brief per #442 lesson).
- **D4 Docs/welcome (dev-1, already rolling)**: #414 + #417 + Arad welcome package + pilot-runbook
  "contained launch" section.
- **D5 Release mechanics (controller + release worker)**: if D1/D2 land code fixes → cut 0.3.2 off
  current main (merge-base ancestry + wheel unzip-grep verified), sign spec + sums (controller),
  publish downloads/0.3.2 + mirror, re-canary. Rides ONLY on this mandate's ratification.
- **D6 Conveyor background**: C5-prep smoke (dev-4 unit 4) · C5 cutover retry ONLY in a genuine
  quiet window (realistically tonight) · pool tail (#401, #403) · harvest/review/merge continuum.

## Authority (requested by this ratification)
- GRANT-A: tenant-facing docs/artifacts changes within the two install paths (docs/, llms-install,
  welcome package) including publishing built docs.
- GRANT-B: cut+sign+publish 0.3.2 if the DoD requires it (release procedure per
  ce-release-spec-signing-procedure; signing stays controller-inline, never a worker).
- GRANT-C: one-time ghcr publish of the canonical runtime image via the existing workflow
  (pending Q3 answer).
- RESERVED still: contacting/scheduling the test users themselves (Operator channel) · any
  history scrub · fleet-wide seat rollout · arming beyond ratified envelopes.

## Standing constraints (unchanged)
Bounded units · full validate-pr one-pass green · independent non-author review on every PR ·
signed-artifact STOP lines · pointer+SHA dispatch + territory + semantic-novelty checks ·
controller inlines nothing except signing · checkpoint + /clear at ctx>45% · no seat idle.

## Operator decisions pending (asked 2026-07-05 ~07:05Z)
Q1 target env scope (recommend: Linux-with-Docker only today; mac = next arc).
Q2 user scope (recommend: Arad today; Nitzan contributor-lens is a distinct flow — prep welcome
   only).
Q3 image delivery (recommend: ghcr publish via existing workflow).
Q4 ratification of this mandate as drafted.

- ~12:5xZ (post account-switch session; "~15:5x" was a local-time mislabel): #823 (ce-451 checker hardening) APPROVED on head 5f6d1006
  after refuting reviewer's stale-baseline blocker (6741f192 nested-worktree guard is release-branch-only,
  NOT on main — reviewer baseline was the rc2 checkout). CEREMONY ADDENDA: (a) removing the UNSET
  allowlist entry when pinning the seat-image digest now also requires updating the FULL allowlist
  metadata tuple (version/source/custody/update_policy/last_evaluated) — #823's ratchet enforces it;
  (b) if 6741f192's nested-worktree guard is ever ported to main, re-apply atop #823's rewritten
  _iter_dockerfiles. Also this session: #822 unblocked (dead-runner Validate run cancelled+rerun → green
  → daemon enqueued), #819 confirmed merged 12:31Z, dev-4 Unit 6 auto-fired correctly.

- ~14:4xZ: #826 (relaunch-UX, dev-4 Unit 6) APPROVED @ a171e0a1 after a THREE-round amendment
  cycle: R1 blockers = sentinel-parse holes bypassing the reuse gate (corrupt events.jsonl skipped
  the whole gate; mixed unparseable pids archived) + doctor/codex resolution desync; R2 verified
  those closed, caught residual except-OSError silent-pass on unreadable-existing sentinel; R3
  verified final. Conveyor merged today additionally: #824 (runner translation dedup), #825
  (brownfield refusal split, follow-up ticket ce-ops#455 filed), #827 (placeholder-digest guard —
  ce-ops#451 now FULLY closed by #823+#827, close at ceremony), #828 approved (dependency-unlock
  contract; closed-without-merge gap banked on ce-ops#454). Pool residue banked in approval
  bodies: translation.py direct helper coverage; EPERM/archive-collision tests; symlink TOCTOU
  (contrived). Egg-info wheel-bake byproduct bit dev-1 U2 AND the #826 fix worker same-day —
  ticket the validator self-clean at ceremony ticket-pass.

- ~16:4xZ CEREMONY STARTED (all 21 conveyor PRs #813-#833 merged; board clear). Recon-corrected
  decisions: (1) install.sh heredoc regen DROPPED — already byte-identical to ce_profile_path
  build_path_block on current tree (checklist item 3 premise dissolved); (2) ceremony branch cut
  FRESH off origin/main; rc2 branch ABANDONED after folding forward its two real fixes
  (nested-worktree skip re-applied atop #823/#827's rewritten _iter_dockerfiles + version-agnostic
  URL assertion) — resolves the ce-ops#416 drift; (3) TAG-TIMING (ce-ops#395 residue) DECISION:
  manual ceremony per 0.3.1 precedent; the auto-tag-fired CI release.yml duplicates (draft release
  + AWAITING-OPERATOR issue) get closed as no-ops post-merge; (4) seat-image publish rides the
  release/v0.3.2 tag automatically → digest pin + UNSET-allowlist-tuple removal = separate small
  PR AFTER the release PR merges, BEFORE canaries (day-one launch pulls it). Release worker
  building ce-release-0.3.2 (worktree .ce/wt-ce-release-0.3.2); controller signs INSTALL_SPEC_TO_SIGN
  inline on its STOP report. Conveyor residue in parallel: #834 amendment (dev-1), #411/#452
  harvest (worker), #431 (dev-4).
