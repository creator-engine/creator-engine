"""CE v3 forge-native branch-push primitive (v3.1-G2a) — the missing push leg before ``open_change``.

``forge.open_change`` (G-3.0) ASSUMES the head branch is already on the remote — it only
GETs/POSTs ``repos/{repo}/pulls``. Nothing in v3 ever pushed that branch: the governed seat
(``v3_seat_bridge``) authors and commits LOCALLY but is push-denied (Ring-1 classifies
``git push`` → ``deploy``), and the orchestrator/Operator does the push by hand. :func:`push_change`
closes that gap — it is the sibling of ``change.py``/``merge.py`` for the *ship* step: push the
seat's authored ``refs/heads/<branch>`` to the remote so ``open_change`` can claim its PR.

Like the rest of ``forge/`` it is **plan-by-default** and talks to git only through an injectable
``spawn`` seam (the live ``subprocess.run`` by default):

* ``apply=False`` (default) READS the remote ref state (``git ls-remote`` through the authenticated
  child env) and the local head, and RETURNS a :class:`PushResult` describing the would-push plan
  WITHOUT mutating anything.
* ``apply=True`` (never run against a live remote in CI) pushes ``refs/heads/<branch>`` to the
  remote, is a verified no-op when the remote ref already equals the local head, and **refuses a
  non-fast-forward** (it NEVER force-pushes).
* Before any remote read or mutation, a deterministic supersession guard compares the would-push
  branch with the current base ref and refuses stale duplicate/regressive courier pushes.

Defensive invariants (deliberate, load-bearing):

* **The HTTPS remote URL is CONSTRUCTED** (``https://github.com/<repo>``) — never the configured
  ``origin`` (the laptop's SSH:22 to github.com is firewalled; a live push must ride HTTPS). The
  configured remote is never consulted.
* **Never force.** The push targets ``refs/heads/<branch>:refs/heads/<branch>`` with NO
  ``--force``/``--force-with-lease``; a remote ref that is not an ancestor of the local head is
  REFUSED (:class:`PushRefused`) — a non-fast-forward is a workflow problem, not something to paper
  over by overwriting the remote.
* **Credential hygiene = the ``credential_runner`` pattern verbatim** (this module mints no token;
  it is HANDED a :class:`~.scoped_token.ScopedToken`). Each authenticated git call builds a FRESH
  child env from ``os.environ`` with the competing-auth / endpoint-debug-redirect / App-private-key
  vars dropped (the ``credential_runner.py`` conventions, re-defined locally so that frozen sibling
  stays byte-unchanged) and ``GH_TOKEN`` set to the scoped token value; git authenticates the HTTPS
  push via ``-c credential.helper=`` + ``-c credential.helper=!gh auth git-credential`` (gh's
  documented env precedence). The token value lands in the child ENV ONLY — never the argv, a log,
  the returned process, disk, or a record.
* **Refuse a malformed request BEFORE any git call** (refuse-before-side-effect): a malformed
  ``repo``, an empty ``branch``, a credential-less ``token``, or a missing/absent local branch is
  refused before ``spawn`` is ever invoked.
* **Refuse a superseded branch BEFORE any remote call**: branch-added paths already present on the
  base ref, path overlap with base-side changes since merge-base, ADR/decision number collisions,
  regressive ``base -> branch`` net-negative diffs, and stale bases all deny before ``ls-remote``.

Network/subprocess only behind the injectable ``spawn`` seam; tests inject a fake and perform ZERO
live git / network. Importing this module performs no I/O and registers no validator check (so
``--list-checks`` stays byte-identical).

Defensive only — pushing our own governed seat's authored branch to our own remote so the pipeline
can open its PR; never offensive (no force-push, no history rewrite, no detection evasion).
"""
from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from ._redact import redact_gh_stderr
from .github_repo_config import ForgeConfigError, ForgeConfigRefused
from .scoped_token import ScopedToken

# Re-defined LOCALLY (literal copied from ``scoped_token.py`` / ``change.py``) per the established
# forge convention, so the frozen sibling modules stay byte-unchanged and this module couples to none.
_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")

