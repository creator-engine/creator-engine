# Independent Verification Organ for the CE dark factory

**Research date:** 2026-07-10  
**Question:** How should Creator Engine independently detect the gap between a decision, a merged change, and the real-world state it was meant to create?

## Executive summary

CE's recent incidents are not primarily code-review failures. They are *state-reconciliation* failures: a controller's legitimate evidence that it drove a ticket, reviewed a PR, or saw a merge was accepted as evidence that the intended program outcome occurred. The four examples in the brief have the same shape: a claim was terminal in one system of record while required evidence was absent in another. The merged-but-not-deployed sibling is the same error across the source/host boundary.

Leading organizations do not solve that with a larger code-review team. They use a mix of (1) a distinct operational/reliability perspective, (2) explicit checklists and objective triggers, (3) evidence-bearing release/deployment gates, and (4) recurring outcome inspection. Google SRE's PRR and Launch Coordination Engineering (LCE), AWS ORRs informed by Correction of Error (COE), Meta's production-engineering/SLO systems, and Netflix's automated canary decisions all separate at least some verification signal from the builder's assertion. At the regulated end, NASA IV&V makes technical, managerial, and financial independence explicit. The common lesson is not "add a QA department"; it is "give a different organ a different evidence set and a non-circular mandate."

The recommended CE mechanism is a **Program Verification agent-organ (PV)**: a read-only, proposal-only agent class, analogous in organizational position to the proposed DevOps agent but intentionally not an executor. Deterministic event triggers create verification cases for ticket closures, ratification records, release/merge events, and deployment events. PV reconciles forge state, the SSOT identity/authority registry, ratification and decision records, the brain ledger, and host/systemd probes. It can only emit an evidence packet and propose an `AWAITING` queue entry or ticket; it cannot close/reopen issues, deploy, merge, change the registry, or bless its own finding.

This is deliberately narrower than independent V&V and narrower than a general QA org. Routine reconciliation should be cheap and deterministic; a strong reasoning model should be reserved for ambiguous intent-to-evidence mapping and adversarial investigation. Its first acceptance test is historical: with snapshots taken before remediation, it must independently identify all four named believed-done incidents and the merged-not-deployed sibling, with the precise missing evidence and no mutation. If it cannot do that, it has not earned live authority.

The strongest objection is valid: externalized QA and handoff-heavy approval bureaucracies slow delivery, and Microsoft retired its dedicated SDET role as fast web teams moved ownership of test automation into engineering. PV therefore must neither test every diff nor block routine delivery. It is an asynchronous, evidence-reconciliation organ, risk-tiered and proposal-only. It complements builder-owned tests and code review; it does not replace them.

## Q1. Industry canon: structural separation at the program level

### Google: SRE as an operational counterparty, with PRR, LCE, and scored commitments

