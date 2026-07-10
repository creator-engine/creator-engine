---
brief_id: BRIEF_dev4_restock2_20260709
ticket: ce-490-contained-launch-preflight-s1
seat: dev-4
seat_kind: contained-commit-only
branch: ce-490-contained-launch-preflight-s1
worktree: /var/tmp/ce-490-contained-launch-preflight-s1
size: S
units: 1
priority: TOP
mandate: live-tenant-launch-fragility-20260709
grounded_on: origin/main@ab27b96e76fd411e6b32ce9702b3d9c33e565b95
composed_at: 2026-07-09
---

# BRIEF: Contained launch plan-time preflight — slice 1

**Mandate (2026-07-09):** Today's Arad rehearsal re-proved that fresh-tenant
`ce launch` (contained-default) is fragile in ways the operator cannot
self-diagnose. The stale July-3 launch surface blocked relaunch with no
guided recovery path. Three plan-time gaps exist in every freshly onboarded
repo regardless of host state; they all fire BEFORE docker is called but
none surfaces a named, actionable refusal. This slice adds the pre-spawn
validation step that catches all three at plan time and surfaces docker
stderr when docker is still reached.

**In-seat validation = TARGETED TESTS ONLY; never run full validate-pr
in-seat (resource kills); controller preflight is authoritative.**

---

## Ticket content (ce-ops#490, embedded)

**Title:** [bug] contained-default launch lane cannot succeed on a fresh
0.3.3 tenant: three stacked plan-time gaps + hidden docker stderr

**State:** OPEN. **Labels:** bug, triage:ready, wc:S, ws:containment.

### Symptom

`ce launch` (contained-default) on a freshly onboarded 0.3.3 tenant refuses
with:

```
ERROR: ce launch refused [G6-LAUNCH-RUNTIME-POLICY-REFUSED]: contained runtime
launch returned no launch-owned runtime probe pid; refusing unproven containment
```

The fail-closed behavior is correct; the problem is that all three root causes
are invisible to the operator, and two of the three causes exist in every fresh
onboarded repo regardless of host state.

### Three stacked causes

**(a) `onboard --apply` emits a placeholder all-zeros image digest**

The emitted policy contains:
```yaml
image_ref:
  name: ghcr.io/creator-engine/creator-engine/ce-seat
  sha: sha256:0000000000000000000000000000000000000000000000000000000000000000
```

`sha256:000...000` is a syntactically valid digest — 64 hex chars — and passes
schema validation. The launcher proceeds to the docker backend with a
non-pullable reference.

**(b) Policy unconditionally bind-mounts four dotfile dirs; docker hard-fails
pre-create when any is absent**

The `mount_manifest` emitted by `onboard --apply` always includes:
```
/home/<user>/.claude        (ro)
/home/<user>/.config/claude (ro)
/home/<user>/.codex         (ro)
/home/<user>/.config/codex  (ro)
```

Docker fails at container-creation time (rc=125, before any image pull) if any
source path does not exist on the host. On a fresh user host, one or more of
these dirs will be absent. The mount is unconditional — there is no `optional`
flag or existence check.

**(c) Container command is a sentinel wrapper at a HOST path outside the mount
manifest**

The `docker run` command ends with the sentinel wrapper at a path under the repo
root. The mount manifest covers `~/ce-workspaces` and the four dotfile dirs —
but not arbitrary repo paths. For any tenant whose repo lives outside
`~/ce-workspaces`, the sentinel wrapper path is not mounted, and exec would fail
even after fixing (a) and (b).

### Diagnosability defect

The launcher's 2s probe times out, finds no launch-owned pid, and surfaces only:

```
G6-LAUNCH-RUNTIME-POLICY-REFUSED: contained runtime launch returned no
launch-owned runtime probe pid
```

The docker stderr (`bind source path does not exist: ...`) is not surfaced.
Root-causing (b) required manually reconstructing the `docker run` argv via
`translate_to_docker_plan` and running it standalone.