#: Competing ambient auth env vars dropped from the child so the scoped ``GH_TOKEN`` is unambiguous
#: (the ``credential_runner.py:48`` convention, re-defined locally).
_NEUTRALIZED_AUTH_ENV = ("GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
#: Endpoint/debug host vars scrubbed so an inherited host var can neither redirect auth to a
#: non-github host nor echo the bearer via gh's debug (the ``credential_runner.py:55`` convention).
_SCRUBBED_CHILD_ENV = ("GH_DEBUG", "GH_HOST", "GH_CONFIG_DIR", "GITHUB_API_URL")

#: The authenticated-git config args: clear any inherited helper, then route credentials through
#: ``gh auth git-credential`` (which reads ``GH_TOKEN`` from the env). The token never enters argv.
_GH_CREDENTIAL_ARGS = ("-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential")
_ADR_NUMBER_RE = re.compile(r"(?:^|/)ADR-(\d{4,})[-_.]")


class PushRefused(ForgeConfigRefused):
    """A push request was refused on a precondition BEFORE (or in lieu of) the push.

    Raised when the request is malformed (bad ``repo``, empty ``branch``, credential-less
    ``token``), the local branch is absent, or — load-bearing — the remote ref is NOT an ancestor
    of the local head (a non-fast-forward; this primitive never force-pushes). A *policy* refusal —
    distinct from a *transport* :class:`~.github_repo_config.ForgeConfigError`.
    """

    code = "V3-FORGE-PUSH-REFUSED"


@dataclass(frozen=True)
class PushResult:
    """The desired-state result of pushing (or planning to push) one branch — secret-free.

    Carries ONLY non-secret data: the ``repo``/``branch`` it targets, the CONSTRUCTED HTTPS
    ``remote_url``, the ``local_head``/``remote_head`` shas it reconciled (``remote_head`` is
    ``None`` when the branch is not yet on the remote), and the ``changed``/``up_to_date``/
    ``applied``/``pushed`` desired-state flags. It holds NO token value (auth stays in the child
    git env).
    """

    repo: str
    branch: str
    remote_url: str
    local_head: str
    remote_head: str | None
    changed: bool
    up_to_date: bool
    applied: bool
    pushed: bool

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "branch": self.branch,
            "remote_url": self.remote_url,
            "local_head": self.local_head,
            "remote_head": self.remote_head,
            "changed": self.changed,
            "up_to_date": self.up_to_date,
            "applied": self.applied,
            "pushed": self.pushed,
        }


@dataclass(frozen=True)
class SupersessionPolicy:
    """Pure policy knobs for refusing stale/superseded branch pushes."""

    base_ref: str = "origin/main"
    max_net_negative_lines: int = 500
    max_base_commits_since_merge_base: int = 50
    max_base_seconds_since_merge_base: int = 48 * 60 * 60


@dataclass(frozen=True)
class SupersessionFacts:
    """Immutable git facts used by the supersession evaluator; carries no secrets."""

    base_ref: str
    base_head: str
    branch_head: str
    merge_base: str
    branch_added_paths: frozenset[str]
    branch_changed_paths: frozenset[str]
    base_paths: frozenset[str]
    base_changed_paths_since_merge_base: frozenset[str]
    branch_added_adr_numbers: frozenset[str]
    base_adr_numbers: frozenset[str]
    base_to_branch_added_lines: int
    base_to_branch_deleted_lines: int
    base_commits_since_merge_base: int
    base_seconds_since_merge_base: int

    @property
    def net_negative_lines(self) -> int:
        return self.base_to_branch_deleted_lines - self.base_to_branch_added_lines


@dataclass(frozen=True)
class SupersessionCheck:
    """One deterministic guard check result."""

    code: str
    passed: bool
    detail: str
    offenders: tuple[str, ...] = ()


@dataclass(frozen=True)
class SupersessionDecision:
    """Pure supersession decision: allow iff every check passed."""

    allowed: bool
    checks: tuple[SupersessionCheck, ...]

    @property
    def failed_checks(self) -> tuple[SupersessionCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)


