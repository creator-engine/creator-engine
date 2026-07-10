# ADR — Mode-Aware Grading & Ratification Model for Creator Engine

- **Status:** RATIFIED 2026-06-26 (Operator). Decision log in §9. Implementation = spine-first; autonomous live-merge executor HELD behind contained controller.
- **Type:** Decision record + cited design research. MADR-style.
- **Date:** 2026-06-26.
- **Authors:** CE-DEV-2 Controller (composed via research fan-out).
- **Supersedes / refines:** extends ce-ops `ADR-0003-reviewer-independence-isolation-domain` (independence = isolation-domain disjointness, multi-principal fleet) to the **N=1 / solo** case it never addressed; informs the three-deputy design's open step 5 (`designs/DESIGN_THREE_DEPUTY_GOVERNANCE_20260624.md` §92 — "specify the Correctness deputy for approval: quorum size, independent-verifier selection, consequence threshold"). Refines the `REVIEWER_TRIAGE.md` line that "in N=1 mode, agentic reviewer evidence is useful but non-counting."
- **Anchors the rejection of:** a naive "approver ≠ author **identity**" merge guard (rejected as a band-aid — see Decision §D1).

---

## 1. Context & problem

CE runs AI coding agents ("seats": Claude Code / Codex instances) that author code and open PRs. A governance "wall" (the armed `approval_capability` HMAC marker, `validators/creator_engine_validator/forge/approval_capability.py`, consumed by `forge/integrator_belt.py`) requires a trusted approval before the integrator merges. The intent is CE's product thesis: a **grader outside the agent** — an agent must not rubber-stamp its own work.

The existing reviewer-independence rule (ce-ops ADR-0003) defines independence as **isolation-domain disjointness** across four axes — identity, credential, execution sandbox, controlling principal — with a risk-tiered ladder (Tier 2 floor for code review, Tier 4 for releases/keys). That rule was authored for a **multi-principal fleet** (dev-1…dev-4, distinct Apps/users/controllers). It assumes a second principal *exists*.

**The forcing problem:** CE's PRIMARY user is a **solo developer**, possibly with **ONE agent**. A hard "different identity/principal" requirement is **structurally unsatisfiable** at N=1 (GitHub itself cannot synthesize a second human — confirmed below), so a naive identity guard would make the single agent unable to ship, killing the core use case. CE also explicitly wants to **leverage coding-harness native threading / sub-agent capabilities**. So the central question is not "is a separate identity nicer" (it is) but: **what does the wall legitimately require at solo / small-team / fleet scale, and can a governed, context-isolated sub-agent of the SAME seat be a valid independent approver of that seat's work?**

This ADR answers that with a mode-aware model, grounded in current prior art (§3) and CE's actual mechanism (§2).

---

## 2. CE's actual model today (ground truth)

