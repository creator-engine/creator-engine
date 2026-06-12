"""v3.1-G2a/G2c — unit tests for the forge-leg composition root (``v3_forge_join``).

Every network/crypto/subprocess edge is faked through injected seams: ZERO live git / gh /
openssl / HTTPS. The headline boundary invariant — the join imports NO v1 module — is asserted
off the module AST. The gate's heart is the secret-hygiene proof: a sentinel token value appears
in NO argv and NO record bytes, lands only in the authenticated child env; the App private key is
execed by (fake) openssl and its bytes never enter the process; the JIT token is minted with
EXACTLY the least-privilege set and revoked on success AND failure.
"""
from __future__ import annotations

import ast
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import _versions as ver
from creator_engine_validator import coordination, v3_forge_join, v3_seat_bridge
from creator_engine_validator.forge.app_jwt_runner import build_app_jwt
from creator_engine_validator.forge.github_repo_config import ForgeConfigError
from creator_engine_validator.v3_forge_join import (
    AppConfig,
    ForgeJoinRefused,
    load_app_config,
    open_change_for_run,
    openssl_signer,
    policy_sha,
)

SENTINEL = "ghs_SENTINELtoken_DEADBEEFcafef00d"
REPO = "creator-engine/creator-engine"
BRANCH = "v31-g2-forge-join"
LOCAL = "a" * 40
HEAD_SHA = "d" * 40
_FIXED_NOW = datetime(2026, 6, 11, 9, 30, 0, tzinfo=timezone.utc)


def _app_config(**over) -> AppConfig:
    base = dict(
        client_id="Iv1.client",
        installation_id=139551869,
        pem_path="/host/.ce-keys/ce-forge-app.pem",
        repo=REPO,
        permissions=(("contents", "write"), ("pull_requests", "write")),
    )
    base.update(over)
    return AppConfig(**base)


def _CP(argv, rc, stdout="", stderr=""):
    return subprocess.CompletedProcess(list(argv), rc, stdout=stdout, stderr=stderr)


class FakeMintRunner:
    """The App-JWT mint runner (GhRunner shape): returns a minted-token JSON."""

    def __init__(self, token_value=SENTINEL):
        self.calls = []
        self.token_value = token_value

    def __call__(self, argv, input_text=None):
        self.calls.append({"argv": list(argv), "input": input_text})
        return _CP(argv, 0, stdout=json.dumps(
            {"token": self.token_value, "expires_at": "2026-06-11T10:00:00Z"}))


class FakeGhSpawn:
    """The authenticated gh-api spawn (open_change + revoke): routes by argv, records env."""

    def __init__(self, *, pr_number=7, head_sha=HEAD_SHA, fail_open=False, fail_revoke=False):
        self.calls = []
        self.posted = False
        self.pr_number = pr_number
        self.head_sha = head_sha
        self.fail_open = fail_open
        self.fail_revoke = fail_revoke

    def __call__(self, argv, input_text, env):
        argv = list(argv)
        self.calls.append({"argv": argv, "input": input_text, "env": dict(env)})
        if "DELETE" in argv and "installation/token" in argv:
            rc = 1 if self.fail_revoke else 0
            return _CP(argv, rc, stdout="" if rc else "{}", stderr="revoke boom" if rc else "")
        if "POST" in argv:  # open the PR
            if self.fail_open:
                return _CP(argv, 1, stderr="open boom")
            self.posted = True
            return _CP(argv, 0, stdout=json.dumps(
                {"number": self.pr_number, "head": {"sha": self.head_sha}}))
        if "GET" in argv:  # read open pulls (none until POSTed)
            body = ([{"number": self.pr_number, "head": {"sha": self.head_sha}}]
                    if self.posted else [])
            return _CP(argv, 0, stdout=json.dumps(body))
        raise AssertionError(f"unexpected gh argv: {argv}")  # pragma: no cover

    def verb_calls(self, *needles):
        return [c for c in self.calls if all(n in c["argv"] for n in needles)]


class FakeGit:
    """The push spawn: rev-parse (local head) / ls-remote / merge-base / push."""

    def __init__(self, *, local=LOCAL, remote=None, push_rc=0):
        self.calls = []
        self.local = local
        self.remote = remote
        self.push_rc = push_rc

    def __call__(self, argv, input_text, env):
        argv = list(argv)
        self.calls.append({"argv": argv, "env": dict(env)})
        if "rev-parse" in argv:
            return _CP(argv, 0, stdout=self.local + "\n")
        if "ls-remote" in argv:
            out = f"{self.remote}\trefs/heads/{BRANCH}\n" if self.remote else ""
            return _CP(argv, 0, stdout=out)
        if "merge-base" in argv:
            return _CP(argv, 0)
        if "push" in argv:
            return _CP(argv, self.push_rc, stderr="push boom" if self.push_rc else "")
        raise AssertionError(f"unexpected git argv: {argv}")  # pragma: no cover

    def pushed(self):
        return [c for c in self.calls if "push" in c["argv"]]


