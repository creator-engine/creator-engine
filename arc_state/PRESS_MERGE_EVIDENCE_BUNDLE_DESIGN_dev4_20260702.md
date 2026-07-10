# Press-Merge Evidence Bundle Design

Read evidence worktree: `/var/tmp/ce-294-press-merge-read` at `2290798396e20b52bf7595e4f442ace48438715b`.

## 1. Existing Per-PR Evidence Inventory

1. **Automerge decision JSON**: `AutoMergeDecision` is the current value record for merge posture. Its stable payload includes class, size band, minimum work class, mutation class, gates, decision, rationale, policy SHA, checks snapshot, run mode, kill switch, class flag, enabling ref, review decision, checks-green boolean, PR number, head SHA, repo, branch, base, required checks, author, and approver (`validators/creator_engine_validator/forge/automerge_policy.py:132-200`). `decide_automerge()` consumes changed paths/stats, declared work class, live checks, review decision, PR identity, author, approver, policy state, and emits `AUTO` only after all gates pass (`validators/creator_engine_validator/forge/automerge_policy.py:325-511`). The dry-run emitter writes `.ce/state/automerge/decisions/<pr>-<head>.json` (`validators/creator_engine_validator/forge/automerge_policy.py:514-556`). Workflow artifact name: `ce-automerge-decision-${{ github.run_id }}-${{ github.run_attempt }}` (`.github/workflows/automerge-decide.yml:357-362`).

2. **Actuation audit JSONL**: `ActuationResult` is the secret-free actuator outcome (`validators/creator_engine_validator/forge/automerge_actuator.py:27-36`). `actuate_if_ready()` re-verifies run mode, `AUTO`, kill switch, class flag, work class, enabling ref, change identity, live policy, distinct author/approver, and live required checks before enabling auto-merge (`validators/creator_engine_validator/forge/automerge_actuator.py:66-137`). The audit record includes surface, status, reason, acted, live run mode, decision, run mode, kill switch, class flag, work class, mutation class, repo, PR number, head SHA, branch, base, author, approver, single-PR marker, and enabling-ref presence (`validators/creator_engine_validator/forge/automerge_actuator.py:404-446`). Workflow artifact name: `ce-automerge-actuation-audit-${{ github.run_id }}-${{ github.run_attempt }}` (`.github/workflows/automerge-actuate.yml:113-118`).

3. **Validate-PR output**: `ce validate-pr` is the local PR preflight for committed `<base>..HEAD` state (`validators/creator_engine_validator/pr_preflight.py:1-6`). It resolves one declared work class from CLI, PR body, or carrier (`validators/creator_engine_validator/pr_preflight.py:304-356`), runs baseline-diff tests against base and head (`validators/creator_engine_validator/pr_preflight.py:445-470`), runs the test-coupling PR-diff gate (`validators/creator_engine_validator/pr_preflight.py:640-672`), includes clean worktree, comparison base, and declared-work-class checks (`validators/creator_engine_validator/pr_preflight.py:699-735`), prints a summary and exits 0 only when all checks pass (`validators/creator_engine_validator/pr_preflight.py:1000-1009`). Existing gap: this is a real per-PR evidence source but not yet a durable workflow artifact unless a caller captures stdout/stderr/exit code. CLI registration is `ce_cli.py:1538-1578` and dispatch is `ce_cli.py:4992-4993`.

4. **Review verdicts, head state, approval state, and changed paths from live GitHub inputs**: The decide workflow resolves PR number, head SHA, branch, base, author, and changed paths from the PR API or git diff fallback (`.github/workflows/automerge-decide.yml:58-152`). It resolves live `reviewDecision`, latest approved reviewer, declared work class from PR body, and check rows via `gh pr view` / `gh pr checks` (`.github/workflows/automerge-decide.yml:154-261`). The integrator model already has a richer secret-free PR evidence shape: repo, PR number, title, URL, body, head ref/SHA, base ref, review decision, approving review commits/reviewers, approval capability state, mergeability, rollup, checks, changed paths, completeness flags, draft state, and approval witnesses (`validators/creator_engine_validator/forge/integrator_belt.py:130-221`).

