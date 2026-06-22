"""Integration tests for the committed ``ce-pretooluse.sh`` hook (CC-G-C).

These run the real POSIX-sh hook as a subprocess — exactly as Claude Code
would — feeding it a hook event on stdin with ``CLAUDE_PROJECT_DIR`` pointed
at a governed or ungoverned posture fixture. The hook is a thin Ring 1
wrapper around ``creator_engine_validator hook-check --format claude``; the
decision semantics belong to the Ring 2 validator (covered elsewhere). Here
we prove the wrapper wires posture, scope, secret, mechanics, the evidence
root, and fail-open behavior correctly and always exits 0.

The hook locates the validator package relative to its own committed repo
(``CE_HOOK_REPO_ROOT``, default = the script's ``../..``), so a tmp posture
fixture under ``CLAUDE_PROJECT_DIR`` does not need its own copy of
``validators/``.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from creator_engine_validator import brain_bootstrap

REPO_ROOT = Path(__file__).resolve().parents[3]
PRETOOLUSE = REPO_ROOT / ".claude/hooks/ce-pretooluse.sh"

# The hook's invocation fallback is console-script -> `python3 -m` -> `python -m`.
# In a governed launch (Ring 0 / CC-G-D) the validator's deps-complete
# interpreter is on PATH; here the ambient `python3` may lack pyyaml/jsonschema,
# in which case posture resolution fails soft to ungoverned (intentional Ring 1
# fail-open). To reproduce the governed-launch precondition deterministically we
# put a deps-complete `python3` (the test interpreter) first on PATH.
_DEPS_BIN = None


@pytest.fixture(scope="module", autouse=True)
def _deps_complete_python3(tmp_path_factory):
    global _DEPS_BIN
    shim = tmp_path_factory.mktemp("hook-python3")
    # A wrapper that execs the test interpreter by its real venv path keeps the
    # venv site-packages on sys.path (a bare symlink would not). The hook's
    # `command -v python3` then resolves to a deps-complete interpreter.
    wrapper = shim / "python3"
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    wrapper.chmod(0o755)
    _DEPS_BIN = str(shim)
    yield
    _DEPS_BIN = None


def _sha_for(paths):
    normalized = "\n".join(sorted(set(p for p in paths if p))) + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _build_governed_root(root: Path, manifest_paths) -> Path:
    """Create a governed posture root: a live tmux pane bound to a live
    unreleased claim whose envelope_ref points at a handoff carrying a fenced
    ALLOWED_PATHS manifest. Mirrors the canonical hook path."""
    claims = root / ".hermes/active-work-ledger/claims/hermes-primary"
    panes = root / ".hermes/pane-registry"
    claims.mkdir(parents=True)
    panes.mkdir(parents=True)
    (claims / "lane.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        'schema_version: "1"\n'
        "controller_id: hermes-primary\n"
        "lane_id: e2e-lane\n"
        'record_timestamp: "source-controlled:lane.yaml"\n'
        "worktree_path: /worktrees/e2e-lane\n"
        "envelope_ref: .hermes/handoff.md\n"
        "lease_seconds: 3600\n"
        'claimed_at: "source-controlled:lane.yaml"\n'
        'last_heartbeat_at: "source-controlled:lane.yaml"\n',
        encoding="utf-8",
    )
    (panes / "pane.yaml").write_text(
        "kind: pane-registry-record\n"
        "record_type: pane_identity\n"
        'schema_version: "1"\n'
        "controller_id: hermes-primary\n"
        "lane_id: e2e-lane\n"
        "claim_ref: ../active-work-ledger/claims/hermes-primary/lane.yaml\n"
        "host_id: workstation-a\n"
        "pane_id: pane-e2e-001\n"
        "role: implementer\n"
        "status: active\n"
        'record_timestamp: "2026-05-26T00:00:00Z"\n'
        "visibility: operator_visible\n"
        "terminal:\n"
        "  kind: tmux\n"
        "  session_id: ce\n"
        "  window_id: w\n"
        "  pane_id: '1'\n"
        'registered_at: "2026-05-26T00:00:00Z"\n'
        "last_seen_at: source-controlled:pane.yaml\n",
        encoding="utf-8",
    )
    ordered = sorted(set(manifest_paths))
    block = "\n".join(ordered)
    (root / ".hermes/handoff.md").write_text(
        "# handoff\n\n"
        f"ALLOWED_PATHS_COUNT={len(ordered)}\n"
        f"ALLOWED_PATHS_SHA256={_sha_for(ordered)}\n\n"
        f"```text\n{block}\n```\n",
        encoding="utf-8",
    )
    return root


def _run_hook(event, project_dir: Path, extra_env=None, stdin_text=None):
    env = dict(os.environ)
    if _DEPS_BIN:
        env["PATH"] = _DEPS_BIN + os.pathsep + env.get("PATH", "")
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    if extra_env:
        env.update(extra_env)
    payload = stdin_text if stdin_text is not None else json.dumps(event)
    return subprocess.run(
        [str(PRETOOLUSE)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
    )


def _bootstrap_env(root: Path, seat_class: str) -> dict[str, str]:
    payload = {
        "kind": brain_bootstrap.BOOTSTRAP_KIND,
        "schema_version": brain_bootstrap.BOOTSTRAP_SCHEMA_VERSION,
        "context": {
            "role": "implementer",
            "seat_class": seat_class,
            "scope": {"seat_class": seat_class},
        },
        "knowledge_ssot": {
            "ledger_path": ".ce/state/brain/assertions.yaml",
            "record_count": 0,
            "active_count": 0,
            "scope_relevant_count": 0,
            "head_content_hash": None,
            "assertions": [],
        },
    }
    ref = root / f"brain-bootstrap-{seat_class}.json"
    digest = brain_bootstrap.write_payload(ref, payload)
    return {
        brain_bootstrap.BOOTSTRAP_REF_ENV: str(ref),
        brain_bootstrap.BOOTSTRAP_SHA256_ENV: digest,
    }


def _permission(proc):
    """Parse the Claude PreToolUse permissionDecision, or None when the hook
    emitted no decision (fail-open / allow)."""
    out = proc.stdout.strip()
    if not out:
        return None
    payload = json.loads(out)
    return payload.get("hookSpecificOutput", {}).get("permissionDecision")


def _governed_event(tool_name, tool_input):
    return {"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input}


def test_governed_out_of_manifest_edit_advisory_allows(tmp_path):
    # G-i (v3 kickoff): a governed path-manifest mismatch is now ADVISORY end to
    # end — the hook emits permissionDecision "allow" with the advisory context
    # in the reason, NOT a hard deny. Scope containment moves to the PR-diff gate
    # (path_manifest_fidelity --base). Secret/mechanic denies stay hard (below).
    root = _build_governed_root(tmp_path, ["docs/keep.md"])
    proc = _run_hook(_governed_event("Edit", {"file_path": "docs/other.md"}), root)
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    hso = out["hookSpecificOutput"]
    assert hso["permissionDecision"] == "allow"
    assert "advisory" in hso["permissionDecisionReason"]


def test_governed_in_manifest_edit_allows(tmp_path):
    root = _build_governed_root(tmp_path, ["docs/keep.md"])
    proc = _run_hook(
        _governed_event("Edit", {"file_path": "docs/keep.md"}),
        root,
        extra_env=_bootstrap_env(root, "worker"),
    )
    assert proc.returncode == 0
    assert _permission(proc) == "allow"


def test_governed_secret_read_denies(tmp_path):
    root = _build_governed_root(tmp_path, ["docs/keep.md"])
    proc = _run_hook(_governed_event("Read", {"file_path": ".env"}), root)
    assert proc.returncode == 0
    assert _permission(proc) == "deny"


def test_governed_git_push_denies(tmp_path):
    root = _build_governed_root(tmp_path, ["docs/keep.md"])
    proc = _run_hook(_governed_event("Bash", {"command": "git push origin main"}), root)
    assert proc.returncode == 0
    assert _permission(proc) == "deny"


def test_governed_coordination_bash_allows(tmp_path):
    root = _build_governed_root(tmp_path, ["docs/keep.md"])
    proc = _run_hook(_governed_event("Bash", {"command": "git status --short"}), root)
    assert proc.returncode == 0
    assert _permission(proc) == "allow"


def test_governed_evidence_write_allows_via_evidence_root(tmp_path):
    # `.hermes/**` writes are allowed because the wrapper passes
    # `--evidence-root .hermes`, even though they are not in the manifest.
    root = _build_governed_root(tmp_path, ["docs/keep.md"])
    proc = _run_hook(_governed_event("Write", {"file_path": ".hermes/run/evidence.txt"}), root)
    assert proc.returncode == 0
    assert _permission(proc) == "allow"


def test_ungoverned_out_of_manifest_advisory_allows(tmp_path):
    # No posture inputs under CLAUDE_PROJECT_DIR -> ungoverned -> advisory allow.
    proc = _run_hook(_governed_event("Edit", {"file_path": "docs/other.md"}), tmp_path)
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    hso = out["hookSpecificOutput"]
    assert hso["permissionDecision"] == "allow"
    assert "advisory" in hso["permissionDecisionReason"]


def test_missing_validator_fails_open(tmp_path):
    # Point the hook's validator-repo root at an empty dir so the package is
    # unimportable; the hook must fail open: exit 0, emit no blocking decision.
    empty_repo = tmp_path / "empty-repo"
    empty_repo.mkdir()
    root = _build_governed_root(tmp_path / "governed", ["docs/keep.md"])
    proc = _run_hook(
        _governed_event("Edit", {"file_path": "docs/other.md"}),
        root,
        extra_env={"CE_HOOK_REPO_ROOT": str(empty_repo)},
    )
    assert proc.returncode == 0
    assert _permission(proc) != "deny"


def test_malformed_event_fails_open(tmp_path):
    root = _build_governed_root(tmp_path, ["docs/keep.md"])
    proc = _run_hook(None, root, stdin_text="{not valid json")
    assert proc.returncode == 0
    assert _permission(proc) != "deny"