def evaluate_supersession(
    facts: SupersessionFacts,
    policy: SupersessionPolicy = SupersessionPolicy(),
) -> SupersessionDecision:
    """Pure deterministic supersession decision for one would-push branch.

    All inputs are already-extracted git facts. A single failed check denies the
    push before any remote mutation, intentionally favoring over-exclusion over
    duplicate or regressive autonomous couriering.
    """
    added_on_base = tuple(sorted(facts.branch_added_paths.intersection(facts.base_paths)))
    base_overlap = tuple(
        sorted(facts.branch_changed_paths.intersection(facts.base_changed_paths_since_merge_base))
    )
    adr_overlap = tuple(sorted(facts.branch_added_adr_numbers.intersection(facts.base_adr_numbers)))
    checks = (
        SupersessionCheck(
            "added_path_already_on_base",
            not added_on_base,
            "branch-added paths are absent from the current base"
            if not added_on_base else
            "branch-added paths already exist on the current base",
            added_on_base,
        ),
        SupersessionCheck(
            "base_changed_path_overlap",
            not base_overlap,
            "branch paths do not overlap paths changed on base since merge-base"
            if not base_overlap else
            "branch paths overlap paths changed on base since merge-base",
            base_overlap,
        ),
        SupersessionCheck(
            "adr_number_available",
            not adr_overlap,
            "branch-added ADR/decision numbers are not already present on base"
            if not adr_overlap else
            "branch-added ADR/decision numbers already exist on base",
            adr_overlap,
        ),
        SupersessionCheck(
            "net_negative_within_threshold",
            facts.net_negative_lines <= policy.max_net_negative_lines,
            (
                f"net-negative lines {facts.net_negative_lines} <= "
                f"{policy.max_net_negative_lines}"
            )
            if facts.net_negative_lines <= policy.max_net_negative_lines else
            (
                f"net-negative lines {facts.net_negative_lines} exceed "
                f"{policy.max_net_negative_lines}"
            ),
        ),
        SupersessionCheck(
            "base_commits_within_threshold",
            facts.base_commits_since_merge_base <= policy.max_base_commits_since_merge_base,
            (
                f"base moved {facts.base_commits_since_merge_base} commit(s) since merge-base "
                f"<= {policy.max_base_commits_since_merge_base}"
            )
            if facts.base_commits_since_merge_base <= policy.max_base_commits_since_merge_base else
            (
                f"base moved {facts.base_commits_since_merge_base} commit(s) since merge-base "
                f"> {policy.max_base_commits_since_merge_base}"
            ),
        ),
        SupersessionCheck(
            "base_age_within_threshold",
            facts.base_seconds_since_merge_base <= policy.max_base_seconds_since_merge_base,
            (
                f"base is {facts.base_seconds_since_merge_base}s newer than merge-base "
                f"<= {policy.max_base_seconds_since_merge_base}s"
            )
            if facts.base_seconds_since_merge_base <= policy.max_base_seconds_since_merge_base else
            (
                f"base is {facts.base_seconds_since_merge_base}s newer than merge-base "
                f"> {policy.max_base_seconds_since_merge_base}s"
            ),
        ),
    )
    return SupersessionDecision(allowed=all(check.passed for check in checks), checks=checks)


#: The injectable git transport: ``(argv, input_text, env) -> CompletedProcess`` (the
#: ``credential_runner`` spawn shape). CI injects a fake; the default is the lone live shell.
GitSpawn = "Callable[[Sequence[str], str | None, dict[str, str]], subprocess.CompletedProcess]"


def _default_spawn(  # pragma: no cover - the lone live git shell; tests inject a fake spawn
    argv: Sequence[str], input_text: str | None, env: dict[str, str]
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, env=env, timeout=60
    )


def _is_app_key_var(name: str) -> bool:
    """True for an env var that could carry the GitHub App private key (dropped from the child).

    Mirrors ``credential_runner._is_app_key_var`` — any ``*_PEM`` / ``*PRIVATE_KEY*`` / ``*APP_KEY*``
    inherited from ``os.environ`` must never reach a child git/gh env.
    """
    upper = name.upper()
    return upper.endswith("_PEM") or "PRIVATE_KEY" in upper or "APP_KEY" in upper