5. **Approval witnesses**: `DaemonApprovalWitness` captures reviewer login, commit OID, review state, and review ID (`validators/creator_engine_validator/forge/integrator_belt.py:150-169`). This is the right source for approval-must-match-current-head: the witness carries the commit OID, and the bundle should mark approval current only when at least one approving witness commit equals the minted head SHA.

6. **Diff/path set and carrier**: The generated carrier renders `.ce/pr-manifests/<branch-slug>.md`, the declared work class line, authorized path count, path hash, and fenced path list (`validators/creator_engine_validator/carrier_gen.py:101-135`). Path-manifest fidelity normalizes unique sorted path lines and validates count/hash (`validators/creator_engine_validator/checks/path_manifest_fidelity.py:92-105`, `validators/creator_engine_validator/checks/path_manifest_fidelity.py:197-320`). Representative artifact: `.ce/pr-manifests/ce-automerge-actuator.md` declares work class `story`, `AUTHORIZED_PATHS_COUNT=4`, hash `29319fcf...`, and four paths (`.ce/pr-manifests/ce-automerge-actuator.md:1-18`).

7. **Changelog**: Per-PR changelog fragments already exist under `.ce/changelog/`. Representative artifact: `.ce/changelog/ce-automerge-actuator.md` has YAML front matter with slug/date/kind/scope/issue and the human summary (`.ce/changelog/ce-automerge-actuator.md:1-12`). Another automerge example records expected/actual dry-run evidence for real PRs (`.ce/changelog/ce-291-automerge-classifier-dryrun.md:25-34`).

8. **Work-class declaration and sizing gates**: Work classes are `XS/S/M/L`; mutation classes include none/docs/code/schema/deploy/governance/identity/security/attestation/redaction (`validators/creator_engine_validator/work_sizing.py:13-37`). `size_ceremony()` emits artifact set, decomposition depth, ratification gates, and ADR requirement (`validators/creator_engine_validator/work_sizing.py:108-130`). `work_sizing_floor` projects included/excluded lines, size band, minimum work class, and `floor_met` (`validators/creator_engine_validator/checks/work_sizing_floor.py:140-192`) and enforces PR diff ceiling via `git diff --numstat --find-renames <base>..HEAD` (`validators/creator_engine_validator/checks/work_sizing_floor.py:306-354`).

9. **Daemon gate/audit records**: `DaemonDecision` records status, reason, repo, PR number, head SHA, path set, path-set source, overlap, and evidence strings (`validators/creator_engine_validator/forge/integrator_belt.py:228-255`). `DaemonPassResult` aggregates enqueue/skip/defer/fail counts and decisions (`validators/creator_engine_validator/forge/integrator_belt.py:270-297`). `run_daemon_pass()` discovers, evaluates, sequences, and enqueues eligible PRs and logs each decision (`validators/creator_engine_validator/forge/integrator_belt.py:693-760`). These records are relevant when the PR has been touched by the integrator belt, but are not required to mint the first one-PR demo bundle.

10. **Safety doctrine**: ADR-0004 says consumed payload is untrusted data only and must not steer execution, filesystem, remote, base-ref, credential, git/gh option, or publish policy (`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:55-88`). It also requires daemon-owned paths and credentialless validation (`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:90-149`), pinned remotes/base refs (`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:151-167`), and no auto-approve, merge, enqueue, review-dismissal, or reviewer-authority action without separate Operator-ratified policy (`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:176-200`).

## 2. Bundle Schema Proposal

Format: `ce-press-merge-evidence-bundle.v1.json`, one JSON object, uploaded as `ce-press-merge-evidence-bundle-<pr>-<head>-<run_id>-<run_attempt>.json`. The artifact is canonicalized with sorted keys plus trailing newline, and the workflow summary prints its SHA256.

Stable fields:

