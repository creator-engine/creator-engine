"""The ADR-0007 egress-broker PURE policy core — the trusted-computing-base heart.

:func:`evaluate` is the deterministic "verify before transmitting" decision of ADR-0007's
publish broker. Given already-extracted, value-free :class:`CommitFacts`, a target branch,
and a :class:`BrokerPolicy` — plus pure-value inputs for the rate guard and the pluggable
ratification/CI precondition — it returns a fail-closed :class:`Decision`.

It is **pure**: ZERO I/O, no clock, no network, no git, no crypto. The cryptographic
signature verdict (``git``'s ``%G?`` code) is computed by the separately-tested extraction
layer and the host's own trust store (gpg keyring / ssh ``allowed_signers``); this module
only consumes that verdict. Keeping the decision pure is what makes it exhaustively
testable and auditable — the whole point of moving egress to a *deterministic* enforcer.

Fail-closed is the law (ADR-0007 "demands hardening, minimal surface, strong audit"):

* **signature_valid** — ONLY a fully-trusted good signature (``%G?`` == ``G``) passes.
  Every other code denies: ``B`` (bad), ``U`` (good signature but UNKNOWN validity — key
  not in the broker host's trust store), ``X`` / ``Y`` / ``R`` (expired sig / expired key /
  revoked key), ``E`` (cannot check — missing key), ``N`` (none). "Good but untrusted" is a
  verification *doubt*, and a doubt is a denial.
* **author_authorized** — the commit author must be on an allow-list of authorized CE
  identities, matched by exact email OR by the GitHub ``<id>+<login>@users.noreply.github.com``
  login (so the controller can allow-list by the GitHub logins it knows — ``cedev4vps-coder``
  etc. — without hand-collecting numeric ids).
* **branch_not_forbidden** — the target branch is NEVER ``main`` (case-insensitively), the
  configured base branch, or any other forbidden branch. This gate is ABSOLUTE: it denies
  even when a namespace prefix would otherwise match.
* **branch_in_namespace** — the (well-formed) target branch matches one of the allowed
  branch-namespace prefixes.
* **within_rate_limit** — a basic scope/rate guard: the recent push count for the seat must
  be under the per-window cap (cap ``0`` disables the guard).
* **precondition:<name>** — each pluggable ratification/CI precondition supplied by the
  orchestrator must be satisfied.

``Decision.allowed`` is the logical AND of every check; a single failure denies. ALL failing
checks are recorded (not short-circuited) so the audit names every reason. The result is a
frozen, JSON-serializable, secret-free value (it carries no token, no PEM, no App id).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

#: The ONLY ``git`` ``%G?`` code that is a fully-trusted good signature. Everything else —
#: ``B`` bad, ``U`` good/unknown-validity, ``X``/``Y``/``R`` expired/revoked, ``E`` cannot
#: check, ``N`` none, or our ``""``/``"NONE"`` sentinels — is a fail-closed denial.
GOOD_SIGNATURE = "G"

#: A full git object id: 40-hex (sha1) or 64-hex (sha256). Abbreviated ids are refused — a
#: head we cannot pin exactly is a head we will not transmit.
_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

#: The canonical GitHub no-reply author email ``<numeric-id>+<login>@users.noreply.github.com``.
#: Anchored end-to-end so a look-alike host (``...github.com.evil.com``) cannot satisfy it; the
#: login is captured for an EXACT (never substring) allow-list comparison.
_NOREPLY_RE = re.compile(
    r"^[0-9]+\+(?P<login>[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)@users\.noreply\.github\.com$"
)

#: A well-formed git branch name for our purposes: non-empty, no whitespace/control chars, no
#: leading dash (would look like a flag), no ``..`` (refspec/range hazard), and no URL query
#: delimiters that could rewrite unescaped downstream API query strings. Deliberately
#: conservative — a branch we cannot cleanly name is a branch we refuse.
_BRANCH_RE = re.compile(r"^(?!-)(?!.*\.\.)[!-~]+$")
_BRANCH_QUERY_DELIMITER_RE = re.compile(r"[?&#=]")

#: Branches the broker NEVER pushes to regardless of config — the absolute floor. ``main`` and
#: ``master`` are matched case-insensitively (so ``MAIN`` is also refused); the configured base
#: branch is added at evaluation time.
_ALWAYS_FORBIDDEN = frozenset({"main", "master"})


@dataclass(frozen=True)
class CommitFacts:
    """Value-free, already-extracted facts about the head commit being couriered.

    ``signature_status`` is ``git``'s ``%G?`` code (``G``/``B``/``U``/``X``/``Y``/``R``/``E``/
    ``N``, or a ``""``/``"NONE"`` sentinel for "no signature line"). ``signer`` is ``%GS`` (the
    verified signer, possibly empty). ``author_name``/``author_email`` are ``%an``/``%ae``.
    Carries no secret — safe to record verbatim in the audit.
    """

    head_sha: str
    signature_status: str
    signer: str
    author_name: str
    author_email: str


@dataclass(frozen=True)
class BrokerPolicy:
    """The deterministic publish policy for one repo/host (a pure, frozen value).

    ``authorized_emails`` is matched case-insensitively against the full author email;
    ``authorized_logins`` is matched (exactly) against the login parsed from a GitHub
    no-reply author email. ``allowed_branch_namespaces`` are prefix matches.
    ``forbidden_branches`` is unioned with the always-forbidden floor and the base branch.
    ``max_pushes_per_window`` is the rate cap (``0`` disables the guard).

    ``require_signed_commits`` controls whether commit-signature verification is enforced
    (default ``True`` = back-compat, fail-closed). Set to ``False`` ONLY for contained seats
    that cannot sign (e.g. gVisor zero-key environments). When ``False`` the signature gate is
    skipped entirely but ALL other gates — author allow-list, branch namespace, forbidden-branch,
    rate-limit, head-sha well-formedness, and preconditions — remain enforced. The broker's own
    authorization boundary (GitHub login allow-list + branch namespace + rate-limit) is the
    trust boundary in that configuration. The skip is logged explicitly.
    """

    base_branch: str
    allowed_branch_namespaces: tuple[str, ...]
    forbidden_branches: frozenset[str]
    authorized_emails: frozenset[str]
    authorized_logins: frozenset[str]
    max_pushes_per_window: int
    window_seconds: int
    require_signed_commits: bool = True


@dataclass(frozen=True)
class RateState:
    """The pure rate input: how many pushes this seat has made inside the policy window."""

    recent_count: int = 0


@dataclass(frozen=True)
class Precondition:
    """A pluggable ratification/CI precondition result, supplied by the orchestrator.

    ``satisfied`` is the only gate-relevant field; ``name``/``detail`` are for the audit.
    Supplying these as pure values (rather than running the hook inside the core) keeps
    :func:`evaluate` pure and fully testable.
    """

    name: str
    satisfied: bool
    detail: str = ""


@dataclass(frozen=True)
class CheckResult:
    """One named gate outcome. ``detail`` is value-free prose for the audit."""

    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Decision:
    """The fail-closed verdict — ``allowed`` is the AND of every :class:`CheckResult`.

    A pure, JSON-serializable, secret-free value (no token, PEM, or App id). ``reasons``
    surfaces exactly the failing checks' details for a refusal message / audit.
    """

    allowed: bool
    checks: tuple[CheckResult, ...]

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(c.detail for c in self.checks if not c.passed)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "checks": [c.to_dict() for c in self.checks],
        }


def _author_authorized(facts: CommitFacts, policy: BrokerPolicy) -> CheckResult:
    email = (facts.author_email or "").strip()
    if not email:
        return CheckResult("author_authorized", False, "commit has no author email")
    if email.lower() in {e.strip().lower() for e in policy.authorized_emails}:
        return CheckResult("author_authorized", True, f"author email on allow-list: {email}")
    m = _NOREPLY_RE.match(email)
    if m and m.group("login") in policy.authorized_logins:
        return CheckResult(
            "author_authorized", True, f"author github-login on allow-list: {m.group('login')}"
        )
    return CheckResult(
        "author_authorized", False, f"author {email} is not on the authorized CE identity allow-list"
    )


def _branch_not_forbidden(branch: str, policy: BrokerPolicy) -> CheckResult:
    name = (branch or "").strip()
    forbidden = {b.strip().lower() for b in policy.forbidden_branches}
    forbidden |= {b for b in _ALWAYS_FORBIDDEN}
    forbidden.add((policy.base_branch or "").strip().lower())
    if name.lower() in forbidden:
        return CheckResult(
            "branch_not_forbidden",
            False,
            f"branch {branch!r} is forbidden (never push to main / the base / a forbidden branch)",
        )
    return CheckResult("branch_not_forbidden", True, f"branch {branch!r} is not a forbidden target")


def _branch_in_namespace(branch: str, policy: BrokerPolicy) -> CheckResult:
    name = branch or ""
    if not _BRANCH_RE.match(name) or _BRANCH_QUERY_DELIMITER_RE.search(name):
        return CheckResult(
            "branch_in_namespace", False, f"branch {branch!r} is empty or malformed"
        )
    for prefix in policy.allowed_branch_namespaces:
        if prefix and name.startswith(prefix):
            return CheckResult(
                "branch_in_namespace", True, f"branch {branch!r} matches allowed namespace {prefix!r}"
            )
    return CheckResult(
        "branch_in_namespace",
        False,
        f"branch {branch!r} is outside every allowed namespace {tuple(policy.allowed_branch_namespaces)!r}",
    )


def evaluate(
    facts: CommitFacts,
    branch: str,
    policy: BrokerPolicy,
    *,
    rate_state: RateState = RateState(),
    preconditions: tuple[Precondition, ...] = (),
) -> Decision:
    """Return the fail-closed :class:`Decision` for couriering ``facts`` onto ``branch``.

    Evaluates every gate (signature / author / branch-forbidden / branch-namespace / head-sha
    well-formedness / rate / preconditions) WITHOUT short-circuiting, so the audit records
    every failing reason, then sets ``allowed`` to the AND of them all. Pure — performs no
    I/O. Deny on any doubt.
    """
    checks: list[CheckResult] = []

    # 1. head sha — a head we cannot pin exactly is a head we will not transmit.
    if _SHA_RE.match(facts.head_sha or ""):
        checks.append(CheckResult("head_sha_wellformed", True, f"head {facts.head_sha}"))
    else:
        checks.append(
            CheckResult(
                "head_sha_wellformed", False, f"head sha {facts.head_sha!r} is not a 40/64-hex object id"
            )
        )

    # 2. signature — ONLY an exact "G" (good, fully trusted) passes by default (fail-closed).
    #    When require_signed_commits is False (contained seats that cannot sign), the gate is
    #    SKIPPED entirely and logged explicitly; all other gates remain enforced as normal.
    if policy.require_signed_commits:
        status = facts.signature_status or ""
        if status == GOOD_SIGNATURE:
            checks.append(
                CheckResult("signature_valid", True, f"git verified a good signature (%G?={status})")
            )
        else:
            shown = status or "NONE"
            checks.append(
                CheckResult(
                    "signature_valid",
                    False,
                    f"signature is not a trusted-good signature (%G?={shown}); fail-closed deny",
                )
            )
    else:
        # Signature check disabled by policy (require_signed_commits=false). This is intended for
        # contained seats that operate in zero-key gVisor environments and cannot sign commits.
        # The broker's authorization boundary (author allow-list + branch namespace + rate-limit)
        # is the enforced trust boundary. All other gates remain active and are NOT relaxed.
        checks.append(
            CheckResult(
                "signature_valid",
                True,
                "signature check disabled by policy (require_signed_commits=false); "
                "broker authorization boundary enforced via other gates",
            )
        )

    # 3. author on the allow-list.
    checks.append(_author_authorized(facts, policy))

    # 4. branch never main / base / forbidden (absolute), and in an allowed namespace.
    checks.append(_branch_not_forbidden(branch, policy))
    checks.append(_branch_in_namespace(branch, policy))

    # 5. basic rate / scope guard (cap 0 disables).
    cap = policy.max_pushes_per_window
    if cap and rate_state.recent_count >= cap:
        checks.append(
            CheckResult(
                "within_rate_limit",
                False,
                f"seat has {rate_state.recent_count} pushes in the window (cap {cap})",
            )
        )
    else:
        checks.append(
            CheckResult(
                "within_rate_limit",
                True,
                f"{rate_state.recent_count} pushes in window (cap {cap or 'disabled'})",
            )
        )

    # 6. pluggable ratification/CI preconditions — each must be satisfied.
    for pre in preconditions:
        checks.append(
            CheckResult(
                f"precondition:{pre.name}",
                bool(pre.satisfied),
                pre.detail or ("satisfied" if pre.satisfied else "unsatisfied"),
            )
        )

    allowed = all(c.passed for c in checks)
    return Decision(allowed=allowed, checks=tuple(checks))
