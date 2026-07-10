# DESIGN — CEO-mode policy-tiered auto-merge (ce-ops#291)

**Arc:** day-shift 2026-06-27, item 1.1 (THE top bet — the run-mode gear-shift). **Status:** design only (build+arm = G5; first live flip = R2/Operator).
**Thesis:** amortize human ratification within our own trust domain (zero attestation needed) so pre-authorized low-risk PR classes merge with no per-PR gesture — Peter's "press merge on aggregated evidence," made into policy.

## 0. The headline: ~70% of this is already built
| Piece | Exists? | Where |
|---|---|---|
| Risk taxonomy (mutation class → ratification gates) | ✅ | `work_sizing.py` `_RISK_TABLE` |
| `auto_back_gate` vs `operator_merge` (= AUTO vs GESTURE) | ✅ | same table |
| Size classifier (line bands + path exclusions) | ✅ | `work_sizing_floor.py` `classify_change_size` |
| The wall: armed/dormant durable state + HMAC capability marker | ✅ | `forge/approval_capability.py` |
| `policy_sha` bound to **run_mode** + risk_tier | ✅ | `approval_capability_policy_sha` → `grading_policy.approval_policy_sha` |
| **Path → mutation_class classifier** | ❌ NEW | `checks/` doesn't map paths to governance/security/identity/... |
| **Policy engine** composing (size, mutation) → AUTO/GESTURE decision | ❌ NEW | — |
| **Merge-glue** (green PR → decision → auto-mint marker or hold) | ❌ NEW | — |

CEO-mode is **not a new mechanism**. It is wiring the *existing* `size_ceremony().ratification_gates` to the *existing* wall + merge queue, switched by the *existing* `run_mode`.

## 1. Classification (the decision)
For each green PR, derive two axes already modeled in `work_sizing.py`:
- **Size axis** — reuse `classify_change_size(numstat)` → `minimum_work_class` (tiny/story/feature/epic) + line band. Already excludes lockfiles/vendored/generated.
- **Mutation axis** — **NEW** `mutation_class_for_paths(changed_paths) -> str` returning the *highest-risk* class touched, by path predicate (fail-closed = pick the most privileged on any ambiguity):

| mutation_class | path predicates (illustrative — finalize in impl) |
|---|---|
| `docs` | only `docs/**`, `*.md`, `.ce/changelog/**`, `.ce/pr-manifests/**` |
| `code` | `validators/**` (non-schema), `tools/**` (non-broker), app source |
| `schema` | `schemas/**`, `surfaces/manifest.yaml`, `*.schema.yaml` |
| `deploy` | `deploy/**`, Dockerfiles, `.github/workflows/**` (CI) |
| `governance` | `.ce/contracts/**`, `docs/contracts/**`, `playbooks/**`, governance artifacts |
| `identity` | identity-registry, `secret_identity.py`, App/account config |
| `security`/`attestation`/`redaction` | `forge/approval_capability.py`, `forge/cred_injection_proxy.py`, `tools/egress-broker/**`, OpenBao/wall paths, redaction filters |

Then **decision = `size_ceremony(declared_work_class, mutation_class)["ratification_gates"]`**:
- `("auto_back_gate",)` → **AUTO** (docs/none only).
- contains `operator_merge` → **GESTURE-REQUIRED** (code/schema/deploy/privileged).
- Additional AUTO guards (all must hold): every required check green; `reviewDecision != CHANGES_REQUESTED`; size band not `split_required`; public-surface guard clean (the existing `public_docs_confidentiality` check); no path in the GESTURE set.

This deliberately reuses the ratified ceremony table — we do **not** invent a parallel risk model.

## 2. Plug-in point (NO change to the capability-token mechanism)
The wall already requires a valid HMAC capability marker *in addition* to GitHub `APPROVED`. Auto-merge does **not** bypass it — it **pre-delegates the minting** of that marker for the AUTO class, recorded as a durable Operator decision.

**Mechanism — extend the integrator/CI admission path:**
1. A workflow `.github/workflows/ce-automerge.yml` fires on `check_suite: completed` / required-checks-green for a PR.
2. It runs `ce-cli automerge-decide --pr N --base origin/main` → `{class, decision, rationale, policy_sha}`.
3. **If AUTO and the per-class flag is enabled** (CEO mode): the controller-side job **mints the capability marker** via the existing `ApprovalCapabilityIssuer.mint(...)` using the wall secret (OpenBao/`CE_APPROVAL_CAPABILITY_SECRET`) — the same secret a human approval would use — then `gh pr merge --auto`. The marker's `approved_by` = `policy:ceo-automerge` and its `policy_sha` encodes `run_mode=ceo` + the enabling decision ref, so the wall verifies it normally and the audit trail shows it was *policy*-authorized.
4. **If GESTURE-REQUIRED, or AUTO-but-disabled, or Dev mode:** no-op. The PR waits for a human to approve (minting the marker the existing way). Identical to today.

The wall's verifier (`ApprovalCapabilityVerifier.verify`) is unchanged: it still demands a valid marker bound to repo/PR/head/policy. We only add a *policy-gated automatic minting path* for one class. The human still owns the secret and the durable decision to enable the class.

