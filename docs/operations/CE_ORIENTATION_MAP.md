# CE Orientation Map

Status: SSOT map for Controllers.
Scope: subsystems, state roots, ledgers, dispatch records, and invariants.

## Subsystem Map

| Subsystem | Purpose | Main surfaces | Primary state/evidence |
| --- | --- | --- | --- |
| Belt | Pulls ready work, dispatches governed seats, polls queues, and repairs merge-queue state. | `ce pickup triage`, `ce pickup poll`, `ce queue poll`, `cev3 fleet status` | Forge work items, Active-Work ledger, dispatch/evidence records. |
| Gate daemons | Enforce pre-launch, hook, path, work-size, runtime-policy, and PR preflight constraints. | `creator-engine-validator check`, `hook-check`, `verify-path-manifest`, `verify-work-sizing-floor`, `ce validate-pr` | Carriers, hook event JSON, path manifests, runtime policies, completion reports. |
| herdr | Operator reach plane for contained seats; authenticated attach replaces raw container exec. | `ce herdr remote-attach`, herdr client/server socket | `/run/creator-engine/herdr/herdr.sock` inside substrate, contained pane metadata. |
| OpenBao | Secret and identity substrate; stores credentials by reference, not in prompts or argv. | OpenBao deployment plans and credential refs | Credential refs, per-seat env-file paths, no raw secret values in source-controlled state. |
| Forge | GitHub-first coordination/review/merge layer. | `cev3 pr`, `cev3 review`, `cev3 merge`, `ce dequeue`, forge status adapters | PRs, reviews, merge queue, app-token permissions, change block in dispatch/evidence. |
| Scope lifecycle | Frame to Shape to Build to Review to Ship; Scope is the work unit. | `cev3 scope`, `cev3 ratify`, `cev3 drive`, `cev3 collect` | `.ce/state/scopes/*.scope.yaml`, dispatch records, collected evidence. |
| Lane runtime | Visible governed seat/lane launcher and pane registry. | `ce lane launch`, `ce lane status`, `ce lane verify`, `ce lane archive` | Pane Registry records, transcripts, completion reports, seat lifecycle records. |
| PCO allocator | Worktree lane allocation/release and lease tracking. | `creator-engine-validator pco-allocate`, `pco-release` | Active-Work ledger claims, worktree lease records, allocation/release events. |
| Brain | Knowledge-SSOT assertion ledger and recall. | `ce brain init/assert/check/correct/ingest/recall/verify/probe/bootstrap` | `.ce/state` brain ledgers and rebuildable recall indexes. |
| Event/PCL ledgers | Local append-only event and PCL chains. | `ce event *`, `ce pcl *` | On-disk event/PCL ledger files plus head manifests/indexes. |

## State Roots

| Root | Owner | Contents | Mutability |
| --- | --- | --- | --- |
| `.ce/state` | CE v3 local state | Scopes, dispatch/evidence projections, brain state, local read models. | Local runtime state; generated/updated by CE commands. |
| `.ce/brain` | Brain/bootstrap state | Brain bootstrap and Knowledge-SSOT support artifacts. | Managed by brain commands. |
| `.ce/changelog` | Governance carrier | Per-PR changelog fragments. | Source-controlled, PR-authored. |
| `.ce/pr-manifests` | Governance carrier | Per-PR authorized path manifests. | Source-controlled, PR-authored, self-inclusive. |
| `.hermes/active-work-ledger` | Active-Work ledger | Claims, leases, events for governed lanes. | Runtime governance ledger; used by allocator/releaser/hook posture. |
| `.hermes/handoffs` | Handoff/envelope records | Assignment envelopes and handoff manifests. | Source/runtime coordination; attribution and path checks read it. |
| Ignored evidence roots | Runtime evidence | Transcripts, archives, fan-in packets, temporary evidence. | Not source-controlled unless explicitly listed by a carrier. |

## Ledger And Record Paths

| Artifact | Common path or resolver | Producer | Consumer |
| --- | --- | --- | --- |
| Scope record | `.ce/state/scopes/<scope-id>.scope.yaml` | `cev3 scope` | `cev3 ratify`, `cev3 drive`, status/read models. |
| Dispatch record | `.ce/state/.../dispatch...` under v3 local state | `cev3 drive --spawn`, `cev3 review --spawn` | `cev3 collect`, reviewer/merge/pr flows, reaper. |
| Dispatch schema | `schemas/dispatch-record.schema.yaml` | Source-controlled schema | Validators and runtime schema checks. |
| Active claim | `.hermes/active-work-ledger/...` | `pco-allocate`, `ce lane launch --claim-ticket` | `hook-check`, `pco-release`, seat reaper. |
| Worktree lease | `.hermes/active-work-ledger/...` | `pco-allocate` | lease conflict checks, release/reaper. |
| Pane registry | ledger/root-local registry paths | `ce lane launch` | `ce lane status`, containment/liveness surfaces. |
| Side-effect ledger | active-work-ledger side-effect records | `ce ledger record` | `ce ledger verify`, audit/replay. |
| Completion report | task-specific path or closeout artifact | Worker/reviewer seat | `ce lane verify`, PR evidence. |
| PR path manifest | `.ce/pr-manifests/<branch-slug>.md` | PR author/worker | `verify-path-manifest`, CI governance job. |
| Changelog fragment | `.ce/changelog/<branch-slug>.md` | PR author/worker | `--require-carrier` gate, release notes process. |

