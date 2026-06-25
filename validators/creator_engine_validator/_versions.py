"""CE version-line taxonomy + the v1↔v3 coexistence boundary (G-3.9).

Single source of truth for *which version line* each module of
``creator_engine_validator`` belongs to. CE v1.0 (the ``ce`` launcher /
lane / PCO / hook coordination runtime) and CE v3.x (the orchestrator /
forge / runner execution runtime) **coexist** on a shared governance base
(the validator engine: the CLI, the check registry, every check, plus
``loader``/``reporting``/``schema``/``environment_guard``/``version`` and the
pure ``runtime_evidence_spine`` substrate).

Directive: ``ce-v1-v3-coexistence-not-deletion`` — v1 is RETAINED; v1 and v3
are independently-operable versions. The boundary is enforced by the
``version_boundary`` check against THIS taxonomy.

Invariant (see ``docs/architecture/VERSION_BOUNDARY.md``):
  * HARD: no ``v1`` module imports a ``v3`` module, or vice-versa. The two
    execution runtimes stay mutually isolated. No exceptions.
  * RATCHET: a ``shared`` (engine/durable-infra) module may import a
    version-specific module ONLY via a baselined, justified entry in
    ``BASELINE_SHARED_TO_VERSION_ALLOWLIST``. New ``shared``→version edges
    fail the check (the allowlist only shrinks).
  * ``shared`` may always be imported by anyone.

All names below are RELATIVE to the ``creator_engine_validator`` package
(e.g. ``"forge.merge"``, ``"checks.mutation_class"``). Any shipped module not
in ``V1_RUNTIME`` or ``V3_RUNTIME`` is ``shared`` by classification; if such a
module couples to a version line it is caught by the RATCHET above, which is
what forces a deliberate decision when new code is added.
"""

from __future__ import annotations

#: This module is part of the shared governance base.
__ce_version_line__ = "shared"

V1 = "v1"
V3 = "v3"
SHARED = "shared"

# --- CE v1.0 coordination/launch runtime surface (RETAINED, frozen-operational) ---
V1_RUNTIME: frozenset[str] = frozenset(
    {
        "__main__",
        "ce_cli",
        # ce-ops#197 PR-3: user-scoped shell profile PATH standardization writer.
        # It is an installer/kernel-adjacent v1 utility; imports no v3 module.
        "ce_profile_path",
        "lane_runtime",
        "launch_runtime",
        "claude_launch_spec",
        "codex_launch_spec",
        "codex_pretooluse",
        "hermes_launch_spec",
        # v3.5-F Q1: the per-seat OS resource-bounding wrap (pure builder +
        # systemd I/O edges) — launch mechanics, sibling of claude_launch_spec.
        # Reads the v3 runtime-policy resource fragment as DATA through the
        # existing policy-read seam (loader.load_yaml); imports no v3 module.
        "resource_bound_spec",
        # ce-ops#128 SUB-C: visible composition bridge from the v1 launch
        # surfaces to the selected RunnerBackend. It is launch mechanics,
        # imported by ``launch_runtime``/``lane_runtime``; it imports runner
        # APIs lazily so the v1->v3 boundary is not crossed at import time.
        "runtime_backend_bridge",
        "tmux_adapter",
        # ce-ops#207 W1: the visibility-backend registry — the v1 launcher's
        # witnessability/surface seam. A THIN wrapper over ``tmux_adapter`` (v1),
        # consumed only by ``lane_runtime`` (v1) at its spawn seam. It belongs to
        # the v1 launcher surface (not ``shared``): it imports a v1 module and is
        # part of the ``ce lane launch`` mechanics, exactly like the launch specs.
        # Classifying it v1 keeps both edges v1->v1 (no new shared->v1 ratchet
        # edge); it imports NO v3 module, so the HARD invariant is untouched.
        "visibility_backend",
        # ce-ops#207 W2′: the CE-owned-PTY session substrate — the headless
        # visibility backend's process-owning surface. Consumed only by
        # ``visibility_backend`` (v1) → ``lane_runtime`` (v1); imports only
        # stdlib (``os``/``pty``), no v3 module. Belongs to the v1 launcher's
        # witnessability/surface seam, exactly like ``visibility_backend`` and
        # ``tmux_adapter``: both edges stay v1->v1, no shared->v1 ratchet edge.
        "seat_pty_session",
        "transcript_archive",
        "pco_allocator",
        "hook_check",
        "hook_pack_confirm",
        # ``ce`` launcher subcommand runtimes (driven by ce_cli)
        # ce-ops#55 autonomous forge work-pickup poller: a READ-ONLY ``ce pickup``
        # subcommand runtime. Imports only stdlib + (S3) crosses to the v1 ``ce
        # lane launch`` as SUBPROCESS + DATA (seed file + argv) — imports NO v3
        # module, so the HARD v1<->v3 isolation invariant stays untouched.
        "pickup",
        "ce_event_runtime",
        # ce-ops#197 PR-5: the `ce onboard` first-run orchestrator. A thin
        # composition layer over the v1 `ce` kernel surfaces (doctor / init /
        # brain-init / launch) + the verify-install + profile-PATH legs. It
        # imports only v1 + shared modules — NO v3 import, so the HARD invariant
        # stays untouched (driven by the v1 `ce` kernel, classified v1 with them).
        "ce_onboard",
        "connector_runtime",
        "doctor_runtime",
        "fanin_runtime",
        "init_runtime",
        "integration_queue_dry_run",
        "packaging_runtime",
        "ce_provenance",
        # ce-ops#222: fleet-wide containment attestation command. A v1 kernel
        # CLI runtime over shared probe helpers; imports no v3 module.
        "containment_status",
        "pcl_runtime",
        # ce-contained-controller-push-model: host-side publish chokepoint for
        # contained seats' commit-only branches. Driven by the v1 `ce` kernel;
        # imports no v3 forge modules, with git push authority behind an
        # injectable host runner and Side-Effect Ledger audit trail.
        "publish_gate",
        "side_effect_ledger_runtime",
        "worker_runtime",
        # ce-ops#163 REQ-2: first-class worker-spawn primitive. This is a v1
        # coordination/launcher surface over ``launch_runtime``; it imports no v3
        # module and leaves later foreman injection/enforcement gates as data
        # consumers of the worker artifact.
        "worker_spawn",
    }
)

