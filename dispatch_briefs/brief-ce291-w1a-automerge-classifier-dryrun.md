# WORK CLAIM — ce-ops#291 W1a · CEO-mode policy-tiered auto-merge — policy engine + PR-class classifier (DRY-RUN / classify-only)

**Seat:** TBD (controller assigns). **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
```
git fetch origin && git checkout -b ce-291-automerge-classifier-dryrun origin/main
```

## Why (self-contained)
This is the TOP BET of the day-shift arc: shift CE from hand-ratifying every PR to **pre-delegating LOW-RISK PR classes to auto-merge with no per-PR gesture**, reserving a human gesture only for HIGH-RISK classes. There is a ratified design (`ce-ops#291`); its load-bearing essentials are embedded below because they live in a host-local file you cannot read.

**This claim builds ONLY the dry-run / classify-only stage.** You build the path→mutation classifier + the policy engine + a dry-run decision emitter + tests. It MUST NOT merge, approve, enqueue, or enable GitHub auto-merge for anything. The first live flip is a separate reserved Operator gesture, entirely out of scope here.

**~70% is already built — REUSE, do not reinvent the risk model:**
- `validators/creator_engine_validator/work_sizing.py` — `size_ceremony(work_class, mutation_class)` (read it: lines ~88–111) returns `ratification_gates`. `("auto_back_gate",)` ⇒ AUTO-eligible; any list containing `"operator_merge"` ⇒ GESTURE-REQUIRED. The mutation-class taxonomy lives in `_RISK_TABLE` (lines ~51–85): keys are exactly `none, docs, code, schema, deploy, governance, identity, security, attestation, redaction`.
- `validators/creator_engine_validator/checks/work_sizing_floor.py` — `classify_change_size(change_stats)` (read it: lines ~175–210) returns `minimum_work_class` (tiny/story/feature/epic) + line band; it already excludes lockfiles/vendored/generated.
- `validators/creator_engine_validator/forge/approval_capability.py` — read lines ~1–90 + the `ApprovalWallState`/armed-dormant durable-state pattern. **MIRROR this secret-free state pattern** for your new policy state. Do NOT call the issuer/minter — that is merge-glue (a later, privileged PR).

**Design decision (honor it):** classification = compose the SIZE axis (`classify_change_size`) and the MUTATION axis (your new path classifier) and feed `mutation_class` into `size_ceremony`. Do **not** invent a parallel risk model.

## Task
1. **New module `validators/creator_engine_validator/forge/mutation_classifier.py`:**
   `mutation_class_for_paths(paths, policy) -> str` returning the **highest-risk** class touched, **fail-closed** (any unknown/ambiguous path ⇒ most-privileged class). The returned string MUST be one of the `_RISK_TABLE` keys above (else `size_ceremony` raises). Path predicates are **config-driven** — read them from the policy config (Task 3), not hardcoded. Seed the config from this table:
   - `docs` — only `docs/**`, `*.md`, `.ce/changelog/**`, `.ce/pr-manifests/**`
   - `code` — `validators/**` (non-schema), `tools/**` (non-broker), app source
   - `schema` — `schemas/**`, `surfaces/manifest.yaml`, `*.schema.yaml`
   - `deploy` — `deploy/**`, Dockerfiles, `.github/workflows/**`
   - `governance` — `.ce/contracts/**`, `docs/contracts/**`, `playbooks/**`, governance artifacts
   - `identity` — identity-registry, `secret_identity.py`, App/account config
   - `security`/`attestation`/`redaction` — `forge/approval_capability.py`, `forge/cred_injection_proxy.py`, `tools/egress-broker/**`, OpenBao/wall paths, redaction filters
2. **New module `validators/creator_engine_validator/forge/automerge_policy.py`:**
   - `AutoMergePolicyState` — load/save, **secret-free**, mirrors `ApprovalWallState`; default `run_mode="dev"`, `kill_switch=false`, every class `auto_merge=false`, `enabling_decision_ref=null`. Persist at `.ce/state/automerge/policy.json` (config-driven path; create the schema in Task 4).
   - `decide_automerge(numstat, paths, declared_work_class, policy_state, checks) -> AutoMergeDecision` — composes size + mutation via `size_ceremony`, then returns a **structured decision + rationale**: `{class, size_band, mutation_class, gates, decision: "AUTO"|"GESTURE", rationale, policy_sha, checks_snapshot}`. AUTO requires ALL of: gates == `("auto_back_gate",)`; every required check green; `reviewDecision != CHANGES_REQUESTED`; size band not `split_required`; no path in the GESTURE set; `kill_switch` false; `run_mode != dev` (in dev EVERYTHING is GESTURE). **`decide_automerge` and everything in this claim is PURE/decision-only — it returns a verdict, it NEVER acts on it.**