### Proposed fix: fail-closed-but-diagnosable at PLAN time (pre-spawn refusal)

Add a pre-spawn policy validation step to the contained-launch path that checks
all three conditions BEFORE calling docker, and emits a named refusal with the
specific cause:

1. **Digest validation:** reject `sha256:000...000` with
   `G6-LAUNCH-POLICY-INVALID: image digest is a placeholder — re-run
   ce onboard after runtime_posture resolves`.
2. **Mount source existence:** for every `type=bind` mount, check that `source`
   exists on the host. For optional agent-config dirs (`~/.config/claude`,
   `~/.claude`, `~/.codex`, `~/.config/codex`): skip mount + warn (conditional).
   For all other absent paths: refuse with
   `G6-LAUNCH-POLICY-INVALID: bind source path does not exist: <path>`.
3. **Command path reachability:** verify the sentinel wrapper path is under at
   least one mounted source. If not, refuse with
   `G6-LAUNCH-POLICY-INVALID: container command path <path> is not under any
   mounted source`.

Also capture and surface docker stderr in the refusal message when docker still
fails pre-spawn (the stderr is available; the launcher just doesn't forward it
today). This is a best-effort log emission — the pre-spawn checks above should
prevent reaching docker in the three documented cases.

**Out of scope for s1:** the sentinel HUP race / kill-session exited event.
That is a separate lifecycle-state issue. Do NOT touch seat_lifecycle.py.
Do NOT touch ce_onboard.py (the zero-digest source is a separate HELD design
decision, ce-ops#71 — the fix here is detection at launch time, not at onboard
time).

### Done-when (s1)

- `ce launch` on a fresh onboarded tenant with zero-digest emits a named,
  actionable pre-spawn refusal (`G6-LAUNCH-POLICY-INVALID`) that identifies
  which cause applies.
- Absent optional dotfile dirs are conditionally omitted from the mount manifest
  rather than causing a hard docker rc=125 failure.
- Sentinel wrapper path not covered by any mount emits a named pre-spawn
  refusal.
- `ce launch --backend host` (explicit opt-out of runtime policy) is unaffected
  — the validation only fires when `plan.runtime_policy is not None`.
- Tests cover all three validation paths (zero-digest, absent optional mount,
  uncovered sentinel path).

---

## Standing obligations (copy verbatim into your PR body + checklist)

- [ ] Changelog fragment: `.ce/changelog/ce-490-contained-launch-preflight-s1.md`
- [ ] Carrier: `.ce/pr-manifests/ce-490-contained-launch-preflight-s1.md`
      slug field MUST be exactly `ce-490-contained-launch-preflight-s1`
- [ ] Work class line in PR body: `**Declared work class: story**`
      (LEGACY vocab: tiny|story|feature|epic; this is story = S)