# --- CE v3.x orchestrator/forge/runner execution runtime surface ---
V3_RUNTIME: frozenset[str] = frozenset(
    {
        "orchestrator",
        "run_assembly",
        "evidence_sink",
        # forge adapter family
        "forge",
        "forge._redact",
        "forge.app_jwt_runner",
        # ce-ops#99 P1 repo-scope devops ops: all plan-by-default, injectable-runner
        # forge surfaces, classified with the rest of the v3 forge adapter family.
        "forge.auto_merge",
        # v3.5-C α-precursor: the Projects-v2 backlog reader/writer + the
        # forge-projected advisory claim (assignee + Status=Running, §A.4);
        # consumed by the A-C4 forge_claim_dedup gate.
        "forge.backlog",
        "forge.change",
        # v3.1-G2a: the missing branch-push primitive — pushes the governed seat's
        # authored head to the CONSTRUCTED HTTPS remote (never the SSH origin) so
        # `open_change` can claim its PR; plan-by-default, never force-pushes.
        "forge.change_push",
        "forge.change_status",
        "forge.credential_runner",
        "forge.eviction_detection",
        "forge.github_repo_config",
        "forge.merge",
        "forge.plan_approval",
        # ce-ops#151: rebase-aware stale-review reconciler (auto-dismiss a CR
        # superseded by an independent approval on the live head). v3 forge
        # adapter family; injectable GhRunner, no v1 import.
        "forge.re_review",
        # ce-ops#188: controller review-pickup leg — routes awaiting-review PRs
        # to distinct non-author seats via forge.re_review. v3 forge adapter
        # family; shares the boundary-neutral Search core (pickup_search) with
        # the v1 poller, so no v1<->v3 import edge is created.
        "forge.review_pickup",
        # ce-ops#95: pure fleet-liveness read-model for `ce seats ls`, reading
        # lifecycle/sentinel state files only. v3 forge surface; imports no v1.
        "forge.seats_status",
        # ce-fleet-status: aggregate fleet read-model for `ce fleet status`,
        # reusing seats_status plus daemon JSONL logs/process probes and the
        # integrator PR board adapter. v3 forge surface; imports no v1.
        "forge.fleet_status",
        # ce-ops#216 Unit 2: deterministic, read-only integrator conflict resolvers
        # for known mechanical families. Pure data transforms; no executor/push/
        # credential authority. v3 forge adapter family, imports no v1 module.
        "forge.deterministic_resolvers",
        # ce-ops#216 Unit 4: data-only escalation seam for unresolved Unit 2
        # resolver outputs. Produces controller-action event data; no executor,
        # network, credential, or write authority.
        "forge.integrator_escalation",
        # ce-ops#216 Unit 3: write-authority executor for applying deterministic
        # resolver output with PR/base race guards. v3 forge adapter family;
        # live write/push authority stays behind an injectable adapter.
        "forge.integrator_executor",
        # ce-ops#216 Unit 5: one-shot Integrator MVP runner wiring the landed
        # detector/resolver/escalation primitives to Unit 3's race-guarded
        # executor API. No daemon; executor import is lazy and fail-closed.
        "forge.integrator_runner",
        # ce-ops#218 belt-poller: chains the landed detector/resolver/executor/
        # escalation primitives behind a bounded merge-queue repair poll loop.
        # Pure-forge v3 adapter family; live actions stay behind injectable
        # adapters + the merge gate, fail-closed; imports no v1 module.
        "forge.integrator_belt",
        "forge.review_submit",
        "forge.ruleset",
        "forge.scoped_token",
        # Search API headroom for v3 forge pollers. The core limiter is shared
        # at ``search_rate_limiter`` so v1 pickup never imports ``forge``.
        "forge.search_rate_limiter",
        # ce-ops#228 PR-1: offline credential-injection transport-deputy policy
        # seam. Pure fail-closed request verdicts before any OneCLI credential
        # injection; no token minting, network, or process execution.
        "forge.transport_deputy_policy",
        # ce-ops#157 shared-App self-serve: user-side OAuth device-flow install
        # discovery (POST /login/device/code → poll → GET /user/installations).
        # Part of the v3 forge adapter family; injectable transport, no v1 import.
        "forge.user_install_discovery",
        # runner backends
        "runner",
        "runner.audit_overlay",
        "runner.backend",
        "runner.cc_hook_adapter",
        "runner.gvisor_proxy_backend",
        "runner.noop_backend",
        # v3.5-A.1 OpenShell backend (defined; registration deferred to A.2)
        "runner.openshell_backend",
        # Runner-owned Ring-1 increment 1: PATH-precedence git/gh shims that call
        # the public hook-check CLI. This remains v3 runner code and must not
        # import the retained v1 hook_check module directly.
        "runner.ring1_tool_guard",
        # ce-ops#71 Tranche 1: the unprivileged OS-native backend — a FAIL-CLOSED
        # scaffold (registered + deny-surface-enforcing; the sandbox mechanism is
        # HELD pending the srt-vs-CE-native-jail Operator decision, research §9).
        "runner.os_native_backend",
        # v3 G-5 tokenomics: the pure spend gate (admission + circuit-breaker)
        "runner.spend_gate",
        # v3.5-D.0.1 compute-demand artifact: the live usage tap
        # (transcript → spend-ledger; reuses runner.spend_gate, pure core + 1 I/O edge)
        "runner.usage_tap",
        # v3.5-B.1 Cockpit: the L2 read-model (= the harness-paper F1
        # Deep-Telemetry projection; pure JSON-serializable fold, principle 6)
        "runner.cockpit_readmodel",
        # v3.1-B.8 Operator-notify feed: pure edge-detection fold over escalations
        # + a notifier-private delivery ledger + desktop/exec sinks (pure core + I/O
        # edges; reuses cockpit_readmodel.load_escalations, imports no textual/v1).
        "runner.notify_feed",
        # v3.5-B.1 Cockpit: the CE_DEMO seed (Fork F-b: its own module — the
        # independently-reviewable pitch artifact)
        "runner.cockpit_demo_seed",
        # v3 G-6 coordination: the outer-loop Scope dispatch spine
        "authority_resolver",
        "coordination",
        # v3.1-G1 live-spawn keystone: the assemble->spawn bridge. Crosses to the
        # v1 launcher as SUBPROCESS + DATA only (`ce launch --json`, files + argv +
        # JSON) — imports NO v1 module, so the HARD invariant + the ratchet stay
        # untouched by construction (AST-asserted in test_v3_seat_bridge).
        "v3_seat_bridge",
        # v3.1-G2a: the forge-leg composition root joining the G1 dispatch to the
        # forge (push→open→merge). Imports forge.*/run_assembly/orchestrator — all
        # v3; imports NO v1 module (AST-asserted in test_v3_forge_join). The JIT
        # token value + the App private key stay behind the credential_runner /
        # openssl seams; never argv/log/disk/record.
        "v3_forge_join",
        # v3 G-7 product surface: the distinct work-driving CLI (``cev3``)
        "v3_cli",
        # v3 G-7 product surface: the session frame + unified status line render
        "v3_session",
        # v3 G-7 product surface: the Frame→Shape grill-me + chat→Scope dial
        "v3_shaping",
        # v3 G-7 product surface: the ◆ CE Completion Report + artifact awareness
        "v3_report",
        # v3 G-7 product surface: the two-mode installer logic + cost opt-out
        "v3_installer",
        # v3.5-E.2 live-drive seam: the signed-spec onboard apply executor.
        "onboard_apply",
        # ce-ops#88: the production live-forge ApplyDriver (Phase 1) — composes the v3
        # forge credential toolchain (mint/app-jwt/credential runner) over onboard_apply.
        "onboard_apply_live",
        # v3.5-E.4 greenfield first-project read model: pure Frame->Ship fold
        # over E2 onboard_apply facts; imports no v1 module and performs no I/O.
        "v3_greenfield",
        # v3.5-B.1 Cockpit: the L3 Textual view (binds to L2 snapshots ONLY;
        # a future GUI replaces this module alone — principle 6)
        "v3_cockpit",
        # ce-ops#43 seat/venue retirement reaper: the substrate-neutral POLICY
        # fold (discover/classify/orchestrate; re-implements the seat-sentinel
        # outcome resolution READ-ONLY — never calls resolve_outcome). Reads
        # ``seat_sentinel`` (shared) as DATA; imports NO v1 module.
        "seat_reaper",
        # ce-ops#43: the per-substrate retirement executors (tmux today). The two
        # v1 crossings — ``ce lane archive --json`` + ``creator-engine-validator
        # pco-release`` — are subprocess+DATA only; imports NO v1 module.
        "reaper_executors",
    }
)