def _seed_dispatch(root: Path, *, spawned=True, failed=False, change=None, policy=None) -> str:
    """Materialize a schema-valid dispatch (via the bridge), then stamp spawn/failure/change state."""
    plan = coordination.DispatchPlan(
        scope_id="rate-limit-login",
        runtime_policy=policy or {"spend_envelopes": [{"scope": "run", "cap_usd": 5}]},
        mutation_class="code",
        scope_ratification={"approver_ref": "a" * 64, "ratified_scope_sha": "b" * 64},
    )
    rec = v3_seat_bridge.materialize_dispatch(plan, root, now=_FIXED_NOW)
    if spawned:
        rec.data["terminal"] = {"kind": "tmux", "session_id": "$1", "window_id": "@2", "pane_id": "%3"}
        rec.data["spawned_at"] = "20260611T093000Z"
    if failed:
        rec.data["spawn_failed_at"] = "20260611T093000Z"
        rec.data["spawn_failure_reason"] = "CC-D-6 refused"
    if change is not None:
        rec.data["change"] = change
    v3_seat_bridge._write_record(rec)
    return rec.run_id


# ---------------------------------------------------------------------------
# Boundary invariant — AST proves zero v1 imports
# ---------------------------------------------------------------------------

def test_forge_join_imports_no_v1_module():
    src = Path(v3_forge_join.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    referenced: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                referenced.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                referenced.add(node.module.split(".")[0])
            if node.level and node.module is None:
                for alias in node.names:
                    referenced.add(alias.name.split(".")[0])
    crossed = referenced & ver.V1_RUNTIME
    assert crossed == set(), f"forge-join must import no v1 module, found: {sorted(crossed)}"


def test_forge_join_classified_v3():
    assert ver.classify("v3_forge_join") == ver.V3
    assert "v3_forge_join" in ver.V3_RUNTIME


# ---------------------------------------------------------------------------
# load_app_config — fail-closed, ids never reach a record
# ---------------------------------------------------------------------------

def _write_cfg(tmp_path, **over) -> Path:
    data = {
        "client_id": "Iv1.client", "installation_id": 139551869,
        "pem_path": "/host/.ce-keys/ce-forge-app.pem", "repo": REPO,
        "permissions": {"contents": "write", "pull_requests": "write"},
    }
    data.update(over)
    p = tmp_path / "ce-forge-app.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_app_config_reads_fields(tmp_path):
    cfg = load_app_config(_write_cfg(tmp_path))
    assert cfg.client_id == "Iv1.client"
    assert cfg.installation_id == 139551869
    assert cfg.repo == REPO
    assert ("contents", "write") in cfg.permissions


def test_load_app_config_repr_hides_app_ids(tmp_path):
    cfg = load_app_config(_write_cfg(tmp_path))
    text = repr(cfg)
    assert "139551869" not in text and "Iv1.client" not in text
    assert "redacted" in text


def test_load_app_config_fail_closed_missing_file(tmp_path):
    with pytest.raises(ForgeJoinRefused):
        load_app_config(tmp_path / "absent.json")


@pytest.mark.parametrize("bad", [
    {"client_id": ""}, {"installation_id": "not-int"}, {"installation_id": 0},
    {"pem_path": ""}, {"repo": "not-a-repo"},
])
def test_load_app_config_fail_closed_bad_fields(tmp_path, bad):
    with pytest.raises(ForgeJoinRefused):
        load_app_config(_write_cfg(tmp_path, **bad))


def test_load_app_config_malformed_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ForgeJoinRefused):
        load_app_config(p)


# ---------------------------------------------------------------------------
# openssl_signer — the App private key stays behind openssl (PEM off-process)
# ---------------------------------------------------------------------------

def test_openssl_signer_execs_openssl_with_input_on_stdin():
    captured = {}

    def fake_openssl(argv, input=None, capture_output=False):
        captured["argv"] = list(argv)
        captured["input"] = input
        return _CP(argv, 0, stdout=b"RAW_SIGNATURE_BYTES")

    sign = openssl_signer("/host/key.pem", runner=fake_openssl)
    sig = sign(b"b64header.b64payload")
    assert sig == b"RAW_SIGNATURE_BYTES"
    assert captured["argv"] == ["openssl", "dgst", "-sha256", "-sign", "/host/key.pem"]
    # the signing input rides STDIN; the PEM is named in argv (openssl reads the file itself)
    assert captured["input"] == b"b64header.b64payload"


def test_openssl_signer_refuses_nonzero_exit():
    sign = openssl_signer("/host/key.pem", runner=lambda *a, **k: _CP(a[0] if a else [], 1))
    with pytest.raises(ForgeJoinRefused):
        sign(b"x")


def test_openssl_signer_refuses_empty_signature():
    sign = openssl_signer("/host/key.pem", runner=lambda *a, **k: _CP([], 0, stdout=b""))
    with pytest.raises(ForgeJoinRefused):
        sign(b"x")


def test_openssl_signer_composes_into_build_app_jwt():
    sign = openssl_signer("/host/key.pem", runner=lambda *a, **k: _CP([], 0, stdout=b"sigbytes"))
    jwt = build_app_jwt("Iv1.client", signer=sign, now=lambda: 1_700_000_000.0)
    assert jwt.count(".") == 2  # header.payload.signature


# ---------------------------------------------------------------------------
# policy_sha — canonical derivation
# ---------------------------------------------------------------------------

def test_policy_sha_uses_existing_hex_or_derives():
    assert policy_sha({"policy_sha": "e" * 64}) == "e" * 64
    derived = policy_sha({"a": 1})
    assert len(derived) == 64 and derived == policy_sha({"a": 1})


# ---------------------------------------------------------------------------
# open_change_for_run — preconditions BEFORE any forge call
# ---------------------------------------------------------------------------

