# SEED BRIEF — ce-ops#166 D1b: memory→brain migration, batch 1 (dev-1)

- **Ticket**: ce-ops#166 (Knowledge SSOT), D1b lane — migrate replacement-controller
  day-1 doctrine from controller memory into the brain assertion ledger.
- **Role**: implementer. You are a non-contained peer controller: build, test,
  full preflight, self-push, open the PR. Review/approval stays with ce-dev-2
  (do NOT self-approve or merge).
- **Branch**: `ce-166-d1b-brain-batch1` off freshly fetched `origin/main`.
- **Declared work class**: M.
- **Allowed paths**: `.ce/brain/assertions.yaml` (via the `ce brain assert` CLI —
  it is a hash-chained append-only ledger, never hand-edit), and IF an encoded
  assertion's evidence-ref is a `docs/contracts/*.md` currently listed in
  `.ce/brain/doctrine-coverage.yaml` exceptions, remove that exception line in
  the same PR (ratchet burn-down — the coverage check must stay green). Plus
  changelog fragment + carrier. NOTHING else — no playbook edits (that is a
  separate slice), no validator code.

## Task

Encode the items below with disposition `assert` as brain assertions, each with
its evidence-ref (the repo artifact named in the table; verify the path exists
on current origin/main first). BEFORE freezing any item, spot-check its
code-behavior claim against current origin/main (stale line numbers / renamed
checks: correct or drop, and log every correction in the PR body). Skip items
dispositioned `playbook` or `skip:*`. Confidentiality rule is ABSOLUTE: no
hostnames, IPs, uids, account names, key paths, or token env names may enter
the ledger — the widened public-repo confidentiality scan (merged today) will
fail your preflight if they do.

## Standing directives