# --- Baselined shared->version couplings (ratchet floor; derived from the full
#     import graph on main @ ab482ee, post-grounding). Each entry is a real,
#     pre-existing edge with a justification. The allowlist only shrinks. ---
BASELINE_SHARED_TO_VERSION_ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {
        # The unified validator CLI hosts v1 launcher subcommands (lazy imports).
        # The v3 CLI arrives at G-7 as a DISTINCT entry point, not by mutating these.
        ("cli", "hook_check"),
        ("cli", "pco_allocator"),
        # The shared env/packaging-contract guard reuses the v1 packaging contract
        # types; candidate for extraction into a shared packaging-contract module.
        ("environment_guard", "packaging_runtime"),
    }
)

# --- v3 plane-C SCHEMAS (G-4.1). The v3-classified schema surface the
#     ``v3_naming_hygiene`` check scans for bootstrapping-harness residue, paired
#     with the v3 CODE surface (``classify(...) == V3``). Paths are repo-root
#     relative. Declared (not derived) so a rename is caught (COMPLETENESS) and
#     the set is an explicit ratchet floor. v1/shared schemas are NOT listed. ---
V3_SCHEMAS: frozenset[str] = frozenset(
    {
        "schemas/runtime-policy.schema.yaml",
        "schemas/runtime-evidence.schema.yaml",
        "schemas/scope.schema.yaml",
        # v3.5-E.3: the two-mode-installer answers file (the v3 installer
        # surface's input inventory — single source of truth for the
        # `install_answers` check + the `v3_installer` engine).
        "schemas/install-answers.schema.yaml",
        # v3.1-G1: the dispatch record — the on-disk handoff a `cev3 drive
        # --spawn` materializes (`v3_seat_bridge`) and `cev3 collect` folds.
        # Value-free: digests + shape refs only.
        "schemas/dispatch-record.schema.yaml",
        # v3.5-B live feeds: the local AWAITING-OPERATOR queue consumed by the
        # Cockpit L2 read-model. Value-free local mirror records only.
        "schemas/escalation-record.schema.yaml",
    }
)

