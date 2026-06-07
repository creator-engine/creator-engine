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
        "lane_runtime",
        "launch_runtime",
        "claude_launch_spec",
        "hermes_launch_spec",
        "tmux_adapter",
        "transcript_archive",
        "pco_allocator",
        "hook_check",
        "hook_pack_confirm",
        # ``ce`` launcher subcommand runtimes (driven by ce_cli)
        "ce_event_runtime",
        "connector_runtime",
        "doctor_runtime",
        "fanin_runtime",
        "init_runtime",
        "integration_queue_dry_run",
        "packaging_runtime",
        "pcl_runtime",
        "side_effect_ledger_runtime",
        "worker_runtime",
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
        "forge.change",
        "forge.change_status",
        "forge.credential_runner",
        "forge.github_repo_config",
        "forge.merge",
        "forge.plan_approval",
        "forge.scoped_token",
        # runner backends
        "runner",
        "runner.audit_overlay",
        "runner.backend",
        "runner.cc_hook_adapter",
        "runner.gvisor_proxy_backend",
        "runner.noop_backend",
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
