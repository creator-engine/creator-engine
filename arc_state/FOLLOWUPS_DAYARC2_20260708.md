# Day-arc-2 follow-ups ledger (batch into one unit when 3+ accumulate)
- [ ] PR#895 MINOR: smoke-singleton-redeploy.sh "Would install" assertion is host-state-conditional
      (false-fails on already-deployed host) — accept the "Would leave unchanged" branch too.
- [ ] PR#895 NIT: sed_replacement_escape misses backslash; mktemp cleanup traps absent.
- [ ] Seat image parity: dev-3 image lacks ssh-keygen — broke seat-side full seat-ready profile
      on first contact (fleet-parity unit already queued; this is the concrete evidence).
- [ ] Codex standby controller session gone on DGX — canonical relaunch + ce-ops#502 fix.
- [ ] PR#896 MINOR: autogen repair commit path untested end-to-end (autogen_artifact_changed=True).
- [ ] PR#896 MINOR: _commit_staged_autogen commits whole index — add `-- <artifact>` restrictor.
- [ ] PR#896 NITs: assert -n4 substitution took; normalize surface-set paths.
- [x] CORRECTED: G5 gate accepts BOTH vocabularies via aliases; the real rule is EXACTLY ONE class line in the PR body (and the stale-rc2 comparison caused the earlier wrong claim). #895 failed on ZERO lines (body rewrite dropped it).
- [ ] Test-isolation race (-n auto): test_surface_determinism_ignores_stale_checkout_artifact_dirs
      creates validators/build/ in the REAL repo dir mid-run → breaks concurrent
      test_release_finalize_docs_copy copytree. Needs tmpdir isolation. (Found by 482 harvest.)
- [ ] deploy/dgx-runsc/build-image.sh hardcodes `render.py --arch arm64` (line 51) — breaks x86_64
      builds with exec-format-error; should take --arch or detect via dpkg. (Found rebuilding dev-3 image.)
- [ ] Dependabot: 2 moderate vulns flagged on default branch (surfaced at 0.3.4 push) — triage.
- [ ] surfaces/manifest.yaml image digests still at 0.3.3 — follow-up PR after 0.3.4 images build.
- [ ] dev-3 rebuilt image regression #4: seat HOME lost ~/.ssh + ~/.gitconfig (signing key/config gone;
      canary commit was sig=N). Masked today because broker-dev3 policy has require_signed_commits=false —
      restore seat signing (keygen + allowed_signers refresh + gitconfig) BEFORE tightening that policy.
- [ ] Launcher should REFUSE the npm-package mount path when image lacks node (silent mis-mount → exit 66);
      relaunch runbook must document the standalone-binary requirement (both from dev-3 saga 20260708).
- [ ] #902 PRE-ARMING preconditions (also on PR record): wire brain_intent_xor_gate.check_xor into
      validate-pr dispatch; add negative/escape-path test for _require_state_subtree; fix carrier per-file
      count; AUTHORIZED_WRITE_PATHS dead frozenset → assert-at-write-sites or remove.
- [ ] dev-4 workspace hygiene: /workspace/creator-engine parked on stale ce239-wall-openbao-supplier
      (Jun 26 leftover, PR #518 closed) with a large dirty index — reset to main, clean.
- [ ] dev-3 host repo parked on ce-portability-guard-hygiene with LOCAL commit ffd6e0a3
      "test: tighten portability guard command fixtures" — triage: dispatched? in-scope? harvest or drop;
      also collect the portability-guard verbatim-error evidence the canary correction asked for.
- [ ] SEAT-IMAGE PARITY: libsodium missing in dev-4 (dgx aarch64) image — breaks check-examples signed
      worktree-lease verification in-seat → false-RED preflight. Add to image build; audit dev-3 image too.
- [ ] PORTABILITY-GATE seat-side false-RED PATTERN: BOTH dev-3 (canary, x86_64) and dev-4 (slice 2, aarch64)
      hit control-plane portability gate red in-seat while main CI is green (dev-4 red points at
      container_launcher.py:86, outside its diff). Diagnose invocation/exemption-manifest divergence between
      in-seat `scan-portability-plane .` and CI's pr_preflight path; fix so seat-ready profile matches CI.
- [ ] #904 PRE-ARMING additions: integration test for XOR gate via run_preflight real sequence;
      bump ACTOR_VERSION to slice tag on next touch; add path.resolve() normalization in
      _require_state_subtree (sole write guard) BEFORE arming.
- [ ] DISPATCH PLAYBOOK: add mechanical GATE-PRECOMPUTE step to brief composition — before
      authorizing a path set, grep for (a) tests asserting contracts over those paths,
      (b) reconciliation/parity guards naming them as surfaces, (c) brain-pinned artifacts
      (assertions.yaml refs). Today's README P0 burned 3 correction round-trips on gates
      that were all greppable at composition time. Update playbooks/controller/briefs/dispatch.md.
- [ ] DISPATCH RULE (add to territory-map step + playbook): units requiring brain-ledger appends
      SERIALIZE (stale-tail + active-count ratchet force it by design). Never run two brain-touching
      units concurrently — sequence them or pre-plan the tail handoff. Found: dev-4 README P0 vs
      dev-1 hermes cut both needed assertions.yaml + test_ce_brain_drift ratchet on 20260708.
- [ ] ENV HYGIENE (root cause of TWO research contaminations today): controller root checkout
      /home/cedev2/creator-engine is parked on stale ce-release-0.3.1-rc2 with uncommitted mods —
      read-only researchers keep treating it as main. Park the rc2 release work in a dedicated
      worktree, return root checkout to main, and add "root tree ≠ canon" warning to worker templates.
- [ ] 🔴 GATE-DAEMON VANISH: ce-queue-daemon container disappeared ~14:00-16:20 20260708 (was UP 20h).
      Diagnose (docker events/journald/OOM) before relaunch; then ACTUALLY DEPLOY the #895 redeploy
      surface on DGX (systemd unit + env file never installed — merged≠deployed, AGAIN).
- [ ] dev-1 brief template says "open DRAFT PR" — #905 sat invisible to the gate as born-draft.
      Fix template to ready-for-review (or gate handles drafts explicitly).