- [ ] NEVER commit a file named READY (gate signal, not a commit artifact)
- [ ] No ce-ops issue number references in PR body, commit messages, or code
      comments (use plain English descriptions of the ticket's intent)

---

## Files to produce — COMPLETE territory

One existing file is modified; three files are new.

```
validators/creator_engine_validator/launch_runtime.py                 (MODIFY)
validators/tests/unit/test_contained_launch_preflight.py              (NEW)
.ce/changelog/ce-490-contained-launch-preflight-s1.md                 (NEW)
.ce/pr-manifests/ce-490-contained-launch-preflight-s1.md              (NEW)
```

**Brain-pin precompute (byte-change rule):**

All static `evidence_ref` paths in `.ce/brain/assertions.yaml` were grepped.
The current-main sha256s are recorded here so the seat can confirm no
brain-pinned file is accidentally modified:

| File | sha256 on origin/main |
|---|---|
| `.github/workflows/validate.yml` | `5b0138b44627b023499bbf124c3702f386e520a17daa6f1c75166a2e912dddc1` |
| `docs/contracts/authoring-a-governed-pr.md` | `88f8e46c67288c456bb72f2f7ba17e1ed3445bebc8285fe9b0e7fbdd8f07029a` |
| `docs/architecture/work-claim-locks.md` | `aa96a707b218958acafb1d9bdd561fbe8416a76234c0408e73a4c7fd8ac9111b` |
| `.ce/brain/notes/deterministic-citations.md` | `51b59ac94fc70f9e69ddaf2891ae7f89d6c9dde441d8a049c0517d83d5ab2236` |
| `validators/pyproject.toml` | `01af7c1c9021489bb76282b630e65fea37d504e4014d40e28c00564a3498147d` |

NONE of the four target files for this PR are brain-pinned. The diff must show
zero modifications to any of the five files above. If the validate-pr gate
reports a brain-drift assertion on any of them, the assertion-ledger append is
NOT in scope for this PR — write BLOCKED immediately.

---

## Frozen / in-flight paths — DO NOT TOUCH

These paths are owned by concurrent open PRs. Your diff must not include any
of them:

| Path | Owned by |
|---|---|
| `docs/governance/identity-registry.example.yaml` | PR #925 |
| `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` | PR #925 |
| `validators/tests/unit/test_identity_registry_schema.py` | PR #925 |
| `validators/creator_engine_validator/forge/integrator_belt.py` | PR #926 |
| `validators/tests/unit/test_integrator_belt.py` | PR #926 |
| `deploy/daemons/smoke-daemon-container.sh` | PR #927 |
| `validators/tests/integration/test_adoption_merge_group_e2e.py` | PR #928 |
| `docs/design/ratification-authorization-binding.md` | PR #912 |
| `tools/controller/state_sync.py` | dev-3 (ce-497, in-flight) |
| `validators/tests/unit/test_controller_state_sync.py` | dev-3 (ce-497, in-flight) |
| `docs/operations/CONTROLLER_BOOTSTRAP.md` | dev-1 (ce-496, in-flight) |
| `validators/tests/unit/test_controller_bootstrap_paths.py` | dev-1 (ce-496, in-flight) |

No `surfaces/manifest.yaml` edit. No `assertions.yaml` edit (brain-ledger
serialization is controller-side; worker never touches it). No new `AGENTS.md`
or `CLAUDE.md` changes. No `ce_onboard.py` changes (zero-digest is a HELD
design gap; the fix here is detection at launch time only).

---

## Implementation specification: `launch_runtime.py` changes

### New error class

Add after the existing `RuntimePolicyRefused` class (around line 110):

```python
class ContainedLaunchPreflightRefused(LaunchError):
    """Raised when a contained-launch plan fails pre-spawn policy validation.

    Fires BEFORE any docker/runtime side effect. Error code is
    G6-LAUNCH-POLICY-INVALID to distinguish from the post-spawn runtime
    policy refusal (G6-LAUNCH-RUNTIME-POLICY-REFUSED).
    """
    code = "G6-LAUNCH-POLICY-INVALID"
```

### New function: `_validate_contained_launch_plan`

Add as a module-level function alongside the other `_` helpers:

```python
# Optional dotfile dirs that agents may not have populated on a fresh host.
# These are skipped (with a warning) when absent rather than refused.
_OPTIONAL_AGENT_DOTFILE_SUFFIXES: tuple[str, ...] = (
    "/.claude",
    "/.config/claude",
    "/.codex",
    "/.config/codex",
)


def _validate_contained_launch_plan(
    policy_record: dict[str, Any],
    sentinel_wrapper_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    """Pre-spawn policy validation for contained (runtime-policy-backed) launch.

    Checks three plan-time gaps before any docker/runtime side effect:
      (a) zero-digest placeholder detection
      (b) mount source existence (optional dotfile dirs are conditional)
      (c) sentinel wrapper path coverage by the mount manifest

    Returns (updated_policy_record, warnings).  updated_policy_record has
    absent optional dotfile mounts removed from mount_manifest so the caller
    can pass it straight to the runtime backend without re-doing the check.

    Raises ContainedLaunchPreflightRefused for hard failures.
    """
    _ZERO_DIGEST = "sha256:" + "0" * 64
    warnings: list[str] = []

    # (a) Placeholder digest detection.
    image_ref = policy_record.get("image_ref") or {}
    sha = image_ref.get("sha", "")
    if sha == _ZERO_DIGEST:
        raise ContainedLaunchPreflightRefused(
            "image digest is a placeholder (sha256:000...000) — "
            "re-run ce onboard after runtime_posture resolves; "
            "the seat image is not yet content-addressed"
        )

    # (b) Mount source existence check.
    surviving_mounts: list[dict[str, Any]] = []
    for entry in list(policy_record.get("mount_manifest") or []):
        if not isinstance(entry, dict):
            surviving_mounts.append(entry)
            continue
        source_path = entry.get("path", "")
        if source_path and not Path(source_path).exists():
            is_optional = any(
                source_path.endswith(sfx)
                for sfx in _OPTIONAL_AGENT_DOTFILE_SUFFIXES
            )
            if is_optional:
                warnings.append(
                    f"optional agent-config dir absent — skipping mount: {source_path}"
                )
                continue  # omit from surviving mounts; do not refuse
            raise ContainedLaunchPreflightRefused(
                f"bind source path does not exist: {source_path}; "
                "ensure the path exists on the host before launching"
            )
        surviving_mounts.append(entry)

    # (c) Sentinel wrapper path coverage.
    mounted_sources = [
        Path(e["path"])
        for e in surviving_mounts
        if isinstance(e, dict) and e.get("path")
    ]
    wrapper = Path(sentinel_wrapper_path)
    covered = any(
        wrapper == src or wrapper.is_relative_to(src)
        for src in mounted_sources
    )
    if not covered:
        raise ContainedLaunchPreflightRefused(
            f"container command path {str(wrapper)!r} is not under any mounted "
            "source in the mount_manifest; add the repo root or seat directory "
            "to the mount manifest"
        )

    updated_policy = dict(policy_record)
    updated_policy["mount_manifest"] = surviving_mounts
    return updated_policy, warnings
```

### Call site in `launch()`

In the `launch()` function, after `sentinel = seat_sentinel.prepare_seat_sentinel(...)` and
BEFORE the `if plan.runtime_policy is not None:` branch that calls
`runtime_backend_bridge.run_visible_runtime(...)`:

```python
    # Pre-spawn contained-launch policy validation (fires for all runtime-policy
    # backed launches; no-op for --backend host / bare launch).
    if plan.runtime_policy is not None and runtime_policy_record is not None:
        runtime_policy_record, _preflight_warnings = _validate_contained_launch_plan(
            runtime_policy_record,
            sentinel.wrapper_path,
        )
        for _w in _preflight_warnings:
            LOGGER.warning("contained-launch preflight: %s", _w)
```

`ContainedLaunchPreflightRefused` propagates uncaught to the CLI layer, which
surfaces it as the named error code. No try/except wrapper needed here.

---

## Unit tests: `validators/tests/unit/test_contained_launch_preflight.py`

All tests are `pytest.mark.fast`. Use `tmp_path` fixtures; no network; no real
docker invocations. Import `_validate_contained_launch_plan` and
`ContainedLaunchPreflightRefused` directly from
`creator_engine_validator.launch_runtime`.

```python
"""Unit tests for the contained-launch pre-spawn policy validation step.

These tests cover the three plan-time gap checks added to launch_runtime
to catch contained-launch failures before any docker/runtime side effect.
"""

import pytest
from pathlib import Path

from creator_engine_validator.launch_runtime import (
    _validate_contained_launch_plan,
    ContainedLaunchPreflightRefused,
)

_VALID_DIGEST = "sha256:" + "a" * 64
_ZERO_DIGEST = "sha256:" + "0" * 64


def _make_policy(sha=_VALID_DIGEST, mounts=None):
    """Minimal runtime policy dict for testing."""
    return {
        "policy_id": "test-policy",
        "image_ref": {"name": "ghcr.io/test/ce-seat", "sha": sha},
        "mount_manifest": mounts if mounts is not None else [],
    }


def test_zero_digest_refused(tmp_path):
    policy = _make_policy(sha=_ZERO_DIGEST)
    sentinel = tmp_path / "sentinel-wrapper.sh"
    with pytest.raises(ContainedLaunchPreflightRefused, match="placeholder"):
        _validate_contained_launch_plan(policy, sentinel)


def test_valid_digest_passes(tmp_path):
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    policy = _make_policy(
        sha=_VALID_DIGEST,
        mounts=[{"path": str(tmp_path), "mode": "rw",
                 "write_justification": "seat dir"}],
    )
    updated, warnings = _validate_contained_launch_plan(policy, sentinel)
    assert updated["image_ref"]["sha"] == _VALID_DIGEST


def test_absent_optional_dotfile_skipped(tmp_path):
    """Absent ~/.claude (optional agent config) is skipped without refusal."""
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_dir = str(tmp_path / "home" / "user" / ".claude")
    # do not create absent_dir
    policy = _make_policy(
        sha=_VALID_DIGEST,
        mounts=[
            {"path": str(tmp_path), "mode": "rw",
             "write_justification": "seat dir"},
            {"path": absent_dir, "mode": "ro"},  # absent optional
        ],
    )
    updated, warnings = _validate_contained_launch_plan(policy, sentinel)
    mount_paths = [e["path"] for e in updated["mount_manifest"]]
    assert absent_dir not in mount_paths
    assert any("skipping mount" in w for w in warnings)


def test_absent_config_claude_skipped(tmp_path):
    """Absent ~/.config/claude (optional) is skipped without refusal."""
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_dir = str(tmp_path / "home" / "user" / ".config" / "claude")
    policy = _make_policy(
        sha=_VALID_DIGEST,
        mounts=[
            {"path": str(tmp_path), "mode": "rw",
             "write_justification": "seat dir"},
            {"path": absent_dir, "mode": "ro"},
        ],
    )
    updated, warnings = _validate_contained_launch_plan(policy, sentinel)
    assert absent_dir not in [e["path"] for e in updated["mount_manifest"]]
    assert warnings  # warning emitted


def test_absent_required_path_refused(tmp_path):
    """Absent non-optional bind source is a hard refusal."""
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_required = str(tmp_path / "required" / "workspace")
    policy = _make_policy(
        sha=_VALID_DIGEST,
        mounts=[
            {"path": str(tmp_path), "mode": "rw",
             "write_justification": "seat dir"},
            {"path": absent_required, "mode": "ro"},  # absent, NOT optional
        ],
    )
    with pytest.raises(ContainedLaunchPreflightRefused,
                       match="bind source path does not exist"):
        _validate_contained_launch_plan(policy, sentinel)


def test_sentinel_not_covered_refused(tmp_path):
    """Sentinel wrapper outside all mount sources is refused."""
    sentinel = tmp_path / "other-dir" / "sentinel-wrapper.sh"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.touch()
    mounted_dir = tmp_path / "mounted"
    mounted_dir.mkdir()
    policy = _make_policy(
        sha=_VALID_DIGEST,
        mounts=[{"path": str(mounted_dir), "mode": "rw",
                 "write_justification": "workspace"}],
    )
    with pytest.raises(ContainedLaunchPreflightRefused,
                       match="not under any mounted source"):
        _validate_contained_launch_plan(policy, sentinel)


def test_sentinel_covered_passes(tmp_path):
    """Sentinel wrapper under a mounted source passes the coverage check."""
    mounted_dir = tmp_path / "repo"
    mounted_dir.mkdir()
    sentinel = mounted_dir / ".ce" / "state" / "sentinel-wrapper.sh"
    sentinel.parent.mkdir(parents=True)
    sentinel.touch()
    policy = _make_policy(
        sha=_VALID_DIGEST,
        mounts=[{"path": str(mounted_dir), "mode": "rw",
                 "write_justification": "repo root"}],
    )
    updated, warnings = _validate_contained_launch_plan(policy, sentinel)
    assert len(updated["mount_manifest"]) == 1


def test_returned_policy_excludes_absent_optional_mounts(tmp_path):
    """Updated policy has absent optional mounts removed from mount_manifest."""
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    present = tmp_path / "present"
    present.mkdir()
    absent_optional = str(tmp_path / "some" / "path" / ".codex")
    policy = _make_policy(
        sha=_VALID_DIGEST,
        mounts=[
            {"path": str(present), "mode": "ro"},
            {"path": absent_optional, "mode": "ro"},  # absent optional
        ],
    )
    # Sentinel is under present/
    sentinel_real = present / "sentinel-wrapper.sh"
    sentinel_real.touch()
    updated, warnings = _validate_contained_launch_plan(policy, sentinel_real)
    assert len(updated["mount_manifest"]) == 1
    assert updated["mount_manifest"][0]["path"] == str(present)


def test_empty_mount_manifest_with_uncovered_sentinel_refused(tmp_path):
    """Empty mount manifest means sentinel can never be covered — refused."""
    sentinel = tmp_path / "sentinel-wrapper.sh"
    policy = _make_policy(sha=_VALID_DIGEST, mounts=[])
    with pytest.raises(ContainedLaunchPreflightRefused,
                       match="not under any mounted source"):
        _validate_contained_launch_plan(policy, sentinel)


def test_no_warnings_when_all_mounts_present(tmp_path):
    """When all mounts exist, no warnings are emitted."""
    mounted = tmp_path / "workspace"
    mounted.mkdir()
    sentinel = mounted / "sentinel-wrapper.sh"
    sentinel.touch()
    policy = _make_policy(
        sha=_VALID_DIGEST,
        mounts=[{"path": str(mounted), "mode": "rw",
                 "write_justification": "workspace"}],
    )
    updated, warnings = _validate_contained_launch_plan(policy, sentinel)
    assert warnings == []
```

---

## Changelog fragment (`.ce/changelog/ce-490-contained-launch-preflight-s1.md`)

```markdown
## ce-490-contained-launch-preflight-s1

- fix(launch): add pre-spawn policy validation for contained launch — slice 1

  Adds `_validate_contained_launch_plan()` to launch_runtime and wires it into
  the contained-launch path (fires when `plan.runtime_policy is not None`, i.e.
  runtime-policy-backed contained launch only; bare and host-backend launches
  are unaffected).

  Three plan-time gaps are now caught BEFORE any docker/runtime side effect
  and surface named, actionable pre-spawn refusals
  (`G6-LAUNCH-POLICY-INVALID`):

  (a) Placeholder image digest (`sha256:000...000`) is detected and refused
      with instructions to re-run `ce onboard` after runtime_posture resolves.

  (b) Absent bind-mount sources are checked. Optional agent-config dirs
      (`~/.claude`, `~/.config/claude`, `~/.codex`, `~/.config/codex`) are
      conditionally omitted when absent (warning emitted). All other absent
      source paths are a hard refusal naming the missing path.

  (c) Sentinel wrapper path coverage is checked: the wrapper must be under at
      least one surviving mount source. If not, the launch is refused before
      docker is reached.

  Previously, all three cases silently reached docker, which either failed at
  container-creation time (rc=125, stderr not surfaced) or produced an
  unresolvable launch-probe timeout with no actionable message.

  Out of scope for slice 1: the sentinel HUP race / kill-session exited event,
  the zero-digest at `onboard --apply` (a HELD design gap), and live docker
  stderr forwarding when docker is still reached (best-effort in a later slice).

  - **Declared work class:** story
```

---

## PR carrier (`.ce/pr-manifests/ce-490-contained-launch-preflight-s1.md`)

```markdown
# PR path manifest — ce-490-contained-launch-preflight-s1

slug: ce-490-contained-launch-preflight-s1

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=426079710feb9a3048363f83dc544743777b94cceb38f65bee38a5f077621bc4

\`\`\`text
.ce/changelog/ce-490-contained-launch-preflight-s1.md
.ce/pr-manifests/ce-490-contained-launch-preflight-s1.md
validators/creator_engine_validator/launch_runtime.py
validators/tests/unit/test_contained_launch_preflight.py
\`\`\`
```

Compute AUTHORIZED_PATHS_SHA256 from the sorted path list if you need to
verify:

```python
import hashlib
paths = sorted([
    ".ce/changelog/ce-490-contained-launch-preflight-s1.md",
    ".ce/pr-manifests/ce-490-contained-launch-preflight-s1.md",
    "validators/creator_engine_validator/launch_runtime.py",
    "validators/tests/unit/test_contained_launch_preflight.py",
])
print(hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest())
# expected: 426079710feb9a3048363f83dc544743777b94cceb38f65bee38a5f077621bc4
```

---

## PR body template (use verbatim, fill in gate output)

```markdown
## Summary

- Add `_validate_contained_launch_plan()` to launch_runtime: pre-spawn policy
  validation for contained (runtime-policy-backed) launch.
- Catches three plan-time gaps BEFORE any docker/runtime side effect and emits
  named, actionable `G6-LAUNCH-POLICY-INVALID` refusals:
  (a) placeholder image digest (`sha256:000...000`)
  (b) absent bind-mount source paths — optional agent-config dirs are
      conditionally omitted; all other absent paths are hard refusals
  (c) sentinel wrapper path not covered by any surviving mount source
- `ce launch --backend host` and bare launch are unaffected (validation fires
  only when `plan.runtime_policy is not None`).
- Adds 10 fast unit tests covering all three validation branches.

**Declared work class: story**

## Validation

```bash
PYTHONPATH=validators .venv/bin/python -m pytest \
  validators/tests/unit/test_contained_launch_preflight.py -v
```

## Gate noise (pre-fill after running validate-pr)

<paste targeted test output here>

## Closes

Contained-launch plan-time preflight: three stacked pre-spawn gaps in the
contained-default launch lane now surface named, actionable refusals before
reaching docker. Fresh-tenant launch fragility — re-proved in today's Arad
rehearsal — is addressed at plan time.
```

---

## Preflight gate (run before pushing)

```bash
# From worktree root — TARGETED TESTS ONLY; never run full validate-pr in-seat
PYTHONPATH=validators .venv/bin/python -m pytest \
  validators/tests/unit/test_contained_launch_preflight.py -v

# Then controller-side (DGX host, not in-seat):
PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli \
  validate-pr --repo-root . --declared-work-class S
```

In-seat validation = TARGETED TESTS ONLY; never run full validate-pr
in-seat (resource kills); controller preflight is authoritative.

If validate-pr reports a path-manifest mismatch, recompute
AUTHORIZED_PATHS_SHA256 and update the carrier before pushing.

---

## Stop-lines (enforced)

1. No `ce_onboard.py` changes — the zero-digest source is a HELD design gap
   (runtime_posture HELD by design); detection at launch time is the correct
   s1 scope.
2. No `assertions.yaml` modifications — brain-ledger serialization is
   controller-side only; if any gate demands it, write BLOCKED immediately.
3. No `seat_lifecycle.py` changes — the sentinel HUP race is out of scope
   for s1.
4. No `validate-pr` in-seat — resource kills the runsc container; targeted
   pytest run only.
5. No READY file committed.
6. No ce-ops# references in PR body, commit messages, or code comments.
7. Diff must be zero on all five brain-pinned files listed in the brain-pin
   precompute table above.