| Field | Source |
| --- | --- |
| `schema_version`, `kind` | Assembler constants: `1`, `ce-press-merge-evidence-bundle` |
| `minted_at_utc`, `assembler_version`, `assembler_workflow`, `assembler_run_id`, `assembler_run_attempt`, `read_repo_sha` | GitHub Actions runtime plus checked-out source SHA |
| `subject.repo`, `subject.pr_number`, `subject.url`, `subject.title`, `subject.base_ref`, `subject.head_ref`, `subject.head_sha`, `subject.is_draft` | Decide workflow PR inputs (`.github/workflows/automerge-decide.yml:58-152`) or integrator PR model (`integrator_belt.py:172-221`) |
| `staleness.valid_for_head_sha`, `staleness.current_head_sha_observed`, `staleness.status` | Minted head from decision JSON and optional live PR head refresh; `status` is `current`, `stale`, or `unknown` |
| `approval.review_decision`, `approval.approving_reviewers`, `approval.approval_witnesses`, `approval.current_head_approved` | Decide live inputs (`automerge-decide.yml:154-261`) and `DaemonApprovalWitness` fields (`integrator_belt.py:150-169`) |
| `checks.required`, `checks.green`, `checks.snapshot`, `checks.rows` | Decision JSON `required_checks`, `checks_green`, `checks_snapshot` (`automerge_policy.py:172-197`) plus `gh pr checks` rows from decide workflow (`automerge-decide.yml:193-260`) |
| `decision` | Exact automerge decision payload and artifact provenance from `ce-automerge-decision-<run_id>-<run_attempt>` |
| `actuation` | Latest matching actuation audit JSONL records for the same PR/head, if present, from `ce-automerge-actuation-audit-<run_id>-<run_attempt>` |
| `validation.validate_pr` | Captured command, exit code, stdout/stderr SHA256, and summary if a durable `ce validate-pr` capture exists; otherwise `available=false` with source gap noted from `pr_preflight.py:1-6` and `pr_preflight.py:1000-1009` |
| `work_sizing.declared_work_class`, `work_sizing.minimum_work_class`, `work_sizing.size_band`, `work_sizing.floor_met`, `work_sizing.ratification_gates`, `work_sizing.adr_required` | Carrier/PR body declaration, decision JSON, `size_ceremony()` (`work_sizing.py:108-130`), and PR diff floor (`work_sizing_floor.py:140-192`) |
| `paths.changed_paths`, `paths.authorized_manifest`, `paths.authorized_count`, `paths.authorized_sha256`, `paths.fidelity_status`, `paths.path_set_source` | Decide changed paths, `.ce/pr-manifests/<slug>.md`, path-manifest fidelity scanner (`path_manifest_fidelity.py:197-320`), and daemon path-set fields (`integrator_belt.py:228-255`) |
| `changelog.fragments` | Matching `.ce/changelog/<slug>.md` file path, blob SHA, front matter, and content SHA256 |
| `daemon.decisions` | Optional `DaemonDecision`/`DaemonPassResult` records for the PR/head (`integrator_belt.py:228-297`) |
| `external_evidence` | Optional array for video or computer-use capture artifacts when relevant: artifact name, URL, SHA256, captured_at, producer. Empty array is valid. |
| `provenance.sources[]` | For every source above: `name`, `type`, `artifact_name` or `file_path`, `file_line_range` where static, `artifact_sha256` where dynamic, `run_id`, `run_attempt`, `created_at`, `head_sha`, `repo_sha`, `producer` |
| `summary.verdict` | Derived only from included fields: `ready_for_human_merge`, `blocked`, or `stale`; never an authority-bearing merge instruction |

The bundle must embed exact dynamic source payloads or their SHA256 digests plus artifact names. It should never paraphrase a gate without retaining the source record that produced the gate result.

## 3. Presentation Surface Decision

Default: **GitHub Actions artifact file**. The ratifier reviews one artifact: `ce-press-merge-evidence-bundle-<pr>-<head>-<run_id>-<run_attempt>.json`. This is the best default because it is immutable for the run, content-hashable, requires no PR write permission, can carry full structured provenance, and stays consistent with ADR-0004's data-only/no-authority posture.

PR comment is not the default for Wave 1.4 because comments require `pull-requests: write`, can become stale in-place, and invite narrative summaries to replace source payloads. A later UX slice can post a short pointer comment containing PR/head/run/artifact/SHA256 only. A dedicated `ce pr evidence` command is useful as a local renderer/verifier, but it should not be the source of record because the press-merge surface must be available from the PR run without local tooling.