def _child_env(token: ScopedToken | None) -> dict[str, str]:
    """A fresh child env from ``os.environ`` with competing-auth / redirect / App-key vars dropped.

    When ``token`` is given, ``GH_TOKEN`` is set to its value (the live secret in the ENV ONLY —
    never argv/log/disk/record); local read-only git calls pass ``None`` (no credential needed).
    The parent ``os.environ`` is never mutated.
    """
    env = dict(os.environ)
    for name in _NEUTRALIZED_AUTH_ENV + _SCRUBBED_CHILD_ENV:
        env.pop(name, None)
    for name in [k for k in env if _is_app_key_var(k)]:
        env.pop(name, None)
    if token is not None:
        env["GH_TOKEN"] = token.value  # scoped token only — never the argv, never logged
    return env


def _https_remote_url(repo: str) -> str:
    """The CONSTRUCTED HTTPS remote URL — never the configured (possibly SSH) origin."""
    return f"https://github.com/{repo}"


def _local_head(spawn, source_dir: str, branch: str) -> str:
    """Resolve the local ``refs/heads/<branch>`` sha; refuse if the branch is absent locally."""
    proc = spawn(
        ["git", "-C", str(source_dir), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        None,
        _child_env(None),
    )
    out = (getattr(proc, "stdout", "") or "").strip()
    if getattr(proc, "returncode", 1) != 0 or not out:
        raise PushRefused(
            f"local branch {branch!r} not found under {source_dir!r}; refusing to push a branch "
            "the seat never authored (refuse-before-side-effect)"
        )
    return out


def _git_stdout(spawn, source_dir: str, args: Sequence[str], *, purpose: str) -> str:
    """Run one local read-only git probe; failure is a fail-closed policy refusal."""
    proc = spawn(["git", "-C", str(source_dir), *args], None, _child_env(None))
    if getattr(proc, "returncode", 1) != 0:
        detail = (getattr(proc, "stderr", "") or "").strip() or "unknown error"
        raise PushRefused(
            f"supersession guard could not {purpose}: {detail}; refusing before push"
        )
    return (getattr(proc, "stdout", "") or "").strip()


def _parse_name_status(stdout: str) -> tuple[frozenset[str], frozenset[str]]:
    added: set[str] = set()
    changed: set[str] = set()
    for raw in stdout.splitlines():
        parts = raw.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        path = parts[-1].strip()
        if not path:
            continue
        code = status[:1]
        if code != "D":
            changed.add(path)
        if code == "A":
            added.add(path)
    return frozenset(added), frozenset(changed)


def _parse_path_lines(stdout: str) -> frozenset[str]:
    return frozenset(line.strip() for line in stdout.splitlines() if line.strip())


def _parse_numstat(stdout: str) -> tuple[int, int]:
    added = 0
    deleted = 0
    for raw in stdout.splitlines():
        parts = raw.split("\t")
        if len(parts) < 3:
            continue
        try:
            added += int(parts[0])
            deleted += int(parts[1])
        except ValueError:
            continue
    return added, deleted


def _parse_int(raw: str, *, purpose: str) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise PushRefused(
            f"supersession guard could not parse {purpose}; refusing before push"
        ) from exc


def _adr_numbers(paths: frozenset[str]) -> frozenset[str]:
    numbers: set[str] = set()
    for path in paths:
        match = _ADR_NUMBER_RE.search(path)
        if match:
            numbers.add(match.group(1))
    return frozenset(numbers)


def _collect_supersession_facts(
    spawn,
    source_dir: str,
    branch: str,
    branch_head: str,
    policy: SupersessionPolicy,
) -> SupersessionFacts:
    """Extract value-free local git facts for the supersession guard."""
    base_ref = (policy.base_ref or "").strip()
    if not base_ref:
        raise PushRefused("supersession guard base_ref is empty; refusing before push")
    base_head = _git_stdout(
        spawn,
        source_dir,
        ["rev-parse", "--verify", "--quiet", base_ref],
        purpose=f"resolve base ref {base_ref!r}",
    )
    if not base_head:
        raise PushRefused(f"supersession guard found empty base ref {base_ref!r}; refusing before push")
    merge_base = _git_stdout(
        spawn,
        source_dir,
        ["merge-base", base_head, branch_head],
        purpose=f"compute merge-base for {base_ref!r} and {branch!r}",
    )
    if not merge_base:
        raise PushRefused("supersession guard found empty merge-base; refusing before push")

    branch_status = _git_stdout(
        spawn,
        source_dir,
        ["diff", "--name-status", merge_base, branch_head],
        purpose="read branch changed paths",
    )
    branch_added_paths, branch_changed_paths = _parse_name_status(branch_status)
    base_paths = _parse_path_lines(
        _git_stdout(
            spawn,
            source_dir,
            ["ls-tree", "-r", "--name-only", base_head],
            purpose=f"list paths at {base_ref!r}",
        )
    )
    base_changed_paths = _parse_path_lines(
        _git_stdout(
            spawn,
            source_dir,
            ["diff", "--name-only", merge_base, base_head],
            purpose=f"read paths changed on {base_ref!r} since merge-base",
        )
    )
    base_to_branch_added, base_to_branch_deleted = _parse_numstat(
        _git_stdout(
            spawn,
            source_dir,
            ["diff", "--numstat", base_head, branch_head],
            purpose=f"read {base_ref!r} to branch diff numstat",
        )
    )
    base_commits = _parse_int(
        _git_stdout(
            spawn,
            source_dir,
            ["rev-list", "--count", f"{merge_base}..{base_head}"],
            purpose=f"count {base_ref!r} commits since merge-base",
        ),
        purpose="base commit count",
    )
    base_time = _parse_int(
        _git_stdout(
            spawn,
            source_dir,
            ["show", "-s", "--format=%ct", base_head],
            purpose=f"read {base_ref!r} commit time",
        ),
        purpose="base commit time",
    )
    merge_base_time = _parse_int(
        _git_stdout(
            spawn,
            source_dir,
            ["show", "-s", "--format=%ct", merge_base],
            purpose="read merge-base commit time",
        ),
        purpose="merge-base commit time",
    )
    return SupersessionFacts(
        base_ref=base_ref,
        base_head=base_head,
        branch_head=branch_head,
        merge_base=merge_base,
        branch_added_paths=branch_added_paths,
        branch_changed_paths=branch_changed_paths,
        base_paths=base_paths,
        base_changed_paths_since_merge_base=base_changed_paths,
        branch_added_adr_numbers=_adr_numbers(branch_added_paths),
        base_adr_numbers=_adr_numbers(base_paths),
        base_to_branch_added_lines=base_to_branch_added,
        base_to_branch_deleted_lines=base_to_branch_deleted,
        base_commits_since_merge_base=base_commits,
        base_seconds_since_merge_base=max(0, base_time - merge_base_time),
    )


def _enforce_supersession_guard(
    spawn,
    source_dir: str,
    branch: str,
    branch_head: str,
    policy: SupersessionPolicy,
) -> None:
    facts = _collect_supersession_facts(spawn, source_dir, branch, branch_head, policy)
    decision = evaluate_supersession(facts, policy)
    if decision.allowed:
        return
    rendered = "; ".join(
        f"{check.code}: {check.detail}"
        + (f" ({', '.join(check.offenders[:5])})" if check.offenders else "")
        for check in decision.failed_checks
    )
    raise PushRefused(
        f"supersession guard refused branch {branch!r} against {policy.base_ref!r}: "
        f"{rendered}"
    )


def _ls_remote(spawn, source_dir: str, url: str, branch: str, token: ScopedToken) -> str | None:
    """The remote ``refs/heads/<branch>`` sha via authenticated ``git ls-remote``, or ``None``."""
    proc = spawn(
        [
            "git", "-C", str(source_dir), *_GH_CREDENTIAL_ARGS,
            "ls-remote", url, f"refs/heads/{branch}",
        ],
        None,
        _child_env(token),
    )
    if getattr(proc, "returncode", 1) != 0:
        raise ForgeConfigError(
            f"could not read remote ref for {url} {branch}: "
            f"{redact_gh_stderr(getattr(proc, 'stderr', '') or '') or 'unknown error'}"
        )
    out = (getattr(proc, "stdout", "") or "").strip()
    if not out:
        return None  # branch not yet on the remote
    first = out.splitlines()[0].split("\t", 1)[0].split()[0].strip()
    return first or None


def _is_ancestor(spawn, source_dir: str, ancestor: str, descendant: str) -> bool:
    """True iff ``ancestor`` is an ancestor of ``descendant`` (a fast-forward is possible).

    ``git merge-base --is-ancestor`` exits 0 (ancestor), 1 (NOT an ancestor), or other (the
    object is missing locally / git error). Only a clean 0 proves a fast-forward; everything else
    is treated as "cannot fast-forward" so the caller refuses rather than ever force-pushing.
    """
    proc = spawn(
        ["git", "-C", str(source_dir), "merge-base", "--is-ancestor", ancestor, descendant],
        None,
        _child_env(None),
    )
    return getattr(proc, "returncode", 1) == 0


def _validate(repo: str, branch: str, token: ScopedToken) -> None:
    """Refuse a malformed / credential-less request BEFORE any git call."""
    if not _REPO_RE.match(repo or ""):
        raise PushRefused(f"repo {repo!r} is not in owner/name form")
    if not (branch or "").strip():
        raise PushRefused("branch must be a non-empty head branch")
    if not getattr(token, "value", ""):
        raise PushRefused(
            "scoped token carries no value; refusing to push (a credential-less push would "
            "silently fall back to ambient auth)"
        )


def push_change(
    repo: str,
    branch: str,
    *,
    source_dir: str,
    token: ScopedToken,
    apply: bool = False,
    spawn=None,
    supersession_policy: SupersessionPolicy | None = SupersessionPolicy(),
) -> PushResult:
    """Push (or plan to push) ``refs/heads/<branch>`` to the CONSTRUCTED HTTPS remote (plan-by-default).

    Validates the request FIRST (raising :class:`PushRefused` before any git call), resolves the
    local head and reads the remote ref state through the authenticated ``spawn`` seam, and computes
    the would-push plan. With ``apply=False`` (default) it returns a non-mutating
    :class:`PushResult`. With ``apply=True`` it pushes the branch — a verified no-op when the remote
    already equals the local head, and a :class:`PushRefused` when the remote ref is not an ancestor
    of the local head (a non-fast-forward; never force). A transport failure raises
    :class:`ForgeConfigError`.
    """
    _validate(repo, branch, token)
    _spawn = spawn or _default_spawn
    url = _https_remote_url(repo)

    local = _local_head(_spawn, source_dir, branch)
    if supersession_policy is not None:
        _enforce_supersession_guard(_spawn, source_dir, branch, local, supersession_policy)
    remote = _ls_remote(_spawn, source_dir, url, branch, token)

    if remote is not None and remote == local:
        # Idempotent: the remote already carries this exact head — nothing to push.
        return PushResult(
            repo=repo, branch=branch, remote_url=url,
            local_head=local, remote_head=remote,
            changed=False, up_to_date=True, applied=apply, pushed=False,
        )

    if remote is not None and not _is_ancestor(_spawn, source_dir, remote, local):
        # The remote head is not an ancestor of the local head: a fast-forward is impossible.
        raise PushRefused(
            f"remote {url} {branch} is not a fast-forward of the local head "
            f"(remote {remote[:12]}.. is not an ancestor of {local[:12]}..); "
            "refusing — this primitive never force-pushes"
        )

    # A push is needed (create or fast-forward update).
    if not apply:
        return PushResult(
            repo=repo, branch=branch, remote_url=url,
            local_head=local, remote_head=remote,
            changed=True, up_to_date=False, applied=False, pushed=False,
        )

    proc = _spawn(
        [
            "git", "-C", str(source_dir), *_GH_CREDENTIAL_ARGS,
            "push", url, f"refs/heads/{branch}:refs/heads/{branch}",
        ],
        None,
        _child_env(token),
    )
    if getattr(proc, "returncode", 1) != 0:
        raise ForgeConfigError(
            f"could not push {branch} to {url}: "
            f"{redact_gh_stderr(getattr(proc, 'stderr', '') or '') or 'unknown error'}"
        )
    return PushResult(
        repo=repo, branch=branch, remote_url=url,
        local_head=local, remote_head=remote,
        changed=True, up_to_date=False, applied=True, pushed=True,
    )
