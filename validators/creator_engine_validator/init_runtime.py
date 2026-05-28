"""RV1-062 — ``ce init`` runtime: idempotent local v1.0 kernel state init.

``ce init`` prepares the repository-local ``.hermes/`` governed state tree that
the kernel reads and writes (Active-Work Ledger, Side-Effect Ledger,
container-instance records, transcripts, handoffs, session state). It is
**idempotent** (safe to re-run; never clobbers existing ledger content) and
**fail-closed**: it refuses to write ungoverned state (``.hermes/`` not ignored),
refuses outside a git work tree, and refuses to overwrite a tracked artifact.

It writes only under the ignored ``.hermes/`` root and uses stdlib ``json`` for
the machine-readable init marker (no TOML writer dependency; format split B6/B7).
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

# Governed state directories the kernel requires (repo-relative, POSIX).
KERNEL_STATE_DIRS: tuple[str, ...] = (
    ".hermes",
    ".hermes/active-work-ledger",
    ".hermes/active-work-ledger/claims",
    ".hermes/active-work-ledger/leases",
    ".hermes/active-work-ledger/panes",
    ".hermes/active-work-ledger/events",
    ".hermes/side-effect-ledger",
    ".hermes/container-instances",
    ".hermes/transcripts",
    ".hermes/handoffs",
    ".hermes/session-state",
    ".hermes/launch",
    ".hermes/launch/ce-controller",
    ".hermes/launch/ce-controller/mcp",
)

MARKER_NAME = ".ce-init.json"
DEFAULT_CONTROLLER_MCP_CONFIG = ".hermes/launch/ce-controller/mcp/ce-mcp.json"
DEFAULT_MCP_CONFIG_PAYLOAD = {"mcpServers": {}}


class InitError(Exception):
    code = "G6-INIT-ERROR"


class InitRefused(InitError):
    code = "G6-INIT-REFUSED"


@dataclass(frozen=True)
class InitResult:
    repo_root: Path
    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    marker_path: Path | None = None

    def to_dict(self) -> dict:
        return {
            "repo_root": str(self.repo_root),
            "created": list(self.created),
            "existing": list(self.existing),
            "marker_path": str(self.marker_path) if self.marker_path else None,
        }


def marker_path(repo_root: Path | str) -> Path:
    return Path(repo_root) / ".hermes" / MARKER_NAME


def default_controller_mcp_config_path(repo_root: Path | str) -> Path:
    return Path(repo_root) / DEFAULT_CONTROLLER_MCP_CONFIG


def _write_default_mcp_config_if_missing(repo_root: Path) -> None:
    target = default_controller_mcp_config_path(repo_root)
    if target.exists():
        if not target.is_file():
            raise InitRefused(
                f"refusing to overwrite non-file at default MCP config path: {DEFAULT_CONTROLLER_MCP_CONFIG}"
            )
        return
    target.write_text(
        json.dumps(DEFAULT_MCP_CONFIG_PAYLOAD, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _git(repo_root: Path, args: Sequence[str]):
    return subprocess.run(
        ["git", "-C", str(repo_root), *args], check=False, capture_output=True, text=True
    )


def _is_git_work_tree(repo_root: Path) -> bool:
    try:
        proc = _git(repo_root, ["rev-parse", "--is-inside-work-tree"])
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return (repo_root / ".git").exists()
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _hermes_ignored(repo_root: Path) -> bool:
    try:
        proc = _git(repo_root, ["check-ignore", ".hermes/__ce_init_probe__"])
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        gitignore = repo_root / ".gitignore"
        if not gitignore.is_file():
            return False
        return any(
            line.strip().rstrip("/") == ".hermes"
            for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
        )
    return proc.returncode == 0


def _tracked_under_hermes(repo_root: Path) -> list[str]:
    try:
        proc = _git(repo_root, ["ls-files", "--", ".hermes"])
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def init_repo(repo_root: Path | str, *, now: datetime | None = None) -> InitResult:
    """Idempotently initialize the local kernel ``.hermes/`` state tree.

    Refuses (``InitRefused``) outside a git work tree, when ``.hermes/`` is not
    git-ignored, or when a tracked artifact occupies a target state path.
    """
    root = Path(repo_root)
    if not root.is_dir():
        raise InitRefused(f"repo root not found: {root}")
    if not _is_git_work_tree(root):
        raise InitRefused(f"{root} is not a git work tree; ce init requires a governed repo")
    if not _hermes_ignored(root):
        raise InitRefused(
            ".hermes/ is not git-ignored; refusing to initialize ungoverned/tracked state"
        )

    tracked = _tracked_under_hermes(root)
    if tracked:
        raise InitRefused(
            "refusing to overwrite tracked artifact(s) under .hermes/: " + ", ".join(sorted(tracked))
        )

    # Pre-flight target sanity: a non-directory occupying a target path is a
    # collision we will not clobber.
    for rel in KERNEL_STATE_DIRS:
        target = root / rel
        if target.exists() and not target.is_dir():
            raise InitRefused(f"refusing to overwrite non-directory at state path: {rel}")

    created: list[str] = []
    existing: list[str] = []
    for rel in KERNEL_STATE_DIRS:
        target = root / rel
        if target.is_dir():
            existing.append(rel)
        else:
            target.mkdir(parents=True, exist_ok=True)
            created.append(rel)

    # CE-owned default MCP config for strict governed Claude launches. Preserve
    # user/operator edits on re-init; the file is config-posture only and
    # intentionally inherits no global/user MCP servers.
    _write_default_mcp_config_if_missing(root)

    # CE-owned machine marker (ignored state; safe to (re)write idempotently).
    timestamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    mpath = marker_path(root)
    marker = {
        "kind": "ce-init-marker",
        "schema_version": "1",
        "initialized_at": timestamp,
        "state_dirs": list(KERNEL_STATE_DIRS),
    }
    mpath.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return InitResult(repo_root=root, created=created, existing=existing, marker_path=mpath)