- FULL `ce validate-pr` GREEN in one pass before push (ce-ops#303).
- PR body: exactly one `- **Declared work class:** feature` line (M maps to
  feature in the legacy CI vocab; keep whichever the G5 gate on main accepts —
  check `validators/creator_engine_validator/work_sizing.py` WORK_CLASSES).
- Carrier stem must equal the pushed branch slug.
- Done-report: PR URL + head SHA.

## Doctrine items (from the 2026-07-02 architect extraction)

### Area 1 — Gate / Merge mechanics
1. [assert] `ce validate-pr` is the sanctioned local preflight; its default test command must match CI's full-tree invocation, not a unit-only subset. Evidence: `validators/creator_engine_validator/pr_preflight.py`, `.github/workflows/validate.yml`.
2. [assert] Every PR carries `.ce/pr-manifests/<branch-slug>.md` whose path-set+SHA256 equals base..HEAD; carrier stem must equal the pushed branch slug. Evidence: `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`, `validators/creator_engine_validator/checks/path_manifest_fidelity.py`.
3. [assert] Every PR touching a release-surface path requires a per-PR changelog fragment `.ce/changelog/<branch-slug>.md`. Evidence: path-manifest gate convention.
4. [assert] PR body must contain exactly one `- **Declared work class:** <class>` line whose class is ≥ the diff's sizing floor. Evidence: `validators/creator_engine_validator/checks/work_sizing_floor.py`.
5. [playbook — SKIP this slice] G5 body-format fix requires close+reopen.
6. [assert] Any PR editing `validators/creator_engine_validator/**` must rebuild the committed wheelhouse wheel + re-pin SHA256SUMS; remove gitignored egg-info before running the suite or test_install_bootstrap false-fails. Evidence: `validators/wheelhouse/`.
7. [assert] `docs/install.sh` and `docs/downloads/<version>/*` are frozen signed release artifacts; editing them is a release op (bump + controller re-sign), never a standalone edit. Evidence: `validators/creator_engine_validator/checks/install_spec_signature_guard.py`.
8. [playbook — SKIP] Release cut from CURRENT origin/main verification mechanic.
9. [assert] A new top-level `ce` CLI group forces same-PR couplings: README.md, test_v1_docs_reconciliation.py, regenerated `.ce/reference/cli.generated.md`. Evidence: `validators/tests/unit/test_v1_docs_reconciliation.py`, `checks/cli_reference_autogen_sync.py`.
10. [assert] The merge queue owns sequencing/testing/merge mechanics; the controller holds approve+enqueue; same-line content conflicts require manual rebase. Evidence: queue-daemon module.
11. [assert] A ce-dev-2 approval IS the merge trigger (queue-daemon auto-merges approved+green); to hold a PR, convert to draft — do not "approve to clear review". Evidence: `validators/creator_engine_validator/forge/integrator_belt.py`.
12. [assert] A dismissed changes-request is NOT approval; merge-readiness = reviewDecision==APPROVED on the CURRENT head; any push requires fresh approval. Evidence: same module.
13. [assert] The authoring controller never reviews/approves its own PR; review runs in a distinct governed reviewer venue with fresh pointer-only context. Evidence: `docs/operations/REVIEWER_VENUE_AUTHORITY.md`, `.claude/agents/reviewer.md`.
14. [assert] Reviewer workers are read-only and cannot fetch; controller must fetch the branch + create a review worktree BEFORE dispatch or the review false-fails "branch not accessible". Evidence: `.claude/agents/reviewer.md`.
15. [assert] A reviewer's comparison base must be freshly fetched origin/main; "carrier/diff mismatch" findings from a stale base are false — verify via gh pr files + fresh three-dot diff. Evidence: reviewer venue doc.
16. [assert] GitHub `Closes` only auto-closes same-repo; cross-repo `Closes ce-ops#N` is mention-only and needs the merge-triggered close-bot. Evidence: close-bot module/workflow if present, else the PR-authoring contract doc.
17. [assert] Governed worker seats are hard-blocked from `git push` by the Ring-1 PreToolUse hook (deploy mechanic, no authority path); pushes are performed by the orchestrator; never bypassed. Evidence: `.claude/hooks/ce-pretooluse.sh`, `validators/creator_engine_validator/hook_check.py`.
18. [assert, REDACTED FORM ONLY] Re-signing the install apply-spec requires the offline ce-root-v1 trust root held by the controller; a seat can only emit spec bytes for the controller to sign. Encode WITHOUT key paths. Evidence: `checks/install_spec_signature_guard.py`.
19. [assert] validate-pr can false-RED on brain drift against a stale gitignored `.ce/state/brain/assertions.yaml` that CI never sees; reconcile from canonical before assuming repo breakage. Evidence: `checks/ce_brain_drift.py`.

### Area 2 — Dispatch / Harvest
20. [assert] CE defines exactly 4 canonical worker roles (architect_research, implementer, verification, reviewer) with fixed tool boundaries; never improvise a role. Evidence: `.claude/agents/*.md`.
21. [playbook — SKIP] pointer+sha dispatch mechanic (already SSOT in `playbooks/controller/briefs/dispatch.md`).
22. [assert] Before any dispatch, intersect the candidate's file scope against the live in-flight territory map incl. shared/gate files, live grounding files, and signed artifacts. Evidence: `playbooks/controller/briefs/dispatch.md`.
23. [assert] Before dispatch, fetch origin/main and probe that the ticket isn't already resolved (changelogs, git log); stale checkouts give false "undone" verdicts. Evidence: dispatch brief.
24. [playbook — SKIP] self-contained no-egress briefs.
25. [assert] A seat "done" report without a verifiable commit SHA is not done; briefs must require `git commit && git rev-parse HEAD` and the controller verifies the ref. Evidence: dispatch brief.
26. [assert] Every dispatch pairs with an armed progress/stall watcher; watchers do not survive context resets and must be re-armed on resume. Evidence: dispatch brief.
27. [assert] After a context reset, prior background agents are neither reliably killed nor reliably resumed — check task/branch state before re-dispatching (duplicate-work risk). Evidence: dispatch brief.
28. [assert] Execution dispatch goes through restricted role-scoped subagents (no Agent tool); context-inheriting forks drift into controller behavior with controller credentials. Evidence: `.claude/agents/*.md`.

### Area 3 — Seat drive
29. [playbook — SKIP] docker exec (not run) probing.
30. [assert] Contained ≠ air-gapped: seats may have brokered git egress; verify per-seat before labeling broken. Evidence: containment backend docs.
31. [assert] Air-gapped seats have stale origin/main refs; harvest reconciles against authoritative origin/main + PR state before pushing. Evidence: harvest playbook if present.
32. [assert] Idle-on-main + no-PR contained seat is usually done-but-unpushed, not stalled; probe worktrees before re-dispatch. Evidence: harvest playbook.
33. [assert] Contained seats relaunch ONLY via the canonical launch path; raw harness relaunch breaks the sandbox. Evidence: launch/runner module.
34. [assert] Containment is an isolation substrate, never an authority tier; APPROVE authority is gated by role (author≠approver) + ratified run-mode, never by substrate. Evidence: `docs/contracts/` authority docs.
35. [assert] Peer controllers push/merge as their own identity; the Ring-1 push-block applies to spawned worker seats, not peer controllers. Evidence: hook_check + authority matrix.
36. [assert] Seats are foreman-controllers running multiple file-disjoint tickets concurrently via worktrees; route disjoint batches, not single tasks. Evidence: foreman seat-class docs.
37. [playbook — SKIP] codex foreman-directive durability across compaction.
38. [assert] Dispatch landing is judged by the pane's active Working indicator, never by the input box clearing; false-idle re-sends create duplicate dispatches. Evidence: herdr/seat-drive doc if present.

### Area 4 — Preflight / validation footguns
39. [assert] The full validator suite legitimately runs tens of minutes; high-CPU running state = grinding, not hung; do not kill on a hang assumption. Evidence: `validators/tests/`.
40. [assert] PYTHONPATH=validators leaks into test_install_bootstrap's install.sh subprocess and false-fails the console-script entrypoint check. Evidence: `validators/tests/integration/test_install_bootstrap.py`.
41. [assert] Never transcribe an agent-claimed hash/digest on trust; reproduce it via the documented rule and cross-check against a known-good value. Evidence: PATH_MANIFEST_FIDELITY_PROTOCOL.
42. [assert] Local validation runs against a clean COMMITTED tree; dirty shared worktrees produce false gate failures unrelated to the PR diff. Evidence: preflight doc.
43. [assert] Unset exported credential env vars before running the suite locally; their presence false-trips token-hygiene tests that never fire in CI. Evidence: preflight doc.

**Stop line**: ledger + coverage-exception burn-down + changelog + carrier only.
If `ce brain assert` cannot express an item (schema limits), drop it and list it
in the PR body under "deferred" — do not extend the schema in this PR.