# --- Neutral v3/v3.1 LOCAL-STATE root (G-4.1). The CE-namespaced, gitignored
#     instance-local state root for the v3 execution runtime — NEVER ``.hermes/``
#     (the v1 bootstrapping-harness residue, retained frozen for v1 only) and
#     NEVER ``.claude/`` (Claude Code's own tool dir; using it would re-bind CE
#     state to one harness — the same mistake). The v3 sink/driver are already
#     path-neutral (``evidence_sink(root)`` / ``make_run_driver(root)`` take the
#     write-root as a parameter), so this is the convention/default the v3 work-
#     driving CLI (G-7) wires production state under. See
#     ``docs/contracts/v3-naming-hygiene.md``. ---
V3_LOCAL_STATE_ROOT = ".ce/state"

# --- Baselined v3 naming-hygiene exceptions (G-4.1 ratchet floor). Each entry is
#     (repo-relative-file, residue-token) — a justified, pre-existing residue in
#     the v3 surface. EXPECTED EMPTY: the v3 surface is clean on day one. The set
#     only shrinks; a new residue in the v3 surface fails ``v3_naming_hygiene``. ---
BASELINE_V3_NAMING_ALLOWLIST: frozenset[tuple[str, str]] = frozenset()


def classify(rel_module: str) -> str:
    """Return the version line (``v1`` / ``v3`` / ``shared``) for a module.

    ``rel_module`` is the dotted name relative to ``creator_engine_validator``
    (the package itself is ``""``). Anything not declared in a runtime surface
    is ``shared`` — see the module docstring for why that is safe (the ratchet).
    """
    if rel_module in V1_RUNTIME:
        return V1
    if rel_module in V3_RUNTIME:
        return V3
    return SHARED