- **The wall is two-layered, not identity-only.** The integrator treats GitHub `reviewDecision == APPROVED` as **necessary but not sufficient**; it additionally requires a controller-minted **approval-capability marker** — an HMAC over `{repo, pr_number, head_sha, approved_by, issued_at, expires_at, policy_sha}` bound to one PR head, TTL-limited, verified against a wall secret (`approval_capability.py`). GitHub already blocks a PR author from approving their own PR; the HMAC layer prevents a forged/unsanctioned approval from counting.
- **Reviewer-venue authority is a bounded capability, not ambient.** Ring-1/Ring-2 (`hook_check.py`) classifies `gh pr review` as the restricted mechanic `pr_review` and **hard-denies it without a validated `reviewer_authority_envelope`** (`checks/reviewer_authority_envelope.py`, ADR-V2-009). The envelope authorizes **exactly one mechanic on exactly one PR**, carries no secret, and is honored only on a distinct `--role reviewer --lane-kind review` venue (`is_distinct_reviewer_venue`). Fail-closed end to end.
- **Same-seat semantic review is already blocked by design.** `REVIEW_GATE_REVIEWER_VENUE_DESIGN.md` emits `BLOCKER_SAME_SEAT_REVIEW_VENUE`: semantic review cannot be satisfied from the authoring seat; a **hidden/background sub-agent is explicitly NOT a distinct CE reviewer venue** "unless a future Source-ratified design gives it identity, transcript, hook-inheritance, evidence, and fan-in semantics." **This ADR is that design gate's input.**
- **Containment is the enforcement floor.** ADR-0004 (mandatory containment) + the contained-controller direction strip ambient credentials, so any approval policy becomes **mechanism-enforced**, not advisory. The three-deputy model names the residual: Transport/Authorization deputies bound *access* and *blast radius* but **not intent** — "a scoped/allowlisted/attributed seat can still APPROVE bad code." Correctness ("grader-on-the-work / quorum / refusal spine") is the irreducible deputy. Its §92 step 5 — quorum size, independent-verifier selection, consequence threshold — is open. This ADR closes it for the grading axis.
- **Current solo stance:** `REVIEWER_TRIAGE.md` — "in N=1 mode, agentic reviewer evidence is useful but **non-counting**; the Operator remains the reviewer/ratifier boundary." That is a safe but blunt default (human is the only grader at N=1). This ADR keeps the human as **ratifier** but defines a **counting deterministic + cross-model grading layer** so the solo agent can ship low/medium-risk work without a per-PR human gate.

---

## 3. Prior art (cited, current — researched 2026-06-26)