def test_open_refuses_unknown_dispatch_before_mint(tmp_path):
    mint = FakeMintRunner()
    with pytest.raises(ForgeJoinRefused):
        open_change_for_run(
            tmp_path, "run-ghost", app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], mint_gh_runner=mint,
        )
    assert mint.calls == []  # never minted


def test_open_refuses_unspawned_run_before_mint(tmp_path):
    run_id = _seed_dispatch(tmp_path, spawned=False)
    mint = FakeMintRunner()
    with pytest.raises(ForgeJoinRefused):
        open_change_for_run(
            tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], mint_gh_runner=mint,
        )
    assert mint.calls == []


def test_open_refuses_spawn_failed_run(tmp_path):
    run_id = _seed_dispatch(tmp_path, spawned=False, failed=True)
    mint = FakeMintRunner()
    with pytest.raises(ForgeJoinRefused):
        open_change_for_run(
            tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], mint_gh_runner=mint,
        )
    assert mint.calls == []


def test_open_refuses_already_stamped_change(tmp_path):
    run_id = _seed_dispatch(tmp_path, change={
        "branch": BRANCH, "base": "main", "pr_number": 5,
        "head_sha": HEAD_SHA, "manifest_paths": ["a.py"], "opened_at": "2026-06-11T09:30:00Z"})
    mint = FakeMintRunner()
    with pytest.raises(ForgeJoinRefused):
        open_change_for_run(
            tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], mint_gh_runner=mint,
        )
    assert mint.calls == []


# ---------------------------------------------------------------------------
# Plan-by-default mutates nothing durable
# ---------------------------------------------------------------------------

def test_plan_mode_mints_reads_revokes_but_stamps_no_change(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    mint, git, gh = FakeMintRunner(), FakeGit(remote=None), FakeGhSpawn()
    ref = open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py", "b.py"], apply=False,
        mint_gh_runner=mint, git_spawn=git, token_spawn=gh,
    )
    assert ref.pr_number is None  # would-create plan
    assert git.pushed() == []  # plan never pushes
    assert gh.verb_calls("POST") == []  # plan never opens
    # the token was still minted (to READ) and revoked
    assert len(mint.calls) == 1 and gh.verb_calls("DELETE", "installation/token")
    # NO change block stamped — plan mutates nothing durable
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    assert "change" not in drec


# ---------------------------------------------------------------------------
# apply=True drives mint→push→open→stamp→revoke
# ---------------------------------------------------------------------------

def test_apply_drives_full_chain_and_stamps_change_block(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    mint, git, gh = FakeMintRunner(), FakeGit(remote=None), FakeGhSpawn(pr_number=7)
    ref = open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True, now=_FIXED_NOW,
        mint_gh_runner=mint, git_spawn=git, token_spawn=gh,
    )
    assert ref.pr_number == 7 and ref.head_sha == HEAD_SHA
    assert git.pushed()  # the branch was pushed
    assert gh.verb_calls("POST")  # a PR was opened
    assert gh.verb_calls("DELETE", "installation/token")  # token revoked
    # the value-free change block landed on dispatch.yaml
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    change = drec["change"]
    assert change["pr_number"] == 7 and change["branch"] == BRANCH and change["base"] == "main"
    assert change["head_sha"] == HEAD_SHA and change["manifest_paths"] == ["a.py"]
    assert change["opened_at"] == "2026-06-11T09:30:00Z"


def test_apply_stamped_dispatch_conforms_to_schema(tmp_path):
    import jsonschema
    run_id = _seed_dispatch(tmp_path)
    open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True, now=_FIXED_NOW,
        mint_gh_runner=FakeMintRunner(), git_spawn=FakeGit(remote=None), token_spawn=FakeGhSpawn(),
    )
    schema = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "schemas" / "dispatch-record.schema.yaml")
        .read_text(encoding="utf-8")
    )
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    jsonschema.validate(drec, schema)  # the stamped change block validates


def test_apply_with_git_identity_stamps_f6_restamp_anchor(tmp_path):
    # F6: when the git identity seam is supplied, open stamps base_sha + the change identity.
    import jsonschema
    from creator_engine_validator.v3_forge_join import default_git_runner  # noqa: F401 (export check)
    run_id = _seed_dispatch(tmp_path)

    def git_identity(argv, input_text=None):
        argv = list(argv)
        if "patch-id" in argv:
            return _CP(argv, 0, stdout="aa" * 20 + " " + "0" * 40 + "\n")
        if "rev-parse" in argv:
            ref = str(argv[-1])
            if ref == "main":
                return _CP(argv, 0, stdout="cc" * 20 + "\n")  # base_sha
            return _CP(argv, 0, stdout="bb" * 20 + "\n")  # head tree
        if "diff" in argv:
            return _CP(argv, 0, stdout="SOME-DIFF\n")
        raise AssertionError(f"unexpected git argv: {argv}")  # pragma: no cover

    open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["validators/a.py"], apply=True, now=_FIXED_NOW,
        mint_gh_runner=FakeMintRunner(), git_spawn=FakeGit(remote=None),
        token_spawn=FakeGhSpawn(), git_identity_runner=git_identity,
    )
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    change = drec["change"]
    assert change["base_sha"] == "cc" * 20
    assert change["head_tree_sha"] == "bb" * 20
    assert len(change["content_diff_id"]) == 64 and len(change["proof_inputs_sha256"]) == 64
    assert len(change["manifest_paths_sha256"]) == 64
    schema = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "schemas" / "dispatch-record.schema.yaml")
        .read_text(encoding="utf-8")
    )
    jsonschema.validate(drec, schema)  # the richer change block still validates