Staleness: the bundle is minted for exactly one `subject.head_sha`. Any push that changes the PR head invalidates the bundle. The assembler should set `staleness.status=stale` if a final live head read disagrees with the decision head; otherwise `current`. Approval is valid only when approval witness commit OID equals the minted head SHA. This preserves the approval-must-match-current-head doctrine and prevents a green bundle for an older commit from ratifying a newer push.

## 4. Assembler Placement

Code location: `validators/creator_engine_validator/forge/press_merge_evidence.py` for pure assembly and provenance validation. CLI seam: add `ce pr evidence` or `ce press-merge-evidence` in `validators/creator_engine_validator/ce_cli.py` near the existing inert automerge commands (`ce_cli.py:1580-1694`, `ce_cli.py:4039-4128`). Workflow seam: add a read-only assembly/upload step after `Run automerge decision` in `.github/workflows/automerge-decide.yml`, because that job already has PR identity, changed paths, review decision, check rows, declared work class, decision JSON, and read permissions (`.github/workflows/automerge-decide.yml:9-13`, `.github/workflows/automerge-decide.yml:263-362`).

Permissions: `contents: read`, `pull-requests: read`, `checks: read`, and `actions: read` if the assembler downloads prior actuation artifacts. No `contents: write`, no `pull-requests: write`, no `statuses: write`, no secrets beyond the default read token needed for PR/check/artifact reads.

Must never do: merge, approve, enable auto-merge, enqueue, dismiss reviews, mint approval markers, update PR body, mutate branch refs, alter policy state, rerun checks, call write-capable GitHub endpoints, or treat missing evidence as success. Its only allowed mutation is publishing the bundle artifact and step-summary hash for the current workflow run.

## 5. One-PR Demo Build Plan

Size: **S**. The smallest end-to-end slice should build a bundle for one pull request on `pull_request` events in `CE Automerge Decide`, using already-collected decision/live/check/path data. It should not claim to solve comment UX, integrator daemon ingestion, or durable local validate-pr capture.

Touch list:

1. `validators/creator_engine_validator/forge/press_merge_evidence.py`: pure assembler, JSON canonicalizer, source provenance model, staleness check helper.
2. `validators/creator_engine_validator/ce_cli.py`: read-only command to assemble from explicit files/JSON and print bundle JSON.
3. `.github/workflows/automerge-decide.yml`: after decision emission, call the assembler with decision file, paths file, live checks JSON, PR metadata, and upload `ce-press-merge-evidence-bundle-*`.
4. `validators/tests/unit/test_press_merge_evidence.py`: unit tests for source mapping, stale-head invalidation, approval witness current-head logic, missing optional validate-pr evidence, and canonical JSON digest stability.
5. Optional but recommended: `validators/creator_engine_validator/schemas/press-merge-evidence-bundle.schema.yaml` plus generated schema reference if this repo's schema practice requires it for new structured artifacts.

Demo success criteria: for one real PR, the decide workflow uploads exactly one bundle artifact whose `subject.head_sha` matches the decision JSON, whose `decision` section embeds the exact decision payload, whose `paths` section includes changed paths and matching carrier/changelog metadata when present, whose `approval.current_head_approved` is computed from witness commit/head equality when witness data is available, whose `validation.validate_pr.available=false` clearly marks the current durability gap, and whose SHA256 is printed in the step summary.

## 6. Ratification Asks

1. Ratify `ce-press-merge-evidence-bundle.v1.json` as the single Wave 1.4 structured evidence artifact. Recommendation: approve.
2. Ratify GitHub Actions artifact as the default presentation surface, with PR comments limited to a later pointer-only enhancement. Recommendation: approve.
3. Ratify strict head binding: bundle minted for one head SHA, invalid on push, approval current only when approval witness commit equals bundle head. Recommendation: approve.
4. Ratify read-only assembler placement in `validators/creator_engine_validator/forge/press_merge_evidence.py` plus inert CLI rendering in `ce_cli.py`. Recommendation: approve.
5. Ratify the Wave 1.4 demo scope as S: one-PR artifact bundle from the decide workflow, no merge/approve/comment mutation, no claim that durable validate-pr capture is solved. Recommendation: approve.
6. Ratify a follow-up ticket for durable validate-pr capture if ratifiers want raw local preflight stdout/stderr in every bundle. Recommendation: approve as follow-up, not as a blocker for the one-PR demo.
