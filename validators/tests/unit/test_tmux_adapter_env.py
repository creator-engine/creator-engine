"""G2.007.3 — tmux adapter can pin launch-time environment via ``-e KEY=VALUE``.

A governed reviewer venue must carry a launch-pinned reviewer-authority reference
into the pane environment (so the in-band hook can resolve it) without printing the
value or using a raw shell. ``ensure_pane(env=...)`` emits one ``-e KEY=VALUE`` token
per entry on the ``new-session`` / ``new-window`` command, before the pane command.

The fake runner records argv only; no real tmux process and no secret printing.
"""
from __future__ import annotations

import subprocess

from creator_engine_validator.tmux_adapter import TmuxAdapter


class FakeTmux:
    IDENTITY = "$3\t@7\t%9\t/dev/pts/4\t2222\n"

    def __init__(self, *, existing_sessions=()):
        self.existing = set(existing_sessions)
        self.calls: list[list[str]] = []

    def __call__(self, argv, check: bool = True):
        argv = list(argv)
        self.calls.append(argv)
        sub = argv[1] if len(argv) > 1 else ""
        if sub == "-V":
            return subprocess.CompletedProcess(argv, 0, "tmux 3.6\n", "")
        if sub == "has-session":
            rc = 0 if argv[-1] in self.existing else 1
            if rc and check:
                raise subprocess.CalledProcessError(rc, argv)
            return subprocess.CompletedProcess(argv, rc, "", "")
        if sub in ("new-session", "new-window"):
            return subprocess.CompletedProcess(argv, 0, self.IDENTITY, "")
        return subprocess.CompletedProcess(argv, 0, "", "")


def _create_call(fake: FakeTmux) -> list[str]:
    return next(c for c in fake.calls if c[1] in ("new-session", "new-window"))


def test_env_emitted_as_dash_e_tokens_before_command():
    fake = FakeTmux()
    adapter = TmuxAdapter(runner=fake)
    adapter.ensure_pane(
        session="ce-lane", window="rev",
        command=["sh", "-c", "true"],
        env={"CE_REVIEWER_AUTHORITY_REF": ".hermes/x/reviewer-authority.ce.yml"},
    )
    create = _create_call(fake)
    assert "-e" in create
    e_idx = create.index("-e")
    assert create[e_idx + 1] == "CE_REVIEWER_AUTHORITY_REF=.hermes/x/reviewer-authority.ce.yml"
    # The env assignment must precede the pane command vector.
    assert create.index("CE_REVIEWER_AUTHORITY_REF=.hermes/x/reviewer-authority.ce.yml") < create.index("sh")


def test_no_env_emits_no_dash_e():
    fake = FakeTmux()
    adapter = TmuxAdapter(runner=fake)
    adapter.ensure_pane(session="ce-lane", window="rev", command=["sh", "-c", "true"])
    assert "-e" not in _create_call(fake)


def test_multiple_env_entries_each_get_dash_e():
    fake = FakeTmux()
    adapter = TmuxAdapter(runner=fake)
    adapter.ensure_pane(
        session="ce-lane", window="rev",
        command=["sh", "-c", "true"],
        env={"A": "1", "B": "2"},
    )
    create = _create_call(fake)
    assert create.count("-e") == 2
    assert "A=1" in create and "B=2" in create
