"""CE v3 forge-native credential value-injection (G-3.4) — a JIT ``ScopedToken`` -> an authenticated ``GhRunner``.

Realizes the seam G-3.1 deferred: the orchestrator threads a value-free ``gh_runner`` FACTORY
into ``run_plan`` (the ``ChangeOpener`` closure captures a factory, never a raw token); here we
build the concrete authenticated :data:`GhRunner` whose CHILD ``gh`` subprocess env carries the
live :attr:`ScopedToken.value` (``GH_TOKEN``), so the forge ops (``open_change`` / ``merge`` / the
G-3.2 reads / ``revoke_scoped_token``) authenticate AS the JIT, least-privilege, per-run credential
rather than the ambient default ``gh auth`` login.

Per the current ``gh`` manual the auth-token precedence for ``github.com`` is
``GH_TOKEN`` > ``GITHUB_TOKEN`` > previously-stored credentials, so setting ``GH_TOKEN`` in the
child env makes ``gh api`` use the scoped token and overrides the ambient login — no ``gh auth``
mutation. A GitHub App installation access token (the ``mint_scoped_token`` result) is a valid
``GH_TOKEN`` bearer for the repo REST/GraphQL calls and the ``DELETE /installation/token`` revoke.

Secret hygiene (deliberate, load-bearing — this is the FIRST subprocess-env secret injection in CE):

* **Value in the child env ONLY.** The live secret lands in a per-call child env (``GH_TOKEN``) and
  NOWHERE else — never the ``argv``, never the ``input_text``, never a log / ``print`` / exception
  message, never disk, never the evidence spine.
* **Child-only scope.** Each call builds a FRESH env dict from ``os.environ``; the parent process
  environment is never mutated, and competing ambient auth (``GITHUB_TOKEN`` and the GHES variants)
  is dropped from the child so the scoped token is unambiguous.
* **Redaction preserved.** The token value is captured privately in the returned closure — it is no
  attribute of the runner and appears in no ``repr``; :class:`ScopedToken`'s own ``value=<redacted>``
  repr is untouched.
* **Never the agent container.** This authenticates CE's OWN forge-coordination ``gh`` subprocess; the
  credential is never injected into the agent task/sandbox container.

Network only behind an injectable ``spawn`` seam (the live ``subprocess.run`` by default); tests inject
a fake ``spawn`` and perform ZERO live ``gh`` / network / subprocess. Importing this module performs no
I/O and registers no validator check.

Defensive only — least-privilege auth for our own sandboxed runs' forge coordination; never offensive
(no token-theft tradecraft, no exfiltration, no detection evasion).
"""
from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence

from .github_repo_config import ForgeConfigRefused, GhRunner
from .scoped_token import ScopedToken

#: Competing ambient auth env vars dropped from the child so the scoped ``GH_TOKEN`` is unambiguous.
#: ``GH_TOKEN`` already wins by precedence; neutralizing these is defense-in-depth.
_NEUTRALIZED_AUTH_ENV = ("GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")


def _default_spawn(  # pragma: no cover - the lone live shell; tests inject a fake spawn
    argv: Sequence[str], input_text: str | None, env: dict[str, str]
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, env=env, timeout=60
    )


def authenticated_gh_runner(token: ScopedToken, *, spawn=None) -> GhRunner:
    """Return a :data:`GhRunner` that injects ``token.value`` into the child ``gh`` env (``GH_TOKEN``).

    The returned runner has the ``GhRunner`` shape ``(argv, input_text) -> CompletedProcess``. On each
    call it builds a FRESH child env from ``os.environ``, drops competing ambient auth, sets
    ``GH_TOKEN`` to the scoped token value, and invokes ``spawn`` (the live ``subprocess.run`` by
    default). The value is in the env ONLY: never the argv, never the input body, never logged, never
    persisted, and the parent ``os.environ`` is never mutated.

    Refuses at build time with :class:`ForgeConfigRefused` (a value-free message) if the token carries
    no value — a credential-less runner would silently fall back to ambient auth, defeating the
    least-privilege guarantee.
    """
    if not token.value:
        raise ForgeConfigRefused(
            "scoped token carries no value; refusing to build an authenticated runner "
            "(a credential-less runner would silently fall back to ambient auth)"
        )
    _spawn = spawn or _default_spawn

    def runner(argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        child_env = dict(os.environ)
        for _name in _NEUTRALIZED_AUTH_ENV:
            child_env.pop(_name, None)
        child_env["GH_TOKEN"] = token.value  # scoped token only — never the argv, never logged
        return _spawn(list(argv), input_text, child_env)

    return runner