# ---------------------------------------------------------------------------
# JIT token: EXACT least-privilege + revoke on success AND failure
# ---------------------------------------------------------------------------

def test_token_request_is_exact_least_privilege(tmp_path, monkeypatch):
    run_id = _seed_dispatch(tmp_path)
    seen = {}
    import creator_engine_validator.v3_forge_join as mod
    real_mint = mod.mint_scoped_token

    def spy_mint(request, *, gh_runner=None):
        seen["request"] = request
        return real_mint(request, gh_runner=gh_runner)

    monkeypatch.setattr(mod, "mint_scoped_token", spy_mint)
    open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True, now=_FIXED_NOW,
        mint_gh_runner=FakeMintRunner(), git_spawn=FakeGit(remote=None), token_spawn=FakeGhSpawn(),
    )
    req = seen["request"]
    assert dict(req.permissions) == {"contents": "write", "pull_requests": "write"}
    assert 0 < req.requested_ttl_seconds <= 900


def test_revoke_runs_even_when_open_fails(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    gh = FakeGhSpawn(fail_open=True)
    with pytest.raises(ForgeConfigError):
        open_change_for_run(
            tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
            manifest_paths=["a.py"], apply=True,
            mint_gh_runner=FakeMintRunner(), git_spawn=FakeGit(remote=None), token_spawn=gh,
        )
    # the credential is released on the failure path too
    assert gh.verb_calls("DELETE", "installation/token")
    # no change block stamped on a failed open
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    assert "change" not in drec


def test_revoke_failure_is_swallowed_not_masking(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    # open succeeds; revoke transport fails — must NOT raise (best-effort, token expires on ttl)
    ref = open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True,
        mint_gh_runner=FakeMintRunner(), git_spawn=FakeGit(remote=None),
        token_spawn=FakeGhSpawn(fail_revoke=True),
    )
    assert ref.pr_number == 7


# ---------------------------------------------------------------------------
# Secret hygiene — the gate's heart
# ---------------------------------------------------------------------------

def test_token_value_in_no_argv_and_no_record_bytes(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    mint, git, gh = FakeMintRunner(), FakeGit(remote=None), FakeGhSpawn()
    open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True, now=_FIXED_NOW,
        mint_gh_runner=mint, git_spawn=git, token_spawn=gh,
    )
    # the sentinel token NEVER appears in any argv (git or gh) or input body
    for c in git.calls + gh.calls:
        assert SENTINEL not in " ".join(c["argv"])
    for c in gh.calls:
        assert SENTINEL not in str(c.get("input"))
    # nor in the persisted dispatch record bytes
    drec_bytes = (tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text()
    assert SENTINEL not in drec_bytes


def test_token_value_only_in_authenticated_call_env(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    git, gh = FakeGit(remote=None), FakeGhSpawn()
    open_change_for_run(
        tmp_path, run_id, app_config=_app_config(), branch=BRANCH,
        manifest_paths=["a.py"], apply=True,
        mint_gh_runner=FakeMintRunner(), git_spawn=git, token_spawn=gh,
    )
    # the authenticated gh calls (open + revoke) carry GH_TOKEN; local git read calls do not
    for c in gh.calls:
        assert c["env"].get("GH_TOKEN") == SENTINEL
    for c in git.calls:
        if "rev-parse" in c["argv"] or "merge-base" in c["argv"]:
            assert "GH_TOKEN" not in c["env"]
        if "push" in c["argv"]:
            assert c["env"].get("GH_TOKEN") == SENTINEL


# ===========================================================================
# v3.1-G2c — merge_for_run (gated merge; distinct identity; pr_merged on real merge)
# ===========================================================================
from creator_engine_validator import evidence_sink as _evidence_sink
from creator_engine_validator import runtime_evidence_spine as _spine
from creator_engine_validator.forge.merge import MergeRefused
from creator_engine_validator.runner.backend import CollectedEvidence
from creator_engine_validator.v3_forge_join import ambient_gh_runner, merge_for_run


import hashlib as _hashlib

from creator_engine_validator.forge.github_repo_config import ForgeConfigError as _ForgeConfigError

OLD_HEAD = "d" * 40
OLD_BASE = "a1" * 20
NEW_HEAD = "c" * 40
NEW_BASE = "b2" * 20
CARRIER_PATH = ".ce/pr-manifests/f6-restamp-test.md"


def _carrier_text(paths, *, note="x") -> str:
    """A minimal but valid per-PR carrier (parse_carrier-readable): COUNT + SHA256 + fenced block.

    ``note`` lets two carriers share a path-set (same normalized hash) while differing in
    mechanical prose — the scenario-5 base-pin drift case.
    """
    uniq = sorted({p for p in paths if p})
    norm = "\n".join(uniq) + "\n"
    sha = _hashlib.sha256(norm.encode("utf-8")).hexdigest()
    body = "\n".join(uniq)
    return (f"# carrier — {note}\n\nAUTHORIZED_PATHS_COUNT={len(uniq)}\n\n"
            f"AUTHORIZED_PATHS_SHA256={sha}\n\n```text\n{body}\n```\n")


class FakeMergeGh:
    """Routes the gated-merge gh calls: the combined pr_state read, the 3 gate reads, + the PUT."""

    def __init__(self, *, review="APPROVED", rollup="SUCCESS", merge_state="CLEAN",
                 mergeable="MERGEABLE", merged=True, commit="f" * 40, put_rc=0, put_stderr="",
                 live_head=OLD_HEAD, live_base=OLD_BASE, branch=BRANCH, base="main"):
        self.calls = []
        self.review = review
        self.rollup = rollup
        self.merge_state = merge_state
        self.mergeable = mergeable
        self.merged = merged
        self.commit = commit
        self.put_rc = put_rc
        self.put_stderr = put_stderr
        self.live_head = live_head
        self.live_base = live_base
        self.branch = branch
        self.base = base

    def __call__(self, argv, input_text=None):
        argv = list(argv)
        self.calls.append(argv)
        joined = " ".join(argv)
        if "-X" in argv and "PUT" in argv:
            out = json.dumps({"merged": self.merged, "sha": self.commit}) if self.put_rc == 0 else ""
            return _CP(argv, self.put_rc, stdout=out, stderr=self.put_stderr)
        if "headRefName" in joined:  # the F6 combined pr_state read (checked FIRST)
            return _CP(argv, 0, stdout=json.dumps({"data": {"repository": {"pullRequest": {
                "number": 7, "headRefName": self.branch, "baseRefName": self.base,
                "headRefOid": self.live_head, "baseRefOid": self.live_base,
                "reviewDecision": self.review, "mergeStateStatus": self.merge_state,
                "mergeable": self.mergeable,
                "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": self.rollup}}}]}}}}}))
        if "reviewDecision" in joined:
            return _CP(argv, 0, stdout=json.dumps(
                {"data": {"repository": {"pullRequest": {"reviewDecision": self.review}}}}))
        if "statusCheckRollup" in joined:
            return _CP(argv, 0, stdout=json.dumps({"data": {"repository": {"pullRequest": {
                "headRefOid": self.live_head,
                "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": self.rollup}}}]}}}}}))
        if "mergeStateStatus" in joined:
            return _CP(argv, 0, stdout=json.dumps({"data": {"repository": {"pullRequest": {
                "mergeStateStatus": self.merge_state, "mergeable": self.mergeable}}}}))
        raise AssertionError(f"unexpected merge gh argv: {joined}")  # pragma: no cover

    def did_put(self):
        return any("-X" in c and "PUT" in c for c in self.calls)