Google's Production Readiness Review is explicitly an SRE engagement that assesses whether a service meets production-setup and operational-readiness standards before SRE takes responsibility for it. The SRE team maintains a service-specific checklist and analyzes the service's architecture, monitoring, capacity, change management, and operational preparation; this is a distinct production perspective, not a pull-request review. [Google SRE, "Evolving the SRE Engagement Model"](https://sre.google/sre-book/evolving-sre-engagement-model/) supports both the PRR purpose and the fact that SRE reviewers conduct it.

LCE is a related launch-review function. Google's launch material says an LCE uses the launch checklist to assess the launch and give the launching team action items; the checklist spans architecture/dependencies, capacity, testing, reliability, and operations. [Google SRE, "Reliable Product Launches"](https://sre.google/sre-book/reliable-product-launches/) and its [original launch checklist](https://sre.google/sre-book/launch-checklist/) support this. The transferable mechanism is an independently maintained, evidence-oriented checklist at a lifecycle boundary—not an assertion by the shipping team that it is ready.

Google also uses postmortem triggers that are defined before an event and expects formal follow-up actions after significant events. Its SRE book lists objective triggers such as user-visible impact, data loss, rollback, and monitoring failure, and describes a postmortem as a record containing follow-up actions to prevent recurrence. [Google SRE, "Postmortem Culture"](https://sre.google/sre-book/postmortem-culture/) supports that trigger-and-follow-up discipline. This is directly relevant to CE: a detected false closure should become a data source for improving the verifier's rules rather than a reason to blame the controller.

At the program layer, OKR grading provides a cadence for reconciling commitments to measured outcomes. Google's former re:Work material is no longer a stable primary page; a widely circulated Google OKR playbook records the 0–1 scoring model and defines key results as measurable evidence rather than activities. [Google OKR Playbook](https://assets.ctfassets.net/mu244eycyvsr/3T7YZSUplO5Wt2UMpHKBoF/70ca14665b9735a7f7cff5f4c95c34df/WhatMatters.com_-_Google_s_OKR_Playbook.pdf). This is useful for CE only if a "committed" result has independently observable completion criteria. OKR scoring alone is not independence: it can still be self-reported.

**Ported lesson.** PV should be an SRE/LCE-like counterparty for program state: an outside-in checklist, deterministic triggers, and published evidence. It must not become an expensive manual PRR for every change; Google itself notes that late PRRs can serialize work and evolve toward earlier, scalable platform engagement. [Google SRE, "Evolving the SRE Engagement Model"](https://sre.google/sre-book/evolving-sre-engagement-model/).

### Amazon: ORR and COE turn incidents into reusable, lifecycle-wide inspection

AWS documents ORR as a scalable, self-service mechanism for a decentralized organization: it turns learning from operational incidents and COE analyses into curated questions, and teams use the checklist through a service's lifecycle. [AWS, "Operational Readiness Reviews"](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/wa-operational-readiness-reviews.html). AWS further recommends an ORR at least before general availability, with stakeholders from security, operations, and development, and says it should be rerun throughout the lifecycle. [AWS Well-Architected, OPS07-BP02](https://docs.aws.amazon.com/wellarchitected/2022-03-31/framework/ops_ready_to_support_const_orr.html).

AWS's COE mechanism is more than a narrative postmortem: it identifies and *tracks* corrective actions, and AWS recommends review by the owning and other teams, with high-impact COEs reviewed in operational meetings. [AWS Cloud Operations Blog, "Why you should develop a COE"](https://aws.amazon.com/blogs/mt/why-you-should-develop-a-correction-of-error-coe/) and [AWS Well-Architected, "Correction of Error"](https://wa.aws.amazon.com/wellarchitected/2020-07-02T19-33-23/wat.concept.coe.en.html) support those claims.

This is not evidence that Amazon has a single independent, companywide QA department. Its public material instead emphasizes decentralized service ownership and self-service ORRs. That distinction matters: the CE analogue is an independent **inspection mechanism** that consumes evidence and proposes action, not a centralized team that owns all testing.

**Ported lesson.** Use every confirmed false-done incident to add or revise a small, outcome-specific PV control (for example, a retirement claim must be paired with a dependency scan and docs-state check). Keep controls templated, risk-specific, and lifecycle-aware so they do not create an unbounded checklist.

### Microsoft: a warning against separating routine testing from ownership

Microsoft historically pioneered the SDET model, which put programmatic testing and test infrastructure in a distinct engineering specialty. Public first-party material from the period describes SDETs as a test role influencing design and implementation. [Microsoft .NET Blog, "Looking for strong SDETs"](https://devblogs.microsoft.com/dotnet/looking-for-strong-sdets-to-help-with-web-development-tools-testing/). In 2014 Microsoft restructured; the company contemporaneously announced a broad simplification/restructuring, but its press release does not specifically document the SDET decision. [Microsoft, July 2014 restructuring announcement](https://news.microsoft.com/source/2014/07/17/microsoft-announces-steps-to-simplify-organization-and-align-devices-strategy/).

The detailed account of retirement of the SDET title and replacement with a unified software-engineer role is therefore best treated as informed secondary evidence, not an official Microsoft policy record. The account says fast web teams put test ownership, integration tests, and monitoring into engineering because handoff to a separate test role delayed frequent shipping. [Gergely Orosz, "How Microsoft does QA"](https://blog.pragmaticengineer.com/how-microsoft-does-qa/). A Microsoft Research study published in 2014 likewise found that test ownership/team structure affects test-run reliability, effectiveness, development speed, and developer satisfaction. [Microsoft Research, "The Impact of Test Ownership and Team Structure"](https://www.microsoft.com/en-us/research/publication/the-impact-of-test-ownership-and-team-structure-on-the-reliability-and-effectiveness-of-quality-test-runs/).

**Ported lesson.** CE must retain builder ownership of unit, integration, end-to-end, deployment, and code-review quality. PV must not take those tests away or create a ticket handoff before every merge. Its independent work is program-level reconciliation across systems—something a feature author and driving controller are structurally unlikely to perform against themselves.

### Meta and Netflix: ownership remains local; verification is automated and operational

Meta does not present a classic QA-department model in its public engineering material. It has Production Engineering, a hybrid software/systems function that partners with product engineering to champion production reliability, scalability, performance, and security. [Meta, "Production Engineering"](https://engineering.fb.com/2014/08/08/production-engineering/). It also uses centralized reliability evidence: its SLICK SLO store makes service objectives discoverable, retains high-granularity data, produces periodic reports, and has detected regressions that prompted review and repair. [Meta, "SLICK: Adopting SLOs"](https://engineering.fb.com/2021/12/13/production-engineering/slick/). Meta's Fix Fast system aggregates automated tests, static analysis, performance logs, crash data, bug reports, and production alarms, then routes regressions to ownership. [Meta, "Fix Fast"](https://engineering.fb.com/2021/02/17/developer-tools/fix-fast/).

Netflix's current engineering-culture page explicitly assigns backend teams the full lifecycle—development, deployment, and operations—and argues that this creates fast feedback loops. [Netflix, "Engineering Culture"](https://sites.google.com/netflix.com/aim/culture). That is the "you build it, you run it" extreme. It is not no verification: Netflix's automated canary analysis compares baseline and canary metrics; its delivery system decides to continue, roll back, or ask for manual intervention. [Netflix TechBlog, "Automated Canary Analysis with Kayenta"](https://medium.com/netflix-techblog/automated-canary-analysis-at-netflix-with-kayenta-3260bc7acc69).

**Ported lesson.** Independent does not require a separate human department. It can mean an evidence source and decision path that the builder cannot simply declare green: SLO/metric truth, deterministic regression signals, and automated canary/rollback. CE should preserve direct owner responsibility while ensuring PV reads evidence outside the controller's narrative.

### Traditional and regulated practice: independence is a property, not a job title

IEEE 1012 is the canonical software/system V&V standard, but its licensed text should not be paraphrased beyond what can be verified. NASA's public implementation is a strong practical analogue: it calls IV&V an objective examination of safety- and mission-critical software processes and products, and defines **technical, managerial, and financial independence** as its key parameters. [NASA Software Engineering Handbook, SWE-141](https://swehb.nasa.gov/spaces/SWEHBVB/pages/32604595/SWE-141%2B-%2BSoftware%2BIndependent%2BVerification%2Band%2BValidation). NASA's newer guidance is explicit that an IV&V provider must not be part of a company associated with the development organization where that independence is required. [NASA SWE-141, Version D](https://swehb.nasa.gov/spaces/SWEHBVD/pages/102695499/SWE-141%2B-%2BSoftware%2BIndependent%2BVerification%2Band%2BValidation).

For financial-control environments, the safe claim is narrower than common shorthand: SOX requires effective internal control over financial reporting and an auditor obtains evidence about material weaknesses; it does **not** itself mandate a named "CAB." [PCAOB AS 2201](https://pcaobus.org/oversight/standards/auditing-standards/details/AS2201). A Change/Configuration Control Board is a common implementation pattern. NIST's configuration-change control calls for review/approval or disapproval, implementation/documentation of approved changes, and monitoring/review of change activity; its glossary defines a CCB. [NIST SP 800-171 Rev. 3](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/800-171r3/NIST.SP.800-171r3.html) and [NIST CCB glossary](https://csrc.nist.gov/glossary/term/CCB). The portable principle is separation of request/implementation/inspection evidence—not ceremonial meetings.

In aviation, the FAA identifies DO-178C/ED-12C as a current standard relied on by development teams and certification authorities to obtain the confidence needed for aviation safety. [FAA, "Abstraction Layer Information"](https://www.faa.gov/aircraft/air_cert/design_approvals/air_software/abstraction_layer). In medical-device software, IEC 62304 establishes lifecycle requirements, while FDA guidance requires validation evidence tied to user needs, intended use, and risk; FDA also discusses independent third-party certification/audit in the off-the-shelf-tool context. [IEC 62304 overview](https://www.iso.org/cms/live/live/en/sites/isoorg/contents/data/standard/03/84/38421.html?browse=tc) and [FDA General Principles of Software Validation](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-principles-software-validation). Do **not** claim that IEC 62304 creates a universal separate verification organization; the public standard overview supports lifecycle rigor, while the degree of independent verification is risk/context dependent.

**Ported lesson.** CE needs independence sufficient for its actual risk: separate model/run authority, a read-only evidence surface, and no self-disposal of findings. It does not need safety-certification bureaucracy or a human board for ordinary changes.

### DORA: the boundary condition

DORA's 2018 research found low performers were materially more likely than elite performers to outsource functions including application development, operations, or testing/QA, and cautioned that functional outsourcing is rarely adopted by elite performers. [DORA 2018 State of DevOps Report, p. 44](https://dora.dev/research/2018/dora-report/2018-dora-accelerate-state-of-devops-report.pdf). This is not proof that every form of independent assessment is harmful; it is strong evidence against a handoff-heavy external QA queue. PV is viable only if it is lightweight, integrated through event evidence, and reserved for cross-system program truth rather than routine functional testing.

## Q2. The two failure classes

### (a) "Ratified/decided" → actually landed

This class fails when a decision record becomes its own proof of execution. The relevant industry mechanisms are:

| Mechanism | What it verifies | CE translation |
|---|---|---|
| Google-style OKR scoring | Measurable result at a cadence, not mere activity | Every ratification/epic needs one or more independently queryable completion predicates and a due/review cadence. |
| LCE/launch checklist | Readiness evidence before a declared lifecycle transition | A retirement, containment, or policy decision has a checklist of required code/docs/registry/runtime evidence. |
| AWS ORR + COE action tracking | Whether corrective commitments are still open and lessons become controls | PV opens a finding when a decision lacks its expected evidence and proposes a new control after a confirmed escape. |
| SAFe PI objectives | Objectives are planned, committed/weighted, and assessed at a program increment boundary | A CE initiative has explicit objective IDs, owner, evidence contract, and end-of-arc reconciliation—not just a closed slice ticket. |
| Change control / CAB | Requested change, approved change, implementation record, and monitored result are distinct artifacts | PV reconciles these four artifacts without becoming their approver. |

SAFe's public guidance describes PI objectives as business/technical goals created during PI planning, used for alignment and program predictability. [Scaled Agile Framework, "PI Objectives"](https://framework.scaledagile.com/pi-objectives/). This is useful as a planning-and-inspection pattern, not as a reason to adopt SAFe wholesale.

The CE rule should be: **a decision is not terminal until its evidence contract is satisfied.** A contract is a small typed record: decision/ratification ID; intended state; authoritative evidence sources; owner; deadline; acceptance predicate; and exceptions. Examples:

* `retire(spec-kit)`: no live docs references, no active workflow dependency, replacement/archival record present.
* `ratify(dev-1 containment)`: approved implementation ticket *and* landed implementation revision *and* target host/container probe attesting the desired run mode.
* `close(ce-ops#467)`: all declared slices/linked deliverables are independently resolved or an explicit scoped exception remains open; a slice-1 merge alone is not a closure predicate.

PV should run on the decision/ratification event, on linked-ticket closure, and on an age/deadline sweep. A deterministic reconciler can establish missing links and absent facts; an agent is needed only to interpret a decision's prose, distinguish a legitimate exception from an orphan, and write a bounded proposal.

### (b) "Merged" → actually deployed/live

Merge verifies source-control integration. It says nothing, by itself, about artifact construction, target selection, rollout, process activation, user traffic, or post-deploy health. This needs a deployment evidence chain:

`source revision → build/attestation → immutable artifact → deployment event → target/host observation → health/SLO evidence → release disposition`.

SLSA provenance specifies a verifiable record of where/how an artifact was built and the source material used. [SLSA v1.0 Provenance](https://slsa.dev/spec/v1.0/provenance). It is necessary for source-to-artifact traceability, but it does **not** prove the artifact is live on the intended host; CE needs the last four links separately.

Continuous verification products make that distinction explicit. Harness describes its Verify step as a deployment-pipeline step that consults logs/APM data, identifies changed instances, detects anomalies, and can trigger rollback. [Harness, "Verify Overview"](https://developer.harness.io/3k-docs/continuous-delivery/verify/verify-deployments-with-the-verify-step/). Netflix's Kayenta similarly compares canary and baseline behavior and lets the delivery system promote, abort, or require manual intervention. [Netflix TechBlog, "Automated Canary Analysis"](https://medium.com/netflix-techblog/automated-canary-analysis-at-netflix-with-kayenta-3260bc7acc69). These are verification **after** source integration and during/after delivery.

For CE, a deploy event must carry a target identity and expected observable version/configuration. PV then queries—not trusts—the target: for a systemd deployment, the unit's enabled/active state, `ExecStart`/Environment or artifact digest, process/container image digest, deployment timestamp, and a bounded health probe. For a broker/runtime/config deployment, it checks the running configuration hash and the intended socket/service behavior. The brain ledger should record the association among decision, PR/merge SHA, artifact, target, observation time, and verifier result. An absent deploy event or mismatched probe is a finding, never silently converted into "probably deployed."

## Q3. Peter Steinberger / OpenClaw

### What the public material establishes

The public [OpenClaw ecosystem](https://openclaw.ai/ecosystem) describes roughly 70 projects around an assistant repo. Relevant entries include ClawSweeper (weekly issue/PR triage), Crabbox (disposable sandboxes that sync a diff and run a suite), Crabfleet (mission control for agent runs), clawpatch (review/patch/land PRs), Kova (runtime validation lab), and a releases project described as a release-automation/evidence ledger. The same page describes a large collection of crawlers and agent tooling. These are useful building blocks: triage, test execution, fleet observation, and release evidence.

The public catalog does **not** describe an independent, program-level verification organ that reconciles a ratified decision, issue closure, merge, target deployment, and observed live state, nor does it describe a proposal-only authority boundary for such an organ. ClawSweeper's stated function—telling maintainers what to close and why—is triage, not evidence-based completion verification. The catalog's release evidence ledger is promising infrastructure but is not, from the published description, an independent adjudicator. This is an absence finding limited to the public ecosystem pages reviewed, not a claim about undisclosed internal tooling.

The question's `AutoReview` appears to be a code-level, pre-land loop rather than a public program-verification product. I could not corroborate a first-party OpenClaw tool page specifying its architecture or independence boundary. A secondary report of Steinberger's shared workflow describes `autoreview`, live tests, and a temporary progress file before commit; that supports the narrower characterization but is not sufficient to establish internal governance design. [Digg's report of the public posts](https://digg.com/tech/p5vldbh4). The OpenClaw vision itself emphasizes focused PRs and explicitly notes review cost, again at the code-contribution rather than program-completion layer. [OpenClaw VISION.md](https://github.com/openclaw/openclaw/blob/main/VISION.md).

### Conclusion and boundary

On public evidence, OpenClaw rents tools for self-verification, test execution, review, triage, and release evidence, but no published independent organ for believed-done drift. That is unsurprising for a personal/maintainer-centered trust domain: the operator/maintainer can inspect, steer, and ratify directly. It is not portable to CE's dark-factory program layer, where a controller's own progress narrative has repeatedly become the accepted ground truth. CE can rent the *components* (evidence ledger, sandbox/live test, fleet observation, triage) but must invent/adapt the missing cross-system independent reconciliation role.

## Q4. CE-native proposal: Program Verification agent-organ (PV)

### Charter and non-goals

**Charter:** detect material divergence between a declared program outcome and independently observable state; create a cited, reproducible proposal for the existing `AWAITING` queue or a ticket.

**Not PV's job:** author code, amend docs, change the SSOT, reopen/close tickets, approve/merge PRs, deploy/restart hosts, alter controller plans, or dispose of its own findings. A finding becomes actionable only through the existing controller/Operator governance path.

PV is therefore an **agent-organ**, not a daemon-only rule: deterministic triggers and collectors decide *when* to inspect, while agent reasoning determines whether semantically related evidence satisfies the actual decision and explains the gap. It is also not a general QA organ. Feature tests stay with builders and existing CI/reviewer mechanisms.

### Independence contract

| Dimension | Required CE rule | Rented mechanism |
|---|---|---|
| Technical | Separate read-only execution identity; evidence fetched directly from authoritative APIs/probes, not supplied as a controller summary; separate prompt/context from the driving controller. | NASA IV&V technical independence; Meta's centralized SLO evidence. |
| Managerial | PV does not report readiness to the controller it is checking and cannot be used by that controller to self-clear a finding; results enter a queue visible to an independent disposer. | NASA IV&V managerial independence; separation of duties/change control. |
| Authority | Proposal-only token: no forge, registry, host, deploy, or queue-disposal mutation. | NIST change-control distinction between review/approval/implementation/monitoring; AWS COE action tracking. |
| Evidence | Every claim identifies source, query/probe, timestamp, target identity, and confidence/ambiguity. | SLSA provenance plus Harness/Kayenta observable deployment verification. |
| Learning | Confirmed escapes add a small control or improve a predicate; false positives are measured and pruned. | AWS ORR derived from COE; Google postmortem follow-up. |

PV must not share the controller's task-local scratchpad as its evidence source. It may read public/authorized forge state and approved internal read surfaces, but the controller's prose is only a lead, never proof.

### Deterministic triggers and case types

| Trigger | Case PV creates | Required reconciliation |
|---|---|---|
| Ticket closed, milestone/epic closed, or scope label removed | `commitment-closure` | Find acceptance contract, linked slices/deliverables, and independent completion evidence. Flag a closed parent with open/missing required work. |
| Ratification/ADR/decision record becomes effective | `decision-landing` | Resolve decision ID to implementation ticket(s), required registry/docs/code/host predicates, owner, and deadline. Re-check on deadline and status changes. |
| PR merged or release tag created | `release-chain` | Map revision to artifact/provenance and declared target(s); distinguish merge, build, staged, deployed, and verified-live. |
| Deploy/redeploy/configuration event | `live-state` | Query the target and health source; compare unit/image/config digest, active/enabled state, and bounded health/SLO signal with expected state. |
| Scheduled reconciliation (daily for open commitments; periodic for critical live state) | `drift-sweep` | Detect aged decisions without a landing chain, targets whose observed state drifts from SSOT/ledger, and release records with no live observation. |
| Incident/postmortem/COE equivalent accepted | `control-learning` | Check whether corrective action evidence is present and propose one narrowly scoped verifier-control update. |

Triggers create cases deterministically and idempotently with a correlation key (`decision-or-ticket + target + intended-state hash`). The agent cannot drop a case; it may classify it as `satisfied`, `ambiguous`, `divergent`, or `not-applicable-with-evidence`. `not-applicable` requires a cited, durable exception record and expiry.

### Evidence sources PV must read

1. **Forge state:** issue/epic and PR states, timelines, linked work, merge/head SHA, checks, release tags, workflow/deployment records, and issue closure reasons. This is the commitment and source-integration truth.
2. **SSOT registry:** canonical identities, target topology, ownership/authority/run-mode declarations, and the expected host/service relationship. A controller note cannot override this source.
3. **Ratification/decision records and implementation contracts:** the actual approved outcome, acceptance predicates, scope/exception notes, and deadlines. PV must preserve the distinction between a proposed epic and a ratified direction.
4. **Systemd/host/container probes:** direct read-only evidence of enabled/active units, process/container/image/configuration digest, sockets/listeners, service health, and deployment timestamp from the named target. This is required for merged-not-deployed detection.
5. **Artifact/provenance and deployment ledger:** build-to-source association, signed artifact/version, deployment target, and rollout record. Provenance stops at the artifact; probes establish live state.
6. **Brain ledger:** the existing CE correlation layer for decisions, tickets, artifacts, targets, observations, and prior PV cases. It should be append-only/auditable for PV reads, never PV-mutated directly.
7. **Docs/dependency/manifest evidence for retirement:** full-text references, runtime/package manifests, generated docs, and registered workflow dependencies. This is what would have caught spec-kit and `.hermes` false retirement.

The first six are mandatory for relevant case types. The seventh is mandatory for retirement/decommission claims. A missing authoritative source is itself `ambiguous` or `divergent`; PV must not invent a passing substitute.

### Output and disposal

PV emits a signed/attributed, immutable evidence packet containing:

* correlation ID, trigger, intended state, scope, severity, and time window;
* exact evidence pointers/queries and observations, including negative evidence;
* classification: `satisfied`, `ambiguous`, `divergent`, or `control-gap`;
* an explanation that separates facts from inference;
* a **proposal only**: enqueue an `AWAITING` item, propose a ticket, request an owner/evidence contract, or request human/independent-controller disposition;
* a deduplication key and recommended recheck condition.

Only the queue/ticket controller with normal authority can create or mutate the proposed item. PV can publish a finding to an append-only findings surface and notify; it cannot execute the remedy. This preserves the author/approver and verifier/disposer walls.

### Model tier and routing

* **Collector and rules:** deterministic, inexpensive code/query jobs. They parse events, follow links, calculate stale deadlines, compare known digests, and create cases. No model is needed for a simple `inactive unit` or `unmerged implementation PR` result.
* **Routine adjudication:** the normal Codex/GPT routing tier used for CE agent work, with a bounded tool set and explicit evidence-first prompt. It handles straightforward semantic mapping and produces a concise finding.
* **Adversarial/ambiguous adjudication:** a high-reasoning Codex tier, separate from the driving controller's context, for decisions with prose ambiguity, cross-repository scope, conflicting evidence, or a proposed false-positive dismissal. It must attempt to falsify the apparent completion claim.
* **Human/Operator escalation:** only for ratification ambiguity, a missing authority boundary, a policy exception, or a finding whose remediation changes the agreed program scope. PV never resolves those by assumption.

This follows CE's stated routing direction—substantive work through the Codex fleet—while conserving expensive reasoning for judgment. The decisive control is not model brand; it is independent context, source access, and absence of mutation authority.

### Acceptance test: prove PV against history before production use

Create a read-only historical fixture from pre-remediation forge/registry/host/ledger snapshots. Seed it with the original decision/closure/merge events and make it impossible for PV to read later explanatory discussion or remediation commits. The expected results are:

| Historical scenario | PV trigger | Required finding |
|---|---|---|
| spec-kit retirement asserted/closed while required documentation cuts never occurred | retirement/closure | `divergent`: decision's docs predicate unsatisfied; cite still-live docs references or absent required deletion/archival evidence. |
| `.hermes` retirement asserted while seven runtime dependencies remained | retirement/closure | `divergent`: dependency predicate unsatisfied; list each independent runtime reference and source. |
| ce-ops#467 closed after a "slice 1" PR while remaining scope was orphaned | parent-ticket closure | `divergent`: closed parent has unresolved/missing required slices or no exception that narrows scope. |
| ce-ops#408 containment ratified/ticketed but never executed | ratification deadline / drift sweep | `divergent`: decision chain lacks landed implementation and/or the target's desired run-mode evidence. |
| gate-redeploy script merged but never deployed to the required host | merge/release age threshold | `divergent`: merge/provenance exists but no matching deploy event and/or target probe is old/mismatched. |

**Pass criteria:** all five findings are produced without a human-supplied diagnosis; each names the missing predicate and at least one direct evidence pointer; duplicate triggers yield one correlation ID; PV makes zero external mutations; and a seeded legitimate exception becomes `not-applicable-with-evidence`, not a false alarm. Measure recall first (5/5 known escapes), then precision on a control set of genuinely completed decisions/releases. Before live use, run a shadow period where PV creates findings but none affect workflow; publish false-positive rate, median time to detection, and percentage of findings with a complete evidence chain.

This test intentionally demands the sibling merged-not-deployed case in addition to the four brief incidents. A verifier that only sees forge state can pass none of the important deployment boundary.

## Adversarial pass: strongest case against a dedicated organ

The best argument against PV is that it recreates the slow, adversarial QA handoff that high-performing delivery organizations have deliberately dismantled. DORA's functional-outsourcing result and the Microsoft SDET transition both warn that moving quality away from builders can delay feedback, reduce ownership, and turn passing a gate into a bureaucratic objective. An LLM verifier also creates new risks: hallucinated dependency links, false confidence from weak evidence, noisy findings that operators ignore, and a second system whose "done" status can itself drift.

Those arguments defeat a proposal for a universal QA queue or a verifier with blocking/repair power. They do **not** defeat the narrower proposal, provided CE enforces the following limits:

1. **No routine code-testing handoff.** Builders still own tests, CI, review, and deploy safety; PV only reconciles program and live-state claims across systems.
2. **Deterministic first, agent second.** The model never fabricates an observation; every conclusion is anchored in collected evidence. Straight mismatches remain rules, not prose judgment.
3. **Asynchronous and risk-tiered.** Routine PRs are not blocked. PV runs after meaningful events and periodically; only an independently governed policy may make specific high-risk findings release-blocking later.
4. **Proposal-only.** PV cannot correct the system, dispose of its own work, or become a shadow controller. This prevents a new all-powerful automation path.
5. **Measured sunset/repair discipline.** Track recall on known escapes, precision, time-to-detection, duplicate rate, and operator disposition. Retire rules that generate noise; strengthen rules after confirmed escapes, as ORR/COE practice suggests.

There is a residual cost: CE will spend tokens and attention checking work that turns out to be complete. That cost is justified only for program commitments, retirements, authority/containment decisions, production deploys, and other cross-system claims where the recent false-done rate is demonstrably nontrivial. For low-risk, easily observable work, PV should not run or should use a deterministic check only. This is a scoped independent evidence organ, not a claim that more oversight always improves delivery.

## Sources

Primary and official sources are preferred below; the Microsoft SDET transition and the AutoReview characterization are explicitly marked secondary because an official source with the required detail was not found.

* [Google SRE: Evolving the SRE Engagement Model / PRR](https://sre.google/sre-book/evolving-sre-engagement-model/) — PRR purpose, SRE checklist, LCE consultation, and the scaling cost of late review.
* [Google SRE: Reliable Product Launches](https://sre.google/sre-book/reliable-product-launches/) and [Launch Checklist](https://sre.google/sre-book/launch-checklist/) — LCE launch checklist and evidence categories.
* [Google SRE: Postmortem Culture](https://sre.google/sre-book/postmortem-culture/) — predefined triggers and follow-up actions.
* [Google OKR Playbook](https://assets.ctfassets.net/mu244eycyvsr/3T7YZSUplO5Wt2UMpHKBoF/70ca14665b9735a7f7cff5f4c95c34df/WhatMatters.com_-_Google_s_OKR_Playbook.pdf) — outcome-oriented key results and scoring; provenance is a circulated Google playbook, not a live official re:Work page.
* [AWS ORR](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/wa-operational-readiness-reviews.html), [AWS ORR best practice](https://docs.aws.amazon.com/wellarchitected/2022-03-31/framework/ops_ready_to_support_const_orr.html), and [AWS COE](https://aws.amazon.com/blogs/mt/why-you-should-develop-a-correction-of-error-coe/) — lifecycle checklist and corrective-action tracking.
* [Microsoft SDET role, first-party historical example](https://devblogs.microsoft.com/dotnet/looking-for-strong-sdets-to-help-with-web-development-tools-testing/) and [Microsoft Research on test ownership](https://www.microsoft.com/en-us/research/publication/the-impact-of-test-ownership-and-team-structure-on-the-reliability-and-effectiveness-of-quality-test-runs/) — historical context and evidence that ownership structure affects outcomes.
* [Secondary: Orosz on Microsoft QA/SDET retirement](https://blog.pragmaticengineer.com/how-microsoft-does-qa/) — detailed 2014 transition account; used with its limitation stated.
* [Meta Production Engineering](https://engineering.fb.com/2014/08/08/production-engineering/), [SLICK](https://engineering.fb.com/2021/12/13/production-engineering/slick/), and [Fix Fast](https://engineering.fb.com/2021/02/17/developer-tools/fix-fast/) — production counterparty, outcome signals, and regression routing.
* [Netflix Engineering Culture](https://sites.google.com/netflix.com/aim/culture) and [Netflix Automated Canary Analysis](https://medium.com/netflix-techblog/automated-canary-analysis-at-netflix-with-kayenta-3260bc7acc69) — lifecycle ownership and automated deployment disposition.
* [NASA SWE-141 IV&V](https://swehb.nasa.gov/spaces/SWEHBVB/pages/32604595/SWE-141%2B-%2BSoftware%2BIndependent%2BVerification%2Band%2BValidation) — objective IV&V and technical/managerial/financial independence.
* [PCAOB AS 2201](https://pcaobus.org/oversight/standards/auditing-standards/details/AS2201) and [NIST SP 800-171r3](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/800-171r3/NIST.SP.800-171r3.html) — internal-control evidence and configuration-change review/implementation/monitoring.
* [FAA on DO-178C](https://www.faa.gov/aircraft/air_cert/design_approvals/air_software/abstraction_layer), [IEC 62304 overview](https://www.iso.org/cms/live/live/en/sites/isoorg/contents/data/standard/03/84/38421.html?browse=tc), and [FDA software validation guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-principles-software-validation) — risk-sensitive regulated lifecycle assurance.
* [DORA 2018 State of DevOps](https://dora.dev/research/2018/dora-report/2018-dora-accelerate-state-of-devops-report.pdf) — functional outsourcing/testing-QA caution.
* [SAFe PI Objectives](https://framework.scaledagile.com/pi-objectives/) — planned program objectives and assessment cadence.
* [SLSA Provenance v1.0](https://slsa.dev/spec/v1.0/provenance) — source/build-to-artifact attestations.
* [Harness Verify Overview](https://developer.harness.io/3k-docs/continuous-delivery/verify/verify-deployments-with-the-verify-step/) — observable post-deploy verification and rollback.
* [OpenClaw ecosystem](https://openclaw.ai/ecosystem) and [OpenClaw vision](https://github.com/openclaw/openclaw/blob/main/VISION.md) — public tools catalog and contribution/review scope.
* [Secondary: report of Steinberger's AutoReview workflow](https://digg.com/tech/p5vldbh4) — used only for the limited code-level AutoReview characterization.