## 3. Run-mode = the master switch (the gear-shift)
`run_mode` already parameterizes `approval_policy_sha`. Define the enforcement contract:
- **Dev** (today): every mutation class — including `docs` — waits for `operator_merge`. Nothing auto-merges.
- **CEO**: `auto_back_gate` classes (docs/none) with their per-class flag on → auto-mint + merge; everything else → gesture. *This is the shift this arc delivers.*
- **strangeLoop** (future): widen AUTO to `code` after `distinct_review` (an AutoReview/#292 pass) is green; privileged classes always stay non-delegable.

## 4. Durable state, arming, and the flip (G5 vs R2)
Mirror the existing secret-free `ApprovalWallState(armed: bool)` pattern with a new **`AutoMergePolicyState`** at `.ce/state/automerge/policy.json`:
```json
{ "run_mode": "dev", "kill_switch": false,
  "classes": { "docs": {"auto_merge": false}, "code": {"auto_merge": false}, ... },
  "enabling_decision_ref": null }
```
- **Build+arm (G5, this arc):** ship the classifier + policy engine + dry-run CLI + workflow, with `run_mode=dev` / all `auto_merge=false`. Nothing merges autonomously. Fully testable.
- **First flip (R2, Operator):** a single low-friction gesture — set `run_mode=ceo` + `classes.docs.auto_merge=true` + an `enabling_decision_ref` (the ratification record). **The CEO gradient:** flip `docs` first, observe, then widen class-by-class. Each flip is the Operator pre-delegating one more class.
- **Kill-switch:** `kill_switch=true` halts all auto-merge instantly regardless of class flags.

## 5. Dry-run (the arc DoD)
`ce-cli automerge-decide --dry-run` classifies without merging. Validation harness: run it over the last ~20 merged PRs and emit, per PR, the class + AUTO/GESTURE decision it *would* have made. Acceptance = the classifier’s decisions match human judgment (docs/changelog PRs → AUTO; anything touching wall/broker/.github/schema → GESTURE), with **zero** false-AUTO on a privileged-path PR. This proves the gear before any live flip.

## 6. Audit & safety
- Every decision (dry-run or live) writes `.ce/state/automerge/decisions/<pr>-<head>.json`: class, size band, mutation_class, gates, decision, policy_sha, enabling_decision_ref, checks snapshot.
- Live auto-merges additionally emit the minted-marker audit (reusing `ApprovalCapabilityVerification.to_audit_record`).
- Fail-closed everywhere: unknown path → most-privileged class; missing/red check → GESTURE; unreadable policy state → Dev/no-op.

## 7. Implementation surface (for seat dispatch)
**NEW files:**
- `validators/creator_engine_validator/forge/mutation_classifier.py` — `mutation_class_for_paths(paths) -> str` (the path-predicate table, fail-closed).
- `validators/creator_engine_validator/forge/automerge_policy.py` — `AutoMergePolicyState` (load/save, secret-free, mirrors `ApprovalWallState`), `decide_automerge(numstat, paths, declared_work_class, policy_state, checks) -> AutoMergeDecision`, kill-switch, `enabling_decision_ref`.
- CLI subcommand `automerge-decide` in `ce_cli.py` / `v3_cli.py` (`--pr`, `--base`, `--dry-run`) → JSON decision; dry-run never mutates.
- `.github/workflows/ce-automerge.yml` — green-trigger → decide → (AUTO+enabled) mint marker + `gh pr merge --auto` + audit; else no-op. Guarded by `kill_switch` + `run_mode`.
- `schemas/automerge-policy.schema.yaml` + `schemas/automerge-decision.schema.yaml`.
- Tests: `validators/tests/unit/test_mutation_classifier.py`, `test_automerge_policy.py` — path→class table, composition with `size_ceremony`, dry-run, kill-switch, **"GESTURE class never auto-merges even when its flag is on"**, fail-closed cases.

**REUSE (do not modify):** `work_sizing.py`, `work_sizing_floor.py`, `approval_capability.py` (call `ApprovalCapabilityIssuer.mint`), `grading_policy.approval_policy_sha`, `public_docs_confidentiality` check, the merge queue.

**Impl DoD:** classifier + policy engine + dry-run CLI built & unit-tested; dry-run validated over the last ~20 merged PRs with zero false-AUTO on privileged paths; workflow present but **armed-off** (`run_mode=dev`, all flags false). Decomposable into 2 PRs: (A) classifier + policy engine + dry-run CLI + tests [story/feature, `code`+`schema` mutation — needs gesture/review]; (B) the workflow + marker-minting glue + audit [`deploy`/`security` mutation — privileged, controller-reviewed]. First flip = Operator.

## 8. Why this is the moat, not a bypass
The wall still enforces a valid capability for every merge. We changed *who supplies the gesture for the lowest-risk class*: from a live human keystroke to a durable, revocable, class-scoped Operator pre-delegation. Human-rooted ratification is preserved (the Operator authored the enabling decision) and merely amortized — exactly the CEO run-mode the deployment×run-mode model predicts. Containment is irrelevant here (own trust domain); attestation (#289) only becomes a precondition if we later let a *contained agent* hold the minting authority — out of scope for this arc.
