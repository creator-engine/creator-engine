"""Host-side extraction of a contained seat's head-commit facts (behind a git ``spawn`` seam).

A contained seat (e.g. dev-4 in gVisor) authors + signs a commit on a local branch; that
branch is reachable host-side through the seat's bind-mount (dev-4:
``/home/cedev4/ce-workspaces/creator-engine`` ↔ container ``/workspace/creator-engine``).
:func:`read_commit_facts` resolves that branch's head and extracts the value-free
:class:`~egress_broker.policy.CommitFacts` the pure policy core decides on — the head sha,
the ``git`` ``%G?`` signature verdict, the ``%GS`` signer, and the ``%an``/``%ae`` author.

Trust boundary (deliberate): the *cryptographic* verdict is ``git``'s job — it checks the
signature against the host's own trust store (gpg keyring / ssh ``allowed_signers``) and
returns a one-char ``%G?`` code. This module passes that code through verbatim; the
fail-closed TRUST decision (only ``G`` passes) lives in the policy core. So the broker's TCB
splits cleanly: deterministic crypto in ``git``, deterministic policy in
``egress_broker.policy`` — no LLM anywhere on the path.

Fail-closed invariants:

* the branch must exist locally (``git rev-parse --verify --quiet refs/heads/<branch>``) — an
  absent branch raises :class:`CommitFactsError`, never a silently-empty fact set;
* extraction pins the resolved SHA and ``git show``-s THAT object (not the ref), so the facts
  describe exactly the object the policy will authorize;
* a ``git show`` transport failure maps to ``"E"`` (cannot-check) — extraction NEVER
  fabricates a good verdict, so the policy core then denies.

All git access is behind an injectable ``spawn`` seam (the live ``subprocess.run`` by
default, read-only); tests inject a fake and run ZERO live git. Importing this module
performs no I/O and registers no validator check.
"""
from __future__ import annotations

import subprocess
from collections.abc import Sequence

from egress_broker.policy import CommitFacts

#: The unit separator joining the ``git show`` format fields — chosen because it can never
#: appear in a sha / signer / author, so the split is unambiguous even for odd author names.
_US = "\x1f"
#: One ``git show`` line carrying ``%G?`` / ``%GS`` / ``%an`` / ``%ae`` / ``%H``.
_SHOW_FORMAT = _US.join(["%G?", "%GS", "%an", "%ae", "%H"])
#: When ``git`` cannot return a verdict (transport error), we record cannot-check, never good.
_CANNOT_CHECK = "E"


class CommitFactsError(Exception):
    """The seat's branch could not be resolved host-side (absent branch / git refusal).

    A fail-closed refusal raised BEFORE any policy decision — the orchestrator turns it into a
    deny audit + non-zero exit. Distinct from a *good* extraction of a *bad* signature (that is
    a valid fact the policy denies on).
    """


def _default_spawn(  # pragma: no cover - the lone live git shell; tests inject a fake spawn
    argv: Sequence[str], input_text: str | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, env=env, timeout=60
    )


def _resolve_head(spawn, repo_path: str, branch: str) -> str:
    proc = spawn(
        ["git", "-C", str(repo_path), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        None,
        None,
    )
    out = (getattr(proc, "stdout", "") or "").strip()
    if getattr(proc, "returncode", 1) != 0 or not out:
        raise CommitFactsError(
            f"local branch {branch!r} not found under {repo_path!r}; refusing to verify a "
            "branch the seat never authored (fail-closed)"
        )
    return out.splitlines()[0].strip()


def read_commit_facts(repo_path: str, branch: str, *, spawn=None) -> CommitFacts:
    """Resolve ``refs/heads/<branch>`` host-side and extract its :class:`CommitFacts`.

    Raises :class:`CommitFactsError` if the branch is absent locally. A ``git show`` transport
    failure yields a ``"E"`` (cannot-check) signature status — extraction never fabricates a
    good verdict — so the policy core then denies. The ``%G?`` code is otherwise passed through
    verbatim. Read-only; no mutation.
    """
    _spawn = spawn or _default_spawn
    head = _resolve_head(_spawn, repo_path, branch)

    proc = _spawn(
        ["git", "-C", str(repo_path), "show", "-s", f"--format={_SHOW_FORMAT}", head],
        None,
        None,
    )
    if getattr(proc, "returncode", 1) != 0:
        # Cannot read the object's signature → cannot-check (the policy denies), never "good".
        return CommitFacts(
            head_sha=head, signature_status=_CANNOT_CHECK, signer="", author_name="", author_email=""
        )

    raw = (getattr(proc, "stdout", "") or "").strip("\n")
    parts = raw.split(_US)
    # Defensive padding: a malformed/short line still yields a fact set the policy can deny on.
    while len(parts) < 5:
        parts.append("")
    status, signer, author_name, author_email, shown_sha = parts[:5]
    return CommitFacts(
        head_sha=(shown_sha.strip() or head),
        signature_status=status.strip(),
        signer=signer.strip(),
        author_name=author_name.strip(),
        author_email=author_email.strip(),
    )