class FakeGitRunner:
    """The injected git seam for identity/tree/carrier reads (subprocess.run shape). Zero live git.

    ``content_by_head`` maps a head SHA to its NON-mechanical diff signature (equal signatures →
    equal ``content_diff_id`` + stable patch-id → base-only equivalence). ``carrier_by_head`` maps
    a head SHA to its carrier text (path-set drift → different normalized hash). ``tree_by_ref``
    maps a ref to its tree (the audit equivalence). ``unavailable`` refs raise (legacy-unprovable).
    """

    def __init__(self, *, content_by_head=None, carrier_by_head=None, tree_by_ref=None,
                 resolve_by_ref=None, default_content="SRC-DIFF", default_tree="a" * 40,
                 unavailable=()):
        self.content_by_head = content_by_head or {}
        self.carrier_by_head = carrier_by_head or {}
        self.tree_by_ref = tree_by_ref or {}
        self.resolve_by_ref = resolve_by_ref or {}
        self.default_content = default_content
        self.default_tree = default_tree
        self.unavailable = set(unavailable)
        self.calls = []

    def __call__(self, argv, input_text=None):
        argv = list(argv)
        self.calls.append(argv)
        if "patch-id" in argv:
            pid = _hashlib.sha1((input_text or "").encode("utf-8")).hexdigest()
            return _CP(argv, 0, stdout=f"{pid} {'0' * 40}\n")
        if "rev-parse" in argv:
            ref = str(argv[-1])
            if ref.endswith("^{tree}"):
                base = ref[: -len("^{tree}")]
                if base in self.unavailable:
                    return _CP(argv, 128, stderr="bad object")
                return _CP(argv, 0, stdout=self.tree_by_ref.get(base, self.default_tree) + "\n")
            if ref in self.unavailable:
                return _CP(argv, 128, stderr="bad revision")
            return _CP(argv, 0, stdout=self.resolve_by_ref.get(ref, ref) + "\n")
        if "diff" in argv:
            spec = next((a for a in argv if ".." in a), "")
            base_ref, _, head = spec.partition("..")
            if head in self.unavailable or base_ref in self.unavailable:
                return _CP(argv, 128, stderr="bad revision")
            return _CP(argv, 0, stdout=self.content_by_head.get(head, self.default_content))
        if "show" in argv:
            ref = str(argv[-1]).partition(":")[0]
            if ref in self.unavailable:
                return _CP(argv, 128, stderr="bad object")
            text = self.carrier_by_head.get(ref)
            if text is None:
                return _CP(argv, 128, stderr="path does not exist")
            return _CP(argv, 0, stdout=text)
        raise AssertionError(f"unexpected git argv: {argv}")  # pragma: no cover


