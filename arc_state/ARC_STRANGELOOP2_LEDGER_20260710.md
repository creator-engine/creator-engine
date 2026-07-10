## Incident: 7-PR uniform CI red / silent queue stall (2026-07-10 ~08:20–11:0x)
- Presentation: every approved PR skipped by the gate with identical reason
  governance_check_not_success across 100+ passes; zero alarms (negative-space blindness —
  the N-15 pair's motivating case). Detected by a human question ("what remains before the
  queue drains?"), not by machinery. Third silent-stall in ~30h.
- Diagnosis path: bisect worker produced a FALSE diagnosis (import-hang; #935 first-bad) —
  its evidence was poisoned by a concurrent host condition (harness stdout blackout during
  /tmp tmpfs pressure waves; root: pr_preflight._python_env drops TMPDIR/PYTEST_ADDOPTS so
  inner suites default-basetemp onto the 8G tmpfs — fourth storage mechanism of the day;
  interim-fixed host-side, product fix = F-1 s2 scope). Face falsified by direct probe:
  checks import = 0.12s on main; all CI example-steps pass on main locally.
- Competing causal theories at ledger time: (a) CI-side flaky tests (sentinel/JIT races —
  deflake #950 sits IN the stuck batch); (b) perishable-green: old-rebase-base heads
  deterministically red vs post-08:09-base heads green. Discriminating experiment RUNNING:
  reruns of the four red heads unchanged. Green→(a); identical-red→(b)→rebase+push remedy.
- Ratified out of this incident: N-15a skip-anomaly alarm (K=3 + PR-age SLO), N-15b
  post-merge main-health run — refined by (a): the detector must retry-once-then-classify
  flake vs breaker before auto-filing.
- Numbering hygiene note: two appenders both minted "N-15" (broker deploy addendum vs
  silent-stall pair) — multi-controller APPEND rule held, but item numbering needs a single
  allocator; broker-deploy item is COMPLETE regardless (canary PASS ledgered).
- RESOLUTION (11:3x): TRUE root cause = the controller's own pipeline automation. The push
  subcommand read changelog/carrier from the MAIN repo root instead of the branch worktree
  (branch files only exist in worktrees pre-merge) → every auto-assembled PR body was a
  placeholder with ZERO work-class lines → the G5 exactly-one gate failed on ALL EIGHT
  pipeline-opened PRs uniformly. Reruns stayed red because a rerun replays the STALE event
  payload (the body at event time) — deterministic, content-uncorrelated, exactly matching
  observations. The "greens" in the first timeline were an unfiltered run-list artifact
  (different workflow). BOTH earlier theories (CI flake; perishable-green/main-poisoning)
  were wrong. Remedy executed: 8 bodies rebuilt from worktree artifacts (exactly-one
  verified), close/reopen for fresh events preserving head-bound approvals; script patched.
  Lessons: (i) N-4 brief-composition-preflight applies to CONTROLLER AUTOMATION OUTPUT too —
  the pipeline must self-validate its bodies against the G5 contract before opening a PR;
  (ii) rerun-red ≠ deterministic-code-red when gates read event payloads (N-15b detector must
  re-EVENT, not re-RUN); (iii) worker-produced scripts need a contract test before first use.
- N-15b SCOPING CORRECTION (Operator pipeline-walkthrough): main-tip run already exists
  (validate.yml push:main, green throughout) — the unit is the COMPOSITION probe alone:
  representative open-PR head merged into new main tip in a throwaway worktree, suite run
  FROM THE MERGED TREE. Controller refinements retained: retry-once-then-classify before
  auto-filing (flake immunity), and detectors must re-EVENT rather than re-RUN wherever a
  gate reads event payloads (today's stale-payload rerun lesson). Task #17 updated to match.
## Incident: post-drain uniform preflight red trio (2026-07-10 ~12:4x–13:1x, new face session)
- Presentation: three consecutive pipeline validates (terra-flip, ce-529, ce239) red with an
  IDENTICAL trio: sentinel trapped-signal test + signed-artifact hash-pin gate + path-manifest
  gate. N-15a fingerprint (uniform identical reds), detected by controller resume-probe, not
  machinery (N-15a still unlanded — in queue).
- THREE distinct causes, none branch-side:
  (1) terra-flip branch was EMPTY — harvest predated dev-3's corrected commit 18534417 and the
      requeue reused the stale worktree (rule-7 premature-signal class, 3rd occurrence; dev-3
      terra canary datapoint). Remedy: re-harvest with expected-sha verify — landed clean.
  (2) signed_artifact_pins gate (#935) fails CLOSED parsing docs/llms-install.md: the file opens
      with an HTML-comment prose header, not YAML frontmatter; gate reds EVERY branch validate
      once the branch (post-auto-rebase) carries #935's registration. Signed artifact → gate-side
      fix only. NOTE: PR-CI "Validate governance artifacts" stayed GREEN on trees carrying both
      the gate and the file (#955) — env-dependent divergence under investigation by fix worker.
  (3) path_manifest_fidelity gate counts examples/malformed/** negative fixtures as real
      offenses in repo scan mode.
  Plus: sentinel test_wrapper_trapped_signal_writes_exit[1-129] fails on unmodified main
  baselines intermittently — flake ON MAIN beyond #950's fix; deflake unit ce-523c drafted.
- Queue discipline lesson: runner POPS entries and does not requeue on red — burning held work
  into red logs. Queue PARKED (pipeline-queue.hold) until hotfix ce-453a-hashpin-hotfix lands;
  restore + requeue burned entries (ce-523b) after merge.
- Incident echo (14:5x): #956 (the gate hotfix itself) red on G5 with the MORNING's body bug —
  root cause: the 12:16 script patch never reached the RUNNING runner. A long-lived
  `bash script.sh runner` process parses the whole script at start; patching the file on disk
  leaves the live daemon executing pre-patch code. The runner that pushed #956 started ~09:00.
  LESSON (rule-9 class): patching a script under a live long-running process REQUIRES restarting
  the process — the singleton+IaC redeploy rule applies to controller-side automation too.
  Remedy: runner restarted (fresh code verified), body rebuilt from worktree artifacts
  (exactly-one verified), re-EVENT close/reopen (approval preserved), auto-merge re-armed.
  Detection gap noted: the PR-state monitor watches OPEN/MERGED only — a CI red on an open PR
  is silent; N-15a's skip-anomaly alarm (in the held wave) is the mechanical fix.
- ADR-0015 ratification (Operator, 12:2xZ): controller's ratification edit named the controller
  SEAT as decision_maker → two CI-caught defects: VAL-PA-SELF-APPROVAL (seat + Operator resolve
  to ONE human under peer-authority identity_map; ratifier must be independent) and a public-doc
  confidentiality leak (seat-login marker in docs/decisions/**). Fixed to the sibling ROLE-identity
  pattern (ce-runtime-architect / ce-gate-architect family). Lesson: decision records name ROLES,
  never seats; the peer-authority gate is the mechanical guard against laundered self-approval and
  it worked on its first live exercise. Pre-arming slice (d) complete at merge.
