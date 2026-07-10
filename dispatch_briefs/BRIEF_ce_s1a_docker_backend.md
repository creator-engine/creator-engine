# BRIEF — ce-s1a-docker-runner-backend — plain-Docker runner backend for tenant contained launch (UNIT 4, dev-3)

Role: implementer (dev-3, contained, foreman mode). Start after your ce-415 unit signals. Branch
`ce-s1a-docker-runner-backend` off freshly-fetched origin/main. Worktree /var/tmp; venv
`.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Why (embedded; Operator-ratified day-arc: tenant `ce launch` must run contained on plain Docker)
Today only `gvisor-proxy` is honored by runtime_backend_bridge.run_visible_runtime()
(runtime_backend_bridge.py:150-179 hard-refuses every other backend key), and that backend is
DGX-fleet-specific: it forces `--runtime=runsc-gvproxy-ptrace` (runner/gvisor_proxy_backend.py:52-59,
161-191, 344-352 refuses plain runtimes) and bind-mounts a HOST codex binary. A tenant with plain
Docker has NO working contained path.

## Deliverable: new backend `docker`
1. New module `validators/creator_engine_validator/runner/docker_backend.py`: mirror
   gvisor_proxy_backend.py's pure-translate/injectable-runner shape, but: NO `--runtime=` flag
   (default Docker runtime); no host-codex bind-mount requirement; image ref comes SOLELY from
   `runtime_policy["image_ref"]` (digest-pinned); reuse the gvisor plan's security posture verbatim
   (`--cap-drop=ALL --security-opt=no-new-privileges --user <uid>:<gid>`, read-only where it is
   today, tmpfs scratch); mounts ONLY from the policy's mount_manifest (the forbidden-mount check
   in checks/ce_runtime_policy.py:194-211 stays authoritative).
2. Register in runner/__init__.py (BACKEND_KEY export, registry entry).
3. runtime_backend_bridge.py:174-179 — honor the new key alongside gvisor-proxy (keep the refusal
   for everything else; do NOT loosen the raw-fallback refusal).
4. checks/ce_runtime_policy.py:79-86 — add "docker" to CLI_BACKEND_CHOICES/_BACKEND_ALIASES.
5. schemas/runtime-policy.schema.yaml + docs/contracts/runtime-policy.md — add `docker` to the
   isolation_backend enum, AND extend the `role` enum (currently architect_research|implementer|
   verification, contract line ~77) with `controller` (needed by the follow-on launch-default unit;
   controller-authorized governance-contract change — note it explicitly in the PR body).
6. Tests: behavioral unit tests in validators/tests/unit/ mirroring the gvisor backend's test
   style — argv translation (image ref, security opts, mounts, user), refusal cases (missing
   image_ref, forbidden mount, unknown backend still refused), bridge composition honoring the new
   key. Hermetic — no docker needed to run tests.

SEMANTIC NOVELTY CHECK FIRST: confirm on fresh main that runner/ has no docker/plain backend and
the bridge still only honors gvisor-proxy; if that changed, signal BLOCKED already-resolved with
evidence.

## STOP lines
- ⛔ Do NOT touch launch_runtime.py, onboard_apply.py, ce_cli.py, or v3_installer.py — those are a
  separate unit's territory (same-day; collision = rework).
- ⛔ Do NOT weaken any existing refusal path or forbidden-mount rule.
- ⛔ Never sign anything; signed-artifact gate failure = STOP and report bytes.
- ⛔ No review/approve/merge/enqueue. Do not revert others' edits.

## Evidence bar
Full `ce validate-pr` GREEN one pass before commit-for-harvest (if ONLY the carrier gate fails,
that is the known contained-seat gap — say so). Changelog + carrier authored. Declared work class:
story. Signal: `READY-FOR-HARVEST ce-s1a-docker-runner-backend <40-hex sha>`.