def _collected_author_run(tmp_path, *, pr_number=7, head_sha=OLD_HEAD, policy_sha="e" * 64,
                          base_sha=None, manifest_paths=("validators/x.py",)):
    """A spawned+collected author dispatch with a persisted pr_opened chain; returns run_id."""
    run_id = _seed_dispatch(tmp_path)  # spawned
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    drec["collected_at"] = "2026-06-11T09:31:00Z"
    (tmp_path / "dispatches" / run_id / "dispatch.yaml").write_text(
        yaml.safe_dump(drec, sort_keys=True), encoding="utf-8")
    change_set = {"branch": BRANCH, "base": "main", "manifest_paths": list(manifest_paths),
                  "head_sha": head_sha, "pr_number": pr_number}
    if base_sha:
        change_set["base_sha"] = base_sha
    body = {
        "kind": _spine.RUN_OUTCOME_RECORD_KIND, "record_type": _spine.RUN_OUTCOME_RECORD_TYPE,
        "schema_version": "1", "policy_sha": policy_sha, "run_id": run_id,
        "recorded_at": "2026-06-11T09:30:00+00:00", "outcome": "pr_opened",
        "change_set": change_set,
    }
    chain = [_spine.append([], body)]
    sink = _evidence_sink.file_evidence_sink(tmp_path / "runs")
    sink(CollectedEvidence(handle_ref=run_id, records=tuple(chain), note="g2c-test"))
    return run_id


def _records(tmp_path, run_id):
    doc = yaml.safe_load((tmp_path / "runs" / f"{run_id}.runtime-evidence.yaml").read_text())
    return doc["records"]


def test_merge_plan_reads_gate_and_attests_nothing(tmp_path):
    run_id = _collected_author_run(tmp_path)
    gh = FakeMergeGh()
    result = merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=False)
    assert result.head_status == "unchanged"
    assert result.would_merge is True and result.merged is False and result.eligible is True
    assert not gh.did_put()  # plan mode never PUTs
    outcomes = [r["outcome"] for r in _records(tmp_path, run_id) if r.get("outcome")]
    assert outcomes == ["pr_opened"]


def test_merge_apply_unchanged_head_attests_pr_merged_and_audit(tmp_path):
    # Scenario 1: unchanged head merges with the attested head + appends a PASSING merge audit.
    run_id = _collected_author_run(tmp_path, pr_number=7)
    gh = FakeMergeGh(merged=True, commit="f" * 40, live_head=OLD_HEAD)
    git = FakeGitRunner(tree_by_ref={OLD_HEAD: "a" * 40, "f" * 40: "a" * 40})  # tested == merged tree
    result = merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=git)
    assert result.merged is True and result.merge_commit_sha == "f" * 40
    assert result.head_status == "unchanged" and result.restamp_recorded is False
    assert result.audit_tree_equivalence is True
    assert gh.did_put()
    records = _records(tmp_path, run_id)
    outcomes = [r["outcome"] for r in records if r.get("outcome")]
    assert outcomes == ["pr_opened", "pr_merged"]
    audits = [r for r in records if r.get("record_type") == "runtime_merge_audit"]
    assert len(audits) == 1 and audits[0]["tree_equivalence"] is True
    assert audits[0]["tested_head_sha"] == OLD_HEAD
    assert _spine.verify_chain(records) == []


def test_merge_apply_base_only_restamps_then_merges_new_head(tmp_path):
    # Scenario 2: base-only drift — same content diff + patch-id → restamp + merge new head + audit.
    paths = ["validators/x.py", CARRIER_PATH]
    run_id = _collected_author_run(tmp_path, base_sha=OLD_BASE, manifest_paths=paths)
    gh = FakeMergeGh(merged=True, commit="f" * 40, live_head=NEW_HEAD, live_base=NEW_BASE)
    carrier = _carrier_text(paths)
    git = FakeGitRunner(
        content_by_head={OLD_HEAD: "SAME-DIFF", NEW_HEAD: "SAME-DIFF"},
        carrier_by_head={OLD_HEAD: carrier, NEW_HEAD: carrier},
        tree_by_ref={NEW_HEAD: "a" * 40, "f" * 40: "a" * 40},
    )
    # plan first: reports the availability, mutates nothing
    plan = merge_for_run(tmp_path, run_id, merge_gh_runner=FakeMergeGh(
        live_head=NEW_HEAD, live_base=NEW_BASE), apply=False, git_runner=git)
    assert plan.head_status == "base_only_restamp_available"
    assert plan.old_head_sha == OLD_HEAD and plan.new_head_sha == NEW_HEAD
    assert [r["outcome"] for r in _records(tmp_path, run_id) if r.get("outcome")] == ["pr_opened"]
    # apply: restamp + merge new head + audit
    result = merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=git)
    assert result.merged is True and result.head_status == "base_only_restamped"
    assert result.restamp_recorded is True and result.audit_tree_equivalence is True
    records = _records(tmp_path, run_id)
    restamps = [r for r in records if r.get("record_type") == "runtime_change_restamp"]
    assert len(restamps) == 1
    rs = restamps[0]
    assert rs["restamp_type"] == "base_only" and rs["authority"] == "machine_rebase_equivalence"
    assert rs["old_head_sha"] == OLD_HEAD and rs["new_head_sha"] == NEW_HEAD
    assert rs["old_content_diff_id"] == rs["new_content_diff_id"]
    assert rs["old_patch_id"] == rs["new_patch_id"]
    # pr_merged points at the NEW (restamped) head
    merged = [r for r in records if r.get("outcome") == "pr_merged"][0]
    assert merged["change_set"]["head_sha"] == NEW_HEAD
    assert _spine.verify_chain(records) == []