### 3.1 Separation of duties / four-eyes — and its legitimate relaxation
- **No framework treats four-eyes as absolute.** SoD splits *authorization, custody, record-keeping, reconciliation* so fraud requires collusion (Wikipedia, citing Botha & Eloff, *IBM Systems Journal*: https://en.wikipedia.org/wiki/Separation_of_duties). **NIST SP 800-53 Rev 5 AC-5** states its purpose as reducing "malevolent activity **without collusion**," and is **N/A at the Low baseline** — the framework itself scopes SoD by risk (https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-5/).
- **Compensating-controls doctrine is the accepted solo relaxation.** ISACA: "compensating controls can be introduced **after thorough risk analysis**… SoD is a control and… should be viewed within the frame of risk management" (https://www.isaca.org/resources/isaca-journal/issues/2016/volume-3/implementing-segregation-of-duties-a-practical-experience-based-on-best-practices). SOC 2 CC8 for startups: where one person develops/deploys/approves, "**secondary review, documented approvals or shared oversight can mitigate the risk when traditional separation is not possible**"; auditors "very rarely have to force a client to change… it usually comes down to improving documentation and formalized procedures" (https://warrenaverett.com/insights/soc-2-catch-22, https://www.designcs.net/soc-2-cc8-common-criteria-related-to-change-management/).
- **When a second human is irreducible.** The canonical irreducible case is **high-consequence + irreversible action where the detective control is itself within the actor's span of control** — PCI-DSS dual control / split knowledge for cleartext key operations, "to eliminate the possibility of one person having access to the whole key" (https://kirkpatrickprice.com/video/pci-requirement-3-6-6-using-split-knowledge-dual-control/). Where the act is **reversible** *or* an **independent tamper-evident detective control** exists outside the actor's control, deterministic controls + documented after-the-fact review are an accepted substitute. Automation **never removes** the requirement; it enforces or detects (https://nhimg.org/articles/segregation-of-duties-vs-separation-of-duties-in-iam-governance/).

### 3.2 Policy-as-code / deterministic gates — power and hard limits
- **GitHub cannot synthesize a second reviewer.** Rulesets can "require… a specific number of approving reviews" and "require an approval from someone other than the last person to push" (https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets). For a **solo/admin repo**, that is either unsatisfiable or routed around via the **bypass list** (repo admins are eligible bypass actors; "for pull requests only" mode preserves an audit trail but still permits self-merge) (https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository). CODEOWNERS is advisory unless "require code owners" is on, **fails open silently over 3 MB**, and maps files→people, never "is this correct" (https://docs.github.com/articles/about-code-owners).
- **OPA/Gatekeeper/Kyverno** are the admission-control analog of required approval — deterministic allow/deny, "consistent, rule-driven outcomes rather than subjective human judgment," deny-overrides (https://www.openpolicyagent.org/docs/kubernetes). CI required status checks generalize this: any deterministic program becomes a merge precondition.
- **The structural limit (load-bearing for CE).** Deterministic gates faithfully substitute for the **mechanical, rule-expressible** fraction of review and **structurally miss** business-logic flaws, authz bypasses, design intent, novel logic/security errors, and "should we do this at all." "Several recent breaches… occurred in organizations with mature 'shift left' programs… automated scanning missing vulnerabilities that manual threat modeling would have caught" (https://securityboulevard.com/2026/03/shift-left-has-shifted-wrong-why-appsec-teams-not-developers-must-lead-security-in-the-age-of-ai-coding/). AI/automated review is good at defects but "not… taking a stance on whether your abstractions make sense or your architecture is heading somewhere bad" — humans are needed for "architectural stewardship," not bug-finding (https://www.swarmia.com/blog/should-humans-still-review-code/). A gate presupposes a human already wrote the rule for this case; novel risks are out-of-distribution by construction.

### 3.3 LLM-as-judge / self-review independence — the decisive evidence
- **A same-model, context-isolated reviewer is NOT independent.** Errors across LLMs are **correlated, not independent**, and correlation is **dramatically higher for same-developer / same-architecture / same-size models** — two instances of the same weights are the **worst case** for shared blind spots (Kim et al. 2025, *Correlated Errors in LLMs*, https://arxiv.org/html/2506.07962v1: wrong-answer agreement 42.3% vs 12.7% chance; "a judge over-inflates the accuracy of models that share its errors").
- **Self-preference is real and causal.** LLM judges recognize and favor their own generations; self-recognition and self-preference are **linearly correlated and causal** (Panickssery et al., NeurIPS 2024, https://arxiv.org/abs/2404.13076). GPT-4 shows significant self-preference, mechanistically tied to favoring lower-perplexity / more-familiar text — which a same-model reviewer maximally shares (Wataoka et al. 2024, https://arxiv.org/abs/2410.21819). Original "self-enhancement bias" documented in Zheng et al. 2023 (https://arxiv.org/abs/2306.05685).
- **Intrinsic self-correction without an external signal fails.** "LLMs Cannot Self-Correct Reasoning Yet" (Huang et al., DeepMind, ICLR 2024, https://arxiv.org/abs/2310.01798): **intrinsic** self-correction (no oracle/external feedback) does **not help and usually hurts** — CommonSenseQA 75.8% → 38.1% after one round; the model "cannot tell which of its answers to fix." Gains only appear **with an external oracle**. Self-Refine/Reflexion gains rely on **external task feedback** (tests, environment reward), not introspection (https://arxiv.org/abs/2303.17651, https://arxiv.org/abs/2303.11366).
- **Multi-agent of the SAME model is not a free win.** At equal compute, same-model debate can **underperform plain self-consistency**; homogeneous agents drift to confident shared-wrong consensus ("tyranny of the majority") (Huang et al. 2024; https://arxiv.org/html/2511.07784v1).
- **What buys real independence:** a **different base model / family** (errors decorrelate), a **diverse panel/jury** rather than N copies (Verga et al. 2024, *Replacing Judges with Juries / PoLL*, https://arxiv.org/abs/2404.18796), **external/verifiable signal** (tests, execution, oracles — not introspection), and **authorship obfuscation** to strip the self-recognition cue (https://arxiv.org/abs/2512.05379). Trajectory-level critique (Agent-as-a-Judge, https://arxiv.org/abs/2410.10934) helps but still inherits judge bias unless the judge differs from the author.

---

## 4. The key question — answered

> Is reviewer independence a property of **identity**, **context-isolation**, or **governance**? Can a governed, context-isolated sub-agent of the SAME seat validly approve that seat's work?

**Independence is a layered property, and the three axes are not interchangeable. Context-isolation is the *weakest* of the three for an LLM grader.** The synthesis (§3.3) is unambiguous: the author's blind spots live in the **model weights and training distribution**, not in the context window. A fresh thread / sub-agent of the same model:
- shares the author's **correlated error distribution** (Kim 2025) — it tends to miss the *same class* of bug;
- exhibits **self-preference** toward text it recognizes as its own family's (Panickssery 2024; Wataoka 2024);
- if asked to "critique its own reasoning," can **degrade** rather than improve absent an external signal (Huang 2024).

So **context-isolation alone does NOT confer independence.** It removes *shared working context / prompt collusion* (a real benefit — it prevents the reviewer from inheriting the author's rationalizations), but it does **not** remove the *shared-weights* blind spot or self-preference.

**Therefore the verdict is CONDITIONAL, not a flat yes/no:**

### Verdict (D-VERDICT)
**A governed, context-isolated sub-agent of the same seat is NOT a valid *sole* independent grader of that seat's work for medium/high-risk changes. It IS an acceptable *contributing* grader for low-risk changes, and a valid *semantic-review-evidence producer* in the solo mode — but only when all of the following conditions hold:**

1. **Anchored to an external, verifiable signal.** The deterministic spine (CI / CE validators / refusal gates / tests / build) is the *primary* counting grader. The sub-agent grade is *secondary* and **never** counts without the spine green. (Huang 2024: introspection without an external oracle is unreliable.)
2. **Cross-model wherever feasible.** The reviewer sub-agent runs a **different model / family** from the author (Claude-authored → Codex/different-model grader, and vice-versa). This is the single highest-leverage mitigation (Kim 2025; Verga 2024). At solo scale CE typically *has* a second harness available, so cross-model is usually achievable even with one human.
3. **Adversarial / red-team grading prompt with authorship obfuscation.** The grader is prompted to *find the flaw*, not to bless; the diff is presented without "I wrote this" framing, stripping the self-recognition cue (Panickssery 2024; https://arxiv.org/abs/2512.05379).
4. **Governed, not ambient.** The venue is a distinct CE reviewer venue with its own **identity, transcript/hash, hook-inheritance, evidence artifact, and fan-in** — exactly the bar `REVIEW_GATE_REVIEWER_VENUE_DESIGN.md` already sets for a non-hidden sub-agent to count. A *hidden background* sub-agent never counts.
5. **Human ratifier for the irreducible set.** High-consequence + irreversible acts (release, root-key/signing, destructive prod, security-control changes, novel/large diffs) require a separate principal / human, per §3.1's irreducible test and ADR-0003 Tier 4.

**Is a separate INSTANCE (different seat) materially better than the same seat's governed context-isolated sub-agent?** **Yes, but the dominant factor is the MODEL, not the seat.** A separate seat running the *same* model carries the same correlated-error / self-preference risk; its only added value over a context-isolated sub-agent of the same model is (a) distinct credential/sandbox (matters for *collusion/forgery* resistance, i.e. ADR-0003's identity/credential axes) and (b) distinct controlling principal (matters for the *drive-both-acts* collusion path). For **correctness independence specifically**, a context-isolated **different-model** sub-agent of the same seat beats a same-model different seat. The two concerns are orthogonal: **ADR-0003's axes defend against forgery/collusion; the model-diversity axis defends against correlated blindness.** A complete grader needs both.

**Failure modes → mitigations (summary table):**

| Failure mode | Root | Mitigation |
|---|---|---|
| Correlated errors (reviewer misses same bug) | shared weights/training dist. | **different model/family** grader; deterministic spine as primary signal; panel/jury at higher tiers |
| Self-preference (rubber-stamp own output) | self-recognition cue | authorship obfuscation; adversarial "find-the-flaw" prompt; cross-model |
| Intrinsic self-critique degrades | no external oracle | anchor every grade to CI/tests/validators (external verifiable signal); never count introspection alone |
| Prompt/context collusion | shared working context | context-isolation (fresh thread, none of author's context) — necessary but not sufficient |
| Same-version enforcer bug defeats author+reviewer | shared CE build / Ring-1 pack | ADR-0003 common-mode guard: fleet version-coherence (#49) — stale/skewed enforcer must refuse to act |
| Single controller drives both acts | shared controlling principal | ADR-0003 axis 4 (non-negotiable at every tier); distinct controller for tier ≥2 |
| Forged approval marker | ambient/loose authority | HMAC approval-capability bound to PR+head+policy+TTL; bounded `reviewer_authority_envelope` (fail-closed) |

---

## 5. Decision — the mode-aware grading & ratification model

CE's grader is a **stack of three counting layers + a ratifier**, configured by mode. The **deterministic spine is always-on and primary at every mode**; the semantic grader's required independence rises with mode and risk tier; the human ratifier's scope shrinks as independence rises but never disappears for the irreducible set.

### The always-on spine (all modes)
The **deterministic correctness spine** — CI, CE validators, the refusal/Ring-1 gates, `--require-carrier` manifest/changelog checks, baseline-diff (zero new failures), tests/build — is the **primary counting grader**. It is the external verifiable signal that every semantic grade is anchored to (§3.3) and the part of review that automation *can* faithfully substitute (§3.2). It is **non-bypassable by the authoring seat** — this is precisely what GitHub branch protection structurally cannot give a solo maintainer (§3.2), and is CE's differentiator. No semantic grade ever counts on a red spine.

### Mode ladder

| Mode | Semantic grader (counting) | Independence basis | Human ratifier scope |
|---|---|---|---|
| **Solo (N=1)** | Spine + **governed cross-model context-isolated reviewer venue** (different model from author; adversarial + authorship-obfuscated prompt; own identity/transcript/evidence/fan-in) | model-diversity + governance + external signal — **not** identity | Ratifies the **irreducible set** only (release, keys/signing, destructive/prod, security-control change, novel/large diff). Low/medium-risk reversible changes may merge on spine+cross-model grade. |
| **Small-team** | Spine + **distinct-principal peer reviewer** at ADR-0003 **Tier ≥2** (separate App/user/controller), cross-model preferred | identity+credential+controller disjoint **and** model-diversity | Ratifies Tier-4 class (release/keys) + escalations. |
| **Fleet** | Spine + Tier ≥2 peer reviewer, **panel/jury (diverse models)** for high-tier, common-mode guards (#49 version-coherence) | full ADR-0003 ladder + diversity panel | Ratifies Tier-4 class + escalations; otherwise governed-autonomous behind the armed wall. |

### What the wall must REQUIRE at each mode
The wall stays **two-layered** (GitHub `APPROVED` necessary + HMAC approval-capability sufficient). The capability's `policy_sha` binds *which mode/policy* minted it. The wall must verify, fail-closed:

1. **Spine green** (deterministic primary grader) — always, every mode. No exceptions, no bypass for the authoring seat.
2. **A semantic-review evidence artifact** from a **distinct governed venue** (`reviewer_venue_kind` ∈ {`visible_lane`, `ratified_subagent_venue`}; hidden background sub-agent = invalid), citing the reviewed head SHA, with transcript hash and an evidence-only verdict.
3. **Independence attestation appropriate to mode** — recorded on the evidence:
   - **Solo:** `reviewer_model != author_model` (cross-model) **+** `authorship_obfuscated: true` **+** `adversarial_prompt: true` **+** context-isolated venue. Identity may equal the author's principal (this is the explicit, ratified relaxation).
   - **Small-team / fleet:** ADR-0003 isolation-domain attestation at the required tier (Tier ≥2 floor; Tier 4 for the irreducible set), distinct controller mandatory, cross-model preferred, panel for high tier.
4. **Risk-tier routing:** the change's risk tier (mutation class × consequence × reversibility) selects the required independence row. **Irreducible set → human ratifier required**, no agent grade substitutes (§3.1 PCI/NIST test).
5. **Head-pinned + TTL:** approval-capability and reviewer-authority envelope bound to one PR + head SHA; stale on head change (already enforced).

### D1 — Why the naive "approver ≠ author identity" guard is rejected
A guard keyed on **identity** alone is both **wrong-axis and unsatisfiable at N=1**. It is **wrong-axis** because identity defends against *forgery/collusion* (ADR-0003) but not against *correlated blindness / self-preference* — a different-identity **same-model** reviewer still shares the author's blind spots (§3.3, Kim 2025). It is **unsatisfiable at N=1** because no second principal exists and GitHub cannot synthesize one (§3.2) — so it would either block the solo agent from shipping or be routed around via admin bypass, giving **false confidence** (§3.1). The right model gates on **(spine-green) + (governed distinct venue) + (mode-appropriate independence: model-diversity at solo, isolation-domain tier at team/fleet) + (risk-tiered human ratifier for the irreducible set)** — not on identity inequality as a standalone predicate.

---

## 6. Consequences

- **Solo users can ship** low/medium-risk reversible work behind an always-on deterministic spine + a governed **cross-model** adversarial reviewer venue, **without a per-PR human gate** — while the irreducible set still escalates to the human. This unblocks the core use case the identity guard would have killed.
- **CE leverages harness-native sub-agents/threading** — but only as a *governed, cross-model, externally-anchored* reviewer venue, never as a hidden self-review. This gives `REVIEW_GATE_REVIEWER_VENUE_DESIGN.md` its missing "ratified_subagent_venue" semantics: identity, transcript, evidence, fan-in, **plus** the cross-model + obfuscation + adversarial conditions this ADR adds.
- **The three-deputy §92 step 5 is closed for grading:** independent-verifier selection = different model + governed venue (attacker must not control it); quorum = panel of diverse models at high tier; consequence threshold = the irreducible set → human.
- **ADR-0003 is extended, not contradicted:** its isolation-domain axes remain the team/fleet independence basis and the forgery/collusion defense at all modes; this ADR adds the **model-diversity axis** as the correlated-blindness defense and the **solo relaxation** (identity may coincide when model-diversity + governance + external signal substitute, per the compensating-controls doctrine §3.1).
- **Cost:** mode detection + risk-tier classification per PR; an independence attestation (incl. `reviewer_model`, obfuscation/adversarial flags) on review evidence; a cross-model reviewer venue must be launchable at solo scale (usually true — two harnesses available). Panel/jury adds compute at high tier only.

---

## 7. Open risks for Operator decision

1. **Solo cross-model availability.** The solo relaxation assumes a *different model* reviewer is launchable on the user's box. If a user truly has only one model/harness, the fallback must be **spine + adversarial obfuscated same-model grade counts only for LOW risk; medium-risk escalates to human**. Confirm this fallback floor. (Risk: a single-model solo user is the weakest configuration — only the spine is truly independent.)
2. **Risk-tier taxonomy.** This ADR asserts a tiering (mutation class × consequence × reversibility) and an "irreducible set." The exact membership of the irreducible set (does it include all `auth`/`crypto`/migration diffs? a LOC threshold?) needs Operator ratification before mechanism.
3. **Panel size / quorum at fleet.** §3.3 supports a diverse jury but warns headcount without diversity can *amplify* bias. Recommend quorum ≥2 distinct models for Tier-4-class only; confirm.
4. **Does the human ratifier ever fully exit?** Recommendation: **no** — keep the human as ratifier for the irreducible set permanently (NIST "without collusion" + PCI key-custody test), even fleet-wide, until/unless strangeLoop changes the bar. Confirm this is the intended permanent floor.
5. **`policy_sha` mode-binding.** The approval-capability `policy_sha` should encode the active mode + tier policy so a solo-minted capability cannot be replayed as a fleet-mode approval. Confirm this binding is in scope for the implementation slice.

---

## 9. Operator decision log (RATIFIED 2026-06-26)

The §4 verdict (D-VERDICT) and §5 model are **ratified**, with the following refinements from the Operator that **supersede** the corresponding §5/§7 text:

- **D9.0 — Organizing axis is DELEGATION LEVEL (CE run-mode), not team size.** The §5 "Solo / small-team / fleet" scale ladder is reframed: the grader stack and human-ratifier scope are a function of **`(run-mode = how much the user delegated) × (risk tier) × (available model diversity)`**, not headcount. CE respects the user's chosen mode and "does its best with what the *user* granted it" (user-choice / CEO-mode-gravity doctrine). Two reference modes:
  - **Dev mode** — user opted *in* to review/grade/ratify. The human covers the irreducible set; agent grades are evidence; spine is primary. (≈ the ADR's solo/small-team rows.)
  - **CEO / strangeLoop mode** — user delegated review itself (no capability or no desire). CE does **not** manufacture a human gate the user declined; it runs spine (always-on, primary) + **maximum available model-diversity**, anchored to external signal. The human-ratifier scope shrinks to what the user explicitly retained.
- **D9.1 — Single-model fallback (resolves §7.1) is MODE-relative.** There is no fixed floor independent of mode. Dev mode → leverage the opted-in human for medium+/irreducible. strangeLoop → spine + best-available diversity, no synthesized human gate. The single-model strangeLoop user is acknowledged as the weakest config (only the spine is truly independent) and CE must be transparent that it is grading at spine-only strength.
- **D9.2 — Irreducible set (resolves §7.2) is MODE-relative, not a fixed list.** Membership × who-ratifies is parameterized by the user's mode/grant: in dev mode the human covers the high-consequence/irreversible classes (release, keys/signing/branch-protection/`.claude`+launcher, destructive/prod/migration, novel/large diffs); in strangeLoop the user may have delegated some/all of these and CE does its best within the grant. The concrete per-mode membership is an implementation-config artifact, not hardcoded.
- **D9.3 — Sequencing (resolves "apply now vs wait"): RATIFY NOW, BUILD SPINE-FIRST, HOLD AUTONOMOUS LIVE-MERGE behind the contained controller.** Build now (additive safety only): the always-on deterministic spine as primary grader, the mode-parameterization + independence attestation on review *evidence*, interim no-controller-self-approval discipline. **HELD until the contained controller lands:** un-stubbing the privileged-action broker for autonomous merge (removes the controller's ambient dual-credential). Rationale: the spine can only *add* gates, never remove a human checkpoint, so it cannot break things in the dangerous direction; the only thing that could is autonomous actuation, which waits for containment (Operator's top priority).
- **D9.4 — Human ratifier exit (resolves §7.4): ENDGAME, not permanent.** Full agent-autonomy of the irreducible set is the explicit endgame (industry-named by Anthropic, Cursor, Steinberger/OpenClaw; none yet met). It is **not** a permanent floor — it is gated on demonstrated maturity (a bar to be defined), and the current/near-term posture keeps the human in the irreducible set. Reframes §7.4's "no, permanent" recommendation to "current posture; retire on a demonstrated-maturity bar."
- **D9.5 — `policy_sha` mode-binding (§7.3, §7.5): CONFIRMED in scope** — the approval-capability `policy_sha` must encode active mode + tier policy so a permissive-mode capability cannot be replayed as a stricter-mode approval. Panel quorum (§7.3) deferred to the fleet-mode implementation slice.

## 8. Non-ratification statement

This ADR records a proposed design and its research basis. It ratifies no authority, mints no envelope, changes no `.claude/**`/launcher/branch-protection surface, and enables no autonomy by itself. Implementation is a separate Source-ratified slice with an explicit path manifest and tests (per `REVIEW_GATE_REVIEWER_VENUE_DESIGN.md` §10 fixtures-first).

---

## Sources

**SoD / four-eyes:** NIST SP 800-53 AC-5 (https://csf.tools/reference/nist-sp-800-53/r5/ac/ac-5/) · ISACA SoD practical experience (https://www.isaca.org/resources/isaca-journal/issues/2016/volume-3/implementing-segregation-of-duties-a-practical-experience-based-on-best-practices) · SOC 2 CC8 (https://www.designcs.net/soc-2-cc8-common-criteria-related-to-change-management/) · SOC 2 catch-22 (https://warrenaverett.com/insights/soc-2-catch-22) · PCI dual control/split knowledge (https://kirkpatrickprice.com/video/pci-requirement-3-6-6-using-split-knowledge-dual-control/) · IAM SoD for non-human identities (https://nhimg.org/articles/segregation-of-duties-vs-separation-of-duties-in-iam-governance/) · Wikipedia SoD (https://en.wikipedia.org/wiki/Separation_of_duties).

**Policy-as-code / gates:** GitHub rulesets available rules (https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets) · creating rulesets / bypass (https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository) · CODEOWNERS (https://docs.github.com/articles/about-code-owners) · OPA K8s (https://www.openpolicyagent.org/docs/kubernetes) · Gatekeeper (https://open-policy-agent.github.io/gatekeeper/website/docs/constrainttemplates/) · shift-left limits (https://securityboulevard.com/2026/03/shift-left-has-shifted-wrong-why-appsec-teams-not-developers-must-lead-security-in-the-age-of-ai-coding/) · Swarmia humans-still-review (https://www.swarmia.com/blog/should-humans-still-review-code/).

**LLM-as-judge / independence:** Kim et al. 2025 Correlated Errors (https://arxiv.org/html/2506.07962v1) · Panickssery et al. 2024 self-recognition/self-preference (https://arxiv.org/abs/2404.13076) · Wataoka et al. 2024 self-preference bias (https://arxiv.org/abs/2410.21819) · Huang et al. 2024 cannot self-correct reasoning (https://arxiv.org/abs/2310.01798) · Zheng et al. 2023 LLM-as-judge (https://arxiv.org/abs/2306.05685) · Verga et al. 2024 juries/PoLL (https://arxiv.org/abs/2404.18796) · Madaan 2023 Self-Refine (https://arxiv.org/abs/2303.17651) · Shinn 2023 Reflexion (https://arxiv.org/abs/2303.11366) · Zhuge 2024 Agent-as-a-Judge (https://arxiv.org/abs/2410.10934) · authorship-obfuscation mitigation (https://arxiv.org/abs/2512.05379).

**CE ground truth:** ce-ops `ADR-0003-reviewer-independence-isolation-domain.md` · `ADR-0004-mandatory-containment.md` · `designs/DESIGN_THREE_DEPUTY_GOVERNANCE_20260624.md` · `specs/v2/adrs/ADR-V2-009-reviewer-venue-authority.md` · `docs/operations/REVIEW_GATE_REVIEWER_VENUE_DESIGN.md` · `docs/operations/REVIEWER_VENUE_AUTHORITY.md` · `docs/operations/REVIEWER_TRIAGE.md` · `validators/creator_engine_validator/forge/approval_capability.py` · `validators/creator_engine_validator/checks/reviewer_authority_envelope.py` · `validators/creator_engine_validator/forge/integrator_belt.py` · `validators/creator_engine_validator/hook_check.py`.