## Dispatch Flow

| Stage | Command | Record/evidence |
| --- | --- | --- |
| Shape | `cev3 scope <id> --goal ... --done-when ... --change-type ...` | Scope record under `.ce/state/scopes`. |
| Ratify | `cev3 ratify <id> --approver-ref <HEX64>` | Scope ratification digest. |
| Build dispatch | `cev3 drive <id>` | Assemble-only dispatch plan. |
| Spawn author | `cev3 drive <id> --spawn --ticket <work-item>` | Dispatch record, claim, lane/seat record. |
| Collect | `cev3 collect <id> --run <run-id> ...` | Evidence fold and outcome. |
| Open PR | `cev3 pr <id> --run <run-id> --branch <branch> --manifest-path <path> --apply` | Forge change block and PR metadata. |
| Review | `cev3 review <id> --run <run-id> --reviewer-actor <login> --spawn` | Distinct reviewer dispatch and venue. |
| Merge | `cev3 merge <id> --run <run-id>` then `--apply` when gated | Forge merge decision and merge action. |

## Key Invariants

| Invariant | Gate/surface | Rule |
| --- | --- | --- |
| Path-manifest fidelity | `verify-path-manifest` | `base..HEAD` changed paths must equal the self-inclusive fenced path list in `.ce/pr-manifests/<branch-slug>.md`. |
| Authorized paths hash | PR manifest | `AUTHORIZED_PATHS_SHA256 = sha256("\n".join(sorted(unique_paths)) + "\n")`. |
| Required carriers | `--require-carrier` | PR must carry both matching path manifest and changelog fragment. |
| Work-sizing floor | `verify-work-sizing-floor` / `ce validate-pr` | Declared work class must meet or exceed derived diff floor: `tiny`, `story`, `feature`, `epic`. |
| Distinct reviewer | `cev3 review --spawn` | Review venue must be a distinct non-author governed seat unless waived by ratified policy. |
| Claim before side effect | `cev3 drive --spawn`, `cev3 review --spawn`, `ce lane launch --claim-ticket` | Ticket claim is acquired and verified before lane/worktree/pane side effects. |
| Root checkout guard | `pco-allocate`, `pco-release` | Allocation/release refuse unsafe root-checkout posture. |
| No raw secrets | OpenBao/credential contract | Secrets travel by reference or owner-only env-file path; raw values do not enter source, prompt, argv, or ledger records. |
| Runtime policy | `ce lane launch --runtime-policy` | Resource envelope bounds seat runtime; unsupported enforce hosts refuse loudly. |
| Operating mode | `ce lane launch --operating-mode` | `strict` is default; elevated modes need ratified tenant policy. |
| Hook posture | `creator-engine-validator hook-check` | Governed seats evaluate hook events against launch-pinned ledger/root/manifest context. |
| Transcript integrity | `ce lane archive`, `ce lane verify`, `cev3 collect` | Transcripts and completion reports are hashed/verified before evidence folding. |
| Forge merge gate | `cev3 merge`, forge adapters | Merge is plan-by-default; apply requires gated authority and current forge state. |
| Version boundary | `_versions` checks | v1/shared/v3 import boundaries are tracked; new runtime modules require registry updates and tests. |

## Controller Lookup Table

| Question | SSOT command/doc |
| --- | --- |
| How do I see CLI groups and flags? | `docs/operations/CE_CLI_REFERENCE.md` |
| How do I spawn a reviewer venue? | `docs/operations/CE_CONTROLLER_PLAYBOOK.md#recipe-spawn-a-governed-reviewer-venue` |
| How do I allocate or release a lane? | `docs/operations/CE_CONTROLLER_PLAYBOOK.md#recipe-allocate-a-lane` and `#recipe-release-a-lane` |
| Where does Scope state live? | `.ce/state/scopes` and this map's State Roots section. |
| Where do PR carriers live? | `.ce/changelog` and `.ce/pr-manifests`. |
| What validates the PR path scope? | `creator-engine-validator verify-path-manifest`. |
| What validates declared work class? | `creator-engine-validator verify-work-sizing-floor` or `ce validate-pr`. |
| What is the attach plane for contained seats? | `docs/operations/HERDR_OPERATOR_REACH_PLANE.md` and `ce herdr remote-attach`. |
| What is the forge coordination contract? | `docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md`. |
| What protects path manifests? | `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. |
