"""CE v3 forge-native change-lifecycle primitive (G-3.0) — open/claim one PR for a branch.

The §5.1 orchestrator lifecycle has a governed agent author inside a sandbox and then
hand its work to the forge (step 5). :func:`open_change` is that hand-off seam: it takes
the authored head ``branch`` and ensures **exactly one** pull request exists for it
against ``base`` — the "push = claim" idempotency of §2.1 (pushing a branch claims it;
there is one open PR per branch, never a duplicate fork).

Like the rest of ``forge/`` this is a small, *idempotent, desired-state* operation that
talks to a live forge ONLY through an injectable ``GhRunner`` (``gh api`` by default) and
is **plan-by-default**:

* ``apply=False`` (default) READS the open-PR state for the head branch and RETURNS a
  :class:`ChangeRef` describing the create-or-claim plan WITHOUT mutating anything.
* ``apply=True`` (never run against a live forge in CI) POSTs exactly one PR when none
  exists, then re-reads to verify; when a PR already claims the branch it is a verified
  no-op (no duplicate).

Defensive invariants (deliberate, load-bearing):

* **Refuse a malformed request BEFORE any forge call** (refuse-before-side-effect):
  :func:`open_change` raises :class:`OpenChangeRefused` (a ``ForgeConfigRefused``) on a
  malformed ``repo``, an empty ``branch``/``base``, a ``base == branch`` self-target, an
  empty ``manifest_paths``, or a ``plan_ref`` that is not a 64-hex policy/plan digest —
  mirroring the G-2.2 mint deny discipline.
* **Carries NO credential.** :func:`open_change` takes no token argument and
  :class:`ChangeRef` holds no token value; auth lives only in the injected ``gh_runner``'s
  environment (the ``revoke_scoped_token`` pattern, where the secret never appears in
  argv). App installation tokens are ~520-char ``ghs_`` JWTs — we make no length/format
  assumption.
* **Thin carrier.** ``open_change`` carries already-ratified data; the diff-vs-manifest
  fidelity check is the CI carrier-gate's job (it parses the PR's own per-PR carrier
  ``.ce/pr-manifests/<branch-slug>.md`` in the diff, NOT this PR body), and the
  no-self-merge / required-review guarantees are GitHub-ruleset facts. Any manifest block
  this module emits in the PR body is an optional human/audit mirror only.

Like the rest of ``forge/`` this reuses ``GhRunner`` / ``ForgeConfigError`` /
``ForgeConfigRefused`` from the byte-unchanged G-iii ``github_repo_config`` module, imports
ZERO doomed modules, performs no I/O on import, and registers no validator check (so
``--list-checks`` stays byte-identical).

Defensive only — a governed agent opening a PR on its own branch for our own pipeline;
never offensive (no branch-protection bypass, no self-merge, no detection evasion).
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from ._redact import redact_gh_stderr
from .github_repo_config import ForgeConfigError, ForgeConfigRefused, GhRunner

# Re-defined LOCALLY (literals copied from ``scoped_token.py`` lines 56-57) per the
# established forge convention — see ``scoped_token.py`` ``_gh_api_method`` — so the
# frozen sibling modules stay byte-unchanged and ``change.py`` couples to none of them.
_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_POLICY_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class OpenChangeRefused(ForgeConfigRefused):
    """An ``open_change`` request was refused on a precondition BEFORE any forge call.

    Raised when the request is malformed (bad ``repo``, empty ``branch``/``base``,
    ``base == branch`` self-target, empty ``manifest_paths``, or a ``plan_ref`` that is not
    a 64-hex policy/plan digest). A *policy* refusal — distinct from a *transport*
    :class:`ForgeConfigError`.
    """

    code = "V3-FORGE-OPENCHANGE-REFUSED"


@dataclass(frozen=True)
class ChangeRef:
    """The desired-state result of opening/claiming one PR for a branch — secret-free.

    Carries ONLY non-secret data: the ``repo``/``branch``/``base`` it targets, the
    ``pr_number``/``head_sha`` of the claimed PR (``None`` when a create is still planned),
    the ``manifest_paths`` this change carries, the ``plan_ref`` binding it to the
    runtime-policy in force, and the ``changed``/``applied``/``verified`` desired-state
    flags. It holds NO token value (auth stays in the injected ``gh_runner`` env).
    """

    repo: str
    branch: str
    base: str
    pr_number: int | None
    head_sha: str | None
    manifest_paths: tuple[str, ...]
    plan_ref: str
    changed: bool
    applied: bool
    verified: bool

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "branch": self.branch,
            "base": self.base,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "manifest_paths": list(self.manifest_paths),
            "plan_ref": self.plan_ref,
            "changed": self.changed,
            "applied": self.applied,
            "verified": self.verified,
        }

    def __repr__(self) -> str:  # structural secret-hygiene guard (carries no secret)
        return (
            f"ChangeRef(repo={self.repo!r}, branch={self.branch!r}, base={self.base!r}, "
            f"pr_number={self.pr_number!r}, head_sha={self.head_sha!r}, "
            f"changed={self.changed!r}, applied={self.applied!r}, "
            f"verified={self.verified!r}, value=<redacted>)"
        )

    __str__ = __repr__


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - requires a live gh + GitHub App
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _gh_api_method(
    runner: GhRunner, method: str, path: str, body: dict | None = None
) -> tuple[int, object, str]:
    """Invoke ``gh api -X <METHOD> <path>`` (JSON body via ``--input -``).

    Returns ``(returncode, parsed_json|None, stderr)``. Never raises on a non-zero exit or
    unparseable stdout. Mirrors the ``scoped_token`` / ``github_repo_config`` ``gh api``
    idiom locally so those frozen modules stay byte-unchanged.
    """
    argv = ["gh", "api", "-X", method, path]
    input_text: str | None = None
    if body is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(body)
    proc = runner(argv, input_text)
    parsed: object = None
    out = (proc.stdout or "").strip()
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return proc.returncode, parsed, proc.stderr or ""


def _render_pr_body(branch: str, base: str, plan_ref: str, manifest_paths: tuple[str, ...]) -> str:
    """Compose the PR body — an OPTIONAL human/audit mirror, NOT the CI carrier-gate feed.

    Embeds the ``plan_ref`` as a ``ce-policy-sha`` marker (parseable by the merged
    ``plan_approval`` marker convention and the downstream review-state op) and the
    ``manifest_paths`` as a fenced audit list. The PR's own per-PR carrier
    ``.ce/pr-manifests/<branch-slug>.md`` in the diff — never this text — is what the
    ``path_manifest_fidelity`` gate parses.
    """
    paths_block = "\n".join(sorted(set(manifest_paths)))
    return (
        f"ce-policy-sha: {plan_ref}\n\n"
        f"Opens/updates a single PR for branch `{branch}` targeting `{base}` "
        f"(push = claim: exactly one open PR per branch).\n\n"
        f"Authorized path manifest (audit mirror — the CI gate parses this PR's "
        f"`.ce/pr-manifests/<branch-slug>.md` carrier in the diff, NOT this body):\n\n"
        f"```text\n{paths_block}\n```\n"
    )


def _validate(
    repo: str, branch: str, base: str, manifest_paths: tuple[str, ...], plan_ref: str
) -> None:
    """Refuse a malformed / unbound request BEFORE any forge call."""
    if not _REPO_RE.match(repo or ""):
        raise OpenChangeRefused(f"repo {repo!r} is not in owner/name form")
    if not (branch or "").strip():
        raise OpenChangeRefused("branch must be a non-empty head branch")
    if not (base or "").strip():
        raise OpenChangeRefused("base must be a non-empty target branch")
    if base == branch:
        raise OpenChangeRefused(
            f"base {base!r} must differ from head branch {branch!r} (self-targeting a PR)"
        )
    if not manifest_paths:
        raise OpenChangeRefused(
            "manifest_paths must list the change's authorized path-set (empty = refuse)"
        )
    if not (plan_ref or "").strip():
        raise OpenChangeRefused("plan_ref (the ratified plan/policy reference) is required")
    if not _POLICY_SHA_RE.match(plan_ref):
        raise OpenChangeRefused(f"plan_ref {plan_ref!r} is not a 64-hex policy/plan digest")


def _read_open_pr(
    runner: GhRunner, repo: str, branch: str, base: str, owner: str
) -> dict | None:
    """Return the single open PR claiming ``owner:branch`` -> ``base``, or ``None``."""
    path = f"repos/{repo}/pulls?state=open&head={owner}:{branch}&base={base}"
    code, parsed, stderr = _gh_api_method(runner, "GET", path)
    if code != 0:
        raise ForgeConfigError(
            f"could not read open pulls for {repo} head {owner}:{branch}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return parsed[0]
    return None


def open_change(
    repo: str,
    branch: str,
    base: str,
    manifest_paths: Sequence[str],
    plan_ref: str,
    *,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> ChangeRef:
    """Open (or idempotently claim) exactly one PR for ``branch`` -> ``base`` (plan-by-default).

    Validates the request FIRST (raising :class:`OpenChangeRefused` before any forge call),
    then READS the open-PR state for the head branch through the injected ``gh_runner``. With
    ``apply=False`` (default) it returns a non-mutating :class:`ChangeRef` describing the
    create-or-claim plan. With ``apply=True`` it POSTs exactly one PR when none exists (then
    re-reads to verify) and is a verified no-op when a PR already claims the branch. A
    transport failure raises :class:`ForgeConfigError`.
    """
    paths = tuple(manifest_paths or ())
    _validate(repo, branch, base, paths, plan_ref)
    runner = gh_runner or _default_gh_runner
    owner = repo.split("/", 1)[0]

    existing = _read_open_pr(runner, repo, branch, base, owner)
    if existing is not None:
        # A PR already claims this branch — idempotent (push = claim). No duplicate.
        return ChangeRef(
            repo=repo, branch=branch, base=base,
            pr_number=existing.get("number"),
            head_sha=(existing.get("head") or {}).get("sha"),
            manifest_paths=paths, plan_ref=plan_ref,
            changed=False, applied=apply, verified=True,
        )

    if not apply:
        # Plan-by-default: a create is needed but nothing is mutated.
        return ChangeRef(
            repo=repo, branch=branch, base=base,
            pr_number=None, head_sha=None,
            manifest_paths=paths, plan_ref=plan_ref,
            changed=True, applied=False, verified=False,
        )

    # apply=True: POST exactly one PR, then re-read to verify it now exists.
    body = {
        "title": f"[ce] {branch} -> {base}",
        "head": branch,
        "base": base,
        "body": _render_pr_body(branch, base, plan_ref, paths),
    }
    code, parsed, stderr = _gh_api_method(runner, "POST", f"repos/{repo}/pulls", body)
    if code != 0 or not isinstance(parsed, dict) or not parsed.get("number"):
        raise ForgeConfigError(
            f"could not open PR for {repo} {branch} -> {base}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    reread = _read_open_pr(runner, repo, branch, base, owner)
    return ChangeRef(
        repo=repo, branch=branch, base=base,
        pr_number=parsed.get("number"),
        head_sha=(parsed.get("head") or {}).get("sha"),
        manifest_paths=paths, plan_ref=plan_ref,
        changed=True, applied=True, verified=reread is not None,
    )