3. **Config file** holding the risk policy (path predicates per class + the policy-state path). The policy is data, not code — a reviewer can tune predicates without editing Python.
4. **Schemas:** `schemas/automerge-policy.schema.yaml` + `schemas/automerge-decision.schema.yaml`.
5. **Dry-run emitter:** a function that, given a PR's `base..HEAD` numstat + changed paths + checks snapshot, writes `.ce/state/automerge/decisions/<pr>-<head>.json` and returns the decision. **No GitHub mutation, no `gh pr merge`, no auto-merge enable.** Wire-up of an `automerge-decide` CLI subcommand and the `ce-automerge.yml` workflow are OUT OF SCOPE for this claim — leave a single `# TODO(ce-ops#291): register automerge-decide subcommand (dev-1 owns ce_cli.py)` stub comment in your new module. **DO NOT edit `ce_cli.py` or `v3_cli.py`** — dev-1 owns all CLI-registration edits this fan-out.
6. **Tests** (`validators/tests/unit/test_mutation_classifier.py`, `test_automerge_policy.py`): path→class table incl. highest-risk-wins + fail-closed; composition with `size_ceremony`; dry-run writes a decision and merges nothing; kill-switch halts; dev-mode ⇒ everything GESTURE; **"a GESTURE class never returns AUTO even if its flag is on."**
7. **DoD validation:** run the dry-run emitter over **≥3 recent arc-merged PRs**, LOG the per-PR decision + rationale to `.ce/state/automerge/decisions/`, and record expected vs actual in the PR body. Required outcome: docs/changelog PRs ⇒ AUTO; any PR touching wall/broker/`.github/**`/schema/governance ⇒ GESTURE; **ZERO false-AUTO on any privileged-path PR.**

## Allowed paths (nothing else)
`validators/creator_engine_validator/forge/mutation_classifier.py`, `validators/creator_engine_validator/forge/automerge_policy.py`, the new automerge policy **config file** (inside the module tree), `schemas/automerge-policy.schema.yaml`, `schemas/automerge-decision.schema.yaml`, `validators/tests/unit/test_mutation_classifier.py`, `validators/tests/unit/test_automerge_policy.py`, registered-check count drift-guard test files **only if** your new check registration forces them (mirror ce-ops#168 precedent), `.ce/changelog/**`, `.ce/pr-manifests/**`.
**EXCLUDE (do NOT touch): `ce_cli.py`, `v3_cli.py` (stub TODO only), `work_sizing.py`, `work_sizing_floor.py`, `approval_capability.py`, `.github/workflows/**`.**

## Evidence (DoD)
- Full `ce validate-pr` GREEN (CI-parity, full suite).
- Dry-run classified **≥3 recent arc PRs** with logged decisions under `.ce/state/automerge/decisions/`; PR body shows expected-vs-actual with **zero false-AUTO on a privileged-path PR**; **nothing was merged/approved/enqueued.** (Suggested spread: one docs-only ⇒ AUTO, one touching `.github/**` or wall/forge ⇒ GESTURE, one `schemas/**` ⇒ GESTURE.)
- ⚠️ **G5 BODY FORMAT (mandatory):** the PR body MUST contain exactly ONE line formatted precisely as `- **Declared work class:** <tiny|story|feature|epic>` (a `**Work class:**` header or a `[PASS]` log line does NOT match). Pick the tier the gate derives (this is `code`+`schema` mutation, story/feature size).

## Stop-line
- **CLASSIFY-ONLY / DRY-RUN. You MUST NOT merge, approve, enqueue, run `gh pr merge`, enable GitHub auto-merge, or mint/call any approval-capability marker.** This stage ships ARMED-OFF: `run_mode=dev`, every class `auto_merge=false`. The live flip is a reserved Operator gesture, out of scope.
- Green + self-push works → push + PR ref ce-ops#291. Do NOT approve/merge/enqueue your own PR.
- Green but push FAILS (contained-seat self-push gap #337) → STOP + report `READY-FOR-HARVEST: branch ce-291-automerge-classifier-dryrun, <N> commits, preflight green`.
- Preflight RED on a NEW gate from your change → STOP + report the failing gate.
- If `size_ceremony` raises on an unknown `mutation_class` → your classifier emitted a key not in `_RISK_TABLE`; fix the classifier, do not patch `work_sizing.py`.
