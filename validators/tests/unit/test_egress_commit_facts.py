"""Unit tests for the egress-broker host-side commit-fact extraction.

``egress_broker.commit_facts.read_commit_facts`` resolves the head of a contained seat's
local branch (reachable host-side via the seat's bind-mount) and extracts the value-free
facts the pure policy core needs: the head sha, the ``git`` ``%G?`` signature verdict, the
``%GS`` signer, and the ``%an``/``%ae`` author. All git access is behind an injectable
``spawn`` seam; these tests inject fakes and run ZERO live git.

Fail-closed posture under test:

* the branch must exist locally (``rev-parse --verify`` succeeds) — an absent branch is a
  refusal, never a silently-empty fact set;
* a ``git show`` transport error surfaces as a ``"E"`` (cannot-check) signature status so the
  pure policy then DENIES — extraction never fabricates a good verdict;
* the extracted ``%G?`` code is passed through verbatim (``G``/``B``/``U``/``E``/``N`` …);
  the trust decision belongs to the policy core, not the extractor.
"""

import socket
import subprocess

import pytest

from egress_broker.commit_facts import CommitFactsError, read_commit_facts

_US = "\x1f"  # the unit-separator the extractor formats with


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=["git"], returncode=returncode, stdout=stdout, stderr=stderr)


def _fake_spawn(*, head="d" * 40, show=None, head_rc=0, calls=None):
    """A fake git ``spawn`` returning a head for rev-parse and a formatted show line."""
    show_line = show if show is not None else _US.join(["G", "cedev4vps-coder", "ce-dev-4", "dev4@x", "d" * 40])

    def spawn(argv, input_text=None, env=None):
        if calls is not None:
            calls.append(list(argv))
        if "rev-parse" in argv:
            return _proc(returncode=head_rc, stdout=(head + "\n") if head_rc == 0 else "")
        if "show" in argv:
            return _proc(returncode=0, stdout=show_line + "\n")
        raise AssertionError(f"unexpected git argv: {argv}")

    return spawn


def test_extracts_all_facts_from_a_signed_commit():
    facts = read_commit_facts("/repo", "ce-egress-broker", spawn=_fake_spawn())
    assert facts.head_sha == "d" * 40
    assert facts.signature_status == "G"
    assert facts.signer == "cedev4vps-coder"
    assert facts.author_name == "ce-dev-4"
    assert facts.author_email == "dev4@x"


def test_unsigned_commit_reports_N_status():
    show = _US.join(["N", "", "ce-dev-4", "dev4@x", "e" * 40])
    facts = read_commit_facts("/repo", "ce-x", spawn=_fake_spawn(head="e" * 40, show=show))
    assert facts.signature_status == "N"
    assert facts.signer == ""


def test_cannot_check_signature_reports_E_status():
    # the real-world dev-4 case: signed, but the verifying key is not in the host trust store
    show = _US.join(["E", "", "ce-dev-4", "dev4@x", "f" * 40])
    facts = read_commit_facts("/repo", "ce-x", spawn=_fake_spawn(head="f" * 40, show=show))
    assert facts.signature_status == "E"


def test_absent_branch_is_refused():
    with pytest.raises(CommitFactsError):
        read_commit_facts("/repo", "no-such-branch", spawn=_fake_spawn(head_rc=1))


def test_rev_parse_is_verify_quiet_for_the_named_branch():
    calls: list[list[str]] = []
    read_commit_facts("/repo", "ce-egress-broker", spawn=_fake_spawn(calls=calls))
    rev = next(c for c in calls if "rev-parse" in c)
    assert "--verify" in rev and "--quiet" in rev
    assert "refs/heads/ce-egress-broker" in rev
    assert "-C" in rev and "/repo" in rev


def test_show_transport_error_yields_cannot_check_not_a_good_verdict():
    def spawn(argv, input_text=None, env=None):
        if "rev-parse" in argv:
            return _proc(returncode=0, stdout="a" * 40 + "\n")
        if "show" in argv:
            return _proc(returncode=128, stderr="fatal: bad object")
        raise AssertionError(argv)

    facts = read_commit_facts("/repo", "ce-x", spawn=spawn)
    # extraction NEVER fabricates "G"; a transport failure maps to cannot-check → policy denies
    assert facts.signature_status == "E"
    assert facts.head_sha == "a" * 40


def test_show_uses_the_rev_parsed_sha_not_the_ref():
    calls: list[list[str]] = []
    read_commit_facts("/repo", "ce-x", spawn=_fake_spawn(head="a" * 40, calls=calls))
    show = next(c for c in calls if "show" in c)
    assert "a" * 40 in show  # the resolved sha is what we show, pinning the exact object


def test_zero_live_git(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("read_commit_facts must use the injected spawn, not live git")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    facts = read_commit_facts("/repo", "ce-x", spawn=_fake_spawn())
    assert facts.head_sha == "d" * 40