def test_merge_apply_content_drift_refuses_before_put(tmp_path):
    # Scenario 3: changed non-mechanical diff identity refuses before any merge PUT.
    paths = ["validators/x.py", CARRIER_PATH]
    run_id = _collected_author_run(tmp_path, base_sha=OLD_BASE, manifest_paths=paths)
    gh = FakeMergeGh(live_head=NEW_HEAD, live_base=NEW_BASE)
    carrier = _carrier_text(paths)
    git = FakeGitRunner(
        content_by_head={OLD_HEAD: "DIFF-A", NEW_HEAD: "DIFF-B"},  # content changed
        carrier_by_head={OLD_HEAD: carrier, NEW_HEAD: carrier},
    )
    with pytest.raises(ForgeJoinRefused) as ei:
        merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=git)
    assert "content_drift_requires_reratification" in str(ei.value)
    assert not gh.did_put()
    assert [r["outcome"] for r in _records(tmp_path, run_id) if r.get("outcome")] == ["pr_opened"]


def test_merge_apply_pathset_drift_refuses_before_put(tmp_path):
    # Scenario 4: changed carrier path-set refuses before any merge PUT.
    paths = ["validators/x.py", CARRIER_PATH]
    run_id = _collected_author_run(tmp_path, base_sha=OLD_BASE, manifest_paths=paths)
    gh = FakeMergeGh(live_head=NEW_HEAD, live_base=NEW_BASE)
    git = FakeGitRunner(
        content_by_head={OLD_HEAD: "SAME", NEW_HEAD: "SAME"},
        carrier_by_head={OLD_HEAD: _carrier_text(paths),
                         NEW_HEAD: _carrier_text(paths + ["validators/extra.py"])},  # path added
    )
    with pytest.raises(ForgeJoinRefused) as ei:
        merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=git)
    assert "content_drift_requires_reratification" in str(ei.value)
    assert not gh.did_put()


def test_merge_apply_mechanical_carrier_basepin_drift_accepted(tmp_path):
    # Scenario 5: carrier base/head PROSE differs but path-set hash unchanged → base-only accepted.
    paths = ["validators/x.py", CARRIER_PATH]
    run_id = _collected_author_run(tmp_path, base_sha=OLD_BASE, manifest_paths=paths)
    gh = FakeMergeGh(merged=True, live_head=NEW_HEAD, live_base=NEW_BASE)
    git = FakeGitRunner(
        content_by_head={OLD_HEAD: "SAME", NEW_HEAD: "SAME"},
        carrier_by_head={OLD_HEAD: _carrier_text(paths, note="base-OLD"),
                         NEW_HEAD: _carrier_text(paths, note="base-NEW")},  # same path-set, new prose
        tree_by_ref={NEW_HEAD: "a" * 40, "f" * 40: "a" * 40},
    )
    result = merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=git)
    assert result.merged is True and result.restamp_recorded is True


def test_merge_apply_legacy_chain_refuses_before_put(tmp_path):
    # Scenario 6: no base_sha (legacy) → refuse as restamp_legacy_unprovable, no PUT, no restamp.
    run_id = _collected_author_run(tmp_path, base_sha=None)  # legacy: no anchor
    gh = FakeMergeGh(live_head=NEW_HEAD, live_base=NEW_BASE)
    with pytest.raises(ForgeJoinRefused) as ei:
        merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=FakeGitRunner())
    assert "restamp_legacy_unprovable" in str(ei.value)
    assert not gh.did_put()
    records = _records(tmp_path, run_id)
    assert not any(r.get("record_type") == "runtime_change_restamp" for r in records)


def test_merge_apply_old_refs_unavailable_is_legacy_unprovable(tmp_path):
    # Scenario 6b: base_sha present but old refs cannot be resolved → legacy-unprovable.
    paths = ["validators/x.py", CARRIER_PATH]
    run_id = _collected_author_run(tmp_path, base_sha=OLD_BASE, manifest_paths=paths)
    gh = FakeMergeGh(live_head=NEW_HEAD, live_base=NEW_BASE)
    git = FakeGitRunner(unavailable=(OLD_HEAD, OLD_BASE))  # old objects gone
    with pytest.raises(ForgeJoinRefused) as ei:
        merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=git)
    assert "restamp_legacy_unprovable" in str(ei.value)
    assert not gh.did_put()


def test_merge_apply_head_race_refused_no_pr_merged(tmp_path):
    # Scenario 7: server rejects the head-pinned merge (head moved post-read) → ForgeConfigError,
    # no pr_merged appended.
    run_id = _collected_author_run(tmp_path)
    gh = FakeMergeGh(put_rc=1, put_stderr="409 head changed", live_head=OLD_HEAD)
    git = FakeGitRunner(tree_by_ref={OLD_HEAD: "a" * 40})
    with pytest.raises(_ForgeConfigError):
        merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=git)
    assert [r["outcome"] for r in _records(tmp_path, run_id) if r.get("outcome")] == ["pr_opened"]


