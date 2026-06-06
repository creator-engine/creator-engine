"""v3 G-3.6b — the offline composition root: the production ``run`` driver.

:func:`make_run_driver` returns a callable that drives ONE ratified, audited
agent-seat run end to end and PERSISTS its evidence. It is the first real
composition root — the single place that assembles the already fake-tested seams
into one :func:`~.orchestrator.run_plan` drive:

* the production ``token_minter`` — a closure over ``forge.mint_scoped_token`` /
  ``forge.revoke_scoped_token`` that maps the value-bearing ``ScopedToken`` to the
  value-free :class:`~.orchestrator.MintedCredential` port the orchestrator gates;
* the **minter->runner bridge** — a closure cell holding the ONE live
  ``ScopedToken`` minted for the run, shared from the minter to the
  ``change_opener``'s authenticated ``gh`` runner via
  ``forge.authenticated_gh_runner`` — so the change-opener authenticates AS the
  SAME minted token, while the orchestrator stays value-free (it only ever sees
  the ``MintedCredential``; the live ``value`` never crosses into ``run_plan``);
* the production ``change_opener`` — a closure over
  ``forge.open_change(..., apply=False)`` through that authenticated runner;
* the G-3.5 ``file_evidence_sink`` — wired into the new
  ``run_plan(evidence_sink=…)`` seam so the run's chain persists after teardown.

The drive proves, entirely offline, the full pipeline:
**mint -> authenticated runner -> run -> collect -> typed ``pr_opened`` outcome ->
persisted evidence**, with ZERO live side effects (the backend / ``gh_runner`` /
``spawn`` / ``write`` are all injectable seams; CI drives fakes with
``subprocess`` / ``socket`` / ``Path.write_text`` monkeypatched to explode). It is
the exact entry G-3.7 promotes to live (``apply=True`` + a real installation,
OUTSIDE the CI-purity envelope).

This module is where ``forge`` IS imported and the live ``ScopedToken.value``
lives — the opposite of the pure, forge-free orchestrator. The value lives ONLY
in the closure cell and, at call time, ONLY in the child ``gh`` env; it never
enters the orchestrator, the evidence, argv, input, a log, disk, or the parent
environment. Importing this module performs zero I/O and registers no check and
no backend.

Defensive only — authorization + accountability for our own agent runtime;
never offensive.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .evidence_sink import file_evidence_sink
from .forge.change import open_change
from .forge.credential_runner import authenticated_gh_runner
from .forge.github_repo_config import ForgeConfigError
from .forge.scoped_token import TokenRequest, mint_scoped_token, revoke_scoped_token
from .orchestrator import ApprovedPlan, MintedCredential, run_plan
from .runner import CollectedEvidence, RunnerBackend

#: The composed driver: drive(runtime_policy, run_id, command, approved_plan, token_request).
RunDriver = Callable[
    [dict[str, Any], str, Sequence[str], ApprovedPlan, TokenRequest], CollectedEvidence
]


def make_run_driver(
    repo: str,
    root: Path,
    *,
    spawn: Any = None,
    write: Any = None,
    backend: RunnerBackend | None = None,
    gh_runner: Any = None,
) -> RunDriver:
    """Return a :data:`RunDriver` composing one offline run end to end + persistence.

    ``repo`` is the ``owner/name`` the change is opened against; ``root`` the
    directory the evidence chain persists under. The injectable seams default to
    production: ``backend`` (else resolved from the runtime-policy by ``run_plan``),
    ``gh_runner`` (the App-level mint/revoke transport), ``spawn`` (the child ``gh``
    transport for the authenticated change-opener runner), and ``write`` (the
    evidence-file writer). CI injects fakes for all four.

    The returned ``drive(runtime_policy, run_id, command, approved_plan,
    token_request)`` mints a JIT per-run credential, shares the live
    ``ScopedToken`` to the change-opener's authenticated ``gh`` runner through a
    closure cell (the orchestrator never sees the value), opens/claims the PR
    plan-by-default, persists the run's evidence chain via the G-3.5 sink, and
    revokes the credential — authenticated AS the token, best-effort — at
    completion (success OR failure).
    """
    root = Path(root)

    def drive(
        runtime_policy: dict[str, Any],
        run_id: str,
        command: Sequence[str],
        approved_plan: ApprovedPlan,
        token_request: TokenRequest,
    ) -> CollectedEvidence:
        # The minter->runner bridge: ONE live ScopedToken, held in a closure cell the
        # change-opener's authenticated runner reads. The cell never crosses into run_plan;
        # the orchestrator sees only the value-free MintedCredential.
        cell: dict[str, Any] = {"token": None}

        def token_minter(policy: dict[str, Any], rid: str) -> MintedCredential:
            token = mint_scoped_token(token_request, gh_runner=gh_runner)
            cell["token"] = token  # share the live token to the runner factory, NOT the orchestrator
            return MintedCredential(
                run_id=token.run_id,
                policy_sha=token.policy_sha,
                secret_name=token.secret_name,
                permissions=token.permissions,
                expires_at=token.expires_at,
                credential_ref=token.token_ref,
            )

        def change_opener(change_set: Any, plan_ref: str) -> Any:
            # Authenticate the change-open AS the minted token — the live value lands in the
            # child gh env only (forge.authenticated_gh_runner), never in argv / here / evidence.
            authed = authenticated_gh_runner(cell["token"], spawn=spawn)
            return open_change(
                repo,
                change_set.branch,
                change_set.base,
                change_set.manifest_paths,
                plan_ref,
                apply=False,
                gh_runner=authed,
            )

        sink = file_evidence_sink(root, write=write)
        # G-3.7.2b: the value-free binding inputs for the runtime head-SHA assertion. The
        # orchestrator recomputes binding_ref over this {repo, installation_id, permissions,
        # ratified_head_sha} tuple and REFUSES if it (or the change head) drifted from the
        # SHA-pinned ratification on the ApprovedPlan. Only the opaque digest lands in evidence,
        # never these raw identifiers; for an unbound ApprovedPlan the gate is inert.
        binding_inputs = {
            "repo": repo,
            "installation_id": token_request.installation_id,
            "permissions": dict(token_request.permissions),
        }
        try:
            return run_plan(
                runtime_policy,
                run_id,
                command,
                approved_plan,
                backend=backend,
                token_minter=token_minter,
                change_opener=change_opener,
                evidence_sink=sink,
                binding_inputs=binding_inputs,
            )
        finally:
            # Defense-in-depth: release the credential the instant the run ends — success OR
            # failure — rather than waiting out its (<=1h) ttl. No mint -> nothing to revoke.
            # DELETE /installation/token must authenticate AS the token being revoked, so route
            # the revoke through an authenticated runner bound to the minted token (NOT the
            # App-level mint runner). Best-effort: a revoke-transport failure must neither mask
            # the run exception nor manufacture a success-path error — it is swallowed and made
            # alertable (value-free), and the token then expires on its own (<=1h) ttl.
            token = cell["token"]
            if token is not None:
                try:
                    revoke_scoped_token(
                        token, gh_runner=authenticated_gh_runner(token, spawn=spawn)
                    )
                except ForgeConfigError:
                    logging.getLogger(__name__).warning(
                        "scoped-token revoke failed for run %s (token_ref %s); "
                        "the token will expire on its ttl",
                        run_id,
                        token.token_ref,
                    )

    return drive
