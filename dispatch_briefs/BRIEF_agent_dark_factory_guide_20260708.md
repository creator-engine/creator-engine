# HANDOFF — definitive CE dark-factory guide (Operator-facing artifact, NOT a PR)

## Deliverables (write BOTH, complete and self-contained)
1. `/home/cedev2/creator-engine/.ce/state/research/ce-dark-factory-guide/CE_DARK_FACTORY_GUIDE.md`
2. `/home/cedev2/creator-engine/.ce/state/research/ce-dark-factory-guide/index.html` — a single-file,
   fully OFFLINE interactive one-pager (no CDN, no external fonts/scripts/images; inline CSS+JS+SVG
   only; must render from file:// in a browser; light+dark theme via prefers-color-scheme; sticky
   section nav; collapsible sections; diagrams as inline SVG).

Audience: the Operator of CE's OWN internal deployment ("autonomous fleet"). This is an INTERNAL
document — internal names (dev-1..4, DGX/VPS, daemon names) are allowed and wanted. It describes
the TARGET state (post-roadmap dark factory), with clearly-marked "TODAY (2026-07-08)" deltas per
section so the Operator can see current vs endgame.

## The Operator's frame of reference (embed faithfully; treat as the spine; extend, don't limit)
Verbatim vision: (a) the Operator "frames" ideas together with the operator-facing controller in
natural language. Open question to ANSWER in the guide: framing today happens without explicit
`ce` verb invocation (the controller isn't yet a ce-governed controller), and end-users on their
governed controllers should also be able to frame naturally — the guide must explain how CE
guarantees governed framing WITHOUT requiring an explicit `/ce frame` invocation (answer via the
harness-enforcement design: governance attaches at the HARNESS seam — hooks/PreToolUse checks,
launch-wired controllers via `ce launch`, `ce takeover` as entry verb — so intent-recognition can
be soft while enforcement stays hard; cite the relevant designs/decisions).
(b) The controller autonomously performs SHAPE: produces the arc (short-term plan), roadmap
updates (mid/long-term), and tickets — the artifacts the build phase consumes.
(c) CE machinery runs autonomous development dark-factory style:
  c1. Seats pick up work units (tickets/grouped tickets) per the arc, implement, and submit
      (commit + push + open PR) — pickup model, not push-dispatch.
  c2. "Local" automation (CE containerized daemons/agents) handles local git mechanics of the PR
      process.
  c3. Forge-level automation handles forge mechanics (merge queue etc.).
  c4. Automation handles reviewer assignment to seats — the guide MUST answer the Operator's
      question: is this local or forge level? (Answer with the hybrid model: forge events are the
      trigger + SSOT transport; the assignment DECISION + reviewer spawn is a local containerized
      daemon applying the authoring/review matrix — forge-as-hub, brains-local.)
  c5. Automation handles triage of seat-filed tickets (bug reports/features from seats, distinct
      from Operator-facing intake) — same local-vs-forge question, same hybrid answer via the
      polling belt-feed doctrine (Search-API polling = durable default; push = premium).

## Required source material (read before writing; main worktree at
## /home/cedev2/creator-engine/.ce/wt-dayarc2-main — treat as current main)
- .ce/state/decisions/DECISIONS_20260708.md + DECISIONS_20260707.md (controller state root
  /home/cedev2/creator-engine/.ce/state/decisions/) — ratified rulings incl. singleton+IaC rule,
  Option A rulings, C5 promotion, signing grant.
- Resume states .ce/state/research/RESUME_STATE_CE_DEV2_DAYARC2*.md — current posture + lanes.
- Designs on main (docs/design/): host-ops-broker-v1.md, ce-491-optiona-merge-intent.md,
  ce-491-ledger-append-serialization-slice1.md, seat-side-preflight.md,
  ephemeral-controller-provider-seam.md, recursion-bottom-out-policy.md,
  ce-forge-side-automation.md + ce-forge-side-automation-epic.md, ce-orchestrator-agent.md,
  ce-brain-memory-augmentation.md, sshsig-signing-deputy.md, controller-bootstrap-injection.md.
- docs/operations/: GOVERNED_LANE_LAUNCH_PROTOCOL.md, WORKER_CONTAINER_PROTOCOL.md,
  HARNESS_SUPPORT_CAPABILITY_MATRIX.md, SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md.
- playbooks/controller/ (duties.yaml, runbooks/, briefs/dispatch.md), playbooks/reviewer/.
- deploy/: queue-daemon/, singleton-redeploy/, dgx-runsc/, vps-runsc/, egress broker at
  tools/egress-broker/ + broker slice at tools/host-ops-broker/.
- docs/guide/how-ce-builds-software.md + quickstart.md (the public journey — contrast with the
  internal fleet deployment).
- CHANGELOG.md v0.3.4 section (what shipped through the gate lately).

## Facts to weave in (verified today, 2026-07-08 — the guide's "TODAY" anchors)
- Gate: containerized ce-queue-daemon IS the merge gate (C5 promoted; host daemon rollback-only);
  merge queue on main via ruleset ce-reference-protection-floor (required check + 1 review +
  merge queue, squash); classic protection retired.
- Identity: per-seat GitHub Apps (dev-1/3/4) + ce-materializer App 4244593 (contents:write,
  single-repo, ruleset always-bypass, provisioned+chain-verified today, arming gated); ce-root-v1
  signing = persistent controller authority (decision 9); registry SSOT ce-ops:infra/
  identity-registry.yaml.
- Seats: dev-1 (VPS, non-contained, self-push), dev-3 (VPS gVisor contained, egress-broker
  self-push, relaunched today on rebuilt image w/ ssh-keygen), dev-4 (DGX gVisor contained,
  App-mint self-push credential helper, strongest). seat-ready validate-pr profile merged (#896).
- Flow today vs target: today the controller hand-authors briefs (file+SHA pointer dispatch),
  harvests contained seats via bundle-over-exec-cat, spawns reviewer subagents, submits approvals
  (approval = merge trigger); target = pickup conveyor + review daemon + triage daemon + Option A
  materializer (slice 1 in build today) + broker-mediated host ops + contained/ephemeral
  controllers (NanoClaw direction; #496/#498 T1 Aug 11 / T2 Aug 31).
- Doctrine anchors: Frame→Shape→Build→Review→Ship stage canon; grader-outside-the-agent is the
  moat (harness-enforced checks, not model self-grading); no per-token API billing (subscription/
  self-hosted lanes); two-plane OS (portable control plane + one container runtime per host);
  singleton + one-click IaC redeploy rule; work sizing XS/S/M/L; carrier manifests + per-PR
  changelog fragments; AWAITING-OPERATOR queue discipline; brain ledger (append-only,
  content-addressed chain) with merge-time intent materialization (Option A).

## Required structure (md and html mirror each other)
1. Executive summary: what the dark factory IS (one screen), the endgame picture.
2. The five layers, each with a diagram: (i) Operator+Controller framing/shaping loop;
   (ii) intake conveyor: arc → tickets → pickup queue → seats; (iii) build: governed seats,
   containment, self-verify (seat-ready), self-push (broker/App identities); (iv) the gate:
   review daemon → approval → merge queue → containerized gate daemon → Option A materializer
   post-merge; (v) host/ops substrate: host-ops broker verbs, IaC singleton redeploy, OpenBao,
   herdr PTY, egress brokers.
3. MASTER DIAGRAM: one full-page SVG of the entire flow from natural-language idea to merged,
   materialized, released code — every actor (Operator, controller, seats, daemons, forge) as a
   swimlane; label which acts are human, which controller, which daemon, which forge-native.
4. Answers section addressing the Operator's three embedded questions explicitly (natural-language
   framing guarantee; c4 local-vs-forge; c5 local-vs-forge).
5. Autonomy ladder: TODAY → seat parity (~Jul 10-11) → daemon wave (~1 week) → conveyor pickup →
   materializer armed → contained controllers (Aug 11/31) → ephemeral controllers. For each rung:
   what the controller stops doing, what evidence gates the rung, rollback story.
6. Authority & safety model: what can never be autonomous (Operator holds: framing ratification,
   arming decisions, external comms, root-key custody... note controller now signs under standing
   grant), stop-lines, fail-closed patterns, kill switches, quarantine, audit trails.
7. Glossary of CE terms (arc, lane, carrier, work class, harvest, seat, foreman, gate, brain,
   intent, materializer, broker, containment ring...).
8. Reference appendix: file paths of every design/runbook cited.

## Hard constraints
- HTML: ONE file, offline, self-contained, no external requests at all; inline SVG diagrams
  (hand-authored, clean, readable in both themes); interactive = section nav + collapsibles +
  maybe a today/endgame toggle per layer diagram; NO mermaid/CDN libraries.
- Truthful TODAY vs TARGET separation — never present target state as current.
- This is internal: do NOT commit to the repo, do NOT open a PR, write ONLY the two deliverable
  files under .ce/state/research/ce-dark-factory-guide/.
- Cite concrete artifacts (file paths, PR numbers, decision numbers) throughout.
- Return in your final message: the two file paths + a 10-line summary of the answers you gave to
  the Operator's three questions.