def test_merge_audit_tree_mismatch_records_alarm(tmp_path):
    # Scenario 8: merged tree != tested tree → audit recorded with tree_equivalence False (alarm).
    run_id = _collected_author_run(tmp_path)
    gh = FakeMergeGh(merged=True, commit="f" * 40, live_head=OLD_HEAD)
    git = FakeGitRunner(tree_by_ref={OLD_HEAD: "a" * 40, "f" * 40: "b" * 40})
    result = merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=git)
    assert result.merged is True and result.audit_tree_equivalence is False
    audits = [r for r in _records(tmp_path, run_id) if r.get("record_type") == "runtime_merge_audit"]
    assert len(audits) == 1 and audits[0]["tree_equivalence"] is False


def test_merge_apply_ineligible_refuses_and_attests_nothing(tmp_path):
    run_id = _collected_author_run(tmp_path)
    gh = FakeMergeGh(rollup="FAILURE")  # checks not green → ineligible
    with pytest.raises(MergeRefused):
        merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=FakeGitRunner())
    assert not gh.did_put()  # never merged an ungated PR
    assert [r["outcome"] for r in _records(tmp_path, run_id) if r.get("outcome")] == ["pr_opened"]


def test_merge_plan_ineligible_reports_would_not_merge(tmp_path):
    run_id = _collected_author_run(tmp_path)
    gh = FakeMergeGh(review="CHANGES_REQUESTED")
    result = merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=False)
    assert result.would_merge is False and result.merged is False


def test_merge_plan_content_drift_reports_status_no_mutation(tmp_path):
    # Plan mode never raises for drift — it reports content_drift_refused and mutates nothing.
    paths = ["validators/x.py", CARRIER_PATH]
    run_id = _collected_author_run(tmp_path, base_sha=OLD_BASE, manifest_paths=paths)
    gh = FakeMergeGh(live_head=NEW_HEAD, live_base=NEW_BASE)
    git = FakeGitRunner(
        content_by_head={OLD_HEAD: "A", NEW_HEAD: "B"},
        carrier_by_head={OLD_HEAD: _carrier_text(paths), NEW_HEAD: _carrier_text(paths)},
    )
    result = merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=False, git_runner=git)
    assert result.head_status == "content_drift_refused" and result.would_merge is False
    assert not gh.did_put()
    assert [r["outcome"] for r in _records(tmp_path, run_id) if r.get("outcome")] == ["pr_opened"]


def test_merge_refuses_uncollected_run(tmp_path):
    run_id = _seed_dispatch(tmp_path)  # spawned but NOT collected
    with pytest.raises(ForgeJoinRefused):
        merge_for_run(tmp_path, run_id, merge_gh_runner=FakeMergeGh(), apply=False)


def test_merge_refuses_when_chain_has_no_pr(tmp_path):
    run_id = _seed_dispatch(tmp_path)
    drec = yaml.safe_load((tmp_path / "dispatches" / run_id / "dispatch.yaml").read_text())
    drec["collected_at"] = "2026-06-11T09:31:00Z"
    (tmp_path / "dispatches" / run_id / "dispatch.yaml").write_text(yaml.safe_dump(drec))
    # a no_change chain (no pr_opened with a pr_number)
    body = {
        "kind": _spine.RUN_OUTCOME_RECORD_KIND, "record_type": _spine.RUN_OUTCOME_RECORD_TYPE,
        "schema_version": "1", "policy_sha": "e" * 64, "run_id": run_id,
        "recorded_at": "2026-06-11T09:30:00+00:00", "outcome": "no_change",
        "change_set": {"branch": run_id, "base": "main", "manifest_paths": [], "head_sha": run_id},
    }
    sink = _evidence_sink.file_evidence_sink(tmp_path / "runs")
    sink(CollectedEvidence(handle_ref=run_id, records=(_spine.append([], body),), note="x"))
    with pytest.raises(ForgeJoinRefused):
        merge_for_run(tmp_path, run_id, merge_gh_runner=FakeMergeGh(), apply=True)


def test_merge_uses_distinct_identity_no_token_minted(tmp_path, monkeypatch):
    # Scenario 9: merge_for_run mints NO per-run token — the merge rides the injected runner only.
    import creator_engine_validator.v3_forge_join as mod
    monkeypatch.setattr(mod, "mint_scoped_token",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("merge minted a token!")))
    run_id = _collected_author_run(tmp_path)
    result = merge_for_run(tmp_path, run_id, merge_gh_runner=FakeMergeGh(), apply=True,
                           git_runner=FakeGitRunner())
    assert result.merged is True


def test_merge_identity_drift_refuses(tmp_path):
    # A re-targeted PR (branch/base changed) is content drift, never a re-stamp.
    run_id = _collected_author_run(tmp_path, base_sha=OLD_BASE)
    gh = FakeMergeGh(base="release-2.0", live_head=NEW_HEAD, live_base=NEW_BASE)  # base re-targeted
    with pytest.raises(ForgeJoinRefused):
        merge_for_run(tmp_path, run_id, merge_gh_runner=gh, apply=True, git_runner=FakeGitRunner())
    assert not gh.did_put()


def test_ambient_gh_runner_injects_no_token(tmp_path):
    # the ambient runner authenticates AS the Operator's gh login — no GH_TOKEN injection.
    captured = {}

    def fake_spawn(argv, **kw):
        captured["argv"] = list(argv)
        return _CP(argv, 0, stdout="{}")

    runner = ambient_gh_runner(spawn=fake_spawn)
    runner(["gh", "api", "-X", "GET", "x"])
    assert captured["argv"][:2] == ["gh", "api"]
